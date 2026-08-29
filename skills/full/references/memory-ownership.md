# CoC continuity and knowledge ownership

Choose the narrowest correct authority. Do not use one generic memory channel
for every kind of campaign state.

## Routing table

| Information | Authority | Examples |
|---|---|---|
| Immutable authored possibility | Module Pack | secret, clue path, NPC dossier, possible ending |
| Scoped scene realization | module progress/state | discovered clue, revealed handout, visited subsection |
| Objective durable branch fact | memory | door destroyed, cult leader dead, ritual interrupted |
| Chronology | campaign event | investigator arrived, SAN encounter occurred, clue shared |
| One actor's subjective state | ActorKnowledge | saw symbol, believes witness, misunderstood phrase |
| Mechanical actor state | character sheet | HP, SAN, Luck, wounds, skills, conditions |
| Encounter state | Chase/Combat facade | positions, actions, turn, pending defense |
| Alternate timeline | branch/snapshot | fork, checkout, restore, undo/redo |

Workspace memory, chat history, summaries, and Agent scratch notes are never
campaign authority.

## Read before deciding

Use continuity_context with:

- exact campaign and branch;
- actual actor and scene scope when relevant;
- dm or player audience;
- bounded query and character budget;
- source references related to the ruling.

Non-DM callers are forced to player projection. Never reuse a DM context bundle
for player narration.

For a long-running investigator or NPC, use `purpose="actor_memory"` to retrieve
identity, motivational, semantic ActorKnowledge, and episodic participant-event
tracks under one deterministic budget. Query recall searches the whole current
branch, not only the recent window. Player reads are filtered at the Core query
entrance by both knowledge disclosure and event audience; Keeper-only events do
not become player-visible merely because an investigator participated. The
projection never chooses an investigator's intent.

## Commit one realized outcome

Prefer memory_change(action="commit") after an investigation or scene outcome
when the accepted meaning creates related continuity:

~~~json
{
  "event": {
    "summary": "<what actually happened>",
    "event_type": "discovery",
    "audience_scope": "actor",
    "participants": ["<actor-id>"]
  },
  "facts": [],
  "actor_knowledge": [
    {
      "action": "add",
      "actor_id": "<actor-id>",
      "knowledge_key": "clue:<stable-id>",
      "proposition": "<what this actor learned>",
      "cause": "discovered",
      "disclosure_scope": "owner"
    }
  ],
  "snapshot": null
}
~~~

Use the current native schema; the example shows semantic routing, not a source
of invented ids. Cite actual source/event references where the schema accepts
them.

The commit owns its event, facts, knowledge, and optional snapshot atomically.
It does not retroactively make the preceding mechanic settlement part of that
transaction.

## Audience rules

- dm: Keeper-only chronology/context.
- party: information shared with the active party scope.
- public: safe for all campaign members.
- actor: limited to named participants/known actors.

An actor's private discovery becomes party/public only through a realized
sharing event. Do not copy private knowledge merely because actors occupy the
same scene; the Agent decides perception, hearing, language, and comprehension.

## Fact revision

- Give durable facts stable fact_key and subject_ref identities.
- Upsert/revise an existing fact only with its expected_revision_id.
- Preserve source event ids and branch identity.
- Deactivate or supersede a fact rather than rewriting history invisibly.
- On conflict, reread and decide from current evidence.

## ActorKnowledge revision

- Keep each investigator, NPC, and creature independent.
- Use stable knowledge_key and subject_ref.
- Record epistemic status, confidence, cause, disclosure scope, and source event.
- Revising knowledge requires the exact knowledge item and revision guard.
- Knowledge imported in an actor card or another campaign never transfers
  automatically.

## Secrets and NPC portrayal

Module-authored secrets remain possibilities until a branch realizes them.
Initial knowers identify authored NPC context, not player knowledge. Open an
isolated npc_conversation for persistent NPC portrayal. The Host-private,
authenticated dispatcher receives only its server-built private capsule and
activation reference; the Director receives only the server-derived
publication. Close commits the
approved public transcript and accepted durable deltas, while abort discards
the private draft. Grounded, deceptive, and uncertain factual speech cites
actor-owned basis refs; nonfactual speech is explicit. A freshness replacement
preserves the original stimulus cursor and reason while invalidating stale
private work.

## Restore

After branch checkout, restore, undo, or redo:

1. discard cached continuity and audience assumptions;
2. refresh native tools;
3. reread current branch, scene progress, events, facts, and actor knowledge;
4. never copy a fact or discovery from a sibling future branch.
