# Scadenze Auto & Casa — design della fase 2: card Lovelace

- **Data:** 2026-09-15
- **Stato:** approvato in chat, in revisione come documento
- **Base:** fase 1 unita in `main` (`iAlias/ScadenzeAutoCasaSalute`), spec `2026-09-14-scadenze-auto-casa-design.md`.

## 1. Obiettivo

Una card Lovelace che mostra le scadenze dell'integrazione `scadenze` con un colore a semaforo, permette di
rinnovarle con un clic confermato e si configura dall'editor visuale. Si installa insieme all'integrazione:
nessuna risorsa da aggiungere a mano.

### Decisioni prese con l'utente

| Tema | Decisione |
|---|---|
| Contenuto | Entrambe le modalità: tutte le voci oppure una sola voce |
| Distribuzione | Servita dall'integrazione, registrata automaticamente nel frontend |
| Funzioni | Pulsante «Rinnovato», opzione per nascondere le scadenze ok, giorni e km mancanti, editor visuale |
| Tecnologia | Web Component in JavaScript moderno, senza passaggi di build |
| Conferma del rinnovo | In due tempi dentro la card, senza finestre di dialogo |

### Fuori perimetro

- Colori personalizzabili, raggruppamento con intestazioni per voce, ordinamenti diversi dalla data.
- Card dedicata a una singola scadenza.
- Lingue diverse da italiano e inglese.
- Test di rendering in un browser reale (la logica è testata a parte, §7).

## 2. File

```
custom_components/scadenze/
├── __init__.py              + async_setup: registra i file statici e il modulo nel frontend
├── const.py                 + URL_STATICO, NOME_FILE_CARD
├── manifest.json            + dependencies: http; after_dependencies: frontend; version 0.2.0
└── frontend/
    ├── scadenze-card.js     Web Component della card e del suo editor
    └── logica.js            modulo puro: raccolta, filtri, ordinamento, testi
tests/
├── card/logica.test.mjs     node --test, nessuna dipendenza npm
└── ha/test_frontend.py      il file è servito e registrato nel frontend
.github/workflows/validate.yml  + job card (Node)
README.md                    + sezione «La card»
```

## 3. Registrazione nel frontend

- `async_setup(hass, config)` (una volta per avvio di Home Assistant, non per voce):
  1. `await hass.http.async_register_static_paths([StaticPathConfig(URL_STATICO, <cartella frontend>, True)])`
     con `URL_STATICO = "/scadenze_static"`;
  2. se `"frontend" in hass.config.components`, `add_extra_js_url(hass, f"{URL_STATICO}/scadenze-card.js?v={versione}")`,
     dove `versione` è la versione dell'integrazione letta con `async_get_integration(hass, DOMAIN)`.
- Il manifest dichiara `dependencies: ["http"]` e `after_dependencies: ["frontend"]`: in un'installazione reale il
  frontend è sempre caricato prima dell'integrazione, mentre nell'ambiente di test il pacchetto del frontend non è
  installato e renderlo una dipendenza impedirebbe l'avvio di tutti i test.
- Una guardia in `hass.data` evita doppie registrazioni se `async_setup` venisse richiamato.
- Poiché l'integrazione ora definisce `async_setup`, il modulo dichiara
  `CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)` (richiesto da hassfest).
- `scadenze-card.js` importa `logica.js` con la stessa query di versione ricavata da `import.meta.url`
  (`await import("./logica.js" + new URL(import.meta.url).search)`), così un aggiornamento non lascia in cache
  una logica vecchia.

## 4. Da dove prende i dati

Nessuna nuova API: solo gli oggetti che il frontend passa a ogni card.

- **Scadenze:** in `hass.entities` le voci con `platform === "scadenze"`, raggruppate per `device_id`
  (il dispositivo della scadenza):
  - sensore della data: entità `sensor.*` senza `translation_key`, il cui stato ha l'attributo `stato`;
  - giorni mancanti: `translation_key === "giorni_mancanti"`;
  - km mancanti: `translation_key === "km_mancanti"`;
  - pulsante: `translation_key === "rinnovato"`.
