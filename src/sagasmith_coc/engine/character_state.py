"""Deterministic CoC character-record mutations outside encounter settlement."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from sagasmith_coc.system import validate_investigator_sheet


def _item_id(value: dict[str, Any]) -> str:
    return str(value.get("id") or value.get("item_id") or "").strip()


def change_inventory(
    sheet: dict[str, Any],
    *,
    action: str,
    item: dict[str, Any] | None = None,
    item_id: str | None = None,
    quantity: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Add, update, remove, or consume one source-identified inventory item."""

    value = validate_investigator_sheet(deepcopy(sheet))
    inventory = list(value.get("inventory") or [])
    if any(not isinstance(entry, dict) for entry in inventory):
        raise ValueError("inventory mutations require object entries with stable ids")
    target_id = str(item_id or _item_id(dict(item or {}))).strip()
    if not target_id:
        raise ValueError("inventory mutation requires item_id")
    matches = [index for index, entry in enumerate(inventory) if _item_id(entry) == target_id]
    if len(matches) > 1:
        raise ValueError(f"inventory contains duplicate item id: {target_id}")
    action_value = str(action or "").strip()
    changed_quantity: int | None = None

    if action_value == "add":
        if matches:
            raise ValueError(f"inventory item already exists: {target_id}")
        created = deepcopy(dict(item or {}))
        name = str(created.get("name") or "").strip()
        if not name:
            raise ValueError("inventory add requires item.name")
        count = int(created.get("quantity", quantity if quantity is not None else 1))
        if count < 1:
            raise ValueError("inventory quantity must be positive")
        created["id"] = target_id
        created.pop("item_id", None)
        created["name"] = name
        created["quantity"] = count
        inventory.append(created)
        result_item = created
    elif action_value == "update":
        if not matches:
            raise LookupError(target_id)
        patch = deepcopy(dict(item or {}))
        patch.pop("id", None)
        patch.pop("item_id", None)
        updated = {**inventory[matches[0]], **patch, "id": target_id}
        if not str(updated.get("name") or "").strip():
            raise ValueError("inventory item name must not be empty")
        if int(updated.get("quantity", 1)) < 1:
            raise ValueError("inventory quantity must be positive")
        updated["quantity"] = int(updated.get("quantity", 1))
        inventory[matches[0]] = updated
        result_item = updated
    elif action_value in {"remove", "consume"}:
        if not matches:
            raise LookupError(target_id)
        index = matches[0]
        current = deepcopy(inventory[index])
        available = int(current.get("quantity", 1))
        count = int(quantity if quantity is not None else available)
        if count < 1 or count > available:
            raise ValueError("inventory removal quantity exceeds the available positive quantity")
        remaining = available - count
        changed_quantity = count
        if remaining:
            current["quantity"] = remaining
            inventory[index] = current
            result_item = current
        else:
            inventory.pop(index)
            result_item = {**current, "quantity": 0}
    else:
        raise ValueError("inventory action must be add, update, remove, or consume")

    value["inventory"] = inventory
    return validate_investigator_sheet(value), {
        "action": action_value,
        "item_id": target_id,
        "item": deepcopy(result_item),
        "quantity_changed": changed_quantity,
    }


def change_money(
    sheet: dict[str, Any],
    *,
    action: str,
    field: str,
    amount: int | float | None = None,
    value: Any = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Set or arithmetically adjust one campaign-defined monetary field."""

    result = validate_investigator_sheet(deepcopy(sheet))
    key = str(field or "").strip()
    if not key or len(key) > 80:
        raise ValueError("money field must contain 1 to 80 characters")
    monetary = deepcopy(dict(result.get("monetary") or {}))
    action_value = str(action or "").strip()
    before = monetary.get(key)
    if action_value == "set":
        if value is None:
            raise ValueError("money set requires value")
        monetary[key] = deepcopy(value)
    elif action_value == "adjust":
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise ValueError("money adjust requires a numeric amount")
        if isinstance(before, bool) or not isinstance(before, (int, float)):
            raise ValueError("money adjust requires an existing numeric field")
        monetary[key] = before + amount
    else:
        raise ValueError("money action must be set or adjust")
    result["monetary"] = monetary
    return validate_investigator_sheet(result), {
        "action": action_value,
        "field": key,
        "before": before,
        "after": monetary[key],
    }


def settle_source_study(
    sheet: dict[str, Any],
    *,
    kind: str,
    source_id: str,
    title: str,
    sanity_loss: int = 0,
    mythos_gain: int = 0,
    spell: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply explicit source-defined tome or spell-study consequences.

    The caller supplies reviewed printed values.  This function owns bounds,
    deduplication, SAN maximum, and the atomic sheet transition; it never
    interprets prose or invents missing source numbers.
    """

    result = validate_investigator_sheet(deepcopy(sheet))
    kind_value = str(kind or "").strip()
    stable_id = str(source_id or "").strip()
    title_value = str(title or "").strip()
    if kind_value not in {"tome", "spell"}:
        raise ValueError("study kind must be tome or spell")
    if not stable_id or not title_value:
        raise ValueError("source study requires source_id and title")
    san_loss = int(sanity_loss)
    mythos = int(mythos_gain)
    if san_loss < 0 or mythos < 0:
        raise ValueError("source study SAN loss and Mythos gain must be non-negative")

    previous_san = int(result["san"])
    previous_mythos = int(result["cthulhu_mythos"])
    result["cthulhu_mythos"] = min(100, previous_mythos + mythos)
    result["san_max"] = max(0, 99 - result["cthulhu_mythos"])
    result["san"] = min(result["san_max"], max(0, previous_san - san_loss))
    collection_name = "books" if kind_value == "tome" else "spells"
    collection = list(result.get(collection_name) or [])
    if any(
        isinstance(entry, dict) and str(entry.get("id") or "") == stable_id
        for entry in collection
    ):
        raise ValueError(f"{kind_value} is already recorded: {stable_id}")
    entry = {"id": stable_id, "title": title_value}
    if kind_value == "spell":
        entry.update(deepcopy(dict(spell or {})))
        entry["id"] = stable_id
        entry["title"] = title_value
    collection.append(entry)
    result[collection_name] = collection
    result = validate_investigator_sheet(result)
    return result, {
        "kind": kind_value,
        "source_id": stable_id,
        "sanity": {"before": previous_san, "loss": san_loss, "after": result["san"]},
        "cthulhu_mythos": {
            "before": previous_mythos,
            "gain": mythos,
            "after": result["cthulhu_mythos"],
        },
        "san_max": result["san_max"],
    }
