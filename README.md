# Bambu Filaments for Home Assistant

[![Validate](https://github.com/Timmes123/ha-bambu-filaments/actions/workflows/validate.yml/badge.svg)](https://github.com/Timmes123/ha-bambu-filaments/actions/workflows/validate.yml)
[![GitHub release](https://img.shields.io/github/v/release/Timmes123/ha-bambu-filaments)](https://github.com/Timmes123/ha-bambu-filaments/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Bring your **Bambu Lab cloud filament library** (the *Filament Manager* introduced in Bambu Studio 2.6.1+ and Bambu Handy) into Home Assistant: every spool in your account — vendor, material, color, remaining weight — as sensors you can automate on.

This integration is about your **account-level spool inventory**. It complements (and does not replace) printer integrations that expose live AMS data from the printer itself.

## ⚠️ Important disclaimer

- This integration uses an **unofficial, reverse-engineered Bambu Lab cloud API**. It is not affiliated with or endorsed by Bambu Lab, and it **may stop working at any time** if Bambu Lab changes their cloud.
- It **requires a Bambu Lab cloud account**. The filament library only exists in the cloud — there is no LAN-only mode for this data.
- Bambu login tokens expire after roughly **90 days**. When that happens, Home Assistant will prompt you to re-authenticate (usually via an email verification code).
- The remaining-weight values are what Bambu's cloud reports: they are updated by slicer consumption deduction and AMS syncs, not by a live scale.

## Features

- **Spool sensors** — one sensor per spool in your library (optional, on by default): state is remaining %, attributes include remaining/total grams, material, color hex, vendor, status, notes, and where the spool is currently mounted (printer/AMS/slot).
- **Aggregate sensors** — number of active spools (with the full inventory and per-material remaining weights as attributes) and total remaining filament in grams.
- **Options** — polling interval, per-spool entities on/off, include inactive spools.
- **`bambu_filaments.refresh` action** — pull the library from the cloud on demand.
- Full config flow with email-code and two-factor login support, re-auth flow, diagnostics (tokens and RFIDs redacted), English and German translations.

## Installation (HACS)

1. In HACS, choose *Custom repositories* and add `https://github.com/Timmes123/ha-bambu-filaments` as an **Integration**.
2. Install **Bambu Filaments** and restart Home Assistant.
3. Go to *Settings → Devices & services → Add integration* and search for **Bambu Filaments**.
4. Sign in with your Bambu Lab account (region, email, password). If Bambu sends you a verification code by email, enter it when prompted.

## Entities

| Entity | State | Notes |
|---|---|---|
| `sensor.bambu_filament_library_spools` | Number of active spools | Attributes: full spool list, remaining grams per material |
| `sensor.bambu_filament_library_total_remaining_filament` | Total remaining grams | Active spools only |
| `sensor.…_<spool>` (per spool) | Remaining % | Attributes: remaining/total g, material, color, vendor, RFID-backed id, mount location |

## Options

Open the integration's *Configure* dialog:

- **Polling interval** (default 15 min) — the cloud data changes slowly; Bambu itself syncs AMS weights at most every 10 minutes while printing.
- **One sensor per spool** (default on) — turn off if you only want the aggregate sensors.
- **Include inactive spools** (default off) — also create sensors for archived/empty spools.

## FAQ

**Does this control my printer?** No. It only reads your cloud filament inventory. Nothing is sent to your printers.

**Why do I have to log in again after a few months?** Bambu cloud tokens expire after ~90 days and cannot be refreshed programmatically. Home Assistant will show a re-authentication prompt.

**Where does my password go?** Only to Bambu Lab's login endpoint, exactly like logging in from Bambu Studio. Home Assistant stores the resulting token, never the password.

## Roadmap

- Write support: adjust remaining weight, edit notes/status, create and archive spools from Home Assistant.
- Linking library spools to live AMS tray data by RFID.
- A dedicated dashboard card.

## Credits

Built on the community's documentation of the Bambu cloud API, in particular [OpenBambuAPI](https://github.com/Doridian/OpenBambuAPI) and the open-source [Bambu Studio](https://github.com/bambulab/BambuStudio) code.

## License

[MIT](LICENSE)
