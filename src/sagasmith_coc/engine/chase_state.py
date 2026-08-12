"""Deterministic source-backed CoC 7e chase state transitions."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .checks.chase import calc_chase_actions

CHASE_SCHEMA = "sagasmith.coc7e-chase.v1"


def _participant(raw: dict[str, Any], input_order: int) -> dict[str, Any]:
    value = dict(raw)
    actor_id = str(value.get("actor_id") or "").strip()
    name = str(value.get("name") or "").strip()
    role = str(value.get("role") or "").strip()
    if not actor_id or not name or role not in {"pursuer", "fleeing"}:
        raise ValueError("each chase participant requires actor_id, name, and pursuer/fleeing role")
    effective_mov = int(value.get("effective_mov", 0))
    dex = int(value.get("dex", -1))
    position = int(value.get("position", 0))
    if effective_mov < 1:
        raise ValueError("participant effective_mov must be positive")
    if not 0 <= dex <= 100:
        raise ValueError("participant dex must be between 0 and 100")
    return {
        "actor_id": actor_id,
        "name": name,
        "role": role,
        "effective_mov": effective_mov,
        "dex": dex,
        "position": position,
        "input_order": input_order,
        "action_points": 0,
        "action_points_remaining": 0,
        "status": "active",
    }


def _route(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    ids: set[str] = set()
    indexes: set[int] = set()
    for item in raw:
        value = dict(item)
        location_id = str(value.get("id") or "").strip()
        title = str(value.get("title") or "").strip()
        source = str(value.get("source") or "").strip()
        index = int(value.get("index", 0))
        if not location_id or not title or not source:
            raise ValueError("each chase route location requires id, title, and source")
        if location_id in ids or index in indexes:
            raise ValueError("chase route ids and indexes must be unique")
        ids.add(location_id)
        indexes.add(index)
        result.append(
            {
                **value,
                "id": location_id,
                "title": title,
                "source": source,
                "index": index,
                "kind": str(value.get("kind") or "clear"),
            }
        )
    return sorted(result, key=lambda item: item["index"])


def _order(participants: dict[str, dict[str, Any]]) -> list[str]:
    values = [item for item in participants.values() if item.get("status") == "active"]
    values.sort(key=lambda item: (-int(item["dex"]), int(item["input_order"])))
    return [str(item["actor_id"]) for item in values]


def _reset_actions(value: dict[str, Any]) -> None:
    active = [
        int(item["effective_mov"])
        for item in value["participants"].values()
        if item.get("status") == "active"
    ]
    if not active:
        raise ValueError("chase has no active participants")
    slowest_mov = min(active)
    value["slowest_mov"] = slowest_mov
    for participant in value["participants"].values():
        if participant.get("status") != "active":
            participant["action_points"] = 0
            participant["action_points_remaining"] = 0
            continue
        actions = calc_chase_actions(int(participant["effective_mov"]), slowest_mov)
        participant["action_points"] = actions
        participant["action_points_remaining"] = actions


def start_chase(
    participants: list[dict[str, Any]],
    *,
    source: str,
    route: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build one chase from already resolved, source-backed effective MOV values."""

    source_value = " ".join(str(source or "").split()).strip()
    if not source_value:
        raise ValueError("chase source is required")
    if len(participants) < 2:
        raise ValueError("chase requires at least two participants")
    normalized: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(participants):
        item = _participant(raw, index)
        if item["actor_id"] in normalized:
            raise ValueError(f"duplicate chase participant: {item['actor_id']}")
        normalized[item["actor_id"]] = item
    if {item["role"] for item in normalized.values()} != {"pursuer", "fleeing"}:
        raise ValueError("chase requires at least one pursuer and one fleeing participant")
    order = _order(normalized)
    value = {
        "schema": CHASE_SCHEMA,
        "active": True,
        "source": source_value,
        "round": 1,
        "turn_index": 0,
        "current_actor_id": order[0],
        "order": order,
        "participants": normalized,
        "route": _route(list(route or [])),
        "pending_choice": None,
        "events": [],
    }
    _reset_actions(value)
    return value


def chase_distance(state: dict[str, Any], first_id: str, second_id: str) -> int:
    participants = dict(state.get("participants") or {})
    if first_id not in participants:
        raise LookupError(first_id)
    if second_id not in participants:
        raise LookupError(second_id)
    return abs(int(participants[first_id]["position"]) - int(participants[second_id]["position"]))


