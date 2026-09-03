"""Data update coordinator for Bambu Filaments."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.core import Event, EventStateChangedData, callback
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AuthExpired, BambuCloudClient, BambuCloudError
from .ams_register import (
    MountedTray,
    bambulab_available,
    build_ams_sync_item,
    printer_busy,
    printer_progress,
    scan_mounted_rfid_trays,
    watched_entity_ids,
)
from .usage import UsageDeductor, find_mounted_manual_spool, slot_from_mapping
from .colors import BambuColorDB
from .const import (
    DEFAULT_AUTO_DEDUP,
    DEFAULT_COLOR_LANG,
    DEFAULT_SCAN_INTERVAL_MIN,
    DOMAIN,
    OPT_AUTO_DEDUP,
    OPT_AUTO_REGISTER,
    DEFAULT_AUTO_REGISTER,
    OPT_SYNC_REMAINING,
    DEFAULT_SYNC_REMAINING,
    OPT_EMPTY_PCT,
    DEFAULT_EMPTY_PCT,
    OPT_DEDUCT_USAGE,
    DEFAULT_DEDUCT_USAGE,
    REMAINING_PUSH_COOLDOWN_S,
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
        # Remaining-weight sync: last pushed (net, monotonic time) per uuid,
        # last seen AMS percent per uuid (for the empty-on-removal rule).
        self._last_push: dict[str, tuple[int, float]] = {}
        self._last_remain: dict[str, tuple[int, MountedTray]] = {}
        # Progress snapshot per printer taken when a print stops - lets a
        # cancelled job be booked proportionally.
        self._last_progress: dict[str, tuple[int, datetime]] = {}
        self.usage = UsageDeductor(hass, entry.entry_id)
        self._unsub_listener = None
        self._listener_ids: set[str] = set()
        self._watched: dict[str, tuple[str, str]] = {}
        self._event_debouncer = Debouncer(
            hass, _LOGGER, cooldown=20, immediate=False,
            function=self.async_request_refresh,
        )

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
        # AMS-driven steps first: a spool registered here is "new vs. the
        # previous sync" for the dedup step below, so pre-entered manual stock
        # gets consumed exactly as it would after Studio/Handy registered it.
        data = await self._async_ams_pass(data)
        if self.data is not None and self.config_entry.options.get(
            OPT_AUTO_DEDUP, DEFAULT_AUTO_DEDUP
        ):
            await self._async_dedup_manual(data)
        await self._async_deduct_usage(data)
        self.async_update_listener()
        return data

    # ------------------------------------------------------------ AMS bridge

    def _opt(self, key: str, default: Any) -> Any:
        return self.config_entry.options.get(key, default)

    async def _async_ams_pass(
        self, data: dict[int, dict[str, Any]]
    ) -> dict[int, dict[str, Any]]:
        """Everything that needs the Bambu Lab printer integration's AMS sensors."""
        want_register = self._opt(OPT_AUTO_REGISTER, DEFAULT_AUTO_REGISTER)
        want_remaining = self._opt(OPT_SYNC_REMAINING, DEFAULT_SYNC_REMAINING)
        empty_pct = int(self._opt(OPT_EMPTY_PCT, DEFAULT_EMPTY_PCT) or 0)
        if not (want_register or want_remaining or empty_pct):
            return data
        if not bambulab_available(self.hass):
            return data
        trays = scan_mounted_rfid_trays(self.hass)
        if want_register:
            data = await self._async_register_ams(data, trays)
        if empty_pct:
            await self._async_mark_removed_empty(data, trays, empty_pct)
        if want_remaining:
            await self._async_sync_remaining(data, trays)
        self._last_remain = {t.tray_uuid: (t.remain, t) for t in trays}
        return data

    @callback
    def async_update_listener(self) -> None:
        """(Re)subscribe to the printer integration's tray/status sensors.

        A change there (spool inserted/removed, AMS weight step, print ended)
        triggers a debounced refresh instead of waiting for the next poll.
        """
        wanted: dict[str, tuple[str, str]] = {}
        if bambulab_available(self.hass) and (
            self._opt(OPT_AUTO_REGISTER, DEFAULT_AUTO_REGISTER)
            or self._opt(OPT_SYNC_REMAINING, DEFAULT_SYNC_REMAINING)
            or int(self._opt(OPT_EMPTY_PCT, DEFAULT_EMPTY_PCT) or 0)
            or self._opt(OPT_DEDUCT_USAGE, DEFAULT_DEDUCT_USAGE)
        ):
            wanted = watched_entity_ids(self.hass)
        if set(wanted) == self._listener_ids:
            return
        if self._unsub_listener is not None:
            self._unsub_listener()
            self._unsub_listener = None
        self._listener_ids = set(wanted)
        self._watched = wanted
        if wanted:
            self._unsub_listener = async_track_state_change_event(
                self.hass, list(wanted), self._handle_bambulab_event
            )

    @callback
    def _handle_bambulab_event(self, event: Event[EventStateChangedData]) -> None:
        new = event.data.get("new_state")
        old = event.data.get("old_state")
        if new is None:
            return
        serial, kind = self._watched.get(event.data["entity_id"], ("", ""))
        if kind == "status" and old is not None and old.state != new.state:
            # A print just stopped: remember how far it got, so a cancelled
            # job can be booked proportionally (the cloud only knows the plan).
            if old.state in ("running", "pause") and new.state not in ("running", "pause"):
                progress = printer_progress(self.hass, serial)
                if progress is not None:
                    self._last_progress[serial] = (progress, dt_util.utcnow())
        elif old is not None and old.state == new.state and old.attributes == new.attributes:
            return
        self.hass.async_create_task(self._event_debouncer.async_call())

    async def async_shutdown(self) -> None:
        if self._unsub_listener is not None:
            self._unsub_listener()
            self._unsub_listener = None
        await self._event_debouncer.async_shutdown()
        await super().async_shutdown()

    async def _async_sync_remaining(
        self, data: dict[int, dict[str, Any]], trays: list[MountedTray]
    ) -> None:
        """Push the AMS remaining weight of known RFID spools to the cloud.

        Mirrors Studio's auto push: skip when unchanged, 10 min cooldown per
        spool while the printer is busy, immediate when idle or at 0 %.
        """
        by_rfid = {
            str(s.get("RFID") or "").upper(): s for s in data.values() if s.get("RFID")
        }
        now = self.hass.loop.time()
        by_printer: dict[str, list[tuple[MountedTray, dict[str, Any], int]]] = {}
        for tray in trays:
            spool = by_rfid.get(tray.tray_uuid)
            if spool is None or tray.remain < 0:
                continue
            total = spool.get("totalNetWeight")
            if not isinstance(total, (int, float)) or total <= 0:
                total = tray.tray_weight if tray.tray_weight > 0 else 1000
            net = max(0, min(int(total), round(int(total) * tray.remain / 100)))
            if net == int(spool.get("netWeight") or 0):
                continue
            last = self._last_push.get(tray.tray_uuid)
            if last is not None and last[0] == net:
                continue
            if (
                net > 0
                and last is not None
                and now - last[1] < REMAINING_PUSH_COOLDOWN_S
                and printer_busy(self.hass, tray.printer_serial)
            ):
                continue
            by_printer.setdefault(tray.printer_serial, []).append((tray, spool, net))
        if not by_printer:
            return
        try:
            catalog = await self.async_get_catalog()
        except (AuthExpired, BambuCloudError):
            catalog = []
        for dev_id, entries in by_printer.items():
            items = []
            for tray, spool, net in entries:
                item = build_ams_sync_item(tray, catalog, self.colordb)
                # Keep the library's identity/total - only the weight comes from the AMS.
                item.update(
                    filamentVendor=spool.get("filamentVendor") or item["filamentVendor"],
                    filamentType=spool.get("filamentType") or item["filamentType"],
                    filamentName=spool.get("filamentName") or item["filamentName"],
                    netWeight=net,
                    totalNetWeight=int(spool.get("totalNetWeight") or item["totalNetWeight"]),
                    note=spool.get("note") or "",
                )
                if spool.get("trayIdName"):
                    item["trayIdName"] = spool["trayIdName"]
                items.append(item)
            try:
                await self.hass.async_add_executor_job(self.client.ams_sync, dev_id, items)
            except (AuthExpired, BambuCloudError) as err:
                _LOGGER.warning("Remaining sync for %s failed: %s", entries[0][0].printer_name, err)
                continue
            for tray, spool, net in entries:
                self._last_push[tray.tray_uuid] = (net, now)
                _LOGGER.info(
                    "Remaining sync: %s %s %s in %s -> %s g (AMS %s %%, was %s g)%s",
                    spool.get("filamentVendor"), spool.get("filamentName"), spool.get("color"),
                    tray.location, net, tray.remain, spool.get("netWeight"),
                    " - spool is now empty" if net == 0 else "",
                )
                spool["netWeight"] = net
                if net == 0:
                    spool["depleted"] = True

    async def _async_mark_removed_empty(
        self, data: dict[int, dict[str, Any]], trays: list[MountedTray], pct: int
    ) -> None:
        """A spool taken out of the AMS with <= pct % left is booked as empty.

        Covers the runout-then-swap case where the 0 % reading was never
        observed (Home Assistant down, AMS estimate stuck at 2-3 %).
        """
        mounted = {t.tray_uuid for t in trays}
        by_rfid = {
            str(s.get("RFID") or "").upper(): s for s in data.values() if s.get("RFID")
        }
        for uuid, (remain, tray) in self._last_remain.items():
            if uuid in mounted or remain < 0 or remain > pct:
                continue
            spool = by_rfid.get(uuid)
            if spool is None or int(spool.get("netWeight") or 0) == 0:
                continue
            try:
                await self.hass.async_add_executor_job(
                    self.client.update_spool,
                    {"id": spool["id"], "filamentName": spool.get("filamentName") or "", "netWeight": 0},
                )
            except (AuthExpired, BambuCloudError) as err:
                _LOGGER.warning("Could not mark removed spool %s as empty: %s", spool["id"], err)
                continue
            spool["netWeight"] = 0
            spool["depleted"] = True
            _LOGGER.info(
                "Spool %s %s %s was removed from %s with %s %% left (<= %s %%) - marked empty",
                spool.get("filamentVendor"), spool.get("filamentName"), spool.get("color"),
                tray.location, remain, pct,
            )

    # ------------------------------------------------------- usage booking

    async def _async_deduct_usage(self, data: dict[int, dict[str, Any]]) -> None:
        """Book finished cloud print jobs against mounted manual spools."""
        enabled = bool(self._opt(OPT_DEDUCT_USAGE, DEFAULT_DEDUCT_USAGE))
        await self.usage.async_set_enabled(enabled)
        if not enabled:
            return
        try:
            tasks = await self.hass.async_add_executor_job(self.client.get_tasks, 30)
        except (AuthExpired, BambuCloudError) as err:
            _LOGGER.debug("Usage booking: fetching print jobs failed: %s", err)
            return
        for task in self.usage.select_tasks(tasks):
            factor = 1.0
            if task.get("status") != 2:
                factor = self._cancelled_factor(task)
                if factor is None:
                    _LOGGER.info(
                        "Usage booking: skipped cancelled job %s (%s) - progress unknown",
                        task.get("id"), task.get("title"),
                    )
                    await self.usage.async_mark_done(task["id"])
                    continue
            booked = True
            for item in task.get("amsDetailMapping") or []:
                if not isinstance(item, dict):
                    continue
                try:
                    grams = float(item.get("weight") or 0) * factor
                except (TypeError, ValueError):
                    continue
                if grams <= 0:
                    continue
                position = slot_from_mapping(item)
                if position is None:
                    _LOGGER.debug("Usage booking: job %s entry without slot: %s", task.get("id"), item)
                    continue
                spool = find_mounted_manual_spool(data, task.get("deviceId"), *position)
                if spool is None:
                    _LOGGER.debug(
                        "Usage booking: no manual spool mounted for job %s at AMS %s slot %s",
                        task.get("id"), position[0], position[1] + 1,
                    )
                    continue
                fid_task, fid_spool = item.get("filamentId") or "", spool.get("filamentId") or ""
                if fid_task and fid_spool and fid_task != fid_spool:
                    _LOGGER.warning(
                        "Usage booking: job %s used %s in %s slot %s but the library has %s "
                        "(%s %s) there - not booked",
                        task.get("id"), fid_task, task.get("deviceName"), position[1] + 1,
                        fid_spool, spool.get("filamentVendor"), spool.get("filamentName"),
                    )
                    continue
                previous = (self.data or {}).get(spool["id"])
                if self.usage.foreign_change_detected(previous, spool, grams):
                    _LOGGER.info(
                        "Usage booking: spool %s already lost ~%s g since the last sync - "
                        "job %s not booked twice",
                        spool["id"], round(grams), task.get("id"),
                    )
                    continue
                new_net = max(0, int(round(float(spool.get("netWeight") or 0) - grams)))
                try:
                    await self.hass.async_add_executor_job(
                        self.client.update_spool,
                        {"id": spool["id"], "filamentName": spool.get("filamentName") or "", "netWeight": new_net},
                    )
                except (AuthExpired, BambuCloudError) as err:
                    _LOGGER.warning("Usage booking: cloud rejected update for spool %s: %s", spool["id"], err)
                    booked = False
                    continue
                _LOGGER.info(
                    "Usage booking: job %s (%s) used %s g of %s %s %s on %s - %s g -> %s g%s",
                    task.get("id"), task.get("title"), round(grams, 1),
                    spool.get("filamentVendor"), spool.get("filamentName"), spool.get("displayName") or spool.get("color"),
                    task.get("deviceName"), spool.get("netWeight"), new_net,
                    "" if factor == 1.0 else f" (cancelled at {int(factor * 100)} %)",
                )
                spool["netWeight"] = new_net
                if new_net == 0:
                    spool["depleted"] = True
            if booked:
                await self.usage.async_mark_done(task["id"])

    def _cancelled_factor(self, task: dict[str, Any]) -> float | None:
        """Share of a cancelled job that was printed, from the progress snapshot."""
        from .usage import parse_task_time

        ended = parse_task_time(task.get("endTime"))
        for serial, (progress, when) in self._last_progress.items():
            if task.get("deviceId") != serial:
                continue
            if ended is not None and abs((ended - when).total_seconds()) > 900:
                continue
            return max(0.0, min(1.0, progress / 100))
        return None

    async def _async_register_ams(
        self, data: dict[int, dict[str, Any]], trays: list[MountedTray]
    ) -> dict[int, dict[str, Any]]:
        """Create library entries for RFID spools that sit in an AMS but are unknown.

        Data comes from the Bambu Lab printer integration's slot sensors; the
        cloud RFID equals the tray uuid. Spools the user deleted while they
        were still loaded are remembered and left alone until unloaded.
        """
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
