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
from homeassistant.util import dt as dt_util

from .api import AuthExpired, BambuCloudError
from .colors import compact_hex
from .const import DOMAIN, SERVICE_REFRESH
from .coordinator import BambuFilamentsCoordinator

SERVICE_SET_REMAINING = "set_remaining"
SERVICE_SET_NOTE = "set_note"
SERVICE_SET_FILAMENT_ID = "set_filament_id"
SERVICE_UPDATE_SPOOL = "update_spool"
SERVICE_CREATE_SPOOL = "create_spool"
SERVICE_DELETE_SPOOL = "delete_spool"
SERVICE_GET_CATALOG = "get_catalog"
SERVICE_GET_SHOP_RANGE = "get_shop_range"
SERVICE_REFRESH_SHOP = "refresh_shop"
REFRESH_SHOP_SCHEMA = vol.Schema(
    {vol.Optional("products", default=[]): vol.All(cv.ensure_list, [cv.string])}
)

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
        # material/name/color are required unless color_code names an official
        # Bambu filament (checked in the handler).
        vol.Optional("material"): cv.string,
        vol.Optional("name"): cv.string,
        vol.Optional("color"): COLOR_SCHEMA,
        # 5-digit code on the Bambu box ("13504"): fills vendor, product,
        # slicer profile and color from the official color database.
        vol.Optional("color_code"): vol.All(cv.string, vol.Match(r"^\s*\d{5}\s*$")),
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
        data = dict(call.data)
        extra_colors: list[str] = []
        if code := (data.get("color_code") or "").strip():
            official = coordinator.colordb.by_code(code, coordinator.color_language)
            if official is None:
                raise HomeAssistantError(
                    f"Unknown Bambu color code {code} (not in the official color database)"
                )
            try:
                catalog = await coordinator.async_get_catalog()
            except BambuCloudError:
                catalog = []
            entry = next(
                (
                    c
                    for c in catalog
                    if c.get("filament_id") == official["filament_id"]
                    and c.get("vendor") == "Bambu Lab"
                ),
                None,
            ) or next(
                (c for c in catalog if c.get("filament_id") == official["filament_id"]),
                None,
            )
            # Not in the create catalog (new product line): the cloud stores
            # free text, so fall back to the database's product name.
            product = official["product"]
            data["vendor"] = (entry or {}).get("vendor") or "Bambu Lab"
            data["name"] = (entry or {}).get("name") or product
            data["material"] = (entry or {}).get("material") or product.split(" ")[0]
            data["filament_id"] = official["filament_id"]
            data["color"] = official["colors"][0]
            if len(official["colors"]) > 1:
                extra_colors = official["colors"]
        elif not all(data.get(key) for key in ("material", "name", "color")):
            raise HomeAssistantError(
                "create_spool needs material, name and color - or a Bambu color_code"
            )
        # The create endpoint takes #RRGGBB like Studio; a transparent color
        # keeps its alpha (#00000000 = Natural support, verified 2026-11-24 -
        # without it the spool becomes Black);
        # manual entries omit RFID/trayIdName/rolls, and there is no `colors`,
        # `note` or `status` field in the create body.
        payload: dict[str, Any] = {
            "createType": "manual",
            "filamentVendor": data["vendor"],
            "filamentType": data["material"],
            "filamentName": data["name"],
            "color": compact_hex(data["color"]),
            "colorType": 2,
            "isSupport": False,
            "netWeight": data.get("remaining_g", total),
            "totalNetWeight": total,
        }
        filament_id = data.get("filament_id")
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
        note = call.data.get("note")
        if note or extra_colors:
            # The create endpoint 400s on a note or colors field, so the note
            # (and the full color list of a multi-color spool) is written with
            # a follow-up PUT onto the just-created spool(s): re-fetch and
            # take the newest matching ids we did not know before.
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
                        "Spool was created but not found on re-fetch; note/colors not set"
                    )
                for target in created:
                    update: dict[str, Any] = {
                        "id": target["id"],
                        "filamentName": target.get("filamentName") or "",
                    }
                    if note:
                        update["note"] = note
                    if extra_colors:
                        update["colors"] = extra_colors
                    await hass.async_add_executor_job(
                        coordinator.client.update_spool, update
                    )
            except BambuCloudError as err:
                _LOGGER.warning(
                    "Spool was created but setting its note/colors failed: %s", err
                )
        await coordinator.async_request_refresh()

    async def handle_update_spool(call: ServiceCall) -> None:
        fields: dict[str, Any] = {
            cloud_key: call.data[key]
            for key, cloud_key in UPDATE_FIELD_MAP.items()
            if key in call.data
        }
        if "color" in call.data:
            color = compact_hex(call.data["color"])
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
        """Canonical vendor/product combos the cloud accepts (cached 1 h).

        `presets` lists the account's own slicer presets (filament_id only,
        e.g. "P1a2b3c4"): valid as a spool's slicer profile, but not as an
        official vendor/product combination.
        """
        coordinator = _first_coordinator(hass)
        try:
            filaments = await coordinator.async_get_catalog()
        except BambuCloudError as err:
            raise HomeAssistantError(f"Fetching the filament catalog failed: {err}") from err
        try:
            presets = await coordinator.async_get_user_presets()
        except BambuCloudError:
            presets = []
        # Official color codes (5 digits, printed on the box) so the card can
        # fill product and color from the code alone.
        colors = coordinator.colordb.codes(coordinator.color_language)
        return {"filaments": filaments, "presets": presets, "colors": colors}

    async def handle_get_shop_range(call: ServiceCall) -> dict[str, Any]:
        """Colors the Bambu shop sells right now (for the missing-colors card),
        plus a photo per color code (for cards with shop photos on).

        Ownership is computed by the card from the live spool list, so this
        response only changes when the daily shop snapshot does.
        """
        coordinator = _first_coordinator(hass)
        shop = coordinator.shop
        if shop is None:
            return {
                "enabled": False,
                "fetched_at": None,
                "shop_url": None,
                "colors": [],
                "images": {},
                "refreshing": False,
                "product_fetched": {},
            }
        fetched = shop.fetched_at
        iso = lambda ts: dt_util.utc_from_timestamp(ts).isoformat() if ts else None  # noqa: E731
        return {
            "enabled": True,
            "fetched_at": iso(fetched),
            "shop_url": shop.shop_url,
            "colors": shop.range_entries(coordinator.colordb, coordinator.color_language),
            "images": shop.images(),
            "refreshing": shop.refreshing,
            "product_fetched": {
                line: iso(ts) for line, ts in shop.product_fetched(coordinator.colordb).items()
            },
        }

    async def handle_refresh_shop(call: ServiceCall) -> dict[str, Any]:
        """Read the Bambu shop now - only the given product lines' pages when
        lines are given (missing-colors card button). Runs in the background;
        get_shop_range reports `refreshing` until it is done."""
        coordinator = _first_coordinator(hass)
        shop = coordinator.shop
        if shop is None:
            raise HomeAssistantError(
                "The shop comparison is off - turn on 'Compare with the current "
                "Bambu shop range' in the integration options"
            )
        started = shop.async_refresh_now(call.data["products"], coordinator.colordb)
        return {"started": started, "refreshing": shop.refreshing}

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, handle_refresh)
    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_SHOP,
        handle_refresh_shop,
        REFRESH_SHOP_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_SHOP_RANGE,
        handle_get_shop_range,
        supports_response=SupportsResponse.ONLY,
    )
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
