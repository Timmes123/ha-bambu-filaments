"""Current Bambu Lab filament range, read from the public Bambu web shop.

The Studio color database (colors.py) lists every color Bambu ever made,
discontinued ones included (PETG HF, the old PLA Silk, ...). The shop is the
only public source of what is sold *today*: every filament product page lists
its colors with the 5-digit color code, a swatch image and the stock state.

There is no shop API - this module reads the sitemap and the product pages
the way a browser would, slowly (one page every few seconds, once a day) and
caches the result in HA storage. Everything here is best effort: a failed or
changed page never breaks the integration, the previous result stays in use.

`store.bambulab.com` redirects to the visitor's regional shop by IP, so the
range matches what the user would see when ordering.
"""

from __future__ import annotations

import asyncio
import html
import json
import logging
import re
import time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SHOP_URL = "https://store.bambulab.com"
STORAGE_KEY = f"{DOMAIN}.shop_range"
STORAGE_VERSION = 1
REFRESH_AFTER_S = 24 * 3600
# After a failed or rate-limited run, try again after this long.
RETRY_AFTER_S = 3 * 3600
# Product pages without any color code (accessories that matched the name
# heuristic, bundles, mystery boxes) are skipped for a week.
NON_FILAMENT_TTL_S = 7 * 24 * 3600
PAGE_DELAY_S = 4
REQUEST_TIMEOUT_S = 40

# Product handles worth fetching: they start with a material name. Bundles,
# packs and boxes carry no per-color swatches and are excluded up front.
_HANDLE_RE = re.compile(
    r"^(pla|petg|pet|abs|asa|pa6|paht|pa|pc|pps|ppa|pva|tpu|support-for)(-|$)"
)
_HANDLE_SKIP_RE = re.compile(
    r"(pack|bundle|box|set|kit|trial|sale|lithophane|cmykw|feed-assist|patch)"
)
_LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>")
_PRODUCT_LOC_RE = re.compile(r"^https?://[^/]+/products/([a-z0-9-]+)/?$")
# Color swatches of the variant picker: <li value="Black (30105)" ...><img src="...">
_SWATCH_RE = re.compile(
    r'<li value="([^"]*?\(\s*(\d{5})\s*\))"[^>]*>\s*<img src="([^"]+)"'
)
_JSONLD_RE = re.compile(
    r'<script id="product-jsonld"[^>]*>(.*?)</script>', re.S
)
_CODE_IN_NAME_RE = re.compile(r"\((\d{5})\)")
_SAFE_URL_RE = re.compile(r"^https://[A-Za-z0-9.-]+/[A-Za-z0-9._~/%+,-]*(\?[A-Za-z0-9=&._-]*)?$")
# Bambu's image CDN scales on the fly; the full product photos are 1600 px.
_CDN_HOST_RE = re.compile(r"^https://[a-z0-9.-]*bblcdn\.[a-z]+/")
_THUMB_OPS = "__op__resize,m_lfit,w_400__op__format,f_auto__op__quality,q_80"


def thumbnail(url: str | None) -> str | None:
    """A 400 px version of a Bambu CDN image (other hosts unchanged)."""
    if not url:
        return None
    if _CDN_HOST_RE.match(url) and "__op__" not in url:
        return url + _THUMB_OPS
    return url


def _safe_url(url: str | None) -> str | None:
    """Only plain https URLs survive - they end up in <img src> / <a href>."""
    if not url:
        return None
    url = html.unescape(url).strip()
    return url if _SAFE_URL_RE.match(url) else None


def filament_handles(sitemap_xml: str) -> list[str]:
    """Product handles from the shop sitemap that look like filament pages."""
    handles: set[str] = set()
    for loc in _LOC_RE.findall(sitemap_xml):
        if not (m := _PRODUCT_LOC_RE.match(loc)):
            continue
        handle = m.group(1)
        if _HANDLE_RE.match(handle) and not _HANDLE_SKIP_RE.search(handle):
            handles.add(handle)
    return sorted(handles)


