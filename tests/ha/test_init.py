"""Test di setup, dispositivi, ricalcoli, rinnovo e politica di reload (spec §8.0 e §9)."""

from __future__ import annotations

from types import MappingProxyType

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.scadenze.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .common import REVISIONE, configura, crea_voce_veicolo, sotto_voce


async def test_setup_crea_il_dispositivo_della_voce(
    hass: HomeAssistant, device_registry: dr.DeviceRegistry
) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    dispositivo = device_registry.async_get_device_by_identifier((DOMAIN, entry.entry_id), entry.entry_id)
    assert dispositivo is not None
    assert (dispositivo.name, dispositivo.model) == ("Panda", "Veicolo")
    assert entry.runtime_data.device_id_voce == dispositivo.id


async def test_stati_iniziali(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)
    stati = entry.runtime_data.coordinator.data.stati

    assert (stati["sub_revisione"].stato, stati["sub_revisione"].giorni_mancanti) == ("in_scadenza", 16)
    assert (stati["sub_bollo"].stato, stati["sub_bollo"].giorni_mancanti) == ("ok", 47)
    assert stati["sub_tagliando"].km_non_disponibili is True


async def test_il_contachilometri_fa_ricalcolare(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    hass.states.async_set("sensor.panda_km", "34500")
    await hass.async_block_till_done()

    stato = entry.runtime_data.coordinator.data.stati["sub_tagliando"]
    assert (stato.stato, stato.km_mancanti) == ("in_scadenza", 500)


async def test_ricalcolo_a_mezzanotte(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    freezer.move_to("2026-09-30T22:00:05+00:00")  # 1 ottobre, 00:00:05 a Roma
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    stato = entry.runtime_data.coordinator.data.stati["sub_revisione"]
    assert (stato.stato, stato.giorni_mancanti) == ("scaduta", -1)


async def test_rinnovo_salva_la_subentry_senza_ricaricare(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)
    coordinator = entry.runtime_data.coordinator

    await coordinator.async_rinnova("sub_revisione")
    await hass.async_block_till_done()

    dati = entry.subentries["sub_revisione"].data
    assert (dati["scadenza"], dati["ultimo_rinnovo"]) == ("2028-09-30", "2026-09-14")
    assert entry.runtime_data.coordinator is coordinator
    assert coordinator.data.stati["sub_revisione"].stato == "ok"


async def test_doppio_rinnovo_ignorato(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)
    coordinator = entry.runtime_data.coordinator

    await coordinator.async_rinnova("sub_bollo")
    await coordinator.async_rinnova("sub_bollo")
    await hass.async_block_till_done()

    dati = entry.subentries["sub_bollo"].data
    assert (dati["mese_scadenza_bollo"], dati["scadenza"]) == ("2027-09-01", "2027-10-31")


async def test_nuova_scadenza_ricarica_la_voce(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)
    vecchio = entry.runtime_data.coordinator

    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(
            data=MappingProxyType({**REVISIONE, "modello": "gomme", "nome": "Gomme", "regola": "stagionale", "scadenza": "2026-11-15"}),
            subentry_type="scadenza",
            title="Gomme",
            unique_id=None,
        ),
    )
    await hass.async_block_till_done()

    nuovo = entry.runtime_data.coordinator
    assert nuovo is not vecchio
    assert "Gomme" in {scadenza.nome for scadenza in nuovo.scadenze.values()}


async def test_scadenza_illeggibile_saltata(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    base = crea_voce_veicolo()
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=base.title,
        data=dict(base.data),
        options=dict(base.options),
        subentries_data=[
            sotto_voce("sub_revisione", REVISIONE),
            sotto_voce("sub_rotta", {"modello": "revisione", "nome": "Rotta"}),
        ],
    )
    await configura(hass, entry)

    assert "sub_rotta" not in entry.runtime_data.coordinator.scadenze
    assert "sub_revisione" in entry.runtime_data.coordinator.scadenze
    assert "ignorata" in caplog.text


async def test_unload(hass: HomeAssistant) -> None:
    entry = crea_voce_veicolo()
    await configura(hass, entry)

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
