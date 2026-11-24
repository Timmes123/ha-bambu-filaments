/* Bambu Filaments Card — shipped with the bambu_filaments integration.
 * Vanilla web component, no external dependencies. Reads the spool list from
 * the integration's aggregate "spools" sensor attributes.
 */

// Must match "version" in manifest.json (enforced by CI). The backend sends
// its version in the spools sensor attributes; a mismatch means this browser
// tab still runs a cached copy of the card from before an update.
const CARD_VERSION = "2.4.0";

// HA's frontend service worker matches its cache entries without the query
// string, so the ?v=<version> bump on the Lovelace resource does not defeat it
// and a plain reload keeps serving the old card. Drop our own cache entries
// first, then reload.
const CARD_FILE = "bambu-filaments-card.js";

async function reloadCard() {
  try {
    for (const key of await caches.keys()) {
      const cache = await caches.open(key);
      for (const req of await cache.keys()) {
        if (req.url.includes(CARD_FILE)) await cache.delete(req);
      }
    }
  } catch (e) {
    console.warn("bambu-filaments-card: could not clear the card cache", e);
  }
  location.reload();
}

console.info(
  "%c BAMBU-FILAMENTS-CARD %c v" + CARD_VERSION + " ",
  "color: white; background: #3f51b5; font-weight: bold;",
  "color: #3f51b5; background: white; font-weight: bold;"
);

const STR = {
  en: {
    spools: (n) => `${n} spool${n === 1 ? "" : "s"}`,
    colors: (n) => `${n} color${n === 1 ? "" : "s"}`,
    empty: "No spools found.",
    no_entity: "Bambu Filaments spools sensor not found. Is the integration set up?",
    stale: "Bambu Filaments was updated - reload the page for the new card.",
    reload: "Reload",
    delete_confirm: (n) => `Delete "${n}" from the Bambu cloud library?`,
    title: "Filament",
    add_btn: "Add spool",
    d_title: "New spool",
    d_edit_title: "Edit spool",
    d_update: "Save changes",
    d_delete: "Delete from cloud",
    d_note: "Note",
    d_vendor: "Vendor",
    d_material: "Material",
    d_name: "Product line (e.g. PLA Matte)",
    d_product: "Filament",
    d_custom: "Custom / third-party…",
    d_brand: "Brand (e.g. Flashforge)",
    d_line: "Product line (optional)",
    d_profile: "Slicer profile (Bambu Studio)",
    d_profile_none: "No profile (not selectable in Studio)",
    d_profile_own: "My presets",
    d_profile_current: "Current profile",
    d_display: "Custom name (optional)",
    d_loading: "Loading catalog…",
    d_color: "Color",
    d_total: "Spool size (g)",
    d_remaining: "Remaining (g)",
    d_count: "Count",
    d_code: "Bambu color code (on the box, e.g. 13504)",
    d_code_unknown: "Unknown code - pick the filament below.",
    d_dup_title: "Add more spools of this type",
    d_dup_hint: "Creates full manual spools (stock) with the same brand, product, color and size - name and note are not copied.",
    d_dup_btn: (n) => `Create ${n} spool${n === 1 ? "" : "s"}`,
    d_save: "Add to library",
    d_cancel: "Cancel",
    d_saving: "Saving…",
    d_error: "The cloud rejected the spool. Check material and name.",
    // editor
    e_entity: "Spools sensor (empty = automatic)",
    e_title: "Title",
    e_group: "Group by", g_line: "Filament line (brand + product)", g_product: "Product line (all brands)", g_material: "Material", g_none: "No grouping",
    e_sort: "Sort by", s_name: "Name", s_rem_asc: "Remaining (low first)", s_rem_desc: "Remaining (high first)",
    s_code: "Bambu color code (palette order)",
    e_combine: "Combine identical spools (sum remaining)",
    e_filters: "Filters",
    e_max_g: "Only show below (g, empty = off)",
    e_max_pct: "Only show below (%, empty = off)",
    e_min_pct: "Only show from (%, empty = off)",
    e_materials: "Materials",
    e_vendors: "Brands",
    e_products: "Product lines",
    m_include: "Only checked (none = all)",
    m_exclude: "All except checked",
    e_type: "Spool type",
    ty_all: "All", ty_rfid: "RFID only", ty_manual: "Manual only (e.g. sealed stock)",
    e_only_printer: "Only spools loaded in a printer/AMS",
    e_max_items: "Max. rows (empty = all)",
    e_show_empty: "Show empty spools",
    e_show_location: "Show printer/AMS location",
    e_show_code: "Show color code and hex",
    e_show_note: "Show note",
    e_show_type: "Show spool type (RFID / manual)",
    type_ams: "RFID",
    type_manual: "manual",
    loc_ext: "External",
    e_show_edit: "Show edit button",
    e_show_details: "Tap a spool for details and history",
    x_storage: "In storage",
    x_location: "Location",
    x_profile: "Slicer profile",
    x_type: "Type",
    x_note: "Note",
    x_history: (d) => `Remaining weight, last ${d} days`,
    x_no_history: "No history: the spool's remaining-weight sensor was not found.",
    x_edit: "Edit",
    x_weigh: "Remaining (g)",
    x_save: "Save",
    x_full: "Full",
    x_full_confirm: (n, g) => `Mark "${n}" as full (${g})?`,
    x_saved: "Saved",
    x_error: "Saving failed.",
    x_close: "Close",
    e_show_add: "Show add-spool button",
    e_compact: "Compact rows",
    e_layout: "Layout", l_list: "List", l_tiles: "Tiles",
    e_show_images: "Shop photos instead of color swatches (Bambu colors, needs the shop sync)",
    e_low: "Red below (%)",
    e_warn: "Orange below (%)",
    e_max_height: "Max. height (px, empty = unlimited)",
    // missing-colors mode
    e_mode: "Show",
    mo_spools: "My spools",
    mo_missing: "Missing colors (current Bambu shop range)",
    e_missing: "Missing colors",
    e_missing_products: "Product lines (none = all)",
    e_missing_empty: "Colors I only have empty spools of count as missing",
    e_missing_noshop: "Product lines appear once the shop range is loaded.",
    mi_title: "Missing colors",
    mi_count: (n) => `${n} missing`,
    mi_off: "The shop comparison is off. Turn on \"Compare with the current Bambu shop range\" in the integration options.",
    mi_loading: "Reading the Bambu shop range - this takes a few minutes after enabling the option.",
    mi_error: "The shop range could not be loaded.",
    mi_none: "You have every color of the selected product lines.",
    mi_sold_out: "sold out",
    mi_as_of: "Shop range of",
  },
  de: {
    spools: (n) => `${n} Spule${n === 1 ? "" : "n"}`,
    colors: (n) => `${n} Farbe${n === 1 ? "" : "n"}`,
    empty: "Keine Spulen gefunden.",
    no_entity: "Bambu-Filaments-Spulensensor nicht gefunden. Ist die Integration eingerichtet?",
    stale: "Bambu Filaments wurde aktualisiert – Seite neu laden für die neue Karte.",
    reload: "Neu laden",
    delete_confirm: (n) => `„${n}" aus der Bambu-Cloud-Bibliothek löschen?`,
    title: "Filament",
    add_btn: "Neue Spule anlegen",
    d_title: "Neue Spule",
    d_edit_title: "Spule bearbeiten",
    d_update: "Änderungen speichern",
    d_delete: "Aus Cloud löschen",
    d_note: "Notiz",
    d_vendor: "Hersteller",
    d_material: "Material",
    d_name: "Sorte (z. B. PLA Matte)",
    d_product: "Filament",
    d_custom: "Benutzerdefiniert / Fremdmarke…",
    d_brand: "Marke (z. B. Flashforge)",
    d_line: "Sorte (optional)",
    d_profile: "Slicer-Profil (Bambu Studio)",
    d_profile_none: "Kein Profil (in Studio nicht zuweisbar)",
    d_profile_own: "Eigene Profile",
    d_profile_current: "Aktuelles Profil",
    d_display: "Eigener Name (optional)",
    d_loading: "Katalog wird geladen…",
    d_color: "Farbe",
    d_total: "Spulengröße (g)",
    d_remaining: "Restgewicht (g)",
    d_count: "Anzahl",
    d_code: "Bambu-Farbcode (auf der Packung, z. B. 13504)",
    d_code_unknown: "Unbekannter Code - Filament unten auswählen.",
    d_dup_title: "Weitere Spulen dieses Typs anlegen",
    d_dup_hint: "Legt volle manuelle Spulen (Vorrat) mit gleicher Marke, Sorte, Farbe und Größe an - Name und Notiz werden nicht übernommen.",
    d_dup_btn: (n) => `${n} Spule${n === 1 ? "" : "n"} anlegen`,
    d_save: "Zur Bibliothek hinzufügen",
    d_cancel: "Abbrechen",
    d_saving: "Speichern…",
    d_error: "Die Cloud hat die Spule abgelehnt. Material und Sorte prüfen.",
    e_entity: "Spulen-Sensor (leer = automatisch)",
    e_title: "Titel",
    e_group: "Gruppieren nach", g_line: "Filamentlinie (Hersteller + Sorte)", g_product: "Sorte (alle Hersteller)", g_material: "Material", g_none: "Keine Gruppierung",
    e_sort: "Sortieren nach", s_name: "Name", s_rem_asc: "Restmenge (wenig zuerst)", s_rem_desc: "Restmenge (viel zuerst)",
    s_code: "Bambu-Farbcode (Farbpalette)",
    e_combine: "Gleiche Filamente zusammenfassen (Rest addieren)",
    e_filters: "Filter",
    e_max_g: "Nur anzeigen unter (g, leer = aus)",
    e_max_pct: "Nur anzeigen unter (%, leer = aus)",
    e_min_pct: "Nur anzeigen ab (%, leer = aus)",
    e_materials: "Materialien",
    e_vendors: "Hersteller",
    e_products: "Sorten",
    m_include: "Nur angehakte (nichts = alle)",
    m_exclude: "Alle außer angehakte",
    e_type: "Spulentyp",
    ty_all: "Alle", ty_rfid: "Nur RFID", ty_manual: "Nur manuelle (z. B. Lagerware)",
    e_only_printer: "Nur eingelegte Spulen (Drucker/AMS)",
    e_max_items: "Max. Zeilen (leer = alle)",
    e_show_empty: "Leere Spulen anzeigen",
    e_show_location: "Drucker-/AMS-Position anzeigen",
    e_show_code: "Farbcode und Hex anzeigen",
    e_show_note: "Notiz anzeigen",
    e_show_type: "Spulentyp anzeigen (RFID / manuell)",
    type_ams: "RFID",
    type_manual: "manuell",
    loc_ext: "Extern",
    e_show_edit: "Bearbeiten-Button anzeigen",
    e_show_details: "Antippen öffnet Details und Verlauf",
    x_storage: "Im Lager",
    x_location: "Ort",
    x_profile: "Slicer-Profil",
    x_type: "Typ",
    x_note: "Notiz",
    x_history: (d) => `Restgewicht der letzten ${d} Tage`,
    x_no_history: "Kein Verlauf: Der Restgewicht-Sensor dieser Spule wurde nicht gefunden.",
    x_edit: "Bearbeiten",
    x_weigh: "Restgewicht (g)",
    x_save: "Speichern",
    x_full: "Voll",
    x_full_confirm: (n, g) => `„${n}" als voll speichern (${g})?`,
    x_saved: "Gespeichert",
    x_error: "Speichern fehlgeschlagen.",
    x_close: "Schließen",
    e_show_add: "Neue-Spule-Button anzeigen",
    e_compact: "Kompakte Zeilen",
    e_layout: "Ansicht", l_list: "Liste", l_tiles: "Kacheln",
    e_show_images: "Shop-Fotos statt Farbfeld (Bambu-Farben, braucht den Shop-Abgleich)",
    e_low: "Rot unter (%)",
    e_warn: "Orange unter (%)",
    e_max_height: "Max. Höhe (px, leer = unbegrenzt)",
    e_mode: "Anzeigen",
    mo_spools: "Meine Spulen",
    mo_missing: "Fehlende Farben (aktuelles Bambu-Shop-Sortiment)",
    e_missing: "Fehlende Farben",
    e_missing_products: "Sorten (nichts = alle)",
    e_missing_empty: "Farben, von denen ich nur leere Spulen habe, gelten als fehlend",
    e_missing_noshop: "Die Sorten erscheinen, sobald das Shop-Sortiment geladen ist.",
    mi_title: "Fehlende Farben",
    mi_count: (n) => `${n} fehlen`,
    mi_off: "Der Shop-Abgleich ist aus. In den Optionen der Integration „Mit dem aktuellen Bambu-Shop-Sortiment abgleichen“ einschalten.",
    mi_loading: "Das Bambu-Shop-Sortiment wird gelesen - das dauert nach dem Einschalten ein paar Minuten.",
    mi_error: "Das Shop-Sortiment konnte nicht geladen werden.",
    mi_none: "Du hast alle Farben der ausgewählten Sorten.",
    mi_sold_out: "ausverkauft",
    mi_as_of: "Shop-Sortiment vom",
  },
};

