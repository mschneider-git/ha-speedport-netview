"""The Speedport Netview integration."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant

from .coordinator import SpeedportConfigEntry, SpeedportCoordinator

PLATFORMS = [Platform.DEVICE_TRACKER]


async def async_setup_entry(hass: HomeAssistant, entry: SpeedportConfigEntry) -> bool:
    """Set up one router from a config entry."""
    coordinator = SpeedportCoordinator(hass, entry, entry.data[CONF_HOST])
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SpeedportConfigEntry) -> bool:
    """Unload the config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: SpeedportConfigEntry) -> None:
    """Apply a changed scan interval."""
    await hass.config_entries.async_reload(entry.entry_id)
