"""Write actions for Bambu Filaments (verified against the cloud API)."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .api import BambuCloudError
from .colors import normalize_hex
from .const import DOMAIN, SERVICE_REFRESH
from .coordinator import BambuFilamentsCoordinator

SERVICE_SET_REMAINING = "set_remaining"
SERVICE_SET_NOTE = "set_note"
SERVICE_CREATE_SPOOL = "create_spool"
SERVICE_DELETE_SPOOL = "delete_spool"

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
CREATE_SPOOL_SCHEMA = vol.Schema(
    {
        vol.Optional("vendor", default="Bambu Lab"): cv.string,
        vol.Required("material"): cv.string,
        vol.Required("name"): cv.string,
        vol.Required("color"): cv.string,
        vol.Optional("total_g", default=1000): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=20000)
        ),
        vol.Optional("remaining_g"): vol.All(vol.Coerce(int), vol.Range(min=0, max=20000)),
        vol.Optional("filament_id"): cv.string,
    }
)
DELETE_SPOOL_SCHEMA = vol.Schema({vol.Required("spool_id"): cv.positive_int})


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

    def _first_coordinator() -> BambuFilamentsCoordinator:
        for entry in hass.config_entries.async_entries(DOMAIN):
            coordinator = getattr(entry, "runtime_data", None)
            if isinstance(coordinator, BambuFilamentsCoordinator):
                return coordinator
        raise HomeAssistantError("No Bambu Filaments account is set up")

    async def handle_create_spool(call: ServiceCall) -> None:
        coordinator = _first_coordinator()
        color = normalize_hex(call.data["color"])
        total = call.data["total_g"]
        payload: dict[str, Any] = {
            "createType": "manual",
            "filamentVendor": call.data["vendor"],
            "filamentType": call.data["material"],
            "filamentName": call.data["name"],
            "color": color,
            "colors": [color],
            "colorType": 2,
            "netWeight": call.data.get("remaining_g", total),
            "totalNetWeight": total,
            "note": "",
        }
        filament_id = call.data.get("filament_id")
        if not filament_id:
            # Best effort: resolve the canonical filamentId from the catalog.
            try:
                catalog = await hass.async_add_executor_job(
                    coordinator.client.get_catalog
                )
                for item in catalog.get("filamentSettings") or []:
                    if (
                        item.get("filamentVendor") == payload["filamentVendor"]
                        and item.get("filamentName") == payload["filamentName"]
                    ):
                        filament_id = item.get("filamentId")
                        break
            except BambuCloudError:
                filament_id = None
        if filament_id:
            payload["filamentId"] = filament_id
        try:
            await hass.async_add_executor_job(coordinator.client.create_spool, payload)
        except BambuCloudError as err:
            raise HomeAssistantError(f"Bambu cloud rejected the new spool: {err}") from err
        await coordinator.async_request_refresh()

    async def handle_delete_spool(call: ServiceCall) -> None:
        coordinator, _spool = _find_spool(hass, call.data["spool_id"])
        try:
            await hass.async_add_executor_job(
                coordinator.client.delete_spools, [call.data["spool_id"]]
            )
        except BambuCloudError as err:
            raise HomeAssistantError(f"Deleting the spool failed: {err}") from err
        await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, handle_refresh)
    hass.services.async_register(
        DOMAIN, SERVICE_SET_REMAINING, handle_set_remaining, schema=SET_REMAINING_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_NOTE, handle_set_note, schema=SET_NOTE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CREATE_SPOOL, handle_create_spool, schema=CREATE_SPOOL_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_DELETE_SPOOL, handle_delete_spool, schema=DELETE_SPOOL_SCHEMA
    )
