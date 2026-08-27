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

- **One device per spool** (optional, on by default) named with the official webshop color (e.g. *PETG HF Waldgrün*), carrying a remaining-% sensor (with a color-swatch entity picture and full details as attributes), a remaining-weight sensor, and a **Delete from Bambu Cloud** button.
- **Official color names** — spool colors are resolved to Bambu's localized webshop color names and color codes via the public Bambu Studio color database (fetched at runtime and cached).
- **Aggregate sensors** on the hub device — number of active spools (full inventory and per-material remaining weights as attributes) and total remaining filament in grams.
- **Bidirectional sync** — spools added or removed in Bambu Studio/Handy appear/disappear in Home Assistant on the next poll; spools created or deleted from Home Assistant appear in Studio/Handy.
- **Write actions** — `set_remaining`, `set_note`, `create_spool`, `delete_spool`; plus `refresh` to poll on demand.
- **Dashboard card** — a `custom:bambu-filaments-card` shipped with the integration (auto-registered, no extra install): spool list in the style of Bambu Studio's Filament Manager with color swatches, remaining bars and per-group totals; configurable grouping (filament line/material/none), sorting, compact mode, thresholds, optional delete buttons — with a full UI editor.
- **Options** — polling interval, per-spool devices on/off, include inactive spools, color name language (auto/German/English — Bambu's own database leaves some colors untranslated, those fall back to English just like in Bambu Studio).
- Full config flow with email-code (incl. resend) and two-factor login support, re-auth flow, diagnostics (tokens and RFIDs redacted), English and German translations.

## Installation (HACS)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Timmes123&repository=ha-bambu-filaments&category=integration)

1. Click the badge above (or add `https://github.com/Timmes123/ha-bambu-filaments` manually in HACS under *Custom repositories* as an **Integration**).
2. Install **Bambu Filaments** and restart Home Assistant.
3. Set up the integration:

   [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=bambu_filaments)

4. Sign in with your Bambu Lab account (region, email, password). If Bambu sends you a verification code by email, enter it when prompted.

## Devices & entities

**Hub device "Bambu Filament Library":**

| Entity | State | Notes |
|---|---|---|
| `sensor.…_spools` | Number of active spools | Attributes: full spool list, remaining grams per material |
| `sensor.…_total_remaining_filament` | Total remaining grams | Active spools only |

**Per spool device** (e.g. *PLA Matte Charcoal*, linked to the hub):

| Entity | State/Action | Notes |
|---|---|---|
| Remaining | Remaining % | Color-swatch picture; attributes: remaining/total g, material, color hex + official color name/code, vendor, status, note, mount location |
| Remaining weight | Remaining grams | |
| Delete from Bambu Cloud | Button | Deletes the spool in the cloud; the device disappears on the next sync |

## Options

Open the integration's *Configure* dialog:

- **Polling interval** (default 15 min) — the cloud data changes slowly; Bambu itself syncs AMS weights at most every 10 minutes while printing.
- **One sensor per spool** (default on) — turn off if you only want the aggregate sensors.
- **Include inactive spools** (default off) — also create sensors for archived/empty spools.

## FAQ

**Does this control my printer?** No. It only reads your cloud filament inventory. Nothing is sent to your printers.

**Why do I have to log in again after a few months?** Bambu cloud tokens expire after ~90 days and cannot be refreshed programmatically. Home Assistant will show a re-authentication prompt.

**Where does my password go?** Only to Bambu Lab's login endpoint, exactly like logging in from Bambu Studio. Home Assistant stores the resulting token, never the password.

## Actions

| Action | Fields | Effect |
|---|---|---|
| `bambu_filaments.refresh` | – | Re-fetch the library from the cloud now |
| `bambu_filaments.set_remaining` | `spool_id`, `remaining_g` | Set a spool's remaining filament weight (grams) |
| `bambu_filaments.set_note` | `spool_id`, `note` | Set a spool's note text |
| `bambu_filaments.create_spool` | `vendor`, `material`, `name`, `color`, `total_g`, `remaining_g`, `filament_id` | Add a new spool to the cloud library |
| `bambu_filaments.delete_spool` | `spool_id` | Delete a spool from the cloud library |

`spool_id` is the cloud id of the spool — shown as the `spool_id` attribute on every spool remaining sensor and in the aggregate sensor's spool list.

## Dashboard card

The integration ships and auto-registers `custom:bambu-filaments-card`. Minimal config:

```yaml
type: custom:bambu-filaments-card
```

The card finds the spools sensor automatically. All options (also available in the visual editor):

| Option | Default | Description |
|---|---|---|
| `entity` | auto | The aggregate spools sensor |
| `title` | "Filament" | Card title ("" hides the header) |
| `group_by` | `line` | `line` (vendor + product), `material`, or `none` |
| `sort` | `name` | `name`, `remaining_asc`, `remaining_desc` |
| `show_empty` | `true` | Include spools with 0 g left |
| `show_archived` | `false` | Include archived/inactive spools |
| `show_location` | `true` | Show printer/AMS slot for mounted spools |
| `show_code` | `true` | Show Bambu color code and hex |
| `show_note` | `false` | Show the spool note |
| `show_delete` | `false` | Trash icon per row (deletes from the cloud after confirmation) |
| `compact` | `false` | Slimmer rows without the meta line |
| `low_threshold` | `20` | Bar turns red below this % |
| `warn_threshold` | `50` | Bar turns orange below this % |
| `max_height` | – | Scroll after this many pixels |

## Roadmap

- Linking library spools to live AMS tray data by RFID.

## Credits

Built on the community's documentation of the Bambu cloud API, in particular [OpenBambuAPI](https://github.com/Doridian/OpenBambuAPI) and the open-source [Bambu Studio](https://github.com/bambulab/BambuStudio) code.

## License

[MIT](LICENSE)
