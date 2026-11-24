# SPEC — HA Bambu Filaments

Status 2026-08-27: **agreed with the user** — standalone project (no contribution to ha-bambulab), write support planned from the start (gated on phase-0 verification), per-spool entities configurable in the integration's options flow, name/domain confirmed. This is the authoritative design document; keep it updated when decisions change.

## Goal

A standalone HACS custom integration that surfaces the **Bambu Lab Filament Manager** (the cloud filament library introduced in Bambu Studio 2.6.1/2.7.1 and Bambu Handy) in Home Assistant: spool inventory, remaining weights, colors, materials — readable as entities, ideally also writable (adjust remaining weight, notes, status). No overlap with ha-bambulab (printer/AMS live data via MQTT stays there).

- Repo: github.com/Timmes123/ha-bambu-filaments (public, MIT), HACS custom repository — same workflow as ha-better-todo.
- Domain: `bambu_filaments`, integration name "Bambu Filaments" (agreed)
- Deployment rule carried over from ha-better-todo: **only via HACS releases**, never direct file deployment to the live HA.

## Architecture

```
custom_components/bambu_filaments/
├── api.py            # Cloud client: auth + /my/filament/v2 CRUD (curl_cffi/cloudscraper)
├── config_flow.py    # region → email/password → email-code / 2FA steps; reauth flow
├── coordinator.py    # DataUpdateCoordinator, polls GET /my/filament/v2
├── sensor.py         # aggregate + per-spool sensors
├── services.py       # refresh + write services (phase 2)
├── diagnostics.py    # redacted (no tokens/RFIDs)
└── ...
```

- **Own cloud client**, no dependency on ha-bambulab. Auth flow is our own implementation of the publicly documented login sequence (RESEARCH.md); Cloudflare handling via `curl_cffi` (`impersonate="chrome"`), fallback `cloudscraper`, fallback plain `requests`. No code copied from third-party integrations (original implementation from the documented API surface); community API documentation may be credited in the README.
- Token (~90 days, no refresh possible) stored in the config entry; 401 → `ConfigEntryAuthFailed` → HA reauth flow asks for a fresh email code. This must be smooth, it will happen quarterly.
- One config entry = one Bambu account = one HA device "Bambu Filament Library".
- Polling: default every 15 min (configurable via options flow; data changes slowly — Studio itself syncs AMS weights at most every 10 min while printing). Manual `bambu_filaments.refresh` action.
- Pagination: `GET /my/filament/v2` default limit 20 → loop with offset until `total` reached.

## Entities

Per account device:
- `sensor.filament_library_spools` — state: number of active spools; attributes: full spool list (id, vendor, type, name, color(s), remaining g, total g, %, RFID, status, in_printer/device).
- `sensor.filament_library_remaining_total` — total remaining grams (active spools).
- Per material category (PLA, PETG, …): remaining grams as attributes on `remaining_total`; promoted to own entities only if a concrete dashboard need appears.

Per spool (dynamically created/removed, unique_id = cloud spool id):
- `sensor.filament_<vendor>_<name>_<id>` — state: remaining %, attributes: netWeight, totalNetWeight, color hex, material, filamentId, RFID, status, note, trayIdName, mount info (inPrinter, deviceName, amsId, slotId).
- **Configurable in the options flow** (agreed): toggle per-spool entities on/off (default ON), toggle whether archived/empty spools get entities (default OFF — only attributes on the aggregate sensor). Removed/filtered spools clean up their entities via the entity registry.

Cross-linkage (phase 3): match library spools to ha-bambulab AMS tray sensors via `tag_uid`/RFID → "which library spool is loaded in which printer right now" without duplicating ha-bambulab's data.

## Write support (phase 2 — agreed, gated on phase-0 verification)

Actions (HA services), all against the documented endpoints:
- `bambu_filaments.set_remaining` (spool id, grams) — `PUT /my/filament/v2`
- `bambu_filaments.update_spool` (note, status active/empty/archived, name…)
- `bambu_filaments.create_spool` / `bambu_filaments.delete_spool`

Caveat from RESEARCH.md: third-party **read** access is proven, write is inferred → phase 0 must verify writes before promising them.

## Custom Lovelace card (phase 3, decide when we get there)

Spool gallery: color chip, vendor/name, remaining bar (g + %), material filter, low-stock highlight. Shipped inside the integration like better-todo's card (single HACS repo). Phase 3+.

## Shop range + share page (v2.3.0, agreed 2026-11-24)

