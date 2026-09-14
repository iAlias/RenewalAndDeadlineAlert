# Scadenze Auto & Casa — design della fase 1

- **Data:** 2026-09-14
- **Stato:** approvato in chat, in revisione come documento
- **Perimetro:** fase 1, l'integrazione Home Assistant. La card Lovelace è la fase 2 e avrà una spec propria.

## 1. Obiettivo

Un'integrazione custom per Home Assistant che tiene traccia delle scadenze italiane di veicoli, casa e
documenti personali, calcola da sola la data successiva secondo le regole di legge e avvisa in tempo.
Tutto è calcolato in locale: nessuna API esterna, nessuno scraping, niente che possa rompersi quando un
sito cambia.

### Decisioni prese con l'utente

| Tema | Decisione |
|---|---|
| Categorie | Veicoli, casa e impianti, documenti personali, scadenze libere |
| Promemoria | Notifiche integrate attivabili **ed** evento + blueprint per automazioni proprie |
| Rinnovo | Pulsante «Rinnovato» per scadenza, che calcola la data successiva |
| Vista | Calendario, sensori per scadenza, lista todo; card dedicata nella fase 2 |
| Chilometri | Il tagliando considera anche i km, letti da un sensore esistente |
| Struttura | Voce (config entry) + scadenze (config subentry) |
| Fasi | Fase 1 integrazione, fase 2 card servita dall'integrazione stessa |

### Fuori perimetro (fase 1)

- Card Lovelace (fase 2).
- Calcolo dell'importo del bollo e qualunque collegamento a ACI, Portale dell'Automobilista o portali regionali.
- Notifiche con pulsanti d'azione («Rinnovato» dentro la notifica).
- Sincronizzazione con calendari esterni.
- Scadenze a chilometri per voci che non sono veicoli.
- Icone brand (`brand/icon.png`): le aggiunge l'autore prima della pubblicazione.
- Lingue diverse da italiano e inglese.

## 2. Identità del progetto

| Elemento | Valore |
|---|---|
| Cartella / repository | `scadenze-auto-casa` |
| Dominio | `scadenze` |
| Nome visualizzato | Scadenze Auto & Casa |
| Home Assistant minimo | 2026.8.0 (motivo in §8.0) |
| `integration_type` | `service` |
| `iot_class` | `calculated` |
| Dipendenze Python a runtime | nessuna |
| Licenza | MIT |
| Lingue | README in italiano; traduzioni `it` ed `en` |

## 3. Architettura

### 3.1 Concetti

- **Voce**: l'oggetto che ha delle scadenze. È una config entry e ha **un dispositivo** in HA, che porta
  il calendario e la lista todo. Tipi: `veicolo`, `casa`, `persona`, `generica`.
- **Scadenza**: una singola cosa da rinnovare. È una config subentry di tipo `scadenza` appesa alla voce
  e ha **un dispositivo proprio**, collegato a quello della voce (§8.0). Nasce da un **modello**
  (revisione, patente, caldaia…) che fissa regola e valori predefiniti.
- **Regola**: la funzione pura che calcola la prossima data. Cinque regole coprono tutti i modelli.

### 3.2 Struttura dei file

```
scadenze-auto-casa/
├── custom_components/scadenze/
│   ├── __init__.py          setup/unload, dispositivo della voce, runtime_data, politica di reload
│   ├── manifest.json
│   ├── const.py             chiavi, valori predefiniti
│   ├── date_utils.py        PURO: aggiungi_mesi, fine_mese, compleanno_dopo, eta
│   ├── modello_dati.py      PURO: dataclass Voce, Scadenza, Stato; conversione da/verso dict
│   ├── regole.py            PURO: prossima_scadenza(), calcola_stato()
│   ├── modelli.py           PURO: catalogo dei modelli e precompilazione dei form
│   ├── promemoria.py        PURO: quali promemoria inviare, senza doppioni
│   ├── coordinator.py       stato in memoria, ricalcoli, rinnovo
│   ├── notifiche.py         pianificazione, Store, chiamata notify, evento, riparazioni
│   ├── config_flow.py       flusso voce, opzioni voce, flusso sotto-voce scadenza
│   ├── entity.py            entità base (device_info, accesso al coordinator)
│   ├── sensor.py            data di scadenza, giorni mancanti, km mancanti
│   ├── binary_sensor.py     in scadenza
│   ├── button.py            rinnovato
│   ├── calendar.py          calendario della voce
│   ├── todo.py              lista «da rinnovare» della voce
│   ├── strings.json
│   └── translations/{it,en}.json
├── blueprints/automation/scadenze/promemoria_scadenze.yaml
├── tests/
├── requirements_test.txt
├── pyproject.toml           configurazione di pytest
├── .github/workflows/validate.yml
├── hacs.json
├── README.md
└── LICENSE
```

