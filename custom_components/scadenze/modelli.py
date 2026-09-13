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
