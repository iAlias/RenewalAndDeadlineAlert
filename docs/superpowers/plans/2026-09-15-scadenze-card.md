# Scadenze Auto & Casa — piano di implementazione della fase 2 (card)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** aggiungere all'integrazione `scadenze` una card Lovelace (`custom:scadenze-card`) con scadenze a semaforo, rinnovo confermato ed editor visuale, servita e registrata automaticamente dall'integrazione.

**Architecture:** due file JavaScript senza build in `custom_components/scadenze/frontend/`: `logica.js` (funzioni pure, testate con `node --test`) e `scadenze-card.js` (Web Component della card e del suo editor). Un nuovo `async_setup` registra la cartella come percorso statico e aggiunge il modulo al frontend con la versione dell'integrazione come parametro anti-cache.

**Tech Stack:** JavaScript ES2022 (moduli ES, top-level await), Node.js 22 (`node:test`), Home Assistant ≥ 2026.8, pytest con `pytest-homeassistant-custom-component==0.13.365`.

**Spec:** `docs/superpowers/specs/2026-09-15-scadenze-card-design.md`

## Global Constraints

- Nessuna dipendenza npm e nessun passaggio di build: i file in `frontend/` sono serviti così come sono.
- `logica.js` non accede al DOM né a `window`: solo funzioni pure esportate.
- Tipo della card `scadenze-card`, editor `scadenze-card-editor`, URL statico `/scadenze_static`.
- Testi della card in italiano (lingua che inizia con `it`) o inglese (tutte le altre).
- Colori solo tramite variabili del tema: `--error-color`, `--warning-color`, `--success-color`, `--disabled-text-color`.
- Rinnovo in due tempi, conferma valida 4 secondi, nessuna finestra di dialogo del browser.
- `manifest.json` passa a `version: "0.2.0"`.
- Test JavaScript: `node --test tests/card` (Node 22, rileva da solo la sintassi dei moduli ES). Test HA solo in CI (su Windows non girano).
- Ogni commit termina con:
  ```
  Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01DospB88Me7xwRVWZPkgCSn
  ```
- Branch di lavoro `fase-2` nel worktree `.claude/worktrees/fase-1`.

---

## Mappa dei file

| File | Responsabilità | Task |
|---|---|---|
| `custom_components/scadenze/frontend/logica.js` | raccolta dati da `hass`, filtri, ordinamento, testi, colori, formati | 1 |
| `tests/card/logica.test.mjs` | test della logica | 1 |
| `custom_components/scadenze/frontend/scadenze-card.js` | Web Component card + editor, registrazione in `customCards` | 2 |
| `custom_components/scadenze/const.py`, `__init__.py`, `manifest.json` | registrazione statica e nel frontend | 3 |
| `tests/ha/test_frontend.py` | file servito e modulo registrato | 3 |
| `.github/workflows/validate.yml`, `README.md` | job Node in CI, documentazione | 4 |

---

### Task 1: Logica pura della card

**Files:**
- Create: `custom_components/scadenze/frontend/logica.js`
- Test: `tests/card/logica.test.mjs`

**Interfaces:**
- Consumes: la forma di `hass` passata alle card: `hass.entities` (`{entity_id, platform, device_id, translation_key}`), `hass.devices` (`{name, name_by_user, via_device_id, config_entries}`), `hass.states` (`{state, attributes}`), `hass.locale.language`.
- Produces (`logica.js`):
  - `PIATTAFORMA = "scadenze"`, `OPZIONI_PREDEFINITE` (oggetto congelato);
  - `normalizzaConfig(config: object) -> object` (lancia `Error` se `config` non è un oggetto);
  - `raccogliScadenze(hass) -> Array<{id, nome, voce, voceId, data, stato, giorni, km, pulsante}>`;
  - `filtraEOrdina(scadenze, config) -> Array` (nuovo array);
  - `lingua(hass) -> "it" | "en"`; `testi(codice) -> object` con `rinnovato`, `conferma`, `vuota`;
  - `testoGiorni(scadenza, codice) -> string`; `coloreStato(stato) -> string`;
  - `formattaKm(km: number, codice) -> string`; `formattaData(data: string | null, codice) -> string`;
  - `puoRinnovare(scadenza) -> boolean`.

- [ ] **Step 1: Scrivere i test che falliscono**

`tests/card/logica.test.mjs`:

