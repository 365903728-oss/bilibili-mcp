# Task Ticket: Search Response Hardening

## Ticket

- ID: `SEARCH-2026-08-09`
- Title: Distinguish empty search results from malformed upstream responses
- Status: `done`
- Owner: `Codex`
- Source: User-authorized follow-up after the 2026-08-09 live search diagnosis

## Objective

Keep an explicit Bilibili `result: []` as a successful empty search while retrying a missing or non-array result once and then failing closed through the existing structured upstream-response error contract.

## Scope

In scope:

- Endpoint-local validation of the successful search payload shape.
- One additional request only for the search-specific malformed shape.
- Focused search and public MCP error-boundary regressions.
- Full build, test, stdio, package, audit, diff, and secret verification.
- Isolated branch, commit, push, PR, and merge delivery.

Out of scope:

- Generic HTTP retry changes, anonymous search, schema/tool-name changes, reclassifying a non-empty result array whose rows all normalize away, or retrying an explicit empty array.
- Real Cookie output, version bumping, tags, npm/MCP Registry publication, GitHub Releases, or deployment.

## Files To Inspect Or Edit

Expected edit:

- `src/bilibili/search.ts`
- `tests/bilibili-search.test.ts`
- `tests/server-error-next-steps.test.ts`
- This ticket, QA, and project-memory evidence.

Do not touch:

- Shared HTTP behavior, package dependencies, `package-lock.json`, generated `dist`, workflows, release metadata, or the dirty main user worktree.

## Acceptance Criteria

- [x] Explicit `{ result: [] }` succeeds with one search request.
- [x] Missing or non-array `result` retries once, then throws `UpstreamResponseError`.
- [x] A valid second response recovers after one malformed response.
- [x] `NetworkError`, HTTP-status errors, and raw `ECONNRESET`-style errors are preserved without an extra endpoint-level retry.
- [x] Aborting during the 500 ms shape backoff prevents the second request.
- [x] The public MCP boundary returns text-only `UPSTREAM_RESPONSE_INVALID` without `structuredContent`.
- [x] Public tool names, schemas, and successful response shapes remain unchanged.
- [x] Credentials, Cookies, tokens, `.env` content, and private values are not printed or committed.
- [x] `docs/agent-memory/codemap.md` was checked; the existing search-module and test navigation remains accurate.

## Verification

- `npx vitest run tests/bilibili-search.test.ts tests/server-error-next-steps.test.ts`
- `npm run build`
- `npm test`
- Selected real stdio JSON-RPC smoke.
- `npm pack --dry-run --json --ignore-scripts`
- `npm audit --omit=dev --json`
- `git diff --check`, lockfile fingerprint, value-free secret scan, and two-axis final review.

## Risks And Rollback

- Risk: a malformed successful payload can add one bounded request and 500 ms of abort-aware backoff. Normal, explicitly empty, network, HTTP-status, system-code, and API-error paths add no endpoint-level request.
- Limitation: the original transient response envelope was not retained, so this patch does not claim that every explicit empty result is anomalous.
- Rollback: before merge, abandon only this isolated branch; after merge, use a normal revert PR.

## Stop And Report Conditions

Stop if the fix requires generic HTTP behavior changes, more than one extra search request, a real credential value, a package/version change, or a public schema change.
