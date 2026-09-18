# Scadenze Auto & Casa — design: configurazione guidata e card con scadenze scelte

- **Data:** 2026-09-18
- **Stato:** approvato in chat, in revisione come documento
- **Base:** fase 1 (integrazione) e fase 2 (card) unite in `main` di `iAlias/ScadenzeAutoCasaSalute`,
  versione `0.2.0`.
- **Perimetro:** preparare la repo alla pubblicazione su HACS default, semplificando la configurazione
  iniziale e permettendo alla card di mostrare solo alcune scadenze scelte a mano.

## 1. Obiettivo

Oggi, dopo aver creato una voce (veicolo/casa/persona), ogni scadenza va aggiunta con un'azione separata
dalla pagina del dispositivo, una alla volta. Per un'auto tipica (revisione, bollo, assicurazione,
tagliando) sono quattro andate e ritorni. La card, dal canto suo, mostra tutte le scadenze o quelle di
un'unica voce, ma non permette di scegliere singole scadenze da voci diverse (es. "le prossime scadenze
importanti", indipendentemente da chi sono).

### Decisioni prese con l'utente

| Tema | Decisione |
|---|---|
| Configurazione | Wizard a catena: dopo aver creato la voce, si scelgono le scadenze da aggiungere e poi si compilano una alla volta, senza dati indovinati |
| Preselezione | Tutti i modelli applicabili al tipo di voce sono preselezionati, tranne «Personalizzata» |
| Card | Terza modalità **scelte**: un selettore multiplo elenca ogni scadenza esistente, di qualunque voce, e se ne scelgono alcune |
| Modalità esistenti | «Tutte» e «Voce» restano invariate |

### Fuori perimetro

- Cambiare il modello dati voce/scadenza (§4 della spec di fase 1) o le regole di calcolo.
- Aggiungere o togliere modelli dal catalogo (§6 della spec di fase 1).
- Semplificare il flusso delle opzioni (notifiche, sensore km): ha già valori predefiniti sensati e non è
  stato indicato come un problema.
- Modificare "riconfigura" di una scadenza singola o l'aggiunta di una scadenza in un momento successivo:
  restano come oggi (§7.3 della spec di fase 1).
- Raggruppamenti, intestazioni o ordinamenti diversi nella card (già fuori perimetro nella fase 2).
- Pubblicazione su HACS default in sé: è il passo successivo a questo lavoro, non ne fa parte.

## 2. Configurazione guidata

### 2.1 Flusso

```
async_step_user            menu dei quattro tipi (invariato)
async_step_{tipo}          campi della voce (invariato); invece di creare la entry,
                            salva i dati in self._dati_voce e passa al punto successivo
async_step_scegli_scadenze form con un solo campo multiplo "modelli": le chiavi disponibili per
                            questo tipo di voce, preselezionate tutte tranne «personalizzata»
                              │
                              ├─ nessun modello scelto → async_create_entry (solo la voce, come oggi)
                              │
                              └─ almeno uno scelto → self._coda = lista scelta, nell'ordine del
                                 catalogo; passa al primo
async_step_dettagli_scadenza stesso form che il flusso "aggiungi scadenza" usa oggi (§7.3 della spec
                            di fase 1: §6 per i campi, valori suggeriti già compilati) per il modello
                            in testa a self._coda
                              │
                              ├─ dati validi → costruisce la Scadenza, la accoda a
                              │   self._scadenze_raccolte; se self._coda non è vuota, si richiama da
                              │   sola per il prossimo modello; altrimenti crea la entry con tutte le
                              │   subentries insieme (§2.3)
                              │
                              └─ dati non validi → stesso form con l'errore, stesso modello (invariato
                                 rispetto al comportamento di oggi)
```

Non c'è un passo "indietro": se ci si sbaglia su un modello già confermato, si corregge dopo con
"Riconfigura" sul suo dispositivo, esattamente come oggi. Chiudere il flusso a metà lascia solo la voce
creata, senza le scadenze non ancora confermate — Home Assistant non salva nulla finché
`async_create_entry` non viene chiamato.

### 2.2 Selezione dei modelli

- Opzioni del campo `modelli`: `modelli_per_tipo(tipo)` (funzione già esistente in `modelli.py`), che
  filtra il catalogo per tipo di voce e mantiene l'ordine con cui i modelli sono elencati oggi.
- Preselezionati: tutti tranne `personalizzata` — è l'unico modello pensato per un caso non previsto dal
  catalogo, meno probabile come scelta "del primo giorno".
- Selettore: `SelectSelector` multiplo con `translation_key` sulle chiavi dei modelli, riusando le
  etichette già tradotte in `strings.json`/`translations/*.json` (stessa chiave usata oggi dal selettore
  singolo del flusso "aggiungi scadenza").

### 2.3 Creazione insieme a voce e scadenze

`ConfigFlow.async_create_entry` accetta un parametro `subentries` (elenco di `ConfigSubentryData`): la
entry e tutte le sue scadenze vengono create in un solo passo, invece che con un `async_create_entry`
per la voce seguito da un subentry per ciascuna scadenza. Ogni `Scadenza` raccolta in
`self._scadenze_raccolte` diventa `ConfigSubentryData(subentry_type=SUBENTRY_SCADENZA, title=s.nome,
unique_id=None, data=s.a_dict())`. Se non è supportato nella forma qui descritta con la versione minima
di Home Assistant richiesta da questa repo (2026.8.0), il piano di implementazione verifica l'alternativa
(creare la entry e poi le subentries con `hass.config_entries.async_add_subentry` prima che
`async_setup_entry` giri, dentro lo stesso flusso) e lo annota come correzione.

