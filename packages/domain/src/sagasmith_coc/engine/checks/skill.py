"""Deterministic Call of Cthulhu 7e percentile-check mechanics."""

from __future__ import annotations

from enum import IntEnum
from typing import Any


class SuccessLevel(IntEnum):
    """Ordered CoC success levels; larger values are better."""

    FUMBLE = -99
    FAILURE = 0
    REGULAR = 1
    HARD = 2
    EXTREME = 3
    CRITICAL = 4


class Difficulty(IntEnum):
    """The minimum success level required by a check."""

    UNKNOWN = -1
    REGULAR = 1
    HARD = 2
    EXTREME = 3
    CRITICAL = 4
    IMPOSSIBLE = 9


DIFFICULTY_LABELS = {
    Difficulty.REGULAR: "Regular",
    Difficulty.HARD: "Hard",
    Difficulty.EXTREME: "Extreme",
    Difficulty.CRITICAL: "Critical",
    Difficulty.UNKNOWN: "Unknown",
    Difficulty.IMPOSSIBLE: "Impossible",
}

SUCCESS_LABELS = {
    SuccessLevel.FUMBLE: "Fumble",
    SuccessLevel.FAILURE: "Failure",
    SuccessLevel.REGULAR: "Regular success",
    SuccessLevel.HARD: "Hard success",
    SuccessLevel.EXTREME: "Extreme success",
    SuccessLevel.CRITICAL: "Critical success",
}

LUCK_ADJUSTABLE_ROLL_KINDS = frozenset({"skill", "characteristic"})
PUSHABLE_ROLL_KINDS = frozenset({"skill", "characteristic"})


def threshold_ranges(threshold: int, flat_threshold_modifier: int = 0) -> dict:
    """Return the non-overlapping roll ranges for each success level."""

    base = int(threshold)
    modifier = int(flat_threshold_modifier)
    if not 0 <= base <= 100:
        raise ValueError("threshold must be between 0 and 100")
    effective = max(0, min(100, base + modifier))
    extreme_max = effective // 5
    hard_max = effective // 2
    fumble_min = 96 if effective < 50 else 100
    result: dict[SuccessLevel, list[int]] = {SuccessLevel.CRITICAL: [1, 1]}
    if extreme_max >= 2:
        result[SuccessLevel.EXTREME] = [2, extreme_max]
    if hard_max >= max(2, extreme_max + 1):
        result[SuccessLevel.HARD] = [max(2, extreme_max + 1), hard_max]
    regular_max = min(effective, fumble_min - 1)
    if regular_max >= max(2, hard_max + 1):
        result[SuccessLevel.REGULAR] = [max(2, hard_max + 1), regular_max]
    if effective + 1 <= fumble_min - 1:
        result[SuccessLevel.FAILURE] = [max(2, effective + 1), fumble_min - 1]
    result[SuccessLevel.FUMBLE] = [fumble_min, 100]
    return result


def _difficulty(value: str | Difficulty) -> Difficulty:
    if isinstance(value, Difficulty):
        return value
    try:
        result = Difficulty[str(value).strip().upper()]
    except KeyError as error:
        raise ValueError(f"unsupported difficulty: {value}") from error
    if result in {Difficulty.UNKNOWN, Difficulty.IMPOSSIBLE}:
        raise ValueError(f"unsupported check difficulty: {value}")
    return result


def _success_level(total: int, ranges: dict[SuccessLevel, list[int]]) -> SuccessLevel:
    for level in sorted(ranges, reverse=True):
        low, high = ranges[level]
        if low <= total <= high:
            return level
    return SuccessLevel.FAILURE


