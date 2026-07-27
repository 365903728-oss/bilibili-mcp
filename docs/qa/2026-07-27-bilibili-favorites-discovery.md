# QA Checklist: Authenticated Bilibili Favorites Discovery

## QA Session

- Title: Issue #22 — `list_bilibili_favorite_videos` public acceptance
- Date: 2026-07-27
- Version or commit: `v1.10.0` source preparation on `master` (uncommitted before release gates)
- Owner: Claude Code (implementation) and Codex (repairs, independent review, and final verification)
- Related ticket, plan, PRD, or release:
  - GitHub Issue [#22](https://github.com/XZXZZX-Ai/bilibili-mcp/issues/22)
  - `docs/bilibili-favorites-discovery-prd.md`
  - `docs/research/2026-07-27-bilibili-favorites-contract.md`
  - `docs/research/2026-07-27-favorites-discovery-github-source-learning.md`
  - `docs/agent-memory/handoffs/2026-07-27-bilibili-favorites-discovery-codex-to-claude.md`
- QA type: `MCP tool change`

## Scope

In scope:

- One new public MCP tool `list_bilibili_favorite_videos` (tool 10) plus its bounded cursor, normalization, and structured-output behavior.
- Bilingual README/tool-reference/changelog updates and codemap navigation refresh.

Out of scope:

- Note generation, AI summarization, RAG, transcript/comment/chapter prefetch, downloads, persistence, cache, mutation, snapshot isolation, global deduplication, configurable page size.
- Package version/release, Git commit/push/PR, Issue #20.

## Preconditions

- [x] Current branch recorded: `master`.
- [x] The Favorites work is uncommitted and unstaged. The pre-existing unrelated `docs/agent-memory/pending-learning-proposals.md` modification remains preserved and outside this task.
- [x] No real Bilibili credential, account ID, Folder ID/title, Video title, or cursor value is printed or persisted in this checklist, the implementation, tests, or the Claude report; tests use only synthetic fixtures.
- [x] Local `~/.bilibili-mcp/config.json` exists and is logged in (used only for the live SDK smoke probe; no values copied).

## Build And Tests

- [x] `npm run build` clean (TypeScript compilation; `dist/` rebuilt by the build script).
- [x] Focused Vitest subset required by the handoff:
  - `npx vitest run tests/bilibili-favorites.test.ts tests/validation.test.ts tests/server-tools.test.ts tests/server-handler-sanitization.test.ts tests/server-error-next-steps.test.ts tests/mcp-server-smoke.test.ts tests/logger-redaction.test.ts`
  - Result: 7 files, 229 tests, all passing.
- [x] Full Vitest suite `npm test`: 25 files, 405 tests, all passing (baseline at v1.9.1/HEAD was 327).
- [x] `npm pack --dry-run --json` succeeds with 138 package entries and zero `scripts/`, `tests/`, internal agent-memory, QA, or research paths.
- [x] `git diff --check` reports only line-ending warnings (no whitespace errors).

## Tool Discovery And Schema Contract

- [x] Official MCP SDK `Client + StdioClientTransport` against `dist/index.js` returns exactly the ten-tool order:
  - `get_credential_setup_instructions, check_bilibili_credentials, check_mcp_update, get_video_info, get_video_comments, get_video_transcript, get_video_metadata, get_video_chapters, search_bilibili_videos, list_bilibili_favorite_videos`
- [x] `list_bilibili_favorite_videos` `inputSchema` declares only optional `cursor` (string, minLength 1, maxLength 256, pattern `^[A-Za-z0-9_-]+$`); `required: []`.
- [x] `list_bilibili_favorite_videos` `outputSchema` declares required `folders_total`, `videos`, `skipped_count`; optional `folder` (object), `page`, `next_cursor`.
- [x] Existing nine tools preserve relative order and unchanged required input fields.

## Request Flow And Counts

- [x] Malformed cursor: zero network requests (validation throws in `decodeFavoritesCursor` before `credentialManager.getAuthHeaders()` or any fetch).
- [x] A generated cursor with an appended base64url sextet is rejected as non-canonical before credentials or network access.
- [x] A maximum-safe page cursor cannot overflow into an unsafe emitted continuation token.
- [x] Missing/blank Cookie header: zero network requests.
- [x] Authenticated no-Folder account: exactly one `/x/web-interface/nav` request and one `/x/v3/fav/folder/created/list-all` request; no resource-list request.
- [x] Authenticated Folder page: one nav + one created/list-all + exactly one `/x/v3/fav/resource/list` request with `media_id`, `pn`, `ps=20`, `keyword=""`, `order="mtime"`, `type=0`, `tid=0`, `platform="web"`.
- [x] No second resource page is fetched to fill filtered results; no transcript/comment/chapter/search/download request is made.

## Cursor And Continuation Behavior

- [x] Cursor payload is exactly `{version: 1, folder_id: <positive safe integer>, page: <positive safe integer>}` encoded as base64url JSON; never contains Cookie, account ID, Folder title, or Video data.
- [x] `has_more=true` advances within the same Folder (next page).
- [x] Empty `medias` page terminates the current Folder even when `has_more=true`, advancing to page 1 of the next Folder — verified by `treats empty medias as terminal for the current folder even when has_more=true` and `omits next_cursor when an empty page is on the final folder`.
- [x] A non-empty upstream page whose rows all fail normalization remains on the same Folder when `has_more=true`; normalized emptiness is not treated as upstream exhaustion.
- [x] `has_more=false` advances to page 1 of the next Folder.
- [x] Final Folder's terminal page omits `next_cursor`.
- [x] Stale cursor whose Folder is no longer in the current account's owned list throws `ValidationError` ("cursor folder no longer belongs to the current account; restart without a cursor") before the resource-list request.
- [x] The same stale-cursor error is returned when the current Folder list normalizes to zero rows.
- [x] Folder rows whose upstream `mid` does not match the authenticated `mid` are filtered out.
- [x] Malformed Folder rows (non-object, invalid ID, non-string title, invalid `media_count`) are filtered before Folder selection; any string title remains eligible.
- [x] The same BVID remains visible through two successive calls in two distinct Folder contexts; no cross-Folder deduplication occurs.

## Real-Account Acceptance (Redacted)

An ephemeral local SDK verifier made a real first call and exactly one continuation call against the local user account. It asserted only schema, counts, page progression, and text/structured equality, then was removed after acceptance so no account-sensitive verifier remains in the worktree.

- [x] First call: succeeded, returned `folders_total = 3`, `videos.length = 20`, `skipped_count = 0`, `next_cursor` present. (Page size = 20 matches the upstream fixed limit.)
- [x] Continuation call with the returned cursor: succeeded and advanced to `page = 2` of the same Folder (cursor decoded `{folder_id, page: 2}` internally; values not printed).
- [x] `JSON.parse(content[0].text)` deep-equals `structuredContent` on both calls.
- [x] No `outputSchema` validation error from the MCP SDK.
- [x] No folder titles, video titles, account IDs, BVID values, or cursor contents were printed by the script or persisted in this checklist, the Claude report, or any other durable artifact.

## Security And Privacy

- [x] Scoped credential scanning produced no non-placeholder or real credential findings after the expected synthetic redaction fixtures were reviewed.
- [x] `grep -rEn "[A-Za-z0-9+/]{40,}"` over changed source (excluding base64url alphabet references): no matches.
- [x] `grep -rEn "<email>|ghp_<36>|npm_<36>"` over changed source and the new favorites test: no matches.
- [x] `credentialManager.getAuthHeaders()` remains the only credential source; credentials are never logged.
- [x] Debug-log redaction covers `mid`, `up_mid`, `media_id`, and `folder_id` in structured params and URL query strings.
- [x] The favorites module returns only normalized Folder/Video fields; raw upstream objects, cover/avatar URLs, uploader IDs, stats, descriptions, and privacy flags are dropped.

## Skipped Checks And Why

- Did not run `npm view` registry checks: no package version or dependency changed.
- Did not run `npm publish`: no release authorized.
- Did not run real-account acceptance against the published `npx -y @xzxzzx/bilibili-mcp@latest` package: the change is uncommitted and unpublished; local `dist/index.js` is the authoritative build.
- Did not paste full `npm pack --dry-run --json` output: the 138-entry count and zero-forbidden-path assertion are sufficient.

## Unresolved Risks And Decision Points

- None blocking. Real Bilibili visibility gaps (deleted rows, partial pages, account switching mid-traversal) remain acceptance caveats per the PRD, not implementation gaps; `media_count` is surfaced only as Bilibili's reported count.
- Claude's initial review missed several issues. Codex's independent Standards/Spec review found and repaired filtered-page continuation, deep cursor error typing, stale cursor behavior on an empty normalized Folder list, canonical base64url validation, debug identifier redaction, cross-Folder coverage, and documentation drift before final verification.
