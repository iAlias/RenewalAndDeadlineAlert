"""Promemoria: pianificazione, invio, evento e riparazioni (spec §10.2)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, time
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_NOTIFICHE_ATTIVE,
    CONF_ORARIO_NOTIFICA,
    CONF_SERVIZIO_NOTIFICA,
    DOMAIN,
    EVENTO_PROMEMORIA,
    PREDEFINITO_ORARIO_NOTIFICA,
    PREDEFINITO_SERVIZIO_NOTIFICA,
)
from .coordinator import ScadenzeCoordinator
from .modello_dati import Scadenza, Stato
from .promemoria import Promemoria, valuta

_LOGGER = logging.getLogger(__name__)
VERSIONE_STORE = 1


class GestoreNotifiche:
    """Valuta le soglie una volta al giorno e invia notifica ed evento."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, coordinator: ScadenzeCoordinator
    ) -> None:
        self._hass = hass
        self._entry = entry
        self._coordinator = coordinator
        self._store: Store[dict[str, Any]] = Store(hass, VERSIONE_STORE, f"{DOMAIN}.{entry.entry_id}")
        self._memoria: dict[str, Any] = {}

    @property
    def orario(self) -> time:
        testo = self._entry.options.get(CONF_ORARIO_NOTIFICA, PREDEFINITO_ORARIO_NOTIFICA)
        return dt_util.parse_time(str(testo)) or time(9, 0)

    @property
    def issue_id(self) -> str:
        return f"servizio_notifica_mancante_{self._entry.entry_id}"

    async def async_carica(self) -> None:
        self._memoria = await self._store.async_load() or {}

    @callback
    def async_pianifica(self) -> Callable[[], None]:
        orario = self.orario

        async def _all_orario(_ora: datetime) -> None:
            await self.async_esegui()

        return async_track_time_change(
            self._hass, _all_orario, hour=orario.hour, minute=orario.minute, second=orario.second
        )

    async def async_esegui(self) -> None:
        """Ricalcola, invia i promemoria dovuti e salva la memoria."""
        self._coordinator.async_ricalcola()
        dati = self._coordinator.data
        preavvisi = self._coordinator.preavvisi
        memoria: dict[str, Any] = {}
        for subentry_id, scadenza in dati.scadenze.items():
            stato = dati.stati[subentry_id]
            esito = valuta(scadenza, stato, preavvisi, self._memoria.get(subentry_id))
            memoria[subentry_id] = esito.memoria
            if esito.promemoria is not None:
                await self._async_invia(subentry_id, scadenza, stato, esito.promemoria)
        self._memoria = memoria
        await self._store.async_save(memoria)

    async def _async_invia(
        self, subentry_id: str, scadenza: Scadenza, stato: Stato, promemoria: Promemoria
    ) -> None:
        voce = self._coordinator.voce
        self._hass.bus.async_fire(
            EVENTO_PROMEMORIA,
            {
                "voce": voce.nome,
                "voce_id": self._entry.entry_id,
                "scadenza": scadenza.nome,
                "scadenza_id": subentry_id,
                "modello": scadenza.modello,
                "data": scadenza.scadenza.isoformat() if scadenza.scadenza else None,
                "giorni_mancanti": stato.giorni_mancanti,
                "km_mancanti": stato.km_mancanti,
                "soglia": promemoria.soglia,
                "messaggio": promemoria.messaggio,
            },
        )

        opzioni = self._entry.options
        if not opzioni.get(CONF_NOTIFICHE_ATTIVE, True):
            return

        servizio = str(opzioni.get(CONF_SERVIZIO_NOTIFICA, PREDEFINITO_SERVIZIO_NOTIFICA))
        dominio, _, nome = servizio.partition(".")
        if not nome or not self._hass.services.has_service(dominio, nome):
            _LOGGER.warning(
                "Servizio di notifica %s non trovato: promemoria di %s non inviato", servizio, scadenza.nome
            )
            ir.async_create_issue(
                self._hass,
                DOMAIN,
                self.issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="servizio_notifica_mancante",
                translation_placeholders={"voce": voce.nome, "servizio": servizio},
            )
            return

        try:
            await self._hass.services.async_call(
                dominio,
                nome,
                {"title": f"{voce.nome} – {scadenza.nome}", "message": promemoria.messaggio},
                blocking=True,
            )
        except (HomeAssistantError, vol.Invalid) as err:
            _LOGGER.warning("Invio del promemoria di %s non riuscito: %s", scadenza.nome, err)
            return
        ir.async_delete_issue(self._hass, DOMAIN, self.issue_id)
