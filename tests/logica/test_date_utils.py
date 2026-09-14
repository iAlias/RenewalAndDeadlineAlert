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
