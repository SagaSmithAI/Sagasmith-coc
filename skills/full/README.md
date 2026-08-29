# SagaSmith CoC 7e Full Runtime

[中文](README.md) · [English](README-en.md) · [仓库说明](../README.md)

> 这是 `sagasmith-coc/skills/full` 的同仓分发，不是独立仓库。

Full Runtime 通过 sagasmith-coc-mcp 运行，绝不调用 CLI 或 full/tools 下的
portable fallback。入口是 SKILL.md；Keeper 与 Campaign Manager 子 Skill
按任务加载。

现代启动顺序：

1. 可选 `server/discover`，并在每个请求携带版本、能力和签名身份；
2. `server_capabilities`、`storage_status` 与 `campaign_query`；
3. 从确定排序的完整目录选择任务/角色/阶段 facade，默认最多向模型展示 16 项；
4. 需要目录导航时使用有 owner/TTL 的 `exposure_handle`；
5. 读取当前 campaign、phase、branch、scene、character 与 continuity。

目录不会因阶段或调用副作用改变，MCP 每次调用仍重新校验权限、阶段与 revision。
`tools/list_changed` 只属于显式 legacy 兼容路径。

详细工具契约见 references/mcp-contract.md，顺序流程见
references/workflows.md，连续性权责见 references/memory-ownership.md。

用户私有来源与 Pack 默认只保存在本地。
