# Research Note: Strix Follow-up Dependency Refresh

## Research Topic

- Topic: Compatible MCP SDK refresh for current production advisories
- Date: 2026-08-05
- Owner: Codex
- Related task: `2026-08-05-strix-deepseek-security-remediation-task-ticket.md`
- Refresh before: any later dependency or release decision

## Question

Can the five Strix-filed transitive advisories and the existing Hono static-file
advisory be removed without an MCP v2 migration or transport redesign?

## Context

The current package uses the monolithic TypeScript SDK v1 and only starts the
legacy stdio transport. The security task may refresh the compatible v1 SDK and
lockfile, but must not begin the separate SDK v2/protocol-modernization work.

## Sources

| Source | Type | Date checked | Notes |
|--------|------|--------------|-------|
| `npm audit --omit=dev --json` in the exact `0a1b` worktree | live npm CLI | 2026-08-05 | Reports five vulnerable packages/nodes plus the SDK effect chain; values contain no credentials. |
| `npm ls fast-uri hono ip-address --all --json` | local dependency tree | 2026-08-05 | Confirms SDK-to-AJV/Hono/express-rate-limit paths and a dev-only second ip-address path. |
| `npm view @modelcontextprotocol/sdk version dependencies --json` | live npm registry | 2026-08-05 | Current compatible v1 release is 1.30.0. |
| `npm view fast-uri/ip-address/hono/@hono/node-server version` | live npm registry | 2026-08-05 | Current versions are 4.1.2, 10.4.0, 4.13.0, and 2.1.0. |
| [GHSA-7p8r-x3mc-p8w7](https://github.com/advisories/GHSA-7p8r-x3mc-p8w7) | GitHub Advisory Database | 2026-08-05 | fast-uri host-confusion advisory. |
| [GHSA-mwp4-54f8-5fhr](https://github.com/advisories/GHSA-mwp4-54f8-5fhr) | GitHub Advisory Database | 2026-08-05 | ip-address leading-zero parsing advisory. |
| [GHSA-22jq-vg5j-6vgg](https://github.com/advisories/GHSA-22jq-vg5j-6vgg) | GitHub Advisory Database | 2026-08-05 | ip-address mapped/NAT64 classification advisory. |
| [GHSA-4xrf-jv44-h6hh](https://github.com/advisories/GHSA-4xrf-jv44-h6hh) | GitHub Advisory Database | 2026-08-05 | ip-address CIDR classification advisory. |
| [GHSA-8j4g-w8fx-2239](https://github.com/advisories/GHSA-8j4g-w8fx-2239) | GitHub Advisory Database | 2026-08-05 | Hono CORS ReDoS advisory. |
| [GHSA-frvp-7c67-39w9](https://github.com/advisories/GHSA-frvp-7c67-39w9) | GitHub Advisory Database | 2026-08-05 | Existing @hono/node-server serve-static advisory. |

## Findings

- `@modelcontextprotocol/sdk@1.30.0` is inside the current v1 line and inside
  the existing `^1.27.1` semantic range, but the lockfile remains pinned to
  1.27.1 until refreshed.
- The current exact installed versions are `fast-uri@3.1.4`, `hono@4.12.31`,
  `ip-address@10.2.0`, and `@hono/node-server@1.19.14`.
- Hono, node-server, and ip-address vulnerable sinks remain unreachable from
  the project's stdio-only imports. AJV/fast-uri is loaded by the SDK server,
  but this project does not call the dynamic elicitation/schema path that would
  parse attacker-controlled URI formats.
- Reachability lowers current exploitability but does not justify retaining a
  stale production lockfile when a compatible SDK refresh is available.

## Applicability To This Project

Applies:

- Raise the direct SDK minimum to `^1.30.0` and refresh the lockfile without
  overrides if the registry resolves all affected transitives.
- Re-run the full legacy stdio discovery/call tests because a v1 SDK minor
  update can still change runtime behavior.

Does not apply:

- SDK v2 split packages, `serveStdio(factory)`, `server/discover`, HTTP/SSE,
  Tasks, MRTR, or any protocol migration.

## Decision Impact

Use the smallest compatible SDK/lock refresh. Do not add dependency overrides
unless the normal 1.30.0 resolution leaves a reported production advisory, and
stop for Codex review before any override or broader migration.

## Risks And Unknowns

- Registry/advisory state can change after this note.
- A new SDK minor can expose compatibility regressions even when semver permits
  it; build, 721-plus tests, stdio smoke, and package inspection are mandatory.

## Resolution (2026-08-05, final)

With the registry reachable again, the remaining production advisory closed
via a normal compatible lockfile refresh — no override, no major:

- `npm view fast-uri@3.1.5 version` → 3.1.5 exists; it is the latest 3.x
  release (`npm view fast-uri version` / the `latest` dist-tag is 4.1.2, a
  new major outside ajv's `^3.0.1` range, so it is not a compatible target).
- `npm update fast-uri` resolved the tree to `fast-uri@3.1.5` within the
  existing `^3.0.1` range; the lockfile diff is fast-uri-only (resolved URL +
  integrity entries); `package.json` is unchanged by this step.
- `npm audit --omit=dev --json` now succeeds and reports **zero
  vulnerabilities** (`total: 0`, 97 prod / 665 total dependencies).
- The earlier classification of `fast-uri@3.1.4` as an unreachable residual
  is superseded; no 4.1.2 upgrade or override was ever needed because 3.1.5
  carries the fix inside the compatible range.

## Follow-Up

- [x] Record the post-refresh `npm audit --omit=dev --json` result in the QA
  and Claude report without printing secrets — done (0 vulnerabilities,
  fast-uri@3.1.5).
