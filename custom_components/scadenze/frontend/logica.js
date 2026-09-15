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
