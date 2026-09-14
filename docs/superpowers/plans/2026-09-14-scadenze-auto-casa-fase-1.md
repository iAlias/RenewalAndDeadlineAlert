# Scadenze Auto & Casa — piano di implementazione della fase 1

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** costruire l'integrazione custom Home Assistant `scadenze`, che calcola in locale le scadenze italiane di veicoli, casa e documenti, le mostra come sensori, calendario e lista todo, le rinnova con un pulsante e manda promemoria senza doppioni.

**Architecture:** la logica di calcolo sta in moduli Python puri (`date_utils`, `modello_dati`, `regole`, `modelli`, `promemoria`) che non importano Home Assistant. Sopra c'è un sottile strato HA: la voce è una config entry con un dispositivo, ogni scadenza è una config subentry con un dispositivo proprio collegato con `via_device_id`. Un `DataUpdateCoordinator` senza polling ricalcola gli stati a mezzanotte, al cambio del contachilometri e dopo ogni rinnovo.

**Tech Stack:** Python ≥ 3.14.2, Home Assistant ≥ 2026.8 (test su 2026.9.2), `pytest`, `pytest-homeassistant-custom-component==0.13.365`, GitHub Actions (hassfest, HACS action).

**Spec:** `docs/superpowers/specs/2026-09-14-scadenze-auto-casa-design.md` (sezione 15 compresa: prevale sulle precedenti).

## Global Constraints

- Home Assistant minimo `2026.8.0` (`hacs.json`); test contro `homeassistant==2026.9.2` tramite `pytest-homeassistant-custom-component==0.13.365`.
- Python `>= 3.14.2`.
- Nessuna dipendenza a runtime: `manifest.json` → `"requirements": []`.
- Dominio `scadenze`; tipo di subentry `scadenza`; evento `scadenze_promemoria`; `integration_type: service`; `iot_class: calculated`; `version: 0.1.0`.
- I moduli `const.py`, `date_utils.py`, `modello_dati.py`, `regole.py`, `modelli.py`, `promemoria.py` **non importano `homeassistant`**.
- Un dispositivo appartiene a una sola subentry: mai entità di subentry diverse sullo stesso dispositivo. Dispositivo della scadenza con `via_device_id` verso il dispositivo della voce.
- Date salvate come stringhe ISO `AAAA-MM-GG`. Nomi nel codice in italiano, come nella spec.
- Testi rivolti all'utente dei promemoria in italiano; traduzioni `translations/it.json` ed `en.json`, con `strings.json` identico a `en.json`.
- Test: `tests/logica/` (solo `pytest`, gira anche su Windows) e `tests/ha/` (richiede Linux: CI o WSL). I test HA cercano le entità per `unique_id`.
- Ogni commit termina con le righe:
  ```
  Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01DospB88Me7xwRVWZPkgCSn
  ```
- Cartella di lavoro: `C:\AI Code\Home Assistant\scadenze-auto-casa` (repository git, branch `main`).

---

## Preparazione dell'ambiente (prima del Task 1)

**Ambiente di logica (Windows o qualunque sistema):**

```powershell
winget install --id Python.Python.3.14 -e
py -3.14 -m venv .venv-logica
.venv-logica\Scripts\python -m pip install pytest==9.0.3
```

Comando dei test di logica: `.venv-logica\Scripts\python -m pytest tests/logica -q`
(su Linux: `.venv-logica/bin/python -m pytest tests/logica -q`).

**Ambiente completo (Linux, WSL o CI):**

```bash
python3.14 -m venv .venv
. .venv/bin/activate
pip install -r requirements_test.txt
```

Comando di tutti i test: `pytest -q`. Solo test HA: `pytest tests/ha -q`.

Nei passi qui sotto «`pytest …`» indica l'interprete dell'ambiente adatto: logica per `tests/logica`, completo per `tests/ha`.

## Mappa dei file

| File | Responsabilità | Task |
|---|---|---|
| `pyproject.toml`, `requirements_test.txt`, `.gitignore` | configurazione di pytest e dipendenze di test | 1 |
| `custom_components/scadenze/const.py` | costanti condivise | 1 |
| `custom_components/scadenze/date_utils.py` | aritmetica delle date | 1 |
| `custom_components/scadenze/modello_dati.py` | `Voce`, `Scadenza`, `Stato`, conversioni | 2 |
| `custom_components/scadenze/regole.py` | rinnovo, stato, attributi, suggerimenti | 3 |
| `custom_components/scadenze/modelli.py` | catalogo modelli e form | 4 |
| `custom_components/scadenze/promemoria.py` | soglie e memoria dei promemoria | 5 |
| `custom_components/scadenze/manifest.json`, `coordinator.py`, `__init__.py` | setup, dispositivo voce, ricalcoli, reload | 6 |
| `custom_components/scadenze/entity.py`, `sensor.py`, `binary_sensor.py` | entità in sola lettura | 7 |
| `custom_components/scadenze/button.py` | pulsante Rinnovato | 8 |
| `custom_components/scadenze/calendar.py`, `todo.py` | entità della voce | 9 |
| `custom_components/scadenze/notifiche.py` | pianificazione e invio promemoria | 10 |
| `custom_components/scadenze/config_flow.py`, `strings.json`, `translations/*.json` | flussi e traduzioni | 11 |
| `blueprints/…`, `hacs.json`, `README.md`, `LICENSE`, `.github/workflows/validate.yml` | distribuzione | 12 |
| `tests/logica/*` | test dei moduli puri | 1–5, 11 |
| `tests/ha/*` | test con Home Assistant | 6–12 |

---

### Task 1: Struttura del progetto e `date_utils`

**Files:**
- Create: `pyproject.toml`, `requirements_test.txt`, `.gitignore`
- Create: `custom_components/scadenze/const.py`, `custom_components/scadenze/date_utils.py`
- Create: `tests/__init__.py`, `tests/logica/__init__.py`, `tests/logica/conftest.py`
- Test: `tests/logica/test_date_utils.py`

**Interfaces:**
- Consumes: nulla.
- Produces:
  - `const.py`: `DOMAIN`, `SUBENTRY_SCADENZA`, `EVENTO_PROMEMORIA`, `CONF_TIPO`, `CONF_NOME`, `CONF_TIPO_VEICOLO`, `CONF_IMMATRICOLAZIONE`, `CONF_DATA_NASCITA`, `TIPO_VEICOLO`, `TIPO_CASA`, `TIPO_PERSONA`, `TIPO_GENERICA`, `TIPI_VOCE`, `ETICHETTE_TIPO_VOCE`, `VEICOLO_AUTO`, `VEICOLO_MOTO`, `CONF_SENSORE_KM`, `CONF_NOTIFICHE_ATTIVE`, `CONF_SERVIZIO_NOTIFICA`, `CONF_PREAVVISI`, `CONF_ORARIO_NOTIFICA`, `PREDEFINITO_SERVIZIO_NOTIFICA`, `PREDEFINITO_PREAVVISI`, `PREDEFINITO_ORARIO_NOTIFICA`, `FINESTRA_SENZA_PREAVVISI`, `SOGLIA_KM`, `TOLLERANZA_ASSICURAZIONE_GIORNI`.
  - `date_utils.py`: `fine_mese(d: date) -> date`, `aggiungi_mesi(d: date, mesi: int) -> date`, `compleanno_dopo(nascita: date, riferimento: date) -> date`, `eta(nascita: date, il_giorno: date) -> int`.

- [ ] **Step 1: Configurazione di progetto**

`pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

`requirements_test.txt`:

```text
pytest-homeassistant-custom-component==0.13.365
```

`.gitignore`:

```text
__pycache__/
*.pyc
.pytest_cache/
.venv/
.venv-logica/
.coverage
```

`tests/__init__.py` e `tests/logica/__init__.py`: file vuoti.

`tests/logica/conftest.py`:

```python
"""Rende importabili i moduli di logica pura anche senza Home Assistant.

`custom_components/scadenze/__init__.py` importa Home Assistant. Dove Home Assistant
non è installato (per esempio su Windows) i pacchetti vengono registrati a mano, con
un `__path__` ma senza eseguire il loro `__init__`, così Python trova i sottomoduli.
Dove Home Assistant c'è (CI, WSL) non serve nulla e si usa il pacchetto vero.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = ROOT / "custom_components"


def _registra(nome: str, percorso: Path) -> None:
    modulo = types.ModuleType(nome)
    modulo.__path__ = [str(percorso)]  # type: ignore[attr-defined]
    sys.modules[nome] = modulo


if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if importlib.util.find_spec("homeassistant") is None:
    _registra("custom_components", COMPONENTS)
    _registra("custom_components.scadenze", COMPONENTS / "scadenze")
```

`custom_components/scadenze/const.py`:

```python
"""Costanti condivise di Scadenze Auto & Casa.

Il modulo non importa Home Assistant: lo usano anche i moduli di logica pura.
"""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "scadenze"
SUBENTRY_SCADENZA: Final = "scadenza"
EVENTO_PROMEMORIA: Final = "scadenze_promemoria"

# Dati della voce (entry.data)
CONF_TIPO: Final = "tipo"
CONF_NOME: Final = "nome"
CONF_TIPO_VEICOLO: Final = "tipo_veicolo"
CONF_IMMATRICOLAZIONE: Final = "immatricolazione"
CONF_DATA_NASCITA: Final = "data_nascita"

TIPO_VEICOLO: Final = "veicolo"
TIPO_CASA: Final = "casa"
TIPO_PERSONA: Final = "persona"
TIPO_GENERICA: Final = "generica"
TIPI_VOCE: Final = (TIPO_VEICOLO, TIPO_CASA, TIPO_PERSONA, TIPO_GENERICA)

ETICHETTE_TIPO_VOCE: Final = {
    TIPO_VEICOLO: "Veicolo",
    TIPO_CASA: "Casa",
    TIPO_PERSONA: "Persona",
    TIPO_GENERICA: "Generica",
}

VEICOLO_AUTO: Final = "auto"
VEICOLO_MOTO: Final = "moto"

# Opzioni della voce (entry.options)
CONF_SENSORE_KM: Final = "sensore_km"
CONF_NOTIFICHE_ATTIVE: Final = "notifiche_attive"
CONF_SERVIZIO_NOTIFICA: Final = "servizio_notifica"
CONF_PREAVVISI: Final = "preavvisi"
CONF_ORARIO_NOTIFICA: Final = "orario_notifica"

PREDEFINITO_SERVIZIO_NOTIFICA: Final = "notify.persistent_notification"
PREDEFINITO_PREAVVISI: Final = (30, 7, 1)
PREDEFINITO_ORARIO_NOTIFICA: Final = "09:00:00"

FINESTRA_SENZA_PREAVVISI: Final = 30
SOGLIA_KM: Final = 1000
TOLLERANZA_ASSICURAZIONE_GIORNI: Final = 15
```

- [ ] **Step 2: Scrivere i test che falliscono**

`tests/logica/test_date_utils.py`:

```python
"""Test dell'aritmetica delle date (spec §5.1)."""

from __future__ import annotations

from datetime import date

import pytest

from custom_components.scadenze.date_utils import (
    aggiungi_mesi,
    compleanno_dopo,
    eta,
    fine_mese,
)


@pytest.mark.parametrize(
    ("giorno", "atteso"),
    [
        (date(2026, 2, 10), date(2026, 2, 28)),
        (date(2028, 2, 1), date(2028, 2, 29)),
        (date(2026, 12, 31), date(2026, 12, 31)),
    ],
)
def test_fine_mese(giorno: date, atteso: date) -> None:
    assert fine_mese(giorno) == atteso


@pytest.mark.parametrize(
    ("partenza", "mesi", "atteso"),
    [
        (date(2026, 1, 31), 1, date(2026, 2, 28)),
        (date(2028, 1, 31), 1, date(2028, 2, 29)),
        (date(2026, 8, 31), 6, date(2027, 2, 28)),
        (date(2026, 3, 15), -3, date(2025, 12, 15)),
        (date(2026, 12, 1), 1, date(2027, 1, 1)),
        (date(2028, 2, 29), 12, date(2029, 2, 28)),
    ],
)
def test_aggiungi_mesi(partenza: date, mesi: int, atteso: date) -> None:
    assert aggiungi_mesi(partenza, mesi) == atteso


@pytest.mark.parametrize(
    ("nascita", "riferimento", "atteso"),
    [
        (date(1990, 5, 8), date(2026, 9, 14), date(2027, 5, 8)),
        (date(1990, 5, 8), date(2026, 5, 8), date(2027, 5, 8)),
        (date(1990, 5, 8), date(2026, 5, 7), date(2026, 5, 8)),
        (date(2000, 2, 29), date(2026, 1, 1), date(2026, 2, 28)),
        (date(2000, 2, 29), date(2027, 12, 31), date(2028, 2, 29)),
    ],
)
def test_compleanno_dopo_strettamente_successivo(
    nascita: date, riferimento: date, atteso: date
) -> None:
    assert compleanno_dopo(nascita, riferimento) == atteso


@pytest.mark.parametrize(
    ("nascita", "giorno", "attesa"),
    [
        (date(1976, 9, 14), date(2026, 9, 14), 50),
        (date(1976, 9, 14), date(2026, 9, 13), 49),
        (date(2000, 2, 29), date(2026, 2, 28), 26),
        (date(2000, 2, 29), date(2026, 2, 27), 25),
    ],
)
def test_eta(nascita: date, giorno: date, attesa: int) -> None:
    assert eta(nascita, giorno) == attesa
```

- [ ] **Step 3: Eseguire i test e verificare che falliscono**

Run: `pytest tests/logica/test_date_utils.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'custom_components.scadenze.date_utils'`

- [ ] **Step 4: Implementare**

`custom_components/scadenze/date_utils.py`:

```python
"""Aritmetica delle date usata dalle regole di scadenza.

Modulo di logica pura: non importa Home Assistant.
"""

from __future__ import annotations

import calendar
from datetime import date


def fine_mese(giorno: date) -> date:
    """L'ultimo giorno del mese di `giorno`."""
    return giorno.replace(day=calendar.monthrange(giorno.year, giorno.month)[1])


def aggiungi_mesi(giorno: date, mesi: int) -> date:
    """Lo stesso giorno `mesi` mesi dopo (o prima), limitato alla fine del mese."""
    indice = giorno.year * 12 + (giorno.month - 1) + mesi
    anno, mese_zero = divmod(indice, 12)
    mese = mese_zero + 1
    return date(anno, mese, min(giorno.day, calendar.monthrange(anno, mese)[1]))


def _compleanno_nell_anno(nascita: date, anno: int) -> date:
    """Il compleanno in `anno`: chi è nato il 29/02 lo festeggia il 28/02 negli anni non bisestili."""
    if nascita.month == 2 and nascita.day == 29 and not calendar.isleap(anno):
        return date(anno, 2, 28)
    return nascita.replace(year=anno)


def compleanno_dopo(nascita: date, riferimento: date) -> date:
    """Il primo compleanno strettamente successivo a `riferimento`."""
    candidato = _compleanno_nell_anno(nascita, riferimento.year)
    if candidato <= riferimento:
        candidato = _compleanno_nell_anno(nascita, riferimento.year + 1)
    return candidato


def eta(nascita: date, il_giorno: date) -> int:
    """Gli anni compiuti in `il_giorno`."""
    anni = il_giorno.year - nascita.year
    if il_giorno < _compleanno_nell_anno(nascita, il_giorno.year):
        anni -= 1
    return anni
```

- [ ] **Step 5: Eseguire i test e verificare che passano**

Run: `pytest tests/logica/test_date_utils.py -q`
Expected: PASS (18 test)

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml requirements_test.txt .gitignore tests/__init__.py tests/logica custom_components/scadenze/const.py custom_components/scadenze/date_utils.py
git commit -m "feat: struttura del progetto e aritmetica delle date"
```

### Task 2: Modello dati (`Voce`, `Scadenza`, `Stato`)

**Files:**
- Create: `custom_components/scadenze/modello_dati.py`
- Test: `tests/logica/test_modello_dati.py`

**Interfaces:**
- Consumes: `const.py` (Task 1).
- Produces (`modello_dati.py`):
  - chiavi `K_MODELLO`, `K_NOME`, `K_REGOLA`, `K_SCADENZA`, `K_ULTIMO_RINNOVO`, `K_COMPLETATA`, `K_INTERVALLO_MESI`, `K_ANCORA`, `K_INTERVALLO_KM`, `K_KM_ULTIMO_RINNOVO`, `K_MESE_SCADENZA_BOLLO`, `K_DOCUMENTO`;
  - regole `REGOLA_FINE_MESE`, `REGOLA_INTERVALLO`, `REGOLA_DOCUMENTO`, `REGOLA_STAGIONALE`, `REGOLA_UNICA`, `REGOLE`; ancore `ANCORA_RINNOVO`, `ANCORA_SCADENZA`;
  - documenti `DOC_PATENTE`, `DOC_CARTA_IDENTITA`, `DOC_PASSAPORTO`, `DOCUMENTI`;
  - modelli `M_REVISIONE`, `M_BOLLO`, `M_ASSICURAZIONE`, `M_TAGLIANDO`, `M_GOMME`, `M_MANUTENZIONE_CALDAIA`, `M_CONTROLLO_FUMI`, `M_CLIMATIZZATORE`, `M_ESTINTORE`, `M_FILTRI_ACQUA`, `M_CANNA_FUMARIA`, `M_CARTA_IDENTITA`, `M_PATENTE`, `M_PASSAPORTO`, `M_TESSERA_SANITARIA`, `M_PERSONALIZZATA`;
  - stati `STATO_SCADUTA`, `STATO_IN_SCADENZA`, `STATO_OK`, `STATO_ILLIMITATA`, `STATO_COMPLETATA`;
  - `class DatiNonValidi(ValueError)`; `leggi_data(valore: Any) -> date | None`; `leggi_intero(valore: Any) -> int | None`;
  - `@dataclass(frozen=True) class Voce(tipo: str, nome: str, tipo_veicolo: str | None = None, immatricolazione: date | None = None, data_nascita: date | None = None)` con `Voce.da_dict(Mapping) -> Voce` e `a_dict() -> dict`;
  - `@dataclass(frozen=True) class Scadenza(modello, nome, regola, scadenza: date | None, ultimo_rinnovo: date | None = None, completata: bool = False, intervallo_mesi: int | None = None, ancora: str = ANCORA_RINNOVO, intervallo_km: int | None = None, km_ultimo_rinnovo: int | None = None, mese_scadenza_bollo: date | None = None, documento: str | None = None)` con proprietà `usa_km -> bool`, `Scadenza.da_dict(Mapping) -> Scadenza`, `a_dict() -> dict`;
  - `@dataclass(frozen=True) class Stato(stato: str, giorni_mancanti: int | None = None, km_attuali: int | None = None, km_scadenza: int | None = None, km_mancanti: int | None = None, km_non_disponibili: bool = False)`.

- [ ] **Step 1: Scrivere i test che falliscono**

`tests/logica/test_modello_dati.py`:

```python
"""Test della lettura e scrittura dei dati salvati (spec §4)."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from custom_components.scadenze.modello_dati import (
    ANCORA_RINNOVO,
    DatiNonValidi,
    Scadenza,
    Voce,
)

DATI_TAGLIANDO: dict[str, Any] = {
    "modello": "tagliando",
    "nome": "Tagliando",
    "regola": "intervallo",
    "scadenza": "2027-03-01",
    "ultimo_rinnovo": "2026-03-01",
    "completata": False,
    "intervallo_mesi": 12,
    "ancora": "rinnovo",
    "intervallo_km": 15000,
    "km_ultimo_rinnovo": 20000,
    "mese_scadenza_bollo": None,
    "documento": None,
}


def test_voce_andata_e_ritorno() -> None:
    voce = Voce.da_dict(
        {
            "tipo": "veicolo",
            "nome": "Panda",
            "tipo_veicolo": "auto",
            "immatricolazione": "2022-05-01",
        }
    )
    assert voce.immatricolazione == date(2022, 5, 1)
    assert Voce.da_dict(voce.a_dict()) == voce


@pytest.mark.parametrize(
    "dati",
    [
        {"tipo": "barca", "nome": "Gozzo"},
        {"tipo": "casa"},
        {"tipo": "persona", "nome": "Mario", "data_nascita": "08/05/1990"},
    ],
)
def test_voce_non_valida(dati: dict[str, Any]) -> None:
    with pytest.raises(DatiNonValidi):
        Voce.da_dict(dati)


def test_scadenza_andata_e_ritorno() -> None:
    scadenza = Scadenza.da_dict(DATI_TAGLIANDO)
    assert scadenza.scadenza == date(2027, 3, 1)
    assert scadenza.km_ultimo_rinnovo == 20000
    assert scadenza.a_dict() == DATI_TAGLIANDO


def test_numeri_dal_form_diventano_interi() -> None:
    scadenza = Scadenza.da_dict(
        {**DATI_TAGLIANDO, "intervallo_mesi": 12.0, "intervallo_km": "15000"}
    )
    assert scadenza.intervallo_mesi == 12
    assert scadenza.intervallo_km == 15000


def test_chiavi_facoltative_con_valori_predefiniti() -> None:
    scadenza = Scadenza.da_dict(
        {
            "modello": "personalizzata",
            "nome": "Canone",
            "regola": "unica",
            "scadenza": "2027-01-31",
        }
    )
    assert scadenza.completata is False
    assert scadenza.ancora == ANCORA_RINNOVO
    assert scadenza.usa_km is False


@pytest.mark.parametrize(
    "difetto",
    [
        {"regola": None},
        {"regola": "mensile"},
        {"scadenza": "31/12/2026"},
        {"intervallo_mesi": None},
        {"intervallo_mesi": "dodici"},
        {"ancora": "sempre"},
        {"scadenza": None},
    ],
)
def test_scadenza_non_valida(difetto: dict[str, Any]) -> None:
    with pytest.raises(DatiNonValidi):
        Scadenza.da_dict({**DATI_TAGLIANDO, **difetto})


def test_documento_richiede_il_tipo_di_documento() -> None:
    dati = {
        "modello": "patente",
        "nome": "Patente",
        "regola": "documento",
        "scadenza": "2031-05-08",
    }
    with pytest.raises(DatiNonValidi):
        Scadenza.da_dict(dati)
    assert Scadenza.da_dict({**dati, "documento": "patente"}).documento == "patente"


def test_documento_illimitato_e_unica_completata_senza_data() -> None:
    illimitata = Scadenza.da_dict(
        {
            "modello": "carta_identita",
            "nome": "Carta d'identità",
            "regola": "documento",
            "scadenza": None,
            "documento": "carta_identita",
        }
    )
    assert illimitata.scadenza is None
    completata = Scadenza.da_dict(
        {
            "modello": "personalizzata",
            "nome": "Trasloco",
            "regola": "unica",
            "scadenza": None,
            "completata": True,
        }
    )
    assert completata.completata is True


def test_usa_km() -> None:
    assert Scadenza.da_dict(DATI_TAGLIANDO).usa_km is True
    assert Scadenza.da_dict({**DATI_TAGLIANDO, "intervallo_km": 0}).usa_km is False
```

- [ ] **Step 2: Eseguire i test e verificare che falliscono**

Run: `pytest tests/logica/test_modello_dati.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'custom_components.scadenze.modello_dati'`

- [ ] **Step 3: Implementare**

`custom_components/scadenze/modello_dati.py`:

