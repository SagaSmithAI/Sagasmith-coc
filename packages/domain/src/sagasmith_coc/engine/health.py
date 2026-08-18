"""Deterministic CoC 7e hit-point, major-wound, and healing transitions."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def apply_damage(
    sheet: dict[str, Any],
    amount: int,
    *,
    con_check_success: bool | None = None,
) -> dict[str, Any]:
    """Apply one blow without rolling the required CON check inside this layer."""

    if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
        raise ValueError("damage amount must be a non-negative integer")
    value = deepcopy(dict(sheet))
    maximum = int(value.get("max_hp", 0))
    current = int(value.get("hp", maximum))
    if maximum < 1 or not 0 <= current <= maximum:
        raise ValueError("sheet requires valid current and maximum hit points")
    conditions = dict(value.get("conditions") or {})
    if bool(conditions.get("dead", False)):
        raise ValueError("damage cannot be applied to a dead actor")

    instant_death = amount >= maximum and amount > 0
    single_blow_major = amount * 2 >= maximum and amount > 0
    prior_major = bool(conditions.get("major_wound", False))
    major_wound = prior_major or single_blow_major
    new_hp = max(0, current - amount)
    requires_con_check = single_blow_major and not instant_death
    if requires_con_check and con_check_success is None:
        unconscious = new_hp == 0
    else:
        unconscious = new_hp == 0 or (requires_con_check and con_check_success is False)
    dying = major_wound and new_hp == 0 and not instant_death
    conditions.update(
        {
            "major_wound": major_wound,
            "unconscious": unconscious and not instant_death,
            "dying": dying,
            "dead": instant_death,
        }
    )
    value["hp"] = new_hp
    value["conditions"] = conditions
    return {
        "sheet": value,
        "amount": amount,
        "previous_hp": current,
        "new_hp": new_hp,
        "maximum_hp": maximum,
        "single_blow_major_wound": single_blow_major,
        "requires_con_check": requires_con_check and con_check_success is None,
        "con_check_success": con_check_success,
        "conditions": conditions,
    }


def apply_healing(
    sheet: dict[str, Any],
    amount: int,
    *,
    source: str,
    extreme_success: bool = False,
) -> dict[str, Any]:
    """Apply source-explicit healing and its standard wound-condition effects."""

    if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
        raise ValueError("healing amount must be a non-negative integer")
    source_value = str(source or "").strip().casefold()
    if source_value not in {"natural", "first_aid", "medicine", "other"}:
        raise ValueError("healing source must be natural, first_aid, medicine, or other")
    value = deepcopy(dict(sheet))
    maximum = int(value.get("max_hp", 0))
    current = int(value.get("hp", maximum))
    if maximum < 1 or not 0 <= current <= maximum:
        raise ValueError("sheet requires valid current and maximum hit points")
    conditions = dict(value.get("conditions") or {})
    if bool(conditions.get("dead", False)):
        raise ValueError("healing cannot restore a dead actor")
    new_hp = min(maximum, current + amount)
    if source_value == "first_aid":
        conditions["dying"] = False
        conditions["unconscious"] = False
    elif amount > 0 and new_hp > 0:
        conditions["unconscious"] = False
    if bool(conditions.get("major_wound", False)) and (extreme_success or new_hp * 2 >= maximum):
        conditions["major_wound"] = False
    value["hp"] = new_hp
    value["conditions"] = conditions
    return {
        "sheet": value,
        "amount": amount,
        "source": source_value,
        "extreme_success": bool(extreme_success),
        "previous_hp": current,
        "new_hp": new_hp,
        "maximum_hp": maximum,
        "conditions": conditions,
    }
