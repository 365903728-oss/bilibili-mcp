# GitHub Source Learning: Authenticated Bilibili Favorites Discovery

## Gate Identity

- Task: implement `list_bilibili_favorite_videos`
- GitHub Issue: [#22](https://github.com/XZXZZX-Ai/bilibili-mcp/issues/22)
- Date verified: 2026-07-27
- Requested prior art: [`Fenglin-Maple/star-owner`](https://github.com/Fenglin-Maple/star-owner)
- Gate owner: Codex
- Gate result: **passed**

## Problem, Invariants, And Non-Goals

Problem:

- The MCP can read a known BVID and search public Videos but cannot automatically discover every Video membership in the current user's Bilibili Favorite Folders.

Invariants:

- The authenticated Bilibili account, not user input, is the identity source.
- Every current created Favorite Folder must be reachable.
- Upstream Favorites requests remain read-only and bounded.
- One MCP call may fetch at most one resource page of 20 rows.
- The MCP returns live discovery data and never persists private Favorites.
- Duplicate BVIDs in different Folders remain distinct Favorite Memberships.
- Existing credential redaction, errors, request throttling, and structured-output behavior remain authoritative.

Non-goals:

- Folder selection by URL/name, Favorites mutation, note generation, transcript prefetch, downloads, ASR, SQLite, filesystem export, background synchronization, task queues, RAG, or global deduplication.

## Discovery Queries

Final bounded query families:

```powershell
gh search repos "bilibili 收藏夹" --archived=false --limit 20 --json fullName,description,stargazersCount,pushedAt,license,url
gh search repos "bilibili favorites" --archived=false --limit 20 --json fullName,description,stargazersCount,pushedAt,license,url
```

Two earlier over-constrained queries (`bilibili favorites knowledge base` and `bilibili favorite folder API`) returned no results and were replaced by the broader bounded queries above.

The user-specified `Fenglin-Maple/star-owner` did not appear in those two result sets, so it was inspected directly. It is the only selected candidate because it is the exact requested product, is active and non-archived, contains the closest production Favorites implementation plus focused verification, and covers both the behavior/state and API mechanism needed by this task. Other results were discovery-only and excluded before source inspection.

## Behavior/Domain Result Ledger

| Repository | Disposition | Reason |
|---|---|---|
| `TLRKFXE/BiliShelf` | excluded | Browser-extension Favorites manager; broader UI/mutation surface, while the exact requested candidate already has production paging and tests. |
| `sweatran/BiliBackup` | excluded | Old backup script last pushed in 2020; persistence-oriented rather than bounded MCP discovery. |
| `oxygenkun/BLSync` | excluded | Synchronization product; local state and mutation semantics are out of scope. |
| `emowen4/bilibili-favlist-links-copy` | excluded | Page button/link copier; no current-account server traversal contract. |
| `MBDAMAO/BiliFavDownloader-Flutter` | excluded | Downloader and Flutter runtime are out of scope. |
| `jqwgt/bilibili-favlist-classifier` | excluded | Mutation/classification userscript with no detected license in search metadata. |
| `reatang/bilibili-my-favorite` | excluded | Favorites manager rather than a bounded read-only evidence-provider seam. |
| `handongccc/py_download` | excluded | Audio download workflow; no detected license in search metadata. |
| `nanana2002/wyy2bili` | excluded | Writes external playlists into Bilibili Favorites; mutation is out of scope. |
| `bagags/music2bb` | excluded | Cross-service playlist-to-Favorites mutation, not account inventory reading. |
| `ZTuTZ/bilibili-rag-java` | excluded | RAG/knowledge application with no detected license; downstream AI is explicitly out of scope. |
| `jinggege666/auto_bili_task` | excluded | Likes/coins/Favorites mutation; no detected license. |
| `Chingliu/onlyfavorite` | excluded | Playback restriction application; no relevant traversal evidence identified from metadata. |
| `kevinliqn/bilifavirousdownload` | excluded | Bulk downloader and persistent download history are out of scope. |
| `Satoing/bilibili-music-helper` | excluded | Filesystem audio synchronization; no detected license. |
| `shangjihao/userscript-bilibili-raindrop` | excluded | Raindrop annotation userscript, not Bilibili account inventory traversal. |
| `minori0721/Bili-favorites-backup` | excluded | Scheduled BBDown/alist archive service with no detected license. |
| `Muhe-nye/QQMusic2BiliFav` | excluded | Cross-service Favorites mutation with no detected license. |
| `wuyilingwei/bilibili-fav-downloader` | excluded | Cookie/guest downloader and aria2 integration are out of scope. |
| `lianjin04/bili-music-player` | excluded | Cached music-player application with no detected license. |

## Mechanism/Technical Result Ledger

| Repository | Disposition | Reason |
|---|---|---|
| `Mr-Po/bilibili-favorites-fix` | excluded | Restores metadata for invalid Favorites; different archival/problem domain and older maintenance. |
| `ayasa520/bilibili-favorites-exporter` | excluded | Export/local-display workflow; selected candidate already provides tested endpoint paging and visibility-gap behavior. |
| `RadiumAg/bilibili-favorites` | excluded | Browser extension for classification/summaries; includes downstream AI/UI outside scope. |
| `AsterisMono/bili-music-sync` | excluded | Audio file synchronization, last pushed in 2022. |
| `shiokiri/bilibili-favorites-crawler` | excluded | Persistent crawler last pushed in 2024; selected candidate is current and closer to the requested product. |
| `XDcedar/bilibili-better-favorite-list` | excluded | CSS-only presentation project with no detected license. |
| `AHCorn/Bilibili-To-Raindrop` | excluded | CSV/Raindrop export and no detected license. |
| `CalculusWJF/bilibili-favorites-organize-by-deepseek` | excluded | AI mutation/classification userscript rather than read-only discovery. |
| `atri1011/Bilibili-Favorites-Classifier` | excluded | AI classifier with no detected license. |
| `xiaokanla/Batch-download-Bilibili-playlists` | excluded | Bulk media download is out of scope. |
| `AHCorn/Bilibili-Favlist-Export` | excluded | CSV/HTML export, no detected license, and no MCP boundary. |
| `atoncooper/MindBase` | excluded | Full ASR/Milvus/RAG knowledge application; downstream system is explicitly out of scope. |
| `nitsaick/bilibili-favorite-folder-downloader` | excluded | Downloader last pushed in 2019. |
| `hhjin/bilibili-favorites-downloader` | excluded | Playwright media download, no detected license, and browser automation is out of scope. |
| `Arthur-Chen-Chinese/Download-Bilibili-Favorite-Videos-B-` | excluded | Downloader last pushed in 2020. |
| `AdlinZ/Netease-Cloud-Music-Playlist-to-Bilibili-Favorites-Tool` | excluded | Cross-service write workflow, not read-only account traversal. |
| `nj-zhangrui-arvin/bilibili-favorites-executor` | excluded | Reviewed mutation-package executor, not discovery. |
| `terawan014/bilibili-fav-duration` | excluded | Duration-only browser extension with no detected license. |
| `EwingYangs/bili2obsidian` | excluded | Obsidian persistence and optional AI summaries; license metadata is non-standard. |
| `MeowBug/ListenBi` | excluded | Android audio player; different runtime and consumer behavior. |

## Selected Candidate

### `Fenglin-Maple/star-owner`

- Full commit SHA: `b6a9c6ce94d04d7fde1a0c683cfda123815c1b1f`
- Default branch: `main`
- Commit date: 2026-07-23
- Commit message: `release: prepare v1.0.3 model state refresh`
- Verified: 2026-07-27
- State: active, non-archived, not a fork
- Latest release: `v1.0.3`, published 2026-07-24, non-draft, non-prerelease
- Search metadata: 14 stars at verification time
- License: GPL-3.0-or-later in `package.json`; repository license recognized as GPL-3.0
- GitHub private vulnerability advisories visible through the authenticated API: 0
- Recursive tree: not truncated

The source was read as untrusted evidence only. No code, test, fixture, prose, asset, dependency, or command was copied or executed.

## Commit-Pinned Evidence Opened

Production and callers:

- [`src/core/bili.js`](https://github.com/Fenglin-Maple/star-owner/blob/b6a9c6ce94d04d7fde1a0c683cfda123815c1b1f/src/core/bili.js)
- [`src/core/collection-state.js`](https://github.com/Fenglin-Maple/star-owner/blob/b6a9c6ce94d04d7fde1a0c683cfda123815c1b1f/src/core/collection-state.js)
- [`src/core/collection-sync-service.js`](https://github.com/Fenglin-Maple/star-owner/blob/b6a9c6ce94d04d7fde1a0c683cfda123815c1b1f/src/core/collection-sync-service.js)
- [`src/core/store.js`](https://github.com/Fenglin-Maple/star-owner/blob/b6a9c6ce94d04d7fde1a0c683cfda123815c1b1f/src/core/store.js)
- [`src/main.js`](https://github.com/Fenglin-Maple/star-owner/blob/b6a9c6ce94d04d7fde1a0c683cfda123815c1b1f/src/main.js)
- [`src/preload.js`](https://github.com/Fenglin-Maple/star-owner/blob/b6a9c6ce94d04d7fde1a0c683cfda123815c1b1f/src/preload.js)
- [`src/renderer/app.js`](https://github.com/Fenglin-Maple/star-owner/blob/b6a9c6ce94d04d7fde1a0c683cfda123815c1b1f/src/renderer/app.js)

Closest verification:

- [`scripts/bili-client-test.js`](https://github.com/Fenglin-Maple/star-owner/blob/b6a9c6ce94d04d7fde1a0c683cfda123815c1b1f/scripts/bili-client-test.js)
- [`scripts/collection-sync-test.js`](https://github.com/Fenglin-Maple/star-owner/blob/b6a9c6ce94d04d7fde1a0c683cfda123815c1b1f/scripts/collection-sync-test.js)

Dependencies and governance:

- [`package.json`](https://github.com/Fenglin-Maple/star-owner/blob/b6a9c6ce94d04d7fde1a0c683cfda123815c1b1f/package.json)
- [`package-lock.json`](https://github.com/Fenglin-Maple/star-owner/blob/b6a9c6ce94d04d7fde1a0c683cfda123815c1b1f/package-lock.json)
- [`LICENSE`](https://github.com/Fenglin-Maple/star-owner/blob/b6a9c6ce94d04d7fde1a0c683cfda123815c1b1f/LICENSE)
- [`SECURITY.md`](https://github.com/Fenglin-Maple/star-owner/blob/b6a9c6ce94d04d7fde1a0c683cfda123815c1b1f/SECURITY.md)
- [`THIRD_PARTY_NOTICES.md`](https://github.com/Fenglin-Maple/star-owner/blob/b6a9c6ce94d04d7fde1a0c683cfda123815c1b1f/THIRD_PARTY_NOTICES.md)

## Seven-Area Trace

### 1. Source of truth and state model

- Live Bilibili data is obtained by `BiliClient.nav`, `listFolders`, and `listVideos`.
- `nav()` supplies `isLogin`, `mid`, user name, and avatar; `listFolders(mid)` uses the authenticated user's numeric identity.
- Folder identity is the remote Folder ID. Persistent collection identity is composed from account ID and Folder ID, not the mutable Folder name.
- Resource identity prefers BVID, then AID, then a derived hash for missing identifiers.
- The sync layer turns the live remote inventory into a persistent SQLite/`sql.js` snapshot with collection/task/video records, tombstones, and transaction records.
- Unknown/temporarily invisible remote data is preserved locally when the Bilibili-reported total is larger than the visible rows.

Local implication:

- Adopt authenticated identity and stable Folder ID.
- Keep Bilibili live responses as the only source of truth for this MCP call.
- Reject every persistent state, fallback identity, tombstone, or derived-hash mechanism.

### 2. Execution path and callers

The selected implementation path is:

1. `src/renderer/app.js` calls `window.orchestrator.listFolders()` and later `syncCollection(...)`.
2. `src/preload.js` maps those calls to `bili:list-folders` and `api:sync-collection` IPC.
3. `src/main.js` refreshes login, captures the current account generation and `mid`, calls `BiliClient.listFolders`, rejects an account change, reconciles persisted Folder state, and dispatches selected-Folder synchronization.
4. `CollectionSyncService.sync/runSync` re-resolves the remote Folder, loads all pages through `BiliClient.listVideos`, verifies that the current account did not change, exports cookies, and applies a database snapshot.
5. `BiliClient.listVideos` requests `/x/v3/fav/resource/list` with `ps=20`, `order=mtime`, and the same parameters independently verified in this repository's live probe.

Nearest local analogue:

- MCP handler → dedicated `favorites.ts` → shared credential/HTTP helpers → one live normalized result.

### 3. Failure semantics

- `fetchJson` uses a 30-second abort timeout, requires JSON, checks HTTP status and Bilibili API code, and propagates failures.
- `listVideos` stops on `!has_more` **or an empty media list**, falls back to page-size inference when `has_more` is absent, waits between looped requests, and caps the desktop full-sync loop at 200 pages.
- It preserves both Bilibili's reported count and visible count and calculates a `visibilityGap`.
- The synchronization service rejects concurrent account sync, checks account identity after long-running network work, records a provisional transaction, restores the previous state on failure/crash, and will not delete unresolved local items when remote visibility is partial.
- Folder disappearance, rename, removal, and unavailable Video titles have explicit persistent state transitions.

Local implication:

- Adopt empty-page termination even if `has_more` is inconsistent.
- Adapt the account-change protection to per-call authoritative identity plus Folder ownership checks.
- Preserve the reported Folder count in the response and avoid claiming that every reported item is visible.
- Reject retries/delays/page-200 cap at the feature layer, transactions, rollback, tombstones, and reconciliation because the MCP writes no state and owns one page per call.

### 4. UI boundaries

- The desktop UI requires the user to load Folders, choose one Folder, and start synchronization.
- It disables the sync button while work is in flight, renders progress, handles empty Folder inventory, shows errors through output and toast, and explicitly displays reported/visible/gap/unavailable counts.
- It protects against stale async Folder results after account switching through serial/generation checks.

Local implication:

- No UI code applies to the stdio MCP.
- The useful interaction principle is to make partial visibility and continuation explicit. The user has already rejected manual Folder selection, so the MCP traverses all Folders automatically.

### 5. Verification

- `scripts/bili-client-test.js` exercises Bilibili client normalization and a partial-visibility result where reported total exceeds visible rows.
- `scripts/collection-sync-test.js` is an integration-style script covering Folder/video mocks, visibility-gap preservation, removal/restoration, rollback after a fetch failure, and startup recovery.
- `package.json` exposes these as `test:bili-client` and `test:collection-sync`.
- The tests are Node assertion scripts, not a unit-test framework. The Bili client test does not assert the exact pagination URL, the 20-row maximum, malformed BVID filtering, or a cursor because the candidate has no cursor interface.
- No candidate command was executed.

Local implication:

- Keep the repository's stronger Vitest plan: exact paths/params/counts, empty-page termination, cursor validation/progression, strict BVID normalization, private-data redaction, and MCP structured-output validation.

### 6. Dependencies and runtime

- The candidate is a private Electron 43 application requiring Node 22.
- It has a postinstall Electron setup script and runtime dependencies for SQLite/WASM, Markdown, Mermaid, PDF, and DOCX handling.
- Portable releases also bundle Python, faster-whisper, CTranslate2, FFmpeg, yt-dlp, models, and optional NVIDIA components.
- The Favorites client itself uses built-in fetch and Electron session cookies, but its end-to-end workflow exports plaintext Netscape Cookie files and writes SQLite/workspace artifacts.

Local implication:

- Adopt no dependency.
- Continue using the existing Node 18-compatible MCP transport and local credential manager.
- Reject Electron sessions, postinstall behavior, Python/media runtime, downloads, and Cookie export.

### 7. Governance and provenance

- The selected commit is a full 40-character SHA and the recursive tree was not truncated.
- The project is active, non-archived, non-forked, and published a current `v1.0.3` release.
- Application code is GPL-3.0-or-later. Third-party notices enumerate separate runtime licenses and warn about GPL/proprietary binary obligations.
- `SECURITY.md` treats Cookies, account identifiers, workspaces, databases, downloaded media, and generated knowledge as sensitive. It documents local-only API, browser, filesystem, safeStorage, and release-hygiene boundaries.
- GitHub reported zero repository security advisories through the authenticated API at verification time; this is not a code-security audit.
- No relevant file was a submodule or identified as generated/vendored source. Binary runtime files exist in the tree but were not opened or executed.

Local implication:

- This work adopts principles only. It copies no source, fixture, prose, asset, or test.
- The local implementation is independently specified by the live first-party Bilibili contract and this repository's own architecture.

## Execution And Failure Trace

Candidate execution trace:

```text
Renderer "load folders"
  → preload IPC bili:list-folders
  → main refresh/current-user generation guard
  → BiliClient.listFolders(nav.mid)
  → created/list-all
  → user selects one Folder
  → preload IPC api:sync-collection
  → CollectionSyncService
  → BiliClient.listVideos
  → resource/list pages of 20 until !has_more or empty
  → visibility-gap calculation
  → account recheck
  → persistent transactional snapshot
```

Nearest candidate failure path:

```text
HTTP / JSON / API / pagination / account-change failure
  → reject list/sync promise
  → rollback recorded collection transaction
  → restore prior local snapshot
  → UI error state/toast
```

Adapted local execution trace:

```text
MCP list_bilibili_favorite_videos(cursor?)
  → validate/decode cursor before side effects
  → require local Cookie
  → nav establishes current mid
  → created/list-all re-establishes owned Folder order
  → cursor Folder ownership check
  → at most one resource/list page with ps=20
  → strict normalization + reported Folder count + skipped count
  → next opaque cursor, or completion
```

Adapted local failure path:

```text
Malformed/stale cursor, missing login, network/API failure, or unsafe response identity
  → existing structured text-only error path
  → no private persistence and no partial local mutation to roll back
```

## Decision Register

| Decision | Status | Evidence | Exact handoff/Plan effect |
|---|---|---|---|
| Use `nav.mid` as current-account truth before Folder enumeration. | adopt | `bili.js`, `main.js` | Keep the mandatory authenticated nav request; never accept account ID input or rely only on configured `DedeUserID`. |
| Use stable Folder ID rather than Folder name for continuation. | adopt | `collection-sync-service.js` | Cursor identifies the next Folder ID/page; current Folder ownership is rechecked each call. |
| Use `created/list-all` then `resource/list` with `ps=20`, `order=mtime`, and terminal `has_more`. | adopt | `bili.js`, independently verified live contract | Keep exact endpoint/parameter tests and one resource page per call. |
| Treat an empty media page as terminal even if `has_more` is inconsistent. | adopt | `bili.js` | Add explicit empty-page continuation to the next Folder and a regression preventing cursor loops. |
| Distinguish Bilibili-reported Folder count from visible/normalizable rows. | adapt | `bili.js`, `bili-client-test.js`, `collection-sync-service.js` | Keep `folder.media_count` as the reported count; keep page-local `skipped_count`; document that reported count is not a snapshot/visibility guarantee. |
| Detect account changes during a long operation. | adapt | `main.js`, `collection-sync-service.js` | The MCP performs no long loop; validate Folder `mid` against nav identity when present and re-establish identity/ownership on every cursor call instead of adding process-global generation state. |
| Fetch every page inside one function with delay and a 200-page cap. | reject | `bili.js` | One MCP call fetches one page only. Shared 500 ms admission and client-driven cursor continuation replace the desktop loop. No arbitrary 4,000-item Folder ceiling. |
| Preserve local unresolved state when remote visibility is partial. | reject | `collection-sync-service.js` | No local state exists. Surface reported count/skipped rows and make no completeness claim beyond pages actually returned. |
| Export Cookie files for downstream media tools. | reject | `bili.js`, `SECURITY.md` | Credentials remain inside existing request headers; no Cookie export or response field. |
| Persist Folder/video/task snapshots, tombstones, transactions, and exports. | reject | `collection-state.js`, `collection-sync-service.js`, `store.js` | No database/filesystem/cache/background sync. |
| Normalize cover, description, raw upstream link, AID fallback, and derived missing-ID hashes. | reject | `bili.js`, `collection-sync-service.js` | Return only strict valid-BVID Video candidates and construct canonical HTTPS source URLs locally. |
| Let the user choose one Folder by name/ID. | reject | `renderer/app.js`, `collection-sync-service.js` | User explicitly requires automatic all-Folder traversal and no Folder input. |
| Reuse candidate code directly. | reject | GPL-3.0-or-later and source-learning trust boundary | Implement independently from local PRD, live first-party contract, and tests; no copied code or fixtures. |
| Exact behavior when Bilibili's reported count permanently exceeds all visible rows. | unresolved | Candidate visibility-gap model; local live sample did not reproduce a gap | Keep `media_count` and page-local `skipped_count`; add a documented caveat and redacted real-acceptance count check. Do not add persistence or synthetic missing records. |

## Plan/Handoff Mapping

The implementation handoff must cite this report and incorporate:

1. Empty media list terminates the current Folder even when `has_more` is true.
2. `folder.media_count` is explicitly a Bilibili-reported count, not a guarantee that all rows are currently visible or callable.
3. Folder rows whose present `mid` disagrees with authenticated `nav.mid` are rejected from the owned Folder set.
4. Tests cover empty-page loop prevention, reported-count/visible discrepancy, and account-identity mismatch.
5. Full-loop delays, a 200-page cap, persistence, Cookie export, synchronization, deletion reconciliation, and UI remain out of scope.

## Missing Or Unverified Evidence

- The selected tree was not truncated.
- Relevant production, callers, focused tests, manifest, lockfile header, license, security policy, notices, release, and advisory count were accessible.
- No separate `NOTICE` file exists beyond `THIRD_PARTY_NOTICES.md`.
- Candidate integration tests were inspected but not executed.
- The candidate has no cursor interface and therefore no cursor verification.
- The candidate's `listVideos` exact URL is not asserted by its focused Bili client test.
- GitHub's zero-advisory response does not prove the absence of vulnerabilities.
- Real Bilibili visibility gaps, deleted rows, and account switching during one local MCP request remain acceptance/caveat concerns, not reasons to expand scope.

## Gate Status

**Passed.** The requested Star-Owner source has been traced at a full pinned commit through production code, callers, failure/state handling, UI, verification, dependencies, and governance. Decisions are mapped to Issue #22's handoff without expanding product scope or copying source.
