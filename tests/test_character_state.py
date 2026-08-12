import pytest

from sagasmith_coc.engine.character_state import (
    change_inventory,
    change_money,
    settle_source_study,
)
from sagasmith_coc.system import validate_investigator_sheet


def test_inventory_lifecycle_preserves_stable_identity_and_quantity() -> None:
    sheet = validate_investigator_sheet({"inventory": []})
    sheet, added = change_inventory(
        sheet,
        action="add",
        item={"id": "item.lantern", "name": "Lantern", "quantity": 2},
    )
    assert added["item"]["quantity"] == 2
    sheet, consumed = change_inventory(
        sheet, action="consume", item_id="item.lantern", quantity=1
    )
    assert consumed["item"]["quantity"] == 1
    sheet, removed = change_inventory(sheet, action="remove", item_id="item.lantern")
    assert removed["item"]["quantity"] == 0
    assert sheet["inventory"] == []
    with pytest.raises(LookupError):
        change_inventory(sheet, action="remove", item_id="item.lantern")


def test_money_set_and_adjust_require_explicit_campaign_fields() -> None:
    sheet = validate_investigator_sheet({"monetary": {}})
    sheet, set_receipt = change_money(
        sheet, action="set", field="cash_cents", value=500
    )
    assert set_receipt["after"] == 500
    sheet, adjustment = change_money(
        sheet, action="adjust", field="cash_cents", amount=-125
    )
    assert adjustment == {
        "action": "adjust",
        "field": "cash_cents",
        "before": 500,
        "after": 375,
    }
    assert sheet["monetary"]["cash_cents"] == 375


def test_source_study_atomically_updates_mythos_san_max_and_catalog() -> None:
    sheet = validate_investigator_sheet(
        {"characteristics": {"pow": 70}, "san": 70, "cthulhu_mythos": 0}
    )
    sheet, receipt = settle_source_study(
        sheet,
        kind="tome",
        source_id="tome.private-fragment",
        title="Private Fragment",
        sanity_loss=3,
        mythos_gain=5,
    )
    assert sheet["san"] == 67
    assert sheet["san_max"] == 94
    assert sheet["books"] == [{"id": "tome.private-fragment", "title": "Private Fragment"}]
    assert receipt["cthulhu_mythos"]["after"] == 5