```python
"""Dati di voci e scadenze, e loro conversione da e verso i dict salvati da HA.

Modulo di logica pura: non importa Home Assistant.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from .const import (
    CONF_DATA_NASCITA,
    CONF_IMMATRICOLAZIONE,
    CONF_NOME,
    CONF_TIPO,
    CONF_TIPO_VEICOLO,
    TIPI_VOCE,
)

# Chiavi dei dati di una scadenza (subentry.data)
K_MODELLO = "modello"
K_NOME = "nome"
K_REGOLA = "regola"
K_SCADENZA = "scadenza"
K_ULTIMO_RINNOVO = "ultimo_rinnovo"
K_COMPLETATA = "completata"
K_INTERVALLO_MESI = "intervallo_mesi"
K_ANCORA = "ancora"
K_INTERVALLO_KM = "intervallo_km"
K_KM_ULTIMO_RINNOVO = "km_ultimo_rinnovo"
K_MESE_SCADENZA_BOLLO = "mese_scadenza_bollo"
K_DOCUMENTO = "documento"

REGOLA_FINE_MESE = "fine_mese"
REGOLA_INTERVALLO = "intervallo"
REGOLA_DOCUMENTO = "documento"
REGOLA_STAGIONALE = "stagionale"
REGOLA_UNICA = "unica"
REGOLE = (
    REGOLA_FINE_MESE,
    REGOLA_INTERVALLO,
    REGOLA_DOCUMENTO,
    REGOLA_STAGIONALE,
    REGOLA_UNICA,
)

ANCORA_RINNOVO = "rinnovo"
ANCORA_SCADENZA = "scadenza"

DOC_PATENTE = "patente"
DOC_CARTA_IDENTITA = "carta_identita"
DOC_PASSAPORTO = "passaporto"
DOCUMENTI = (DOC_PATENTE, DOC_CARTA_IDENTITA, DOC_PASSAPORTO)

# Chiavi dei modelli; il catalogo completo è in modelli.py
M_REVISIONE = "revisione"
M_BOLLO = "bollo"
M_ASSICURAZIONE = "assicurazione"
M_TAGLIANDO = "tagliando"
M_GOMME = "gomme"
M_MANUTENZIONE_CALDAIA = "manutenzione_caldaia"
M_CONTROLLO_FUMI = "controllo_fumi"
M_CLIMATIZZATORE = "climatizzatore"
M_ESTINTORE = "estintore"
M_FILTRI_ACQUA = "filtri_acqua"
M_CANNA_FUMARIA = "canna_fumaria"
M_CARTA_IDENTITA = "carta_identita"
M_PATENTE = "patente"
M_PASSAPORTO = "passaporto"
M_TESSERA_SANITARIA = "tessera_sanitaria"
M_PERSONALIZZATA = "personalizzata"

STATO_SCADUTA = "scaduta"
STATO_IN_SCADENZA = "in_scadenza"
STATO_OK = "ok"
STATO_ILLIMITATA = "illimitata"
STATO_COMPLETATA = "completata"


class DatiNonValidi(ValueError):
    """I dati salvati di una voce o di una scadenza non sono leggibili."""


def leggi_data(valore: Any) -> date | None:
    """Una data ISO, un oggetto `date` o niente."""
    if valore is None or valore == "":
        return None
    if isinstance(valore, date):
        return valore
    try:
        return date.fromisoformat(str(valore))
    except ValueError as err:
        raise DatiNonValidi(f"data non valida: {valore!r}") from err


def leggi_intero(valore: Any) -> int | None:
    """Un intero; i selettori numerici di HA restituiscono float."""
    if valore is None or valore == "":
        return None
    try:
        return int(float(valore))
    except (TypeError, ValueError) as err:
        raise DatiNonValidi(f"numero non valido: {valore!r}") from err


def _iso(valore: date | None) -> str | None:
    return valore.isoformat() if valore is not None else None


def _obbligatorio(dati: Mapping[str, Any], chiave: str) -> Any:
    valore = dati.get(chiave)
    if valore is None or valore == "":
        raise DatiNonValidi(f"manca {chiave!r}")
    return valore


@dataclass(frozen=True)
class Voce:
    """L'oggetto che ha delle scadenze: veicolo, casa, persona o generica."""

    tipo: str
    nome: str
    tipo_veicolo: str | None = None
    immatricolazione: date | None = None
    data_nascita: date | None = None

    @classmethod
    def da_dict(cls, dati: Mapping[str, Any]) -> Voce:
        tipo = _obbligatorio(dati, CONF_TIPO)
        if tipo not in TIPI_VOCE:
            raise DatiNonValidi(f"tipo di voce sconosciuto: {tipo!r}")
        return cls(
            tipo=tipo,
            nome=str(_obbligatorio(dati, CONF_NOME)),
            tipo_veicolo=dati.get(CONF_TIPO_VEICOLO),
            immatricolazione=leggi_data(dati.get(CONF_IMMATRICOLAZIONE)),
            data_nascita=leggi_data(dati.get(CONF_DATA_NASCITA)),
        )

    def a_dict(self) -> dict[str, Any]:
        dati: dict[str, Any] = {CONF_TIPO: self.tipo, CONF_NOME: self.nome}
        if self.tipo_veicolo is not None:
            dati[CONF_TIPO_VEICOLO] = self.tipo_veicolo
        if self.immatricolazione is not None:
            dati[CONF_IMMATRICOLAZIONE] = self.immatricolazione.isoformat()
        if self.data_nascita is not None:
            dati[CONF_DATA_NASCITA] = self.data_nascita.isoformat()
        return dati


@dataclass(frozen=True)
class Scadenza:
    """Una singola cosa da rinnovare, con la regola che calcola la data successiva."""

    modello: str
    nome: str
    regola: str
    scadenza: date | None
    ultimo_rinnovo: date | None = None
    completata: bool = False
    intervallo_mesi: int | None = None
    ancora: str = ANCORA_RINNOVO
    intervallo_km: int | None = None
    km_ultimo_rinnovo: int | None = None
    mese_scadenza_bollo: date | None = None
    documento: str | None = None

    @property
    def usa_km(self) -> bool:
        """La scadenza ha anche un limite in chilometri."""
        return bool(self.intervallo_km)

    @classmethod
    def da_dict(cls, dati: Mapping[str, Any]) -> Scadenza:
        regola = _obbligatorio(dati, K_REGOLA)
        if regola not in REGOLE:
            raise DatiNonValidi(f"regola sconosciuta: {regola!r}")
        ancora = dati.get(K_ANCORA) or ANCORA_RINNOVO
        if ancora not in (ANCORA_RINNOVO, ANCORA_SCADENZA):
            raise DatiNonValidi(f"ancora sconosciuta: {ancora!r}")
        documento = dati.get(K_DOCUMENTO)
        if regola == REGOLA_DOCUMENTO and documento not in DOCUMENTI:
            raise DatiNonValidi(f"documento sconosciuto: {documento!r}")

        scadenza = cls(
            modello=str(_obbligatorio(dati, K_MODELLO)),
            nome=str(_obbligatorio(dati, K_NOME)),
            regola=regola,
            scadenza=leggi_data(dati.get(K_SCADENZA)),
            ultimo_rinnovo=leggi_data(dati.get(K_ULTIMO_RINNOVO)),
            completata=bool(dati.get(K_COMPLETATA, False)),
            intervallo_mesi=leggi_intero(dati.get(K_INTERVALLO_MESI)),
            ancora=ancora,
            intervallo_km=leggi_intero(dati.get(K_INTERVALLO_KM)),
            km_ultimo_rinnovo=leggi_intero(dati.get(K_KM_ULTIMO_RINNOVO)),
            mese_scadenza_bollo=leggi_data(dati.get(K_MESE_SCADENZA_BOLLO)),
            documento=documento,
        )

        if regola == REGOLA_INTERVALLO and not (scadenza.intervallo_mesi or 0) >= 1:
            raise DatiNonValidi("intervallo_mesi mancante")
        # Senza data sono ammesse solo le scadenze completate e i documenti illimitati.
        if (
            scadenza.scadenza is None
            and not scadenza.completata
            and regola != REGOLA_DOCUMENTO
        ):
            raise DatiNonValidi("manca 'scadenza'")
        return scadenza

    def a_dict(self) -> dict[str, Any]:
        return {
            K_MODELLO: self.modello,
            K_NOME: self.nome,
            K_REGOLA: self.regola,
            K_SCADENZA: _iso(self.scadenza),
            K_ULTIMO_RINNOVO: _iso(self.ultimo_rinnovo),
            K_COMPLETATA: self.completata,
            K_INTERVALLO_MESI: self.intervallo_mesi,
            K_ANCORA: self.ancora,
            K_INTERVALLO_KM: self.intervallo_km,
            K_KM_ULTIMO_RINNOVO: self.km_ultimo_rinnovo,
            K_MESE_SCADENZA_BOLLO: _iso(self.mese_scadenza_bollo),
            K_DOCUMENTO: self.documento,
        }


@dataclass(frozen=True)
class Stato:
    """Lo stato calcolato di una scadenza in un certo giorno (non salvato)."""

    stato: str
    giorni_mancanti: int | None = None
    km_attuali: int | None = None
    km_scadenza: int | None = None
    km_mancanti: int | None = None
    km_non_disponibili: bool = False
```

- [ ] **Step 4: Eseguire i test e verificare che passano**

Run: `pytest tests/logica/test_modello_dati.py -q`
Expected: PASS (17 test)

- [ ] **Step 5: Commit**

```bash
git add custom_components/scadenze/modello_dati.py tests/logica/test_modello_dati.py
git commit -m "feat: modello dati di voci, scadenze e stati"
```

### Task 3: Regole di calcolo

**Files:**
- Create: `custom_components/scadenze/regole.py`
- Test: `tests/logica/test_regole.py`

**Interfaces:**
- Consumes: `const.FINESTRA_SENZA_PREAVVISI`, `const.SOGLIA_KM`, `const.TOLLERANZA_ASSICURAZIONE_GIORNI` (Task 1); `date_utils.*` (Task 1); `modello_dati.*` (Task 2).
- Produces (`regole.py`):
  - `DATA_CIE_ILLIMITATA = date(2026, 7, 30)`, `MESI_PRIMA_REVISIONE = 48`, `MESI_REVISIONE = 24`, `AZIONE_MONTA = "monta_invernali"`, `AZIONE_SMONTA = "smonta_invernali"`;
  - `class RinnovoIgnorato(Exception)`;
  - `prima_revisione(immatricolazione: date) -> date`;
  - `prossima_revisione_da_immatricolazione(immatricolazione: date, oggi: date) -> date`;
  - `pagamento_bollo(mese_scadenza: date) -> date`;
  - `mese_scadenza_bollo_suggerito(immatricolazione: date, oggi: date) -> date`;
  - `data_gomme_da(riferimento: date, *, strettamente_dopo: bool) -> date`;
  - `azione_gomme(giorno: date) -> str`;
  - `scadenza_documento(documento: str, nascita: date, emissione: date) -> date | None`;
  - `rinnova(scadenza: Scadenza, voce: Voce, oggi: date, km_attuali: int | None) -> Scadenza` (solleva `RinnovoIgnorato`, `DatiNonValidi`);
  - `calcola_stato(scadenza: Scadenza, oggi: date, preavvisi: Sequence[int], km_attuali: int | None, *, km_configurati: bool) -> Stato`;
  - `attributi_extra(scadenza: Scadenza) -> dict[str, str]`.

- [ ] **Step 1: Scrivere i test che falliscono**

`tests/logica/test_regole.py`:

```python
"""Test delle regole di calcolo (spec §4.4 e §5)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest

from custom_components.scadenze.modello_dati import (
    ANCORA_SCADENZA,
    DOC_CARTA_IDENTITA,
    DOC_PASSAPORTO,
    DOC_PATENTE,
    M_ASSICURAZIONE,
    M_BOLLO,
    M_GOMME,
    M_REVISIONE,
    M_TAGLIANDO,
    REGOLA_DOCUMENTO,
    REGOLA_FINE_MESE,
    REGOLA_INTERVALLO,
    REGOLA_STAGIONALE,
    REGOLA_UNICA,
    STATO_COMPLETATA,
    STATO_ILLIMITATA,
    STATO_IN_SCADENZA,
    STATO_OK,
    STATO_SCADUTA,
    DatiNonValidi,
    Scadenza,
    Voce,
)
from custom_components.scadenze.regole import (
    RinnovoIgnorato,
    attributi_extra,
    azione_gomme,
    calcola_stato,
    data_gomme_da,
    mese_scadenza_bollo_suggerito,
    pagamento_bollo,
    prima_revisione,
    prossima_revisione_da_immatricolazione,
    rinnova,
    scadenza_documento,
)

OGGI = date(2026, 9, 14)
PREAVVISI = [30, 7, 1]
VEICOLO = Voce(
    tipo="veicolo", nome="Panda", tipo_veicolo="auto", immatricolazione=date(2022, 5, 1)
)


def crea(**campi: Any) -> Scadenza:
    valori: dict[str, Any] = {
        "modello": "personalizzata",
        "nome": "Prova",
        "regola": REGOLA_UNICA,
        "scadenza": date(2026, 12, 31),
    }
    valori.update(campi)
    return Scadenza(**valori)


def tagliando(giorno: date = OGGI + timedelta(days=200)) -> Scadenza:
    return crea(
        modello=M_TAGLIANDO,
        regola=REGOLA_INTERVALLO,
        scadenza=giorno,
        ultimo_rinnovo=date(2026, 3, 1),
        intervallo_mesi=12,
        intervallo_km=15000,
        km_ultimo_rinnovo=20000,
    )


# --- Revisione -------------------------------------------------------------


def test_prima_revisione_a_fine_mese_dopo_quattro_anni() -> None:
    assert prima_revisione(date(2022, 5, 1)) == date(2026, 5, 31)


@pytest.mark.parametrize(
    ("immatricolazione", "attesa"),
    [
        (date(2024, 9, 1), date(2028, 9, 30)),  # 2 anni: prima revisione futura
        (date(2022, 9, 1), date(2026, 9, 30)),  # 4 anni: scade questo mese
        (date(2017, 3, 1), date(2027, 3, 31)),  # 9 anni: revisioni biennali
    ],
)
def test_prossima_revisione_suggerita(immatricolazione: date, attesa: date) -> None:
    assert prossima_revisione_da_immatricolazione(immatricolazione, OGGI) == attesa


def test_rinnovo_revisione_due_anni_dal_mese_del_rinnovo() -> None:
    scadenza = crea(modello=M_REVISIONE, regola=REGOLA_FINE_MESE, scadenza=date(2026, 9, 30))
    nuova = rinnova(scadenza, VEICOLO, OGGI, None)
    assert nuova.scadenza == date(2028, 9, 30)
    assert nuova.ultimo_rinnovo == OGGI


# --- Bollo -----------------------------------------------------------------


def test_pagamento_bollo_entro_fine_mese_successivo() -> None:
    assert pagamento_bollo(date(2026, 12, 1)) == date(2027, 1, 31)
    assert pagamento_bollo(date(2027, 1, 1)) == date(2027, 2, 28)


def test_mese_bollo_suggerito_dal_mese_di_immatricolazione() -> None:
    assert mese_scadenza_bollo_suggerito(date(2022, 5, 1), OGGI) == date(2027, 4, 1)
    assert mese_scadenza_bollo_suggerito(date(2020, 1, 1), date(2026, 1, 10)) == date(2025, 12, 1)


def test_rinnovo_bollo_non_dipende_dal_giorno() -> None:
    scadenza = crea(
        modello=M_BOLLO,
        regola=REGOLA_FINE_MESE,
        scadenza=date(2026, 5, 31),
        mese_scadenza_bollo=date(2026, 4, 1),
    )
    nuova = rinnova(scadenza, VEICOLO, date(2026, 5, 20), None)
    assert nuova.mese_scadenza_bollo == date(2027, 4, 1)
    assert nuova.scadenza == date(2027, 5, 31)


# --- Intervallo ------------------------------------------------------------


def test_rinnovo_intervallo_dal_giorno_del_rinnovo_con_km() -> None:
    nuova = rinnova(tagliando(), VEICOLO, OGGI, 30500)
    assert (nuova.scadenza, nuova.ultimo_rinnovo, nuova.km_ultimo_rinnovo) == (
        date(2027, 9, 14),
        OGGI,
        30500,
    )


def test_rinnovo_senza_lettura_km_lascia_i_km() -> None:
    assert rinnova(tagliando(), VEICOLO, OGGI, None).km_ultimo_rinnovo == 20000


def test_rinnovo_intervallo_dalla_scadenza() -> None:
    assicurazione = crea(
        modello=M_ASSICURAZIONE,
        regola=REGOLA_INTERVALLO,
        scadenza=date(2026, 10, 2),
        intervallo_mesi=12,
        ancora=ANCORA_SCADENZA,
    )
    assert rinnova(assicurazione, VEICOLO, date(2026, 9, 30), None).scadenza == date(2027, 10, 2)


# --- Documenti -------------------------------------------------------------


@pytest.mark.parametrize(
    ("documento", "nascita", "emissione", "attesa"),
    [
        (DOC_PATENTE, date(1977, 1, 1), OGGI, date(2037, 1, 1)),  # 49 anni: 10 anni
        (DOC_PATENTE, date(1976, 9, 14), OGGI, date(2032, 9, 14)),  # 50 anni esatti: 5
        (DOC_PATENTE, date(1950, 1, 1), OGGI, date(2030, 1, 1)),  # 76 anni: 3
        (DOC_PATENTE, date(1940, 3, 10), OGGI, date(2029, 3, 10)),  # 86 anni: 2
        (DOC_CARTA_IDENTITA, date(2025, 1, 1), OGGI, date(2030, 1, 1)),  # 1 anno: 3
        (DOC_CARTA_IDENTITA, date(2023, 9, 14), OGGI, date(2032, 9, 14)),  # 3 anni: 5
        (DOC_CARTA_IDENTITA, date(2009, 1, 1), OGGI, date(2032, 1, 1)),  # 17 anni: 5
        (DOC_CARTA_IDENTITA, date(2008, 1, 1), OGGI, date(2036, 1, 1)),  # 18 anni: 9+
        (DOC_CARTA_IDENTITA, date(1957, 1, 1), OGGI, date(2036, 1, 1)),  # 69 anni
        (DOC_CARTA_IDENTITA, date(1956, 1, 1), date(2026, 7, 29), date(2036, 1, 1)),
        (DOC_CARTA_IDENTITA, date(1990, 5, 8), date(2026, 5, 8), date(2036, 5, 8)),
        (DOC_PASSAPORTO, date(2025, 1, 1), OGGI, date(2029, 9, 14)),
        (DOC_PASSAPORTO, date(2015, 1, 1), OGGI, date(2031, 9, 14)),
        (DOC_PASSAPORTO, date(1990, 5, 8), OGGI, date(2036, 9, 14)),
    ],
)
def test_scadenza_documento(
    documento: str, nascita: date, emissione: date, attesa: date
) -> None:
    assert scadenza_documento(documento, nascita, emissione) == attesa


def test_carta_identita_illimitata_dai_70_anni() -> None:
    assert scadenza_documento(DOC_CARTA_IDENTITA, date(1956, 1, 1), OGGI) is None


def test_documento_sconosciuto() -> None:
    with pytest.raises(DatiNonValidi):
        scadenza_documento("tessera", date(1990, 1, 1), OGGI)


def test_rinnovo_documento_usa_la_data_di_nascita() -> None:
    persona = Voce(tipo="persona", nome="Mario", data_nascita=date(1977, 1, 1))
    patente = crea(
        modello="patente", regola=REGOLA_DOCUMENTO, documento=DOC_PATENTE, scadenza=date(2026, 10, 1)
    )
    assert rinnova(patente, persona, OGGI, None).scadenza == date(2037, 1, 1)
    with pytest.raises(DatiNonValidi):
        rinnova(patente, VEICOLO, OGGI, None)


# --- Gomme -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("riferimento", "strettamente_dopo", "attesa"),
    [
        (date(2026, 9, 14), False, date(2026, 11, 15)),
        (date(2026, 11, 15), False, date(2026, 11, 15)),
        (date(2026, 11, 15), True, date(2027, 5, 15)),
        (date(2026, 12, 1), True, date(2027, 5, 15)),
        (date(2026, 3, 1), True, date(2026, 5, 15)),
    ],
)
def test_data_gomme_da(riferimento: date, strettamente_dopo: bool, attesa: date) -> None:
    assert data_gomme_da(riferimento, strettamente_dopo=strettamente_dopo) == attesa


@pytest.mark.parametrize(
    ("giorno_rinnovo", "attesa"),
    [
        (date(2026, 10, 20), date(2027, 5, 15)),  # in anticipo
        (date(2026, 11, 20), date(2027, 5, 15)),  # in ritardo
        (date(2027, 6, 1), date(2027, 11, 15)),  # una stagione saltata
    ],
)
def test_rinnovo_gomme(giorno_rinnovo: date, attesa: date) -> None:
    gomme = crea(modello=M_GOMME, regola=REGOLA_STAGIONALE, scadenza=date(2026, 11, 15))
    assert rinnova(gomme, VEICOLO, giorno_rinnovo, None).scadenza == attesa


def test_azione_gomme() -> None:
    assert azione_gomme(date(2026, 11, 15)) == "monta_invernali"
    assert azione_gomme(date(2027, 5, 15)) == "smonta_invernali"


# --- Unica e doppio rinnovo ------------------------------------------------


def test_rinnovo_unica_completa() -> None:
    nuova = rinnova(crea(), VEICOLO, OGGI, None)
    assert nuova.completata is True
    assert nuova.scadenza is None


def test_doppio_rinnovo_nello_stesso_giorno() -> None:
    with pytest.raises(RinnovoIgnorato):
        rinnova(crea(ultimo_rinnovo=OGGI), VEICOLO, OGGI, None)


# --- Stato -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("giorni", "atteso"),
    [(31, STATO_OK), (30, STATO_IN_SCADENZA), (0, STATO_IN_SCADENZA), (-1, STATO_SCADUTA)],
)
def test_stato_per_data(giorni: int, atteso: str) -> None:
    stato = calcola_stato(
        crea(scadenza=OGGI + timedelta(days=giorni)), OGGI, PREAVVISI, None, km_configurati=False
    )
    assert (stato.stato, stato.giorni_mancanti) == (atteso, giorni)


def test_senza_preavvisi_la_finestra_e_di_30_giorni() -> None:
    a_30 = crea(scadenza=OGGI + timedelta(days=30))
    a_31 = crea(scadenza=OGGI + timedelta(days=31))
    assert calcola_stato(a_30, OGGI, [], None, km_configurati=False).stato == STATO_IN_SCADENZA
    assert calcola_stato(a_31, OGGI, [], None, km_configurati=False).stato == STATO_OK


def test_stati_completata_e_illimitata() -> None:
    completata = crea(scadenza=None, completata=True)
    illimitata = crea(regola=REGOLA_DOCUMENTO, documento=DOC_CARTA_IDENTITA, scadenza=None)
    assert calcola_stato(completata, OGGI, PREAVVISI, None, km_configurati=False).stato == STATO_COMPLETATA
    assert calcola_stato(illimitata, OGGI, PREAVVISI, None, km_configurati=False).stato == STATO_ILLIMITATA


@pytest.mark.parametrize(
    ("km", "atteso", "mancanti"),
    [
        (30000, STATO_OK, 5000),
        (34500, STATO_IN_SCADENZA, 500),
        (35200, STATO_SCADUTA, -200),
    ],
)
def test_stato_per_km(km: int, atteso: str, mancanti: int) -> None:
    stato = calcola_stato(tagliando(), OGGI, PREAVVISI, km, km_configurati=True)
    assert (stato.stato, stato.km_scadenza, stato.km_mancanti) == (atteso, 35000, mancanti)


def test_la_data_puo_scadere_prima_dei_km() -> None:
    stato = calcola_stato(
        tagliando(OGGI - timedelta(days=1)), OGGI, PREAVVISI, 25000, km_configurati=True
    )
    assert stato.stato == STATO_SCADUTA
    assert stato.km_mancanti == 10000


def test_km_non_disponibili() -> None:
    stato = calcola_stato(tagliando(), OGGI, PREAVVISI, None, km_configurati=True)
    assert stato.km_non_disponibili is True
    assert stato.km_mancanti is None
    assert stato.stato == STATO_OK


def test_km_non_configurati() -> None:
    stato = calcola_stato(tagliando(), OGGI, PREAVVISI, 34500, km_configurati=False)
    assert stato.km_scadenza is None
    assert stato.km_non_disponibili is False
    assert stato.stato == STATO_OK


# --- Attributi -------------------------------------------------------------


def test_attributi_extra() -> None:
    bollo = crea(
        modello=M_BOLLO,
        regola=REGOLA_FINE_MESE,
        scadenza=date(2026, 10, 31),
        mese_scadenza_bollo=date(2026, 9, 1),
    )
    assicurazione = crea(
        modello=M_ASSICURAZIONE,
        regola=REGOLA_INTERVALLO,
        intervallo_mesi=12,
        ancora=ANCORA_SCADENZA,
        scadenza=date(2026, 10, 2),
    )
    gomme = crea(modello=M_GOMME, regola=REGOLA_STAGIONALE, scadenza=date(2026, 11, 15))
    revisione = crea(modello=M_REVISIONE, regola=REGOLA_FINE_MESE)

    assert attributi_extra(bollo) == {
        "mese_scadenza_bollo": "2026-09-01",
        "da_pagare_entro": "2026-10-31",
    }
    assert attributi_extra(assicurazione) == {"fine_tolleranza": "2026-10-17"}
    assert attributi_extra(gomme) == {"azione": "monta_invernali"}
    assert attributi_extra(revisione) == {}
```

