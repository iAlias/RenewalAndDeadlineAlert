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
