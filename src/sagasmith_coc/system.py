"""CoC 7e system definition and investigator validation."""

from __future__ import annotations

from typing import Any

from sagasmith_core.systems import SystemDefinition

_CHARACTERISTICS = ("str", "con", "siz", "dex", "app", "int", "pow", "edu")


def damage_bonus_and_build(strength: int, size: int) -> tuple[str, int]:
    total = strength + size
    if total <= 64:
        return "-2", -2
    if total <= 84:
        return "-1", -1
    if total <= 124:
        return "0", 0
    if total <= 164:
        return "1D4", 1
    if total <= 204:
        return "1D6", 2
    extra = (total - 205) // 80
    return f"{2 + extra}D6", 3 + extra


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
    pulp = bool(value.get("pulp", False) or value.get("ruleset") == "pulp")
    default_hp = (characteristics["con"] + characteristics["siz"]) // 10
    if pulp:
        default_hp *= 2
    max_hp = max(1, int(value.get("max_hp", default_hp)))
    max_mp = max(0, int(value.get("max_mp", characteristics["pow"] // 5)))
    mythos = max(0, min(100, int(value.get("cthulhu_mythos", 0))))
    san_max = max(0, 99 - mythos)
    value["max_hp"] = max_hp
    value["hp"] = max(0, min(max_hp, int(value.get("hp", max_hp))))
    value["max_mp"] = max_mp
    value["mp"] = max(0, min(max_mp, int(value.get("mp", max_mp))))
    value["san_max"] = san_max
    value["san"] = max(0, min(san_max, int(value.get("san", characteristics["pow"]))))
    value["san_daily_loss"] = max(0, int(value.get("san_daily_loss", 0)))
    value["san_daily_limit"] = max(
        1,
        int(value.get("san_daily_limit", value["san"] // 5)),
    )
    value["luck"] = max(0, min(100, int(value.get("luck", 50))))
    value["mov"] = max(1, int(value.get("mov", 8)))
    damage_bonus, build = damage_bonus_and_build(
        characteristics["str"],
        characteristics["siz"],
    )
    value.setdefault("damage_bonus", damage_bonus)
    value.setdefault("build", build)
    value.setdefault("dodge", characteristics["dex"] // 2)
    value.setdefault("occupation", "")
    value.setdefault("archetype", "")
    value["skills"] = {
        str(name): max(0, min(100, int(score)))
        for name, score in dict(value.get("skills", {})).items()
    }
    value.setdefault("weapons", [])
    value.setdefault(
        "conditions",
        {
            "major_wound": False,
            "dying": False,
            "unconscious": False,
            "temporary_insanity": False,
            "indefinite_insanity": False,
        },
    )
    value["cthulhu_mythos"] = mythos
    value.setdefault(
        "development",
        {
            "personal": characteristics["int"] * 2,
            "occupation": 0,
            "archetype": 0,
            "experience_package": 0,
            "checked_skills": [],
        },
    )
    value.setdefault("biography", [])
    value.setdefault("sanity_loss_events", [])
    value.setdefault("inventory", [])
    value.setdefault("books", [])
    value.setdefault("monetary", {})
    value.setdefault("backstory", {})
    value.setdefault("pulp_talents", [])
    value["ruleset"] = "pulp" if pulp else value.get("ruleset", "classic")
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
