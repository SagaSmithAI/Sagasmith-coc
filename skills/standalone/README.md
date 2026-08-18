# SagaSmith CoC Skills — Standalone

**Python 标准库便携模式。** 用于无 Full runtime 环境的演示、快速调查与文件状态。

```powershell
cd standalone
python portable.py doctor
python portable.py campaign start --name "Arkham"
python portable.py roll d100 --score 65
```

加载 [`SKILL.md`](SKILL.md)。数据默认位于 `~/.sagasmith/`。

Standalone 不解析 PDF，不提供 FTS5/ChromaDB、完整 SAN/战斗引擎、认证 principal 或 Core 级分支保证。它的写入不会同步到 Full runtime；Agent 切换前必须明确说明能力差异。
