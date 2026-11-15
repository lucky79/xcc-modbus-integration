"""Poll the xCC once per interval for all Home Assistant entities."""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_SCAN_INTERVAL, DOMAIN
from .modbus import XccClient, XccError, contiguous_blocks
from .registers import Register, registers_for

_LOGGER = logging.getLogger(__name__)
type XccConfigEntry = ConfigEntry[XccCoordinator]


class XccCoordinator(DataUpdateCoordinator[dict[str, bool | int | float]]):
    """Maintain the last confirmed device state."""

    devices: dict

    def __init__(self, hass: HomeAssistant, entry: XccConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=entry.data[CONF_SCAN_INTERVAL]),
            always_update=False,
        )
        self.registers = registers_for(entry.data)
        self._blocks = tuple(contiguous_blocks(self.registers))
        self.client = XccClient(entry.data[CONF_HOST], entry.data[CONF_PORT])

    async def _async_update_data(self) -> dict[str, bool | int | float]:
        try:
            data = await self.client.read(self._blocks)
        except XccError as err:
            raise UpdateFailed(f"Chyba komunikace s xCC: {err}") from err
        if "outdoor_temperature" not in data:
            await self.client.close()
            raise UpdateFailed("xCC neposkytuje registr venkovní teploty na adrese 0")
        return data

    async def async_write(self, register: Register, value: bool | float) -> None:
        """Apply a change and ask the controller for current values."""
        if not self.last_update_success or register.key not in self.data:
            raise HomeAssistantError(f"Hodnota {register.name} je nedostupná")
        try:
            await self.client.write(register, value)
        except XccError as err:
            raise HomeAssistantError(f"Zápis do xCC selhal: {err}") from err
        await self.async_request_refresh()
