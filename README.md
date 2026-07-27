# SagaSmith CoC UI

**Prototype Keeper workbench for the SagaSmithAI Call of Cthulhu 7e stack.** This repository explores how investigators, clues, SAN, scenes, handouts, chases, and snapshot continuity should be presented during a live investigation.

## Current status

The repository is a UI prototype, not a production CoC client. The CoC runtime currently exposes a JSON CLI and has not yet reached the independent MCP/session-exposure boundary used by the D&D reference stack. Until that boundary and an authenticated gateway exist:

- no browser view should claim authoritative writes;
- Keeper-only scene data must never be filtered only in client code;
- commercial scenario content must not be bundled into the frontend;
- UI mock data must remain clearly labeled.

## Intended architecture

```text
Keeper Workbench
    ↓ authenticated, audience-safe gateway
SagaSmith CoC MCP (session exposure and actor-scoped state)
    ↓
sagasmith-coc + sagasmith-core
```

The future workbench should cover the current scene and visibility, investigator sheets, clue/handout graph, SAN and insanity state, chase/combat timeline, scenario node navigation, and branch-aware snapshots.

## Development

Requires Node.js 22.12+.

```bash
npm install
npm run dev
npm run build
npm run preview
```

## License

Original code is licensed under Apache-2.0. Call of Cthulhu and commercial scenario content belong to their respective rights holders and are not included.
