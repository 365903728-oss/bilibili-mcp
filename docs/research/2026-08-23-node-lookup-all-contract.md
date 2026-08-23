# Node.js Custom Lookup `all` Contract

## Research Topic

- Topic: Node.js custom lookup callback shape when `all: true`
- Date: 2026-08-23
- Owner: Codex
- Related task, PRD, ticket, or plan: GitHub Issue #54
- Refresh before: Reusing this conclusion for a later Node major compatibility change

## Question

What result shape must a custom network lookup callback return when Node.js requests all addresses?

## Context

Why this matters for `@xzxzzx/bilibili-mcp`:

- The ASR audio downloader pins one validated CDN address through a custom HTTPS lookup callback.
- Node.js 25.6.1 calls that callback with `all: true` in the reproduced Issue #54 path.

What decision or implementation this may affect:

- Whether the existing pinned address should be returned as one record or as an array while preserving the DNS-rebinding defense.

## Sources

| Source | Type | Date checked | Notes |
|--------|------|--------------|-------|
| [Node.js v25.6.1 DNS documentation](https://nodejs.org/download/release/v25.6.1/docs/api/dns.html#dnslookuphostname-options-callback) | official docs | 2026-08-23 | `all: true` changes the callback result to an array of `{ address, family }` records. |
| [Node.js v25.6.1 Net documentation](https://nodejs.org/download/release/v25.6.1/docs/api/net.html#socketconnectoptions-connectlistener) | official docs | 2026-08-23 | Family auto-selection sets `all: true` on the custom lookup. |

## Findings

- With `all: false` or absent, the callback receives one address and family.
- With `all: true`, the callback receives an array of address records and no separate family argument.
- Returning one already validated pinned address inside a one-element array satisfies the contract without allowing Node to resolve or select an unvalidated destination.

## Applicability To This Project

Applies:

- Branching on the lookup options and returning the pinned address in the shape Node requests.
- Regression coverage for both callback forms.

Does not apply:

- Removing the custom lookup, changing the resolver, broadening allowed media hosts, or returning additional DNS answers.

## Decision Impact

Recommended project action:

- Preserve the current pinned address and security checks; change only the callback result shape for `all: true`.

Rules or files that may need updates:

- The pinned HTTPS implementation and its focused regression test only.

## Risks And Unknowns

- The exact runtime path that requests `all: true` may vary by Node version and connection options, so both callback forms must remain supported.

## Staleness Notes

Refresh this research when:

- Node changes the custom lookup contract or the project changes its HTTPS/DNS pinning design.

## Follow-Up

- [x] Verify the focused regression on Node.js 20, 22, and 25.
