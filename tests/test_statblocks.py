import pytest

from sagasmith_coc.statblocks import coc7e_statblock_readiness, validate_coc7e_statblock


def test_coc_statblock_preserves_partial_source_facts_and_reports_readiness() -> None:
    value = validate_coc7e_statblock(
        {
            "schema_version": 1,
            "actor_type": "npc",
            "name": "The Watchman",
            "characteristics": {"dex": 55},
            "skills": {"Spot Hidden": 45},
            "notes": ["Only social and perception statistics are printed."],
        }
    )

    assert value["characteristics"] == {"dex": 55}
    assert "hit_points" not in value
    assert coc7e_statblock_readiness(value)["missing_for_combat"] == [
        "characteristics.str",
        "characteristics.con",
        "characteristics.siz",
        "characteristics.pow",
        "hit_points",
        "move",
        "attacks",
    ]


def test_combat_ready_coc_statblock_requires_mechanical_fields() -> None:
    with pytest.raises(ValueError, match="combat-ready.*hit_points, attacks"):
        validate_coc7e_statblock(
            {
                "actor_type": "creature",
                "name": "Unfinished Thing",
                "characteristics": {"dex": 80},
                "combat_ready": True,
            }
        )


def test_coc_statblock_normalizes_a_complete_creature() -> None:
    value = validate_coc7e_statblock(
        {
            "actor_type": "creature",
            "name": "Deep One",
            "characteristics": {
                "str": 80,
                "con": 70,
                "siz": 65,
                "dex": 50,
                "pow": 50,
            },
            "hit_points": {"current": 13, "maximum": 13},
            "move": 8,
            "build": 1,
            "damage_bonus": "+1D4",
            "skills": {"Fighting (Brawl)": 45},
            "attacks": [
                {
                    "name": "Claw",
                    "skill": 45,
                    "damage": "1D6+DB",
                    "attacks_per_round": 1,
                }
            ],
            "sanity_loss": "0/1D6",
            "combat_ready": True,
        }
    )

    assert coc7e_statblock_readiness(value)["combat_ready"] is True
    assert value["attacks"][0]["damage"] == "1D6+DB"
