"""Sensors for the Bambu Filaments integration.

Model: one hub device per account ("Bambu Filament Library") carrying the
aggregate sensors, plus one device per spool (via_device -> hub) carrying a
remaining-% and a remaining-weight sensor.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfMass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BambuFilamentsConfigEntry
from .colors import normalize_hex
from .const import (
    DEFAULT_INCLUDE_INACTIVE,
    DEFAULT_SPOOL_ENTITIES,
    DOMAIN,
    OPT_INCLUDE_INACTIVE,
    OPT_SPOOL_ENTITIES,
)
from .coordinator import BambuFilamentsCoordinator, spool_is_active, spool_remaining_pct


def _spool_colors(spool: dict[str, Any]) -> list[str]:
    return [c for c in (spool.get("colors") or [spool.get("color")]) if c]


def _swatch_picture(colors: list[str]) -> str | None:
    """Small SVG color swatch as data URI, used as the entity picture."""
    normalized = [normalize_hex(c) for c in colors if c]
    if not normalized:
        return None
    if len(normalized) == 1:
        body = f"<circle cx='16' cy='16' r='14' fill='{normalized[0]}'/>"
    else:
        body = (
            f"<path d='M16 2 A14 14 0 0 0 16 30 Z' fill='{normalized[0]}'/>"
            f"<path d='M16 2 A14 14 0 0 1 16 30 Z' fill='{normalized[1]}'/>"
        )
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
        f"{body}"
        "<circle cx='16' cy='16' r='14' fill='none' stroke='#7f8c8d' stroke-width='1.5'/>"
        "</svg>"
    )
    return f"data:image/svg+xml,{quote(svg)}"


def spool_attributes(
    spool: dict[str, Any], coordinator: BambuFilamentsCoordinator
) -> dict[str, Any]:
    color_name, color_code = coordinator.color_lookup(spool)
    return {
        "spool_id": spool.get("id"),
        "vendor": spool.get("filamentVendor"),
        "material": spool.get("filamentType"),
        "name": spool.get("filamentName"),
        "filament_id": spool.get("filamentId"),
        "color": spool.get("color"),
        "colors": spool.get("colors"),
        "color_name": color_name,
        "bambu_color_code": color_code,
        "remaining_g": spool.get("netWeight"),
        "total_g": spool.get("totalNetWeight"),
        "status": spool.get("status"),
        "note": spool.get("note"),
        "tray_id_name": spool.get("trayIdName"),
        "create_type": spool.get("createType"),
        "in_printer": spool.get("inPrinter"),
        "device_name": spool.get("deviceName"),
        "ams_id": spool.get("amsId"),
        "slot_id": spool.get("slotId"),
    }


def _spool_display_name(
    spool: dict[str, Any], coordinator: BambuFilamentsCoordinator
) -> str:
    base = spool.get("filamentName") or spool.get("filamentType") or "Spool"
    color_name, _ = coordinator.color_lookup(spool)
    if color_name:
        return f"{base} {color_name}"
    if hex_color := normalize_hex(spool.get("color")):
        return f"{base} {hex_color[:7]}"
    return base


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BambuFilamentsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up aggregate sensors and dynamically managed per-spool devices."""
    coordinator = entry.runtime_data
    async_add_entities(
        [SpoolCountSensor(coordinator, entry), TotalRemainingSensor(coordinator, entry)]
    )

    if not entry.options.get(OPT_SPOOL_ENTITIES, DEFAULT_SPOOL_ENTITIES):
        _remove_stale_spools(hass, entry, keep=set())
        return

    include_inactive = entry.options.get(OPT_INCLUDE_INACTIVE, DEFAULT_INCLUDE_INACTIVE)
    known: set[int] = set()

    @callback
    def _sync_spools() -> None:
        data = coordinator.data or {}
        wanted = {
            sid
            for sid, spool in data.items()
            if include_inactive or spool_is_active(spool)
        }
        if new := wanted - known:
            entities: list[SensorEntity] = []
            for sid in new:
                entities.append(SpoolRemainingSensor(coordinator, entry, sid))
                entities.append(SpoolWeightSensor(coordinator, entry, sid))
            async_add_entities(entities)
            known.update(new)
        if known - wanted:
            _remove_stale_spools(hass, entry, keep=wanted)
            known.intersection_update(wanted)

    _sync_spools()
    entry.async_on_unload(coordinator.async_add_listener(_sync_spools))


def _remove_stale_spools(
    hass: HomeAssistant, entry: BambuFilamentsConfigEntry, keep: set[int]
) -> None:
    """Drop registry entities and devices of spools that should no longer exist."""
    ent_reg = er.async_get(hass)
    prefix = f"{entry.entry_id}-spool-"
    for reg_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        unique_id = reg_entry.unique_id
        if not unique_id.startswith(prefix) or unique_id.endswith(("-count", "-remaining")):
            continue
        try:
            sid = int(unique_id.removeprefix(prefix).split("-")[0])
        except ValueError:
            continue
        if sid not in keep:
            ent_reg.async_remove(reg_entry.entity_id)
    dev_reg = dr.async_get(hass)
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


