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
