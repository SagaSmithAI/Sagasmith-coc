# CoC Full Runtime workflows

Use these ordered flows with the current native schemas. Read
mcp-contract.md for phase and authorization details.

## New campaign

1. server_capabilities; storage_status.
2. exposure open without campaign.
3. exposure search/set campaign_change; refresh native tools.
4. campaign_change create with name, settings, and stable request identity.
5. exposure open with returned campaign_id.
6. campaign_query get; game_phase; branch_query current.
7. Expose character/Pack/access tools needed for setup.
8. Create and reread confirmed investigators.
9. Build/import/activate finalized rules and Module Packs as needed, or
   explicitly record an improvised Keeper setup.
10. Snapshot the ready Lobby state.
11. campaign_change set_phase Play with current revision.
12. Refresh tools and read the first legal scene/context.

## Resume campaign

1. campaign_query list/get and select the exact campaign.
2. exposure open for that campaign/principal.
3. game_phase; branch_query current; state_revision receipt/history.
4. Read characters, active module/current progress, pending investigation,
   active Chase/Combat, continuity, and ActorKnowledge.
5. Search/set only the tools needed for the next legal action.
6. Narrate a recap from player-safe current evidence, not stale chat history.

## Enter a scene

1. module_query current/progress/index as needed.
2. continuity_context for the actual actor/scope/audience.
3. Separate immediately perceivable evidence, hidden truth, available actions,
   and source mechanics.
4. Present only player-safe situation/evidence.
5. Await player method and intent.

## Reveal obvious/core evidence

1. Confirm the source makes the evidence available for the stated method.
2. Do not roll.
3. memory_change commit the realized event, any objective fact, and only the
   actors who perceived/understood it.
4. module_change set_progress for the appropriate party/group/player scope.
5. Narrate the safe discovery.

## Run an investigation check

1. Read actor sheet/revision, campaign revision, source, and current scene.
2. investigation_query pending.
3. investigation_check open with source, goal, trait or traits, difficulty,
   dice modifiers, and any/all requirement for a combined check.
4. Present roll/outcome and available actions.
5. If the player spends Luck, call spend_luck with exact amount and new
   revisions. If pushing, record changed approach and failure consequence first.
6. Call settle after the choice.
7. If interrupted at any point, query pending/history before retrying.
8. memory_change commit actual meaning/audience/knowledge.
9. module_change progress if scene state changed.

## Group Luck

1. Identify only investigators present for this group question.
2. group_luck_query with their actor ids.
3. If lowest Luck ties, the Keeper selects one returned candidate explicitly.
4. group_luck_check with source, goal, current revision, and selected actor.
5. Commit actual consequence/audience with memory_change.

## SAN encounter

1. Retrieve the exact trigger and success/failure loss expressions.
2. Read current campaign and character revisions.
3. coc_sanity_check with real_time or summary context.
4. Use returned authoritative SAN/INT/bout receipt and updated sheet.
5. Commit only audience-safe actual narration/knowledge.

## Chase

1. Confirm Play, no active Combat, source evidence, participants, actor
   revisions, route/hazards, and current campaign revision.
2. For a vehicle participant, bind participant_kind=vehicle and its reviewed
   source_id/name/Build/MOV card. Then call chase_start and refresh if exposure
   changes.
3. chase_query before each action.
4. chase_action move/check/speed_check/end_turn only from legal actions.
5. Persist narrative consequences without duplicating chase state.
6. chase_end with explicit outcome and source.
7. Refresh Play tools and commit scene continuity.

## Combat

1. Confirm Play, no active Chase, exact participants/revisions, source, and
   positioning_mode grid or agent.
2. combat_start; consume tools/list_changed and refresh Combat tools.
3. combat_query before each turn/action.
4. combat_action join/move/end_turn for guarded non-attack actions.
5. combat_attack open for a response choice; resolve or abort the exact pending
   attack.
