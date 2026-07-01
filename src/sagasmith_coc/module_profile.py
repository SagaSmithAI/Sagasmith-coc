"""CoC scenario enrichment for the generic module parser."""

from __future__ import annotations

from sagasmith_core.modules import GenericModuleProfile

_TAGS = {
    "clue": ("clue", "线索", "证据"),
    "handout": ("handout", "玩家资料", "手记", "剪报"),
    "sanity": ("san loss", "sanity", "理智损失", "san 检定"),
    "mythos": ("mythos", "克苏鲁神话", "神话"),
    "npc": ("npc", "人物", "调查员"),
    "location": ("location", "地点", "场景"),
    "timeline": ("timeline", "时间线"),
}


class CocModuleProfile(GenericModuleProfile):
    name = "coc7e"
    version = "1"

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
