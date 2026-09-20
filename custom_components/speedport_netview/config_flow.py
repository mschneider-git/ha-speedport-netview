"""Configuration flow for Speedport Netview."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

from .api import SpeedportClient, SpeedportConnectionError, SpeedportError
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_HOST,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)


def _interval_selector() -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(
            min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL, mode=NumberSelectorMode.BOX
        )
    )


class SpeedportConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Ask for the router address and verify the status page."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()
            client = SpeedportClient(async_get_clientsession(self.hass), host)
            try:
                await client.async_get_devices()
            except SpeedportConnectionError:
                errors["base"] = "cannot_connect"
            except SpeedportError:
                errors["base"] = "invalid_response"
            else:
                return self.async_create_entry(
                    title=f"Speedport {host}", data={CONF_HOST: host}
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST,
                        default=(user_input or {}).get(CONF_HOST, DEFAULT_HOST),
                    ): TextSelector()
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return SpeedportOptionsFlow()


class SpeedportOptionsFlow(config_entries.OptionsFlow):
    """Let the polling interval be changed."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the options step."""
        if user_input is not None:
            return self.async_create_entry(
                data={CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])}
            )
        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=current
                    ): _interval_selector()
                }
            ),
        )
