"""Deduct print consumption from manually created (non-RFID) spools.

Nobody books consumption for third-party spools today - not Bambu Studio,
not Handy, not the cloud (verified 2026-09-03 against the Studio source and
a real print: a 64 g print left the mapped manual spool untouched). The cloud
does know the per-slot usage of every print job (`my/tasks` ->
`amsDetailMapping[]` with grams, amsId, slotId, filamentId), so this module
books each finished job exactly once against the manual spool the library
says is mounted in that slot.

Double-booking protection:
- every processed task id is persisted in HA storage (bookkept once, ever);
- only jobs finished AFTER the option was enabled are considered;
- RFID spools are never touched (the AMS reports their remaining weight);
- if a spool's weight already dropped by about the job's grams since the
  previous sync, someone else booked it and the job is skipped.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

TASK_FINISHED = 2
TASK_FAILED = 3  # also cancelled
MAX_DONE_IDS = 500
STORAGE_VERSION = 1


def parse_task_time(value: Any) -> datetime | None:
    """Cloud task times look like 2026-08-29T10:04:35Z."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def slot_from_mapping(item: dict[str, Any]) -> tuple[int, int] | None:
    """(amsId, slotId) of an amsDetailMapping entry.

    Verified live: the cloud fills `amsId`/`slotId` with 0 for every entry;
    the real position is the flat `ams` index Studio uses everywhere
    (unit * 4 + tray for regular units, 16-23 for AMS HT units 128+).
    """
    ams = item.get("ams")
    if isinstance(ams, bool) or not isinstance(ams, int):
        return None
    if 0 <= ams < 16:
        return ams // 4, ams % 4
    if 16 <= ams < 24:
        return 128 + (ams - 16), 0
    return None


def find_mounted_manual_spool(
    spools: dict[int, dict[str, Any]], dev_id: str, ams_id: Any, slot_id: Any
) -> dict[str, Any] | None:
    """The manual (no RFID) spool the library shows in this printer slot."""
    for spool in spools.values():
        if not spool.get("inPrinter") or spool.get("devId") != dev_id:
            continue
        if spool.get("RFID"):
            continue  # RFID spools get their weight from the AMS
        if str(spool.get("amsId")) != str(ams_id) or str(spool.get("slotId")) != str(slot_id):
            continue
        return spool
    return None


class UsageDeductor:
    """Books finished print jobs against manual spools, once each."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.usage_{entry_id}"
        )
        self._done: list[int] = []
        self._since: datetime | None = None
        self._loaded = False

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self._done = [i for i in data.get("done", []) if isinstance(i, int)]
        self._since = parse_task_time(data.get("since"))
        self._loaded = True

    async def _async_save(self) -> None:
        await self._store.async_save(
            {
                "done": self._done[-MAX_DONE_IDS:],
                "since": self._since.isoformat() if self._since else None,
            }
        )

    async def async_set_enabled(self, enabled: bool) -> None:
        """Start the booking window when enabled; forget it when disabled.

        Re-enabling later starts a fresh window, so old jobs are never booked
        retroactively (that would drive pre-existing spools into the red).
        """
        if not self._loaded:
            await self.async_load()
        if enabled and self._since is None:
            self._since = dt_util.utcnow()
            await self._async_save()
        elif not enabled and self._since is not None:
            self._since = None
            await self._async_save()

    def select_tasks(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Finished/cancelled jobs inside the window that were not booked yet."""
        if self._since is None:
            return []
        selected = []
        for task in tasks:
            tid = task.get("id")
            if not isinstance(tid, int) or tid in self._done:
                continue
            if task.get("status") not in (TASK_FINISHED, TASK_FAILED):
                continue
            ended = parse_task_time(task.get("endTime"))
            if ended is None or ended <= self._since:
                continue
            selected.append(task)
        return selected

    async def async_mark_done(self, task_id: int) -> None:
        if task_id not in self._done:
            self._done.append(task_id)
            self._done = self._done[-MAX_DONE_IDS:]
            await self._async_save()

    @staticmethod
    def foreign_change_detected(
        previous: dict[str, Any] | None, current: dict[str, Any], grams: float
    ) -> bool:
        """True when the spool already lost about `grams` since the last sync."""
        if previous is None or grams <= 0:
            return False
        try:
            drop = float(previous.get("netWeight") or 0) - float(current.get("netWeight") or 0)
        except (TypeError, ValueError):
            return False
        return drop > 0 and abs(drop - grams) <= max(3.0, grams * 0.15)
