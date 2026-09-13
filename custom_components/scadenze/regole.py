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
