# SagaSmith CoC 7e Full Runtime

[中文](README.md) · [English](README-en.md) · [Repository](../README-en.md)

Full Runtime operates through sagasmith-coc-mcp and never calls a CLI or a
portable fallback under full/tools. Load SKILL.md, then the task-specific Keeper
or Campaign Manager child Skill.

Startup order:

1. server_capabilities and storage_status;
2. campaign_query;
3. exposure open/search/set;
4. refresh native tools after tools/list_changed;
5. read current campaign, phase, branch, scene, character, and continuity state.

See references/mcp-contract.md for the native surface,
references/workflows.md for ordered flows, and
references/memory-ownership.md for continuity ownership.

Private user sources and Pack archives remain local by default.
