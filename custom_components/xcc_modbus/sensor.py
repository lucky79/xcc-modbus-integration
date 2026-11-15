"""Measurements from xCC holding registers."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import XccConfigEntry
from .entity import XccEntity
from .registers import HOURS, TEMPERATURE, Register


async def async_setup_entry(
    hass: HomeAssistant,
    entry: XccConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(
        XccSensor(entry, register)
        for register in entry.runtime_data.registers
        if not register.coil and not register.writable
    )


class XccSensor(XccEntity, SensorEntity):
    """A sensor backed by a holding register."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, entry: XccConfigEntry, register: Register) -> None:
        super().__init__(entry, register)
        self._attr_native_unit_of_measurement = register.unit
        if register.unit == TEMPERATURE:
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
        elif register.unit == HOURS:
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_state_class = None

    @property
    def native_value(self) -> int | float | None:
        return self.value
