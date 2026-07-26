# Codex To Claude Handoff: Bounded Authenticated Bilibili Video Discovery

> Status update (2026-07-26): the user explicitly replaced delegated execution
> with direct Codex execution. This file remains the bounded implementation
> contract and historical handoff record; no Claude-authored report is expected.

## Objective

Implement GitHub Issue #21 and `docs/bilibili-video-search-prd.md`: add one read-only `search_bilibili_videos` MCP tool that returns a bounded authenticated first-page set of normal Bilibili Video candidates as identical structured and formatted-text results.

This is a public MCP tool change. Complete implementation, focused tests, bilingual docs, QA evidence, codemap update, and the required Claude report. Do not commit, push, release, version, branch, or open a PR.

## Current State

- Baseline commit: `54e3acdea74d04ac106d023cb90f3f8f7053a353` on `master`.
- Baseline `npm test`: 23 files, 299 tests passed.
- Baseline `npm run build`: passed.
- Package version: `1.8.0`; it must remain unchanged.
- Existing public tool count: eight.
- Only `get_video_transcript` currently uses `outputSchema + structuredContent + formatted JSON text`.
- Existing local credentials were safely checked by Codex and were configured/logged in; never inspect, print, or copy their values.
- Live provider selection is resolved by Codex outside this file. Do not write provider/model choices into the repository.

Existing worktree changes:

- `docs/agent-memory/pending-learning-proposals.md` — generated pre-existing state; do not touch, stage, revert, or quote.
- `CONTEXT.md` — Codex-owned confirmed `Video Discovery` term; read only.
- `docs/bilibili-video-search-prd.md` — authoritative product contract; read only.
- `docs/research/2026-07-26-bilibili-video-search-contract.md` — authoritative first-party interface evidence; read only.
- `docs/qa/2026-07-26-bilibili-video-search.md` — Claude may update only checkboxes/results backed by commands it actually ran.
- This handoff — read only.

Issue #20 is unrelated and must remain untouched.

## Files To Inspect

- `AGENTS.md`, `CLAUDE.md`, `CONTEXT.md`
- GitHub Issue #21, including current labels and comments
- `docs/bilibili-video-search-prd.md`
- `docs/research/2026-07-26-bilibili-video-search-contract.md`
- `docs/qa/2026-07-26-bilibili-video-search.md`
- `docs/agent-memory/codemap.md`
- `docs/agent-memory/harness-security.md`
- `src/bilibili/http.ts`
- `src/bilibili/types.ts`
- `src/utils/bvid.ts`
- `src/utils/credentials.ts`
- `src/utils/validation.ts`
- `src/utils/error-guidance.ts`
- `src/server/tool-schemas.ts`
- `src/server/tool-handlers.ts`
- Relevant existing tests and README sections

## Files To Edit

Expected source:

- new `src/bilibili/search.ts`
- `src/bilibili/types.ts`
- `src/utils/validation.ts`
- `src/server/tool-schemas.ts`
- `src/server/tool-handlers.ts`

Expected tests:

- new `tests/bilibili-search.test.ts`
- `tests/validation.test.ts`
- `tests/server-tools.test.ts`
- `tests/server-handler-sanitization.test.ts`
- `tests/server-error-next-steps.test.ts`
- `tests/mcp-server-smoke.test.ts`

Expected docs:

- `README.md`
- `README_EN.md`
- `docs/qa/2026-07-26-bilibili-video-search.md`
- `docs/agent-memory/codemap.md`
- new `docs/agent-memory/handoffs/2026-07-26-bilibili-video-search-claude-report.md`

Do not edit package metadata, lockfile, changelogs, release workflow, credential files, hook/rule files, PRD, research note, formal project facts/decisions/lessons, or unrelated source.

## Required Capabilities

Skills:

- Use the installed Claude Code `vitest` skill for failing-first test work.
- Use the installed Claude Code `secret-scanning` skill or its safe local fallback for the final diff/package leak check.

Claude Code subagents:

