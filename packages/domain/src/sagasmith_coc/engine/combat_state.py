"""Deterministic CoC 7e combat order and spatial-state transitions."""

from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

COMBAT_SCHEMA = "sagasmith.coc7e-combat.v1"


def _participant(raw: dict[str, Any], *, positioning_mode: str, input_order: int) -> dict[str, Any]:
    value = dict(raw)
    actor_id = str(value.get("actor_id") or "").strip()
    name = str(value.get("name") or "").strip()
    side = str(value.get("side") or "").strip()
    if not actor_id or not name or not side:
        raise ValueError("each combat participant requires actor_id, name, and side")
    dex = int(value.get("dex", -1))
    if not 0 <= dex <= 100:
        raise ValueError("participant dex must be between 0 and 100")
    attacks_per_round = int(value.get("attacks_per_round", 1))
    if attacks_per_round < 1:
        raise ValueError("attacks_per_round must be positive")
    ready_firearm = bool(value.get("ready_firearm", False))
    position = value.get("position")
    if positioning_mode == "grid":
        if (
            not isinstance(position, list)
            or len(position) != 2
            or any(
                isinstance(item, bool) or not isinstance(item, (int, float)) for item in position
            )
        ):
            raise ValueError("grid combat participants require a numeric [x, y] position")
        normalized_position: list[float] | None = [float(position[0]), float(position[1])]
    else:
        if position is not None:
            raise ValueError("agent positioning mode must not use synthetic coordinates")
        normalized_position = None
    return {
        "actor_id": actor_id,
        "name": name,
        "side": side,
        "dex": dex,
        "ready_firearm": ready_firearm,
        "initiative_score": dex + (50 if ready_firearm else 0),
        "initiative_tiebreak": input_order,
        "attacks_per_round": attacks_per_round,
        "attacks_taken_this_turn": 0,
        "defenses_this_round": 0,
        "forfeit_next_action": bool(value.get("forfeit_next_action", False)),
        "position": normalized_position,
        "available_from_round": int(value.get("available_from_round", 1)),
    }


def _ordered_ids(participants: dict[str, dict[str, Any]], round_number: int) -> list[str]:
    ready = [
        item
        for item in participants.values()
        if int(item.get("available_from_round", 1)) <= round_number
    ]
    ready.sort(key=lambda item: (-int(item["initiative_score"]), int(item["initiative_tiebreak"])))
    return [str(item["actor_id"]) for item in ready]


def start_combat(
    participants: list[dict[str, Any]],
    *,
    positioning_mode: str,
    source: str,
    grid_metric: str = "chebyshev",
    grid_unit_feet: float = 5.0,
) -> dict[str, Any]:
    """Build an authoritative encounter without reading or writing persistence."""

    if positioning_mode not in {"grid", "agent"}:
        raise ValueError("positioning_mode must be grid or agent")
    if grid_metric not in {"chebyshev", "euclidean"}:
        raise ValueError("grid_metric must be chebyshev or euclidean")
    if isinstance(grid_unit_feet, bool) or float(grid_unit_feet) <= 0:
        raise ValueError("grid_unit_feet must be positive")
    source_value = " ".join(str(source or "").split()).strip()
    if not source_value:
        raise ValueError("combat source is required")
    if len(participants) < 2:
        raise ValueError("combat requires at least two participants")
    normalized: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(participants):
        item = _participant(raw, positioning_mode=positioning_mode, input_order=index)
        if item["actor_id"] in normalized:
            raise ValueError(f"duplicate combat participant: {item['actor_id']}")
        normalized[item["actor_id"]] = item
    if len({item["side"] for item in normalized.values()}) < 2:
        raise ValueError("combat requires participants from at least two sides")
    order = _ordered_ids(normalized, 1)
    return {
        "schema": COMBAT_SCHEMA,
        "active": True,
        "source": source_value,
        "positioning_mode": positioning_mode,
        "grid_metric": grid_metric if positioning_mode == "grid" else None,
        "grid_unit_feet": float(grid_unit_feet) if positioning_mode == "grid" else None,
        "round": 1,
        "turn_index": 0,
        "current_actor_id": order[0],
        "order": order,
        "participants": normalized,
        "pending_choice": None,
        "events": [],
    }


def join_combat(state: dict[str, Any], participant: dict[str, Any]) -> dict[str, Any]:
    """Queue a new combatant for the next round without changing the current order."""

    value = deepcopy(state)
    if not value.get("active"):
        raise ValueError("combat is not active")
    if value.get("pending_choice") is not None:
        raise ValueError("resolve the pending combat choice before joining a combatant")
    normalized = _participant(
        {**dict(participant), "available_from_round": int(value["round"]) + 1},
        positioning_mode=str(value["positioning_mode"]),
        input_order=len(value["participants"]),
    )
    actor_id = str(normalized["actor_id"])
    if actor_id in value["participants"]:
        raise ValueError(f"combat participant already exists: {actor_id}")
    value["participants"][actor_id] = normalized
    value["events"].append(
        {"type": "join_queued", "actor_id": actor_id, "available_from_round": value["round"] + 1}
    )
    return value


def record_attack(state: dict[str, Any], actor_id: str) -> dict[str, Any]:
    """Consume one of the current actor's attacks for this turn."""

    value = deepcopy(state)
    if actor_id != value.get("current_actor_id"):
        raise ValueError("only the current combat actor may attack")
    participant = value["participants"][actor_id]
    taken = int(participant.get("attacks_taken_this_turn", 0))
    if taken >= int(participant.get("attacks_per_round", 1)):
        raise ValueError("the current actor has no attacks remaining this turn")
    participant["attacks_taken_this_turn"] = taken + 1
    return value


