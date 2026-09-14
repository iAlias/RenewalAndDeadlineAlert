"""Fixture comuni ai test con Home Assistant."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
import pytest

from homeassistant.core import HomeAssistant

ADESSO = "2026-09-14T06:00:00+00:00"  # 08:00 a Roma, prima dell'orario dei promemoria


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Abilita il caricamento di custom_components in ogni test."""


@pytest.fixture(autouse=True)
async def fuso_orario_roma(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """Tutti i test partono il 14/09/2026 alle 08:00, ora di Roma."""
    await hass.config.async_set_time_zone("Europe/Rome")
    freezer.move_to(ADESSO)
