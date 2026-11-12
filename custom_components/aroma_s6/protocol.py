"""Xiaomi standard BLE login and power control for the Aroma S6."""
import asyncio
import hmac
import secrets
import struct

from cryptography.hazmat.primitives.ciphers.aead import AESCCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .const import LIGHT_COLOR, LIGHT_GRADIENT, LIGHT_LEVEL, LIGHT_ON, POWER, PROPERTIES, PROPERTY_TYPES
READY = b"\x00\x00\x01\x01"
RECEIVED = b"\x00\x00\x01\x00"
COMPACT_RECEIVED = b"\x00\x00\x03\x00"


def _uuid(short):
    return f"0000{short:04x}-0000-1000-8000-00805f9b34fb"


CONTROL, AUTH, SEND, RECEIVE = map(_uuid, (0x10, 0x19, 0x1A, 0x1B))


class ProtocolError(Exception):
    """The diffuser did not accept or confirm the request."""


class Session:
    """One authenticated GATT connection."""

    def __init__(self, client):
        self._client = client
        self._queues = {channel: asyncio.Queue() for channel in (CONTROL, AUTH, SEND, RECEIVE)}
        self._counter = 0

    async def _write(self, channel, data):
        await self._client.write_gatt_char(channel, data, response=False)

    async def _read(self, channel):
        return await asyncio.wait_for(self._queues[channel].get(), 5)

    async def _send_parcel(self, channel, kind, data):
        chunks = [data[i:i + 18] for i in range(0, len(data), 18)]
        await self._write(channel, struct.pack("<BBBBH", 0, 0, 0, kind, len(chunks)))
        if await self._read(channel) != READY:
            raise ProtocolError("The diffuser did not accept a Bluetooth message")
        for index, chunk in enumerate(chunks, 1):
            await self._write(channel, struct.pack("<H", index) + chunk)
            if index < len(chunks):
                await asyncio.sleep(0.05)
        if await self._read(channel) != RECEIVED:
            raise ProtocolError("The diffuser did not acknowledge a Bluetooth message")

    async def _receive_parcel(self, channel):
        frame = await self._read(channel)
        if channel == RECEIVE and len(frame) > 4 and frame[:3] == b"\x00\x00\x02":
            await self._write(channel, COMPACT_RECEIVED)
            return frame[4:]
        if len(frame) != 6 or frame[:3] != b"\x00\x00\x00":
            raise ProtocolError("Unexpected Bluetooth message header")
        count = int.from_bytes(frame[4:], "little")
        if not 1 <= count <= 64:
            raise ProtocolError("Invalid Bluetooth message length")
        await self._write(channel, READY)
        chunks = []
        for index in range(1, count + 1):
            frame = await self._read(channel)
            if len(frame) <= 2 or int.from_bytes(frame[:2], "little") != index:
                raise ProtocolError("Out-of-order Bluetooth message")
            chunks.append(frame[2:])
        await self._write(channel, RECEIVED)
        return b"".join(chunks)

    async def authenticate(self, token):
        for channel, queue in self._queues.items():
            await self._client.start_notify(
                channel, lambda _sender, data, queue=queue: queue.put_nowait(bytes(data))
            )
        app_random = secrets.token_bytes(16)
        await self._write(CONTROL, b"\x24\x00\x00\x00")
        await self._send_parcel(AUTH, 0x0B, app_random)
        device_random = await self._receive_parcel(AUTH)
        proof = await self._receive_parcel(AUTH)
        if len(device_random) != 16:
            raise ProtocolError("Invalid login challenge")
        keys = HKDF(
            algorithm=SHA256(), length=64, salt=app_random + device_random,
            info=b"mible-login-info",
        ).derive(token)
        expected = hmac.digest(keys[:16], device_random + app_random, "sha256")
        if not hmac.compare_digest(proof, expected):
            raise ProtocolError("The diffuser rejected the login token")
        await self._send_parcel(AUTH, 0x0A, hmac.digest(keys[16:32], app_random + device_random, "sha256"))
        if await self._read(CONTROL) != b"\x21\x00\x00\x00":
            raise ProtocolError("The diffuser rejected the Bluetooth login")
        self._decrypt = AESCCM(keys[:16], tag_length=4)
        self._encrypt = AESCCM(keys[16:32], tag_length=4)
        self._device_iv, self._app_iv = keys[32:36], keys[36:40]

    @staticmethod
    def _nonce(iv, counter):
        return iv + bytes(4) + counter + bytes(2)

    async def _request(self, opcode, body):
        if self._counter == 65535:
            raise ProtocolError("Bluetooth session counter exhausted")
        self._counter += 1
        tid = self._counter
        counter = tid.to_bytes(2, "little")
        packet = struct.pack("<HHB", 0x2000 | (5 + len(body)), tid, opcode) + body
        ciphertext = self._encrypt.encrypt(self._nonce(self._app_iv, counter), packet, None)
        await self._send_parcel(SEND, 0, counter + ciphertext)
        return tid

    async def _property_responses(self, request_id):
        while True:
            frame = await self._receive_parcel(RECEIVE)
            if len(frame) < 6:
                continue
            nonce = self._nonce(self._device_iv, frame[:2])
            packet = self._decrypt.decrypt(nonce, frame[2:], None)
            result = _parse_properties(packet, request_id)
            if result is not None:
                yield result

    async def read_properties(self):
        body = bytes([len(PROPERTIES)]) + b"".join(
            struct.pack("<BH", *prop) for prop in PROPERTIES
        )
        request_id = await self._request(2, body)
        values = {}
        async with asyncio.timeout(8):
            async for _, updates, _ in self._property_responses(request_id):
                values.update(updates)
                if all(prop in values for prop in PROPERTIES):
                    return values

    async def set_property(self, prop, value):
        descriptor = PROPERTY_TYPES[prop]
        body = struct.pack("<BBHH", 1, *prop, descriptor) + value.to_bytes(descriptor & 0xFFF, "little")
        request_id = await self._request(0, body)
        async with asyncio.timeout(8):
            async for opcode, values, errors in self._property_responses(request_id):
                if opcode == 1 and prop in errors:
                    raise ProtocolError(f"The diffuser rejected property {prop} ({errors[prop]})")
                if values.get(prop) == value:
                    return values


    async def set_ambient_light(self, on, color=None):
        values = await self.read_properties()
        current_flags = values[LIGHT_LEVEL]
        flags = (current_flags | LIGHT_ON) if on else (current_flags & ~LIGHT_ON)
        if color is not None:
            # A palette selection uses a fixed RGB color.
            flags &= ~LIGHT_GRADIENT
        if flags != current_flags:
            values.update(await self.set_property(LIGHT_LEVEL, flags))
        if color is not None and values[LIGHT_COLOR] != color:
            values.update(await self.set_property(LIGHT_COLOR, color))
        return values


def _parse_properties(packet, request_id):
    if len(packet) < 6:
        raise ProtocolError("Short property response")
    size, tid, opcode, count = struct.unpack_from("<HHBB", packet)
    if (size & 0xFFF) != len(packet):
        raise ProtocolError("Invalid property response length")
    if opcode not in (1, 3, 4) or (opcode != 4 and tid != request_id):
        return None

    offset = 6
    values = {}
    errors = {}
    for _ in range(count):
        prop = struct.unpack_from("<BH", packet, offset)
        offset += 3
        if opcode in (1, 3):
            code = struct.unpack_from("<h", packet, offset)[0]
            offset += 2
            if code:
                errors[prop] = code
            if opcode == 1 or code:
                continue
        descriptor = struct.unpack_from("<H", packet, offset)[0]
        offset += 2
        width = descriptor & 0xFFF
        if offset + width > len(packet):
            raise ProtocolError("Truncated property value")
        if descriptor == PROPERTY_TYPES.get(prop):
            value = int.from_bytes(packet[offset:offset + width], "little")
            if prop != POWER or value in (0, 1):
                values[prop] = value
        offset += width
    return opcode, values, errors
