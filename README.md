# SagaSmith Call of Cthulhu

[Domain](packages/domain/README.md) · [MCP](packages/mcp/README.md) ·
[Skills](skills/README.md) · [Workbench](apps/ui/README.md) ·
[Platform](https://github.com/SagaSmithAI/.github/blob/main/profile/README.md)

SagaSmith CoC is the vertical monorepo for Call of Cthulhu 7th Edition. It
versions the deterministic domain package, authoritative MCP server, Agent
Skills, gateway, and UI together while preserving their independent runtime
and distribution boundaries.

## Repository layout

```text
packages/domain/              sagasmith-coc Python package and CLI
packages/mcp/                 sagasmith-coc-mcp server and gateway
apps/ui/                      CoC workbench
skills/                       Keeper and campaign procedures
skills/coc-module-generator/  CoC Pack authoring procedure
```

`sagasmith-core` remains an independent system-neutral dependency. D&D and CoC
have no source dependency on each other.

This repository is the current source of truth for every CoC component listed
above. The former standalone MCP, Skills, UI, and generic Module Generator
repositories are archived read-only; current issues, releases, integrations,
and documentation belong here.

## Local Agent Kit install profiles

The CoC-only text MCP does not require PDF, image, embedding, or vector stacks:

```bash
pip install sagasmith-coc-mcp
sagasmith-coc-mcp
```

That baseline provides SQLite state, Markdown/text content, FTS retrieval, and
the native MCP contract. Optional profiles are explicit:

```bash
pip install "sagasmith-coc-mcp[documents]"  # PDF text and page handling
pip install "sagasmith-coc-mcp[images]"     # visual PDF page review
pip install "sagasmith-coc-mcp[dense]"      # Domain embedding/vector stack
pip install "sagasmith-coc-mcp[all]"        # every implemented optional profile
```

The current CoC importer has no OCR execution path, so this repository does not
advertise a misleading `ocr` extra; scanned sources must first receive a legal,
reviewable text layer. Cross-system Local Agent Kit manifests remain owned by
`SagaSmith-agent`; this vertical repository owns only the CoC package/extras
contract.

## Verified integration baseline

The 2026-08-20 hosted regression uses the current SagaSmith Agent and Service,
signed `sagasmith.auth-context/v1` principal context, session-scoped dynamic MCP
tools, and this repository's Domain/MCP/Skills revision. The CoC reference
campaign ran concurrently with the D&D reference campaign without a reported
regression gap. This is evidence for the current hosted integration boundary,
not a claim that every scenario or mutually exclusive path has been played.

## Development

```bash
uv sync --all-packages --all-extras
uv run --package sagasmith-coc pytest packages/domain/tests
uv run --package sagasmith-coc-mcp pytest packages/mcp/tests
uv run ruff check packages/domain packages/mcp

npm ci
npm run build:ui
```

Package-specific documentation remains under `packages/domain`, `packages/mcp`,
`skills`, and `apps/ui`.
