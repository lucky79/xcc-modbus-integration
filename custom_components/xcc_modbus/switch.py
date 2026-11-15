"""Writable xCC coils."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import XccConfigEntry
from .entity import XccEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: XccConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(
        XccSwitch(entry, register)
        for register in entry.runtime_data.registers
        if register.coil and register.writable
    )


class XccSwitch(XccEntity, SwitchEntity):
    """A writable coil whose state comes from the controller."""

    @property
    def is_on(self) -> bool | None:
        return self.value

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_write(self.register, True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_write(self.register, False)
