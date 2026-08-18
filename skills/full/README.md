# SagaSmith CoC 7e Full Runtime

[中文](README.md) · [English](README-en.md) · [仓库说明](../README.md)

Full Runtime 通过 sagasmith-coc-mcp 运行，绝不调用 CLI 或 full/tools 下的
portable fallback。入口是 SKILL.md；Keeper 与 Campaign Manager 子 Skill
按任务加载。

启动顺序：

1. server_capabilities 与 storage_status；
2. campaign_query；
3. exposure open/search/set；
4. 刷新 tools/list_changed 后的原生工具；
5. 读取当前 campaign、phase、branch、scene、character 与 continuity。

详细工具契约见 references/mcp-contract.md，顺序流程见
references/workflows.md，连续性权责见 references/memory-ownership.md。

用户私有来源与 Pack 默认只保存在本地。
