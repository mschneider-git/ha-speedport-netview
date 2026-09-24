"""Polling coordinator for the Speedport device list."""

from __future__ import annotations

import logging
import time
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SpeedportClient, SpeedportDevice, SpeedportError
from .const import (
    CONF_CLEANUP_DAYS,
    CONF_SCAN_INTERVAL,
    DEFAULT_CLEANUP_DAYS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
SAVE_DELAY = 60

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
        self.cleanup_days: int = entry.options.get(
            CONF_CLEANUP_DAYS, DEFAULT_CLEANUP_DAYS
        )
        # MAC -> Zeitpunkt (Unix-Zeit), zu dem der Router das Geraet zuletzt
        # als verbunden gemeldet hat. Ueberlebt Neustarts, damit das Aufraeumen
        # nicht bei jedem Start von vorn zaehlt.
        self.last_seen: dict[str, float] = {}
        self._store: Store[dict[str, float]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}.last_seen"
        )

    async def async_load_last_seen(self) -> None:
        """Restore when each device was last connected."""
        stored = await self._store.async_load()
        if isinstance(stored, dict):
            self.last_seen = {
                str(mac): float(ts)
                for mac, ts in stored.items()
                if isinstance(ts, (int, float))
            }

    def mark_seen(self, mac: str, now: float | None = None) -> None:
        """Start the clock for a device that has no record yet."""
        if mac not in self.last_seen:
            self.last_seen[mac] = time.time() if now is None else now
            self._schedule_save()

    def is_stale(self, mac: str, now: float | None = None) -> bool:
        """Return whether a device has been away longer than the cleanup period."""
        if self.cleanup_days <= 0:
            return False
        seen = self.last_seen.get(mac)
        if seen is None:
            return False
        now = time.time() if now is None else now
        return now - seen > self.cleanup_days * 86400

    def _schedule_save(self) -> None:
        self._store.async_delay_save(lambda: dict(self.last_seen), SAVE_DELAY)

    async def _async_update_data(self) -> dict[str, SpeedportDevice]:
        try:
            devices = await self.client.async_get_devices()
        except SpeedportError as err:
            raise UpdateFailed(str(err)) from err
        now = time.time()
        for device in devices:
            if device.connected:
                self.last_seen[device.mac] = now
            else:
                self.last_seen.setdefault(device.mac, now)
        self._schedule_save()
        return {device.mac: device for device in devices}
