# SagaSmith CoC

Call of Cthulhu 7th Edition runtime for `sagasmith-core`.

The package exposes a portable JSON CLI used by nanobot and other agent
platforms through `SagaSmith-coc-skills`. It does not register platform-specific
agent tools and does not bundle commercial rulebooks. Users can ingest rule
documents they are permitted to use.

```bash
pip install "sagasmith-coc[documents]"
sagasmith-coc doctor --json
sagasmith-coc campaign start --name Arkham --json
```

Runtime coverage matches the SagaSmith D&D adapter layer: campaigns,
investigators, rules and scenario ingestion/retrieval, events, branch-aware
memory, snapshots, audited undo/redo, module scene indexes, and bounded JSON
responses. CoC-specific mechanics include validated Classic/Pulp investigator
sheets, d100 and opposed checks, SAN/insanity, melee/ranged combat, chases, and
development.

The data shape and adjudication coverage were reviewed against the open-source
CoC7 Foundry VTT system as an implementation reference. SagaSmith does not copy
its Foundry UI, compendiums, or commercial rules content.
