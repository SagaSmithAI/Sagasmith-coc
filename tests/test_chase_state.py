from __future__ import annotations

import pytest

from sagasmith_coc.engine.chase_state import (
    advance_chase_turn,
    chase_distance,
    end_chase,
    set_effective_mov,
    start_chase,
    take_chase_action,
)
from sagasmith_coc.engine.checks.chase import calc_chase_actions, resolve_chase_speed_check


def participants() -> list[dict]:
    return [
        {
            "actor_id": "investigator",
            "name": "Investigator",
            "role": "fleeing",
            "effective_mov": 9,
            "dex": 60,
            "position": 2,
        },
        {
            "actor_id": "cultist",
            "name": "Cultist",
            "role": "pursuer",
            "effective_mov": 7,
            "dex": 50,
            "position": 0,
        },
    ]


def test_speed_check_uses_explicit_skill_and_slowest_mov() -> None:
    extreme = resolve_chase_speed_check(5, 50, 8, 7)
    assert extreme["new_mov"] == 9
    assert extreme["actions"] == 3
    failed = resolve_chase_speed_check(90, 50, 8, 7)
    assert failed["new_mov"] == 7
    assert failed["actions"] == 1
    assert calc_chase_actions(9, 7) == 3
    with pytest.raises(ValueError, match="positive"):
        calc_chase_actions(9, 0)


def test_chase_consumes_points_tracks_distance_and_resets_next_round() -> None:
    state = start_chase(
        participants(),
        source="Source-backed pursuit.",
        route=[
            {"id": "street", "index": 0, "title": "Street", "source": "scene:street"},
            {
                "id": "fence",
                "index": 3,
                "title": "Fence",
                "kind": "barrier",
                "source": "scene:fence",
            },
        ],
    )
    assert state["slowest_mov"] == 7
    assert state["participants"]["investigator"]["action_points"] == 3
    assert state["current_actor_id"] == "investigator"
    state = take_chase_action(
        state,
        "investigator",
        action_type="move",
        position_change=2,
        cost=2,
        source="The investigator spends two chase actions.",
    )
    assert chase_distance(state, "investigator", "cultist") == 4
    assert state["participants"]["investigator"]["action_points_remaining"] == 1
    with pytest.raises(ValueError, match="exceeds"):
        take_chase_action(
            state,
            "investigator",
            action_type="move",
            position_change=2,
            cost=2,
            source="Too far.",
        )
    state = advance_chase_turn(state)
    assert state["current_actor_id"] == "cultist"
    assert state["events"][-1]["forfeited_action_points"] == 1
    state = set_effective_mov(state, "cultist", 8, source="Resolved Drive Auto check.")
    state = advance_chase_turn(state)
    assert state["round"] == 2
    assert state["slowest_mov"] == 8
    assert state["participants"]["investigator"]["action_points"] == 2
    assert state["participants"]["cultist"]["action_points"] == 1


def test_chase_requires_both_roles_and_explicit_end_outcome() -> None:
    invalid = participants()
    invalid[1]["role"] = "fleeing"
    with pytest.raises(ValueError, match="pursuer"):
        start_chase(invalid, source="No pursuer.")
    state = start_chase(participants(), source="Source-backed pursuit.")
    ended = end_chase(state, outcome="escaped", source="The fleeing actor reached safety.")
    assert ended["active"] is False
    assert ended["outcome"] == "escaped"


def test_vehicle_chase_preserves_source_bound_vehicle_card() -> None:
    values = participants()
    values[0].update(
        {
            "participant_kind": "vehicle",
            "vehicle": {"source_id": "vehicle.sedan", "name": "Sedan", "build": 5},
        }
    )
    values[1].update(
        {
            "participant_kind": "vehicle",
            "vehicle": {"source_id": "vehicle.truck", "name": "Truck", "build": 6},
        }
    )
    state = start_chase(values, source="Reviewed vehicle chase setup.")

    assert state["participants"]["investigator"]["vehicle"] == {
        "source_id": "vehicle.sedan",
        "name": "Sedan",
        "build": 5,
    }
