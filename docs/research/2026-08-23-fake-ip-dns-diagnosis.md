# Research Note

## Research Topic

- Topic: Standard Fake-IP DNS classification and user remediation
- Date: 2026-08-23
- Owner: Codex
- Related task, PRD, ticket, or plan: GitHub Issues #56 and #57
- Refresh before: changing the classified range or vendor-specific guidance

## Question

Which address range can be diagnosed as the standard Fake-IP case without
weakening playback-media connection safety, and which documented Mihomo
controls can an AI Agent explain to the user?

## Context

Why this matters for `@xzxzzx/bilibili-mcp`:

- Local ASR must reject special-purpose DNS answers but should distinguish the
  common Fake-IP configuration problem from generic audio unavailability.

What decision or implementation this may affect:

- DNS classification in `src/security/pinned-https.ts` and bounded MCP recovery
  guidance for `ASR_FAKE_IP_DNS`.

## Sources

| Source | Type | Date checked | Notes |
|--------|------|--------------|-------|
| [IANA IPv4 Special-Purpose Address Space](https://www.iana.org/assignments/iana-ipv4-special-registry) | official registry | 2026-08-23 | Lists `198.18.0.0/15` as benchmarking space and not globally reachable. |
| [Mihomo DNS configuration](https://wiki.metacubex.one/en/config/dns/) | official docs | 2026-08-23 | Documents `fake-ip`, configurable `fake-ip-range`, domain-wildcard `fake-ip-filter`, rule-mode `real-ip`, and `nameserver-policy`. |

## Findings

- IANA defines the whole `198.18.0.0/15` block, not one observed address, as
  special-purpose benchmarking space with `Globally Reachable = False`.
- Mihomo's Fake-IP range is configurable. Its official example uses an address
  within the IANA block, so one runtime-observed IP or one vendor default is not
  a durable classifier.
- Mihomo supports domain wildcards in `fake-ip-filter`; rule mode can return
  `real-ip` for selected domains. `nameserver-policy` provides a separate
  domain-specific resolver control.

## Applicability To This Project

Applies:

- Recognize only a non-empty, bounded DNS answer set whose every answer is an
  IPv4 address in `198.18.0.0/15`.
- Continue rejecting the addresses. Explain Fake-IP filtering or equivalent
  real-IP DNS rules for `*.bilivideo.com` and `*.bilivideo.cn` as user choices.

Does not apply:

- Do not infer the user's proxy product, node, route, or local configuration.
- Do not classify mixed answers, other special-purpose addresses, ordinary DNS
  failure, or media HTTP failure as Fake-IP.
- Do not allowlist `198.18.0.0/15` in the MCP server.

## Decision Impact

Recommended project action:

- Preserve pinned HTTPS, Host/SNI, TLS, redirect validation, credential
  stripping, and public-address rejection; carry only a bounded reason marker
  through candidate aggregation to MCP guidance.

Rules or files that may need updates:

- `src/security/pinned-https.ts`, `src/asr/transcription.ts`,
  `src/utils/errors.ts`, `src/utils/error-guidance.ts`, and their existing test
  seams.

## Risks And Unknowns

- Other proxy products can configure different Fake-IP ranges. Issue #57 is
  intentionally limited to the standard `198.18.0.0/15` diagnosis.
- UI steps vary by client. Public guidance should describe supported concepts,
  not promise exact FlClash menu names.

## Staleness Notes

Refresh this research when:

- IANA changes the registry entry, Mihomo changes Fake-IP configuration
  semantics, or the project adds another explicitly supported Fake-IP range.

## Follow-Up

- [x] Implement and test the bounded standard-range diagnosis without changing
  the connection allowlist.
