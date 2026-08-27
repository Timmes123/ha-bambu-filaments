# Draft: HACS default-store submission plan

> Status: DRAFT — do not submit until the user gives the go. Two PRs are
> required, in this order. Everything below is prepared; submitting is a
> 15-minute job once approved.

## Prerequisites (all already met)

- [x] Public repo with description, topics (`hacs`, `home-assistant`, `integration`, …) and README
- [x] `hacs.json` with `name`, `zip_release`, `filename`
- [x] Tagged GitHub releases with the `bambu_filaments.zip` asset
- [x] `manifest.json` with domain, name, codeowners, version, documentation, issue_tracker
- [x] HACS action + hassfest green in CI (weekly schedule + on push)
- [x] Brand images ready (256 px + 512 px PNG in `custom_components/bambu_filaments/brand/`)

## PR 1 — home-assistant/brands (required first)

Fork https://github.com/home-assistant/brands and add:

```
custom_integrations/bambu_filaments/icon.png       (256×256, our brand/icon.png)
custom_integrations/bambu_filaments/icon@2x.png    (512×512, our brand/icon@2x.png)
```

PR title: `Add bambu_filaments`

PR text draft:

> Adds the icon for the `bambu_filaments` custom integration
> (https://github.com/Timmes123/ha-bambu-filaments), a HACS integration that
> surfaces the Bambu Lab cloud filament library in Home Assistant.
> Icon is original artwork created for this project.

Notes: the brands repo CI checks image sizes/optimization — run their
`hassfest brands` locally or just rely on the PR check; images may need
`optipng`/`zopflipng` optimization if the bot complains.

## PR 2 — hacs/default (after brands PR is merged)

Fork https://github.com/hacs/default and add one line to the `integration`
file (alphabetical position):

```
Timmes123/ha-bambu-filaments
```

PR checklist answers (from the hacs/default template):
- Repository is public, has a description and topics ✔
- I am the owner of the repository ✔ (submitted from the Timmes123 account)
- The repository passes the HACS action with `category: integration` ✔ (link the latest green run)
- Integration is in `custom_components/bambu_filaments/` with `manifest.json` ✔
- Added to home-assistant/brands ✔ (link PR 1)

PR text draft:

> **Bambu Filaments** — surfaces the Bambu Lab cloud filament library
> (Filament Manager, Bambu Studio 2.6+/Handy) in Home Assistant: one device
> per spool with remaining-weight sensors, bidirectional create/delete,
> official color names, plus a bundled dashboard card.
>
> - Repo: https://github.com/Timmes123/ha-bambu-filaments
> - HACS action run: <link latest green Validate run>
> - Brands PR: <link merged PR 1>
> - The README clearly discloses that this uses an unofficial cloud API and
>   requires a Bambu cloud account.

## After acceptance

- Remove the "custom repository" install step from README (HACS search will find it).
- Keep the My-HA badge — it works for default-store repos too.
