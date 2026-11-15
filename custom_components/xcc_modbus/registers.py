"""xCC Modbus register map, protocol 2.5 for xCC 5.9/8.5."""

from dataclasses import dataclass, replace
from enum import StrEnum

from .const import (
    CONF_DHW_TANKS,
    CONF_EXTERNAL_INPUTS,
    CONF_FEATURES,
    CONF_HEATING_CIRCUITS,
    CONF_MBUS_METERS,
    CONF_OUTDOOR_UNITS,
    CONF_POOLS,
    CONF_ZONES,
    DHW_SCHEDULES,
    METER,
    PHOTOVOLTAICS,
    POWER_LIMITS,
)

TEMPERATURE = "°C"
PERCENTAGE = "%"
DAYS = "d"
HOURS = "h"
WATTS = "W"
KILOWATT_HOURS = "kWh"
FLOW = "m³/h"
RPM = "rpm"
WEEKDAYS = ("Po", "Út", "St", "Čt", "Pá", "So", "Ne")
ROOM_MODES = ("Bez čidla", "Termostatický", "Adaptivní")


class Section(StrEnum):
    """Logical sections of the xCC controller."""

    SYSTEM = "system"
    HEATING = "heating"
    BUFFER = "buffer"
    DHW = "dhw"
    OUTDOOR = "outdoor"
    AUXILIARY = "auxiliary"
    POOL = "pool"
    METER = "meter"
    PV = "photovoltaics"
    LIMITS = "power_limits"
    SCHEDULES = "schedules"
    MBUS = "mbus"


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
    words: int = 1
    signed: bool = False
    hhmm: bool = False
    options: tuple[str, ...] = ()
    diagnostic: bool = False

    def decode(
        self, raw: int, second: int = 0, *, low_word_first: bool = False
    ) -> bool | int | float:
        """Convert a Modbus value into the entity's native unit."""
        if self.coil:
            return bool(raw)
        if self.words == 2:
            high, low = (second, raw) if low_word_first else (raw, second)
            raw = (high << 16) | low
        elif (self.unit == TEMPERATURE or self.signed) and raw >= 0x8000:
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
    temperature("unfiltered_outdoor_temperature", "Nefiltrovaná venkovní teplota", 126),
    Register(
        "heat_pump_output", "Aktuální výkon venkovní jednotky 1", 207, unit=PERCENTAGE
    ),
    coil("main_switch", "Hlavní vypínač", 0, writable=True, enabled=False),
    coil("error", "Porucha", 33, problem=True),
    coil("noncritical_error", "Nekritická porucha", 34, problem=True),
    coil("critical_error", "Kritická porucha", 35, problem=True),
    coil("low_tariff", "Nízký tarif HDO", 72),
    coil("auxiliary_heat", "Bivalentní zdroj aktivní", 74),
    coil("auxiliary_heat_blocked", "Bivalentní zdroj blokován", 75),
    coil("ignore_low_tariff", "Ignorovat HDO", 73, writable=True, enabled=False),
    Register("auxiliary_heat_hours", "Bivalenční zdroj – motohodiny", 225, unit=HOURS),
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
        Register(
            key + "room_mode",
            name + "režim prostoru",
            372 + index,
            writable=True,
            options=ROOM_MODES,
            enabled_by_default=False,
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
            key + "heater_hours",
            name + "motohodiny externího ohřevu",
            219 + index,
            unit=HOURS,
        ),
        Register(
            key + "since_sanitation_start",
            name + "čas od spuštění sanitace",
            223 + index,
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
            key + "force_auxiliary_heat",
            name + "vynucení externího ohřevu",
            122 + index,
            writable=True,
            enabled=False,
        ),
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
    coil(
        "dhw_circulation_cycle",
        "TUV 1 – cyklovač cirkulace",
        77,
        writable=True,
        enabled=False,
    ),
    coil(
        "dhw_circulation_ignore_holiday",
        "TUV 1 – cirkulace během prázdnin",
        78,
        writable=True,
        enabled=False,
    ),
    coil(
        "dhw_circulation_during_sanitation",
        "TUV 1 – cirkulace při sanitaci",
        81,
        writable=True,
        enabled=False,
    ),
    coil(
        "dhw_boost",
        "TUV 1 – zvýšení teploty pro spuštění ohřevu",
        87,
        writable=True,
        enabled=False,
    ),
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


