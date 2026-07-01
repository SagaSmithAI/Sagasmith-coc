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
