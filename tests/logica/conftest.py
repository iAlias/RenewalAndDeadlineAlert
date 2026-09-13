"""Rende importabili i moduli di logica pura anche senza Home Assistant.

`custom_components/scadenze/__init__.py` importa Home Assistant. Dove Home Assistant
non è installato (per esempio su Windows) i pacchetti vengono registrati a mano, con
un `__path__` ma senza eseguire il loro `__init__`, così Python trova i sottomoduli.
Dove Home Assistant c'è (CI, WSL) non serve nulla e si usa il pacchetto vero.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = ROOT / "custom_components"


def _registra(nome: str, percorso: Path) -> None:
    modulo = types.ModuleType(nome)
    modulo.__path__ = [str(percorso)]  # type: ignore[attr-defined]
    sys.modules[nome] = modulo


if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if importlib.util.find_spec("homeassistant") is None:
    _registra("custom_components", COMPONENTS)
    _registra("custom_components.scadenze", COMPONENTS / "scadenze")
