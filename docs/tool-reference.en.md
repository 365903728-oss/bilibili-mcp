# Bilibili MCP Tool Reference

[Back to English README](../README_EN.md) · [简体中文](./tool-reference.md) · [Client setup](./client-setup.en.md)

This page preserves detailed behavior, parameters, examples, error contracts, and runtime request controls for all twelve MCP tools. Start with the project README for installation and the first successful call.

## Quick selection

| Goal | Recommended tool | What you get |
|---|---|---|
| Start from a topic without a video link | `search_bilibili_videos` | Up to 10 normal Video candidates with reusable BVIDs; no automatic subtitle or comment retrieval |
| Start from a topic and want Creator candidates | `search_bilibili_creators` | Up to 10 Creator candidates with stable numeric `mid`; display names are fuzzy and never auto-selected |
| Read a chosen creator's overview, video catalog, Collections, Series, or Dynamics | `get_bilibili_creator_content` | One live overview or bounded content page (at most 20 rows); follow `next_cursor`; no image download or automatic Video evidence fetch |
| Start from my Bilibili Favorites | `list_bilibili_favorite_videos` | One bounded page of videos from the current account's created Favorite Folders (at most 20 rows); follow `next_cursor` until absent; no subtitles, comments, or downloads |
| Summarize a video | `get_video_info` | Subtitles first; falls back to title, description, tags |
| Get clean transcript text or locate keywords | `get_video_transcript` | Native subtitles first, explicit ASR fallback; supports timestamps, ranges, and keyword search |
| See structured metadata | `get_video_metadata` | Title, author, duration, publish date, tags, stats, multi-Part listing |
| View audience reactions | `get_video_comments` | Popular comments, timestamped highlights, optional replies |
| See video Chapters | `get_video_chapters` | Chapter titles, start/end seconds; empty list when absent |
| Guide users through Cookie setup | `get_credential_setup_instructions` | Safe setup steps, recommended commands, security notes |
| Check whether Cookies are configured/logged in | `check_bilibili_credentials` | configured, source, logged_in, next_steps, next_steps_zh |
| Check whether the MCP package needs an update | `check_mcp_update` | current_version, latest_version, update_available, notes_zh, update commands |

## Tool capabilities and behavior

### 1. Video Summarization (`get_video_info`)
- Prioritizes retrieving CC or AI subtitles.
- Automatically falls back to video title, description, and tags if no subtitles are available.
- Supports multi-language subtitle selection (defaults to Simplified Chinese).
- Supports explicit subtitle languages `zh-Hans`, `zh-CN`, `zh-Hant`, `en`, `ja`, `ko`, and `ai-zh`; `ai-zh` reaches selection unchanged, while unsupported values return `VALIDATION_ERROR`.
- When any of Bilibili's AI tracks (`ai-zh`, `ai-en`, etc.) is selected, `data_source` is `ai_subtitle` (not `subtitle`); `ai_subtitle` is Bilibili AI transcription, may be inaccurate, and is not equivalent to a human-checked citation.
- Every selected `ai-*` track passes an unconditional integrity assessment first; an unusable track returns the description result (`data_source: "description"`) without caching, never its body.
- Optional parameter `exclude_ai_subtitles`: filters out all Bilibili AI tracks (`ai-zh`, `ai-en`, etc.) so only human subtitles remain; AI-only results degrade to description (default `false`).

### 2. Comment Summarization (`get_video_comments`)
- Retrieves popular comments to help gauge video sentiment.
- Filters emoji placeholders (e.g., `[doge]`) for cleaner text.
- Prioritizes comments with timestamps (e.g., `05:20`) for quick highlight location.
- Supports two levels of detail:
  - `brief`: 10 popular comments summary.
  - `detailed`: 20 popular comments + high-quality replies.
- Optional parameters:
  - `limit`: Main-comment count, integer `1-50`; overrides the `detail_level` default. When replies are included, the flattened `comments[]` may contain more than `limit` items.
  - `sort`: Sort order `"hot"` (default) or `"time"`.
  - `include_replies`: Whether to include top replies (default `true`).

