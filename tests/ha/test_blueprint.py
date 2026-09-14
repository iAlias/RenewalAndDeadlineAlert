"""La blueprint ascolta l'evento dei promemoria (spec §10.3)."""

from __future__ import annotations

from pathlib import Path

from homeassistant.util.yaml import load_yaml
from homeassistant.util.yaml.objects import Input

PERCORSO = (
    Path(__file__).resolve().parents[2]
    / "blueprints"
    / "automation"
    / "scadenze"
    / "promemoria_scadenze.yaml"
)


def test_blueprint_ascolta_l_evento_dei_promemoria() -> None:
    dati = load_yaml(PERCORSO)
    assert dati["blueprint"]["domain"] == "automation"
    assert set(dati["blueprint"]["input"]) == {"voce", "azioni"}
    assert dati["triggers"] == [{"trigger": "event", "event_type": "scadenze_promemoria"}]
    assert isinstance(dati["actions"], Input)
