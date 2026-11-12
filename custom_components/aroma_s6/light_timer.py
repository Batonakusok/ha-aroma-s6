"""Countdown that switches off only the S6 ambient light."""

import asyncio
from datetime import timedelta
import logging

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN

DEFAULT_MINUTES = 2
MIN_MINUTES = 1
MAX_MINUTES = 120
RETRY_DELAY = timedelta(seconds=15)
RETRY_WINDOW = timedelta(minutes=2)
_LOGGER = logging.getLogger(__name__)


def timer_store(hass, entry_id):
    return Store(hass, 1, f"{DOMAIN}.{entry_id}.light_timer", atomic_writes=True)


class LightTimer:
    def __init__(self, coordinator, entry_id):
        self.coordinator = coordinator
        self._store = timer_store(coordinator.hass, entry_id)
        self._lock = asyncio.Lock()
        self._cancel = None
        self._closed = False
        self.minutes = DEFAULT_MINUTES
        self.deadline = None

    async def async_load(self):
        data = await self._store.async_load() or {}
        minutes = data.get("minutes")
        if type(minutes) is int and MIN_MINUTES <= minutes <= MAX_MINUTES:
            self.minutes = minutes
        saved = data.get("deadline")
        if isinstance(saved, str) and (deadline := dt_util.parse_datetime(saved)):
            self.deadline = dt_util.as_utc(deadline)
            self._schedule(max(self.deadline, dt_util.utcnow()))

    def _schedule(self, when):
        deadline = self.deadline

        async def expire(_now):
            await self._async_expire(deadline)

        self._cancel = async_track_point_in_utc_time(self.coordinator.hass, expire, when)

    def _cancel_callback(self):
        if self._cancel is not None:
            self._cancel()
            self._cancel = None

    async def _async_save(self):
        await self._store.async_save({
            "minutes": self.minutes,
            "deadline": self.deadline.isoformat() if self.deadline else None,
        })
        self.coordinator.async_update_listeners()

    async def async_set_minutes(self, value):
        if not MIN_MINUTES <= value <= MAX_MINUTES or value != int(value):
            raise HomeAssistantError("Choose a whole number of minutes from 1 to 120")
        async with self._lock:
            self.minutes = int(value)
            await self._async_save()

    async def async_start(self):
        async with self._lock:
            if self._closed:
                return
            self._cancel_callback()
            self.deadline = dt_util.utcnow() + timedelta(minutes=self.minutes)
            self._schedule(self.deadline)
            await self._async_save()

    async def async_cancel(self):
        async with self._lock:
            self._cancel_callback()
            self.deadline = None
            await self._async_save()

    async def async_close(self):
        async with self._lock:
            self._closed = True
            self._cancel_callback()

    async def _async_expire(self, deadline):
        async with self._lock:
            if self._closed or self.deadline != deadline:
                return
            self._cancel = None
            cutoff = deadline + RETRY_WINDOW
            if dt_util.utcnow() <= cutoff:
                try:
                    await self.coordinator.async_set_ambient_light(False)
                except HomeAssistantError as exc:
                    retry_at = dt_util.utcnow() + RETRY_DELAY
                    if retry_at <= cutoff:
                        self._schedule(retry_at)
                        return
                    _LOGGER.warning("Could not switch off the ambient light after its timer: %s", exc)
            else:
                _LOGGER.warning("The ambient light timer elapsed while the diffuser was unavailable")
            self.deadline = None
            await self._async_save()
