"""Auto-register RFID spools that sit in an AMS but are missing from the cloud library.

Bambu's own apps only register a freshly loaded official spool when someone
opens the printer page in Bambu Handy or Bambu Studio. This module closes that
gap using the AMS slot sensors of the *Bambu Lab* printer integration
(github.com/greghesp/ha-bambulab): every slot sensor carries the tray's
`tray_uuid`, which is exactly the `RFID` value the cloud library stores for
AMS-registered spools (verified live 2026-09-03).

Missing spools are pushed through `POST /my/filament/v2/ams/sync` - the same
call Bambu Studio makes after an AMS read. Verified live: the server creates
unknown RFIDs (`createdRFIDs` in the response), stores the mount position
(printer / AMS / slot, even the cloud-side printer name) and leaves every
other slot mapping alone. The plain create endpoint ignores position fields.

Nothing here talks to the printer - all data comes from Home Assistant's
state machine, so the feature is inert without the printer integration.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .colors import BambuColorDB, normalize_hex
from .const import AMS_TYPE_BY_MODEL, BAMBULAB_DOMAIN

_LOGGER = logging.getLogger(__name__)

BAMBULAB_REPO_URL = "https://github.com/greghesp/ha-bambulab"

# unique_id shape of ha-bambulab's AMS tray sensors (sensor.py):
#   {device_type}_{printer_serial}_AMS_{ams_serial}_tray_{1..4}
# External-spool holders have no RFID reader on current printers and the
# ams/sync endpoint needs an AMS serial, so those sensors are not considered.
_AMS_TRAY_RE = re.compile(r"^(?P<dev>[^_]+)_(?P<serial>[^_]+)_AMS_(?P<ams>[^_]+)_tray_(?P<n>\d+)$")
_AMS_DEVICE_INDEX_RE = re.compile(r"_AMS_(?P<n>\d+)$")
_HEX32_RE = re.compile(r"^[0-9A-F]{32}$")


def bambulab_available(hass: HomeAssistant) -> bool:
    """True when at least one Bambu Lab printer config entry is loaded."""
    return any(
        entry.state.name == "LOADED"
        for entry in hass.config_entries.async_entries(BAMBULAB_DOMAIN)
    )


_PRINT_STATUS_RE = re.compile(r"^(?P<serial>[^_]+)_print_status$")
_BUSY_STATES = {"running", "pause", "prepare", "slicing", "init"}


def _entity_by_unique_id(hass: HomeAssistant, unique_id: str) -> str | None:
    return er.async_get(hass).async_get_entity_id("sensor", BAMBULAB_DOMAIN, unique_id)


def printer_busy(hass: HomeAssistant, printer_serial: str) -> bool:
    """Printing/pausing/preparing - Studio applies its push cooldown only then."""
    entity_id = _entity_by_unique_id(hass, f"{printer_serial}_print_status")
    state = hass.states.get(entity_id) if entity_id else None
    return bool(state and state.state in _BUSY_STATES)


def printer_progress(hass: HomeAssistant, printer_serial: str) -> int | None:
    """Current print progress in percent, if the printer integration knows it."""
    entity_id = _entity_by_unique_id(hass, f"{printer_serial}_print_progress")
    state = hass.states.get(entity_id) if entity_id else None
    try:
        return int(float(state.state)) if state else None
    except (TypeError, ValueError):
        return None


def watched_entity_ids(hass: HomeAssistant) -> dict[str, tuple[str, str]]:
    """Bambu Lab entities worth reacting to: tray sensors + print status.

    Returns {entity_id: (printer_serial, kind)} with kind "tray" or "status".
    """
    found: dict[str, tuple[str, str]] = {}
    for entry in er.async_get(hass).entities.values():
        if entry.platform != BAMBULAB_DOMAIN or entry.domain != "sensor" or entry.disabled:
            continue
        uid = entry.unique_id or ""
        if m := _AMS_TRAY_RE.match(uid):
            found[entry.entity_id] = (m.group("serial"), "tray")
        elif m := _PRINT_STATUS_RE.match(uid):
            found[entry.entity_id] = (m.group("serial"), "status")
    return found


def _valid_uid(value: Any) -> bool:
    """Bambu's own rule (FilamentSpool::is_valid_tag_uid): non-empty, not all zeros."""
    return isinstance(value, str) and bool(value) and any(c != "0" for c in value)


@dataclass
class MountedTray:
    """One physical RFID spool currently sitting in an AMS slot."""

    entity_id: str
    tray_uuid: str
    filament_id: str
    tray_name: str
    material: str
    color: str
    tray_weight: int
    remain: int
    printer_serial: str
    printer_name: str
    ams_serial: str
    ams_model: str
    ams_id: int
    slot_id: str
    active: bool = False

    @property
    def location(self) -> str:
        return f"{self.printer_name} {self.ams_model or 'AMS'} slot {int(self.slot_id) + 1}"


