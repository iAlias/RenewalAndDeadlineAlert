"""La card è servita dall'integrazione e registrata nel frontend (spec fase 2, §3 e §7)."""

from __future__ import annotations

from unittest.mock import patch

from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.scadenze import async_setup
from homeassistant.core import HomeAssistant

from .common import configura, crea_voce_veicolo


async def test_i_file_della_card_sono_serviti(
    hass: HomeAssistant, hass_client: ClientSessionGenerator
) -> None:
    await configura(hass, crea_voce_veicolo())
    client = await hass_client()

    card = await client.get("/scadenze_static/scadenze-card.js")
    assert card.status == 200
    assert "customElements.define" in await card.text()

    logica = await client.get("/scadenze_static/logica.js")
    assert logica.status == 200


async def test_modulo_aggiunto_al_frontend_con_la_versione(hass: HomeAssistant) -> None:
    hass.config.components.add("frontend")
    with patch("custom_components.scadenze._aggiungi_modulo_frontend") as aggiungi:
        await configura(hass, crea_voce_veicolo())

    aggiungi.assert_called_once_with(hass, "/scadenze_static/scadenze-card.js?v=0.3.0")


async def test_senza_frontend_nessun_modulo(hass: HomeAssistant) -> None:
    with patch("custom_components.scadenze._aggiungi_modulo_frontend") as aggiungi:
        await configura(hass, crea_voce_veicolo())

    aggiungi.assert_not_called()


async def test_la_registrazione_avviene_una_volta_sola(hass: HomeAssistant) -> None:
    await configura(hass, crea_voce_veicolo())

    with patch.object(hass.http, "async_register_static_paths") as registra:
        assert await async_setup(hass, {})

    registra.assert_not_called()
