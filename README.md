# Bambu Filaments for Home Assistant

[![GitHub release](https://img.shields.io/github/v/release/Timmes123/ha-bambu-filaments)](https://github.com/Timmes123/ha-bambu-filaments/releases/latest)
[![Pre-release](https://img.shields.io/github/v/release/Timmes123/ha-bambu-filaments?include_prereleases&label=pre-release&color=orange)](https://github.com/Timmes123/ha-bambu-filaments/releases)
[![Validate](https://github.com/Timmes123/ha-bambu-filaments/actions/workflows/validate.yml/badge.svg)](https://github.com/Timmes123/ha-bambu-filaments/actions/workflows/validate.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Downloads](https://img.shields.io/github/downloads/Timmes123/ha-bambu-filaments/total?label=downloads)](https://github.com/Timmes123/ha-bambu-filaments/releases)
[![License](https://img.shields.io/github/license/Timmes123/ha-bambu-filaments)](https://github.com/Timmes123/ha-bambu-filaments/blob/main/LICENSE)
[![Community Forum](https://img.shields.io/badge/community-forum-41BDF5.svg?logo=homeassistant&logoColor=white)](https://community.home-assistant.io/t/bambu-filaments-your-bambu-lab-cloud-filament-library-spools-colors-remaining-weight-in-ha/1022849)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-donate-FF5E5B?logo=kofi&logoColor=white)](https://ko-fi.com/timmes123)
[![PayPal](https://img.shields.io/badge/PayPal-donate-00457C?logo=paypal&logoColor=white)](https://www.paypal.com/paypalme/timmes123)

Your **Bambu Lab cloud filament library** (the *Filament Manager* of Bambu Studio 2.6.1+ and the Bambu app) in Home Assistant: every spool with vendor, material, official color name and remaining weight — as devices, sensors, actions and a dashboard card. With the [Bambu Lab printer integration](https://github.com/greghesp/ha-bambulab) installed it also does what Bambu's apps only do while they are open: registers spools you load into the AMS, keeps remaining weights current and books empty spools.

<img src="https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/card-overview.png" width="480" alt="Bambu Filaments card showing the full spool library grouped by filament line">

## ⚠️ Disclaimer

Unofficial, reverse-engineered cloud API — not affiliated with Bambu Lab, may break at any time. Needs a Bambu cloud account (the library only exists in the cloud, no LAN mode). Tokens expire after ~90 days; Home Assistant then asks you to sign in again. Remaining weights are Bambu's estimates, not a scale.

## Features

- **One device per spool** with remaining % and grams, official color name, mount location and a delete button; aggregate sensors for spool count and total remaining.
- **Dashboard card** in the look of Studio's Filament Manager: grouping, sorting, ×n stacks for identical spools, filters, RFID/manual badges, add and edit dialogs — third-party brands and multi-spool stock included.
- **Actions** to create, update, delete and refresh spools; catalog lookup.
- **AMS bridge** (optional, needs ha-bambulab): auto-register loaded spools, sync AMS remaining weights, book runouts.
- **Stock tracking**: pre-register sealed spools, auto-remove the manual entry when the real spool hits the AMS, deduct print usage from third-party spools.
- Email-code and 2FA login, re-auth, diagnostics, English and German.

## What the Bambu apps don't do — and this integration does

**Register spools you load.** Bambu only adds a freshly loaded official spool to the library when you open the printer page in Handy or Studio. The integration watches the AMS slot sensors and registers missing RFID spools within seconds — brand, color, weight and printer/AMS/slot position included. Spools you deleted on purpose while still loaded are left alone.

**Keep weights current.** The printer never talks to the library; weights only change while an app is open. Enabled, the integration pushes the AMS estimate of official spools whenever it changes (same cloud call as Studio, same 10-minute cooldown while printing) and books a spool as empty when it is removed while a print was drawing from it. Spools removed after a finished print, or mid-print with plenty left, are never touched.

**Book third-party usage.** Nobody deducts consumption for non-RFID spools — not Studio, not the app, not the cloud. Enabled, every finished print job is booked once against the manual spool the library shows in that slot, using the per-slot grams the cloud records (multi-color prints included, wherever the print was started). Jobs are remembered so nothing is booked twice; RFID spools are untouched.

**No duplicate stock.** Register sealed spools in one step (count field in the card, `count` in `create_spool`). When the real spool is first loaded, Bambu creates a new RFID entry and your manual one would stay behind — the integration removes exactly one matching full manual spool automatically.

All of it is off by default and toggled on the **Features** step after login or later via *Configure*. The AMS features are greyed out until the [Bambu Lab printer integration](https://github.com/greghesp/ha-bambulab) is installed; usage booking and stock dedup work from the cloud alone.

## Installation (HACS)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Timmes123&repository=ha-bambu-filaments&category=integration)

1. Add the repository via the badge (or manually as a custom **Integration** repository), install **Bambu Filaments**, restart Home Assistant. Requires Home Assistant 2026.8 or newer.
2. Set up the integration and sign in with your Bambu Lab account (email code or 2FA if asked):

   [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=bambu_filaments)

3. Pick your features on the second step. Everything can be changed later via *Configure*.

## Devices & entities

**Hub "Bambu Filament Library":**

| Entity | State | Notes |
|---|---|---|
| `sensor.…_spools` | Number of spools | Attributes: full spool list, remaining grams per material |
| `sensor.…_total_remaining_filament` | Total remaining grams | |

**Per spool** (e.g. *PLA Matte Charcoal*):

| Entity | State/Action | Notes |
|---|---|---|
| Remaining | Remaining % | Color-swatch picture; attributes: grams, material, color hex + official name/code, vendor, note, mount location |
| Remaining weight | Remaining grams | |
| Delete from Bambu Cloud | Button | Deletes the spool in the cloud |

## Options

Shown on the **Features** step during setup and behind *Configure*: polling interval (default 15 min; AMS and print changes trigger extra refreshes), one device per spool, auto-remove manual duplicates, auto-register AMS spools, sync remaining weight from the AMS, mark as empty on runout (plus an optional percent rule), deduct print usage, color name language (auto/German/English).

## Actions

| Action | Fields | Effect |
|---|---|---|
| `bambu_filaments.refresh` | – | Re-fetch the library now |
| `bambu_filaments.set_remaining` | `spool_id`, `remaining_g` | Set remaining grams |
| `bambu_filaments.set_note` | `spool_id`, `note` | Set the note |
| `bambu_filaments.set_filament_id` | `spool_id`, `filament_id` | Link a Bambu slicer profile (`GFA00` = PLA Basic, `GFL99` = Generic PLA); `""` unlinks |
| `bambu_filaments.update_spool` | `spool_id` + any of `vendor`, `material`, `name`, `color`, `total_g`, `remaining_g`, `note`, `filament_id`, `display_name` | Change fields; only given fields are written |
| `bambu_filaments.create_spool` | `vendor`, `material`, `name`, `color`, `total_g`, `remaining_g`, `filament_id`, `display_name`, `note`, `count` | Add spool(s); `filament_id: ""` for third-party brands, `count` 1–50 |
| `bambu_filaments.delete_spool` | `spool_id` | Delete from the cloud library |
| `bambu_filaments.get_catalog` | – | Vendor/product combinations the cloud accepts (response data) |

`spool_id` is the cloud id, shown as attribute on every spool sensor. Write actions are **admin-only** — they change your Bambu account.

## Dashboard card

Ships with the integration, no extra install. Minimal config:

```yaml
type: custom:bambu-filaments-card
```

**Full library** with `combine: true` — identical spools become one ×n row, click to expand:

```yaml
type: custom:bambu-filaments-card
combine: true
```

<img src="https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/card-combine.png" width="400" alt="Card grouped by filament line with combined spools">

**Low-stock watchlist** — colors with at most 500 g left, emptiest first:

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

**Loaded right now** — `only_in_printer: true`, locations in Studio notation:

<img src="https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/card-loaded.png" width="400" alt="Card filtered to spools loaded in a printer">

**Add and edit dialogs** — catalog dropdowns, color picker, count field for stock, custom/third-party brands with a linked slicer profile so Studio can assign them, and a cog per row to edit or delete:

<img src="https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/card-add-dialog.png" width="300" alt="In-card dialog for adding a new spool"> <img src="https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/card-add-custom.png" width="300" alt="Custom third-party brand mode of the add dialog"> <img src="https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/card-edit-dialog.png" width="300" alt="In-card dialog for editing an existing spool">

A third-party spool created this way shows up in Studio's AMS picker under its own brand, note included:

<img src="https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/studio-assign.png" width="600" alt="Bambu Studio AMS dialog listing the custom Flashforge spool under its own brand">

Everything is configurable in the visual editor.

### All options

| Option | Default | Description |
|---|---|---|
| `entity` | auto | The aggregate spools sensor |
| `title` | "Filament" | Card title ("" hides the header) |
| `group_by` | `line` | `line` (brand + product), `product` (product across brands), `material`, `none` |
| `sort` | `name` | `name`, `remaining_asc`, `remaining_desc` |
| `combine` | `false` | Merge identical spools into one ×n row with summed remaining; click to expand |
| `max_remaining_g` | – | Only entries with at most this many grams left |
| `max_remaining_pct` | – | Only entries at or below this remaining % |
| `materials` | – | Materials to include, e.g. `[PLA, PETG]` |
| `only_in_printer` | `false` | Only spools loaded in a printer/AMS |
| `max_items` | – | Cap the number of rows after sorting |
| `show_empty` | `true` | Include spools with 0 g left (filtered before `combine`) |
| `show_location` | `true` | Mount location in Studio notation (`A2L · AMS 2 Pro · A1`, second AMS B1–B4, AMS HT `HT-A`, external `External`) |
| `show_code` | `true` | Bambu color code and hex |
| `show_note` | `false` | Spool note |
| `show_type` | `false` | `RFID` / `manual` badge; stacks show the mix |
| `show_edit` | `true` | Cog icon per row (edit, delete) |
| `show_add` | `true` | "Add spool" button |
| `compact` | `false` | Slimmer rows without the meta line |
| `low_threshold` | `20` | Bar turns red below this % |
| `warn_threshold` | `50` | Bar turns orange below this % |
| `max_height` | – | Scroll after this many pixels |

## FAQ

**Does this control my printer?** No — nothing is sent to your printers. AMS information comes from the Bambu Lab printer integration's sensors inside Home Assistant.

**Do I need ha-bambulab?** Only for the AMS features. Library, card, stock dedup and usage booking work with the cloud account alone.

**Why sign in again after a few months?** Bambu tokens expire after ~90 days and cannot be refreshed. Your password only goes to Bambu's login endpoint and is never stored.

## Feedback

[Community forum thread](https://community.home-assistant.io/t/bambu-filaments-your-bambu-lab-cloud-filament-library-spools-colors-remaining-weight-in-ha/1022849) or [GitHub issues](https://github.com/Timmes123/ha-bambu-filaments/issues).

## ☕ Support

[![Ko-fi](https://img.shields.io/badge/Ko--fi-Buy%20me%20a%20coffee-FF5E5B?logo=kofi&logoColor=white)](https://ko-fi.com/timmes123)
[![PayPal](https://img.shields.io/badge/PayPal-Donate-00457C?logo=paypal&logoColor=white)](https://www.paypal.com/paypalme/timmes123)

## Credits

Built on the community's documentation of the Bambu cloud API, in particular [OpenBambuAPI](https://github.com/Doridian/OpenBambuAPI) and the open-source [Bambu Studio](https://github.com/bambulab/BambuStudio) code.

## License

[MIT](https://github.com/Timmes123/ha-bambu-filaments/blob/main/LICENSE)
