"""Official Bambu Lab filament color database.

Maps a spool's filamentId + color hex to the official webshop color name
(localized) and color code. The database is the public
`filaments_color_codes.json` from the Bambu Studio repository; it is fetched
at runtime and cached in HA storage so we do not redistribute it.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

COLOR_DB_URL = (
    "https://raw.githubusercontent.com/bambulab/BambuStudio/master/"
    "resources/profiles/BBL/filament/filaments_color_codes.json"
)
STORAGE_KEY = f"{DOMAIN}.color_codes"
STORAGE_VERSION = 1
REFRESH_AFTER_S = 7 * 24 * 3600


def normalize_hex(value: str | None) -> str:
    """Uppercase #RRGGBBAA form so cloud and database hexes compare equal."""
    if not value:
        return ""
    value = value.strip().upper()
    if not value.startswith("#"):
        value = f"#{value}"
    if len(value) == 7:
        value = f"{value}FF"
    return value


def _color_key(colors: list[str]) -> tuple[str, ...]:
    return tuple(sorted(normalize_hex(c) for c in colors if c))


class BambuColorDB:
    """Lazy-loaded lookup: (filament_id, colors) -> localized name + code."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._by_id_color: dict[tuple[str, tuple[str, ...]], dict] = {}
        self._by_color: dict[tuple[str, ...], dict] = {}

    async def async_load(self) -> None:
        """Load from cache, refreshing from the public source when stale."""
        cached = await self._store.async_load() or {}
        entries = cached.get("data")
        stale = time.time() - cached.get("fetched_at", 0) > REFRESH_AFTER_S
        if not entries or stale:
            if fresh := await self._fetch():
                entries = fresh
                await self._store.async_save({"data": entries, "fetched_at": time.time()})
        if entries:
            self._build_index(entries)

    async def _fetch(self) -> list[dict] | None:
        try:
            session = async_get_clientsession(self._hass)
            async with session.get(COLOR_DB_URL, timeout=30) as response:
                if response.status != 200:
                    _LOGGER.warning("Color database fetch failed: HTTP %s", response.status)
                    return None
                payload = await response.json(content_type=None)
            return payload.get("data") or None
        except Exception as err:  # network failures must never break setup
            _LOGGER.warning("Color database fetch failed: %s", err)
            return None

    def _build_index(self, entries: list[dict]) -> None:
        by_id_color: dict[tuple[str, tuple[str, ...]], dict] = {}
        by_color: dict[tuple[str, ...], dict] = {}
        for entry in entries:
            colors = entry.get("fila_color") or []
            if not colors:
                continue
            key = _color_key(colors)
            record = {
                "names": entry.get("fila_color_name") or {},
                "code": entry.get("fila_color_code"),
            }
            if fila_id := entry.get("fila_id"):
                by_id_color[(fila_id, key)] = record
            by_color.setdefault(key, record)
        self._by_id_color = by_id_color
        self._by_color = by_color

    def lookup(
        self, filament_id: str | None, colors: list[str], language: str
    ) -> tuple[str | None, str | None]:
        """Return (localized color name, Bambu color code) or (None, None)."""
        if not colors:
            return None, None
        key = _color_key(colors)
        record = None
        if filament_id:
            record = self._by_id_color.get((filament_id, key))
        if record is None:
            record = self._by_color.get(key)
        if record is None:
            return None, None
        names = record["names"]
        lang = (language or "en").split("-")[0].lower()
        name = names.get(lang) or names.get("en") or next(iter(names.values()), None)
        return name, record["code"]
