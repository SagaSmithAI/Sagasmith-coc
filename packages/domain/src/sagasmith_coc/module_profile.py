"""CoC scenario enrichment for the generic module parser."""

from __future__ import annotations

import json
import re

from sagasmith_core.modules import GenericModuleProfile, SceneBoundary

_TAGS = {
    "clue": ("clue", "线索", "证据"),
    "handout": ("handout", "玩家资料", "手记", "剪报"),
    "sanity": ("san loss", "sanity", "理智损失", "san 检定"),
    "mythos": ("mythos", "克苏鲁神话", "神话"),
    "npc": ("npc", "人物", "调查员"),
    "location": ("location", "地点", "场景"),
    "timeline": ("timeline", "时间线"),
}
_HANDOUT_RE = re.compile(
    r"(?:handout|player(?:'s)?\s+aid|玩家资料|手记|剪报|照片)\s*(?:[:：#-]|\d|$)",
    re.IGNORECASE,
)
_SOLO_NODE_RE = re.compile(r"^\s*(\d{1,4})\s*[.)、]?\s*$")
_SOLO_EDGE_RE = re.compile(
    r"(?:go|turn|proceed|return)\s+to[*_`~\s]*(\d{1,4})|"
    r"(?:转到|前往|跳到|返回)[*_`~\s]*(\d{1,4})|"
    r"→[*_`~\s]*(\d{1,4})",
    re.IGNORECASE,
)
_REFERENCE_SIGNALS = (
    "credits",
    "table of contents",
    "introduction",
    "scenario overview",
    "background",
    "setting up",
    "running the",
    "keeper guidance",
    "conclusion",
    "rewards",
    "epilogue",
    "致谢",
    "目录",
    "介绍",
    "概述",
    "背景",
    "准备",
    "守秘人指南",
    "结局",
    "奖励",
    "尾声",
)
_SCENE_TYPE_SIGNALS = (
    ("handout", ("handout", "玩家资料", "手记", "剪报", "照片")),
    ("chase", ("chase", "pursuit", "追逐", "追击")),
    ("combat", ("combat", "fight", "attack", "ambush", "战斗", "攻击", "伏击")),
    (
        "social",
        ("interview", "questioning", "conversation", "reception", "访谈", "询问", "交谈"),
    ),
    ("travel", ("travel", "journey", "voyage", "road", "旅行", "旅程", "航行")),
)
_SUBSECTION_SIGNALS = (
    ("core_clue", ("core clue", "核心线索")),
    ("clue", ("clue", "evidence", "线索", "证据")),
    ("handout", ("handout", "玩家资料", "手记", "剪报", "照片")),
    ("sanity_check", ("san", "sanity", "理智")),
    ("timeline", ("timeline", "时间线")),
    ("npc", ("npc", "character", "人物", "调查员")),
    ("creature", ("creature", "monster", "怪物", "生物")),
    ("keeper_note", ("keeper", "守秘人")),
)
_SAN_RE = re.compile(
    r"(?:SAN|sanity|理智)[^0-9\n]{0,20}"
    r"(?P<success_before>\d+[dD]\d+|\d+)\s*/\s*"
    r"(?P<failure_before>\d+[dD]\d+|\d+)|"
    r"(?P<success_after>\d+[dD]\d+|\d+)\s*/\s*"
    r"(?P<failure_after>\d+[dD]\d+|\d+)"
    r"[^.\n]{0,24}(?:SAN|sanity|理智)",
    re.IGNORECASE,
)
_RUNTIME_MANIFEST = re.compile(
    r"<!--\s*sagasmith-runtime-manifest\s*(?P<body>\{.*?\})\s*-->",
    re.IGNORECASE | re.DOTALL,
)
_RUNTIME_ID = re.compile(r"^[a-z0-9][a-z0-9:_-]{0,199}$")
_RUNTIME_COLLECTIONS = (
    "entities",
    "secrets",
    "clues",
    "plot_nodes",
    "foreshadowing",
    "branches",
    "fronts",
    "story_threads",
    "character_arcs",
    "scene_links",
)

