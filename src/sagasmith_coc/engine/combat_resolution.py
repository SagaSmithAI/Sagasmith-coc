"""Canonical aggregate transitions for Call of Cthulhu combat attacks."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from sagasmith_coc.system import validate_investigator_sheet

from .checks.combat import resolve_melee_attack, resolve_ranged_attack
from .checks.skill import resolve_skill_check
from .combat_state import outnumbering_bonus_dice, record_attack, record_defense
from .dice.rolls import roll_d100
from .health import apply_damage
from .sheet import combat_weapon, exact_sheet_value


def combat_attack_profile(sheet: dict[str, Any], weapon_name: str) -> dict[str, Any]:
    """Return canonical weapon, threshold, and response options for an attack."""

    value = validate_investigator_sheet(sheet)
    weapon = combat_weapon(value, weapon_name)
    if weapon["ranged"] and int(weapon.get("ammo", 0)) < 1:
        raise ValueError("ranged weapon has no ammunition")
    threshold = exact_sheet_value(
        dict(value.get("skills") or {}),
        str(weapon["skill_name"]),
        "combat skill",
    )
    return {
        "weapon": weapon,
        "attacker_threshold": threshold,
        "damage_bonus": str(value.get("damage_bonus") or "0"),
        "response_options": (
            ["none", "dive_for_cover"]
            if weapon["ranged"]
            else ["none", "dodge", "fight-back"]
        ),
    }


def resolve_combat_attack(
    combat: dict[str, Any],
    attacker_sheet: dict[str, Any],
    target_sheet: dict[str, Any],
    attack: dict[str, Any],
    *,
    defense: str,
    attacker_name: str = "",
    target_name: str = "",
    target_weapon_name: str | None = None,
) -> dict[str, Any]:
    """Resolve an explicit attack response and return canonical state deltas.

    The caller supplies an authoritative random-stream context and owns actor
    authorization, revisions, persistence, idempotency, and audience projection.
    """

    state = deepcopy(dict(combat))
    pending = deepcopy(dict(attack))
    attacker = validate_investigator_sheet(attacker_sheet)
    target = validate_investigator_sheet(target_sheet)
    attacker_id = str(pending.get("attacker_id") or "").strip()
    target_id = str(pending.get("target_actor_id") or "").strip()
    if not attacker_id or not target_id or attacker_id == target_id:
        raise ValueError("attack requires distinct attacker and target actor ids")
    options = list(pending.get("response_options") or [])
    if defense not in options:
        raise ValueError("defense must be one of " + ", ".join(options))
    weapon = dict(pending["weapon"])
    target_weapon = None
    target_threshold = None
    if defense == "dodge":
        target_threshold = int(target["dodge"])
    elif defense == "fight-back":
        target_weapon = combat_weapon(target, str(target_weapon_name or ""))
        if target_weapon["ranged"]:
            raise ValueError("a ranged weapon cannot be used to fight back")
        target_threshold = exact_sheet_value(
            dict(target.get("skills") or {}),
            str(target_weapon["skill_name"]),
            "combat skill",
        )

    defense_roll = None
    dive_success = False
    if defense in {"dodge", "fight-back", "dive_for_cover"}:
        defense_roll = roll_d100()
    if defense == "dive_for_cover":
        dodge = resolve_skill_check(
            int(defense_roll["total"]),
            int(target["dodge"]),
            skill_name="Dodge",
            investigator_name=target_name,
        )
        dive_success = bool(dodge["success"])
    bonus_dice = outnumbering_bonus_dice(
        state,
        target_id,
        ranged=bool(weapon["ranged"]),
    )
    penalty_dice = 1 if dive_success else 0
    attack_roll = roll_d100(bonus_dice=bonus_dice, penalty_dice=penalty_dice)
    if weapon["ranged"]:
        resolution = resolve_ranged_attack(
            int(attack_roll["total"]),
            int(pending["attacker_threshold"]),
            str(weapon["damage"]),
            range_band=str(pending["range_band"]),
            damage_bonus=str(pending["damage_bonus"]),
            bonus_dice=bonus_dice,
            penalty_dice=penalty_dice,
            malfunction=(
                int(weapon["malfunction"])
                if weapon.get("malfunction") is not None
                else None
            ),
            attacker_name=attacker_name,
            weapon_name=str(weapon["name"]),
            impaling=bool(weapon["impaling"]),
        )
    else:
        resolution = resolve_melee_attack(
            int(attack_roll["total"]),
            int(pending["attacker_threshold"]),
            damage_bonus=str(pending["damage_bonus"]),
            weapon_damage=str(weapon["damage"]),
            target_dodge=target_threshold if defense == "dodge" else None,
            target_fighting=target_threshold if defense == "fight-back" else None,
            target_roll=(int(defense_roll["total"]) if defense_roll is not None else None),
            defense=defense,
            bonus_dice=bonus_dice,
            attacker_name=attacker_name,
            weapon_name=str(weapon["name"]),
            target_weapon_damage=(str(target_weapon["damage"]) if target_weapon else None),
            target_damage_bonus=str(target.get("damage_bonus") or "0"),
            impaling=bool(weapon["impaling"]),
            target_impaling=bool(target_weapon and target_weapon["impaling"]),
        )

    damaged_id = None
    damage_value = 0
    if resolution.get("damage") is not None:
        damaged_id = target_id
        damage_value = int(resolution["damage"]["total"])
    elif resolution.get("counterattack") is not None:
        damaged_id = attacker_id
        damage_value = int(resolution["counterattack"]["total"])
    health_transition = None
    con_roll = None
    if damaged_id is not None:
        damaged_sheet = target if damaged_id == target_id else attacker
        preview = apply_damage(damaged_sheet, damage_value)
        con_success = None
        if preview["requires_con_check"]:
            con_roll = roll_d100()
            con_success = int(con_roll["total"]) <= int(
                damaged_sheet["characteristics"]["con"]
            )
        health_transition = apply_damage(
            damaged_sheet,
            damage_value,
            con_check_success=con_success,
        )

    next_combat = record_attack(state, attacker_id)
    if defense != "none":
        next_combat = record_defense(
            next_combat,
            target_id,
            dive_for_cover=defense == "dive_for_cover",
        )
    next_combat["pending_choice"] = None
    sheet_updates: dict[str, dict[str, Any]] = {}
    if weapon["ranged"]:
        next_attacker = deepcopy(attacker)
        next_weapons = [dict(item) for item in next_attacker["weapons"]]
        indexes = [
            index
            for index, item in enumerate(next_weapons)
            if str(item.get("name") or "").casefold() == str(weapon["name"]).casefold()
        ]
        if len(indexes) != 1:
            raise ValueError("resolved ranged weapon is no longer unique on the attacker sheet")
        next_weapons[indexes[0]]["ammo"] = int(weapon["ammo"]) - 1
        next_attacker["weapons"] = next_weapons
        sheet_updates[attacker_id] = next_attacker
    if health_transition is not None and damaged_id is not None:
        damaged_sheet = dict(health_transition["sheet"])
        if damaged_id in sheet_updates:
            damaged_sheet["weapons"] = sheet_updates[damaged_id]["weapons"]
        sheet_updates[damaged_id] = damaged_sheet
    return {
        "combat": next_combat,
        "resolution": resolution,
        "attack_roll": attack_roll,
        "defense_roll": defense_roll,
        "dive_success": dive_success,
        "damaged_actor_id": damaged_id,
        "health_transition": health_transition,
        "con_roll": con_roll,
        "sheet_updates": sheet_updates,
    }
