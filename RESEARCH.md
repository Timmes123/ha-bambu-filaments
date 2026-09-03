# Research: Accessing the Bambu Lab Filament Manager (cloud filament library)

Date: 2026-08-27. Consolidated findings from three parallel research passes (BambuStudio source code, community API reverse-engineering docs, HA ecosystem). This document is the factual basis for SPEC.md.

## Verdict

**Yes, the account filament library is accessible.** Bambu Studio's "Filament Manager" (official name; introduced in Studio 2.6.1 beta, first public release 2.7.1, June 2026) is cloud-first by design: all spool data is stored in the Bambu Cloud and synced between Bambu Studio and Bambu Handy. The REST endpoints are known (route paths and full JSON schemas are visible in the open-source BambuStudio repo, even though the HTTP layer itself is in the closed network plugin), and a third-party client using a plain bearer token has already demonstrated read access (ha-bambulab PR #2028).

## The Filament Manager feature

- Spool-level **inventory** system, not a preset editor. Per spool: vendor/brand, material type, name, `filamentId` (e.g. `GFA00`), color(s) incl. gradient/multicolor, RFID `tag_uid`, remaining net weight in grams (`netWeight`), full-spool net weight (`totalNetWeight`), status (active/empty/archived), note, favorite, entry method (manual / ams_sync / rfid), price, drying reminder, and a live mount snapshot (which printer/AMS/slot the spool sits in).
- Remaining **percent is not stored server-side** — clients derive it as `netWeight / totalNetWeight * 100`.
- Official Bambu spools auto-register via RFID; third-party spools are entered manually. Remaining weight is updated ONLY by the AMS sync of a running Studio/Handy client (`POST /ams/sync`, throttled to every 10 min per spool while printing), never by the printer itself. There is NO consumption deduction anywhere - not in Studio's filament manager, not in the cloud (verified 2026-09-03: a 64 g print left the mapped manual spool untouched); third-party spools without RFID never change on their own.
- Studio keeps a local cache (`%APPDATA%\BambuStudio\filament_inventory\spools.json`), but the cloud is authoritative.
- Distinct from the older **slicer preset sync** (`/v1/iot-service/api/slicer/setting`, `PFUS…` custom filament presets) — that system stores tuning profiles (temps, flow), not spools. A spool links to a preset via `setting_id`/`filamentId`.

## Confirmed API surface

Base: `https://api.bambulab.com/v1/design-user-service` (China: `api.bambulab.cn`). Auth: standard Bambu cloud bearer token.

| Operation | Endpoint |
|---|---|
| List spools | `GET /my/filament/v2?offset=&limit=` (filters: `category`, `status`, `ids`, `RFIDs`; default limit 20; response `{"total": N, "hits": [...]}`) |
| Create spool | `POST /my/filament/v2` (returns `{}` — re-GET to learn the id) |
| Update spool | `PUT /my/filament/v2` (int64 `id` in **body**, not path; body must include `id` + `filamentName`) |
| Batch delete | `DELETE /my/filament/v2/batch` (body `{"ids": []}` and/or `{"RFIDs": []}`) |
| Filament catalog | `GET /v1/design-user-service/filament/config` (~110 canonical vendor/type/name/filamentId entries; the Studio source claims "no auth required", but a direct probe on 2026-08-27 returned 401 without a token — auth IS required. Positive side effect of the probe: curl_cffi passes Cloudflare from this network, 401 is a real API response, not a bot block) |
| AMS weight sync | `POST /my/filament/v2/ams/sync` |
| Slot binding sync | `POST /my/filament/v2/slot-mappings/sync` |

Cloud JSON schema (camelCase), verified against a captured live response:

```json
{ "id": 6915055, "createType": "ams",
  "filamentVendor": "Bambu Lab", "filamentType": "PLA",
  "filamentName": "PLA Basic", "filamentId": "GFA00",
  "RFID": "…", "color": "#FFFFFFFF", "colorType": 2, "colors": ["#FFFFFFFF"],
  "netWeight": 931, "totalNetWeight": 1000,
  "note": "", "createdAt": 1780424283, "updatedAt": 1780424283,
  "status": 0, "isSupport": false, "trayIdName": "A00-W01", "category": "PLA",
  "inPrinter": true, "devId": "…", "amsSn": "…", "amsId": 0, "slotId": "…", "deviceName": "…" }
```

