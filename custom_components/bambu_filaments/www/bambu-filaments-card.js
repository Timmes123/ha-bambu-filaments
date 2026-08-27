/* Bambu Filaments Card — shipped with the bambu_filaments integration.
 * Vanilla web component, no external dependencies. Reads the spool list from
 * the integration's aggregate "spools" sensor attributes.
 */

const STR = {
  en: {
    spools: (n) => `${n} spool${n === 1 ? "" : "s"}`,
    empty: "No spools found.",
    no_entity: "Bambu Filaments spools sensor not found. Is the integration set up?",
    delete_confirm: (n) => `Delete "${n}" from the Bambu cloud library?`,
    archived: "archived",
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
    d_display: "Custom name (optional)",
    d_loading: "Loading catalog…",
    d_color: "Color",
    d_total: "Spool size (g)",
    d_remaining: "Remaining (g)",
    d_save: "Add to library",
    d_cancel: "Cancel",
    d_saving: "Saving…",
    d_error: "The cloud rejected the spool. Check material and name.",
    // editor
    e_entity: "Spools sensor (empty = automatic)",
    e_title: "Title",
    e_group: "Group by", g_line: "Filament line (brand + product)", g_product: "Product line (all brands)", g_material: "Material", g_none: "No grouping",
    e_sort: "Sort by", s_name: "Name", s_rem_asc: "Remaining (low first)", s_rem_desc: "Remaining (high first)",
    e_combine: "Combine identical spools (sum remaining)",
    e_filters: "Filters",
    e_max_g: "Only show below (g, empty = off)",
    e_max_pct: "Only show below (%, empty = off)",
    e_materials: "Materials (none checked = all)",
    e_only_printer: "Only spools loaded in a printer/AMS",
    e_max_items: "Max. rows (empty = all)",
    e_show_empty: "Show empty spools",
    e_show_archived: "Show archived spools",
    e_show_location: "Show printer/AMS location",
    e_show_code: "Show color code and hex",
    e_show_note: "Show note",
    e_show_edit: "Show edit button",
    e_show_add: "Show add-spool button",
    e_compact: "Compact rows",
    e_low: "Red below (%)",
    e_warn: "Orange below (%)",
    e_max_height: "Max. height (px, empty = unlimited)",
  },
  de: {
    spools: (n) => `${n} Spule${n === 1 ? "" : "n"}`,
    empty: "Keine Spulen gefunden.",
    no_entity: "Bambu-Filaments-Spulensensor nicht gefunden. Ist die Integration eingerichtet?",
    delete_confirm: (n) => `„${n}" aus der Bambu-Cloud-Bibliothek löschen?`,
    archived: "archiviert",
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
    d_display: "Eigener Name (optional)",
    d_loading: "Katalog wird geladen…",
    d_color: "Farbe",
    d_total: "Spulengröße (g)",
    d_remaining: "Restgewicht (g)",
    d_save: "Zur Bibliothek hinzufügen",
    d_cancel: "Abbrechen",
    d_saving: "Speichern…",
    d_error: "Die Cloud hat die Spule abgelehnt. Material und Sorte prüfen.",
    e_entity: "Spulen-Sensor (leer = automatisch)",
    e_title: "Titel",
    e_group: "Gruppieren nach", g_line: "Filamentlinie (Hersteller + Sorte)", g_product: "Sorte (alle Hersteller)", g_material: "Material", g_none: "Keine Gruppierung",
    e_sort: "Sortieren nach", s_name: "Name", s_rem_asc: "Restmenge (wenig zuerst)", s_rem_desc: "Restmenge (viel zuerst)",
    e_combine: "Gleiche Filamente zusammenfassen (Rest addieren)",
    e_filters: "Filter",
    e_max_g: "Nur anzeigen unter (g, leer = aus)",
    e_max_pct: "Nur anzeigen unter (%, leer = aus)",
    e_materials: "Materialien (nichts angehakt = alle)",
    e_only_printer: "Nur eingelegte Spulen (Drucker/AMS)",
    e_max_items: "Max. Zeilen (leer = alle)",
    e_show_empty: "Leere Spulen anzeigen",
    e_show_archived: "Archivierte Spulen anzeigen",
    e_show_location: "Drucker-/AMS-Position anzeigen",
    e_show_code: "Farbcode und Hex anzeigen",
    e_show_note: "Notiz anzeigen",
    e_show_edit: "Bearbeiten-Button anzeigen",
    e_show_add: "Neue-Spule-Button anzeigen",
    e_compact: "Kompakte Zeilen",
    e_low: "Rot unter (%)",
    e_warn: "Orange unter (%)",
    e_max_height: "Max. Höhe (px, leer = unbegrenzt)",
  },
};

