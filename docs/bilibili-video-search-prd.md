# Product Requirements Document: Bilibili Video Discovery

**Version**: 1.0
**Date**: 2026-07-26
**Author**: Sarah (Product Owner)
**Quality Score**: 96/100

## Executive Summary

Add one bounded `search_bilibili_videos` MCP tool so an Agent can start with a topic instead of requiring the user to find and paste a BVID. The tool returns a small ordered set of Bilibili Video candidates that can be passed directly to the existing metadata, transcript, Chapter, and comment tools.

Search is only the entry to the existing evidence workflow. It does not inspect candidate subtitles or comments, re-rank results, crawl creators or collections, or broaden the Bilibili-native product boundary.

## Problem Statement

**Current situation**: All five content tools require a BVID or Bilibili Video URL. A user who knows only a topic must leave the MCP client, search Bilibili manually, and return with a link.

**Proposed solution**: Accept one required topic query and an optional result limit, then return enough candidate metadata for an Agent or user to choose a Video.

**Expected impact**: A user can complete `topic → candidate Video → bounded transcript match → timestamp evidence` inside one Agent conversation.

## Requirements Quality

- Business Value & Goals: 29/30
- Functional Requirements: 25/25
- User Experience: 19/20
- Technical Constraints: 15/15
- Scope & Priorities: 8/10

## Success Metrics

- A user who supplies only a topic can reach a clickable transcript evidence moment in approximately three MCP calls.
- One search call makes one Bilibili search request after credential validation and returns at most 10 candidates.
- Search never automatically requests candidate metadata, subtitles, Chapters, comments, creator feeds, or collections.
- Valid results are available as both MCP `structuredContent` and backward-compatible formatted JSON text.
- Missing or invalid credentials fail before the Bilibili search request and return existing safe credential setup guidance.
- Focused tests, the full suite, build, package inspection, official SDK stdio discovery/call, and one real credentialed discovery-to-evidence workflow pass.

## User Persona

### Primary: Bilibili Evidence Researcher

- **Role**: Uses an MCP-capable Agent to learn from or research Bilibili Videos.
- **Goal**: Start with a subject, identify a useful Video, and verify a relevant statement at its original playback time.
- **Pain point**: The current server is deep after a BVID is known but provides no discovery entry.
- **Technical level**: Any.

## User Stories And Acceptance Criteria

### Discover candidate Videos

**As a** Bilibili evidence researcher,
**I want** to search by topic,
**so that** I can choose a Video without manually finding a BVID.

**Acceptance criteria:**

- [ ] `query` is required, trimmed, non-empty, and at most 100 characters.
- [ ] `limit` is an optional integer from 1 to 10, defaulting to 5.
- [ ] Results preserve Bilibili's comprehensive search order.
- [ ] The first version has no page, cursor, sort, category, or date filters.
- [ ] An empty upstream result is a successful `{ query, results: [] }` response.

### Select a candidate

**As an** Agent,
**I want** enough stable metadata for each candidate,
**so that** I can present a useful choice and pass its BVID to existing tools.

**Acceptance criteria:**

- [ ] Each result contains `bvid`, plain-text `title`, `author`, numeric `duration_seconds`, ISO `published_at`, numeric `view_count`, bounded plain-text `description`, and canonical HTTPS `source_url`.
- [ ] Bilibili search-highlight `<em>` markup is removed from returned text.
- [ ] Descriptions are bounded to 200 Unicode code points plus an ellipsis when truncated.
- [ ] Only entries with `type === "video"`, a valid BVID, and a usable title are returned.
- [ ] Filtering may produce fewer than `limit` results; the tool does not fetch another page to fill the list.
- [ ] No per-result follow-up request is made.

### Receive predictable MCP output

**As an** MCP client integrator,
**I want** a declared structured result with a text compatibility copy,
**so that** clients can consume candidates without reparsing an undocumented payload.

**Acceptance criteria:**

- [ ] `tools/list` exposes the exact `outputSchema`.
- [ ] Successful calls return the same object as `structuredContent` and `JSON.stringify(result, null, 2)` in `content[0].text`.
- [ ] Validation, credential, network, and API errors remain `content + isError` only.

### Enforce authenticated discovery

**As a** user,
**I want** search to use a validated local Bilibili login,
**so that** access behavior and recovery guidance are consistent.

**Acceptance criteria:**

- [ ] Missing local credentials fail without making a Bilibili search request.
- [ ] Configured credentials are checked through the existing login-status path before search.
- [ ] Logged-out or expired credentials return the existing `COOKIE_EXPIRED` guidance without exposing values.
- [ ] Credential use is for reliable access only; the tool does not promise personalized ranking.

## Public MCP Interface

### Tool

`search_bilibili_videos`

### Input

- Required: `query: string`
- Optional: `limit: integer` with minimum 1, maximum 10, default 5

### Successful output

