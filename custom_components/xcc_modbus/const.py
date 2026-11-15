"""Configuration of the xCC integration."""

DOMAIN = "xcc_modbus"
DEFAULT_PORT = 502
DEFAULT_SCAN_INTERVAL = 15
DEVICE_ID = 1
TIMEOUT = 3

CONF_SCAN_INTERVAL = "scan_interval"
CONF_HEATING_CIRCUITS = "heating_circuits"
CONF_DHW_TANKS = "dhw_tanks"
CONF_ZONES = "zones"
CONF_EXTERNAL_INPUTS = "external_inputs"
CONF_OUTDOOR_UNITS = "outdoor_units"
CONF_POOLS = "pools"
CONF_MBUS_METERS = "mbus_meters"
CONF_FEATURES = "features"
CONF_WORD_ORDER = "word_order"
METER = "electric_meter"
PHOTOVOLTAICS = "photovoltaics"
POWER_LIMITS = "power_limits"
DHW_SCHEDULES = "dhw_schedules"
FEATURES = (METER, PHOTOVOLTAICS, POWER_LIMITS, DHW_SCHEDULES)
HIGH_WORD_FIRST = "high_word_first"
LOW_WORD_FIRST = "low_word_first"