Confirmed: routes, schemas, sync semantics (from BambuStudio source: `src/slic3r/GUI/fila_manager/wgtFilaManagerCloudClient.h/.cpp`, `wgtFilaManagerCloudSync.cpp`, `src/slic3r/Utils/NetworkAgent.hpp`, `bambu_networking.hpp`, and the React device page `features/filament-manager/types.ts`). Read access by third-party clients is demonstrated (PR #2028). **Inferred, not yet demonstrated:** that the write endpoints accept third-party clients the same way — must be verified early with a test script against a real account.

## Authentication (as used by ha-bambulab / pybambu today)

- `POST https://api.bambulab.com/v1/user-service/user/login` with `{account, password}` → either an `accessToken` directly, or `loginType: "verifyCode"` (request code via `POST /v1/user-service/user/sendemail/code`, re-login with `{account, code}`), or `loginType: "tfa"` (post `{tfaKey, tfaCode}` to `https://bambulab.com/api/sign-in/tfa`, token comes back as cookie).
- Token: JWT, `expiresIn` ≈ 90 days. **The refresh endpoint is dead (401)** — plan for full re-login (HA reauth flow), not silent refresh.
- `api.bambulab.com` sits behind **Cloudflare bot protection**: plain Python `requests` gets 403 on login. pybambu's working mitigation: `curl_cffi` with `impersonate="chrome"`, fallback `cloudscraper`. Studio-like headers (`User-Agent: bambu_network_agent/…`, `X-BBL-*`) are sent but per direct probing not actually required by the server.
- Regions: global `.com` / China `.cn` (SMS code instead of email).

## Ecosystem / competition

- **ha-bambulab** (installed here: v2.2.25, entities for both printers' AMS): covers printer + AMS live data via MQTT (per-tray type, color hex, remain %, `tray_uuid`, `tag_uid`, `filament_id`). It touches `GET /slicer/setting` only to resolve custom preset names. **No filament-library support.** [PR #2028](https://github.com/greghesp/ha-bambulab/pull/2028) (June 2026, neoKushan) adds a read-only inventory sensor polling `/my/filament/v2` — open, rebased, zero maintainer response; effectively stalled. Origin: discussion #2004.
- **Spoolman / Bambuddy / SpoolmanSync etc.** all work from printer MQTT tray data or manual entry — none read the account library. The `/my/filament/v2` surface is documented (OpenBambuAPI) but otherwise unexploited. **No direct competition for this integration.**
- What Bambu's Filament Manager does NOT replace: local-only setups (it requires internet), third-party-spool automation, multi-vendor fleets, cost tracking, live mid-print weight.

## Risks & constraints (state these in the README)

1. **Unofficial API.** Reverse-engineered; Bambu sanctions only LAN/Developer Mode/Bambu Connect for third parties and has invoked ToS against cloud-API projects before (OrcaSlicer cloud-fork takedown). The Jan-2025 "Authorization Control" changes affect signed MQTT *printer commands*, not cloud reads — but Bambu is generally narrowing third-party access. Breakage risk is real.
2. **Cloudflare**: needs `curl_cffi`/`cloudscraper`; could tighten at any time.
3. **Cloud-only**: no LAN fallback for this data — the integration requires a cloud login even if the printers run in LAN mode.
4. **Token expiry ~90 days, no refresh** → recurring reauth (email code) must be a first-class UX via HA's reauth flow.
5. Write endpoints unverified by third parties (read is proven).

## Key sources

- BambuStudio source: https://github.com/bambulab/BambuStudio (sparse clone kept in the session scratchpad under `bs/`)
- OpenBambuAPI (cloud-http.md): https://github.com/Doridian/OpenBambuAPI
- open-bambu-networking `NETWORK_PLUGIN.md` (full MITM'd request/response shapes, §6.9/§6.15): https://github.com/AlexanderViand/open-bambu-networking
- ha-bambulab + vendored pybambu (auth reference): https://github.com/greghesp/ha-bambulab — `custom_components/bambu_lab/pybambu/bambu_cloud.py`
- ha-bambulab PR #2028 / discussion #2004 (working third-party read of `/my/filament/v2`)
- Wiki: https://wiki.bambulab.com/en/software/bambu-studio/filament-manager (blocks bots; content via excerpts)
- Reference copies of `cloud-http.md`, `network_plugin.md`, `bambu_cloud.py`, `const.py` are in the session scratchpad.
