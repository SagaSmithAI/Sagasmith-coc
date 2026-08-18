"""Call of Cthulhu-owned vocabulary for multilingual retrieval."""

from __future__ import annotations

from collections.abc import Sequence

COC7E_QUERY_HINTS: dict[str, Sequence[str]] = {
    "检定": ("check", "roll", "test"),
    "属性": ("characteristic", "stat"),
    "技能": ("skill",),
    "困难": ("hard", "difficulty"),
    "极难": ("extreme", "difficulty"),
    "孤注一掷": ("pushed", "push", "roll"),
    "幸运": ("luck",),
    "理智": ("sanity", "san"),
    "疯狂": ("insanity", "madness"),
    "伤害": ("damage", "wound", "hurt"),
    "治疗": ("heal", "healing", "first aid", "medicine"),
    "武器": ("weapon", "firearm"),
    "骰子": ("dice", "roll"),
    "线索": ("clue", "hint", "evidence"),
    "证据": ("evidence", "clue"),
    "战斗": ("combat", "fight"),
    "追逐": ("chase", "pursuit"),
    "调查员": ("investigator",),
    "守秘人": ("keeper",),
    "神话": ("mythos", "cthulhu"),
    "法术": ("spell", "magic"),
    "典籍": ("tome", "book"),
    "怪物": ("monster", "creature"),
    "回合": ("turn", "round"),
    "移动": ("move", "movement"),
    "搜索": ("search", "investigate", "explore"),
    "隐藏": ("hidden", "secret", "conceal"),
}

__all__ = ["COC7E_QUERY_HINTS"]
