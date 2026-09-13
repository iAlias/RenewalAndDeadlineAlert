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
