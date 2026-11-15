"""Shared identity and availability for xCC entities."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import XccConfigEntry, XccCoordinator
from .registers import Register


class XccEntity(CoordinatorEntity[XccCoordinator]):
    """An entity backed by one xCC Modbus address."""

    _attr_has_entity_name = True

    def __init__(self, entry: XccConfigEntry, register: Register) -> None:
        super().__init__(entry.runtime_data)
        self.register = register
        self._attr_name = register.name
        self._attr_unique_id = f"{entry.entry_id}_{register.key}"
        self._attr_entity_registry_enabled_default = register.enabled_by_default
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="AC Heating",
            model="Convert AW / xCC",
            name="AC Heating xCC",
        )

    @property
    def available(self) -> bool:
        """An optional register can be unavailable independently of the device."""
        return super().available and self.register.key in self.coordinator.data

    @property
    def value(self) -> bool | int | float | None:
        return self.coordinator.data.get(self.register.key)
