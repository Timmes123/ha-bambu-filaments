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
    // editor
    e_entity: "Spools sensor (empty = automatic)",
    e_title: "Title",
    e_group: "Group by", g_line: "Filament line", g_material: "Material", g_none: "No grouping",
    e_sort: "Sort by", s_name: "Name", s_rem_asc: "Remaining (low first)", s_rem_desc: "Remaining (high first)",
    e_combine: "Combine identical spools (sum remaining)",
    e_show_empty: "Show empty spools",
    e_show_archived: "Show archived spools",
    e_show_location: "Show printer/AMS location",
    e_show_code: "Show color code and hex",
    e_show_note: "Show note",
    e_show_delete: "Show delete button",
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
    e_entity: "Spulen-Sensor (leer = automatisch)",
    e_title: "Titel",
    e_group: "Gruppieren nach", g_line: "Filamentlinie", g_material: "Material", g_none: "Keine Gruppierung",
    e_sort: "Sortieren nach", s_name: "Name", s_rem_asc: "Restmenge (wenig zuerst)", s_rem_desc: "Restmenge (viel zuerst)",
    e_combine: "Gleiche Filamente zusammenfassen (Rest addieren)",
    e_show_empty: "Leere Spulen anzeigen",
    e_show_archived: "Archivierte Spulen anzeigen",
    e_show_location: "Drucker-/AMS-Position anzeigen",
    e_show_code: "Farbcode und Hex anzeigen",
    e_show_note: "Notiz anzeigen",
    e_show_delete: "Löschen-Button anzeigen",
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
  show_empty: true,
  show_archived: false,
  show_location: true,
  show_code: true,
  show_note: false,
  show_delete: false,
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

function normHex(v) {
  // The cloud sometimes returns colors without the leading "#" (AMS-created
  // spools) - normalize before using as CSS or as a combine key.
  if (!v) return "";
  v = String(v).trim().toUpperCase();
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
    .filter(Boolean).map(normHex);
  if (!colors.length) return "background:#888";
  if (colors.length === 1) return `background:${esc(colors[0])}`;
  return `background:linear-gradient(135deg, ${esc(colors[0])} 50%, ${esc(colors[1])} 50%)`;
}

class BambuFilamentsCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._collapsed = new Set();
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

  set hass(hass) {
    this._hass = hass;
    const entityId = this._config?.entity || findSpoolsEntity(hass);
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

  _spoolEntityId(spoolId) {
    // Cache the spool_id -> remaining-sensor map per state generation.
    if (!this._entityMap || this._entityMapKey !== this._lastRenderKey) {
      this._entityMap = {};
      this._entityMapKey = this._lastRenderKey;
      for (const [id, st] of Object.entries(this._hass.states)) {
        if (!id.startsWith("sensor.")) continue;
        const sid = st.attributes?.spool_id;
        if (sid != null && st.attributes?.total_g != null) this._entityMap[sid] = id;
      }
    }
    return this._entityMap[spoolId];
  }

  _visibleSpools(st) {
    const c = this._config;
    let spools = (st.attributes.spools || []).slice();
    if (!c.show_archived) spools = spools.filter((s) => (s.status ?? 0) === 0);
    if (c.combine) spools = this._combine(spools);
    // With combine on, the empty filter judges the summed remainder — a color
    // with enough backup spools no longer shows up as (nearly) empty.
    if (!c.show_empty) spools = spools.filter((s) => (s.remaining_g ?? 0) > 0);
    const name = (s) => `${s.vendor || ""} ${s.name || ""} ${s.color_name || s.color || ""}`;
    const rem = (s) => (s.total_g ? (s.remaining_g ?? 0) / s.total_g : 0);
    if (c.sort === "remaining_asc") spools.sort((a, b) => rem(a) - rem(b) || name(a).localeCompare(name(b)));
    else if (c.sort === "remaining_desc") spools.sort((a, b) => rem(b) - rem(a) || name(a).localeCompare(name(b)));
    else spools.sort((a, b) => name(a).localeCompare(name(b)));
    return spools;
  }

  _combine(spools) {
    const map = new Map();
    for (const s of spools) {
      const colors = (s.colors && s.colors.length ? s.colors : [s.color]).filter(Boolean);
      const key = [s.vendor, s.name || s.material, ...colors.map(normHex).sort()].join("|");
      const agg = map.get(key);
      if (!agg) {
        map.set(key, { ...s, _count: 1, _locations: [] });
      } else {
        agg._count += 1;
        agg.remaining_g = (agg.remaining_g || 0) + (s.remaining_g || 0);
        agg.total_g = (agg.total_g || 0) + (s.total_g || 0);
        agg.in_printer = agg.in_printer || s.in_printer;
      }
      const rec = map.get(key);
      if (s.in_printer && s.device_name) {
        rec._locations.push(`${s.device_name}${s.slot_id !== undefined && s.slot_id !== "" ? ` · Slot ${s.slot_id}` : ""}`);
      }
    }
    return [...map.values()];
  }

  _groups(spools) {
    const c = this._config;
    if (c.group_by === "none") return [[null, spools]];
    const keyFn = c.group_by === "material"
      ? (s) => s.material || "?"
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
        const rows = collapsed ? "" : items.map((s) => this._row(s, t)).join("");
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

    const scroll = c.max_height ? `style="max-height:${Number(c.max_height)}px;overflow-y:auto"` : "";
    this.shadowRoot.innerHTML = `
      <ha-card>
        ${title ? `<div class="head">
          <div class="title">${esc(title)}</div>
          <div class="sum">${t.spools(spools.length)} · ${fmtG(totalG)}</div>
        </div>` : ""}
        <div class="list" ${scroll}>${body}</div>
      </ha-card>${this._css()}`;

    this.shadowRoot.querySelectorAll(".ghead").forEach((el) =>
      el.addEventListener("click", () => {
        const g = el.dataset.group;
        this._collapsed.has(g) ? this._collapsed.delete(g) : this._collapsed.add(g);
        this._configDirty = true;
        this._render(st);
      })
    );
    this.shadowRoot.querySelectorAll(".row").forEach((el) =>
      el.addEventListener("click", () => {
        if (!el.dataset.spool) return; // combined rows have no single spool
        const entityId = this._spoolEntityId(Number(el.dataset.spool));
        if (!entityId) return;
        this.dispatchEvent(new CustomEvent("hass-more-info", {
          detail: { entityId }, bubbles: true, composed: true,
        }));
      })
    );
    this.shadowRoot.querySelectorAll(".del").forEach((el) =>
      el.addEventListener("click", (ev) => {
        ev.stopPropagation();
        const name = el.dataset.name;
        if (!confirm(t.delete_confirm(name))) return;
        this._hass.callService("bambu_filaments", "delete_spool", {
          spool_id: Number(el.dataset.spool),
        });
      })
    );
  }

  _row(s, t) {
    const c = this._config;
    const pct = s.total_g ? Math.max(0, Math.min(100, Math.round((s.remaining_g ?? 0) / s.total_g * 100))) : 0;
    const barColor = (s.remaining_g ?? 0) <= 0 ? "var(--disabled-text-color, #9e9e9e)"
      : pct < c.low_threshold ? "var(--error-color, #e74c3c)"
      : pct < c.warn_threshold ? "#f39c12"
      : "#00ae42";
    const titleLine = c.group_by === "line"
      ? (s.color_name || normHex(s.color).slice(0, 7) || s.name || "?")
      : `${s.name || s.material || "?"} ${s.color_name || normHex(s.color).slice(0, 7)}`.trim();
    const combined = (s._count || 1) > 1;
    const meta = [];
    if (c.group_by !== "line" && s.color_name && s.color) meta.push(esc(s.color_name));
    if (c.show_code && s.bambu_color_code) meta.push(esc(s.bambu_color_code));
    if (c.show_code && s.color) meta.push(esc(normHex(s.color).slice(0, 7)));
    if (c.show_location) {
      if (combined && s._locations?.length) meta.push(s._locations.map(esc).join(", "));
      else if (s.in_printer && s.device_name) {
        meta.push(`${esc(s.device_name)}${s.slot_id !== undefined && s.slot_id !== "" ? ` · Slot ${esc(s.slot_id)}` : ""}`);
      }
    }
    if ((s.status ?? 0) !== 0) meta.push(t.archived);
    if (c.show_note && !combined && s.note) meta.push(esc(s.note));
    const del = c.show_delete && !combined
      ? `<ha-icon class="del" icon="mdi:delete-outline" data-spool="${s.spool_id}" data-name="${esc(titleLine)}"></ha-icon>`
      : "";
    return `
      <div class="row ${c.compact ? "compact" : ""}" data-spool="${combined ? "" : s.spool_id}">
        <span class="swatch" style="${swatchStyle(s)}"></span>
        <div class="mid">
          <div class="rname">${esc(titleLine)}${combined ? ` <span class="chip">×${s._count}</span>` : ""}</div>
          ${meta.length && !c.compact ? `<div class="meta">${meta.join(" · ")}</div>` : ""}
          <div class="barbg"><div class="bar" style="width:${pct}%;background:${barColor}"></div></div>
        </div>
        <div class="right">
          <div class="grams"><b>${fmtG(s.remaining_g)}</b> / ${fmtG(s.total_g)}</div>
          <div class="pct">${pct}%</div>
        </div>
        ${del}
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
             border-bottom:1px solid var(--divider-color); cursor:pointer; }
      .row:last-child { border-bottom:none; }
      .row.compact { padding:4px 0; gap:8px; }
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
      .del { --mdc-icon-size:20px; color:var(--secondary-text-color); flex:none; }
      .del:hover { color: var(--error-color, #e74c3c); }
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
      </style>
      <div class="form">
        <label>${t.e_entity}<input type="text" data-f="entity" value="${esc(c.entity || "")}"/></label>
        <label>${t.e_title}<input type="text" data-f="title" value="${esc(c.title !== undefined ? c.title : t.title)}"/></label>
        <div class="cols">
          <label>${t.e_group}
            <select data-f="group_by">
              <option value="line" ${c.group_by === "line" ? "selected" : ""}>${t.g_line}</option>
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
        ${check("show_empty", t.e_show_empty)}
        ${check("show_archived", t.e_show_archived)}
        ${check("show_location", t.e_show_location)}
        ${check("show_code", t.e_show_code)}
        ${check("show_note", t.e_show_note)}
        ${check("show_delete", t.e_show_delete)}
        ${check("compact", t.e_compact)}
        <div class="cols">
          <label>${t.e_low}<input type="number" min="0" max="100" data-f="low_threshold" value="${c.low_threshold}"/></label>
          <label>${t.e_warn}<input type="number" min="0" max="100" data-f="warn_threshold" value="${c.warn_threshold}"/></label>
        </div>
        <label>${t.e_max_height}<input type="number" min="100" data-f="max_height" value="${c.max_height || ""}"/></label>
      </div>`;
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
