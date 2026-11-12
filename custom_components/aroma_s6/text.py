"""RGB color setting for the diffuser's ambient light."""
import re

from homeassistant.components.text import TextEntity
from homeassistant.exceptions import HomeAssistantError

from .const import LIGHT_COLOR
from .entity import AromaS6Entity

COLOR_PATTERN = r"#[0-9A-Fa-f]{6}"


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([AromaS6Color(entry.runtime_data, "light_color")])


class AromaS6Color(AromaS6Entity, TextEntity):
    _attr_native_min = 7
    _attr_native_max = 7
    _attr_pattern = COLOR_PATTERN
    _attr_icon = "mdi:palette"

    @property
    def native_value(self):
        return f"#{self.coordinator.data[LIGHT_COLOR]:06X}"

    async def async_set_value(self, value):
        if not re.fullmatch(COLOR_PATTERN, value):
            raise HomeAssistantError("Enter a color in the form #RRGGBB")
        await self.coordinator.async_set_property(LIGHT_COLOR, int(value[1:], 16))
