"""Buttons for starting and cancelling the ambient light countdown."""

from homeassistant.components.button import ButtonEntity

from .entity import AromaS6TimerEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    async_add_entities([
        AromaS6StartLightTimer(coordinator, "light_timer_start"),
        AromaS6CancelLightTimer(coordinator, "light_timer_cancel"),
    ])


class AromaS6StartLightTimer(AromaS6TimerEntity, ButtonEntity):
    _attr_icon = "mdi:timer-play-outline"

    async def async_press(self):
        await self.coordinator.light_timer.async_start()


class AromaS6CancelLightTimer(AromaS6TimerEntity, ButtonEntity):
    _attr_icon = "mdi:timer-off-outline"

    async def async_press(self):
        await self.coordinator.light_timer.async_cancel()
