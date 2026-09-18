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

test("modalita scelte mostra solo le scadenze indicate, in qualunque ordine di selezione", () => {
  const scadenze = raccogliScadenze(hassDiProva());
  assert.deepEqual(
    filtraEOrdina(scadenze, { modalita: "scelte", scelte: ["dev_tag", "dev_bollo"] }).map((s) => s.id),
    ["dev_bollo", "dev_tag"],
  );
  assert.deepEqual(filtraEOrdina(scadenze, { modalita: "scelte", scelte: [] }).map((s) => s.id), []);
});

test("senza modalita si comporta come prima: voce se impostata, altrimenti tutte", () => {
  const scadenze = raccogliScadenze(hassDiProva());
  assert.deepEqual(
    filtraEOrdina(scadenze, { voce: "entry_mario" }).map((s) => s.id),
    filtraEOrdina(scadenze, { modalita: "voce", voce: "entry_mario" }).map((s) => s.id),
  );
  assert.deepEqual(
    filtraEOrdina(scadenze, {}).map((s) => s.id),
    filtraEOrdina(scadenze, { modalita: "tutte" }).map((s) => s.id),
  );
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
    modalita: "",
    scelte: [],
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
