"""Canonical, source-preserving CoC 7e statblock validation."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

CHARACTERISTICS = frozenset({"str", "con", "siz", "dex", "app", "int", "pow", "edu"})
ACTOR_TYPES = frozenset({"investigator", "npc", "creature"})
STATBLOCK_FIELDS = frozenset(
    {
        "schema_version",
        "actor_type",
        "name",
        "characteristics",
        "hit_points",
        "magic_points",
        "move",
        "build",
        "damage_bonus",
        "dodge",
        "armor",
        "skills",
        "attacks",
        "sanity_loss",
        "notes",
        "combat_ready",
    }
)
ATTACK_FIELDS = frozenset(
    {
        "name",
        "skill",
        "damage",
        "range",
        "attacks_per_round",
        "ammo",
        "impale",
        "notes",
    }
)


def _score(value: Any, field: str, *, maximum: int = 999) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise ValueError(f"{field} must be an integer between 0 and {maximum}")
    return value


def _text(value: Any, field: str, *, maximum: int = 500) -> str:
    result = str(value or "").strip()
    if not result or len(result) > maximum:
        raise ValueError(f"{field} must contain 1 to {maximum} characters")
    return result


def validate_coc7e_statblock(statblock: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one reviewed statblock without inventing omitted source facts.

    The canonical form deliberately permits partial non-combat NPC cards. Setting
    ``combat_ready`` to true opts into the fields needed for authoritative combat.
    """

    if not isinstance(statblock, Mapping):
        raise TypeError("CoC statblock must be an object")
    unknown = sorted(set(statblock) - STATBLOCK_FIELDS)
    if unknown:
        raise ValueError("CoC statblock has unsupported fields: " + ", ".join(unknown))
    value = deepcopy(dict(statblock))
    if value.get("schema_version", 1) != 1:
        raise ValueError("CoC statblock schema_version must be 1")
    value["schema_version"] = 1
    actor_type = str(value.get("actor_type") or "").strip()
    if actor_type not in ACTOR_TYPES:
        raise ValueError("CoC statblock actor_type must be investigator, npc, or creature")
    value["actor_type"] = actor_type
    value["name"] = _text(value.get("name"), "CoC statblock name", maximum=200)

    characteristics = value.get("characteristics", {})
    if not isinstance(characteristics, Mapping):
        raise ValueError("CoC statblock characteristics must be an object")
    unsupported_characteristics = sorted(set(characteristics) - CHARACTERISTICS)
    if unsupported_characteristics:
        raise ValueError(
            "CoC statblock has unsupported characteristics: "
            + ", ".join(unsupported_characteristics)
        )
    value["characteristics"] = {
        str(name): _score(score, f"characteristics.{name}")
        for name, score in characteristics.items()
    }

    if "hit_points" in value:
        hit_points = value["hit_points"]
        if not isinstance(hit_points, Mapping) or set(hit_points) != {"current", "maximum"}:
            raise ValueError("CoC statblock hit_points requires exactly current and maximum")
        maximum = _score(hit_points["maximum"], "hit_points.maximum")
        current = _score(hit_points["current"], "hit_points.current")
        if maximum < 1 or current > maximum:
            raise ValueError(
                "CoC statblock hit_points requires 0 <= current <= maximum and max > 0"
            )
        value["hit_points"] = {"current": current, "maximum": maximum}
    for field in ("magic_points", "move", "dodge"):
        if field in value:
            value[field] = _score(value[field], field)
    if "move" in value and value["move"] < 1:
        raise ValueError("CoC statblock move must be positive")
    if "build" in value:
        build = value["build"]
        if isinstance(build, bool) or not isinstance(build, int) or not -10 <= build <= 100:
            raise ValueError("CoC statblock build must be an integer between -10 and 100")
    if "damage_bonus" in value:
        value["damage_bonus"] = _text(value["damage_bonus"], "damage_bonus", maximum=100)
    if "armor" in value:
        armor = value["armor"]
        if isinstance(armor, bool) or not isinstance(armor, (int, str)):
            raise ValueError("CoC statblock armor must be an integer or source-explicit string")
        if isinstance(armor, int):
            value["armor"] = _score(armor, "armor")
        else:
            value["armor"] = _text(armor, "armor", maximum=500)
    if "sanity_loss" in value:
        value["sanity_loss"] = _text(value["sanity_loss"], "sanity_loss", maximum=100)

    skills = value.get("skills", {})
    if not isinstance(skills, Mapping):
        raise ValueError("CoC statblock skills must be an object")
    normalized_skills: dict[str, int] = {}
    for name, score in skills.items():
        skill_name = _text(name, "skill name", maximum=200)
        if skill_name in normalized_skills:
            raise ValueError(f"duplicate CoC statblock skill: {skill_name}")
        normalized_skills[skill_name] = _score(score, f"skills.{skill_name}")
    value["skills"] = normalized_skills

    attacks = value.get("attacks", [])
    if not isinstance(attacks, list) or any(not isinstance(item, Mapping) for item in attacks):
        raise ValueError("CoC statblock attacks must be an array of objects")
    normalized_attacks = []
    for index, item in enumerate(attacks):
        attack = deepcopy(dict(item))
        unknown_attack = sorted(set(attack) - ATTACK_FIELDS)
        if unknown_attack:
            raise ValueError(
                f"CoC statblock attack {index} has unsupported fields: " + ", ".join(unknown_attack)
            )
        for field in ("name", "damage"):
            attack[field] = _text(attack.get(field), f"attacks[{index}].{field}", maximum=200)
        if "skill" in attack:
            attack["skill"] = _score(attack["skill"], f"attacks[{index}].skill")
        for field in ("attacks_per_round", "ammo"):
            if field in attack:
                attack[field] = _score(attack[field], f"attacks[{index}].{field}")
        if "attacks_per_round" in attack and attack["attacks_per_round"] < 1:
            raise ValueError(f"attacks[{index}].attacks_per_round must be positive")
        if "range" in attack:
            attack["range"] = _text(attack["range"], f"attacks[{index}].range", maximum=200)
        if "notes" in attack:
            attack["notes"] = _text(attack["notes"], f"attacks[{index}].notes", maximum=500)
        if "impale" in attack and not isinstance(attack["impale"], bool):
            raise ValueError(f"attacks[{index}].impale must be a boolean")
        normalized_attacks.append(attack)
    value["attacks"] = normalized_attacks

    notes = value.get("notes", [])
    if not isinstance(notes, list):
        raise ValueError("CoC statblock notes must be an array")
    value["notes"] = [
        _text(note, f"notes[{index}]", maximum=1000) for index, note in enumerate(notes)
    ]
    combat_ready = value.get("combat_ready", False)
    if not isinstance(combat_ready, bool):
        raise ValueError("CoC statblock combat_ready must be a boolean")
    value["combat_ready"] = combat_ready

    mechanical_fields = {
        "characteristics": bool(value["characteristics"]),
        "hit_points": "hit_points" in value,
        "skills": bool(value["skills"]),
        "attacks": bool(value["attacks"]),
        "sanity_loss": "sanity_loss" in value,
    }
    if not any(mechanical_fields.values()):
        raise ValueError("CoC statblock must contain at least one source-backed mechanic")
    if combat_ready:
        missing = []
        if "dex" not in value["characteristics"]:
            missing.append("characteristics.dex")
        if "hit_points" not in value:
            missing.append("hit_points")
        if not value["attacks"]:
            missing.append("attacks")
        if missing:
            raise ValueError("combat-ready CoC statblock is missing: " + ", ".join(missing))
    return value


def coc7e_statblock_readiness(statblock: Mapping[str, Any]) -> dict[str, Any]:
    """Return advisory runtime readiness after canonical validation."""

    value = validate_coc7e_statblock(statblock)
    missing = []
    for field in ("str", "con", "siz", "dex", "pow"):
        if field not in value["characteristics"]:
            missing.append(f"characteristics.{field}")
    for field in ("hit_points", "move"):
        if field not in value:
            missing.append(field)
    if not value["attacks"]:
        missing.append("attacks")
    return {
        "combat_ready": not missing,
        "missing_for_combat": missing,
        "advisory_only": not bool(value["combat_ready"]),
    }
