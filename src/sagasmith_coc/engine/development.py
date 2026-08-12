"""Deterministic Call of Cthulhu 7e development mechanics."""

from __future__ import annotations

from typing import Any

from sagasmith_coc.random_stream import randint


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