### 3. Video Transcript (`get_video_transcript`)
- Returns newline-joined native subtitles or explicitly requested local ASR transcription.
- Supports preferred language selection (defaults to `zh-Hans` > `ai-zh` > `zh-CN` > `zh-Hant` > `en` priority).
- Supports multi-Part selection, timestamp output, time-range filtering, and optional keyword search.
- Successful calls return both the backward-compatible formatted JSON text and the same data as MCP `structuredContent`.
- Optional parameters:
  - `preferred_lang`: Preferred subtitle language code: `zh-Hans`, `zh-CN`, `zh-Hant`, `en`, `ja`, `ko`, or `ai-zh`. `ai-zh` reaches selection unchanged; unsupported values return `VALIDATION_ERROR`.
  - `fallback_to_description`: Fall back to video description if subtitles unavailable (default `false`).
  - `fallback_to_asr`: Run ready local ASR only after subtitles are definitively unavailable (default `false`).
  - `exclude_ai_subtitles`: Filter out all Bilibili AI subtitles (`ai-zh`, `ai-en`, etc.) so only human subtitles remain; AI-only results are treated as definitive absence (default `false`).
  - `force_asr`: Bypass subtitle metadata and content selection and transcribe the resolved Part with the ready local ASR, even when valid human subtitles exist; does not require `fallback_to_asr` and wins over `exclude_ai_subtitles` (default `false`).
  - `page`: Multi-Part video page number (1-based positive integer).
  - `include_timestamps`: Prefix each line with `[HH:MM:SS --> HH:MM:SS]`.
  - `start_seconds` / `end_seconds`: Only return segments overlapping this range.
  - `query`: Keyword search term (max 100 chars, case-insensitive literal matching).
  - `max_matches`: Maximum matches to return (1-20, default 10).
  - `context_segments`: Context segments per match side (0-5, default 1).
- By default, returns `SUBTITLE_UNAVAILABLE` error when no subtitles exist.
- Precedence is fixed: native subtitles → explicit ASR → description only when both fallbacks are explicit and playback returns a valid empty audio set.
- When any `ai-*` track is selected, `data_source` is `ai_subtitle`. Every selected `ai-*` track is unconditionally read twice and passes a deterministic integrity assessment before its body is returned: cross-read stability (two reads with different normalized bodies are unusable; applies to every `ai-*` language) and language (ai-zh only: a body with at least 80 Unicode letters and under 10% Han letters is an `ai-zh` mismatch; other `ai-*` languages are not rejected for being non-Chinese). Stable same-language bodies that are semantically off-topic are an accepted limitation, controlled by `force_asr` / `exclude_ai_subtitles`. Human subtitles stay single-read and are never assessed.
- An unusable body is never returned: `fallback_to_asr: true` invokes the local ASR; otherwise the existing `fallback_to_description` contract applies, with `SUBTITLE_UNAVAILABLE` when no fallback is authorized; `get_video_info` returns the description result without caching it. A transport, timeout, auth, or parse failure on the second read remains visible and never becomes an integrity failure or ASR trigger.
- ASR starts only for a confirmed empty subtitle list, selected subtitle, or subtitle body, an `ai-*` track judged unusable by the integrity assessment (stability; language for ai-zh only. ASR only with explicit `fallback_to_asr`), or explicit `force_asr`. Cookie, HTTP, timeout, parse, anti-bot, and other API errors remain visible.
- ASR uses the ready setup-managed model on CPU INT8 and one temporary audio file. MCP calls never download or switch models.
- Bounds: one Part up to 7,200 seconds; 128 MiB audio; 3 candidate URLs with 3 redirects each; 120-second download; 30-minute transcription; 2 MiB stdout; 10,000 segments; one active job and no queue.
- Timestamps/range filtering/keyword search is incompatible with description fallback.
- Cookie expiration always returns `COOKIE_EXPIRED`, never silently falls back.
- Evidence links:
  - Root `source_url` on every successful result: browser URL of the selected Part (multi-Part videos append `p=<page>`).
  - `timestamp_url` on each search `matches[]` item: same as `source_url` plus `t=<start_seconds>`, opening the player at the matched subtitle.

### 4. Video Metadata (`get_video_metadata`)
- Returns video title, author, duration, publish date, description, tags, and stats (views, likes, coins, etc.).
- Returns multi-Part listing (`pages`) with page number, CID, title, and duration.
- Does not fetch subtitles or comments.

### 5. Video Chapters (`get_video_chapters`)
- Returns Bilibili creator-defined Chapter intervals (view_points) with title, start, and end seconds.
- Returns empty `chapters` array when no Chapters exist; never infers Chapters.
- Accepts optional `page` parameter for multi-Part videos.

### 6. Video Discovery (`search_bilibili_videos`)

