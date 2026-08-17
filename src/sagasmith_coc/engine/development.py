"""Deterministic Call of Cthulhu 7e development mechanics."""

from __future__ import annotations

from typing import Any

from sagasmith_coc.random_stream import randint
from sagasmith_coc.system import validate_investigator_sheet

from .sheet import development_skill_eligible, exact_sheet_value


def _percentile(value: int, *, field: str) -> int:
    result = int(value)
    if not 0 <= result <= 100:
        raise ValueError(f"{field} must be between 0 and 100")
    return result


def _die(value: int | None, sides: int, *, field: str) -> int:
    result = randint(1, sides) if value is None else int(value)
    if not 1 <= result <= sides:
        raise ValueError(f"{field} must be between 1 and {sides}")
    return result


def resolve_skill_development(
    current_value: int,
    *,
    improvement_roll: int | None = None,
    gain_roll: int | None = None,
    mastery_san_rolls: tuple[int, int] | None = None,
) -> dict[str, Any]:
    """Resolve one checked skill at the end of a session or scenario.

    The skill improves only when the percentile roll is greater than its
    current value. A successful improvement adds 1D10, capped at 100. The
    existing 7e mastery reward is emitted only when this improvement first
    crosses 90; callers remain responsible for applying SAN against SAN max.
    """

    current = _percentile(current_value, field="current_value")
    check = _die(improvement_roll, 100, field="improvement_roll")
    if check <= current:
        if gain_roll is not None or mastery_san_rolls is not None:
            raise ValueError("gain and mastery rolls are not used when the skill does not improve")
        return {
            "current_value": current,
            "improvement_roll": check,
            "improved": False,
            "gain_roll": None,
            "gain": 0,
            "new_value": current,
            "mastered": False,
            "mastery_san_rolls": [],
            "san_recovery": 0,
            "summary_line": f"Skill did not improve ({check} <= {current}).",
        }

    gain = _die(gain_roll, 10, field="gain_roll")
    new_value = min(100, current + gain)
    mastered = current < 90 <= new_value
    san_rolls: list[int] = []
    if mastered:
        supplied = mastery_san_rolls or (None, None)
        san_rolls = [
            _die(supplied[0], 6, field="mastery_san_roll_1"),
            _die(supplied[1], 6, field="mastery_san_roll_2"),
        ]
    elif mastery_san_rolls is not None:
        raise ValueError("mastery SAN rolls are used only when the skill first reaches 90")
    san_recovery = sum(san_rolls)
    return {
        "current_value": current,
        "improvement_roll": check,
        "improved": True,
        "gain_roll": gain,
        "gain": gain,
        "new_value": new_value,
        "mastered": mastered,
        "mastery_san_rolls": san_rolls,
        "san_recovery": san_recovery,
        "summary_line": (
            f"Skill improved {current} -> {new_value} (+{gain})."
            + (f" Mastery restores {san_recovery} SAN." if mastered else "")
        ),
    }


def resolve_luck_development(
    current_luck: int,
    *,
    improvement_roll: int | None = None,
    gain_rolls: tuple[int, int] | None = None,
) -> dict[str, Any]:
    """Resolve the package's optional Luck-development procedure.

    This helper preserves the existing 2D10 procedure for profiles that opt
    into it. The MCP must never invoke it unless the active campaign settings
    explicitly select that Luck-recovery rule.
    """

    current = _percentile(current_luck, field="current_luck")
    check = _die(improvement_roll, 100, field="improvement_roll")
    if check <= current:
        if gain_rolls is not None:
            raise ValueError("gain rolls are not used when Luck does not improve")
        return {
            "current_value": current,
            "improvement_roll": check,
            "improved": False,
            "gain_rolls": [],
            "gain": 0,
            "new_value": current,
            "summary_line": f"Luck did not improve ({check} <= {current}).",
        }
    supplied = gain_rolls or (None, None)
    rolls = [
        _die(supplied[0], 10, field="gain_roll_1"),
        _die(supplied[1], 10, field="gain_roll_2"),
    ]
    gain = sum(rolls)
    new_value = min(100, current + gain)
    return {
        "current_value": current,
        "improvement_roll": check,
        "improved": True,
        "gain_rolls": rolls,
        "gain": gain,
        "new_value": new_value,
        "summary_line": f"Luck improved {current} -> {new_value} (+{gain}).",
    }


def mark_skill_for_development(success_level: int) -> bool:
    """Return whether an ordinary skill success earns its single check mark."""

    from .checks.skill import SuccessLevel

    return int(success_level) >= int(SuccessLevel.REGULAR)


def development_query(sheet: dict[str, Any]) -> list[dict[str, Any]]:
    """Describe every checked skill without mutating the investigator sheet."""

    value = validate_investigator_sheet(sheet)
    checked = [
        str(item).strip()
        for item in list(dict(value.get("development") or {}).get("checked_skills") or [])
        if str(item).strip()
    ]
    if len({name.casefold() for name in checked}) != len(checked):
        raise ValueError("checked skill names must be unique")
    skills = dict(value.get("skills") or {})
    actual_names = {str(name).casefold(): str(name) for name in skills}
    pending = []
    for skill_name in checked:
        canonical_name = actual_names.get(skill_name.casefold())
        if canonical_name is None:
            raise ValueError(f"checked skill is missing from actor sheet: {skill_name!r}")
        eligible = development_skill_eligible(canonical_name)
        pending.append(
            {
                "skill_name": canonical_name,
                "current_value": exact_sheet_value(skills, canonical_name, "skill"),
                "eligible": eligible,
                "reason": (
                    None
                    if eligible
                    else "Cthulhu Mythos does not use ordinary development checks"
                ),
            }
        )
    return pending


def settle_development(
    sheet: dict[str, Any],
    *,
    source: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve and clear all checked skills under the active random context.

    Random authority remains with the caller: an MCP campaign stream can be
    installed with ``use_random_stream`` before this pure sheet transition is
    called.  The returned receipt contains only system-mechanical facts.
    """

    source_value = " ".join(str(source or "").split()).strip()
    if not source_value or len(source_value) > 500:
        raise ValueError("source must contain 1 to 500 characters")
    value = validate_investigator_sheet(sheet)
    pending = development_query(value)
    if not pending:
        raise ValueError("actor has no checked skills awaiting development")
    skills = dict(value.get("skills") or {})
    development = dict(value.get("development") or {})
    results: list[dict[str, Any]] = []
    san_before = int(value["san"])
    san_current = san_before
    for item in pending:
        skill_name = str(item["skill_name"])
        current = int(item["current_value"])
        if not bool(item["eligible"]):
            results.append(dict(item))
            continue
        result = resolve_skill_development(current)
        skills[skill_name] = int(result["new_value"])
        san_gain = min(
            int(result["san_recovery"]),
            max(0, int(value["san_max"]) - san_current),
        )
        san_current += san_gain
        results.append(
            {
                "skill_name": skill_name,
                "eligible": True,
                **result,
                "san_applied": san_gain,
            }
        )
    receipt = {
        "sequence": len(list(development.get("history") or [])) + 1,
        "source": source_value,
        "results": results,
        "san_before": san_before,
        "san_after": san_current,
    }
    development["checked_skills"] = []
    development["history"] = [*list(development.get("history") or [])[-99:], receipt]
    next_sheet = validate_investigator_sheet(
        {
            **value,
            "skills": skills,
            "san": san_current,
            "development": development,
        }
    )
    return next_sheet, receipt
