"""Read-only xCC status coils."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import XccConfigEntry
from .entity import XccEntity
from .registers import Register


async def async_setup_entry(
    hass: HomeAssistant,
    entry: XccConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(
        XccBinarySensor(entry, register)
        for register in entry.runtime_data.registers
        if register.coil and not register.writable
    )


class XccBinarySensor(XccEntity, BinarySensorEntity):
    """A status or error signal."""

    def __init__(self, entry: XccConfigEntry, register: Register) -> None:
        super().__init__(entry, register)
        if register.problem:
            self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool | None:
        return self.value
