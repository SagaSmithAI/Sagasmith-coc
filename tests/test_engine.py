import pytest

from sagasmith_coc.engine.checks.combat import resolve_melee_attack
from sagasmith_coc.engine.checks.sanity import calculate_sanity_max, resolve_sanity_loss
from sagasmith_coc.engine.checks.skill import (
    SuccessLevel,
    group_luck_candidates,
    luck_spend_options,
    resolve_combined_check,
    resolve_opposed_check,
    resolve_skill_check,
)
from sagasmith_coc.engine.development import (
    resolve_luck_development,
    resolve_skill_development,
)
from sagasmith_coc.engine.dice.rolls import roll_d100, roll_dice_expression
from sagasmith_coc.random_stream import (
    CampaignRandomStream,
    initial_random_stream,
    use_random_stream,
)
from sagasmith_coc.system import validate_investigator_sheet


def test_investigator_and_core_mechanics() -> None:
    sheet = validate_investigator_sheet({"characteristics": {"pow": 70, "con": 50, "siz": 60}})
    assert sheet["san"] == 70
    assert sheet["hp"] == 11
    assert sheet["max_hp"] == 11
    assert sheet["damage_bonus"] == "0"
    assert sheet["build"] == 0
    assert sheet["san_max"] == 99
    assert sheet["development"]["personal"] == 100
    assert calculate_sanity_max(12) == 87

    result = resolve_skill_check(20, 60, difficulty="hard")
    assert result["success"] is True
    assert result["success_level"] >= SuccessLevel.HARD

    sanity = resolve_sanity_loss(70, 99, 5)
    assert sanity["new_san"] == 65
    assert sanity["requires_int_check"] is True
    assert sanity["temp_insanity"] is False
    insanity = resolve_sanity_loss(70, 99, 5, int_check_success=True)
    assert insanity["temp_insanity"] is True

    die = roll_d100(bonus_dice=1)
    assert 1 <= die["total"] <= 100
    damage = roll_dice_expression("1D6+2")
    assert len(damage["rolls"]) == 1
    assert damage["total"] == damage["rolls"][0] + 2


def test_opposed_and_melee_defense_are_fully_resolved() -> None:
    opposed = resolve_opposed_check(35, 70, 20, 40)
    assert opposed["winner"] == "attacker"

    dodged = resolve_melee_attack(
        30,
        60,
        weapon_damage="1D6",
        target_dodge=50,
        target_roll=20,
        defense="dodge",
    )
    assert dodged["hit"] is False
    assert dodged["target_success_level"] >= SuccessLevel.HARD


def test_luck_and_push_options_follow_the_source_restrictions() -> None:
    assert luck_spend_options(50, 40) == {
        "regular": 10,
        "hard": 30,
        "extreme": 42,
    }
    adjusted = resolve_skill_check(50, 40, luck_spent=10)
    assert adjusted["success"] is True
    assert adjusted["success_level"] == SuccessLevel.REGULAR
    assert adjusted["luck_spent"] == 10
    assert adjusted["push_eligible"] is False

    failed = resolve_skill_check(70, 40)
    assert failed["push_eligible"] is True
    pushed = resolve_skill_check(70, 40, pushed=True)
    assert pushed["failed_pushed_roll"] is True
    assert pushed["luck_options"] == {}
    with pytest.raises(ValueError, match="pushed"):
        resolve_skill_check(50, 40, pushed=True, luck_spent=10)
    with pytest.raises(ValueError, match="fumble"):
        resolve_skill_check(100, 40, luck_spent=60)
    with pytest.raises(ValueError, match="Luck cannot adjust a luck roll"):
        resolve_skill_check(50, 40, luck_spent=10, roll_kind="luck")
    assert resolve_skill_check(100, 100)["is_fumble"] is True


def test_equal_opposed_skills_fall_back_to_the_lower_roll() -> None:
    result = resolve_opposed_check(30, 60, 20, 60)
    assert result["winner"] == "defender"