const DEFAULTS = {
  mode: "spools",
  layout: "list",
  show_images: false,
  missing_count_empty: true,
  group_by: "line",
  sort: "name",
  combine: false,
  only_in_printer: false,
  show_add: true,
  show_empty: true,
  show_location: true,
  show_code: true,
  show_note: false,
  show_type: false,
  show_edit: true,
  show_details: true,
  details_days: 30,
  compact: false,
  low_threshold: 20,
  warn_threshold: 50,
};

function lang(hass) {
  const l = (hass?.locale?.language || "en").split("-")[0];
  return STR[l] ? l : "en";
}

function findSpoolsEntity(hass) {
  for (const [id, st] of Object.entries(hass.states)) {
    if (!id.startsWith("sensor.")) continue;
    if (Array.isArray(st.attributes?.spools) && st.attributes?.remaining_g_by_material) {
      if (hass.entities?.[id] && hass.entities[id].platform !== "bambu_filaments") continue;
      return id;
    }
  }
  return null;
}

const HEX_RE = /^#?[0-9A-F]{6}([0-9A-F]{2})?$/;

function normHex(v) {
  // The cloud sometimes returns colors without the leading "#" (AMS-created
  // spools) - normalize before using as CSS or as a combine key. Anything
  // that is not a 6/8-digit hex returns "" (the value ends up in CSS, so
  // strict validation doubles as the injection guard).
  if (!v) return "";
  v = String(v).trim().toUpperCase();
  if (!HEX_RE.test(v)) return "";
  return v.startsWith("#") ? v : `#${v}`;
}

// The three list filters of the card (config key -> spool value). Each has a
// "<key>_mode": "include" (default, only listed values) or "exclude" (all but
// the listed values); an empty list never filters.
const LIST_FILTERS = {
  materials: (s) => s.material || "",
  vendors: (s) => s.vendor || "",
  products: (s) => s.name || s.material || "",
};

function listFilter(config, key) {
  const list = config[key];
  if (!Array.isArray(list) || !list.length) return null;
  const exclude = config[`${key}_mode`] === "exclude";
  const get = LIST_FILTERS[key];
  return (s) => list.includes(get(s)) !== exclude;
}

// Shop range data is refreshed by the backend once a day.
const SHOP_MAX_AGE_MS = 30 * 60 * 1000;
const SAFE_URL_RE = /^https:\/\/[A-Za-z0-9.-]+\/[A-Za-z0-9._~\/%+,-]*(\?[A-Za-z0-9=&._-]*)?$/;

// Shop links and swatch images come from scraped pages: plain https only.
function safeUrl(u) {
  return typeof u === "string" && SAFE_URL_RE.test(u);
}

