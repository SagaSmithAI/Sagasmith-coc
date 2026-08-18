# SagaSmith CoC 7e Skills

[中文](README.md) · [English](README-en.md) · [Website](https://sagasmithai.github.io) · [Platform overview](https://github.com/SagaSmithAI/.github/blob/main/profile/README.md) · [Hosted service](https://github.com/SagaSmithAI/SagaSmith-service) · [Content catalog](https://github.com/SagaSmithAI/SagaSmith-dnd-content-library)

Agent Skills for SagaSmith Call of Cthulhu 7e. Full Runtime uses
sagasmith-coc-mcp native dynamic tools for investigation, clues, Luck/Push, SAN,
injury, combat, chases, development, Content Packs, continuity, ActorKnowledge,
branches, and snapshots.

## Two explicitly separate distributions

| Distribution | Entry | Boundary |
|---|---|---|
| Full Runtime | full/SKILL.md | authoritative MCP state, authorization, random streams, revisions, idempotency, and dynamic tools |
| Standalone | standalone/SKILL.md | separate file-based demo subset without Full transaction/permission guarantees |

Full Runtime never silently falls back to a CLI or portable.py.

## Install Full Runtime

Install into one Python 3.11+ environment:

~~~powershell
pip install -e "..\sagasmith-core[documents]"
pip install -e ..\sagasmith-coc
pip install -e ..\SagaSmith-coc-mcp
~~~

Configure and run sagasmith-coc-mcp, then expose full/ and
SagaSmith-module-gen-skills as Skill roots. The Host must refresh native schemas
after tools/list_changed; a Host without dynamic native tool support cannot run
Full Runtime.

Commercial rulebooks/scenarios are not distributed. Private PDFs, extracted
text, page renders, and Pack archives remain local by default.

## Validate

~~~powershell
python scripts\validate_skill.py .
~~~

Original Skill content is Apache-2.0. Call of Cthulhu and commercial content
belong to their respective rights holders.
