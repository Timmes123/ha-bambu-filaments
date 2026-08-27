"""Data update coordinator for Bambu Filaments."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AuthExpired, BambuCloudClient, BambuCloudError
from .colors import BambuColorDB
from .const import DEFAULT_SCAN_INTERVAL_MIN, DOMAIN, OPT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


def spool_is_active(spool: dict[str, Any]) -> bool:
    """A spool counts as active while the cloud reports status 0."""
    return spool.get("status", 0) == 0


def spool_remaining_pct(spool: dict[str, Any]) -> int:
    """Derive remaining percent; the cloud only stores gram values."""
    net = spool.get("netWeight") or 0
    total = spool.get("totalNetWeight") or 0
    if not isinstance(net, (int, float)) or not isinstance(total, (int, float)) or total <= 0:
        return 0
    return max(0, min(100, round(net / total * 100)))


class BambuFilamentsCoordinator(DataUpdateCoordinator[dict[int, dict[str, Any]]]):
    """Polls the cloud filament inventory. Data is a dict keyed by spool id."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: BambuCloudClient,
        colordb: BambuColorDB,
    ) -> None:
        minutes = entry.options.get(OPT_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MIN)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(minutes=minutes),
        )
        self.client = client
        self.colordb = colordb

    def color_lookup(self, spool: dict[str, Any]) -> tuple[str | None, str | None]:
        """Localized official color name + Bambu color code for a spool."""
        colors = [c for c in (spool.get("colors") or [spool.get("color")]) if c]
        return self.colordb.lookup(
            spool.get("filamentId"), colors, self.hass.config.language
        )

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        try:
            spools = await self.hass.async_add_executor_job(self.client.get_spools)
        except AuthExpired as err:
            raise ConfigEntryAuthFailed(
                "Bambu cloud token expired - re-authentication required"
            ) from err
        except BambuCloudError as err:
            raise UpdateFailed(str(err)) from err
        return {s["id"]: s for s in spools if isinstance(s.get("id"), int)}
