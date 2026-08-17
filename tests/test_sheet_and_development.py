import pytest

from sagasmith_coc.engine.development import development_query, settle_development
from sagasmith_coc.engine.sheet import (
    combat_weapon,
    investigation_combined_traits,
    investigation_trait,
)
from sagasmith_coc.random_stream import (
    CampaignRandomStream,
    initial_random_stream,
    use_random_stream,
)
from sagasmith_coc.system import validate_investigator_sheet


def investigator_sheet() -> dict:
    return validate_investigator_sheet(
        {
            "characteristics": {"pow": 70, "dex": 60},
            "skills": {"Spot Hidden": 45, "Cthulhu Mythos": 12, "Fighting": 55},
            "weapons": [
                {
                    "name": "Knife",
                    "skill": {"name": "Fighting"},
                    "damage": "1D4+DB",
                    "properties": {"impl": True},
                }
            ],
            "development": {
                "checked_skills": ["spot hidden", "Cthulhu Mythos"],
                "history": [],
            },
        }
    )


def test_canonical_sheet_queries_are_case_insensitive_and_exact() -> None:
    sheet = investigator_sheet()
    assert investigation_trait(sheet, "skill", "SPOT HIDDEN") == (
        "skill",
        "SPOT HIDDEN",
        45,
    )
    assert investigation_trait(sheet, "luck", "Luck") == ("luck", "Luck", 50)
    assert investigation_combined_traits(
        sheet,
        [
            {"kind": "characteristic", "name": "DEX"},
            {"kind": "skill", "name": "Spot Hidden", "difficulty": "hard"},
        ],
    ) == [
        {"kind": "characteristic", "name": "DEX", "threshold": 60, "difficulty": "regular"},
        {"kind": "skill", "name": "Spot Hidden", "threshold": 45, "difficulty": "hard"},
    ]
    weapon = combat_weapon(sheet, "knife")
    assert weapon["skill_name"] == "Fighting"
    assert weapon["impaling"] is True
    assert weapon["ranged"] is False


def test_development_query_reports_ineligible_mythos() -> None:
    assert development_query(investigator_sheet()) == [
        {
            "skill_name": "Spot Hidden",
            "current_value": 45,
            "eligible": True,
            "reason": None,
        },
        {
            "skill_name": "Cthulhu Mythos",
            "current_value": 12,
            "eligible": False,
            "reason": "Cthulhu Mythos does not use ordinary development checks",
        },
    ]


def test_settle_development_uses_caller_random_stream_and_clears_marks() -> None:
    sheet = investigator_sheet()
    state = {"random_stream": initial_random_stream("development")}
    stream = CampaignRandomStream.from_campaign_state(
        "campaign",
        state,
        operation="development_settle",
        idempotency_key="settle-1",
    )
    with use_random_stream(stream):
        next_sheet, receipt = settle_development(sheet, source="End of chapter")
    assert next_sheet["development"]["checked_skills"] == []
    assert receipt["source"] == "End of chapter"
    assert receipt["results"][1]["eligible"] is False
    assert stream.draw_count in {1, 2, 4}
    assert next_sheet["development"]["history"][-1] == receipt


def test_development_rejects_duplicate_or_missing_marks() -> None:
    sheet = investigator_sheet()
    sheet["development"]["checked_skills"] = ["Spot Hidden", "spot hidden"]
    with pytest.raises(ValueError, match="unique"):
        development_query(sheet)
    sheet["development"]["checked_skills"] = ["Not On Sheet"]
    with pytest.raises(ValueError, match="missing"):
        development_query(sheet)
