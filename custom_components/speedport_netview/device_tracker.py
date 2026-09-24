"""Device trackers for the clients the Speedport lists."""

from __future__ import annotations

import time
from typing import Any

from homeassistant.components.device_tracker import ScannerEntity, SourceType
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import SpeedportDevice
from .coordinator import SpeedportConfigEntry, SpeedportCoordinator

PARALLEL_UPDATES = 0

# Veraltete Tracker werden hoechstens so oft gesucht.
CLEANUP_INTERVAL = 3600


def _is_random_mac(mac: str) -> bool:
    """Return whether a MAC is locally administered, e.g. a private Wi-Fi address."""
    return bool(int(mac[:2], 16) & 0x02)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SpeedportConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create a tracker per device and pick up new ones as they appear."""
    coordinator = entry.runtime_data
    registry = er.async_get(hass)
    known: set[str] = set()
    last_cleanup = 0.0

    # Tracker aus frueheren Versionen haben noch keinen Zeitstempel: Ihre
    # Frist beginnt jetzt, statt dass sie beim ersten Start sofort verschwinden.
    now = time.time()
    for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if reg_entry.unique_id:
            coordinator.mark_seen(reg_entry.unique_id, now)

    @callback
    def _async_remove_stale() -> None:
        now = time.time()
        for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
            mac = reg_entry.unique_id
            if mac and coordinator.is_stale(mac, now):
                registry.async_remove(reg_entry.entity_id)
                known.discard(mac)

    @callback
    def _async_update() -> None:
        nonlocal last_cleanup
        now = time.time()
        if now - last_cleanup >= CLEANUP_INTERVAL:
            last_cleanup = now
            _async_remove_stale()
        # Ein Geraet, das der Router noch listet, das aber laenger als die
        # Aufraeumfrist nicht verbunden war, bekommt erst wieder einen Tracker,
        # wenn es sich erneut verbindet.
        new = [
            mac
            for mac in coordinator.data
            if mac not in known and not coordinator.is_stale(mac, now)
        ]
        if not new:
            return
        known.update(new)
        async_add_entities(SpeedportTracker(coordinator, mac) for mac in sorted(new))

    _async_update()
    entry.async_on_unload(coordinator.async_add_listener(_async_update))


class SpeedportTracker(CoordinatorEntity[SpeedportCoordinator], ScannerEntity):
    """Presence of one client, as reported by the router."""

    def __init__(self, coordinator: SpeedportCoordinator, mac: str) -> None:
        super().__init__(coordinator)
        self._mac = mac
        # Die eindeutige Kennung leitet ScannerEntity selbst aus mac_address ab.

    @property
    def _device(self) -> SpeedportDevice | None:
        return self.coordinator.data.get(self._mac)

    @property
    def name(self) -> str:
        """Return the router's name for the device, else its MAC."""
        device = self._device
        if device is not None and device.name:
            return device.name
        return self._mac.upper()

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Register trackers enabled, except for private (random) addresses.

        Home Assistant deaktiviert MAC-basierte Tracker sonst, solange kein
        anderes Geraet dieselbe MAC kennt. Hier ist der Router die einzige
        Quelle, und genau seine Liste soll sichtbar sein -- ein still
        deaktivierter Tracker waere kein brauchbares Ergebnis.

        Private WLAN-Adressen wechseln aber je nach Geraet regelmaessig; jede
        neue Adresse waere ein weiterer Tracker. Diese werden deshalb
        deaktiviert angelegt und lassen sich bei Bedarf einzeln einschalten.
        """
        return not _is_random_mac(self._mac)

    @property
    def source_type(self) -> SourceType:
        """Presence comes from the router, not from the device itself."""
        return SourceType.ROUTER

    @property
    def is_connected(self) -> bool:
        """Report exactly what the router reports.

        Ein Geraet, das aus der Liste verschwindet, gilt als abwesend -- die
        Integration erfindet keine eigene Nachlaufzeit.
        """
        device = self._device
        return device is not None and device.connected

    @property
    def mac_address(self) -> str:
        """Return the client's MAC address."""
        return self._mac

    @property
    def ip_address(self) -> str | None:
        """Return the address the router handed out."""
        device = self._device
        return device.ipv4 if device is not None else None

    @property
    def hostname(self) -> str | None:
        """Return the name the router knows the client by."""
        device = self._device
        return device.name if device is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose how the client is attached."""
        device = self._device
        if device is None:
            return {}
        attributes: dict[str, Any] = {"verbindung": device.connection}
        if device.rssi is not None:
            attributes["rssi"] = device.rssi
        if device.standards:
            attributes["standards"] = device.standards
        return attributes
