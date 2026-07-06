# CoC 7e Scenario Parsing Design

`sagasmith-core` owns PDF-to-Markdown conversion, source provenance, generic
ingestion, chunking, and retrieval. `sagasmith-coc` owns interpretation of that
Markdown as a Call of Cthulhu scenario.

## 1. Classify the document role

Classify before creating a scene index:

- `scenario`: a conventional Keeper-run investigation.
- `solo_scenario`: numbered or linked decision nodes, such as an Alone Against
  book.
- `handout_pack`: player-facing letters, photographs, clippings, maps, or
  records.
- `rules`: rules reference without scenario content.
- `mixed`: rules/front matter plus one or more scenarios or handout appendices.

Mixed documents must create separate structural regions. Rules sections must not
appear as playable scenes.

## 2. Recover scenario boundaries

Conventional scenarios should recognize:

- scenario or part boundaries;
- playable scenes and named locations;
- nested sublocations;
- introduction, Keeper guidance, background, timeline, setup, conclusion, and
  rewards as reference scenes;
- appendices, investigator sheets, NPC records, creature statistics, maps, and
  handout collections.

Useful heading signals include `SCENE`, `LOCATION`, `PART`, `CHAPTER`,
`INTRODUCTION`, `BACKGROUND`, `SETTING UP`, `CONCLUSION`, `HANDOUT`, and their
Chinese equivalents.

For a `solo_scenario`, numbered passages are `node` records rather than ordinary
scene headings. Parse their choices and target node numbers into directed edges.
Do not load the entire decision graph as one scene.

For a `handout_pack`, each handout is an asset boundary even when there is no
chapter heading.

## 3. Parse investigation substructure

Each scene should expose:

```json
{
  "scene_type": "investigation",
  "visibility": "keeper",
  "subsections": [],
  "clues": [],
  "checks": [],
  "sanity": [],
  "entities": [],
  "transitions": [],
  "tags": []
}
```

### Scene types

- `investigation`
- `social`
- `combat`
- `chase`
- `travel`
- `downtime`
- `reference`
- `handout`
- `solo_node`

### Subsection types

- `location` or `sublocation`
- `clue`
- `core_clue`
- `npc`
- `creature`
- `handout`
- `read_aloud`
- `keeper_note`
- `timeline`
- `hazard`
- `check`
- `sanity_check`

### Checks

When explicitly stated, retain:

- skill name;
- Regular, Hard, or Extreme difficulty;
- bonus or penalty dice;
- whether a pushed roll is allowed;
- success information;
- failure consequence.

Do not infer a missing difficulty or invent a failure consequence.

### Clues

Retain:

- clue title or stable generated key;
- source page and heading path;
- whether it is a core clue;
- acquisition method;
- prerequisites;
- destinations or follow-up scenes;
- player-visible content separately from Keeper-only explanation.

### Sanity

Recognize explicit SAN expressions such as `0/1D4`, including trigger and
context. Preserve the expression as source text; rules resolution remains in
the CoC engine.

## 4. Preserve information boundaries

Every scene, subsection, clue, and asset needs a visibility value:

- `keeper`
- `player`
- `read_aloud`
- `discovered`

Handout exports must never include adjacent Keeper notes. Search results may
locate Keeper-only material, but player-facing rendering must filter it.

## 5. Preserve progression relationships

Parse only explicit relationships:

- scene or node transitions;
- clue destinations;
- timeline triggers;
- prerequisite discoveries;
- solo-node choice edges;
- conclusion or ending conditions.

Store unresolved textual references for review rather than guessing a target.

## 6. Scope runtime progress

Runtime progress is separate from parsed structure. Track the shared group as
`party`, split groups as `group:<id>`, and private investigator knowledge or
solo branches as `player:<character-id>`. A player inherits the party scene
until the player scope records a different current scene. Never merge private
clue state merely because two scopes point at the same parsed scene.

## 7. Quality gates

Reject or require review when:

- a scenario becomes one full-document scene;
- numbered solo nodes are not separated;
- a handout pack becomes one undifferentiated asset;
- rules sections are indexed as playable scenes;
- source page ranges are missing;
- player and Keeper text cannot be separated safely.

## 8. Acceptance fixtures

Use the local `test_pdfs` corpus:

- `Dead Boarder.pdf`: conventional short scenario without useful bookmarks.
- `The Lightless Beacon - Call of Cthulhu.pdf`: location investigation.
- `Lightless Beacon plain text handouts.pdf`: three independent handouts.
- `CHA23145 - Alone Against the Flames.pdf`: solo nodes and choice edges.
- `CHA23131 Call of Cthulhu 7th Edition Quick-Start Rules.pdf`: mixed rules and
  The Haunting scenario.
- `雨乡.pdf`: scanned/OCR quality gate.