```js
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  coloreStato,
  filtraEOrdina,
  formattaData,
  formattaKm,
  lingua,
  normalizzaConfig,
  puoRinnovare,
  raccogliScadenze,
  testoGiorni,
} from "../../custom_components/scadenze/frontend/logica.js";

function entita(entity_id, device_id, translation_key, platform = "scadenze") {
  return { entity_id, device_id, translation_key, platform };
}

function hassDiProva() {
  const lista = [
    entita("sensor.panda_revisione", "dev_rev"),
    entita("sensor.panda_revisione_days_left", "dev_rev", "giorni_mancanti"),
    entita("binary_sensor.panda_revisione_due_soon", "dev_rev", "in_scadenza"),
    entita("button.panda_revisione_renewed", "dev_rev", "rinnovato"),
    entita("sensor.panda_bollo", "dev_bollo"),
    entita("sensor.panda_bollo_days_left", "dev_bollo", "giorni_mancanti"),
    entita("button.panda_bollo_renewed", "dev_bollo", "rinnovato"),
    entita("sensor.panda_tagliando", "dev_tag"),
    entita("sensor.panda_tagliando_days_left", "dev_tag", "giorni_mancanti"),
    entita("sensor.panda_tagliando_kilometres_left", "dev_tag", "km_mancanti"),
    entita("button.panda_tagliando_renewed", "dev_tag", "rinnovato"),
    entita("sensor.mario_carta_d_identita", "dev_cie"),
    entita("button.mario_carta_d_identita_renewed", "dev_cie", "rinnovato"),
    entita("calendar.panda_scadenze", "dev_panda", "calendario"),
    entita("todo.panda_da_rinnovare", "dev_panda", "da_rinnovare"),
    entita("sensor.panda_rotta", "dev_rotta"),
    entita("sensor.meteo", "dev_meteo", undefined, "met"),
  ];
  const dispositivo = (name, via_device_id, config_entries, name_by_user = null) => ({
    name,
    name_by_user,
    via_device_id,
    config_entries,
  });
  return {
    locale: { language: "it" },
    entities: Object.fromEntries(lista.map((e) => [e.entity_id, e])),
    devices: {
      dev_panda: dispositivo("Panda", null, ["entry_panda"]),
      dev_mario: dispositivo("Mario", null, ["entry_mario"]),
      dev_rev: dispositivo("Panda Revisione", "dev_panda", ["entry_panda"]),
      dev_bollo: dispositivo("Panda Bollo", "dev_panda", ["entry_panda"], "Bollo auto"),
      dev_tag: dispositivo("Panda Tagliando", "dev_panda", ["entry_panda"]),
      dev_cie: dispositivo("Mario Carta d'identità", "dev_mario", ["entry_mario"]),
      dev_rotta: dispositivo("Panda Rotta", "dev_panda", ["entry_panda"]),
    },
    states: {
      "sensor.panda_revisione": { state: "2026-09-30", attributes: { stato: "in_scadenza" } },
      "sensor.panda_revisione_days_left": { state: "16", attributes: {} },
      "sensor.panda_bollo": { state: "2026-08-31", attributes: { stato: "scaduta" } },
      "sensor.panda_bollo_days_left": { state: "-14", attributes: {} },
      "sensor.panda_tagliando": { state: "2027-03-01", attributes: { stato: "ok" } },
      "sensor.panda_tagliando_days_left": { state: "168", attributes: {} },
      "sensor.panda_tagliando_kilometres_left": { state: "35000", attributes: {} },
      "sensor.mario_carta_d_identita": { state: "unknown", attributes: { stato: "illimitata" } },
      "sensor.meteo": { state: "12", attributes: {} },
    },
  };
}

const perId = (scadenze) => Object.fromEntries(scadenze.map((s) => [s.id, s]));

test("raccoglie una scadenza per dispositivo con sensore della data", () => {
  const scadenze = raccogliScadenze(hassDiProva());
  assert.deepEqual(new Set(scadenze.map((s) => s.id)), new Set(["dev_rev", "dev_bollo", "dev_tag", "dev_cie"]));
});

test("compone la scadenza con voce, giorni, km e pulsante", () => {
  const { dev_rev, dev_tag, dev_cie } = perId(raccogliScadenze(hassDiProva()));
  assert.deepEqual(dev_rev, {
    id: "dev_rev",
    nome: "Revisione",
    voce: "Panda",
    voceId: "entry_panda",
    data: "2026-09-30",
    stato: "in_scadenza",
    giorni: 16,
    km: null,
    pulsante: "button.panda_revisione_renewed",
  });
  assert.equal(dev_tag.km, 35000);
  assert.equal(dev_cie.data, null);
  assert.equal(dev_cie.giorni, null);
  assert.equal(dev_cie.voce, "Mario");
});

test("il nome scelto dall'utente resta intero", () => {
  assert.equal(perId(raccogliScadenze(hassDiProva())).dev_bollo.nome, "Bollo auto");
});

test("ordina: scadute, poi per data, illimitate e completate in fondo", () => {
  const ordinate = filtraEOrdina(raccogliScadenze(hassDiProva()), {});
  assert.deepEqual(ordinate.map((s) => s.id), ["dev_bollo", "dev_rev", "dev_tag", "dev_cie"]);
});

test("filtra per voce e nasconde le scadenze ok", () => {
  const scadenze = raccogliScadenze(hassDiProva());
  assert.deepEqual(filtraEOrdina(scadenze, { voce: "entry_mario" }).map((s) => s.id), ["dev_cie"]);
  assert.deepEqual(filtraEOrdina(scadenze, { nascondi_ok: true }).map((s) => s.id), ["dev_bollo", "dev_rev"]);
});

test("testo dei giorni in italiano e inglese", () => {
  const casi = [
    [{ stato: "in_scadenza", giorni: 0 }, "oggi", "today"],
    [{ stato: "in_scadenza", giorni: 1 }, "domani", "tomorrow"],
    [{ stato: "ok", giorni: 16 }, "tra 16 giorni", "in 16 days"],
    [{ stato: "scaduta", giorni: -1 }, "scaduta ieri", "overdue since yesterday"],
    [{ stato: "scaduta", giorni: -14 }, "scaduta da 14 giorni", "overdue by 14 days"],
    [{ stato: "illimitata", giorni: null }, "illimitata", "no expiry"],
    [{ stato: "completata", giorni: null }, "completata", "done"],
    [{ stato: "ok", giorni: null }, "", ""],
  ];
  for (const [scadenza, it, en] of casi) {
    assert.equal(testoGiorni(scadenza, "it"), it);
    assert.equal(testoGiorni(scadenza, "en"), en);
  }
});

test("colore per stato", () => {
  assert.equal(coloreStato("scaduta"), "var(--error-color)");
  assert.equal(coloreStato("in_scadenza"), "var(--warning-color)");
  assert.equal(coloreStato("ok"), "var(--success-color)");
  assert.equal(coloreStato("illimitata"), "var(--disabled-text-color)");
  assert.equal(coloreStato("completata"), "var(--disabled-text-color)");
});

test("formati di km e data", () => {
  assert.equal(formattaKm(35000, "it"), "35.000 km");
  assert.equal(formattaKm(35000, "en"), "35,000 km");
  assert.equal(formattaData("2026-09-30", "it"), "30/09/2026");
  assert.equal(formattaData(null, "it"), "");
});

test("lingua dei testi", () => {
  assert.equal(lingua({ locale: { language: "it-IT" } }), "it");
  assert.equal(lingua({ locale: { language: "en" } }), "en");
  assert.equal(lingua({}), "en");
});

test("configurazione con valori predefiniti", () => {
  assert.deepEqual(normalizzaConfig({ titolo: "Casa" }), {
    titolo: "Casa",
    voce: "",
    nascondi_ok: false,
    mostra_giorni: true,
    mostra_km: true,
    mostra_rinnovato: true,
  });
  for (const sbagliata of [null, [], "scadenze"]) {
    assert.throws(() => normalizzaConfig(sbagliata));
  }
});

test("si può rinnovare solo con pulsante e scadenza attiva", () => {
  const { dev_rev, dev_cie } = perId(raccogliScadenze(hassDiProva()));
  assert.equal(puoRinnovare(dev_rev), true);
  assert.equal(puoRinnovare(dev_cie), false);
  assert.equal(puoRinnovare({ ...dev_rev, pulsante: null }), false);
});
```

