"""Native Home Assistant color controls for the S6 ambient light."""

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_RGB_COLOR, ColorMode, LightEntity

from .const import LIGHT_COLOR, LIGHT_LEVEL, LIGHT_ON
from .entity import AromaS6Entity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([AromaS6Light(entry.runtime_data, "ambient_light")])


class AromaS6Light(AromaS6Entity, LightEntity):
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB
    _attr_icon = "mdi:palette"

    @property
    def is_on(self):
        return bool(self.coordinator.data[LIGHT_LEVEL] & LIGHT_ON)

    @property
    def _channels(self):
        color = self.coordinator.data[LIGHT_COLOR]
        return ((color >> 16) & 255, (color >> 8) & 255, color & 255)

    @property
    def brightness(self):
        return max(self._channels)

    @property
    def rgb_color(self):
        channels = self._channels
        peak = max(channels)
        return tuple(round(channel * 255 / peak) for channel in channels) if peak else channels

    async def async_turn_on(self, **kwargs):
        if ATTR_RGB_COLOR not in kwargs and ATTR_BRIGHTNESS not in kwargs:
            await self.coordinator.async_set_ambient_light(True)
            return
        channels = kwargs.get(ATTR_RGB_COLOR, self._channels)
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        if brightness is not None:
            peak = max(channels)
            channels = (
                tuple(round(channel * brightness / peak) for channel in channels)
                if peak
                else (brightness, brightness, brightness)
            )
        red, green, blue = channels
        color = (red << 16) | (green << 8) | blue
        if color:
            await self.coordinator.async_set_ambient_light(True, color)
        else:
            await self.coordinator.async_set_ambient_light(False)

    async def async_turn_off(self, **kwargs):
        await self.coordinator.async_set_ambient_light(False)
