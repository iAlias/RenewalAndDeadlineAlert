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
