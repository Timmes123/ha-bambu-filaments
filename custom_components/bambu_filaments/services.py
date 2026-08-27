"""Write actions for Bambu Filaments (verified against the cloud API)."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .api import BambuCloudError
from .const import DOMAIN, SERVICE_REFRESH
from .coordinator import BambuFilamentsCoordinator

SERVICE_SET_REMAINING = "set_remaining"
SERVICE_SET_NOTE = "set_note"

SET_REMAINING_SCHEMA = vol.Schema(
    {
        vol.Required("spool_id"): cv.positive_int,
        vol.Required("remaining_g"): vol.All(vol.Coerce(int), vol.Range(min=0, max=20000)),
    }
)
SET_NOTE_SCHEMA = vol.Schema(
    {
        vol.Required("spool_id"): cv.positive_int,
        vol.Required("note"): cv.string,
    }
)


def _find_spool(
    hass: HomeAssistant, spool_id: int
) -> tuple[BambuFilamentsCoordinator, dict[str, Any]]:
    for entry in hass.config_entries.async_entries(DOMAIN):
        coordinator = getattr(entry, "runtime_data", None)
        if isinstance(coordinator, BambuFilamentsCoordinator):
            if spool := (coordinator.data or {}).get(spool_id):
                return coordinator, spool
    raise HomeAssistantError(f"Spool {spool_id} not found in any filament library")


async def _update_fields(hass: HomeAssistant, spool_id: int, fields: dict[str, Any]) -> None:
    """PUT the full spool object back with the given fields changed."""
    coordinator, spool = _find_spool(hass, spool_id)
    payload = {**spool, **fields}
    try:
        await hass.async_add_executor_job(coordinator.client.update_spool, payload)
    except BambuCloudError as err:
        raise HomeAssistantError(f"Bambu cloud rejected the update: {err}") from err
    await coordinator.async_request_refresh()


def async_register_services(hass: HomeAssistant) -> None:
    """Register domain-level services (idempotent)."""

    async def handle_refresh(call: ServiceCall) -> None:
        for entry in hass.config_entries.async_entries(DOMAIN):
            coordinator = getattr(entry, "runtime_data", None)
            if isinstance(coordinator, BambuFilamentsCoordinator):
                await coordinator.async_request_refresh()

    async def handle_set_remaining(call: ServiceCall) -> None:
        await _update_fields(
            hass, call.data["spool_id"], {"netWeight": call.data["remaining_g"]}
        )

    async def handle_set_note(call: ServiceCall) -> None:
        await _update_fields(hass, call.data["spool_id"], {"note": call.data["note"]})

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, handle_refresh)
    hass.services.async_register(
        DOMAIN, SERVICE_SET_REMAINING, handle_set_remaining, schema=SET_REMAINING_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_NOTE, handle_set_note, schema=SET_NOTE_SCHEMA
    )
