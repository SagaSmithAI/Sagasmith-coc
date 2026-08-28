from __future__ import annotations

import re
from pathlib import Path

from sagasmith_coc_mcp.tool_profiles import CORE_TOOLS, PHASE_TOOLS

REFERENCE = Path(__file__).parents[3] / "skills" / "full" / "references" / "mcp-contract.md"


def _section(reference: str, heading: str, next_heading: str) -> str:
    return reference.split(heading, 1)[1].split(next_heading, 1)[0]


def test_skill_reference_core_tools_match_runtime_policy() -> None:
    reference = REFERENCE.read_text(encoding="utf-8")
    section = _section(
        reference,
        "## Always-visible tools",
        "## Complete public tool inventory",
    )
    documented = re.findall(r"^\| ([a-z][a-z0-9_]*) \|", section, flags=re.MULTILINE)

    assert f"The {len(CORE_TOOLS)} bootstrap tools are visible" in section
    assert len(documented) == len(CORE_TOOLS)
    assert set(documented) == set(CORE_TOOLS)


def test_skill_reference_public_inventory_matches_runtime_policy() -> None:
    reference = REFERENCE.read_text(encoding="utf-8")
    section = _section(
        reference,
        "## Complete public tool inventory",
        "## Phase catalog",
    )
    inventory = section.split("~~~text", 1)[1].split("~~~", 1)[0]
    documented = re.findall(r"\b[a-z][a-z0-9_]*\b", inventory)
    runtime = set(CORE_TOOLS).union(*(set(tools) for tools in PHASE_TOOLS.values()))

    assert f"CORE tools are the {len(CORE_TOOLS)} bootstrap tools above." in section
    assert len(documented) == len(runtime)
    assert set(documented) == runtime