- Returns normal Video candidates in Bilibili's comprehensive order; 5 by default and at most 10.
- Candidate metadata is for selection and follow-up calls only; the tool does not fetch subtitles/comments or apply AI re-ranking.
- Requires configured, logged-in Bilibili Cookies; success returns formatted JSON text plus identical MCP `structuredContent`.

### 7. Creator Search (`search_bilibili_creators`)

- Returns Creator candidates in Bilibili's platform order; 5 by default and at most 10.
- Each candidate carries the stable numeric `mid` (the only identity), display name, bio, avatar URL, follower count, video count, level, and a locally derived `source_url`. A candidate is accepted only when `mid` is a positive safe integer and the bounded name is non-empty; malformed profile facts normalize to empty strings or non-negative integer zero.
- Display names are fuzzy and non-unique: duplicate or near-duplicate names remain separate candidates in Bilibili's original order. The tool never selects one Creator and never crawls candidate content.
- Requires configured, logged-in Bilibili Cookies; success returns formatted JSON text plus identical MCP `structuredContent`.

### 8. Favorites Discovery (`list_bilibili_favorite_videos`)

- Automatically discovers every created Favorite Folder of the currently logged-in account and walks Folder-by-Folder, page-by-page.
- Each call returns at most one upstream resource page (fixed at 20 rows). `next_cursor` is an opaque, stateless, versioned base64url token that encodes only the next Folder ID and page number.
- The cursor is strictly validated before any network request: type, length (1-256), charset (base64url only), JSON structure, supported version, positive safe-integer Folder ID, and positive safe-integer page.
- Continuation rules: when the current Folder's `has_more=true`, the cursor points to the next page of the same Folder; when upstream returns an empty `medias` array (even if `has_more=true`) or when `has_more=false`, the cursor points to page 1 of the next Folder; the final Folder's terminal page omits `next_cursor`.
- The same BVID in two Folders is returned once in each Folder context (Favorite Membership semantics); the MCP does not deduplicate across Folders.
- `skipped_count` reports upstream rows that could not be safely normalized (for example, an invalid BVID or empty title); no replacement page is fetched.
- Upstream `media_count` is Bilibili's reported count and may exceed the rows currently visible or callable; the response only promises the current upstream page.
- Traversal is a best-effort read of Bilibili's live state, not a snapshot. Adding, removing, or moving memberships during continuation may change ordering or visible results.
- No persistence, cache, download, transcript/comment/chapter/search fetch, or anonymous fallback.
- Requires configured, logged-in Bilibili Cookies; success returns formatted JSON text plus identical MCP `structuredContent`.
- Optional parameters:
  - `cursor`: Opaque continuation token returned by the previous successful call. Omit on the first call.

### 9. Creator Content Discovery (`get_bilibili_creator_content`)

- Starts from one caller-selected, validated Creator `mid` and reads Bilibili space-page-visible content currently live; `section` is one of:
  - `overview`: returns one byte-bounded live profile reading (`name`, `bio`, `avatar_url`, `level`, `video_count`, and `live_state`; `follower_count` appears only when the upstream provides a valid `fans` fact — it is never fabricated as 0). `video_count` prefers the upstream `acc/info` value; only when the upstream profile does not provide it is one bounded `arc/search` count probe allowed (`pn=1, ps=1, order=pubdate`) — the tool never invents a count.
  - `videos`: returns one page of the currently listable video catalog (at most 20 BVID metadata rows); `next_cursor` is an opaque, stateless, versioned base64url token encoding only the mid and the next page number.
  - `collections` / `series`: without `container_id`, separately lists Collection or Series containers; with the container ID returned by that section, reads one bounded `members` page from only the selected container. The families remain distinct and never reuse multi-Part Video or Favorite Folder semantics.
  - `dynamics`: returns one Creator Dynamic page (at most 20 rows) with bounded text, image URL and available dimensions, referenced BVIDs, publication time, and an explicit original relationship for reposts. An ordinary feed entry remains a Dynamic when its browser URL uses `/opus/`; dedicated long-form article/Opus-body extraction is not provided.