- [ ] **Step 2: Eseguire i test e verificare che falliscono**

Run: `node --test tests/card`
Expected: FAIL con `ERR_MODULE_NOT_FOUND` per `custom_components/scadenze/frontend/logica.js`

- [ ] **Step 3: Implementare**

`custom_components/scadenze/frontend/logica.js`:

```js
// Logica della card Scadenze: funzioni pure, nessun accesso al DOM.

export const PIATTAFORMA = "scadenze";

export const OPZIONI_PREDEFINITE = Object.freeze({
  titolo: "",
  voce: "",
  nascondi_ok: false,
  mostra_giorni: true,
  mostra_km: true,
  mostra_rinnovato: true,
});

// Scadute in cima, poi le altre per data; senza data (illimitate, completate) in fondo.
const GRUPPO_ORDINE = { scaduta: 0, in_scadenza: 1, ok: 1, illimitata: 2, completata: 2 };
const STATI_VISIBILI_SE_NASCONDI_OK = new Set(["scaduta", "in_scadenza"]);
const STATI_SENZA_RINNOVO = new Set(["illimitata", "completata"]);
const DATA_ISO = /^\d{4}-\d{2}-\d{2}$/;

const TESTI = {
  it: {
    oggi: "oggi",
    domani: "domani",
    tra: (n) => `tra ${n} giorni`,
    ieri: "scaduta ieri",
    scadutaDa: (n) => `scaduta da ${n} giorni`,
    illimitata: "illimitata",
    completata: "completata",
    rinnovato: "Rinnovato",
    conferma: "Conferma",
    vuota: "Nessuna scadenza da mostrare",
  },
  en: {
    oggi: "today",
    domani: "tomorrow",
    tra: (n) => `in ${n} days`,
    ieri: "overdue since yesterday",
    scadutaDa: (n) => `overdue by ${n} days`,
    illimitata: "no expiry",
    completata: "done",
    rinnovato: "Renewed",
    conferma: "Confirm",
    vuota: "No deadlines to show",
  },
};

export function normalizzaConfig(config) {
  if (config === null || typeof config !== "object" || Array.isArray(config)) {
    throw new Error("Configurazione della card non valida");
  }
  return { ...OPZIONI_PREDEFINITE, ...config };
}

function nomeDispositivo(dispositivo) {
  if (!dispositivo) return "";
  return dispositivo.name_by_user ?? dispositivo.name ?? "";
}

function numero(stato) {
  if (!stato || stato.state === "" || stato.state === null) return null;
  const valore = Number(stato.state);
  return Number.isFinite(valore) ? valore : null;
}

export function raccogliScadenze(hass) {
  const gruppi = new Map();
  for (const voce of Object.values(hass.entities ?? {})) {
    if (voce.platform !== PIATTAFORMA || !voce.device_id) continue;
    const gruppo = gruppi.get(voce.device_id) ?? {};
    const dominio = voce.entity_id.split(".")[0];
    if (voce.translation_key === "giorni_mancanti") gruppo.giorni = voce.entity_id;
    else if (voce.translation_key === "km_mancanti") gruppo.km = voce.entity_id;
    else if (voce.translation_key === "rinnovato") gruppo.pulsante = voce.entity_id;
    else if (dominio === "sensor" && !voce.translation_key) gruppo.data = voce.entity_id;
    gruppi.set(voce.device_id, gruppo);
  }

  const scadenze = [];
  for (const [deviceId, gruppo] of gruppi) {
    const statoData = gruppo.data ? hass.states?.[gruppo.data] : undefined;
    if (!statoData?.attributes || statoData.attributes.stato === undefined) continue;

    const dispositivo = hass.devices?.[deviceId];
    const dispositivoVoce = dispositivo?.via_device_id ? hass.devices?.[dispositivo.via_device_id] : undefined;
    const voce = nomeDispositivo(dispositivoVoce);
    let nome = nomeDispositivo(dispositivo);
    if (voce && nome.startsWith(`${voce} `)) nome = nome.slice(voce.length + 1);

    scadenze.push({
      id: deviceId,
      nome,
      voce,
      voceId: dispositivoVoce?.config_entries?.[0] ?? null,
      data: DATA_ISO.test(statoData.state) ? statoData.state : null,
      stato: statoData.attributes.stato,
      giorni: gruppo.giorni ? numero(hass.states?.[gruppo.giorni]) : null,
      km: gruppo.km ? numero(hass.states?.[gruppo.km]) : null,
      pulsante: gruppo.pulsante ?? null,
    });
  }
  return scadenze;
}

export function filtraEOrdina(scadenze, config) {
  const opzioni = normalizzaConfig(config);
  return scadenze
    .filter((s) => !opzioni.voce || s.voceId === opzioni.voce)
    .filter((s) => !opzioni.nascondi_ok || STATI_VISIBILI_SE_NASCONDI_OK.has(s.stato))
    .sort((a, b) => {
      const gruppo = (GRUPPO_ORDINE[a.stato] ?? 3) - (GRUPPO_ORDINE[b.stato] ?? 3);
      if (gruppo !== 0) return gruppo;
      const data = (a.data ?? "9999-99-99").localeCompare(b.data ?? "9999-99-99");
      return data !== 0 ? data : a.nome.localeCompare(b.nome);
    });
}

export function lingua(hass) {
  const codice = String(hass?.locale?.language ?? hass?.language ?? "en").toLowerCase();
  return codice.startsWith("it") ? "it" : "en";
}

export function testi(codice) {
  return TESTI[codice] ?? TESTI.en;
}

export function testoGiorni(scadenza, codice) {
  const t = testi(codice);
  if (scadenza.stato === "illimitata") return t.illimitata;
  if (scadenza.stato === "completata") return t.completata;
  const n = scadenza.giorni;
  if (n === null || n === undefined) return "";
  if (n === 0) return t.oggi;
  if (n === 1) return t.domani;
  if (n > 1) return t.tra(n);
  if (n === -1) return t.ieri;
  return t.scadutaDa(-n);
}

export function coloreStato(stato) {
  switch (stato) {
    case "scaduta":
      return "var(--error-color)";
    case "in_scadenza":
      return "var(--warning-color)";
    case "ok":
      return "var(--success-color)";
    default:
      return "var(--disabled-text-color)";
  }
}

export function formattaKm(km, codice) {
  return `${new Intl.NumberFormat(codice === "it" ? "it-IT" : "en-US").format(km)} km`;
}

export function formattaData(data, codice) {
  if (!data) return "";
  const [anno, mese, giorno] = data.split("-").map(Number);
  return new Intl.DateTimeFormat(codice === "it" ? "it-IT" : "en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(anno, mese - 1, giorno)));
}

export function puoRinnovare(scadenza) {
  return Boolean(scadenza.pulsante) && !STATI_SENZA_RINNOVO.has(scadenza.stato);
}
```