6. Use agent positioning only with explicit Keeper range/sight/obstruction facts;
   never synthesize coordinates.
7. combat_end with explicit outcome.
8. Consume tools/list_changed, refresh Play tools, reread characters/continuity,
   and settle actual consequences.

## Module Pack authoring/install

1. Stay in Lobby and load sagasmith-modulegen.
2. module_draft start one managed source.
3. Review inspection and module_draft evidence.
4. Apply narrow evidence-backed edits with current draft revisions.
5. Save exact coc7e Package decisions and explicit Agent confirmation.
6. Finalize and inspect the immutable schema-v2 artifact.
7. Stop at build-only unless install/activation was authorized.
8. content_pack import with current campaign revision; keep inactive.
9. Refresh revision, review progress impact, and activate the imported module.

## Rules Pack authoring/install

1. Stay in Lobby and load rulebook_draft, content_pack, and rule_query.
2. Start from one user-authorized managed PDF/Markdown/text source.
3. Search draft evidence and review source checksums/normalization.
4. Finalize the reviewed revision as a private core_rules schema-v2 Pack.
5. Import inactive with the current campaign revision, then explicitly activate.
6. Use rule_query effective to verify the rule lock, search a known rule, and
   expand its source context before relying on the Pack in Play.

## Isolated NPC conversation

1. Confirm Play with no active Chase/Combat and gather every participant id.
2. npc_conversation open; keep each returned conversation/revision handle.
3. For each speech/action/scene stimulus, the Agent explicitly rules perceived,
   understood, and response actor ids, then calls ingest.
4. Send only activation_ref to the local host worker. The worker claims its
   private capsule and submits a strict proposal without tool/state authority.
5. Use only the server-derived publication. Resolve any requested mechanic via
   public tools, then publish with fresh Agent-resolved audience facts.
6. Repeat until no pending activation, publication, or resolution remains.
7. Close to commit the public transcript and explicitly selected durable
   deltas, or abort to discard the uncommitted dialogue.

Never move phase, start Chase, or start Combat while a conversation is active.

## Snapshot, branch, and restore

1. snapshot_query list/get/verify and branch_query current.
2. Explain the target and that restore creates/uses history rather than deleting
   later snapshots.
3. snapshot_change restore with exact snapshot, expected campaign revision,
   expected active branch, and idempotency key.
4. Consume tools/list_changed and refresh schemas.
5. Reread phase, branch, characters, module progress, continuity,
   ActorKnowledge, pending checks, Chase, and Combat.
6. Run the next legal native call to prove recovery.

For alternatives, create a snapshot, branch_change create from the intended
parent, refresh the campaign revision returned by branch creation even when it
does not checkout, then checkout with guards and keep sibling random
streams/state isolated.

Mixed continuity commits that include events, facts, ActorKnowledge, progress,
or receipts are non-reversible. If state_revision refuses undo/redo, verify and
restore a snapshot or branch; do not attempt document-only reversal.

## Session/scenario close and development

1. Settle/abort pending choices, close/abort NPC conversations, and close active
   Chase/Combat.
2. Commit events/facts/knowledge/progress and create a boundary snapshot.
3. Return from Play to Lobby with the latest revision.
4. Refresh Lobby tools.
5. For each authorized investigator, development_query then
   development_settle with current campaign/character revisions.
6. Apply authorized long_term_change transactions for Luck recovery, therapy,
   aging, or source study using reviewed source values.
7. Snapshot the post-development state.

## Two campaigns in parallel

Use separate native MCP sessions/exposures. For each campaign maintain distinct:

- campaign_id and principal binding;
- branch/head and revisions;
- random stream;
- actors and ActorKnowledge;
- Module Pack/progress;
- pending checks and encounter state;
- snapshots and idempotency keys.

Never carry retrieved source, secret, roll, revision, or tool result across the
two campaign contexts. Alternate only at explicit safe boundaries and reread the
target campaign before every resumed action.