def record_defense(
    state: dict[str, Any], actor_id: str, *, dive_for_cover: bool = False
) -> dict[str, Any]:
    """Record a response so later melee attackers can receive outnumbering dice."""

    value = deepcopy(state)
    participant = value["participants"].get(actor_id)
    if participant is None:
        raise LookupError(actor_id)
    participant["defenses_this_round"] = int(participant.get("defenses_this_round", 0)) + 1
    if dive_for_cover:
        participant["forfeit_next_action"] = True
    return value


def outnumbering_bonus_dice(
    state: dict[str, Any], defender_id: str, *, ranged: bool = False
) -> int:
    """Return the standard one bonus die after a prior melee response this round."""

    participant = dict(state.get("participants", {})).get(defender_id)
    if participant is None:
        raise LookupError(defender_id)
    if ranged:
        return 0
    return 1 if int(participant.get("defenses_this_round", 0)) > 0 else 0


def combat_distance_feet(state: dict[str, Any], first_id: str, second_id: str) -> float:
    """Return engine-owned grid distance; Agent mode deliberately has no answer."""

    if state.get("positioning_mode") != "grid":
        raise ValueError("agent positioning mode requires an explicit spatial ruling")
    participants = dict(state.get("participants") or {})
    first = participants.get(first_id)
    second = participants.get(second_id)
    if first is None:
        raise LookupError(first_id)
    if second is None:
        raise LookupError(second_id)
    first_position = first["position"]
    second_position = second["position"]
    dx = abs(float(first_position[0]) - float(second_position[0]))
    dy = abs(float(first_position[1]) - float(second_position[1]))
    distance = max(dx, dy) if state["grid_metric"] == "chebyshev" else math.hypot(dx, dy)
    return distance * float(state["grid_unit_feet"])


def advance_turn(state: dict[str, Any]) -> dict[str, Any]:
    """Advance DEX order, reset round counters, and consume dive-for-cover forfeits."""

    value = deepcopy(state)
    if not value.get("active"):
        raise ValueError("combat is not active")
    if value.get("pending_choice") is not None:
        raise ValueError("resolve the pending combat choice before ending the turn")
    order = list(value.get("order") or [])
    if not order:
        raise ValueError("combat has no active order")
    skipped: list[str] = []
    for _ in range(len(value["participants"]) + 1):
        next_index = int(value["turn_index"]) + 1
        if next_index >= len(order):
            value["round"] = int(value["round"]) + 1
            for participant in value["participants"].values():
                participant["defenses_this_round"] = 0
                participant["attacks_taken_this_turn"] = 0
            order = _ordered_ids(value["participants"], int(value["round"]))
            value["order"] = order
            next_index = 0
        value["turn_index"] = next_index
        actor_id = order[next_index]
        participant = value["participants"][actor_id]
        participant["attacks_taken_this_turn"] = 0
        if participant.get("forfeit_next_action"):
            participant["forfeit_next_action"] = False
            skipped.append(actor_id)
            value["events"].append(
                {"type": "turn_forfeited", "actor_id": actor_id, "round": value["round"]}
            )
            continue
        value["current_actor_id"] = actor_id
        value["events"].append(
            {"type": "turn_started", "actor_id": actor_id, "round": value["round"]}
        )
        value["last_skipped_actor_ids"] = skipped
        return value
    raise ValueError("combat cannot advance because every available action is forfeited")


def move_combatant(
    state: dict[str, Any],
    actor_id: str,
    *,
    destination: list[float] | None = None,
    movement_budget: float | None = None,
    agent_ruling: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Move in authoritative grid mode or record an explicit Agent spatial ruling."""

    value = deepcopy(state)
    participant = value["participants"].get(actor_id)
    if participant is None:
        raise LookupError(actor_id)
    if value["positioning_mode"] == "agent":
        if destination is not None:
            raise ValueError("agent positioning mode must not use synthetic coordinates")
        ruling = dict(agent_ruling or {})
        if (
            not isinstance(ruling.get("allowed"), bool)
            or not str(ruling.get("source") or "").strip()
        ):
            raise ValueError("agent movement requires explicit allowed and source facts")
        if not ruling["allowed"]:
            raise ValueError("the explicit Agent spatial ruling does not allow this movement")
        event = {"type": "agent_move", "actor_id": actor_id, "ruling": ruling}
    else:
        if (
            not isinstance(destination, list)
            or len(destination) != 2
            or any(
                isinstance(item, bool) or not isinstance(item, (int, float)) for item in destination
            )
        ):
            raise ValueError("grid movement requires a numeric destination [x, y]")
        if movement_budget is None or float(movement_budget) < 0:
            raise ValueError("grid movement requires a non-negative movement_budget")
        origin = participant["position"]
        dx = abs(float(destination[0]) - float(origin[0]))
        dy = abs(float(destination[1]) - float(origin[1]))
        distance = max(dx, dy) if value["grid_metric"] == "chebyshev" else math.hypot(dx, dy)
        if distance > float(movement_budget):
            raise ValueError("grid movement exceeds the explicit movement budget")
        participant["position"] = [float(destination[0]), float(destination[1])]
        event = {
            "type": "grid_move",
            "actor_id": actor_id,
            "origin": origin,
            "destination": participant["position"],
            "distance": distance,
            "distance_feet": distance * float(value["grid_unit_feet"]),
            "movement_budget": float(movement_budget),
        }
    value["events"].append(event)
    return value