- [ ] **Step 2: Eseguire i test e verificare che falliscono**

Run: `pytest tests/logica/test_regole.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'custom_components.scadenze.regole'`

- [ ] **Step 3: Implementare**

`custom_components/scadenze/regole.py`:

```python
"""Regole di calcolo delle scadenze italiane (spec §5).

Modulo di logica pura: non importa Home Assistant.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import date, timedelta

from .const import FINESTRA_SENZA_PREAVVISI, SOGLIA_KM, TOLLERANZA_ASSICURAZIONE_GIORNI
from .date_utils import aggiungi_mesi, compleanno_dopo, eta, fine_mese
from .modello_dati import (
    ANCORA_SCADENZA,
    DOC_CARTA_IDENTITA,
    DOC_PASSAPORTO,
    DOC_PATENTE,
    M_ASSICURAZIONE,
    REGOLA_DOCUMENTO,
    REGOLA_FINE_MESE,
    REGOLA_INTERVALLO,
    REGOLA_STAGIONALE,
    REGOLA_UNICA,
    STATO_COMPLETATA,
    STATO_ILLIMITATA,
    STATO_IN_SCADENZA,
    STATO_OK,
    STATO_SCADUTA,
    DatiNonValidi,
    Scadenza,
    Stato,
    Voce,
)

DATA_CIE_ILLIMITATA = date(2026, 7, 30)
MESI_PRIMA_REVISIONE = 48
MESI_REVISIONE = 24
AZIONE_MONTA = "monta_invernali"
AZIONE_SMONTA = "smonta_invernali"

# Date fisse del cambio gomme, in ordine di calendario: (mese, giorno)
_DATE_GOMME = ((5, 15), (11, 15))


class RinnovoIgnorato(Exception):
    """La scadenza è già stata rinnovata oggi."""


def prima_revisione(immatricolazione: date) -> date:
    """Fine del mese, quattro anni dopo l'immatricolazione."""
    return fine_mese(aggiungi_mesi(immatricolazione, MESI_PRIMA_REVISIONE))


def prossima_revisione_da_immatricolazione(immatricolazione: date, oggi: date) -> date:
    """La prima revisione da oggi in poi, ipotizzando revisioni sempre nel mese giusto."""
    data = prima_revisione(immatricolazione)
    while data < oggi:
        data = fine_mese(aggiungi_mesi(data, MESI_REVISIONE))
    return data


def pagamento_bollo(mese_scadenza: date) -> date:
    """Il bollo si paga entro l'ultimo giorno del mese successivo alla scadenza."""
    return fine_mese(aggiungi_mesi(mese_scadenza.replace(day=1), 1))


def mese_scadenza_bollo_suggerito(immatricolazione: date, oggi: date) -> date:
    """Il bollo scade nel mese prima di quello di immatricolazione: il primo ancora da pagare."""
    mese = aggiungi_mesi(immatricolazione.replace(day=1), -1).month
    candidato = date(oggi.year - 1, mese, 1)
    while pagamento_bollo(candidato) < oggi:
        candidato = aggiungi_mesi(candidato, 12)
    return candidato


def data_gomme_da(riferimento: date, *, strettamente_dopo: bool) -> date:
    """La prima data fissa del cambio gomme dopo (o da) `riferimento`."""
    for anno in (riferimento.year, riferimento.year + 1):
        for mese, giorno in _DATE_GOMME:
            candidato = date(anno, mese, giorno)
            if candidato > riferimento or (not strettamente_dopo and candidato == riferimento):
                return candidato
    raise AssertionError("una delle due date dell'anno successivo è sempre futura")


def azione_gomme(giorno: date) -> str:
    """A novembre si montano le invernali, a maggio si smontano."""
    return AZIONE_MONTA if giorno.month == 11 else AZIONE_SMONTA


def scadenza_documento(documento: str, nascita: date, emissione: date) -> date | None:
    """La scadenza di un documento emesso in `emissione` (tabella §5.4). `None` = illimitata."""
    anni = eta(nascita, emissione)
    if documento == DOC_PATENTE:
        validita = 10 if anni < 50 else 5 if anni < 70 else 3 if anni < 80 else 2
        return compleanno_dopo(nascita, aggiungi_mesi(emissione, 12 * validita))
    if documento == DOC_CARTA_IDENTITA:
        if anni >= 70 and emissione >= DATA_CIE_ILLIMITATA:
            return None
        validita = 3 if anni < 3 else 5 if anni < 18 else 9
        return compleanno_dopo(nascita, aggiungi_mesi(emissione, 12 * validita))
    if documento == DOC_PASSAPORTO:
        validita = 3 if anni < 3 else 5 if anni < 18 else 10
        return aggiungi_mesi(emissione, 12 * validita)
    raise DatiNonValidi(f"documento sconosciuto: {documento!r}")


def rinnova(
    scadenza: Scadenza, voce: Voce, oggi: date, km_attuali: int | None
) -> Scadenza:
    """La scadenza dopo un rinnovo fatto `oggi`."""
    if scadenza.ultimo_rinnovo == oggi:
        raise RinnovoIgnorato(scadenza.nome)

    if scadenza.regola == REGOLA_FINE_MESE:
        if scadenza.mese_scadenza_bollo is not None:
            mese = aggiungi_mesi(scadenza.mese_scadenza_bollo, 12)
            return replace(
                scadenza,
                mese_scadenza_bollo=mese,
                scadenza=pagamento_bollo(mese),
                ultimo_rinnovo=oggi,
            )
        return replace(
            scadenza,
            scadenza=fine_mese(aggiungi_mesi(oggi, MESI_REVISIONE)),
            ultimo_rinnovo=oggi,
        )

    if scadenza.regola == REGOLA_INTERVALLO:
        if not scadenza.intervallo_mesi:
            raise DatiNonValidi("intervallo_mesi mancante")
        base = (
            scadenza.scadenza
            if scadenza.ancora == ANCORA_SCADENZA and scadenza.scadenza is not None
            else oggi
        )
        km = scadenza.km_ultimo_rinnovo
        if scadenza.usa_km and km_attuali is not None:
            km = km_attuali
        return replace(
            scadenza,
            scadenza=aggiungi_mesi(base, scadenza.intervallo_mesi),
            ultimo_rinnovo=oggi,
            km_ultimo_rinnovo=km,
        )

    if scadenza.regola == REGOLA_DOCUMENTO:
        if voce.data_nascita is None:
            raise DatiNonValidi("data di nascita mancante")
        return replace(
            scadenza,
            scadenza=scadenza_documento(scadenza.documento or "", voce.data_nascita, oggi),
            ultimo_rinnovo=oggi,
        )

    if scadenza.regola == REGOLA_STAGIONALE:
        nuova = data_gomme_da(scadenza.scadenza or oggi, strettamente_dopo=True)
        while nuova <= oggi:
            nuova = data_gomme_da(nuova, strettamente_dopo=True)
        return replace(scadenza, scadenza=nuova, ultimo_rinnovo=oggi)

    if scadenza.regola == REGOLA_UNICA:
        return replace(scadenza, scadenza=None, completata=True, ultimo_rinnovo=oggi)

    raise DatiNonValidi(f"regola sconosciuta: {scadenza.regola!r}")


def calcola_stato(
    scadenza: Scadenza,
    oggi: date,
    preavvisi: Sequence[int],
    km_attuali: int | None,
    *,
    km_configurati: bool,
) -> Stato:
    """Lo stato di una scadenza in un giorno, con i km se il contachilometri è configurato."""
    if scadenza.completata:
        return Stato(STATO_COMPLETATA)
    if scadenza.scadenza is None:
        return Stato(STATO_ILLIMITATA)

    giorni = (scadenza.scadenza - oggi).days
    km_scadenza: int | None = None
    km_mancanti: int | None = None
    km_non_disponibili = False
    if scadenza.usa_km and km_configurati and scadenza.km_ultimo_rinnovo is not None:
        km_scadenza = scadenza.km_ultimo_rinnovo + (scadenza.intervallo_km or 0)
        if km_attuali is None:
            km_non_disponibili = True
        else:
            km_mancanti = km_scadenza - km_attuali

    finestra = max(preavvisi) if preavvisi else FINESTRA_SENZA_PREAVVISI
    if giorni < 0 or (km_mancanti is not None and km_mancanti <= 0):
        stato = STATO_SCADUTA
    elif giorni <= finestra or (km_mancanti is not None and km_mancanti <= SOGLIA_KM):
        stato = STATO_IN_SCADENZA
    else:
        stato = STATO_OK

    return Stato(stato, giorni, km_attuali, km_scadenza, km_mancanti, km_non_disponibili)


def attributi_extra(scadenza: Scadenza) -> dict[str, str]:
    """Attributi specifici del modello: pagamento del bollo, tolleranza, azione sulle gomme."""
    extra: dict[str, str] = {}
    if scadenza.mese_scadenza_bollo is not None:
        extra["mese_scadenza_bollo"] = scadenza.mese_scadenza_bollo.isoformat()
        if scadenza.scadenza is not None:
            extra["da_pagare_entro"] = scadenza.scadenza.isoformat()
    if scadenza.modello == M_ASSICURAZIONE and scadenza.scadenza is not None:
        fine = scadenza.scadenza + timedelta(days=TOLLERANZA_ASSICURAZIONE_GIORNI)
        extra["fine_tolleranza"] = fine.isoformat()
    if scadenza.regola == REGOLA_STAGIONALE and scadenza.scadenza is not None:
        extra["azione"] = azione_gomme(scadenza.scadenza)
    return extra
```

- [ ] **Step 4: Eseguire i test e verificare che passano**

Run: `pytest tests/logica/test_regole.py -q`
Expected: PASS (52 test)

- [ ] **Step 5: Commit**

```bash
git add custom_components/scadenze/regole.py tests/logica/test_regole.py
git commit -m "feat: regole di calcolo di revisione, bollo, documenti, gomme e stato"
```

### Task 4: Catalogo dei modelli e conversione dei form

**Files:**
- Create: `custom_components/scadenze/modelli.py`
- Test: `tests/logica/test_modelli.py`

**Interfaces:**
- Consumes: `const.TIPI_VOCE`, `const.TIPO_*` (Task 1); `date_utils.aggiungi_mesi`, `date_utils.fine_mese` (Task 1); `modello_dati.*` (Task 2); `regole.data_gomme_da`, `regole.mese_scadenza_bollo_suggerito`, `regole.pagamento_bollo`, `regole.prossima_revisione_da_immatricolazione` (Task 3).
- Produces (`modelli.py`):
  - campi `CAMPO_MODELLO = "modello"`, `CAMPO_NOME`, `CAMPO_SCADENZA`, `CAMPO_MESE_SCADENZA_BOLLO`, `CAMPO_ULTIMO_RINNOVO`, `CAMPO_INTERVALLO_MESI`, `CAMPO_KM_ULTIMO_RINNOVO`, `CAMPO_INTERVALLO_KM`, `CAMPO_RICORRENZA`; `CAMPI_NOTI`;
  - `RICORRENZA_NESSUNA`, `RICORRENZA_DALLA_SCADENZA`, `RICORRENZA_DAL_RINNOVO`, `RICORRENZE`;
  - `@dataclass(frozen=True) class Modello(chiave, etichetta, icona, tipi_voce, regola, campi, intervallo_mesi=None, ancora=ANCORA_RINNOVO, intervallo_km=None, documento=None)`;
  - `MODELLI: dict[str, Modello]` (16 voci, ordine della spec §6);
  - `class ErroreForm(ValueError)` con attributi `campo: str`, `codice: str`;
  - `modelli_per_tipo(tipo_voce: str) -> list[str]`;
  - `valori_suggeriti(chiave: str, voce: Voce, oggi: date) -> dict[str, Any]`;
  - `costruisci_scadenza(chiave: str, dati: Mapping[str, Any], voce: Voce, oggi: date) -> Scadenza` (solleva `ErroreForm`);
  - `valori_da_scadenza(scadenza: Scadenza) -> dict[str, Any]`.

- [ ] **Step 1: Scrivere i test che falliscono**

`tests/logica/test_modelli.py`:

```python
"""Test del catalogo dei modelli e dei form (spec §6 e §7.3)."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from custom_components.scadenze.modelli import (
    CAMPI_NOTI,
    MODELLI,
    ErroreForm,
    costruisci_scadenza,
    modelli_per_tipo,
    valori_da_scadenza,
    valori_suggeriti,
)
from custom_components.scadenze.modello_dati import (
    ANCORA_RINNOVO,
    ANCORA_SCADENZA,
    DOC_PATENTE,
    REGOLA_DOCUMENTO,
    REGOLA_FINE_MESE,
    REGOLA_INTERVALLO,
    REGOLA_UNICA,
    Voce,
)

OGGI = date(2026, 9, 14)
VEICOLO = Voce(tipo="veicolo", nome="Panda", tipo_veicolo="auto", immatricolazione=date(2022, 5, 1))
CASA = Voce(tipo="casa", nome="Casa")
PERSONA = Voce(tipo="persona", nome="Mario", data_nascita=date(1990, 5, 8))


def test_catalogo_completo_e_campi_noti() -> None:
    assert len(MODELLI) == 16
    for chiave, modello in MODELLI.items():
        assert modello.chiave == chiave
        assert set(modello.campi) <= CAMPI_NOTI
        assert modello.icona.startswith("mdi:")


def test_modelli_per_tipo() -> None:
    assert modelli_per_tipo("veicolo") == [
        "revisione", "bollo", "assicurazione", "tagliando", "gomme", "personalizzata",
    ]
    assert modelli_per_tipo("casa") == [
        "manutenzione_caldaia", "controllo_fumi", "climatizzatore",
        "estintore", "filtri_acqua", "canna_fumaria", "personalizzata",
    ]
    assert modelli_per_tipo("persona") == [
        "carta_identita", "patente", "passaporto", "tessera_sanitaria", "personalizzata",
    ]
    assert modelli_per_tipo("generica") == ["personalizzata"]


@pytest.mark.parametrize(
    ("chiave", "voce", "attesi"),
    [
        ("revisione", VEICOLO, {"nome": "Revisione", "scadenza": "2028-05-31"}),
        ("bollo", VEICOLO, {"nome": "Bollo", "mese_scadenza_bollo": "2027-04-01"}),
        ("gomme", VEICOLO, {"nome": "Cambio gomme", "scadenza": "2026-11-15"}),
        ("assicurazione", VEICOLO, {"nome": "Assicurazione", "intervallo_mesi": 12}),
        (
            "tagliando",
            VEICOLO,
            {
                "nome": "Tagliando",
                "ultimo_rinnovo": "2026-09-14",
                "km_ultimo_rinnovo": 0,
                "intervallo_mesi": 12,
                "intervallo_km": 15000,
            },
        ),
        (
            "controllo_fumi",
            CASA,
            {"nome": "Controllo fumi caldaia", "ultimo_rinnovo": "2026-09-14", "intervallo_mesi": 48},
        ),
        ("patente", PERSONA, {"nome": "Patente"}),
        (
            "personalizzata",
            CASA,
            {"nome": "Personalizzata", "ricorrenza": "nessuna", "intervallo_mesi": 12},
        ),
    ],
)
def test_valori_suggeriti(chiave: str, voce: Voce, attesi: dict[str, Any]) -> None:
    assert valori_suggeriti(chiave, voce, OGGI) == attesi


def test_revisione_a_fine_mese() -> None:
    scadenza = costruisci_scadenza("revisione", {"nome": "Revisione", "scadenza": "2028-05-10"}, VEICOLO, OGGI)
    assert (scadenza.regola, scadenza.scadenza) == (REGOLA_FINE_MESE, date(2028, 5, 31))


def test_bollo_dal_mese_di_scadenza() -> None:
    scadenza = costruisci_scadenza("bollo", {"nome": "Bollo", "mese_scadenza_bollo": "2027-04-18"}, VEICOLO, OGGI)
    assert scadenza.mese_scadenza_bollo == date(2027, 4, 1)
    assert scadenza.scadenza == date(2027, 5, 31)


def test_tagliando_con_km() -> None:
    scadenza = costruisci_scadenza(
        "tagliando",
        {
            "nome": "Tagliando",
            "ultimo_rinnovo": "2026-03-01",
            "km_ultimo_rinnovo": 20000.0,
            "intervallo_mesi": 12.0,
            "intervallo_km": 15000.0,
        },
        VEICOLO,
        OGGI,
    )
    assert scadenza.scadenza == date(2027, 3, 1)
    assert (scadenza.km_ultimo_rinnovo, scadenza.intervallo_km) == (20000, 15000)
    assert (scadenza.regola, scadenza.ancora) == (REGOLA_INTERVALLO, ANCORA_RINNOVO)


def test_tessera_sanitaria_senza_campo_intervallo() -> None:
    scadenza = costruisci_scadenza(
        "tessera_sanitaria", {"nome": "Tessera sanitaria", "scadenza": "2030-01-31"}, PERSONA, OGGI
    )
    assert (scadenza.intervallo_mesi, scadenza.ancora) == (72, ANCORA_SCADENZA)


def test_documento() -> None:
    scadenza = costruisci_scadenza("patente", {"nome": "Patente", "scadenza": "2031-05-08"}, PERSONA, OGGI)
    assert (scadenza.regola, scadenza.documento) == (REGOLA_DOCUMENTO, DOC_PATENTE)


@pytest.mark.parametrize(
    ("ricorrenza", "regola", "ancora"),
    [
        ("nessuna", REGOLA_UNICA, ANCORA_RINNOVO),
        ("dalla_scadenza", REGOLA_INTERVALLO, ANCORA_SCADENZA),
        ("dal_rinnovo", REGOLA_INTERVALLO, ANCORA_RINNOVO),
    ],
)
def test_personalizzata(ricorrenza: str, regola: str, ancora: str) -> None:
    scadenza = costruisci_scadenza(
        "personalizzata",
        {"nome": "Abbonamento", "scadenza": "2027-01-31", "ricorrenza": ricorrenza, "intervallo_mesi": 6},
        CASA,
        OGGI,
    )
    assert (scadenza.regola, scadenza.ancora) == (regola, ancora)


@pytest.mark.parametrize(
    ("chiave", "voce", "dati", "campo", "codice"),
    [
        ("revisione", VEICOLO, {"nome": "  ", "scadenza": "2028-05-31"}, "nome", "campo_obbligatorio"),
        ("revisione", VEICOLO, {"nome": "Revisione"}, "scadenza", "campo_obbligatorio"),
        ("revisione", VEICOLO, {"nome": "Revisione", "scadenza": "31/05/2028"}, "scadenza", "data_non_valida"),
        (
            "tagliando",
            VEICOLO,
            {"nome": "Tagliando", "ultimo_rinnovo": "2026-09-15", "km_ultimo_rinnovo": 0, "intervallo_mesi": 12, "intervallo_km": 15000},
            "ultimo_rinnovo",
            "data_futura",
        ),
        (
            "manutenzione_caldaia",
            CASA,
            {"nome": "Caldaia", "ultimo_rinnovo": "2026-01-10", "intervallo_mesi": 0},
            "intervallo_mesi",
            "intervallo_non_valido",
        ),
        ("patente", PERSONA, {"nome": "Patente", "scadenza": "1980-01-01"}, "scadenza", "scadenza_prima_della_nascita"),
    ],
)
def test_errori_del_form(
    chiave: str, voce: Voce, dati: dict[str, Any], campo: str, codice: str
) -> None:
    with pytest.raises(ErroreForm) as errore:
        costruisci_scadenza(chiave, dati, voce, OGGI)
    assert (errore.value.campo, errore.value.codice) == (campo, codice)


@pytest.mark.parametrize(
    ("chiave", "voce", "form"),
    [
        (
            "tagliando",
            VEICOLO,
            {"nome": "Tagliando", "ultimo_rinnovo": "2026-03-01", "km_ultimo_rinnovo": 20000, "intervallo_mesi": 12, "intervallo_km": 15000},
        ),
        ("bollo", VEICOLO, {"nome": "Bollo", "mese_scadenza_bollo": "2027-04-01"}),
        ("assicurazione", VEICOLO, {"nome": "RC auto", "scadenza": "2026-10-02", "intervallo_mesi": 12}),
        (
            "personalizzata",
            CASA,
            {"nome": "Abbonamento", "scadenza": "2027-01-31", "ricorrenza": "dal_rinnovo", "intervallo_mesi": 6},
        ),
        ("patente", PERSONA, {"nome": "Patente", "scadenza": "2031-05-08"}),
    ],
)
def test_valori_da_scadenza_ricostruiscono_la_scadenza(
    chiave: str, voce: Voce, form: dict[str, Any]
) -> None:
    scadenza = costruisci_scadenza(chiave, form, voce, OGGI)
    assert costruisci_scadenza(chiave, valori_da_scadenza(scadenza), voce, OGGI) == scadenza
```

- [ ] **Step 2: Eseguire i test e verificare che falliscono**

Run: `pytest tests/logica/test_modelli.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'custom_components.scadenze.modelli'`

- [ ] **Step 3: Implementare**

`custom_components/scadenze/modelli.py`:

