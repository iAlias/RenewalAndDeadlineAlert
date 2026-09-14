"""Sensori di una scadenza: data, giorni mancanti, km mancanti."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ScadenzeConfigEntry
from .entity import EntitaScadenza
from .regole import attributi_extra


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ScadenzeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    runtime = entry.runtime_data
    coordinator = runtime.coordinator
    for subentry_id, scadenza in coordinator.scadenze.items():
        entita: list[SensorEntity] = [
            SensoreScadenza(coordinator, subentry_id, "scadenza", runtime.device_id_voce),
            SensoreGiorniMancanti(coordinator, subentry_id, "giorni", runtime.device_id_voce),
        ]
        if scadenza.usa_km and coordinator.sensore_km:
            entita.append(SensoreKmMancanti(coordinator, subentry_id, "km", runtime.device_id_voce))
        async_add_entities(entita, config_subentry_id=subentry_id)


class SensoreScadenza(EntitaScadenza, SensorEntity):
    """La data di scadenza; il nome è quello del dispositivo."""

    _attr_name = None
    _attr_device_class = SensorDeviceClass.DATE

    @property
    def native_value(self) -> date | None:
        return self.scadenza.scadenza if self.scadenza else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        scadenza, stato = self.scadenza, self.stato
        if scadenza is None or stato is None:
            return {}
        attributi: dict[str, Any] = {
            "stato": stato.stato,
            "modello": scadenza.modello,
            "ultimo_rinnovo": scadenza.ultimo_rinnovo.isoformat() if scadenza.ultimo_rinnovo else None,
        }
        attributi.update(attributi_extra(scadenza))
        if scadenza.usa_km:
            attributi["km_scadenza"] = stato.km_scadenza
            attributi["km_non_disponibili"] = stato.km_non_disponibili
        return attributi


class SensoreGiorniMancanti(EntitaScadenza, SensorEntity):
    _attr_translation_key = "giorni_mancanti"
    _attr_native_unit_of_measurement = UnitOfTime.DAYS

    @property
    def native_value(self) -> int | None:
        return self.stato.giorni_mancanti if self.stato else None


class SensoreKmMancanti(EntitaScadenza, SensorEntity):
    _attr_translation_key = "km_mancanti"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS

    @property
    def available(self) -> bool:
        return super().available and self.stato is not None and not self.stato.km_non_disponibili

    @property
    def native_value(self) -> int | None:
        return self.stato.km_mancanti if self.stato else None