- The cursor is strictly validated before any network request and binds the requested mid and section plus either a positive safe-integer page/optional container ID or the opaque upstream Dynamic offset; a mismatch or out-of-range value returns `VALIDATION_ERROR` with no request sent.
- `continuationProven` decides `next_cursor`: when `videos_total` exists and `page * 20 < videos_total`, the next page is returned; when the total is absent but the raw upstream row count is exactly 20, the next page is also returned, so one malformed row never truncates the traversal; emitting `page + 1` is guarded by a safe-integer check on `(page + 1) * 20`.
- `skipped_count` reports upstream rows that could not be safely normalized (for example, an invalid BVID or an empty title); no replacement page is fetched. Collaboration rows whose in-row mid differs from the selected Creator remain listable Creator Videos and are kept with their in-row author.
- Each row carries only metadata that feeds the existing evidence tools: `bvid`, title, description, cover, category, duration, publish time, author, play/danmaku/reply counts, and `source_url`; duration parses the upstream `length` (minutes may exceed 59) with the numeric `duration` as compatibility fallback and publish time prefers `created`; under `arc/search` semantics `comment` is the reply count and `video_review` is the danmaku count; `is_charge_video` is set to `true` only on explicit upstream truthy evidence (`is_pay`/`is_charging_arc`/`elec_arc_type` or the compatibility field `is_charge_video`); `access` is always `"unknown"` (the tool never probes accessibility).
- Collection/Series lists and member pages preserve Bilibili order, contain at most 20 rows, and report target-family rows that cannot be normalized through `skipped_count`. The same BVID in different containers remains a separate Membership; no global deduplication occurs. Results are live, non-snapshot state.
- Dynamics preserve upstream order and explicitly type original, repost, text, image, Video-share, and unknown entries as `text`, `image`, `video`, `repost`, or `unknown`. Each row contains `dynamic_id`, `upstream_type`, `published_at`, bounded `text`, at most 9 `images[]`, at most 20 `referenced_bvids[]`, and `source_url`; a repost also contains bounded `original`. A referenced BVID records only a relationship and never proves that the Dynamic author owns the Video.
- No persistence, cache, image download/proxy, OCR, image captioning, vision inference, subtitle/comment/chapter/search fetch, referenced-Video detail fetch, automatic traversal of other containers, or full-catalog crawl.
- Requires configured, logged-in Bilibili Cookies; success returns formatted JSON text plus identical MCP `structuredContent`.
- Parameters:
  - `mid` (required): the Creator's numeric `mid` (positive safe integer).
  - `section` (required): `"overview"`, `"videos"`, `"collections"`, `"series"`, or `"dynamics"`.
  - `container_id` (optional): only for `collections` or `series`; omit to list containers, provide it to read the selected container's members.
  - `cursor` (optional): opaque token returned by a previous successful call with the same mid, section, and container mode. `overview` does not accept a cursor.

### 10. Credential Helper Tools

- `get_credential_setup_instructions`: Returns safe setup commands for Bilibili Cookie configuration. AI agents installing this MCP can call this tool to guide users through setup.
- `check_bilibili_credentials`: Checks whether credentials are configured and logged in without returning Cookie values. Returns next steps when credentials are missing or invalid.
- `check_mcp_update`: Checks the local package version against npm latest and returns safe update guidance for `npx @latest` or global installs.

### 11. Behavior and Error Handling

- **Intelligent Cookie Expiration Detection**: Automatically verifies login status when subtitles are empty, distinguishing between "videos without subtitles" and "invalid credentials," and throwing a clear `COOKIE_EXPIRED` error to prevent silent degradation.

#### Without Cookie

- Some public video metadata (`get_video_metadata`) may work without authentication.
- Subtitles (`get_video_info`, `get_video_transcript`) may be unavailable, incomplete, or fail without authentication.
- Comments (`get_video_comments`) may be incomplete, empty, or rate-limited without authentication.
- Video discovery (`search_bilibili_videos`) requires configured, valid login credentials and never falls back to anonymous search.
- Creator search (`search_bilibili_creators`) likewise requires configured, valid login credentials and never falls back to anonymous search.
- Favorites discovery (`list_bilibili_favorite_videos`) must start from the currently logged-in account identity; it never falls back to anonymous access and never reads another user's public Favorites.
- Creator content discovery (`get_bilibili_creator_content`) requires configured, valid login credentials; it never falls back to anonymous access, `access` is always `"unknown"`, and it never probes whether a resource is accessible.
- Do not rely on cookie-less mode for reliable subtitle or comment access.

#### Credential Sources

- Credentials should be supplied via `.env` file, environment variables, or the credential helper.
- Supported environment variables: `BILIBILI_SESSDATA`, `BILIBILI_BILI_JCT`, `BILIBILI_DEDEUSERID`.
- **Never** hard-code Cookie values in source code, scripts, docs, tests, logs, or examples.
- If Cookie values were previously exposed in repository history, rotate them immediately via Bilibili account settings.

#### Expected Error Codes

