"""Spray settings for the SO Aroma Diffuser S6."""
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import UnitOfTime
from homeassistant.exceptions import HomeAssistantError

from .const import IDLE_INTERVAL, SPRAY_DURATION
from .entity import AromaS6Entity, AromaS6TimerEntity
from .light_timer import MAX_MINUTES, MIN_MINUTES


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    async_add_entities([
        AromaS6Number(coordinator, "spray_duration", SPRAY_DURATION, 3),
        AromaS6Number(coordinator, "spray_interval", IDLE_INTERVAL, 0),
        AromaS6LightTimerMinutes(coordinator, "light_timer_minutes"),
    ])


class AromaS6Number(AromaS6Entity, NumberEntity):
    _attr_mode = NumberMode.SLIDER
    _attr_native_max_value = 30
    _attr_native_step = 1
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator, key, prop, minimum):
        super().__init__(coordinator, key)
        self._property = prop
        self._attr_native_min_value = minimum

    @property
    def native_value(self):
        return self.coordinator.data[self._property]

    async def async_set_native_value(self, value):
        if not self.native_min_value <= value <= self.native_max_value or value != int(value):
            raise HomeAssistantError("The diffuser requires a whole number within the slider range")
        await self.coordinator.async_set_property(self._property, int(value))


class AromaS6LightTimerMinutes(AromaS6TimerEntity, NumberEntity):
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = MIN_MINUTES
    _attr_native_max_value = MAX_MINUTES
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_icon = "mdi:timer-outline"

    @property
    def native_value(self):
        return self.coordinator.light_timer.minutes

    async def async_set_native_value(self, value):
        await self.coordinator.light_timer.async_set_minutes(value)