_RUNTIME_ITEM_SCHEMAS = {
    "entities": {"id", "kind", "name"},
    "secrets": {"id", "initial_knowers", "reveal_trigger"},
    "clues": {
        "id",
        "label",
        "trigger",
        "revelation",
        "linked_thread_ids",
        "fallback_scene_ids",
    },
    "plot_nodes": {"id", "trigger", "consequences", "linked_thread_ids"},
    "foreshadowing": {
        "id",
        "signal",
        "reveal_trigger",
        "linked_thread_ids",
        "payoff_scene_ids",
    },
    "branches": {"id", "trigger", "consequences", "scene_ids"},
    "fronts": {"id", "name", "goal", "stakes", "grim_portents", "linked_thread_ids"},
    "story_threads": {"id", "title", "question", "linked_front_ids", "linked_clue_ids"},
    "character_arcs": {
        "id",
        "actor_id",
        "actor_kind",
        "opportunities",
        "planned_beats",
        "possible_endings",
    },
    "scene_links": {"id", "from_scene_id", "to_scene_id", "kind", "trigger"},
}


def _runtime_exact_fields(
    item: dict[str, object], path: str, fields: set[str], errors: list[str]
) -> None:
    if missing := sorted(fields - set(item)):
        errors.append(f"runtime manifest {path} is missing fields: {', '.join(missing)}")
    if unknown := sorted(set(item) - fields):
        errors.append(f"runtime manifest {path} contains unsupported fields: {', '.join(unknown)}")


def _runtime_text(item: dict[str, object], field: str, path: str, errors: list[str]) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"runtime manifest {path}.{field} must be a non-empty string")
        return ""
    return value.strip()


def _runtime_strings(
    item: dict[str, object],
    field: str,
    path: str,
    errors: list[str],
    *,
    require_ids: bool = False,
) -> list[str]:
    value = item.get(field)
    if not isinstance(value, list) or any(
        not isinstance(entry, str) or not entry.strip() for entry in value
    ):
        errors.append(f"runtime manifest {path}.{field} must be a string list")
        return []
    if len(value) != len(set(value)):
        errors.append(f"runtime manifest {path}.{field} must not contain duplicates")
    if require_ids and any(not _RUNTIME_ID.fullmatch(entry) for entry in value):
        errors.append(f"runtime manifest {path}.{field} must contain stable lowercase ids")
    return value


