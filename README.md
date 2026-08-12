# SagaSmith CoC UI

Keeper-facing Astro/React workbench for the current `sagasmith-coc-mcp` contract.
It covers campaign-scoped investigation, CoC Module Pack state, investigators,
chases/combat, branches/snapshots/revisions, and an advanced console for all 43
native MCP tools.

## Authority boundary

The browser does **not** connect to the stdio MCP server directly and never sends
`principal_id`. It calls an authenticated, sticky-session gateway at:

```text
POST {PUBLIC_COC_GATEWAY_BASE}/api/coc/mcp/tool
Cookie: <authenticated session>
Content-Type: application/json

{"tool":"campaign_query","arguments":{"action":"list"}}
```

The gateway owns authentication, injects the bound principal, keeps one MCP
session sticky, forwards `tools/list_changed`, and returns the tool's structured
result. The UI refuses caller-supplied `principal_id`; MCP remains authoritative
for authorization, dynamic exposure, random streams, revisions, idempotency, and
atomic settlement.

No gateway is implemented in this repository. Web hosting and the authenticated
gateway belong to the separate web-application task.

## Run

```bash
npm install
npm test
npm run dev
```

Configuration:

- `PUBLIC_COC_GATEWAY_BASE` — gateway origin, default `http://127.0.0.1:8767`
- `PUBLIC_COC_UI_MODE=demo` — explicit read-only demo mode

For a one-off local demo, open `/?demo=1`. Demo data is visibly marked,
read-only, and is not evidence that either sample campaign has been backtested.
Live connection failures never silently fall back to demo data.

## Production build

```bash
npm run build
```

The output is a static client in `dist/`; deploy it behind the same authenticated
origin as the gateway or configure CORS and credential handling deliberately.