- [ ] **Step 4: Eseguire i test e verificare che passano**

Run: `node --test tests/card`
Expected: PASS (11 test)

- [ ] **Step 5: Commit**

```bash
git add custom_components/scadenze/frontend/logica.js tests/card/logica.test.mjs
git commit -m "feat: logica della card delle scadenze"
```

### Task 2: Web Component della card e dell'editor

**Files:**
- Create: `custom_components/scadenze/frontend/scadenze-card.js`
- Test: `tests/card/card.test.mjs`

**Interfaces:**
- Consumes: tutte le funzioni di `logica.js` (Task 1).
- Produces:
  - elemento `scadenze-card` (classe `ScadenzeCard`) con `setConfig(config)`, setter `hass`, `getCardSize()`,
    statici `getConfigElement()` e `getStubConfig()`;
  - elemento `scadenze-card-editor` (classe `ScadenzeCardEditor`) con `setConfig(config)`, setter `hass`,
    evento `config-changed` con `detail.config`;
  - voce `{ type: "scadenze-card", name: "Scadenze", description, preview: true }` in `window.customCards`.

- [ ] **Step 1: Scrivere i test che falliscono**

`tests/card/card.test.mjs`:

```js
import { test } from "node:test";
import assert from "node:assert/strict";

// Elementi DOM minimi: bastano per costruire la card e leggerne l'HTML generato.
class ElementoFinto {
  constructor() {
    this.ascoltatori = {};
    this.dataset = {};
    this.figli = [];
  }
  attachShadow() {
    this.shadowRoot = new ElementoFinto();
    this.shadowRoot.innerHTML = "";
    return this.shadowRoot;
  }
  addEventListener(tipo, funzione) {
    (this.ascoltatori[tipo] ??= []).push(funzione);
  }
  dispatchEvent(evento) {
    for (const funzione of this.ascoltatori[evento.type] ?? []) funzione(evento);
    return true;
  }
  appendChild(figlio) {
    this.figli.push(figlio);
    return figlio;
  }
}

const registro = new Map();
globalThis.HTMLElement = ElementoFinto;
globalThis.customElements = {
  define: (nome, classe) => registro.set(nome, classe),
  get: (nome) => registro.get(nome),
};
globalThis.window = globalThis;
globalThis.document = {
  createElement: (nome) => {
    const Classe = registro.get(nome);
    return Classe ? new Classe() : new ElementoFinto();
  },
};
globalThis.CustomEvent = class {
  constructor(type, init = {}) {
    this.type = type;
    this.detail = init.detail;
  }
};

await import("../../custom_components/scadenze/frontend/scadenze-card.js");

function hassDiProva(chiamate = []) {
  const entita = (entity_id, device_id, translation_key) => ({
    entity_id,
    device_id,
    translation_key,
    platform: "scadenze",
  });
  const lista = [
    entita("sensor.panda_revisione", "dev_rev"),
    entita("sensor.panda_revisione_days_left", "dev_rev", "giorni_mancanti"),
    entita("button.panda_revisione_renewed", "dev_rev", "rinnovato"),
    entita("sensor.mario_carta_d_identita", "dev_cie"),
    entita("button.mario_carta_d_identita_renewed", "dev_cie", "rinnovato"),
  ];
  const dispositivo = (name, via_device_id, config_entries) => ({
    name,
    name_by_user: null,
    via_device_id,
    config_entries,
  });
  return {
    locale: { language: "it" },
    entities: Object.fromEntries(lista.map((e) => [e.entity_id, e])),
    devices: {
      dev_panda: dispositivo("Panda", null, ["entry_panda"]),
      dev_mario: dispositivo("Mario", null, ["entry_mario"]),
      dev_rev: dispositivo("Panda Revisione", "dev_panda", ["entry_panda"]),
      dev_cie: dispositivo("Mario Carta d'identità", "dev_mario", ["entry_mario"]),
    },
    states: {
      "sensor.panda_revisione": { state: "2026-09-30", attributes: { stato: "in_scadenza" } },
      "sensor.panda_revisione_days_left": { state: "16", attributes: {} },
      "sensor.mario_carta_d_identita": { state: "unknown", attributes: { stato: "illimitata" } },
    },
    callService: (dominio, servizio, dati) => chiamate.push([dominio, servizio, dati]),
  };
}

function nuovaCard(config, hass) {
  const card = document.createElement("scadenze-card");
  card.setConfig(config);
  card.hass = hass;
  return card;
}

function clicSulPulsante(card, entita) {
  const pulsante = { dataset: { entita } };
  card.shadowRoot.dispatchEvent({ type: "click", target: { closest: () => pulsante } });
}

test("registra card, editor e voce nel selettore delle card", () => {
  assert.ok(customElements.get("scadenze-card"));
  assert.ok(customElements.get("scadenze-card-editor"));
  assert.deepEqual(
    window.customCards.filter((c) => c.type === "scadenze-card").map((c) => [c.name, c.preview]),
    [["Scadenze", true]],
  );
  assert.deepEqual(customElements.get("scadenze-card").getStubConfig(), { titolo: "Scadenze" });
});

test("mostra titolo, voce, data, giorni e un solo pulsante", () => {
  const html = nuovaCard({ titolo: "Scadenze" }, hassDiProva()).shadowRoot.innerHTML;
  for (const atteso of ['header="Scadenze"', "Revisione", "<span>Panda</span>", "30/09/2026", "tra 16 giorni", "Rinnovato", "illimitata"]) {
    assert.ok(html.includes(atteso), `manca ${atteso}`);
  }
  assert.equal(html.split("data-entita=").length - 1, 1);
});

test("con una voce sola non ripete il nome della voce", () => {
  const html = nuovaCard({ voce: "entry_panda" }, hassDiProva()).shadowRoot.innerHTML;
  assert.ok(html.includes("Revisione"));
  assert.ok(!html.includes("<span>Panda</span>"));
  assert.ok(!html.includes("Carta d'identità"));
});

test("lista vuota", () => {
  const hass = hassDiProva();
  hass.states["sensor.panda_revisione"].attributes.stato = "ok";
  const html = nuovaCard({ nascondi_ok: true }, hass).shadowRoot.innerHTML;
  assert.ok(html.includes("Nessuna scadenza da mostrare"));
});

test("il rinnovo chiede conferma prima di premere il pulsante", () => {
  const chiamate = [];
  const card = nuovaCard({}, hassDiProva(chiamate));

  clicSulPulsante(card, "button.panda_revisione_renewed");
  assert.ok(card.shadowRoot.innerHTML.includes("Conferma"));
  assert.deepEqual(chiamate, []);

  clicSulPulsante(card, "button.panda_revisione_renewed");
  assert.deepEqual(chiamate, [["button", "press", { entity_id: "button.panda_revisione_renewed" }]]);
  assert.ok(!card.shadowRoot.innerHTML.includes("Conferma"));
});

test("dimensione della card", () => {
  assert.equal(nuovaCard({}, hassDiProva()).getCardSize(), 3);
});

test("l'editor emette la configurazione senza voce e titolo vuoti", () => {
  const editor = document.createElement("scadenze-card-editor");
  const ricevute = [];
  editor.addEventListener("config-changed", (evento) => ricevute.push(evento.detail.config));
  editor.setConfig({ type: "custom:scadenze-card" });
  editor.hass = hassDiProva();

  const form = editor.figli[0];
  assert.equal(form.data.mostra_giorni, true);
  assert.equal(form.schema.find((campo) => campo.name === "voce").selector.config_entry.integration, "scadenze");

  form.dispatchEvent({
    type: "value-changed",
    detail: {
      value: {
        type: "custom:scadenze-card",
        titolo: "",
        voce: "",
        nascondi_ok: true,
        mostra_giorni: true,
        mostra_km: true,
        mostra_rinnovato: true,
      },
    },
  });

  assert.deepEqual(ricevute, [
    {
      type: "custom:scadenze-card",
      nascondi_ok: true,
      mostra_giorni: true,
      mostra_km: true,
      mostra_rinnovato: true,
    },
  ]);
});
```

