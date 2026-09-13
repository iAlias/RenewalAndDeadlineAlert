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
