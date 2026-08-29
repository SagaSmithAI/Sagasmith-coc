# SagaSmith CoC 7e Skills

[中文](README.md) · [English](README-en.md) · [官网](https://sagasmithai.github.io) · [平台总览](https://github.com/SagaSmithAI/.github/blob/main/profile/README.md) · [SagaSmith Web](https://github.com/SagaSmithAI/SagaSmith-Web) · [内容目录](https://github.com/SagaSmithAI/SagaSmith-dnd-content-library)

> 当前 Skill 源码位于 `sagasmith-coc/skills`；原独立 Skills 与通用 Module Generator 仓库已归档。

面向 SagaSmith Call of Cthulhu 7e 的 Agent Skills。Full Runtime 使用
sagasmith-coc-mcp 的原生工具与 Host 端有界投影，覆盖调查、线索、Luck/Push、SAN、伤害、
战斗、追逐、成长、Content Pack、连续性、角色知识、分支与 Snapshot。

## 两个明确分开的分发

| 分发 | 入口 | 边界 |
|---|---|---|
| Full Runtime | full/SKILL.md | 权威 MCP 状态、逐请求权限、随机流、修订、幂等与稳定工具目录 |
| Standalone | standalone/SKILL.md | 独立的文件型演示子集，不具备 Full 的事务与权限保证 |

Full Runtime 不会在 MCP 不可用时静默退回 CLI 或 portable.py。

## Full Runtime 安装

在同一 Python 3.11+ 环境中安装：

~~~powershell
pip install -e "..\sagasmith-core[documents]"
pip install -e ..\sagasmith-coc
pip install -e packages/mcp
~~~

配置并启动 sagasmith-coc-mcp，再把 `skills/full/skills` 和仓内
`skills/coc-module-generator` 作为 Skill 根目录提供给 Host。现代 Host 从确定排序的完整目录
按任务、角色和阶段选择小型 facade（SagaSmith 默认最多 16 项），但 MCP 每次执行仍重新校验
权限、阶段和 revision。legacy Host 只在显式兼容模式下依赖 `tools/list_changed`。

## 权责边界

- Core：系统中立持久化、文档、检索、分支、快照和事务。
- sagasmith-coc：确定性 CoC 规则、角色/Statblock schema、模组解析和 Pack 验证。
- MCP：权威状态、逐请求授权、随机流、修订、幂等、结算和稳定目录。
- Agent/Skills：来源解释、感知/理解/受众、线索含义、NPC 决策、叙事和 Pack 审阅。

商业规则书和模组不随本项目分发。用户私有 PDF、提取文本、页面渲染与 Pack
默认只保存在本地。

## 验证

~~~powershell
python skills\scripts\validate_skill.py skills
~~~

原创 Skill 内容使用 Apache License 2.0。Call of Cthulhu 及商业内容归各自
权利人所有。
