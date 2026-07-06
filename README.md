# 🕯️ SagaSmith CoC

[中文](README.md) | [English](README-en.md)

**Call of Cthulhu 7e 运行时** — 为 `sagasmith-core` 提供 CoC 7e 系统插件与便携 JSON CLI。

> *"宇宙不关心你的调查员。我们关心。"*

`sagasmith-coc` 在 `sagasmith-core` 之上注册 `coc7e` 系统 profile。它不包含商业规则书，也不绑定 Agent 平台——Agent 平台通过 `SagaSmith-coc-skills` 调用同一 `sagasmith-coc --json` CLI。用户可将自己合法持有的 PDF/Markdown 导入运行时。

---

## 生态

| 仓库 | 定位 |
|------|------|
| 🕯️ **sagasmith-coc**（本仓库） | CoC 7e 系统插件 + CLI |
| 🏗️ [sagasmith-core](https://github.com/dajiaohuang/sagasmith-core) | 通用引擎 — DB、文档、RAG |
| 🎲 [SagaSmith-agent](https://github.com/dajiaohuang/SagaSmith-agent) | 完整 AI DM 运行时 |
| 📦 [SagaSmith-coc-skills](https://github.com/dajiaohuang/SagaSmith-coc-skills) | CoC Agent Skill 定义 |

---

## 功能

- 🕯️ **战役管理** — 调查团创建、调查员管理、规则集/模组绑定、事件日志
- 👤 **调查员** — Classic/Pulp 双版属性面板验证，技能、职业、资产、伴
- 🎲 **规则引擎** — d100/对抗检定、成功等级、孤注一掷、奖励/惩罚骰
- 🧠 **SAN 与疯狂** — 理智检定、临时/ indefinite 疯狂、恐惧/狂躁症
- ⚔️ **战斗与追逐** — 近战/远程回合制、追逐轮次、动作/反应
- 📖 **模组** — PDF/Markdown 导入、三种解析模式：常规调查、单人模组（编号节点 + 跳转边）、资料包（handout）
- 🔍 **场景元数据** — `scene_type`（investigation / social / combat / chase / travel / reference / handout / solo_node）、`visibility`（keeper / player / read_aloud）、线索、检定、SAN 表达式、跳转边
- 🧩 **场景进度** — 作用域式追踪（`party` / `group:<id>` / `player:<id>`），从 party 透明继承
- 💾 **Snapshot** — DAG 存档树，支持调查团分支读档

---

## 快速开始

```bash
# 安装
pip install "sagasmith-coc[documents]"

# 检查运行时健康状况
sagasmith-coc doctor --json

# 创建调查团
sagasmith-coc campaign start --name "阿卡姆" --json

# 导入规则
sagasmith-coc rules ingest --path ./rulebooks --publication "CoC 7e Keeper Rulebook" --locale zh --json

# 检查模组结构
sagasmith-coc module inspect --path ./scenario.pdf --json

# 导入模组
sagasmith-coc module ingest --campaign <id> --path ./scenario.pdf --json

# 查看场景索引（含 scene_type、visibility、clues、checks、sanity）
sagasmith-coc module index --campaign <id> --json

# 查询当前场景
sagasmith-coc module current --campaign <id> --scope party --json

# 更新进度
sagasmith-coc module set-progress --campaign <id> --scope player:herbert --scene <scene-id> --progress 30 --state '{"discovered_clues":["染血手记"]}' --json

# 创建调查员
sagasmith-coc investigator create --campaign <id> --name "赫伯特·韦斯特" --occupation "医生" --str 50 --con 60 --siz 65 --dex 55 --app 45 --int 80 --pow 70 --edu 75 --json

# d100 检定
sagasmith-coc check --campaign <id> --skill "图书馆使用" --score 65 --difficulty hard --json

# SAN 检定
sagasmith-coc sanity --campaign <id> --loss "1/1D6" --json
```

---

## CoC Profile 场景解析

`CocModuleProfile` 实现了三种解析模式，自动选择：

### 自动分类

1. **单人模组 (solo_scenario)** — 检测编号段落（`## **1**` ~ `## **N**`）+ 显式跳转边（`→`、`Go to`、`转到`），N ≥ 10 且边数足够时触发
2. **资料包 (handout_pack)** — 检测 `HANDOUT` / `玩家资料` / `手记` 等关键词标题，占比足够时触发
3. **常规调查 (scenario)** — 默认模式，H2/H3 智能层级

### 场景元数据

| 字段 | 说明 |
|------|------|
| `scene_type` | `investigation` / `social` / `combat` / `chase` / `travel` / `reference` / `handout` / `solo_node` |
| `visibility` | `keeper`（仅守秘人）、`player`（玩家可见）、`read_aloud`（可朗读） |
| `subsections` | 子节列表，含 `type`（clue / core_clue / location / npc / creature / handout / sanity_check / check / keeper_note / timeline） |
| `clues` | 线索列表（含子节中的线索和核心线索） |
| `checks` | 检定项，含 `difficulty`（regular / hard / extreme） |
| `sanity` | SAN 表达式（保留原文，如 `0/1D4`） |
| `transitions` | solo 场景的跳转目标节点 ID |
| `node_id` | solo 场景的节点编号 |

---

## 安装 extras

| Extra | 用途 |
|-------|------|
| `dense` | sentence-transformers + ChromaDB 向量检索 |
| `documents` | PDF 解析 |
| `all` | 全部 extras |

---

## 贡献

```bash
pip install -e ".[all,dev]"
pytest --cov
ruff check .
```

---

## 致谢

- [CoC7 Foundry VTT System](https://github.com/foundryvtt-coc7/CoC7-FoundryVTT) — 数据形状与裁决覆盖的实现参考
- Call of Cthulhu 7th Edition © Chaosium Inc.

---

## 许可证

MIT