- [ ] **Step 2: Eseguire i test e verificare che falliscono**

Run: `node --test tests/card`
Expected: FAIL in `card.test.mjs` con `ERR_MODULE_NOT_FOUND` per `scadenze-card.js`; i test di `logica.test.mjs` passano

- [ ] **Step 3: Implementare**

`custom_components/scadenze/frontend/scadenze-card.js`:

```js
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
```

- [ ] **Step 4: Eseguire i test e verificare che passano**

Run: `node --test tests/card`
Expected: PASS (11 test di `logica.test.mjs` e 7 di `card.test.mjs`)

- [ ] **Step 5: Commit**

```bash
git add custom_components/scadenze/frontend/scadenze-card.js tests/card/card.test.mjs
git commit -m "feat: card Lovelace delle scadenze con editor visuale"
```

### Task 3: Registrazione della card da parte dell'integrazione

**Files:**
- Modify: `custom_components/scadenze/const.py` (in fondo al file)
- Modify: `custom_components/scadenze/__init__.py` (import, `CONFIG_SCHEMA`, `async_setup`, `_aggiungi_modulo_frontend`)
- Modify: `custom_components/scadenze/manifest.json`
- Test: `tests/ha/test_frontend.py`

**Interfaces:**
- Consumes: i file `frontend/*.js` (Task 1 e 2); `tests/ha/common.py::configura`, `crea_voce_veicolo` (fase 1).
- Produces:
  - `const.py`: `URL_STATICO = "/scadenze_static"`, `NOME_FILE_CARD = "scadenze-card.js"`, `CHIAVE_FRONTEND_REGISTRATO`;
  - `__init__.py`: `CONFIG_SCHEMA`, `CARTELLA_FRONTEND: Path`, `async async_setup(hass, config) -> bool`,
    `_aggiungi_modulo_frontend(hass, url: str) -> None`.

