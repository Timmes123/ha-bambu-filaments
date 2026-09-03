"""Data update coordinator for Bambu Filaments."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AuthExpired, BambuCloudClient, BambuCloudError
from .ams_register import (
    MountedTray,
    bambulab_available,
    build_ams_sync_item,
    scan_mounted_rfid_trays,
)
from .colors import BambuColorDB
from .const import (
    DEFAULT_AUTO_DEDUP,
    DEFAULT_COLOR_LANG,
    DEFAULT_SCAN_INTERVAL_MIN,
    DOMAIN,
    OPT_AUTO_DEDUP,
    OPT_AUTO_REGISTER,
    DEFAULT_AUTO_REGISTER,
    OPT_COLOR_LANG,
    OPT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


def _hex6(color: Any) -> str:
    """Normalize a cloud color to bare RRGGBB (AMS spools may lack '#' or carry alpha)."""
    if not isinstance(color, str):
        return ""
    return color.lstrip("#").upper()[:6]


def spool_remaining_pct(spool: dict[str, Any]) -> int:
    """Derive remaining percent; the cloud only stores gram values."""
    net = spool.get("netWeight") or 0
    total = spool.get("totalNetWeight") or 0
    if not isinstance(net, (int, float)) or not isinstance(total, (int, float)) or total <= 0:
        return 0
    return max(0, min(100, round(net / total * 100)))


class BambuFilamentsCoordinator(DataUpdateCoordinator[dict[int, dict[str, Any]]]):
    """Polls the cloud filament inventory. Data is a dict keyed by spool id."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: BambuCloudClient,
        colordb: BambuColorDB,
    ) -> None:
        minutes = entry.options.get(OPT_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MIN)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(minutes=minutes),
        )
        self.client = client
        self.colordb = colordb
        self._catalog_cache: list[dict[str, Any]] | None = None
        self._catalog_cached_at: float = 0.0
        # Auto-register bookkeeping: uuids we created ourselves (until the
        # cloud lists them) and uuids the user deleted while the spool was
        # still mounted (never re-create those until the spool is removed).
        self._registered_uuids: set[str] = set()
        self._skip_uuids: set[str] = set()
        self._mounted_known: set[str] = set()

    def color_lookup(self, spool: dict[str, Any]) -> tuple[str | None, str | None]:
        """Localized official color name + Bambu color code for a spool."""
        colors = [c for c in (spool.get("colors") or [spool.get("color")]) if c]
        lang = (self.config_entry.options or {}).get(OPT_COLOR_LANG, DEFAULT_COLOR_LANG)
        if lang == "auto":
            lang = self.hass.config.language
        return self.colordb.lookup(spool.get("filamentId"), colors, lang)

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        try:
            spools = await self.hass.async_add_executor_job(self.client.get_spools)
        except AuthExpired as err:
            raise ConfigEntryAuthFailed(
                "Bambu cloud token expired - re-authentication required"
            ) from err
        except BambuCloudError as err:
            raise UpdateFailed(str(err)) from err
        data = {
            s["id"]: _sanitize_spool(s) for s in spools if isinstance(s.get("id"), int)
        }
        # Auto-dedup only acts on spools that are NEW relative to the previous
        # sync - the first refresh after (re)load establishes the baseline and
        # never deletes, so a restart can't mass-match the whole library.
        # Register first: a spool we just added is "new vs. the previous sync"
        # for the dedup step below, so pre-entered manual stock gets consumed
        # exactly as it would after Studio/Handy registered the spool.
        if self.config_entry.options.get(OPT_AUTO_REGISTER, DEFAULT_AUTO_REGISTER):
            data = await self._async_register_ams(data)
        if self.data is not None and self.config_entry.options.get(
            OPT_AUTO_DEDUP, DEFAULT_AUTO_DEDUP
        ):
            await self._async_dedup_manual(data)
        return data

    async def _async_register_ams(
        self, data: dict[int, dict[str, Any]]
    ) -> dict[int, dict[str, Any]]:
        """Create library entries for RFID spools that sit in an AMS but are unknown.

        Data comes from the Bambu Lab printer integration's slot sensors; the
        cloud RFID equals the tray uuid. Spools the user deleted while they
        were still loaded are remembered and left alone until unloaded.
        """
        if not bambulab_available(self.hass):
            return data
        trays = scan_mounted_rfid_trays(self.hass)
        mounted = {t.tray_uuid for t in trays}
        known = {
            str(s.get("RFID") or "").upper() for s in data.values() if s.get("RFID")
        }
        # A uuid that was mounted AND in the library last time but is gone
        # from the library now was deleted on purpose - do not resurrect it.
        self._skip_uuids |= (self._mounted_known & mounted) - known
        self._skip_uuids &= mounted
        self._registered_uuids &= mounted - known
        self._mounted_known = mounted & known
        missing = [
            t for t in trays
            if t.tray_uuid not in known
            and t.tray_uuid not in self._skip_uuids
            and t.tray_uuid not in self._registered_uuids
        ]
        if not missing:
            return data
        try:
            catalog = await self.async_get_catalog()
        except (AuthExpired, BambuCloudError):
            catalog = []
        created = 0
        by_printer: dict[str, list[MountedTray]] = {}
        for tray in missing:
            by_printer.setdefault(tray.printer_serial, []).append(tray)
        for dev_id, dev_trays in by_printer.items():
            items = [build_ams_sync_item(t, catalog, self.colordb) for t in dev_trays]
            try:
                result = await self.hass.async_add_executor_job(
                    self.client.ams_sync, dev_id, items
                )
            except (AuthExpired, BambuCloudError) as err:
                _LOGGER.warning(
                    "Auto-register: AMS sync for %s rejected (%s): %s",
                    dev_trays[0].printer_name,
                    ", ".join(t.location for t in dev_trays),
                    err,
                )
                continue
            made = {str(r).upper() for r in (result.get("createdRFIDs") or [])}
            for tray, item in zip(dev_trays, items):
                self._registered_uuids.add(tray.tray_uuid)
                if tray.tray_uuid in made:
                    created += 1
                    _LOGGER.info(
                        "Auto-register: added RFID spool %s %s %s (%s, %s/%s g) found in %s "
                        "to the cloud library",
                        item["filamentVendor"], item["filamentName"], item["color"],
                        item["filamentId"], item["netWeight"], item["totalNetWeight"],
                        tray.location,
                    )
                else:
                    _LOGGER.debug(
                        "Auto-register: cloud did not report %s in %s as created: %s",
                        tray.tray_uuid, tray.location, result,
                    )
        if not created:
            return data
        try:
            spools = await self.hass.async_add_executor_job(self.client.get_spools)
        except (AuthExpired, BambuCloudError) as err:
            _LOGGER.debug("Auto-register: re-fetch after create failed: %s", err)
            return data
        return {
            s["id"]: _sanitize_spool(s) for s in spools if isinstance(s.get("id"), int)
        }

    async def _async_dedup_manual(self, data: dict[int, dict[str, Any]]) -> None:
        """For each newly appeared AMS spool, delete ONE matching full manual spool.

        The cloud creates a fresh spool keyed by RFID whenever an official
        spool is first loaded into an AMS; a manually pre-created entry for
        that spool can never be matched by Bambu and would stay behind as a
        duplicate. This removes exactly one full manual twin per new AMS spool.
        """
        new_ams = [
            spool
            for sid, spool in data.items()
            if sid not in self.data and spool.get("createType") == "ams"
        ]
        for ams_spool in new_ams:
            twin = self._find_manual_twin(ams_spool, data)
            if twin is None:
                continue
            try:
                await self.hass.async_add_executor_job(
                    self.client.delete_spools, [twin["id"]]
                )
            except (AuthExpired, BambuCloudError) as err:
                _LOGGER.warning(
                    "Auto-dedup: could not delete manual spool %s: %s", twin["id"], err
                )
                continue
            data.pop(twin["id"], None)
            _LOGGER.info(
                "Auto-dedup: new AMS spool %s (%s %s %s) adopted manual spool %s - "
                "deleted the manual duplicate",
                ams_spool.get("id"),
                ams_spool.get("filamentVendor"),
                ams_spool.get("filamentName"),
                ams_spool.get("color"),
                twin["id"],
            )

    @staticmethod
    def _find_manual_twin(
        ams_spool: dict[str, Any], data: dict[int, dict[str, Any]]
    ) -> dict[str, Any] | None:
        """A full, manually created spool of the same product and color."""

        def _norm(value: Any) -> str:
            return str(value or "").strip().lower()

        candidates = [
            spool
            for spool in data.values()
            if spool.get("createType") == "manual"
            and _norm(spool.get("filamentVendor")) == _norm(ams_spool.get("filamentVendor"))
            and _norm(spool.get("filamentId")) == _norm(ams_spool.get("filamentId"))
            and _hex6(spool.get("color")) == _hex6(ams_spool.get("color"))
            and isinstance(spool.get("totalNetWeight"), (int, float))
            and (spool.get("totalNetWeight") or 0) > 0
            and (spool.get("netWeight") or 0) >= spool["totalNetWeight"]
        ]
        if not candidates:
            return None
        # Prefer an untouched entry (no note, no custom name); oldest id first
        # so personalized spools survive the longest.
        candidates.sort(
            key=lambda s: (bool(s.get("note")), bool(s.get("displayName")), s.get("id", 0))
        )
        return candidates[0]

    async def async_get_catalog(self) -> list[dict[str, Any]]:
        """Normalized create-catalog entries, cached for an hour."""
        now = self.hass.loop.time()
        if self._catalog_cache is None or now - self._catalog_cached_at > 3600:
            raw = await self.hass.async_add_executor_job(self.client.get_catalog)
            self._catalog_cache = [
                {
                    "vendor": e.get("filamentVendor"),
                    "material": e.get("filamentType"),
                    "name": e.get("filamentName"),
                    "filament_id": e.get("filamentId"),
                }
                for e in raw.get("filamentSettings") or []
                if isinstance(e, dict)
            ]
            self._catalog_cached_at = now
        return self._catalog_cache


def _sanitize_spool(spool: dict[str, Any]) -> dict[str, Any]:
    """Coerce cloud weight fields to numbers so sums and sensors never throw."""
    for key, default in (("netWeight", 0), ("totalNetWeight", None)):
        value = spool.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            try:
                spool[key] = int(value)
            except (TypeError, ValueError):
                spool[key] = default
    return spool
