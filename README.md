# Scadenze Auto & Casa

**Revisione, bollo, patente, caldaia: le scadenze di tutti i giorni dentro Home Assistant, calcolate con le regole italiane e ricordate in tempo.**

Nessun account, nessuna API, nessun sito da leggere: le date si calcolano in locale, quindi l'integrazione non smette di funzionare quando un portale cambia.

---

## Cosa fa

- Tiene insieme le scadenze di **veicoli**, **casa**, **persone** e di qualunque altra cosa.
- **Propone la data giusta**: la prima revisione quattro anni dopo l'immatricolazione, il bollo entro la fine del mese successivo, la patente al compleanno giusto per la tua età.
- Quando rinnovi premi **Rinnovato**, o spunti la scadenza nella lista: la data successiva si calcola da sola.
- **Ti avvisa** con i preavvisi che scegli, di serie 30, 7 e 1 giorno prima, senza ripetere lo stesso avviso.

## Requisiti

Home Assistant **2026.8** o successivo.

## Installazione

1. HACS → Integrazioni → menu ⋮ → **Repository personalizzati**
2. Aggiungi `https://github.com/iAlias/scadenze-auto-casa-salute` con categoria **Integration**
3. Installa e riavvia Home Assistant
4. **Impostazioni → Dispositivi e servizi → Aggiungi integrazione → Scadenze Auto & Casa**

## Come si usa

1. **Crea una voce**: un veicolo (con il mese di prima immatricolazione), una casa, una persona (con la data di nascita) o una voce generica.
2. Sulla scheda della voce premi **Aggiungi scadenza** e scegli il tipo. Il form arriva già compilato: **controlla le date con i tuoi documenti** e salva.
3. Apri **Configura** sulla voce per scegliere il servizio di notifica, i preavvisi, l'orario e, per i veicoli, il sensore del contachilometri.

| Voce | Scadenze |
|---|---|
| Panda (auto, immatricolata a maggio 2022) | Revisione, Bollo, Assicurazione, Tagliando ogni 12 mesi o 15.000 km, Cambio gomme |
| Casa | Manutenzione caldaia, Controllo fumi caldaia, Pulizia climatizzatore |
| Mario (nato l'8 maggio 1990) | Carta d'identità, Patente, Passaporto |

## Cosa trovi in Home Assistant

Ogni scadenza è un dispositivo, collegato a quello della sua voce.

| Entità | Dove | Cosa mostra |
|---|---|---|
| `sensor` data | scadenza | la data di scadenza; negli attributi stato, ultimo rinnovo e dati del modello |
| `sensor` giorni mancanti | scadenza | giorni alla scadenza, negativi se è passata |
| `sensor` km mancanti | tagliando | km al prossimo tagliando, se hai configurato il contachilometri |
| `binary_sensor` in scadenza | scadenza | acceso quando la scadenza è vicina o superata |
| `button` rinnovato | scadenza | registra il rinnovo e calcola la data successiva |
| `calendar` scadenze | voce | tutte le scadenze della voce nel pannello Calendario |
| `todo` da rinnovare | voce | le scadenze vicine o superate; spuntarle equivale a «Rinnovato» |

## Le regole

| Scadenza | Regola |
|---|---|
| Revisione | Prima entro la fine del mese, quattro anni dopo l'immatricolazione; poi ogni due anni dal mese dell'ultima |
| Bollo | Annuale; si paga entro l'ultimo giorno del mese successivo alla scadenza |
| Assicurazione | Annuale; un attributo indica la fine dei 15 giorni di tolleranza |
| Tagliando | Ogni N mesi o N km, quello che arriva prima |
| Cambio gomme | Invernali entro il 15 novembre, estive entro il 15 maggio |
| Patente | 10 anni sotto i 50, 5 fino ai 70, 3 fino agli 80, poi 2; scade al compleanno |
| Carta d'identità | 3 anni sotto i 3, 5 fino ai 18, poi fino al compleanno dopo 9 anni; **illimitata** dai 70 anni per le carte emesse dal 30 luglio 2026 |
| Passaporto | 3 anni sotto i 3, 5 fino ai 18, poi 10 |
| Caldaia, climatizzatore, estintore, filtri, canna fumaria | Ogni N mesi dall'ultima volta |

## Promemoria

Ogni giorno all'orario scelto l'integrazione controlla le scadenze e, per quelle che hanno superato una soglia:

- lancia l'evento **`scadenze_promemoria`**, con voce, scadenza, data, giorni e km mancanti e il messaggio;
- se le notifiche sono attive, chiama il servizio scelto, per esempio `notify.mobile_app_telefono`.

Preferisci le tue automazioni? In `blueprints/automation/scadenze/` c'è una blueprint pronta, oppure:

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

I test in `tests/logica` coprono le regole e girano anche senza Home Assistant (basta `pip install pytest`); quelli in `tests/ha` richiedono Linux.

## Licenza

[MIT](LICENSE)
