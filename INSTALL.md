# 安装引导 — SagaSmith CoC

Agent 请按此流程安装。

## 前置检查

```powershell
sagasmith-coc doctor --json 2>nul
```

如果返回 `{"status":"ok"}` → ✅ **已安装**，直接加载 skill。

## 安装完整运行时

如果未安装，先装 Python 包：

```bash
pip install "sagasmith-coc[documents]"
```

验证：

```bash
sagasmith-coc doctor --json
```

完整版 skill 在 `SagaSmith-coc-skills` 仓库的 **main** 分支：
`https://github.com/SagaSmithAI/SagaSmith-coc-skills/tree/main`

Agent 加载 `skills/coc7-keeper/SKILL.md`。

CoC 无捆绑规则书。用户需自行导入合法持有的规则 PDF。

## Standalone 轻量模式

如果当前环境无法安装 Python 包（无 pip、无 Python 3.11+），使用 standalone 分支：

`https://github.com/SagaSmithAI/SagaSmith-coc-skills/tree/standalone`

Agent 直接加载根目录的 `SKILL.md`。

Standalone 模式使用 `tools/portable.py`（纯标准库，零依赖），数据存 `~/.sagasmith/`。
不支持 PDF 导入、FTS5 检索、ChromaDB。需要 PDF 时请用户先转为 Markdown。
