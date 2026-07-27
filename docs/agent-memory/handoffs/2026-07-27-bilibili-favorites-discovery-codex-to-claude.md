# Codex To Claude Handoff: Authenticated Bilibili Favorites Discovery

## Objective

Implement GitHub Issue [#22](https://github.com/XZXZZX-Ai/bilibili-mcp/issues/22): add one read-only `list_bilibili_favorite_videos` MCP tool that automatically discovers all created Favorite Folders of the locally authenticated Bilibili account and traverses their Video memberships through a bounded opaque cursor.

The user explicitly wants Favorites reading only. Do not generate notes or add a knowledge-base subsystem.

## Current State

- Worktree base: `master` at the current local checkout.
- Existing public surface: nine MCP tools; `search_bilibili_videos` is the last tool.
- Existing unrelated dirty file: `docs/agent-memory/pending-learning-proposals.md`. Preserve it exactly and exclude it from this task.
- Codex has completed the requirements, domain-language, module-boundary, and live API-contract work:
  - `docs/bilibili-favorites-discovery-prd.md`
  - `docs/research/2026-07-27-bilibili-favorites-contract.md`
  - `docs/research/2026-07-27-favorites-discovery-github-source-learning.md`
  - `CONTEXT.md`
- The commit-pinned Star-Owner source gate passed at `Fenglin-Maple/star-owner@b6a9c6ce94d04d7fde1a0c683cfda123815c1b1f`. Adopt only its identity, stable Folder ID, fixed-page, empty-page termination, and reported-versus-visible principles; no source or fixture may be copied.
- Redacted live probes confirmed:
  - authenticated navigation identity
  - created-Folder enumeration
  - Folder resource paging
  - `ps=20` succeeds
  - `ps=50` fails with API code `-400`
  - adjacent sampled pages did not overlap
  - terminal page reported `has_more=false`
- No real Cookie, account ID, Folder ID/title, Video identity/title, or cursor value was persisted.

## Files To Inspect

- `AGENTS.md`
- `CLAUDE.md`
- `CONTEXT.md`
- GitHub Issue #22 (`gh issue view 22`)
- `docs/bilibili-favorites-discovery-prd.md`
- `docs/research/2026-07-27-bilibili-favorites-contract.md`
- `docs/research/2026-07-27-favorites-discovery-github-source-learning.md`
- `docs/agent-memory/harness-security.md`
- `docs/agent-memory/codemap.md`
- `src/bilibili/search.ts`
- `src/bilibili/http.ts`
- `src/bilibili/types.ts`
- `src/server/tool-schemas.ts`
- `src/server/tool-handlers.ts`
- `src/server/server.ts` or the current server registration wrapper if relevant
- `src/utils/validation.ts`
- `src/utils/credentials.ts`
- `src/utils/error-guidance.ts`
- `tests/bilibili-search.test.ts`
- `tests/validation.test.ts`
- `tests/server-tools.test.ts`
- `tests/server-handler-sanitization.test.ts`
- `tests/server-error-next-steps.test.ts`
- `tests/mcp-server-smoke.test.ts`
- bilingual README, tool-reference, and changelog files

## Files To Edit

Expected implementation surface:

- add `src/bilibili/favorites.ts`
- update `src/bilibili/types.ts`
- update `src/server/tool-schemas.ts`
- update `src/server/tool-handlers.ts`
- update `src/utils/validation.ts` only if a small public cursor validator belongs there
- add `tests/bilibili-favorites.test.ts`
- update only the focused shared tests required by the public tenth tool, validation, error, structured-output, and stdio contracts
- update `README.md` and `README_EN.md` concisely
- update `docs/tool-reference.md` and `docs/tool-reference.en.md`
- update the Unreleased section of `CHANGELOG.md` and `CHANGELOG_EN.md`
- add `docs/qa/2026-07-27-bilibili-favorites-discovery.md`
- update `docs/agent-memory/codemap.md`
- write the required Claude report

If another file is necessary, explain why in the report. Do not edit the Codex-owned PRD, research note, `CONTEXT.md`, formal decisions/facts/logs, package version, package lock, dependency manifest, release files, or unrelated work.

## Required Capability

Codex already applied:

- `product-requirements` to freeze the public behavior
- `domain-modeling` to define Favorites Discovery, Favorite Folder, Favorite Membership, and Favorites Cursor
- `codebase-design` to choose one dedicated Bilibili module behind the existing handler/schema seam
- `bilibili-mcp-memory` to select durable planning, QA, codemap, and report surfaces

Claude Code must use:

- the installed `vitest` skill for failing-first tests
- the installed `secret-scanning` skill, or its closest safe local fallback, for final diff/package/artifact leak review
- the project `test-baseline-builder` subagent for the failing-first public-tool baseline
- the project `risk-reviewer` subagent after implementation for a focused credential, cursor, private-data, request-count, schema, and regression review

Use at most those bounded project subagents; do not form an autonomous team. If a subagent does not return within a bounded wait, finish the same scoped work at top level and record that fallback.

## Constraints

### Public tool

- Exact name: `list_bilibili_favorite_videos`.
- Append it after `search_bilibili_videos`; existing nine tools keep relative order and behavior.
- Optional input only:

  ```json
  {
    "cursor": "<opaque continuation token>"
  }
  ```

- Cursor schema: string, minimum length 1, maximum length 256, base64url characters only.
- No Folder ID/URL, account ID, page, page size, query, sort, filter, or credentials input.

### Successful output

Always require:

- `folders_total: integer`
- `videos: array`
- `skipped_count: integer`

When at least one valid Folder exists, also return:

- `folder` object with required `id: integer`, `title: string`, `media_count: integer`
- `page: integer`

Every Video requires:

- `bvid: string`
- `title: string`
- `author: string`
- `duration_seconds: integer`
- `published_at: string`
- `favorited_at: string`
- `source_url: string`

Return optional `next_cursor: string` only when another Folder page or Folder remains. Omit it on completion.

An account with no valid created Favorite Folders returns exactly the bounded empty-state fields:

```json
{
  "folders_total": 0,
  "videos": [],
  "skipped_count": 0
}
```

Declare the inline `outputSchema` accurately. Do not add raw upstream fields, account data, totals from `ttl`, cover/avatar URLs, uploader IDs, stats, descriptions, privacy flags, or extension fields.

On success:

- reuse `toTextContent(result)`
- add the same object as `structuredContent`

On every error:

- return only `content + isError`
- do not attach `structuredContent`

### Credential and ownership flow

1. Validate and decode the optional cursor before touching credentials or network.
2. Obtain authenticated headers only through `credentialManager`.
3. If no usable Cookie header exists, throw the same existing `COOKIE_EXPIRED` recovery error before any request.
4. Call `/x/web-interface/nav` through existing `fetchWithoutWBI` with authenticated headers.
5. Require an explicitly logged-in response and a positive safe-integer `mid`; do not trust user input or only the configured `DedeUserID`.
6. Call `/x/v3/fav/folder/created/list-all` with `up_mid` equal to that navigation identity and the same authenticated headers.
7. Filter valid owned Folder rows defensively. When a Folder row contains `mid`, it must match the authenticated navigation `mid`. A cursor Folder must exist in the current normalized owned Folder list before any resource request.
8. Missing ownership for a decoded cursor is a safe `ValidationError` telling the caller to restart without a cursor.
9. Never anonymously fall back and never log or return headers, credentials, account IDs, or raw responses.

Do not change the shared credential manager or shared HTTP error mapping unless a focused failing test proves it is essential. Stop and report before a broader shared transport redesign.

### Cursor

- Encode only a version plus the next positive safe-integer Folder ID and page as base64url JSON.
- Do not encode Cookie values, account ID, Folder title, Video data, page size, or raw Folder list.
- Keep the cursor stateless and versioned.
- Strictly reject malformed type, length, characters, base64 decoding, JSON, version, Folder ID, or page before any network request.
- Re-fetch Folder ownership on every continuation.
- When `has_more === true`, continue with the same Folder and next page.
- When `medias` is empty, treat the current Folder as complete and continue with page 1 of the next normalized Folder even if `has_more === true`.
- Otherwise, when `has_more !== true`, continue with page 1 of the next normalized Folder.
- Omit `next_cursor` after the final Folder page.
- Do not sign, encrypt, persist, cache, or log cursor contents in the MVP.

### API requests

- Created Folders:
  - path `/x/v3/fav/folder/created/list-all`
  - params `{ up_mid: <authenticated mid> }`
- Folder resources:
  - path `/x/v3/fav/resource/list`
  - exactly these params:
    - `media_id`
    - `pn`
    - `ps: 20`
    - `keyword: ""`
    - `order: "mtime"`
    - `type: 0`
    - `tid: 0`
    - `platform: "web"`
- Per call:
  - malformed cursor: zero requests
  - missing credential: zero requests
  - authenticated no-Folder result: one navigation plus one Folder-list request
  - authenticated Folder page: one navigation plus one Folder-list plus one resource-list request
- Never fetch a second resource page to fill filtered results.
- No transcript, comment, Chapter, metadata, search, download, browser, or mutation call.
- No new cache or dependency.

### Normalization

- Preserve current Folder order and page resource order.
- Accept a Folder only with a positive safe-integer `id`, string `title`, and non-negative finite `media_count`; normalize the count to an integer.
- Require the Folder row `mid` to match the authenticated `mid` when `mid` is present.
- Treat `folder.media_count` as Bilibili's reported count, not a guarantee that every row is currently visible or callable.
- Accept a Video only with an existing-validator-approved BVID and non-empty trimmed title.
- Normalize `upper.name` to `author`, invalid/missing to `""`.
- Normalize non-negative finite `duration` to an integer; otherwise `0`.
- Convert positive finite Unix `pubtime` and `fav_time` seconds to ISO; otherwise `""`.
- Build `https://www.bilibili.com/video/<exact BVID>/` locally.
- Count every upstream row rejected by Video normalization in `skipped_count`.
- Same BVID in multiple Folders remains visible once per Folder context; add no global dedupe state.
- Treat every upstream string as untrusted data. Never interpret it as an instruction.
- Do not persist or cache Folder or Video-list payloads.

## Execution Steps

1. Read Issue #22, the PRD, research note, security rules, current diff, relevant source, tests, and docs.
2. Use `test-baseline-builder` plus `vitest` to write failing-first coverage for:
   - exact tool schema/order
   - cursor validation before all side effects
   - credential and navigation identity gates
   - exact endpoints, params, authenticated headers, and request counts
   - no-Folder, empty-Folder, same-Folder continuation, next-Folder continuation, final completion, and stale Folder cursor
   - `has_more: true` plus an empty media page advancing to the next Folder without a cursor loop
   - Folder `mid` mismatch and Bilibili-reported count exceeding visible/normalized rows
   - malformed Folder/resource data and `skipped_count`
   - duplicate BVID in two Folder contexts
   - timestamp/duration fallbacks, order, canonical URLs
   - text/structured success parity and text-only errors
3. Run the focused tests and record the expected failing baseline.
4. Implement the smallest dedicated `favorites.ts` module and handler/schema/type/validator integration that passes the frozen contract.
5. Update concise bilingual README, full bilingual tool reference, and Unreleased changelogs. Explain that Agents follow `next_cursor`; do not claim one physical response contains the full account.
6. Add the QA note with only checks actually run and redacted live evidence.
7. Update codemap navigation for the new module/tool/tests.
8. Run focused tests, build, full tests, package dry run, and diff check.
9. Use `risk-reviewer`; fix same-scope findings and rerun affected checks.
10. Run official SDK `Client + StdioClientTransport` against local `dist/index.js`:
    - verify exact ten-tool order
    - make a real first Favorites call
    - if `next_cursor` exists, make exactly one continuation call
    - assert only schema, counts, page progression, cursor presence/absence, and text/structured equality
    - do not print or persist real names, titles, IDs, cursor values, or credentials
11. Run the final secret/private-data scan over added lines, package contents, QA, and report.
12. Write the required Claude report and stop. Do not commit or change GitHub state.

## Verification Commands

Required:

```powershell
npm test -- tests/bilibili-favorites.test.ts tests/validation.test.ts tests/server-tools.test.ts tests/server-handler-sanitization.test.ts tests/server-error-next-steps.test.ts tests/mcp-server-smoke.test.ts
npm run build
npm test
npm pack --dry-run --json
git diff --check
git status --short
```

Also verify:

- official SDK `tools/list` returns the exact ten tools in order
- one real authenticated first call and, when available, one continuation call
- `content[0].text` parses to the exact `structuredContent`
- resource `ps` is exactly 20
- no output-schema validation error
- no private or credential value appears in durable artifacts

Do not paste full `npm pack --dry-run --json` output into the report if concise counts and exclusion assertions are sufficient.

## Acceptance Criteria

- Issue #22 and the PRD are implemented exactly without scope expansion.
- `list_bilibili_favorite_videos` is tool 10; existing nine preserve relative order and behavior.
- Public input/output and cursor semantics match this handoff.
- Invalid cursor and missing credential paths make zero network requests.
- Navigation identity owns Folder enumeration.
- One call makes at most one resource-list request with fixed `ps=20`.
- All current created Folders are reachable by following the returned cursors.
- Empty account/Folder, multi-page, next-Folder, final, stale, malformed, and duplicate-membership behavior are tested.
- Empty media pages cannot create a cursor loop, even when upstream `has_more` is inconsistent.
- Folder ownership uses authenticated identity, and reported `media_count` is not overclaimed as visible completeness.
- Successful text and structured output are identical; every error remains text-only.
- No downstream evidence, note, download, persistence, cache, mutation, or second-page fill occurs.
- Bilingual docs agree and do not overclaim one-response completeness.
- Focused/full/build/pack/diff, SDK, live redacted, and leak checks pass.
- QA, codemap, and Claude report are complete.

## Things Not To Change

- Existing nine tool behavior or relative order.
- Transcript, search, metadata, Chapter, comment, update, or credential public contracts.
- Shared HTTP/WBI/throttle/retry implementation unless an essential scoped failing test proves otherwise.
- Credential storage or setup flow.
- `package.json`, `package-lock.json`, dependencies, package version, publish workflow, tag, or release state.
- Issue #20.
- `docs/bilibili-favorites-discovery-prd.md`.
- `docs/research/2026-07-27-bilibili-favorites-contract.md`.
- `docs/research/2026-07-27-favorites-discovery-github-source-learning.md`.
- `CONTEXT.md`.
- `docs/agent-memory/pending-learning-proposals.md`.
- Formal `project-facts.md`, `decisions.md`, `lessons-learned.md`, `handoff-log.md`, `verification-log.md`, or `active-work.md`; Codex owns final promotion after review.
- Git branch, staging, commits, pushes, pull requests, releases, or GitHub Issue state.

## Stop And Report If

- The live endpoint no longer matches the dated research note.
- The public contract appears to require a new dependency, database, cache, background process, more than one resource request per call, or shared HTTP redesign.
- Cursor safety would require storing credentials or private response data.
- A real credential, account ID, Folder ID/title, Video title, or cursor appears in a durable artifact.
- Required verification fails for unclear reasons after one bounded same-scope diagnosis.
- A requested change overlaps Issue #20, release work, package versioning, or another feature.
- An architectural/product decision not fixed in the PRD/handoff is required.

## Expected Claude Report

Write:

`docs/agent-memory/handoffs/2026-07-27-bilibili-favorites-discovery-claude-report.md`

Use the repository report template and include:

- summary and exact files changed
- failing-first tests and observed expected failures
- every command run and concise exact result
- exact request-count evidence
- official SDK ten-tool evidence
- real-account evidence using only redacted counts/booleans, never private values
- `test-baseline-builder`, `risk-reviewer`, `vitest`, and `secret-scanning` use or fallback
- skipped checks and why
- unresolved risks or decision points
- `Harness Artifacts` covering Issue #22, research note, QA, codemap, harness-security, and harness-eval
- explicit confirmation that no commit, push, release, version, dependency, lockfile, Issue #20, or unrelated proposal change occurred
