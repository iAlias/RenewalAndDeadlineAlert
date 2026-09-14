"""Calendario delle scadenze di una voce."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import ScadenzeConfigEntry
from .coordinator import ScadenzeCoordinator
from .entity import EntitaVoce
from .regole import attributi_extra


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ScadenzeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([CalendarioScadenze(entry.runtime_data.coordinator)])


class CalendarioScadenze(EntitaVoce, CalendarEntity):
    """Un evento di un giorno intero per ogni scadenza con una data."""

    _attr_translation_key = "calendario"

    def __init__(self, coordinator: ScadenzeCoordinator) -> None:
        super().__init__(coordinator, "calendario")

    def _eventi(self) -> list[CalendarEvent]:
        dati = self.coordinator.data
        eventi: list[CalendarEvent] = []
        for subentry_id, scadenza in dati.scadenze.items():
            if scadenza.scadenza is None:
                continue
            righe = [f"Stato: {dati.stati[subentry_id].stato}"]
            righe += [f"{chiave}: {valore}" for chiave, valore in attributi_extra(scadenza).items()]
            eventi.append(
                CalendarEvent(
                    start=scadenza.scadenza,
                    end=scadenza.scadenza + timedelta(days=1),
                    summary=scadenza.nome,
                    description="\n".join(righe),
                    uid=subentry_id,
                )
            )
        eventi.sort(key=lambda evento: (evento.start, evento.summary))
        return eventi

    @property
    def event(self) -> CalendarEvent | None:
        oggi = self.coordinator.data.oggi
        return next((evento for evento in self._eventi() if evento.start >= oggi), None)

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        return [
            evento
            for evento in self._eventi()
            if dt_util.start_of_local_day(evento.start) < end_date
            and dt_util.start_of_local_day(evento.end) > start_date
        ]
