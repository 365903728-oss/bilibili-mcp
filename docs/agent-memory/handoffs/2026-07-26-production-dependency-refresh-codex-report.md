# Codex Report: Production Dependency Refresh

## Summary

Codex implemented GitHub Issue #19 after the user confirmed that GLM had no remaining quota and explicitly selected Codex execution.

The smallest safe fix refreshed only compatible transitive lockfile resolutions:

- `body-parser`: 2.2.2 → 2.3.0
- `fast-uri`: 3.1.2 → 3.1.4
- `type-is`: 2.0.1 → 2.1.0
- `body-parser/node_modules/content-type`: added at 2.0.0
- `type-is/node_modules/content-type`: added at 2.0.0

No direct dependency, override, SDK upgrade, source change, test change, workflow change, or Node support change was added.

## Execution Routing

- Paseo agent `7e140c8b-cb41-42d8-ac64-3b1a50c1aeda` was launched with `claude/glm-5.2[1m]`.
- It produced no model activity or file change during two bounded waits and was stopped.
- The user then explicitly directed Codex to execute because GLM had no quota.
- No provider was silently substituted.
- The inactive Paseo agent was archived after Codex verification and independent review completed.

## Files Changed

Implementation:

- `package-lock.json`
- `CHANGELOG.md`
- `CHANGELOG_EN.md`

Codex-owned evidence:

- `docs/research/2026-07-26-v1.8.0-production-dependency-advisory-triage.md`
- `docs/qa/2026-07-26-v1.8.0-release-prep.md`
- project memory and Harness evaluation files
- this report and the Issue #19 handoff

## Commands Run

- `npm update body-parser fast-uri --package-lock-only --ignore-scripts`
- `npm ci`
- `npm ls --omit=dev --all @modelcontextprotocol/sdk @hono/node-server express body-parser ajv fast-uri`
- `npm explain body-parser fast-uri @hono/node-server`
- `npm run build`
- `npm test`
- Node 18.20.8 official MCP SDK stdio smoke
- official SDK 1.27.1 credentialed ordinary and multi-Part transcript acceptance
- `node dist/cli.js check`
- `npm audit --omit=dev --json`
- `npm pack --dry-run --json`
- strict UTF-8, intended-addition secret-pattern, package-sensitive-artifact, and `git diff --check` gates

## Results

- Clean install resolved `body-parser@2.3.0`, `fast-uri@3.1.4`, `type-is@2.1.0`, and the two required nested `content-type@2.0.0` copies through their existing parent ranges.
- MCP SDK stayed at 1.27.1 and Hono stayed on 1.x.
- Build passed.
- Full Vitest passed: 23 files / 299 tests.
- Node 18.20.8 started the built server through official `Client + StdioClientTransport`; server version was 1.8.0 and all eight tools were present.
- Official SDK credentialed calls preserved the full transcript schema, ordinary and multi-Part evidence URLs, and exact text/structured equality.
- Package dry run remained 124 files with the same entry points and no sensitive/internal artifacts.
- The three body-parser/fast-uri advisories disappeared.
- The audit now reports no high or critical production advisory. Its only underlying advisory is `GHSA-frvp-7c67-39w9`, surfaced on Hono and the SDK dependency edge.
- Strict UTF-8 decoding, intended additions, secret patterns, sensitive package artifacts, and diff checks passed.

## Security Boundary

Hono 2.0.5+ fixes the remaining advisory but requires Node 20. This package and MCP SDK 1.x support Node 18. The SDK imports only `getRequestListener`; neither it nor this stdio-only server imports the vulnerable `serveStatic` path.

Forcing a major Hono override would trade an unreachable finding for a real runtime compatibility break. The reviewed decision is to keep Node 18 and wait for the open upstream SDK range fix.

## Node 18 Caveat

The current Vitest/Rolldown development toolchain cannot start on Node 18 because it imports `node:util.styleText`. This is a development-tool limitation. The relevant shipped runtime boundary was tested directly under Node 18.20.8 with the official MCP SDK and passed.

## Harness Artifacts

- Task ticket: GitHub Issue #19.
- Research note: updated with the exact upstream and package decision.
- QA checklist: updated.
- Codemap: checked unchanged.
- Harness security: reviewed.
- Harness eval: updated.
- Independent package and risk reviews: passed after this report was corrected to enumerate the complete lockfile closure.

## Git And Publication Boundary

No commit, push, tag, workflow dispatch, npm publication, or GitHub Release was performed by this implementation.
