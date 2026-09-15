"""Scadenze Auto & Casa: scadenze italiane di veicoli, casa e documenti."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration
from homeassistant.util import dt as dt_util

from .const import (
    CHIAVE_FRONTEND_REGISTRATO,
    DOMAIN,
    ETICHETTE_TIPO_VOCE,
    NOME_FILE_CARD,
    URL_STATICO,
)
from .coordinator import ScadenzeCoordinator
from .notifiche import GestoreNotifiche

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
CARTELLA_FRONTEND = Path(__file__).parent / "frontend"

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CALENDAR,
    Platform.SENSOR,
    Platform.TODO,
]

type Firma = tuple[frozenset[tuple[str, str]], dict[str, Any], dict[str, Any]]


@dataclass
class ScadenzeRuntime:
    """Ciò che serve alle piattaforme di una voce caricata."""

    coordinator: ScadenzeCoordinator
    notifiche: GestoreNotifiche
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


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve i file della card e li aggiunge al frontend, una sola volta per avvio."""
    if hass.data.get(CHIAVE_FRONTEND_REGISTRATO):
        return True
    hass.data[CHIAVE_FRONTEND_REGISTRATO] = True

    await hass.http.async_register_static_paths(
        [StaticPathConfig(URL_STATICO, str(CARTELLA_FRONTEND), True)]
    )
    if "frontend" in hass.config.components:
        integrazione = await async_get_integration(hass, DOMAIN)
        _aggiungi_modulo_frontend(hass, f"{URL_STATICO}/{NOME_FILE_CARD}?v={integrazione.version}")
    return True


def _aggiungi_modulo_frontend(hass: HomeAssistant, url: str) -> None:
    """Importa il frontend solo quando serve: nell'ambiente di test il suo pacchetto non c'è."""
    from homeassistant.components.frontend import add_extra_js_url  # noqa: PLC0415

    add_extra_js_url(hass, url)


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
    notifiche = GestoreNotifiche(hass, entry, coordinator)
    await notifiche.async_carica()
    entry.runtime_data = ScadenzeRuntime(
        coordinator=coordinator,
        notifiche=notifiche,
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
    entry.async_on_unload(notifiche.async_pianifica())
    entry.async_on_unload(entry.add_update_listener(_async_entry_aggiornata))

    if dt_util.now().time() >= notifiche.orario:
        entry.async_create_task(hass, notifiche.async_esegui(), "scadenze: promemoria all'avvio")
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