def luck_spend_options(
    d100_total: int,
    threshold: int,
    *,
    flat_dice_modifier: int = 0,
    flat_threshold_modifier: int = 0,
    pushed: bool = False,
    roll_kind: str = "skill",
) -> dict[str, int]:
    """Return exact Luck costs for every legal improved success level.

    Spending Luck may improve a skill or characteristic roll to Regular,
    Hard, or Extreme. It cannot alter a fumble or a pushed, Luck, SAN,
    damage, or malfunction roll, and it cannot purchase a Critical success.
    """

    rolled = int(d100_total)
    if not 1 <= rolled <= 100:
        raise ValueError("d100_total must be between 1 and 100")
    kind = str(roll_kind).strip().casefold()
    current = max(1, min(100, rolled + int(flat_dice_modifier)))
    ranges = threshold_ranges(threshold, flat_threshold_modifier)
    current_level = _success_level(current, ranges)
    if pushed or kind not in LUCK_ADJUSTABLE_ROLL_KINDS or current_level == SuccessLevel.FUMBLE:
        return {}
    options: dict[str, int] = {}
    for level in (SuccessLevel.REGULAR, SuccessLevel.HARD, SuccessLevel.EXTREME):
        target = ranges.get(level)
        if target is None or level <= current_level:
            continue
        cost = current - target[1]
        if cost > 0:
            options[level.name.lower()] = cost
    return options


def resolve_skill_check(
    d100_total: int,
    threshold: int,
    difficulty: str | Difficulty = "regular",
    bonus_dice: int = 0,
    penalty_dice: int = 0,
    flat_dice_modifier: int = 0,
    flat_threshold_modifier: int = 0,
    luck_spent: int = 0,
    skill_name: str = "",
    investigator_name: str = "",
    *,
    pushed: bool = False,
    roll_kind: str = "skill",
) -> dict[str, Any]:
    """Resolve one already-rolled percentile check under CoC 7e rules."""

    rolled = int(d100_total)
    if not 1 <= rolled <= 100:
        raise ValueError("d100_total must be between 1 and 100")
    if not 0 <= int(bonus_dice) <= 2 or not 0 <= int(penalty_dice) <= 2:
        raise ValueError("bonus_dice and penalty_dice must be between 0 and 2")
    kind = str(roll_kind).strip().casefold()
    if not kind:
        raise ValueError("roll_kind is required")
    required_level = _difficulty(difficulty)
    ranges = threshold_ranges(int(threshold), int(flat_threshold_modifier))
    unadjusted_total = max(1, min(100, rolled + int(flat_dice_modifier)))
    original_level = _success_level(unadjusted_total, ranges)
    options = luck_spend_options(
        rolled,
        int(threshold),
        flat_dice_modifier=int(flat_dice_modifier),
        flat_threshold_modifier=int(flat_threshold_modifier),
        pushed=bool(pushed),
        roll_kind=kind,
    )
    spent = int(luck_spent)
    if spent < 0:
        raise ValueError("luck_spent must not be negative")
    if spent and spent not in set(options.values()):
        if pushed:
            raise ValueError("Luck cannot adjust a pushed roll")
        if original_level == SuccessLevel.FUMBLE:
            raise ValueError("Luck cannot adjust a fumble")
        if kind not in LUCK_ADJUSTABLE_ROLL_KINDS:
            raise ValueError(f"Luck cannot adjust a {kind} roll")
        raise ValueError("luck_spent must exactly purchase a listed success level")
    modified_total = max(1, unadjusted_total - spent)
    success_level = _success_level(modified_total, ranges)
    if spent and success_level == SuccessLevel.CRITICAL:
        success_level = SuccessLevel.EXTREME
    succeeded = success_level >= required_level
    original_succeeded = original_level >= required_level
    push_eligible = bool(
        not pushed
        and not spent
        and kind in PUSHABLE_ROLL_KINDS
        and not original_succeeded
    )
    success_label = SUCCESS_LABELS[success_level]
    name_label = investigator_name or "Investigator"
    skill_label = skill_name or kind.title()
    detail_lines = [
        f"{name_label}: {skill_label} {int(threshold)} at {required_level.name.lower()} difficulty",
        f"d100={rolled}; adjusted={modified_total}; {success_label}",
    ]
    if spent:
        detail_lines.append(f"Spent {spent} Luck")
    if pushed:
        detail_lines.append("Pushed roll")
    return {
        "d100": rolled,
        "unadjusted_total": unadjusted_total,
        "modified_total": modified_total,
        "threshold": int(threshold),
        "difficulty": required_level.name.lower(),
        "effective_threshold": max(
            0, min(100, int(threshold) + int(flat_threshold_modifier))
        ),
        "roll_kind": kind,
        "pushed": bool(pushed),
        "success": succeeded,
        "original_success": original_succeeded,
        "success_level": success_level,
        "original_success_level": original_level,
        "success_label": success_label,
        "is_critical": success_level == SuccessLevel.CRITICAL,
        "is_fumble": original_level == SuccessLevel.FUMBLE,
        "luck_spent": spent,
        "luck_options": options,
        "luck_eligible": bool(options),
        "push_eligible": push_eligible,
        "failed_pushed_roll": bool(pushed and not succeeded),
        "development_eligible": bool(kind == "skill" and succeeded),
        "detail_lines": detail_lines,
        "summary_line": (
            f"{name_label} ({skill_label} {int(threshold)}%): "
            f"d100={rolled}{f' -{spent} Luck' if spent else ''} -> {success_label}"
        ),
    }


