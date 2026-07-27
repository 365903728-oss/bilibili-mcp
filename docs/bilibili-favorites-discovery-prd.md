# Product Requirements Document: Authenticated Bilibili Favorites Discovery

**Version**: 1.0
**Date**: 2026-07-27
**Author**: Codex
**Quality Score**: 97/100

## Executive Summary

Add one read-only `list_bilibili_favorite_videos` MCP tool that starts from the locally authenticated Bilibili account, discovers all of that account's created Favorite Folders, and traverses their Videos through a bounded opaque cursor.

The user-facing workflow is one request such as “读取我的全部 B 站收藏视频.” The MCP protocol remains paginated because Bilibili accepts at most 20 resources per favorites request and an unbounded response would be unsafe for MCP clients. An Agent follows `next_cursor` until it is absent.

This feature only discovers favorite memberships. It does not prefetch transcripts, comments, Chapters, or metadata; generate notes; download media; persist a database; run a background sync; or deduplicate a Video that appears in more than one Folder.

## Problem Statement

**Current situation**: The server can search public Videos and deeply read a known BVID, but it cannot use the current user's Bilibili Favorites as a discovery source. Users must manually open every Folder and copy Video links.

**Proposed solution**: With no Folder URL or ID supplied by the user, authenticate the configured account, enumerate all of its created Favorite Folders, return one upstream Folder page at a time, and provide an opaque continuation cursor until the traversal is complete.

**Expected impact**: A user can expose their existing Bilibili learning queue to any MCP Host, then choose their own downstream transcript, note-generation, or knowledge-base workflow.

## Requirements Quality

- Business Value & Goals: 30/30
- Functional Requirements: 25/25
- User Experience: 19/20
- Technical Constraints: 15/15
- Scope & Priorities: 8/10

## Success Metrics

- A call with no Folder input begins reading the current authenticated account's created Favorite Folders.
- Following every returned `next_cursor` reaches every Folder page that Bilibili exposes at traversal time.
- Every upstream resource-list request uses the verified page size of 20 or less.
- One tool call makes exactly one navigation request, one Folder-list request, and at most one resource-list request.
- No transcript, comment, Chapter, per-Video metadata, download, or write request is triggered.
- Missing, invalid, or logged-out credentials fail safely without exposing Cookie or account values.
- Successful output is identical in MCP text and `structuredContent`.
- Focused tests, full tests, build, package inspection, official SDK stdio discovery/call, a redacted real-account traversal, and secret scanning pass.

## User Persona

### Primary: Bilibili Learning Collector

- **Role**: Uses an MCP-capable Agent to work with Videos already organized in Bilibili Favorites.
- **Goal**: Let the Agent discover all saved Videos without manually copying Folder links.
- **Pain point**: Existing tools require a BVID, URL, or search query and cannot start from the user's private account organization.
- **Technical level**: Any.

## User Stories And Acceptance Criteria

### Start from the current account

**As a** Bilibili learning collector,
**I want** the MCP to discover my Favorite Folders automatically,
**so that** I do not need to find or paste a Folder URL or ID.

**Acceptance criteria:**

- [ ] The only optional input is `cursor`.
- [ ] A missing cursor starts at the first Folder in Bilibili's returned Folder order and page 1.
- [ ] The account identity comes from the authenticated Bilibili navigation response, not from user input.
- [ ] All valid Folder rows returned by the current account's created-Folder endpoint participate in traversal.
- [ ] An account with no Favorite Folders succeeds with `folders_total: 0` and `videos: []`.

### Traverse all Folder pages safely

**As an** Agent,
**I want** a continuation cursor,
**so that** I can reach the full collection without creating one unbounded MCP response.

**Acceptance criteria:**

- [ ] Each call reads at most one Bilibili resource page with `ps=20`.
- [ ] When the current Folder has another page, `next_cursor` points to that page.
- [ ] When the current Folder ends, `next_cursor` points to page 1 of the next Folder.
- [ ] An empty upstream media page ends the current Folder even if `has_more` is inconsistent, preventing a continuation loop.
- [ ] The final response omits `next_cursor`.
- [ ] The cursor is versioned, opaque, bounded, contains no credential or Folder title, and is validated before any network request.
- [ ] A syntactically invalid cursor returns `VALIDATION_ERROR` without a network request.
- [ ] A cursor whose Folder no longer belongs to the current account returns a safe validation error instructing the caller to restart without a cursor.
- [ ] Traversal is best-effort over live state; concurrent Bilibili edits do not create a snapshot guarantee.

### Identify Folder membership and Videos

**As an** Agent,
**I want** normalized Folder and Video fields,
**so that** I can display, filter, or pass BVIDs to existing evidence tools.

