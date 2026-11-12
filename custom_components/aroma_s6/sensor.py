"""Battery level and charging state reported by the diffuser."""
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE

from .const import BATTERY, CHARGING
from .entity import AromaS6Entity, AromaS6TimerEntity

CHARGE_STATES = {0: "not_charging", 1: "charging", 2: "charged"}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    async_add_entities([
        AromaS6Battery(coordinator, "battery"),
        AromaS6Charging(coordinator, "charging_status"),
        AromaS6LightTimerDeadline(coordinator, "light_timer_deadline"),
    ])


class AromaS6Battery(AromaS6Entity, SensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self):
        return self.coordinator.data[BATTERY]


class AromaS6Charging(AromaS6Entity, SensorEntity):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(CHARGE_STATES.values())
    _attr_icon = "mdi:power-plug-battery-outline"

    @property
    def native_value(self):
        return CHARGE_STATES.get(self.coordinator.data[CHARGING])


class AromaS6LightTimerDeadline(AromaS6TimerEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:timer-sand"

    @property
    def native_value(self):
        return self.coordinator.light_timer.deadline
