# Emergent CoC campaign expansion

Use this mode when the table begins with a compact setting and a few playable
scenes, then discovers the investigation through play. It also covers a complete
authored scenario when investigators choose a reasonable destination outside
its Scene Atlas. Missing Atlas coverage is not an invisible wall.

## Two orthogonal classifications

Keep the existing Pack classification (`scenario`, `campaign`,
`solo_adventure`, or `handout_pack`) unchanged. Separately record runtime design
classification as `authored_scenario`, `emergent_seed`, or
`emergent_episode`. A seed and every reviewed episode are immutable Packs; do
not rewrite an earlier shard.

An episode records one root, its immediate parent, and exactly the parent's
generation plus one. It must add a Scene Atlas entry and a scene link. The
playthrough manifest lists installed shards in order, and Scene Atlas identity
is always the composite `(pack/module id, scene id)`.

## Seed design

Prepare only enough for honest opening play: premise and tone, safety
constraints, starting situation, a few locations and actors, and an immediately
playable scene. Add:

- fronts with goals, stakes, and visible escalation signals;
- story threads framed as questions with multiple plausible developments;
- clues with redundant discovery paths and no single-check dead end;
- investigator arc opportunities that create tension without choosing an investigator's
  action, beat, or ending; and
- NPC arc opportunities grounded in goals, relationships, knowledge, SAN,
  obsessions, phobias, and events.

The seed may omit distant regions, villains, answers, and endings that are not
needed for the opening. CoC Pack endings remain required for authored play, but
not for `emergent_seed` or `emergent_episode` runtime design.

## Expansion cadence

At a safe intermission, close NPC conversations, leave Combat/Chase, and return
to Lobby. Request `continuity_context(purpose="campaign_expansion")`. The
isolated worker has zero tools and may return only a bounded proposal grounded
in the signed campaign-design reference. `bounded_evaluation` validates it but
never writes campaign truth.

Keeper review must check continuity, source constraints, unresolved
consequences, fronts, threads, clue redundancy, investigator agency, NPC motivation, and
the smallest useful next horizon. Then use the normal Module draft, evidence,
repair, finalize, import, and explicit activation gates. Only MCP may persist
the reviewed playthrough manifest and later settle actual events, facts,
ActorKnowledge, clues, and progress.

Runtime progress for an advanced/resolved/averted front,
advanced/resolved/abandoned thread, or advanced/resolved/closed arc requires at
least one exact evidence reference. An investigator or NPC arc advances only through a
completed authored opportunity; it never schedules a forced outcome.

## Authored scenario detours

When investigators name an off-Atlas destination, first check geography,
travel, factions, source facts, and established branch truth. At the next safe
boundary, author the smallest useful `emergent_episode`, link it from a valid
transition point, root it at the immutable authored scenario, and switch the
playthrough mode to `authored_with_extensions`. The extension is campaign canon,
not retroactive publisher canon.

New clues may illuminate an authored mystery but must not silently replace a
published answer. Reconnection is another scene link or later episode, never a
rewrite of the root. A generator or subagent may propose content but may not
roll, mutate state, publish narration, or activate a Pack.
