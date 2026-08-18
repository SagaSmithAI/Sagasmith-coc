import pytest

from sagasmith_coc.engine.health import apply_damage, apply_healing
from sagasmith_coc.system import validate_investigator_sheet


def sheet() -> dict:
    return validate_investigator_sheet(
        {"characteristics": {"con": 60, "siz": 60}, "max_hp": 12, "hp": 12}
    )


def test_major_wound_requires_con_and_zero_hp_with_major_wound_is_dying() -> None:
    pending = apply_damage(sheet(), 6)
    assert pending["requires_con_check"] is True
    assert pending["conditions"]["major_wound"] is True

    failed = apply_damage(sheet(), 6, con_check_success=False)
    assert failed["conditions"]["unconscious"] is True
    dying = apply_damage(failed["sheet"], 6, con_check_success=True)
    assert dying["new_hp"] == 0
    assert dying["conditions"]["dying"] is True


def test_one_blow_equal_to_maximum_hp_kills_instantly() -> None:
    result = apply_damage(sheet(), 12)
    assert result["conditions"]["dead"] is True
    assert result["conditions"]["dying"] is False
    assert result["requires_con_check"] is False


def test_separate_small_hits_do_not_create_a_major_wound() -> None:
    first = apply_damage(sheet(), 4)
    second = apply_damage(first["sheet"], 4)
    assert second["new_hp"] == 4
    assert second["conditions"]["major_wound"] is False


def test_first_aid_stabilizes_and_half_hp_clears_major_wound() -> None:
    damaged = apply_damage(sheet(), 7, con_check_success=True)
    dying = apply_damage(damaged["sheet"], 5, con_check_success=True)
    stabilized = apply_healing(dying["sheet"], 1, source="first_aid")
    assert stabilized["conditions"]["dying"] is False
    assert stabilized["new_hp"] == 1
    healed = apply_healing(stabilized["sheet"], 5, source="medicine")
    assert healed["new_hp"] == 6
    assert healed["conditions"]["major_wound"] is False


def test_dead_actor_cannot_be_healed() -> None:
    dead = apply_damage(sheet(), 12)
    with pytest.raises(ValueError, match="dead actor"):
        apply_healing(dead["sheet"], 1, source="first_aid")
