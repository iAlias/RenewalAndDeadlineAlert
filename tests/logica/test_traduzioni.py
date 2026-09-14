"""Coerenza dei file di traduzione (li legge solo come JSON: nessun import di HA)."""

from __future__ import annotations

from collections.abc import Iterator
import json
from pathlib import Path
from typing import Any

from custom_components.scadenze.modelli import MODELLI

CARTELLA = Path(__file__).resolve().parents[2] / "custom_components" / "scadenze"
ERRORI_SCADENZA = {
    "campo_obbligatorio",
    "data_non_valida",
    "data_futura",
    "intervallo_non_valido",
    "scadenza_prima_della_nascita",
}


def _carica(nome: str) -> dict[str, Any]:
    percorso = CARTELLA / nome if nome == "strings.json" else CARTELLA / "translations" / nome
    return json.loads(percorso.read_text(encoding="utf-8"))


def _chiavi(nodo: Any, prefisso: str = "") -> Iterator[str]:
    if isinstance(nodo, dict):
        for chiave, valore in nodo.items():
            yield from _chiavi(valore, f"{prefisso}.{chiave}" if prefisso else chiave)
    else:
        yield prefisso


def test_strings_json_uguale_all_inglese() -> None:
    assert _carica("strings.json") == _carica("en.json")


def test_italiano_con_le_stesse_chiavi_dell_inglese() -> None:
    assert set(_chiavi(_carica("it.json"))) == set(_chiavi(_carica("en.json")))


def test_ogni_modello_ha_un_nome_tradotto() -> None:
    for lingua in ("en.json", "it.json"):
        assert set(_carica(lingua)["selector"]["modello"]["options"]) == set(MODELLI)


def test_errori_dei_form_tradotti() -> None:
    errori = _carica("en.json")["config_subentries"]["scadenza"]["error"]
    assert ERRORI_SCADENZA <= set(errori)
