# CoC campaign manager deep reference

## Creation gate

Before entering Play, verify:

- server system coc7e and storage ready;
- campaign owner/principal binding;
- explicit Classic/Pulp ruleset, era, locale, and optional Spending Luck choice;
- current main branch and recoverable revision history;
- at least one confirmed controlled investigator;
- active finalized Module Pack or explicit improvised Keeper setup;
- active reviewed core_rules Pack when the campaign depends on imported rules;
- no unresolved source/permission blocker;
- Lobby snapshot created.

## Access

campaign_change grant_campaign assigns a campaign role to a stable principal.
grant_actor assigns actor access/control according to the native schema. The
server validates both again at call time.

Never expose principal_id as a model decision. A single-user host should bind it
in server configuration; a multi-user host should hide/inject its authenticated
identity.

## Character audit

For each investigator/NPC/creature record:

- id, type, campaign, name, player binding;
- sheet/schema and ruleset;
- characteristics, derived values, HP/MP/SAN/Luck;
- skills/weapons/conditions;
- stable-id inventory, books, spells, and campaign-defined monetary fields;
- development marks/history;
- notes/backstory/source;
- character revision and actor grants.

After any dedicated mechanic, reread rather than assuming the generic update
shape.

## Pack audit

For every active Module Pack verify:

- content-package schema 2 and system coc7e;
- immutable package id/version/checksum;
- source/asset licenses and local-private boundary;
- CoC classification/profile/catalog validity;
- explicit Agent finalization;
- imported module id distinct from the authoring draft module;
- active revision and progress remap history.

For every active rules Pack also verify classification core_rules, immutable
source checksums, current effective rule lock, and successful rule_query
search/expand from the imported source. Keep commercial source text and Pack
artifacts local.

## Character transactions

- inventory_change owns one stable-id item mutation; reread after add, update,
  remove, or consume.
- wallet_change owns one campaign-defined field. Never infer Credit Rating or
  social status from a cash field.
- long_term_change owns one Lobby-only Luck recovery, therapy, aging, or
  source-study transaction. Supply reviewed source values, current campaign and
  actor revisions, and one exact idempotency key.
- source_study records a tome or spell source id and atomically applies the
  supplied SAN/Mythos consequences. Do not invent printed values or learn the
  same source twice.

## Branch/snapshot operations

### Snapshot

Read current branch and campaign revision. Create with a meaningful label at a
decision boundary. Verify the snapshot before relying on it.

### Branch

Create from an explicit parent/snapshot using expected campaign revision and
active branch id. Creation advances campaign revision even without checkout, so
use the returned revision for the next guarded call. Checkout with the refreshed
guards. Use branch_query compare before explaining divergence.

### Restore

1. snapshot_query verify.
2. Explain target branch/head and non-destructive history behavior.
3. snapshot_change restore with current revision/branch and exact key.
4. Refresh native schemas.
5. Reread all campaign, character, module, continuity, ActorKnowledge, random,
   pending-check, Chase, and Combat state.
6. Execute the next legal public call.

### Undo/redo

Use state_revision history/receipt before mutation. Undo/redo changes the branch
head; it does not delete snapshots. A mixed continuity ledger mutation is
non-reversible and requires verified snapshot/branch recovery. Refresh and reread
state after either path.

## Session close

1. Settle or abort pending investigation/attack choices.
2. Close or abort active NPC conversations, then close active Chase/Combat.
3. Commit realized scene continuity and progress.
4. Snapshot the end-of-session Play state.
5. Return to Lobby with current revision.
6. Run development for each authorized actor.
7. Apply any authorized source-backed long-term changes.
8. Snapshot post-development state and retain receipts.

## Regression manifest

Track test/rehearsal progress outside campaign authority only as an audit
manifest. Each runnable scenario must prove:

- source-bound Lobby setup and Pack activation;
- rules Pack activation and a legal rule search/expand when a rules source is present;
- Play scene evidence and at least one legal investigation settlement;
- audience-safe continuity/ActorKnowledge;
- isolated NPC conversation settlement when the scenario exercises dialogue;
- SAN or HP mechanic when the source exercises it;
- Chase or Combat when the source contains it;
- Snapshot/restore and one next legal native call;
- at least one legal ending;
- restart/resume and exact idempotent retry;
- machine-readable exclusion for unsupported paths.

For two concurrent campaigns, prove separate sessions, random streams, branches,
actors, secrets, idempotency keys, and restores without cross-contamination.
