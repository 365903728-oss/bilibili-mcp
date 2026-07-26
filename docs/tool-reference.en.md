# Bilibili MCP Tool Reference

[Back to English README](../README_EN.md) · [简体中文](./tool-reference.md) · [Client setup](./client-setup.en.md)

This page preserves detailed behavior, parameters, examples, error contracts, and runtime request controls for all nine MCP tools. Start with the project README for installation and the first successful call.

## Quick selection

| Goal | Recommended tool | What you get |
|---|---|---|
| Start from a topic without a video link | `search_bilibili_videos` | Up to 10 normal Video candidates with reusable BVIDs; no automatic subtitle or comment retrieval |
| Summarize a video | `get_video_info` | Subtitles first; falls back to title, description, tags |
| Get clean transcript text or locate keywords | `get_video_transcript` | Plain subtitle text, language, data source; supports timestamps, range filtering, and keyword search |
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
- Supports manual preference for subtitle languages (e.g., `en`, `zh-Hant`).

### 2. Comment Summarization (`get_video_comments`)
- Retrieves popular comments to help gauge video sentiment.
- Filters emoji placeholders (e.g., `[doge]`) for cleaner text.
- Prioritizes comments with timestamps (e.g., `05:20`) for quick highlight location.
- Supports two levels of detail:
  - `brief`: 10 popular comments summary.
  - `detailed`: 20 popular comments + high-quality replies.
- Optional parameters:
  - `limit`: Explicit comment count `1-50`, overrides `detail_level` default.
  - `sort`: Sort order `"hot"` (default) or `"time"`.
  - `include_replies`: Whether to include top replies (default `true`).

### 3. Video Transcript (`get_video_transcript`)
- Returns clean subtitle text, joined by newlines.
- Supports preferred language selection (defaults to `zh-Hans` > `ai-zh` > `zh-CN` > `zh-Hant` > `en` priority).
- Supports multi-Part selection, timestamp output, time-range filtering, and optional keyword search.
- Successful calls return both the backward-compatible formatted JSON text and the same data as MCP `structuredContent`.
- Optional parameters:
  - `preferred_lang`: Preferred subtitle language code.
  - `fallback_to_description`: Fall back to video description if subtitles unavailable (default `false`).
  - `page`: Multi-Part video page number (1-based positive integer).
  - `include_timestamps`: Prefix each line with `[HH:MM:SS --> HH:MM:SS]`.
  - `start_seconds` / `end_seconds`: Only return segments overlapping this range.
  - `query`: Keyword search term (max 100 chars, case-insensitive literal matching).
  - `max_matches`: Maximum matches to return (1-20, default 10).
  - `context_segments`: Context segments per match side (0-5, default 1).
- By default, returns `SUBTITLE_UNAVAILABLE` error when no subtitles exist.
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

### 7. Credential Helper Tools

- `get_credential_setup_instructions`: Returns safe setup commands for Bilibili Cookie configuration. AI agents installing this MCP can call this tool to guide users through setup.
- `check_bilibili_credentials`: Checks whether credentials are configured and logged in without returning Cookie values. Returns next steps when credentials are missing or invalid.
- `check_mcp_update`: Checks the local package version against npm latest and returns safe update guidance for `npx @latest` or global installs.

### 8. Behavior and Error Handling

- **Intelligent Cookie Expiration Detection**: Automatically verifies login status when subtitles are empty, distinguishing between "videos without subtitles" and "invalid credentials," and throwing a clear `COOKIE_EXPIRED` error to prevent silent degradation.

#### Without Cookie

- Some public video metadata (`get_video_metadata`) may work without authentication.
- Subtitles (`get_video_info`, `get_video_transcript`) may be unavailable, incomplete, or fail without authentication.
- Comments (`get_video_comments`) may be incomplete, empty, or rate-limited without authentication.
- Video discovery (`search_bilibili_videos`) requires configured, valid login credentials and never falls back to anonymous search.
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
- `category`: classification (`validation` / `credentials` / `content` / `network` / `access` / `rate_limit` / `api` / `unknown`).
- `retryable`: whether automatic retry is reasonable.
- `user_action_required`: whether the user must act before the call can succeed.
- `details`: optional metadata such as HTTP status, timeout in milliseconds, or Bilibili API code; never includes Cookie values or full URLs.

Supported error codes:

| Code | Meaning | Caller Action |
|------|---------|---------------|
| `VALIDATION_ERROR` | Invalid input parameter | Fix the `bvid_or_url` or other parameter |
| `COOKIE_EXPIRED` | Cookie expired or not logged in | User should refresh/rotate Bilibili credentials |
| `SUBTITLE_UNAVAILABLE` | No subtitles available for this video | For `get_video_transcript`, retry with `fallback_to_description: true` |
| `NETWORK_ERROR` | Network request failed (HTTP 5xx, connection errors, etc.) | Retry later; check network/proxy/firewall if it keeps happening |
| `NETWORK_TIMEOUT` | Request to Bilibili timed out | Retry later; check network/proxy/firewall if it keeps happening |
| `API_RATE_LIMITED` | Bilibili API rate limit hit (HTTP 429) | Wait and retry; reduce request frequency or raise `BILIBILI_RATE_LIMIT_MS` |
| `ACCESS_DENIED` | Bilibili denied access (permissions, private, region-locked, removed) | Verify the video access permissions; run the credential check if needed |
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

### `get_video_transcript`

**Best for**: feeding video content into AI for summarization, note-taking, Q&A, or knowledge management.

Request:

```json
{
  "name": "get_video_transcript",
  "arguments": {
    "bvid_or_url": "https://www.bilibili.com/video/BV1xx411c7mD",
    "preferred_lang": "en",
    "fallback_to_description": false
  }
}
```

Returns: `bvid`, `title`, `language`, `transcript` (newline-joined), `data_source` (`subtitle` or `description`), `page`.

> Returns `SUBTITLE_UNAVAILABLE` when no subtitles exist. Set `fallback_to_description: true` to fall back.

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

Returns: `data_source` (`subtitle` or `description`), `video_info` (title, description, tags, subtitle text, publish date).

> Videos without subtitles automatically degrade to description and tags (`data_source: "description"`).

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

> Expired or missing cookies may result in empty comments. Use `sort: "time"` for newest comments, `include_replies: false` to skip replies.

---

## Request controls and cache

Built-in request controls reduce the chance of triggering Bilibili risk checks or API rate limits:

- **Request start interval**: defaults to 500ms (0.5s), configurable with `BILIBILI_RATE_LIMIT_MS`.
- **Execution model**: throttles API request starts to avoid burst concurrency; intended for local single-user MCP usage.
- **Retry strategy**: retries 408, 429, 5xx, network errors, and timeouts up to 3 times with exponential backoff.
- **Timeout**: defaults to 10 seconds, configurable with `BILIBILI_REQUEST_TIMEOUT_MS`.
- **Cache capacity**: defaults to 100 entries, configurable with `BILIBILI_CACHE_SIZE`.
- **User-Agent**: overridable via `USER_AGENT`.

All of the above environment variables are read at MCP server process startup. After changing them, restart the MCP client or reconnect the MCP server for the new values to take effect.

---
