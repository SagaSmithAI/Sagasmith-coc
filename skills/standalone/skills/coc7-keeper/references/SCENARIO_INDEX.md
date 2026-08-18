# 场景索引与解析

PDF 到 Markdown、页码溯源、通用入库和检索块由 `sagasmith-core` 负责。
`sagasmith-coc` 的 CoC profile 将 Markdown 解释为调查场景。

## 文档角色

- `scenario`：常规守秘人模组。
- `solo_scenario`：以编号段落和跳转选择组成的单人模组。
- `handout_pack`：信件、剪报、照片、地图和记录。
- `rules`：规则参考，不作为可推进场景。
- `mixed`：规则、模组和附件混合；各区域必须分开处理。

## 导入

```powershell
sagasmith-coc module inspect --path "<scenario.pdf>" --json
sagasmith-coc module ingest --campaign <id> --path "<scenario.pdf>" --json
sagasmith-coc module index --campaign <id> --json
sagasmith-coc module current --campaign <id> --scope <scope> --json
```

先检查 `inspect` 的 warnings 和结构计数。出现以下情况时停止自动开团并报告：

- 整本模组只有一个 scene；
- solo 模组未拆出 numbered nodes；
- handout pack 未拆成独立 handout；
- 规则章节被标为可推进调查场景；
- scene/chunk 缺失页码；
- 无法安全区分玩家文本与 Keeper 信息。

## Scene index 字段

每个 scene 包含：

- `scene_type`：`investigation`、`social`、`combat`、`chase`、`travel`、
  `downtime`、`reference`、`handout` 或 `solo_node`；
- `visibility`：Core canonical `restricted`、`group` 或 `public`；
- 起止行、起止页、heading path；
- `subsections`：location、clue、core_clue、NPC、creature、handout、
  timeline、check、sanity_check 等；
- `clues`、`checks`、`sanity`、`transitions` 和 tags；
- solo node 的 `node_id` 与显式跳转目标。

只能依赖源文档中明确写出的难度、SAN 表达式和跳转关系；不得补写缺失规则或失败后果。

## 运行

`scope` 使用 `party`、`group:<id>` 或 `player:<character-id>`。个人 scope 在未独立推进前
继承 party scene；单独调查、被隔离、梦境、疯狂发作和 solo node 均应切到个人 scope。

每次处理调查员行动：

1. 调用 `module current --scope ...`，再 `read-scene`。若没有 current，才从 index
   选择 scene；跳过 `reference`。
2. 当前 scene 缺信息时用 search 定位候选，expand 后再使用。不得把相似检索结果当成
   当前地点，也不得读取其他 scope 的私人发现。
3. 按字段执行：
   - `reference` 只供 Keeper 备课，不作为 current scene；
   - `visibility=restricted` 不可朗读，`public` 可公开呈现，`group` 仅向授权小组呈现；
   - `clues`/`core_clue` 只表示可获取线索，必须满足原文获取方式后才能发现；
   - `checks`/`sanity` 只在原文触发条件出现时调用规则引擎，不自动掷骰；
   - `transitions` 只表示合法候选，不替玩家作选择。
4. 先读取当前 state，合并后整体写回，不能删除未知键。建议结构：

```json
{
  "discovered_clues": [],
  "revealed_handouts": [],
  "visited_subsections": [],
  "resolved_checks": [],
  "triggered_timeline": [],
  "keeper_flags": [],
  "selected_transition": null
}
```

5. 线索只写入发现者或共享小组的 scope；线索被交流后再复制到接收 scope，并写
   discovery event。客观世界变化另写 event/memory，避免与人物认知混为一谈。
6. 输出 handout 时只使用玩家可见内容，不得连带 Keeper 注释。solo 模组只沿当前
   node 的显式 transition 推进；先验证目标存在，再把当前 node 标为 completed。
7. 离开场景时把旧 scene 设为 `completed`/100，再把新 scene 设为 `current`。
   重大揭示、分队重合或章节切换时创建 Snapshot。
