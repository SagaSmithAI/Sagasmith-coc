# 安装引导 — SagaSmith CoC

Agent 请按此流程安装。

安装入口：
`https://github.com/SagaSmithAI/SagaSmith-coc-skills`

## 前置检查

```powershell
sagasmith-coc doctor --json 2>nul
```

如果返回 `{"status":"ok"}` → ✅ **已安装**，直接加载 skill。

加载哪个 SKILL.md 由 Agent 根据环境自动选择。

## 完整版（推荐）

```bash
pip install "sagasmith-coc[documents]"
sagasmith-coc doctor --json
```

SKILL.md：`https://github.com/SagaSmithAI/SagaSmith-coc-skills/releases/tag/v1.0-full`
→ 解压后加载 `skills/coc7-keeper/SKILL.md`

CoC 无捆绑规则书。用户需自行导入合法持有的规则 PDF。

## Standalone 轻量版

如果当前环境无法安装 Python 包（无 pip、无 Python 3.11+）：

SKILL.md：`https://github.com/SagaSmithAI/SagaSmith-coc-skills/releases/tag/v1.0-standalone`
→ 解压后加载根目录 `SKILL.md` + `tools/portable.py`

使用 Python 标准库，数据存 `~/.sagasmith/`。不支持 PDF 导入、FTS5、ChromaDB。
需要 PDF 时请用户先转为 Markdown。
