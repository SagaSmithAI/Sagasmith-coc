from __future__ import annotations

import pytest

from sagasmith_coc.engine.combat_state import (
    advance_turn,
    combat_distance_feet,
    join_combat,
    move_combatant,
    outnumbering_bonus_dice,
    record_attack,
    record_defense,
    start_combat,
)


def participants(*, mode: str = "grid") -> list[dict]:
    values = [
        {
            "actor_id": "investigator",
            "name": "Investigator",
            "side": "investigators",
            "dex": 60,
            "position": [0, 0] if mode == "grid" else None,
        },
        {
            "actor_id": "cultist",
            "name": "Cultist",
            "side": "opposition",
            "dex": 40,
            "ready_firearm": True,
            "position": [3, 0] if mode == "grid" else None,
        },
    ]
    if mode == "agent":
        for value in values:
            value.pop("position")
    return values


def test_combat_order_uses_ready_firearm_and_stable_input_ties() -> None:
    state = start_combat(
        participants(),
        positioning_mode="grid",
        source="Source-backed confrontation.",
    )
    assert state["order"] == ["cultist", "investigator"]
    assert state["current_actor_id"] == "cultist"
    assert state["participants"]["cultist"]["initiative_score"] == 90


def test_join_outnumbering_attack_limits_and_round_transition() -> None:
    state = start_combat(
        participants(),
        positioning_mode="grid",
        source="Source-backed confrontation.",
    )
    state = record_attack(state, "cultist")
    with pytest.raises(ValueError, match="no attacks remaining"):
        record_attack(state, "cultist")
    state = record_defense(state, "investigator")
    assert outnumbering_bonus_dice(state, "investigator") == 1
    assert outnumbering_bonus_dice(state, "investigator", ranged=True) == 0
    state = join_combat(
        state,
        {
            "actor_id": "ally",
            "name": "Ally",
            "side": "investigators",
            "dex": 50,
            "position": [1, 0],
        },
    )
    state = advance_turn(state)
    assert state["current_actor_id"] == "investigator"
    state = advance_turn(state)
    assert state["round"] == 2
    assert "ally" in state["order"]
    assert state["participants"]["investigator"]["defenses_this_round"] == 0


def test_dive_for_cover_forfeits_the_next_action() -> None:
    state = start_combat(
        participants(),
        positioning_mode="grid",
        source="Source-backed confrontation.",
    )
    state = record_defense(state, "investigator", dive_for_cover=True)
    state = advance_turn(state)
    assert state["round"] == 2
    assert state["current_actor_id"] == "cultist"
    assert state["last_skipped_actor_ids"] == ["investigator"]
    assert state["participants"]["investigator"]["forfeit_next_action"] is False


def test_grid_and_agent_movement_keep_their_spatial_authorities_separate() -> None:
    grid = start_combat(
        participants(),
        positioning_mode="grid",
        source="Source-backed confrontation.",
    )
    grid = move_combatant(
        grid,
        "investigator",
        destination=[2, 1],
        movement_budget=2,
    )
    assert grid["participants"]["investigator"]["position"] == [2.0, 1.0]
    assert combat_distance_feet(grid, "investigator", "cultist") == 5.0
    with pytest.raises(ValueError, match="exceeds"):
        move_combatant(grid, "investigator", destination=[9, 9], movement_budget=2)

    agent = start_combat(
        participants(mode="agent"),
        positioning_mode="agent",
        source="Source-backed confrontation.",
    )
    agent = move_combatant(
        agent,
        "investigator",
        agent_ruling={"allowed": True, "source": "The Keeper ruled the route clear."},
    )
    assert agent["participants"]["investigator"]["position"] is None
    with pytest.raises(ValueError, match="synthetic coordinates"):
        move_combatant(agent, "investigator", destination=[1, 1])
