"""Set up xCC from the Home Assistant interface."""

import re
from ipaddress import ip_address

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .const import (
    CONF_DHW_TANKS,
    CONF_EXTERNAL_INPUTS,
    CONF_FEATURES,
    CONF_HEATING_CIRCUITS,
    CONF_MBUS_METERS,
    CONF_OUTDOOR_UNITS,
    CONF_POOLS,
    CONF_SCAN_INTERVAL,
    CONF_WORD_ORDER,
    CONF_ZONES,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FEATURES,
    HIGH_WORD_FIRST,
    LOW_WORD_FIRST,
)
from .modbus import XccClient, XccError
from .registers import SYSTEM

HOSTNAME = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")


def normalize_host(value: str) -> str:
    """Accept an IP address or a DNS hostname without a URL or port."""
    value = value.strip().lower()
    try:
        return str(ip_address(value))
    except ValueError:
        value = value.rstrip(".")
        if len(value) > 253 or not all(
            HOSTNAME.fullmatch(label) for label in value.split(".")
        ):
            raise ValueError("Expected an IP address or hostname") from None
        return value


def connection_settings(defaults: dict) -> vol.Schema:
    """Describe the connection and which groups the controller exposes."""
    host = (
        vol.Required(CONF_HOST, default=defaults[CONF_HOST])
        if CONF_HOST in defaults
        else vol.Required(CONF_HOST)
    )
    fields = {host: str}
    for key, default, minimum, maximum in (
        (CONF_PORT, DEFAULT_PORT, 1, 65535),
        (CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, 5, 300),
        (CONF_HEATING_CIRCUITS, 1, 0, 12),
        (CONF_DHW_TANKS, 1, 0, 2),
        (CONF_ZONES, 0, 0, 16),
        (CONF_EXTERNAL_INPUTS, 0, 0, 16),
        (CONF_OUTDOOR_UNITS, 1, 1, 10),
        (CONF_POOLS, 0, 0, 2),
        (CONF_MBUS_METERS, 0, 0, 4),
    ):
        fields[vol.Required(key, default=defaults.get(key, default))] = vol.All(
            vol.Coerce(int),
            vol.Range(min=minimum, max=maximum),
        )
    fields[vol.Optional(CONF_FEATURES, default=defaults.get(CONF_FEATURES, []))] = (
        SelectSelector(
            SelectSelectorConfig(
                options=list(FEATURES), multiple=True, translation_key=CONF_FEATURES
            )
        )
    )
    fields[
        vol.Optional(
            CONF_WORD_ORDER, default=defaults.get(CONF_WORD_ORDER, HIGH_WORD_FIRST)
        )
    ] = SelectSelector(
        SelectSelectorConfig(
            options=[HIGH_WORD_FIRST, LOW_WORD_FIRST], translation_key=CONF_WORD_ORDER
        )
    )
    return vol.Schema(fields)


class XccConfigFlow(ConfigFlow, domain=DOMAIN):
    """Validate a Modbus connection before creating an entry."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        return await self._async_connection_step("user", user_input)

    async def async_step_reconfigure(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        return await self._async_connection_step("reconfigure", user_input)

    async def _async_connection_step(self, step_id, user_input) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry() if step_id == "reconfigure" else None
        errors = {}
        if user_input is not None:
            try:
                host = normalize_host(user_input[CONF_HOST])
            except ValueError:
                return self.async_show_form(
                    step_id=step_id,
                    data_schema=connection_settings(user_input),
                    errors={CONF_HOST: "invalid_host"},
                )
            user_input = {**user_input, CONF_HOST: host}
            port = user_input[CONF_PORT]
            unique_id = f"[{host}]:{port}"
            existing = await self.async_set_unique_id(unique_id)
            if existing is not None and existing is not entry:
                return self.async_abort(reason="already_configured")

            same_endpoint = entry is not None and (host, port) == (
                entry.data[CONF_HOST],
                entry.data[CONF_PORT],
            )
            if not same_endpoint:
                client = XccClient(host, port)
                try:
                    data = await client.read((SYSTEM[:1],))
                    if "outdoor_temperature" not in data:
                        errors["base"] = "cannot_connect"
                except XccError:
                    errors["base"] = "cannot_connect"
                finally:
                    await client.close()

            if not errors:
                title = f"AC Heating xCC ({host})"
                if entry is not None:
                    return self.async_update_reload_and_abort(
                        entry,
                        data=user_input,
                        unique_id=unique_id,
                        title=title,
                    )
                return self.async_create_entry(title=title, data=user_input)

        defaults = (
            user_input if user_input is not None else (entry.data if entry else {})
        )
        return self.async_show_form(
            step_id=step_id, data_schema=connection_settings(defaults), errors=errors
        )
