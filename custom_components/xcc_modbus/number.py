"""Writable xCC temperatures and sanitation intervals."""

import math

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import XccConfigEntry
from .entity import XccEntity
from .registers import DAYS, TEMPERATURE, Register


async def async_setup_entry(
    hass: HomeAssistant,
    entry: XccConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(
        XccNumber(entry, register)
        for register in entry.runtime_data.registers
        if register.writable and register.limits is not None
    )


class XccNumber(XccEntity, NumberEntity):
    """A setting in native units, converted to a Modbus word on write."""

    _attr_mode = NumberMode.BOX

    def __init__(self, entry: XccConfigEntry, register: Register) -> None:
        super().__init__(entry, register)
        self._attr_native_unit_of_measurement = register.unit
        self._attr_native_min_value, self._attr_native_max_value = register.limits
        self._attr_native_step = 1 / register.scale
        if register.unit == TEMPERATURE:
            self._attr_device_class = NumberDeviceClass.TEMPERATURE
        elif register.unit == DAYS:
            self._attr_device_class = NumberDeviceClass.DURATION

    @property
    def native_value(self) -> int | float | None:
        return self.value

    async def async_set_native_value(self, value: float) -> None:
        if (
            not math.isfinite(value)
            or not self.native_min_value <= value <= self.native_max_value
        ):
            raise HomeAssistantError(
                f"Hodnota pro {self.register.name} je mimo povolený rozsah"
            )
        if self.register.scale == 1 and not float(value).is_integer():
            raise HomeAssistantError("Zadejte celé číslo")
        if self.register.hhmm and int(value) % 100 >= 60:
            raise HomeAssistantError("Čas zadejte ve formátu HHMM s minutami 00 až 59")
        await self.coordinator.async_write(self.register, value)
