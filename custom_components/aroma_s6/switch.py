"""Power switch for the SO Aroma Diffuser S6."""
from homeassistant.components.switch import SwitchEntity

from .const import POWER
from .entity import AromaS6Entity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([AromaS6Switch(entry.runtime_data, "power")])


class AromaS6Switch(AromaS6Entity, SwitchEntity):
    _attr_name = None
    _attr_icon = "mdi:scent"

    @property
    def is_on(self):
        return bool(self.coordinator.data[POWER])

    async def async_turn_on(self, **kwargs):
        await self.coordinator.async_set_property(POWER, 1)

    async def async_turn_off(self, **kwargs):
        await self.coordinator.async_set_property(POWER, 0)