def test_skill_development_rolls_over_then_clears_at_the_authoritative_caller() -> None:
    unchanged = resolve_skill_development(45, improvement_roll=43)
    assert unchanged["improved"] is False
    assert unchanged["gain_roll"] is None

    improved = resolve_skill_development(45, improvement_roll=73, gain_roll=8)
    assert improved["new_value"] == 53
    assert improved["mastered"] is False

    mastered = resolve_skill_development(
        89,
        improvement_roll=97,
        gain_roll=4,
        mastery_san_rolls=(3, 5),
    )
    assert mastered["new_value"] == 93
    assert mastered["mastered"] is True
    assert mastered["san_recovery"] == 8

    already_mastered = resolve_skill_development(91, improvement_roll=99, gain_roll=4)
    assert already_mastered["mastered"] is False
    assert already_mastered["san_recovery"] == 0


def test_optional_luck_development_is_explicit_and_bounded() -> None:
    result = resolve_luck_development(
        80,
        improvement_roll=91,
        gain_rolls=(8, 7),
    )
    assert result["gain"] == 15
    assert result["new_value"] == 95
    with pytest.raises(ValueError, match="gain rolls"):
        resolve_luck_development(80, improvement_roll=20, gain_rolls=(1, 1))


def test_combined_checks_use_one_roll_and_keeper_declared_requirement() -> None:
    traits = [
        {"kind": "characteristic", "name": "DEX", "threshold": 60},
        {"kind": "skill", "name": "Climb", "threshold": 40},
    ]
    any_result = resolve_combined_check(50, traits, requirement="any")
    assert any_result["success"] is True
    assert [item["success"] for item in any_result["components"]] == [True, False]
    assert any_result["development_eligible_skills"] == []

    all_result = resolve_combined_check(50, traits, requirement="all")
    assert all_result["success"] is False
    assert all_result["luck_options"] == {"meet_requirement": 10}
    bought = resolve_combined_check(50, traits, requirement="all", luck_spent=10)
    assert bought["success"] is True
    assert bought["modified_total"] == 40
    assert bought["development_eligible_skills"] == ["Climb"]
    with pytest.raises(ValueError, match="exactly purchase"):
        resolve_combined_check(50, traits, requirement="all", luck_spent=9)


def test_group_luck_uses_every_lowest_luck_actor_as_a_tie_candidate() -> None:
    result = group_luck_candidates(
        [
            {"actor_id": "a", "luck": 50},
            {"actor_id": "b", "luck": 20},
            {"actor_id": "c", "luck": 20},
        ]
    )
    assert result == {"lowest_luck": 20, "candidate_actor_ids": ["b", "c"]}


def test_fight_back_requires_a_strictly_better_success_and_can_deal_damage() -> None:
    tied = resolve_melee_attack(
        30,
        60,
        weapon_damage="1D3",
        target_fighting=60,
        target_roll=30,
        defense="fight-back",
        target_weapon_damage="1D3",
    )
    assert tied["winner"] is None
    assert tied["damage"] is None
    assert tied["counterattack"] is None

    countered = resolve_melee_attack(
        40,
        60,
        weapon_damage="1D3",
        target_fighting=60,
        target_roll=20,
        defense="fight-back",
        target_weapon_damage="1",
    )
    assert countered["winner"] == "defender"
    assert countered["hit"] is False
    assert countered["counterattack"]["total"] == 1


def test_extreme_damage_maximizes_weapon_but_rolls_db_and_impaling_extra() -> None:
    state = {"random_stream": initial_random_stream("extreme-damage")}
    stream = CampaignRandomStream.from_campaign_state(
        "campaign",
        state,
        operation="test.extreme",
        idempotency_key="extreme",
    )
    with use_random_stream(stream):
        ordinary = resolve_melee_attack(
            1,
            60,
            weapon_damage="1D6",
            damage_bonus="1D4",
        )
    assert ordinary["damage"]["weapon_total"] == 6
    assert 1 <= ordinary["damage"]["db_total"] <= 4
    assert stream.draw_count == 1

    impaling_stream = CampaignRandomStream.from_campaign_state(
        "campaign",
        state,
        operation="test.impaling",
        idempotency_key="impaling",
    )
    with use_random_stream(impaling_stream):
        impaling = resolve_melee_attack(
            1,
            60,
            weapon_damage="1D6",
            damage_bonus="1D4",
            impaling=True,
        )
    assert 7 <= impaling["damage"]["weapon_total"] <= 12
    assert impaling_stream.draw_count == 2