def resolve_opposed_check(
    attacker_roll: int,
    attacker_threshold: int,
    defender_roll: int,
    defender_threshold: int,
    *,
    tie_breaker: str = "higher-skill",
) -> dict[str, Any]:
    """Resolve an opposed check by success level, skill value, then lower roll."""

    if tie_breaker not in {"higher-skill", "lower-roll"}:
        raise ValueError("tie_breaker must be higher-skill or lower-roll")
    attacker = resolve_skill_check(attacker_roll, attacker_threshold)
    defender = resolve_skill_check(defender_roll, defender_threshold)
    attacker_level = attacker["success_level"]
    defender_level = defender["success_level"]
    winner: str | None
    if attacker_level > defender_level:
        winner = "attacker"
    elif defender_level > attacker_level:
        winner = "defender"
    elif attacker_level < SuccessLevel.REGULAR:
        winner = None
    elif tie_breaker == "higher-skill" and attacker_threshold != defender_threshold:
        winner = "attacker" if attacker_threshold > defender_threshold else "defender"
    elif attacker_roll != defender_roll:
        winner = "attacker" if attacker_roll < defender_roll else "defender"
    else:
        winner = None
    return {
        "attacker": attacker,
        "defender": defender,
        "winner": winner,
        "tie": winner is None and attacker_level == defender_level,
        "tie_breaker": tie_breaker,
    }