```python
"""Catalogo dei modelli di scadenza e conversione dei form (spec §6).

Modulo di logica pura: non importa Home Assistant.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any, Final

from .const import TIPI_VOCE, TIPO_CASA, TIPO_PERSONA, TIPO_VEICOLO
from .date_utils import aggiungi_mesi, fine_mese
from .modello_dati import (
    ANCORA_RINNOVO,
    ANCORA_SCADENZA,
    DOC_CARTA_IDENTITA,
    DOC_PASSAPORTO,
    DOC_PATENTE,
    M_ASSICURAZIONE,
    M_BOLLO,
    M_CANNA_FUMARIA,
    M_CARTA_IDENTITA,
    M_CLIMATIZZATORE,
    M_CONTROLLO_FUMI,
    M_ESTINTORE,
    M_FILTRI_ACQUA,
    M_GOMME,
    M_MANUTENZIONE_CALDAIA,
    M_PASSAPORTO,
    M_PATENTE,
    M_PERSONALIZZATA,
    M_REVISIONE,
    M_TAGLIANDO,
    M_TESSERA_SANITARIA,
    REGOLA_DOCUMENTO,
    REGOLA_FINE_MESE,
    REGOLA_INTERVALLO,
    REGOLA_STAGIONALE,
    REGOLA_UNICA,
    DatiNonValidi,
    Scadenza,
    Voce,
    leggi_data,
    leggi_intero,
)
from .regole import (
    data_gomme_da,
    mese_scadenza_bollo_suggerito,
    pagamento_bollo,
    prossima_revisione_da_immatricolazione,
)

CAMPO_MODELLO: Final = "modello"
CAMPO_NOME: Final = "nome"
CAMPO_SCADENZA: Final = "scadenza"
CAMPO_MESE_SCADENZA_BOLLO: Final = "mese_scadenza_bollo"
CAMPO_ULTIMO_RINNOVO: Final = "ultimo_rinnovo"
CAMPO_INTERVALLO_MESI: Final = "intervallo_mesi"
CAMPO_KM_ULTIMO_RINNOVO: Final = "km_ultimo_rinnovo"
CAMPO_INTERVALLO_KM: Final = "intervallo_km"
CAMPO_RICORRENZA: Final = "ricorrenza"
CAMPI_NOTI: Final = frozenset(
    {
        CAMPO_SCADENZA,
        CAMPO_MESE_SCADENZA_BOLLO,
        CAMPO_ULTIMO_RINNOVO,
        CAMPO_INTERVALLO_MESI,
        CAMPO_KM_ULTIMO_RINNOVO,
        CAMPO_INTERVALLO_KM,
        CAMPO_RICORRENZA,
    }
)

RICORRENZA_NESSUNA: Final = "nessuna"
RICORRENZA_DALLA_SCADENZA: Final = "dalla_scadenza"
RICORRENZA_DAL_RINNOVO: Final = "dal_rinnovo"
RICORRENZE: Final = (RICORRENZA_NESSUNA, RICORRENZA_DALLA_SCADENZA, RICORRENZA_DAL_RINNOVO)


@dataclass(frozen=True)
class Modello:
    """Un tipo di scadenza: regola, valori predefiniti e campi del form."""

    chiave: str
    etichetta: str
    icona: str
    tipi_voce: tuple[str, ...]
    regola: str
    campi: tuple[str, ...]
    intervallo_mesi: int | None = None
    ancora: str = ANCORA_RINNOVO
    intervallo_km: int | None = None
    documento: str | None = None


_CAMPI_CASA = (CAMPO_ULTIMO_RINNOVO, CAMPO_INTERVALLO_MESI)

MODELLI: Final[dict[str, Modello]] = {
    modello.chiave: modello
    for modello in (
        Modello(M_REVISIONE, "Revisione", "mdi:car-wrench", (TIPO_VEICOLO,), REGOLA_FINE_MESE, (CAMPO_SCADENZA,)),
        Modello(M_BOLLO, "Bollo", "mdi:cash-multiple", (TIPO_VEICOLO,), REGOLA_FINE_MESE, (CAMPO_MESE_SCADENZA_BOLLO,)),
        Modello(
            M_ASSICURAZIONE, "Assicurazione", "mdi:shield-car", (TIPO_VEICOLO,), REGOLA_INTERVALLO,
            (CAMPO_SCADENZA, CAMPO_INTERVALLO_MESI), intervallo_mesi=12, ancora=ANCORA_SCADENZA,
        ),
        Modello(
            M_TAGLIANDO, "Tagliando", "mdi:oil", (TIPO_VEICOLO,), REGOLA_INTERVALLO,
            (CAMPO_ULTIMO_RINNOVO, CAMPO_KM_ULTIMO_RINNOVO, CAMPO_INTERVALLO_MESI, CAMPO_INTERVALLO_KM),
            intervallo_mesi=12, intervallo_km=15000,
        ),
        Modello(M_GOMME, "Cambio gomme", "mdi:snowflake", (TIPO_VEICOLO,), REGOLA_STAGIONALE, (CAMPO_SCADENZA,)),
        Modello(M_MANUTENZIONE_CALDAIA, "Manutenzione caldaia", "mdi:water-boiler", (TIPO_CASA,), REGOLA_INTERVALLO, _CAMPI_CASA, intervallo_mesi=12),
        Modello(M_CONTROLLO_FUMI, "Controllo fumi caldaia", "mdi:smoke", (TIPO_CASA,), REGOLA_INTERVALLO, _CAMPI_CASA, intervallo_mesi=48),
        Modello(M_CLIMATIZZATORE, "Pulizia climatizzatore", "mdi:air-conditioner", (TIPO_CASA,), REGOLA_INTERVALLO, _CAMPI_CASA, intervallo_mesi=12),
        Modello(M_ESTINTORE, "Controllo estintore", "mdi:fire-extinguisher", (TIPO_CASA,), REGOLA_INTERVALLO, _CAMPI_CASA, intervallo_mesi=6),
        Modello(M_FILTRI_ACQUA, "Cambio filtri acqua", "mdi:water-check", (TIPO_CASA,), REGOLA_INTERVALLO, _CAMPI_CASA, intervallo_mesi=6),
        Modello(M_CANNA_FUMARIA, "Pulizia canna fumaria", "mdi:fireplace", (TIPO_CASA,), REGOLA_INTERVALLO, _CAMPI_CASA, intervallo_mesi=12),
        Modello(M_CARTA_IDENTITA, "Carta d'identità", "mdi:card-account-details", (TIPO_PERSONA,), REGOLA_DOCUMENTO, (CAMPO_SCADENZA,), documento=DOC_CARTA_IDENTITA),
        Modello(M_PATENTE, "Patente", "mdi:card-account-details-outline", (TIPO_PERSONA,), REGOLA_DOCUMENTO, (CAMPO_SCADENZA,), documento=DOC_PATENTE),
        Modello(M_PASSAPORTO, "Passaporto", "mdi:passport", (TIPO_PERSONA,), REGOLA_DOCUMENTO, (CAMPO_SCADENZA,), documento=DOC_PASSAPORTO),
        Modello(
            M_TESSERA_SANITARIA, "Tessera sanitaria", "mdi:card-plus", (TIPO_PERSONA,), REGOLA_INTERVALLO,
            (CAMPO_SCADENZA,), intervallo_mesi=72, ancora=ANCORA_SCADENZA,
        ),
        Modello(
            M_PERSONALIZZATA, "Personalizzata", "mdi:calendar-clock", TIPI_VOCE, REGOLA_UNICA,
            (CAMPO_SCADENZA, CAMPO_RICORRENZA, CAMPO_INTERVALLO_MESI), intervallo_mesi=12,
        ),
    )
}


class ErroreForm(ValueError):
    """Un campo del form non è valido; `codice` è la chiave di traduzione dell'errore."""

    def __init__(self, campo: str, codice: str) -> None:
        super().__init__(f"{campo}: {codice}")
        self.campo = campo
        self.codice = codice


def _modello(chiave: str) -> Modello:
    try:
        return MODELLI[chiave]
    except KeyError as err:
        raise DatiNonValidi(f"modello sconosciuto: {chiave!r}") from err


def modelli_per_tipo(tipo_voce: str) -> list[str]:
    """Le chiavi dei modelli disponibili per un tipo di voce, nell'ordine del catalogo."""
    return [chiave for chiave, modello in MODELLI.items() if tipo_voce in modello.tipi_voce]


def valori_suggeriti(chiave: str, voce: Voce, oggi: date) -> dict[str, Any]:
    """I valori iniziali del form di una nuova scadenza, pronti per il selettore (date ISO)."""
    modello = _modello(chiave)
    valori: dict[str, Any] = {CAMPO_NOME: modello.etichetta}
    if chiave == M_REVISIONE and voce.immatricolazione is not None:
        valori[CAMPO_SCADENZA] = prossima_revisione_da_immatricolazione(voce.immatricolazione, oggi).isoformat()
    elif chiave == M_BOLLO and voce.immatricolazione is not None:
        valori[CAMPO_MESE_SCADENZA_BOLLO] = mese_scadenza_bollo_suggerito(voce.immatricolazione, oggi).isoformat()
    elif chiave == M_GOMME:
        valori[CAMPO_SCADENZA] = data_gomme_da(oggi, strettamente_dopo=False).isoformat()
    if CAMPO_ULTIMO_RINNOVO in modello.campi:
        valori[CAMPO_ULTIMO_RINNOVO] = oggi.isoformat()
    if CAMPO_INTERVALLO_MESI in modello.campi:
        valori[CAMPO_INTERVALLO_MESI] = modello.intervallo_mesi
    if CAMPO_KM_ULTIMO_RINNOVO in modello.campi:
        valori[CAMPO_KM_ULTIMO_RINNOVO] = 0
    if CAMPO_INTERVALLO_KM in modello.campi:
        valori[CAMPO_INTERVALLO_KM] = modello.intervallo_km
    if CAMPO_RICORRENZA in modello.campi:
        valori[CAMPO_RICORRENZA] = RICORRENZA_NESSUNA
    return valori


def _data_form(dati: Mapping[str, Any], campo: str, *, massima: date | None = None) -> date:
    valore = dati.get(campo)
    if valore is None or valore == "":
        raise ErroreForm(campo, "campo_obbligatorio")
    try:
        giorno = leggi_data(valore)
    except DatiNonValidi as err:
        raise ErroreForm(campo, "data_non_valida") from err
    assert giorno is not None
    if massima is not None and giorno > massima:
        raise ErroreForm(campo, "data_futura")
    return giorno


def _intero_form(dati: Mapping[str, Any], campo: str, minimo: int, massimo: int) -> int:
    valore = dati.get(campo)
    if valore is None or valore == "":
        raise ErroreForm(campo, "campo_obbligatorio")
    try:
        numero = leggi_intero(valore)
    except DatiNonValidi as err:
        raise ErroreForm(campo, "intervallo_non_valido") from err
    if numero is None or not minimo <= numero <= massimo:
        raise ErroreForm(campo, "intervallo_non_valido")
    return numero


def costruisci_scadenza(
    chiave: str, dati: Mapping[str, Any], voce: Voce, oggi: date
) -> Scadenza:
    """Converte i valori del form in una `Scadenza`, validandoli."""
    modello = _modello(chiave)
    nome = str(dati.get(CAMPO_NOME) or "").strip()
    if not nome:
        raise ErroreForm(CAMPO_NOME, "campo_obbligatorio")

    if modello.regola == REGOLA_FINE_MESE:
        if chiave == M_BOLLO:
            mese = _data_form(dati, CAMPO_MESE_SCADENZA_BOLLO).replace(day=1)
            return Scadenza(chiave, nome, REGOLA_FINE_MESE, pagamento_bollo(mese), mese_scadenza_bollo=mese)
        return Scadenza(chiave, nome, REGOLA_FINE_MESE, fine_mese(_data_form(dati, CAMPO_SCADENZA)))

    if modello.regola == REGOLA_STAGIONALE:
        return Scadenza(chiave, nome, REGOLA_STAGIONALE, _data_form(dati, CAMPO_SCADENZA))

    if modello.regola == REGOLA_DOCUMENTO:
        scadenza = _data_form(dati, CAMPO_SCADENZA)
        if voce.data_nascita is not None and scadenza <= voce.data_nascita:
            raise ErroreForm(CAMPO_SCADENZA, "scadenza_prima_della_nascita")
        return Scadenza(chiave, nome, REGOLA_DOCUMENTO, scadenza, documento=modello.documento)

    if chiave == M_PERSONALIZZATA:
        scadenza = _data_form(dati, CAMPO_SCADENZA)
        ricorrenza = dati.get(CAMPO_RICORRENZA) or RICORRENZA_NESSUNA
        if ricorrenza not in RICORRENZE:
            raise ErroreForm(CAMPO_RICORRENZA, "campo_obbligatorio")
        if ricorrenza == RICORRENZA_NESSUNA:
            return Scadenza(chiave, nome, REGOLA_UNICA, scadenza)
        return Scadenza(
            chiave,
            nome,
            REGOLA_INTERVALLO,
            scadenza,
            intervallo_mesi=_intero_form(dati, CAMPO_INTERVALLO_MESI, 1, 240),
            ancora=ANCORA_SCADENZA if ricorrenza == RICORRENZA_DALLA_SCADENZA else ANCORA_RINNOVO,
        )

    # Regola intervallo dei modelli predefiniti
    if CAMPO_INTERVALLO_MESI in modello.campi:
        mesi = _intero_form(dati, CAMPO_INTERVALLO_MESI, 1, 240)
    else:
        assert modello.intervallo_mesi is not None
        mesi = modello.intervallo_mesi

    if modello.ancora == ANCORA_SCADENZA:
        return Scadenza(
            chiave, nome, REGOLA_INTERVALLO, _data_form(dati, CAMPO_SCADENZA),
            intervallo_mesi=mesi, ancora=ANCORA_SCADENZA,
        )

    ultimo = _data_form(dati, CAMPO_ULTIMO_RINNOVO, massima=oggi)
    km_ultimo: int | None = None
    intervallo_km: int | None = None
    if CAMPO_INTERVALLO_KM in modello.campi:
        km_ultimo = _intero_form(dati, CAMPO_KM_ULTIMO_RINNOVO, 0, 2_000_000)
        intervallo_km = _intero_form(dati, CAMPO_INTERVALLO_KM, 0, 100_000)
    return Scadenza(
        chiave,
        nome,
        REGOLA_INTERVALLO,
        aggiungi_mesi(ultimo, mesi),
        ultimo_rinnovo=ultimo,
        intervallo_mesi=mesi,
        ancora=ANCORA_RINNOVO,
        intervallo_km=intervallo_km,
        km_ultimo_rinnovo=km_ultimo,
    )


def valori_da_scadenza(scadenza: Scadenza) -> dict[str, Any]:
    """I valori del form di riconfigurazione di una scadenza esistente."""
    modello = _modello(scadenza.modello)
    valori: dict[str, Any] = {CAMPO_NOME: scadenza.nome}
    if CAMPO_SCADENZA in modello.campi and scadenza.scadenza is not None:
        valori[CAMPO_SCADENZA] = scadenza.scadenza.isoformat()
    if CAMPO_MESE_SCADENZA_BOLLO in modello.campi and scadenza.mese_scadenza_bollo is not None:
        valori[CAMPO_MESE_SCADENZA_BOLLO] = scadenza.mese_scadenza_bollo.isoformat()
    if CAMPO_ULTIMO_RINNOVO in modello.campi and scadenza.ultimo_rinnovo is not None:
        valori[CAMPO_ULTIMO_RINNOVO] = scadenza.ultimo_rinnovo.isoformat()
    if CAMPO_INTERVALLO_MESI in modello.campi:
        valori[CAMPO_INTERVALLO_MESI] = scadenza.intervallo_mesi or modello.intervallo_mesi
    if CAMPO_KM_ULTIMO_RINNOVO in modello.campi:
        valori[CAMPO_KM_ULTIMO_RINNOVO] = scadenza.km_ultimo_rinnovo or 0
    if CAMPO_INTERVALLO_KM in modello.campi:
        valori[CAMPO_INTERVALLO_KM] = (
            scadenza.intervallo_km if scadenza.intervallo_km is not None else modello.intervallo_km
        )
    if CAMPO_RICORRENZA in modello.campi:
        if scadenza.regola == REGOLA_UNICA:
            valori[CAMPO_RICORRENZA] = RICORRENZA_NESSUNA
        elif scadenza.ancora == ANCORA_SCADENZA:
            valori[CAMPO_RICORRENZA] = RICORRENZA_DALLA_SCADENZA
        else:
            valori[CAMPO_RICORRENZA] = RICORRENZA_DAL_RINNOVO
    return valori
```

- [ ] **Step 4: Eseguire i test e verificare che passano**

Run: `pytest tests/logica/test_modelli.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/scadenze/modelli.py tests/logica/test_modelli.py
git commit -m "feat: catalogo dei modelli e conversione dei form"
```

### Task 5: Logica dei promemoria

**Files:**
- Create: `custom_components/scadenze/promemoria.py`
- Test: `tests/logica/test_promemoria.py`

**Interfaces:**
- Consumes: `const.SOGLIA_KM` (Task 1); `modello_dati.Scadenza`, `Stato`, `STATO_ILLIMITATA`, `STATO_COMPLETATA` (Task 2).
- Produces (`promemoria.py`):
  - `SOGLIA_OGGI = 0`, `SOGLIA_SCADUTA = -1`, `SOGLIA_KM_VICINI = "km"`, `SOGLIA_KM_SUPERATI = "km_superati"`, `MEMORIA_RIFERIMENTO = "riferimento"`, `MEMORIA_INVIATI = "inviati"`;
  - `@dataclass(frozen=True) class Promemoria(soglia: int | str, messaggio: str)`;
  - `@dataclass(frozen=True) class Esito(promemoria: Promemoria | None, memoria: dict[str, Any])`;
  - `class PreavvisiNonValidi(ValueError)`;
  - `analizza_preavvisi(testo: str) -> list[int]` (decrescente, senza doppioni, 1–365);
  - `formatta_preavvisi(preavvisi: Sequence[int]) -> str`;
  - `riferimento(scadenza: Scadenza, stato: Stato) -> str`;
  - `valuta(scadenza: Scadenza, stato: Stato, preavvisi: Sequence[int], memoria: Mapping[str, Any] | None) -> Esito`.

- [ ] **Step 1: Scrivere i test che falliscono**

`tests/logica/test_promemoria.py`:

```python
"""Test della scelta dei promemoria e della memoria anti-doppioni (spec §4.5 e §10.1)."""

from __future__ import annotations

from datetime import date

import pytest

from custom_components.scadenze.modello_dati import (
    REGOLA_DOCUMENTO,
    REGOLA_INTERVALLO,
    REGOLA_UNICA,
    STATO_ILLIMITATA,
    STATO_IN_SCADENZA,
    STATO_OK,
    STATO_SCADUTA,
    Scadenza,
    Stato,
)
from custom_components.scadenze.promemoria import (
    PreavvisiNonValidi,
    analizza_preavvisi,
    formatta_preavvisi,
    valuta,
)

PREAVVISI = [30, 7, 1]
REVISIONE = Scadenza("revisione", "Revisione", "fine_mese", date(2026, 9, 19))
TAGLIANDO = Scadenza(
    "tagliando",
    "Tagliando",
    REGOLA_INTERVALLO,
    date(2027, 3, 1),
    ultimo_rinnovo=date(2026, 3, 1),
    intervallo_mesi=12,
    intervallo_km=15000,
    km_ultimo_rinnovo=20000,
)


def stato_a(giorni: int) -> Stato:
    if giorni < 0:
        return Stato(STATO_SCADUTA, giorni)
    return Stato(STATO_IN_SCADENZA if giorni <= 30 else STATO_OK, giorni)


@pytest.mark.parametrize(
    ("testo", "attesi"),
    [("30, 7, 1", [30, 7, 1]), ("7;30;7", [30, 7]), ("", []), (" 1 ", [1])],
)
def test_analizza_preavvisi(testo: str, attesi: list[int]) -> None:
    assert analizza_preavvisi(testo) == attesi


@pytest.mark.parametrize("testo", ["0", "abc", "400", "7, -1"])
def test_preavvisi_non_validi(testo: str) -> None:
    with pytest.raises(PreavvisiNonValidi):
        analizza_preavvisi(testo)


def test_formatta_preavvisi() -> None:
    assert formatta_preavvisi([30, 7, 1]) == "30, 7, 1"


def test_creata_a_ridosso_manda_un_solo_promemoria() -> None:
    esito = valuta(REVISIONE, stato_a(5), PREAVVISI, None)
    assert esito.promemoria is not None
    assert esito.promemoria.soglia == 7
    assert esito.promemoria.messaggio == "Scade tra 5 giorni (19/09/2026)."
    assert esito.memoria == {"riferimento": "2026-09-19|", "inviati": [30, 7]}


def test_nessun_doppione_con_la_stessa_memoria() -> None:
    primo = valuta(REVISIONE, stato_a(5), PREAVVISI, None)
    secondo = valuta(REVISIONE, stato_a(5), PREAVVISI, primo.memoria)
    assert secondo.promemoria is None
    assert secondo.memoria == primo.memoria


def test_sequenza_fino_alla_scadenza_superata() -> None:
    memoria = valuta(REVISIONE, stato_a(5), PREAVVISI, None).memoria

    domani = valuta(REVISIONE, stato_a(1), PREAVVISI, memoria)
    assert domani.promemoria is not None
    assert domani.promemoria.messaggio == "Scade domani (19/09/2026)."

    oggi = valuta(REVISIONE, stato_a(0), PREAVVISI, domani.memoria)
    assert oggi.promemoria is not None
    assert (oggi.promemoria.soglia, oggi.promemoria.messaggio) == (0, "Scade oggi.")

    scaduta = valuta(REVISIONE, stato_a(-3), PREAVVISI, oggi.memoria)
    assert scaduta.promemoria is not None
    assert (scaduta.promemoria.soglia, scaduta.promemoria.messaggio) == (-1, "Scaduta dal 19/09/2026.")
    assert scaduta.memoria["inviati"] == [30, 7, 1, 0, -1]

    assert valuta(REVISIONE, stato_a(-4), PREAVVISI, scaduta.memoria).promemoria is None


def test_la_memoria_si_azzera_quando_cambia_la_data() -> None:
    memoria = {"riferimento": "2026-09-19|", "inviati": [30, 7]}
    rinnovata = Scadenza("revisione", "Revisione", "fine_mese", date(2028, 9, 30))
    esito = valuta(rinnovata, stato_a(747), PREAVVISI, memoria)
    assert esito.promemoria is None
    assert esito.memoria == {"riferimento": "2028-09-30|", "inviati": []}


def test_promemoria_per_km() -> None:
    vicini = valuta(TAGLIANDO, Stato(STATO_IN_SCADENZA, 168, 34200, 35000, 800), PREAVVISI, None)
    assert vicini.promemoria is not None
    assert (vicini.promemoria.soglia, vicini.promemoria.messaggio) == ("km", "Mancano 800 km.")
    assert vicini.memoria == {"riferimento": "2027-03-01|35000", "inviati": ["km"]}

    superati = valuta(TAGLIANDO, Stato(STATO_SCADUTA, 168, 35200, 35000, -200), PREAVVISI, vicini.memoria)
    assert superati.promemoria is not None
    assert (superati.promemoria.soglia, superati.promemoria.messaggio) == (
        "km_superati",
        "Limite di 35.000 km raggiunto.",
    )


def test_nessun_promemoria_fuori_finestra_o_senza_data() -> None:
    assert valuta(REVISIONE, stato_a(45), PREAVVISI, None).promemoria is None
    illimitata = Scadenza("carta_identita", "Carta d'identità", REGOLA_DOCUMENTO, None, documento="carta_identita")
    assert valuta(illimitata, Stato(STATO_ILLIMITATA), PREAVVISI, None).promemoria is None
    completata = Scadenza("personalizzata", "Trasloco", REGOLA_UNICA, None, completata=True)
    assert valuta(completata, Stato("completata"), PREAVVISI, None).promemoria is None
```