All MCP tool error responses use a unified structured payload. The backward-compatible `error`, `message`, `code`, and `next_steps` fields remain, alongside explicit bilingual fields:

```json
{
  "error": true,
  "message": "Network request failed.",
  "message_en": "Network request failed.",
  "message_zh": "网络请求失败。",
  "code": "NETWORK_ERROR",
  "category": "network",
  "retryable": true,
  "user_action_required": false,
  "next_steps": ["Retry later.", "Check local network, proxy, firewall, or VPN settings if the problem repeats."],
  "next_steps_en": ["Retry later.", "Check local network, proxy, firewall, or VPN settings if the problem repeats."],
  "next_steps_zh": ["稍后重试。", "如果问题反复出现，请检查本机网络、代理、防火墙或 VPN 设置。"],
  "details": {
    "status_code": 503
  }
}
```

Field meaning:

- `error` / `message` / `code` / `next_steps`: backward-compatible fields; `next_steps` mirrors `next_steps_en`.
- `message_en` / `message_zh` / `next_steps_en` / `next_steps_zh`: explicit English and Chinese copies for clients that render by language.
- `category`: classification (`validation` / `credentials` / `content` / `network` / `access` / `rate_limit` / `api` / `runtime` / `unknown`).
- `retryable`: whether automatic retry is reasonable.
- `user_action_required`: whether the user must act before the call can succeed.
- `details`: optional metadata such as HTTP status, timeout in milliseconds, or Bilibili API code; never includes Cookie values or full URLs.

Supported error codes:

| Code | Meaning | Caller Action |
|------|---------|---------------|
| `VALIDATION_ERROR` | Invalid input parameter | Fix the `bvid_or_url` or other parameter |
| `COOKIE_EXPIRED` | Cookie expired or not logged in | User should refresh/rotate Bilibili credentials |
| `SUBTITLE_UNAVAILABLE` | No subtitles available for this video | For `get_video_transcript`, retry with `fallback_to_description: true` |
| `ASR_NOT_READY` | Local ASR is not ready | Run local `setup`, then confirm ready with `doctor --json` |
| `ASR_AUDIO_UNAVAILABLE` | Safe temporary audio is unavailable | Retry later; Bilibili playback URLs are temporary |
| `ASR_LIMIT_EXCEEDED` | Part, audio, or output exceeds a safety bound | Choose a shorter Part or use native subtitles |
| `ASR_BUSY` | One local ASR job is already active | Retry after it finishes; requests are not queued |
| `ASR_TRANSCRIPTION_TIMEOUT` | Local transcription exceeded 30 minutes | Retry later or choose a shorter Part |
| `ASR_TRANSCRIPTION_FAILED` | Managed Python/model execution failed | Check `doctor --json`, then retry |
| `ASR_OUTPUT_INVALID` | Managed ASR returned invalid or oversized NDJSON | Check local ASR state and report repeated failures |
| `NETWORK_ERROR` | Network request failed (HTTP 5xx, connection errors, etc.) | Retry later; check network/proxy/firewall if it keeps happening |
| `NETWORK_TIMEOUT` | Request to Bilibili timed out | Retry later; check network/proxy/firewall if it keeps happening |
| `API_RATE_LIMITED` | Bilibili API rate limit hit (HTTP 429) | Wait and retry; reduce request frequency or raise `BILIBILI_RATE_LIMIT_MS` |
| `ACCESS_DENIED` | Bilibili denied access to a resource (permissions, private, region/account restrictions, removed) | Verify the resource and account access permissions; run the credential check if needed |
| `PAID_VIDEO` | Video may require payment, membership, or extra permissions | Confirm in Bilibili; this MCP will not bypass paid or restricted access |
| `COMMENTS_DISABLED` | Comments are disabled or restricted | Use transcript or metadata tools; confirm on the Bilibili page |
| `BILIBILI_API_ERROR` | Other Bilibili API errors | Retry if it looks temporary; include the code when reporting repeated issues |
| `UNKNOWN_ERROR` | Unknown failure | Retry later; never include Cookie values when reporting |

## Call examples

> Your AI client will automatically turn your natural-language intent into the corresponding JSON call.

### `get_credential_setup_instructions`

**Best for**: letting an agent guide Cookie setup after installing the MCP server.

Request:

```json
{
  "name": "get_credential_setup_instructions",
  "arguments": {}
}
```

Returns: recommended setup commands, global-install commands, required Cookie fields, and bilingual `security_notes_en` / `security_notes_zh`; never returns Cookie values.

### `check_bilibili_credentials`

