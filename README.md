# SagaSmith Call of Cthulhu

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