- [ ] **Step 2: Eseguire i test e verificare che falliscono**

Run: `pytest tests/logica/test_promemoria.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'custom_components.scadenze.promemoria'`

- [ ] **Step 3: Implementare**

`custom_components/scadenze/promemoria.py`:

```python
"""Decide quali promemoria inviare, senza doppioni (spec §10.1).

Modulo di logica pura: non importa Home Assistant.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from .const import SOGLIA_KM
from .modello_dati import STATO_COMPLETATA, STATO_ILLIMITATA, Scadenza, Stato

SOGLIA_OGGI = 0
SOGLIA_SCADUTA = -1
SOGLIA_KM_VICINI = "km"
SOGLIA_KM_SUPERATI = "km_superati"

MEMORIA_RIFERIMENTO = "riferimento"
MEMORIA_INVIATI = "inviati"


@dataclass(frozen=True)
class Promemoria:
    """Un promemoria da inviare: la soglia che lo ha causato e il testo."""

    soglia: int | str
    messaggio: str


@dataclass(frozen=True)
class Esito:
    """Il promemoria da inviare (se c'è) e la memoria aggiornata della scadenza."""

    promemoria: Promemoria | None
    memoria: dict[str, Any]


class PreavvisiNonValidi(ValueError):
    """Il testo dei preavvisi contiene un valore che non è un intero fra 1 e 365."""


def analizza_preavvisi(testo: str) -> list[int]:
    """«30, 7, 1» → [30, 7, 1]; accetta anche il punto e virgola."""
    valori: set[int] = set()
    for parte in testo.replace(";", ",").split(","):
        parte = parte.strip()
        if not parte:
            continue
        try:
            numero = int(parte)
        except ValueError as err:
            raise PreavvisiNonValidi(parte) from err
        if not 1 <= numero <= 365:
            raise PreavvisiNonValidi(parte)
        valori.add(numero)
    return sorted(valori, reverse=True)


def formatta_preavvisi(preavvisi: Sequence[int]) -> str:
    """[30, 7, 1] → «30, 7, 1»."""
    return ", ".join(str(preavviso) for preavviso in preavvisi)


def _data_it(giorno: date) -> str:
    return giorno.strftime("%d/%m/%Y")


def _km_it(km: int) -> str:
    return f"{km:,}".replace(",", ".")


def riferimento(scadenza: Scadenza, stato: Stato) -> str:
    """Data e km di scadenza: se cambiano, i promemoria inviati si azzerano."""
    data = scadenza.scadenza.isoformat() if scadenza.scadenza is not None else ""
    km = "" if stato.km_scadenza is None else str(stato.km_scadenza)
    return f"{data}|{km}"


def _messaggio_giorni(giorni: int, scadenza: date) -> str:
    if giorni == 1:
        return f"Scade domani ({_data_it(scadenza)})."
    return f"Scade tra {giorni} giorni ({_data_it(scadenza)})."


def valuta(
    scadenza: Scadenza,
    stato: Stato,
    preavvisi: Sequence[int],
    memoria: Mapping[str, Any] | None,
) -> Esito:
    """Al massimo un promemoria per scadenza: il più urgente fra le soglie non ancora inviate."""
    rif = riferimento(scadenza, stato)
    inviati: list[int | str] = []
    if memoria and memoria.get(MEMORIA_RIFERIMENTO) == rif:
        inviati = list(memoria.get(MEMORIA_INVIATI, []))

    if (
        stato.stato in (STATO_ILLIMITATA, STATO_COMPLETATA)
        or scadenza.scadenza is None
        or stato.giorni_mancanti is None
    ):
        return Esito(None, {MEMORIA_RIFERIMENTO: rif, MEMORIA_INVIATI: inviati})

    giorni = stato.giorni_mancanti
    # Dalla meno urgente alla più urgente: l'ultima nuova è quella da inviare.
    superate: list[Promemoria] = [
        Promemoria(preavviso, _messaggio_giorni(giorni, scadenza.scadenza))
        for preavviso in sorted(set(preavvisi), reverse=True)
        if giorni <= preavviso
    ]
    if stato.km_mancanti is not None and stato.km_mancanti <= SOGLIA_KM:
        superate.append(
            Promemoria(SOGLIA_KM_VICINI, f"Mancano {_km_it(max(stato.km_mancanti, 0))} km.")
        )
    if giorni == 0:
        superate.append(Promemoria(SOGLIA_OGGI, "Scade oggi."))
    if stato.km_mancanti is not None and stato.km_mancanti <= 0 and stato.km_scadenza is not None:
        superate.append(
            Promemoria(SOGLIA_KM_SUPERATI, f"Limite di {_km_it(stato.km_scadenza)} km raggiunto.")
        )
    if giorni < 0:
        superate.append(Promemoria(SOGLIA_SCADUTA, f"Scaduta dal {_data_it(scadenza.scadenza)}."))

    nuove = [promemoria for promemoria in superate if promemoria.soglia not in inviati]
    if not nuove:
        return Esito(None, {MEMORIA_RIFERIMENTO: rif, MEMORIA_INVIATI: inviati})
    return Esito(
        nuove[-1],
        {MEMORIA_RIFERIMENTO: rif, MEMORIA_INVIATI: inviati + [p.soglia for p in nuove]},
    )
```

- [ ] **Step 4: Eseguire i test e verificare che passano**

Run: `pytest tests/logica/test_promemoria.py -q`
Expected: PASS

- [ ] **Step 5: Eseguire tutti i test di logica**

Run: `pytest tests/logica -q`
Expected: PASS, nessun errore

- [ ] **Step 6: Commit**

```bash
git add custom_components/scadenze/promemoria.py tests/logica/test_promemoria.py
git commit -m "feat: scelta dei promemoria senza doppioni"
```

### Task 6: Manifest, coordinator e setup della voce

**Files:**
- Create: `custom_components/scadenze/manifest.json`, `custom_components/scadenze/coordinator.py`, `custom_components/scadenze/__init__.py`
- Create: `tests/ha/__init__.py` (vuoto), `tests/ha/conftest.py`, `tests/ha/common.py`
- Test: `tests/ha/test_init.py`

**Interfaces:**
- Consumes: `const.*` (Task 1); `modello_dati.Voce`, `Scadenza`, `Stato`, `DatiNonValidi` (Task 2); `regole.rinnova`, `regole.calcola_stato`, `regole.RinnovoIgnorato` (Task 3).
- Produces:
  - `coordinator.py`: `@dataclass(frozen=True) class DatiScadenze(oggi: date, km_attuali: int | None, scadenze: dict[str, Scadenza], stati: dict[str, Stato])`; `class ScadenzeCoordinator(DataUpdateCoordinator[DatiScadenze])` con attributi `voce: Voce`, `scadenze: dict[str, Scadenza]`, proprietà `sensore_km -> str | None`, `preavvisi -> list[int]`, metodi `carica_scadenze() -> None`, `leggi_km() -> int | None`, `calcola() -> DatiScadenze`, `@callback async_ricalcola() -> None`, `async async_rinnova(subentry_id: str) -> None`.
  - `__init__.py`: `PLATFORMS: list[Platform]`; `@dataclass class ScadenzeRuntime(coordinator: ScadenzeCoordinator, device_id_voce: str, firma: Firma)`; `type ScadenzeConfigEntry = ConfigEntry[ScadenzeRuntime]`; `firma_entry(entry: ConfigEntry) -> Firma`; `async_setup_entry`, `async_unload_entry`.
  - `tests/ha/common.py`: `REVISIONE`, `BOLLO`, `TAGLIANDO` (dict dei dati), `OPZIONI_BASE`, `sotto_voce(subentry_id: str, dati: dict) -> ConfigSubentryDataWithId`, `crea_voce_veicolo(**opzioni) -> MockConfigEntry`, `async configura(hass, entry) -> None`, `entity_id(hass, piattaforma: str, unique_id: str) -> str`.

- [ ] **Step 1: Infrastruttura dei test HA**

`tests/ha/__init__.py`: file vuoto.

`tests/ha/conftest.py`:

```python
"""Fixture comuni ai test con Home Assistant."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
import pytest

from homeassistant.core import HomeAssistant

ADESSO = "2026-09-14T06:00:00+00:00"  # 08:00 a Roma, prima dell'orario dei promemoria


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Abilita il caricamento di custom_components in ogni test."""


@pytest.fixture(autouse=True)
async def fuso_orario_roma(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """Tutti i test partono il 14/09/2026 alle 08:00, ora di Roma."""
    await hass.config.async_set_time_zone("Europe/Rome")
    freezer.move_to(ADESSO)
```

`tests/ha/common.py`:

```python
"""Dati e funzioni condivisi dai test con Home Assistant."""

from __future__ import annotations

from typing import Any

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.scadenze.const import DOMAIN
from homeassistant.config_entries import ConfigSubentryDataWithId
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

_VUOTA: dict[str, Any] = {
    "ultimo_rinnovo": None,
    "completata": False,
    "intervallo_mesi": None,
    "ancora": "rinnovo",
    "intervallo_km": None,
    "km_ultimo_rinnovo": None,
    "mese_scadenza_bollo": None,
    "documento": None,
}

# Il 14/09/2026: revisione fra 16 giorni, bollo fra 47, tagliando fra 168.
REVISIONE: dict[str, Any] = {
    **_VUOTA,
    "modello": "revisione",
    "nome": "Revisione",
    "regola": "fine_mese",
    "scadenza": "2026-09-30",
}
BOLLO: dict[str, Any] = {
    **_VUOTA,
    "modello": "bollo",
    "nome": "Bollo",
    "regola": "fine_mese",
    "scadenza": "2026-10-31",
    "mese_scadenza_bollo": "2026-09-01",
}
TAGLIANDO: dict[str, Any] = {
    **_VUOTA,
    "modello": "tagliando",
    "nome": "Tagliando",
    "regola": "intervallo",
    "scadenza": "2027-03-01",
    "ultimo_rinnovo": "2026-03-01",
    "intervallo_mesi": 12,
    "intervallo_km": 15000,
    "km_ultimo_rinnovo": 20000,
}

OPZIONI_BASE: dict[str, Any] = {
    "sensore_km": "sensor.panda_km",
    "notifiche_attive": False,
    "servizio_notifica": "notify.telefono",
    "preavvisi": [30, 7, 1],
    "orario_notifica": "09:00:00",
}


def sotto_voce(subentry_id: str, dati: dict[str, Any]) -> ConfigSubentryDataWithId:
    return ConfigSubentryDataWithId(
        subentry_id=subentry_id,
        subentry_type="scadenza",
        title=dati["nome"],
        unique_id=None,
        data=dati,
    )


def crea_voce_veicolo(**opzioni: Any) -> MockConfigEntry:
    """La Panda con revisione, bollo e tagliando; le opzioni sovrascrivono OPZIONI_BASE."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Panda",
        data={
            "tipo": "veicolo",
            "nome": "Panda",
            "tipo_veicolo": "auto",
            "immatricolazione": "2022-05-01",
        },
        options={**OPZIONI_BASE, **opzioni},
        subentries_data=[
            sotto_voce("sub_revisione", REVISIONE),
            sotto_voce("sub_bollo", BOLLO),
            sotto_voce("sub_tagliando", TAGLIANDO),
        ],
    )


async def configura(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def entity_id(hass: HomeAssistant, piattaforma: str, unique_id: str) -> str:
    trovato = er.async_get(hass).async_get_entity_id(piattaforma, DOMAIN, unique_id)
    assert trovato is not None, f"nessuna entità {piattaforma} con unique_id {unique_id}"
    return trovato
```

- [ ] **Step 2: Scrivere i test che falliscono**

`tests/ha/test_init.py`:

```python
"""Test di setup, dispositivi, ricalcoli, rinnovo e politica di reload (spec §8.0 e §9)."""

from __future__ import annotations

from types import MappingProxyType

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.scadenze.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .common import REVISIONE, configura, crea_voce_veicolo, sotto_voce


async def test_setup_crea_il_dispositivo_della_voce(
    hass: HomeAssistant, device_registry: dr.DeviceRegistry
) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    dispositivo = device_registry.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    assert dispositivo is not None
    assert (dispositivo.name, dispositivo.model) == ("Panda", "Veicolo")
    assert entry.runtime_data.device_id_voce == dispositivo.id


async def test_stati_iniziali(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)
    stati = entry.runtime_data.coordinator.data.stati

    assert (stati["sub_revisione"].stato, stati["sub_revisione"].giorni_mancanti) == ("in_scadenza", 16)
    assert (stati["sub_bollo"].stato, stati["sub_bollo"].giorni_mancanti) == ("ok", 47)
    assert stati["sub_tagliando"].km_non_disponibili is True


async def test_il_contachilometri_fa_ricalcolare(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    hass.states.async_set("sensor.panda_km", "34500")
    await hass.async_block_till_done()

    stato = entry.runtime_data.coordinator.data.stati["sub_tagliando"]
    assert (stato.stato, stato.km_mancanti) == ("in_scadenza", 500)


async def test_ricalcolo_a_mezzanotte(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    freezer.move_to("2026-09-30T22:00:05+00:00")  # 1 ottobre, 00:00:05 a Roma
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    stato = entry.runtime_data.coordinator.data.stati["sub_revisione"]
    assert (stato.stato, stato.giorni_mancanti) == ("scaduta", -1)


async def test_rinnovo_salva_la_subentry_senza_ricaricare(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)
    coordinator = entry.runtime_data.coordinator

    await coordinator.async_rinnova("sub_revisione")
    await hass.async_block_till_done()

    dati = entry.subentries["sub_revisione"].data
    assert (dati["scadenza"], dati["ultimo_rinnovo"]) == ("2028-09-30", "2026-09-14")
    assert entry.runtime_data.coordinator is coordinator
    assert coordinator.data.stati["sub_revisione"].stato == "ok"


async def test_doppio_rinnovo_ignorato(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)
    coordinator = entry.runtime_data.coordinator

    await coordinator.async_rinnova("sub_bollo")
    await coordinator.async_rinnova("sub_bollo")
    await hass.async_block_till_done()

    dati = entry.subentries["sub_bollo"].data
    assert (dati["mese_scadenza_bollo"], dati["scadenza"]) == ("2027-09-01", "2027-10-31")


async def test_nuova_scadenza_ricarica_la_voce(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)
    vecchio = entry.runtime_data.coordinator

    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(
            data=MappingProxyType({**REVISIONE, "modello": "gomme", "nome": "Gomme", "regola": "stagionale", "scadenza": "2026-11-15"}),
            subentry_type="scadenza",
            title="Gomme",
            unique_id=None,
        ),
    )
    await hass.async_block_till_done()

    nuovo = entry.runtime_data.coordinator
    assert nuovo is not vecchio
    assert "Gomme" in {scadenza.nome for scadenza in nuovo.scadenze.values()}


async def test_scadenza_illeggibile_saltata(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    base = crea_voce_veicolo()
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=base.title,
        data=dict(base.data),
        options=dict(base.options),
        subentries_data=[
            sotto_voce("sub_revisione", REVISIONE),
            sotto_voce("sub_rotta", {"modello": "revisione", "nome": "Rotta"}),
        ],
    )
    await configura(hass, entry)

    assert "sub_rotta" not in entry.runtime_data.coordinator.scadenze
    assert "sub_revisione" in entry.runtime_data.coordinator.scadenze
    assert "ignorata" in caplog.text


async def test_unload(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
```

- [ ] **Step 3: Eseguire i test e verificare che falliscono**

Run: `pytest tests/ha/test_init.py -q`
Expected: FAIL (integrazione `scadenze` non trovata: manca `manifest.json`)

- [ ] **Step 4: Implementare**

`custom_components/scadenze/manifest.json`:

```json
{
  "domain": "scadenze",
  "name": "Scadenze Auto & Casa",
  "codeowners": ["@iAlias"],
  "config_flow": true,
  "dependencies": [],
  "documentation": "https://github.com/iAlias/scadenze-auto-casa",
  "integration_type": "service",
  "iot_class": "calculated",
  "issue_tracker": "https://github.com/iAlias/scadenze-auto-casa/issues",
  "requirements": [],
  "version": "0.1.0"
}
```

`custom_components/scadenze/coordinator.py`:

```python
"""Coordinator: tiene in memoria voce e scadenze e ricalcola gli stati."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_PREAVVISI,
    CONF_SENSORE_KM,
    DOMAIN,
    PREDEFINITO_PREAVVISI,
    SUBENTRY_SCADENZA,
    TIPO_VEICOLO,
)
from .modello_dati import DatiNonValidi, Scadenza, Stato, Voce
from .regole import RinnovoIgnorato, calcola_stato, rinnova

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatiScadenze:
    """Fotografia di un ricalcolo: le scadenze e il loro stato in un giorno."""

    oggi: date
    km_attuali: int | None
    scadenze: dict[str, Scadenza]
    stati: dict[str, Stato]


class ScadenzeCoordinator(DataUpdateCoordinator[DatiScadenze]):
    """Nessun polling: ricalcola quando arriva un trigger (spec §9)."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=None,
        )
        self.voce = Voce.da_dict(entry.data)
        self.scadenze: dict[str, Scadenza] = {}
        self._ultimi_km: int | None = None
        self.carica_scadenze()

    @property
    def sensore_km(self) -> str | None:
        """Il sensore del contachilometri, solo per i veicoli."""
        if self.voce.tipo != TIPO_VEICOLO:
            return None
        return self.config_entry.options.get(CONF_SENSORE_KM) or None

    @property
    def preavvisi(self) -> list[int]:
        return [int(p) for p in self.config_entry.options.get(CONF_PREAVVISI, PREDEFINITO_PREAVVISI)]

    def carica_scadenze(self) -> None:
        """Rilegge le scadenze dalle subentries; quelle illeggibili vengono saltate."""
        scadenze: dict[str, Scadenza] = {}
        for subentry_id, subentry in self.config_entry.subentries.items():
            if subentry.subentry_type != SUBENTRY_SCADENZA:
                continue
            try:
                scadenze[subentry_id] = Scadenza.da_dict(subentry.data)
            except DatiNonValidi as err:
                _LOGGER.error("Scadenza %s ignorata: %s", subentry.title, err)
        self.scadenze = scadenze

    def leggi_km(self) -> int | None:
        """La lettura attuale del contachilometri, se numerica."""
        if self.sensore_km is None:
            return None
        stato = self.hass.states.get(self.sensore_km)
        if stato is None:
            return None
        try:
            km = int(float(stato.state))
        except (TypeError, ValueError):
            return None
        self._ultimi_km = km
        return km

    def calcola(self) -> DatiScadenze:
        oggi = dt_util.now().date()
        km = self.leggi_km()
        configurati = self.sensore_km is not None
        stati = {
            subentry_id: calcola_stato(scadenza, oggi, self.preavvisi, km, km_configurati=configurati)
            for subentry_id, scadenza in self.scadenze.items()
        }
        return DatiScadenze(oggi, km, dict(self.scadenze), stati)

    async def _async_update_data(self) -> DatiScadenze:
        return self.calcola()

    @callback
    def async_ricalcola(self) -> None:
        self.async_set_updated_data(self.calcola())

    async def async_rinnova(self, subentry_id: str) -> None:
        """Rinnova una scadenza oggi, salva la subentry e aggiorna le entità."""
        scadenza = self.scadenze.get(subentry_id)
        subentry = self.config_entry.subentries.get(subentry_id)
        if scadenza is None or subentry is None:
            _LOGGER.warning("Scadenza %s non trovata: rinnovo annullato", subentry_id)
            return

        oggi = dt_util.now().date()
        km = self.leggi_km()
        if km is None:
            km = self._ultimi_km
        try:
            nuova = rinnova(scadenza, self.voce, oggi, km)
        except RinnovoIgnorato:
            _LOGGER.info("%s è già stata rinnovata oggi: rinnovo ignorato", scadenza.nome)
            return
        except DatiNonValidi as err:
            _LOGGER.error("Rinnovo di %s non riuscito: %s", scadenza.nome, err)
            return
        if nuova.usa_km and km is None:
            _LOGGER.warning(
                "Nessuna lettura del contachilometri per %s: km del rinnovo invariati", scadenza.nome
            )

        self.scadenze[subentry_id] = nuova
        self.hass.config_entries.async_update_subentry(
            self.config_entry, subentry, data=nuova.a_dict()
        )
        self.async_ricalcola()
```

`custom_components/scadenze/__init__.py`:

```python
"""Scadenze Auto & Casa: scadenze italiane di veicoli, casa e documenti."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)

from .const import DOMAIN, ETICHETTE_TIPO_VOCE
from .coordinator import ScadenzeCoordinator

PLATFORMS: list[Platform] = []

type Firma = tuple[frozenset[tuple[str, str]], dict[str, Any], dict[str, Any]]


@dataclass
class ScadenzeRuntime:
    """Ciò che serve alle piattaforme di una voce caricata."""

    coordinator: ScadenzeCoordinator
    device_id_voce: str
    firma: Firma


type ScadenzeConfigEntry = ConfigEntry[ScadenzeRuntime]


def firma_entry(entry: ConfigEntry) -> Firma:
    """Se cambia, la entry va ricaricata: subentries (id e titolo), dati o opzioni."""
    return (
        frozenset((subentry_id, subentry.title) for subentry_id, subentry in entry.subentries.items()),
        dict(entry.data),
        dict(entry.options),
    )


async def async_setup_entry(hass: HomeAssistant, entry: ScadenzeConfigEntry) -> bool:
    coordinator = ScadenzeCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    dispositivo = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=coordinator.voce.nome,
        model=ETICHETTE_TIPO_VOCE[coordinator.voce.tipo],
        entry_type=dr.DeviceEntryType.SERVICE,
    )
    entry.runtime_data = ScadenzeRuntime(
        coordinator=coordinator,
        device_id_voce=dispositivo.id,
        firma=firma_entry(entry),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    def _a_mezzanotte(_ora: datetime) -> None:
        coordinator.async_ricalcola()

    @callback
    def _km_cambiati(_evento: Event[EventStateChangedData]) -> None:
        coordinator.async_ricalcola()

    entry.async_on_unload(
        async_track_time_change(hass, _a_mezzanotte, hour=0, minute=0, second=5)
    )
    if coordinator.sensore_km:
        entry.async_on_unload(
            async_track_state_change_event(hass, [coordinator.sensore_km], _km_cambiati)
        )
    entry.async_on_unload(entry.add_update_listener(_async_entry_aggiornata))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ScadenzeConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_entry_aggiornata(hass: HomeAssistant, entry: ScadenzeConfigEntry) -> None:
    """Reload solo se servono entità o impostazioni nuove; altrimenti basta ricalcolare."""
    runtime = entry.runtime_data
    if firma_entry(entry) != runtime.firma:
        await hass.config_entries.async_reload(entry.entry_id)
        return
    runtime.coordinator.carica_scadenze()
    runtime.coordinator.async_ricalcola()
```

- [ ] **Step 5: Eseguire i test e verificare che passano**

Run: `pytest tests/ha/test_init.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add custom_components/scadenze/manifest.json custom_components/scadenze/coordinator.py custom_components/scadenze/__init__.py tests/ha
git commit -m "feat: setup della voce, coordinator, rinnovo e politica di reload"
```

### Task 7: Entità della scadenza (sensori e sensore binario)