class BambuFilamentsEntity(CoordinatorEntity[BambuFilamentsCoordinator]):
    """Base entity bound to the account-level Filament Library hub device."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: BambuFilamentsCoordinator, entry: BambuFilamentsConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Bambu Filament Library",
            manufacturer="Bambu Lab",
            model="Filament Manager",
            configuration_url="https://bambulab.com",
        )

    def _spools(self, active_only: bool = False) -> list[dict[str, Any]]:
        spools = list((self.coordinator.data or {}).values())
        if active_only:
            spools = [s for s in spools if spool_is_active(s)]
        return spools


class SpoolCountSensor(BambuFilamentsEntity, SensorEntity):
    """Number of active spools; full inventory in the attributes."""

    _attr_translation_key = "spool_count"
    _attr_icon = "mdi:counter"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}-spool-count"

    @property
    def native_value(self) -> int:
        return len(self._spools(active_only=True))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        spools = self._spools()
        by_material: dict[str, int] = {}
        for spool in spools:
            if spool_is_active(spool):
                material = spool.get("filamentType") or "unknown"
                by_material[material] = by_material.get(material, 0) + (
                    spool.get("netWeight") or 0
                )
        return {
            "total_spools": len(spools),
            "remaining_g_by_material": by_material,
            "spools": [spool_attributes(s, self.coordinator) for s in spools],
        }


class TotalRemainingSensor(BambuFilamentsEntity, SensorEntity):
    """Total remaining filament weight across active spools."""

    _attr_translation_key = "total_remaining"
    _attr_icon = "mdi:weight-gram"
    _attr_native_unit_of_measurement = UnitOfMass.GRAMS
    _attr_device_class = SensorDeviceClass.WEIGHT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        # Must NOT start with "{entry_id}-spool-<int>" (stale-spool cleanup
        # prefix) and must keep the pre-v0.3.0 value for registry continuity.
        self._attr_unique_id = f"{entry.entry_id}-total-remaining"

    @property
    def native_value(self) -> int:
        return sum(s.get("netWeight") or 0 for s in self._spools(active_only=True))


class SpoolEntityBase(CoordinatorEntity[BambuFilamentsCoordinator], SensorEntity):
    """Base for per-spool sensors; each spool is its own HA device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BambuFilamentsCoordinator,
        entry: BambuFilamentsConfigEntry,
        spool_id: int,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._spool_id = spool_id
        spool = (coordinator.data or {}).get(spool_id) or {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}-spool-{spool_id}")},
            via_device=(DOMAIN, entry.entry_id),
            name=_spool_display_name(spool, coordinator),
            manufacturer=spool.get("filamentVendor") or "Bambu Lab",
            model=spool.get("filamentName") or spool.get("filamentType"),
            model_id=spool.get("filamentId"),
            serial_number=spool.get("trayIdName") or None,
        )

    @property
    def _spool(self) -> dict[str, Any] | None:
        return (self.coordinator.data or {}).get(self._spool_id)

    @property
    def available(self) -> bool:
        return super().available and self._spool is not None


class SpoolRemainingSensor(SpoolEntityBase):
    """Remaining percent of one spool, with the full details as attributes."""

    _attr_translation_key = "spool_remaining_pct"
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator, entry, spool_id: int) -> None:
        super().__init__(coordinator, entry, spool_id)
        # Keeps the unique_id of the former single per-spool sensor (< v0.3.0).
        self._attr_unique_id = f"{entry.entry_id}-spool-{spool_id}"

    @property
    def entity_picture(self) -> str | None:
        if spool := self._spool:
            return _swatch_picture(_spool_colors(spool))
        return None

    @property
    def native_value(self) -> int | None:
        if spool := self._spool:
            return spool_remaining_pct(spool)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if spool := self._spool:
            return spool_attributes(spool, self.coordinator)
        return {}


class SpoolWeightSensor(SpoolEntityBase):
    """Remaining filament weight of one spool in grams."""

    _attr_translation_key = "spool_remaining_g"
    _attr_native_unit_of_measurement = UnitOfMass.GRAMS
    _attr_device_class = SensorDeviceClass.WEIGHT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, spool_id: int) -> None:
        super().__init__(coordinator, entry, spool_id)
        self._attr_unique_id = f"{entry.entry_id}-spool-{spool_id}-weight"

    @property
    def native_value(self) -> int | None:
        if spool := self._spool:
            return spool.get("netWeight") or 0
        return None