def parse_product_page(page: str, base_url: str, handle: str) -> dict[str, Any]:
    """Colors on one product page: {code: {name, swatch, photo, url, available}}.

    Swatches come from the variant picker; stock state, the variant link and
    the product photo of each color (a sample print in that color) from the
    page's schema.org JSON-LD (one entry per color x packaging).
    """
    colors: dict[str, dict[str, Any]] = {}
    for label, code, img in _SWATCH_RE.findall(page):
        name = html.unescape(re.sub(r"\(\s*\d{5}\s*\)", "", label)).strip()
        colors.setdefault(code, {"name": name, "swatch": _safe_url(img)})
    in_stock: dict[str, bool] = {}
    links: dict[str, str] = {}
    photos: dict[str, str] = {}
    product_name = None
    if m := _JSONLD_RE.search(page):
        try:
            data = json.loads(m.group(1))
        except ValueError:
            data = {}
        product_name = data.get("name") if isinstance(data, dict) else None
        variants = data.get("hasVariant") if isinstance(data, dict) else None
        for variant in variants or []:
            if not isinstance(variant, dict):
                continue
            code_m = _CODE_IN_NAME_RE.search(str(variant.get("name") or ""))
            if not code_m:
                continue
            code = code_m.group(1)
            offer = variant.get("offers") or {}
            available = str(offer.get("availability") or "").endswith("InStock")
            in_stock[code] = in_stock.get(code, False) or available
            url = _safe_url(offer.get("url"))
            if url and (code not in links or available):
                links[code] = url
            if code not in photos and (photo := _safe_url(variant.get("image"))):
                photos[code] = photo
    page_url = f"{base_url}/products/{handle}"
    for code, color in colors.items():
        # No JSON-LD entry for a color = unknown stock state; shown as available.
        color["available"] = in_stock.get(code, True)
        color["url"] = links.get(code) or page_url
        color["photo"] = photos.get(code)
    return {
        "handle": handle,
        "name": product_name if isinstance(product_name, str) else None,
        "colors": colors,
    }


