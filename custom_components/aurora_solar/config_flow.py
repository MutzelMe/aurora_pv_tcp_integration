"""Config flow for ABB Aurora Solar Inverter integration."""
from __future__ import annotations
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_SLAVE_ID

_LOGGER = logging.getLogger(__name__)

# Schema für die Benutzereingaben (Host, Port, Slave-ID)
DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=5000): int,
        vol.Required(CONF_SLAVE_ID, default=2): int,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Prüft, ob die Verbindung zum Wechselrichter möglich ist."""
    try:
        # Verbindung herstellen
        client = AuroraTCPClient(
            ip=data[CONF_HOST],
            port=data[CONF_PORT],
            address=data[CONF_SLAVE_ID],
            timeout=10
        )
        # Verbindungstest im Executor ausführen (asynchron)
        await hass.async_add_executor_job(client.connect)
        # Beispiel: Seriennummer abfragen, um die Verbindung zu bestätigen
        serial_number = await hass.async_add_executor_job(client.get_serial_number)
        await hass.async_add_executor_job(client.close)
        # Erfolg: Titel mit Seriennummer zurückgeben
        return {"title": f"Wechselrichter {data[CONF_SLAVE_ID]} (SN: {serial_number})"}

    except AuroraError as e:
        _LOGGER.error("Verbindungsfehler zum Wechselrichter: %s", str(e))
        raise config_entries.ConfigFlowError("cannot_connect") from e
    except Exception as e:
        _LOGGER.exception("Unbekannter Fehler bei der Verbindung")
        raise config_entries.ConfigFlowError("unknown") from eclass CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect to the inverter."""

class AuroraSolarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ABB Aurora Solar Inverter."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step (GUI-Formular anzeigen)."""
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
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Optionen für bestehende Einträge (z. B. Slave-ID ändern)."""
        return AuroraSolarOptionsFlow(config_entry)

class AuroraSolarOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for ABB Aurora Solar Inverter."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options (z. B. Slave-ID ändern)."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SLAVE_ID,
                        default=self.config_entry.options.get(CONF_SLAVE_ID, 2),
                    ): int,
                }
            ),
        )
