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

Bring your **Bambu Lab cloud filament library** (the *Filament Manager* introduced in Bambu Studio 2.6.1+ and the Bambu app) into Home Assistant: every spool in your account — vendor, material, color, remaining weight — as sensors you can automate on.

This integration is about your **account-level spool inventory**. It complements (and does not replace) printer integrations that expose live AMS data from the printer itself — and, if the [Bambu Lab printer integration (ha-bambulab)](https://github.com/greghesp/ha-bambulab) is installed, it bridges the two: spools loaded into an AMS get registered, remaining weights stay current and empty spools are booked, all without opening a Bambu app.

<img src="https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/card-overview.png" width="480" alt="Bambu Filaments card showing the full spool library grouped by filament line">


## ⚠️ Important disclaimer

- This integration uses an **unofficial, reverse-engineered Bambu Lab cloud API**. It is not affiliated with or endorsed by Bambu Lab, and it **may stop working at any time** if Bambu Lab changes their cloud.
- It **requires a Bambu Lab cloud account**. The filament library only exists in the cloud — there is no LAN-only mode for this data.
- Bambu login tokens expire after roughly **90 days**. When that happens, Home Assistant will prompt you to re-authenticate (usually via an email verification code).
- The remaining-weight values are what Bambu's cloud reports. Bambu only updates them while Studio or the Bambu app is open (AMS estimate for official spools, nothing at all for third-party spools) — this integration can take over that job, see [Keep remaining weights current](#keep-remaining-weights-current--without-opening-an-app). None of it is a live scale.

## Features

- **One device per spool** (optional, on by default) named with the official webshop color in your HA language (e.g. *PETG HF Forest Green*, or a custom name you gave the spool), carrying a remaining-% sensor (with a color-swatch entity picture and full details as attributes), a remaining-weight sensor, and a **Delete from Bambu Cloud** button.
- **Official color names** — spool colors are resolved to Bambu's localized webshop color names and color codes via the public Bambu Studio color database (fetched at runtime and cached).
- **Aggregate sensors** on the hub device — number of active spools (full inventory and per-material remaining weights as attributes) and total remaining filament in grams.
- **Bidirectional sync** — spools added or removed in Bambu Studio or the Bambu app appear/disappear in Home Assistant on the next poll (or immediately after an AMS change when the printer integration is present); spools created or deleted from Home Assistant appear there too.
- **Remaining weights that stay current** — AMS estimates pushed to the library without Studio running, runout detection, and print-usage deduction for third-party spools ([details below](#keep-remaining-weights-current--without-opening-an-app)).
- **Auto-register spools loaded into the AMS** — no more opening the Bambu app just so the cloud learns about the spool you just inserted ([details below](#auto-register-spools-you-load-into-the-ams); requires the [ha-bambulab](https://github.com/greghesp/ha-bambulab) printer integration).
- **Stock tracking without duplicates** — pre-register sealed spools manually and let the integration auto-remove the manual entry the moment the real spool is first loaded into the AMS ([details below](#track-unopened-stock--without-duplicates)) — something even Bambu's own apps can't do.
- **Write actions** — `set_remaining`, `set_note`, `set_filament_id`, `update_spool`, `create_spool`, `delete_spool`; plus `refresh` to poll on demand.
- **Dashboard card** — a `custom:bambu-filaments-card` shipped with the integration (auto-registered, no extra install): spool list in the style of Bambu Studio's Filament Manager with color swatches, remaining bars, Studio-style AMS locations, RFID/manual badges and per-group totals; ×n stacks for identical spools, filters (low stock, materials, loaded only), add/edit dialogs incl. third-party brands and multi-spool stock — with a full UI editor.
- **Everything optional** — all of the above bridge features are toggles (shown right after login and behind *Configure*), plus polling interval, per-spool devices on/off and color name language (auto/German/English — Bambu's own database leaves some colors untranslated, those fall back to English just like in Bambu Studio).
- Full config flow with email-code (incl. resend) and two-factor login support, re-auth flow, diagnostics (tokens and RFIDs redacted), English and German translations.

## Auto-register spools you load into the AMS

Bambu's own apps only add a freshly loaded official spool to the cloud library once you open the printer page in Bambu Handy or Bambu Studio. Until then the spool is in your AMS but not in your inventory.

Enable **"Auto-register new RFID spools loaded into the AMS"** in the integration options and the integration does it for you: on every sync it compares the RFID spools currently sitting in your AMS units with the library and creates the missing ones exactly the way Studio does — same brand/product/color, remaining weight from the AMS, and the printer/AMS/slot position. Spools you deliberately deleted from the library while they were still loaded are left alone.

> **Requires the [Bambu Lab printer integration (ha-bambulab)](https://github.com/greghesp/ha-bambulab).** Its AMS slot sensors are the only source for what is physically in your AMS — the cloud library API itself does not know about unregistered spools. Without that integration the option is greyed out in the options dialog. Nothing needs to be configured: printers and AMS units are detected from the sensors automatically. Third-party spools (no RFID) are never touched.

## Keep remaining weights current — without opening an app

Your printer never talks to the filament library. Remaining weights only change when Bambu Studio or the Bambu app is open and pushes the AMS estimate — so a spool that ran out overnight still shows as half full the next day, and third-party spools never move at all (verified against the Studio source and real prints).

Three options in the integration settings close that gap, each independently switchable:

- **Sync remaining weight from the AMS** — every change of the AMS estimate for official RFID spools is pushed to the library (same cloud call Studio uses, same 10-minute cooldown while printing). A slot reading 0 % books the spool as empty immediately.
- **Mark a spool as empty when it is removed while a print was drawing from it** — the safe runout rule: a spool that was the active tray of a running or paused print (an AMS backup switch is remembered too) and is taken out before that print ends is set to 0 g. Spools removed after a finished print, or mid-print with more than 20 % left (a filament change), are never touched — real 2 % leftovers stay in your inventory. An optional percentage rule ("also mark as empty when removed with ≤ N % left", default off) exists for those who prefer it.
- **Deduct print usage from manually created spools** — Bambu books nothing for third-party spools. With this on, every print job finished after enabling is booked **once** against the manual spool the library shows in that slot, using the per-slot grams the cloud records for the job (multi-color prints included, prints started from the printer or the app included). Processed jobs are remembered, jobs already booked elsewhere are skipped, RFID spools are never touched, cancelled jobs are booked proportionally when the progress was observed. Accuracy is that of the slicer estimate (purge and prime-tower waste is only partly included).

> The first two need the [Bambu Lab printer integration (ha-bambulab)](https://github.com/greghesp/ha-bambulab) and are greyed out without it. Usage deduction works from the cloud alone.

## Track unopened stock — without duplicates

Bought five spools of a color but only loaded one? Register the sealed ones manually so your inventory reflects what's actually on the shelf — in one step, just like in Studio: the card's add dialog has a **Count** field, the edit dialog (cog icon) of any existing spool offers **"Add more spools of this type"**, and the `create_spool` action takes `count`.

With the official apps that backfires later: the moment such a spool is first loaded into an AMS, the Bambu cloud creates a **new** entry from the spool's RFID tag — it never links up with your manual entry, which stays behind as a duplicate you have to hunt down and delete by hand.

This integration closes that gap. Enable **"Auto-remove manual duplicates when a spool is loaded into the AMS"** in the integration options and, whenever a new AMS-registered spool appears in the library, exactly **one** matching manual spool — same brand, same product, same color, still full — is deleted from the cloud automatically. Spools you personalized (custom name or note) are kept the longest, partially used manual spools are never touched, and the feature only ever reacts to spools that are genuinely new since the previous sync. Your stock count stays correct from sealed box to AMS — a reconciliation even Bambu's own apps don't offer.

## Installation (HACS)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Timmes123&repository=ha-bambu-filaments&category=integration)

1. Click the badge above (or add `https://github.com/Timmes123/ha-bambu-filaments` manually in HACS under *Custom repositories* as an **Integration**).
2. Install **Bambu Filaments** and restart Home Assistant.
3. Set up the integration:

   [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=bambu_filaments)

4. Sign in with your Bambu Lab account (region, email, password). If Bambu sends you a verification code by email, enter it when prompted.
5. On the **Features** step pick what the integration should do beyond mirroring your library (auto-register, remaining-weight sync, runout detection, usage booking, auto-dedup, color language). All of it stays changeable later via the integration's *Configure* button.

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

The same form is shown as the **Features** step during setup and later behind the integration's *Configure* button:

- **Polling interval** (default 15 min) — the cloud data changes slowly; Bambu itself syncs AMS weights at most every 10 minutes while printing. With the printer integration present, AMS and print-status changes trigger an extra refresh right away.
- **One device per spool** (default on) — turn off if you only want the aggregate sensors.
- **Auto-register new RFID spools loaded into the AMS** (default off; greyed out unless the [ha-bambulab](https://github.com/greghesp/ha-bambulab) printer integration is installed) — create library entries for official spools the AMS sees but the library lacks ([details](#auto-register-spools-you-load-into-the-ams)).
- **Sync remaining weight from the AMS** (default off; needs ha-bambulab), **Mark a spool as empty when it is removed while a print was drawing from it** (default off; needs ha-bambulab), **Also mark as empty when removed with ≤ N % left** (default 0 = off; needs ha-bambulab), **Deduct print usage from manually created spools** (default off) — see [Keep remaining weights current](#keep-remaining-weights-current--without-opening-an-app).
- **Auto-remove manual duplicates** (default off) — when a new AMS-registered spool appears, delete one matching full, manually created spool from the cloud library ([details](#track-unopened-stock--without-duplicates)).
- **Color name language** (default automatic) — force English or German color names; Bambu's own database leaves some colors untranslated, those fall back to English.

## FAQ

**Does this control my printer?** No. Nothing is ever sent to your printers. The integration reads and writes your *cloud filament library*; what it knows about your AMS comes from the Bambu Lab printer integration's sensors inside Home Assistant.

**Do I need the Bambu Lab printer integration (ha-bambulab)?** Only for the AMS bridge features (auto-register, remaining-weight sync, runout detection). Library mirroring, the card, stock tracking and print-usage deduction work with the cloud account alone.

**Why do I have to log in again after a few months?** Bambu cloud tokens expire after ~90 days and cannot be refreshed programmatically. Home Assistant will show a re-authentication prompt.

**Where does my password go?** Only to Bambu Lab's login endpoint, exactly like logging in from Bambu Studio. Home Assistant stores the resulting token, never the password.

## Actions

| Action | Fields | Effect |
|---|---|---|
| `bambu_filaments.refresh` | – | Re-fetch the library from the cloud now |
| `bambu_filaments.set_remaining` | `spool_id`, `remaining_g` | Set a spool's remaining filament weight (grams) |
| `bambu_filaments.set_note` | `spool_id`, `note` | Set a spool's note text |
| `bambu_filaments.set_filament_id` | `spool_id`, `filament_id` | Link a spool to a Bambu slicer profile (e.g. `GFA00` = Bambu PLA Basic, `GFL99` = Generic PLA) so Bambu Studio can assign it with matching print settings; `""` unlinks |
| `bambu_filaments.update_spool` | `spool_id` + any of `vendor`, `material`, `name`, `color`, `total_g`, `remaining_g`, `note`, `filament_id`, `display_name` | Change fields of an existing spool — only the provided fields are written; empty strings clear custom name/note/profile |
| `bambu_filaments.create_spool` | `vendor`, `material`, `name`, `color`, `total_g`, `remaining_g`, `filament_id`, `display_name`, `note`, `count` | Add a new spool to the cloud library (pass `filament_id: ""` for custom/third-party brands; the note is written right after creation; `count` 1–50 creates that many identical spools) |
| `bambu_filaments.delete_spool` | `spool_id` | Delete a spool from the cloud library |
| `bambu_filaments.get_catalog` | – | Returns the vendor/product combinations the cloud accepts (response data) |

`spool_id` is the cloud id of the spool — shown as the `spool_id` attribute on every spool remaining sensor and in the aggregate sensor's spool list. The cloud-write actions (`set_remaining`, `set_note`, `set_filament_id`, `update_spool`, `create_spool`, `delete_spool`) are **admin-only** — they irreversibly modify your Bambu account (automations are unaffected).

## Dashboard card

The integration ships and auto-registers `custom:bambu-filaments-card` — no extra install. Minimal config (the card finds the spools sensor automatically):

```yaml
type: custom:bambu-filaments-card
```

### Examples

**Full library**, grouped by filament line with per-group totals. `combine: true` merges identical spools into one ×n row with summed remaining weight — click the row to expand the individual spools (emptiest first, each editable):

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

**What's loaded right now** — only spools currently sitting in a printer/AMS:

```yaml
type: custom:bambu-filaments-card
title: Loaded right now
group_by: none
only_in_printer: true
```

<img src="https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/card-loaded.png" width="400" alt="Card filtered to spools loaded in a printer">

**Adding spools without leaving the dashboard** — the card's "Add spool" button opens a small dialog with vendor/filament dropdowns fed by the official cloud catalog, a native color picker, and an optional custom display name. Picking **"Custom / third-party…"** unlocks free-text brand and material — so a *Flashforge PLA Burnt Titanium* can be registered with its real brand name, which even the official Bambu apps don't offer. A **slicer profile** dropdown links the custom spool to an official Bambu filament profile (defaults to the matching Generic one), so Bambu Studio can assign the spool with sensible print settings; without a profile Studio treats the spool as unsupported:

<img src="https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/card-add-dialog.png" width="340" alt="In-card dialog for adding a new spool"> <img src="https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/card-add-custom.png" width="340" alt="Custom third-party brand mode of the add dialog">

The result in Bambu Studio: the third-party spool appears in the AMS filament picker **under its own brand** and is assignable with the linked profile's print settings — something even Bambu's own apps can't do for custom brands. The spool's **note** shows up there too, as Studio's "remark" line:

<img src="https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/studio-assign.png" width="700" alt="Bambu Studio AMS dialog listing the custom Flashforge spool under its own brand">

**Editing spools** — every row has a cog icon (toggleable via `show_edit`) that opens the same dialog prefilled with the spool's data: rename, change brand/material/product, pick another color, correct the weights, edit the note, or link/unlink a slicer profile. Only the fields you actually change are written to the cloud. Deleting the spool from the cloud library also lives in this dialog (with confirmation):

<img src="https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/card-edit-dialog.png" width="340" alt="In-card dialog for editing an existing spool">

Everything is also configurable in the **visual editor**, including material filter checkboxes generated from your own inventory:

<img src="https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/card-editor.png" width="400" alt="Visual card editor">

### All options

| Option | Default | Description |
|---|---|---|
| `entity` | auto | The aggregate spools sensor |
| `title` | "Filament" | Card title ("" hides the header) |
| `group_by` | `line` | `line` (brand + product), `product` (product line across all brands, e.g. one "PLA Matte" group), `material`, or `none` |
| `sort` | `name` | `name`, `remaining_asc`, `remaining_desc` |
| `combine` | `false` | Merge identical spools (same vendor/product/color) into one ×n row with summed remaining — a color with enough backup spools then no longer counts as low. Clicking a ×n row expands the individual spools, each with its own edit icon |
| `max_remaining_g` | – | Filter: only show entries with at most this many grams left |
| `max_remaining_pct` | – | Filter: only show entries at or below this remaining % |
| `materials` | – | Filter: list of materials to include (e.g. `[PLA, PETG]`) |
| `only_in_printer` | `false` | Filter: only spools currently loaded in a printer/AMS |
| `max_items` | – | Cap the number of rows after sorting (top-N list) |
| `show_empty` | `true` | Include spools with 0 g left. When off, empty spools are removed before `combine` merges stacks, so a ×n stack shrinks to its non-empty members |
| `show_location` | `true` | Show where a mounted spool sits, in Bambu Studio notation: printer · AMS model · slot (e.g. `A2L · AMS 2 Pro · A1`; second AMS = B1–B4, AMS HT = `HT-A`, external holder = `External`) |
| `show_code` | `true` | Show Bambu color code and hex |
| `show_note` | `false` | Show the spool note |
| `show_type` | `false` | Badge showing how each spool entered the library — `RFID` (tag-registered by the AMS) or `manual`; combined stacks show the mix (e.g. `RFID ×5` `manual ×2`) |
| `show_edit` | `true` | Cog icon per row that opens the edit dialog (rename, weights, color, profile, note — and delete from the cloud) |
| `show_add` | `true` | "Add spool" button that opens an in-card dialog (vendor, material, product line, color picker, weights) — for third-party spools too |
| `compact` | `false` | Slimmer rows without the meta line |
| `low_threshold` | `20` | Bar turns red below this % |
| `warn_threshold` | `50` | Bar turns orange below this % |
| `max_height` | – | Scroll after this many pixels |

## Feedback

Questions, ideas or feedback? Join the [community forum thread](https://community.home-assistant.io/t/bambu-filaments-your-bambu-lab-cloud-filament-library-spools-colors-remaining-weight-in-ha/1022849) or open an [issue](https://github.com/Timmes123/ha-bambu-filaments/issues).

## ☕ Support

If this integration is useful to you and you want to support its development:

[![Ko-fi](https://img.shields.io/badge/Ko--fi-Buy%20me%20a%20coffee-FF5E5B?logo=kofi&logoColor=white)](https://ko-fi.com/timmes123)
[![PayPal](https://img.shields.io/badge/PayPal-Donate-00457C?logo=paypal&logoColor=white)](https://www.paypal.com/paypalme/timmes123)

## Credits

Built on the community's documentation of the Bambu cloud API, in particular [OpenBambuAPI](https://github.com/Doridian/OpenBambuAPI) and the open-source [Bambu Studio](https://github.com/bambulab/BambuStudio) code.

## License

[MIT](https://github.com/Timmes123/ha-bambu-filaments/blob/main/LICENSE)
