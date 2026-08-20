# Bilibili Creator Dynamics Contract

## Research Topic

- Topic: Current Bilibili Creator Dynamic feed contract
- Date: 2026-08-20
- Owner: Codex
- Related task, PRD, ticket, or plan: GitHub Issue #48 and parent spec #44
- Refresh before: changing the Dynamic response contract or endpoint

## Question

Which current first-party Bilibili endpoint can provide one bounded Creator Dynamic page while preserving text, image metadata, referenced BVIDs, and repost relationships?

## Context

This matters because Issue #48 adds a `dynamics` section to `get_bilibili_creator_content`. The implementation must stay read-only, use one upstream page per call, and must not invent evidence that the upstream response does not expose.

## Sources

| Source | Type | Date checked | Notes |
|--------|------|--------------|-------|
| `https://space.bilibili.com/2/dynamic` and its first-party `fresh-space` assets | official page/source | 2026-08-20 | Current space client routes Dynamic pagination through `/x/polymer/web-dynamic/v1/opus/feed/space`. |
| Anonymous response from `/x/polymer/web-dynamic/v1/opus/feed/space` | live API output | 2026-08-20 | HTTP 200/API code 0; exposes `items`, `offset`, and `has_more`, but its flattened rows expose only a single cover and no explicit original/repost structure or complete referenced-BVID evidence. |
| Anonymous response from `/x/polymer/web-dynamic/v1/feed/space` | live API output | 2026-08-20 | HTTP 200/API code `-352`; authenticated response shape was not probed because no user credential use was authorized. |

## Findings

- The current page UI has moved to the flattened `opus/feed/space` family.
- That flattened response is insufficient for Issue #48's explicit original/repost relationship, all image metadata, and referenced-BVID requirements.
- The detailed `feed/space` wire shape remains the only known single-page contract that can satisfy those requirements without per-item requests, but anonymous access currently triggers Bilibili risk control.

## Applicability To This Project

Applies:

- Keep the authenticated detailed endpoint for the bounded Dynamic page.
- Treat its response as untrusted: validate the page envelope, cap rows/images/rich-text nodes, and skip malformed rows without converting endpoint failures into empty success.
- Keep `offset` opaque and bind it to the selected Creator in the local cursor.

Does not apply:

- No anonymous fallback, webpage scraping, OCR, image download, or automatic transcript/comment/metadata crawl.
- A referenced BVID is only a relationship visible in the Dynamic; it is not proof that the Creator owns that Video.

## Decision Impact

Add the `dynamics` section using one authenticated `/x/polymer/web-dynamic/v1/feed/space` request per call. Return bounded text, image URL/dimensions, referenced BVIDs, and an explicit nested original for reposts. Preserve unknown upstream Dynamic kinds as `type: "unknown"` instead of guessing.

## Risks And Unknowns

- Authenticated live behavior and current detailed response shape remain unverified.
- Bilibili may retire or alter the detailed endpoint as its space UI continues to use the flattened Opus endpoint.
- HTTP/API risk-control behavior can change independently of this repository.

## Staleness Notes

Refresh this research when the Creator Dynamic endpoint changes, live smoke starts failing, or the public Dynamic output contract is expanded.

## Follow-Up

- [ ] Run one credential-safe authenticated live smoke only with explicit credential-use authority; record shapes/statuses, never Cookie values or private content.