### 2.4 Riuso del codice esistente

`_schema_dettagli`, `valori_suggeriti` e `costruisci_scadenza` (tutte già in `modelli.py`, già usate dal
flusso "aggiungi scadenza") si riusano senza modifiche per `async_step_dettagli_scadenza`. Il flusso
"aggiungi scadenza" più tardi (`ScadenzaSubentryFlow`) resta com'è: questo lavoro cambia solo cosa succede
subito dopo aver creato una voce nuova.

## 3. Card — modalità «scelte»

### 3.1 Configurazione

```yaml
type: custom:scadenze-card
titolo: Scadenze importanti     # invariato
modalita: scelte                # nuovo; tutte (predefinito) | voce | scelte
voce: <config_entry_id>         # invariato; usato solo se modalita = voce
scelte: [<device_id>, ...]      # nuovo; usato solo se modalita = scelte
nascondi_ok: false              # invariato, si applica anche in modalita scelte
mostra_giorni: true
mostra_km: true
mostra_rinnovato: true
```

`voce` e `scelte` restano entrambi nella configurazione salvata (comodo se si passa da una modalità
all'altra senza perdere la selezione precedente), ma solo il campo della modalità attiva incide sul
filtro.

### 3.2 Editor

- Nuovo campo `modalita`: `SelectSelector` a scelta singola con le tre opzioni.
- Il campo `voce` (già esistente, selettore `config_entry` filtrato su `integration: scadenze`) è visibile
  solo con `modalita: voce`.
- Nuovo campo `scelte`: selettore multiplo che elenca ogni scadenza esistente (non le voci), visibile solo
  con `modalita: scelte`. Ogni opzione mostra un nome riconoscibile (es. "Revisione — La mia Panda").
  L'implementazione esatta (probabilmente un selettore `device` filtrato sull'integrazione, dato che ogni
  scadenza ha già un proprio dispositivo per via del vincolo di HA 2026.8+ sui subentry) va verificata
  contro le API di `ha-form`/`ha-selector` correnti durante il piano: se non permettono di escludere i
  dispositivi delle voci (che non sono scadenze) dall'elenco, l'alternativa è un controllo scritto a mano
  nella card, sul modello di come `logica.js` già raccoglie le scadenze da `hass.entities`/`hass.devices`.
- Mostra/nascondi condizionale dei campi in base a `modalita`: da verificare quale meccanismo di `ha-form`
  usare (schema con più varianti selezionato in base al valore corrente, dato che è il modo comune per
  campi condizionali in HA) e annotarlo come correzione se diverso da quanto qui previsto.

### 3.3 Logica di filtro (`logica.js`)

- `modalita` sostituisce, come sorgente di verità, la logica attuale "se `voce` è impostato filtra,
  altrimenti mostra tutte": con `modalita: voce` si comporta come oggi; con `modalita: tutte` mostra tutto
  come oggi; con `modalita: scelte` tiene solo le scadenze il cui `id` (già raccolto oggi, è il device_id
  della scadenza) è nell'elenco `scelte`, nell'ordine di ordinamento generale (non nell'ordine di
  selezione).
- Le configurazioni salvate prima di questo cambiamento non hanno `modalita`: se assente, si comporta come
  `voce` se `voce` è impostato, altrimenti come `tutte` — compatibile con ogni card già configurata.
- Con `modalita: scelte` e `scelte` vuoto o assente, o con id che non corrispondono più a nessuna scadenza
  esistente (es. eliminata), la card mostra il messaggio di lista vuota già esistente («Nessuna scadenza
  da mostrare»), senza errori.
- `nascondi_ok` e gli altri filtri/opzioni di visualizzazione restano invariati e si applicano a valle,
  qualunque sia la modalità.

### 3.4 Cosa non cambia

Raccolta delle scadenze da `hass.entities`/`hass.devices`, colori, testi, pulsante «Rinnovato», editor con
`ha-form`, distribuzione servita dall'integrazione: tutto com'è oggi (§3–§6 della spec di fase 2).

## 4. Test

- **Logica pura (config flow, `tests/logica` o nuovo modulo se serve isolare la selezione dei modelli):**
  preselezione corretta per ciascun tipo di voce (tutti tranne `personalizzata`); nessun modello scelto →
  nessuna subentry; ordine delle scadenze create = ordine del catalogo, non l'ordine di selezione.
- **Integrazione (`pytest-homeassistant-custom-component`, CI):** il flusso completo crea voce e scadenze
  scelte in una sola entry con le subentries attese; un errore di validazione su un modello (es. data
  futura) riporta lo stesso form con l'errore, senza perdere le scadenze già confermate nella coda; chiudere
  il flusso dopo aver confermato solo alcune scadenze lascia create solo quelle.
- **Card (`node --test "tests/card/*.test.mjs"`):** filtro `scelte` con una lista di id; configurazione
  senza `modalita` ma con `voce` si comporta come `modalita: voce` (compatibilità); editor: cambiare
  `modalita` mostra/nasconde i campi giusti ed emette `config-changed` con i valori coerenti.

## 5. Distribuzione

- Versione dell'integrazione: bump minore (`0.3.0`), sia in `manifest.json` sia nella query di versione
  della card (§3 della spec di fase 2, `versione` letta con `async_get_integration`).
- README: aggiornare la sezione di configurazione (nuovo flusso) e la sezione «La card» (nuovo campo
  `modalita`/`scelte` con esempio).
- Nessun impatto su `hacs.json` o sui requisiti Python.
