"""Test del pulsante «Rinnovato» (spec §8.1 e §5.7)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from .common import configura, crea_voce_veicolo, entity_id


async def premi(hass: HomeAssistant, pulsante: str) -> None:
    await hass.services.async_call("button", "press", {}, target={"entity_id": pulsante}, blocking=True)
    await hass.async_block_till_done()


async def test_premere_rinnova_la_scadenza(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    await premi(hass, entity_id(hass, "button", "sub_revisione_rinnova"))

    assert entry.subentries["sub_revisione"].data["scadenza"] == "2028-09-30"
    assert hass.states.get(entity_id(hass, "sensor", "sub_revisione_scadenza")).state == "2028-09-30"
    assert hass.states.get(entity_id(hass, "binary_sensor", "sub_revisione_in_scadenza")).state == "off"


async def test_doppia_pressione_nello_stesso_giorno(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)
    pulsante = entity_id(hass, "button", "sub_bollo_rinnova")

    await premi(hass, pulsante)
    await premi(hass, pulsante)

    assert entry.subentries["sub_bollo"].data["scadenza"] == "2027-10-31"
