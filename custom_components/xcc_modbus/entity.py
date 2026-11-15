"""Shared identity and availability for xCC entities."""

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import XccConfigEntry, XccCoordinator
from .registers import Register, Section

SECTION_NAMES = {
    Section.HEATING: "Topení",
    Section.BUFFER: "Akumulace",
    Section.DHW: "Teplá užitková voda",
    Section.OUTDOOR: "Venkovní jednotky",
    Section.AUXILIARY: "Kotel na tuhá paliva",
    Section.POOL: "Bazén",
    Section.METER: "Elektroměr",
    Section.PV: "Fotovoltaika",
    Section.LIMITS: "Omezení výkonu",
    Section.SCHEDULES: "Programy cirkulace TUV",
    Section.MBUS: "M-Bus měřiče",
}


@callback
def async_device_info(hass: HomeAssistant, entry: XccConfigEntry) -> dict:
    """Register the controller before its entities attach to child devices."""
    parent_info = dr.DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer="AC Heating",
        model="Convert AW / xCC",
        name="AC Heating xCC",
    )
    devices = {Section.SYSTEM: parent_info}
    child_info = getattr(dr, "ChildDeviceInfo", None)
    if child_info is None:
        return devices

    parent = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, **parent_info
    )
    for section in {register.section for register in entry.runtime_data.registers}:
        if section in SECTION_NAMES:
            devices[section] = child_info(
                identifiers={(DOMAIN, f"{entry.entry_id}_{section}")},
                name=SECTION_NAMES[section],
                parent_device_id=parent.id,
            )
    return devices


class XccEntity(CoordinatorEntity[XccCoordinator]):
    """An entity backed by one xCC Modbus address."""

    _attr_has_entity_name = True

    def __init__(self, entry: XccConfigEntry, register: Register) -> None:
        super().__init__(entry.runtime_data)
        self.register = register
        self._attr_name = register.name
        self._attr_unique_id = f"{entry.entry_id}_{register.key}"
        self._attr_entity_registry_enabled_default = register.enabled_by_default
        devices = entry.runtime_data.devices
        self._attr_device_info = devices.get(register.section, devices[Section.SYSTEM])

    @property
    def available(self) -> bool:
        """An optional register can be unavailable independently of the device."""
        return super().available and self.register.key in self.coordinator.data

    @property
    def value(self) -> bool | int | float | None:
        return self.coordinator.data.get(self.register.key)
