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

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

TASK_FINISHED = 2
TASK_FAILED = 3  # also cancelled
MAX_DONE_IDS = 500
STORAGE_VERSION = 1
# A backup switch is matched to its job by time; clocks differ a little.
SWITCH_TIME_TOLERANCE = timedelta(minutes=2)
# Long prints run for days; a switch is kept until its job is booked.
SWITCH_MAX_AGE = timedelta(days=30)


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


@dataclass(frozen=True)
class BackupSwitch:
    """An AMS backup switch during a print, as seen on the tray sensors.

    The cloud job only knows the planned slot. When that slot runs out and
    the AMS continues from a backup slot with the same filament, the rest of
    the job comes from another spool - only the printer side shows that.
    """

    printer_serial: str
    from_pos: tuple[int, int]  # (amsId, slotId) that ran out
    to_pos: tuple[int, int]  # (amsId, slotId) that took over
    fraction: float  # print progress (0..1) when the backup slot took over
    when: datetime
    # Manual spool the library showed in the run-out slot at that moment
    # (Studio unbinds an emptied slot within seconds).
    spool_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "printer_serial": self.printer_serial,
            "from_pos": list(self.from_pos),
            "to_pos": list(self.to_pos),
            "fraction": self.fraction,
            "when": self.when.isoformat(),
            "spool_id": self.spool_id,
        }

    @classmethod
    def from_dict(cls, data: Any) -> BackupSwitch | None:
        try:
            when = datetime.fromisoformat(data["when"])
            if when.tzinfo is None:
                return None
            spool_id = data.get("spool_id")
            return cls(
                printer_serial=str(data["printer_serial"]),
                from_pos=_pos(data["from_pos"]),
                to_pos=_pos(data["to_pos"]),
                fraction=max(0.0, min(1.0, float(data["fraction"]))),
                when=when.astimezone(timezone.utc),
                spool_id=spool_id if isinstance(spool_id, int) else None,
            )
        except (AttributeError, KeyError, TypeError, ValueError):
            return None


@dataclass(frozen=True)
class PendingRunout:
    """The active slot of a running print reported empty; no backup slot yet."""

    pos: tuple[int, int]
    filament_id: str
    color: str
    spool_id: int | None
    when: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "pos": list(self.pos),
            "filament_id": self.filament_id,
            "color": self.color,
            "spool_id": self.spool_id,
            "when": self.when.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Any) -> PendingRunout | None:
        try:
            when = datetime.fromisoformat(data["when"])
            if when.tzinfo is None:
                return None
            spool_id = data.get("spool_id")
            return cls(
                pos=_pos(data["pos"]),
                filament_id=str(data.get("filament_id") or ""),
                color=str(data.get("color") or ""),
                spool_id=spool_id if isinstance(spool_id, int) else None,
                when=when.astimezone(timezone.utc),
            )
        except (AttributeError, KeyError, TypeError, ValueError):
            return None


def _pos(value: Any) -> tuple[int, int]:
    ams, slot = value
    return int(ams), int(slot)


def switches_for_task(
    task: dict[str, Any], switches: list[BackupSwitch]
) -> list[BackupSwitch]:
    """Backup switches that happened on the job's printer while it ran."""
    started = parse_task_time(task.get("startTime"))
    ended = parse_task_time(task.get("endTime"))
    if started is None or ended is None:
        return []
    return sorted(
        (
            sw
            for sw in switches
            if sw.printer_serial == task.get("deviceId")
            and started - SWITCH_TIME_TOLERANCE <= sw.when <= ended + SWITCH_TIME_TOLERANCE
        ),
        key=lambda sw: sw.when,
    )


