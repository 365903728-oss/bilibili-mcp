# Changelog

All notable changes to the **Bilibili MCP Server** will be documented in this file.

---

## [Unreleased]

---

## [1.13.0] - 2026-08-20

### Added
- Added the 11th tool `search_bilibili_creators`, returning Creator candidates in Bilibili's platform order. `limit` defaults to 5 and is capped at 10; each candidate includes the stable numeric `mid` (the only identity), name, bio, avatar URL, follower count, video count, level, and a locally derived source URL. Display names are fuzzy and non-unique; candidates are returned as candidates only — the tool never selects one Creator and never crawls candidate content. (Issue #45)
- Creator Search success returns formatted JSON text plus identical MCP `structuredContent`; it requires configured, logged-in Bilibili Cookies and never falls back to anonymous search.
- Added the 12th tool `get_bilibili_creator_content`, starting from a selected Creator's stable numeric `mid` and reading `overview`, `videos`, `collections`, `series`, or `dynamics`. Every non-overview call returns at most one 20-row page and continues with an opaque `next_cursor` bound to the Creator, section, and container. (Issues #46-#48)
- The Video catalog keeps ordinary uploads, collaboration rows, and videos with an upstream charge marker when they are listable to the logged-in identity, returning BVIDs and bounded metadata that feed the existing evidence tools. Listing visibility does not prove playback entitlement, so `access` stays `unknown` and no per-row access probe is added.
- Collections and Series remain distinct container types. Callers can list containers or read one container's members, while the same BVID keeps each membership when it appears in multiple contexts instead of being deduplicated across containers.
- Creator Dynamics cover original posts, reposts, text, images, Video shares, and unknown types with bounded text, image URL/dimensions, referenced BVIDs, and original-post relationships. The MCP does not download or interpret images, extract dedicated long-form article/Opus bodies, or fetch referenced Videos automatically.

### Security and compatibility
- Both Creator tools require configured, valid login credentials and reuse the existing timeout, throttling, retry, response-size, and structured-error boundaries. HTTP 412, authentication, API, and malformed-response failures never become empty successes.
- Discovery stays bounded: it never batch-fetches transcripts, comments, OCR, vision output, or per-row details. Pagination reflects live Bilibili state and is not a snapshot guarantee.

### Verified
- Passed the TypeScript build and 1058 tests across 42 files; also passed a 193-file npm package check, a zero-vulnerability audit of 97 production dependencies, five-field version parity, and credential scanning of the current release tree and this change.

---

## [1.12.0] - 2026-08-18

### Added
- Distinguish Bilibili AI subtitles from human subtitles: when any Bilibili AI track (`ai-zh`, `ai-en`, or another `ai-*` language) is selected, both `get_video_transcript` and `get_video_info` return `data_source: "ai_subtitle"` (no longer `"subtitle"`; managed local ASR stays `"asr"`). `ai_subtitle` is Bilibili AI transcription, may be inaccurate, and is not equivalent to a human-checked citation.
- New optional `exclude_ai_subtitles` (default `false`) on `get_video_transcript` and `get_video_info`: filters AI tracks before selection and prefers remaining human subtitles; AI-only results are treated as definitive absence (transcript may use explicit ASR/description fallback; video-info returns the description). The video-info cache key includes this option.
- New optional `force_asr` (default `false`) on `get_video_transcript`: bypasses subtitle selection and transcribes the resolved Part with the ready local ASR, without requiring `fallback_to_asr`, and wins over `exclude_ai_subtitles`.
- Every selected `ai-*` track is unconditionally read twice and passes a deterministic integrity assessment before its body is returned: cross-read stability (two reads with different normalized bodies are unusable; applies to every `ai-*` language) and language (ai-zh only: a body with at least 80 Unicode letters and under 10% Han letters is an `ai-zh` mismatch; other `ai-*` languages are not rejected for being non-Chinese). An unusable track with `fallback_to_asr: true` invokes the local ASR, otherwise the existing `fallback_to_description` contract applies (`SUBTITLE_UNAVAILABLE` when no fallback is authorized); video-info returns the description without caching it. Stable same-language bodies that are semantically off-topic are an accepted limitation, controlled by `force_asr` / `exclude_ai_subtitles`. A transport, timeout, auth, or parse failure on the second read remains an error and never becomes an integrity failure or ASR trigger.
- Added `--non-interactive` (uses already-loadable credentials from environment variables or the global config file; never prompts and never reads credential values from stdin/argv; without `--asr-model` it confirms loadability and exits successfully) and `--asr-model <tiny|base|small>` (requires `--non-interactive`; installs the given model) to `setup`.

