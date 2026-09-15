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
  assert.ok(!html.includes("Carta d"));
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
