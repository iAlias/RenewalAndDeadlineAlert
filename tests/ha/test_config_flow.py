"""Test dei flussi: nuova voce, opzioni, scadenza e riconfigurazione (spec §7)."""

from __future__ import annotations

from typing import Any

from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.scadenze.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .common import configura, crea_voce_veicolo


def suggerito(risultato: dict[str, Any], campo: str) -> Any:
    """Il valore precompilato di un campo in un form."""
    for chiave in risultato["data_schema"].schema:
        if chiave == campo:
            return (chiave.description or {}).get("suggested_value")
    raise AssertionError(f"campo {campo} assente dal form")


def opzioni_selettore(risultato: dict[str, Any], campo: str) -> list[str]:
    for chiave, selettore in risultato["data_schema"].schema.items():
        if chiave == campo:
            return list(selettore.config["options"])
    raise AssertionError(f"campo {campo} assente dal form")


async def avvia_voce(hass: HomeAssistant, tipo: str) -> dict[str, Any]:
    risultato = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert risultato["type"] is FlowResultType.MENU
    assert risultato["menu_options"] == ["veicolo", "casa", "persona", "generica"]
    return await hass.config_entries.flow.async_configure(risultato["flow_id"], {"next_step_id": tipo})


async def test_nuovo_veicolo(hass: HomeAssistant) -> None:
    form = await avvia_voce(hass, "veicolo")
    assert (form["type"], form["step_id"]) == (FlowResultType.FORM, "veicolo")

    risultato = await hass.config_entries.flow.async_configure(
        form["flow_id"], {"nome": "Panda", "tipo_veicolo": "auto", "immatricolazione": "2022-05-18"}
    )

    assert risultato["type"] is FlowResultType.CREATE_ENTRY
    assert risultato["title"] == "Panda"
    assert risultato["data"] == {
        "tipo": "veicolo",
        "nome": "Panda",
        "tipo_veicolo": "auto",
        "immatricolazione": "2022-05-01",
    }


async def test_immatricolazione_futura(hass: HomeAssistant) -> None:
    form = await avvia_voce(hass, "veicolo")
    risultato = await hass.config_entries.flow.async_configure(
        form["flow_id"], {"nome": "Panda", "tipo_veicolo": "auto", "immatricolazione": "2026-10-01"}
    )
    assert risultato["errors"] == {"immatricolazione": "data_futura"}


async def test_nuova_persona_casa_e_generica(hass: HomeAssistant) -> None:
    form = await avvia_voce(hass, "persona")
    persona = await hass.config_entries.flow.async_configure(
        form["flow_id"], {"nome": "Mario", "data_nascita": "1990-05-08"}
    )
    assert persona["data"] == {"tipo": "persona", "nome": "Mario", "data_nascita": "1990-05-08"}

    for tipo, nome in (("casa", "Casa al mare"), ("generica", "Abbonamenti")):
        form = await avvia_voce(hass, tipo)
        risultato = await hass.config_entries.flow.async_configure(form["flow_id"], {"nome": nome})
        assert risultato["data"] == {"tipo": tipo, "nome": nome}


async def test_opzioni_del_veicolo(hass: HomeAssistant) -> None:
    async_mock_service(hass, "notify", "telefono")
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    form = await hass.config_entries.options.async_init(entry.entry_id)
    assert form["step_id"] == "init"
    assert suggerito(form, "preavvisi") == "30, 7, 1"

    risultato = await hass.config_entries.options.async_configure(
        form["flow_id"],
        {
            "sensore_km": "sensor.panda_km",
            "notifiche_attive": True,
            "servizio_notifica": "notify.telefono",
            "preavvisi": "7, 30",
            "orario_notifica": "08:30:00",
        },
    )
    await hass.async_block_till_done()

    assert risultato["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {
        "sensore_km": "sensor.panda_km",
        "notifiche_attive": True,
        "servizio_notifica": "notify.telefono",
        "preavvisi": [30, 7],
        "orario_notifica": "08:30:00",
    }


async def test_opzioni_con_errori(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    form = await hass.config_entries.options.async_init(entry.entry_id)
    risultato = await hass.config_entries.options.async_configure(
        form["flow_id"],
        {
            "notifiche_attive": True,
            "servizio_notifica": "notify.inesistente",
            "preavvisi": "30, mille",
            "orario_notifica": "09:00:00",
        },
    )
    assert risultato["errors"] == {
        "servizio_notifica": "servizio_non_trovato",
        "preavvisi": "preavvisi_non_validi",
    }


async def test_nuova_scadenza_precompilata(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    scelta = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "scadenza"), context={"source": SOURCE_USER}
    )
    assert opzioni_selettore(scelta, "modello") == [
        "revisione", "bollo", "assicurazione", "tagliando", "gomme", "personalizzata",
    ]
    form = await hass.config_entries.subentries.async_configure(scelta["flow_id"], {"modello": "revisione"})
    assert form["step_id"] == "dettagli"
    assert suggerito(form, "nome") == "Revisione"
    assert suggerito(form, "scadenza") == "2028-05-31"

    risultato = await hass.config_entries.subentries.async_configure(
        form["flow_id"], {"nome": "Revisione 2028", "scadenza": "2028-05-31"}
    )
    await hass.async_block_till_done()

    assert risultato["type"] is FlowResultType.CREATE_ENTRY
    nuova = next(s for s in entry.subentries.values() if s.title == "Revisione 2028")
    assert (nuova.data["regola"], nuova.data["scadenza"]) == ("fine_mese", "2028-05-31")


async def test_scadenza_con_data_futura(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    scelta = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "scadenza"), context={"source": SOURCE_USER}
    )
    form = await hass.config_entries.subentries.async_configure(scelta["flow_id"], {"modello": "tagliando"})
    risultato = await hass.config_entries.subentries.async_configure(
        form["flow_id"],
        {
            "nome": "Tagliando",
            "ultimo_rinnovo": "2026-09-15",
            "km_ultimo_rinnovo": 0,
            "intervallo_mesi": 12,
            "intervallo_km": 15000,
        },
    )
    assert risultato["errors"] == {"ultimo_rinnovo": "data_futura"}


async def test_riconfigurare_una_scadenza(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    form = await entry.start_subentry_reconfigure_flow(hass, "sub_bollo")
    assert form["step_id"] == "dettagli"
    assert suggerito(form, "mese_scadenza_bollo") == "2026-09-01"

    risultato = await hass.config_entries.subentries.async_configure(
        form["flow_id"], {"nome": "Bollo Panda", "mese_scadenza_bollo": "2026-11-01"}
    )
    await hass.async_block_till_done()

    assert risultato["type"] is FlowResultType.ABORT
    assert risultato["reason"] == "reconfigure_successful"
    bollo = entry.subentries["sub_bollo"]
    assert (bollo.title, bollo.data["scadenza"]) == ("Bollo Panda", "2026-12-31")


async def test_una_voce_generica_offre_solo_la_personalizzata(hass: HomeAssistant) -> None:
    form = await avvia_voce(hass, "generica")
    creata = await hass.config_entries.flow.async_configure(form["flow_id"], {"nome": "Abbonamenti"})
    await hass.async_block_till_done()

    scelta = await hass.config_entries.subentries.async_init(
        (creata["result"].entry_id, "scadenza"), context={"source": SOURCE_USER}
    )
    assert opzioni_selettore(scelta, "modello") == ["personalizzata"]
