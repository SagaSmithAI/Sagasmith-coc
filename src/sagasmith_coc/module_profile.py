"""CoC scenario enrichment for the generic module parser."""

from __future__ import annotations

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
        return "player"
    if text.lstrip().startswith(">"):
        return "read_aloud"
    return "keeper"


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
    version = "2"

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
        headings = list(
            re.finditer(r"^(#{1,6})\s+(.+?)\s*$", chapter_content, re.MULTILINE)
        )
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

        handout_headings = [
            heading for heading in headings if _HANDOUT_RE.search(heading.group(2))
        ]
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
            level: sum(len(match.group(1)) == level for match in headings)
            for level in (2, 3, 4)
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
        scene_headings = [
            heading for heading in headings if len(heading.group(1)) == scene_level
        ]
        chapter_reference = any(
            signal in chapter_title.casefold() for signal in _REFERENCE_SIGNALS
        )
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
        clues = [
            item
            for item in subsections
            if item["type"] in {"clue", "core_clue"}
        ]
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
