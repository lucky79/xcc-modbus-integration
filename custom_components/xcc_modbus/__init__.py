"""AC Heating xCC Modbus TCP integration."""

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import XccConfigEntry, XccCoordinator

PLATFORMS = (Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SWITCH, Platform.NUMBER)


async def async_setup_entry(hass: HomeAssistant, entry: XccConfigEntry) -> bool:
    """Connect to the controller and load the entity platforms."""
    coordinator = XccCoordinator(hass, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except BaseException:
        await coordinator.client.close()
        raise
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: XccConfigEntry) -> bool:
    """Unload platforms and release the controller's connection."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    await entry.runtime_data.async_shutdown()
    await entry.runtime_data.client.close()
    return True
