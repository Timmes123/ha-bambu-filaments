# HA-Bambu-Filaments

Custom Home Assistant integration ("Bambu Filaments", domain `bambu_filaments`) that surfaces the Bambu Lab cloud Filament Manager (spool inventory from Bambu Studio 2.6.1+/Handy) in Home Assistant. Will be published on GitHub (account: **Timmes123**, repo `ha-bambu-filaments`, public, MIT) and installed via HACS as a custom repository.

Authoritative documents:
- `RESEARCH.md` — API research (endpoints, auth, schemas, risks). Factual basis; verified 2026-08-27.
- `SPEC.md` — agreed design (architecture, entities, phases). Keep updated when decisions change.

## Project status (2026-08-27)

- Research complete: cloud endpoints under `https://api.bambulab.com/v1/design-user-service/my/filament/v2` confirmed.
- Design agreed: standalone project, write support planned, per-spool entities toggleable via options flow.
- **Phase 0 PASSED (2026-08-27)**: read AND write verified against the user's real account via `tools/phase0_verify.py` (~34 spools; full-object PUT works; `/filament/config` needs auth despite Studio source comment). Token cache `tools/.bambu_token.json` is local/gitignored.
- Phase 1 (read-only MVP integration) in development.
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
