"""Constants for the Speedport Netview integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "speedport_netview"

DEFAULT_HOST: Final = "192.168.2.1"
DEFAULT_SCAN_INTERVAL: Final = 30
MIN_SCAN_INTERVAL: Final = 10
MAX_SCAN_INTERVAL: Final = 600

CONF_SCAN_INTERVAL: Final = "scan_interval"

# Tracker fuer Geraete, die so lange nicht mehr verbunden waren, werden
# entfernt (0 = nie). Handys und Laptops wechseln ihre private WLAN-Adresse,
# ohne Aufraeumen sammeln sich sonst verwaiste Tracker an.
CONF_CLEANUP_DAYS: Final = "cleanup_days"
DEFAULT_CLEANUP_DAYS: Final = 30
MAX_CLEANUP_DAYS: Final = 365

# Die Statusseite /html/login/netview.html liefert die Geraeteliste ohne Login,
# allerdings AES-CCM-verschluesselt. Den Schluessel fuer nicht angemeldete
# Aufrufe haelt die Weboberflaeche selbst in js/jquery-addons.js vor
# (Variable keyArrayDefault). Diese Integration liest ihn dort zur Laufzeit aus,
# statt ihn mitzuliefern: So steht er nirgends im Quelltext, und ein anderes
# Modell oder eine neue Firmware bringt einfach ihren eigenen mit.
SCRIPT_PATH: Final = "/js/jquery-addons.js"
KEY_PATTERN: Final = r'keyArrayDefault\s*=\s*[\'"]([0-9a-fA-F]{64})[\'"]'

DEVICE_LIST_PATH: Final = "/data/DeviceList.json"

# Ein haengender Router soll eine Abfrage nicht minutenlang blockieren.
REQUEST_TIMEOUT: Final = 10

# Maximale Groesse der Antwort, damit ein defektes oder fremdes Geraet den
# Speicher nicht vollaeuft.
MAX_RESPONSE_BYTES: Final = 4 * 1024 * 1024

# varid der Listeneintraege -> Verbindungsart
DEVICE_TEMPLATES: Final = {
    "addmlandevice": "LAN",
    "addmwlandevice": "2,4 GHz",
    "addmwlan5device": "5 GHz",
}
