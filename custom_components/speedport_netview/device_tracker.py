"""Device trackers for the clients the Speedport lists."""

from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import ScannerEntity, SourceType
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import SpeedportDevice
from .coordinator import SpeedportConfigEntry, SpeedportCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: Any,
    entry: SpeedportConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create a tracker per device and pick up new ones as they appear."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _async_add_new() -> None:
        new = [mac for mac in coordinator.data if mac not in known]
        if not new:
            return
        known.update(new)
        async_add_entities(SpeedportTracker(coordinator, mac) for mac in sorted(new))

    _async_add_new()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_new))


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
        """Register trackers enabled.

        Home Assistant deaktiviert MAC-basierte Tracker sonst, solange kein
        anderes Geraet dieselbe MAC kennt. Hier ist der Router die einzige
        Quelle, und genau seine Liste soll sichtbar sein -- ein still
        deaktivierter Tracker waere kein brauchbares Ergebnis.
        """
        return True

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
