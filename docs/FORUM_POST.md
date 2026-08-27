# Draft: Home Assistant community forum post

> Post to https://community.home-assistant.io/c/projects/ (category: Projects / Custom Integrations).
> Suggested title below. Images use absolute raw URLs so they render on Discourse.

---

**Title:** Bambu Filaments — your Bambu Lab cloud filament library (spools, colors, remaining weight) in HA

Hi everyone! :wave:

Bambu Studio 2.6+ and the Handy app got a built-in **Filament Manager**: every spool you own lives in your Bambu account with brand, color and remaining weight, updated automatically from the AMS and after every print. Great feature — but it lives only inside Bambu's apps.

**Bambu Filaments** brings that library into Home Assistant.

## What it does

- :white_check_mark: **One device per spool** — named with the official webshop color in your HA language (*PETG HF Forest Green*) or your own custom name, with a remaining-% sensor (color-swatch picture), a remaining-weight sensor and a delete button.
- :bar_chart: **Aggregate sensors** — spool count and total remaining grams (per-material breakdown in the attributes), ready for low-stock automations.
- :arrows_counterclockwise: **Bidirectional sync** — spools added/removed in Studio, Handy or via the AMS show up or disappear in HA on the next poll; spools created or deleted from HA appear in Studio/Handy.
- :heavy_plus_sign: **Add spools from the dashboard** — the bundled card has an add dialog with vendor/filament dropdowns fed live from Bambu's own catalog, a color picker and an optional custom name. There's even a **custom/third-party mode**: register e.g. a *Flashforge PLA "Burnt Titanium"* under its real brand name — something the official apps don't offer.
- :black_joker: **Dashboard card included** (auto-registers, no extra install): grouped like Bambu Studio's Filament Manager, with combine-identical-spools (×n with summed remaining), filters (below X g / X %, materials, loaded-in-printer, top-N), compact mode and a full visual editor. English + German.
- :hammer_and_wrench: **Actions** for automations: `set_remaining`, `set_note`, `create_spool`, `delete_spool`, `refresh`, `get_catalog`.

## Screenshots

Full library, grouped by filament line, identical spools combined:

![Card overview](https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/card-combine.png)

Low-stock watchlist (only colors with ≤ 500 g left across all their spools):

![Low stock](https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/card-low-stock.png)

Adding a spool — official catalog or custom third-party brand:

![Add dialog](https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/card-add-dialog.png)
![Custom brand](https://raw.githubusercontent.com/Timmes123/ha-bambu-filaments/main/images/card-add-custom.png)

## Installation

1. Add `https://github.com/Timmes123/ha-bambu-filaments` as a HACS custom repository (Integration), install **Bambu Filaments**, restart.
2. Settings → Devices & services → Add integration → *Bambu Filaments* → sign in with your Bambu account (email verification code and 2FA are supported).

The card auto-registers — just add `custom:bambu-filaments-card` to a dashboard. Full option docs in the [README](https://github.com/Timmes123/ha-bambu-filaments).

## Honest fine print

- This uses Bambu's **unofficial cloud API** (the same one Studio/Handy talk to). It can break whenever Bambu changes their cloud.
- It **requires a Bambu cloud account** — the filament library only exists in the cloud, so pure LAN-mode setups can't use it.
- Bambu tokens expire after ~90 days; HA will show a re-authentication prompt (email code) when that happens.
- Remaining weights are what Bambu computes (slicer deduction + AMS sync), not a live scale.

## Status

v1.0.0 is out — the integration went through a full security/correctness audit before the stable release. Feedback, bug reports and ideas are very welcome, here or on [GitHub](https://github.com/Timmes123/ha-bambu-filaments/issues). :pray:
