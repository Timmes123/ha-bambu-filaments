"""Render the README screenshots of the Bambu Filaments card.

Usage (from the repo root, needs `pip install playwright` + `playwright
install chromium` in a venv):

    python tools/screenshots/take_shots.py

harness.html mocks the hass object (spool data, catalog service) and provides
minimal ha-card/ha-icon stand-ins so the card renders 1:1 outside Home
Assistant. Element screenshots land in images/.
"""

import pathlib
import shutil

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).parent
REPO = HERE.parent.parent
OUT = REPO / "images"
OUT.mkdir(exist_ok=True)

shutil.copy(
    REPO / "custom_components/bambu_filaments/www/bambu-filaments-card.js",
    HERE / "bambu-filaments-card.js",
)

SHOTS = ["overview", "combine", "low-stock", "loaded", "editor"]

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1700, "height": 1600}, device_scale_factor=2)
    page.goto((HERE / "harness.html").as_uri())
    page.wait_for_function("document.title === 'ready'")
    page.wait_for_timeout(200)
    # expand one combined stack so the combine shot shows the child rows
    page.locator("#shot-combine .row[data-key]").first.click()
    page.wait_for_timeout(200)
    for shot in SHOTS:
        page.locator(f"#shot-{shot}").screenshot(path=str(OUT / f"card-{shot}.png"))
        print("saved", f"card-{shot}.png")
    # open the in-card add dialog and shoot the dialog box itself
    page.locator("#shot-overview .addrow").click()
    page.wait_for_timeout(200)
    page.locator("#f-color").fill("#4e00ad")  # purple-blue, like a real spool
    page.locator(".dlg").screenshot(path=str(OUT / "card-add-dialog.png"))
    print("saved card-add-dialog.png")
    # switch to custom/third-party mode, fill it like a real Flashforge spool
    page.locator("#f-vendor").select_option("__custom__")
    page.locator("#f-cvendor").fill("Flashforge")
    page.locator("#f-cmaterial").fill("PLA")
    page.locator("#f-cname").fill("PLA Pro")
    page.locator("#f-display").fill("Burnt Titanium")
    page.wait_for_timeout(100)
    page.locator(".dlg").screenshot(path=str(OUT / "card-add-custom.png"))
    print("saved card-add-custom.png")
    # close it and open the edit dialog for the Flashforge spool (prefilled
    # custom mode, Generic PLA profile preselected, note filled)
    page.locator(".dlg-cancel").click()
    page.wait_for_timeout(100)
    page.locator("#shot-overview .row").filter(has_text="Burnt Titanium").locator(".edit").click()
    page.wait_for_timeout(200)
    page.locator(".dlg").screenshot(path=str(OUT / "card-edit-dialog.png"))
    print("saved card-edit-dialog.png")
    browser.close()
(HERE / "bambu-filaments-card.js").unlink()
print("done ->", OUT)