I moduli marcati **PURO** non importano `homeassistant`: contengono tutta la logica di calcolo e sono
testabili come normali funzioni.

### 3.3 Flusso dei dati

```
config entry (voce) + subentries (scadenze)
        │  lettura all'avvio / dopo modifica
        ▼
  ScadenzeCoordinator ──► regole.calcola_stato() ──► entità (sensor, binary_sensor, calendar, todo)
        ▲        │
        │        └──► notifiche.py ──► promemoria.py ──► notify + evento scadenze_promemoria
        │
  trigger: mezzanotte · cambio del sensore km · pulsante/todo «Rinnovato» · modifica configurazione
```

Il coordinator estende `DataUpdateCoordinator` con `update_interval=None`: non interroga nulla,
ricalcola quando arriva un trigger e poi notifica le entità.

## 4. Modello dati

Le date sono salvate come stringhe ISO `AAAA-MM-GG`.

### 4.1 Voce (`entry.data`)

| Chiave | Tipo | Voce | Note |
|---|---|---|---|
| `tipo` | `veicolo` \| `casa` \| `persona` \| `generica` | tutte | non modificabile dopo la creazione |
| `nome` | str | tutte | titolo della entry e nome del dispositivo |
| `tipo_veicolo` | `auto` \| `moto` | veicolo | |
| `immatricolazione` | data (giorno 1 del mese) | veicolo | non nel futuro |
| `data_nascita` | data | persona | non nel futuro |

### 4.2 Opzioni della voce (`entry.options`)

| Chiave | Tipo | Predefinito | Vincoli |
|---|---|---|---|
| `sensore_km` | entity_id \| assente | assente | solo veicolo |
| `notifiche_attive` | bool | `true` | |
| `servizio_notifica` | str | `notify.persistent_notification` | deve esistere (§7.2) |
| `preavvisi` | lista di interi (giorni) | `[30, 7, 1]` | ogni valore 1–365; lista anche vuota |
| `orario_notifica` | ora `HH:MM:SS` | `09:00:00` | |

### 4.3 Scadenza (`subentry.data`)

| Chiave | Tipo | Uso |
|---|---|---|
| `modello` | str | chiave del modello (§6) |
| `nome` | str | titolo della subentry e parte del nome del dispositivo |
| `regola` | `fine_mese` \| `intervallo` \| `documento` \| `stagionale` \| `unica` | copiata dal modello |
| `scadenza` | data \| `null` | prossima data; `null` = illimitata o completata |
| `ultimo_rinnovo` | data \| `null` | data dell'ultimo rinnovo registrato |
| `completata` | bool | solo regola `unica` |
| `intervallo_mesi` | int \| `null` | regola `intervallo` |
| `ancora` | `rinnovo` \| `scadenza` | regola `intervallo`: da dove si contano i mesi |
| `intervallo_km` | int \| `null` | tagliando; `null` o `0` = km disattivati |
| `km_ultimo_rinnovo` | int \| `null` | tagliando |
| `mese_scadenza_bollo` | data (giorno 1) | solo bollo |
| `documento` | `patente` \| `carta_identita` \| `passaporto` | regola `documento` |

### 4.4 Stato calcolato (non salvato)

`Stato(stato, giorni_mancanti, km_attuali, km_scadenza, km_mancanti, km_non_disponibili)` dove
`stato` ∈ `scaduta`, `in_scadenza`, `ok`, `illimitata`, `completata`.

- `giorni_mancanti = (scadenza − oggi).days`.
- `scaduta` se `giorni_mancanti < 0` oppure `km_mancanti ≤ 0`.
- `in_scadenza` se `giorni_mancanti ≤ finestra` oppure `km_mancanti ≤ 1000` (costante `SOGLIA_KM`),
  dove `finestra = max(preavvisi)`, oppure 30 giorni se `preavvisi` è vuota.
