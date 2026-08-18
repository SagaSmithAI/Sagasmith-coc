---
name: coc-module-generator
description: Create, review, revise, and finalize Call of Cthulhu 7e scenario or rules Packs through the authoritative SagaSmith CoC MCP authoring facade.
---

# CoC Module Generator

Build one reviewed `sagasmith.content-package` v2 artifact for an authoring
campaign whose authoritative `system_id` is `coc7e`.

Read [workflow.md](references/workflow.md) before starting or editing a draft.
Read [system-profile.md](references/system-profile.md) before saving Package
decisions. Read [narrative-patterns.md](references/narrative-patterns.md) only
when selecting the composition shape for a long investigation or campaign.

## Boundaries

- Stay in Lobby and use only the current native `module_draft`,
  `rulebook_draft`, and `content_pack` facades exposed by CoC MCP.
- Bind the campaign's exact 7e Classic/Pulp profile. Do not infer the system,
  era, or ruleset from title, genre, filename, or prose.
- Let the Agent own source interpretation and semantic repair; let the CoC
  package own deterministic mechanics and validation; let MCP own revisions,
  evidence receipts, idempotency, finalization, installation, and activation.
- Keep one-book interpretation in the draft evidence and audit history. Do not
  add source-specific parsing heuristics to Core, the CoC package, or MCP.
- Never fabricate clues, SAN expressions, evidence, checksums, actor facts,
  dependencies, scene keys, statblocks, or chase geometry.
- Default to building the immutable artifact only. Installation and campaign
  activation require separate user authorization.

## Completion

Deliver the artifact handle, Pack id and version, checksum, ruleset/era, source
and draft revisions, reviewed component counts, material warnings, and whether
the artifact is built, imported, or active.
