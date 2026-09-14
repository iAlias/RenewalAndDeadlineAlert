"""Coordinator: tiene in memoria voce e scadenze e ricalcola gli stati."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_PREAVVISI,
    CONF_SENSORE_KM,
    DOMAIN,
    PREDEFINITO_PREAVVISI,
    SUBENTRY_SCADENZA,
    TIPO_VEICOLO,
)
from .modello_dati import DatiNonValidi, Scadenza, Stato, Voce
from .regole import RinnovoIgnorato, calcola_stato, rinnova

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatiScadenze:
    """Fotografia di un ricalcolo: le scadenze e il loro stato in un giorno."""

    oggi: date
    km_attuali: int | None
    scadenze: dict[str, Scadenza]
    stati: dict[str, Stato]


class ScadenzeCoordinator(DataUpdateCoordinator[DatiScadenze]):
    """Nessun polling: ricalcola quando arriva un trigger (spec §9)."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=None,
        )
        self.voce = Voce.da_dict(entry.data)
        self.scadenze: dict[str, Scadenza] = {}
        self._ultimi_km: int | None = None
        self.carica_scadenze()

    @property
    def sensore_km(self) -> str | None:
        """Il sensore del contachilometri, solo per i veicoli."""
        if self.voce.tipo != TIPO_VEICOLO:
            return None
        return self.config_entry.options.get(CONF_SENSORE_KM) or None

    @property
    def preavvisi(self) -> list[int]:
        return [int(p) for p in self.config_entry.options.get(CONF_PREAVVISI, PREDEFINITO_PREAVVISI)]

    def carica_scadenze(self) -> None:
        """Rilegge le scadenze dalle subentries; quelle illeggibili vengono saltate."""
        scadenze: dict[str, Scadenza] = {}
        for subentry_id, subentry in self.config_entry.subentries.items():
            if subentry.subentry_type != SUBENTRY_SCADENZA:
                continue
            try:
                scadenze[subentry_id] = Scadenza.da_dict(subentry.data)
            except DatiNonValidi as err:
                _LOGGER.error("Scadenza %s ignorata: %s", subentry.title, err)
        self.scadenze = scadenze

    def leggi_km(self) -> int | None:
        """La lettura attuale del contachilometri, se numerica."""
        if self.sensore_km is None:
            return None
        stato = self.hass.states.get(self.sensore_km)
        if stato is None:
            return None
        try:
            km = int(float(stato.state))
        except (TypeError, ValueError):
            return None
        self._ultimi_km = km
        return km

    def calcola(self) -> DatiScadenze:
        oggi = dt_util.now().date()
        km = self.leggi_km()
        configurati = self.sensore_km is not None
        stati = {
            subentry_id: calcola_stato(scadenza, oggi, self.preavvisi, km, km_configurati=configurati)
            for subentry_id, scadenza in self.scadenze.items()
        }
        return DatiScadenze(oggi, km, dict(self.scadenze), stati)

    async def _async_update_data(self) -> DatiScadenze:
        return self.calcola()

    @callback
    def async_ricalcola(self) -> None:
        self.async_set_updated_data(self.calcola())

    async def async_rinnova(self, subentry_id: str) -> None:
        """Rinnova una scadenza oggi, salva la subentry e aggiorna le entità."""
        scadenza = self.scadenze.get(subentry_id)
        subentry = self.config_entry.subentries.get(subentry_id)
        if scadenza is None or subentry is None:
            _LOGGER.warning("Scadenza %s non trovata: rinnovo annullato", subentry_id)
            return

        oggi = dt_util.now().date()
        km = self.leggi_km()
        if km is None:
            km = self._ultimi_km
        try:
            nuova = rinnova(scadenza, self.voce, oggi, km)
        except RinnovoIgnorato:
            _LOGGER.info("%s è già stata rinnovata oggi: rinnovo ignorato", scadenza.nome)
            return
        except DatiNonValidi as err:
            _LOGGER.error("Rinnovo di %s non riuscito: %s", scadenza.nome, err)
            return
        if nuova.usa_km and km is None:
            _LOGGER.warning(
                "Nessuna lettura del contachilometri per %s: km del rinnovo invariati", scadenza.nome
            )

        self.scadenze[subentry_id] = nuova
        self.hass.config_entries.async_update_subentry(
            self.config_entry, subentry, data=nuova.a_dict()
        )
        self.async_ricalcola()
