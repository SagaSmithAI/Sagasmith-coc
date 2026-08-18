import pytest

from sagasmith_coc.engine.investigation import (
    resolve_investigation_check,
    spend_luck_on_investigation,
)
from sagasmith_coc.random_stream import CampaignRandomStream, use_random_stream
from sagasmith_coc.system import validate_investigator_sheet


def investigator_sheet() -> dict:
    return validate_investigator_sheet(
        {
            "characteristics": {"dex": 60},
            "skills": {"Spot Hidden": 45, "Listen": 55},
            "luck": 50,
        }
    )


def test_single_check_uses_caller_stream_and_canonical_sheet_value() -> None:
    stream = CampaignRandomStream.from_campaign_state(
        "campaign",
        {},
        operation="investigation",
        idempotency_key="open-1",
    )
    with use_random_stream(stream):
        result = resolve_investigation_check(
            investigator_sheet(),
            {"trait_name": "SPOT HIDDEN", "difficulty": "hard"},
            investigator_name="Harvey",
        )
    assert result["check_kind"] == "single"
    assert result["threshold"] == 45
    assert result["roll"]["total"] == result["outcome"]["d100"]
    assert stream.draw_count == 2


def test_combined_push_preserves_explicit_requirement() -> None:
    stream = CampaignRandomStream.from_campaign_state(
        "campaign",
        {},
        operation="investigation",
        idempotency_key="push-1",
    )
    with use_random_stream(stream):
        result = resolve_investigation_check(
            investigator_sheet(),
            {
                "traits": [
                    {"kind": "skill", "name": "Spot Hidden"},
                    {"kind": "skill", "name": "Listen"},
                ],
                "requirement": "all",
            },
            pushed=True,
        )
    assert result["check_kind"] == "combined"
    assert result["requirement"] == "all"
    assert result["outcome"]["pushed"] is True


def test_luck_purchase_updates_sheet_and_reuses_recorded_roll() -> None:
    check = {
        "id": "check-1",
        "source": "Library ledger",
        "check_kind": "single",
        "trait_kind": "skill",
        "trait_name": "Spot Hidden",
        "threshold": 45,
        "difficulty": "regular",
        "bonus_dice": 0,
        "penalty_dice": 0,
        "roll": {"total": 50},
    }
    result = spend_luck_on_investigation(investigator_sheet(), check, 5)
    assert result["sheet"]["luck"] == 45
    assert result["sheet"]["luck_events"][-1]["check_id"] == "check-1"
    assert result["outcome"]["success"] is True
    with pytest.raises(ValueError, match="exactly"):
        spend_luck_on_investigation(investigator_sheet(), check, 4)
