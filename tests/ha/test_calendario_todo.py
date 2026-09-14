"""Test del calendario e della lista todo della voce (spec §8.2)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from .common import configura, crea_voce_veicolo, entity_id


async def test_calendario_prossima_scadenza(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    stato = hass.states.get(entity_id(hass, "calendar", f"{entry.entry_id}_calendario"))
    assert stato is not None
    assert stato.attributes["message"] == "Revisione"
    assert stato.attributes["all_day"] is True


async def test_calendario_eventi_in_un_intervallo(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)
    calendario = entity_id(hass, "calendar", f"{entry.entry_id}_calendario")

    risposta = await hass.services.async_call(
        "calendar",
        "get_events",
        {"start_date_time": "2026-09-01T00:00:00+02:00", "end_date_time": "2026-11-01T00:00:00+01:00"},
        target={"entity_id": calendario},
        blocking=True,
        return_response=True,
    )

    eventi = risposta[calendario]["events"]
    assert [evento["summary"] for evento in eventi] == ["Revisione", "Bollo"]
    assert (eventi[0]["start"], eventi[0]["end"]) == ("2026-09-30", "2026-10-01")


async def test_todo_elenca_solo_le_scadenze_vicine(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)
    lista = entity_id(hass, "todo", f"{entry.entry_id}_todo")

    assert hass.states.get(lista).state == "1"
    risposta = await hass.services.async_call(
        "todo", "get_items", {}, target={"entity_id": lista}, blocking=True, return_response=True
    )
    elementi = risposta[lista]["items"]
    assert [(e["summary"], e["uid"], e["status"], e["due"]) for e in elementi] == [
        ("Revisione", "sub_revisione", "needs_action", "2026-09-30")
    ]


async def test_spuntare_un_elemento_rinnova(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)
    lista = entity_id(hass, "todo", f"{entry.entry_id}_todo")

    await hass.services.async_call(
        "todo",
        "update_item",
        {"item": "Revisione", "status": "completed"},
        target={"entity_id": lista},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert entry.subentries["sub_revisione"].data["scadenza"] == "2028-09-30"
    assert hass.states.get(lista).state == "0"
