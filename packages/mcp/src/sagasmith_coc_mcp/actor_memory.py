"""Deterministic four-track, actor-scoped long-term memory selection."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from typing import Any, Iterable, Mapping

MEMORY_TRACKS = ("identity", "motivational", "semantic", "episodic")
_MOTIVATIONAL = frozenset(
    {
        "bond",
        "commitment",
        "desire",
        "drive",
        "duty",
        "fear",
        "flaw",
        "goal",
        "ideal",
        "motivation",
        "objective",
        "obsession",
        "phobia",
        "promise",
        "relationship",
        "relationship_to",
    }
)
_TOKEN = re.compile(r"[\w:-]+", re.UNICODE)


def select_actor_memory_context(
    *,
    actor_state: Mapping[str, Any] | Iterable[Mapping[str, Any] | Any] | Any,
    actor_knowledge: Iterable[Mapping[str, Any] | Any],
    events: Iterable[Mapping[str, Any] | Any],
    current_refs: Iterable[str] = (),
    query: str = "",
    budget_chars: int = 8_000,
) -> dict[str, Any]:
    """Return evidence-carrying memories without proposing actor intent."""

    if isinstance(budget_chars, bool) or not isinstance(budget_chars, int) or budget_chars < 0:
        raise ValueError("budget_chars must be a non-negative integer")
    candidates: list[dict[str, Any]] = []
    for record in _state_records(actor_state):
        predicate = _text(record.get("predicate")).casefold().replace("-", "_")
        kind = _text(record.get("kind")).casefold().replace("-", "_")
        track = (
            "motivational"
            if predicate in _MOTIVATIONAL or kind in {"goal", "motivation", "relationship"}
            else "identity"
        )
        candidates.append(_candidate(record, track, "actor_state"))
    for raw in actor_knowledge:
        candidates.append(_candidate(_record(raw), "semantic", "actor_knowledge"))
    for raw in events:
        candidates.append(_candidate(_record(raw), "episodic", "event"))

    current = {_text(item) for item in current_refs if _text(item)}
    terms = set(_TOKEN.findall(str(query or "").casefold()))
    deduped: dict[str, dict[str, Any]] = {}
    for item in candidates:
        identity = item["identity_key"]
        current_item = deduped.get(identity)
        preference = (item["recency"], item["salience"], item["confidence"])
        if current_item is None or preference > (
            current_item["recency"],
            current_item["salience"],
            current_item["confidence"],
        ):
            deduped[identity] = item
    ranked = []
    for item in deduped.values():
        exact = len(current.intersection([item["basis_ref"], *item["refs"]]))
        haystack = " ".join(
            [item["content"], item["basis_ref"], *item["refs"], _canonical(item["record"])]
        ).casefold()
        lexical = sum(term in haystack for term in terms)
        score = (
            exact * 1_000_000
            + lexical * 10_000
            + item["salience"] * 1_000
            + item["confidence"] * 100
            + min(99, int(item["recency"]))
        )
        ranked.append(
            (
                (
                    -exact,
                    -lexical,
                    -item["salience"],
                    -item["confidence"],
                    -item["recency"],
                    item["basis_ref"],
                ),
                item,
                score,
            )
        )
    ranked.sort(key=lambda value: value[0])
    selected: dict[str, list[dict[str, Any]]] = {track: [] for track in MEMORY_TRACKS}
    used = 0
    omitted = 0
    first_by_track: list[tuple[Any, dict[str, Any], int]] = []
    selected_identities: set[str] = set()
    for track in MEMORY_TRACKS:
        first = next((entry for entry in ranked if entry[1]["track"] == track), None)
        if first is not None:
            first_by_track.append(first)
            selected_identities.add(first[1]["identity_key"])
    ordered = [
        *first_by_track,
        *(entry for entry in ranked if entry[1]["identity_key"] not in selected_identities),
    ]
    for _rank, item, score in ordered:
        rendered = {
            "basis_ref": item["basis_ref"],
            "source": item["source"],
            "content": item["content"],
            "refs": item["refs"],
            "record": item["record"],
            "score": score,
        }
        cost = len(_canonical(rendered))
        if used + cost > budget_chars:
            omitted += 1
            continue
        selected[item["track"]].append(deepcopy(rendered))
        used += cost
    return {
        **selected,
        "diagnostics": {
            "strategy": "track_floor_exact_refs_lexical_salience_confidence_recency_v1",
            "budget_chars": budget_chars,
            "used_chars": used,
            "candidate_count": len(candidates),
            "deduplicated_count": len(deduped),
            "selected_count": sum(len(items) for items in selected.values()),
            "omitted_for_budget": omitted,
            "query_terms": sorted(terms),
        },
    }


def _candidate(record: dict[str, Any], track: str, source: str) -> dict[str, Any]:
    item_id = _text(record.get("id")) or _digest(record)
    revision = _text(record.get("revision_id") or record.get("revision"))
    prefix = {"actor_state": "actor", "actor_knowledge": "knowledge", "event": "event"}[source]
    basis_ref = f"{prefix}:{item_id}" + (f":{revision}" if revision and source != "event" else "")
    if source == "actor_knowledge":
        content = _text(record.get("proposition")) or _canonical(record)
        identity = (
            f"knowledge:{_text(record.get('actor_id'))}:"
            f"{_text(record.get('knowledge_key')) or item_id}"
        )
    elif source == "event":
        content = _text(record.get("retrieval_text") or record.get("summary")) or _canonical(record)
        identity = f"event:{item_id}"
    else:
        content = _text(record.get("content") or record.get("summary")) or _canonical(record)
        identity = f"state:{_text(record.get('fact_key')) or item_id}"
    return {
        "track": track,
        "source": source,
        "basis_ref": basis_ref,
        "content": content,
        "refs": _refs(record, source),
        "record": record,
        "identity_key": identity,
        "recency": _number(record.get("sequence") or record.get("revision") or 0),
        "confidence": _signal(record.get("confidence"), 3),
        "salience": _signal(
            record.get("salience")
            or record.get("importance")
            or dict(record.get("payload") or {}).get("salience"),
            5 if source == "actor_state" else 3,
        ),
    }


def _state_records(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, Mapping) or (is_dataclass(value) and not isinstance(value, type)):
        item = _record(value)
        nested: list[dict[str, Any]] = []
        for field in ("state_facts", "facts"):
            raw = item.pop(field, None)
            if raw is not None:
                if not isinstance(raw, list):
                    raise ValueError(f"actor_state.{field} must be a list")
                nested.extend(_record(entry) for entry in raw)
        return [item, *nested]
    if isinstance(value, (str, bytes)):
        raise ValueError("actor_state must contain objects")
    return [_record(item) for item in value]


def _record(value: Any) -> dict[str, Any]:
    if is_dataclass(value) and not isinstance(value, type):
        value = asdict(value)
    if not isinstance(value, Mapping):
        raise ValueError("actor memory inputs must be objects")
    return deepcopy(dict(value))


def _refs(record: Mapping[str, Any], source: str) -> list[str]:
    refs: set[str] = set()

    def visit(value: Any, key: str = "") -> None:
        if isinstance(value, Mapping):
            for child_key, child in value.items():
                name = str(child_key)
                if source == "actor_knowledge" and name == "actor_id":
                    continue
                if name.endswith("_ref") and _text(child):
                    refs.add(_text(child))
                elif name.endswith("_refs") and isinstance(child, list):
                    refs.update(_text(item) for item in child if _text(item))
                elif name in {"actor_id", "speaker_actor_id"} and _text(child):
                    refs.add(f"actor:{_text(child)}")
                elif name in {"event_id", "source_event_id"} and _text(child):
                    refs.add(f"event:{_text(child)}")
                elif name == "scene_id" and _text(child):
                    scene_ref = _text(child)
                    refs.add(scene_ref if scene_ref.startswith("scene:") else f"scene:{scene_ref}")
                visit(child, name)
        elif isinstance(value, list):
            for item in value:
                visit(item, key)

    visit(record)
    return sorted(refs)


def _signal(value: Any, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        return max(0, min(5, int(value)))
    except (TypeError, ValueError):
        return default


def _number(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()[:16]


def _text(value: Any) -> str:
    return str(value or "").strip()
