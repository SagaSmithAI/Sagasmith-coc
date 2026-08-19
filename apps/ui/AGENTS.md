# CoC Workbench Agent Guide

Follow the repository root `AGENTS.md`. This UI is a projection and control
surface for the authenticated sticky-session gateway in sibling `packages/mcp`.

- Never connect the browser directly to MCP state or accept caller-supplied
  `principal_id`.
- Refresh the real native tool schema after `tools/list_changed`; do not keep a
  fixed catalog or simulate unavailable tools.
- Render only audience-filtered server DTOs and resolution presentations.
- Keep demo mode explicit, read-only, and visually distinct. A live failure must
  never silently fall back to demo data.
- Keep source and Pack rights visible; public catalog presence is not a license.

Validate UI changes from the repository root:

```powershell
npm ci
npm run test:ui
npm run build:ui
```