**Acceptance criteria:**

- [ ] A non-empty page contains a `folder` summary with `id`, `title`, and `media_count`.
- [ ] `folder.media_count` is documented as Bilibili's reported count, which may exceed currently visible or callable rows.
- [ ] Every normalized Video contains `bvid`, `title`, `author`, `duration_seconds`, `published_at`, `favorited_at`, and canonical HTTPS `source_url`.
- [ ] Only rows with a valid BVID and non-empty title are returned as Videos.
- [ ] `skipped_count` reports upstream rows that could not be represented safely; no replacement page is fetched.
- [ ] Upstream order is preserved.
- [ ] A Video present in two Folders is returned once in each Folder context. Server-side cross-Folder deduplication is out of scope.

### Receive predictable MCP output

**As an** MCP client integrator,
**I want** a declared structured result and a text compatibility copy,
**so that** clients can consume Favorites without reparsing an undocumented payload.

**Acceptance criteria:**

- [ ] `tools/list` exposes the exact `inputSchema` and `outputSchema`.
- [ ] Successful calls return the same object as `structuredContent` and `JSON.stringify(result, null, 2)` in `content[0].text`.
- [ ] Validation, credential, network, API, and stale-cursor errors remain `content + isError` only.
- [ ] Existing tools preserve their order and behavior; Favorites Discovery is appended as tool 10.

## Public MCP Interface

### Tool

`list_bilibili_favorite_videos`

### Input

- Optional: `cursor: string`, an opaque continuation token returned by the preceding successful call.
- No Folder ID, Folder URL, account ID, page number, page size, sort, or filter input.

### Successful output with a Folder page

```json
{
  "folders_total": 3,
  "folder": {
    "id": 123456,
    "title": "学习",
    "media_count": 54
  },
  "page": 1,
  "videos": [
    {
      "bvid": "BV...",
      "title": "Video title",
      "author": "Uploader",
      "duration_seconds": 600,
      "published_at": "2026-01-01T00:00:00.000Z",
      "favorited_at": "2026-07-01T00:00:00.000Z",
      "source_url": "https://www.bilibili.com/video/BV.../"
    }
  ],
  "skipped_count": 0,
  "next_cursor": "<opaque>"
}
```

`next_cursor` is omitted on the final page. `folder` and `page` are omitted only when the authenticated account has no valid created Favorite Folders.

### Successful output with no Folders

```json
{
  "folders_total": 0,
  "videos": [],
  "skipped_count": 0
}
```

## Functional Requirements

### Request flow

1. Validate and decode the optional cursor before network access.
2. Require an available local Cookie header.
3. Call `/x/web-interface/nav` with authenticated headers and require an explicitly logged-in response with a safe numeric account ID.
4. Call `/x/v3/fav/folder/created/list-all` with that account ID and authenticated headers.
5. Normalize valid Folder rows in Bilibili's returned order.
6. Resolve the start Folder/page from the cursor, or select the first Folder/page 1.
7. If there is a Folder, call `/x/v3/fav/resource/list` once with `media_id`, `pn`, fixed `ps=20`, empty keyword, `order=mtime`, `type=0`, `tid=0`, and `platform=web`.
8. Normalize the page and compute the next versioned cursor from `has_more` and the next Folder.
9. Return identical structured and formatted-text payloads.

If the resource response contains an empty `medias` array, treat the current Folder as complete even when `has_more` is true and advance to the next Folder. This prevents a malformed or drifting upstream response from producing an endless cursor chain.

### Cursor contract

- Encode only `{ version, folder_id, page }` as bounded base64url JSON.
- Never include Cookie values, account IDs, Folder titles, Video data, or auth headers.
- Treat the token as opaque in public documentation.
- Require a supported version, a positive safe-integer Folder ID, and a positive safe-integer page.
- Resolve Folder ownership again on every call.
- Do not sign or persist cursor state in the MVP; tampering is harmless because IDs are checked against the authenticated account's current Folder list before resource access.

### Normalization

- Treat Folder names, Video titles, uploader names, and all API data as untrusted content.
- Accept only positive safe-integer Folder IDs, string Folder titles, and non-negative integer `media_count`.
- Treat `media_count` as Bilibili's reported remote count, not as proof that every row is currently visible.
- Accept a Video only when `bvid` passes the existing BVID validator and trimmed `title` is non-empty.
- Normalize missing or malformed author/publication/favorite timestamps to `""`.
- Normalize invalid duration to `0`.
- Convert positive finite Unix seconds to ISO timestamps.
- Construct `source_url` locally from the exact validated BVID.
- Preserve API order and never interpret content as Agent instructions.
- Do not persist or cache private Folder or Video-list data.

