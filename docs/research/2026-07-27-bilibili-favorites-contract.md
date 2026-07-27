# Research Note: Authenticated Bilibili Favorites Contract

## Research Topic

- Topic: First-party contract for current-account Favorite Folder and Video traversal
- Date: 2026-07-27
- Owner: Codex
- Related task: `list_bilibili_favorite_videos` MVP
- Probe window: 2026-07-27 07:51-07:58 UTC+8
- Refresh before: implementation if this note is older than 30 days, or immediately after a Favorites API behavior change

## Question

Which current Bilibili first-party endpoints and limits can support a read-only MCP tool that automatically discovers every created Favorite Folder of the locally authenticated account and safely traverses its Video memberships?

## Context

Why this matters for `@xzxzzx/bilibili-mcp`:

- The user wants the MCP to start from their account rather than requiring a Folder URL.
- Favorites can contain private interest data, so identity, ownership, logging, and response bounds must be explicit.
- A full account may contain far more data than one MCP response or one upstream request can safely carry.

What decision or implementation this may affect:

- Public cursor semantics, page size, request ownership, credential gating, normalization, and privacy controls for a new Favorites Discovery tool.

## Sources

| Source | Type | Date checked | Notes |
|--------|------|--------------|-------|
| [`/x/web-interface/nav`](https://api.bilibili.com/x/web-interface/nav) | Official API, live authenticated probe | 2026-07-27 | Confirmed a successful response can establish explicit login state and the authenticated account ID. No account value was recorded. |
| [`/x/v3/fav/folder/created/list-all`](https://api.bilibili.com/x/v3/fav/folder/created/list-all) | Official API, live authenticated probe | 2026-07-27 | Confirmed the current account's created Folder list and observed its response keys. No Folder ID or title was recorded. |
| [`/x/v3/fav/resource/list`](https://api.bilibili.com/x/v3/fav/resource/list) | Official API, live authenticated probe | 2026-07-27 | Confirmed Folder resource paging, response keys, page-size limit, adjacent-page behavior, and terminal `has_more`. No Video identity or text was recorded. |
| [`src/bilibili/http.ts`](../../src/bilibili/http.ts) | Current repository source | 2026-07-27 | Existing authenticated request transport, throttle, retry, timeout, API error, and redacted logging behavior. |
| [`src/utils/credentials.ts`](../../src/utils/credentials.ts) | Current repository source | 2026-07-27 | Existing local-only Cookie loading and authenticated header construction. |

No third-party API catalog, tutorial, copied implementation, or private response content was used as contract evidence.

## Safe Probe Shape

The probe loaded credentials only through the repository's credential manager and never printed request headers. It recorded only HTTP/API success, response key names, field types, row counts needed to establish paging behavior, and overlap counts.

The successful sequence was:

1. `GET /x/web-interface/nav` with authenticated headers.
2. Require API code 0, `data.isLogin === true`, and a positive safe-integer `data.mid`.
3. `GET /x/v3/fav/folder/created/list-all?up_mid=<authenticated-mid>`.
4. Select an owned Folder ID in memory without printing it.
5. `GET /x/v3/fav/resource/list` with:

   ```text
   media_id=<owned-folder-id>
   pn=<positive page>
   ps=20
   keyword=
   order=mtime
   type=0
   tid=0
   platform=web
   ```

No Cookie, account ID, Folder ID, Folder title, Video ID, Video title, uploader, cursor, or private payload was written to this note.

## Findings

### Authenticated identity

- The navigation endpoint returned HTTP 200, API code 0, `isLogin: true`, and a numeric `mid` for the configured local credential.
- The account ID should come from this authenticated response. Using a user-supplied ID or trusting only the configured `DedeUserID` would weaken the “current logged-in account” contract.
- Favorites Discovery must stop when a local Cookie is unavailable or navigation does not establish an explicit logged-in identity. It must not fall back to another user's public Folders or anonymous access.

### Created Favorite Folders

- The created-Folder endpoint returned HTTP 200 and API code 0.
- Observed `data` keys were `count`, `list`, and `season`.
- `data.list` was an array. Observed Folder-row keys were:
  - `attr`
  - `fav_state`
  - `fid`
  - `id`
  - `is_kid_playlist`
  - `kid_playlist_desc`
  - `media_count`
  - `mid`
  - `title`
- The live account returned multiple Folder rows, including the default/custom created-Folder surface expected by the Bilibili Favorites UI.
- The MVP should use only `id`, `title`, and `media_count`; it should not expose or infer privacy from undocumented bit fields.
- `season` is outside the created Favorite Folder traversal and should not be merged into the MVP.

### Folder resources

- The resource endpoint returned HTTP 200 and API code 0 for an owned Folder.
- Observed `data` keys were `has_more`, `info`, `medias`, and `ttl`.
- `data.medias` was an array and `data.has_more` was a Boolean.
- Observed resource-row keys were:
  - `attr`
  - `bv_id`
  - `bvid`
  - `cnt_info`
  - `cover`
  - `ctime`
  - `duration`
  - `fav_time`
  - `id`
  - `intro`
  - `link`
  - `media_list_link`
  - `ogv`
  - `page`
  - `pubtime`
  - `season`
  - `title`
  - `type`
  - `ugc`
  - `upper`
- Observed `upper` keys were `face`, `jump_link`, `mid`, and `name`.
- The sampled fields needed by the MVP had stable primitive types: `bvid`/`title` strings; `duration`, `pubtime`, and `fav_time` numbers; `upper.name` a string in normal rows.
- The public contract should read only the minimal normalized fields and never return the raw object, cover URL, counts object, internal links, or uploader IDs.

### Page-size and continuation behavior

- `ps=20` returned 20 rows with API code 0 and `has_more: true` for a Folder with more data.
- `ps=50` returned API code `-400` and no rows. Therefore 20 is the verified upstream maximum and must be fixed in the MVP.
- Page 1 and page 2 each returned 20 rows in the controlled sample, with zero overlap by the in-memory resource identity pair.
- The sampled last page returned fewer than 20 rows and `has_more: false`.
- All sampled normal rows had valid BVID-shaped strings, but this is not a guarantee. Removed, unavailable, malformed, or non-Video rows must be filtered defensively and counted as skipped.
- One MCP call should own at most one resource request. Crossing Folder or page boundaries inside a single call would create variable request amplification.

### Traversal semantics

- The Folder endpoint supplies an ordered current list, while the resource endpoint supplies page-local order with `order=mtime`.
- A stateless cursor can identify the next `{ folder_id, page }`. On each call, the Folder list can be fetched again and the cursor Folder checked against current ownership.
- The cursor does not need credentials, account ID, Folder title, or Video data.
- Because Favorites can change between calls, this is a best-effort live traversal rather than snapshot isolation. If the cursor Folder disappears, the safe behavior is a stale-cursor validation error and restart.
- The same BVID may belong to several Folders. Returning it once per Folder context preserves Favorite Membership; global deduplication would erase user organization and require cross-call state.

## Applicability To This Project

Applies:

- A single current-account `list_bilibili_favorite_videos` MCP tool.
- Existing credential manager and shared unsigned authenticated GET transport.
- One navigation request, one Folder-list request, and zero or one resource request per tool call.
- Fixed page size 20, opaque continuation, strict normalization, and identical structured/text output.
- No persistence of private Favorites data.

Does not apply:

- Another user's public Favorites, Watch Later, subscriptions, followed collections, season data, or Favorites mutation.
- Batch transcript retrieval, media download, ASR, note generation, database sync, or knowledge retrieval.
- A single unbounded response or configurable upstream page size above 20.

## Decision Impact

Recommended project action:

- Add the bounded current-account Favorites Discovery contract from `docs/bilibili-favorites-discovery-prd.md`.
- Keep endpoint logic, cursor encoding/decoding, Folder normalization, and Video normalization in one dedicated Bilibili module.
- Reuse the existing handler/schema/error and credential surfaces without changing shared HTTP semantics.

Rules or files that may need updates:

- `CONTEXT.md`
- `src/bilibili/types.ts`
- `src/bilibili/favorites.ts`
- `src/server/tool-schemas.ts`
- `src/server/tool-handlers.ts`
- focused Vitest tests, bilingual tool docs, codemap, decisions, project facts, and QA records

## Risks And Unknowns

- These are undocumented consumer endpoints and may change without notice.
- The probe did not manufacture deleted, region-restricted, malformed, or mixed-media rows; defensive fixtures are still required.
- The probe did not mutate a Folder during traversal. Stale-cursor behavior must be specified and unit tested.
- Bilibili may reorder resources when favorites change; the MVP cannot provide snapshot isolation.
- Folder titles and Video lists are private interest-profile data even though they are intentionally returned to the local caller.

## Staleness Notes

Refresh this research when:

- either Favorites endpoint changes its response shape or codes
- Bilibili changes the resource page-size limit
- the project adds Folder filtering, sorting, snapshotting, caching, or mutation
- real acceptance reveals a field or row type not covered here
- this note is used after 2026-08-26

## Follow-Up

- [ ] Re-run the redacted real-account probe after implementation through the public MCP tool.
- [ ] Record only schema, counts, cursor progression, and pass/fail evidence in QA; never persist private content.
