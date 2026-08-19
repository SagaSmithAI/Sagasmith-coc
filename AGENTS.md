# SagaSmith CoC Agent Guide

## Repository boundary

This is the current vertical source repository for Call of Cthulhu 7e:

- `packages/domain` owns deterministic CoC mechanics and canonical schemas.
- `packages/mcp` owns authoritative state, authorization, revisions, random
  streams, idempotency, settlement, and session-scoped tool exposure.
- `skills` owns reusable Keeper/Agent procedures and scenario authoring review.
- `apps/ui` is the CoC Workbench and uses the authenticated sticky-session
  gateway rather than direct database or caller-selected principal access.

The former standalone CoC MCP, Skills, UI, and generic Module Generator
repositories are archived. Do not restore them as dependencies, mirrors,
fallbacks, or documentation authorities.

## Placement rules

- Keep source interpretation, clue meaning, perception, audience, NPC choice,
  and scenario-specific truth in Agent/Skills or Pack evidence.
- Put only reusable deterministic CoC mechanics in `packages/domain`.
- Put authoritative writes and call-time permission checks in `packages/mcp`.
- Preserve dynamic native tool exposure and `tools/list_changed`; never ship a
  fixed superset or silent CLI/portable fallback for Full Runtime.
- Do not add one-book parser heuristics to Domain or MCP. Repair source-specific
  truth in the draft Pack and preserve its evidence.

## Validation

```powershell
uv sync --all-packages --all-extras
uv run --package sagasmith-coc pytest packages/domain/tests
uv run --package sagasmith-coc-mcp pytest packages/mcp/tests
uv run ruff check packages/domain packages/mcp
npm ci
npm run test:ui
npm run build:ui
```

Run checks proportional to the change and add a real public-facade integration
path whenever a cross-component contract changes.
