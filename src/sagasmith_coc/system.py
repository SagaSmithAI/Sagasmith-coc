"""CoC 7e system definition and investigator validation."""

from __future__ import annotations

from typing import Any

from sagasmith_core.systems import SystemDefinition

_CHARACTERISTICS = ("str", "con", "siz", "dex", "app", "int", "pow", "edu")


def validate_investigator_sheet(sheet: dict[str, Any]) -> dict[str, Any]:
    value = dict(sheet)
    characteristics = dict(value.get("characteristics", {}))
    for name in _CHARACTERISTICS:
        raw = characteristics.get(name, 50)
        if isinstance(raw, dict):
            raw = raw.get("value", 50)
        score = int(raw)
        if not 0 <= score <= 100:
            raise ValueError(f"{name} must be between 0 and 100")
        characteristics[name] = score
    value["characteristics"] = characteristics
    default_hp = (characteristics["con"] + characteristics["siz"]) // 10
    value["hp"] = max(0, int(value.get("hp", default_hp)))
    value["mp"] = max(0, int(value.get("mp", characteristics["pow"] // 5)))
    value["san"] = max(0, min(99, int(value.get("san", characteristics["pow"]))))
    value["luck"] = max(0, min(100, int(value.get("luck", 50))))
    value["mov"] = max(1, int(value.get("mov", 8)))
    value.setdefault("occupation", "")
    value.setdefault("skills", {})
    value.setdefault("weapons", [])
    value.setdefault("conditions", {})
    value.setdefault("cthulhu_mythos", 0)
    return value


COC7E = SystemDefinition(
    id="coc7e",
    display_name="Call of Cthulhu 7th Edition",
    character_types=("investigator", "npc", "creature"),
    campaign_defaults={
        "ruleset": "classic",
        "revision": "7e",
        "locale": "zh",
        "combat": None,
        "chase": None,
        "world": {},
    },
    validate_sheet=validate_investigator_sheet,
)


def get_system() -> SystemDefinition:
    return COC7E
