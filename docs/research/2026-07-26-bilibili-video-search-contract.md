# Research Note: Bilibili Video Search Contract

## Research Topic

- Topic: First-party contract for a bounded `search_bilibili_videos` MCP tool
- Date: 2026-07-26
- Owner: Codex
- Related task: User-approved Bilibili-only video discovery feature
- Probe window: 2026-07-26 08:13-08:17 UTC / 16:13-16:17 UTC+8
- Refresh before: implementation if this note is older than 30 days, or immediately after a search API behavior change

## Question

Which current Bilibili first-party endpoint can support a read-only, credential-gated video search with a required keyword, default 5 results, maximum 10 results, comprehensive ranking, no pagination, and no automatic transcript or comment requests?

## Sources

| Source | Type | Date checked | Notes |
|---|---|---|---|
| [Bilibili search page](https://search.bilibili.com/all?keyword=MCP) | Official webpage | 2026-07-26 | Loads the current first-party search application bundle. |
| [Current Bilibili search application bundle](https://s1.hdslb.com/bfs/static/shanks/laputa-search/assets/index-2ae4a1c0.js) | Official frontend source | 2026-07-26 | Constructs the browser path `/x/web-interface/wbi/search/type`, uses `search_type: "video"`, `page_size`, and comprehensive order `totalrank`; includes WBI signing middleware. The hashed asset URL is expected to change on deployment. |
| [`/x/web-interface/wbi/search/type`](https://api.bilibili.com/x/web-interface/wbi/search/type?search_type=video&keyword=MCP&page=1&page_size=5) | Official API, live probe | 2026-07-26 | Successful current endpoint. Probes covered anonymous/authenticated requests, signed/unsigned requests, limits, sorting, invalid input, field types, mixed result types, and low-match queries. |
| [`/x/web-interface/nav`](https://api.bilibili.com/x/web-interface/nav) | Official API, live probe | 2026-07-26 | Used only to verify logged-in state without recording credentials or account data. |
| [Legacy `/x/web-interface/search/type`](https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=MCP&page=1&page_size=5) | Official API, negative live probe | 2026-07-26 | Returned HTTP 412 with API code `-412`; it is not a viable fallback. |
| [`src/bilibili/http.ts`](../../src/bilibili/http.ts), [`src/utils/credentials.ts`](../../src/utils/credentials.ts), [`src/utils/validation.ts`](../../src/utils/validation.ts) | Current repository source | 2026-07-26 | Existing rate limiting, retry, authentication-header loading, login check, and bounded string validation. |

No third-party tutorial, unofficial API catalog, or competing implementation was used as contract evidence.

## Safe Probe Shape

The successful request sequence was:

1. Confirm that a credential source is configured locally without printing its contents.
2. `GET https://api.bilibili.com/x/web-interface/nav` with the in-memory authentication header; inspect only HTTP status, API code, and `data.isLogin`.
3. If logged in, request:

   ```text
   GET https://api.bilibili.com/x/web-interface/wbi/search/type
     ?search_type=video
     &keyword=<URL-encoded keyword>
     &page=1
     &page_size=<bounded integer>
   ```

4. Send the repository's existing general `User-Agent`, `Referer`, and JSON `Accept` headers plus the in-memory authentication header. Never log request headers.

A redacted response shape observed during the probe was:

```json
{
  "code": 0,
  "message": "OK",
  "data": {
    "page": 1,
    "pagesize": 5,
    "numResults": 1000,
    "numPages": 200,
    "result": [
      {
        "type": "video",
        "bvid": "BV...",
        "title": "...<em class=\"keyword\">MCP</em>...",
        "author": "...",
        "duration": "27:6",
        "pubdate": 1700000000,
        "play": 12345,
        "video_review": 123,
        "description": "..."
      }
    ]
  }
}
```

The numeric values and content above are illustrative redactions, not stable fixtures.

## Findings

### Endpoint, parameters, and ranking

- The current browser endpoint is `GET /x/web-interface/wbi/search/type`.
- `search_type=video` and a non-empty `keyword` are the minimum required parameters. Omitting either, or sending an empty keyword, returned HTTP 200 with API code `-400` and `请求错误`.
- Omitting `page` and `page_size` produced page 1 with 20 results. `page_size=5` and `page_size=10` were honored; `pagesize` and `ps` were ignored.
- Omitting `order` and sending `order=totalrank` produced the same leading BVID order in the controlled probe. The official frontend also labels `totalrank` as comprehensive ranking. The MVP can omit `order`.
- `page` must remain fixed at 1. The approved MVP has no pagination or cursor.

### WBI status

- The official browser bundle uses the `/wbi/` path and contains WBI signing logic with `wts` and `w_rid`.
- On 2026-07-26, the endpoint also accepted a completely unsigned request. A request with an invalid signature still returned API code 0, and the repository's existing signed request path succeeded.
- Therefore WBI signing is **not currently enforced by this endpoint**, but this is an observation rather than a published guarantee.
- MVP recommendation: after the mandatory login precheck, use the existing `fetchWithoutWBI` transport against the `/wbi/search/type` path. This avoids a second navigation request solely to obtain signing material. Keep the endpoint call isolated so it can switch to the existing signed transport if unsigned requests begin failing.

### Credential and login behavior

- The search endpoint itself succeeded anonymously. Authentication is not an upstream requirement observed in this probe.
- The approved product contract nevertheless requires a configured, valid login and forbids anonymous fallback. Without a separate precheck, a missing or expired credential would silently change the request to anonymous behavior.
- An unauthenticated navigation probe returned HTTP 200, API code `-101`, and a false login state. The safely loaded local credential produced HTTP 200, API code 0, and a true login state.
- Required sequence:
  1. Stop locally with existing credential setup guidance when no credential source exists.
  2. Call the existing login-status path before search.
  3. Stop with the existing expired/invalid credential guidance unless the result is explicitly logged in.
  4. Only then send the search request with in-memory authentication headers.
- The MCP must not claim personalized ranking. Logged-in and anonymous result order differed under otherwise equal parameters, but this probe cannot distinguish personalization from experiments, advertising, or other server-side variation.

### Result types and normalization

- `search_type=video` does not guarantee that every row is a normal video. Live samples included `type="ketang"` rows with an empty BVID.
- Only accept rows where `type === "video"` and `bvid` passes the repository's existing BVID validation. Do not fetch a second page to replace filtered rows.
- Observed normal-video field types:

  | Field | Observed type | Contract treatment |
  |---|---|---|
  | `bvid` | string | Validate and return. |
  | `title` | string | Remove only Bilibili's exact search-highlight tags. |
  | `author` | string | Return as uploader display name. |
  | `duration` | string | Parse defensively; values are not consistently zero-padded and minutes can exceed 59. |
  | `pubdate` | number | Unix seconds. |
  | `play` | number | Return as the single bounded statistic. |
  | `description` | string | Treat as untrusted text and truncate for the public response. |
  | `arcurl` | string | Do not expose; observed values used HTTP and AV identifiers. |

- Titles commonly contain exact markup such as `<em class="keyword">...</em>`. The official frontend removes these tags before display. The MVP should do the same without adding an HTML parsing dependency.
- Description samples did not contain markup, but descriptions remain untrusted user-generated text.
- Construct `https://www.bilibili.com/video/<BVID>` locally rather than returning `arcurl`.
- Do not expose upstream `numResults` or `numPages` as an exact total. Low-match/random queries still reported `numResults=1000`.

### Empty results and relevance

- A true empty first-page result could not be reproduced reliably. Long random strings, rare characters, and symbols still returned API code 0 with recommendation-like video rows.
- Consequently, `results: []` can only mean that the upstream array was empty or that no row survived strict type/BVID validation. It must not mean “Bilibili found no semantically relevant video.”
- Do not add a title-keyword relevance heuristic, AI reranker, or additional upstream request in the MVP. Agents can choose among the bounded candidates.

### Errors and risk controls

- Missing/empty required parameters: HTTP 200, API code `-400`.
- Invalid `search_type`: HTTP 200, API code `-1200`.
- Legacy non-WBI endpoint: HTTP 412, API code `-412`, `request was banned`, in both anonymous and authenticated probes.
- No intentional load test was performed. HTTP 412, 429, transport failures, timeouts, and non-zero API codes must remain errors and must not be converted into an empty successful result.
- Do not add webpage scraping as a fallback. It would duplicate the first-party client, increase anti-bot exposure, and create an unrelated HTML parsing path.

## Recommended MVP Contract

Input:

```json
{
  "keyword": "required trimmed string, 1-100 characters",
  "limit": "optional integer, default 5, range 1-10"
}
```

Output:

```json
{
  "query": "trimmed original keyword",
  "results": [
    {
      "bvid": "BV...",
      "title": "highlight tags removed",
      "author": "uploader display name",
      "duration": "normalized human-readable duration",
      "pubdate_timestamp": 1700000000,
      "play_count": 12345,
      "description": "bounded plain-text snippet",
      "video_url": "https://www.bilibili.com/video/BV..."
    }
  ]
}
```

Contract rules:

- `results.length <= limit`; returning fewer results after strict filtering is valid.
- Request one bounded first page, filter, then slice. Do not paginate to fill the requested count.
- Return the same object as MCP `structuredContent` and as the existing formatted JSON text representation.
- A valid empty result is a successful `{ "query": "...", "results": [] }`.
- Search never invokes transcript, comments, metadata, chapters, or AI ranking. The client chooses a returned BVID for subsequent existing tools.
- Errors retain the repository's current structured error and setup guidance; error results have no `structuredContent`.

## Decision Impact

The first implementation should be one Bilibili-only tool, `search_bilibili_videos`, using the existing credential manager, login-status check, HTTP rate limiting/retry behavior, JSON text formatter, BVID validation, and dual structured/text response pattern.

No new dependency, browser fallback, pagination abstraction, ranking model, total-count field, creator search, collection search, transcript prefetch, or comment prefetch is justified.

## Risks And Unknowns

- The endpoint is first-party but not a published stable developer API.
- Unsigned acceptance, result fields, injected row types, ranking, and low-match fallback can change without notice.
- A logged-in request can differ from an anonymous request even when the MCP itself performs no personalization.
- The probe did not force rate limiting or deliberately invalidate a real credential.
- A genuine empty first-page result was not observed.

## Staleness Notes

Refresh this note when any of the following occurs:

- Bilibili deploys a new search bundle and the endpoint/request construction changes.
- Unsigned `/wbi/search/type` requests return a signature or access error.
- `search_type=video` stops returning the documented field set or introduces new non-video row types.
- Login precheck or authenticated search begins returning different API codes.
- A release changes the repository's shared HTTP, WBI, credential, validation, or error mapping.
- Real-client verification shows low relevance, excessive filtered rows, or response-size pressure at limit 10.

## Follow-Up

- [x] Freeze the exact public schema and 200-code-point description limit in `docs/bilibili-video-search-prd.md` and GitHub Issue #21.
- [x] Implement the minimum isolated search API adapter and MCP handler.
- [x] Verify `tools/list`, a successful authenticated search, credential failure, validation errors, strict row filtering, dual output, and the full search-to-timestamp-evidence flow.
