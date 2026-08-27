# Bambu Filaments for Home Assistant

[![Validate](https://github.com/Timmes123/ha-bambu-filaments/actions/workflows/validate.yml/badge.svg)](https://github.com/Timmes123/ha-bambu-filaments/actions/workflows/validate.yml)
[![GitHub release](https://img.shields.io/github/v/release/Timmes123/ha-bambu-filaments)](https://github.com/Timmes123/ha-bambu-filaments/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Community Forum](https://img.shields.io/badge/community-forum-41BDF5.svg?logo=homeassistant&logoColor=white)](https://community.home-assistant.io/t/bambu-filaments-your-bambu-lab-cloud-filament-library-spools-colors-remaining-weight-in-ha/1022849)

Bring your **Bambu Lab cloud filament library** (the *Filament Manager* introduced in Bambu Studio 2.6.1+ and the Bambu app) into Home Assistant: every spool in your account — vendor, material, color, remaining weight — as sensors you can automate on.

This integration is about your **account-level spool inventory**. It complements (and does not replace) printer integrations that expose live AMS data from the printer itself.

<img src="https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/card-overview.png" width="480" alt="Bambu Filaments card showing the full spool library grouped by filament line">


## ⚠️ Important disclaimer

- This integration uses an **unofficial, reverse-engineered Bambu Lab cloud API**. It is not affiliated with or endorsed by Bambu Lab, and it **may stop working at any time** if Bambu Lab changes their cloud.
- It **requires a Bambu Lab cloud account**. The filament library only exists in the cloud — there is no LAN-only mode for this data.
- Bambu login tokens expire after roughly **90 days**. When that happens, Home Assistant will prompt you to re-authenticate (usually via an email verification code).
- The remaining-weight values are what Bambu's cloud reports: they are updated by slicer consumption deduction and AMS syncs, not by a live scale.

## Features

- **One device per spool** (optional, on by default) named with the official webshop color in your HA language (e.g. *PETG HF Forest Green*, or a custom name you gave the spool), carrying a remaining-% sensor (with a color-swatch entity picture and full details as attributes), a remaining-weight sensor, and a **Delete from Bambu Cloud** button.
- **Official color names** — spool colors are resolved to Bambu's localized webshop color names and color codes via the public Bambu Studio color database (fetched at runtime and cached).
- **Aggregate sensors** on the hub device — number of active spools (full inventory and per-material remaining weights as attributes) and total remaining filament in grams.
- **Bidirectional sync** — spools added or removed in Bambu Studio or the Bambu app appear/disappear in Home Assistant on the next poll; spools created or deleted from Home Assistant appear there too.
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
- **One device per spool** (default on) — turn off if you only want the aggregate sensors.
- **Include inactive spools** (default off) — also create devices for archived/empty spools.
- **Color name language** (default automatic) — force English or German color names; Bambu's own database leaves some colors untranslated, those fall back to English.

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
| `bambu_filaments.set_filament_id` | `spool_id`, `filament_id` | Link a spool to a Bambu slicer profile (e.g. `GFA00` = Bambu PLA Basic, `GFL99` = Generic PLA) so Bambu Studio can assign it with matching print settings; `""` unlinks |
| `bambu_filaments.create_spool` | `vendor`, `material`, `name`, `color`, `total_g`, `remaining_g`, `filament_id`, `display_name` | Add a new spool to the cloud library (pass `filament_id: ""` for custom/third-party brands) |
| `bambu_filaments.delete_spool` | `spool_id` | Delete a spool from the cloud library |
| `bambu_filaments.get_catalog` | – | Returns the vendor/product combinations the cloud accepts (response data) |

`spool_id` is the cloud id of the spool — shown as the `spool_id` attribute on every spool remaining sensor and in the aggregate sensor's spool list. The cloud-write actions (`set_remaining`, `set_note`, `set_filament_id`, `create_spool`, `delete_spool`) are **admin-only** — they irreversibly modify your Bambu account (automations are unaffected).

## Dashboard card

The integration ships and auto-registers `custom:bambu-filaments-card` — no extra install. Minimal config (the card finds the spools sensor automatically):

```yaml
type: custom:bambu-filaments-card
```

### Examples

**Full library**, grouped by filament line with per-group totals. `combine: true` merges identical spools into one ×n row with summed remaining weight:

```yaml
type: custom:bambu-filaments-card
combine: true
```

<img src="https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/card-combine.png" width="400" alt="Card grouped by filament line with combined spools">

**Low-stock watchlist** — only colors with at most 500 g left across all their spools, emptiest first:

```yaml
type: custom:bambu-filaments-card
title: Low stock
group_by: none
combine: true
sort: remaining_asc
max_remaining_g: 500
compact: true
```

<img src="https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/card-low-stock.png" width="400" alt="Compact low-stock card filtered to 500 g">

**What's loaded right now** — only spools currently sitting in a printer/AMS, with delete buttons enabled:

```yaml
type: custom:bambu-filaments-card
title: Loaded right now
group_by: none
only_in_printer: true
show_delete: true
```

<img src="https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/card-loaded.png" width="400" alt="Card filtered to spools loaded in a printer">

**Adding spools without leaving the dashboard** — the card's "Add spool" button opens a small dialog with vendor/filament dropdowns fed by the official cloud catalog, a native color picker, and an optional custom display name. Picking **"Custom / third-party…"** unlocks free-text brand and material — so a *Flashforge PLA Burnt Titanium* can be registered with its real brand name, which even the official Bambu apps don't offer. A **slicer profile** dropdown links the custom spool to an official Bambu filament profile (defaults to the matching Generic one), so Bambu Studio can assign the spool with sensible print settings; without a profile Studio treats the spool as unsupported:

<img src="https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/card-add-dialog.png" width="340" alt="In-card dialog for adding a new spool"> <img src="https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/card-add-custom.png" width="340" alt="Custom third-party brand mode of the add dialog">

Everything is also configurable in the **visual editor**, including material filter checkboxes generated from your own inventory:

<img src="https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/card-editor.png" width="400" alt="Visual card editor">

### All options

| Option | Default | Description |
|---|---|---|
| `entity` | auto | The aggregate spools sensor |
| `title` | "Filament" | Card title ("" hides the header) |
| `group_by` | `line` | `line` (brand + product), `product` (product line across all brands, e.g. one "PLA Matte" group), `material`, or `none` |
| `sort` | `name` | `name`, `remaining_asc`, `remaining_desc` |
| `combine` | `false` | Merge identical spools (same vendor/product/color) into one ×n row with summed remaining — a color with enough backup spools then no longer counts as low |
| `max_remaining_g` | – | Filter: only show entries with at most this many grams left |
| `max_remaining_pct` | – | Filter: only show entries at or below this remaining % |
| `materials` | – | Filter: list of materials to include (e.g. `[PLA, PETG]`) |
| `only_in_printer` | `false` | Filter: only spools currently loaded in a printer/AMS |
| `max_items` | – | Cap the number of rows after sorting (top-N list) |
| `show_empty` | `true` | Include spools with 0 g left |
| `show_archived` | `false` | Include archived/inactive spools |
| `show_location` | `true` | Show printer/AMS slot for mounted spools |
| `show_code` | `true` | Show Bambu color code and hex |
| `show_note` | `false` | Show the spool note |
| `show_delete` | `false` | Trash icon per row (deletes from the cloud after confirmation) |
| `show_add` | `true` | "Add spool" button that opens an in-card dialog (vendor, material, product line, color picker, weights) — for third-party spools too |
| `compact` | `false` | Slimmer rows without the meta line |
| `low_threshold` | `20` | Bar turns red below this % |
| `warn_threshold` | `50` | Bar turns orange below this % |
| `max_height` | – | Scroll after this many pixels |

## Feedback

Questions, ideas or feedback? Join the [community forum thread](https://community.home-assistant.io/t/bambu-filaments-your-bambu-lab-cloud-filament-library-spools-colors-remaining-weight-in-ha/1022849) or open an [issue](https://github.com/Timmes123/ha-bambu-filaments/issues).

## Credits

Built on the community's documentation of the Bambu cloud API, in particular [OpenBambuAPI](https://github.com/Doridian/OpenBambuAPI) and the open-source [Bambu Studio](https://github.com/bambulab/BambuStudio) code.

## License

[MIT](LICENSE)
