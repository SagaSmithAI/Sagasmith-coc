# SagaSmith CoC MCP

## MCP 2026-07-28 and compatibility mode

The same handlers serve modern MCP 2026-07-28 and the explicit legacy migration
path. Modern requests do not rely on `initialize`, `Mcp-Session-Id`, or a
connection-bound principal. Every request carries a target-specific, at-most
15-minute `sagasmith.auth-context/v2` delegation in `_meta`. The MCP revalidates
the target service, operation, audience, requester/resource owner/acting identity,
`room_turn_id`, `base_revision`, and expiry, then overwrites model-authored identity.
Browser tokens and tokens minted for another audience must never be passed through.

Modern `tools/list` is complete, deterministically sorted, and privately cacheable
for the same authorization scope (`ttlMs=300000`). Phase, role, and tool side
effects do not mutate the catalog. A Host may show its model a task/phase subset,
while the MCP still rechecks role, phase, and revision at execution. `exposure`
returns an owner- and TTL-bound opaque handle for catalog guidance only; it grants
no authority. Connection exposure and `tools/list_changed` remain only in the
explicit legacy adapter and are not a durable security boundary.

Collection reads expose the same top-level `query`, `limit`, and `cursor` contract.
They default to 50 records, enforce a maximum of 100, and return both
`next_cursor` and `has_more`; callers must reuse the opaque cursor verbatim with
the same filters. This applies to module drafts, rule sources, module/scene/progress
indexes and search, objective memory, actor knowledge, branches, snapshot lists and
lineage, investigation history, campaign events, and state-revision history. Event
and revision cursors are pushed into Core, so records after the first 100 remain
reachable without loading complete campaign history into the MCP process. Actor
memory can also resolve up to 128 exact `event:<id>` references through Core actor,
branch, knowledge-disclosure, and audience policy. The locked CI lane uses Core
`59173c2fe3b80637a0890062dff381b38aa325fe` for both authority contracts.

Expected, model-repairable
failures return `isError: true` with actionable guidance. Protocol/input failures
remain JSON-RPC errors, and unexpected internal failures do not expose details.
Every public tool publishes parameter descriptions, enforced request bounds,
behavior annotations, and a stable output schema. Tool-execution failures retain
the compatibility text block and add `structuredContent.error` with `code`,
`message`, `retryable`, and `recovery`. The real transport contract matrix runs
both legacy and 2026-07-28 clients over stdio and Streamable HTTP.

