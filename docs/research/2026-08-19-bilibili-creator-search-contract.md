# Bilibili Creator Search Contract

## Research Topic

- Topic: Current Bilibili Creator search identity and response boundary
- Date: 2026-08-19
- Owner: Codex
- Related task, PRD, ticket, or plan: GitHub Issues #44 and #45
- Refresh before: implementation live smoke or after material Bilibili search changes

## Question

Can the current Bilibili search surface return bounded Creator candidates with stable identity without treating a display name as resolved identity or crawling candidate content?

## Context

Why this matters for `@xzxzzx/bilibili-mcp`:

- Existing evidence tools need a BVID, and the next Creator workflow needs a stable `mid` before Video or Dynamic traversal.

What decision or implementation this may affect:

- The `search_bilibili_creators` input, candidate output, authentication, bounds, and failure semantics.

## Sources

| Source | Type | Date checked | Notes |
|--------|------|--------------|-------|
| `https://api.bilibili.com/x/web-interface/wbi/search/type` | live official API output | 2026-08-19 | `search_type=bili_user`, `keyword`, and `page`; returns fuzzy candidates including `mid`, `uname`, `usign`, `fans`, `videos`, `level`, and `upic`. WBI/risk control applies. |
| `https://space.bilibili.com/{mid}` | official page identity | 2026-08-19 | Numeric `mid` is the stable Creator space identity. |

## Findings

- Creator display names are fuzzy and non-unique. A search result is a candidate, never resolved identity.
- Numeric `mid` is the stable identity needed by later Creator Content Discovery.
- A bounded first-page query is sufficient for disambiguation and does not need per-candidate profile, Video, Dynamic, transcript, or comment requests.
- Bilibili may return HTTP 412 or a risk-control payload. Endpoint failure must remain an explicit failure rather than an empty result.
- Candidate text and image URLs are untrusted remote evidence and require existing response-size bounds.

## Applicability To This Project

Applies:

- Reuse authenticated Video Search behavior: login precheck, platform order, small result limit, bounded text, one search request on a valid response, structured/text output, and explicit shape failure.
- Return a canonical Creator source URL derived locally from `mid`.

Does not apply:

- No Creator auto-selection, semantic ranking, recommendation, Content Discovery, or per-candidate detail crawl.
- No anonymous or webpage fallback.

## Decision Impact

Recommended project action:

- Add `search_bilibili_creators` beside the existing Video Search interface and reuse existing search, credential, validation, bounded-text, and error patterns without a generalized search framework.

Rules or files that may need updates:

- Creator domain language, tool schema/handler, shared search module/types, validation tests, protocol smoke, bilingual tool references, changelog, and codemap.

## Risks And Unknowns

- The web-facing response may add or omit optional profile fields.
- HTTP 412 and WBI/risk-control behavior can vary by request identity and time.
- Authenticated live success is not authorized for this implementation run; deterministic fixtures must carry acceptance and the report must mark live smoke skipped.

## Staleness Notes

Refresh this research when:

- Bilibili changes Creator search, WBI, identity, or risk-control behavior
- a later ticket begins Creator Content Discovery

## Follow-Up

- [ ] Run a credential-safe authenticated smoke only after explicit credential-use authority.