function fmtG(g) {
  if (g == null) return "?";
  return g >= 10000 ? `${(g / 1000).toFixed(1).replace(/\.0$/, "")} kg` : `${g} g`;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

// Maps the cloud's numeric amsType (Studio's DevAmsType enum) to product
// names - mirrors AMS_TYPE_NAMES in BambuStudio's filament-manager web UI.
const AMS_TYPE_NAMES = { 1: "AMS", 2: "AMS Lite", 3: "AMS 2 Pro", 4: "AMS HT", 5: "AMS Lite", 6: "AMS", 7: "AMS" };

// Studio-style slot label ("A1".."D4", second AMS = "B1".., AMS HT = "HT-A",
// external spool holder = null -> caller shows the ext label). Mirrors
// GetTrayId + transition_tridid in the BambuStudio source: letter is
// 'A' + amsId, number is slotId + 1.
function slotLabel(s) {
  const ams = Number(s.ams_id);
  const slot = Number(s.slot_id);
  if (s.slot_id == null || s.slot_id === "" || !Number.isFinite(slot)) return null;
  if (Number(s.ams_type) === 4 || (Number.isFinite(ams) && ams >= 128)) {
    const i = ams - 128;
    return i >= 0 && i < 26 ? `HT-${String.fromCharCode(65 + i)}` : null;
  }
  if (!Number.isFinite(ams) || ams < 0 || ams > 25) return `Slot ${slot + 1}`;
  return `${String.fromCharCode(65 + ams)}${slot + 1}`;
}

// "A2L · AMS 2 Pro · A1" - same three parts, same order as Bambu Studio's
// filament manager (formatSlotLocation). extLabel is the localized text for
// the external spool holder (slotId 255 / amsType 0).
function locationLabel(s, extLabel) {
  if (!s.device_name) return null;
  const isExt = String(s.slot_id) === "255" || Number(s.ams_type) === 0;
  const parts = [s.device_name];
  if (isExt) {
    parts.push(extLabel);
  } else {
    const model = AMS_TYPE_NAMES[Number(s.ams_type)];
    if (model) parts.push(model);
    const sl = slotLabel(s);
    if (sl) parts.push(sl);
  }
  return parts.join(" · ");
}

function swatchStyle(spool) {
  const colors = (spool.colors && spool.colors.length ? spool.colors : [spool.color])
    .map(normHex).filter(Boolean);
  if (!colors.length) return "background:#888";
  if (colors.length === 1) return `background:${esc(colors[0])}`;
  return `background:linear-gradient(135deg, ${esc(colors[0])} 50%, ${esc(colors[1])} 50%)`;
}

class BambuFilamentsCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._collapsed = new Set();
    this._expandedStacks = new Set();
    this._lastRenderKey = null;
  }

  static getConfigElement() {
    return document.createElement("bambu-filaments-card-editor");
  }

  static getStubConfig(hass) {
    const entity = hass ? findSpoolsEntity(hass) : null;
    return entity ? { entity } : {};
  }

  setConfig(config) {
    this._config = { ...DEFAULTS, ...config };
    this._lastRenderKey = null;
  }

  // HA attaches a card, detaches and re-attaches it while building a view
  // (and when moving it between containers). Only a card that stays detached
  // closes its dialog - otherwise a dialog opened by a deep link on page load
  // would vanish right away.
  disconnectedCallback() {
    super.disconnectedCallback?.();
    setTimeout(() => {
      if (this.isConnected) return;
      this._dialogHost?.remove();
      this._dialogHost = null;
      this._details = null;
    }, 0);
  }

  connectedCallback() {
    if (this._lastState) this._openLinkedSpool(this._lastState);
  }

  set hass(hass) {
    this._hass = hass;
    // Cache the auto-discovered entity: hass is reassigned on every state
    // change in the whole instance, and a full hass.states scan each time is
    // wasted main-thread work on large installations.
    let entityId = this._config?.entity;
    if (!entityId) {
      if (!this._autoEntity || !hass.states[this._autoEntity]) {
        this._autoEntity = findSpoolsEntity(hass);
      }
      entityId = this._autoEntity;
    }
    const st = entityId ? hass.states[entityId] : null;
    const key = st ? `${entityId}|${st.last_updated}` : "none";
    if (key !== this._lastRenderKey || this._configDirty) {
      this._lastRenderKey = key;
      this._configDirty = false;
      this._render(st);
    }
    this._refreshDetails(st);
    this._openLinkedSpool(st);
  }

  // Deep links: `?edit_spool=<spool_id>` in the dashboard URL opens that
  // spool's edit dialog once, `?spool=<spool_id>` its details dialog (e.g.
  // from a markdown link, a push notification or a QR code). The parameter
  // is removed first, so a reload or back navigation does not reopen it.
  _openLinkedSpool(st) {
    // Not before the card is in the page (see disconnectedCallback).
    if (!st || !this.isConnected || !/[?&](edit_spool|spool)=/.test(location.search)) return;
    const params = new URLSearchParams(location.search);
    const editId = params.get("edit_spool");
    const id = Number(editId ?? params.get("spool"));
    params.delete("edit_spool");
    params.delete("spool");
    const query = params.toString();
    history.replaceState(history.state, "", `${location.pathname}${query ? `?${query}` : ""}${location.hash}`);
    const spool = (st.attributes.spools || []).find((s) => s.spool_id === id);
    if (!spool) return;
    const t = STR[lang(this._hass)];
    if (editId !== null) this._openDialog(t, spool);
    else this._openDetails(t, spool);
  }

  getCardSize() {
    return 6;
  }

  _visibleSpools(st) {
    const c = this._config;
    let spools = (st.attributes.spools || []).slice();
    // Empty spools are dropped before combining so a stack shrinks to its
    // non-empty members (×5 instead of ×7) — matching what the Bambu apps show.
    if (!c.show_empty) spools = spools.filter((s) => (s.remaining_g ?? 0) > 0);
    // Per-spool filters also run before combining: a stack mixing RFID and
    // manual spools shrinks to the members the card asks for.
    for (const key of Object.keys(LIST_FILTERS)) {
      const keep = listFilter(c, key);
      if (keep) spools = spools.filter(keep);
    }
    if (c.spool_type === "rfid") spools = spools.filter((s) => s.create_type === "ams");
    else if (c.spool_type === "manual") spools = spools.filter((s) => s.create_type === "manual");
    if (c.combine) spools = this._combine(spools);
    if (c.only_in_printer) spools = spools.filter((s) => s.in_printer);
    if (c.min_remaining_pct != null) {
      spools = spools.filter((s) => (s.total_g ? (s.remaining_g ?? 0) / s.total_g * 100 : 0) >= Number(c.min_remaining_pct));
    }
    if (c.max_remaining_g != null) spools = spools.filter((s) => (s.remaining_g ?? 0) <= Number(c.max_remaining_g));
    if (c.max_remaining_pct != null) {
      spools = spools.filter((s) => (s.total_g ? (s.remaining_g ?? 0) / s.total_g * 100 : 0) <= Number(c.max_remaining_pct));
    }
    const name = (s) => `${s.vendor || ""} ${s.name || ""} ${s.color_name || s.color || ""}`;
    const rem = (s) => (s.total_g ? (s.remaining_g ?? 0) / s.total_g : 0);
    if (c.sort === "remaining_asc") spools.sort((a, b) => rem(a) - rem(b) || name(a).localeCompare(name(b)));
    else if (c.sort === "remaining_desc") spools.sort((a, b) => rem(b) - rem(a) || name(a).localeCompare(name(b)));
    else if (c.sort === "color_code") {
      // Bambu's 5-digit codes run along the color palette within a product
      // line; spools without one (third-party brands) follow, by name.
      const code = (s) => {
        const n = Number(s.bambu_color_code);
        return s.bambu_color_code && Number.isFinite(n) ? n : Infinity;
      };
      spools.sort((a, b) => {
        const ca = code(a), cb = code(b);
        return (ca === cb ? 0 : ca < cb ? -1 : 1) || name(a).localeCompare(name(b));
      });
    }
    else spools.sort((a, b) => name(a).localeCompare(name(b)));
    if (c.max_items) spools = spools.slice(0, Number(c.max_items));
    return spools;
  }

  _combine(spools) {
    const map = new Map();
    for (const s of spools) {
      const colors = (s.colors && s.colors.length ? s.colors : [s.color]).filter(Boolean);
      const key = [s.vendor, s.name || s.material, s.display_name || "",
        ...colors.map(normHex).sort()].join("|");
      const agg = map.get(key);
      if (!agg) {
        // _spools keeps the original spool objects so an expanded stack can
        // render (and edit) each physical spool individually - locations are
        // derived from it at render time (needs the translated ext label).
        map.set(key, { ...s, _count: 1, _key: key, _spools: [s] });
      } else {
        agg._count += 1;
        agg.remaining_g = (agg.remaining_g || 0) + (s.remaining_g || 0);
        agg.total_g = (agg.total_g || 0) + (s.total_g || 0);
        agg.in_printer = agg.in_printer || s.in_printer;
        agg._spools.push(s);
      }
    }
    return [...map.values()];
  }

  _groups(spools) {
    const c = this._config;
    if (c.group_by === "none") return [[null, spools]];
    const keyFn = c.group_by === "material"
      ? (s) => s.material || "?"
      : c.group_by === "product"
        ? (s) => s.name || s.material || "?"
        : (s) => `${s.vendor || "?"} ${s.name || s.material || "?"}`;
    const map = new Map();
    for (const s of spools) {
      const k = keyFn(s);
      if (!map.has(k)) map.set(k, []);
      map.get(k).push(s);
    }
    return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }

  _render(st) {
    const t = STR[lang(this._hass)];
    const c = this._config;
    if (!st) {
      this.shadowRoot.innerHTML = `<ha-card><div class="msg">${esc(t.no_entity)}</div></ha-card>${this._css()}`;
      return;
    }
    if (c.mode === "missing") {
      this._renderMissing(st, t);
      return;
    }
    const spools = this._visibleSpools(st);
    const totalG = spools.reduce((a, s) => a + (s.remaining_g || 0), 0);
    // With combine on, one row can stand for several physical spools: count
    // the spools inside the stacks, and show the row count as colors.
    const spoolCount = (items) => items.reduce((a, s) => a + (s._count || 1), 0);
    const summary = c.combine
      ? `${t.colors(spools.length)} · ${t.spools(spoolCount(spools))}`
      : t.spools(spools.length);
    const title = c.title !== undefined ? c.title : t.title;
    // Shop photos need the shop snapshot (photo per color code).
    if (c.show_images) this._ensureShopRange();
    const tiles = c.layout === "tiles";

    let body;
    if (!spools.length) {
      body = `<div class="msg">${esc(t.empty)}</div>`;
    } else {
      body = this._groups(spools).map(([gname, items]) => {
        const gTotal = items.reduce((a, s) => a + (s.remaining_g || 0), 0);
        const collapsed = gname && this._collapsed.has(gname);
        const inner = items.map((s) => this._stack(s, t)).join("");
        const rows = collapsed ? ""
          : tiles ? `<div class="tgrid ${c.compact ? "compact" : ""}">${inner}</div>` : inner;
        const header = gname === null ? "" : `
          <div class="ghead" data-group="${esc(gname)}">
            <ha-icon icon="mdi:chevron-${collapsed ? "right" : "down"}"></ha-icon>
            <span class="gname">${esc(gname)}</span>
            <span class="chip">${spoolCount(items)}</span>
            <span class="gsum">${fmtG(gTotal)}</span>
          </div>`;
        return `<div class="group">${header}${rows}</div>`;
      }).join("");
    }

    this._lastState = st;
    const scroll = c.max_height ? `style="max-height:${Number(c.max_height)}px;overflow-y:auto"` : "";
    const backendVersion = st.attributes.version;
    const stale = backendVersion && backendVersion !== CARD_VERSION;
    this.shadowRoot.innerHTML = `
      <ha-card>
        ${stale ? `<div class="stale"><span>${esc(t.stale)}</span><button class="stale-btn">${esc(t.reload)}</button></div>` : ""}
        ${title ? `<div class="head">
          <div class="title">${esc(title)}</div>
          <div class="sum">${summary} · ${fmtG(totalG)}</div>
          ${c.show_add ? `<ha-icon class="headadd" icon="mdi:plus" title="${esc(t.add_btn)}" role="button" tabindex="0"></ha-icon>` : ""}
        </div>` : ""}
        <div class="list" ${scroll}>${body}</div>
        ${c.show_add ? `<div class="addrow"><ha-icon icon="mdi:plus"></ha-icon><span>${t.add_btn}</span></div>` : ""}
      </ha-card>${this._css()}`;

    // Add button twice: below the list and (with a title) in the header, so
    // a long list does not have to be scrolled to its end.
    this.shadowRoot.querySelectorAll(".addrow, .headadd").forEach((el) =>
      el.addEventListener("click", () => this._openDialog(t, null))
    );
    this.shadowRoot.querySelector(".stale-btn")?.addEventListener("click", () => reloadCard());

    this.shadowRoot.querySelectorAll(".ghead").forEach((el) =>
      el.addEventListener("click", () => {
        const g = el.dataset.group;
        this._collapsed.has(g) ? this._collapsed.delete(g) : this._collapsed.add(g);
        this._configDirty = true;
        this._render(st);
      })
    );
    // A combined ×n row expands/collapses its individual spools on click
    // (single rows open the details dialog, editing goes through the cog icon).
    this.shadowRoot.querySelectorAll(".item[data-key]").forEach((el) =>
      el.addEventListener("click", () => {
        const k = el.dataset.key;
        this._expandedStacks.has(k)
          ? this._expandedStacks.delete(k)
          : this._expandedStacks.add(k);
        this._configDirty = true;
        this._render(st);
      })
    );
    const findSpool = (id) => {
      for (const s of spools) {
        if (s._spools) {
          const child = s._spools.find((x) => x.spool_id === id);
          if (child) return child;
        } else if (s.spool_id === id) {
          return s;
        }
      }
      return null;
    };
    this.shadowRoot.querySelectorAll(".edit").forEach((el) =>
      el.addEventListener("click", (ev) => {
        ev.stopPropagation();
        const spool = findSpool(Number(el.dataset.spool));
        if (spool) this._openDialog(t, spool);
      })
    );
    if (c.show_details) {
      this.shadowRoot.querySelectorAll(".item.tap").forEach((el) =>
        el.addEventListener("click", () => {
          const spool = findSpool(Number(el.dataset.spool));
          if (spool) this._openDetails(t, spool);
        })
      );
    }
    this._bindPhotoFallback();
  }

  // A photo that does not load (blocked, offline, moved) is replaced by the
  // color fill kept in data-fill - also when it failed before this ran.
  _bindPhotoFallback() {
    this.shadowRoot.querySelectorAll(".ph img").forEach((img) => {
      const fallback = () => {
        const box = img.parentElement;
        if (!box) return;
        box.setAttribute("style", box.dataset.fill || "");
        box.classList.remove("ph");
        img.remove();
      };
      if (img.complete && img.naturalWidth === 0) fallback();
      else img.addEventListener("error", fallback);
    });
  }

  // Product photo of a spool's color (Bambu Lab spools with a known color
  // code, card option show_images, shop sync on) - null otherwise.
  _photoFor(s) {
    if (!this._config.show_images || s.vendor !== "Bambu Lab" || !s.bambu_color_code) return null;
    const url = this._shop?.images?.[String(s.bambu_color_code)];
    return safeUrl(url) ? url : null;
  }

  // The color square of a row / tile: the photo on a neutral background
  // (data-fill keeps the color for the load-error fallback) or the color.
  _swatchHtml(s, cls) {
    const fill = swatchStyle(s);
    const photo = this._photoFor(s);
    return photo
      ? `<span class="${cls} ph" data-fill="${fill}"><img src="${esc(photo)}" alt="" loading="lazy" referrerpolicy="no-referrer"></span>`
      : `<span class="${cls}" style="${fill}"></span>`;
  }

  // ---------------------------------------------------------- missing colors

  // The shop range only changes once a day - fetched once per card and
  // re-fetched after SHOP_MAX_AGE_MS; ownership is recomputed from the live
  // spool list on every render.
  _ensureShopRange() {
    const stale = this._shopAt && Date.now() - this._shopAt > SHOP_MAX_AGE_MS;
    if ((!this._shop && !this._shopError) || stale) this._loadShopRange();
  }

  _loadShopRange() {
    if (this._shopLoading) return;
    this._shopLoading = true;
    this._hass.callService("bambu_filaments", "get_shop_range", {}, undefined, false, true)
      .then((resp) => {
        this._shop = resp?.response || { enabled: false, colors: [] };
        this._shopError = false;
      })
      .catch(() => {
        this._shopError = true;
      })
      .finally(() => {
        this._shopLoading = false;
        this._shopAt = Date.now();
        if (this._lastState) {
          this._configDirty = true;
          this._render(this._lastState);
        }
      });
  }

  _missingColors(st) {
    const c = this._config;
    const owned = new Map();
    for (const s of st.attributes.spools || []) {
      if (s.vendor !== "Bambu Lab" || !s.bambu_color_code) continue;
      const key = `${s.bambu_color_code}|${s.filament_id || ""}`;
      const o = owned.get(key) || { full: 0, empty: 0 };
      if ((s.remaining_g ?? 0) > 0) o.full += 1;
      else o.empty += 1;
      owned.set(key, o);
    }
    const products = Array.isArray(c.missing_products) ? c.missing_products : [];
    return (this._shop?.colors || []).filter((e) => {
      if (products.length && !products.includes(e.product)) return false;
      const o = owned.get(`${e.code}|${e.filament_id || ""}`) || { full: 0, empty: 0 };
      return o.full === 0 && (c.missing_count_empty || o.empty === 0);
    });
  }

  _renderMissing(st, t) {
    const c = this._config;
    this._lastState = st;
    this._ensureShopRange();
    const title = c.title !== undefined ? c.title : t.mi_title;
    let body;
    let sum = "";
    if (!this._shop) {
      body = `<div class="msg">${esc(this._shopError ? t.mi_error : t.d_loading)}</div>`;
    } else if (!this._shop.enabled) {
      body = `<div class="msg">${esc(t.mi_off)}</div>`;
    } else if (!this._shop.fetched_at) {
      body = `<div class="msg">${esc(t.mi_loading)}</div>`;
    } else {
      const missing = this._missingColors(st);
      sum = t.mi_count(missing.length);
      const groups = new Map();
      for (const e of missing) {
        if (!groups.has(e.product)) groups.set(e.product, []);
        groups.get(e.product).push(e);
      }
      body = missing.length ? [...groups.entries()]
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([gname, items]) => {
          const collapsed = this._collapsed.has(gname);
          const tiles = collapsed ? "" : `<div class="mgrid">${items.map((e) => this._missingTile(e, t)).join("")}</div>`;
          return `<div class="group">
            <div class="ghead" data-group="${esc(gname)}">
              <ha-icon icon="mdi:chevron-${collapsed ? "right" : "down"}"></ha-icon>
              <span class="gname">${esc(gname)}</span>
              <span class="chip">${items.length}</span>
            </div>${tiles}</div>`;
        }).join("")
        : `<div class="msg">${esc(t.mi_none)}</div>`;
      const asOf = new Date(this._shop.fetched_at);
      if (!Number.isNaN(asOf.getTime())) {
        body += `<div class="asof">${esc(t.mi_as_of)} ${esc(asOf.toLocaleDateString(this._hass?.locale?.language || undefined))}</div>`;
      }
    }
    const scroll = c.max_height ? `style="max-height:${Number(c.max_height)}px;overflow-y:auto"` : "";
    const backendVersion = st.attributes.version;
    const staleCard = backendVersion && backendVersion !== CARD_VERSION;
    this.shadowRoot.innerHTML = `
      <ha-card>
        ${staleCard ? `<div class="stale"><span>${esc(t.stale)}</span><button class="stale-btn">${esc(t.reload)}</button></div>` : ""}
        ${title ? `<div class="head"><div class="title">${esc(title)}</div><div class="sum">${esc(sum)}</div></div>` : ""}
        <div class="list" ${scroll}>${body}</div>
      </ha-card>${this._css()}`;
    this.shadowRoot.querySelector(".stale-btn")?.addEventListener("click", () => reloadCard());
    this.shadowRoot.querySelectorAll(".ghead").forEach((el) =>
      el.addEventListener("click", () => {
        const g = el.dataset.group;
        this._collapsed.has(g) ? this._collapsed.delete(g) : this._collapsed.add(g);
        this._render(st);
      })
    );
    this._bindPhotoFallback();
  }

  _missingTile(e, t) {
    const colors = (e.colors || []).map(normHex).filter(Boolean);
    const fill = colors.length > 1
      ? `background:linear-gradient(135deg, ${colors.map(esc).join(", ")})`
      : `background:${esc(colors[0] || "#888")}`;
    // With a photo (option show_images) the tile stays neutral - the photo
    // has its own light background; the color fill only appears if the
    // photo fails to load.
    const photo = this._config.show_images && safeUrl(e.image) ? e.image : null;
    const img = photo
      ? `<img src="${esc(photo)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : "";
    const inner = `
      <div class="msw ${photo ? "ph" : ""}" ${photo ? `data-fill="${fill}"` : `style="${fill}"`}>${img}</div>
      <div class="mname">${esc(e.name)}</div>
      <div class="mmeta">${esc(e.code)}${e.available ? "" : ` · <span class="soldout">${esc(t.mi_sold_out)}</span>`}</div>`;
    return safeUrl(e.url)
      ? `<a class="mtile" href="${esc(e.url)}" target="_blank" rel="noopener noreferrer">${inner}</a>`
      : `<div class="mtile">${inner}</div>`;
  }

  // The per-spool remaining-weight sensor, found via its device (identifier
  // "<entry_id>-spool-<id>") - entity ids are user-renamable, so they cannot
  // be derived from the spool. Null when per-spool entities are disabled.
  // hass.devices normally carries the identifiers; if not, the device
  // registry is fetched once as a fallback.
  async _weightEntity(spoolId) {
    const hass = this._hass;
    const suffix = `-spool-${spoolId}`;
    let devices = hass.devices || {};
    const sample = Object.values(devices)[0];
    if (sample && !Array.isArray(sample.identifiers)) {
      if (!this._deviceIds) {
        try {
          const list = await hass.callWS({ type: "config/device_registry/list" });
          this._deviceIds = Object.fromEntries(list.map((d) => [d.id, d]));
        } catch (e) {
          this._deviceIds = {};
        }
      }
      devices = this._deviceIds;
    }
    for (const e of Object.values(hass.entities || {})) {
      if (e.platform !== "bambu_filaments" || !e.device_id) continue;
      const isWeight = e.translation_key === "spool_remaining_g"
        || hass.states[e.entity_id]?.attributes?.device_class === "weight";
      if (!isWeight) continue;
      const ids = devices[e.device_id]?.identifiers || [];
      if (ids.some(([d, v]) => d === "bambu_filaments" && String(v).endsWith(suffix))) {
        return e.entity_id;
      }
    }
    return null;
  }

  // Read-only details of one spool with a remaining-weight history chart
  // (HA's own statistics-graph card, so it uses the long-term statistics and
  // reaches back further than the recorder's purge window). "Edit" hands
  // over to the edit dialog.
  _openDetails(t, spool) {
    if (this._dialogHost) return;
    const c = this._config;
    const days = Math.max(1, Number(c.details_days) || 30);
    const host = document.createElement("div");
    const root = host.attachShadow({ mode: "open" });
    root.innerHTML = `
      <style>
        .overlay { position:fixed; inset:0; z-index:9999; background:rgba(0,0,0,.55);
                   display:flex; align-items:center; justify-content:center;
                   font-family: var(--primary-font-family, Roboto, "Segoe UI", sans-serif);
                   color: var(--primary-text-color, #e3e5ea); }
        .dlg { background:var(--card-background-color, #1c2027);
               border:1px solid var(--divider-color, rgba(255,255,255,.12));
               border-radius:14px; padding:18px; width:min(420px, calc(100vw - 48px));
               max-height: calc(100vh - 48px); overflow-y:auto;
               display:flex; flex-direction:column; gap:12px;
               box-shadow:0 8px 32px rgba(0,0,0,.5); }
        .xhead { display:flex; align-items:center; gap:12px; }
        .swatch { width:42px; height:42px; border-radius:10px; flex:none;
                  border:1px solid var(--divider-color, rgba(255,255,255,.12)); }
        .xtitle { font-size:1.1em; font-weight:600; }
        .xsub { color:var(--secondary-text-color, #9aa1ad); font-size:0.88em; }
        .xgrams { display:flex; justify-content:space-between; align-items:baseline; }
        .xgrams b { font-size:1.3em; }
        .xpct { color:var(--secondary-text-color, #9aa1ad); }
        .barbg { height:6px; border-radius:3px; background:var(--secondary-background-color, #2b313c);
                 overflow:hidden; margin-top:4px; }
        .bar { height:100%; border-radius:3px; }
        dl { display:grid; grid-template-columns:auto 1fr; gap:4px 12px; margin:0; font-size:0.9em; }
        dt { color:var(--secondary-text-color, #9aa1ad); }
        dd { margin:0; overflow-wrap:anywhere; }
        .xhist-title { font-size:0.85em; color:var(--secondary-text-color, #9aa1ad); }
        .xhist { min-height:40px; --ha-card-border-width:0; --ha-card-box-shadow:none;
                 --ha-card-background:transparent; margin:0 -16px; }
        .xhint { font-size:0.85em; color:var(--secondary-text-color, #9aa1ad); }
        [hidden] { display:none !important; }
        .dbtns { display:flex; justify-content:flex-end; gap:8px; margin-top:4px; }
        .dbtns button { padding:8px 14px; border-radius:8px; border:none; cursor:pointer;
          font-size:0.95em; }
        .dlg-close { background:var(--secondary-background-color, #2b313c);
          color:var(--primary-text-color, #e3e5ea); }
        .dlg-edit { background:#00ae42; color:#fff; font-weight:600; }
        .xquick { display:flex; gap:8px; align-items:flex-end;
                  border-top:1px solid var(--divider-color, rgba(255,255,255,.12)); padding-top:12px; }
        .xquick label { display:flex; flex-direction:column; gap:3px; font-size:0.85em; flex:1;
                        color:var(--secondary-text-color, #9aa1ad); min-width:0; }
        .xquick input { box-sizing:border-box; width:100%; padding:7px 9px; font-size:1rem;
          border:1px solid var(--divider-color, rgba(255,255,255,.12)); border-radius:8px;
          background:var(--secondary-background-color, #2b313c); color:var(--primary-text-color, #e3e5ea); }
        .xquick button { padding:8px 12px; border-radius:8px; border:none; cursor:pointer; font-size:0.95em;
          background:var(--secondary-background-color, #2b313c); color:var(--primary-text-color, #e3e5ea);
          font-weight:600; }
        .xquick button:disabled { opacity:.6; }
        .xerr { color:var(--error-color, #e74c3c); font-size:0.85em; }
      </style>
      <div class="overlay">
        <div class="dlg">
          <div class="xhead">
            <span class="swatch" style="${swatchStyle(spool)}"></span>
            <div>
              <div class="xtitle"></div>
              <div class="xsub"></div>
            </div>
          </div>
          <div>
            <div class="xgrams"><span><b class="xrem"></b> / <span class="xtot"></span></span><span class="xpct"></span></div>
            <div class="barbg"><div class="bar"></div></div>
          </div>
          <dl class="xinfo"></dl>
          ${c.show_edit ? `
          <div class="xquick">
            <label>${esc(t.x_weigh)}<input class="xweigh" type="number" min="0" max="20000" inputmode="numeric" value="${spool.remaining_g ?? ""}"/></label>
            <button class="xsave">${esc(t.x_save)}</button>
            <button class="xfull">${esc(t.x_full)}</button>
          </div>
          <div class="xerr" hidden></div>` : ""}
          <div class="xhist-title">${esc(t.x_history(days))}</div>
          <div class="xhist"></div>
          <div class="xhint" hidden>${esc(t.x_no_history)}</div>
          <div class="dbtns">
            <button class="dlg-close">${esc(t.x_close)}</button>
            ${c.show_edit ? `<button class="dlg-edit">${esc(t.x_edit)}</button>` : ""}
          </div>
        </div>
      </div>`;
    // Inside <home-assistant> instead of on document.body: HA's chart
    // components read theme data from context providers there and fail
    // outside of that tree. Still outside the dashboard's transformed
    // containers, so position:fixed stays viewport-relative.
    (document.querySelector("home-assistant")?.shadowRoot || document.body).appendChild(host);
    this._dialogHost = host;
    this._details = { root, spoolId: spool.spool_id, chart: null, t };
    this._fillDetails(spool);

    const close = () => {
      host.remove();
      this._dialogHost = null;
      this._details = null;
    };
    // Like the edit dialog: no click-outside-to-close (text selection would
    // release over the overlay and close it by accident).
    root.querySelector(".dlg-close").addEventListener("click", close);
    root.querySelector(".dlg-edit")?.addEventListener("click", () => {
      const current = (this._lastState?.attributes?.spools || [])
        .find((s) => s.spool_id === spool.spool_id) || spool;
      close();
      this._openDialog(t, current);
    });
    if (c.show_edit) this._bindQuickActions(root, t, spool.spool_id);

    this._showHistory(root, spool.spool_id, days);
  }

  // Quick remaining-weight updates (weighing a spool, refilling) without the
  // full edit dialog. The dialog stays open; the sync updates its values.
  _bindQuickActions(root, t, spoolId) {
    const input = root.querySelector(".xweigh");
    const err = root.querySelector(".xerr");
    const current = () => (this._lastState?.attributes?.spools || [])
      .find((s) => s.spool_id === spoolId);
    const save = async (btn, grams) => {
      const label = btn.textContent;
      err.hidden = true;
      btn.disabled = true;
      btn.textContent = t.d_saving;
      try {
        await this._hass.callService("bambu_filaments", "set_remaining", {
          spool_id: spoolId, remaining_g: grams,
        });
        input.value = grams;
        btn.textContent = t.x_saved;
        setTimeout(() => { btn.textContent = label; btn.disabled = false; }, 1500);
      } catch (e) {
        btn.textContent = label;
        btn.disabled = false;
        err.hidden = false;
        err.textContent = t.x_error;
      }
    };
    root.querySelector(".xsave").addEventListener("click", (ev) => {
      const g = Math.round(Number(input.value));
      if (input.value === "" || !Number.isFinite(g) || g < 0 || g > 20000) {
        err.hidden = false;
        err.textContent = t.x_error;
        return;
      }
      save(ev.currentTarget, g);
    });
    root.querySelector(".xfull").addEventListener("click", (ev) => {
      const s = current();
      if (!s || !s.total_g) return;
      const name = (s.display_name || `${s.vendor || ""} ${s.name || s.material || ""}`).trim();
      if (!confirm(t.x_full_confirm(name, fmtG(s.total_g)))) return;
      save(ev.currentTarget, s.total_g);
    });
  }

  async _showHistory(root, spoolId, days) {
    const entityId = await this._weightEntity(spoolId);
    if (!entityId || !window.loadCardHelpers) {
      root.querySelector(".xhist").hidden = true;
      root.querySelector(".xhint").hidden = false;
      return;
    }
    window.loadCardHelpers().then((helpers) => {
      if (!this._details || this._details.root !== root) return;
      const chart = helpers.createCardElement({
        type: "statistics-graph",
        entities: [entityId],
        days_to_show: days,
        period: "day",
        stat_types: ["mean"],
        chart_type: "line",
        hide_legend: true,
        min_y_axis: 0,
      });
      chart.hass = this._hass;
      this._details.chart = chart;
      root.querySelector(".xhist").appendChild(chart);
    });
  }

  // Writes the spool's current values into the open details dialog.
  _fillDetails(spool) {
    const d = this._details;
    if (!d) return;
    const { root, t } = d;
    const c = this._config;
    const custom = (spool.display_name || "").trim();
    const colorLabel = spool.color_name || normHex(spool.color).slice(0, 7);
    root.querySelector(".xtitle").textContent = custom || `${spool.name || spool.material || "?"} ${colorLabel}`.trim();
    root.querySelector(".xsub").textContent = [spool.vendor, spool.material, spool.name, custom ? colorLabel : ""]
      .filter(Boolean).filter((v, i, a) => a.indexOf(v) === i).join(" · ");
    const pct = spool.total_g ? Math.max(0, Math.min(100, Math.round((spool.remaining_g ?? 0) / spool.total_g * 100))) : 0;
    root.querySelector(".xrem").textContent = fmtG(spool.remaining_g);
    root.querySelector(".xtot").textContent = fmtG(spool.total_g);
    root.querySelector(".xpct").textContent = `${pct}%`;
    const bar = root.querySelector(".bar");
    bar.style.width = `${pct}%`;
    bar.style.background = (spool.remaining_g ?? 0) <= 0 ? "var(--disabled-text-color, #9e9e9e)"
      : pct < c.low_threshold ? "var(--error-color, #e74c3c)"
      : pct < c.warn_threshold ? "#f39c12"
      : "#00ae42";
    const type = spool.create_type === "ams" ? t.type_ams : spool.create_type === "manual" ? t.type_manual : spool.create_type;
    const rows = [
      [t.x_location, spool.in_printer ? locationLabel(spool, t.loc_ext) : t.x_storage],
      [t.x_profile, spool.filament_id],
      [t.x_type, type],
      [t.x_note, spool.note],
      ["ID", String(spool.spool_id)],
    ].filter(([, v]) => v);
    root.querySelector(".xinfo").innerHTML = rows
      .map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("");
  }

  // Keeps an open details dialog current: new values after a sync or an
  // edit, and fresh hass for the chart. A spool deleted meanwhile closes it.
  _refreshDetails(st) {
    const d = this._details;
    if (!d || !st) return;
    if (d.chart) d.chart.hass = this._hass;
    const spool = (st.attributes.spools || []).find((s) => s.spool_id === d.spoolId);
    if (!spool) {
      this._dialogHost?.remove();
      this._dialogHost = null;
      this._details = null;
      return;
    }
    this._fillDetails(spool);
  }

  async _openDialog(t, spool) {
    // spool = null opens the create dialog; a spool object opens it in edit
    // mode with every field prefilled and a delete button.
    if (this._dialogHost) return;
    const isEdit = !!spool;
    // The cloud only accepts vendor/product combos from its official catalog
    // (free text is rejected with HTTP 400), so the dialog uses dropdowns fed
    // by the get_catalog action - exactly like the Handy app.
    let catalog = [];
    // The account's own slicer presets (filament_id "P…"): selectable as a
    // spool's slicer profile only, never as an official vendor/product.
    let presets = [];
    // Official color codes (5 digits on the box): typing one fills product
    // and color, so sealed spools can be registered without the AMS.
    let codes = [];
    try {
      const resp = await this._hass.callService(
        "bambu_filaments", "get_catalog", {}, undefined, false, true
      );
      catalog = resp?.response?.filaments || [];
      presets = resp?.response?.presets || [];
      codes = resp?.response?.colors || [];
    } catch (e) {
      catalog = [];
    }
    const vendors = [...new Set(catalog.map((f) => f.vendor).filter(Boolean))];
    // Editing an official spool preselects its catalog entry; anything else
    // (custom brand, unknown id) opens in custom mode with fields prefilled.
    const editEntry = isEdit && catalog.length
      ? catalog.find(
          (f) => f.vendor === spool.vendor && f.filament_id === (spool.filament_id || "")
        ) || null
      : null;
    const customInit = isEdit && catalog.length && !editEntry;
    // Do not assume "Bambu Lab" exists (e.g. localized China-region catalogs) -
    // the initial product list must match whatever vendor the select shows.
    const initialVendor = editEntry ? editEntry.vendor
      : vendors.includes("Bambu Lab") ? "Bambu Lab" : vendors[0] || "";
    const productOpts = (vendor) => catalog
      .filter((f) => f.vendor === vendor)
      .map((f) => `<option value="${esc(f.filament_id)}">${esc(f.name)}${f.name === f.material ? "" : ` (${esc(f.material)})`}</option>`)
      .join("");
    // Custom-brand spools can still carry an official filamentId so Bambu
    // Studio finds a slicer profile for them (verified: the cloud stores any
    // id independently of the free-text vendor). Option values are catalog
    // indices; the visible list is sorted for scanning.
    const profileOpts = catalog
      .map((f, i) => ({ f, i }))
      .sort((a, b) => `${a.f.vendor} ${a.f.name}`.localeCompare(`${b.f.vendor} ${b.f.name}`))
      .map(({ f, i }) => `<option value="${i}">${esc(f.vendor)} ${esc(f.name)}${f.name === f.material ? "" : ` (${esc(f.material)})`}</option>`)
      .join("");
    // Own presets as "p:<index>". A profile id found in neither list (e.g. a
    // preset of another account) stays selectable as "keep", so saving an
    // edit never clears a profile the dialog cannot name.
    const presetOpts = presets.length
      ? `<optgroup label="${esc(t.d_profile_own)}">${presets
          .map((p, i) => `<option value="p:${i}">${esc(p.name)}${p.vendor ? ` (${esc(p.vendor)})` : ""}</option>`)
          .join("")}</optgroup>`
      : "";
    const currentId = isEdit ? spool.filament_id || "" : "";
    const keepCurrent = !!currentId
      && !catalog.some((f) => f.filament_id === currentId)
      && !presets.some((p) => p.filament_id === currentId);
    const keepOpt = keepCurrent
      ? `<option value="keep">${esc(t.d_profile_current)} (${esc(currentId)})</option>`
      : "";

    // The dialog lives on document.body: HA's dashboard containers use CSS
    // transforms, which turn position:fixed inside a card into card-relative
    // positioning. On body it is always centered in the viewport.
    const host = document.createElement("div");
    const root = host.attachShadow({ mode: "open" });
    root.innerHTML = `
      <style>
        .overlay { position:fixed; inset:0; z-index:9999; background:rgba(0,0,0,.55);
                   display:flex; align-items:center; justify-content:center;
                   font-family: var(--primary-font-family, Roboto, "Segoe UI", sans-serif);
                   color: var(--primary-text-color, #e3e5ea); }
        .dlg { background:var(--card-background-color, #1c2027);
               border:1px solid var(--divider-color, rgba(255,255,255,.12));
               border-radius:14px; padding:18px; width:min(340px, calc(100vw - 48px));
               max-height: calc(100vh - 48px); overflow-y:auto;
               display:flex; flex-direction:column; gap:10px;
               box-shadow:0 8px 32px rgba(0,0,0,.5); }
        .dtitle { font-size:1.1em; font-weight:600; }
        label { display:flex; flex-direction:column; gap:3px; font-size:0.85em;
                color:var(--secondary-text-color, #9aa1ad); min-width:0; }
        input { box-sizing:border-box; width:100%; }
        input[type=text], input[type=number], select {
          padding:7px 9px; border:1px solid var(--divider-color, rgba(255,255,255,.12));
          border-radius:8px; background:var(--secondary-background-color, #2b313c);
          color:var(--primary-text-color, #e3e5ea); font-size:1rem; }
        select { box-sizing:border-box; width:100%; }
        #row-custom { display:flex; flex-direction:column; gap:10px; }
        [hidden] { display:none !important; }
        input[type=color] { width:100%; height:38px; padding:2px; border-radius:8px;
          border:1px solid var(--divider-color, rgba(255,255,255,.12));
          background:var(--secondary-background-color, #2b313c); }
        .cols2 { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
        .derr { color:var(--error-color, #e74c3c); font-size:0.85em; }
        .codehint { font-size:0.85em; color:var(--primary-text-color, #e3e5ea);
                    display:flex; align-items:center; gap:6px; min-height:1.2em; }
        .codehint.bad { color:var(--error-color, #e74c3c); }
        .codehint i { width:14px; height:14px; border-radius:50%; flex:none;
                      border:1px solid var(--divider-color, rgba(255,255,255,.3)); }
        .dbtns { display:flex; justify-content:flex-end; gap:8px; margin-top:4px; }
        .dbtns button { padding:8px 14px; border-radius:8px; border:none; cursor:pointer;
          font-size:0.95em; }
        .dlg-cancel { background:var(--secondary-background-color, #2b313c);
          color:var(--primary-text-color, #e3e5ea); }
        .dlg-save { background:#00ae42; color:#fff; font-weight:600; }
        .dlg-save:disabled { opacity:.6; }
        .dlg-del { background:var(--error-color, #e74c3c); color:#fff; margin-right:auto; }
        .dup { border-top:1px solid var(--divider-color, rgba(255,255,255,.12));
               padding-top:10px; display:flex; flex-direction:column; gap:6px; }
        .dup .dhint { font-size:0.78em; color:var(--secondary-text-color, #9aa1ad); }
        .dup .duprow { display:flex; gap:8px; align-items:center; }
        .dup input[type=number] { width:80px; }
        .dlg-dup { padding:8px 14px; border-radius:8px; border:none; cursor:pointer;
          font-size:0.95em; background:var(--secondary-background-color, #2b313c);
          color:var(--primary-text-color, #e3e5ea); font-weight:600; }
        .dlg-dup:disabled { opacity:.6; }
      </style>
      <div class="overlay">
        <div class="dlg">
          <div class="dtitle">${isEdit ? t.d_edit_title : t.d_title}</div>
          ${!isEdit && catalog.length && codes.length ? `
          <label>${t.d_code}
            <input id="f-code" type="text" inputmode="numeric" maxlength="5" autocomplete="off" placeholder="13504"/>
            <span class="codehint" hidden></span></label>` : ""}
          ${catalog.length ? `
          <label>${t.d_vendor}
            <select id="f-vendor">
              ${vendors.map((v) => `<option ${v === initialVendor && !customInit ? "selected" : ""}>${esc(v)}</option>`).join("")}
              <option value="__custom__" ${customInit ? "selected" : ""}>${t.d_custom}</option>
            </select></label>
          <label id="row-product" ${customInit ? "hidden" : ""}>${t.d_product}
            <select id="f-product">${productOpts(initialVendor)}</select></label>
          <div id="row-custom" ${customInit ? "" : "hidden"}>
            <label>${t.d_brand}<input id="f-cvendor" type="text" placeholder="Flashforge" value="${customInit ? esc(spool.vendor || "") : ""}"/></label>
            <label>${t.d_material}
              <input id="f-cmaterial" type="text" list="dl-cmats" placeholder="PLA" value="${customInit ? esc(spool.material || "") : ""}"/>
              <datalist id="dl-cmats">${[...new Set(catalog.map((f) => f.material).filter(Boolean))].map((m) => `<option value="${esc(m)}"></option>`).join("")}</datalist></label>
            <label>${t.d_line}<input id="f-cname" type="text" placeholder="PLA Pro" value="${customInit ? esc(spool.name || "") : ""}"/></label>
            <label>${t.d_profile}
              <select id="f-cprofile">
                <option value="">${t.d_profile_none}</option>
                ${keepOpt}
                ${presetOpts}
                ${profileOpts}
              </select></label>
          </div>
          ` : `
          <label>${t.d_vendor}<input id="f-vendor" type="text" value="${isEdit ? esc(spool.vendor || "") : "Bambu Lab"}"/></label>
          <label>${t.d_material}<input id="f-material" type="text" placeholder="PLA" value="${isEdit ? esc(spool.material || "") : ""}"/></label>
          <label>${t.d_name}<input id="f-name" type="text" placeholder="PLA Matte" value="${isEdit ? esc(spool.name || "") : ""}"/></label>
          `}
          <label>${t.d_display}<input id="f-display" type="text" placeholder="Burnt Titanium" value="${isEdit ? esc(spool.display_name || "") : ""}"/></label>
          <label class="colorlab">${t.d_color}<input id="f-color" type="color" value="${isEdit ? (normHex(spool.color).slice(0, 7) || "#00ae42") : "#00ae42"}"/></label>
          <div class="cols2">
            <label>${t.d_total}<input id="f-total" type="number" min="1" value="${isEdit ? (spool.total_g ?? 1000) : 1000}"/></label>
            <label>${t.d_remaining}<input id="f-remaining" type="number" min="0" placeholder="1000" value="${isEdit ? (spool.remaining_g ?? "") : ""}"/></label>
          </div>
          ${isEdit
            ? `<label>${t.d_note}<input id="f-note" type="text" value="${esc(spool.note || "")}"/></label>`
            : `<div class="cols2">
            <label>${t.d_note}<input id="f-note" type="text" value=""/></label>
            <label>${t.d_count}<input id="f-count" type="number" min="1" max="50" value="1"/></label>
          </div>`}
          ${isEdit ? `
          <div class="dup">
            <div class="dtitle" style="font-size:0.95em">${t.d_dup_title}</div>
            <div class="dhint">${t.d_dup_hint}</div>
            <div class="duprow">
              <input id="f-dupcount" type="number" min="1" max="50" value="1"/>
              <button class="dlg-dup">${t.d_dup_btn(1)}</button>
            </div>
          </div>` : ""}
          <div class="derr" hidden></div>
          <div class="dbtns">
            ${isEdit ? `<button class="dlg-del">${t.d_delete}</button>` : ""}
            <button class="dlg-cancel">${t.d_cancel}</button>
            <button class="dlg-save">${isEdit ? t.d_update : t.d_save}</button>
          </div>
        </div>
      </div>`;
    document.body.appendChild(host);
    this._dialogHost = host;

    // Preselect the edited spool's product / slicer profile (selects cannot
    // carry a value attribute in markup).
    if (editEntry) root.querySelector("#f-product").value = editEntry.filament_id;
    if (customInit && spool.filament_id) {
      const pidx = catalog.findIndex((f) => f.filament_id === spool.filament_id);
      const oidx = presets.findIndex((p) => p.filament_id === spool.filament_id);
      root.querySelector("#f-cprofile").value =
        oidx >= 0 ? `p:${oidx}` : pidx >= 0 ? String(pidx) : keepCurrent ? "keep" : "";
    }

    const close = () => {
      host.remove();
      this._dialogHost = null;
    };
    // Deliberately NO click-outside-to-close: selecting text in a field and
    // releasing the mouse over the overlay would fire a click there and slam
    // the dialog shut. Only Cancel (or delete/save) closes it.
    root.querySelector(".dlg-cancel").addEventListener("click", close);
    root.querySelector(".dlg-del")?.addEventListener("click", () => {
      const label = (spool.display_name
        || `${spool.vendor || ""} ${spool.name || spool.material || ""}`).trim();
      if (!confirm(t.delete_confirm(label))) return;
      this._hass.callService("bambu_filaments", "delete_spool", { spool_id: spool.spool_id });
      close();
    });
    if (isEdit) {
      const dupBtn = root.querySelector(".dlg-dup");
      const dupCount = root.querySelector("#f-dupcount");
      const clampDup = () => Math.min(50, Math.max(1, Math.round(Number(dupCount.value)) || 1));
      dupCount.addEventListener("input", () => { dupBtn.textContent = t.d_dup_btn(clampDup()); });
      dupBtn.addEventListener("click", async () => {
        const n = clampDup();
        const err = root.querySelector(".derr");
        dupBtn.disabled = true;
        dupBtn.textContent = t.d_saving;
        try {
          await this._hass.callService("bambu_filaments", "create_spool", {
            vendor: spool.vendor || "Bambu Lab",
            material: spool.material || "",
            name: spool.name || spool.material || "",
            filament_id: spool.filament_id || "",
            color: normHex(spool.color).slice(0, 7) || "#000000",
            total_g: spool.total_g || 1000,
            count: n,
          });
          close();
        } catch (e) {
          dupBtn.disabled = false;
          dupBtn.textContent = t.d_dup_btn(n);
          err.hidden = false;
          err.textContent = t.d_error;
        }
      });
    }
    // Color code -> official product + color. `codeEntry` stays set only while
    // product and color still are what the code filled in; any manual change
    // turns the dialog back into a plain manual create.
    let codeEntry = null;
    let codeFilling = false;
    const codeInput = root.querySelector("#f-code");
    if (codeInput) {
      const hint = root.querySelector(".codehint");
      const dropCode = () => {
        if (!codeEntry) return;
        codeEntry = null;
        codeInput.value = "";
        hint.hidden = true;
      };
      codeInput.addEventListener("input", () => {
        const code = codeInput.value.replace(/\D/g, "");
        if (code !== codeInput.value) codeInput.value = code;
        codeEntry = null;
        hint.hidden = code.length < 5;
        if (code.length < 5) return;
        const hit = codes.find((c) => c.code === code);
        const cat = hit && (
          catalog.find((f) => f.filament_id === hit.filament_id && f.vendor === "Bambu Lab")
          || catalog.find((f) => f.filament_id === hit.filament_id));
        const hex = hit ? normHex((hit.colors || [])[0]).slice(0, 7) : "";
        hint.classList.toggle("bad", !hit || !hex);
        if (!hit || !hex) {
          hint.textContent = t.d_code_unknown;
          return;
        }
        if (cat) {
          const vendorSel = root.querySelector("#f-vendor");
          vendorSel.value = cat.vendor;
          // Rebuilds the product list; must not count as a manual change.
          codeFilling = true;
          vendorSel.dispatchEvent(new Event("change"));
          codeFilling = false;
          root.querySelector("#f-product").value = cat.filament_id;
        }
        root.querySelector("#f-color").value = hex.toLowerCase();
        hint.innerHTML = `<i style="background:${hex}"></i>${esc(cat ? cat.name : hit.product)}${hit.color_name ? ` · ${esc(hit.color_name)}` : ""}`;
        codeEntry = hit;
      });
      for (const id of ["f-vendor", "f-product", "f-color"]) {
        root.querySelector(`#${id}`).addEventListener("change", () => {
          if (!codeFilling) dropCode();
        });
      }
    }
    if (catalog.length) {
      root.querySelector("#f-vendor").addEventListener("change", (ev) => {
        const isCustom = ev.target.value === "__custom__";
        root.querySelector("#row-product").hidden = isCustom;
        root.querySelector("#row-custom").hidden = !isCustom;
        if (!isCustom) {
          root.querySelector("#f-product").innerHTML = productOpts(ev.target.value);
        }
      });
      // Default the slicer profile to the matching Generic entry while the
      // user types the material - until they pick a profile themselves.
      const profileSel = root.querySelector("#f-cprofile");
      let profileTouched = isEdit;
      profileSel.addEventListener("change", () => { profileTouched = true; });
      root.querySelector("#f-cmaterial").addEventListener("input", (ev) => {
        if (profileTouched) return;
        const mat = ev.target.value.trim().toLowerCase();
        const idx = catalog.findIndex(
          (f) => f.vendor === "Generic" && (f.material || "").toLowerCase() === mat
        );
        profileSel.value = idx >= 0 ? String(idx) : "";
      });
    }
    root.querySelector(".dlg-save").addEventListener("click", async () => {
      const val = (id) => (root.querySelector(`#${id}`)?.value || "").trim();
      const err = root.querySelector(".derr");
      const total = Number(val("f-total")) || 1000;
      const data = {
        vendor: val("f-vendor") || "Bambu Lab",
        color: val("f-color"),
        total_g: total,
        remaining_g: val("f-remaining") === "" ? total : Number(val("f-remaining")),
      };
      if (codeEntry) {
        // The backend resolves vendor, product, profile and (multi-)color
        // from the official database.
        delete data.vendor;
        delete data.color;
        data.color_code = codeEntry.code;
      } else if (catalog.length && val("f-vendor") === "__custom__") {
        // Custom/third-party brand: free-text vendor/material/name. The
        // filamentId is the chosen slicer profile - or "" for "no profile",
        // the verified way Studio models non-official spools.
        data.vendor = val("f-cvendor");
        data.material = val("f-cmaterial");
        data.name = val("f-cname") || data.material;
        const pidx = val("f-cprofile");
        data.filament_id = pidx === "" ? ""
          : pidx === "keep" ? currentId
          : pidx.startsWith("p:") ? (presets[Number(pidx.slice(2))]?.filament_id || "")
          : (catalog[Number(pidx)]?.filament_id || "");
        if (!data.vendor || !data.material) {
          err.hidden = false;
          err.textContent = t.d_error;
          return;
        }
      } else if (catalog.length) {
        // Match vendor + id (an id could repeat across vendors in the catalog).
        const entry = catalog.find(
          (f) => f.filament_id === val("f-product") && f.vendor === val("f-vendor")
        ) || catalog.find((f) => f.filament_id === val("f-product"));
        if (!entry) {
          err.hidden = false;
          err.textContent = t.d_error;
          return;
        }
        data.material = entry.material;
        data.name = entry.name;
        data.filament_id = entry.filament_id;
      } else {
        data.material = val("f-material");
        data.name = val("f-name");
        if (!data.material || !data.name) {
          err.hidden = false;
          err.textContent = t.d_error;
          return;
        }
      }
      if (val("f-display")) data.display_name = val("f-display");
      const btn = root.querySelector(".dlg-save");
      btn.disabled = true;
      btn.textContent = t.d_saving;
      try {
        if (!isEdit) {
          if (val("f-note")) data.note = val("f-note");
          const n = Math.min(50, Math.max(1, Math.round(Number(val("f-count"))) || 1));
          if (n > 1) data.count = n;
          await this._hass.callService("bambu_filaments", "create_spool", data);
        } else {
          // Send only the fields that actually changed (minimal PUT, like
          // Studio). Empty strings deliberately clear name/note/profile.
          const upd = { spool_id: spool.spool_id };
          const same = (a, b) => String(a ?? "") === String(b ?? "");
          if (!same(data.vendor, spool.vendor)) upd.vendor = data.vendor;
          if (!same(data.material, spool.material)) upd.material = data.material;
          if (!same(data.name, spool.name)) upd.name = data.name;
          if (data.filament_id !== undefined && !same(data.filament_id, spool.filament_id)) {
            upd.filament_id = data.filament_id;
          }
          const disp = val("f-display");
          if (!same(disp, spool.display_name)) upd.display_name = disp;
          const color = normHex(data.color).slice(0, 7);
          if (color && color !== normHex(spool.color).slice(0, 7)) upd.color = color;
          if (data.total_g !== (spool.total_g ?? null)) upd.total_g = data.total_g;
          if (data.remaining_g !== (spool.remaining_g ?? null)) upd.remaining_g = data.remaining_g;
          const note = val("f-note");
          if (!same(note, spool.note)) upd.note = note;
          if (Object.keys(upd).length > 1) {
            await this._hass.callService("bambu_filaments", "update_spool", upd);
          }
        }
        close();
      } catch (e) {
        btn.disabled = false;
        btn.textContent = isEdit ? t.d_update : t.d_save;
        err.hidden = false;
        err.textContent = t.d_error;
      }
    });
  }

  _stack(s, t) {
    // A combined row plus, when expanded, one child row per physical spool
    // (emptiest first) - each with its own cog icon.
    // In the tile layout the children follow the stack tile in the same grid.
    const item = this._config.layout === "tiles" ? this._tile.bind(this) : this._row.bind(this);
    const expanded = (s._count || 1) > 1 && this._expandedStacks.has(s._key);
    let html = item(s, t, { expanded });
    if (expanded) {
      html += s._spools
        .slice()
        .sort((a, b) => (a.remaining_g ?? 0) - (b.remaining_g ?? 0))
        .map((child) => item(child, t, { child: true }))
        .join("");
    }
    return html;
  }

  // Everything a row and a tile share: fill level, title, meta parts,
  // edit icon and the ×n chip of a combined stack.
  _itemData(s, t, opts) {
    const c = this._config;
    const pct = s.total_g ? Math.max(0, Math.min(100, Math.round((s.remaining_g ?? 0) / s.total_g * 100))) : 0;
    const barColor = (s.remaining_g ?? 0) <= 0 ? "var(--disabled-text-color, #9e9e9e)"
      : pct < c.low_threshold ? "var(--error-color, #e74c3c)"
      : pct < c.warn_threshold ? "#f39c12"
      : "#00ae42";
    const custom = (s.display_name || "").trim();
    const colorLabel = s.color_name || normHex(s.color).slice(0, 7);
    const titleLine = custom || (c.group_by === "line"
      ? (colorLabel || s.name || "?")
      : c.group_by === "product"
        // Group header carries the product; rows distinguish by brand + color.
        ? `${s.vendor || "?"} ${colorLabel}`.trim()
        : `${s.name || s.material || "?"} ${colorLabel}`.trim());
    const combined = (s._count || 1) > 1;
    // The color name is already part of the title in every grouping mode -
    // the meta line only carries code/hex/location/note.
    const meta = [];
    // The type pill leads the meta line - trailing it would hide it whenever
    // the (often long) location list makes the line ellipsize.
    if (c.show_type) {
      const label = (ct) => ct === "ams" ? t.type_ams : ct === "manual" ? t.type_manual : (ct || "?");
      const pill = (txt) => `<span class="pill">${esc(txt)}</span>`;
      if (combined) {
        // A stack can mix entry types - "RFID ×5, manuell ×2" as separate
        // pills; uniform stacks just show the label (the ×n chip already
        // carries the count).
        const counts = new Map();
        for (const sp of s._spools || []) {
          const k = label(sp.create_type);
          counts.set(k, (counts.get(k) || 0) + 1);
        }
        meta.push([...counts.entries()]
          .map(([k, n]) => pill(counts.size > 1 ? `${k} ×${n}` : k))
          .join(" "));
      } else {
        meta.push(pill(label(s.create_type)));
      }
    }
    if (c.show_code && s.bambu_color_code) meta.push(esc(s.bambu_color_code));
    if (c.show_code && s.color) meta.push(esc(normHex(s.color).slice(0, 7)));
    if (c.show_location) {
      const locs = (combined ? s._spools || [] : [s])
        .filter((sp) => sp.in_printer && sp.device_name)
        .map((sp) => locationLabel(sp, t.loc_ext))
        .filter(Boolean);
      if (locs.length) meta.push(locs.map(esc).join(", "));
    }
    if (c.show_note && !combined && s.note) meta.push(esc(s.note));
    const edit = c.show_edit && !combined
      ? `<ha-icon class="edit" icon="mdi:cog-outline" data-spool="${s.spool_id}"></ha-icon>`
      : "";
    const stackChip = combined
      ? ` <span class="chip">×${s._count}</span><ha-icon class="schev" icon="mdi:chevron-${opts.expanded ? "up" : "down"}"></ha-icon>`
      : "";
    const attrs = `${combined ? `data-key="${esc(s._key)}"` : ""} data-spool="${combined ? "" : s.spool_id}"`;
    const cls = `item ${opts.child ? "child" : ""} ${opts.expanded ? "open" : ""} ${c.show_details && !combined ? "tap" : ""}`;
    return { pct, barColor, titleLine, meta, edit, stackChip, attrs, cls };
  }

  _row(s, t, opts = {}) {
    const c = this._config;
    const { pct, barColor, titleLine, meta, edit, stackChip, attrs, cls } = this._itemData(s, t, opts);
    return `
      <div class="row ${cls} ${c.compact ? "compact" : ""} ${this._photoFor(s) ? "withph" : ""}" ${attrs}>
        ${this._swatchHtml(s, "swatch")}
        <div class="mid">
          <div class="rname">${esc(titleLine)}${stackChip}</div>
          ${meta.length && !c.compact ? `<div class="meta">${meta.join(" · ")}</div>` : ""}
          <div class="barbg"><div class="bar" style="width:${pct}%;background:${barColor}"></div></div>
        </div>
        <div class="right">
          <div class="grams"><b>${fmtG(s.remaining_g)}</b> / ${fmtG(s.total_g)}</div>
          <div class="pct">${pct}%</div>
        </div>
        ${edit}
      </div>`;
  }

  // Tile layout: big swatch/photo, title, meta line, bar and grams. The cog
  // sits on the swatch; tapping works like a row (details / expand stack).
  _tile(s, t, opts = {}) {
    const c = this._config;
    const { pct, barColor, titleLine, meta, edit, stackChip, attrs, cls } = this._itemData(s, t, opts);
    return `
      <div class="tile ${cls}" ${attrs}>
        <div class="tswwrap">${this._swatchHtml(s, "tsw")}${edit}</div>
        <div class="tname">${esc(titleLine)}${stackChip}</div>
        ${meta.length && !c.compact ? `<div class="meta">${meta.join(" · ")}</div>` : ""}
        <div class="barbg"><div class="bar" style="width:${pct}%;background:${barColor}"></div></div>
        <div class="tgrams"><span><b>${fmtG(s.remaining_g)}</b> / ${fmtG(s.total_g)}</span><span>${pct}%</span></div>
      </div>`;
  }

  _css() {
    return `<style>
      ha-card { padding: 12px 16px 8px; }
      .head { display:flex; align-items:baseline; gap:10px; margin-bottom:4px; }
      .title { font-size:1.15em; font-weight:600; margin-right:auto; }
      .headadd { --mdc-icon-size:20px; align-self:center; flex:none; cursor:pointer; padding:3px;
                 border-radius:50%; color:var(--secondary-text-color);
                 border:1px solid var(--divider-color); }
      .headadd:hover { color:var(--primary-text-color); border-color:var(--secondary-text-color); }
      .sum { color: var(--secondary-text-color); font-size:0.9em; }
      .msg { padding:16px 4px; color: var(--secondary-text-color); }
      .stale { display:flex; align-items:center; justify-content:space-between; gap:8px; flex-wrap:wrap;
               margin:0 0 8px; padding:6px 10px; border-radius:8px; font-size:0.9em;
               background: color-mix(in srgb, var(--warning-color, #ff9800) 18%, transparent); }
      .stale-btn { border:none; border-radius:6px; padding:4px 10px; cursor:pointer; font:inherit;
                   color: var(--text-primary-color, #fff); background: var(--warning-color, #ff9800); }
      .group { margin-bottom:2px; }
      .ghead { display:flex; align-items:center; gap:6px; padding:8px 0 4px; cursor:pointer;
               border-bottom:1px solid var(--divider-color); font-weight:600; }
      .ghead ha-icon { --mdc-icon-size:18px; color:var(--secondary-text-color); }
      .chip { background: var(--secondary-background-color); border-radius:10px; padding:0 8px;
              font-size:0.8em; font-weight:400; }
      .gsum { margin-left:auto; color:var(--secondary-text-color); font-weight:400; font-size:0.9em; }
      .row { display:flex; align-items:center; gap:12px; padding:8px 0;
             border-bottom:1px solid var(--divider-color); }
      .row[data-key], .row.tap { cursor:pointer; }
      .row:last-child { border-bottom:none; }
      .row.compact { padding:4px 0; gap:8px; }
      .row.child { padding-left:46px; }
      .row.compact.child { padding-left:30px; }
      .row.child .swatch { width:26px; height:26px; border-radius:6px; }
      .schev { --mdc-icon-size:16px; color:var(--secondary-text-color); vertical-align:middle; }
      .swatch { width:34px; height:34px; border-radius:8px; flex:none;
                border:1px solid var(--divider-color); }
      .compact .swatch { width:22px; height:22px; border-radius:6px; }
      /* Shop photos: a bit larger than the color square, neutral background
         (the product photos have a light backdrop of their own). */
      .ph { position:relative; overflow:hidden; background:#f2f2f2; }
      .ph img { position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }
      .row.withph .swatch { width:46px; height:46px; }
      .row .ph img { transform:scale(1.35); }
      .row.withph.child .swatch { width:34px; height:34px; }
      .row.withph.compact .swatch { width:30px; height:30px; }
      .tgrid { display:grid; grid-template-columns:repeat(auto-fill, minmax(118px, 1fr)); gap:8px;
               padding:8px 0 6px; }
      .tgrid.compact { grid-template-columns:repeat(auto-fill, minmax(88px, 1fr)); gap:6px; }
      .tile { min-width:0; border-radius:10px; padding:6px; border:1px solid var(--divider-color); }
      .tile[data-key], .tile.tap { cursor:pointer; }
      .tile[data-key]:hover, .tile.tap:hover { border-color:var(--secondary-text-color); }
      .tile.open { border-color:var(--primary-color); }
      .tile.child { border-style:dashed; }
      .tswwrap { position:relative; }
      .tsw { display:block; aspect-ratio:1; border-radius:7px; border:1px solid var(--divider-color); }
      .tswwrap .edit { position:absolute; top:4px; right:4px; padding:3px; border-radius:50%;
                       --mdc-icon-size:18px; color:var(--primary-text-color);
                       background:color-mix(in srgb, var(--card-background-color, #fff) 80%, transparent); }
      .tname { font-size:0.9em; font-weight:500; margin-top:5px; line-height:1.25; overflow-wrap:anywhere; }
      .tname .chip { white-space:nowrap; }
      .tile .meta { font-size:0.75em; }
      .tgrams { font-size:0.78em; color:var(--secondary-text-color); margin-top:3px; display:flex;
                flex-wrap:wrap; justify-content:space-between; column-gap:6px; white-space:nowrap; }
      .tgrams b { color:var(--primary-text-color); font-weight:600; }
      .mid { flex:1; min-width:0; }
      .rname { font-weight:500; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
      .meta { color:var(--secondary-text-color); font-size:0.82em; white-space:nowrap;
              overflow:hidden; text-overflow:ellipsis; }
      .pill { display:inline-block; background:var(--secondary-background-color);
              border:1px solid var(--divider-color); border-radius:9px;
              padding:0 7px; line-height:1.5; font-size:0.95em; }
      .barbg { height:5px; border-radius:3px; background:var(--secondary-background-color);
               margin-top:4px; overflow:hidden; }
      .compact .barbg { margin-top:2px; height:4px; }
      .bar { height:100%; border-radius:3px; }
      .right { text-align:right; flex:none; }
      .grams { font-size:0.9em; }
      .pct { color:var(--secondary-text-color); font-size:0.8em; }
      .edit { --mdc-icon-size:20px; color:var(--secondary-text-color); flex:none; }
      .edit:hover { color: var(--primary-text-color); }
      .addrow { display:flex; align-items:center; justify-content:center; gap:6px;
                margin:8px 0 4px; padding:8px; border:1px dashed var(--divider-color);
                border-radius:8px; color:var(--secondary-text-color); cursor:pointer; }
      .addrow:hover { color:var(--primary-text-color); border-color:var(--secondary-text-color); }
      .addrow ha-icon { --mdc-icon-size:18px; }
      .mgrid { display:grid; grid-template-columns:repeat(auto-fill, minmax(86px, 1fr)); gap:8px;
               padding:8px 0 6px; }
      .mtile { display:block; min-width:0; color:inherit; text-decoration:none; border-radius:10px;
               padding:6px; border:1px solid var(--divider-color); }
      a.mtile:hover { border-color:var(--secondary-text-color); }
      .msw { position:relative; aspect-ratio:1; border-radius:7px; overflow:hidden;
             border:1px solid var(--divider-color); }
      .mname { font-size:0.85em; font-weight:500; margin-top:4px; overflow-wrap:anywhere; line-height:1.25; }
      .mmeta { font-size:0.75em; color:var(--secondary-text-color); }
      .soldout { color:var(--error-color, #e74c3c); }
      .asof { font-size:0.75em; color:var(--secondary-text-color); text-align:right; padding:4px 0 2px; }
    </style>`;
  }
}

class BambuFilamentsCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    this._config = { ...DEFAULTS, ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) this._render();
    this._loadShopProducts();
  }

  // Product lines of the current shop range, for the missing-colors filter.
  _loadShopProducts() {
    if (this._config?.mode !== "missing" || this._shopProducts || this._shopLoading || !this._hass) return;
    this._shopLoading = true;
    this._hass.callService("bambu_filaments", "get_shop_range", {}, undefined, false, true)
      .then((resp) => {
        const colors = resp?.response?.colors || [];
        this._shopProducts = [...new Set(colors.map((e) => e.product).filter(Boolean))];
      })
      .catch(() => { this._shopProducts = []; })
      .finally(() => {
        this._shopLoading = false;
        this._render();
      });
  }

  _fire() {
    const config = { type: "custom:bambu-filaments-card", ...this._config };
    for (const [k, v] of Object.entries(DEFAULTS)) {
      if (config[k] === v) delete config[k];
    }
    if (config.title === undefined) delete config.title;
    if (!config.entity) delete config.entity;
    if (!config.max_height) delete config.max_height;
    this.dispatchEvent(new CustomEvent("config-changed", {
      detail: { config }, bubbles: true, composed: true,
    }));
  }

  _render() {
    if (!this._config) return;
    this._rendered = true;
    const t = STR[lang(this._hass)];
    const c = this._config;
    const check = (f, label) => `
      <label class="chk"><input type="checkbox" data-f="${f}" ${c[f] ? "checked" : ""}/> ${label}</label>`;
    const stEntity = c.entity || (this._hass ? findSpoolsEntity(this._hass) : null);
    const st = stEntity ? this._hass?.states?.[stEntity] : null;
    // One checkbox list per list filter, fed by the live inventory. Values
    // already selected stay listed even when no spool carries them any more,
    // so they can still be unchecked.
    const listSection = (key, label) => {
      const selected = Array.isArray(c[key]) ? c[key] : [];
      const values = [...new Set([
        ...((st?.attributes?.spools) || []).map(LIST_FILTERS[key]),
        ...selected,
      ].filter(Boolean))].sort((a, b) => a.localeCompare(b));
      if (!values.length) return "";
      const exclude = c[`${key}_mode`] === "exclude";
      return `
        <div class="lhead"><span>${label}</span>
          <select data-mode="${key}">
            <option value="include" ${exclude ? "" : "selected"}>${t.m_include}</option>
            <option value="exclude" ${exclude ? "selected" : ""}>${t.m_exclude}</option>
          </select></div>
        <div class="mats">${values.map((v) => `
          <label class="chk"><input type="checkbox" data-list="${key}" data-val="${esc(v)}" ${selected.includes(v) ? "checked" : ""}/> ${esc(v)}</label>`).join("")}</div>`;
    };
    const missingMode = c.mode === "missing";
    const missingSection = () => {
      const selected = Array.isArray(c.missing_products) ? c.missing_products : [];
      const values = [...new Set([...(this._shopProducts || []), ...selected])]
        .sort((a, b) => a.localeCompare(b));
      return `
        <div class="sect">${t.e_missing}</div>
        ${check("missing_count_empty", t.e_missing_empty)}
        ${check("show_images", t.e_show_images)}
        <div class="lhead"><span>${t.e_missing_products}</span></div>
        ${values.length ? `<div class="mats">${values.map((v) => `
          <label class="chk"><input type="checkbox" data-list="missing_products" data-val="${esc(v)}" ${selected.includes(v) ? "checked" : ""}/> ${esc(v)}</label>`).join("")}</div>`
          : `<div class="lhead">${t.e_missing_noshop}</div>`}`;
    };
    this.shadowRoot.innerHTML = `
      <style>
        .form { display:flex; flex-direction:column; gap:10px; padding:4px 0; }
        label { display:flex; flex-direction:column; gap:2px; font-size:0.9em;
                color: var(--secondary-text-color); }
        label.chk { flex-direction:row; align-items:center; gap:8px;
                    color: var(--primary-text-color); }
        input[type=text], input[type=number], select {
          padding:6px 8px; border:1px solid var(--divider-color); border-radius:6px;
          background: var(--card-background-color); color: var(--primary-text-color); }
        .cols { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:10px; }
        .cols select, .cols input { box-sizing:border-box; width:100%; min-width:0; }
        .sect { font-weight:600; margin-top:6px; border-bottom:1px solid var(--divider-color);
                padding-bottom:2px; color: var(--primary-text-color); }
        .mats { display:flex; flex-wrap:wrap; gap:4px 14px; }
        .lhead { display:flex; align-items:center; justify-content:space-between; gap:10px;
                 margin-top:4px; font-size:0.9em; color: var(--secondary-text-color); }
      </style>
      <div class="form">
        <label>${t.e_mode}
          <select data-f="mode">
            <option value="spools" ${missingMode ? "" : "selected"}>${t.mo_spools}</option>
            <option value="missing" ${missingMode ? "selected" : ""}>${t.mo_missing}</option>
          </select></label>
        <label>${t.e_entity}<input type="text" data-f="entity" value="${esc(c.entity || "")}"/></label>
        <label>${t.e_title}<input type="text" data-f="title" value="${esc(c.title !== undefined ? c.title : missingMode ? t.mi_title : t.title)}"/></label>
        ${missingMode ? missingSection() : `
        <label>${t.e_layout}
          <select data-f="layout">
            <option value="list" ${c.layout === "tiles" ? "" : "selected"}>${t.l_list}</option>
            <option value="tiles" ${c.layout === "tiles" ? "selected" : ""}>${t.l_tiles}</option>
          </select></label>
        ${check("show_images", t.e_show_images)}
        <div class="cols">
          <label>${t.e_group}
            <select data-f="group_by">
              <option value="line" ${c.group_by === "line" ? "selected" : ""}>${t.g_line}</option>
              <option value="product" ${c.group_by === "product" ? "selected" : ""}>${t.g_product}</option>
              <option value="material" ${c.group_by === "material" ? "selected" : ""}>${t.g_material}</option>
              <option value="none" ${c.group_by === "none" ? "selected" : ""}>${t.g_none}</option>
            </select></label>
          <label>${t.e_sort}
            <select data-f="sort">
              <option value="name" ${c.sort === "name" ? "selected" : ""}>${t.s_name}</option>
              <option value="remaining_asc" ${c.sort === "remaining_asc" ? "selected" : ""}>${t.s_rem_asc}</option>
              <option value="remaining_desc" ${c.sort === "remaining_desc" ? "selected" : ""}>${t.s_rem_desc}</option>
              <option value="color_code" ${c.sort === "color_code" ? "selected" : ""}>${t.s_code}</option>
            </select></label>
        </div>
        ${check("combine", t.e_combine)}
        <div class="sect">${t.e_filters}</div>
        <div class="cols">
          <label>${t.e_max_g}<input type="number" min="0" data-f="max_remaining_g" value="${c.max_remaining_g ?? ""}"/></label>
          <label>${t.e_max_pct}<input type="number" min="0" max="100" data-f="max_remaining_pct" value="${c.max_remaining_pct ?? ""}"/></label>
        </div>
        <div class="cols">
          <label>${t.e_min_pct}<input type="number" min="0" max="100" data-f="min_remaining_pct" value="${c.min_remaining_pct ?? ""}"/></label>
          <label>${t.e_max_items}<input type="number" min="1" data-f="max_items" value="${c.max_items ?? ""}"/></label>
        </div>
        <label>${t.e_type}
          <select data-f="spool_type">
            <option value="" ${!c.spool_type ? "selected" : ""}>${t.ty_all}</option>
            <option value="rfid" ${c.spool_type === "rfid" ? "selected" : ""}>${t.ty_rfid}</option>
            <option value="manual" ${c.spool_type === "manual" ? "selected" : ""}>${t.ty_manual}</option>
          </select></label>
        ${check("only_in_printer", t.e_only_printer)}
        ${listSection("vendors", t.e_vendors)}
        ${listSection("materials", t.e_materials)}
        ${listSection("products", t.e_products)}
        <div class="sect"></div>
        ${check("show_empty", t.e_show_empty)}
        ${check("show_location", t.e_show_location)}
        ${check("show_code", t.e_show_code)}
        ${check("show_note", t.e_show_note)}
        ${check("show_type", t.e_show_type)}
        ${check("show_edit", t.e_show_edit)}
        ${check("show_details", t.e_show_details)}
        ${check("show_add", t.e_show_add)}
        ${check("compact", t.e_compact)}
        <div class="cols">
          <label>${t.e_low}<input type="number" min="0" max="100" data-f="low_threshold" value="${c.low_threshold}"/></label>
          <label>${t.e_warn}<input type="number" min="0" max="100" data-f="warn_threshold" value="${c.warn_threshold}"/></label>
        </div>
        `}
        <label>${t.e_max_height}<input type="number" min="100" data-f="max_height" value="${c.max_height || ""}"/></label>
      </div>`;
    this.shadowRoot.querySelectorAll("[data-list]").forEach((el) =>
      el.addEventListener("change", () => {
        const key = el.dataset.list;
        const checked = [...this.shadowRoot.querySelectorAll(`[data-list="${key}"]`)]
          .filter((x) => x.checked).map((x) => x.dataset.val);
        if (checked.length) this._config[key] = checked;
        else delete this._config[key];
        this._fire();
      })
    );
    this.shadowRoot.querySelectorAll("[data-mode]").forEach((el) =>
      el.addEventListener("change", () => {
        const key = `${el.dataset.mode}_mode`;
        if (el.value === "exclude") this._config[key] = "exclude";
        else delete this._config[key];
        this._fire();
      })
    );
    this.shadowRoot.querySelectorAll("[data-f]").forEach((el) =>
      el.addEventListener("change", () => {
        const f = el.dataset.f;
        if (el.type === "checkbox") this._config[f] = el.checked;
        else if (el.type === "number") {
          const v = el.value === "" ? null : Number(el.value);
          if (v === null) delete this._config[f];
          else this._config[f] = v;
        } else if (f === "title") this._config[f] = el.value;
        else if (el.value === "") delete this._config[f];
        else this._config[f] = el.value;
        this._fire();
        if (f === "mode") {
          this._render();
          this._loadShopProducts();
        }
      })
    );
  }
}

customElements.define("bambu-filaments-card", BambuFilamentsCard);
customElements.define("bambu-filaments-card-editor", BambuFilamentsCardEditor);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "bambu-filaments-card",
  name: "Bambu Filaments Card",
  description: "Spool inventory card for the Bambu Filaments integration.",
  preview: true,
  documentationURL: "https://github.com/Timmes123/ha-bambu-filaments",
});
