"""Config flow for ABB Aurora Solar Inverter integration."""
from __future__ import annotations
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_SLAVE_ID, CONF_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=5000): int,
        vol.Required(CONF_SLAVE_ID, default=2): int,
        vol.Required("name", default="Inverter"): str,
        vol.Required(CONF_SCAN_INTERVAL, default=60): int,
    }
)

# Translation strings for config flow
CONFIG_FLOW_DESCRIPTION = "Please enter the connection details for your ABB Aurora inverter. Use a short name (e.g., 'Inverter 1') for better entity names."

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect to the inverter."""

class InvalidHost(HomeAssistantError):
    """Error for invalid host address."""

class InvalidPort(HomeAssistantError):
    """Error for invalid port."""

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate connection to the inverter."""
    from aurorapy.client import AuroraTCPClient, AuroraError
    try:
        # Test actual connection to the inverter
        client = AuroraTCPClient(
            ip=data[CONF_HOST],
            port=data[CONF_PORT],
            address=data[CONF_SLAVE_ID],
            timeout=120
        )
        client.connect()
        client.close()
        # Use the provided name for the title
        name = data.get("name", f"Inverter {data[CONF_SLAVE_ID]}")
        return {"title": name}
    except AuroraError as e:
        _LOGGER.exception("Connection error: %s", e)
        raise CannotConnect from e
    except Exception as e:
        _LOGGER.exception("Unexpected connection error: %s", e)
        raise CannotConnect from e

class AuroraSolarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ABB Aurora Solar Inverter."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step (show GUI form)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                await self.async_set_unique_id(f"{user_input[CONF_HOST]}_{user_input[CONF_SLAVE_ID]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
            description_placeholders={"suggestion": "e.g., Inverter 1"},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get options flow for existing entries (e.g. change Slave ID)."""
        return AuroraSolarOptionsFlow(config_entry)

class AuroraSolarOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for ABB Aurora Solar Inverter."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__()  # OptionsFlow does not take config_entry parameter
        # Manually store config_entry since OptionsFlow doesn't set it automatically
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options (e.g. change Slave ID)."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            # Validate the input
            try:
                # Return the updated options
                return self.async_create_entry(title=self.config_entry.title, data=user_input)
            except Exception as e:
                _LOGGER.error("Error updating options: %s", e)
                errors["base"] = "unknown"

        # Get current values from options or data
        current_slave_id = (
            self.config_entry.options.get(CONF_SLAVE_ID)
            or self.config_entry.data.get(CONF_SLAVE_ID, 2)
        )
        current_scan_interval = (
            self.config_entry.options.get(CONF_SCAN_INTERVAL)
            or self.config_entry.data.get(CONF_SCAN_INTERVAL, 60)
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SLAVE_ID,
                        default=current_slave_id,
                    ): int,
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=current_scan_interval,
                    ): int,
                }
            ),
            errors=errors,
        )