- `ok` negli altri casi.

### 4.5 Stato dei promemoria (`Store`, chiave `scadenze.<entry_id>`)

```json
{ "<subentry_id>": { "riferimento": "2026-10-31|15000", "inviati": [30, 7] } }
```

`riferimento` unisce data e km di scadenza. Quando cambia (rinnovo, riconfigurazione), `inviati` si
azzera. Valori speciali in `inviati`: `0` = «scade oggi», `-1` = «scaduta», `"km"` = soglia km,
`"km_superati"` = km superati.

## 5. Regole di calcolo

### 5.1 Funzioni di base (`date_utils.py`)

- `fine_mese(d)`: ultimo giorno del mese di `d`.
- `aggiungi_mesi(d, n)`: stesso giorno `n` mesi dopo, limitato alla fine del mese (31/01 + 1 → 28/02 o 29/02).
- `compleanno_dopo(nascita, riferimento)`: primo compleanno **strettamente successivo** a `riferimento`.
  Chi è nato il 29/02 compie gli anni il 28/02 negli anni non bisestili.
- `eta(nascita, il_giorno)`: anni compiuti a quella data.

### 5.2 `fine_mese` — revisione e bollo

**Revisione** (auto e moto):
- Prima revisione: `fine_mese(aggiungi_mesi(immatricolazione, 48))`.
- Precompilazione per veicoli con più di 4 anni: si parte dalla prima revisione e si aggiungono 24 mesi
  finché la data non è ≥ oggi (ipotesi: revisioni sempre fatte nel mese giusto).
- Rinnovo nel giorno `D`: `fine_mese(aggiungi_mesi(D, 24))`.

**Bollo**:
- Dato di partenza: `mese_scadenza_bollo` (il mese di scadenza riportato sulla ricevuta).
- `scadenza = fine_mese(aggiungi_mesi(mese_scadenza_bollo, 1))`: il pagamento va fatto entro l'ultimo
  giorno del mese successivo alla scadenza.
- Precompilazione: il bollo scade nel mese che precede quello di immatricolazione. Si propone il primo
  mese così ottenuto il cui pagamento cade da oggi in poi.
- Rinnovo: `mese_scadenza_bollo += 12 mesi`, poi si ricalcola `scadenza`. Il giorno di pressione non conta.
- Attributi `da_pagare_entro` (= `scadenza`) e `mese_scadenza_bollo`.

### 5.3 `intervallo` — mesi, con km facoltativi

- Con `ancora = rinnovo`: `scadenza = aggiungi_mesi(ultimo_rinnovo, intervallo_mesi)`; al rinnovo
  `ultimo_rinnovo = D`.
- Con `ancora = scadenza`: al rinnovo `scadenza = aggiungi_mesi(scadenza, intervallo_mesi)`; `ultimo_rinnovo = D`.
- **Km** (solo con `intervallo_km > 0` e `sensore_km` configurato):
  `km_scadenza = km_ultimo_rinnovo + intervallo_km`, `km_mancanti = km_scadenza − km_attuali`.
  Al rinnovo `km_ultimo_rinnovo` = ultima lettura valida del sensore; se non ce n'è mai stata una resta
  invariato e viene scritto un warning nel log.
- **Assicurazione**: attributo `fine_tolleranza = scadenza + 15 giorni`.

### 5.4 `documento` — patente, carta d'identità, passaporto

Usano `data_nascita` della voce. Il form chiede la **data di scadenza stampata sul documento**. La regola
serve al rinnovo, con `D` = giorno di pressione (circa la data di emissione). La data resta correggibile
con «Riconfigura».