def scan_mounted_rfid_trays(hass: HomeAssistant) -> list[MountedTray]:
    """Collect every AMS slot that holds an official RFID spool right now."""
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)
    trays: list[MountedTray] = []
    for entry in ent_reg.entities.values():
        if entry.platform != BAMBULAB_DOMAIN or entry.domain != "sensor" or entry.disabled:
            continue
        match = _AMS_TRAY_RE.match(entry.unique_id or "")
        if match is None:
            continue
        state = hass.states.get(entry.entity_id)
        if state is None or state.state in ("unavailable", "unknown"):
            continue
        attrs = state.attributes
        if attrs.get("empty") or attrs.get("unknown"):
            continue
        tray_uuid = str(attrs.get("tray_uuid") or "").upper()
        # Official spools carry both a 16-hex NFC tag id and a 32-hex cloud
        # uuid; third-party spools report all zeros for both.
        if not _HEX32_RE.match(tray_uuid) or not _valid_uid(tray_uuid):
            continue
        if not _valid_uid(attrs.get("tag_uid")):
            continue
        filament_id = str(attrs.get("filament_id") or "")
        if not filament_id:
            continue

        # The AMS index (cloud amsId) comes from ha-bambulab's device name:
        # regular units are named 1-based (AMS_1 -> 0), AMS HT keeps 128+.
        device = dev_reg.async_get(entry.device_id) if entry.device_id else None
        if device is None:
            continue
        index_match = _AMS_DEVICE_INDEX_RE.search(device.name or "")
        if index_match is None:
            _LOGGER.debug("Auto-register: cannot derive AMS index for %s", entry.entity_id)
            continue
        n = int(index_match.group("n"))
        ams_id = n - 1 if n < 128 else n
        printer_name = match.group("dev")
        printer_dev = dev_reg.async_get(device.via_device_id) if device.via_device_id else None
        if printer_dev is not None:
            printer_name = printer_dev.name_by_user or printer_dev.name or printer_name
        try:
            tray_weight = int(float(attrs.get("tray_weight") or 0))
        except (TypeError, ValueError):
            tray_weight = 0
        try:
            remain = int(attrs.get("remain", -1))
        except (TypeError, ValueError):
            remain = -1
        try:
            slot_id = str(max(0, int(attrs.get("slot") or match.group("n")) - 1))
        except (TypeError, ValueError):
            slot_id = str(int(match.group("n")) - 1)
        trays.append(
            MountedTray(
                entity_id=entry.entity_id,
                tray_uuid=tray_uuid,
                filament_id=filament_id,
                tray_name=str(attrs.get("name") or ""),
                material=str(attrs.get("type") or ""),
                color=str(attrs.get("color") or ""),
                tray_weight=tray_weight,
                remain=remain,
                printer_serial=match.group("serial"),
                printer_name=printer_name,
                ams_serial=match.group("ams"),
                ams_model=device.model or "",
                ams_id=ams_id,
                slot_id=slot_id,
                active=bool(attrs.get("active")),
            )
        )
    return trays


def build_ams_sync_item(
    tray: MountedTray, catalog: list[dict[str, Any]], colordb: BambuColorDB
) -> dict[str, Any]:
    """One `items[]` entry for ams/sync, mirroring Studio's AmsSyncItem.

    Field set verified live (2026-09-03): the server insists on `isSupport`
    and happily creates the spool with mount position from this shape.
    """
    entry = next((c for c in catalog if c.get("filament_id") == tray.filament_id), None)
    if entry is not None:
        vendor = entry.get("vendor") or "Bambu Lab"
        material = entry.get("material") or tray.material
        name = entry.get("name") or tray.material
    else:
        vendor = "Bambu Lab"
        material = tray.material
        name = re.sub(r"^Bambu\s+", "", tray.tray_name).strip() or material
    total = tray.tray_weight if tray.tray_weight > 0 else 1000
    net = total if tray.remain < 0 else max(0, min(total, round(total * tray.remain / 100)))
    color8 = normalize_hex(tray.color)
    color6 = color8[:7] or "#FFFFFF"
    item: dict[str, Any] = {
        "RFID": tray.tray_uuid,
        "createType": "ams",
        "filamentVendor": vendor,
        "filamentType": material,
        "filamentName": name,
        "filamentId": tray.filament_id,
        "isSupport": "support" in name.lower() or material.upper().endswith("-S"),
        "color": color6,
        "colorType": 2,
        "colors": [color8 or color6],
        "rolls": 1,
        "netWeight": net,
        "totalNetWeight": total,
        "note": "",
        "amsSn": tray.ams_serial,
        "slotId": tray.slot_id,
        "amsId": tray.ams_id,
        "amsType": AMS_TYPE_BY_MODEL.get(tray.ams_model, 0),
    }
    # Studio derives trayIdName as "<filamentId minus GF prefix>-<color code>"
    # from the official color database (e.g. GFG00 + dark green -> "G00-G01").
    tray_code = colordb.tray_code(tray.filament_id, [tray.color]) if tray.color else None
    if tray_code and len(tray.filament_id) > 2:
        item["trayIdName"] = f"{tray.filament_id[2:]}-{tray_code}"
    return item
