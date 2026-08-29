from __future__ import annotations

import re
import sys
from pathlib import Path


SKILLS = {
    "full/SKILL.md": "sagasmith-coc-suite",
    "full/skills/coc7-keeper/SKILL.md": "coc7-keeper",
    "full/skills/coc7-campaign-manager/SKILL.md": "coc7-campaign-manager",
}

REQUIRED = {
    *SKILLS,
    "full/agents/openai.yaml",
    "full/skills/coc7-keeper/agents/openai.yaml",
    "full/skills/coc7-campaign-manager/agents/openai.yaml",
    "full/references/mcp-contract.md",
    "full/references/workflows.md",
    "full/references/memory-ownership.md",
    "full/skills/coc7-campaign-manager/references/CAMPAIGN_MANAGER_DEEP_REFERENCE.md",
    "full/skills/coc7-keeper/references/KEEPER_RULES.md",
    "full/skills/coc7-keeper/references/INVESTIGATION.md",
    "full/skills/coc7-keeper/references/SANITY.md",
    "full/skills/coc7-keeper/references/COMBAT_CHASE.md",
    "full/skills/coc7-keeper/references/INVESTIGATOR_CREATION.md",
    "full/skills/coc7-keeper/references/SCENARIO_INDEX.md",
}

TOOLS = {
    "actor_knowledge_change",
    "actor_knowledge_query",
    "bounded_evaluation",
    "branch_change",
    "branch_query",
    "campaign_change",
    "campaign_query",
    "campaign_event",
    "character_change",
    "character_query",
    "chase_action",
    "chase_end",
    "chase_query",
    "chase_start",
    "coc_dice_roll",
    "coc_hp_change",
    "coc_resolve",
    "coc_sanity_check",
    "combat_action",
    "combat_attack",
    "combat_end",
    "combat_query",
    "combat_start",
    "content_pack",
    "continuity_context",
    "development_query",
    "development_settle",
    "exposure",
    "game_phase",
    "group_luck_check",
    "group_luck_query",
    "investigation_check",
    "investigation_query",
    "inventory_change",
    "long_term_change",
    "memory_change",
    "memory_query",
    "module_change",
    "module_draft",
    "module_query",
    "npc_conversation",
    "playthrough_manifest",
    "rule_query",
    "rulebook_draft",
    "server_capabilities",
    "skill_query",
    "snapshot_change",
    "snapshot_query",
    "state_revision",
    "storage_status",
    "wallet_change",
}

MOJIBAKE = ("�", "鈫", "涓", "鐞", "瀹", "璋", "绾", "鎴", "妫", "锛")


def fail(message: str) -> None:
    raise SystemExit(message)


def validate_skill(path: Path, expected_name: str) -> int:
    text = path.read_text(encoding="utf-8-sig")
    if not text.startswith("---\n"):
        fail("{}: missing frontmatter".format(path))
    parts = text.split("---", 2)
    if len(parts) != 3:
        fail("{}: malformed frontmatter".format(path))
    fields = set()
    for line in parts[1].splitlines():
        match = re.match(r"^([a-z_]+):", line)
        if match:
            fields.add(match.group(1))
    if fields != {"name", "description"}:
        fail("{}: frontmatter fields must be exactly name and description".format(path))
    if not re.search(
        r"^name:\s*{}\s*$".format(re.escape(expected_name)),
        parts[1],
        re.MULTILINE,
    ):
        fail("{}: unexpected skill name".format(path))
    lines = len(text.splitlines())
    if lines > 500:
        fail("{}: {} lines exceeds the 500-line budget".format(path, lines))
    return lines


def validate_links(root: Path, path: Path, text: str) -> None:
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        target = target.split("#", 1)[0]
        if not target or "://" in target or target.startswith("#"):
            continue
        resolved = (path.parent / target).resolve()
        try:
            resolved.relative_to(root.resolve())
        except ValueError:
            fail("{}: link escapes repository: {}".format(path, target))
        if not resolved.exists():
            fail("{}: broken link: {}".format(path, target))


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    missing = sorted(item for item in REQUIRED if not (root / item).is_file())
    if missing:
        fail("missing required files: " + ", ".join(missing))
    if (root / "full" / "tools" / "portable.py").exists():
        fail("Full Runtime must not include a portable fallback")
    if (root / "full" / "references" / "cli-contract.md").exists():
        fail("Full Runtime must not include the superseded CLI contract")

    counts = {
        name: validate_skill(root / relative, name)
        for relative, name in SKILLS.items()
    }

    full_files = [
        path
        for path in (root / "full").rglob("*")
        if path.is_file() and path.suffix.casefold() in {".md", ".yaml"}
    ]
    for path in full_files:
        text = path.read_text(encoding="utf-8-sig")
        if path.suffix.casefold() == ".md":
            validate_links(root, path, text)
        if "sagasmith-coc --json" in text or "python tools/portable.py" in text:
            fail("{}: Full Runtime contains a CLI/portable fallback".format(path))
        if any(marker in text for marker in MOJIBAKE):
            fail("{}: likely mojibake marker found".format(path))

    contract = (root / "full" / "references" / "mcp-contract.md").read_text(
        encoding="utf-8-sig"
    )
    missing_tools = sorted(tool for tool in TOOLS if tool not in contract)
    if missing_tools:
        fail("MCP contract missing tools: " + ", ".join(missing_tools))
    if len(TOOLS) != 51:
        fail("validator public tool catalog must contain exactly 51 tools")

    metadata = list((root / "full").rglob("agents/openai.yaml"))
    if len(metadata) != 3:
        fail("expected agents/openai.yaml for the suite and both child Skills")
    for path in metadata:
        text = path.read_text(encoding="utf-8-sig")
        for marker in ('display_name: "', 'short_description: "', 'default_prompt: "Use $'):
            if marker not in text:
                fail("{}: missing interface marker {}".format(path, marker))

    print(
        "validated CoC Full Skills: {} tools; {}".format(
            len(TOOLS),
            ", ".join("{}={} lines".format(name, count) for name, count in counts.items()),
        )
    )


if __name__ == "__main__":
    main()