| Documento | Età a `D` | Nuova scadenza |
|---|---|---|
| Patente | < 50 | `compleanno_dopo(nascita, D + 10 anni)` |
| | 50–69 | `compleanno_dopo(nascita, D + 5 anni)` |
| | 70–79 | `compleanno_dopo(nascita, D + 3 anni)` |
| | ≥ 80 | `compleanno_dopo(nascita, D + 2 anni)` |
| Carta d'identità | < 3 | `compleanno_dopo(nascita, D + 3 anni)` |
| | 3–17 | `compleanno_dopo(nascita, D + 5 anni)` |
| | 18–69 | `compleanno_dopo(nascita, D + 9 anni)` |
| | ≥ 70 e `D ≥ 2026-07-30` | `null` → stato `illimitata` |
| | ≥ 70 e `D < 2026-07-30` | `compleanno_dopo(nascita, D + 9 anni)` |
| Passaporto | < 3 | `D + 3 anni` |
| | 3–17 | `D + 5 anni` |
| | ≥ 18 | `D + 10 anni` |

Nella tabella «`D + N anni`» si calcola come `aggiungi_mesi(D, 12·N)`.

### 5.5 `stagionale` — gomme invernali

- Date fisse: **15/11** (montaggio, azione `monta_invernali`) e **15/05** (smontaggio, azione `smonta_invernali`).
  L'obbligo va dal 15/11 al 15/04, con un mese di tolleranza per il cambio.
- Precompilazione: la prima delle due date ≥ oggi.
- Rinnovo nel giorno `D`: si passa alla data fissa successiva a `scadenza`, e si ripete finché il
  risultato non è `> D`.
- Attributo `azione`.

### 5.6 `unica`

- Nessuna ricorrenza. Al rinnovo: `completata = true`, `scadenza = null`, stato `completata`.

### 5.7 Doppio rinnovo

Se `ultimo_rinnovo == oggi`, un secondo rinnovo nello stesso giorno viene ignorato e registrato nel log
a livello `info`. Vale per pulsante e todo.

## 6. Catalogo dei modelli (`modelli.py`)

| Chiave | Voce | Regola | Parametri predefiniti | Campi del form |
|---|---|---|---|---|
| `revisione` | veicolo | fine_mese | 48 poi 24 mesi | scadenza (precompilata) |
| `bollo` | veicolo | fine_mese (bollo) | 12 mesi | mese di scadenza bollo (precompilato) |
| `assicurazione` | veicolo | intervallo | 12 mesi, ancora `scadenza` | scadenza, intervallo (6 o 12) |
| `tagliando` | veicolo | intervallo | 12 mesi, 15.000 km, ancora `rinnovo` | data ultimo tagliando, km ultimo tagliando, intervallo mesi, intervallo km |
| `gomme` | veicolo | stagionale | — | scadenza (precompilata) |
| `manutenzione_caldaia` | casa | intervallo | 12 mesi, ancora `rinnovo` | data ultima manutenzione, intervallo |
| `controllo_fumi` | casa | intervallo | 48 mesi, ancora `rinnovo` | data ultimo controllo, intervallo |
| `climatizzatore` | casa | intervallo | 12 mesi, ancora `rinnovo` | data ultima pulizia, intervallo |
| `estintore` | casa | intervallo | 6 mesi, ancora `rinnovo` | data ultimo controllo, intervallo |
| `filtri_acqua` | casa | intervallo | 6 mesi, ancora `rinnovo` | data ultimo cambio, intervallo |
| `canna_fumaria` | casa | intervallo | 12 mesi, ancora `rinnovo` | data ultima pulizia, intervallo |
| `carta_identita` | persona | documento | tabella §5.4 | scadenza stampata |
| `patente` | persona | documento | tabella §5.4 | scadenza stampata |
| `passaporto` | persona | documento | tabella §5.4 | scadenza stampata |
| `tessera_sanitaria` | persona | intervallo | 72 mesi, ancora `scadenza` | scadenza stampata |
| `personalizzata` | tutte | unica o intervallo | — | nome, scadenza, ricorrenza (nessuna / ogni N mesi dalla scadenza / ogni N mesi dal rinnovo) |

- Il nome predefinito della scadenza è l'etichetta tradotta del modello ed è modificabile.
- Ogni modello ha un'icona MDI (es. `mdi:car-wrench`, `mdi:card-account-details`, `mdi:water-boiler`).
- I modelli con periodicità che variano per regione (controllo fumi: 48 mesi per impianti a gas 10–100 kW,
  24 per combustibili liquidi o solidi) lo spiegano nella descrizione del campo.
