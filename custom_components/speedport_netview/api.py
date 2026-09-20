"""Read the Speedport status page without logging in.

Die Weboberflaeche des Speedport erlaubt nur eine Sitzung. Diese Integration
meldet sich deshalb bewusst nicht an, sondern liest ausschliesslich die
oeffentliche Statusseite -- so bleibt die Anmeldung im Browser jederzeit
moeglich.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from aiohttp import ClientError, ClientResponse, ClientSession
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESCCM

from .const import (
    DEVICE_LIST_PATH,
    DEVICE_TEMPLATES,
    KEY_PATTERN,
    MAX_RESPONSE_BYTES,
    SCRIPT_PATH,
)


class SpeedportError(Exception):
    """Base error for this client."""


class SpeedportConnectionError(SpeedportError):
    """The router could not be reached."""


class SpeedportResponseError(SpeedportError):
    """The router answered, but not with a readable device list."""


@dataclass(frozen=True, slots=True)
class SpeedportDevice:
    """One entry of the router's device list."""

    mac: str
    name: str | None
    ipv4: str | None
    connection: str
    connected: bool
    rssi: int | None
    standards: str | None


class SpeedportClient:
    """Fetch and decode the unauthenticated device list."""

    def __init__(self, session: ClientSession, host: str) -> None:
        self._session = session
        self._host = host
        self._key: bytes | None = None

    @property
    def host(self) -> str:
        """Return the configured router address."""
        return self._host

    async def async_get_devices(self) -> list[SpeedportDevice]:
        """Return every device the router currently lists."""
        payload = await self._fetch(DEVICE_LIST_PATH)
        key = self._key or await self._async_load_key()
        try:
            document = _decrypt(payload, key)
        except SpeedportResponseError:
            # Ein Firmware-Update kann den Schluessel wechseln. Einmal neu
            # einlesen, bevor der Abruf als fehlgeschlagen gilt.
            if self._key is None:
                raise
            document = _decrypt(payload, await self._async_load_key())
        return _parse(document)

    async def _async_load_key(self) -> bytes:
        """Read the key the router's own web interface uses."""
        script = await self._fetch(SCRIPT_PATH)
        match = re.search(KEY_PATTERN, script.decode("utf-8", "replace"))
        if match is None:
            raise SpeedportResponseError("router did not expose a decryption key")
        self._key = bytes.fromhex(match.group(1))
        return self._key

    async def _fetch(self, path: str) -> bytes:
        """Fetch one unauthenticated path from the router."""
        url = f"http://{self._host}{path}"
        try:
            async with self._session.get(url, allow_redirects=False) as response:
                return await self._read(response)
        except ClientError as err:
            raise SpeedportConnectionError(str(err)) from err
        except TimeoutError as err:
            raise SpeedportConnectionError("timeout") from err

    async def _read(self, response: ClientResponse) -> bytes:
        # Ohne Anmeldung antwortet der Speedport auf geschuetzte Pfade mit 302
        # auf die Loginseite. Umleitungen gelten deshalb als Fehler und nicht
        # als leere Geraeteliste.
        if response.status != 200:
            raise SpeedportResponseError(
                f"router returned HTTP status {response.status}"
            )
        chunks: list[bytes] = []
        size = 0
        async for chunk in response.content.iter_chunked(65536):
            size += len(chunk)
            if size > MAX_RESPONSE_BYTES:
                raise SpeedportResponseError("device list is too large")
            chunks.append(chunk)
        return b"".join(chunks)


def _decrypt(payload: bytes, key: bytes) -> list[dict]:
    """Turn the hex-encoded, AES-CCM protected body into its JSON document."""
    try:
        ciphertext = bytes.fromhex(payload.decode("ascii").strip())
    except (UnicodeDecodeError, ValueError) as err:
        raise SpeedportResponseError("device list is not hex encoded") from err
    try:
        plaintext = AESCCM(key, tag_length=16).decrypt(key[:8], ciphertext, b"")
    except (InvalidTag, ValueError) as err:
        raise SpeedportResponseError("device list could not be decrypted") from err
    try:
        document = json.loads(plaintext)
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise SpeedportResponseError("device list is not valid JSON") from err
    if not isinstance(document, list):
        raise SpeedportResponseError("device list has an unexpected shape")
    return document


def _parse(document: list[dict]) -> list[SpeedportDevice]:
    """Turn the router's variable list into device records."""
    devices: list[SpeedportDevice] = []
    for entry in document:
        if not isinstance(entry, dict) or entry.get("vartype") != "template":
            continue
        connection = DEVICE_TEMPLATES.get(str(entry.get("varid")))
        if connection is None:
            continue
        fields = {
            str(field.get("varid")): field.get("varvalue")
            for field in entry.get("varvalue", [])
            if isinstance(field, dict)
        }
        mac = _mac(fields.get("mdevice_mac"))
        if mac is None:
            continue
        devices.append(
            SpeedportDevice(
                mac=mac,
                name=_text(fields.get("mdevice_name")),
                ipv4=_text(fields.get("mdevice_ipv4")),
                connection=connection,
                connected=str(fields.get("mdevice_connected")) == "1",
                rssi=_rssi(fields.get("mdevice_rssi")),
                standards=_text(fields.get("mdevice_standards")),
            )
        )
    return devices


def _mac(value: object) -> str | None:
    """Normalize the router's AA-BB-… notation to Home Assistant's aa:bb:…."""
    if not isinstance(value, str):
        return None
    candidate = value.strip().replace("-", ":").lower()
    parts = candidate.split(":")
    if len(parts) != 6 or not all(
        len(part) == 2 and all(c in "0123456789abcdef" for c in part) for part in parts
    ):
        return None
    return candidate


def _text(value: object) -> str | None:
    """Return a printable value, treating the router's placeholders as empty."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped if stripped and stripped != "-" else None


def _rssi(value: object) -> int | None:
    """Return the signal strength, skipping the 0 used for wired entries."""
    try:
        rssi = int(str(value))
    except (TypeError, ValueError):
        return None
    return rssi if rssi < 0 else None
