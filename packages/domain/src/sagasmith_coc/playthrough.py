"""Validated campaign-growth manifest for authored and emergent CoC play."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

SCHEMA_VERSION = 1
CAMPAIGN_MODES = {"authored_scenario", "authored_with_extensions", "emergent"}
CONTENT_CLASSIFICATIONS = {"authored_scenario", "emergent_seed", "emergent_episode"}
FRONT_STATUSES = {"dormant", "active", "advanced", "resolved", "averted"}
THREAD_STATUSES = {"dormant", "open", "advanced", "resolved", "abandoned"}
ARC_STATUSES = {"dormant", "available", "advanced", "resolved", "closed"}
EVIDENCE_KINDS = {"event", "snapshot", "scene", "memory_fact", "conversation", "clue"}

_FRONT_TRANSITIONS = {
    "dormant": FRONT_STATUSES,
    "active": {"active", "advanced", "resolved", "averted"},
    "advanced": {"advanced", "resolved", "averted"},
    "resolved": {"resolved"},
    "averted": {"averted"},
}
_THREAD_TRANSITIONS = {
    "dormant": THREAD_STATUSES,
    "open": {"open", "advanced", "resolved", "abandoned"},
    "advanced": {"advanced", "resolved", "abandoned"},
    "resolved": {"resolved"},
    "abandoned": {"abandoned"},
}
_ARC_TRANSITIONS = {
    "dormant": ARC_STATUSES,
    "available": {"available", "advanced", "resolved", "closed"},
    "advanced": {"advanced", "resolved", "closed"},
    "resolved": {"resolved"},
    "closed": {"closed"},
}


def new_playthrough_manifest(
    *,
    campaign_line_id: str,
    module_ids: list[str],
    campaign_mode: str = "authored_scenario",
    content_lineage: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    lineage = content_lineage or [
        {
            "module_id": module_id,
            "classification": "authored_scenario",
            "root_module_id": module_id,
            "parent_module_id": "",
            "generation": 0,
            "scene_ids": [],
            "source_refs": [],
        }
        for module_id in module_ids
    ]
    return validate_playthrough_manifest(
        {
            "schema_version": SCHEMA_VERSION,
            "campaign_line_id": campaign_line_id,
            "campaign_mode": campaign_mode,
            "module_ids": module_ids,
            "content_lineage": lineage,
            "current": {
                "module_id": "",
                "chapter_id": "",
                "chapter_title": "",
                "scene_id": "",
                "scene_title": "",
                "objective": "",
            },
            "traversal": {"reachable_scene_ids": [], "visited_scene_ids": []},
            "front_progress": [],
            "thread_progress": [],
            "arc_progress": [],
        }
    )


def validate_playthrough_manifest(value: Any) -> dict[str, Any]:
    manifest = _object(value, "playthrough_manifest")
    _only(
        manifest,
        "playthrough_manifest",
        {
            "schema_version",
            "campaign_line_id",
            "campaign_mode",
            "module_ids",
            "content_lineage",
            "current",
            "traversal",
            "front_progress",
            "thread_progress",
            "arc_progress",
        },
    )
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"playthrough_manifest.schema_version must be {SCHEMA_VERSION}")
    mode = _choice(manifest.get("campaign_mode"), "campaign_mode", CAMPAIGN_MODES)
    module_ids = _unique_strings(manifest.get("module_ids"), "module_ids")
    if not module_ids:
        raise ValueError("playthrough_manifest.module_ids must not be empty")
    lineage = _validate_lineage(manifest.get("content_lineage"), module_ids, mode)
    current = _object(manifest.get("current"), "current")
    current_fields = {
        "module_id",
        "chapter_id",
        "chapter_title",
        "scene_id",
        "scene_title",
        "objective",
    }
    _only(current, "current", current_fields)
    normalized_current = {field: _text(current.get(field)) for field in current_fields}
    if normalized_current["module_id"] and normalized_current["module_id"] not in module_ids:
        raise ValueError("current.module_id must identify an installed shard")
    all_scene_ids = {scene for item in lineage for scene in item["scene_ids"]}
    if normalized_current["scene_id"] and normalized_current["scene_id"] not in all_scene_ids:
        raise ValueError("current.scene_id must identify a lineage Scene Atlas entry")
    if normalized_current["module_id"] and normalized_current["scene_id"]:
        current_lineage = next(
            item for item in lineage if item["module_id"] == normalized_current["module_id"]
        )
        if normalized_current["scene_id"] not in current_lineage["scene_ids"]:
            raise ValueError("current.scene_id must belong to current.module_id")
    traversal = _object(manifest.get("traversal"), "traversal")
    _only(traversal, "traversal", {"reachable_scene_ids", "visited_scene_ids"})
    reachable = _unique_strings(traversal.get("reachable_scene_ids"), "reachable_scene_ids")
    visited = _unique_strings(traversal.get("visited_scene_ids"), "visited_scene_ids")
    if set(reachable) - all_scene_ids:
        raise ValueError("reachable_scene_ids must belong to installed Scene Atlas shards")
    if set(visited) - set(reachable):
        raise ValueError("visited_scene_ids must be a subset of reachable_scene_ids")
    fronts = _progress(manifest.get("front_progress"), "front_progress", FRONT_STATUSES, True)
    threads = _progress(manifest.get("thread_progress"), "thread_progress", THREAD_STATUSES, False)
    arcs = _arc_progress(manifest.get("arc_progress"))
    return {
        "schema_version": SCHEMA_VERSION,
        "campaign_line_id": _required(manifest.get("campaign_line_id"), "campaign_line_id"),
        "campaign_mode": mode,
        "module_ids": module_ids,
        "content_lineage": lineage,
        "current": normalized_current,
        "traversal": {"reachable_scene_ids": reachable, "visited_scene_ids": visited},
        "front_progress": fronts,
        "thread_progress": threads,
        "arc_progress": arcs,
    }


def validate_playthrough_transition(current_value: Any, next_value: Any) -> dict[str, Any]:
    """Validate a monotonic campaign-line update and return the normalized successor."""

    current = validate_playthrough_manifest(current_value)
    successor = validate_playthrough_manifest(next_value)
    if successor["campaign_line_id"] != current["campaign_line_id"]:
        raise ValueError("playthrough campaign_line_id is immutable")
    old_module_ids = current["module_ids"]
    if successor["module_ids"][: len(old_module_ids)] != old_module_ids:
        raise ValueError("playthrough module_ids may only append reviewed shards")
    if len(successor["module_ids"]) < len(old_module_ids):
        raise ValueError("playthrough module_ids may not delete existing shards")
    old_lineage = current["content_lineage"]
    if successor["content_lineage"][: len(old_lineage)] != old_lineage:
        raise ValueError("existing playthrough lineage and shard metadata are immutable")

    old_mode = current["campaign_mode"]
    new_mode = successor["campaign_mode"]
    appended = successor["content_lineage"][len(old_lineage) :]
    if new_mode != old_mode:
        legal_authored_extension = (
            old_mode == "authored_scenario"
            and new_mode == "authored_with_extensions"
            and bool(appended)
            and all(item["classification"] == "emergent_episode" for item in appended)
        )
        if not legal_authored_extension:
            raise ValueError("campaign_mode transition is not permitted")
    if appended and any(item["classification"] != "emergent_episode" for item in appended):
        raise ValueError("playthrough updates may append only emergent_episode shards")
    if not set(current["traversal"]["visited_scene_ids"]).issubset(
        successor["traversal"]["visited_scene_ids"]
    ):
        raise ValueError("visited_scene_ids may not delete established traversal history")
    _validate_progress_transition(
        current["front_progress"],
        successor["front_progress"],
        field="front_progress",
        transitions=_FRONT_TRANSITIONS,
        staged=True,
    )
    _validate_progress_transition(
        current["thread_progress"],
        successor["thread_progress"],
        field="thread_progress",
        transitions=_THREAD_TRANSITIONS,
    )
    _validate_arc_transition(current["arc_progress"], successor["arc_progress"])
    return successor


def _validate_progress_transition(
    current: list[dict[str, Any]],
    successor: list[dict[str, Any]],
    *,
    field: str,
    transitions: dict[str, set[str]],
    staged: bool = False,
) -> None:
    next_by_id = {item["id"]: item for item in successor}
    for previous in current:
        item_id = previous["id"]
        following = next_by_id.get(item_id)
        if following is None:
            raise ValueError(f"{field} may not delete established id {item_id!r}")
        if following["status"] not in transitions[previous["status"]]:
            raise ValueError(
                f"{field} {item_id!r} may not move from {previous['status']!r} "
                f"to {following['status']!r}"
            )
        if staged and following["stage"] < previous["stage"]:
            raise ValueError(f"{field} {item_id!r} stage may not decrease")
        _require_evidence_history(previous, following, field=field)


def _validate_arc_transition(
    current: list[dict[str, Any]], successor: list[dict[str, Any]]
) -> None:
    next_by_id = {item["id"]: item for item in successor}
    for previous in current:
        arc_id = previous["id"]
        following = next_by_id.get(arc_id)
        if following is None:
            raise ValueError(f"arc_progress may not delete established id {arc_id!r}")
        if (following["actor_id"], following["actor_kind"]) != (
            previous["actor_id"],
            previous["actor_kind"],
        ):
            raise ValueError(f"arc_progress {arc_id!r} actor identity is immutable")
        if following["status"] not in _ARC_TRANSITIONS[previous["status"]]:
            raise ValueError(
                f"arc_progress {arc_id!r} may not move from {previous['status']!r} "
                f"to {following['status']!r}"
            )
        if not set(previous["completed_opportunity_ids"]).issubset(
            following["completed_opportunity_ids"]
        ):
            raise ValueError(
                f"arc_progress {arc_id!r} completed_opportunity_ids may not delete history"
            )
        _require_evidence_history(previous, following, field="arc_progress")


def _require_evidence_history(
    previous: dict[str, Any], following: dict[str, Any], *, field: str
) -> None:
    old_evidence = {(item["kind"], item["ref_id"]) for item in previous["evidence_refs"]}
    new_evidence = {(item["kind"], item["ref_id"]) for item in following["evidence_refs"]}
    if not old_evidence.issubset(new_evidence):
        raise ValueError(f"{field} {previous['id']!r} evidence_refs may not delete history")


def _validate_lineage(value: Any, module_ids: list[str], mode: str) -> list[dict[str, Any]]:
    raw_items = _list(value)
    items: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_items):
        field = f"content_lineage[{index}]"
        item = _object(raw, field)
        _only(
            item,
            field,
            {
                "module_id",
                "classification",
                "root_module_id",
                "parent_module_id",
                "generation",
                "scene_ids",
                "source_refs",
            },
        )
        module_id = _required(item.get("module_id"), f"{field}.module_id")
        classification = _choice(
            item.get("classification"), f"{field}.classification", CONTENT_CLASSIFICATIONS
        )
        root = _required(item.get("root_module_id"), f"{field}.root_module_id")
        parent = _text(item.get("parent_module_id"))
        generation = _integer(item.get("generation"), f"{field}.generation", 0)
        if classification in {"authored_scenario", "emergent_seed"} and (
            root != module_id or parent or generation != 0
        ):
            raise ValueError(f"{field} root shards must be generation 0 with no parent")
        if classification == "emergent_episode" and (not parent or generation < 1):
            raise ValueError(f"{field} emergent_episode requires a parent and positive generation")
        refs = _refs(item.get("source_refs"), f"{field}.source_refs")
        items.append(
            {
                "module_id": module_id,
                "classification": classification,
                "root_module_id": root,
                "parent_module_id": parent,
                "generation": generation,
                "scene_ids": _unique_strings(item.get("scene_ids"), f"{field}.scene_ids"),
                "source_refs": refs,
            }
        )
    if [item["module_id"] for item in items] != module_ids:
        raise ValueError("content_lineage module ids must match module_ids in order")
    _unique(items, "module_id", "content_lineage")
    scenes = [scene for item in items for scene in item["scene_ids"]]
    if len(scenes) != len(set(scenes)):
        raise ValueError("content_lineage scene_ids must be unique across shards")
    by_id = {item["module_id"]: item for item in items}
    for index, item in enumerate(items):
        if item["classification"] != "emergent_episode":
            continue
        parent = by_id.get(item["parent_module_id"])
        if parent is None:
            raise ValueError(f"content_lineage[{index}].parent_module_id is not installed")
        if item["root_module_id"] != parent["root_module_id"]:
            raise ValueError(f"content_lineage[{index}] must share its parent's root")
        if item["generation"] != parent["generation"] + 1:
            raise ValueError(f"content_lineage[{index}] generation must equal parent + 1")
    if mode == "authored_scenario" and any(
        item["classification"] != "authored_scenario" for item in items
    ):
        raise ValueError("authored_scenario mode cannot contain emergent shards")
    if mode == "authored_with_extensions":
        if not any(item["classification"] == "authored_scenario" for item in items):
            raise ValueError("authored_with_extensions requires an authored root")
        if any(item["classification"] == "emergent_seed" for item in items):
            raise ValueError("authored extensions use emergent_episode, not emergent_seed")
    if mode == "emergent" and not any(item["classification"] == "emergent_seed" for item in items):
        raise ValueError("emergent mode requires an emergent_seed")
    return items


def _progress(value: Any, field: str, statuses: set[str], staged: bool) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    material = {"advanced", "resolved", "averted", "abandoned"}
    for index, raw in enumerate(_list(value)):
        path = f"{field}[{index}]"
        item = _object(raw, path)
        allowed = {"id", "status", "source_ref", "evidence_refs"} | ({"stage"} if staged else set())
        _only(item, path, allowed)
        status = _choice(item.get("status"), f"{path}.status", statuses)
        evidence = _refs(item.get("evidence_refs"), f"{path}.evidence_refs")
        if status in material and not evidence:
            raise ValueError(f"{path}.status={status!r} requires evidence_refs")
        normalized = {
            "id": _required(item.get("id"), f"{path}.id"),
            "status": status,
            "source_ref": deepcopy(item.get("source_ref")),
            "evidence_refs": evidence,
        }
        if staged:
            normalized["stage"] = _integer(item.get("stage"), f"{path}.stage", 0)
        result.append(normalized)
    _unique(result, "id", field)
    return result


def _arc_progress(value: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, raw in enumerate(_list(value)):
        path = f"arc_progress[{index}]"
        item = _object(raw, path)
        _only(
            item,
            path,
            {
                "id",
                "actor_id",
                "actor_kind",
                "status",
                "completed_opportunity_ids",
                "source_ref",
                "evidence_refs",
            },
        )
        status = _choice(item.get("status"), f"{path}.status", ARC_STATUSES)
        evidence = _refs(item.get("evidence_refs"), f"{path}.evidence_refs")
        if (status in {"advanced", "resolved", "closed"} or item.get(
            "completed_opportunity_ids"
        )) and not evidence:
            raise ValueError(f"{path}.status={status!r} requires evidence_refs")
        result.append(
            {
                "id": _required(item.get("id"), f"{path}.id"),
                "actor_id": _required(item.get("actor_id"), f"{path}.actor_id"),
                "actor_kind": _choice(item.get("actor_kind"), f"{path}.actor_kind", {"pc", "npc"}),
                "status": status,
                "completed_opportunity_ids": _unique_strings(
                    item.get("completed_opportunity_ids"), f"{path}.completed_opportunity_ids"
                ),
                "source_ref": deepcopy(item.get("source_ref")),
                "evidence_refs": evidence,
            }
        )
    _unique(result, "id", "arc_progress")
    return result


def _refs(value: Any, field: str) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for index, raw in enumerate(_list(value)):
        item = _object(raw, f"{field}[{index}]")
        _only(item, f"{field}[{index}]", {"kind", "ref_id"})
        result.append(
            {
                "kind": _choice(item.get("kind"), f"{field}[{index}].kind", EVIDENCE_KINDS),
                "ref_id": _required(item.get("ref_id"), f"{field}[{index}].ref_id"),
            }
        )
    identities = [(item["kind"], item["ref_id"]) for item in result]
    if len(identities) != len(set(identities)):
        raise ValueError(f"{field} must not contain duplicates")
    return result


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return deepcopy(value)


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("manifest collections must be arrays")
    return deepcopy(value)


def _only(value: dict[str, Any], field: str, allowed: set[str]) -> None:
    if unknown := sorted(set(value) - allowed):
        raise ValueError(f"{field} contains unsupported fields: {', '.join(unknown)}")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _required(value: Any, field: str) -> str:
    result = _text(value)
    if not result:
        raise ValueError(f"{field} is required")
    return result


def _integer(value: Any, field: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{field} must be an integer >= {minimum}")
    return value


def _choice(value: Any, field: str, choices: set[str]) -> str:
    result = _required(value, field)
    if result not in choices:
        raise ValueError(f"{field} must be one of {', '.join(sorted(choices))}")
    return result


def _unique_strings(value: Any, field: str) -> list[str]:
    result = [_required(item, f"{field}[]") for item in _list(value)]
    if len(result) != len(set(result)):
        raise ValueError(f"{field} must not contain duplicates")
    return result


def _unique(items: list[dict[str, Any]], key: str, field: str) -> None:
    values = [item[key] for item in items]
    if len(values) != len(set(values)):
        raise ValueError(f"{field} contains duplicate {key} values")