- Tutte le date precompilate sono suggerimenti: l'utente può sempre cambiarle prima di salvare.
- Validazione: le date «ultimo rinnovo» non possono essere nel futuro; `intervallo_mesi` 1–240;
  `intervallo_km` 0–100.000; `km_ultimo_rinnovo` ≥ 0.

## 7. Flussi di configurazione

### 7.1 Nuova voce (`ConfigFlow`)

1. `user`: menu con i quattro tipi.
2. Passo del tipo scelto: `nome` più i campi di §4.1.
3. Crea la entry con `title = nome`. `unique_id` non impostato: sono ammessi due veicoli con lo stesso nome.

### 7.2 Opzioni della voce (`OptionsFlow`)

Un unico form con i campi di §4.2. `sensore_km` compare solo per i veicoli (selettore entità del dominio
`sensor`). `servizio_notifica` è un campo di testo nel formato `notify.nome_servizio`; se
`hass.services.has_service` risponde di no, il form mostra l'errore `servizio_non_trovato`.

### 7.3 Scadenza (`ConfigSubentryFlow`, tipo `scadenza`)

1. `user`: selettore del modello, filtrato per tipo di voce.
2. `dettagli`: campi del modello (§6), precompilati con i valori calcolati.
3. Crea la subentry con `title = nome`.
4. `reconfigure`: stesso form `dettagli` con i valori attuali; il modello non si cambia.

## 8. Dispositivi ed entità

### 8.0 Dispositivi

Da Home Assistant 2026.8 **un dispositivo appartiene a una sola config subentry**. Registrare sullo
stesso dispositivo entità di subentry diverse lo sposta in silenzio da una all'altra, fa rimuovere le
entità della subentry precedente, ed è deprecato fino al 2027.8, quando diventerà un errore. Nella stessa
versione la chiave `via_device` (tupla di identificatori) è deprecata a favore di `via_device_id`.
Per questo:

- **Dispositivo della voce**: creato in `async_setup_entry` con il registro dispositivi, prima di caricare
  le piattaforme: `config_entry_id = entry_id`, nessuna subentry, `identifiers = {("scadenze", entry_id)}`,
  `name` = nome della voce, `model` = tipo di voce tradotto, `entry_type = DeviceEntryType.SERVICE`.
  Il suo `id` di registro viene salvato in `runtime_data`.
- **Dispositivo della scadenza**: creato dalle entità della scadenza tramite `device_info`:
  `identifiers = {("scadenze", subentry_id)}`, `name = "{nome voce} {nome scadenza}"` (es. «Panda Revisione»),
  `model` = etichetta del modello, `entry_type = DeviceEntryType.SERVICE`,
  `via_device_id` = id del dispositivo della voce.
- Quando una subentry viene eliminata, HA rimuove da sé il suo dispositivo e le sue entità.

Tutte le entità usano `has_entity_name = True` e `translation_key` per il nome.

### 8.1 Per ogni scadenza (dispositivo della scadenza, `config_subentry_id = subentry_id`)

| Piattaforma | Nome entità | `unique_id` | Contenuto |
|---|---|---|---|
| `sensor` | nessuno (usa il nome del dispositivo) | `{subentry_id}_scadenza` | `device_class: date`; `None` se illimitata o completata. Attributi: `stato`, `modello`, `ultimo_rinnovo`, e secondo il modello `da_pagare_entro`, `mese_scadenza_bollo`, `fine_tolleranza`, `azione` |
| `sensor` | Giorni mancanti | `{subentry_id}_giorni` | intero, unità `d`; negativo se scaduta; `None` se illimitata o completata |
| `sensor` | Km mancanti | `{subentry_id}_km` | solo se la scadenza usa i km; unità `km`, `device_class: distance`; non disponibile se il sensore km non lo è |
| `binary_sensor` | In scadenza | `{subentry_id}_in_scadenza` | `device_class: problem`; `on` se lo stato è `in_scadenza` o `scaduta` |
| `button` | Rinnovato | `{subentry_id}_rinnova` | chiama `coordinator.async_rinnova(subentry_id)` |

Esempi di entity_id risultanti: `sensor.panda_revisione`, `sensor.panda_revisione_giorni_mancanti`,
`binary_sensor.panda_revisione_in_scadenza`, `button.panda_revisione_rinnovato`.

