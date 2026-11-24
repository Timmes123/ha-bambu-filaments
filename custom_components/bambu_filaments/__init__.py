"""The Bambu Filaments integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.loader import async_get_integration

from .api import BambuCloudClient
from .colors import BambuColorDB
from .const import (
    CONF_REGION,
    CONF_TOKEN,
    DEFAULT_SHARE_PAGE,
    DEFAULT_SHOP_SYNC,
    DOMAIN,
    OPT_SHARE_PAGE,
    OPT_SHOP_SYNC,
)
from .coordinator import BambuFilamentsCoordinator
from .frontend import async_setup_frontend
from .services import async_register_services
from .share import BambuShareView, ShareLink
from .shop import BambuShopRange

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS = [Platform.BUTTON, Platform.SENSOR]

type BambuFilamentsConfigEntry = ConfigEntry[BambuFilamentsCoordinator]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register domain-level services."""
    async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: BambuFilamentsConfigEntry) -> bool:
    """Set up a Bambu account from a config entry."""
    # Register the card once per HA run - re-registering the static path on
    # every entry reload would accumulate duplicate routes.
    domain_data = hass.data.setdefault(DOMAIN, {})
    integration = await async_get_integration(hass, DOMAIN)
    # Exposed as a sensor attribute so the card can detect a stale, cached
    # copy of itself after an update (browser tabs survive a HA restart).
    domain_data["version"] = str(integration.version)
    if not domain_data.get("frontend_registered"):
        await async_setup_frontend(hass, str(integration.version))
        domain_data["frontend_registered"] = True

    client = BambuCloudClient(entry.data[CONF_REGION], entry.data[CONF_TOKEN])
    colordb = BambuColorDB(hass)
    await colordb.async_load()
    coordinator = BambuFilamentsCoordinator(hass, entry, client, colordb)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    # Create the hub device before the platforms run; per-spool devices link
    # to it by registry id (via_device_id - the identifier-based via_device is
    # deprecated since HA 2026.8 and removed in 2027.8).
    hub = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name="Bambu Filament Library",
        manufacturer="Bambu Lab",
        model="Filament Manager",
    )
    coordinator.hub_device_id = hub.id

    await _async_setup_shop_and_share(hass, entry, coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_setup_shop_and_share(
    hass: HomeAssistant,
    entry: BambuFilamentsConfigEntry,
    coordinator: BambuFilamentsCoordinator,
) -> None:
    """Shop-range snapshot (shared by all entries) and the public share page."""
    domain_data = hass.data[DOMAIN]
    if entry.options.get(OPT_SHOP_SYNC, DEFAULT_SHOP_SYNC):
        shop = domain_data.get("shop")
        if shop is None:
            shop = domain_data["shop"] = BambuShopRange(hass)
        await shop.async_load()
        coordinator.shop = shop
        # Delayed first check: setup (and HA start) must not wait for or
        # compete with a few minutes of shop page reads.
        entry.async_on_unload(
            async_call_later(hass, 60, callback(lambda _now: shop.async_schedule_refresh()))
        )
        entry.async_on_unload(
            async_track_time_interval(
                hass,
                callback(lambda _now: shop.async_schedule_refresh()),
                timedelta(hours=1),
            )
        )
    if entry.options.get(OPT_SHARE_PAGE, DEFAULT_SHARE_PAGE):
        share = ShareLink(hass, entry.entry_id)
        await share.async_load()
        coordinator.share = share
        if not domain_data.get("share_view_registered"):
            hass.http.register_view(BambuShareView(hass))
            domain_data["share_view_registered"] = True


async def _async_update_listener(hass: HomeAssistant, entry: BambuFilamentsConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: BambuFilamentsConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
