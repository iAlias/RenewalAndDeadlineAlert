# Scadenze Auto & Casa

[![Validate](https://github.com/iAlias/ScadenzeAutoCasaSalute/actions/workflows/validate.yml/badge.svg)](https://github.com/iAlias/ScadenzeAutoCasaSalute/actions/workflows/validate.yml)
[![HACS: Custom repository](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/docs/faq/custom_repositories/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Leggi in italiano](https://img.shields.io/badge/lingua-italiano-009246.svg)](README.it.md)

**Vehicle inspections, road tax, driving licence, boiler maintenance: everyday Italian deadlines tracked inside Home Assistant, calculated from the actual rules and never missed.**

No account, no API, no website to scrape: every date is calculated locally, so the integration keeps working even when a government portal changes or goes down.

---

## Table of contents

- [What it does](#what-it-does)
- [Requirements](#requirements)
- [Installation](#installation)
- [Getting started](#getting-started)
- [What you get in Home Assistant](#what-you-get-in-home-assistant)
- [Rules and sources](#rules-and-sources)
- [Reminders](#reminders)
- [The card](#the-card)
- [Declared limitations](#declared-limitations)
- [Development](#development)
- [Issues and contributions](#issues-and-contributions)
- [License](#license)

## What it does

- Tracks deadlines for **vehicles**, **home systems**, **people**, and anything else you want to remind yourself of.
- **Suggests the correct due date** using the actual Italian rules: the first roadworthiness test four years after first registration, road tax due by the end of the month following expiry, a driving licence that expires on the birthday that matches your age bracket.
- **One-click renewal**: press **Renewed**, or check the item off the to-do list, and the next due date is calculated automatically from the rule that applies to it.
- **Notifies you** at the advance-notice thresholds you choose — 30, 7 and 1 day by default — without repeating the same alert twice.
- **Guided setup**: after you create a vehicle, home, or person, a single wizard walks you through adding its first deadlines one at a time, with values already suggested where they can be computed.
- A Lovelace card ships with the integration and registers itself automatically — no manual resource to add.

## Requirements

Home Assistant **2026.8** or later.

## Installation

### Via HACS (recommended)

This integration is not yet in the HACS default store; add it as a custom repository:

1. HACS → Integrations → ⋮ menu → **Custom repositories**
2. Add `https://github.com/iAlias/ScadenzeAutoCasaSalute` with category **Integration**
3. Install it, then restart Home Assistant
4. **Settings → Devices & services → Add integration → Scadenze Auto & Casa**

### Manually

Copy `custom_components/scadenze` into your `config/custom_components` directory, restart Home Assistant, then add the integration as in step 4 above.

## Getting started

1. **Create an item**: a vehicle (with its first-registration month), a home, a person (with a date of birth), or a generic item for anything else.
2. **Choose which deadlines to add now** — inspection, road tax, insurance, and so on. The wizard walks you through them one at a time, with suggested values already filled in wherever they can be computed. You can always add more later from the item's device page with **Add deadline**.
3. Open **Configure** on the item to pick the notification service, the advance-notice thresholds, the time of day, and, for vehicles, the odometer sensor.

| Item | Deadlines |
|---|---|
| Panda (car, registered May 2022) | Inspection, road tax, insurance, service every 12 months or 15,000 km, tyre change |
| Home | Boiler maintenance, boiler emissions check, air conditioner cleaning |
| Mario (born 8 May 1990) | Identity card, driving licence, passport |

## What you get in Home Assistant

Every deadline is its own device, linked to the device of the item it belongs to.

| Entity | Where | What it shows |
|---|---|---|
| `sensor` due date | deadline | the next due date; attributes include status, last renewal, and model-specific data |
| `sensor` days left | deadline | days until the deadline, negative once it's overdue |
| `sensor` kilometres left | service | kilometres until the next service, if an odometer sensor is configured |
| `binary_sensor` due soon | deadline | on when the deadline is close or overdue |
| `button` renewed | deadline | records the renewal and computes the next due date |
| `calendar` deadlines | item | every deadline of the item, in the Calendar panel |
| `todo` to renew | item | deadlines that are close or overdue; checking one off is the same as pressing Renewed |

## Rules and sources

| Deadline | Rule |
|---|---|
| Vehicle inspection | First due by the end of the month, four years after first registration; every two years after that from the month of the last one |
| Road tax | Annual; payable by the end of the month following expiry |
| Insurance | Annual; an attribute reports the end of the 15-day grace period |
| Service | Every N months or N kilometres, whichever comes first |
| Tyre change | Winter tyres by 15 November, summer tyres by 15 May |
| Driving licence | 10 years under 50, 5 up to 70, 3 up to 80, then 2; expires on the matching birthday |
| Identity card | 3 years under 3, 5 up to 18, then on the birthday after 9 years; **no expiry** from age 70 for cards issued from 30 July 2026 |
| Passport | 3 years under 3, 5 up to 18, then 10 |
| Boiler, air conditioner, fire extinguisher, water filters, chimney | Every N months from the last time |

These rules were checked against the following official and reference sources, and are re-verified whenever they change:

- Vehicle inspection: [MIT – Revisione periodica veicoli](https://www.mit.gov.it/revisione-periodica-veicoli)
- Road tax: [L'Automobile ACI – Bollo auto 2026](https://www.lautomobile.aci.it/attualita/bollo-auto-2026-scadenze-tariffe-ed-esenzioni-la-guida-completa/)
- Driving licence: [MIT – Rinnovo patente](https://www.mit.gov.it/rinnovo-patente)
- Identity card: [Wikipedia – CIE](https://it.wikipedia.org/wiki/Carta_d'identit%C3%A0_elettronica_italiana), [ANAP – CIE over 70 illimitata](https://www.anap.it/notizia/cie-over-70-carta-identita-elettronica-a-vita/)
- Insurance grace period: [ConTe.it](https://www.conte.it/blog/assicurazione-auto/scadenza-assicurazione-auto-e-proroga-15-giorni/)
- Winter tyres: [Ayvens – Cambio gomme invernali](https://www.ayvens.com/it-it/blog/conducenti/cambio-gomme-invernali/)
- Boiler maintenance, DPR 74/2013: [Bosetti & Gatti – dPR 74/2013](https://www.bosettiegatti.eu/info/norme/statali/2013_0074.htm)

## Reminders

Every day, at the time you choose, the integration checks every deadline and, for the ones that have crossed a threshold:

- fires the **`scadenze_promemoria`** event, with the item, the deadline, the date, the days and kilometres left, and the message;
- if notifications are enabled, calls the notify service you configured, for example `notify.mobile_app_phone`.

Prefer your own automations? There's a ready-made blueprint in `blueprints/automation/scadenze/`, or write your own:

```yaml
triggers:
  - trigger: event
    event_type: scadenze_promemoria
actions:
  - action: notify.mobile_app_phone
    data:
      title: "{{ trigger.event.data.voce }} – {{ trigger.event.data.scadenza }}"
      message: "{{ trigger.event.data.messaggio }}"
```

## The card

The integration ships with a Lovelace card, already registered — there's no resource to add to your dashboard by hand. It appears in the card picker as **Scadenze** and can be configured through its visual editor.

```yaml
type: custom:scadenze-card
titolo: Deadlines
modalita: tutte            # tutte (default) | voce | scelte
voce: <item>                # with modalita: voce
scelte:                     # with modalita: scelte
  - <deadline 1>
  - <deadline 2>
nascondi_ok: false
mostra_giorni: true
mostra_km: true
mostra_rinnovato: true
```

| Option | Default | What it does |
|---|---|---|
| `titolo` | none | Card header |
| `modalita` | `tutte` | `tutte` (everything), `voce` (a single item), or `scelte` (hand-picked deadlines, from any item) |
| `voce` | — | With `modalita: voce`, which item to show |
| `scelte` | — | With `modalita: scelte`, which deadlines to show |
| `nascondi_ok` | `false` | Shows only overdue or upcoming deadlines |
| `mostra_giorni` | `true` | Adds "in N days" or "overdue by N days" |
| `mostra_km` | `true` | Adds the kilometres left for a service |
| `mostra_rinnovato` | `true` | The "Renewed" button: the first click asks for confirmation, the second renews |

Every row has a coloured strip: red if the deadline is overdue, amber if it's coming up, green if it's fine, grey if it has no expiry or is done.

## Declared limitations

- **Suggested dates are calculations, not official documents.** Check them against your vehicle logbook, receipts, and documents; they can always be corrected with "Reconfigure".
- **Some periods vary by region** (emissions check, first road tax in Lombardy and Piedmont): the proposed values are editable.
- Document rules are current as of **September 2026**.
- Reminder text is in Italian.

## Development

```bash
pip install -r requirements_test.txt
pytest -q
```

Tests under `tests/logica` cover the pure calculation rules and run without Home Assistant installed (just `pip install pytest`); tests under `tests/ha` require Linux.

## Issues and contributions

Found a bug, or a rule that no longer matches the law? Open an issue at
[github.com/iAlias/ScadenzeAutoCasaSalute/issues](https://github.com/iAlias/ScadenzeAutoCasaSalute/issues).

## License

[MIT](LICENSE)
