# Changelog

All notable changes to the **Bilibili MCP Server** will be documented in this file.

---

## [Unreleased]

---

## [1.8.0] - 2026-07-26

### Added
- `get_video_transcript` returns the same successful result as MCP `structuredContent` alongside the existing formatted JSON text, and declares an `outputSchema` matching the complete current result. The legacy text format is unchanged, error results remain text-only `content + isError`, and the other seven tools and Bilibili request count are unchanged. (Issue #16)
- Successful transcript results now include a root-level `source_url`, and each keyword-search `Transcript Match` includes a `timestamp_url` that opens the exact Bilibili Video or Part and cited subtitle moment. BVID casing is preserved. (Issue #17)

### Security
- Refreshed the lockfile to `body-parser` 2.3.0 and `fast-uri` 3.1.4 within their existing compatible ranges, clearing three production advisories without a new direct dependency or override. Node 18 support remains; the unused Hono `serveStatic` advisory continues to track its upstream fix. (Issue #19)

### Verified
- Passed 299 tests, TypeScript build, npm package dry-run, production dependency advisory audit and reachability triage, and credential-pattern scan.

---

## [1.7.2] - 2026-07-20

### Added
- `get_video_transcript` supports optional keyword search: new `query`, `max_matches`, `context_segments` parameters, returning timestamped `Transcript Match` entries with bounded context and a compact transcript. Case-insensitive literal matching with zero extra network requests.
- New validators: `validateQuery`, `validateMaxMatches`, `validateContextSegments`.

### Changed
- Keyword search is incompatible with description fallback; search mode never silently falls back to video description.
- `getVideoTranscriptData` accepts an optional `TranscriptSearchOptions` object (8th parameter), preserving all existing call compatibility.

### Verified
- 286 tests (42 new), TypeScript build, npm package dry-run, MCP smoke test, and git diff --check.

---

## [1.7.1] - 2026-07-20

### Docs
- Updated both README release links to `v1.7.1`.
- Documented `BILIBILI_CACHE_SIZE` and `USER_AGENT` runtime tuning environment variables, noting that a restart is required.
- Updated build command wording to "Clean `dist/` then compile TypeScript".
- Updated development-process facts to 8 MCP tools, 244 unit tests, and the current bounded Codex/Paseo/Claude workflow.

### Maintenance
- Deleted the legacy authentication module (`src/bilibili/auth.ts`) and inert package configuration code.
- Runtime cache capacity is now wired to `config.maxCacheSize`; the previous hard-coded value was removed.
- `npm run build` cleans `dist/` before TypeScript compilation so deleted modules no longer survive as publishable artifacts.

### Verification
- Passed 244 tests across 23 Vitest files, the TypeScript build, npm package dry-run, and credential-pattern scan.
---

## [1.7.0] - 2026-07-20

### Added
- Video transcript (`get_video_transcript`) supports multi-Part selection (`page`), timestamp output (`include_timestamps`), and time-range filtering (`start_seconds` / `end_seconds`).
- Video metadata (`get_video_metadata`) returns multi-Part listing (`pages`).
- New `get_video_chapters` tool returns Bilibili-provided Chapter intervals (view_points).
- `get_video_info` accepts optional `page` parameter for multi-Part videos.

### Fixed
- Multi-Part CID resolution is centralized in a shared navigation module.
- Cache keys include page numbers to prevent cross-Part cache collisions.

### Verification
- Passed 243 tests across 23 Vitest files, TypeScript build, production dependency audit, and npm package dry-run.

---

## [1.6.4] - 2026-07-20

### Fixed
- Concurrent HTTP requests now receive start admission at the configured interval while response bodies remain free to overlap.
- Empty subtitle lists share one login-status check, and description fallbacks caused by transient subtitle failures are no longer cached.
- Comment cache keys include detail level and explicit limit; redundant metadata lookup was removed; bounded pagination now honors `limit: 1-50`.
- Login-status, subtitle, and WBI requests preserve HTTP status for retry decisions, normalize transport failures, and clean up request timers deterministically.
- The MCP stdio startup test now waits for the observable ready signal instead of a fixed 300ms delay.

### Security
- Updated the transitive Hono dependency from 4.12.23 to 4.12.31, clearing the high-severity production dependency audit finding.

### Verification
- Passed 180 tests across 20 Vitest files, the TypeScript build, production dependency audit, npm package dry-run, MCP stdio smoke, and credential-pattern scan.

---

## [1.6.5] - 2026-07-20

### Fixed
- MCP server metadata version now reads from `package.json` at runtime instead of the hard-coded `"1.0.0"`, so tool discovery surfaces the actual package version.

### Verification
- Passed 181 tests across 20 Vitest files, the TypeScript build, production dependency audit, npm package dry-run, and credential-pattern scan.

---

## [1.6.3] - 2026-06-19

### Fixed
- Included the bilingual credential next-step helpers required by the structured error payload mapper, fixing the v1.6.2 publish workflow failure on a clean checkout.
- Added the `notes_en` / `notes_zh` package-update response implementation and tests so the published package behavior matches the README documentation.

### Verification
- Re-ran the full Vitest suite, TypeScript build, npm package dry-run, and equivalent MCP stdio smoke.

---

## [1.6.1] - 2026-06-18

### Docs
- Added explicit Chinese README guidance for `@latest` MCP configs, global install updates, and `bilibili-mcp check-update`.
- Added `check_mcp_update` to the English agent-install guidance.
- Added `check_mcp_update` to the English tool selection table and added Chinese/English tool call examples.

---

## [1.6.0] - 2026-06-18

### Added
- Added `check_mcp_update`, a safe MCP tool that reports the local package version, npm latest version, update availability, and recommended update commands.
- Added `bilibili-mcp check-update` for CLI-based package freshness checks.

### Changed
- MCP client setup examples now prefer `npx -y @xzxzzx/bilibili-mcp@latest` so new client sessions resolve the latest npm release.
- Credential setup guidance and credential-related error next steps now use the `@latest` package spec.
- README status text now reflects 7 MCP tools and 145 unit tests.

### Tests
- Added package update guidance tests and updated MCP tool-list contract tests for the new public tool.

---

## [1.4.1] - 2026-06-04

### 🔧 Changed
- README restructure: improved hero, AI client setup guide, and tool call examples readability

## [1.4.0] - 2026-06-04

### 🚀 Added
- **Two new MCP tools**:
  - `get_video_transcript`: Returns clean subtitle text. Does not silently fall back to description by default; returns `SUBTITLE_UNAVAILABLE` when subtitles are unavailable.
  - `get_video_metadata`: Returns title, author, duration, publish date, description, tags, and stats without fetching subtitles or comments.
- `get_video_comments` now supports `limit` (1-50), `sort` (hot/time), `include_replies` (boolean). Old calling style remains compatible.

### 🔧 Changed
- **Security hardening**: Preserved Cookie-backed subtitle access while requiring credentials to come from environment variables or the credential helper; package contents, docs, tests, and examples do not include real Cookie values.
- **Package entry points**: `main`/`module`/`types` in `package.json` now correctly target `dist` build output.
- **Smithery removal**: Deleted `smithery.json`, `smithery.yaml`, `@smithery/cli` dependency, and related scripts.
- **Bilibili module split**: Refactored the large `client.ts` into focused modules (`http.ts`, `wbi.ts`, `fingerprint.ts`, `video-api.ts`, `comments-api.ts`) while preserving public API compatibility.
- Subtitle fallback, WBI signing, and buvid fingerprint behavior are unchanged.

### 🧪 Tests
- Real Vitest baseline: 110 unit tests covering validation, BVID parsing, input sanitization, subtitle fallback, comment wrapper controls, MCP schemas, and API behavior.
- Tests do not require real network access, Cookies, or external APIs.

### 📝 Docs
- README updated: all 4 tools documented, new comment parameters, no-cookie and Cookie-backed behavior, error codes, and standard degradation strategy.

## [1.3.7] - 2026-03-09

### 🚀 Added
- **Intelligent Cookie Expiration Detection**: When the subtitle interface returns an empty list, the tool now calls `/x/web-interface/nav` to verify the current login status before deciding whether to trigger a `COOKIE_EXPIRED` error.
  - If **Logged In** but no subtitles → Gracefully falls back to the description (normal behavior).
  - If **Not Logged In** (Cookie expired) → Throws a clear error to prevent "silent degradation," making it easier for users and AI to troubleshoot.
- *Security Note*: Error messages only contain status descriptions and are **strictly de-identified, never leaking actual Cookie content**.

---

## [1.3.5] - 2026-03-08
- Initial stable release with support for basic video info and comment fetching.