- [ ] **Step 1: Scrivere i test che falliscono**

`tests/ha/test_frontend.py`:

```python
"""La card è servita dall'integrazione e registrata nel frontend (spec fase 2, §3 e §7)."""

from __future__ import annotations

from unittest.mock import patch

from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.scadenze import async_setup
from homeassistant.core import HomeAssistant

from .common import configura, crea_voce_veicolo


async def test_i_file_della_card_sono_serviti(
    hass: HomeAssistant, hass_client: ClientSessionGenerator
) -> None:
    await configura(hass, crea_voce_veicolo())
    client = await hass_client()

    card = await client.get("/scadenze_static/scadenze-card.js")
    assert card.status == 200
    assert "customElements.define" in await card.text()

    logica = await client.get("/scadenze_static/logica.js")
    assert logica.status == 200


async def test_modulo_aggiunto_al_frontend_con_la_versione(hass: HomeAssistant) -> None:
    hass.config.components.add("frontend")
    with patch("custom_components.scadenze._aggiungi_modulo_frontend") as aggiungi:
        await configura(hass, crea_voce_veicolo())

    aggiungi.assert_called_once_with(hass, "/scadenze_static/scadenze-card.js?v=0.2.0")


async def test_senza_frontend_nessun_modulo(hass: HomeAssistant) -> None:
    with patch("custom_components.scadenze._aggiungi_modulo_frontend") as aggiungi:
        await configura(hass, crea_voce_veicolo())

    aggiungi.assert_not_called()


async def test_la_registrazione_avviene_una_volta_sola(hass: HomeAssistant) -> None:
    await configura(hass, crea_voce_veicolo())

    with patch.object(hass.http, "async_register_static_paths") as registra:
        assert await async_setup(hass, {})

    registra.assert_not_called()
```