**Files:**
- Create: `custom_components/scadenze/entity.py`, `custom_components/scadenze/sensor.py`, `custom_components/scadenze/binary_sensor.py`
- Modify: `custom_components/scadenze/__init__.py` (riga `PLATFORMS`)
- Test: `tests/ha/test_sensori.py`

**Interfaces:**
- Consumes: `ScadenzeCoordinator`, `DatiScadenze` (Task 6); `ScadenzeConfigEntry`, `ScadenzeRuntime.device_id_voce` (Task 6); `modelli.MODELLI` (Task 4); `regole.attributi_extra` (Task 3); `tests/ha/common.py` (Task 6).
- Produces:
  - `entity.py`: `class EntitaScadenza(CoordinatorEntity[ScadenzeCoordinator])` con `__init__(coordinator, subentry_id: str, chiave: str, device_id_voce: str)`, attributo `subentry_id`, proprietà `scadenza -> Scadenza | None`, `stato -> Stato | None`; `class EntitaVoce(CoordinatorEntity[ScadenzeCoordinator])` con `__init__(coordinator, chiave: str)`.
  - `unique_id`: `{subentry_id}_scadenza`, `{subentry_id}_giorni`, `{subentry_id}_km`, `{subentry_id}_in_scadenza`.
  - `translation_key`: `giorni_mancanti`, `km_mancanti`, `in_scadenza`.

- [ ] **Step 1: Scrivere i test che falliscono**

`tests/ha/test_sensori.py`:

```python
"""Test di sensori, sensore binario e dispositivi delle scadenze (spec §8.0 e §8.1)."""

from __future__ import annotations

import pytest

from custom_components.scadenze.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .common import configura, crea_voce_veicolo, entity_id


async def test_sensore_data_con_attributi(hass: HomeAssistant) -> None:
    await configura(hass, crea_voce_veicolo())

    revisione = hass.states.get(entity_id(hass, "sensor", "sub_revisione_scadenza"))
    assert revisione is not None
    assert revisione.state == "2026-09-30"
    assert revisione.attributes["stato"] == "in_scadenza"
    assert revisione.attributes["modello"] == "revisione"
    assert revisione.attributes["ultimo_rinnovo"] is None

    bollo = hass.states.get(entity_id(hass, "sensor", "sub_bollo_scadenza"))
    assert bollo is not None
    assert bollo.attributes["mese_scadenza_bollo"] == "2026-09-01"
    assert bollo.attributes["da_pagare_entro"] == "2026-10-31"


async def test_giorni_mancanti(hass: HomeAssistant) -> None:
    await configura(hass, crea_voce_veicolo())

    giorni = hass.states.get(entity_id(hass, "sensor", "sub_revisione_giorni"))
    assert giorni is not None
    assert giorni.state == "16"
    assert giorni.attributes["unit_of_measurement"] == "d"


async def test_km_mancanti_seguono_il_contachilometri(hass: HomeAssistant) -> None:
    await configura(hass, crea_voce_veicolo())
    km = entity_id(hass, "sensor", "sub_tagliando_km")

    assert hass.states.get(km).state == "unavailable"

    hass.states.async_set("sensor.panda_km", "34500")
    await hass.async_block_till_done()
    assert hass.states.get(km).state == "500"


async def test_km_mancanti_solo_con_contachilometri(hass: HomeAssistant) -> None:
    await configura(hass, crea_voce_veicolo(sensore_km=None))
    assert er.async_get(hass).async_get_entity_id("sensor", DOMAIN, "sub_tagliando_km") is None


async def test_in_scadenza(hass: HomeAssistant) -> None:
    await configura(hass, crea_voce_veicolo())

    assert hass.states.get(entity_id(hass, "binary_sensor", "sub_revisione_in_scadenza")).state == "on"
    assert hass.states.get(entity_id(hass, "binary_sensor", "sub_bollo_in_scadenza")).state == "off"


async def test_un_dispositivo_per_scadenza_collegato_alla_voce(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    voce = device_registry.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    revisione = device_registry.async_get_device(identifiers={(DOMAIN, "sub_revisione")})
    assert voce is not None and revisione is not None
    assert revisione.name == "Panda Revisione"
    assert revisione.model == "Revisione"
    assert revisione.via_device_id == voce.id

    voce_entita = entity_registry.async_get(entity_id(hass, "sensor", "sub_revisione_giorni"))
    assert voce_entita is not None
    assert voce_entita.device_id == revisione.id
    assert voce_entita.config_subentry_id == "sub_revisione"
    assert "silently moves the device" not in caplog.text


async def test_eliminare_la_scadenza_toglie_dispositivo_ed_entita(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    hass.config_entries.async_remove_subentry(entry, "sub_revisione")
    await hass.async_block_till_done()

    assert device_registry.async_get_device(identifiers={(DOMAIN, "sub_revisione")}) is None
    assert entity_registry.async_get_entity_id("sensor", DOMAIN, "sub_revisione_scadenza") is None
```

- [ ] **Step 2: Eseguire i test e verificare che falliscono**

Run: `pytest tests/ha/test_sensori.py -q`
Expected: FAIL con `AssertionError: nessuna entità sensor con unique_id sub_revisione_scadenza`

- [ ] **Step 3: Implementare**

`custom_components/scadenze/entity.py`:

```python
"""Entità base di Scadenze Auto & Casa."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ScadenzeCoordinator
from .modelli import MODELLI
from .modello_dati import Scadenza, Stato


class EntitaScadenza(CoordinatorEntity[ScadenzeCoordinator]):
    """Entità di una scadenza, sul dispositivo della scadenza (spec §8.0)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ScadenzeCoordinator,
        subentry_id: str,
        chiave: str,
        device_id_voce: str,
    ) -> None:
        super().__init__(coordinator)
        self.subentry_id = subentry_id
        scadenza = coordinator.scadenze[subentry_id]
        modello = MODELLI.get(scadenza.modello)
        self._attr_unique_id = f"{subentry_id}_{chiave}"
        self._attr_icon = modello.icona if modello else None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, subentry_id)},
            name=f"{coordinator.voce.nome} {scadenza.nome}",
            model=modello.etichetta if modello else scadenza.modello,
            entry_type=DeviceEntryType.SERVICE,
            via_device_id=device_id_voce,
        )

    @property
    def scadenza(self) -> Scadenza | None:
        return self.coordinator.data.scadenze.get(self.subentry_id)

    @property
    def stato(self) -> Stato | None:
        return self.coordinator.data.stati.get(self.subentry_id)

    @property
    def available(self) -> bool:
        return super().available and self.stato is not None


class EntitaVoce(CoordinatorEntity[ScadenzeCoordinator]):
    """Entità della voce, sul dispositivo della voce creato nel setup."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ScadenzeCoordinator, chiave: str) -> None:
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{chiave}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})
```

`custom_components/scadenze/sensor.py`:

```python
"""Sensori di una scadenza: data, giorni mancanti, km mancanti."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ScadenzeConfigEntry
from .entity import EntitaScadenza
from .regole import attributi_extra


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ScadenzeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    runtime = entry.runtime_data
    coordinator = runtime.coordinator
    for subentry_id, scadenza in coordinator.scadenze.items():
        entita: list[SensorEntity] = [
            SensoreScadenza(coordinator, subentry_id, "scadenza", runtime.device_id_voce),
            SensoreGiorniMancanti(coordinator, subentry_id, "giorni", runtime.device_id_voce),
        ]
        if scadenza.usa_km and coordinator.sensore_km:
            entita.append(SensoreKmMancanti(coordinator, subentry_id, "km", runtime.device_id_voce))
        async_add_entities(entita, config_subentry_id=subentry_id)


class SensoreScadenza(EntitaScadenza, SensorEntity):
    """La data di scadenza; il nome è quello del dispositivo."""

    _attr_name = None
    _attr_device_class = SensorDeviceClass.DATE

    @property
    def native_value(self) -> date | None:
        return self.scadenza.scadenza if self.scadenza else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        scadenza, stato = self.scadenza, self.stato
        if scadenza is None or stato is None:
            return {}
        attributi: dict[str, Any] = {
            "stato": stato.stato,
            "modello": scadenza.modello,
            "ultimo_rinnovo": scadenza.ultimo_rinnovo.isoformat() if scadenza.ultimo_rinnovo else None,
        }
        attributi.update(attributi_extra(scadenza))
        if scadenza.usa_km:
            attributi["km_scadenza"] = stato.km_scadenza
            attributi["km_non_disponibili"] = stato.km_non_disponibili
        return attributi


class SensoreGiorniMancanti(EntitaScadenza, SensorEntity):
    _attr_translation_key = "giorni_mancanti"
    _attr_native_unit_of_measurement = UnitOfTime.DAYS

    @property
    def native_value(self) -> int | None:
        return self.stato.giorni_mancanti if self.stato else None


class SensoreKmMancanti(EntitaScadenza, SensorEntity):
    _attr_translation_key = "km_mancanti"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS

    @property
    def available(self) -> bool:
        return super().available and self.stato is not None and not self.stato.km_non_disponibili

    @property
    def native_value(self) -> int | None:
        return self.stato.km_mancanti if self.stato else None
```

`custom_components/scadenze/binary_sensor.py`:

```python
"""Sensore binario «In scadenza» di una scadenza."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ScadenzeConfigEntry
from .entity import EntitaScadenza
from .modello_dati import STATO_IN_SCADENZA, STATO_SCADUTA


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ScadenzeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    runtime = entry.runtime_data
    for subentry_id in runtime.coordinator.scadenze:
        async_add_entities(
            [InScadenza(runtime.coordinator, subentry_id, "in_scadenza", runtime.device_id_voce)],
            config_subentry_id=subentry_id,
        )


class InScadenza(EntitaScadenza, BinarySensorEntity):
    _attr_translation_key = "in_scadenza"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool | None:
        if self.stato is None:
            return None
        return self.stato.stato in (STATO_IN_SCADENZA, STATO_SCADUTA)
```

In `custom_components/scadenze/__init__.py` sostituire la riga `PLATFORMS: list[Platform] = []` con:

```python
PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]
```

- [ ] **Step 4: Eseguire i test e verificare che passano**

Run: `pytest tests/ha/test_sensori.py tests/ha/test_init.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/scadenze/entity.py custom_components/scadenze/sensor.py custom_components/scadenze/binary_sensor.py custom_components/scadenze/__init__.py tests/ha/test_sensori.py
git commit -m "feat: sensori e dispositivi delle scadenze"
```

### Task 8: Pulsante «Rinnovato»

**Files:**
- Create: `custom_components/scadenze/button.py`
- Modify: `custom_components/scadenze/__init__.py` (riga `PLATFORMS`)
- Test: `tests/ha/test_pulsante.py`

**Interfaces:**
- Consumes: `EntitaScadenza` (Task 7); `ScadenzeCoordinator.async_rinnova` (Task 6); `tests/ha/common.py` (Task 6).
- Produces: entità `button` con `unique_id` `{subentry_id}_rinnova` e `translation_key` `rinnovato`.

- [ ] **Step 1: Scrivere i test che falliscono**

`tests/ha/test_pulsante.py`:

```python
"""Test del pulsante «Rinnovato» (spec §8.1 e §5.7)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from .common import configura, crea_voce_veicolo, entity_id


async def premi(hass: HomeAssistant, pulsante: str) -> None:
    await hass.services.async_call("button", "press", {}, target={"entity_id": pulsante}, blocking=True)
    await hass.async_block_till_done()


async def test_premere_rinnova_la_scadenza(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    await premi(hass, entity_id(hass, "button", "sub_revisione_rinnova"))

    assert entry.subentries["sub_revisione"].data["scadenza"] == "2028-09-30"
    assert hass.states.get(entity_id(hass, "sensor", "sub_revisione_scadenza")).state == "2028-09-30"
    assert hass.states.get(entity_id(hass, "binary_sensor", "sub_revisione_in_scadenza")).state == "off"


async def test_doppia_pressione_nello_stesso_giorno(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)
    pulsante = entity_id(hass, "button", "sub_bollo_rinnova")

    await premi(hass, pulsante)
    await premi(hass, pulsante)

    assert entry.subentries["sub_bollo"].data["scadenza"] == "2027-10-31"
```

- [ ] **Step 2: Eseguire i test e verificare che falliscono**

Run: `pytest tests/ha/test_pulsante.py -q`
Expected: FAIL con `AssertionError: nessuna entità button con unique_id sub_revisione_rinnova`

- [ ] **Step 3: Implementare**

`custom_components/scadenze/button.py`:

```python
"""Pulsante «Rinnovato» di una scadenza."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ScadenzeConfigEntry
from .entity import EntitaScadenza


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ScadenzeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    runtime = entry.runtime_data
    for subentry_id in runtime.coordinator.scadenze:
        async_add_entities(
            [Rinnovato(runtime.coordinator, subentry_id, "rinnova", runtime.device_id_voce)],
            config_subentry_id=subentry_id,
        )


class Rinnovato(EntitaScadenza, ButtonEntity):
    _attr_translation_key = "rinnovato"

    async def async_press(self) -> None:
        await self.coordinator.async_rinnova(self.subentry_id)
```

In `custom_components/scadenze/__init__.py` la riga `PLATFORMS` diventa:

```python
PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR]
```

- [ ] **Step 4: Eseguire i test e verificare che passano**

Run: `pytest tests/ha -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/scadenze/button.py custom_components/scadenze/__init__.py tests/ha/test_pulsante.py
git commit -m "feat: pulsante Rinnovato"
```

### Task 9: Calendario e lista «Da rinnovare» della voce

**Files:**
- Create: `custom_components/scadenze/calendar.py`, `custom_components/scadenze/todo.py`
- Modify: `custom_components/scadenze/__init__.py` (riga `PLATFORMS`)
- Test: `tests/ha/test_calendario_todo.py`

**Interfaces:**
- Consumes: `EntitaVoce` (Task 7); `DatiScadenze` e `ScadenzeCoordinator.async_rinnova` (Task 6); `regole.attributi_extra` (Task 3); `STATO_IN_SCADENZA`, `STATO_SCADUTA` (Task 2).
- Produces: `calendar` con `unique_id` `{entry_id}_calendario`, `translation_key` `calendario`; `todo` con `unique_id` `{entry_id}_todo`, `translation_key` `da_rinnovare`.

- [ ] **Step 1: Scrivere i test che falliscono**

`tests/ha/test_calendario_todo.py`:

```python
"""Test del calendario e della lista todo della voce (spec §8.2)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from .common import configura, crea_voce_veicolo, entity_id


async def test_calendario_prossima_scadenza(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    stato = hass.states.get(entity_id(hass, "calendar", f"{entry.entry_id}_calendario"))
    assert stato is not None
    assert stato.attributes["message"] == "Revisione"
    assert stato.attributes["all_day"] is True


async def test_calendario_eventi_in_un_intervallo(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)
    calendario = entity_id(hass, "calendar", f"{entry.entry_id}_calendario")

    risposta = await hass.services.async_call(
        "calendar",
        "get_events",
        {"start_date_time": "2026-09-01T00:00:00+02:00", "end_date_time": "2026-11-01T00:00:00+01:00"},
        target={"entity_id": calendario},
        blocking=True,
        return_response=True,
    )

    eventi = risposta[calendario]["events"]
    assert [evento["summary"] for evento in eventi] == ["Revisione", "Bollo"]
    assert (eventi[0]["start"], eventi[0]["end"]) == ("2026-09-30", "2026-10-01")


async def test_todo_elenca_solo_le_scadenze_vicine(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)
    lista = entity_id(hass, "todo", f"{entry.entry_id}_todo")

    assert hass.states.get(lista).state == "1"
    risposta = await hass.services.async_call(
        "todo", "get_items", {}, target={"entity_id": lista}, blocking=True, return_response=True
    )
    elementi = risposta[lista]["items"]
    assert [(e["summary"], e["uid"], e["status"], e["due"]) for e in elementi] == [
        ("Revisione", "sub_revisione", "needs_action", "2026-09-30")
    ]


async def test_spuntare_un_elemento_rinnova(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)
    lista = entity_id(hass, "todo", f"{entry.entry_id}_todo")

    await hass.services.async_call(
        "todo",
        "update_item",
        {"item": "Revisione", "status": "completed"},
        target={"entity_id": lista},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert entry.subentries["sub_revisione"].data["scadenza"] == "2028-09-30"
    assert hass.states.get(lista).state == "0"
```

- [ ] **Step 2: Eseguire i test e verificare che falliscono**

Run: `pytest tests/ha/test_calendario_todo.py -q`
Expected: FAIL con `AssertionError: nessuna entità calendar con unique_id …_calendario`

- [ ] **Step 3: Implementare**

`custom_components/scadenze/calendar.py`:

```python
"""Calendario delle scadenze di una voce."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import ScadenzeConfigEntry
from .coordinator import ScadenzeCoordinator
from .entity import EntitaVoce
from .regole import attributi_extra


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ScadenzeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([CalendarioScadenze(entry.runtime_data.coordinator)])


class CalendarioScadenze(EntitaVoce, CalendarEntity):
    """Un evento di un giorno intero per ogni scadenza con una data."""

    _attr_translation_key = "calendario"

    def __init__(self, coordinator: ScadenzeCoordinator) -> None:
        super().__init__(coordinator, "calendario")

    def _eventi(self) -> list[CalendarEvent]:
        dati = self.coordinator.data
        eventi: list[CalendarEvent] = []
        for subentry_id, scadenza in dati.scadenze.items():
            if scadenza.scadenza is None:
                continue
            righe = [f"Stato: {dati.stati[subentry_id].stato}"]
            righe += [f"{chiave}: {valore}" for chiave, valore in attributi_extra(scadenza).items()]
            eventi.append(
                CalendarEvent(
                    start=scadenza.scadenza,
                    end=scadenza.scadenza + timedelta(days=1),
                    summary=scadenza.nome,
                    description="\n".join(righe),
                    uid=subentry_id,
                )
            )
        eventi.sort(key=lambda evento: (evento.start, evento.summary))
        return eventi

    @property
    def event(self) -> CalendarEvent | None:
        oggi = self.coordinator.data.oggi
        return next((evento for evento in self._eventi() if evento.start >= oggi), None)

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        return [
            evento
            for evento in self._eventi()
            if dt_util.start_of_local_day(evento.start) < end_date
            and dt_util.start_of_local_day(evento.end) > start_date
        ]
```

`custom_components/scadenze/todo.py`:

```python
"""Lista «Da rinnovare» di una voce: spuntare un elemento equivale a «Rinnovato»."""

from __future__ import annotations

from datetime import date

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ScadenzeConfigEntry
from .coordinator import ScadenzeCoordinator
from .entity import EntitaVoce
from .modello_dati import STATO_IN_SCADENZA, STATO_SCADUTA


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ScadenzeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([DaRinnovare(entry.runtime_data.coordinator)])


class DaRinnovare(EntitaVoce, TodoListEntity):
    _attr_translation_key = "da_rinnovare"
    _attr_supported_features = TodoListEntityFeature.UPDATE_TODO_ITEM

    def __init__(self, coordinator: ScadenzeCoordinator) -> None:
        super().__init__(coordinator, "todo")
        self._attr_todo_items = self._elementi()

    def _elementi(self) -> list[TodoItem]:
        dati = self.coordinator.data
        elementi: list[TodoItem] = []
        ordinate = sorted(
            dati.scadenze.items(),
            key=lambda coppia: (coppia[1].scadenza or date.max, coppia[1].nome),
        )
        for subentry_id, scadenza in ordinate:
            stato = dati.stati[subentry_id]
            if stato.stato not in (STATO_IN_SCADENZA, STATO_SCADUTA):
                continue
            elementi.append(
                TodoItem(
                    summary=scadenza.nome,
                    uid=subentry_id,
                    status=TodoItemStatus.NEEDS_ACTION,
                    due=scadenza.scadenza,
                    description=f"Stato: {stato.stato}",
                )
            )
        return elementi

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_todo_items = self._elementi()
        super()._handle_coordinator_update()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        if item.status == TodoItemStatus.COMPLETED and item.uid in self.coordinator.scadenze:
            await self.coordinator.async_rinnova(item.uid)
```

In `custom_components/scadenze/__init__.py` la riga `PLATFORMS` diventa:

```python
PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CALENDAR,
    Platform.SENSOR,
    Platform.TODO,
]
```

- [ ] **Step 4: Eseguire i test e verificare che passano**

Run: `pytest tests/ha -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/scadenze/calendar.py custom_components/scadenze/todo.py custom_components/scadenze/__init__.py tests/ha/test_calendario_todo.py
git commit -m "feat: calendario e lista Da rinnovare della voce"
```

### Task 10: Invio dei promemoria

**Files:**
- Create: `custom_components/scadenze/notifiche.py`
- Modify: `custom_components/scadenze/__init__.py` (runtime, setup)
- Test: `tests/ha/test_notifiche.py`

**Interfaces:**
- Consumes: `ScadenzeCoordinator` (`data`, `preavvisi`, `voce`, `async_ricalcola`) (Task 6); `promemoria.valuta`, `Promemoria` (Task 5); costanti `CONF_NOTIFICHE_ATTIVE`, `CONF_SERVIZIO_NOTIFICA`, `CONF_ORARIO_NOTIFICA`, `PREDEFINITO_*`, `EVENTO_PROMEMORIA`, `DOMAIN` (Task 1).
- Produces:
  - `notifiche.py`: `class GestoreNotifiche` con `__init__(hass, entry, coordinator)`, proprietà `orario -> time`, `issue_id -> str`, metodi `async async_carica() -> None`, `@callback async_pianifica() -> Callable[[], None]`, `async async_esegui() -> None`.
  - `ScadenzeRuntime` acquisisce il campo `notifiche: GestoreNotifiche`.
  - Evento `scadenze_promemoria` con dati `voce`, `voce_id`, `scadenza`, `scadenza_id`, `modello`, `data`, `giorni_mancanti`, `km_mancanti`, `soglia`, `messaggio`.
  - Issue `servizio_notifica_mancante_{entry_id}` con `translation_key` `servizio_notifica_mancante`.

- [ ] **Step 1: Scrivere i test che falliscono**

`tests/ha/test_notifiche.py`:

```python
"""Test dell'invio dei promemoria (spec §10.2)."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    async_capture_events,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.scadenze.const import DOMAIN, EVENTO_PROMEMORIA
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .common import configura, crea_voce_veicolo

ALLE_NOVE = "2026-09-14T07:00:00+00:00"  # 09:00 a Roma
ALLE_DIECI = "2026-09-14T08:00:00+00:00"  # 10:00 a Roma


async def test_promemoria_all_orario(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    chiamate = async_mock_service(hass, "notify", "telefono")
    eventi = async_capture_events(hass, EVENTO_PROMEMORIA)
    await configura(hass, crea_voce_veicolo(notifiche_attive=True))
    assert chiamate == []

    freezer.move_to(ALLE_NOVE)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert len(chiamate) == 1
    assert chiamate[0].data == {
        "title": "Panda – Revisione",
        "message": "Scade tra 16 giorni (30/09/2026).",
    }
    assert len(eventi) == 1
    assert eventi[0].data["scadenza_id"] == "sub_revisione"
    assert eventi[0].data["soglia"] == 30
    assert eventi[0].data["giorni_mancanti"] == 16


async def test_nessun_doppione_dopo_un_riavvio(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    chiamate = async_mock_service(hass, "notify", "telefono")
    entry = crea_voce_veicolo(notifiche_attive=True)
    await configura(hass, entry)

    freezer.move_to(ALLE_NOVE)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert len(chiamate) == 1

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert len(chiamate) == 1


async def test_promemoria_all_avvio_se_l_orario_e_passato(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(ALLE_DIECI)
    chiamate = async_mock_service(hass, "notify", "telefono")

    await configura(hass, crea_voce_veicolo(notifiche_attive=True))

    assert len(chiamate) == 1


async def test_servizio_mancante_crea_una_riparazione(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, issue_registry: ir.IssueRegistry
) -> None:
    freezer.move_to(ALLE_DIECI)
    eventi = async_capture_events(hass, EVENTO_PROMEMORIA)
    entry = crea_voce_veicolo(notifiche_attive=True, servizio_notifica="notify.inesistente")

    await configura(hass, entry)

    assert issue_registry.async_get_issue(DOMAIN, f"servizio_notifica_mancante_{entry.entry_id}") is not None
    assert len(eventi) == 1


async def test_notifiche_disattivate_lanciano_solo_l_evento(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(ALLE_DIECI)
    chiamate = async_mock_service(hass, "notify", "telefono")
    eventi = async_capture_events(hass, EVENTO_PROMEMORIA)

    await configura(hass, crea_voce_veicolo(notifiche_attive=False))

    assert chiamate == []
    assert len(eventi) == 1
```