### 8.2 Per ogni voce (dispositivo della voce, senza subentry)

| Piattaforma | Nome entità | `unique_id` | Contenuto |
|---|---|---|---|
| `calendar` | Scadenze | `{entry_id}_calendario` | un evento di un giorno intero per scadenza con data; `summary = nome`, `description` con stato e attributi utili; `uid = subentry_id`. `event` = la prossima scadenza da oggi in poi |
| `todo` | Da rinnovare | `{entry_id}_todo` | un elemento per scadenza con stato `in_scadenza` o `scaduta`; `uid = subentry_id`, `due = scadenza`. Supporta solo `UPDATE_TODO_ITEM`: portare un elemento a `completed` chiama `async_rinnova`. Creazione e cancellazione non supportate |

## 9. Coordinator e reload

- All'avvio della entry il coordinator costruisce `Voce` e la lista di `Scadenza` dalla entry e dalle subentries.
- **Trigger di ricalcolo:** `async_track_time_change` alle 00:00:05; cambio di stato di `sensore_km`
  (`async_track_state_change_event`, solo veicoli); dopo ogni rinnovo; dopo una modifica della configurazione.
- **Lettura km:** valore numerico dello stato; se `unavailable`, `unknown` o non numerico → `km_attuali = None`,
  `km_non_disponibili = true`, e la parte km non concorre allo stato. Il coordinator memorizza l'ultima lettura valida.
- **Rinnovo** (`async_rinnova`): applica la regola (§5), aggiorna subito il modello in memoria, salva con
  `hass.config_entries.async_update_subentry(entry, subentry, data=...)`, ricalcola e notifica le entità.
- **Politica del listener di aggiornamento:**
  - se l'insieme degli id delle subentries, `entry.data` o `entry.options` sono cambiati → reload della entry
    (servono entità nuove, entità da togliere o impostazioni nuove);
  - altrimenti (cambiati solo i dati di subentries esistenti, per rinnovo o riconfigurazione) → il coordinator
    rilegge i dati delle subentries e ricalcola, **senza reload**.

## 10. Promemoria

### 10.1 Logica pura (`promemoria.py`)

Input: stato calcolato, `preavvisi`, voce `inviati` dello Store. Output: al massimo **un** promemoria per
scadenza per esecuzione, più la lista aggiornata di `inviati`.

- Soglie in giorni: ogni `p` in `preavvisi` con `giorni_mancanti ≤ p`, più `0` se `giorni_mancanti == 0`
  e `-1` se `giorni_mancanti < 0`.
- Se ci sono soglie superate non ancora in `inviati`, si invia **un solo** promemoria con il testo della
  più urgente e si segnano come inviate **tutte** le soglie superate. Esempio: scadenza creata a 5 giorni
  con preavvisi `[30, 7, 1]` → un messaggio «scade tra 5 giorni», `inviati = [30, 7]`.
- Km: `"km"` quando `km_mancanti ≤ 1000`, `"km_superati"` quando `km_mancanti ≤ 0`, con la stessa logica.
- Stati `illimitata` e `completata` non generano promemoria.

### 10.2 Esecuzione (`notifiche.py`)

- Una volta al giorno a `orario_notifica`, e una volta all'avvio se l'orario di oggi è già passato
  (i doppioni li evita lo Store).
- Per ogni promemoria:
  - **evento** `scadenze_promemoria`, sempre, con i dati
    `voce`, `voce_id`, `scadenza`, `scadenza_id`, `modello`, `data`, `giorni_mancanti`, `km_mancanti`, `soglia`, `messaggio`;
  - **notifica**, se `notifiche_attive`: servizio `servizio_notifica` con `title = "{voce} – {nome}"` e
    `message` come «Scade tra 7 giorni (31/10/2026).», «Scade oggi.», «Scaduta dal 31/10/2026.»,
    «Mancano 800 km al tagliando.».
- Dopo l'invio lo Store viene salvato.
- **Errori:** se il servizio di notifica non esiste → warning nel log e issue nel registro Riparazioni
  (`servizio_notifica_mancante_{entry_id}`, severità `warning`); l'issue si cancella al primo invio
  riuscito. Un errore nella chiamata notify non blocca l'evento né gli altri promemoria.

