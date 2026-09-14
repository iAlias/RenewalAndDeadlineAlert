"""Lista «Da rinnovare» di una voce: spuntare un elemento equivale a «Rinnovato»."""

from __future__ import annotations

from datetime import date

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ScadenzeConfigEntry
from .coordinator import ScadenzeCoordinator
from .entity import EntitaVoce
from .modello_dati import STATO_IN_SCADENZA, STATO_SCADUTA


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ScadenzeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([DaRinnovare(entry.runtime_data.coordinator)])


class DaRinnovare(EntitaVoce, TodoListEntity):
    _attr_translation_key = "da_rinnovare"
    _attr_supported_features = TodoListEntityFeature.UPDATE_TODO_ITEM

    def __init__(self, coordinator: ScadenzeCoordinator) -> None:
        super().__init__(coordinator, "todo")
        self._attr_todo_items = self._elementi()

    def _elementi(self) -> list[TodoItem]:
        dati = self.coordinator.data
        elementi: list[TodoItem] = []
        ordinate = sorted(
            dati.scadenze.items(),
            key=lambda coppia: (coppia[1].scadenza or date.max, coppia[1].nome),
        )
        for subentry_id, scadenza in ordinate:
            stato = dati.stati[subentry_id]
            if stato.stato not in (STATO_IN_SCADENZA, STATO_SCADUTA):
                continue
            elementi.append(
                TodoItem(
                    summary=scadenza.nome,
                    uid=subentry_id,
                    status=TodoItemStatus.NEEDS_ACTION,
                    due=scadenza.scadenza,
                    description=f"Stato: {stato.stato}",
                )
            )
        return elementi

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_todo_items = self._elementi()
        super()._handle_coordinator_update()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        if item.status == TodoItemStatus.COMPLETED and item.uid in self.coordinator.scadenze:
            await self.coordinator.async_rinnova(item.uid)
