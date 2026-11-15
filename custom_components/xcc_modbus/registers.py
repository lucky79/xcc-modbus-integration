"""xCC Modbus register map, protocol 2.5 for xCC 5.9/8.5."""

from dataclasses import dataclass, replace
from enum import StrEnum

from .const import (
    CONF_DHW_TANKS,
    CONF_EXTERNAL_INPUTS,
    CONF_HEATING_CIRCUITS,
    CONF_ZONES,
)

TEMPERATURE = "°C"
PERCENTAGE = "%"
DAYS = "d"
HOURS = "h"


class Section(StrEnum):
    """Logical sections of the xCC controller."""

    SYSTEM = "system"
    HEATING = "heating"
    BUFFER = "buffer"
    DHW = "dhw"


@dataclass(frozen=True, slots=True)
class Register:
    key: str
    name: str
    address: int
    coil: bool = False
    unit: str | None = None
    scale: int = 1
    limits: tuple[int, int] | None = None
    writable: bool = False
    problem: bool = False
    enabled_by_default: bool = True
    section: Section = Section.SYSTEM

    def decode(self, raw: int) -> bool | int | float:
        """Convert a Modbus value into the entity's native unit."""
        if self.coil:
            return bool(raw)
        if self.unit == TEMPERATURE and raw >= 0x8000:
            raw -= 0x10000
        return raw if self.scale == 1 else raw / self.scale

    def encode(self, value: float) -> int:
        """Convert a value to an unsigned Modbus word."""
        return round(value * self.scale) & 0xFFFF


def temperature(key, name, address, limits=None):
    return Register(
        key,
        name,
        address,
        unit=TEMPERATURE,
        scale=100,
        limits=limits,
        writable=limits is not None,
    )


def coil(key, name, address, *, writable=False, problem=False, enabled=True):
    return Register(
        key,
        name,
        address,
        coil=True,
        writable=writable,
        problem=problem,
        enabled_by_default=enabled,
    )


SYSTEM = (
    temperature("outdoor_temperature", "Venkovní teplota", 0),
    temperature("flow_temperature", "Výstupní teplota topné vody", 1),
    temperature("target_flow_temperature", "Požadovaná teplota topné vody", 2),
    Register("system_output", "Aktuální výkon systému", 3, unit=PERCENTAGE),
    temperature("return_temperature", "Teplota vratné vody", 284),
    Register(
        "heat_pump_output", "Aktuální výkon venkovní jednotky 1", 207, unit=PERCENTAGE
    ),
    coil("main_switch", "Hlavní vypínač", 0, writable=True, enabled=False),
    coil("error", "Porucha", 33, problem=True),
    coil("noncritical_error", "Nekritická porucha", 34, problem=True),
    coil("critical_error", "Kritická porucha", 35, problem=True),
    coil("low_tariff", "Nízký tarif HDO", 72),
    coil("auxiliary_heat", "Bivalentní zdroj aktivní", 74),
)


BUFFER = (
    temperature("buffer_temperature", "Teplota nádrže", 95),
    coil("buffer_active", "Akumulace aktivní", 32),
)


def heating_circuit(index):
    key = f"heating_{index + 1}_"
    name = f"Topný okruh {index + 1} – "
    return (
        temperature(key + "room_temperature", name + "teplota místnosti", 4 + index),
        temperature(
            key + "room_target",
            name + "požadovaná teplota místnosti",
            16 + index,
            (5, 35),
        ),
        temperature(key + "water_temperature", name + "teplota topné vody", 28 + index),
        temperature(
            key + "water_target",
            name + "konstantní teplota vody",
            114 + index,
            (10, 65),
        ),
        coil(key + "enabled", name + "povolení", 1 + index, writable=True),
        coil(key + "active", name + "aktivní", 13 + index),
        coil(
            key + "constant_mode",
            name + "režim konstantní teploty",
            110 + index,
            writable=True,
        ),
    )


def dhw_tank(index):
    key = f"dhw_{index + 1}_"
    name = f"TUV {index + 1} – "
    return (
        temperature(key + "temperature", name + "teplota zásobníku", 92 + index),
        temperature(
            key + "max_temperature", name + "maximální teplota", 88 + index, (10, 65)
        ),
        temperature(
            key + "min_temperature", name + "minimální teplota", 90 + index, (10, 65)
        ),
        temperature(
            key + "sanitation_temperature",
            name + "sanitační teplota",
            217 + index,
            (50, 75),
        ),
        Register(
            key + "since_sanitation",
            name + "čas od poslední sanitace",
            221 + index,
            unit=HOURS,
            scale=10,
        ),
        Register(
            key + "sanitation_interval",
            name + "interval sanitace",
            370 + index,
            unit=DAYS,
            limits=(1, 365),
            writable=True,
        ),
        coil(key + "enabled", name + "povolení ohřevu", 25 + index, writable=True),
        coil(key + "active", name + "ohřev aktivní", 27 + index),
        coil(key + "auxiliary_heat", name + "externí ohřev aktivní", 83 + index),
        coil(key + "sanitation_active", name + "sanitace aktivní", 85 + index),
        coil(
            key + "sanitation_enabled",
            name + "povolení sanitace",
            124 + index,
            writable=True,
        ),
    )


DHW_CIRCULATION = (
    coil("dhw_circulation_enabled", "TUV 1 – povolení cirkulace", 76, writable=True),
    coil("dhw_circulation_manual", "TUV 1 – ruční režim cirkulace", 79, writable=True),
    coil(
        "dhw_circulation_manual_state",
        "TUV 1 – ruční spuštění oběhového čerpadla",
        80,
        writable=True,
    ),
    coil("dhw_circulation_active", "TUV 1 – cirkulace aktivní", 82),
)


def zone(index):
    key = f"zone_{index + 1}_"
    name = f"Zóna {index + 1} – "
    return (
        temperature(key + "temperature", name + "teplota vzduchu", 56 + index),
        temperature(key + "target", name + "požadovaná teplota", 40 + index, (5, 35)),
        # The table lists °C for valve opening. Use the documented scale without a unit.
        Register(
            key + "valve", name + "požadované otevření ventilu", 72 + index, scale=100
        ),
        coil(key + "enabled", name + "povolení vytápění", 36 + index, writable=True),
        coil(key + "active", name + "vytápění aktivní", 52 + index),
    )


def registers_for(config) -> tuple[Register, ...]:
    """Build entities for the circuits and inputs configured on this controller."""
    heating = []
    for index in range(config[CONF_HEATING_CIRCUITS]):
        heating.extend(heating_circuit(index))
    for index in range(config[CONF_ZONES]):
        heating.extend(zone(index))
    for index in range(config[CONF_EXTERNAL_INPUTS]):
        heating.append(
            temperature(
                f"external_temperature_{index + 1}",
                f"Externí teplotní vstup {index + 1}",
                96 + index,
                (-40, 80),
            )
        )

    hot_water = []
    for index in range(config[CONF_DHW_TANKS]):
        hot_water.extend(dhw_tank(index))
    if hot_water:
        hot_water.extend(DHW_CIRCULATION)

    return (
        *SYSTEM,
        *(replace(register, section=Section.HEATING) for register in heating),
        *(replace(register, section=Section.BUFFER) for register in BUFFER),
        *(replace(register, section=Section.DHW) for register in hot_water),
    )
