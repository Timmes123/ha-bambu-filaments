"""Per-spool delete button: removes the spool from the Bambu cloud library.

The cloud stays the single source of truth - pressing the button deletes the
spool there, and the follow-up refresh removes the HA device via the normal
sync path.
"""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BambuFilamentsConfigEntry
from .api import AuthExpired, BambuCloudError
from .coordinator import BambuFilamentsCoordinator
from .entity import async_setup_spool_platform, spool_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BambuFilamentsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one delete button per spool device (follows the sensor option)."""
    async_setup_spool_platform(
        hass,
        entry,
        async_add_entities,
        lambda coord, ent, sid: [SpoolDeleteButton(coord, ent, sid)],
    )


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
        self._attr_device_info = spool_device_info(coordinator, entry, spool_id)

    @property
    def available(self) -> bool:
        return super().available and self._spool_id in (self.coordinator.data or {})

    async def async_press(self) -> None:
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.client.delete_spools, [self._spool_id]
            )
        except AuthExpired as err:
            self.coordinator.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                "Bambu cloud token expired - re-authentication started"
            ) from err
        except BambuCloudError as err:
            raise HomeAssistantError(f"Deleting the spool failed: {err}") from err
        await self.coordinator.async_request_refresh()
