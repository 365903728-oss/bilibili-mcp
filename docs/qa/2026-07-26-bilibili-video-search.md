# QA Checklist: Bilibili Video Discovery

## QA Session

- Date: 2026-07-26
- Baseline commit: `54e3acdea74d04ac106d023cb90f3f8f7053a353`
- Package version: `1.8.0` (unchanged by this ticket)
- Owner: Codex
- Related: GitHub Issue #21, `docs/bilibili-video-search-prd.md`
- QA type: MCP tool change and credential flow

## Scope

In scope:

- `search_bilibili_videos` discovery, schema, dual output, mandatory credential precheck, normalization, error handling, package contents, and one real discovery-to-evidence workflow.

Out of scope:

- Pagination, ranking/filter options, non-Video search, automatic candidate evidence retrieval, release/version work, and Issue #20.

## Preconditions

- [x] Baseline branch and commit recorded.
- [x] Package version recorded.
- [x] Credentials are loaded only from approved local sources; no value is recorded here.
- [x] Local credential configuration exists and the 2026-07-26 login check returned `logged_in: true`.
- [x] First-party search contract is cached in `docs/research/2026-07-26-bilibili-video-search-contract.md`.

## Baseline

- [x] `npm run build` — passed.
- [x] `npm test` — 23 files, 299 tests passed.
- [x] Existing generated `docs/agent-memory/pending-learning-proposals.md` modification is excluded from feature work.

## Automated Acceptance

- [x] Focused search/schema/handler/error/smoke tests pass (6 files, 155 tests).
- [x] `npm run build` passes.
- [x] `npm test` passes (24 files, 327 tests).
- [x] `npm pack --dry-run --json` contains 128 intended package files and no test, local credential, `.env`, `.claude`, or `.codex` content.
- [x] `git diff --check` passes (line-ending notices only; no whitespace error).

## MCP Contract

- [x] `tools/list` exposes nine tools with `search_bilibili_videos` appended after the existing eight.
- [x] Search input requires `query` and bounds `limit` to 1-10 with default behavior 5.
- [x] Exact output schema matches the PRD and Issue #21.
- [x] Successful text and `structuredContent` contain the same object.
- [x] Validation and runtime errors omit `structuredContent`.
- [x] Existing eight tool schemas and behavior remain unchanged.

## Credential And Security

- [x] Missing local credentials stop before login/search network calls and return safe setup guidance.
- [x] Logged-out credentials stop before the search request.
- [x] Network failure during login remains a network error, not a credential or empty-result response.
- [x] Valid credentials are checked before search and sent only in memory.
- [x] Logs, fixtures, docs, report, diff, and package contents contain no real Cookie/token/private value; the final bounded scan covered 151 files with zero high-confidence findings.
- [x] Search result strings are treated as untrusted data; highlight markup is removed and descriptions are bounded.

## Real Workflow

- [x] Official SDK `Client + StdioClientTransport` lists the exact nine tools against local `dist/index.js`.
- [x] A real credentialed Chinese query returned four normal Video candidates with valid BVIDs and canonical HTTPS URLs.
- [x] No non-Video `ketang` row survives normalization (fixture coverage plus normal-Video-only live output).
- [x] Returned Video `BV1Eb411u7Fw` completed a bounded Part 4 `get_video_transcript` call for `函数`.
- [x] The transcript match returned `https://www.bilibili.com/video/BV1Eb411u7Fw/?p=4&t=1.12`.
- [x] SDK 1.27.1 completed both structured calls with no output-schema validation error.

## Client Compatibility

| Client | Version | Result | Notes |
|---|---|---|---|
| Official MCP TypeScript SDK | 1.27.1 | pass | Nine-tool stdio discovery, authenticated search, and transcript evidence call |
| Codex | current local | not tested | Non-blocking; official SDK exercised the required local output-schema path |
| Claude Desktop | — | not tested | Non-blocking |
| Cursor | — | not tested | Non-blocking |

## Documentation

- [x] Chinese and English READMEs document the same bounded search behavior and mandatory credential requirement.
- [x] Docs do not present search as personalized ranking, relevance proof, or exhaustive results.
- [x] Docs do not suggest putting Cookie values in MCP client config.

## Result

- Overall result: pass
- Blocking issues: none
- Non-blocking caveats: first-party endpoint is undocumented and may change; search can return recommendation-like rows for low-match queries
- Follow-up: Issue #20 remains separate
- Codemap status: updated for the new search module/tool/test route
