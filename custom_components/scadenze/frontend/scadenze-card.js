// Card Lovelace «Scadenze» di Scadenze Auto & Casa: Web Component senza build.
// La logica sta in logica.js, importata con la stessa versione anti-cache di questo file.

const {
  coloreStato,
  filtraEOrdina,
  formattaData,
  formattaKm,
  lingua,
  normalizzaConfig,
  puoRinnovare,
  raccogliScadenze,
  testi,
  testoGiorni,
} = await import(`./logica.js${new URL(import.meta.url).search}`);

const DURATA_CONFERMA_MS = 4000;

const STILE = `
  :host { display: block; }
  .elenco { display: flex; flex-direction: column; padding-block: 8px; }
  .riga {
    display: grid;
    grid-template-columns: 4px minmax(0, 1fr) auto;
    gap: 12px;
    align-items: center;
    padding: 8px 16px;
  }
  .striscia { align-self: stretch; min-height: 32px; border-radius: 2px; }
  .testo { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .nome {
    color: var(--primary-text-color);
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .dettagli {
    display: flex;
    flex-wrap: wrap;
    gap: 2px 10px;
    color: var(--secondary-text-color);
    font-size: 0.875em;
  }
  .vuota { padding: 16px; color: var(--secondary-text-color); }
  button {
    font: inherit;
    font-size: 0.875em;
    padding: 6px 14px;
    border-radius: 16px;
    border: 1px solid var(--divider-color);
    background: var(--card-background-color);
    color: var(--primary-color);
    cursor: pointer;
    white-space: nowrap;
  }
  button.conferma {
    background: var(--primary-color);
    border-color: var(--primary-color);
    color: var(--text-primary-color);
  }
  button:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
`;

const CARATTERI_HTML = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

function html(testo) {
  return String(testo).replace(/[&<>"']/g, (carattere) => CARATTERI_HTML[carattere]);
}

class ScadenzeCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = normalizzaConfig({});
    this._hass = null;
    this._inConferma = null;
    this._timer = null;
    this.shadowRoot.addEventListener("click", (evento) => this._clic(evento));
  }

  static getConfigElement() {
    return document.createElement("scadenze-card-editor");
  }

  static getStubConfig() {
    return { titolo: "Scadenze" };
  }

  setConfig(config) {
    this._config = normalizzaConfig(config);
    this._disegna();
  }

  set hass(hass) {
    this._hass = hass;
    this._disegna();
  }

  getCardSize() {
    return 1 + Math.max(1, this._righe().length);
  }

  _righe() {
    return this._hass ? filtraEOrdina(raccogliScadenze(this._hass), this._config) : [];
  }

  _clic(evento) {
    const pulsante = evento.target?.closest?.("button[data-entita]");
    if (!pulsante || !this._hass) return;
    const entita = pulsante.dataset.entita;
    clearTimeout(this._timer);
    if (this._inConferma !== entita) {
      this._inConferma = entita;
      this._timer = setTimeout(() => {
        this._inConferma = null;
        this._disegna();
      }, DURATA_CONFERMA_MS);
    } else {
      this._inConferma = null;
      this._hass.callService("button", "press", { entity_id: entita });
    }
    this._disegna();
  }

  _disegna() {
    const codice = lingua(this._hass);
    const t = testi(codice);
    const righe = this._righe();
    const contenuto = righe.length
      ? `<div class="elenco">${righe.map((scadenza) => this._riga(scadenza, codice, t)).join("")}</div>`
      : `<div class="vuota">${html(t.vuota)}</div>`;
    const intestazione = this._config.titolo ? ` header="${html(this._config.titolo)}"` : "";
    this.shadowRoot.innerHTML = `<style>${STILE}</style><ha-card${intestazione}>${contenuto}</ha-card>`;
  }

  _riga(scadenza, codice, t) {
    const config = this._config;
    const dettagli = [];
    if (!config.voce && scadenza.voce) dettagli.push(scadenza.voce);
    if (scadenza.data) dettagli.push(formattaData(scadenza.data, codice));
    if (config.mostra_giorni) {
      const giorni = testoGiorni(scadenza, codice);
      if (giorni) dettagli.push(giorni);
    }
    if (config.mostra_km && scadenza.km !== null) dettagli.push(formattaKm(scadenza.km, codice));

    let azione = "<span></span>";
    if (config.mostra_rinnovato && puoRinnovare(scadenza)) {
      const inConferma = this._inConferma === scadenza.pulsante;
      azione =
        `<button type="button" data-entita="${html(scadenza.pulsante)}"${inConferma ? ' class="conferma"' : ""}>` +
        `${html(inConferma ? t.conferma : t.rinnovato)}</button>`;
    }

    return (
      `<div class="riga">` +
      `<span class="striscia" style="background: ${coloreStato(scadenza.stato)}"></span>` +
      `<div class="testo"><span class="nome">${html(scadenza.nome)}</span>` +
      `<span class="dettagli">${dettagli.map((d) => `<span>${html(d)}</span>`).join("")}</span></div>` +
      `${azione}</div>`
    );
  }
}

const SCHEMA_EDITOR = [
  { name: "titolo", selector: { text: {} } },
  { name: "voce", selector: { config_entry: { integration: "scadenze" } } },
  { name: "nascondi_ok", selector: { boolean: {} } },
  { name: "mostra_giorni", selector: { boolean: {} } },
  { name: "mostra_km", selector: { boolean: {} } },
  { name: "mostra_rinnovato", selector: { boolean: {} } },
];

const ETICHETTE_EDITOR = {
  it: {
    titolo: "Titolo",
    voce: "Voce (vuoto = tutte)",
    nascondi_ok: "Nascondi le scadenze in regola",
    mostra_giorni: "Mostra i giorni mancanti",
    mostra_km: "Mostra i km mancanti",
    mostra_rinnovato: "Mostra il pulsante Rinnovato",
  },
  en: {
    titolo: "Title",
    voce: "Item (empty = all)",
    nascondi_ok: "Hide deadlines that are fine",
    mostra_giorni: "Show days left",
    mostra_km: "Show kilometres left",
    mostra_rinnovato: "Show the Renewed button",
  },
};

class ScadenzeCardEditor extends HTMLElement {
  constructor() {
    super();
    this._config = {};
    this._hass = null;
    this._form = null;
  }

  setConfig(config) {
    this._config = { ...config };
    this._aggiorna();
  }

  set hass(hass) {
    this._hass = hass;
    this._aggiorna();
  }

  _aggiorna() {
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (campo) => ETICHETTE_EDITOR[lingua(this._hass)][campo.name] ?? campo.name;
      this._form.addEventListener("value-changed", (evento) => this._cambiata(evento.detail.value));
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = SCHEMA_EDITOR;
    this._form.data = normalizzaConfig(this._config);
  }

  _cambiata(valore) {
    const config = { ...valore };
    if (!config.titolo) delete config.titolo;
    if (!config.voce) delete config.voce;
    this._config = config;
    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }));
  }
}

if (!customElements.get("scadenze-card")) customElements.define("scadenze-card", ScadenzeCard);
if (!customElements.get("scadenze-card-editor")) customElements.define("scadenze-card-editor", ScadenzeCardEditor);

window.customCards = window.customCards ?? [];
if (!window.customCards.some((card) => card.type === "scadenze-card")) {
  window.customCards.push({
    type: "scadenze-card",
    name: "Scadenze",
    description: "Scadenze Auto & Casa a semaforo, con rinnovo confermato.",
    preview: true,
  });
}
