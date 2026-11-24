"""Public, read-only share page of the spool inventory.

A friend opens `<external HA url>/bambu_filaments/share/<token>` without a
Home Assistant login and sees which filament colors are in stock. The page is
rendered server-side from the coordinator data and exposes only brand,
product line, color name/code and (optionally) the remaining weight - never
notes, RFIDs, printer names or anything else from the account.

The token is a long random secret kept in HA storage (not in the config
entry, so regenerating it does not reload the integration). A wrong token
returns a plain 404.
"""

from __future__ import annotations

from collections.abc import Callable
import hmac
import html
import logging
import secrets
from typing import TYPE_CHECKING, Any

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .colors import normalize_hex
from .const import DEFAULT_SHARE_REMAINING, DOMAIN, OPT_SHARE_REMAINING, SHARE_URL_BASE

if TYPE_CHECKING:
    from .coordinator import BambuFilamentsCoordinator

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1


class ShareLink:
    """The secret share token of one config entry."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._hass = hass
        self._store: Store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.share_{entry_id}")
        self.token: str = ""
        self._listeners: list[Callable[[], None]] = []

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        token = data.get("token")
        if isinstance(token, str) and len(token) >= 32:
            self.token = token
        else:
            await self.async_regenerate()

    async def async_regenerate(self) -> None:
        """New secret - every previously shared link stops working."""
        self.token = secrets.token_urlsafe(32)
        await self._store.async_save({"token": self.token})
        for listener in list(self._listeners):
            listener()

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    @property
    def path(self) -> str:
        return f"{SHARE_URL_BASE}/{self.token}"

    def url(self) -> str:
        """Full link with the external HA URL, else the bare path."""
        try:
            base = get_url(self._hass, allow_internal=False, allow_ip=True)
        except NoURLAvailableError:
            return self.path
        return f"{base.rstrip('/')}{self.path}"


# --------------------------------------------------------------- page data

_CATEGORY_ORDER = ("pla", "petg", "other")


def _category(material: str, line: str = "") -> str:
    # Support filaments carry the material they support ("PLA" for Support
    # For PLA/PETG, "PLA-S" for Support For PLA) but belong under Other.
    if "SUPPORT" in (line or "").upper():
        return "other"
    material = (material or "").upper()
    if material.endswith("-S"):
        return "other"
    if material.startswith("PLA"):
        return "pla"
    if material.startswith("PETG"):
        return "petg"
    return "other"


def share_tiles(coordinator: BambuFilamentsCoordinator) -> list[dict[str, Any]]:
    """One tile per color in stock (spools with filament left, combined)."""
    from .entity import clean_display_name  # local: entity imports the coordinator

    shop = coordinator.shop
    tiles: dict[tuple, dict[str, Any]] = {}
    for spool in (coordinator.data or {}).values():
        net = spool.get("netWeight") or 0
        if not isinstance(net, (int, float)) or net <= 0:
            continue
        raw = spool.get("colors") or [spool.get("color")]
        colors = [h[:7] for h in (normalize_hex(c) for c in raw if c) if h]
        vendor = (spool.get("filamentVendor") or "").strip()
        line = (spool.get("filamentName") or spool.get("filamentType") or "").strip()
        custom = clean_display_name(spool) or ""
        key = (vendor, line, custom, tuple(sorted(colors)))
        tile = tiles.get(key)
        if tile is None:
            color_name, _ = coordinator.color_lookup(spool)
            code = None
            if vendor == "Bambu Lab":
                code = coordinator.colordb.strict_code(spool.get("filamentId"), raw)
            tile = tiles[key] = {
                "vendor": vendor,
                "line": line,
                "title": custom or color_name or (colors[0] if colors else "?"),
                "code": code,
                "colors": colors,
                "image": shop.image(code) if shop and code else None,
                "category": _category(spool.get("filamentType") or line, line),
                "count": 0,
                "remaining_g": 0,
            }
        tile["count"] += 1
        tile["remaining_g"] += int(net)
    return sorted(
        tiles.values(),
        key=lambda t: (
            t["vendor"] != "Bambu Lab",
            t["vendor"].lower(),
            t["line"].lower(),
            t["code"] or "99999",
            t["title"].lower(),
        ),
    )


# -------------------------------------------------------------------- HTML

_STRINGS = {
    "en": {
        "title": "Filament collection",
        "colors": lambda n: f"{n} color{'' if n == 1 else 's'} in stock",
        "as_of": "as of",
        "all": "All",
        "pla": "PLA",
        "petg": "PETG",
        "other": "Other",
        "spools": lambda n: f"{n} spool{'' if n == 1 else 's'}",
        "empty": "No filament in stock right now.",
    },
    "de": {
        "title": "Filament-Sammlung",
        "colors": lambda n: f"{n} Farbe{'' if n == 1 else 'n'} vorrätig",
        "as_of": "Stand",
        "all": "Alle",
        "pla": "PLA",
        "petg": "PETG",
        "other": "Sonstige",
        "spools": lambda n: f"{n} Spule{'' if n == 1 else 'n'}",
        "empty": "Gerade ist kein Filament vorrätig.",
    },
}


def _fmt_g(grams: int) -> str:
    return f"{grams / 1000:.1f} kg".replace(".0 kg", " kg") if grams >= 1000 else f"{grams} g"


def _swatch_html(tile: dict[str, Any]) -> str:
    colors = tile["colors"]
    if len(colors) > 1:
        stops = ", ".join(colors)
        style = f"background:linear-gradient(135deg, {stops})"
    elif colors:
        style = f"background:{colors[0]}"
    else:
        style = "background:#888"
    if not tile["image"]:
        return f'<div class="sw" style="{style}"></div>'
    # With a photo the tile stays neutral (the photo has its own light
    # background); the page script swaps in the color fill if it fails.
    return (
        f'<div class="sw" data-fill="{html.escape(style)}">'
        f'<img src="{html.escape(tile["image"])}" alt="" loading="lazy" '
        'referrerpolicy="no-referrer"></div>'
    )


def render_share_page(
    coordinator: BambuFilamentsCoordinator, language: str, nonce: str
) -> str:
    t = _STRINGS["de" if (language or "").lower().startswith("de") else "en"]
    show_remaining = bool(
        coordinator.config_entry.options.get(OPT_SHARE_REMAINING, DEFAULT_SHARE_REMAINING)
    )
    tiles = share_tiles(coordinator)
    counts = {c: sum(1 for x in tiles if x["category"] == c) for c in _CATEGORY_ORDER}
    groups: dict[str, list[dict[str, Any]]] = {}
    for tile in tiles:
        head = tile["line"] if tile["vendor"] in ("Bambu Lab", "") else f"{tile['vendor']} {tile['line']}".strip()
        groups.setdefault(head or "?", []).append(tile)

    sections = []
    for head, items in groups.items():
        cards = []
        for tile in items:
            meta = []
            if tile["code"]:
                meta.append(html.escape(tile["code"]))
            if show_remaining:
                meta.append(_fmt_g(tile["remaining_g"]))
                if tile["count"] > 1:
                    meta.append(t["spools"](tile["count"]))
            cards.append(
                f'<div class="tile" data-cat="{tile["category"]}">'
                f"{_swatch_html(tile)}"
                f'<div class="name">{html.escape(tile["title"])}</div>'
                f'<div class="meta">{" · ".join(meta)}</div>'
                "</div>"
            )
        cats = " ".join(sorted({x["category"] for x in items}))
        sections.append(
            f'<section data-cats="{cats}"><h2>{html.escape(head)}</h2>'
            f'<div class="grid">{"".join(cards)}</div></section>'
        )

    chips = [f'<button class="chip on" data-f="all">{t["all"]} <span>{len(tiles)}</span></button>']
    # Categories without any color get no chip at all (an empty, disabled
    # chip only cost space and wrapped the row on phones).
    for cat in _CATEGORY_ORDER:
        if counts[cat]:
            chips.append(
                f'<button class="chip" data-f="{cat}">{t[cat]} <span>{counts[cat]}</span></button>'
            )
    as_of = dt_util.now()
    stamp = as_of.strftime("%d.%m.%Y %H:%M") if t is _STRINGS["de"] else as_of.strftime("%Y-%m-%d %H:%M")
    body = "".join(sections) if tiles else f'<p class="empty">{html.escape(t["empty"])}</p>'
    lang_attr = "de" if t is _STRINGS["de"] else "en"
    return f"""<!doctype html>