**Best for**: checking whether the current environment has Cookies configured and whether they are logged in.

Request:

```json
{
  "name": "check_bilibili_credentials",
  "arguments": {}
}
```

Returns: `configured`, `source` (`env` / `global_config` / `none`), `logged_in`, backward-compatible `next_steps`, and bilingual `next_steps_en` / `next_steps_zh`; never returns Cookie values.

### `check_mcp_update`

**Best for**: checking whether the installed MCP package is behind npm latest and showing safe update commands.

Request:

```json
{
  "name": "check_mcp_update",
  "arguments": {}
}
```

Returns: `current_version`, `latest_version`, `update_available`, `recommended_mcp_config`, `update_commands`, and bilingual `notes_en` / `notes_zh`; never updates packages automatically.

### `search_bilibili_videos`

**Best for**: starting with a topic and finding a small candidate set on Bilibili.

Request:

```json
{
  "name": "search_bilibili_videos",
  "arguments": {
    "query": "MCP tutorial",
    "limit": 5
  }
}
```

Returns: normal Video candidates in comprehensive order with `bvid`, title, author, duration, publish time, view count, bounded description, and source URL. Search requires valid logged-in credentials and never fetches candidate subtitles or comments automatically.

### `search_bilibili_creators`

**Best for**: letting an Agent start from a topic and get Bilibili UP 主 candidates with stable numeric `mid` values for later Creator-identity steps. Display names are fuzzy and non-unique; every candidate is a candidate, not a resolved identity. This tool never selects one Creator and never crawls candidate content.

Request:

```json
{
  "name": "search_bilibili_creators",
  "arguments": {
    "query": "MCP",
    "limit": 5
  }
}
```

Parameters:

- `query` (required): search keyword. Must be non-empty after trimming, at most 100 characters.
- `limit` (optional): candidate Creator count, integer 1-10, default 5.

Returns: `query` and `results[]` in Bilibili's original order. Each entry carries the stable numeric `mid` (positive safe integer, the only identity), `name`, `bio`, `avatar_url`, `follower_count`, `video_count`, `level`, and a locally derived `source_url`. A candidate is accepted only when `mid` is a positive safe integer and the bounded name is non-empty; malformed profile facts normalize to empty strings or non-negative integer zero. Duplicate or near-duplicate names remain separate candidates. Search requires valid logged-in credentials and never fetches candidate Videos, Dynamics, subtitles, comments, or other per-candidate details.

### `list_bilibili_favorite_videos`

**Best for**: letting an Agent start from your already-logged-in Bilibili account and read every created Favorite Folder. The MCP protocol stays paginated: each call returns at most one upstream page of 20 rows, and the Agent follows the returned `next_cursor` until it is absent. **Do not assume a single response contains the full account's Favorites.**

Request (first call, omit `cursor`):

```json
{
  "name": "list_bilibili_favorite_videos",
  "arguments": {}
}
```

Returns: `folders_total`, `folder` (current Folder `id`, `title`, `media_count`), `page`, `videos[]` (each with `bvid`, `title`, `author`, `duration_seconds`, `published_at`, `favorited_at`, `source_url`), `skipped_count`, and optional `next_cursor`. An account with no valid created Folders returns only `folders_total: 0`, `videos: []`, `skipped_count: 0`.

Continuation:

```json
{
  "name": "list_bilibili_favorite_videos",
  "arguments": {
    "cursor": "<next_cursor from the previous response>"
  }
}
```

> When upstream returns an empty `medias` page, even with `has_more=true`, the tool treats the current Folder as complete and jumps to page 1 of the next Folder, preventing a cursor loop. If the cursor's Folder no longer belongs to the current account (deleted or transferred), the call returns `VALIDATION_ERROR` and instructs the caller to restart without a cursor.

### `get_bilibili_creator_content`

**Best for**: after `search_bilibili_creators` (or any source) yields one selected Creator's stable numeric `mid`, reading that creator's profile, video catalog, Collections, Series, or Dynamics. Each call returns at most one upstream page (at most 20 rows); the Agent follows the returned `next_cursor` until it is absent. **Do not assume a single response contains the full catalog, and do not crawl every page automatically.**

Overview request:

```json
{
  "name": "get_bilibili_creator_content",
  "arguments": {
    "mid": 2088259175,
    "section": "overview"
  }
}
```

