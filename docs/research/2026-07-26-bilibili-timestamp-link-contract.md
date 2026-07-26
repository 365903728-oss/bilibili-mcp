# Research Note: Bilibili Timestamp Link Contract

## Research Topic

- Topic: Bilibili ordinary-video and multi-Part timestamp links
- Date: 2026-07-26
- Owner: Codex
- Related task, PRD, ticket, or plan: `docs/transcript-evidence-links-prd.md`
- Refresh before: changing the URL contract, adding mobile/app deep links, or using this result after 2026-10-26

## Question

Which canonical web URLs reliably identify a selected Bilibili Part and open its player at a subtitle match time?

## Context

`get_video_transcript` already returns BVID, resolved Part, subtitle match start/end seconds, and structured output. It lacks a direct browser link back to the selected source and match.

The implementation must derive links locally without another Bilibili request, preserve exact BVID casing, and work for both ordinary and multi-Part Videos.

## Sources

| Source | Type | Date checked | Notes |
|---|---|---|---|
| `https://www.bilibili.com/video/BV1vL411G7N7/?t=42` | live first-party page | 2026-07-26 | URL remained unchanged; the 670-second player loaded at approximately 42.54 seconds. |
| `https://www.bilibili.com/video/BV1vL411G7N7/?t=42.5` | live first-party page | 2026-07-26 | Decimal `t` remained in the URL and the player started at or after 42.5 seconds. |
| `https://www.bilibili.com/video/BV153411j7Ys/?p=2&t=17` | live first-party multi-Part page | 2026-07-26 | Loaded Part 2, title `刚刚添加的p2`, CID `516952952`, and playback at or after 17 seconds. |
| `get_video_metadata` for `BV153411j7Ys` | live local MCP call over Bilibili view API | 2026-07-26 | Confirmed three Parts and that CID `516952952` is Part 2. |
| `https://www.bilibili.com/video/BV1VL411G7N7` | live first-party counterexample | 2026-07-26 | Uppercasing `BV1vL411G7N7` opened a different Video, proving BVID casing must be preserved. |

Playwright performed the browser checks in a fresh page without changing global MCP or browser configuration. Firecrawl and generic URL fetch attempts were blocked by the target and were not used as evidence.

## Findings

- `t=<seconds>` is accepted on an ordinary Video and may preserve decimal seconds.
- A multi-Part link needs `p=<one-based Part>`; combining `p` and `t` selects the Part before applying playback time.
- The canonical ordinary source URL can omit `p`; the canonical multi-Part source URL should include the resolved `p` even for explicit Part identity.
- A match link should reuse its Part source URL and add `t=<start_seconds>`.
- BVID characters are case-sensitive. The existing `normalizeBVId`/`createVideoUrl` uppercase behavior is unsafe for these evidence links and must not be used.
- Arbitrary tracking parameters from the caller's input URL are not part of the evidence contract.

## Applicability To This Project

Applies:

- `VideoTranscriptData.source_url` for every successful subtitle or description result.
- `TranscriptMatch.timestamp_url` for every returned search match.
- Locally constructed `https://www.bilibili.com/video/<exact-bvid>/` URLs.

Does not apply:

- Mobile-app URI schemes, short links, download URLs, subtitle resource URLs, Chapters, comments, or the other seven MCP tools.

## Decision Impact

Recommended project action:

- Add a single private transcript URL builder using the standard `URL` API.
- For a Video with one Part, return `https://www.bilibili.com/video/<bvid>/`.
- For a Video with multiple Parts, add `p=<resolved page>`.
- For each `Transcript Match`, add `t=<start_seconds>` to that Part URL.

Rules or files that may need updates:

- `CONTEXT.md`
- `src/bilibili/types.ts`
- `src/bilibili/subtitle.ts`
- `src/server/tool-schemas.ts`
- transcript/schema/handler tests
- README and README_EN

## Risks And Unknowns

- Bilibili may change web query-parameter behavior.
- Native mobile clients were not tested; these fields intentionally promise browser URLs only.
- Playback advances while the page loads, so observed current time is expected to be slightly greater than `t`.

## Staleness Notes

Refresh this research when:

- Bilibili changes Video URLs or player query parameters
- mobile/app deep links enter scope
- BVID parsing or Part resolution changes
- live client acceptance no longer reaches the requested Part/time

## Follow-Up

- [x] Implemented and verified transcript evidence links without new upstream requests; see `docs/qa/2026-07-26-transcript-evidence-links.md`.
