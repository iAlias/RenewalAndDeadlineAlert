"""Test di sensori, sensore binario e dispositivi delle scadenze (spec §8.0 e §8.1)."""

from __future__ import annotations

import pytest

from custom_components.scadenze.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .common import configura, crea_voce_veicolo, entity_id


async def test_sensore_data_con_attributi(hass: HomeAssistant) -> None:
    await configura(hass, crea_voce_veicolo())

    revisione = hass.states.get(entity_id(hass, "sensor", "sub_revisione_scadenza"))
    assert revisione is not None
    assert revisione.state == "2026-09-30"
    assert revisione.attributes["stato"] == "in_scadenza"
    assert revisione.attributes["modello"] == "revisione"
    assert revisione.attributes["ultimo_rinnovo"] is None

    bollo = hass.states.get(entity_id(hass, "sensor", "sub_bollo_scadenza"))
    assert bollo is not None
    assert bollo.attributes["mese_scadenza_bollo"] == "2026-09-01"
    assert bollo.attributes["da_pagare_entro"] == "2026-10-31"


async def test_giorni_mancanti(hass: HomeAssistant) -> None:
    await configura(hass, crea_voce_veicolo())

    giorni = hass.states.get(entity_id(hass, "sensor", "sub_revisione_giorni"))
    assert giorni is not None
    assert giorni.state == "16"
    assert giorni.attributes["unit_of_measurement"] == "d"


async def test_km_mancanti_seguono_il_contachilometri(hass: HomeAssistant) -> None:
    await configura(hass, crea_voce_veicolo())
    km = entity_id(hass, "sensor", "sub_tagliando_km")

    assert hass.states.get(km).state == "unavailable"

    hass.states.async_set("sensor.panda_km", "34500")
    await hass.async_block_till_done()
    assert hass.states.get(km).state == "500"


async def test_km_mancanti_solo_con_contachilometri(hass: HomeAssistant) -> None:
    await configura(hass, crea_voce_veicolo(sensore_km=None))
    assert er.async_get(hass).async_get_entity_id("sensor", DOMAIN, "sub_tagliando_km") is None


async def test_in_scadenza(hass: HomeAssistant) -> None:
    await configura(hass, crea_voce_veicolo())

    assert hass.states.get(entity_id(hass, "binary_sensor", "sub_revisione_in_scadenza")).state == "on"
    assert hass.states.get(entity_id(hass, "binary_sensor", "sub_bollo_in_scadenza")).state == "off"


async def test_un_dispositivo_per_scadenza_collegato_alla_voce(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    voce = device_registry.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    revisione = device_registry.async_get_device(identifiers={(DOMAIN, "sub_revisione")})
    assert voce is not None and revisione is not None
    assert revisione.name == "Panda Revisione"
    assert revisione.model == "Revisione"
    assert revisione.via_device_id == voce.id

    voce_entita = entity_registry.async_get(entity_id(hass, "sensor", "sub_revisione_giorni"))
    assert voce_entita is not None
    assert voce_entita.device_id == revisione.id
    assert voce_entita.config_subentry_id == "sub_revisione"
    assert "silently moves the device" not in caplog.text


async def test_eliminare_la_scadenza_toglie_dispositivo_ed_entita(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    hass.config_entries.async_remove_subentry(entry, "sub_revisione")
    await hass.async_block_till_done()

    assert device_registry.async_get_device(identifiers={(DOMAIN, "sub_revisione")}) is None
    assert entity_registry.async_get_entity_id("sensor", DOMAIN, "sub_revisione_scadenza") is None
