"""Serve the Bambu Filaments card and register it as a Lovelace resource."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import CARD_FILENAME, CARD_URL_BASE

_LOGGER = logging.getLogger(__name__)


async def async_setup_frontend(hass: HomeAssistant, version: str) -> None:
    """Register the static path for the card and add the Lovelace resource."""
    www_path = Path(__file__).parent / "www"
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL_BASE, str(www_path), cache_headers=True)]
        )
    except RuntimeError:
        # Path already registered (e.g. after a config entry reload).
        pass
    await _ensure_resource(hass, f"{CARD_URL_BASE}/{CARD_FILENAME}?v={version}")


async def _ensure_resource(hass: HomeAssistant, url: str) -> None:
    lovelace = hass.data.get("lovelace")
    resources = getattr(lovelace, "resources", None)
    if resources is None or not hasattr(resources, "async_create_item"):
        _LOGGER.info(
            "Lovelace resources not editable (YAML mode?). Add the card resource "
            "manually: %s (type: module)",
            url,
        )
        return
    try:
        if not resources.loaded:
            await resources.async_load()
            resources.loaded = True
        base = url.split("?")[0]
        for item in list(resources.async_items()):
            if str(item.get("url", "")).split("?")[0] == base:
                if item["url"] != url:
                    await resources.async_update_item(
                        item["id"], {"res_type": "module", "url": url}
                    )
                    _LOGGER.info("Updated Bambu Filaments card resource to %s", url)
                return
        await resources.async_create_item({"res_type": "module", "url": url})
        _LOGGER.info("Registered Bambu Filaments card resource %s", url)
    except Exception:  # noqa: BLE001 - resource registration must never break setup
        _LOGGER.exception("Could not register the Bambu Filaments card resource")