- [ ] **Step 2: Eseguire i test e verificare che falliscono**

Run: `pytest tests/ha/test_notifiche.py -q`
Expected: FAIL (`assert len(chiamate) == 1` con 0 chiamate: nessun promemoria viene inviato)

- [ ] **Step 3: Implementare**

`custom_components/scadenze/notifiche.py`:

```python
"""Promemoria: pianificazione, invio, evento e riparazioni (spec §10.2)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, time
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_NOTIFICHE_ATTIVE,
    CONF_ORARIO_NOTIFICA,
    CONF_SERVIZIO_NOTIFICA,
    DOMAIN,
    EVENTO_PROMEMORIA,
    PREDEFINITO_ORARIO_NOTIFICA,
    PREDEFINITO_SERVIZIO_NOTIFICA,
)
from .coordinator import ScadenzeCoordinator
from .modello_dati import Scadenza, Stato
from .promemoria import Promemoria, valuta

_LOGGER = logging.getLogger(__name__)
VERSIONE_STORE = 1


class GestoreNotifiche:
    """Valuta le soglie una volta al giorno e invia notifica ed evento."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, coordinator: ScadenzeCoordinator
    ) -> None:
        self._hass = hass
        self._entry = entry
        self._coordinator = coordinator
        self._store: Store[dict[str, Any]] = Store(hass, VERSIONE_STORE, f"{DOMAIN}.{entry.entry_id}")
        self._memoria: dict[str, Any] = {}

    @property
    def orario(self) -> time:
        testo = self._entry.options.get(CONF_ORARIO_NOTIFICA, PREDEFINITO_ORARIO_NOTIFICA)
        return dt_util.parse_time(str(testo)) or time(9, 0)

    @property
    def issue_id(self) -> str:
        return f"servizio_notifica_mancante_{self._entry.entry_id}"

    async def async_carica(self) -> None:
        self._memoria = await self._store.async_load() or {}

    @callback
    def async_pianifica(self) -> Callable[[], None]:
        orario = self.orario

        async def _all_orario(_ora: datetime) -> None:
            await self.async_esegui()

        return async_track_time_change(
            self._hass, _all_orario, hour=orario.hour, minute=orario.minute, second=orario.second
        )

    async def async_esegui(self) -> None:
        """Ricalcola, invia i promemoria dovuti e salva la memoria."""
        self._coordinator.async_ricalcola()
        dati = self._coordinator.data
        preavvisi = self._coordinator.preavvisi
        memoria: dict[str, Any] = {}
        for subentry_id, scadenza in dati.scadenze.items():
            stato = dati.stati[subentry_id]
            esito = valuta(scadenza, stato, preavvisi, self._memoria.get(subentry_id))
            memoria[subentry_id] = esito.memoria
            if esito.promemoria is not None:
                await self._async_invia(subentry_id, scadenza, stato, esito.promemoria)
        self._memoria = memoria
        await self._store.async_save(memoria)

    async def _async_invia(
        self, subentry_id: str, scadenza: Scadenza, stato: Stato, promemoria: Promemoria
    ) -> None:
        voce = self._coordinator.voce
        self._hass.bus.async_fire(
            EVENTO_PROMEMORIA,
            {
                "voce": voce.nome,
                "voce_id": self._entry.entry_id,
                "scadenza": scadenza.nome,
                "scadenza_id": subentry_id,
                "modello": scadenza.modello,
                "data": scadenza.scadenza.isoformat() if scadenza.scadenza else None,
                "giorni_mancanti": stato.giorni_mancanti,
                "km_mancanti": stato.km_mancanti,
                "soglia": promemoria.soglia,
                "messaggio": promemoria.messaggio,
            },
        )

        opzioni = self._entry.options
        if not opzioni.get(CONF_NOTIFICHE_ATTIVE, True):
            return

        servizio = str(opzioni.get(CONF_SERVIZIO_NOTIFICA, PREDEFINITO_SERVIZIO_NOTIFICA))
        dominio, _, nome = servizio.partition(".")
        if not nome or not self._hass.services.has_service(dominio, nome):
            _LOGGER.warning(
                "Servizio di notifica %s non trovato: promemoria di %s non inviato", servizio, scadenza.nome
            )
            ir.async_create_issue(
                self._hass,
                DOMAIN,
                self.issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="servizio_notifica_mancante",
                translation_placeholders={"voce": voce.nome, "servizio": servizio},
            )
            return

        try:
            await self._hass.services.async_call(
                dominio,
                nome,
                {"title": f"{voce.nome} – {scadenza.nome}", "message": promemoria.messaggio},
                blocking=True,
            )
        except (HomeAssistantError, vol.Invalid) as err:
            _LOGGER.warning("Invio del promemoria di %s non riuscito: %s", scadenza.nome, err)
            return
        ir.async_delete_issue(self._hass, DOMAIN, self.issue_id)
```

`custom_components/scadenze/__init__.py`: sostituire l'intero file con:

```python
"""Scadenze Auto & Casa: scadenze italiane di veicoli, casa e documenti."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.util import dt as dt_util

from .const import DOMAIN, ETICHETTE_TIPO_VOCE
from .coordinator import ScadenzeCoordinator
from .notifiche import GestoreNotifiche

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CALENDAR,
    Platform.SENSOR,
    Platform.TODO,
]

type Firma = tuple[frozenset[tuple[str, str]], dict[str, Any], dict[str, Any]]


@dataclass
class ScadenzeRuntime:
    """Ciò che serve alle piattaforme di una voce caricata."""

    coordinator: ScadenzeCoordinator
    notifiche: GestoreNotifiche
    device_id_voce: str
    firma: Firma


type ScadenzeConfigEntry = ConfigEntry[ScadenzeRuntime]


def firma_entry(entry: ConfigEntry) -> Firma:
    """Se cambia, la entry va ricaricata: subentries (id e titolo), dati o opzioni."""
    return (
        frozenset((subentry_id, subentry.title) for subentry_id, subentry in entry.subentries.items()),
        dict(entry.data),
        dict(entry.options),
    )


async def async_setup_entry(hass: HomeAssistant, entry: ScadenzeConfigEntry) -> bool:
    coordinator = ScadenzeCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    dispositivo = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=coordinator.voce.nome,
        model=ETICHETTE_TIPO_VOCE[coordinator.voce.tipo],
        entry_type=dr.DeviceEntryType.SERVICE,
    )
    notifiche = GestoreNotifiche(hass, entry, coordinator)
    await notifiche.async_carica()
    entry.runtime_data = ScadenzeRuntime(
        coordinator=coordinator,
        notifiche=notifiche,
        device_id_voce=dispositivo.id,
        firma=firma_entry(entry),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    def _a_mezzanotte(_ora: datetime) -> None:
        coordinator.async_ricalcola()

    @callback
    def _km_cambiati(_evento: Event[EventStateChangedData]) -> None:
        coordinator.async_ricalcola()

    entry.async_on_unload(
        async_track_time_change(hass, _a_mezzanotte, hour=0, minute=0, second=5)
    )
    if coordinator.sensore_km:
        entry.async_on_unload(
            async_track_state_change_event(hass, [coordinator.sensore_km], _km_cambiati)
        )
    entry.async_on_unload(notifiche.async_pianifica())
    entry.async_on_unload(entry.add_update_listener(_async_entry_aggiornata))

    if dt_util.now().time() >= notifiche.orario:
        entry.async_create_task(hass, notifiche.async_esegui(), "scadenze: promemoria all'avvio")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ScadenzeConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_entry_aggiornata(hass: HomeAssistant, entry: ScadenzeConfigEntry) -> None:
    """Reload solo se servono entità o impostazioni nuove; altrimenti basta ricalcolare."""
    runtime = entry.runtime_data
    if firma_entry(entry) != runtime.firma:
        await hass.config_entries.async_reload(entry.entry_id)
        return
    runtime.coordinator.carica_scadenze()
    runtime.coordinator.async_ricalcola()
```

- [ ] **Step 4: Eseguire i test e verificare che passano**