def take_chase_action(
    state: dict[str, Any],
    actor_id: str,
    *,
    action_type: str,
    cost: int = 1,
    position_change: int = 0,
    source: str,
) -> dict[str, Any]:
    """Consume explicit action points and apply an explicit track-position change."""

    value = deepcopy(state)
    if not value.get("active"):
        raise ValueError("chase is not active")
    if value.get("pending_choice") is not None:
        raise ValueError("resolve the pending chase choice before taking another action")
    if actor_id != value.get("current_actor_id"):
        raise ValueError("only the current chase actor may act")
    source_value = " ".join(str(source or "").split()).strip()
    if not source_value:
        raise ValueError("chase action source is required")
    if isinstance(cost, bool) or int(cost) < 1:
        raise ValueError("chase action cost must be a positive integer")
    participant = value["participants"][actor_id]
    remaining = int(participant["action_points_remaining"])
    if cost > remaining:
        raise ValueError("chase action exceeds the actor's remaining action points")
    participant["action_points_remaining"] = remaining - int(cost)
    participant["position"] = int(participant["position"]) + int(position_change)
    value["events"].append(
        {
            "type": "chase_action",
            "actor_id": actor_id,
            "action_type": str(action_type or "other"),
            "cost": int(cost),
            "position_change": int(position_change),
            "position": participant["position"],
            "source": source_value,
        }
    )
    return value


def set_effective_mov(
    state: dict[str, Any], actor_id: str, effective_mov: int, *, source: str
) -> dict[str, Any]:
    """Record a speed-check result; new action points take effect next round."""

    value = deepcopy(state)
    if actor_id not in value.get("participants", {}):
        raise LookupError(actor_id)
    if int(effective_mov) < 1:
        raise ValueError("effective_mov must be positive")
    source_value = " ".join(str(source or "").split()).strip()
    if not source_value:
        raise ValueError("effective MOV source is required")
    value["participants"][actor_id]["effective_mov"] = int(effective_mov)
    value["events"].append(
        {
            "type": "effective_mov_changed",
            "actor_id": actor_id,
            "effective_mov": int(effective_mov),
            "source": source_value,
        }
    )
    return value


def advance_chase_turn(state: dict[str, Any]) -> dict[str, Any]:
    """Pass any remaining actions, advance DEX order, and reset points each round."""

    value = deepcopy(state)
    if not value.get("active"):
        raise ValueError("chase is not active")
    if value.get("pending_choice") is not None:
        raise ValueError("resolve the pending chase choice before ending the turn")
    order = list(value.get("order") or [])
    if not order:
        raise ValueError("chase has no active turn order")
    current_id = str(value["current_actor_id"])
    current = value["participants"][current_id]
    forfeited = int(current.get("action_points_remaining", 0))
    current["action_points_remaining"] = 0
    next_index = int(value["turn_index"]) + 1
    if next_index >= len(order):
        value["round"] = int(value["round"]) + 1
        value["order"] = _order(value["participants"])
        order = value["order"]
        _reset_actions(value)
        next_index = 0
    value["turn_index"] = next_index
    value["current_actor_id"] = order[next_index]
    value["events"].append(
        {
            "type": "chase_turn_ended",
            "actor_id": current_id,
            "forfeited_action_points": forfeited,
            "next_actor_id": value["current_actor_id"],
            "round": value["round"],
        }
    )
    return value


def end_chase(state: dict[str, Any], *, outcome: str, source: str) -> dict[str, Any]:
    """Close a chase using an explicit source-backed outcome."""

    value = deepcopy(state)
    if not value.get("active"):
        raise ValueError("chase is not active")
    if value.get("pending_choice") is not None:
        raise ValueError("resolve or abort the pending chase choice before ending")
    outcome_value = str(outcome or "").strip()
    source_value = " ".join(str(source or "").split()).strip()
    if not outcome_value or not source_value:
        raise ValueError("chase outcome and source are required")
    value["active"] = False
    value["outcome"] = outcome_value
    value["ended_source"] = source_value
    value["events"].append(
        {"type": "chase_ended", "outcome": outcome_value, "source": source_value}
    )
    return value