const DEFAULTS = {
  group_by: "line",
  sort: "name",
  combine: false,
  only_in_printer: false,
  show_add: true,
  show_empty: true,
  show_archived: false,
  show_location: true,
  show_code: true,
  show_note: false,
  show_edit: true,
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

function fmtG(g) {
  if (g == null) return "?";
  return g >= 10000 ? `${(g / 1000).toFixed(1).replace(/\.0$/, "")} kg` : `${g} g`;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
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

  disconnectedCallback() {
    super.disconnectedCallback?.();
    this._dialogHost?.remove();
    this._dialogHost = null;
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
  }

  getCardSize() {
    return 6;
  }

  _visibleSpools(st) {
    const c = this._config;
    let spools = (st.attributes.spools || []).slice();
    if (!c.show_archived) spools = spools.filter((s) => (s.status ?? 0) === 0);
    if (c.combine) spools = this._combine(spools);
    // With combine on, the empty filter judges the summed remainder — a color
    // with enough backup spools no longer shows up as (nearly) empty.
    if (!c.show_empty) spools = spools.filter((s) => (s.remaining_g ?? 0) > 0);
    if (c.only_in_printer) spools = spools.filter((s) => s.in_printer);
    if (Array.isArray(c.materials) && c.materials.length) {
      spools = spools.filter((s) => c.materials.includes(s.material));
    }
    if (c.max_remaining_g != null) spools = spools.filter((s) => (s.remaining_g ?? 0) <= Number(c.max_remaining_g));
    if (c.max_remaining_pct != null) {
      spools = spools.filter((s) => (s.total_g ? (s.remaining_g ?? 0) / s.total_g * 100 : 0) <= Number(c.max_remaining_pct));
    }
    const name = (s) => `${s.vendor || ""} ${s.name || ""} ${s.color_name || s.color || ""}`;
    const rem = (s) => (s.total_g ? (s.remaining_g ?? 0) / s.total_g : 0);
    if (c.sort === "remaining_asc") spools.sort((a, b) => rem(a) - rem(b) || name(a).localeCompare(name(b)));
    else if (c.sort === "remaining_desc") spools.sort((a, b) => rem(b) - rem(a) || name(a).localeCompare(name(b)));
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
        // render (and edit) each physical spool individually.
        map.set(key, { ...s, _count: 1, _locations: [], _key: key, _spools: [s] });
      } else {
        agg._count += 1;
        agg.remaining_g = (agg.remaining_g || 0) + (s.remaining_g || 0);
        agg.total_g = (agg.total_g || 0) + (s.total_g || 0);
        agg.in_printer = agg.in_printer || s.in_printer;
        agg._spools.push(s);
      }
      const rec = map.get(key);
      if (s.in_printer && s.device_name) {
        rec._locations.push(`${s.device_name}${s.slot_id != null && s.slot_id !== "" ? ` · Slot ${s.slot_id}` : ""}`);
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
    const spools = this._visibleSpools(st);
    const totalG = spools.reduce((a, s) => a + (s.remaining_g || 0), 0);
    const title = c.title !== undefined ? c.title : t.title;

    let body;
    if (!spools.length) {
      body = `<div class="msg">${esc(t.empty)}</div>`;
    } else {
      body = this._groups(spools).map(([gname, items]) => {
        const gTotal = items.reduce((a, s) => a + (s.remaining_g || 0), 0);
        const collapsed = gname && this._collapsed.has(gname);
        const rows = collapsed ? "" : items.map((s) => this._stack(s, t)).join("");
        const header = gname === null ? "" : `
          <div class="ghead" data-group="${esc(gname)}">
            <ha-icon icon="mdi:chevron-${collapsed ? "right" : "down"}"></ha-icon>
            <span class="gname">${esc(gname)}</span>
            <span class="chip">${items.length}</span>
            <span class="gsum">${fmtG(gTotal)}</span>
          </div>`;
        return `<div class="group">${header}${rows}</div>`;
      }).join("");
    }

    this._lastState = st;
    const scroll = c.max_height ? `style="max-height:${Number(c.max_height)}px;overflow-y:auto"` : "";
    this.shadowRoot.innerHTML = `
      <ha-card>
        ${title ? `<div class="head">
          <div class="title">${esc(title)}</div>
          <div class="sum">${t.spools(spools.length)} · ${fmtG(totalG)}</div>
        </div>` : ""}
        <div class="list" ${scroll}>${body}</div>
        ${c.show_add ? `<div class="addrow"><ha-icon icon="mdi:plus"></ha-icon><span>${t.add_btn}</span></div>` : ""}
      </ha-card>${this._css()}`;

    this.shadowRoot.querySelector(".addrow")?.addEventListener("click", () => {
      this._openDialog(t, null);
    });

    this.shadowRoot.querySelectorAll(".ghead").forEach((el) =>
      el.addEventListener("click", () => {
        const g = el.dataset.group;
        this._collapsed.has(g) ? this._collapsed.delete(g) : this._collapsed.add(g);
        this._configDirty = true;
        this._render(st);
      })
    );
    // A combined ×n row expands/collapses its individual spools on click
    // (single rows are inert - editing goes through the cog icon).
    this.shadowRoot.querySelectorAll(".row[data-key]").forEach((el) =>
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
    try {
      const resp = await this._hass.callService(
        "bambu_filaments", "get_catalog", {}, undefined, false, true
      );
      catalog = resp?.response?.filaments || [];
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
        .dbtns { display:flex; justify-content:flex-end; gap:8px; margin-top:4px; }
        .dbtns button { padding:8px 14px; border-radius:8px; border:none; cursor:pointer;
          font-size:0.95em; }
        .dlg-cancel { background:var(--secondary-background-color, #2b313c);
          color:var(--primary-text-color, #e3e5ea); }
        .dlg-save { background:#00ae42; color:#fff; font-weight:600; }
        .dlg-save:disabled { opacity:.6; }
        .dlg-del { background:var(--error-color, #e74c3c); color:#fff; margin-right:auto; }
      </style>
      <div class="overlay">
        <div class="dlg">
          <div class="dtitle">${isEdit ? t.d_edit_title : t.d_title}</div>
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
          <label>${t.d_note}<input id="f-note" type="text" value="${isEdit ? esc(spool.note || "") : ""}"/></label>
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
      if (pidx >= 0) root.querySelector("#f-cprofile").value = String(pidx);
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
      if (catalog.length && val("f-vendor") === "__custom__") {
        // Custom/third-party brand: free-text vendor/material/name. The
        // filamentId is the chosen slicer profile - or "" for "no profile",
        // the verified way Studio models non-official spools.
        data.vendor = val("f-cvendor");
        data.material = val("f-cmaterial");
        data.name = val("f-cname") || data.material;
        const pidx = val("f-cprofile");
        data.filament_id = pidx === "" ? "" : (catalog[Number(pidx)]?.filament_id || "");
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
    const expanded = (s._count || 1) > 1 && this._expandedStacks.has(s._key);
    let html = this._row(s, t, { expanded });
    if (expanded) {
      html += s._spools
        .slice()
        .sort((a, b) => (a.remaining_g ?? 0) - (b.remaining_g ?? 0))
        .map((child) => this._row(child, t, { child: true }))
        .join("");
    }
    return html;
  }

  _row(s, t, opts = {}) {
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
    if (c.show_code && s.bambu_color_code) meta.push(esc(s.bambu_color_code));
    if (c.show_code && s.color) meta.push(esc(normHex(s.color).slice(0, 7)));
    if (c.show_location) {
      if (combined && s._locations?.length) meta.push(s._locations.map(esc).join(", "));
      else if (s.in_printer && s.device_name) {
        meta.push(`${esc(s.device_name)}${s.slot_id != null && s.slot_id !== "" ? ` · Slot ${esc(s.slot_id)}` : ""}`);
      }
    }
    if ((s.status ?? 0) !== 0) meta.push(t.archived);
    if (c.show_note && !combined && s.note) meta.push(esc(s.note));
    const edit = c.show_edit && !combined
      ? `<ha-icon class="edit" icon="mdi:cog-outline" data-spool="${s.spool_id}"></ha-icon>`
      : "";
    const stackChip = combined
      ? ` <span class="chip">×${s._count}</span><ha-icon class="schev" icon="mdi:chevron-${opts.expanded ? "up" : "down"}"></ha-icon>`
      : "";
    return `
      <div class="row ${c.compact ? "compact" : ""} ${opts.child ? "child" : ""}"
           ${combined ? `data-key="${esc(s._key)}"` : ""} data-spool="${combined ? "" : s.spool_id}">
        <span class="swatch" style="${swatchStyle(s)}"></span>
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

  _css() {
    return `<style>
      ha-card { padding: 12px 16px 8px; }
      .head { display:flex; align-items:baseline; justify-content:space-between; margin-bottom:4px; }
      .title { font-size:1.15em; font-weight:600; }
      .sum { color: var(--secondary-text-color); font-size:0.9em; }
      .msg { padding:16px 4px; color: var(--secondary-text-color); }
      .group { margin-bottom:2px; }
      .ghead { display:flex; align-items:center; gap:6px; padding:8px 0 4px; cursor:pointer;
               border-bottom:1px solid var(--divider-color); font-weight:600; }
      .ghead ha-icon { --mdc-icon-size:18px; color:var(--secondary-text-color); }
      .chip { background: var(--secondary-background-color); border-radius:10px; padding:0 8px;
              font-size:0.8em; font-weight:400; }
      .gsum { margin-left:auto; color:var(--secondary-text-color); font-weight:400; font-size:0.9em; }
      .row { display:flex; align-items:center; gap:12px; padding:8px 0;
             border-bottom:1px solid var(--divider-color); }
      .row[data-key] { cursor:pointer; }
      .row:last-child { border-bottom:none; }
      .row.compact { padding:4px 0; gap:8px; }
      .row.child { padding-left:46px; }
      .row.compact.child { padding-left:30px; }
      .row.child .swatch { width:26px; height:26px; border-radius:6px; }
      .schev { --mdc-icon-size:16px; color:var(--secondary-text-color); vertical-align:middle; }
      .swatch { width:34px; height:34px; border-radius:8px; flex:none;
                border:1px solid var(--divider-color); }
      .compact .swatch { width:22px; height:22px; border-radius:6px; }
      .mid { flex:1; min-width:0; }
      .rname { font-weight:500; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
      .meta { color:var(--secondary-text-color); font-size:0.82em; white-space:nowrap;
              overflow:hidden; text-overflow:ellipsis; }
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
    const materials = [...new Set(((st?.attributes?.spools) || [])
      .map((s) => s.material).filter(Boolean))].sort();
    const selectedMats = c.materials || [];
    const matBoxes = materials.map((m) => `
      <label class="chk"><input type="checkbox" data-mat="${esc(m)}" ${selectedMats.includes(m) ? "checked" : ""}/> ${esc(m)}</label>`).join("");
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
        .cols { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
        .sect { font-weight:600; margin-top:6px; border-bottom:1px solid var(--divider-color);
                padding-bottom:2px; color: var(--primary-text-color); }
        .mats { display:flex; flex-wrap:wrap; gap:4px 14px; }
      </style>
      <div class="form">
        <label>${t.e_entity}<input type="text" data-f="entity" value="${esc(c.entity || "")}"/></label>
        <label>${t.e_title}<input type="text" data-f="title" value="${esc(c.title !== undefined ? c.title : t.title)}"/></label>
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
            </select></label>
        </div>
        ${check("combine", t.e_combine)}
        <div class="sect">${t.e_filters}</div>
        <div class="cols">
          <label>${t.e_max_g}<input type="number" min="0" data-f="max_remaining_g" value="${c.max_remaining_g ?? ""}"/></label>
          <label>${t.e_max_pct}<input type="number" min="0" max="100" data-f="max_remaining_pct" value="${c.max_remaining_pct ?? ""}"/></label>
        </div>
        <div class="cols">
          <label>${t.e_max_items}<input type="number" min="1" data-f="max_items" value="${c.max_items ?? ""}"/></label>
        </div>
        ${check("only_in_printer", t.e_only_printer)}
        ${materials.length ? `<label>${t.e_materials}</label><div class="mats">${matBoxes}</div>` : ""}
        <div class="sect"></div>
        ${check("show_empty", t.e_show_empty)}
        ${check("show_archived", t.e_show_archived)}
        ${check("show_location", t.e_show_location)}
        ${check("show_code", t.e_show_code)}
        ${check("show_note", t.e_show_note)}
        ${check("show_edit", t.e_show_edit)}
        ${check("show_add", t.e_show_add)}
        ${check("compact", t.e_compact)}
        <div class="cols">
          <label>${t.e_low}<input type="number" min="0" max="100" data-f="low_threshold" value="${c.low_threshold}"/></label>
          <label>${t.e_warn}<input type="number" min="0" max="100" data-f="warn_threshold" value="${c.warn_threshold}"/></label>
        </div>
        <label>${t.e_max_height}<input type="number" min="100" data-f="max_height" value="${c.max_height || ""}"/></label>
      </div>`;
    this.shadowRoot.querySelectorAll("[data-mat]").forEach((el) =>
      el.addEventListener("change", () => {
        const checked = [...this.shadowRoot.querySelectorAll("[data-mat]")]
          .filter((x) => x.checked).map((x) => x.dataset.mat);
        if (checked.length) this._config.materials = checked;
        else delete this._config.materials;
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
