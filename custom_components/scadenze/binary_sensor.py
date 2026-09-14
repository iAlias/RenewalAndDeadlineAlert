"""Sensore binario «In scadenza» di una scadenza."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ScadenzeConfigEntry
from .entity import EntitaScadenza
from .modello_dati import STATO_IN_SCADENZA, STATO_SCADUTA


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ScadenzeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    runtime = entry.runtime_data
    for subentry_id in runtime.coordinator.scadenze:
        async_add_entities(
            [InScadenza(runtime.coordinator, subentry_id, "in_scadenza", runtime.device_id_voce)],
            config_subentry_id=subentry_id,
        )


class InScadenza(EntitaScadenza, BinarySensorEntity):
    _attr_translation_key = "in_scadenza"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool | None:
        if self.stato is None:
            return None
        return self.stato.stato in (STATO_IN_SCADENZA, STATO_SCADUTA)
