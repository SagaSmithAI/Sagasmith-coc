# SagaSmith CoC 7e Full Runtime

[中文](README.md) · [English](README-en.md) · [Repository](../README-en.md)

> This is the repository-local `sagasmith-coc/skills/full` distribution, not a standalone repository.

Full Runtime operates through sagasmith-coc-mcp and never calls a CLI or a
portable fallback under full/tools. Load SKILL.md, then the task-specific Keeper
or Campaign Manager child Skill.

Modern startup order:

1. optionally call `server/discover`, then carry version, capabilities, and
   signed identity on every request;
2. call `server_capabilities`, `storage_status`, and `campaign_query`;
3. select a task/role/phase facade from the complete deterministic catalog,
   exposing at most 16 tools to the model by default;
4. use an owner/TTL-bound `exposure_handle` only when catalog navigation helps;
5. read current campaign, phase, branch, scene, character, and continuity state.

The catalog does not mutate because phase or tool side effects changed. The MCP
still revalidates authorization, phase, and revision on every call.
`tools/list_changed` belongs only to the explicit legacy compatibility path.

See references/mcp-contract.md for the native surface,
references/workflows.md for ordered flows, and
references/memory-ownership.md for continuity ownership.

Private user sources and Pack archives remain local by default.
