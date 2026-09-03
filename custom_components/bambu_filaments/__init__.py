"""The Bambu Filaments integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.loader import async_get_integration

from .api import BambuCloudClient
from .colors import BambuColorDB
from .const import CONF_REGION, CONF_TOKEN, DOMAIN
from .coordinator import BambuFilamentsCoordinator
from .frontend import async_setup_frontend
from .services import async_register_services

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

    # Create the hub device before the platforms run, so per-spool devices can
    # reference it via_device without ordering warnings.
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name="Bambu Filament Library",
        manufacturer="Bambu Lab",
        model="Filament Manager",
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: BambuFilamentsConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: BambuFilamentsConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
