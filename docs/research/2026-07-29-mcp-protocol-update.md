# Research Topic

- Topic: MCP `2026-07-28` stable protocol release
- Date: 2026-07-29 (Asia/Shanghai)
- Owner: Codex
- Related task: User-requested research into today's MCP protocol update
- Refresh before: upgrading the MCP SDK, adding modern-protocol support, or changing transports

## Question

What MCP protocol update became stable today, what changed normatively from
`2025-11-25`, how does version compatibility work, and what is the initial
impact on `@xzxzzx/bilibili-mcp`?

## Context

Why this matters for `@xzxzzx/bilibili-mcp`:

- The repository is a TypeScript MCP server, so a new stable protocol revision
  can affect SDK choice, server startup, handler registration, interoperability,
  and future conformance requirements.
- The current worktree uses `@modelcontextprotocol/sdk` v1, a singleton
  low-level `Server`, schema-first handlers, and stdio only. It must not be
  treated as if it already speaks the new protocol merely because a newer SDK
  exists.

What decision or implementation this may affect:

- Whether to keep the current stable legacy-era server for now or open a
  separate, bounded SDK v2 and dual-era migration ticket.

## Sources

Only MCP project, official SDK, GitHub release/API, and npm registry sources
were used.

| Source | Type | Date checked | Notes |
|---|---|---|---|
| [The `2026-07-28` Specification](https://blog.modelcontextprotocol.io/posts/2026-07-28/) | official project blog | 2026-07-29 | Stable-release overview from the MCP lead maintainers; the tagged specification remains normative. |
| [MCP `2026-07-28` release](https://github.com/modelcontextprotocol/modelcontextprotocol/releases/tag/2026-07-28) | official release | 2026-07-29 | Stable, non-prerelease release; published `2026-07-28T16:47:49Z` (`2026-07-29 00:47:49+08:00`), target commit `5f5440bb26a62e2cf3440b92da5a667efa03b267`. |
| [Stable `2026-07-28` changelog at the release tag](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2026-07-28/docs/specification/2026-07-28/changelog.mdx) | official specification source | 2026-07-29 | Normative change inventory against `2025-11-25`; file blob `dc5c9a9cf3e6895504534cf3f300514394d8c6ae`. |
| [Published `2026-07-28` changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog) | official specification | 2026-07-29 | Human-readable dated specification change list. |
| [Versioning and compatibility](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning) | official specification | 2026-07-29 | Defines modern, legacy, dual-era behavior, per-request version selection, fallback, and the compatibility matrix. |
| [`server/discover`](https://modelcontextprotocol.io/specification/2026-07-28/server/discover) | official specification | 2026-07-29 | Required server RPC; optional client preflight and recommended stdio compatibility probe. |
| [Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http) | official specification | 2026-07-29 | New POST-only, sessionless, header-validated HTTP behavior and legacy fallback rules. |
| [Deprecated features registry](https://modelcontextprotocol.io/specification/2026-07-28/deprecated) | official specification | 2026-07-29 | Confirms deprecation is not removal and lists earliest removal dates. |
| [2026 release-candidate announcement](https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/) | official project blog | 2026-07-29 | Prior announcement from 2026-05-21, used to distinguish the preview from today's stable release. |
| [TypeScript SDK repository](https://github.com/modelcontextprotocol/typescript-sdk) | official SDK source | 2026-07-29 | v2 is the stable split-package line for the new revision; v1 continues bug and security fixes for at least six months after v2 release. |
| [`@modelcontextprotocol/server@2.0.0`](https://github.com/modelcontextprotocol/typescript-sdk/releases/tag/%40modelcontextprotocol%2Fserver%402.0.0) | official SDK release | 2026-07-29 | SDK implementation release, published `2026-07-27T23:55:41Z`; distinct from the protocol release. |
| [TypeScript SDK v1-to-v2 migration](https://ts.sdk.modelcontextprotocol.io/v2/migration/upgrade-to-v2) | official SDK guide | 2026-07-29 | Split packages, codemod boundary, method-string handlers, and manual migration requirements. |
| [TypeScript SDK support for `2026-07-28`](https://ts.sdk.modelcontextprotocol.io/v2/migration/support-2026-07-28) | official SDK guide | 2026-07-29 | Modern protocol is an explicit serving/connection choice; documents `serveStdio`, dual-era defaults, wire injection, and cache defaults. |
| `npm view @modelcontextprotocol/{sdk,server,core} version dist-tags --json` | live npm registry CLI output | 2026-07-29 | `@modelcontextprotocol/sdk` latest `1.30.0`; `@modelcontextprotocol/server` and `@modelcontextprotocol/core` latest `2.0.0`. |

## Findings

### What actually happened today

- The MCP project published stable protocol revision `2026-07-28` at
  `2026-07-28T16:47:49Z`, which is `2026-07-29 00:47:49` in Asia/Shanghai.
  The release is neither a draft nor a prerelease.
- The new stable revision is identified by the date `2026-07-28`, targets
  commit `5f5440bb26a62e2cf3440b92da5a667efa03b267`, and supersedes the prior
  stable revision `2025-11-25`.
- This is a stable-specification event. The release candidate was announced on
  2026-05-21, and TypeScript SDK v2 packages were published separately shortly
  before the final protocol tag. The RC article and SDK releases are useful
  implementation context, but neither is the normative stable specification.

### Core protocol changes since `2025-11-25`

1. **Stateless and sessionless core**
   - The `initialize` / `notifications/initialized` handshake is removed for
     the modern era.
   - Protocol version and client capabilities are required in per-request
     `_meta`; client identity is a `SHOULD`, and server identity is a `SHOULD`
     on each result's `_meta`.
   - Protocol-level sessions and `Mcp-Session-Id` are removed. Cross-call state
     must use explicit server-minted handles passed in ordinary application
     data.
   - Servers must implement `server/discover`; clients may call it for
     capabilities and version selection and should use it as the stdio
     backward-compatibility probe.

2. **Server-to-client interaction is restructured**
   - Servers no longer initiate independent JSON-RPC requests.
   - Multi Round-Trip Requests replace that channel: a server returns
     `resultType: "input_required"` plus `inputRequests`; the client gathers
     answers and retries the original request with `inputResponses` and
     `requestState`.
   - Every result now has `resultType`: `"complete"` or `"input_required"`.
     Clients must interpret a legacy result without it as `"complete"`.

3. **Notifications and streams change**
   - The HTTP GET stream and `resources/subscribe` /
     `resources/unsubscribe` are replaced by a client-opened
     `subscriptions/listen` POST-response stream.
   - `ping`, `logging/setLevel`, and
     `notifications/roots/list_changed` are removed in the modern era.
     Logging level becomes per-request metadata.
   - SSE resumption and redelivery via `Last-Event-ID` and SSE event IDs are
     removed. A client must retry an interrupted request with a new request ID.

4. **Tasks become an extension**
   - Experimental core Tasks move to the optional
     `io.modelcontextprotocol/tasks` extension.
   - The extension uses `tasks/get`, `tasks/update`, and cancellation; it
     removes `tasks/list` and the blocking `tasks/result` model.

### Additional normative changes

- `ClientCapabilities` and `ServerCapabilities` gain an `extensions` map;
  extensions are optional and require support from both sides.
- Streamable HTTP requires `MCP-Protocol-Version` and `Mcp-Method`, plus
  `Mcp-Name` for named operations. Header/body mismatch is rejected with HTTP
  400 and MCP error `-32020`.
- Tool parameters can opt into `Mcp-Param-*` HTTP header mirroring through
  `x-mcp-header`, with strict validation and encoding rules.
- Cacheable discovery/list/read results require `ttlMs` and `cacheScope`.
  Servers should return tools in a deterministic order.
- OpenTelemetry `_meta` conventions are documented for `traceparent`,
  `tracestate`, and `baggage`.
- Resource-not-found changes from MCP error `-32002` to JSON-RPC Invalid Params
  `-32602`.
- The MCP-reserved JSON-RPC server-error range is `-32020` through `-32099`.
  The modern errors are `HeaderMismatch` `-32020`,
  `MissingRequiredClientCapability` `-32021`, and
  `UnsupportedProtocolVersion` `-32022`.
- Authorization hardening requires validation of a present RFC 9207 `iss`,
  an appropriate Dynamic Client Registration `application_type`, and
  issuer-bound credential persistence with no cross-issuer reuse.
- Tool input/output schemas can use full JSON Schema 2020-12; output schemas
  and `structuredContent` may represent any JSON value, subject to documented
  `$ref` and resource-bound rules.
- URL-mode `notifications/elicitation/complete` and `elicitationId` are
  removed; correlation moves to `requestState`.
- The generated JSON schema now represents numeric minimum, maximum, and
  default values as numbers rather than integers only.

### Deprecation is not removal

- Roots, Sampling, Logging, Dynamic Client Registration, HTTP+SSE, and the
  `includeContext` values `"thisServer"` / `"allServers"` are deprecated.
- Roots, Sampling, Logging, and Dynamic Client Registration remain in this
  specification. Their earliest eligible removal is the first revision
  released on or after 2027-07-28.
- The new lifecycle policy requires a minimum twelve-month deprecation window.
  No feature has yet been removed under that policy.

### Compatibility implications

- `2026-07-28` and later are the modern era; `2025-11-25` and earlier are the
  legacy, initialization-based era.
- A modern request declares its version independently. An unsupported version
  must produce `UnsupportedProtocolVersionError` `-32022` with supported
  versions, after which the client should select a mutual version and retry.
- Modern-only client plus legacy-only server fails. Legacy-only client plus
  modern-only server also fails.
- A dual-era implementation interoperates with both. On stdio, a dual-era
  client probes with `server/discover` and falls back to `initialize` only
  when the result is not a recognized modern response/error. On HTTP, it
  inspects a failed modern request before deciding to fall back.
- Therefore, adopting `2026-07-28` does not force every deployed implementation
  to break immediately, but moving a server to modern-only behavior is a
  deliberate compatibility break.

### SDK releases are separate from protocol conformance

- TypeScript SDK v2 is a stable split-package line:
  `@modelcontextprotocol/server`, `@modelcontextprotocol/client`, and
  `@modelcontextprotocol/core`. The old monolithic
  `@modelcontextprotocol/sdk` remains the v1 line.
- The official repository promises v1 bug and security fixes for at least six
  months after v2 release; live npm tags currently report v1 `1.30.0` and v2
  `2.0.0`.
- Merely installing v2 does not make a hand-constructed
  `Server` / `McpServer` connected to `StdioServerTransport` speak
  `2026-07-28`; that shape remains 2025-era.
- Modern or dual-era stdio serving requires
  `serveStdio(() => buildServer())`. Its default accepts legacy openings too;
  `{ legacy: "reject" }` is an explicit modern-only choice.
- The low-level v2 handler API uses method strings such as
  `setRequestHandler("tools/call", handler)` instead of v1 schema-first
  registration.
- For modern requests, the SDK owns wire bookkeeping such as `resultType`,
  reserved per-request metadata, and required cache fields. Its conservative
  default cache hints are `ttlMs: 0` and `cacheScope: "private"`.

## Applicability To This Project

Applies:

- Current local source depends on `@modelcontextprotocol/sdk` `^1.27.1`; the
  current lockfile resolves `1.27.1`.
- The server is stdio-only and uses a singleton low-level `Server`,
  `StdioServerTransport`, and v1 schema-first handlers. It currently serves the
  legacy era, not `2026-07-28`.
- Dual-era clients can continue to reach it through legacy fallback.
  Modern-only clients cannot.
- A future migration must cover both the v1-to-v2 API change and the separate
  decision to serve the modern era. The smallest compatibility-preserving
  target is v2 plus `serveStdio(factory)` in its default dual-era mode.
- Because current capabilities expose tools only, the Roots, Sampling, and
  Logging deprecations do not require feature migration here.

Does not apply:

- `Mcp-Session-Id`, HTTP GET streams, `Mcp-Method` / `Mcp-Name`,
  `x-mcp-header`, HTTP Origin validation, and HTTP fallback behavior do not
  affect the current stdio-only runtime.
- There is no need to add Tasks, MCP Apps, HTTP transport, caching policy, or
  new extension infrastructure merely because the specification now permits
  them.
- The server's Bilibili API behavior and existing tool response contracts do
  not need speculative changes before a bounded SDK migration is approved.

## Decision Impact

Recommended project action:

- **Do not change code immediately.** Record this update as research and open a
  separate migration ticket only when modern-client compatibility or explicit
  `2026-07-28` conformance becomes an approved goal.
- When that ticket is opened, preserve dual-era compatibility by default:
  migrate to the v2 split packages, convert the singleton server into a
  factory, convert schema-first handlers to method strings, enter through
  `serveStdio(factory)`, and test both modern discovery and legacy
  initialization.
- Do not manually duplicate SDK-owned wire metadata, `resultType`, or cache
  fields in Bilibili business handlers.

Rules or files that may need updates in that future ticket:

- `package.json`
- `package-lock.json`
- `src/server.ts`
- `src/index.ts`
- `src/cli.ts`
- MCP stdio smoke and handler tests
- user-facing compatibility documentation only after behavior is verified

## Risks And Unknowns

- The protocol specification defines compatibility behavior, but it does not
  provide a current support matrix for every real host used by this project.
  Host adoption must be checked before choosing a migration deadline.
- The TypeScript v2 line is newly stable. A migration should pin reviewed
  versions and run the full build, test, stdio smoke, package, and client
  interoperability checks.
- A superficial package-only upgrade can leave the server on the 2025 era.
  Conversely, setting `legacy: "reject"` would intentionally drop older
  clients.
- The RC article predates the final schema. Final PR
  [#3002](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/3002)
  moved `serverInfo` into result `_meta` and changed per-request `clientInfo`
  from required to `SHOULD`; final dated specification and SDK v2 migration
  docs take precedence over RC examples.
- The stable-release blog is a useful overview, while the stable GitHub
  release, dated specification, and tagged changelog are the authoritative
  evidence for protocol requirements.
- The version is named for 2026-07-28 because that is its UTC release date;
  the observed “today” date is 2026-07-29 in Asia/Shanghai.

## Staleness Notes

Refresh this research when:

- the MCP project publishes a revision after `2026-07-28`
- TypeScript SDK v2 changes its default era negotiation or stdio serving APIs
- v1 support status or npm dist-tags change
- a real project host becomes modern-only
- a v2 migration ticket is approved

## Follow-Up

- [ ] Before any migration, inventory the actual MCP hosts used with this
  package and verify their legacy, modern, or dual-era behavior.
- [ ] If migration is approved, create a bounded ticket for SDK v2 plus
  dual-era stdio support; do not mix it into unrelated ASR work.
- [ ] Add one modern `server/discover` smoke test and retain one legacy
  `initialize` smoke test before claiming `2026-07-28` support.
