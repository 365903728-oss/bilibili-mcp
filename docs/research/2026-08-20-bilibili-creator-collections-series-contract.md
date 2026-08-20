# Research Note: Bilibili Creator Collections And Series Contract

## Research Topic

- Topic: Creator Collection/Series container listing and selected-member paging
- Date: 2026-08-20
- Owner: Codex
- Related task, PRD, ticket, or plan: GitHub Issues #44 and #47
- Refresh before: changing these endpoints, response fields, paging parameters, or authentication policy

## Question

Which current Bilibili-origin interfaces and response shapes can support distinct,
bounded `collections` and `series` sections in Creator Content Discovery?

## Context

Why this matters for `@xzxzzx/bilibili-mcp`:

- Issue #47 must preserve Bilibili's separate Collection and Series concepts,
  validate selected-container ownership, and return one bounded member page
  without per-Video detail requests.

What decision or implementation this may affect:

- Endpoint choice, container identity fields, cursor binding, request counts,
  response normalization, and explicit missing/risk-control errors.

## Sources

| Source | Type | Date checked | Notes |
|--------|------|--------------|-------|
| `https://api.bilibili.com/x/polymer/web-space/seasons_series_list` | live official API output | 2026-08-20 | Anonymous shape probes for public Creator mids returned `items_lists.page`, separate `seasons_list`, and separate `series_list`. No Cookie was sent. |
| `https://api.bilibili.com/x/polymer/web-space/seasons_archives_list` | live official API output | 2026-08-20 | Anonymous valid-container probe returned API `-352`; a credential-safe authenticated shape probe returned `aids`, `archives`, `meta`, and `page`. Only login/configuration booleans, keys, IDs, and counts were retained; no credential value or private content was printed. |
| `https://api.bilibili.com/x/series/series` | live official API output | 2026-08-20 | A valid Series returned `meta` with `series_id`, `mid`, name, description, and total; an invalid Series returned API code `147002`. No Cookie was sent. |
| `https://api.bilibili.com/x/series/archives` | live official API output | 2026-08-20 | A valid Series returned `archives` plus `page.num`, `page.size`, and `page.total`. Invalid/mismatched IDs can return code `0` with empty or unrelated data, so this endpoint alone cannot prove ownership. No Cookie was sent. |
| GitHub Issues #44 and #47 | accepted product specification and implementation ticket | 2026-08-20 | Defines distinct container families, bounded traversal, repeated membership preservation, and discovery-only behavior. |

## Findings

- `seasons_series_list` returns both families in one bounded combined page. Each
  item has `meta`; Collection identity is `season_id`, Series identity is
  `series_id`, and both metadata shapes carry the owning Creator `mid`, name,
  bounded description, and member `total`.
- Collection members use `seasons_archives_list`. A successful response carries
  Collection `meta`, so the response can prove both selected identity and
  Creator ownership before returning `archives`. Anonymous risk control must
  remain an explicit failure.
- Series ownership must be established with the bounded `series/series` metadata
  request before reading `series/archives`; the archive endpoint by itself does
  not reliably reject an invalid or cross-Creator `mid`.
- Both member responses expose BVID-based archive rows with title, cover,
  duration, publish time, optional stats, and charge/lesson markers. Neither
  requires a per-row Video detail request.
- Container-list continuation follows the upstream combined page because the
  endpoint exposes no independent family-total paging contract. A section may
  therefore return an empty family page with a continuation cursor when another
  family occupies that upstream page; callers continue until `next_cursor` is
  absent.

## Applicability To This Project

Applies:

- Reuse `fetchWithoutWBI`, credential/login precheck, bounded JSON, retry,
  timeout, validation, bounded text, and resource-limit errors.
- Use fixed upstream/output pages of 20, preserve upstream order, bind cursors
  to Creator/section/container, and expose page-local skipped rows.
- Revalidate selected Collection/Series identity and Creator ownership on every
  member-page call; never turn API failures or malformed identity into empty
  success.

Does not apply:

- No webpage fallback, automatic all-container member crawl, per-row detail
  request, transcript/comment fetch, persistence, OCR, or interpretation.

## Decision Impact

Recommended project action:

- Deepen the existing Creator Content module and tool with `collections` and
  `series`; keep one interface and use an optional positive `container_id` only
  for selected-member traversal.
- Keep the existing v1 cursor compatible while adding an optional container
  identity for Collection/Series cursors.

Rules or files that may need updates:

- Creator Content types, validation, handler/schema, focused tests, bilingual
  tool documentation, domain glossary, codemap, decisions, and package receipt.

## Risks And Unknowns

- Bilibili may change these web-facing interfaces or apply HTTP/API risk control
  even with configured credentials.
- The combined container-list page does not provide a separate total for each
  family; the implementation must not invent one.

## Staleness Notes

Refresh this research when:

- the Collection/Series endpoints, parameters, response fields, or risk-control
  behavior are changed or reused after a substantial delay.

## Follow-Up

- [ ] Re-run one credential-safe Collection member shape smoke before release.