def resolve_combined_check(
    d100_total: int,
    traits: list[dict[str, Any]],
    *,
    requirement: str,
    bonus_dice: int = 0,
    penalty_dice: int = 0,
    luck_spent: int = 0,
    pushed: bool = False,
) -> dict[str, Any]:
    """Compare one percentile result with two or more named traits.

    The Keeper must state whether success with any listed trait or every
    listed trait is required. Luck, when used, adjusts the shared roll and
    therefore every comparison. It must exactly buy the stated aggregate
    requirement and can never buy a Critical success.
    """

    rolled = int(d100_total)
    if not 1 <= rolled <= 100:
        raise ValueError("d100_total must be between 1 and 100")
    mode = str(requirement).strip().casefold()
    if mode not in {"any", "all"}:
        raise ValueError("requirement must be any or all")
    if not 2 <= len(traits) <= 8:
        raise ValueError("a combined check requires between 2 and 8 traits")
    if not 0 <= int(bonus_dice) <= 2 or not 0 <= int(penalty_dice) <= 2:
        raise ValueError("bonus_dice and penalty_dice must be between 0 and 2")
    normalized: list[dict[str, Any]] = []
    identities: set[tuple[str, str]] = set()
    for raw in traits:
        item = dict(raw)
        name = str(item.get("name") or "").strip()
        kind = str(item.get("kind") or "skill").strip().casefold()
        if not name:
            raise ValueError("every combined trait requires a name")
        if kind not in PUSHABLE_ROLL_KINDS:
            raise ValueError("combined traits must be skills or characteristics")
        identity = (kind, name.casefold())
        if identity in identities:
            raise ValueError("combined trait names must be unique within each kind")
        identities.add(identity)
        normalized.append(
            {
                "name": name,
                "kind": kind,
                "threshold": int(item["threshold"]),
                "difficulty": _difficulty(str(item.get("difficulty") or "regular")),
            }
        )

    unadjusted_total = rolled

    def component(item: dict[str, Any], total: int) -> dict[str, Any]:
        ranges = threshold_ranges(int(item["threshold"]))
        level = _success_level(total, ranges)
        required = item["difficulty"]
        return {
            "name": item["name"],
            "kind": item["kind"],
            "threshold": item["threshold"],
            "difficulty": required.name.lower(),
            "success": level >= required,
            "success_level": level,
            "success_label": SUCCESS_LABELS[level],
            "is_fumble": level == SuccessLevel.FUMBLE,
            "development_eligible": bool(
                item["kind"] == "skill" and level >= SuccessLevel.REGULAR
            ),
        }

    original_components = [component(item, unadjusted_total) for item in normalized]
    original_success = (
        any(item["success"] for item in original_components)
        if mode == "any"
        else all(item["success"] for item in original_components)
    )
    needed_costs: list[int | None] = []
    for item, result in zip(normalized, original_components, strict=True):
        if result["success"]:
            needed_costs.append(0)
            continue
        if pushed or result["is_fumble"] or item["difficulty"] == Difficulty.CRITICAL:
            needed_costs.append(None)
            continue
        target = threshold_ranges(int(item["threshold"])).get(
            SuccessLevel(int(item["difficulty"]))
        )
        needed_costs.append(None if target is None else unadjusted_total - target[1])
    aggregate_cost: int | None = None
    if not original_success:
        if mode == "any":
            candidates = [cost for cost in needed_costs if cost is not None and cost > 0]
            aggregate_cost = min(candidates) if candidates else None
        elif all(cost is not None for cost in needed_costs):
            aggregate_cost = max(int(cost) for cost in needed_costs)
    options = (
        {"meet_requirement": aggregate_cost}
        if aggregate_cost is not None and aggregate_cost > 0
        else {}
    )
    spent = int(luck_spent)
    if spent < 0:
        raise ValueError("luck_spent must not be negative")
    if spent and spent not in set(options.values()):
        if pushed:
            raise ValueError("Luck cannot adjust a pushed combined roll")
        if all(item["is_fumble"] for item in original_components):
            raise ValueError("Luck cannot adjust a fumbled combined roll")
        raise ValueError("luck_spent must exactly purchase the combined requirement")
    modified_total = max(1, unadjusted_total - spent)
    components = [component(item, modified_total) for item in normalized]
    success = (
        any(item["success"] for item in components)
        if mode == "any"
        else all(item["success"] for item in components)
    )
    return {
        "d100": rolled,
        "unadjusted_total": unadjusted_total,
        "modified_total": modified_total,
        "requirement": mode,
        "success": success,
        "original_success": original_success,
        "components": components,
        "luck_spent": spent,
        "luck_options": options,
        "luck_eligible": bool(options),
        "push_eligible": bool(not pushed and not spent and not original_success),
        "pushed": bool(pushed),
        "failed_pushed_roll": bool(pushed and not success),
        "development_eligible_skills": [
            item["name"]
            for item in components
            if item["development_eligible"] and item["success"]
        ],
    }


def group_luck_candidates(participants: list[dict[str, Any]]) -> dict[str, Any]:
    """Return every participant tied for the scene's lowest current Luck."""

    if not 2 <= len(participants) <= 20:
        raise ValueError("a group Luck roll requires between 2 and 20 participants")
    normalized = []
    seen: set[str] = set()
    for raw in participants:
        actor_id = str(dict(raw).get("actor_id") or "").strip()
        if not actor_id or actor_id in seen:
            raise ValueError("group Luck actor ids must be present and unique")
        seen.add(actor_id)
        luck = int(dict(raw).get("luck"))
        if not 0 <= luck <= 100:
            raise ValueError("group Luck values must be between 0 and 100")
        normalized.append({"actor_id": actor_id, "luck": luck})
    lowest = min(item["luck"] for item in normalized)
    return {
        "lowest_luck": lowest,
        "candidate_actor_ids": [
            item["actor_id"] for item in normalized if item["luck"] == lowest
        ],
    }


def get_success_label(level: int) -> str:
    """Return the stable English label for a success level."""

    try:
        resolved = SuccessLevel(int(level))
    except ValueError:
        return f"Level {level}"
    return SUCCESS_LABELS[resolved]
