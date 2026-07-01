from sagasmith_coc.engine.checks.combat import resolve_melee_attack
from sagasmith_coc.engine.checks.sanity import calculate_sanity_max, resolve_sanity_loss
from sagasmith_coc.engine.checks.skill import (
    SuccessLevel,
    resolve_opposed_check,
    resolve_skill_check,
)
from sagasmith_coc.engine.dice.rolls import roll_d100, roll_dice_expression
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
