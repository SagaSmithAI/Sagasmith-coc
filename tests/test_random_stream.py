from __future__ import annotations

import pytest

from sagasmith_coc.engine.checks.sanity import roll_bout_of_madness
from sagasmith_coc.engine.dice.rolls import roll_d100, roll_dice_expression, roll_stat
from sagasmith_coc.random_stream import (
    CampaignRandomStream,
    initial_random_stream,
    use_random_stream,
    validate_random_stream_state,
)


def _stream(position: int = 0) -> CampaignRandomStream:
    state = {"random_stream": initial_random_stream("campaign-seed")}
    state["random_stream"]["position"] = position
    return CampaignRandomStream.from_campaign_state(
        "campaign-1",
        state,
        operation="test.roll",
        idempotency_key="test-key",
    )


def test_same_seed_and_position_replay_the_same_coc_sequence() -> None:
    first = _stream()
    second = _stream()

    with use_random_stream(first):
        first_results = [
            roll_d100(bonus_dice=2, penalty_dice=1),
            roll_dice_expression("2d6+3"),
            roll_stat("3D6*5"),
            roll_bout_of_madness(),
        ]
    with use_random_stream(second):
        second_results = [
            roll_d100(bonus_dice=2, penalty_dice=1),
            roll_dice_expression("2d6+3"),
            roll_stat("3D6*5"),
            roll_bout_of_madness(),
        ]

    assert first_results == second_results
    assert first.position == second.position == 9
    assert first.receipt() == {
        "algorithm": "sha256-counter-v1",
        "seed_fingerprint": first.seed[:16],
        "position_before": 0,
        "position_after": 9,
        "draw_count": 9,
        "operation": "test.roll",
        "idempotency_key": "test-key",
    }


def test_bonus_and_penalty_dice_cancel_before_random_draws() -> None:
    stream = _stream()
    with use_random_stream(stream):
        result = roll_d100(bonus_dice=2, penalty_dice=2)

    assert len(result["all_tens"]) == 1
    assert stream.draw_count == 2


def test_restoring_position_replays_only_the_suffix() -> None:
    original = _stream()
    with use_random_stream(original):
        roll_dice_expression("3d8")
        checkpoint = original.position
        suffix = roll_dice_expression("4d10")

    restored = _stream(checkpoint)
    with use_random_stream(restored):
        replayed = roll_dice_expression("4d10")

    assert replayed == suffix
    assert restored.position == original.position


def test_rewind_and_state_validation_reject_tampering() -> None:
    stream = _stream()
    with use_random_stream(stream):
        roll_dice_expression("1d20")
        stream.mark_persisted()
        checkpoint = stream.position
        suffix = roll_dice_expression("2d6")
        stream.rewind_unpersisted(checkpoint)
        assert roll_dice_expression("2d6") == suffix

    with pytest.raises(ValueError, match="persisted draws"):
        stream.rewind_unpersisted(checkpoint - 1)
    with pytest.raises(ValueError, match="unsupported fields"):
        validate_random_stream_state(
            {**initial_random_stream("campaign-seed"), "caller_roll": 20}
        )
