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

## Milestones

- **Phase 0 — Verification: PASSED 2026-08-27.** `tools/phase0_verify.py` run by the user against their real account: login OK, READ TEST PASSED (~34 spools, pagination works), catalog `/filament/config` works **with** token (99 entries; contrary to Studio source comment it requires auth), WRITE TEST PASSED (full-object PUT with modified note → HTTP 200 with `filamentV2` echo, change verified on re-read, reverted). Write support is therefore confirmed feasible → phase 2 is a go.
- **Phase 1 — Read-only MVP:** config flow (incl. reauth), coordinator, aggregate + per-spool sensors, HACS scaffolding (hacs.json, CI: hassfest + HACS action), README with the unofficial-API/cloud-only/ToS disclaimer.
- **Phase 2 — Write actions** (if phase 0 confirmed writes).
- **Phase 3 — Comfort:** custom card, AMS cross-linkage, low-stock threshold helpers/notifications, `/filament/config` catalog for nicer labels.

## Known constraints (README material)

Unofficial reverse-engineered API; requires cloud account (no LAN mode for this data); Cloudflare-dependent login; ~90-day reauth; Bambu may break or restrict this at any time. Remaining weights are slicer-deduction/AMS-sync values, not live scales.
