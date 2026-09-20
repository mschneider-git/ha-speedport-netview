"""Polling coordinator for the Speedport device list."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SpeedportClient, SpeedportDevice, SpeedportError
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type SpeedportConfigEntry = ConfigEntry[SpeedportCoordinator]


class SpeedportCoordinator(DataUpdateCoordinator[dict[str, SpeedportDevice]]):
    """Keep the device list up to date."""

    config_entry: SpeedportConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: SpeedportConfigEntry, host: str
    ) -> None:
        interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=interval),
        )
        self.client = SpeedportClient(async_get_clientsession(hass), host)

    async def _async_update_data(self) -> dict[str, SpeedportDevice]:
        try:
            devices = await self.client.async_get_devices()
        except SpeedportError as err:
            raise UpdateFailed(str(err)) from err
        return {device.mac: device for device in devices}
