# SagaSmith CoC 7e Skills

[中文](README.md) · [English](README-en.md) · [Website](https://sagasmithai.github.io) · [Platform overview](https://github.com/SagaSmithAI/.github/blob/main/profile/README.md) · [SagaSmith Web](https://github.com/SagaSmithAI/SagaSmith-Web) · [Content catalog](https://github.com/SagaSmithAI/SagaSmith-dnd-content-library)

> Current Skill source lives at `sagasmith-coc/skills`; the former standalone Skills and generic Module Generator repositories are archived.

Agent Skills for SagaSmith Call of Cthulhu 7e. Full Runtime uses
sagasmith-coc-mcp native tools with bounded Host projection for investigation, clues, Luck/Push, SAN,
injury, combat, chases, development, Content Packs, continuity, ActorKnowledge,
branches, and snapshots.

## Two explicitly separate distributions

| Distribution | Entry | Boundary |
|---|---|---|
| Full Runtime | full/SKILL.md | authoritative MCP state, per-request authorization, random streams, revisions, idempotency, and a stable tool catalog |
| Standalone | standalone/SKILL.md | separate file-based demo subset without Full transaction/permission guarantees |

Full Runtime never silently falls back to a CLI or portable.py.

## Install Full Runtime

Install into one Python 3.11+ environment:

~~~powershell
pip install -e "..\sagasmith-core[documents]"
pip install -e ..\sagasmith-coc
pip install -e packages/mcp
~~~

Configure and run sagasmith-coc-mcp, expose `skills/full/skills` as the Full
Runtime root, and expose the repository-local `skills/coc-module-generator` as
the authoring Skill root. A modern Host selects a small task/role/phase facade
from the complete, deterministically sorted catalog (SagaSmith defaults to at
most 16 model-visible tools). The MCP still revalidates authorization, phase,
and revision at execution. Only the explicit legacy mode relies on
`tools/list_changed`.

## Ownership boundary

- Core owns system-neutral persistence, documents, retrieval, branches,
  snapshots, and transactions.
- Domain owns deterministic CoC rules, actor/statblock schemas, scenario parsing,
  and Pack validation.
- MCP owns authoritative state, per-request authorization, random streams,
  revisions, idempotency, and settlement.
- Agent/Skills own source interpretation, perception, audience, clue meaning,
  NPC decisions, narration, and Pack review.

Commercial rulebooks/scenarios are not distributed. Private PDFs, extracted
text, page renders, and Pack archives remain local by default.

## Validate

~~~powershell
python skills\scripts\validate_skill.py skills
~~~

Original Skill content is Apache-2.0. Call of Cthulhu and commercial content
belong to their respective rights holders.