Run: `pytest tests/ha -q`
Expected: PASS (anche `test_init.py`: a partire dalle 08:00 non parte nessun promemoria all'avvio)

- [ ] **Step 5: Commit**

```bash
git add custom_components/scadenze/notifiche.py custom_components/scadenze/__init__.py tests/ha/test_notifiche.py
git commit -m "feat: promemoria con notifica, evento e riparazione"
```

### Task 11: Flussi di configurazione e traduzioni

**Files:**
- Create: `custom_components/scadenze/config_flow.py`
- Create: `custom_components/scadenze/strings.json`, `custom_components/scadenze/translations/en.json`, `custom_components/scadenze/translations/it.json`
- Test: `tests/ha/test_config_flow.py`, `tests/logica/test_traduzioni.py`

**Interfaces:**
- Consumes: `const.*` (Task 1); `modello_dati.Voce`, `Scadenza` (Task 2); `modelli.*` (Task 4); `promemoria.analizza_preavvisi`, `formatta_preavvisi`, `PreavvisiNonValidi` (Task 5); `tests/ha/common.py` (Task 6).
- Produces:
  - `config_flow.py`: `class ScadenzeConfigFlow(ConfigFlow, domain=DOMAIN)` (passi `user` menu, `veicolo`, `casa`, `persona`, `generica`); `class ScadenzeOptionsFlow(OptionsFlow)` (passo `init`); `class ScadenzaSubentryFlow(ConfigSubentryFlow)` (passi `user`, `dettagli`, `reconfigure`).
  - Codici di errore: config `campo_obbligatorio`, `data_futura`; opzioni `servizio_non_trovato`, `preavvisi_non_validi`; subentry `campo_obbligatorio`, `data_non_valida`, `data_futura`, `intervallo_non_valido`, `scadenza_prima_della_nascita`.
  - Chiavi di traduzione dei selettori: `tipo_veicolo`, `modello`, `ricorrenza`.

- [ ] **Step 1: Scrivere i test che falliscono**

`tests/ha/test_config_flow.py`:

```python
"""Test dei flussi: nuova voce, opzioni, scadenza e riconfigurazione (spec §7)."""

from __future__ import annotations

from typing import Any

from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.scadenze.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .common import configura, crea_voce_veicolo


def suggerito(risultato: dict[str, Any], campo: str) -> Any:
    """Il valore precompilato di un campo in un form."""
    for chiave in risultato["data_schema"].schema:
        if chiave == campo:
            return (chiave.description or {}).get("suggested_value")
    raise AssertionError(f"campo {campo} assente dal form")


def opzioni_selettore(risultato: dict[str, Any], campo: str) -> list[str]:
    for chiave, selettore in risultato["data_schema"].schema.items():
        if chiave == campo:
            return list(selettore.config["options"])
    raise AssertionError(f"campo {campo} assente dal form")


async def avvia_voce(hass: HomeAssistant, tipo: str) -> dict[str, Any]:
    risultato = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert risultato["type"] is FlowResultType.MENU
    assert risultato["menu_options"] == ["veicolo", "casa", "persona", "generica"]
    return await hass.config_entries.flow.async_configure(risultato["flow_id"], {"next_step_id": tipo})


async def test_nuovo_veicolo(hass: HomeAssistant) -> None:
    form = await avvia_voce(hass, "veicolo")
    assert (form["type"], form["step_id"]) == (FlowResultType.FORM, "veicolo")

    risultato = await hass.config_entries.flow.async_configure(
        form["flow_id"], {"nome": "Panda", "tipo_veicolo": "auto", "immatricolazione": "2022-05-18"}
    )

    assert risultato["type"] is FlowResultType.CREATE_ENTRY
    assert risultato["title"] == "Panda"
    assert risultato["data"] == {
        "tipo": "veicolo",
        "nome": "Panda",
        "tipo_veicolo": "auto",
        "immatricolazione": "2022-05-01",
    }


async def test_immatricolazione_futura(hass: HomeAssistant) -> None:
    form = await avvia_voce(hass, "veicolo")
    risultato = await hass.config_entries.flow.async_configure(
        form["flow_id"], {"nome": "Panda", "tipo_veicolo": "auto", "immatricolazione": "2026-10-01"}
    )
    assert risultato["errors"] == {"immatricolazione": "data_futura"}


async def test_nuova_persona_casa_e_generica(hass: HomeAssistant) -> None:
    form = await avvia_voce(hass, "persona")
    persona = await hass.config_entries.flow.async_configure(
        form["flow_id"], {"nome": "Mario", "data_nascita": "1990-05-08"}
    )
    assert persona["data"] == {"tipo": "persona", "nome": "Mario", "data_nascita": "1990-05-08"}

    for tipo, nome in (("casa", "Casa al mare"), ("generica", "Abbonamenti")):
        form = await avvia_voce(hass, tipo)
        risultato = await hass.config_entries.flow.async_configure(form["flow_id"], {"nome": nome})
        assert risultato["data"] == {"tipo": tipo, "nome": nome}


async def test_opzioni_del_veicolo(hass: HomeAssistant) -> None:
    async_mock_service(hass, "notify", "telefono")
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    form = await hass.config_entries.options.async_init(entry.entry_id)
    assert form["step_id"] == "init"
    assert suggerito(form, "preavvisi") == "30, 7, 1"

    risultato = await hass.config_entries.options.async_configure(
        form["flow_id"],
        {
            "sensore_km": "sensor.panda_km",
            "notifiche_attive": True,
            "servizio_notifica": "notify.telefono",
            "preavvisi": "7, 30",
            "orario_notifica": "08:30:00",
        },
    )
    await hass.async_block_till_done()

    assert risultato["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {
        "sensore_km": "sensor.panda_km",
        "notifiche_attive": True,
        "servizio_notifica": "notify.telefono",
        "preavvisi": [30, 7],
        "orario_notifica": "08:30:00",
    }


async def test_opzioni_con_errori(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    form = await hass.config_entries.options.async_init(entry.entry_id)
    risultato = await hass.config_entries.options.async_configure(
        form["flow_id"],
        {
            "notifiche_attive": True,
            "servizio_notifica": "notify.inesistente",
            "preavvisi": "30, mille",
            "orario_notifica": "09:00:00",
        },
    )
    assert risultato["errors"] == {
        "servizio_notifica": "servizio_non_trovato",
        "preavvisi": "preavvisi_non_validi",
    }


async def test_nuova_scadenza_precompilata(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    scelta = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "scadenza"), context={"source": SOURCE_USER}
    )
    assert opzioni_selettore(scelta, "modello") == [
        "revisione", "bollo", "assicurazione", "tagliando", "gomme", "personalizzata",
    ]
    form = await hass.config_entries.subentries.async_configure(scelta["flow_id"], {"modello": "revisione"})
    assert form["step_id"] == "dettagli"
    assert suggerito(form, "nome") == "Revisione"
    assert suggerito(form, "scadenza") == "2028-05-31"

    risultato = await hass.config_entries.subentries.async_configure(
        form["flow_id"], {"nome": "Revisione 2028", "scadenza": "2028-05-31"}
    )
    await hass.async_block_till_done()

    assert risultato["type"] is FlowResultType.CREATE_ENTRY
    nuova = next(s for s in entry.subentries.values() if s.title == "Revisione 2028")
    assert (nuova.data["regola"], nuova.data["scadenza"]) == ("fine_mese", "2028-05-31")


async def test_scadenza_con_data_futura(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    scelta = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "scadenza"), context={"source": SOURCE_USER}
    )
    form = await hass.config_entries.subentries.async_configure(scelta["flow_id"], {"modello": "tagliando"})
    risultato = await hass.config_entries.subentries.async_configure(
        form["flow_id"],
        {
            "nome": "Tagliando",
            "ultimo_rinnovo": "2026-09-15",
            "km_ultimo_rinnovo": 0,
            "intervallo_mesi": 12,
            "intervallo_km": 15000,
        },
    )
    assert risultato["errors"] == {"ultimo_rinnovo": "data_futura"}


async def test_riconfigurare_una_scadenza(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    form = await entry.start_subentry_reconfigure_flow(hass, "sub_bollo")
    assert form["step_id"] == "dettagli"
    assert suggerito(form, "mese_scadenza_bollo") == "2026-09-01"

    risultato = await hass.config_entries.subentries.async_configure(
        form["flow_id"], {"nome": "Bollo Panda", "mese_scadenza_bollo": "2026-11-01"}
    )
    await hass.async_block_till_done()

    assert risultato["type"] is FlowResultType.ABORT
    assert risultato["reason"] == "reconfigure_successful"
    bollo = entry.subentries["sub_bollo"]
    assert (bollo.title, bollo.data["scadenza"]) == ("Bollo Panda", "2026-12-31")


async def test_una_voce_generica_offre_solo_la_personalizzata(hass: HomeAssistant) -> None:
    form = await avvia_voce(hass, "generica")
    creata = await hass.config_entries.flow.async_configure(form["flow_id"], {"nome": "Abbonamenti"})
    await hass.async_block_till_done()

    scelta = await hass.config_entries.subentries.async_init(
        (creata["result"].entry_id, "scadenza"), context={"source": SOURCE_USER}
    )
    assert opzioni_selettore(scelta, "modello") == ["personalizzata"]
```

`tests/logica/test_traduzioni.py`:

```python
"""Coerenza dei file di traduzione (li legge solo come JSON: nessun import di HA)."""

from __future__ import annotations

from collections.abc import Iterator
import json
from pathlib import Path
from typing import Any

from custom_components.scadenze.modelli import MODELLI

CARTELLA = Path(__file__).resolve().parents[2] / "custom_components" / "scadenze"
ERRORI_SCADENZA = {
    "campo_obbligatorio",
    "data_non_valida",
    "data_futura",
    "intervallo_non_valido",
    "scadenza_prima_della_nascita",
}


def _carica(nome: str) -> dict[str, Any]:
    percorso = CARTELLA / nome if nome == "strings.json" else CARTELLA / "translations" / nome
    return json.loads(percorso.read_text(encoding="utf-8"))


def _chiavi(nodo: Any, prefisso: str = "") -> Iterator[str]:
    if isinstance(nodo, dict):
        for chiave, valore in nodo.items():
            yield from _chiavi(valore, f"{prefisso}.{chiave}" if prefisso else chiave)
    else:
        yield prefisso


def test_strings_json_uguale_all_inglese() -> None:
    assert _carica("strings.json") == _carica("en.json")


def test_italiano_con_le_stesse_chiavi_dell_inglese() -> None:
    assert set(_chiavi(_carica("it.json"))) == set(_chiavi(_carica("en.json")))


def test_ogni_modello_ha_un_nome_tradotto() -> None:
    for lingua in ("en.json", "it.json"):
        assert set(_carica(lingua)["selector"]["modello"]["options"]) == set(MODELLI)


def test_errori_dei_form_tradotti() -> None:
    errori = _carica("en.json")["config_subentries"]["scadenza"]["error"]
    assert ERRORI_SCADENZA <= set(errori)
```

- [ ] **Step 2: Eseguire i test e verificare che falliscono**

Run: `pytest tests/ha/test_config_flow.py tests/logica/test_traduzioni.py -q`
Expected: FAIL (`Flow handler not found` per `scadenze`; `FileNotFoundError` per `strings.json`)

- [ ] **Step 3: Implementare i flussi**

`custom_components/scadenze/config_flow.py`:

```python
"""Flussi di configurazione: voce, opzioni della voce e scadenze (spec §7)."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_USER,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DATA_NASCITA,
    CONF_IMMATRICOLAZIONE,
    CONF_NOME,
    CONF_NOTIFICHE_ATTIVE,
    CONF_ORARIO_NOTIFICA,
    CONF_PREAVVISI,
    CONF_SENSORE_KM,
    CONF_SERVIZIO_NOTIFICA,
    CONF_TIPO,
    CONF_TIPO_VEICOLO,
    DOMAIN,
    PREDEFINITO_ORARIO_NOTIFICA,
    PREDEFINITO_PREAVVISI,
    PREDEFINITO_SERVIZIO_NOTIFICA,
    SUBENTRY_SCADENZA,
    TIPI_VOCE,
    TIPO_CASA,
    TIPO_GENERICA,
    TIPO_PERSONA,
    TIPO_VEICOLO,
    VEICOLO_AUTO,
    VEICOLO_MOTO,
)
from .modelli import (
    CAMPO_INTERVALLO_KM,
    CAMPO_INTERVALLO_MESI,
    CAMPO_KM_ULTIMO_RINNOVO,
    CAMPO_MESE_SCADENZA_BOLLO,
    CAMPO_MODELLO,
    CAMPO_NOME,
    CAMPO_RICORRENZA,
    CAMPO_SCADENZA,
    CAMPO_ULTIMO_RINNOVO,
    MODELLI,
    RICORRENZE,
    ErroreForm,
    costruisci_scadenza,
    modelli_per_tipo,
    valori_da_scadenza,
    valori_suggeriti,
)
from .modello_dati import Scadenza, Voce
from .promemoria import PreavvisiNonValidi, analizza_preavvisi, formatta_preavvisi

_SCHEMA_SOLO_NOME = vol.Schema({vol.Required(CONF_NOME): selector.TextSelector()})


def _numero(minimo: int, massimo: int, unita: str) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=minimo,
            max=massimo,
            step=1,
            mode=selector.NumberSelectorMode.BOX,
            unit_of_measurement=unita,
        )
    )


_SELETTORI_CAMPI: dict[str, Any] = {
    CAMPO_SCADENZA: selector.DateSelector(),
    CAMPO_MESE_SCADENZA_BOLLO: selector.DateSelector(),
    CAMPO_ULTIMO_RINNOVO: selector.DateSelector(),
    CAMPO_INTERVALLO_MESI: _numero(1, 240, "mesi"),
    CAMPO_KM_ULTIMO_RINNOVO: _numero(0, 2_000_000, "km"),
    CAMPO_INTERVALLO_KM: _numero(0, 100_000, "km"),
    CAMPO_RICORRENZA: selector.SelectSelector(
        selector.SelectSelectorConfig(options=list(RICORRENZE), translation_key=CAMPO_RICORRENZA)
    ),
}


def _schema_dettagli(chiave: str) -> vol.Schema:
    campi: dict[Any, Any] = {vol.Required(CAMPO_NOME): selector.TextSelector()}
    for campo in MODELLI[chiave].campi:
        campi[vol.Required(campo)] = _SELETTORI_CAMPI[campo]
    return vol.Schema(campi)


def _schema_opzioni(veicolo: bool) -> vol.Schema:
    campi: dict[Any, Any] = {}
    if veicolo:
        campi[vol.Optional(CONF_SENSORE_KM)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
    campi[vol.Required(CONF_NOTIFICHE_ATTIVE)] = selector.BooleanSelector()
    campi[vol.Required(CONF_SERVIZIO_NOTIFICA)] = selector.TextSelector()
    campi[vol.Optional(CONF_PREAVVISI, default="")] = selector.TextSelector()
    campi[vol.Required(CONF_ORARIO_NOTIFICA)] = selector.TimeSelector()
    return vol.Schema(campi)


class ScadenzeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Crea una voce: veicolo, casa, persona o generica."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return ScadenzeOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_SCADENZA: ScadenzaSubentryFlow}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(step_id="user", menu_options=list(TIPI_VOCE))

    async def async_step_veicolo(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        schema = vol.Schema(
            {
                vol.Required(CONF_NOME): selector.TextSelector(),
                vol.Required(CONF_TIPO_VEICOLO, default=VEICOLO_AUTO): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[VEICOLO_AUTO, VEICOLO_MOTO], translation_key=CONF_TIPO_VEICOLO
                    )
                ),
                vol.Required(CONF_IMMATRICOLAZIONE): selector.DateSelector(),
            }
        )
        return self._passo_voce(TIPO_VEICOLO, schema, user_input, CONF_IMMATRICOLAZIONE)

    async def async_step_casa(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self._passo_voce(TIPO_CASA, _SCHEMA_SOLO_NOME, user_input)

    async def async_step_persona(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        schema = vol.Schema(
            {
                vol.Required(CONF_NOME): selector.TextSelector(),
                vol.Required(CONF_DATA_NASCITA): selector.DateSelector(),
            }
        )
        return self._passo_voce(TIPO_PERSONA, schema, user_input, CONF_DATA_NASCITA)

    async def async_step_generica(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self._passo_voce(TIPO_GENERICA, _SCHEMA_SOLO_NOME, user_input)

    def _passo_voce(
        self,
        tipo: str,
        schema: vol.Schema,
        user_input: dict[str, Any] | None,
        campo_data: str | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            dati: dict[str, Any] = {CONF_TIPO: tipo, **user_input}
            dati[CONF_NOME] = str(user_input.get(CONF_NOME, "")).strip()
            if not dati[CONF_NOME]:
                errors[CONF_NOME] = "campo_obbligatorio"
            if campo_data is not None:
                giorno = date.fromisoformat(str(user_input[campo_data]))
                if tipo == TIPO_VEICOLO:
                    giorno = giorno.replace(day=1)
                if giorno > dt_util.now().date():
                    errors[campo_data] = "data_futura"
                dati[campo_data] = giorno.isoformat()
            if not errors:
                return self.async_create_entry(title=dati[CONF_NOME], data=dati)
        return self.async_show_form(
            step_id=tipo,
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
        )


class ScadenzeOptionsFlow(OptionsFlow):
    """Sensore km (veicoli) e promemoria di una voce."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self.config_entry
        errors: dict[str, str] = {}
        if user_input is not None:
            opzioni = dict(user_input)
            try:
                opzioni[CONF_PREAVVISI] = analizza_preavvisi(str(user_input.get(CONF_PREAVVISI, "")))
            except PreavvisiNonValidi:
                errors[CONF_PREAVVISI] = "preavvisi_non_validi"
            servizio = str(user_input.get(CONF_SERVIZIO_NOTIFICA, "")).strip()
            opzioni[CONF_SERVIZIO_NOTIFICA] = servizio
            dominio, _, nome = servizio.partition(".")
            if user_input.get(CONF_NOTIFICHE_ATTIVE) and (
                not nome or not self.hass.services.has_service(dominio, nome)
            ):
                errors[CONF_SERVIZIO_NOTIFICA] = "servizio_non_trovato"
            if not errors:
                return self.async_create_entry(data=opzioni)
            valori = user_input
        else:
            valori = {
                CONF_NOTIFICHE_ATTIVE: True,
                CONF_SERVIZIO_NOTIFICA: PREDEFINITO_SERVIZIO_NOTIFICA,
                CONF_ORARIO_NOTIFICA: PREDEFINITO_ORARIO_NOTIFICA,
                **entry.options,
                CONF_PREAVVISI: formatta_preavvisi(entry.options.get(CONF_PREAVVISI, PREDEFINITO_PREAVVISI)),
            }
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                _schema_opzioni(entry.data.get(CONF_TIPO) == TIPO_VEICOLO), valori
            ),
            errors=errors,
        )


class ScadenzaSubentryFlow(ConfigSubentryFlow):
    """Aggiunge o riconfigura una scadenza di una voce."""

    def __init__(self) -> None:
        self._modello: str | None = None

    def _voce(self) -> Voce:
        return Voce.da_dict(self._get_entry().data)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        if user_input is not None:
            self._modello = user_input[CAMPO_MODELLO]
            return await self.async_step_dettagli()
        schema = vol.Schema(
            {
                vol.Required(CAMPO_MODELLO): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=modelli_per_tipo(self._voce().tipo),
                        translation_key=CAMPO_MODELLO,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        self._modello = self._get_reconfigure_subentry().data["modello"]
        return await self.async_step_dettagli()

    async def async_step_dettagli(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        assert self._modello is not None
        chiave = self._modello
        voce = self._voce()
        oggi = dt_util.now().date()
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                scadenza = costruisci_scadenza(chiave, user_input, voce, oggi)
            except ErroreForm as err:
                errors[err.campo] = err.codice
            else:
                if self.source == SOURCE_USER:
                    return self.async_create_entry(title=scadenza.nome, data=scadenza.a_dict())
                subentry = self._get_reconfigure_subentry()
                precedente = Scadenza.da_dict(subentry.data)
                if scadenza.ultimo_rinnovo is None:
                    scadenza = replace(scadenza, ultimo_rinnovo=precedente.ultimo_rinnovo)
                return self.async_update_and_abort(
                    self._get_entry(), subentry, title=scadenza.nome, data=scadenza.a_dict()
                )
            valori: dict[str, Any] = user_input
        elif self.source == SOURCE_USER:
            valori = valori_suggeriti(chiave, voce, oggi)
        else:
            valori = valori_da_scadenza(Scadenza.da_dict(self._get_reconfigure_subentry().data))

        return self.async_show_form(
            step_id="dettagli",
            data_schema=self.add_suggested_values_to_schema(_schema_dettagli(chiave), valori),
            errors=errors,
            description_placeholders={"modello": MODELLI[chiave].etichetta},
        )
```

- [ ] **Step 4: Scrivere le traduzioni**

`custom_components/scadenze/translations/en.json` (e `custom_components/scadenze/strings.json` con **lo stesso identico contenuto**):

```json
{
  "config": {
    "step": {
      "user": {
        "title": "What has deadlines?",
        "menu_options": {
          "veicolo": "A vehicle",
          "casa": "A home",
          "persona": "A person",
          "generica": "Something else"
        }
      },
      "veicolo": {
        "title": "New vehicle",
        "data": {
          "nome": "Name",
          "tipo_veicolo": "Vehicle type",
          "immatricolazione": "First registration"
        },
        "data_description": {
          "immatricolazione": "Only month and year matter: the first inspection is due four years later."
        }
      },
      "casa": {
        "title": "New home",
        "data": {
          "nome": "Name"
        }
      },
      "persona": {
        "title": "New person",
        "data": {
          "nome": "Name",
          "data_nascita": "Date of birth"
        },
        "data_description": {
          "data_nascita": "Used to calculate when the driving licence and the identity card expire."
        }
      },
      "generica": {
        "title": "New item",
        "data": {
          "nome": "Name"
        }
      }
    },
    "error": {
      "campo_obbligatorio": "This field is required.",
      "data_futura": "The date cannot be in the future."
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Reminders",
        "data": {
          "sensore_km": "Odometer sensor",
          "notifiche_attive": "Send notifications",
          "servizio_notifica": "Notify service",
          "preavvisi": "Advance notice (days)",
          "orario_notifica": "Time of day"
        },
        "data_description": {
          "sensore_km": "A sensor with the vehicle's total kilometres, used by the service deadline.",
          "servizio_notifica": "For example notify.mobile_app_phone. The scadenze_promemoria event is fired anyway.",
          "preavvisi": "Days before the deadline, separated by commas, for example 30, 7, 1."
        }
      }
    },
    "error": {
      "servizio_non_trovato": "This notify service does not exist.",
      "preavvisi_non_validi": "Use whole numbers between 1 and 365, separated by commas."
    }
  },
  "config_subentries": {
    "scadenza": {
      "entry_type": "Deadline",
      "initiate_flow": {
        "user": "Add deadline",
        "reconfigure": "Edit deadline"
      },
      "step": {
        "user": {
          "title": "Choose the deadline",
          "data": {
            "modello": "Deadline type"
          }
        },
        "dettagli": {
          "title": "{modello}",
          "data": {
            "nome": "Name",
            "scadenza": "Due date",
            "mese_scadenza_bollo": "Month the road tax expires",
            "ultimo_rinnovo": "Last done on",
            "intervallo_mesi": "Every how many months",
            "km_ultimo_rinnovo": "Kilometres at the last service",
            "intervallo_km": "Every how many kilometres",
            "ricorrenza": "Repeats"
          },
          "data_description": {
            "scadenza": "Suggested dates come from the rules: check them against your documents.",
            "mese_scadenza_bollo": "The expiry month on the last receipt. Payment is due by the end of the following month.",
            "intervallo_km": "0 disables the kilometre limit."
          }
        }
      },
      "error": {
        "campo_obbligatorio": "This field is required.",
        "data_non_valida": "This date is not valid.",
        "data_futura": "The date cannot be in the future.",
        "intervallo_non_valido": "The value is out of range.",
        "scadenza_prima_della_nascita": "The due date is before the date of birth."
      },
      "abort": {
        "reconfigure_successful": "Deadline updated."
      }
    }
  },
  "selector": {
    "tipo_veicolo": {
      "options": {
        "auto": "Car",
        "moto": "Motorcycle"
      }
    },
    "modello": {
      "options": {
        "revisione": "Vehicle inspection (revisione)",
        "bollo": "Road tax (bollo)",
        "assicurazione": "Insurance",
        "tagliando": "Service",
        "gomme": "Tyre change",
        "manutenzione_caldaia": "Boiler maintenance",
        "controllo_fumi": "Boiler emissions check",
        "climatizzatore": "Air conditioner cleaning",
        "estintore": "Fire extinguisher check",
        "filtri_acqua": "Water filter change",
        "canna_fumaria": "Chimney sweeping",
        "carta_identita": "Identity card",
        "patente": "Driving licence",
        "passaporto": "Passport",
        "tessera_sanitaria": "Health insurance card",
        "personalizzata": "Custom"
      }
    },
    "ricorrenza": {
      "options": {
        "nessuna": "Does not repeat",
        "dalla_scadenza": "Every N months from the due date",
        "dal_rinnovo": "Every N months from when it is done"
      }
    }
  },
  "entity": {
    "sensor": {
      "giorni_mancanti": {
        "name": "Days left"
      },
      "km_mancanti": {
        "name": "Kilometres left"
      }
    },
    "binary_sensor": {
      "in_scadenza": {
        "name": "Due soon"
      }
    },
    "button": {
      "rinnovato": {
        "name": "Renewed"
      }
    },
    "calendar": {
      "calendario": {
        "name": "Deadlines"
      }
    },
    "todo": {
      "da_rinnovare": {
        "name": "To renew"
      }
    }
  },
  "issues": {
    "servizio_notifica_mancante": {
      "title": "Notify service not found for {voce}",
      "description": "Scadenze Auto & Casa could not send a reminder because {servizio} does not exist. Open the options of {voce} and choose an existing notify service."
    }
  }
}
```

`custom_components/scadenze/translations/it.json`:

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Che cosa ha delle scadenze?",
        "menu_options": {
          "veicolo": "Un veicolo",
          "casa": "Una casa",
          "persona": "Una persona",
          "generica": "Altro"
        }
      },
      "veicolo": {
        "title": "Nuovo veicolo",
        "data": {
          "nome": "Nome",
          "tipo_veicolo": "Tipo di veicolo",
          "immatricolazione": "Prima immatricolazione"
        },
        "data_description": {
          "immatricolazione": "Contano solo mese e anno: la prima revisione cade quattro anni dopo."
        }
      },
      "casa": {
        "title": "Nuova casa",
        "data": {
          "nome": "Nome"
        }
      },
      "persona": {
        "title": "Nuova persona",
        "data": {
          "nome": "Nome",
          "data_nascita": "Data di nascita"
        },
        "data_description": {
          "data_nascita": "Serve a calcolare quando scadono patente e carta d'identità."
        }
      },
      "generica": {
        "title": "Nuova voce",
        "data": {
          "nome": "Nome"
        }
      }
    },
    "error": {
      "campo_obbligatorio": "Questo campo è obbligatorio.",
      "data_futura": "La data non può essere nel futuro."
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Promemoria",
        "data": {
          "sensore_km": "Sensore del contachilometri",
          "notifiche_attive": "Invia notifiche",
          "servizio_notifica": "Servizio di notifica",
          "preavvisi": "Preavvisi (giorni)",
          "orario_notifica": "Orario"
        },
        "data_description": {
          "sensore_km": "Un sensore con i chilometri totali del veicolo, usato dal tagliando.",
          "servizio_notifica": "Per esempio notify.mobile_app_telefono. L'evento scadenze_promemoria parte comunque.",
          "preavvisi": "Giorni prima della scadenza, separati da virgole, per esempio 30, 7, 1."
        }
      }
    },
    "error": {
      "servizio_non_trovato": "Questo servizio di notifica non esiste.",
      "preavvisi_non_validi": "Usa numeri interi fra 1 e 365, separati da virgole."
    }
  },
  "config_subentries": {
    "scadenza": {
      "entry_type": "Scadenza",
      "initiate_flow": {
        "user": "Aggiungi scadenza",
        "reconfigure": "Modifica scadenza"
      },
      "step": {
        "user": {
          "title": "Scegli la scadenza",
          "data": {
            "modello": "Tipo di scadenza"
          }
        },
        "dettagli": {
          "title": "{modello}",
          "data": {
            "nome": "Nome",
            "scadenza": "Data di scadenza",
            "mese_scadenza_bollo": "Mese di scadenza del bollo",
            "ultimo_rinnovo": "Ultima volta il",
            "intervallo_mesi": "Ogni quanti mesi",
            "km_ultimo_rinnovo": "Chilometri all'ultimo tagliando",
            "intervallo_km": "Ogni quanti chilometri",
            "ricorrenza": "Si ripete"
          },
          "data_description": {
            "scadenza": "Le date suggerite vengono dalle regole: controllale con i tuoi documenti.",
            "mese_scadenza_bollo": "Il mese di scadenza sull'ultima ricevuta. Si paga entro la fine del mese successivo.",
            "intervallo_km": "0 disattiva il limite in chilometri."
          }
        }
      },
      "error": {
        "campo_obbligatorio": "Questo campo è obbligatorio.",
        "data_non_valida": "Questa data non è valida.",
        "data_futura": "La data non può essere nel futuro.",
        "intervallo_non_valido": "Il valore è fuori dall'intervallo ammesso.",
        "scadenza_prima_della_nascita": "La scadenza è precedente alla data di nascita."
      },
      "abort": {
        "reconfigure_successful": "Scadenza aggiornata."
      }
    }
  },
  "selector": {
    "tipo_veicolo": {
      "options": {
        "auto": "Auto",
        "moto": "Moto"
      }
    },
    "modello": {
      "options": {
        "revisione": "Revisione",
        "bollo": "Bollo",
        "assicurazione": "Assicurazione",
        "tagliando": "Tagliando",
        "gomme": "Cambio gomme",
        "manutenzione_caldaia": "Manutenzione caldaia",
        "controllo_fumi": "Controllo fumi caldaia",
        "climatizzatore": "Pulizia climatizzatore",
        "estintore": "Controllo estintore",
        "filtri_acqua": "Cambio filtri acqua",
        "canna_fumaria": "Pulizia canna fumaria",
        "carta_identita": "Carta d'identità",
        "patente": "Patente",
        "passaporto": "Passaporto",
        "tessera_sanitaria": "Tessera sanitaria",
        "personalizzata": "Personalizzata"
      }
    },
    "ricorrenza": {
      "options": {
        "nessuna": "Non si ripete",
        "dalla_scadenza": "Ogni N mesi dalla scadenza",
        "dal_rinnovo": "Ogni N mesi da quando la fai"
      }
    }
  },
  "entity": {
    "sensor": {
      "giorni_mancanti": {
        "name": "Giorni mancanti"
      },
      "km_mancanti": {
        "name": "Km mancanti"
      }
    },
    "binary_sensor": {
      "in_scadenza": {
        "name": "In scadenza"
      }
    },
    "button": {
      "rinnovato": {
        "name": "Rinnovato"
      }
    },
    "calendar": {
      "calendario": {
        "name": "Scadenze"
      }
    },
    "todo": {
      "da_rinnovare": {
        "name": "Da rinnovare"
      }
    }
  },
  "issues": {
    "servizio_notifica_mancante": {
      "title": "Servizio di notifica non trovato per {voce}",
      "description": "Scadenze Auto & Casa non ha potuto inviare un promemoria perché {servizio} non esiste. Apri le opzioni di {voce} e scegli un servizio di notifica esistente."
    }
  }
}
```

- [ ] **Step 5: Eseguire i test e verificare che passano**

Run: `pytest tests/logica -q` (ambiente di logica) e `pytest -q` (ambiente completo)
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add custom_components/scadenze/config_flow.py custom_components/scadenze/strings.json custom_components/scadenze/translations tests/ha/test_config_flow.py tests/logica/test_traduzioni.py
git commit -m "feat: flussi di configurazione e traduzioni"
```

### Task 12: Blueprint, distribuzione e verifica finale

**Files:**
- Create: `blueprints/automation/scadenze/promemoria_scadenze.yaml`, `hacs.json`, `README.md`, `LICENSE`, `.github/workflows/validate.yml`
- Test: `tests/ha/test_blueprint.py`

**Interfaces:**
- Consumes: evento `scadenze_promemoria` e i suoi dati (Task 10).
- Produces: repository pronto per HACS (categoria integration) con CI.

- [ ] **Step 1: Scrivere il test che fallisce**

`tests/ha/test_blueprint.py`:

```python
"""La blueprint ascolta l'evento dei promemoria (spec §10.3)."""

from __future__ import annotations

from pathlib import Path

from homeassistant.util.yaml import load_yaml
from homeassistant.util.yaml.objects import Input

PERCORSO = (
    Path(__file__).resolve().parents[2]
    / "blueprints"
    / "automation"
    / "scadenze"
    / "promemoria_scadenze.yaml"
)


def test_blueprint_ascolta_l_evento_dei_promemoria() -> None:
    dati = load_yaml(PERCORSO)
    assert dati["blueprint"]["domain"] == "automation"
    assert set(dati["blueprint"]["input"]) == {"voce", "azioni"}
    assert dati["triggers"] == [{"trigger": "event", "event_type": "scadenze_promemoria"}]
    assert isinstance(dati["actions"], Input)
```

- [ ] **Step 2: Eseguire il test e verificare che fallisce**

Run: `pytest tests/ha/test_blueprint.py -q`
Expected: FAIL con `FileNotFoundError` sul file della blueprint

- [ ] **Step 3: Scrivere blueprint e file di distribuzione**

`blueprints/automation/scadenze/promemoria_scadenze.yaml`:

```yaml
blueprint:
  name: Promemoria delle scadenze
  description: >-
    Esegue le azioni che scegli quando Scadenze Auto & Casa segnala una scadenza.
    Nelle azioni puoi usare trigger.event.data.messaggio, trigger.event.data.voce
    e trigger.event.data.scadenza.
  domain: automation
  source_url: https://github.com/iAlias/scadenze-auto-casa/blob/main/blueprints/automation/scadenze/promemoria_scadenze.yaml
  input:
    voce:
      name: Voce
      description: Il nome della voce da seguire. Vuoto = tutte le voci.
      default: ""
      selector:
        text: {}
    azioni:
      name: Azioni
      description: Cosa fare quando arriva un promemoria.
      selector:
        action: {}

mode: queued

triggers:
  - trigger: event
    event_type: scadenze_promemoria

variables:
  voce_seguita: !input voce

conditions:
  - condition: template
    value_template: "{{ voce_seguita == '' or trigger.event.data.voce == voce_seguita }}"

actions: !input azioni
```

`hacs.json`:

```json
{
  "name": "Scadenze Auto & Casa",
  "homeassistant": "2026.8.0",
  "render_readme": true,
  "country": ["IT"]
}
```

`LICENSE`:

```text
MIT License

Copyright (c) 2026 iAlias

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

`.github/workflows/validate.yml`:

```yaml
name: Validate

on:
  push:
  pull_request:
  workflow_dispatch:

jobs:
  hassfest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: home-assistant/actions/hassfest@master

  hacs:
    runs-on: ubuntu-latest
    steps:
      - uses: hacs/action@main
        with:
          category: integration
          ignore: brands description topics

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: "3.14"
      - run: pip install -r requirements_test.txt
      - run: pytest -q
```

`README.md`:

````markdown
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
2. Aggiungi `https://github.com/iAlias/scadenze-auto-casa` con categoria **Integration**
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
````

- [ ] **Step 4: Eseguire tutti i test**

Run: `pytest -q` (ambiente completo)
Expected: PASS, nessun errore né avviso di deprecazione dei dispositivi

- [ ] **Step 5: Verificare che i moduli puri non importino Home Assistant**

Run:

```bash
grep -n "homeassistant" custom_components/scadenze/const.py custom_components/scadenze/date_utils.py custom_components/scadenze/modello_dati.py custom_components/scadenze/regole.py custom_components/scadenze/modelli.py custom_components/scadenze/promemoria.py
```

Expected: nessuna riga in uscita

- [ ] **Step 6: Commit**

```bash
git add blueprints hacs.json README.md LICENSE .github tests/ha/test_blueprint.py
git commit -m "feat: blueprint, README, licenza e CI"
```

- [ ] **Step 7: Verifica in CI**

Quando il repository viene pubblicato su GitHub (decisione dell'utente), controllare che i tre job di `Validate` (hassfest, hacs, test) siano verdi. Se hassfest segnala chiavi di traduzione mancanti o in eccesso, correggere `strings.json` e le due traduzioni insieme e rieseguire `pytest tests/logica/test_traduzioni.py -q`.

---

## Note di esecuzione (2026-09-14)

- Lavoro svolto nel worktree `.claude/worktrees/fase-1`, branch locale `worktree-fase-1`, pubblicato come `fase-1` su
  `https://github.com/iAlias/scadenze-auto-casa-salute` (privato).
- Task 1–5 verificati in locale (Windows, `.venv-logica`): 131 test verdi.
- I test HA non girano su Windows (`fcntl` e DLL bloccate): i task 6–12 sono verificati in CI.
- Deviazioni dall'ordine del piano:
  - il job `test` di `.github/workflows/validate.yml` è stato aggiunto dopo il task 6; hassfest e HACS col task 12;
  - il task 11 (`config_flow.py` e traduzioni) è stato committato prima del task 10, perché il setup delle entry
    richiede la piattaforma `config_flow` (spec §16.2);
  - `.gitignore` include anche `.claude/`, dove vivono i worktree;
  - `tests/ha/common.py::configura` riporta stato e motivo della entry quando il setup fallisce.
