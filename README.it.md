# Renewal & Deadline Alert (Home, Car, Health)

[![Validate](https://github.com/iAlias/ScadenzeAutoCasaSalute/actions/workflows/validate.yml/badge.svg)](https://github.com/iAlias/ScadenzeAutoCasaSalute/actions/workflows/validate.yml)
[![HACS: Custom repository](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/docs/faq/custom_repositories/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Read in English](https://img.shields.io/badge/language-english-0033A0.svg)](README.md)

**Revisione, bollo, patente, caldaia: le scadenze di tutti i giorni dentro Home Assistant, calcolate con le regole italiane e ricordate in tempo.**

Nessun account, nessuna API, nessun sito da leggere: le date si calcolano in locale, quindi l'integrazione non smette di funzionare quando un portale della pubblica amministrazione cambia o va giù.

---

## Indice

- [Cosa fa](#cosa-fa)
- [Requisiti](#requisiti)
- [Installazione](#installazione)
- [Come si usa](#come-si-usa)
- [Cosa trovi in Home Assistant](#cosa-trovi-in-home-assistant)
- [Le regole e le fonti](#le-regole-e-le-fonti)
- [Promemoria](#promemoria)
- [La card](#la-card)
- [Limiti dichiarati](#limiti-dichiarati)
- [Sviluppo](#sviluppo)
- [Problemi e contributi](#problemi-e-contributi)
- [Licenza](#licenza)

## Cosa fa

- Tiene insieme le scadenze di **veicoli**, **casa**, **persone** e di qualunque altra cosa.
- **Propone la data giusta** usando le regole italiane vere: la prima revisione quattro anni dopo l'immatricolazione, il bollo entro la fine del mese successivo alla scadenza, la patente al compleanno giusto per la tua fascia d'età.
- **Rinnovo con un clic**: premi **Rinnovato**, o spunta la scadenza nella lista delle cose da fare, e la data successiva si calcola da sola in base alla regola che le si applica.
- **Ti avvisa** alle soglie di preavviso che scegli — 30, 7 e 1 giorno di serie — senza ripetere lo stesso avviso due volte.
- **Configurazione guidata**: dopo aver creato un veicolo, una casa o una persona, un unico flusso ti guida ad aggiungere le sue prime scadenze una alla volta, con i valori già suggeriti dove possono essere calcolati.
- Una card Lovelace arriva insieme all'integrazione e si registra da sola: nessuna risorsa da aggiungere a mano.

## Requisiti

Home Assistant **2026.8** o successivo.

## Installazione

### Via HACS (consigliato)

Questa integrazione non è ancora nello store predefinito di HACS; aggiungila come repository personalizzato:

1. HACS → Integrazioni → menu ⋮ → **Repository personalizzati**
2. Aggiungi `https://github.com/iAlias/ScadenzeAutoCasaSalute` con categoria **Integration**
3. Installa, poi riavvia Home Assistant
4. **Impostazioni → Dispositivi e servizi → Aggiungi integrazione → Renewal & Deadline Alert (Home, Car, Health)**

### Manualmente

Copia `custom_components/scadenze` nella cartella `config/custom_components`, riavvia Home Assistant, poi aggiungi l'integrazione come al punto 4 sopra.

## Come si usa

1. **Crea una voce**: un veicolo (con il mese di prima immatricolazione), una casa, una persona (con la data di nascita) o una voce generica per tutto il resto.
2. **Scegli quali scadenze aggiungere subito** — revisione, bollo, assicurazione e così via. Il flusso ti guida una alla volta, con i valori suggeriti già compilati dove possono essere calcolati. Puoi sempre aggiungerne altre più tardi dalla pagina del dispositivo della voce, con **Aggiungi scadenza**.
3. Apri **Configura** sulla voce per scegliere il servizio di notifica, i preavvisi, l'orario e, per i veicoli, il sensore del contachilometri.

| Voce | Scadenze |
|---|---|
| Panda (auto, immatricolata a maggio 2022) | Revisione, Bollo, Assicurazione, Tagliando ogni 12 mesi o 15.000 km, Cambio gomme |
| Casa | Manutenzione caldaia, Controllo fumi caldaia, Pulizia climatizzatore |
| Mario (nato l'8 maggio 1990) | Carta d'identità, Patente, Passaporto |

## Cosa trovi in Home Assistant

Ogni scadenza è un dispositivo a sé, collegato a quello della voce a cui appartiene.

| Entità | Dove | Cosa mostra |
|---|---|---|
| `sensor` data | scadenza | la prossima data di scadenza; negli attributi stato, ultimo rinnovo e dati del modello |
| `sensor` giorni mancanti | scadenza | giorni alla scadenza, negativi se è già passata |
| `sensor` km mancanti | tagliando | km al prossimo tagliando, se hai configurato il sensore del contachilometri |
| `binary_sensor` in scadenza | scadenza | acceso quando la scadenza è vicina o superata |
| `button` rinnovato | scadenza | registra il rinnovo e calcola la data successiva |
| `calendar` scadenze | voce | tutte le scadenze della voce nel pannello Calendario |
| `todo` da rinnovare | voce | le scadenze vicine o superate; spuntarle equivale a premere Rinnovato |

## Le regole e le fonti

| Scadenza | Regola |
|---|---|
| Revisione | Prima entro la fine del mese, quattro anni dopo l'immatricolazione; poi ogni due anni dal mese dell'ultima |
| Bollo | Annuale; si paga entro l'ultimo giorno del mese successivo alla scadenza |
| Assicurazione | Annuale; un attributo indica la fine dei 15 giorni di tolleranza |
| Tagliando | Ogni N mesi o N km, quello che arriva prima |
| Cambio gomme | Invernali entro il 15 novembre, estive entro il 15 maggio |
| Patente | 10 anni sotto i 50, 5 fino ai 70, 3 fino agli 80, poi 2; scade al compleanno giusto |
| Carta d'identità | 3 anni sotto i 3, 5 fino ai 18, poi al compleanno dopo 9 anni; **illimitata** dai 70 anni per le carte emesse dal 30 luglio 2026 |
| Passaporto | 3 anni sotto i 3, 5 fino ai 18, poi 10 |
| Caldaia, climatizzatore, estintore, filtri, canna fumaria | Ogni N mesi dall'ultima volta |

Queste regole sono state verificate sulle seguenti fonti ufficiali e di riferimento, e si riverificano ogni volta che cambiano:

- Revisione: [MIT – Revisione periodica veicoli](https://www.mit.gov.it/revisione-periodica-veicoli)
- Bollo: [L'Automobile ACI – Bollo auto 2026](https://www.lautomobile.aci.it/attualita/bollo-auto-2026-scadenze-tariffe-ed-esenzioni-la-guida-completa/)
- Patente: [MIT – Rinnovo patente](https://www.mit.gov.it/rinnovo-patente)
- Carta d'identità: [Wikipedia – CIE](https://it.wikipedia.org/wiki/Carta_d'identit%C3%A0_elettronica_italiana), [ANAP – CIE over 70 illimitata](https://www.anap.it/notizia/cie-over-70-carta-identita-elettronica-a-vita/)
- Tolleranza assicurazione: [ConTe.it](https://www.conte.it/blog/assicurazione-auto/scadenza-assicurazione-auto-e-proroga-15-giorni/)
- Gomme invernali: [Ayvens – Cambio gomme invernali](https://www.ayvens.com/it-it/blog/conducenti/cambio-gomme-invernali/)
- Manutenzione caldaia, DPR 74/2013: [Bosetti & Gatti – dPR 74/2013](https://www.bosettiegatti.eu/info/norme/statali/2013_0074.htm)

## Promemoria

Ogni giorno, all'orario che scegli, l'integrazione controlla le scadenze e, per quelle che hanno superato una soglia:

- lancia l'evento **`scadenze_promemoria`**, con voce, scadenza, data, giorni e km mancanti e il messaggio;
- se le notifiche sono attive, chiama il servizio di notifica scelto, per esempio `notify.mobile_app_telefono`.

Preferisci le tue automazioni? In `blueprints/automation/scadenze/` c'è una blueprint pronta, oppure scrivine una tua:

```yaml
triggers:
  - trigger: event
    event_type: scadenze_promemoria
actions:
  - action: notify.mobile_app_telefono
    data:
      title: "{{ trigger.event.data.voce }} – {{ trigger.event.data.scadenza }}"
      message: "{{ trigger.event.data.messaggio }}"
```

## La card

L'integrazione porta con sé una card Lovelace già registrata: non serve aggiungere risorse alla dashboard a mano. Si trova nel selettore delle card come **Scadenze** e si configura anche dall'editor visuale.

```yaml
type: custom:scadenze-card
titolo: Scadenze
modalita: tutte            # tutte (predefinito) | voce | scelte
voce: <voce>                # con modalita: voce
scelte:                     # con modalita: scelte
  - <scadenza 1>
  - <scadenza 2>
nascondi_ok: false
mostra_giorni: true
mostra_km: true
mostra_rinnovato: true
```

| Opzione | Predefinito | Cosa fa |
|---|---|---|
| `titolo` | nessuno | Intestazione della card |
| `modalita` | `tutte` | `tutte`, `voce` (una voce sola) o `scelte` (scadenze scelte a mano, di qualunque voce) |
| `voce` | — | Con `modalita: voce`, quale voce mostrare |
| `scelte` | — | Con `modalita: scelte`, quali scadenze mostrare |
| `nascondi_ok` | `false` | Mostra solo le scadenze superate o vicine |
| `mostra_giorni` | `true` | Aggiunge «tra N giorni» o «scaduta da N giorni» |
| `mostra_km` | `true` | Aggiunge i km mancanti al tagliando |
| `mostra_rinnovato` | `true` | Pulsante «Rinnovato»: il primo clic chiede conferma, il secondo rinnova |

Ogni riga ha una striscia colorata: rossa se la scadenza è superata, ambra se è vicina, verde se è in regola, grigia se è illimitata o completata.

## Limiti dichiarati

- **Le date suggerite sono calcoli, non documenti ufficiali.** Controllale con libretto, ricevute e documenti; si correggono sempre con «Riconfigura».
- **Alcune periodicità cambiano da regione a regione** (controllo fumi, primo bollo in Lombardia e Piemonte): i valori proposti sono modificabili.
- Le regole dei documenti sono aggiornate a **settembre 2026**.
- I testi dei promemoria sono in italiano.

## Sviluppo

```bash
pip install -r requirements_test.txt
pytest -q
```

I test in `tests/logica` coprono le regole di calcolo e girano anche senza Home Assistant installato (basta `pip install pytest`); quelli in `tests/ha` richiedono Linux.

## Problemi e contributi

Hai trovato un bug, o una regola che non corrisponde più alla legge? Apri una issue su
[github.com/iAlias/ScadenzeAutoCasaSalute/issues](https://github.com/iAlias/ScadenzeAutoCasaSalute/issues).

## Licenza

[MIT](LICENSE)
