"""Shared Home Assistant device information for the diffuser."""
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class AromaS6Entity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, key):
        super().__init__(coordinator)
        address = coordinator.address
        self._attr_unique_id = f"{address}_{key}"
        if key != "power":
            self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, address)},
            connections={(CONNECTION_BLUETOOTH, address)},
            name="SO Aroma Diffuser S6",
            model="S6",
        )


class AromaS6TimerEntity(AromaS6Entity):
    @property
    def available(self):
        """Keep the local timer controls available if Bluetooth drops."""
        return True
