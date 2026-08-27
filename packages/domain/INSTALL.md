# 安装引导 — SagaSmith CoC

Agent 请按此流程安装。

安装入口：
`https://github.com/SagaSmithAI/sagasmith-coc/tree/main/skills`

## 前置检查

```powershell
sagasmith-coc doctor --json 2>nul
```

如果返回 `{"status":"ok"}` → ✅ **已安装**，直接加载 skill。

加载哪个 SKILL.md 由 Agent 根据环境自动选择。

## 基础文字版（推荐起点）

```bash
pip install sagasmith-coc
sagasmith-coc doctor --json
```

SKILL.md：`https://github.com/SagaSmithAI/sagasmith-coc/tree/main/skills/full`
→ 加载 `full/SKILL.md`

CoC 无捆绑规则书。用户需自行导入合法持有的规则 PDF。

基础版支持 SQLite、FTS、Markdown/text 和普通文字团，不安装 PDF、Pillow、
ChromaDB、Sentence Transformers 或 Torch。需要 PDF 时按需安装：

```bash
pip install "sagasmith-coc[documents]"
```

安装后询问用户是否启用 ChromaDB：

```powershell
# 安装 ChromaDB + sentence-transformers（向量语义搜索，~2GB）
pip install "sagasmith-coc[dense]"

# 设存储路径后启用
$env:CHROMA_DB_PATH = "$env:APPDATA\sagasmith\chroma_db"
```

不装也不影响基础功能（FTS5 全文检索 + 词法搜索已可用）。当前 CoC 运行时
没有 OCR 路径；扫描件须先生成可复核文本层。

## Standalone 轻量版

如果当前环境无法安装 Python 包（无 pip、无 Python 3.11+）：

SKILL.md：`https://github.com/SagaSmithAI/sagasmith-coc/tree/main/skills/standalone`
→ 从 `standalone/` 目录操作，加载 `standalone/SKILL.md`、使用 `standalone/portable.py`

使用 Python 标准库，数据存 `~/.sagasmith/`。不支持 PDF 导入、FTS5、ChromaDB。
需要 PDF 时请用户先转为 Markdown。