def split_usage(
    position: tuple[int, int], printed: float, switches: list[BackupSwitch]
) -> list[tuple[tuple[int, int], float, int | None]]:
    """Split one job slot entry along the backup switches of that job.

    Returns [(slot position, share of the planned grams, fallback spool id)].
    `printed` is the share of the job that was printed at all (1.0 for a
    finished job). Without a matching switch the result is the single entry
    (position, printed, None). The progress is time based, so the shares
    are an estimate.
    """
    parts: list[tuple[tuple[int, int], float, int | None]] = []
    current, start = position, 0.0
    for sw in switches:
        if sw.from_pos != current or sw.to_pos == current:
            continue
        cut = min(max(sw.fraction, start), printed)
        if cut > start:
            parts.append((current, cut - start, sw.spool_id))
        current, start = sw.to_pos, cut
    if printed > start:
        parts.append((current, printed - start, None))
    return parts


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
        # AMS backup switches seen by the tray listener, kept until their
        # job is booked, and per printer the slot that ran empty and waits
        # for a backup slot to take over. Stored with the rest, so a Home
        # Assistant restart during a long print does not lose them.
        self.switches: list[BackupSwitch] = []
        self.pending: dict[str, PendingRunout] = {}
        # Parts of a job that are settled although the job is not done
        # yet (the cloud rejected another part): a retry skips them.
        self._partial: dict[int, list[str]] = {}

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self._done = [i for i in data.get("done", []) if isinstance(i, int)]
        self._since = parse_task_time(data.get("since"))
        stored = [BackupSwitch.from_dict(raw) for raw in data.get("switches") or []]
        self.switches = [sw for sw in stored if sw is not None] + self.switches
        pending = data.get("pending")
        for serial, raw in (pending.items() if isinstance(pending, dict) else ()):
            if (item := PendingRunout.from_dict(raw)) is not None:
                self.pending.setdefault(str(serial), item)
        partial = data.get("partial")
        for tid, keys in (partial.items() if isinstance(partial, dict) else ()):
            if str(tid).isdigit() and isinstance(keys, list):
                self._partial[int(tid)] = [str(k) for k in keys]
        self._loaded = True

    def _payload(self) -> dict[str, Any]:
        return {
            "done": self._done[-MAX_DONE_IDS:],
            "since": self._since.isoformat() if self._since else None,
            "switches": [sw.to_dict() for sw in self.switches],
            "pending": {serial: item.to_dict() for serial, item in self.pending.items()},
            "partial": {str(tid): keys for tid, keys in self._partial.items()},
        }

    async def _async_save(self) -> None:
        await self._store.async_save(self._payload())

    @callback
    def _save_soon(self) -> None:
        """Save from the (synchronous) tray listener."""
        self._store.async_delay_save(self._payload, 1)

    @callback
    def set_pending(self, serial: str, item: PendingRunout) -> None:
        self.pending[serial] = item
        self._save_soon()

    @callback
    def drop_pending(self, serial: str) -> None:
        if self.pending.pop(serial, None) is not None:
            self._save_soon()

    @callback
    def add_switch(self, switch: BackupSwitch) -> None:
        self.switches.append(switch)
        self._save_soon()

    def settled_parts(self, task_id: int) -> set[str]:
        """Parts of a not yet finished job that must not be booked again."""
        return set(self._partial.get(task_id, ()))

    async def async_set_settled_parts(self, task_id: int, keys: set[str]) -> None:
        if set(self._partial.get(task_id, ())) != keys:
            self._partial[task_id] = sorted(keys)
            await self._async_save()

    def forget_parts_except(self, task_ids: set[int]) -> None:
        """Drop part lists of jobs the cloud no longer returns (saved with the next write)."""
        self._partial = {tid: keys for tid, keys in self._partial.items() if tid in task_ids}

    async def async_prune(self, now: datetime) -> None:
        """Forget switches and open runouts no job can belong to any more."""
        oldest = now - SWITCH_MAX_AGE
        switches = [sw for sw in self.switches if sw.when >= oldest]
        pending = {s: p for s, p in self.pending.items() if p.when >= oldest}
        if len(switches) != len(self.switches) or len(pending) != len(self.pending):
            self.switches, self.pending = switches, pending
            await self._async_save()

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
        elif not enabled and (
            self._since is not None or self.switches or self.pending or self._partial
        ):
            self._since = None
            self.switches = []
            self.pending = {}
            self._partial = {}
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

    async def async_mark_done(
        self, task_id: int, used_switches: list[BackupSwitch] | None = None
    ) -> None:
        """Remember a processed job; its backup switches are used up with it."""
        changed = False
        if used_switches:
            kept = [sw for sw in self.switches if sw not in used_switches]
            changed = len(kept) != len(self.switches)
            self.switches = kept
        if self._partial.pop(task_id, None) is not None:
            changed = True
        if task_id not in self._done:
            self._done.append(task_id)
            self._done = self._done[-MAX_DONE_IDS:]
            changed = True
        if changed:
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
