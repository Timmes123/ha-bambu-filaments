"""The Bambu Filaments integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .api import BambuCloudClient
from .const import CONF_REGION, CONF_TOKEN, DOMAIN, SERVICE_REFRESH
from .coordinator import BambuFilamentsCoordinator

PLATFORMS = [Platform.SENSOR]

type BambuFilamentsConfigEntry = ConfigEntry[BambuFilamentsCoordinator]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register domain-level services."""

    async def handle_refresh(call: ServiceCall) -> None:
        for entry in hass.config_entries.async_entries(DOMAIN):
            if isinstance(getattr(entry, "runtime_data", None), BambuFilamentsCoordinator):
                await entry.runtime_data.async_request_refresh()

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, handle_refresh)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: BambuFilamentsConfigEntry) -> bool:
    """Set up a Bambu account from a config entry."""
    client = BambuCloudClient(entry.data[CONF_REGION], entry.data[CONF_TOKEN])
    coordinator = BambuFilamentsCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: BambuFilamentsConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: BambuFilamentsConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