- **Shop range** (`shop.py`, option `shop_sync`, default off): the Studio color DB has no "discontinued" flag (PETG HF, old PLA Silk, retired PETG Basic colors are all still listed). The Bambu web shop is the only public source of the current range. No API: `store.bambulab.com` geo-redirects to the regional shop (from Germany always EU); `sitemap_products_1.xml` lists all products; filament pages are picked by handle prefix (material name, minus pack/bundle/box/set/kit/trial/sale), each page carries the variant picker `<li value="Name (12345)"><img src=swatch>` and a schema.org `product-jsonld` ProductGroup whose variants are named `"<line> - <color> (<code>) / <packaging> / <weight>"` with `offers.availability` + `offers.url`. ~43 pages, one every 4 s, once a day (24 h stale check every hour, first check 60 s after setup), 429 = abort and keep the last result, retry after 3 h. Pages without codes are skipped for 7 days. Per color the JSON-LD variant `image` is a product photo (sample print in that color, 1600 px); thumbnails via the CDN op suffix `__op__resize,m_lfit,w_400__op__format,f_auto__op__quality,q_80` (6-15 KB). Photo and swatch URLs accumulate across refreshes (a color that leaves the range keeps its picture once seen; retired pages like petg-hf are already gone, so those colors show a hex tile). Cloudflare answered 429 after ~28 pages at 1 page/s during research.
- **Missing colors** = card `mode: missing` (`missing_products`, `missing_count_empty` default true). Backend action `get_shop_range` (read-only, response only) returns the range joined with the color DB; ownership is computed in the card: spool vendor `Bambu Lab` + `bambu_color_code` + `filament_id` equal to the shop entry's.
- **Share page** (`share.py`, options `share_page` + `share_show_remaining`, default off): `HomeAssistantView` with `requires_auth = False` at `/bambu_filaments/share/<token>`, registered once per HA run; token = `secrets.token_urlsafe(32)` in Store `bambu_filaments.share_<entry_id>` (not in the entry, so renewing does not reload), compared with `hmac.compare_digest`, wrong token = 404. Server-rendered HTML, only vendor/product line/color name/code/(remaining + count); spools with 0 g are hidden; identical colors merged. Headers: `Referrer-Policy: no-referrer` (token must not leak to the image CDN), CSP with per-request script nonce, `no-store`, `noindex`. Hub entities `sensor.…_share_link` (full URL via `get_url(allow_internal=False)`) and `button.…_renew_share_link`; both are removed from the entity registry when the option is off.
- Product line of a shop color (v2.4.1): the color DB name by default, but the color DB files sub-lines under their base line (PLA Basic Gradient = "PLA Basic", PLA Silk Multi-Color = "PLA Silk"). A shop page name that extends the DB name by another word wins (`shop.product_line`); "Support for PLA (New Version)" and the combined "TPU 85A / TPU 90A" page keep the DB names. Live: PLA Basic 30 colors, PLA Basic Gradient 8, PLA Silk Multi-Color 10.
- Color DB lookup order (v2.4.2): tray code first (`trayIdName` "A16-R0" = filament id without "GF" + the DB `color_code`; unique per filament id across the whole DB; a prefix that does not match the spool's filament id is ignored), then filament id + exact colors, then color only (name lookup, not strict codes). Reason: some RFID tags carry a hex that differs from the DB - every PLA Wood Rosewood tag reads #3F231C, DB and shop say #4C241C (seen on a second user's spool in SpoolmanSync issue 108; ha-bambulab PR 2357 uses the same fallback). Auto-dedup also matches a manual twin by equal strict color code, so stock created by color code is adopted. ha-bambulab tray sensors do not expose the tag's tray code, so auto-register (user decision 2026-11-24, "auf Nummer sicher") only creates spools whose filament id + colors (`cols` attribute, multi-color included) match the DB exactly (`official_tray_code`); others are logged once at INFO and left to Handy/Studio, which read the tray code from the printer.
- Transparent colors (v2.4.3): 25 color DB codes carry an alpha below FF (Natural support 65102 = #00000000, translucent PLA/PETG lines). `compact_hex` keeps the alpha (opaque colors stay #RRGGBB like Studio); create/update send it, verified by a self-cleaning probe 2026-11-24 (create accepts #00000000 as color, PUT accepts it in color + colors). Before, cutting the alpha turned Natural into Black (65103) and translucent code-created spools lost their name. Card and share page draw a checkerboard behind (partly) transparent colors.
- Share page layout (v2.4.4, user request): tiles min 200 px on desktop (about 5 per row), exactly 2 columns up to 600 px width; tapping a tile opens a zoom overlay (photo at 1200 px via `shop.enlarged`, falling back to the thumbnail, then to the color fill; caption = name + meta; closes on click or Escape).
- Share page categories: material prefix PLA / PETG, everything else Other; support filaments (line contains "Support", or material ending in `-S`) count as Other although the cloud reports them as `PLA` / `PLA-S`. Categories without colors get no chip.
- Card photos + tiles (v2.4.0, user request 2026-11-24): `show_images` (default off, all modes) swaps the color square of Bambu Lab spools with a known `bambu_color_code` for the shop photo (`get_shop_range` response key `images` = {code: thumbnail} over every code seen, retired ones included; same neutral-box + data-fill load-error fallback as the share page). `layout: tiles` (default `list`, spools mode) renders a grid per group; stacks/children/cog/details behave like rows (shared `_itemData`, `.item` class for the click handlers).
- Product photos (user's choice, 2026-11-24, instead of the near-flat picker swatches) are hot-linked from Bambu's CDN, never stored in the repo; README screenshots use hex fills only. The tile is neutral grey behind a photo and switches to the hex fill only if the photo fails to load.

## Milestones

- **Phase 0 — Verification: PASSED 2026-08-27.** `tools/phase0_verify.py` run by the user against their real account: login OK, READ TEST PASSED (~34 spools, pagination works), catalog `/filament/config` works **with** token (99 entries; contrary to Studio source comment it requires auth), WRITE TEST PASSED (full-object PUT with modified note → HTTP 200 with `filamentV2` echo, change verified on re-read, reverted). Write support is therefore confirmed feasible → phase 2 is a go.
- **Phase 1 — Read-only MVP:** config flow (incl. reauth), coordinator, aggregate + per-spool sensors, HACS scaffolding (hacs.json, CI: hassfest + HACS action), README with the unofficial-API/cloud-only/ToS disclaimer.
- **Phase 2 — Write actions** (if phase 0 confirmed writes).
- **Phase 3 — Comfort:** custom card, AMS cross-linkage, low-stock threshold helpers/notifications, `/filament/config` catalog for nicer labels.

## Known constraints (README material)

Unofficial reverse-engineered API; requires cloud account (no LAN mode for this data); Cloudflare-dependent login; ~90-day reauth; Bambu may break or restrict this at any time. Remaining weights are slicer-deduction/AMS-sync values, not live scales.
