"""Home Assistant integration for the SO Aroma Diffuser S6."""
import asyncio
from contextlib import suppress
from datetime import timedelta
import logging
import struct

from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from cryptography.exceptions import InvalidTag
from homeassistant.components import bluetooth
from homeassistant.const import Platform
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_ADDRESS, CONF_TOKEN, DOMAIN, POWER
from .light_timer import LightTimer, timer_store
from .protocol import ProtocolError, Session

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [
    Platform.SWITCH, Platform.NUMBER, Platform.SENSOR, Platform.TEXT,
    Platform.LIGHT, Platform.BUTTON,
]
COMMUNICATION_ERRORS = (BleakError, InvalidTag, ProtocolError, struct.error, TimeoutError)


async def async_setup_entry(hass, entry):
    coordinator = AromaS6Coordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await coordinator.light_timer.async_load()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    await entry.runtime_data.light_timer.async_close()
    await entry.runtime_data.async_close()
    return True


async def async_remove_entry(hass, entry):
    await timer_store(hass, entry.entry_id).async_remove()


class AromaS6Coordinator(DataUpdateCoordinator[dict[tuple[int, int], int]]):
    def __init__(self, hass, entry):
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=DOMAIN,
            update_interval=timedelta(minutes=2),
        )
        self.address = entry.data[CONF_ADDRESS]
        self._token = bytes.fromhex(entry.data[CONF_TOKEN])
        self._lock = asyncio.Lock()
        self._client = None
        self._session = None
        self.light_timer = LightTimer(self, entry.entry_id)

    async def _disconnect(self):
        client, self._client, self._session = self._client, None, None
        if client is not None:
            with suppress(BleakError, TimeoutError):
                async with asyncio.timeout(4):
                    await client.disconnect()

    async def async_close(self):
        async with self._lock:
            await self._disconnect()

    async def _get_session(self):
        if self._client is not None and self._client.is_connected and self._session is not None:
            return self._session
        await self._disconnect()
        device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if device is None:
            raise ProtocolError("No connectable Home Assistant Bluetooth adapter sees the diffuser")
        self._client = await establish_connection(
            BleakClientWithServiceCache, device, "SO Aroma Diffuser S6", max_attempts=2
        )
        self._session = Session(self._client)
        await self._session.authenticate(self._token)
        return self._session

    async def _exchange(self, setting=None, value=None, *, ambient=None):
        try:
            async with asyncio.timeout(28):
                session = await self._get_session()
                if ambient is not None:
                    actual = await session.set_ambient_light(*ambient)
                elif setting is None:
                    actual = await session.read_properties()
                else:
                    actual = {**self.data, **await session.set_property(setting, value)}
        except (Exception, asyncio.CancelledError):
            await self._disconnect()
            raise
        # This diffuser stops advertising when turned off. Keep its authenticated
        # GATT link open in standby so it can receive the next turn-on command.
        if actual[POWER]:
            await self._disconnect()
        return actual

    async def _async_update_data(self):
        async with self._lock:
            try:
                return await self._exchange()
            except COMMUNICATION_ERRORS as exc:
                raise UpdateFailed(str(exc) or type(exc).__name__) from exc

    async def async_set_property(self, setting, value):
        await self._async_write(setting=setting, value=value)

    async def async_set_ambient_light(self, on, color=None):
        await self._async_write(ambient=(on, color))

    async def _async_write(self, **kwargs):
        async with self._lock:
            try:
                actual = await self._exchange(**kwargs)
            except COMMUNICATION_ERRORS as exc:
                reason = str(exc) or type(exc).__name__
                self.async_set_update_error(UpdateFailed(f"Setting was not confirmed: {reason}"))
                raise HomeAssistantError(
                    "The diffuser did not confirm the requested setting"
                ) from exc
            self.async_set_updated_data(actual)
