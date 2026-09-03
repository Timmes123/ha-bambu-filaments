"""Write actions for Bambu Filaments (verified against the cloud API)."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.service import async_register_admin_service

from .api import AuthExpired, BambuCloudError
from .colors import normalize_hex
from .const import DOMAIN, SERVICE_REFRESH
from .coordinator import BambuFilamentsCoordinator

SERVICE_SET_REMAINING = "set_remaining"
SERVICE_SET_NOTE = "set_note"
SERVICE_SET_FILAMENT_ID = "set_filament_id"
SERVICE_UPDATE_SPOOL = "update_spool"
SERVICE_CREATE_SPOOL = "create_spool"
SERVICE_DELETE_SPOOL = "delete_spool"
SERVICE_GET_CATALOG = "get_catalog"

_LOGGER = logging.getLogger(__name__)

# 6-digit hex, optionally with alpha and/or leading '#'.
COLOR_SCHEMA = vol.All(
    cv.string, vol.Match(r"^#?[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?$")
)

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
SET_FILAMENT_ID_SCHEMA = vol.Schema(
    {
        vol.Required("spool_id"): cv.positive_int,
        # Empty string is meaningful: it clears the profile (Studio's
        # "non-official spool" state), so no vol.Length guard here.
        vol.Required("filament_id"): cv.string,
    }
)
CREATE_SPOOL_SCHEMA = vol.Schema(
    {
        vol.Optional("vendor", default="Bambu Lab"): cv.string,
        vol.Required("material"): cv.string,
        vol.Required("name"): cv.string,
        vol.Required("color"): COLOR_SCHEMA,
        vol.Optional("total_g", default=1000): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=20000)
        ),
        vol.Optional("remaining_g"): vol.All(vol.Coerce(int), vol.Range(min=0, max=20000)),
        vol.Optional("filament_id"): cv.string,
        vol.Optional("display_name"): cv.string,
        vol.Optional("note"): cv.string,
        # Studio/Handy let you add N spools of one type in a single step
        # ("stock"); the cloud has no batch create, so this loops the POST.
        vol.Optional("count", default=1): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
    }
)
DELETE_SPOOL_SCHEMA = vol.Schema({vol.Required("spool_id"): cv.positive_int})
# Every field is optional (empty strings clear display_name/note/filament_id);
# the handler requires at least one field besides spool_id.
UPDATE_SPOOL_SCHEMA = vol.Schema(
    {
        vol.Required("spool_id"): cv.positive_int,
        vol.Optional("vendor"): vol.All(cv.string, vol.Length(min=1)),
        vol.Optional("material"): vol.All(cv.string, vol.Length(min=1)),
        vol.Optional("name"): vol.All(cv.string, vol.Length(min=1)),
        vol.Optional("color"): COLOR_SCHEMA,
        vol.Optional("total_g"): vol.All(vol.Coerce(int), vol.Range(min=1, max=20000)),
        vol.Optional("remaining_g"): vol.All(vol.Coerce(int), vol.Range(min=0, max=20000)),
        vol.Optional("note"): cv.string,
        vol.Optional("filament_id"): cv.string,
        vol.Optional("display_name"): cv.string,
    }
)
# service field -> cloud PUT field (verified live: all editable via minimal PUT)
UPDATE_FIELD_MAP = {
    "vendor": "filamentVendor",
    "material": "filamentType",
    "name": "filamentName",
    "total_g": "totalNetWeight",
    "remaining_g": "netWeight",
    "note": "note",
    "filament_id": "filamentId",
    "display_name": "displayName",
}


def _coordinators(hass: HomeAssistant) -> Iterable[BambuFilamentsCoordinator]:
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        coordinator = getattr(entry, "runtime_data", None)
        if isinstance(coordinator, BambuFilamentsCoordinator):
            yield coordinator


def _first_coordinator(hass: HomeAssistant) -> BambuFilamentsCoordinator:
    for coordinator in _coordinators(hass):
        return coordinator
    raise HomeAssistantError("No Bambu Filaments account is set up")


def _find_spool(
    hass: HomeAssistant, spool_id: int
) -> tuple[BambuFilamentsCoordinator, dict[str, Any]]:
    for coordinator in _coordinators(hass):
        if spool := (coordinator.data or {}).get(spool_id):
            return coordinator, spool
    raise HomeAssistantError(f"Spool {spool_id} not found in any filament library")


async def _cloud_write(
    hass: HomeAssistant,
    coordinator: BambuFilamentsCoordinator,
    func,
    *args,
    action: str,
) -> Any:
    """Run a blocking cloud write; token expiry starts the reauth flow."""
    try:
        return await hass.async_add_executor_job(func, *args)
    except AuthExpired as err:
        coordinator.config_entry.async_start_reauth(hass)
        raise HomeAssistantError(
            "Bambu cloud token expired - re-authentication started"
        ) from err
    except BambuCloudError as err:
        raise HomeAssistantError(f"{action}: {err}") from err


async def _update_fields(hass: HomeAssistant, spool_id: int, fields: dict[str, Any]) -> None:
    """PUT only the changed fields (plus the mandatory id + filamentName).

    A minimal body matches what Bambu Studio sends and avoids reverting
    concurrent cloud-side changes (e.g. AMS weight updates between polls)
    that a full read-modify-write of the cached spool would write back.
    """
    coordinator, spool = _find_spool(hass, spool_id)
    payload = {
        "id": spool["id"],
        "filamentName": spool.get("filamentName") or "",
        **fields,
    }
    await _cloud_write(
        hass,
        coordinator,
        coordinator.client.update_spool,
        payload,
        action="Bambu cloud rejected the update",
    )
    await coordinator.async_request_refresh()


def async_register_services(hass: HomeAssistant) -> None:
    """Register domain-level services (idempotent)."""

    async def handle_refresh(call: ServiceCall) -> None:
        for coordinator in _coordinators(hass):
            await coordinator.async_request_refresh()

    async def handle_set_remaining(call: ServiceCall) -> None:
        await _update_fields(
            hass, call.data["spool_id"], {"netWeight": call.data["remaining_g"]}
        )

    async def handle_set_note(call: ServiceCall) -> None:
        await _update_fields(hass, call.data["spool_id"], {"note": call.data["note"]})

    async def handle_set_filament_id(call: ServiceCall) -> None:
        # Verified live: a minimal PUT changes filamentId in place and leaves
        # vendor/material/displayName/color untouched, so an existing custom
        # spool can be linked to a Studio slicer profile retroactively.
        await _update_fields(
            hass,
            call.data["spool_id"],
            {"filamentId": call.data["filament_id"].strip()},
        )

    async def handle_create_spool(call: ServiceCall) -> None:
        coordinator = _first_coordinator(hass)
        total = call.data["total_g"]
        # The create endpoint expects #RRGGBB without alpha (Studio MITM shape);
        # manual entries omit RFID/trayIdName/rolls, and there is no `colors`,
        # `note` or `status` field in the create body.
        payload: dict[str, Any] = {
            "createType": "manual",
            "filamentVendor": call.data["vendor"],
            "filamentType": call.data["material"],
            "filamentName": call.data["name"],
            "color": normalize_hex(call.data["color"])[:7],
            "colorType": 2,
            "isSupport": False,
            "netWeight": call.data.get("remaining_g", total),
            "totalNetWeight": total,
        }
        filament_id = call.data.get("filament_id")
        if filament_id is None:
            # Best effort for official filaments: resolve the canonical id from
            # the catalog - exact name match first, then vendor + material.
            # An EXPLICIT empty string means "custom/non-official spool" and
            # deliberately skips this lookup.
            try:
                catalog = await coordinator.async_get_catalog()
            except BambuCloudError:
                catalog = []
            for item in catalog:
                if (
                    item["vendor"] == payload["filamentVendor"]
                    and item["name"] == payload["filamentName"]
                ):
                    filament_id = item["filament_id"]
                    break
            else:
                for item in catalog:
                    if (
                        item["vendor"] == payload["filamentVendor"]
                        and item["material"] == payload["filamentType"]
                    ):
                        filament_id = item["filament_id"]
                        break
        # The cloud requires the filamentId FIELD to be present (missing field
        # -> HTTP 400) but accepts an empty string for custom/third-party
        # brands - that is how Studio models "non-official" spools.
        payload["filamentId"] = filament_id or ""
        if display_name := call.data.get("display_name"):
            payload["displayName"] = display_name
        known_ids = set((coordinator.data or {}).keys())
        count = call.data["count"]
        created_n = 0
        try:
            for _ in range(count):
                await _cloud_write(
                    hass,
                    coordinator,
                    coordinator.client.create_spool,
                    payload,
                    action="Bambu cloud rejected the new spool",
                )
                created_n += 1
        except HomeAssistantError as err:
            if created_n == 0:
                raise
            # Partial batch: keep what was created, tell the caller how far
            # it got (the refresh below shows the spools that made it).
            await coordinator.async_request_refresh()
            raise HomeAssistantError(
                f"{err} (created {created_n} of {count} spools before the error)"
            ) from err
        if note := call.data.get("note"):
            # The create endpoint 400s on a note field, so the note is written
            # with a follow-up PUT onto the just-created spool(s): re-fetch
            # and take the newest matching ids we did not know before.
            try:
                spools = await hass.async_add_executor_job(coordinator.client.get_spools)
                created = sorted(
                    (
                        s
                        for s in spools
                        if isinstance(s.get("id"), int)
                        and s["id"] not in known_ids
                        and s.get("filamentVendor") == payload["filamentVendor"]
                        and s.get("filamentName") == payload["filamentName"]
                    ),
                    key=lambda s: s["id"],
                    reverse=True,
                )[:created_n]
                if not created:
                    _LOGGER.warning(
                        "Spool was created but not found on re-fetch; note not set"
                    )
                for target in created:
                    await hass.async_add_executor_job(
                        coordinator.client.update_spool,
                        {
                            "id": target["id"],
                            "filamentName": target.get("filamentName") or "",
                            "note": note,
                        },
                    )
            except BambuCloudError as err:
                _LOGGER.warning("Spool was created but setting its note failed: %s", err)
        await coordinator.async_request_refresh()

    async def handle_update_spool(call: ServiceCall) -> None:
        fields: dict[str, Any] = {
            cloud_key: call.data[key]
            for key, cloud_key in UPDATE_FIELD_MAP.items()
            if key in call.data
        }
        if "color" in call.data:
            color = normalize_hex(call.data["color"])[:7]
            # Also rewrite the colors array: the apps (and the card) display
            # `colors` over `color` when present, so updating only `color`
            # would leave the visible swatch unchanged. Verified: PUT accepts
            # `colors` (unlike create, which 400s on it).
            fields["color"] = color
            fields["colors"] = [color]
        if not fields:
            raise HomeAssistantError("update_spool needs at least one field to change")
        await _update_fields(hass, call.data["spool_id"], fields)

    async def handle_delete_spool(call: ServiceCall) -> None:
        coordinator, _spool = _find_spool(hass, call.data["spool_id"])
        await _cloud_write(
            hass,
            coordinator,
            coordinator.client.delete_spools,
            [call.data["spool_id"]],
            action="Deleting the spool failed",
        )
        await coordinator.async_request_refresh()

    async def handle_get_catalog(call: ServiceCall) -> dict[str, Any]:
        """Canonical vendor/product combos the cloud accepts (cached 1 h)."""
        coordinator = _first_coordinator(hass)
        try:
            return {"filaments": await coordinator.async_get_catalog()}
        except BambuCloudError as err:
            raise HomeAssistantError(f"Fetching the filament catalog failed: {err}") from err

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, handle_refresh)
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_CATALOG,
        handle_get_catalog,
        supports_response=SupportsResponse.ONLY,
    )
    # Cloud-write services are admin-only: they irreversibly modify the user's
    # Bambu account (automations without a user context are still allowed).
    async_register_admin_service(
        hass, DOMAIN, SERVICE_SET_REMAINING, handle_set_remaining, SET_REMAINING_SCHEMA
    )
    async_register_admin_service(
        hass, DOMAIN, SERVICE_SET_NOTE, handle_set_note, SET_NOTE_SCHEMA
    )
    async_register_admin_service(
        hass, DOMAIN, SERVICE_SET_FILAMENT_ID, handle_set_filament_id, SET_FILAMENT_ID_SCHEMA
    )
    async_register_admin_service(
        hass, DOMAIN, SERVICE_CREATE_SPOOL, handle_create_spool, CREATE_SPOOL_SCHEMA
    )
    async_register_admin_service(
        hass, DOMAIN, SERVICE_DELETE_SPOOL, handle_delete_spool, DELETE_SPOOL_SCHEMA
    )
    async_register_admin_service(
        hass, DOMAIN, SERVICE_UPDATE_SPOOL, handle_update_spool, UPDATE_SPOOL_SCHEMA
    )
