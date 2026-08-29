# CoC Workbench Agent Guide

Follow the repository root `AGENTS.md`. This UI is a projection and control
surface for the authenticated gateway in sibling `packages/mcp`.

- Never connect the browser directly to MCP state or accept caller-supplied
  `principal_id`.
- Use the modern deterministic catalog and bounded Host projection. Refresh on
  authorization/catalog changes; `tools/list_changed` is legacy compatibility
  only. Do not simulate unavailable tools.
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