- Use `test-baseline-builder` for the failing-first search/schema/handler baseline.
- Use `risk-reviewer` after implementation for a focused credential, error, request-count, schema, and regression review.
- Do not create an autonomous team or broaden their scope.

Tools:

- Local `git`, `rg`, `npm`, `node`, and official installed MCP SDK.
- `gh issue view 21` for the live ticket.
- Existing local Bilibili credentials only through project code; do not display values.

The final report must name each capability/subagent used and summarize its result. If a named capability stalls, finish the same bounded work at top level and record the fallback.

## Constraints

### Public input

- Tool name: `search_bilibili_videos`.
- Required `query`: string, trim before use, non-empty, maximum 100 characters.
- Optional `limit`: integer 1-10, default 5.
- No other input.

Reuse `validateQuery` for string/non-empty/length rules. Add only the smallest limit validator needed; do not add a generic validation framework.

### Public output

Root:

- required `query: string`
- required `results: array`

Every result requires:

- `bvid: string`
- `title: string`
- `author: string`
- `duration_seconds: integer`
- `published_at: string`
- `view_count: integer`
- `description: string`
- `source_url: string`

Declare this exact inline `outputSchema`; do not add `$schema`, `oneOf`, pagination, totals, ranking scores, thumbnails, tags, raw response fields, extension fields, or additional business constraints.

On success:

- reuse `toTextContent(result)`
- add the same object as `structuredContent`

On any validation/runtime error:

- keep existing `content + isError`
- no `structuredContent`

Append the new tool after the current eight so every existing tool keeps its relative order.

### Credential flow

- Obtain auth headers through the existing credential manager.
- If no usable local Cookie header exists, throw the existing credential-recovery error before any login or search request.
- If a local credential exists, call existing `checkLoginStatus`.
- Continue only when `isLogin === true`; otherwise throw the same existing credential-recovery error.
- A login check network error remains a network error.
- Never anonymously fall back.
- Never log or return authentication headers or values.
- Reuse the existing `COOKIE_EXPIRED` structured guidance rather than inventing a new public error family.

### Search request

- Use `fetchWithoutWBI` with authenticated headers against `/x/web-interface/wbi/search/type`.
- Parameters: trimmed `keyword`, `search_type: "video"`, fixed `page: 1`, `page_size: limit`.
- Omit `order`; Bilibili comprehensive order is the verified default.
- Exactly one search request after credential validation.
- No per-result request, second page, legacy endpoint, HTML/browser fallback, cache, dependency, or new HTTP abstraction.

### Normalization

- Treat the upstream response as untrusted.
- Read only `result` when it is an array; otherwise return the successful empty list only for a successful API response.
- Preserve upstream order.
- Keep only rows where `type === "video"`, BVID is a string accepted by existing `isValidBVId`, and the title is a non-empty string after highlight removal.
- Do not fetch replacement rows after filtering; fewer than `limit` is valid.
- Defensively slice to `limit`.
- Remove only Bilibili `<em ...>` / `</em>` highlight tags from title and description with a small local helper; no HTML dependency or broad sanitizer rewrite.
- Parse variable-width colon duration text:
  - `27:6` → 1626
  - `123:28` → 7408
  - `1:02:03` → 3723
  - invalid/missing values normalize predictably without throwing.
- Convert positive finite Unix seconds to ISO; invalid/missing values normalize predictably without throwing.
- Normalize non-negative finite play count to an integer.
- Bound description to 200 Unicode code points and append `…` only when truncated.
- Construct `https://www.bilibili.com/video/<exact BVID>/` locally; do not use upstream `arcurl` or the uppercasing `createVideoUrl`.
- Do not interpret, execute, rank, summarize, or trust title/description content.

Use `""` for missing/malformed author, description, or publication time and `0` for invalid duration or view count. Cover these fallbacks in tests. Do not drop a valid Video solely because one secondary upstream metadata field is malformed.

## Execution Steps