<html lang="{lang_attr}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<meta name="referrer" content="no-referrer">
<title>{html.escape(t["title"])}</title>
<style>
:root {{ --bg:#f4f5f7; --card:#fff; --text:#1c1d21; --muted:#6b6f76; --line:#dfe1e5; --accent:#00ae42; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#111214; --card:#1d1f23; --text:#ececee; --muted:#9a9ea6; --line:#2e3137; }}
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--text);
  font:15px/1.4 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
header {{ position:sticky; top:0; z-index:2; background:var(--bg); padding:16px 16px 10px;
  border-bottom:1px solid var(--line); }}
.top {{ max-width:1100px; margin:0 auto; }}
h1 {{ margin:0; font-size:1.35em; }}
.sub {{ color:var(--muted); font-size:0.9em; margin-top:2px; }}
.chips {{ display:flex; gap:8px; flex-wrap:wrap; margin-top:12px; }}
.chip {{ border:1px solid var(--line); background:var(--card); color:var(--text); border-radius:18px;
  padding:6px 14px; font:inherit; cursor:pointer; }}
.chip span {{ color:var(--muted); margin-left:4px; }}
.chip.on {{ background:var(--accent); border-color:var(--accent); color:#fff; }}
.chip.on span {{ color:rgba(255,255,255,0.85); }}
main {{ padding:4px 16px 32px; max-width:1100px; margin:0 auto; }}
section {{ margin-top:18px; }}
h2 {{ font-size:1.05em; margin:0 0 8px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(100px, 1fr)); gap:10px; }}
.tile {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:8px; min-width:0; }}
.sw {{ position:relative; aspect-ratio:1; border-radius:8px; overflow:hidden; border:1px solid var(--line);
  background:#f2f2f2; }}
.sw img {{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }}
.name {{ font-weight:600; margin-top:6px; font-size:0.92em; overflow-wrap:anywhere; }}
.meta {{ color:var(--muted); font-size:0.8em; }}
.hide {{ display:none; }}
.empty {{ color:var(--muted); margin-top:24px; }}
</style>
</head>
<body>
<header><div class="top">
<h1>{html.escape(t["title"])}</h1>
<div class="sub">{html.escape(t["colors"](len(tiles)))} · {html.escape(t["as_of"])} {stamp}</div>
<div class="chips">{"".join(chips)}</div>
</div></header>
<main>{body}</main>
<script nonce="{nonce}">
function fill(img) {{
  var box = img.parentElement;
  box.setAttribute("style", box.dataset.fill || "");
  img.remove();
}}
document.querySelectorAll(".sw img").forEach(function (img) {{
  if (img.complete && img.naturalWidth === 0) fill(img);
  else img.addEventListener("error", function () {{ fill(img); }});
}});
document.querySelectorAll(".chip").forEach(function (chip) {{
  chip.addEventListener("click", function () {{
    var f = chip.dataset.f;
    document.querySelectorAll(".chip").forEach(function (c) {{ c.classList.toggle("on", c === chip); }});
    document.querySelectorAll(".tile").forEach(function (el) {{
      el.classList.toggle("hide", f !== "all" && el.dataset.cat !== f);
    }});
    document.querySelectorAll("section").forEach(function (s) {{
      s.classList.toggle("hide", f !== "all" && s.dataset.cats.split(" ").indexOf(f) < 0);
    }});
  }});
}});
</script>
</body>
</html>"""


class BambuShareView(HomeAssistantView):
    """Serves the share page without HA authentication (token in the path)."""

    url = SHARE_URL_BASE + "/{token}"
    name = "bambu_filaments:share"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    def _coordinator_for(self, token: str) -> BambuFilamentsCoordinator | None:
        for entry in self._hass.config_entries.async_entries(DOMAIN):
            if entry.state is not ConfigEntryState.LOADED:
                continue
            coordinator = getattr(entry, "runtime_data", None)
            share = getattr(coordinator, "share", None)
            if share and share.token and hmac.compare_digest(share.token, token):
                return coordinator
        return None

    async def get(self, request: web.Request, token: str) -> web.Response:
        coordinator = self._coordinator_for(token)
        if coordinator is None:
            return web.Response(status=404, text="Not found")
        nonce = secrets.token_urlsafe(16)
        try:
            page = render_share_page(coordinator, self._hass.config.language, nonce)
        except Exception:  # noqa: BLE001 - never leak a traceback to the public page
            _LOGGER.exception("Rendering the share page failed")
            return web.Response(status=500, text="Error")
        return web.Response(
            text=page,
            content_type="text/html",
            headers={
                "Cache-Control": "no-store",
                # The token is in the URL: no Referer to the image CDN.
                "Referrer-Policy": "no-referrer",
                "X-Robots-Tag": "noindex, nofollow",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": (
                    "default-src 'none'; img-src https: data:; style-src 'unsafe-inline'; "
                    f"script-src 'nonce-{nonce}'; base-uri 'none'; form-action 'none'; "
                    "frame-ancestors 'none'"
                ),
            },
        )
