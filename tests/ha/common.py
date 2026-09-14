"""Dati e funzioni condivisi dai test con Home Assistant."""

from __future__ import annotations

from typing import Any

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.scadenze.const import DOMAIN
from homeassistant.config_entries import ConfigSubentryDataWithId
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

_VUOTA: dict[str, Any] = {
    "ultimo_rinnovo": None,
    "completata": False,
    "intervallo_mesi": None,
    "ancora": "rinnovo",
    "intervallo_km": None,
    "km_ultimo_rinnovo": None,
    "mese_scadenza_bollo": None,
    "documento": None,
}

# Il 14/09/2026: revisione fra 16 giorni, bollo fra 47, tagliando fra 168.
REVISIONE: dict[str, Any] = {
    **_VUOTA,
    "modello": "revisione",
    "nome": "Revisione",
    "regola": "fine_mese",
    "scadenza": "2026-09-30",
}
BOLLO: dict[str, Any] = {
    **_VUOTA,
    "modello": "bollo",
    "nome": "Bollo",
    "regola": "fine_mese",
    "scadenza": "2026-10-31",
    "mese_scadenza_bollo": "2026-09-01",
}
TAGLIANDO: dict[str, Any] = {
    **_VUOTA,
    "modello": "tagliando",
    "nome": "Tagliando",
    "regola": "intervallo",
    "scadenza": "2027-03-01",
    "ultimo_rinnovo": "2026-03-01",
    "intervallo_mesi": 12,
    "intervallo_km": 15000,
    "km_ultimo_rinnovo": 20000,
}

OPZIONI_BASE: dict[str, Any] = {
    "sensore_km": "sensor.panda_km",
    "notifiche_attive": False,
    "servizio_notifica": "notify.telefono",
    "preavvisi": [30, 7, 1],
    "orario_notifica": "09:00:00",
}


def sotto_voce(subentry_id: str, dati: dict[str, Any]) -> ConfigSubentryDataWithId:
    return ConfigSubentryDataWithId(
        subentry_id=subentry_id,
        subentry_type="scadenza",
        title=dati["nome"],
        unique_id=None,
        data=dati,
    )


def crea_voce_veicolo(**opzioni: Any) -> MockConfigEntry:
    """La Panda con revisione, bollo e tagliando; le opzioni sovrascrivono OPZIONI_BASE."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Panda",
        data={
            "tipo": "veicolo",
            "nome": "Panda",
            "tipo_veicolo": "auto",
            "immatricolazione": "2022-05-01",
        },
        options={**OPZIONI_BASE, **opzioni},
        subentries_data=[
            sotto_voce("sub_revisione", REVISIONE),
            sotto_voce("sub_bollo", BOLLO),
            sotto_voce("sub_tagliando", TAGLIANDO),
        ],
    )


async def configura(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    riuscito = await hass.config_entries.async_setup(entry.entry_id)
    assert riuscito, f"setup non riuscito: stato={entry.state}, motivo={entry.reason}"
    await hass.async_block_till_done()


def entity_id(hass: HomeAssistant, piattaforma: str, unique_id: str) -> str:
    trovato = er.async_get(hass).async_get_entity_id(piattaforma, DOMAIN, unique_id)
    assert trovato is not None, f"nessuna entità {piattaforma} con unique_id {unique_id}"
    return trovato
