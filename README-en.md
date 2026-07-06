# 🕯️ SagaSmith CoC

[中文](README.md) | [English](README-en.md)

**Call of Cthulhu 7th Edition runtime** — system plugin and portable JSON CLI for `sagasmith-core`.

> *"The universe doesn't care about your investigator. We do."*

`sagasmith-coc` registers the `coc7e` system profile on top of `sagasmith-core`. Commercial rulebooks are not bundled — users may ingest documents they are permitted to use. The package is independent of any agent platform; platforms load `SagaSmith-coc-skills` and operate the same `sagasmith-coc --json` CLI.

---

## Ecosystem

| Repo | Role |
|------|------|
| 🕯️ **sagasmith-coc** (this repo) | CoC 7e system plugin + CLI |
| 🏗️ [sagasmith-core](https://github.com/dajiaohuang/sagasmith-core) | General engine — DB, docs, RAG |
| 🎲 [SagaSmith-agent](https://github.com/dajiaohuang/SagaSmith-agent) | Complete AI DM runtime |
| 📦 [SagaSmith-coc-skills](https://github.com/dajiaohuang/SagaSmith-coc-skills) | CoC agent skill definitions |

---

## Features

- 🕯️ **Campaign Management** — Investigator group creation, character management, rule/module binding, event log
- 👤 **Investigators** — Classic/Pulp dual-edition validated sheets, skills, occupations, assets, companions
- 🎲 **Rule Engine** — d100 / opposed checks, success levels, pushed rolls, bonus/penalty dice
- 🧠 **SAN & Insanity** — Sanity checks, temporary/indefinite madness, phobias/manias
- ⚔️ **Combat & Chases** — Melee/ranged turn-based combat, chase rounds, actions/reactions
- 📖 **Modules** — PDF/Markdown import with three parsing modes: conventional investigation, solo scenario (numbered nodes + choice edges), handout pack
- 🔍 **Scene Metadata** — `scene_type` (investigation / social / combat / chase / travel / reference / handout / solo_node), `visibility` (keeper / player / read_aloud), clues, checks, SAN expressions, transitions
- 🧩 **Scene Progress** — Scoped to `party` / `group:<id>` / `player:<id>` with transparent inheritance from party
- 💾 **Snapshot** — DAG save tree with branch-aware restore for investigator groups

---

## Quick Start

```bash
# Install
pip install "sagasmith-coc[documents]"

# Check runtime health
sagasmith-coc doctor --json

# Create a campaign
sagasmith-coc campaign start --name "Arkham" --json

# Import rules
sagasmith-coc rules ingest --path ./rulebooks --publication "CoC 7e Keeper Rulebook" --locale en --json

# Inspect module structure
sagasmith-coc module inspect --path ./scenario.pdf --json

# Import a module
sagasmith-coc module ingest --campaign <id> --path ./scenario.pdf --json

# View scene index (with scene_type, visibility, clues, checks, sanity)
sagasmith-coc module index --campaign <id> --json

# Query current scene
sagasmith-coc module current --campaign <id> --scope party --json

# Update progress
sagasmith-coc module set-progress --campaign <id> --scope player:herbert --scene <scene-id> --progress 30 --state '{"discovered_clues":["bloody letter"]}' --json

# Create an investigator
sagasmith-coc investigator create --campaign <id> --name "Herbert West" --occupation "Doctor" --str 50 --con 60 --siz 65 --dex 55 --app 45 --int 80 --pow 70 --edu 75 --json

# d100 check
sagasmith-coc check --campaign <id> --skill "Library Use" --score 65 --difficulty hard --json

# SAN check
sagasmith-coc sanity --campaign <id> --loss "1/1D6" --json
```

---

## CoC Profile Scene Parsing

`CocModuleProfile` implements three parsing modes, auto-selected:

### Auto-Classification

1. **Solo scenario** — detects numbered passages (`## **1**` ~ `## **N**`) with explicit choice edges (`→`, `Go to`, `转到`), triggers at N ≥ 10 with sufficient edges
2. **Handout pack** — detects `HANDOUT` / `玩家资料` / `手记` titles, triggers when sufficiently prevalent
3. **Conventional scenario** — default mode with smart H2/H3 level detection

### Scene Metadata

| Field | Description |
|-------|-------------|
| `scene_type` | `investigation` / `social` / `combat` / `chase` / `travel` / `reference` / `handout` / `solo_node` |
| `visibility` | `keeper` (GM only), `player` (player-facing), `read_aloud` (boxed text) |
| `subsections` | Sub-headings with `type` (clue / core_clue / location / npc / creature / handout / sanity_check / check / keeper_note / timeline) |
| `clues` | Clue list (includes clues and core clues from subsections) |
| `checks` | Check items with `difficulty` (regular / hard / extreme) |
| `sanity` | SAN expressions preserved as source text (e.g. `0/1D4`) |
| `transitions` | Solo node transition target IDs |
| `node_id` | Solo node identifier |

---

## Optional Extras

| Extra | Purpose |
|-------|---------|
| `dense` | sentence-transformers + ChromaDB vector retrieval |
| `documents` | PDF parsing |
| `all` | All extras |

---

## Development

```bash
pip install -e ".[all,dev]"
pytest --cov
ruff check .
```

---

## Credits

- [CoC7 Foundry VTT System](https://github.com/foundryvtt-coc7/CoC7-FoundryVTT) — Implementation reference for data shapes and adjudication coverage
- Call of Cthulhu 7th Edition © Chaosium Inc.

---

## License

MIT