class BambuShopRange:
    """Daily-refreshed snapshot of the filament colors the shop sells."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict[str, Any] = {}
        self._loaded = False
        self._task: asyncio.Task | None = None
        self._last_attempt = 0.0

    @property
    def fetched_at(self) -> float:
        return float(self._data.get("fetched_at") or 0)

    @property
    def shop_url(self) -> str | None:
        return self._data.get("base_url")

    async def async_load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        try:
            self._data = await self._store.async_load() or {}
        except Exception as err:  # noqa: BLE001 - a broken cache is just discarded
            _LOGGER.warning("Shop range cache unreadable: %s", err)
            self._data = {}

    def colors(self) -> dict[str, dict[str, Any]]:
        """{code: {name, swatch, photo, url, available, handle}} of the current range."""
        return dict(self._data.get("colors") or {})

    def range_entries(self, colordb: Any, language: str) -> list[dict[str, Any]]:
        """The current range joined with the Studio color database.

        Product line, filament id, hex colors and the localized color name
        come from the database when it knows the code (it normally does), the
        shop's own wording is the fallback for brand-new colors.
        """
        products = self._data.get("products") or {}
        entries = []
        for code, color in self.colors().items():
            known = colordb.by_code(code, language) if colordb else None
            entries.append(
                {
                    "code": code,
                    "product": (known or {}).get("product")
                    or products.get(color.get("handle"))
                    or color.get("handle")
                    or "?",
                    "filament_id": (known or {}).get("filament_id"),
                    "colors": (known or {}).get("colors") or [],
                    "name": (known or {}).get("color_name") or color.get("name") or code,
                    "image": thumbnail(color.get("photo")) or color.get("swatch"),
                    "url": color.get("url"),
                    "available": bool(color.get("available", True)),
                }
            )
        entries.sort(key=lambda e: (e["product"], e["code"]))
        return entries

    def image(self, code: str | None) -> str | None:
        """Product photo (else swatch) for a color code - also for colors no
        longer sold, as long as the shop listed them once since this feature
        was enabled."""
        if not code:
            return None
        photo = (self._data.get("photos") or {}).get(str(code))
        return thumbnail(photo) or (self._data.get("swatches") or {}).get(str(code))

    def async_schedule_refresh(self) -> None:
        """Start a background refresh when the snapshot is stale."""
        if self._task is not None and not self._task.done():
            return
        now = time.time()
        if now - self.fetched_at < REFRESH_AFTER_S:
            return
        if now - self._last_attempt < RETRY_AFTER_S:
            return
        self._last_attempt = now
        self._task = self._hass.async_create_background_task(
            self._async_refresh(), name=f"{DOMAIN} shop range refresh"
        )

    async def _async_get(self, url: str) -> tuple[int, str, str]:
        session = async_get_clientsession(self._hass)
        async with session.get(url, timeout=REQUEST_TIMEOUT_S) as response:
            text = await response.text(errors="replace") if response.status == 200 else ""
            return response.status, text, str(response.url)

    async def _async_refresh(self) -> None:
        try:
            await self._async_refresh_inner()
        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001 - best effort, keep the old snapshot
            _LOGGER.warning("Reading the Bambu shop range failed: %s", err)

    async def _async_refresh_inner(self) -> None:
        status, sitemap, final_url = await self._async_get(
            f"{SHOP_URL}/sitemap_products_1.xml"
        )
        if status != 200 or "<loc>" not in sitemap:
            _LOGGER.warning("Bambu shop sitemap not available (HTTP %s)", status)
            return
        base_url = re.sub(r"/sitemap_products_1\.xml.*$", "", final_url).rstrip("/")
        handles = filament_handles(sitemap)
        if not handles:
            _LOGGER.warning("Bambu shop sitemap lists no filament pages - format changed?")
            return
        now = time.time()
        non_filament = {
            h: t
            for h, t in (self._data.get("non_filament") or {}).items()
            if now - t < NON_FILAMENT_TTL_S
        }
        colors: dict[str, dict[str, Any]] = {}
        products: dict[str, str] = {}
        failed = 0
        for index, handle in enumerate(h for h in handles if h not in non_filament):
            if index:
                await asyncio.sleep(PAGE_DELAY_S)
            status, page, _ = await self._async_get(f"{base_url}/products/{handle}")
            if status == 429:
                _LOGGER.info("Bambu shop rate limit hit - keeping the previous range")
                return
            if status != 200:
                failed += 1
                continue
            parsed = parse_product_page(page, base_url, handle)
            if not parsed["colors"]:
                non_filament[handle] = now
                continue
            if parsed["name"]:
                products[handle] = parsed["name"]
            for code, color in parsed["colors"].items():
                colors.setdefault(code, {**color, "handle": handle})
        if not colors or failed > len(handles) // 2:
            _LOGGER.warning(
                "Bambu shop range looks incomplete (%s colors, %s failed pages) - "
                "keeping the previous range",
                len(colors),
                failed,
            )
            return
        # Swatch images accumulate: a color that leaves the range keeps its
        # picture for the share page.
        swatches = dict(self._data.get("swatches") or {})
        swatches.update({c: v["swatch"] for c, v in colors.items() if v.get("swatch")})
        photos = dict(self._data.get("photos") or {})
        photos.update({c: v["photo"] for c, v in colors.items() if v.get("photo")})
        self._data = {
            "fetched_at": now,
            "base_url": base_url,
            "colors": colors,
            "products": products,
            "swatches": swatches,
            "photos": photos,
            "non_filament": non_filament,
        }
        await self._store.async_save(self._data)
        _LOGGER.info(
            "Bambu shop range updated: %s colors on %s product pages",
            len(colors),
            len(products),
        )
