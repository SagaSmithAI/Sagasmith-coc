# CoC Pack authoring workflow

## Establish the ledger

Before expanding prose, record the portable id, version, title, language,
license, attribution, exact 7e rulesets, era, investigator/session ranges,
dependencies, classification, required capabilities, pregen and solo review,
scene graph, clues, handouts, SAN triggers, tomes, spells, chases, actors,
secrets, branches, and endings. Record which facts require evidence and which
assets must remain private.

For rules Packs, record source identity, privacy, and the reviewed rules areas
that must be searchable. Do not add scenario scenes, actors, catalogs, or
endings to a rules Pack.

## Author one source

Create one UTF-8 Markdown source with at most one
`sagasmith-runtime-manifest`. Use stable lowercase ids and meaningful headings.
Separate Keeper truth, discovered investigator knowledge, and public narration.
Preserve obvious clues and alternate discovery paths; failed checks may change
cost, time, risk, or detail but must not erase the only legal path forward.

Record exact SAN success/failure expressions and triggers. Distinguish ordinary,
hard, extreme, opposed, combined, pushed, and group-Luck intent. Preserve actor
characteristics, skills, attacks, armor, special abilities, chase facts, and
solo transitions without inventing missing values or geometry.

## Draft and repair

1. Confirm Lobby, authenticated authority, `system_id=coc7e`, current revision,
   profile, and the native authoring tools.
2. Start one draft with either a managed source path or generated name plus
   complete content. Keep the returned job, inactive module id, state, parser
   profile, and revision.
3. Inspect the draft and obtain exact evidence receipts from the native
   evidence action.
4. Repair the narrowest draft field. Use source-text edits for transcription,
   structured content/statblock edits for reviewed mechanics, asset edits for
   managed assets, actor edits for validated bindings, and Package edits for
   manifest, catalogs, narrative, dependencies, metadata, or version.
5. Pass the latest expected revision and a request-specific idempotency key on
   every write, then refresh before the next write.
6. Record concise evidence and ruling notes. Treat optional presentation fields
   and unavailable portraits as non-blocking.

## Finalize and deliver

Validate source identity, scene reachability, clue routes, SAN and check intent,
actors, chase facts, dependencies, evidence, profile compatibility, catalogs,
solo transitions, and endings. Finalize only the current compiled draft with
explicit confirmation. Inspect the immutable artifact through `content_pack`
and verify its schema, `coc7e` identity, checksum, source binding, and counts.

Stop at the built artifact unless the user separately requested installation.
Import inactive. Activate only against a fresh campaign revision, and never
guess progress remaps for a replacement.