Returns: `mid`, `section: "overview"`, `name`, `bio`, `avatar_url`, `level`, `video_count`, and `live_state`; `follower_count` is optional and appears only when the upstream provides a valid `fans` fact — it is never fabricated as 0. `video_count` prefers the upstream `acc/info` value; only when the upstream profile lacks it is one bounded count probe allowed — the tool never invents a count.

Video catalog request (first call, omit `cursor`):

```json
{
  "name": "get_bilibili_creator_content",
  "arguments": {
    "mid": 2088259175,
    "section": "videos"
  }
}
```

Returns: `mid`, `section: "videos"`, `page`, `videos_total` (when bounded), `videos[]` (each with `bvid`, `title`, `description`, `cover_url`, category, `duration_seconds`, `published_at`, `author`, play/danmaku/reply counts, `access: "unknown"`, `source_url`), `skipped_count`, `live_state`, and optional `next_cursor`.

Continuation:

```json
{
  "name": "get_bilibili_creator_content",
  "arguments": {
    "mid": 2088259175,
    "section": "videos",
    "cursor": "<next_cursor from the previous response>"
  }
}
```

> The cursor accepts only a token returned by a previous `videos` call for the same `mid`; a cross-mid or cross-section cursor, a cursor on `overview`, an out-of-range page, or a malformed token returns `VALIDATION_ERROR` before any network request.

Collection list and member examples:

```json
{"name":"get_bilibili_creator_content","arguments":{"mid":2088259175,"section":"collections"}}
```

```json
{"name":"get_bilibili_creator_content","arguments":{"mid":2088259175,"section":"collections","container_id":1903592}}
```

Series uses the same pattern with `section: "series"` and a `series_id` returned by the Series list. Container lists return `collections[]` or `series[]`; member pages return `selected_collection` or `selected_series` plus `members[]`. Member cursors bind mid, section, and `container_id` and cannot be reused across containers.

Dynamic request:

```json
{"name":"get_bilibili_creator_content","arguments":{"mid":2088259175,"section":"dynamics"}}
```

Returns `dynamics[]`, `skipped_count`, `live_state: "live"`, and optional `next_cursor`. Rows contain only bounded text, image URL/dimensions, referenced BVIDs, and repost relationships; the MCP neither downloads/interprets images nor fetches referenced Video evidence. Continue by passing the previous `next_cursor` unchanged to `dynamics` for the same mid. The cursor binds Creator and section; upstream changes during traversal can affect order and visibility.

### `get_video_transcript`

**Best for**: feeding video content into AI for summarization, note-taking, Q&A, or knowledge management.

Request:

```json
{
  "name": "get_video_transcript",
  "arguments": {
    "bvid_or_url": "https://www.bilibili.com/video/BV1xx411c7mD",
    "preferred_lang": "en",
    "fallback_to_description": false,
    "fallback_to_asr": false
  }
}
```

Returns: `bvid`, `title`, `language`, `transcript` (newline-joined), `data_source` (`subtitle`, `ai_subtitle`, `asr`, or `description`), `page`.

> `preferred_lang` accepts only `zh-Hans`, `zh-CN`, `zh-Hant`, `en`, `ja`, `ko`, or `ai-zh`. Explicit `ai-zh` is not rewritten to another language; unsupported values return `VALIDATION_ERROR`. The tool returns `SUBTITLE_UNAVAILABLE` when no subtitles exist. Set `fallback_to_description: true` to fall back. `data_source: "ai_subtitle"` means Bilibili's AI track was selected — it is AI transcription, may be inaccurate, and is not equivalent to a human-checked citation.

**Explicit ASR fallback example**:

```json
{
  "name": "get_video_transcript",
  "arguments": {
    "bvid_or_url": "BV1xx411c7mD",
    "page": 1,
    "fallback_to_asr": true,
    "include_timestamps": true
  }
}
```

Native subtitles always win. Only a definitively subtitle-free Video with a model reported ready by `doctor --json` can return `data_source: "asr"`. ASR segments reuse the same ranges, keyword/context search, `source_url`, and `timestamp_url` pipeline. `force_asr: true` bypasses subtitle selection and always uses the local ASR (without requiring `fallback_to_asr`).

**Excluding AI subtitles example**:

```json
{
  "name": "get_video_transcript",
  "arguments": {
    "bvid_or_url": "BV1xx411c7mD",
    "exclude_ai_subtitles": true
  }
}
```

With `exclude_ai_subtitles: true`, selection considers human subtitles only; AI-only results are treated as definitive absence and may combine with `fallback_to_asr` or `fallback_to_description`.

**Keyword search example**:

