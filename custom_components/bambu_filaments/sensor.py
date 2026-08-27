"""Sensors for the Bambu Filaments integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfMass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BambuFilamentsConfigEntry
from .const import (
    DEFAULT_INCLUDE_INACTIVE,
    DEFAULT_SPOOL_ENTITIES,
    DOMAIN,
    OPT_INCLUDE_INACTIVE,
    OPT_SPOOL_ENTITIES,
)
from .coordinator import BambuFilamentsCoordinator, spool_is_active, spool_remaining_pct


def _spool_attributes(spool: dict[str, Any]) -> dict[str, Any]:
    return {
        "spool_id": spool.get("id"),
        "vendor": spool.get("filamentVendor"),
        "material": spool.get("filamentType"),
        "name": spool.get("filamentName"),
        "filament_id": spool.get("filamentId"),
        "color": spool.get("color"),
        "colors": spool.get("colors"),
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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BambuFilamentsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up aggregate sensors and dynamically managed per-spool sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [SpoolCountSensor(coordinator, entry), TotalRemainingSensor(coordinator, entry)]
    )

    if not entry.options.get(OPT_SPOOL_ENTITIES, DEFAULT_SPOOL_ENTITIES):
        _remove_stale_spool_entities(hass, entry, keep=set())
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
            async_add_entities(SpoolSensor(coordinator, entry, sid) for sid in new)
            known.update(new)
        if gone := known - wanted:
            _remove_stale_spool_entities(hass, entry, keep=wanted)
            known.difference_update(gone)

    _sync_spools()
    entry.async_on_unload(coordinator.async_add_listener(_sync_spools))


def _remove_stale_spool_entities(
    hass: HomeAssistant, entry: BambuFilamentsConfigEntry, keep: set[int]
) -> None:
    """Drop registry entries of per-spool sensors that should no longer exist."""
    registry = er.async_get(hass)
    for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        unique_id = reg_entry.unique_id
        if not unique_id.startswith(f"{entry.entry_id}-spool-"):
            continue
        try:
            sid = int(unique_id.rsplit("-", 1)[1])
        except ValueError:
            continue
        if sid not in keep:
            registry.async_remove(reg_entry.entity_id)


class BambuFilamentsEntity(CoordinatorEntity[BambuFilamentsCoordinator]):
    """Base entity bound to the account-level Filament Library device."""

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
            "spools": [_spool_attributes(s) for s in spools],
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
        self._attr_unique_id = f"{entry.entry_id}-total-remaining"

    @property
    def native_value(self) -> int:
        return sum(s.get("netWeight") or 0 for s in self._spools(active_only=True))


class SpoolSensor(BambuFilamentsEntity, SensorEntity):
    """One physical spool from the cloud library; state is remaining percent."""

    _attr_icon = "mdi:printer-3d-nozzle"
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator, entry, spool_id: int) -> None:
        super().__init__(coordinator, entry)
        self._spool_id = spool_id
        self._attr_unique_id = f"{entry.entry_id}-spool-{spool_id}"

    @property
    def _spool(self) -> dict[str, Any] | None:
        return (self.coordinator.data or {}).get(self._spool_id)

    @property
    def available(self) -> bool:
        return super().available and self._spool is not None

    @property
    def name(self) -> str:
        if spool := self._spool:
            return f"{spool.get('filamentName') or 'Spool'} #{self._spool_id}"
        return f"Spool #{self._spool_id}"

    @property
    def native_value(self) -> int | None:
        if spool := self._spool:
            return spool_remaining_pct(spool)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if spool := self._spool:
            return _spool_attributes(spool)
        return {}