## MVP Scope

### Included

- One current-account, read-only Favorites Discovery tool.
- Automatic discovery of all created Favorite Folders.
- One upstream Folder page per MCP call and an opaque continuation cursor.
- Folder-context-preserving membership semantics.
- Exact structured/text output parity.
- Unit, handler, schema, request-count, credential, cursor, real SDK, real-account, and leak tests.
- Concise bilingual tool-reference, README, and unreleased changelog updates.

### Out Of Scope

- Note generation, summarization, AI processing, embeddings, vector search, or RAG.
- Transcript, comment, Chapter, metadata, image, or danmaku prefetch.
- Downloads, ASR, screenshots, keyframes, or browser automation.
- Database, filesystem export, cache, background sync, scheduled refresh, checkpoint service, or webhook.
- Watch Later, subscriptions, followed collections, creator series, courses, bangumi, or another user's public Favorites.
- Mutating Favorites, adding/removing Videos, creating/renaming Folders, or changing privacy.
- Global deduplication, snapshot isolation, manual Folder selection, search/filter/sort, configurable page size, or parallel fetching.
- New dependency, package version, release, commit, push, branch, pull request, or Issue #20.

## Test And Verification Requirements

Add failing-first Vitest coverage for:

- optional cursor type/length/base64url/payload/version/integer validation
- malformed cursor validation before any credential or network access
- missing, expired, and logged-out credentials
- navigation identity ownership rather than user-supplied account IDs
- exact Folder-list and resource-list paths, parameters, headers, order, and request counts
- no-Folder, empty-Folder, multi-page, next-Folder, final-page, and stale-cursor behavior
- inconsistent `has_more: true` with an empty media page, which must advance rather than loop
- authenticated `mid` mismatch in Folder data and reported-count/visible-row discrepancy
- same BVID in multiple Folder contexts without server deduplication
- malformed Folder/resource rows, `skipped_count`, timestamp/duration fallbacks, order preservation, and canonical URL construction
- exact tenth-tool schema and existing-tool relative order
- successful text/structured equality and text-only errors

Run:

```powershell
npm test -- tests/bilibili-favorites.test.ts tests/validation.test.ts tests/server-tools.test.ts tests/server-handler-sanitization.test.ts tests/server-error-next-steps.test.ts tests/mcp-server-smoke.test.ts
npm run build
npm test
npm pack --dry-run --json
git diff --check
```

Also run:

- official SDK `Client + StdioClientTransport` against local `dist/index.js`
- one real authenticated first call plus cursor continuation without printing Folder names, Video titles, account IDs, cursor contents, or credentials in durable artifacts
- a secret/private-data scan over the diff, generated package list, handoff/report, research note, and QA note

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Undocumented consumer endpoints change | Medium | High | Isolate the two Favorites endpoints in one module, reuse shared transport, and cache live contract evidence in a dated research note. |
| Favorites reveal a private interest profile | High | High | Require the current local login, make no anonymous fallback, never log/cache/persist payloads, and keep real QA evidence redacted. |
| One call becomes an unbounded crawl | Medium | High | Fix upstream `ps=20`, allow one resource request per call, and require explicit cursor continuation. |
| Folder edits during traversal cause drift | Medium | Medium | Re-fetch current Folder ownership each call, document best-effort live traversal, and reject stale Folder cursors. |
| Invalid/removed rows silently disappear | Medium | Medium | Validate callable Videos and expose `skipped_count` without fetching replacements. |
| Duplicate BVIDs surprise consumers | High | Low | Define Favorite Membership explicitly; retain Folder context and leave deduplication to the caller. |
| Upstream text contains prompt injection | Medium | High | Treat all returned text as untrusted data and never execute, summarize, or interpret it inside the server. |

## Dependencies And Blockers

**Dependencies:**

- Existing `credentialManager`, `fetchWithoutWBI`, shared throttle/retry/error handling, BVID validation, and structured-output patterns.
- Live evidence in `docs/research/2026-07-27-bilibili-favorites-contract.md`.
- Valid locally stored Bilibili credentials for final acceptance.

**Known blockers:**

- None at specification time. If live account data cannot be tested safely, implementation may complete but real-account acceptance must remain explicitly pending.

## References

- `CONTEXT.md`
- `docs/research/2026-07-27-bilibili-favorites-contract.md`
- `docs/research/2026-07-20-feature-opportunities.md`
- `docs/research/2026-07-25-cross-platform-video-content-mcp-landscape.md`
- `src/bilibili/http.ts`
- `src/utils/credentials.ts`
- `src/server/tool-schemas.ts`
- `src/server/tool-handlers.ts`
