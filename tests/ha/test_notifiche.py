"""Test dell'invio dei promemoria (spec §10.2)."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    async_capture_events,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.scadenze.const import DOMAIN, EVENTO_PROMEMORIA
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .common import configura, crea_voce_veicolo

ALLE_NOVE = "2026-09-14T07:00:00+00:00"  # 09:00 a Roma
ALLE_DIECI = "2026-09-14T08:00:00+00:00"  # 10:00 a Roma


async def test_promemoria_all_orario(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    chiamate = async_mock_service(hass, "notify", "telefono")
    eventi = async_capture_events(hass, EVENTO_PROMEMORIA)
    await configura(hass, crea_voce_veicolo(notifiche_attive=True))
    assert chiamate == []

    freezer.move_to(ALLE_NOVE)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert len(chiamate) == 1
    assert chiamate[0].data == {
        "title": "Panda – Revisione",
        "message": "Scade tra 16 giorni (30/09/2026).",
    }
    assert len(eventi) == 1
    assert eventi[0].data["scadenza_id"] == "sub_revisione"
    assert eventi[0].data["soglia"] == 30
    assert eventi[0].data["giorni_mancanti"] == 16


async def test_nessun_doppione_dopo_un_riavvio(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    chiamate = async_mock_service(hass, "notify", "telefono")
    entry = crea_voce_veicolo(notifiche_attive=True)
    await configura(hass, entry)

    freezer.move_to(ALLE_NOVE)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert len(chiamate) == 1

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert len(chiamate) == 1


async def test_promemoria_all_avvio_se_l_orario_e_passato(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(ALLE_DIECI)
    chiamate = async_mock_service(hass, "notify", "telefono")

    await configura(hass, crea_voce_veicolo(notifiche_attive=True))

    assert len(chiamate) == 1


async def test_servizio_mancante_crea_una_riparazione(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, issue_registry: ir.IssueRegistry
) -> None:
    freezer.move_to(ALLE_DIECI)
    eventi = async_capture_events(hass, EVENTO_PROMEMORIA)
    entry = crea_voce_veicolo(notifiche_attive=True, servizio_notifica="notify.inesistente")

    await configura(hass, entry)

    assert issue_registry.async_get_issue(DOMAIN, f"servizio_notifica_mancante_{entry.entry_id}") is not None
    assert len(eventi) == 1


async def test_notifiche_disattivate_lanciano_solo_l_evento(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(ALLE_DIECI)
    chiamate = async_mock_service(hass, "notify", "telefono")
    eventi = async_capture_events(hass, EVENTO_PROMEMORIA)

    await configura(hass, crea_voce_veicolo(notifiche_attive=False))

    assert chiamate == []
    assert len(eventi) == 1