```json
{
  "query": "MCP",
  "results": [
    {
      "bvid": "BV...",
      "title": "Plain title",
      "author": "Uploader",
      "duration_seconds": 1374,
      "published_at": "2025-10-23T07:19:37.000Z",
      "view_count": 155824,
      "description": "Bounded description snippet",
      "source_url": "https://www.bilibili.com/video/BV.../"
    }
  ]
}
```

The inline `outputSchema` requires `query` and `results`; every result requires the eight fields shown above. Do not add `$schema`, `oneOf`, pagination metadata, ranking scores, raw upstream objects, or undocumented extension fields.

## Functional Requirements

### Request flow

1. Validate and trim `query`; validate `limit`.
2. Confirm local credentials exist.
3. Confirm the credentials are logged in through the existing login-status path.
4. Call Bilibili's verified `/x/web-interface/wbi/search/type` endpoint through the existing unsigned HTTP transport with authenticated headers, `search_type=video`, `page=1`, `page_size=limit`, and no custom order.
5. Normalize and defensively cap results to `limit`.
6. Return identical structured and formatted-text payloads.

### Normalization

- Reuse existing authenticated headers, request throttling, timeout, retry, and structured error behavior. Do not add a second signing implementation; the endpoint currently accepts unsigned requests and the call remains isolated for a future transport switch.
- Parse variable-width Bilibili duration text such as `27:6`, `123:28`, or `1:02:03` to integer seconds.
- Convert the positive Unix publication timestamp to an ISO timestamp.
- Remove Bilibili `<em>` search highlights from title and description.
- Construct `source_url` locally from the validated BVID and fixed `https://www.bilibili.com/video/` origin.
- Preserve a valid Video row when secondary metadata is malformed: normalize missing author/description/publication time to `""` and invalid duration/view count to `0`.
- Treat upstream strings as untrusted content; never execute or interpret embedded instructions.

## MVP Scope

### Included

- One new read-only video-discovery tool.
- One verified Bilibili search endpoint.
- Required credential precheck.
- One bounded response shape with dual MCP output.
- Unit, handler, schema, error, stdio, real-client, and discovery-to-evidence acceptance.
- Concise Chinese and English README documentation.

### Out Of Scope

- UP 主、user, series, collection, playlist, bangumi, article, dynamic, or live-room search.
- Pagination, cursors, custom ordering, category/date filters, recommendations, or AI re-ranking.
- Automatic metadata, subtitle, Chapter, comment, or danmaku retrieval for candidates.
- Web scraping, browser fallback, downloads, ASR, embeddings, cross-platform support, remote hosting, or write operations.
- New dependency, cache subsystem, package version, changelog, release, commit, push, branch, or pull request.
- Issue #20's Node engine-floor correction.

## Test And Verification Requirements

- Add failing-first Vitest coverage for:
  - query and limit validation
  - missing and logged-out credentials
  - authenticated search request parameters and exact request count
  - HTML-highlight removal, duration parsing, timestamp conversion, description bounding, invalid-row filtering, limit capping, and empty results
  - exact tool schema and nine-tool order
  - text/structured equality and text-only errors
- Run:
  - `npm test -- tests/bilibili-search.test.ts tests/validation.test.ts tests/server-tools.test.ts tests/server-handler-sanitization.test.ts tests/server-error-next-steps.test.ts tests/mcp-server-smoke.test.ts`
  - `npm run build`
  - `npm test`
  - official SDK `Client + StdioClientTransport` against local `dist/index.js`
  - one real credentialed search followed by a bounded transcript keyword call against a returned BVID with subtitles
  - `npm pack --dry-run --json`
  - `git diff --check`
- Never print or persist Cookie values during verification.

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Bilibili changes or rate-limits the undocumented consumer endpoint | Medium | High | Reuse shared throttle/retry/error paths, keep one bounded request, and cache the verified contract in a dated research note. |
| Search results contain markup or untrusted text | High | Medium | Strip known highlight markup, bound descriptions, and treat every upstream string as data. |
| Forced Cookie setup raises onboarding friction | High | Medium | Reuse existing setup/status tools and return actionable bilingual guidance without exposing values. |
| Search becomes a thin API collection | Medium | High | Keep video-only discovery and require an end-to-end evidence workflow for acceptance. |
| Search response drifts from the schema | Medium | Medium | Normalize at one module boundary and assert the full public schema and result object. |

## Dependencies And Blockers

**Dependencies:**

- Existing `fetchWithoutWBI`, `checkLoginStatus`, `credentialManager`, retry/throttle/error guidance, and MCP structured-output pattern.
- Live interface evidence in `docs/research/2026-07-26-bilibili-video-search-contract.md`.
- Safely stored valid Bilibili credentials for real acceptance.

**Known blockers:**

- None at specification time. If the real endpoint or credentials fail during acceptance, keep the ticket unaccepted and report the exact safe error.

## References

- `CONTEXT.md`
- `docs/research/2026-07-26-bilibili-video-search-contract.md`
- `docs/research/2026-07-25-cross-platform-video-content-mcp-landscape.md`
- `src/bilibili/http.ts`
- `src/utils/credentials.ts`
- `src/server/tool-schemas.ts`
- `src/server/tool-handlers.ts`