### 10.3 Blueprint

`blueprints/automation/scadenze/promemoria_scadenze.yaml`: trigger sull'evento `scadenze_promemoria`,
input facoltativo per filtrare per voce, azione di notifica scelta dall'utente con il messaggio dell'evento.

## 11. Gestione degli errori

| Situazione | Comportamento |
|---|---|
| Sensore km non disponibile o non numerico | Conta solo la data; `km_non_disponibili = true`; sensore km mancanti non disponibile |
| Sensore km rimosso dal sistema | Come sopra; nessun errore di setup |
| Servizio notify inesistente | Errore nel form opzioni; a runtime warning + issue in Riparazioni |
| Date impossibili nel form | Errori `data_futura`, `nascita_dopo_emissione`, `intervallo_non_valido` |
| Dati di subentry illeggibili (chiave mancante, data malformata) | La scadenza viene saltata con un errore nel log; le altre funzionano |
| Doppio rinnovo nello stesso giorno | Ignorato (§5.7) |
| Rinnovo senza lettura km mai disponibile | Data aggiornata, km invariati, warning nel log |

## 12. Test

- **Logica pura** (`date_utils`, `regole`, `modelli`, `promemoria`), casi obbligatori:
  - fine mese e mesi corti (31/01 + 1 mese; 31/08 + 6 mesi);
  - 29 febbraio per nascita e per `aggiungi_mesi`;
  - patente a 49 e 50 anni esatti; carta d'identità a 2, 3, 17, 18, 69, 70 anni e intorno al 30/07/2026;
    emissione nel giorno del compleanno;
  - revisione di un veicolo di 2, 4 e 9 anni; bollo con scadenza a dicembre (pagamento a gennaio);
  - gomme con rinnovo in anticipo, in ritardo e con una stagione saltata;
  - tagliando con scadenza per data prima dei km e viceversa;
  - stato con `preavvisi` vuota (finestra di 30 giorni);
  - promemoria: creazione a ridosso della scadenza, riavvio senza doppioni, azzeramento dopo il rinnovo,
    scaduta notificata una sola volta.
- **Integrazione** con `pytest-homeassistant-custom-component`:
  - config flow dei quattro tipi, opzioni, subentry flow e riconfigurazione;
  - setup, unload, politica di reload (§9);
  - dispositivi: uno per voce, uno per scadenza collegato con `via_device_id`, nessun avviso di deprecazione
    sui dispositivi nel log, rimozione del dispositivo quando si elimina la subentry;
  - entità: valori, attributi, pulsante, todo completato che rinnova, eventi del calendario in un intervallo;
  - notifiche: chiamata al servizio, evento, issue di riparazione.
- **CI** (`.github/workflows/validate.yml`): hassfest, validazione HACS (categoria integration), pytest.
- **Ambiente:** `requirements_test.txt` fissa la versione di `pytest-homeassistant-custom-component`
  corrispondente a Home Assistant ≥ 2026.8; la versione di Python è quella richiesta da quel pacchetto.

## 13. Distribuzione

- `hacs.json`: `{"name": "Scadenze Auto & Casa", "homeassistant": "2026.8.0", "render_readme": true, "country": ["IT"]}`.
- `manifest.json`: `domain`, `name`, `codeowners: ["@iAlias"]`, `config_flow: true`, `dependencies: []`,
  `documentation` e `issue_tracker` verso `github.com/iAlias/scadenze-auto-casa`, `integration_type`,
  `iot_class`, `requirements: []`, `version: "0.1.0"`.
- README in italiano: cosa fa, installazione, esempio completo (auto + casa + persona), tabella delle regole
  con i riferimenti normativi, **limiti dichiarati** (periodicità regionali, date suggerite da verificare,
  regole dei documenti aggiornate a settembre 2026).

## 14. Fonti