def _runtime_manifest_errors(manifest: dict[str, object]) -> list[str]:
    errors: list[str] = []
    allowed = {
        "schema_version",
        "module_key",
        "classification",
        "lineage",
        *_RUNTIME_COLLECTIONS,
    }
    if unknown := sorted(set(manifest) - allowed):
        errors.append(f"runtime manifest contains unsupported fields: {', '.join(unknown)}")
    if manifest.get("schema_version") != 2:
        errors.append("runtime manifest schema_version must be 2")
    module_key = manifest.get("module_key")
    if not isinstance(module_key, str) or not _RUNTIME_ID.fullmatch(module_key):
        errors.append("runtime manifest module_key must be a stable lowercase id")
        module_key = ""
    classification = manifest.get("classification")
    if classification not in {"authored_scenario", "emergent_seed", "emergent_episode"}:
        errors.append(
            "runtime manifest classification must be authored_scenario, emergent_seed, "
            "or emergent_episode"
        )
    lineage = manifest.get("lineage")
    if not isinstance(lineage, dict):
        errors.append("runtime manifest lineage must be an object")
    else:
        _runtime_exact_fields(
            lineage,
            "lineage",
            {"root_module_key", "parent_module_key", "generation"},
            errors,
        )
        root = lineage.get("root_module_key")
        parent = lineage.get("parent_module_key")
        generation = lineage.get("generation")
        if not isinstance(root, str) or not _RUNTIME_ID.fullmatch(root):
            errors.append("runtime manifest lineage.root_module_key must be a stable lowercase id")
        if parent not in {None, ""} and (
            not isinstance(parent, str) or not _RUNTIME_ID.fullmatch(parent)
        ):
            errors.append("runtime manifest lineage.parent_module_key is invalid")
        if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
            errors.append("runtime manifest lineage.generation must be non-negative")
        elif classification in {"authored_scenario", "emergent_seed"} and (
            root != module_key or parent not in {None, ""} or generation != 0
        ):
            errors.append(f"{classification} lineage must be a generation-0 self root")
        elif classification == "emergent_episode" and (
            not isinstance(parent, str) or not parent or generation < 1
        ):
            errors.append("emergent_episode lineage requires a parent and positive generation")
    collections: dict[str, list[dict[str, object]]] = {}
    seen: set[str] = set()
    for collection in _RUNTIME_COLLECTIONS:
        if collection not in manifest:
            errors.append(f"runtime manifest {collection} is required")
        raw = manifest.get(collection, [])
        if not isinstance(raw, list):
            errors.append(f"runtime manifest {collection} must be a list")
            collections[collection] = []
            continue
        values: list[dict[str, object]] = []
        for index, item in enumerate(raw):
            if not isinstance(item, dict):
                errors.append(f"runtime manifest {collection}[{index}] must be an object")
                continue
            if fields := _RUNTIME_ITEM_SCHEMAS.get(collection):
                _runtime_exact_fields(item, f"{collection}[{index}]", fields, errors)
            item_id = item.get("id")
            if not isinstance(item_id, str) or not _RUNTIME_ID.fullmatch(item_id):
                errors.append(f"runtime manifest {collection}[{index}].id is invalid")
            elif item_id in seen:
                errors.append(f"runtime manifest contains duplicate id: {item_id}")
            else:
                seen.add(item_id)
            values.append(item)
        collections[collection] = values
    ids = {
        name: {str(item.get("id")) for item in values if item.get("id")}
        for name, values in collections.items()
    }
    for index, entity in enumerate(collections["entities"]):
        path = f"entities[{index}]"
        for field in ("kind", "name"):
            _runtime_text(entity, field, path, errors)
    for index, secret in enumerate(collections["secrets"]):
        path = f"secrets[{index}]"
        _runtime_text(secret, "reveal_trigger", path, errors)
        _runtime_strings(secret, "initial_knowers", path, errors, require_ids=True)
    for index, clue in enumerate(collections["clues"]):
        path = f"clues[{index}]"
        for field in ("label", "trigger", "revelation"):
            _runtime_text(clue, field, path, errors)
        _runtime_strings(clue, "fallback_scene_ids", path, errors, require_ids=True)
        for thread in _runtime_strings(clue, "linked_thread_ids", path, errors, require_ids=True):
            if thread not in ids["story_threads"]:
                errors.append(
                    f"runtime manifest clues[{index}] references unknown thread: {thread}"
                )
    for index, front in enumerate(collections["fronts"]):
        path = f"fronts[{index}]"
        for field in ("name", "goal", "stakes"):
            _runtime_text(front, field, path, errors)
        _runtime_strings(front, "grim_portents", path, errors)
        for thread in _runtime_strings(front, "linked_thread_ids", path, errors, require_ids=True):
            if thread not in ids["story_threads"]:
                errors.append(
                    f"runtime manifest fronts[{index}] references unknown thread: {thread}"
                )
    for index, node in enumerate(collections["plot_nodes"]):
        path = f"plot_nodes[{index}]"
        _runtime_text(node, "trigger", path, errors)
        _runtime_strings(node, "consequences", path, errors)
        for thread in _runtime_strings(node, "linked_thread_ids", path, errors, require_ids=True):
            if thread not in ids["story_threads"]:
                errors.append(
                    f"runtime manifest plot_nodes[{index}] references unknown thread: {thread}"
                )
    for index, signal in enumerate(collections["foreshadowing"]):
        path = f"foreshadowing[{index}]"
        for field in ("signal", "reveal_trigger"):
            _runtime_text(signal, field, path, errors)
        _runtime_strings(signal, "payoff_scene_ids", path, errors, require_ids=True)
        for thread in _runtime_strings(signal, "linked_thread_ids", path, errors, require_ids=True):
            if thread not in ids["story_threads"]:
                errors.append(
                    f"runtime manifest foreshadowing[{index}] references unknown thread: {thread}"
                )
    for index, branch in enumerate(collections["branches"]):
        path = f"branches[{index}]"
        _runtime_text(branch, "trigger", path, errors)
        _runtime_strings(branch, "consequences", path, errors)
        _runtime_strings(branch, "scene_ids", path, errors, require_ids=True)
    for index, thread in enumerate(collections["story_threads"]):
        path = f"story_threads[{index}]"
        for field in ("title", "question"):
            _runtime_text(thread, field, path, errors)
        for front in _runtime_strings(thread, "linked_front_ids", path, errors, require_ids=True):
            if front not in ids["fronts"]:
                errors.append(
                    f"runtime manifest story_threads[{index}] references unknown front: {front}"
                )
        for clue in _runtime_strings(thread, "linked_clue_ids", path, errors, require_ids=True):
            if clue not in ids["clues"]:
                errors.append(
                    f"runtime manifest story_threads[{index}] references unknown clue: {clue}"
                )
    opportunity_ids: set[str] = set()
    for index, arc in enumerate(collections["character_arcs"]):
        path = f"character_arcs[{index}]"
        actor_id = _runtime_text(arc, "actor_id", path, errors)
        if actor_id and not _RUNTIME_ID.fullmatch(actor_id):
            errors.append(
                f"runtime manifest character_arcs[{index}].actor_id must be a stable lowercase id"
            )
        actor_kind = arc.get("actor_kind")
        if actor_kind not in {"pc", "npc"}:
            errors.append(f"runtime manifest character_arcs[{index}].actor_kind must be pc or npc")
        opportunities = arc.get("opportunities", [])
        if not isinstance(opportunities, list):
            errors.append(f"runtime manifest character_arcs[{index}].opportunities must be a list")
            opportunities = []
        for opportunity_index, opportunity in enumerate(opportunities):
            if not isinstance(opportunity, dict):
                errors.append(
                    f"runtime manifest character_arcs[{index}].opportunities[{opportunity_index}] "
                    "must be an object"
                )
                continue
            opportunity_path = f"{path}.opportunities[{opportunity_index}]"
            _runtime_exact_fields(
                opportunity,
                opportunity_path,
                {"id", "prompt", "scene_ids", "thread_ids"},
                errors,
            )
            _runtime_text(opportunity, "prompt", opportunity_path, errors)
            _runtime_strings(opportunity, "scene_ids", opportunity_path, errors, require_ids=True)
            opportunity_id = opportunity.get("id")
            if not isinstance(opportunity_id, str) or not _RUNTIME_ID.fullmatch(opportunity_id):
                errors.append("runtime manifest character arc opportunity id is invalid")
            elif opportunity_id in opportunity_ids:
                errors.append(f"runtime manifest duplicate opportunity id: {opportunity_id}")
            else:
                opportunity_ids.add(opportunity_id)
            for thread in _runtime_strings(
                opportunity, "thread_ids", opportunity_path, errors, require_ids=True
            ):
                if thread not in ids["story_threads"]:
                    errors.append("runtime manifest character arc references unknown thread")
        planned_beats = _runtime_strings(arc, "planned_beats", path, errors)
        possible_endings = _runtime_strings(arc, "possible_endings", path, errors)
        if actor_kind == "pc" and (planned_beats or possible_endings):
            errors.append(
                "runtime manifest investigator arcs may define opportunities only; "
                "outcomes remain player choice"
            )
    for index, link in enumerate(collections["scene_links"]):
        path = f"scene_links[{index}]"
        start = _runtime_text(link, "from_scene_id", path, errors)
        end = _runtime_text(link, "to_scene_id", path, errors)
        _runtime_text(link, "kind", path, errors)
        _runtime_text(link, "trigger", path, errors)
        if start and not _RUNTIME_ID.fullmatch(start):
            errors.append(
                f"runtime manifest scene_links[{index}].from_scene_id must be a stable lowercase id"
            )
        if end and not _RUNTIME_ID.fullmatch(end):
            errors.append(
                f"runtime manifest scene_links[{index}].to_scene_id must be a stable lowercase id"
            )
        if start and start == end:
            errors.append(f"runtime manifest scene_links[{index}] cannot self-link")
    if classification == "emergent_episode" and not collections["scene_links"]:
        errors.append("emergent_episode runtime manifest requires at least one scene_link")
    return errors


