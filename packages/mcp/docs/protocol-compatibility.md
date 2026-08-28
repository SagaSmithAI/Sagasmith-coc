# CoC MCP protocol compatibility / 协议兼容

| Boundary | MCP 2026-07-28 | Legacy migration path |
|---|---|---|
| Discovery | Optional `server/discover`; request metadata on every call | `initialize` / `initialized` |
| Version and client capabilities | Every request `_meta` | Negotiated once at initialization |
| HTTP routing | `Mcp-Method` / `Mcp-Name`; no session id required | Streamable HTTP session adapter |
| Identity | Per-request `sagasmith.auth-context/v2`, target/audience bound | Signed v1 context, retained only for compatibility |
| Cross-call workflow | Explicit `exposure_handle` or campaign/revision parameters | Connection exposure adapter |
| `tools/list` | Complete, sorted, private-cache scope, 300 s TTL | Exposure-filtered; real changes may send `tools/list_changed` |
| Tool execution | Role, phase, revision, identity, and idempotency rechecked per call | Same authoritative handlers and checks |
| stdio / HTTP | Same schemas, handlers, errors, and authority semantics | Same compatibility adapter on both transports |

The modern catalog never changes because another request opened or edited an
exposure. A handle is only a server-issued name with an owner and expiry; it is
not a capability. Shared HTTP pools may reuse sockets, but must not pool a
principal, campaign, exposure, or authorization decision.

现代目录不会因其他请求打开或修改 exposure 而变化。handle 只是带 owner 与过期时间的
服务器签发名称，不是 capability。HTTP 连接池可以复用连接，但不得池化 principal、
campaign、exposure 或授权决定。

## Upgrade

1. Deploy `sagasmith-core` containing auth-context v2 support.
2. Deploy this dual-era MCP and verify the legacy stdio and HTTP contract tests.
3. Upgrade the Host/Agent to send v2 delegation on every modern request and use
   the stable catalog.
4. Observe modern versus legacy request counts. Remove the legacy adapter only
   after all supported clients have migrated.

## Rollback

Application rollback is safe while database schema compatibility is retained:
stop traffic, restore the previous MCP/Domain/Core component lock as one set,
then restart and run the legacy contract smoke test. Never downgrade only the
MCP SDK while leaving Host request semantics on 2026-07-28. Database snapshot
schema rollback still requires restoring the matching pre-upgrade backup.

升级顺序必须是 Core → 双时代 MCP → Host/Agent；回滚必须把 MCP、Domain、Core 与组件锁
作为一组恢复。不得只降级 SDK 而继续发送 2026-07-28 请求。数据库 snapshot schema 的
回滚仍需恢复升级前匹配备份。
