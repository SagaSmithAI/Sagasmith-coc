# Scenario index, Pack review, and scene operation

Core owns generic documents/chunks/archive identity. sagasmith-coc owns CoC
scenario parsing and Package validation. The Agent owns source interpretation
and repeated draft repair.

## Supported Module Pack profiles

- scenario;
- campaign;
- solo_adventure;
- handout_pack.

Every finalized CoC Module Pack uses system coc7e, content-package schema 2,
7e compatibility, six evidenced play-profile sections, seven exact catalog
arrays, dossiers/endings arrays, and explicit Agent finalization. Use
coc-module-generator for the full contract.

## Mechanical first-pass review

After module_draft start, verify:

- parser profile coc7e and current parser version;
- expected chapters/scenes/chunks and stable keys;
- investigation, social, combat, chase, travel, reference, handout, and solo
  scene classifications where sourced;
- canonical `restricted`/`group`/`public` visibility advisories;
- clue, core-clue, handout, SAN, NPC, creature, timeline, and check subsections;
- source page/chunk evidence;
- numeric solo nodes and explicit transitions;
- source-preserving statblocks and missing-value diagnostics;
- no swallowed, duplicated, empty, or accidentally split scenes.

The parser is a first pass. Repair source/draft evidence rather than adding a
single-book heuristic.

## Scene operation

Use module_query:

- list for installed modules;
- index for legal scene index;
- current for a party/group/player scope;
- progress for scoped scene state;
- search for bounded source hits.

The current CoC MCP has no separate module_expand/read-scene facade. Use the
exact content returned by legal module queries and managed draft evidence; do
not claim D&D module_expand behavior.

Use scopes such as party, group:<id>, or player:<actor-id> only when the current
server accepts and authorizes them. One scope's private discovery does not
automatically enter another.

## Progress state

Before module_change, read the current state and merge rather than deleting
unknown keys. Useful Pack-specific state may include:

~~~json
{
  "discovered_clues": [],
  "revealed_handouts": [],
  "visited_subsections": [],
  "resolved_checks": [],
  "triggered_timeline": [],
  "keeper_flags": [],
  "selected_transition": null
}
~~~

This is Module data, not a universal schema. Use exact current source ids and
preserve Pack-specific fields.

## Visibility

- `restricted` content is not player narration.
- `group`/`public` material still requires the actual audience/context.
- CoC clues, checks, SAN expressions, transitions, and solo `node_id` live in
  `profile_data`; do not read them as a fixed top-level Core scene superset.
- A clue entry is available content, not proof of discovery.
- A transition is a candidate, not a forced player choice.
- Handouts must exclude Keeper annotations and hidden solution text.

## Private commercial sources

Keep original PDFs, normalized text, private Pack archives, page renders, and
checksums local. Commit only synthetic regression fixtures or non-infringing
metadata unless the user explicitly authorizes lawful distribution.
