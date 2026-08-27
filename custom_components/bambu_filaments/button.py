"""Per-spool delete button: removes the spool from the Bambu cloud library.

The cloud stays the single source of truth - pressing the button deletes the
spool there, and the follow-up refresh removes the HA device via the normal
sync path.
"""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BambuFilamentsConfigEntry
from .api import BambuCloudError
from .const import (
    DEFAULT_INCLUDE_INACTIVE,
    DEFAULT_SPOOL_ENTITIES,
    DOMAIN,
    OPT_INCLUDE_INACTIVE,
    OPT_SPOOL_ENTITIES,
)
from .coordinator import BambuFilamentsCoordinator, spool_is_active
from .sensor import _spool_display_name


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BambuFilamentsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one delete button per spool device (follows the sensor option)."""
    if not entry.options.get(OPT_SPOOL_ENTITIES, DEFAULT_SPOOL_ENTITIES):
        return

    coordinator = entry.runtime_data
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
            async_add_entities(
                SpoolDeleteButton(coordinator, entry, sid) for sid in new
            )
            known.update(new)
        # Stale entity/device removal is handled centrally in sensor.py.
        known.intersection_update(wanted)

    _sync_spools()
    entry.async_on_unload(coordinator.async_add_listener(_sync_spools))


class SpoolDeleteButton(CoordinatorEntity[BambuFilamentsCoordinator], ButtonEntity):
    """Delete this spool from the Bambu cloud filament library."""

    _attr_has_entity_name = True
    _attr_translation_key = "delete_spool"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:delete-forever"

    def __init__(
        self,
        coordinator: BambuFilamentsCoordinator,
        entry: BambuFilamentsConfigEntry,
        spool_id: int,
    ) -> None:
        super().__init__(coordinator)
        self._spool_id = spool_id
        self._attr_unique_id = f"{entry.entry_id}-spool-{spool_id}-delete"
        spool = (coordinator.data or {}).get(spool_id) or {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}-spool-{spool_id}")},
            via_device=(DOMAIN, entry.entry_id),
            name=_spool_display_name(spool, coordinator),
        )

    @property
    def available(self) -> bool:
        return super().available and self._spool_id in (self.coordinator.data or {})

    async def async_press(self) -> None:
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.client.delete_spools, [self._spool_id]
            )
        except BambuCloudError as err:
            raise HomeAssistantError(f"Deleting the spool failed: {err}") from err
        await self.coordinator.async_request_refresh()
