"""Scadenze Auto & Casa: scadenze italiane di veicoli, casa e documenti."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)

from .const import DOMAIN, ETICHETTE_TIPO_VOCE
from .coordinator import ScadenzeCoordinator

PLATFORMS: list[Platform] = []

type Firma = tuple[frozenset[tuple[str, str]], dict[str, Any], dict[str, Any]]


@dataclass
class ScadenzeRuntime:
    """Ciò che serve alle piattaforme di una voce caricata."""

    coordinator: ScadenzeCoordinator
    device_id_voce: str
    firma: Firma


type ScadenzeConfigEntry = ConfigEntry[ScadenzeRuntime]


def firma_entry(entry: ConfigEntry) -> Firma:
    """Se cambia, la entry va ricaricata: subentries (id e titolo), dati o opzioni."""
    return (
        frozenset((subentry_id, subentry.title) for subentry_id, subentry in entry.subentries.items()),
        dict(entry.data),
        dict(entry.options),
    )


async def async_setup_entry(hass: HomeAssistant, entry: ScadenzeConfigEntry) -> bool:
    coordinator = ScadenzeCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    dispositivo = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=coordinator.voce.nome,
        model=ETICHETTE_TIPO_VOCE[coordinator.voce.tipo],
        entry_type=dr.DeviceEntryType.SERVICE,
    )
    entry.runtime_data = ScadenzeRuntime(
        coordinator=coordinator,
        device_id_voce=dispositivo.id,
        firma=firma_entry(entry),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    def _a_mezzanotte(_ora: datetime) -> None:
        coordinator.async_ricalcola()

    @callback
    def _km_cambiati(_evento: Event[EventStateChangedData]) -> None:
        coordinator.async_ricalcola()

    entry.async_on_unload(
        async_track_time_change(hass, _a_mezzanotte, hour=0, minute=0, second=5)
    )
    if coordinator.sensore_km:
        entry.async_on_unload(
            async_track_state_change_event(hass, [coordinator.sensore_km], _km_cambiati)
        )
    entry.async_on_unload(entry.add_update_listener(_async_entry_aggiornata))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ScadenzeConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_entry_aggiornata(hass: HomeAssistant, entry: ScadenzeConfigEntry) -> None:
    """Reload solo se servono entità o impostazioni nuove; altrimenti basta ricalcolare."""
    runtime = entry.runtime_data
    if firma_entry(entry) != runtime.firma:
        await hass.config_entries.async_reload(entry.entry_id)
        return
    runtime.coordinator.carica_scadenze()
    runtime.coordinator.async_ricalcola()