```json
{
  "name": "get_video_transcript",
  "arguments": {
    "bvid_or_url": "BV1xx411c7mD",
    "query": "machine learning",
    "max_matches": 5,
    "context_segments": 1
  }
}
```

Search mode returns: `query`, `total_matches`, `returned_matches`, `truncated`, `matches` (with `start_seconds`, `end_seconds`, `content`, `context`), and compact `transcript`.

**Timed range example**:

```json
{
  "name": "get_video_transcript",
  "arguments": {
    "bvid_or_url": "BV1xx411c7mD",
    "page": 1,
    "include_timestamps": true,
    "start_seconds": 120,
    "end_seconds": 300
  }
}
```

### `get_video_metadata`

**Best for**: quickly checking video basics without subtitles or comments.

Request:

```json
{
  "name": "get_video_metadata",
  "arguments": {
    "bvid_or_url": "BV1xx411c7mD"
  }
}
```

Returns: `bvid`, `title`, `author`, `duration`, `pubdate` / `pubdate_timestamp`, `description`, `tags`, `pages` (multi-Part listing), and `stats` (views, likes, coins, favorites, shares, replies, danmaku).

### `get_video_chapters`

**Best for**: getting Bilibili creator-defined Chapter intervals for navigation.

Request:

```json
{
  "name": "get_video_chapters",
  "arguments": {
    "bvid_or_url": "BV1vL411G7N7"
  }
}
```

Returns: `bvid`, `page`, `cid`, `title`, `chapters` (array with `title`, `start_seconds`, `end_seconds`). Empty array when no Chapters exist.

### `get_video_info`

**Best for**: letting AI summarize a video -- attempts subtitles first, falls back to description and tags.

Request:

```json
{
  "name": "get_video_info",
  "arguments": {
    "bvid_or_url": "https://www.bilibili.com/video/BV1xx411c7mD",
    "preferred_lang": "en"
  }
}
```

Returns: `data_source` (`subtitle`, `ai_subtitle`, or `description`), `video_info` (title, description, tags, subtitle text, publish date).

> `preferred_lang` accepts only `zh-Hans`, `zh-CN`, `zh-Hant`, `en`, `ja`, `ko`, or `ai-zh`. Explicit `ai-zh` is not rewritten to another language; unsupported values return `VALIDATION_ERROR`. Videos without subtitles automatically degrade to description and tags (`data_source: "description"`). `data_source: "ai_subtitle"` means Bilibili's AI track was selected — it is AI transcription, may be inaccurate, and is not equivalent to a human-checked citation. Pass `exclude_ai_subtitles: true` when only human subtitles are acceptable.

### `get_video_comments`

**Best for**: gauging audience sentiment and finding highlight timestamps.

Request:

```json
{
  "name": "get_video_comments",
  "arguments": {
    "bvid_or_url": "BV1xx411c7mD",
    "detail_level": "detailed",
    "limit": 10,
    "sort": "hot",
    "include_replies": true
  }
}
```

Returns: `comments[]` (author, content, likes, timestamp, has_timestamp), `summary` (total count, timestamp count).

> `limit` applies only to main comments. With `include_replies: true` and `detail_level: "detailed"`, the flattened `comments[]` also contains child replies and may therefore exceed `limit`. Expired or missing cookies may result in empty comments. Use `sort: "time"` for newest comments, `include_replies: false` to skip replies.

---

## Request controls and cache

Built-in request controls reduce the chance of triggering Bilibili risk checks or API rate limits:

- **Request start interval**: defaults to 500ms (0.5s), configurable with `BILIBILI_RATE_LIMIT_MS`.
- **Execution model**: throttles API request starts to avoid burst concurrency; intended for local single-user MCP usage.
- **Retry strategy**: retries 408, 429, 5xx, network errors, and timeouts up to 3 times with exponential backoff.
- **Timeout**: defaults to 10 seconds, configurable with `BILIBILI_REQUEST_TIMEOUT_MS`.
- **Cache capacity**: defaults to 100 entries, configurable with `BILIBILI_CACHE_SIZE`.
- **User-Agent**: overridable via `USER_AGENT`.

All three numeric variables must be complete decimal positive safe integers. Empty, partial, zero, negative, or unsafe-integer values raise a configuration error and prevent startup. The two millisecond variables must also not exceed the Node.js timer limit of `2147483647`; cache capacity has no additional arbitrary cap.

All of the above environment variables are read at MCP server process startup. After changing them, restart the MCP client or reconnect the MCP server for the new values to take effect.

---
