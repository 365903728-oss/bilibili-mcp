# QA: Search Response Hardening

## QA Session

- Title: Explicit-empty versus malformed search response
- Date: 2026-08-09
- Version or commit: unreleased `1.11.3` source baseline at `741dcf0`
- Owner: Codex
- Related ticket: `docs/agent-memory/handoffs/2026-08-09-search-response-hardening-task-ticket.md`
- QA type: `MCP tool change | regression`

## Scope

In scope:

- Search response shape validation and its one-retry boundary.
- Direct search behavior and public MCP error mapping.
- Full local regression and package-safety gates.

Out of scope:

- Live Cookie output, anonymous search, true-empty reclassification, external desktop clients, versioning, publication, and deployment.

## Preconditions

- [x] Isolated branch and `741dcf0` baseline recorded.
- [x] Package version remains `1.11.3`.
- [x] Tests use synthetic credential headers and mocked Bilibili responses.
- [x] No real credential value is read or recorded by the tests.

## Automated Baseline

- Build: `npm run build` passed.
- Focused tests: 2 files / 36 tests passed.
- Full tests: 41 files / 862 tests passed.
- Stdio: selected real child-process `initialize` -> exact `tools/list` -> representative `tools/call` passed, 1 selected / 11 skipped.
- Pack: 185 files, 1,088,660 packed bytes, 1,718,633 unpacked bytes; required entrypoints present and forbidden paths zero.
- Audit: zero production vulnerabilities across 97 dependencies.

## MCP And Search Behavior

- [x] Explicit `result: []` returns `{ query, results: [] }` after one request.
- [x] Missing and non-array results each make at most two endpoint requests and then fail as `UpstreamResponseError`.
- [x] A valid second response recovers after the first malformed response.
- [x] A search `NetworkError` remains the original error and receives no outer retry.
- [x] HTTP 503 and raw `ECONNRESET` errors receive no endpoint-level retry, so the search layer cannot multiply the shared HTTP retry policy.
- [x] Aborting during the 500 ms shape backoff rejects as `AbortError` before a second request.
- [x] The MCP error is text-only, sets `isError=true`, omits `structuredContent`, and reports `UPSTREAM_RESPONSE_INVALID`.
- [x] Non-empty arrays continue to normalize/filter rows under the existing contract.

## Security And Privacy Checks

- [x] The endpoint-local shape retry emits no query, Cookie, response body, or credential value.
- [x] No public success schema, credential requirement, or response-size limit changed.
- [x] Package output excludes source, tests, QA, agent memory, local config, and credential paths.
- [x] Value-free scan found zero private-key, GitHub-token, npm-token, AWS-key, JWT, or secret-filename findings; the only Cookie-shaped changed-file match is historical verification prose with no value.
- [x] `git diff --check` passed and `package-lock.json` retained blob `70cee9306932ebb2d32bc1cce4016770cd2963d4`.

## Result

- Overall result: `pass with caveats`
- Blocking issues: none
- Non-blocking caveat: because the original transient raw envelope was not captured, this patch fixes the provable missing/non-array ambiguity but intentionally keeps an explicit empty array as a legitimate result.
- Follow-up tickets: none; reconsider true-empty retry only with captured upstream evidence.
- Codemap update status: checked and left unchanged; existing search navigation remains accurate.
- Research note: not required because local source, tests, and captured runtime diagnosis are authoritative.
- Independent review: initial review found the shared retry helper's raw-system-code fallback; after the local shape-only correction, risk, standards, and specification re-reviews returned PASS with no remaining P0-P3.
