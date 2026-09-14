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