def runtime_manifest_errors(value: object) -> list[str]:
    """Return deterministic design/lineage errors for one runtime manifest."""

    if not isinstance(value, dict):
        return ["runtime manifest must be an object"]
    return _runtime_manifest_errors(value)


def _runtime_metadata(content: str) -> dict[str, object]:
    matches = list(_RUNTIME_MANIFEST.finditer(content))
    if not matches:
        return {}
    if len(matches) > 1:
        return {"runtime_manifest_errors": ["module must contain at most one runtime manifest"]}
    try:
        manifest = json.loads(matches[0].group("body"))
    except json.JSONDecodeError as exc:
        return {"runtime_manifest_errors": [f"runtime manifest JSON is invalid: {exc.msg}"]}
    if not isinstance(manifest, dict):
        return {"runtime_manifest_errors": ["runtime manifest must be an object"]}
    return {
        "runtime_manifest": manifest,
        "runtime_manifest_errors": runtime_manifest_errors(manifest),
    }


def _line_number(content: str, offset: int) -> int:
    return content.count("\n", 0, offset) + 1


def _preamble_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") and stripped.lstrip("#").strip():
            return stripped.lstrip("#").strip()
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("<!--"):
            return stripped[:80]
    return fallback


def _scene_type(title: str, text: str, *, reference: bool = False) -> str:
    del text
    folded = title.casefold()
    if reference or any(signal in folded for signal in _REFERENCE_SIGNALS):
        return "reference"
    for scene_type, signals in _SCENE_TYPE_SIGNALS:
        if any(signal in folded for signal in signals):
            return scene_type
    return "investigation"