OUTDOOR_METRICS = (
    ("condensate_temperature", "teplota kondenzátu", 127, TEMPERATURE, 100),
    ("discharge_temperature", "teplota výtlaku", 137, TEMPERATURE, 100),
    ("evaporator_temperature", "teplota výparníku", 147, TEMPERATURE, 100),
    (
        "upper_evaporator_temperature",
        "teplota horního výparníku",
        157,
        TEMPERATURE,
        100,
    ),
    ("suction_temperature", "teplota sání", 167, TEMPERATURE, 100),
    ("upper_fan_speed", "otáčky horního ventilátoru", 177, RPM, 1),
    ("lower_fan_speed", "otáčky spodního ventilátoru", 187, RPM, 1),
    ("compressor_hours", "motohodiny kompresoru", 197, HOURS, 1),
    ("output", "výkon", 207, PERCENTAGE, 1),
    ("flow", "průtok výměníkem", 360, FLOW, 100),
)


def outdoor_registers(count):
    for index in range(count):
        for key, label, address, unit, scale in OUTDOOR_METRICS:
            if index == 0 and address == 207:
                continue  # Already exposed as heat_pump_output on the main device.
            yield Register(
                f"outdoor_{index + 1}_{key}",
                f"Venkovní jednotka {index + 1} – {label}",
                address + index,
                unit=unit,
                scale=scale,
            )


POOL_ONE = (
    temperature("pool_1_target", "Bazén 1 – požadovaná teplota", 112, (5, 45)),
    temperature("pool_1_temperature", "Bazén 1 – skutečná teplota", 113),
    coil("pool_1_enabled", "Bazén 1 – povolení", 29, writable=True),
    coil("pool_1_filtration", "Bazén 1 – povolení filtrace", 68, writable=True),
    coil("pool_1_heat_anytime", "Bazén 1 – topit kdykoliv", 70, writable=True),
    coil(
        "pool_1_filter_high_tariff",
        "Bazén 1 – filtrace ve vysoké sazbě HDO",
        71,
        writable=True,
    ),
)
POOL_TWO = coil("pool_2_enabled", "Bazén 2 – povolení", 30, writable=True)
AUXILIARY = (
    temperature("solid_fuel_temperature", "Kotel na tuhá paliva – teplota", 94),
    coil("solid_fuel_active", "Kotel na tuhá paliva – aktivní", 31),
)

METER_POWER = tuple(
    Register(
        f"meter_power_l{phase}", f"Příkon L{phase}", 356 + phase, unit=WATTS, scale=10
    )
    for phase in range(1, 4)
)
METER_ENERGY = tuple(
    Register(
        f"meter_energy_{key}",
        name,
        349 + index * 2,
        unit=KILOWATT_HOURS,
        scale=10,
        words=2,
    )
    for index, (key, name) in enumerate(
        (
            ("l1", "Spotřeba L1"),
            ("l2", "Spotřeba L2"),
            ("l3", "Spotřeba L3"),
            ("total", "Celková spotřeba"),
        )
    )
)
PV_REGISTERS = tuple(
    Register(
        f"pv_{key}_l{phase}",
        f"{name} L{phase}",
        base + phase - 1,
        unit=WATTS,
        signed=True,
    )
    for base, key, name in (
        (286, "export", "Přetok FVE"),
        (289, "cascade", "Přetok FVE – Cascade"),
        (292, "ssr", "Přetok FVE – SSR"),
    )
    for phase in range(1, 4)
)


def mbus_registers(count):
    for index in range(count):
        base = 384 + 17 * index
        name = f"M-Bus měřič {index + 1}"
        for field in range(1, 9):
            yield Register(
                f"mbus_{index + 1}_data_{field}",
                f"{name} – data {field}",
                base + 2 * (field - 1),
                scale=10 if 4 <= field <= 6 else 1,
                words=2,
                diagnostic=True,
            )
        yield Register(
            f"mbus_{index + 1}_status", f"{name} – stav", base + 16, diagnostic=True
        )


