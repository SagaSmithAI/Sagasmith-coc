"""Canonical transitions for Call of Cthulhu investigation checks."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from sagasmith_coc.system import validate_investigator_sheet

from .checks.skill import resolve_combined_check, resolve_skill_check
from .dice.rolls import roll_d100
from .sheet import investigation_combined_traits, investigation_trait


def resolve_investigation_check(
    sheet: dict[str, Any],
    declaration: dict[str, Any],
    *,
    investigator_name: str = "",
    pushed: bool = False,
) -> dict[str, Any]:
    """Roll and resolve one explicit single or combined check declaration.

    The caller owns authorization, the random-stream context, persistence, and the
    semantic source/goal for the check. This transition owns only canonical sheet
    normalization and CoC percentile mechanics.
    """

    value = validate_investigator_sheet(sheet)
    data = deepcopy(dict(declaration or {}))
    difficulty = str(data.get("difficulty") or "regular")
    bonus_dice = int(data.get("bonus_dice", 0))
    penalty_dice = int(data.get("penalty_dice", 0))
    roll = roll_d100(bonus_dice=bonus_dice, penalty_dice=penalty_dice)
    if data.get("traits") is not None:
        traits = investigation_combined_traits(
            value,
            data["traits"],
            default_difficulty=difficulty,
        )
        requirement = str(data.get("requirement") or "").strip().casefold()
        outcome = resolve_combined_check(
            int(roll["total"]),
            traits,
            requirement=requirement,
            bonus_dice=bonus_dice,
            penalty_dice=penalty_dice,
            pushed=pushed,
        )
        shape: dict[str, Any] = {
            "check_kind": "combined",
            "traits": traits,
            "requirement": requirement,
        }
    else:
        trait_kind, trait_name, threshold = investigation_trait(
            value,
            str(data.get("trait_kind") or "skill"),
            str(data.get("trait_name") or ""),
        )
        outcome = resolve_skill_check(
            int(roll["total"]),
            threshold,
            difficulty=difficulty,
            bonus_dice=bonus_dice,
            penalty_dice=penalty_dice,
            skill_name=trait_name,
            investigator_name=investigator_name,
            pushed=pushed,
            roll_kind=trait_kind,
        )
        shape = {
            "check_kind": "single",
            "trait_kind": trait_kind,
            "trait_name": trait_name,
            "threshold": threshold,
            "difficulty": difficulty,
        }
    return {
        **shape,
        "bonus_dice": bonus_dice,
        "penalty_dice": penalty_dice,
        "roll": roll,
        "outcome": outcome,
    }


def spend_luck_on_investigation(
    sheet: dict[str, Any],
    check: dict[str, Any],
    luck_spent: int,
    *,
    investigator_name: str = "",
) -> dict[str, Any]:
    """Apply an exact legal Luck purchase and return the next sheet and outcome."""

    value = validate_investigator_sheet(sheet)
    pending = deepcopy(dict(check or {}))
    spent = int(luck_spent)
    if spent <= 0 or spent > int(value["luck"]):
        raise ValueError("luck_spent must be positive and no greater than current Luck")
    if pending.get("check_kind") == "combined":
        outcome = resolve_combined_check(
            int(dict(pending["roll"])["total"]),
            list(pending["traits"]),
            requirement=str(pending["requirement"]),
            bonus_dice=int(pending["bonus_dice"]),
            penalty_dice=int(pending["penalty_dice"]),
            luck_spent=spent,
        )
    elif pending.get("check_kind") == "single":
        outcome = resolve_skill_check(
            int(dict(pending["roll"])["total"]),
            int(pending["threshold"]),
            difficulty=str(pending["difficulty"]),
            bonus_dice=int(pending["bonus_dice"]),
            penalty_dice=int(pending["penalty_dice"]),
            luck_spent=spent,
            skill_name=str(pending["trait_name"]),
            investigator_name=investigator_name,
            roll_kind=str(pending["trait_kind"]),
        )
    else:
        raise ValueError("check_kind must be single or combined")
    next_sheet = deepcopy(value)
    before = int(value["luck"])
    next_sheet["luck"] = before - spent
    next_sheet["luck_events"] = [
        *list(value.get("luck_events") or [])[-499:],
        {
            "check_id": str(pending.get("id") or ""),
            "source": str(pending.get("source") or ""),
            "spent": spent,
            "before": before,
            "after": before - spent,
        },
    ]
    return {"sheet": validate_investigator_sheet(next_sheet), "outcome": outcome}