- Revisione: [MIT – Revisione periodica veicoli](https://www.mit.gov.it/revisione-periodica-veicoli)
- Bollo: [L'Automobile ACI – Bollo auto 2026](https://www.lautomobile.aci.it/attualita/bollo-auto-2026-scadenze-tariffe-ed-esenzioni-la-guida-completa/)
- Patente: [MIT – Rinnovo patente](https://www.mit.gov.it/rinnovo-patente)
- Carta d'identità: [Wikipedia – CIE](https://it.wikipedia.org/wiki/Carta_d'identit%C3%A0_elettronica_italiana), [ANAP – CIE over 70 illimitata](https://www.anap.it/notizia/cie-over-70-carta-identita-elettronica-a-vita/)
- Assicurazione, tolleranza 15 giorni: [ConTe.it](https://www.conte.it/blog/assicurazione-auto/scadenza-assicurazione-auto-e-proroga-15-giorni/)
- Gomme invernali: [Ayvens – Cambio gomme invernali](https://www.ayvens.com/it-it/blog/conducenti/cambio-gomme-invernali/)
- Caldaia, DPR 74/2013: [Bosetti & Gatti – dPR 74/2013](https://www.bosettiegatti.eu/info/norme/statali/2013_0074.htm)
- Config subentries: [HA Developer Docs – Config entries](https://developers.home-assistant.io/docs/config_entries_index/)
- Dispositivi e subentry, `via_device_id`: [HA core 2026.8.0 – device_registry.py](https://github.com/home-assistant/core/blob/2026.8.0/homeassistant/helpers/device_registry.py)

## 15. Correzioni emerse scrivendo il piano (2026-09-14)

Queste voci prevalgono sulle sezioni indicate.

1. **§6, §8.0 — etichette.** Il nome predefinito di una scadenza, il `model` del dispositivo della scadenza e
   il `model` del dispositivo della voce usano **etichette italiane fisse** (`Modello.etichetta`,
   `ETICHETTE_TIPO_VOCE`). Il registro dispositivi non traduce `model` e l'integrazione è pensata per l'Italia.
   Le traduzioni `it`/`en` restano per form, selettori, nomi delle entità e riparazioni.
2. **§6 — assicurazione.** Il campo intervallo è un numero di mesi (predefinito 12, ammessi 1–240), non una scelta fra 6 e 12.
3. **§8.1 — entity_id.** Home Assistant genera gli entity_id dai nomi **inglesi** delle entità: gli esempi reali
   sono `sensor.panda_revisione`, `sensor.panda_revisione_days_left`, `binary_sensor.panda_revisione_due_soon`,
   `button.panda_revisione_renewed`. I test cercano le entità per `unique_id`, non per entity_id.
4. **§11 — codici di errore dei form scadenza:** `campo_obbligatorio`, `data_non_valida`, `data_futura`,
   `intervallo_non_valido`, `scadenza_prima_della_nascita` (per i documenti, al posto di `nascita_dopo_emissione`).
   Opzioni: `servizio_non_trovato`, `preavvisi_non_validi`. Nuova voce: `campo_obbligatorio`, `data_futura`.
5. **§4.2 — preavvisi nel form.** Si inseriscono come testo separato da virgole (`30, 7, 1`) e si salvano come lista di interi.
6. **§12 — ambiente dei test.** `tests/logica/` contiene i test dei moduli puri e gira con il solo `pytest`, anche su
   Windows. `tests/ha/` usa `pytest-homeassistant-custom-component==0.13.365` (Home Assistant 2026.9.2, Python ≥ 3.14.2)
   e richiede Linux (CI o WSL).
7. **§10.1 — testi dei promemoria.** Oltre agli esempi: «Scade domani (gg/mm/aaaa).» quando manca un giorno;
   «Limite di N km raggiunto.» per i km superati.

## 16. Correzioni emerse durante l'implementazione (2026-09-14)

1. **§13 — repository.** Il repository reale è `iAlias/scadenze-auto-casa-salute` (privato): `manifest.json`,
   README e blueprint puntano a questo indirizzo.
2. **Ordine dei moduli.** Home Assistant carica la piattaforma `config_flow` durante il setup di ogni config entry:
   con `config_flow: true` nel manifest, `config_flow.py` deve esistere prima di qualunque test di setup.
3. **§12 — ambiente.** Su Windows i test con Home Assistant non si possono eseguire: `homeassistant.runner` importa
   `fcntl` e, su questa macchina, il controllo delle applicazioni blocca la DLL di `bluetooth_data_tools`.
   I test di `tests/ha` si verificano solo in CI (GitHub Actions, Ubuntu); `tests/logica` gira anche in locale.
