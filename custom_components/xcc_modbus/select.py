"""Enumerated xCC settings backed by holding registers."""

from homeassistant.components.select import SelectEntity
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
        XccSelect(entry, register)
        for register in entry.runtime_data.registers
        if register.options
    )


class XccSelect(XccEntity, SelectEntity):
    """A setting whose raw value indexes the firmware's documented options."""

    def __init__(self, entry: XccConfigEntry, register: Register) -> None:
        super().__init__(entry, register)
        self._attr_options = list(register.options)

    @property
    def current_option(self) -> str | None:
        raw = self.value
        if isinstance(raw, int) and 0 <= raw < len(self.options):
            return self.options[raw]
        return None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_write(self.register, self.options.index(option))
