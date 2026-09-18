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
    modelli_raccomandati,
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


def test_modelli_raccomandati_esclude_personalizzata() -> None:
    assert modelli_raccomandati("veicolo") == [
        "revisione", "bollo", "assicurazione", "tagliando", "gomme",
    ]
    assert modelli_raccomandati("casa") == [
        "manutenzione_caldaia",
        "controllo_fumi",
        "climatizzatore",
        "estintore",
        "filtri_acqua",
        "canna_fumaria",
    ]
    assert modelli_raccomandati("persona") == [
        "carta_identita", "patente", "passaporto", "tessera_sanitaria",
    ]
    assert modelli_raccomandati("generica") == []