def _visibility(scene_type: str, text: str) -> str:
    if scene_type in {"handout", "solo_node"}:
        return "group"
    content_lines = [
        line.lstrip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if content_lines and content_lines[0].startswith(">"):
        return "public"
    return "restricted"


def _subsection_type(title: str) -> str:
    folded = title.casefold()
    for subsection_type, signals in _SUBSECTION_SIGNALS:
        if any(signal in folded for signal in signals):
            return subsection_type
    if "roll" in folded or "check" in folded or "检定" in folded:
        return "check"
    return "sublocation"


def _difficulty(title: str) -> str | None:
    folded = title.casefold()
    for value, signals in (
        ("extreme", ("extreme", "极难")),
        ("hard", ("hard", "困难")),
        ("regular", ("regular", "常规")),
    ):
        if any(signal in folded for signal in signals):
            return value
    return None


def _sanity_expressions(text: str) -> list[dict[str, str]]:
    values: list[dict[str, str]] = []
    for match in _SAN_RE.finditer(text):
        success = match.group("success_before") or match.group("success_after")
        failure = match.group("failure_before") or match.group("failure_after")
        values.append(
            {
                "expression": match.group(0).strip(),
                "success_loss": success.upper(),
                "failure_loss": failure.upper(),
            }
        )
    return values


def _solo_edges(text: str) -> list[int]:
    values: list[int] = []
    for match in _SOLO_EDGE_RE.finditer(text):
        value = next((item for item in match.groups() if item), None)
        if value is not None:
            values.append(int(value))
    return list(dict.fromkeys(values))


def _plain_heading(title: str) -> str:
    return title.strip().strip("*_`~").strip()


class CocModuleProfile(GenericModuleProfile):
    name = "coc7e"
    version = "3"

    def document_metadata(self, content: str) -> dict[str, object]:
        return _runtime_metadata(content)

    def classify_chunk(self, heading: str, text: str) -> str:
        folded = f"{heading}\n{text}".casefold()
        if any(signal in folded for signal in _TAGS["handout"]):
            return "handout"
        if any(signal in folded for signal in _TAGS["clue"]):
            return "clue"
        return super().classify_chunk(heading, text)

    def keywords(self, title: str, text: str) -> list[str]:
        values = super().keywords(title, text)
        folded = f"{title}\n{text}".casefold()
        for tag, signals in _TAGS.items():
            if any(signal in folded for signal in signals):
                values.append(tag)
        return list(dict.fromkeys(values))

    def scene_boundaries(
        self,
        chapter_title: str,
        chapter_content: str,
    ) -> list[SceneBoundary]:
        headings = list(re.finditer(r"^(#{1,6})\s+(.+?)\s*$", chapter_content, re.MULTILINE))
        solo_headings = []
        for heading in headings:
            match = _SOLO_NODE_RE.fullmatch(_plain_heading(heading.group(2)))
            if match is not None:
                solo_headings.append((heading, match))
        solo_edges = 0
        for index, (heading, _match) in enumerate(solo_headings):
            end = (
                solo_headings[index + 1][0].start()
                if index + 1 < len(solo_headings)
                else len(chapter_content)
            )
            solo_edges += bool(_solo_edges(chapter_content[heading.start() : end]))
        if len(solo_headings) >= 10 and solo_edges >= max(3, len(solo_headings) // 10):
            return self._solo_boundaries(
                chapter_title,
                chapter_content,
                solo_headings,
            )

        handout_headings = [heading for heading in headings if _HANDOUT_RE.search(heading.group(2))]
        if handout_headings and len(handout_headings) >= max(2, len(headings) // 2):
            return self._handout_boundaries(
                chapter_title,
                chapter_content,
                handout_headings,
            )
        return self._scenario_boundaries(chapter_title, chapter_content, headings)

    def _scenario_boundaries(
        self,
        chapter_title: str,
        content: str,
        headings: list[re.Match[str]],
    ) -> list[SceneBoundary]:
        counts = {
            level: sum(len(match.group(1)) == level for match in headings) for level in (2, 3, 4)
        }
        if counts[2] and counts[3] >= counts[2] * 5:
            scene_level = 3
        elif counts[2]:
            scene_level = 2
        elif counts[3]:
            scene_level = 3
        else:
            scene_level = 4
        sub_level = scene_level + 1 if scene_level < 6 else None
        scene_headings = [heading for heading in headings if len(heading.group(1)) == scene_level]
        chapter_reference = any(signal in chapter_title.casefold() for signal in _REFERENCE_SIGNALS)
        if not scene_headings:
            return [
                self._boundary(
                    chapter_title,
                    content,
                    0,
                    len(content),
                    scene_level,
                    [],
                    reference=chapter_reference,
                )
            ]

        boundaries: list[SceneBoundary] = []
        first_start = scene_headings[0].start()
        if content[:first_start].strip():
            title = _preamble_title(content[:first_start], chapter_title)
            boundaries.append(
                self._boundary(
                    title,
                    content,
                    0,
                    first_start,
                    scene_level,
                    [],
                    reference=True,
                )
            )
        for index, heading in enumerate(scene_headings):
            end = (
                scene_headings[index + 1].start()
                if index + 1 < len(scene_headings)
                else len(content)
            )
            subsections = self._subsections(
                headings,
                heading.start(),
                end,
                sub_level,
                content,
            )
            boundaries.append(
                self._boundary(
                    heading.group(2).strip(),
                    content,
                    heading.start(),
                    end,
                    scene_level,
                    subsections,
                    reference=chapter_reference,
                )
            )
        return boundaries

    def _handout_boundaries(
        self,
        chapter_title: str,
        content: str,
        headings: list[re.Match[str]],
    ) -> list[SceneBoundary]:
        boundaries: list[SceneBoundary] = []
        first_start = headings[0].start()
        if content[:first_start].strip():
            boundaries.append(
                self._boundary(
                    _preamble_title(content[:first_start], chapter_title),
                    content,
                    0,
                    first_start,
                    len(headings[0].group(1)),
                    [],
                    reference=True,
                )
            )
        for index, heading in enumerate(headings):
            end = headings[index + 1].start() if index + 1 < len(headings) else len(content)
            boundaries.append(
                self._boundary(
                    heading.group(2).strip(),
                    content,
                    heading.start(),
                    end,
                    len(heading.group(1)),
                    [],
                    forced_type="handout",
                )
            )
        return boundaries

    def _solo_boundaries(
        self,
        chapter_title: str,
        content: str,
        headings: list[tuple[re.Match[str], re.Match[str]]],
    ) -> list[SceneBoundary]:
        boundaries: list[SceneBoundary] = []
        first_start = headings[0][0].start()
        if content[:first_start].strip():
            boundaries.append(
                self._boundary(
                    _preamble_title(content[:first_start], chapter_title),
                    content,
                    0,
                    first_start,
                    len(headings[0][0].group(1)),
                    [],
                    reference=True,
                )
            )
        for index, (heading, node_match) in enumerate(headings):
            end = headings[index + 1][0].start() if index + 1 < len(headings) else len(content)
            node_text = content[heading.start() : end]
            boundary = self._boundary(
                node_match.group(1),
                content,
                heading.start(),
                end,
                len(heading.group(1)),
                [],
                forced_type="solo_node",
            )
            boundaries.append(
                SceneBoundary(
                    boundary.title,
                    boundary.start,
                    boundary.end,
                    {
                        **boundary.metadata,
                        "node_id": int(node_match.group(1)),
                        "transitions": _solo_edges(node_text),
                    },
                )
            )
        return boundaries

    def _boundary(
        self,
        title: str,
        content: str,
        start: int,
        end: int,
        scene_level: int,
        subsections: list[dict[str, object]],
        *,
        reference: bool = False,
        forced_type: str | None = None,
    ) -> SceneBoundary:
        text = content[start:end]
        scene_type = forced_type or _scene_type(title, text, reference=reference)
        clues = [item for item in subsections if item["type"] in {"clue", "core_clue"}]
        checks = [
            {
                "title": item["title"],
                "line": item["line"],
                "difficulty": _difficulty(str(item["title"])),
            }
            for item in subsections
            if item["type"] in {"check", "sanity_check"}
        ]
        return SceneBoundary(
            title,
            start,
            end,
            {
                "scene_type": scene_type,
                "scene_level": scene_level,
                "visibility": _visibility(scene_type, text),
                "subsections": subsections,
                "headings": [str(item["title"]) for item in subsections],
                "tags": [
                    tag
                    for tag, signals in _TAGS.items()
                    if any(signal in f"{title}\n{text}".casefold() for signal in signals)
                ],
                "clues": clues,
                "checks": checks,
                "sanity": _sanity_expressions(text),
                "transitions": [],
                "line_count": max(
                    1,
                    _line_number(content, end) - _line_number(content, start) + 1,
                ),
            },
        )

    @staticmethod
    def _subsections(
        headings: list[re.Match[str]],
        start: int,
        end: int,
        sub_level: int | None,
        content: str,
    ) -> list[dict[str, object]]:
        if sub_level is None:
            return []
        return [
            {
                "title": heading.group(2).strip(),
                "line": _line_number(content, heading.start()),
                "type": _subsection_type(heading.group(2)),
            }
            for heading in headings
            if start < heading.start() < end and len(heading.group(1)) == sub_level
        ]
