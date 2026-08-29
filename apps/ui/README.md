# SagaSmith CoC UI

[Website](https://sagasmithai.github.io) · [Platform overview](https://github.com/SagaSmithAI/.github/blob/main/profile/README.md) · [SagaSmith Web](https://github.com/SagaSmithAI/SagaSmith-Web) · [Content catalog](https://github.com/SagaSmithAI/SagaSmith-dnd-content-library)

> Current source: `sagasmith-coc/apps/ui`. The former standalone CoC UI repository is archived.

Keeper-facing Astro/React workbench for the current `sagasmith-coc-mcp` contract.
It covers campaign-scoped investigation, CoC Module Pack state, investigators,
chases/combat, branches/snapshots/revisions, and an advanced console populated
from the Host's current bounded projection of the stable native MCP catalog.

## Authority boundary

The browser does **not** connect to the stdio MCP server directly and never sends
`principal_id`. It calls an authenticated gateway at:

```text
POST {PUBLIC_COC_GATEWAY_BASE}/api/coc/mcp/tool
Cookie: <authenticated session>
Content-Type: application/json

{"tool":"campaign_query","arguments":{"action":"list"}}
```

The gateway owns browser authentication and derives requester/workload identity
server-side. It may reuse pooled HTTP connections, but it sends a target-specific
signed delegation on every MCP request and never pools a principal, campaign, or
authorization decision. The UI refuses caller-supplied `principal_id`; MCP remains
authoritative for authorization, phases, random streams, revisions, idempotency,
and atomic settlement. The modern catalog is deterministic; only the explicit
legacy adapter uses sticky exposure and `tools/list_changed`.

The authenticated gateway is implemented by the sibling `packages/mcp`
directory and can serve this built UI directly. Connection reuse is bounded and
never carries implicit principal or campaign authority.

## Run

```bash
npm install
npm test
npm run check
npm run dev
```

Configuration:

- `PUBLIC_COC_GATEWAY_BASE` — gateway origin, default `http://127.0.0.1:8768`
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
Live failures remain visible and never fall back to demo data. The gateway is an
application boundary, not a license to forward browser tokens to MCP.
