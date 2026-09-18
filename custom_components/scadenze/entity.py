"""Entità base di Renewal & Deadline Alert (Home, Car, Health)."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ScadenzeCoordinator
from .modelli import MODELLI
from .modello_dati import Scadenza, Stato


class EntitaScadenza(CoordinatorEntity[ScadenzeCoordinator]):
    """Entità di una scadenza, sul dispositivo della scadenza (spec §8.0)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ScadenzeCoordinator,
        subentry_id: str,
        chiave: str,
        device_id_voce: str,
    ) -> None:
        super().__init__(coordinator)
        self.subentry_id = subentry_id
        scadenza = coordinator.scadenze[subentry_id]
        modello = MODELLI.get(scadenza.modello)
        self._attr_unique_id = f"{subentry_id}_{chiave}"
        self._attr_icon = modello.icona if modello else None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, subentry_id)},
            name=f"{coordinator.voce.nome} {scadenza.nome}",
            model=modello.etichetta if modello else scadenza.modello,
            entry_type=DeviceEntryType.SERVICE,
            via_device_id=device_id_voce,
        )

    @property
    def scadenza(self) -> Scadenza | None:
        return self.coordinator.data.scadenze.get(self.subentry_id)

    @property
    def stato(self) -> Stato | None:
        return self.coordinator.data.stati.get(self.subentry_id)

    @property
    def available(self) -> bool:
        return super().available and self.stato is not None


class EntitaVoce(CoordinatorEntity[ScadenzeCoordinator]):
    """Entità della voce, sul dispositivo della voce creato nel setup."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ScadenzeCoordinator, chiave: str) -> None:
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{chiave}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})
