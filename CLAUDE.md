# HA-Bambu-Filaments

Custom Home Assistant integration ("Bambu Filaments", domain `bambu_filaments`) that surfaces the Bambu Lab cloud Filament Manager (spool inventory from Bambu Studio 2.6.1+/Handy) in Home Assistant. Will be published on GitHub (account: **Timmes123**, repo `ha-bambu-filaments`, public, MIT) and installed via HACS as a custom repository.

Authoritative documents:
- `RESEARCH.md` — API research (endpoints, auth, schemas, risks). Factual basis; verified 2026-08-27.
- `SPEC.md` — agreed design (architecture, entities, phases). Keep updated when decisions change.

## Project status (2026-08-27)

- Research complete: cloud endpoints under `https://api.bambulab.com/v1/design-user-service/my/filament/v2` confirmed.
- Design agreed: standalone project, write support planned, per-spool entities toggleable via options flow.
- **Phase 0 PASSED (2026-08-27)**: read AND write verified against the user's real account via `tools/phase0_verify.py` (~34 spools; full-object PUT works; `/filament/config` needs auth despite Studio source comment). Token cache `tools/.bambu_token.json` is local/gitignored.
- **Phases 1+2 SHIPPED (2026-08-27)**: repo live at github.com/Timmes123/ha-bambu-filaments, CI (hassfest + HACS action) green on main. Releases: v0.1.0 (read-only MVP) and v0.2.0 (adds `set_remaining`/`set_note` actions), both with `bambu_filaments.zip` asset (zip_release flow). Brand icons in `custom_components/bambu_filaments/brand/` + repo topics were required to pass the HACS action. Import smoke test passed against homeassistant==2026.8.3 in the local `.venv`.
- **LIVE and validated (2026-08-27, v0.3.1)**: installed via HACS on the user's HA, account configured by the user, 34 spools synced. v0.3.0 redesigned the model per user request: one HA device per spool (via_device -> "Bambu Filament Library" hub) with remaining-%/remaining-weight sensors and a delete-from-cloud button; official webshop color names (localized, via runtime-fetched `filaments_color_codes.json` from the BambuStudio repo, cached 7 days in HA storage); actions create_spool/delete_spool/set_remaining/set_note/refresh. Create/delete round trip tested live (create via action → device appeared → deleted via button → device gone). Login double-email fixed in v0.3.0 (Bambu auto-sends a code on the login attempt; never request another automatically).
- Gotchas learned: create body needs `#RRGGBB` color WITHOUT alpha and no colors/note/status fields (400 otherwise); never rename unique_ids between releases (v0.3.0 duplicated the total sensor, fixed in v0.3.1); per-spool cleanup keys on the `{entry_id}-spool-<int>` unique_id prefix, so aggregate unique_ids must not match it; PS 5.1 native-arg quoting breaks `git commit -m` messages containing double quotes (tag then pointed at the wrong commit — re-tag with `git tag -f`).
- **v0.4.0 (2026-08-27)**: ships `custom:bambu-filaments-card` (vanilla web component in `www/`, served via `frontend.py` + auto-registered Lovelace resource with `?v=<version>`; manifest needs `dependencies: ["http", "lovelace"]` for hassfest). Card reads the aggregate spools sensor attributes (auto-discovered), DE/EN, visual editor; options: group_by line/material/none, sort, show_empty/archived/location/code/note/delete, compact, thresholds, max_height. New integration option `color_language` (auto/de/en) — Bambu's color DB has empty `de` names for several colors, fallback is EN (same as Studio). Test dashboard "Filamente" (`/bambu-filamente/spulen`) created on the live HA with two card variants. README got My-HA install/setup badges.
- Next ideas (user roadmap): AMS-RFID linkage to ha-bambulab tray sensors.
- The user's live HA is reachable via MCP; the Bambu printer integration (cloud mode) is installed there, printers: A1 Mini + A2L, each with AMS.

## Hard rule: deployment only via HACS releases (same as ha-better-todo)

No direct file deployment into the live Home Assistant (`ha_write_file` for integration code is forbidden). Develop locally → commit → bump `manifest.json` → tagged GitHub release (`gh` CLI at `C:\Program Files\GitHub CLI\gh.exe`, not on PATH) → update via HACS → restart HA → verify via MCP (read-only). Once the repo exists, mirror ha-better-todo's release setup (zip_release, draft-with-asset flow).

## Security rules for this project

- Never ask for, read, echo, or store the user's Bambu password/tokens in chat, files tracked by git, or logs. The Phase-0 script prompts interactively; the token cache stays local and gitignored.
- Diagnostics in the integration must redact tokens, RFIDs, device serials.

## Conventions

- User speaks German — respond in German. Repo files (README, code comments, docs) in English.
- HA timezone: Europe/Berlin.
- Windows/PowerShell 5.1 gotcha (from ha-better-todo): write UTF-8 files without BOM — use `[System.IO.File]::WriteAllText` with `UTF8Encoding($false)`, not `Set-Content -Encoding utf8`; hassfest rejects BOMs.
- README must state clearly: unofficial reverse-engineered cloud API, requires Bambu cloud account (no LAN mode), ~90-day re-login, may break at any time.