def schedule_registers(key, name, base):
    for day, weekday in enumerate(WEEKDAYS):
        for slot, label in enumerate(("Zap 1", "Vyp 1", "Zap 2", "Vyp 2")):
            address = base + day * 4 + slot
            yield Register(
                f"{key}_{address}",
                f"{name} – {weekday} {label} (HHMM)",
                address,
                limits=(0, 2400),
                writable=True,
                hhmm=True,
            )


def dhw_schedule_registers():
    yield from schedule_registers("dhw_schedule_1", "Cirkulace TUV 1 – program 1", 226)
    yield from schedule_registers("dhw_schedule_2", "Cirkulace TUV 1 – program 2", 254)
    yield Register(
        "dhw_cycle_on_time",
        "Cirkulace TUV 1 – délka zapnutí (HHMM)",
        282,
        limits=(0, 65535),
        writable=True,
        hhmm=True,
    )
    yield Register(
        "dhw_cycle_off_time",
        "Cirkulace TUV 1 – délka vypnutí (HHMM)",
        283,
        limits=(0, 65535),
        writable=True,
        hhmm=True,
    )


LIMIT_LABELS = (
    "Globální",
    "Časové",
    "Teplotní",
    "Externí",
    "Topný okruh 1",
    "Bazén 1",
    "Bazénová místnost",
    "TUV 1",
    "Topný okruh 2",
    "Topný okruh 12",
    "TUV 2",
    "Bazén 2",
    *(f"Topný okruh {i}" for i in range(3, 12)),
)


def limit_registers():
    for index, label in enumerate(LIMIT_LABELS):
        address = 298 + index
        yield Register(
            f"power_limit_{address}",
            f"{label} – maximální výkon",
            address,
            unit=PERCENTAGE,
            limits=(0, 100),
            writable=True,
        )
    # The table labels these as percentages but describes a temperature and hysteresis.
    yield Register(
        "power_limit_threshold",
        "Teplotní omezení – práh (hodnota registru)",
        319,
        limits=(-32768, 32767),
        writable=True,
        signed=True,
        enabled_by_default=False,
    )
    yield Register(
        "power_limit_hysteresis",
        "Teplotní omezení – hystereze (hodnota registru)",
        320,
        limits=(0, 65535),
        writable=True,
        enabled_by_default=False,
    )
    labels = (*LIMIT_LABELS[:4], "Omezení pro bloky", *LIMIT_LABELS[4:])
    for index, label in enumerate(labels):
        address = 88 + index
        yield coil(
            f"power_limit_enable_{address}",
            f"{label} – povolení omezení výkonu",
            address,
            writable=True,
        )
    yield from schedule_registers("power_limit_schedule", "Program omezení výkonu", 321)


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
        hot_water.append(
            temperature("dhw_return_temperature", "Teplota zpátečky okruhu TUV", 285)
        )

    pools = config.get(CONF_POOLS, 0)
    features = config.get(CONF_FEATURES, ())
    sections = {
        Section.HEATING: heating,
        Section.BUFFER: BUFFER,
        Section.DHW: hot_water,
        Section.AUXILIARY: AUXILIARY,
        Section.OUTDOOR: outdoor_registers(config.get(CONF_OUTDOOR_UNITS, 1)),
        Section.MBUS: mbus_registers(config.get(CONF_MBUS_METERS, 0)),
    }
    if pools:
        sections[Section.POOL] = POOL_ONE if pools == 1 else (*POOL_ONE, POOL_TWO)
    if METER in features:
        sections[Section.METER] = (*METER_POWER, *METER_ENERGY)
    if PHOTOVOLTAICS in features:
        sections[Section.PV] = PV_REGISTERS
    if POWER_LIMITS in features:
        sections[Section.LIMITS] = limit_registers()
    if DHW_SCHEDULES in features and hot_water:
        sections[Section.SCHEDULES] = dhw_schedule_registers()
    return (
        *SYSTEM,
        *(
            replace(register, section=section)
            for section, registers in sections.items()
            for register in registers
        ),
    )