### Verified
- Passed the TypeScript build and 906 tests across 41 files with the publish workflow's Node.js `22.14.0` and npm `11.18.0`; also passed a 189-file npm package check, zero-vulnerability production audit, version-parity checks, and credential scanning.

---

## [1.11.4] - 2026-08-09

### Fixed
- Corrected top-level comment `limit` semantics with a fixed upstream `ps=20`, bounded pagination, and local truncation to the caller-visible limit; missing or non-array `replies` containers now fail closed instead of being treated as empty pages. Also standardized supported-language validation while preserving `ai-zh`, protected existing credentials from blank replacement, enforced strict numeric environment configuration, and made Bilibili JSON `-403` classification endpoint-aware. (PR #26)
- Hardened search response shapes: explicit `result: []` remains a successful one-request empty result; missing or non-array `result` values receive one abort-aware shape retry before returning `UPSTREAM_RESPONSE_INVALID`. A valid second response recovers, while network, HTTP-status, and abort errors are not retried by the search layer. (PR #27)

### Verified
- The final automated suite passed 862 tests across 41 files, covering comment pagination boundaries, malformed reply containers, explicit-empty search results, malformed-search recovery, and MCP error mapping. TypeScript build, real MCP stdio protocol smoke, a 185-file npm package check, production dependency audit, and credential scanning also passed. Authenticated live smoke covered normal success paths: repeated searches returned stable results and comment limits of 21 and 50 reached their caller-visible caps. Malformed, explicit-empty, and upstream-error paths remain deterministically automation-backed. No Cookie value appeared in output.

---

## [1.11.3] - 2026-08-06

### Fixed
- Fixed the Official MCP Registry namespace casing: `mcpName` and `server.json.name` corrected from `io.github.xzxzzx-ai/bilibili-mcp` to `io.github.XZXZZX-Ai/bilibili-mcp`, matching the case-sensitive GitHub-authorized permission (`io.github.XZXZZX-Ai/*`); the v1.11.2 publish attempt returned HTTP 403 on the casing mismatch. No runtime, MCP tool, or dependency changes.

### Verified
- Passed the TypeScript build, 39 files / 803 tests, and `npm pack --dry-run` (181 files, including the corrected `mcpName`); `package.json` and the lockfile both report `1.11.3`.

---

## [1.11.2] - 2026-08-06

### Added
- Added Official MCP Registry metadata: `mcpName` in `package.json` and a root `server.json` pointing to npm package `@xzxzzx/bilibili-mcp` v1.11.2 (stdio transport). No runtime, MCP tool, or dependency changes.

### Verified
- Passed the TypeScript build, 39 files / 803 tests, and `npm pack --dry-run` (181 files, including `mcpName`; `server.json` stays at the repository root for the Official Registry); `package.json` and the lockfile both report `1.11.2`.

---

## [1.11.1] - 2026-08-05

### Fixed
- Valid Bilibili AI subtitle numeric IDs above `Number.MAX_SAFE_INTEGER` are no longer rejected as invalid metadata; the public response shape and remaining validation are unchanged. (Issue #24, PR #25)

### Acknowledgements
- Thanks to [@CYL-collab](https://github.com/CYL-collab) for reporting the issue and contributing the fix.

### Verified
- Passed the TypeScript build, 39 files / 803 tests, a production dependency audit with zero vulnerabilities, a 181-file package dry run (dist entry points and public docs included; source, tests, internal records, local config, credentials, and Smithery files excluded), `git diff --check`, strict UTF-8, and value-free secret classification; `package.json` and the lockfile both report `1.11.1`.

---

## [1.11.0] - 2026-08-05

### Added
- Added `setup` command: interactive credential setup that auto-guides when unconfigured and shows current state when already configured. Offers optional ASR model installation after credential setup (defaults to No).
- Added `doctor` command and `doctor --json`: purely local status check (package info, runtime, credential loadability, ASR status) with no network requests. `--json` emits machine-readable output for Agents.
- Added optional ASR model installation: default-off, offers three model choices (tiny 78 MB / base 148 MB / small 486 MB) with Enter defaulting to recommended small. Installs into a user-managed `~/.bilibili-mcp/asr/` directory, verified via CPU INT8 load.
- Added explicit `fallback_to_asr` to `get_video_transcript` (default `false`). Native subtitles always win; only confirmed subtitle absence retrieves temporary audio for one resolved Part and transcribes it with the ready project-managed faster-whisper model. ASR returns `data_source: "asr"` and reuses timestamps, ranges, keyword/context search, and evidence links.

### Fixed
- Fixed duplicated `[command]` placeholder in CLI help output; unified to a single Commander dispatch path.
- Fixed internal validation-error disclosure for non-string video input and tightened subtitle URL host, port, and userinfo validation.

### Changed
- Updated recommended setup commands in documentation from `config` to `setup` (`config` remains available for forced reconfiguration).
- Raised package Node.js engine minimum to `>=20.0.0`.
- Upgraded the MCP TypeScript SDK compatibly to `1.30.0` and refreshed the lockfile to a production dependency set with no known advisories.

### Security
- ASR accepts only Bilibili-specific HTTPS CDN hosts and revalidates up to three redirects. Cookies go only to the playback API, never the CDN or Python child; signed playback URLs are excluded from results, errors, and logs.
- ASR uses a unique OS temp directory, hard 128 MiB / two-hour / 30-minute / 2 MiB / 10,000-segment bounds, one active job with no queue, an isolated child environment, strict NDJSON, and cleanup after success, failure, or timeout.
- Added shared size, time, count, and concurrency budgets across stdio, MCP responses, Bilibili HTTP, caches, logs, playback audio, and ASR. Playback downloads validate public DNS answers, pin the connection, and strip credentials on every hop.
- Sanitized control, bidirectional override, zero-width, and unpaired-surrogate content from Bilibili. ASR state uses owner-only directories, unpredictable exclusive temporary files, atomic replacement, and rejects symlinks or incorrect path types.

### Documentation
- Rewrote both READMEs with visible prerequisites, scannable install steps, and product-outcome feature groups. Corrected `skipped_count` to count only video entries; corrected comment ordering to prioritize timestamp-bearing and higher-liked comments. Chinese copy uses natural terms throughout; BVID explained at first use.
- Added a text-free project overview Hero showing video discovery flowing through the local MCP server into transcript search, chapters, comments, and Favorites. Existing install-flow and Favorites-pagination illustrations remain scoped to their own sections.

### Verified
- ASR Phase 3 passes the TypeScript build, 10 focused files / 356 tests, 29 files / 629 full tests, a 156-file package dry run, public stdio initialize/list/call, scoped secret scanning, and zero post-test temp residue. No ready local model existed, so no model was downloaded and no live ASR transcription was run.
- Final security regression passes the TypeScript build, 39 files / 803 tests, 95 focused stdio/tool/handler tests, a 180-file package dry run, zero `npm audit --omit=dev` vulnerabilities, value-free secret classification, and zero ASR state temporary-file residue.

---

## [1.10.1] - 2026-07-27

### Documentation
- Reworked both README openings around discovering Videos from the current account's Favorites or a topic, obtaining BVIDs, and letting users request transcripts, metadata, chapters, or comments only when needed.
- Narrowed both GitHub-safe SVG heroes to complete Favorites traversal: start without `cursor`, read at most 20 rows per call, keep passing `next_cursor`, and finish when that field is absent while preserving Folder context, titles, and BVIDs.
- Reorganized the ten MCP tools, setup entry point, design priorities, and behavior boundaries, explicitly leaving knowledge-note generation to the user.

### Verified
- Passed bilingual README audits, local-link and heading-parity checks, SVG XML/safety checks, 900px/360px rendering, npm package dry-run, credential-pattern scanning, the TypeScript build, and the full test suite.

---

## [1.10.0] - 2026-07-27

### Added
- Added `list_bilibili_favorite_videos` (the 10th tool), which automatically discovers every created Favorite Folder of the currently logged-in account and returns Folder/page-bounded Video memberships. Each call returns at most one upstream page (fixed at 20 rows); the optional `cursor` is an opaque, stateless, versioned base64url token that encodes only the next Folder ID and page number — never Cookie values, account IDs, Folder titles, or Video data. Agents follow `next_cursor` until it is absent. (Issue #22)
- Successful calls return formatted JSON text plus identical MCP `structuredContent`; an account with no valid Folders returns only `folders_total: 0`, `videos: []`, `skipped_count: 0`.
- Added `validateFavoritesCursor` public input validator; the favorites module performs strict decoding (type/length/charset/JSON/version/positive safe-integer Folder ID and page) before any network request.

### Security
- Favorites discovery must start from the currently logged-in account identity; it never falls back to anonymous access and never reads another user's public Favorites. Each call makes at most one nav request, one created/list-all request, and zero or one resource/list request; no transcript/comment/chapter/search/download/persistence/cache/write request is made.
- Cursor is strictly validated before any side effect; the same BVID appearing in multiple Folders stays visible per Folder context (no cross-Folder dedupe); `skipped_count` reports rows that could not be safely normalized and never triggers a replacement request.

### Verified
- Passed 405 tests across 25 files, the TypeScript build, official MCP SDK stdio ten-tool order plus real paginated continuation acceptance, npm package dry-run (138 files), and credential/private-data scanning.

---

## [1.9.1] - 2026-07-26

### Documentation
- Reduced both READMEs to concise project homepages and centralized the Agent installation prompt, 33 client configurations, credential validation, runtime environment variables, and source setup in bilingual installation guides.
- Moved complete tool parameters, call examples, error semantics, and request controls into bilingual tool references, and included these documents in the npm package.
- Redrew both GitHub-safe SVG heroes with a stable single-title and three-step evidence layout, removing font-fallback and fixed-coordinate alignment failures.

### Verified
- Passed bilingual README audits, desktop and narrow SVG rendering, client and environment-variable coverage checks, credential-focused tests, npm package dry-run, link validation, and credential-pattern scanning.

---

## [1.9.0] - 2026-07-26

### Added
- Added `search_bilibili_videos` to return normal Video candidates in Bilibili's platform relevance order. `limit` defaults to 5 and is capped at 10; each candidate includes its BVID, title, author, duration, publication time, view count, description, and source URL. (Issue #21)
- Successful searches return both formatted JSON text and identical MCP `structuredContent`, so a candidate BVID can be passed directly to the existing transcript, metadata, chapter, and comment tools.

### Security
- Video search requires valid, logged-in Bilibili Cookie credentials and does not fall back to anonymous access. Credential failures retain the existing safe setup guidance without exposing Cookie values in responses or logs.

### Verified
- Passed 327 tests, TypeScript build, official MCP SDK 1.27.1 nine-tool stdio acceptance, a real search-to-transcript-timestamp workflow, npm package dry-run, and credential-pattern scan.

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
