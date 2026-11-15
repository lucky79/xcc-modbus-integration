"""Measurements from xCC holding registers."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_FEATURES, METER
from .coordinator import XccConfigEntry
from .entity import XccEntity
from .registers import (
    FLOW,
    HOURS,
    KILOWATT_HOURS,
    METER_POWER,
    TEMPERATURE,
    WATTS,
    Register,
    Section,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: XccConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    entities = [
        XccSensor(entry, register)
        for register in entry.runtime_data.registers
        if not register.coil and not register.writable
    ]
    if METER in entry.data.get(CONF_FEATURES, ()):
        entities.append(XccTotalPowerSensor(entry))
    async_add_entities(entities)


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
        elif register.unit == WATTS:
            self._attr_device_class = SensorDeviceClass.POWER
        elif register.unit == KILOWATT_HOURS:
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        elif register.unit == FLOW:
            self._attr_device_class = SensorDeviceClass.VOLUME_FLOW_RATE
        if register.diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_state_class = None

    @property
    def native_value(self) -> int | float | None:
        return self.value


TOTAL_POWER = Register(
    "meter_power_total",
    "Celkový aktuální příkon",
    -1,
    unit=UnitOfPower.KILO_WATT,
    section=Section.METER,
)


class XccTotalPowerSensor(XccSensor):
    """Sum the three phase measurements, only when all are available."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_suggested_display_precision = 4

    def __init__(self, entry: XccConfigEntry) -> None:
        super().__init__(entry, TOTAL_POWER)

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.native_value is not None

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if data is None or any(phase.key not in data for phase in METER_POWER):
            return None
        return round(sum(data[phase.key] for phase in METER_POWER) / 1000, 4)
