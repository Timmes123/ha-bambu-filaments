"""Shared helpers for the per-spool platforms (sensor, button).

One spool = one HA device. Both platforms register their entities through
async_setup_spool_platform, which owns the wanted-set diffing, device-level
cleanup of vanished spools, and keeping device names in sync with the cloud.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .colors import normalize_hex
from .const import (
    DEFAULT_INCLUDE_INACTIVE,
    DEFAULT_SPOOL_ENTITIES,
    DOMAIN,
    OPT_INCLUDE_INACTIVE,
    OPT_SPOOL_ENTITIES,
)
from .coordinator import BambuFilamentsCoordinator, spool_is_active

_DATE_RE = re.compile(r"\d{1,4}[./-]\d{1,2}[./-]\d{1,4}")
_TIME_RE = re.compile(r"\d{1,2}:\d{2}")

SpoolEntityFactory = Callable[
    [BambuFilamentsCoordinator, ConfigEntry, int], Iterable[Entity]
]


def clean_display_name(spool: dict[str, Any]) -> str | None:
    """The user-chosen spool name, or None.

    Bambu's apps sometimes auto-fill displayName with a localized creation
    stamp like "07/29/2026 10:03 hinzugefügt" (AMS bulk-add); Studio's own UI
    ignores the field entirely for such spools. Anything containing both a
    date and a time is treated as auto-generated, not a real name.
    """
    name = (spool.get("displayName") or "").strip()
    if not name or (_DATE_RE.search(name) and _TIME_RE.search(name)):
        return None
    return name


def spool_display_name(
    spool: dict[str, Any], coordinator: BambuFilamentsCoordinator
) -> str:
    """Device name: custom name, else product + official color, else hex."""
    if custom := clean_display_name(spool):
        return custom
    base = spool.get("filamentName") or spool.get("filamentType") or "Spool"
    color_name, _ = coordinator.color_lookup(spool)
    if color_name:
        return f"{base} {color_name}"
    if hex_color := normalize_hex(spool.get("color")):
        return f"{base} {hex_color[:7]}"
    return base


def spool_device_info(
    coordinator: BambuFilamentsCoordinator, entry: ConfigEntry, spool_id: int
) -> DeviceInfo:
    spool = (coordinator.data or {}).get(spool_id) or {}
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}-spool-{spool_id}")},
        via_device=(DOMAIN, entry.entry_id),
        name=spool_display_name(spool, coordinator),
        manufacturer=spool.get("filamentVendor") or "Bambu Lab",
        model=spool.get("filamentName") or spool.get("filamentType"),
        model_id=spool.get("filamentId"),
        serial_number=spool.get("trayIdName") or None,
    )


def sync_spool_devices(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: BambuFilamentsCoordinator,
    keep: set[int],
) -> None:
    """Device-level reconciliation against the cloud inventory.

    Removes spool devices no longer in `keep` (removing a device cascades to
    all its entities, regardless of platform or unique_id shape) and refreshes
    the default name of kept devices so renames in Studio/Handy propagate.
    The hub device's identifier has no "-spool-" prefix and is never touched.
    """
    dev_reg = dr.async_get(hass)
    prefix = f"{entry.entry_id}-spool-"
    data = coordinator.data or {}
    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        for domain, identifier in device.identifiers:
            if domain != DOMAIN or not identifier.startswith(prefix):
                continue
            try:
                sid = int(identifier.removeprefix(prefix))
            except ValueError:
                continue
            if sid not in keep:
                dev_reg.async_update_device(
                    device.id, remove_config_entry_id=entry.entry_id
                )
            elif sid in data:
                name = spool_display_name(data[sid], coordinator)
                if device.name != name:
                    dev_reg.async_update_device(device.id, name=name)


@callback
def async_setup_spool_platform(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    factory: SpoolEntityFactory,
) -> None:
    """Dynamically manage one platform's per-spool entities."""
    coordinator: BambuFilamentsCoordinator = entry.runtime_data
    if not entry.options.get(OPT_SPOOL_ENTITIES, DEFAULT_SPOOL_ENTITIES):
        sync_spool_devices(hass, entry, coordinator, keep=set())
        return

    include_inactive = entry.options.get(OPT_INCLUDE_INACTIVE, DEFAULT_INCLUDE_INACTIVE)
    known: set[int] = set()

    @callback
    def _sync() -> None:
        data = coordinator.data or {}
        wanted = {
            sid
            for sid, spool in data.items()
            if include_inactive or spool_is_active(spool)
        }
        if new := wanted - known:
            entities: list[Entity] = []
            for sid in new:
                entities.extend(factory(coordinator, entry, sid))
            async_add_entities(entities)
            known.update(new)
        known.intersection_update(wanted)
        # Unconditional: also prunes spools that vanished while HA was down
        # or were filtered out by an options change before this (re)load.
        sync_spool_devices(hass, entry, coordinator, keep=wanted)

    _sync()
    entry.async_on_unload(coordinator.async_add_listener(_sync))