[中文](README.md) · [English](README-en.md) · [Website](https://sagasmithai.github.io) · [Platform overview](https://github.com/SagaSmithAI/.github/blob/main/profile/README.md) · [SagaSmith Web](https://github.com/SagaSmithAI/SagaSmith-Web) · [Content catalog](https://github.com/SagaSmithAI/SagaSmith-dnd-content-library)

> Current source lives at `sagasmith-coc/packages/mcp` and is released from the CoC vertical monorepo with its Domain, Skills, and Workbench contracts.

The local authoritative MCP server for SagaSmithAI's Call of Cthulhu 7e stack. It combines campaign persistence, branch-aware memory, per-actor knowledge, snapshots, module retrieval, and unified Content Packs from `sagasmith-core` with CoC d100, sanity, combat, chase, and replayable random-stream mechanics from `sagasmith-coc`.

## Runtime boundary

- MCP owns campaign state, authorization, revisions, idempotency, random-stream receipts, and atomic random resolution.
- Modern `tools/list` is stable and sorted. The Host selects a Lobby, Play, or Combat subset for its model (SagaSmith defaults to at most 16 tools); policy is enforced again at call time. Sixteen is a Host accuracy policy, not a protocol limit.
- Legacy clients may retain connection exposure and `tools/list_changed` during migration. Neither is an authorization boundary.
- The Agent owns source interpretation and scenario-specific semantic decisions. Finalized Pack decisions retain source evidence.

The native capability flow is:

```text
tools/list -> Host task/phase selection -> native domain tool
optional: exposure(open) -> exposure(search|set, exposure_handle)  # guidance only
```

Keeper recovery uses `branch_query/change`, `snapshot_query/change`, and
`state_revision`. Every mutation requires explicit revision, branch or history-cursor
guards plus an `idempotency_key`. When checkout, restore, undo, or redo changes the
authoritative phase, modern catalogs remain stable and the Host updates only its model-facing
selection. The legacy adapter may emit `tools/list_changed` for old clients.

Snapshots remain independently restorable full state documents at the public
boundary. Core schema v9 stores each document as one bounded, checksummed
`zlib-1` record. Snapshot query/restore, branch checkout, undo/redo, and restart
recovery do not replay an ancestor chain.

Play and Combat expose two source-explicit actor-state settlements:

- `coc_sanity_check` atomically rolls the SAN check, loss, required INT check, temporary/indefinite/permanent insanity, bout, and duration, then commits the campaign random stream and investigator sheet in one revision group.
- `coc_hp_change` atomically applies damage or healing. A major single blow draws any required CON check from the authoritative stream and persists major-wound, unconscious, dying, dead, and recovery state. A fixed HP change with no random draw does not manufacture a campaign revision.

Both tools require actor-control authorization, campaign and character revisions, and an idempotency key. An exact retry returns the original response without drawing or settling twice.

Authoritative combat uses task-shaped native tools instead of allowing callers to patch `campaign.state` directly:

```text
combat_start -> combat_query
             -> combat_action(move|join|end_turn)
             -> combat_attack(open -> resolve|abort)
             -> combat_end
```

`combat_start` checks participant character revisions, then enters Combat using DEX, DEX+50 for a readied firearm, and stable ties. An attack first persists a pending response; the target controller then chooses dodge, fight back, dive for cover, or no response. `resolve` draws from the campaign stream and atomically settles attack, defense, extreme/impaling damage, ammunition, CON, HP, and wounds in one campaign/character revision group. Grid mode owns coordinates and validates movement and melee distance. Agent mode creates no coordinates and accepts only explicit Agent spatial facts. `combat_end` returns to Play and reports actors that still require dying recovery.

A real stdio-host regression covers Lobby → Play → Combat → Play. The complete
modern catalog remains unchanged while the Host updates its model-visible facade;
the server rejects calls that are illegal in the new phase and accepts the next
legal phase tools. The legacy regression separately verifies the exposure and
`tools/list_changed` adapter.

Chases stay within Play and use `chase_start/query/action/end`, with strict mutual exclusion against Combat. At chase start, MCP reads an explicitly named CON, Drive Auto, or Pack-defined skill from each sheet, resolves speed checks from the campaign stream, then derives per-round action points from the slowest effective MOV. `chase_action` owns DEX order, action-point consumption, route position, obstacle checks, and round resets. A Pack or Agent must explicitly supply the sourced position effects of success and failure; MCP does not guess narrative terrain. Players can act only for controlled actors, start/end remain Keeper-only, and every random/state transition has revision and exact-idempotency receipts.

Investigation continuity uses three distinct ledgers instead of treating narration as shared knowledge:

- `campaign_event` appends a branch-local chronology entry with an explicit `dm`, `party`, `public`, or `actor` audience and optional speaker/listener/witness/target participants.
- `continuity_context` returns one budgeted, branch-scoped context projection. Non-Keeper callers are always forced through the player projection and may retrieve private knowledge only for an owned actor.
- `memory_change(action="commit")` atomically settles one event together with objective fact revisions, per-actor knowledge revisions, and an optional snapshot. Every derived fact and knowledge row defaults its provenance to the committed event; exact retries replay the same response and any failed component rolls back the whole settlement.

Objective `memory_query` and all continuity writes are Keeper-only. Players cannot use the objective fact ledger to bypass clue, secret, false-belief, or split-party boundaries. Continuity remains available during Combat as a safe read, while chronology and memory writes close until Play resumes. Real stdio coverage verifies these native tools are added and removed with the phase-specific schema.

Source-backed investigation checks use `investigation_check(open|spend_luck|push|settle|abort)` plus `investigation_query`. The MCP reads the exact named skill, characteristic, or Luck value from the actor sheet, rolls from the campaign stream, and persists the unresolved human choice. Optional Spending Luck must be enabled in campaign settings; the exact Luck cost and actor revision settle atomically. A Push requires an explicit new approach and Keeper failure consequence, rolls a second time, and can never be adjusted with Luck. Pending choices survive restart and block Combat, Chase, or return to Lobby until settled or Keeper-aborted. Successful skills are marked once for later development.

Combined checks use the same resumable workflow but compare one shared d100 with two to eight sheet-backed skills or characteristics. The Keeper must explicitly choose `requirement="any"` or `"all"`; Spending Luck buys exactly that aggregate requirement and a successful component skill receives its own development mark. CoC does not invent a D&D-style majority-success group rule. For a true group Luck roll, `group_luck_query/check` reads every scene participant's current sheet and permits only an investigator tied for the lowest Luck to represent the group; a lowest-value tie requires an explicit Keeper selection.

End-of-session growth is a Lobby operation. `development_query` lists the actor's checked skills and `development_settle` rolls all eligible checks in one campaign stream transaction, updates skills and any first-time mastery SAN reward, clears every check mark, and stores a bounded audit receipt. Cthulhu Mythos is reported and cleared as ineligible rather than being silently advanced by the ordinary skill procedure. Player control, campaign/character revisions, branch scope, restart recovery, and exact idempotent replay are enforced at the write boundary.

Checks do not invent clue meaning or audience. `settle` and `group_luck_check` return mechanical receipts and direct the Agent to record source-specific narration, objective facts, actor knowledge, and failure consequences through `memory_change(action="commit")`. An obvious or indispensable clue bypasses the check entirely and uses that continuity settlement directly, so repeated poor dice cannot deadlock the scenario.

## Module Pack authoring

CoC scenarios use the unified `sagasmith.content-package` schema version 2 lifecycle:

```text
module_draft(start)
  -> module_draft(edit, operation="advance")  # only after an interrupted first pass
  -> module_draft(evidence)
  -> module_draft(edit, operation="statblock|content|asset|actor")
  -> module_draft(edit, operation="package")
  -> module_draft(finalize)
  -> content_pack(import)
  -> content_pack(activate)
  -> content_pack(deactivate|remove)
```

`start` accepts either an allowlisted PDF/Markdown/text `source_path` or generated `name` plus `content`. Mechanical import creates an inactive draft; `advance` resumes from a committed intermediate step after interruption. `evidence` exposes bounded chunks, managed PDF-page render receipts, assets, and content reviews. `edit` supports checksum-bound PDF transcription repair, reviewed CoC content, current CoC statblock-schema validation, allowlisted assets, actor bindings, and Pack decisions. Statblocks may preserve source-true partial non-combat NPC data; only an explicit `combat_ready` declaration requires combat fields. Any source-text repair creates a new inactive mechanical revision and invalidates downstream draft decisions. Pack profile and catalog decisions must use the exact source receipts returned by `evidence`. Finalization requires an explicit Agent confirmation and writes an immutable `.sagasmith-pack` archive. Only a module re-imported from that finalized archive may be activated.

Commercial rulebooks and scenarios remain local. Configure allowed source roots with `SAGASMITH_COC_MCP_MODULE_IMPORT_ROOTS`, separated by the platform path separator. Source books and extracted assets are never bundled in this repository.

Pack import uses a deterministic recovery protocol. The Pack checksum belongs to candidate
version identity, while module, asset, content-review, actor, and binding steps converge by
content identity or child idempotency keys. If the process stops before the final receipt,
retry the original request and `idempotency_key`; no duplicate runtime objects are created.
Activation, deactivation, and removal each commit an exact receipt, including replay after
the target was removed.

## Run

```bash
pip install sagasmith-coc-mcp
sagasmith-coc-mcp
```

This is the CoC-only Local Kit text baseline: SQLite, FTS, Markdown/text, and
the authoritative MCP handlers work without forcing Core documents/vector/
embedding, Pillow, ChromaDB, or Torch onto the installation. PDF libraries load
only when their capability is called and otherwise return an actionable install
instruction.

| Extra | Capability |
|---|---|
| `documents` | PDF text extraction and page rendering |
| `images` | visual PDF page review; currently shares the `documents` stack |
| `embedding` | Domain/CLI Sentence Transformers embeddings |
| `vector` | Domain/CLI ChromaDB vector storage |
| `dense` | `embedding` + `vector` |
| `gateway` | Workbench gateway |
| `all` | all currently implemented document, embedding, and vector capabilities |

```bash
pip install "sagasmith-coc-mcp[documents]"
pip install "sagasmith-coc-mcp[dense]"
```

The current CoC importer has no OCR execution path, so it does not declare a
misleading `ocr` extra; scanned sources need a legal, reviewable text layer
before import. `SagaSmith-agent` owns cross-system Local Kit manifests. This
repository declares only the CoC wheel and extras boundary.

Local stdio and loopback Streamable HTTP both run the same `create_server()`
and authoritative handlers. Tool schemas, errors, revisions, idempotency, and
authority semantics do not fork by transport. Use stdio when one Agent owns the
process; the unified local stack uses Streamable HTTP and serves the Workbench
through a bounded connection-reusing gateway:

```powershell
$env:SAGASMITH_COC_MCP_TRANSPORT = "streamable-http"
$env:SAGASMITH_COC_MCP_HTTP_PORT = "8769"
sagasmith-coc-mcp

# another terminal
$env:SAGASMITH_COC_MCP_URL = "http://127.0.0.1:8769/mcp"
$env:SAGASMITH_COC_GATEWAY_PORT = "8768"
sagasmith-coc-gateway
```

The browser never submits an authoritative principal. The gateway derives identity
server-side and may reuse HTTP connections, but every MCP request is independently
authorized; no principal or campaign state is pooled in the connection.

State defaults to `.sagasmith-coc-mcp/`. The main configuration variables are:

- `SAGASMITH_COC_MCP_HOME`
- `SAGASMITH_COC_MCP_MODULE_IMPORT_ROOTS`
- `SAGASMITH_COC_SKILLS_DIR`
- `SAGASMITH_MODULEGEN_SKILLS_DIR`
- `SAGASMITH_COC_MCP_BOUND_PRINCIPAL_ID`
- `SAGASMITH_COC_MCP_TRANSPORT` (`stdio` or `streamable-http`)
- `SAGASMITH_COC_MCP_HTTP_HOST`, `SAGASMITH_COC_MCP_HTTP_PORT`, and `SAGASMITH_COC_MCP_HTTP_PATH`
- `SAGASMITH_AUTH_CONTEXT_SECRET` (required for non-loopback HTTP, at least 32 bytes)

The server applies Core Alembic migrations at startup and requires the current
Snapshot schema v9. Before deployment, stop the server and take a consistent
backup of `data/ttrpgbase.db` after its SQLite WAL has settled, or use the
external database's native backup mechanism. Snapshot schema v9 has no in-place
downgrade. Protocol compatibility is dual-era: modern is the default and legacy
is an explicit migration/rollback adapter. Data rollback restores the database
together with matching Core, CoC, and MCP versions as one unit.

## Observability and verification

Modern requests propagate `traceparent`, `tracestate`, and `baggage`. Transport,
discover/initialize, catalog/exposure, tool, and projection metrics use only
low-cardinality dimensions; user, campaign, run, and arguments must never become
metric labels. Structured errors and audit receipts preserve safe trace
correlation without exposing authorization tokens or private arguments.

`evaluations/read_only.xml` contains ten independent, complex, stable, and
actually solved read-only evaluations. Automated coverage also exercises the
modern/legacy × stdio/HTTP matrix, deterministic catalogs, private cache scopes,
identity isolation, schemas, structured errors, traces, pagination, idempotency,
stale revisions, and restart recovery.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

Run the complete vertical validation from the repository root:

```bash
uv sync --all-packages --all-extras
uv run --package sagasmith-coc pytest packages/domain/tests
uv run --package sagasmith-coc-mcp pytest packages/mcp/tests
uv run ruff check packages/domain packages/mcp
npm ci
npm run test:ui
npm run build:ui
```

Original code is licensed under Apache-2.0. Call of Cthulhu and related commercial content remain the property of their respective rights holders.