1. Read the ticket, PRD, research note, relevant source/tests, and current worktree diff.
2. Use `test-baseline-builder` and the `vitest` skill to add failing-first coverage for exact schemas, handlers, validation, credential gating, request ownership, normalization, and empty results.
3. Run the focused tests and record the expected failures.
4. Implement the smallest code satisfying the tests and Issue #21.
5. Update only the concise Chinese/English tool descriptions, feature list/intention table, and one bounded example if local README structure requires it. Do not duplicate the full schema.
6. Update the QA checklist only with checks actually executed.
7. Update codemap for the new public tool, search module, and test file.
8. Run focused tests, build, full tests, package dry run, and diff check.
9. Run `risk-reviewer`; repair same-scope issues once and rerun affected checks.
10. Run the official SDK stdio `tools/list` and credentialed `tools/call` search against local `dist/index.js` without printing credentials. If a returned candidate with subtitles is safely identifiable, also run the bounded transcript keyword evidence leg; otherwise report it for Codex to complete.
11. Perform the final secret/leak scan.
12. Write the required Claude report and stop. Do not commit or mutate GitHub.

## Verification Commands

Required:

```powershell
npm test -- tests/bilibili-search.test.ts tests/validation.test.ts tests/server-tools.test.ts tests/server-handler-sanitization.test.ts tests/server-error-next-steps.test.ts tests/mcp-server-smoke.test.ts
npm run build
npm test
npm pack --dry-run --json
git diff --check
```

Also verify:

- exact `tools/list` through official SDK `Client + StdioClientTransport`
- one real authenticated `search_bilibili_videos` call
- no output-schema validation error
- no Cookie values in any output or artifact

## Acceptance Criteria

- GitHub Issue #21 is implemented exactly without scope expansion.
- Tool count is nine; existing eight relative order is unchanged; search is appended.
- Exact input/output schema matches the PRD.
- Success text and structured output are identical.
- Every error is text-only.
- Query/limit validation occurs before credential/search work.
- Missing/logged-out credentials make no search request and return safe existing next steps.
- A login network failure is not mislabeled as invalid credentials.
- Authenticated search uses the exact verified path/params and one search request.
- Mixed `ketang`/invalid BVID rows are removed; order and cap are correct.
- Duration, publication time, view count, highlight removal, description bounding, URL construction, invalid metadata fallback, and empty/filtered result behavior are deterministic.
- No candidate evidence or second page is fetched.
- Bilingual README text agrees.
- Focused/full/build/pack/diff and real SDK checks pass.
- No real secret appears.
- Codemap and QA are current.
- Claude report is complete.

## Things Not To Change

- Existing eight tool behavior except the tool list growing by one appended tool.
- Transcript evidence contract.
- Shared `toTextContent` / error helpers.
- Shared HTTP/WBI implementation.
- Credential storage/configuration implementation.
- Dependencies, package version, lockfile, changelogs, release workflow.
- Issue #20 or Node engine declaration.
- `docs/agent-memory/pending-learning-proposals.md`.
- Codex-owned PRD/research/CONTEXT/hand-off planning records.

## Stop And Report If

- The live endpoint no longer matches the research note.
- The implementation would need a dependency, second search path, pagination, shared HTTP/WBI redesign, or public schema change.
- Valid credentials cannot be used without unsafe inspection.
- A real credential or private value is found in tracked/untracked project artifacts.
- Required verification fails for unclear reasons after one same-scope diagnosis.
- Any requested change would overlap Issue #20, release work, or a different public feature.

## Expected Claude Report

Write:

`docs/agent-memory/handoffs/2026-07-26-bilibili-video-search-claude-report.md`

Use the repository report template and include:

- summary and files changed
- failing-first evidence
- commands and exact results
- real SDK/client evidence with safe query/BVID only
- subagents/skills used and their findings
- skipped checks and why
- unresolved risks/decision points
- `Harness Artifacts` covering Issue #21, research note, QA, codemap, harness-security, and harness-eval
- explicit confirmation that no commit, push, release, version, dependency, lockfile, or Issue #20 change occurred