- [ ] **Step 2: Eseguire i test e verificare che falliscono**

Run (ambiente completo, Linux/CI): `pytest tests/ha/test_frontend.py -q`
Expected: FAIL con `ImportError: cannot import name 'async_setup' from 'custom_components.scadenze'`

- [ ] **Step 3: Implementare**

In fondo a `custom_components/scadenze/const.py` aggiungere:

```python

# Card Lovelace (fase 2)
URL_STATICO: Final = "/scadenze_static"
NOME_FILE_CARD: Final = "scadenze-card.js"
CHIAVE_FRONTEND_REGISTRATO: Final = f"{DOMAIN}_frontend_registrato"
```

In `custom_components/scadenze/__init__.py`:

1. sostituire il blocco degli import con:

```python
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration
from homeassistant.util import dt as dt_util

from .const import (
    CHIAVE_FRONTEND_REGISTRATO,
    DOMAIN,
    ETICHETTE_TIPO_VOCE,
    NOME_FILE_CARD,
    URL_STATICO,
)
from .coordinator import ScadenzeCoordinator
from .notifiche import GestoreNotifiche

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
CARTELLA_FRONTEND = Path(__file__).parent / "frontend"
```

2. subito prima di `async def async_setup_entry(` aggiungere:

```python
async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve i file della card e li aggiunge al frontend, una sola volta per avvio."""
    if hass.data.get(CHIAVE_FRONTEND_REGISTRATO):
        return True
    hass.data[CHIAVE_FRONTEND_REGISTRATO] = True

    await hass.http.async_register_static_paths(
        [StaticPathConfig(URL_STATICO, str(CARTELLA_FRONTEND), True)]
    )
    if "frontend" in hass.config.components:
        integrazione = await async_get_integration(hass, DOMAIN)
        _aggiungi_modulo_frontend(hass, f"{URL_STATICO}/{NOME_FILE_CARD}?v={integrazione.version}")
    return True


def _aggiungi_modulo_frontend(hass: HomeAssistant, url: str) -> None:
    """Importa il frontend solo quando serve: nell'ambiente di test il suo pacchetto non c'è."""
    from homeassistant.components.frontend import add_extra_js_url  # noqa: PLC0415

    add_extra_js_url(hass, url)


```

