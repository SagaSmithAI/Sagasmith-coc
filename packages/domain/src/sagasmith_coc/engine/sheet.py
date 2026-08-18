"""Canonical reads from a validated Call of Cthulhu investigator sheet."""

from __future__ import annotations

from typing import Any

from sagasmith_coc.system import validate_investigator_sheet


def exact_sheet_value(values: dict[str, Any], name: str, label: str) -> int:
    """Return one case-insensitive numeric value without guessing duplicates."""

    requested = str(name or "").strip()
    if not requested:
        raise ValueError(f"{label} name is required")
    folded = requested.casefold()
    matches = [int(value) for key, value in values.items() if str(key).casefold() == folded]
    if len(matches) != 1:
        raise ValueError(f"actor sheet must contain exactly one {label} {requested!r}")
    return matches[0]


def combat_weapon(sheet: dict[str, Any], weapon_name: str) -> dict[str, Any]:
    """Return the canonical mechanical fields for one named weapon."""

    value = validate_investigator_sheet(sheet)
    requested = str(weapon_name or "").strip()
    if not requested:
        raise ValueError("weapon_name is required")
    folded = requested.casefold()
    matches = [
        dict(item)
        for item in list(value.get("weapons") or [])
        if isinstance(item, dict) and str(item.get("name") or "").casefold() == folded
    ]
    if len(matches) != 1:
        raise ValueError(f"actor sheet must contain exactly one weapon named {requested!r}")
    weapon = matches[0]
    skill_field = weapon.get("skill")
    skill_name = (
        str(dict(skill_field).get("name") or "").strip()
        if isinstance(skill_field, dict)
        else str(skill_field or "").strip()
    )
    damage = str(weapon.get("damage") or "").strip()
    if not skill_name or not damage:
        raise ValueError("combat weapon requires skill and damage")
    properties = dict(weapon.get("properties") or {})
    return {
        **weapon,
        "name": requested,
        "skill_name": skill_name,
        "damage": damage,
        "ranged": bool(properties.get("rngd", False)),
        "impaling": bool(properties.get("impl", False)),
    }


def investigation_trait(
    sheet: dict[str, Any], trait_kind: str, trait_name: str
) -> tuple[str, str, int]:
    """Resolve one skill, characteristic, or Luck declaration."""

    value = validate_investigator_sheet(sheet)
    kind = str(trait_kind or "skill").strip().casefold()
    name = str(trait_name or "").strip()
    if kind == "luck":
        if name and name.casefold() != "luck":
            raise ValueError("a luck roll must use trait_name='Luck'")
        return "luck", "Luck", int(value["luck"])
    if not name:
        raise ValueError("data.trait_name is required")
    if kind == "skill":
        return kind, name, exact_sheet_value(dict(value.get("skills") or {}), name, "skill")
    if kind == "characteristic":
        return (
            kind,
            name,
            exact_sheet_value(
                dict(value.get("characteristics") or {}),
                name,
                "characteristic",
            ),
        )
    raise ValueError("trait_kind must be skill, characteristic, or luck")


def investigation_combined_traits(
    sheet: dict[str, Any],
    raw_traits: Any,
    *,
    default_difficulty: str = "regular",
) -> list[dict[str, Any]]:
    """Normalize the traits for one Keeper-declared combined check."""

    if not isinstance(raw_traits, list):
        raise ValueError("data.traits must be an array for a combined check")
    values = []
    for raw in raw_traits:
        if not isinstance(raw, dict):
            raise ValueError("every combined trait must be an object")
        kind, name, threshold = investigation_trait(
            sheet,
            str(raw.get("trait_kind") or raw.get("kind") or "skill"),
            str(raw.get("trait_name") or raw.get("name") or ""),
        )
        if kind == "luck":
            raise ValueError("Luck cannot be one component of a combined check")
        values.append(
            {
                "kind": kind,
                "name": name,
                "threshold": threshold,
                "difficulty": str(raw.get("difficulty") or default_difficulty),
            }
        )
    return values


def development_skill_eligible(skill_name: str) -> bool:
    """Return whether a skill uses the ordinary development procedure."""

    return str(skill_name).strip().casefold() != "cthulhu mythos"
