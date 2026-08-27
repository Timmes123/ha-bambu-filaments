"""Diagnostics for Bambu Filaments. Tokens, RFIDs and device ids are redacted."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import BambuFilamentsConfigEntry
from .const import CONF_TOKEN

REDACT_ENTRY = {CONF_TOKEN, "email"}
REDACT_SPOOL = {"RFID", "devId", "amsSn", "slotId", "deviceName", "trayIdName", "amsId"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: BambuFilamentsConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(dict(entry.data), REDACT_ENTRY),
        "options": dict(entry.options),
        "spools": [
            async_redact_data(spool, REDACT_SPOOL)
            for spool in (coordinator.data or {}).values()
        ],
    }