`custom_components/scadenze/manifest.json` diventa:

```json
{
  "domain": "scadenze",
  "name": "Scadenze Auto & Casa",
  "after_dependencies": ["frontend"],
  "codeowners": ["@iAlias"],
  "config_flow": true,
  "dependencies": ["http"],
  "documentation": "https://github.com/iAlias/ScadenzeAutoCasaSalute",
  "integration_type": "service",
  "iot_class": "calculated",
  "issue_tracker": "https://github.com/iAlias/ScadenzeAutoCasaSalute/issues",
  "requirements": [],
  "version": "0.2.0"
}
```

- [ ] **Step 4: Eseguire i test e verificare che passano**

Run (ambiente completo): `pytest -q`
Expected: PASS, compresi tutti i test della fase 1 (ora caricano anche `http`)

- [ ] **Step 5: Commit**

```bash
git add custom_components/scadenze/const.py custom_components/scadenze/__init__.py custom_components/scadenze/manifest.json tests/ha/test_frontend.py
git commit -m "feat: l'integrazione serve e registra la card"
```

### Task 4: CI, README e pubblicazione

**Files:**
- Modify: `.github/workflows/validate.yml` (nuovo job `card` in fondo)
- Modify: `README.md` (nuova sezione prima di `## Limiti dichiarati`)

**Interfaces:**
- Consumes: `tests/card/*.test.mjs` (Task 1 e 2), tutta la suite pytest.
- Produces: CI con quattro job (`hassfest`, `hacs`, `test`, `card`), documentazione della card.

- [ ] **Step 1: Aggiungere il job della card**

In fondo a `.github/workflows/validate.yml` aggiungere, allineato agli altri job:

```yaml

  card:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
      - run: node --test tests/card
```

- [ ] **Step 2: Documentare la card**

In `README.md`, subito prima della riga `## Limiti dichiarati`, inserire:

````markdown
## La card

L'integrazione porta con sé una card Lovelace già registrata: non serve aggiungere risorse alla dashboard.
Si trova nel selettore delle card come **Scadenze** e si configura anche dall'editor visuale.

```yaml
type: custom:scadenze-card
titolo: Scadenze
voce: <voce>            # facoltativo: senza, mostra tutte le voci
nascondi_ok: false
mostra_giorni: true
mostra_km: true
mostra_rinnovato: true
```

| Opzione | Predefinito | Cosa fa |
|---|---|---|
| `titolo` | nessuno | Intestazione della card |
| `voce` | tutte | Mostra solo le scadenze di una voce |
| `nascondi_ok` | `false` | Mostra solo le scadenze superate o vicine |
| `mostra_giorni` | `true` | Aggiunge «tra N giorni» o «scaduta da N giorni» |
| `mostra_km` | `true` | Aggiunge i km mancanti al tagliando |
| `mostra_rinnovato` | `true` | Pulsante «Rinnovato»: il primo clic chiede conferma, il secondo rinnova |

Ogni riga ha una striscia colorata: rossa se la scadenza è superata, ambra se è vicina, verde se è in regola,
grigia se è illimitata o completata.

````

- [ ] **Step 3: Verifica locale della parte JavaScript**

Run: `node --test tests/card`
Expected: PASS (18 test)

- [ ] **Step 4: Commit e push del branch**

```bash
git add .github/workflows/validate.yml README.md
git commit -m "ci: test della card; docs: sezione La card nel README"
git push -u origin fase-2
```

- [ ] **Step 5: Verifica in CI**

Su GitHub Actions il run di `fase-2` deve avere `hassfest`, `test` e `card` verdi (`hacs` è saltato fuori dal
branch predefinito). Se `test` fallisce per il caricamento di `http`, leggere l'annotazione (stato e motivo della
entry) prima di cambiare codice.

- [ ] **Step 6: Pull Request**

Con la conferma dell'utente, aprire la PR `fase-2 → main` con il riepilogo della card e le righe di attribuzione,
attendere i controlli verdi e unirla solo se l'utente lo chiede.
