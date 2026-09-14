"""Pulsante «Rinnovato» di una scadenza."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ScadenzeConfigEntry
from .entity import EntitaScadenza


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ScadenzeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    runtime = entry.runtime_data
    for subentry_id in runtime.coordinator.scadenze:
        async_add_entities(
            [Rinnovato(runtime.coordinator, subentry_id, "rinnova", runtime.device_id_voce)],
            config_subentry_id=subentry_id,
        )


class Rinnovato(EntitaScadenza, ButtonEntity):
    _attr_translation_key = "rinnovato"

    async def async_press(self) -> None:
        await self.coordinator.async_rinnova(self.subentry_id)
