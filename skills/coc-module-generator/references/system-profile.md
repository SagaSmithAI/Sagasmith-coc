# Call of Cthulhu 7e Package profile

The live CoC MCP schema and deterministic CoC validator are authoritative. These
notes constrain Agent decisions; they do not replace native schemas.

## Identity

- `system_id`: `coc7e`
- portable Module id prefix: `coc7e.module.`
- classifications: `scenario`, `campaign`, `solo_adventure`, `handout_pack`
- compatibility edition: `7e`
- rulesets: `classic`, `pulp`, or both when supported by the source
- scenarios, campaigns, and solo adventures require a reachable ending
- solo adventures require an evidence-backed supported solo profile

Pack classification is orthogonal to runtime design classification. Preserve
the Pack value above while runtime design uses `authored_scenario`,
`emergent_seed`, or `emergent_episode`. Emergent seeds and episodes may omit an
ending until the table asks for a bounded finale; authored scenarios retain the
reachable-ending requirement. Runtime lineage and Scene Atlas links are
validated independently of Pack type.

## Required play-profile review

Use real source receipts for investigator count, supported/recommended ruleset,
era, estimated session range, pregenerated investigators, and solo support.
Ranges must be positive and ordered; the recommended ruleset must be included
in the supported rulesets.

## Catalogs and mechanics

Use the native CoC Package arrays for clues, handouts, encounters, hazards,
tomes, spells, and mechanics. Review exact clue truth and availability, SAN
triggers/expressions, pushed consequences, check intent, actor statblocks,
chases, Mythos facts, solo nodes, and Classic/Pulp differences.

Do not finalize when identity, source binding, required evidence, indispensable
clue routes, actor mechanics, dependencies, profile compatibility, or a
required ending remains undefined or conflicting.