- **Voce:** `hass.devices[device_id].via_device_id` porta al dispositivo della voce, da cui si leggono
  `name_by_user ?? name` e `config_entries[0]` (l'id della config entry, usato dal filtro `voce`).
- **Nome della scadenza:** dal dispositivo della scadenza (`name_by_user ?? name`), togliendo il prefisso
  «nome voce + spazio» quando presente.
- Un gruppo senza sensore della data o senza stato viene ignorato.

Ogni scadenza raccolta diventa un oggetto
`{ id, nome, voce, voceId, data, stato, giorni, km, pulsante }`
(`data` stringa ISO o `null`, `giorni` e `km` numeri o `null`, `pulsante` entity_id o `null`).

## 5. Configurazione

```yaml
type: custom:scadenze-card
titolo: Scadenze          # facoltativo; senza titolo nessuna intestazione
voce: <config_entry_id>   # facoltativo; assente = tutte le voci
nascondi_ok: false        # true = solo scadute e in scadenza
mostra_giorni: true
mostra_km: true
mostra_rinnovato: true
```

- Valori mancanti = predefiniti sopra. `setConfig` rifiuta una configurazione che non è un oggetto.
- `getStubConfig()` restituisce `{ titolo: "Scadenze" }`.
- **Editor visuale** (`scadenze-card-editor`): `ha-form` con lo schema
  `titolo` (text), `voce` (selector `config_entry` con `integration: scadenze`), e i quattro booleani.
  A ogni modifica emette l'evento `config-changed`.
- La card si registra in `window.customCards` con tipo `scadenze-card`, nome «Scadenze» e anteprima attiva.

## 6. Aspetto e comportamento

- **Ordine:** `scaduta`, poi per data crescente; `illimitata` e `completata` in fondo.
- **Filtri:** `voce` tiene solo la voce scelta; `nascondi_ok` toglie `ok`, `illimitata`, `completata`.
- **Riga:** striscia colorata a sinistra, nome della scadenza, nome della voce (solo in modalità «tutte»),
  data formattata con `Intl.DateTimeFormat` nella lingua di `hass.locale`, testo dei giorni, km mancanti,
  pulsante.
- **Colori** (variabili del tema, quindi validi in chiaro e in scuro):
  `scaduta` → `--error-color`, `in_scadenza` → `--warning-color`, `ok` → `--success-color`,
  `illimitata`/`completata` → `--disabled-text-color`.
- **Testo dei giorni:** `0` «oggi», `1` «domani», `N>1` «tra N giorni», `-1` «scaduta ieri»,
  `N<-1` «scaduta da N giorni»; `illimitata` «illimitata»; `completata` «completata».
  In inglese: «today», «tomorrow», «in N days», «overdue since yesterday», «overdue by N days»,
  «no expiry», «done».
- **Km:** «N km» con separatore delle migliaia della lingua; mostrati solo se `mostra_km` e il valore esiste.
- **Rinnovato:** primo clic → il pulsante diventa «Conferma» per 4 secondi; secondo clic →
  `hass.callService("button", "press", { entity_id })`; allo scadere dei 4 secondi torna «Rinnovato».
  Non compare per `illimitata` e `completata`.
- **Lista vuota:** «Nessuna scadenza da mostrare» / «No deadlines to show».
- **Lingua dei testi della card:** italiano se `hass.locale.language` inizia con `it`, altrimenti inglese.
- `getCardSize()` = 1 + numero di righe (minimo 2).

## 7. Test

- **Logica (`node --test tests/card`)**, con oggetti `hass` finti:
  raccolta e raggruppamento, nome della voce e della scadenza, filtro per voce, `nascondi_ok`,
  ordinamento, testi dei giorni in italiano e inglese, colore per stato, formato dei km,
  gruppi incompleti ignorati.
- **Card (`node --test tests/card`)**, con elementi DOM finti al posto del browser: registrazione di card,
  editor e `customCards`; righe con voce, data, giorni e pulsante; modalità a voce singola; lista vuota;
  rinnovo in due tempi che chiama `button.press` solo alla conferma; l'editor emette `config-changed` senza
  `voce` e `titolo` vuoti.
- **Backend (pytest, CI):** dopo il setup il file `scadenze-card.js` risponde 200 all'URL statico e
  contiene `customElements.define`; con `frontend` fra i componenti caricati, `add_extra_js_url` riceve l'URL
  con la versione (verificato con un mock); senza `frontend` non viene chiamata; una seconda chiamata a
  `async_setup` non registra due volte.
- **CI:** nuovo job `card` con `actions/setup-node` (Node 22) che esegue `node --test tests/card`.

## 8. Distribuzione

- `manifest.json`: `dependencies: ["http"]`, `after_dependencies: ["frontend"]`, `version: "0.2.0"`.
- README: sezione «La card» con esempio YAML, opzioni e schermata descritta a parole.
