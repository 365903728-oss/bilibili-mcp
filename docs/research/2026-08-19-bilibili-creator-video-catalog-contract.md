# Research Note: Bilibili Creator Video Catalog Contract

## Research Topic

- Topic: Creator overview and currently listable Video paging
- Date: 2026-08-19
- Owner: Codex
- Related task: GitHub Issues #44 and #46
- Refresh before: changing endpoints, fields, pagination, or authentication policy

## Question

Which current Bilibili-origin interfaces and failure boundaries can support the bounded `overview` and `videos` sections of `get_bilibili_creator_content` without per-row crawling?

## Context

Issue #46 requires authenticated, bounded Creator Video discovery. The implementation must reuse the existing WBI/HTTP module, preserve upstream order, and fail closed instead of presenting risk control as an empty catalog.

## Sources

| Source | Type | Date checked | Notes |
|---|---|---|---|
| `https://api.bilibili.com/x/space/wbi/arc/search` | live official API output | 2026-08-19 | Anonymous, correctly WBI-signed probe with `mid`, `pn=1`, `ps=1`, `order=pubdate`, `tid=0`, and empty keyword returned HTTP 412. No Cookie was read or sent. |
| `https://api.bilibili.com/x/space/wbi/acc/info` | live official API output | 2026-08-19 | Anonymous, correctly WBI-signed probe returned API code `-352` (risk-control failure). No Cookie was read or sent. |
| GitHub Issue #44 | accepted product specification and live-research record | 2026-08-19 | Records verified Creator Video paging, authenticated operation, conservative access semantics, and bounded no-crawl behavior. |
| GitHub Issue #46 | implementation ticket | 2026-08-19 | Defines the `overview` and `videos` acceptance criteria and maximum page size 20. |

## Findings

- The intended Creator space interfaces are WBI/risk-controlled; anonymous failure is current evidence that authentication/risk-control failures must remain explicit.
- This probe did not verify response field shapes because both endpoints failed before returning data. Tests must use bounded deterministic fixtures based on the accepted Issue #44/#46 contract, and normalization must reject malformed identity/list shapes.
- A valid `videos` call needs only the selected Creator, one page cursor, and one bounded upstream catalog page. It must not issue a detail request for each BVID.
- Metadata visibility does not prove playback entitlement. Without explicit upstream proof, access remains `unknown`.

## Applicability To This Project

Applies:

- Reuse `fetchWithWBI`, credential/login precheck, operation cancellation, retry, timeout, bounded JSON, validation, bounded text, and resource-limit errors.
- Treat HTTP 412, API `-352`, unexpected codes, and malformed payloads as failures, never empty success.

Does not apply:

- No anonymous fallback, webpage scraping, per-row detail request, transcript/comment/chapter fetch, or credential use in this implementation run.

## Decision Impact

- Keep one deep Creator Content module with a small `mid`/section/cursor interface.
- Use a versioned, canonical base64url cursor bound to Creator and section.
- Keep the live response-shape check as residual uncertainty until the user separately authorizes a credential-safe authenticated smoke.

## Risks And Unknowns

- Authenticated response field shapes and current listing of charge-exclusive Videos are not live-verified in this run.
- Bilibili may continue to return HTTP 412 or other risk-control codes even with configured credentials.

## Follow-Up

- [ ] Run a credential-safe authenticated smoke only after explicit credential-use authority.
