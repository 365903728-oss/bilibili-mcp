# Codex To Claude Handoff: Production Dependency Refresh

## Update Goal

Implement GitHub Issue [#19](https://github.com/XZXZZX-Ai/bilibili-mcp/issues/19) without widening the v1.8.0 product surface.

## Current Judgment

- `body-parser` 2.2.2 and `fast-uri` 3.1.2 can move to patched versions within their existing parent ranges.
- `@hono/node-server` cannot: all 1.x versions remain affected, while patched 2.x requires Node 20 and would break this package's documented Node 18 support.
- The current stdio server does not import Hono HTTP or `serveStatic`; forcing a major override is riskier than the unreachable advisory.

Source of truth:

- GitHub Issue #19
- `docs/research/2026-07-26-v1.8.0-production-dependency-advisory-triage.md`
- upstream MCP SDK Issues #2531 and #2548

## Recommended Approach

Run npm's native lockfile-only update for `body-parser` and `fast-uri`. Do not add dependencies or overrides.

## Files To Inspect

- `package.json`
- `package-lock.json`
- `CHANGELOG.md`
- `CHANGELOG_EN.md`
- `src/index.ts`
- `src/server.ts`
- `tests/mcp-server-smoke.test.ts`
- `docs/agent-memory/harness-security.md`

## Files To Edit

- `package-lock.json`
- `CHANGELOG.md`
- `CHANGELOG_EN.md`
- `docs/agent-memory/handoffs/2026-07-26-production-dependency-refresh-claude-report.md`

No other file should change.

## Required Capabilities

- Use `package-maintainer` to inspect the lockfile and package contents.
- Use `risk-reviewer` after the update.
- Do not use `test-baseline-builder`; no test or fixture change is expected.

## Constraints

- Preserve `package.json.engines.node` as `>=18.0.0`.
- Preserve `@modelcontextprotocol/sdk` at the existing root range.
- Do not add `overrides`, direct dependencies, scripts, or workflow changes.
- Do not modify source, tests, tool schemas, credentials, package entry points, or the eight-tool order.
- Do not touch `docs/agent-memory/pending-learning-proposals.md` or unrelated dirty files.
- No commit, push, tag, publication, or GitHub Release.

## Execution Steps

1. Record the existing dependency paths and dirty files.
2. Run:

   ```powershell
   npm update body-parser fast-uri --package-lock-only --ignore-scripts
   ```

3. Require:
   - `body-parser` resolves to at least 2.3.0.
   - `fast-uri` resolves to at least 3.1.4 and remains on major 3.
   - Hono, SDK, root manifest, scripts, and package entry points are unchanged.
4. Add equivalent CN/EN v1.8.0 security notes describing the compatible lock refresh and the deliberate Node 18/Hono boundary.
5. Run `npm ci`, build, full tests, production advisory check, package dry run, SDK stdio smoke, UTF-8, secret-pattern, and diff checks.
6. Write the Claude report and stop.

## Acceptance Criteria

- Three body-parser/fast-uri advisory records are cleared.
- The only remaining production advisory is the statically non-actionable Hono finding.
- Node 18 support and all MCP behavior remain unchanged.
- Build, all tests, package, stdio, and security gates pass.
- No source, test, dependency declaration, override, workflow, Git, or publication change occurs.

## Stop And Report If

- npm changes `package.json`, the MCP SDK, Hono, or unrelated direct dependencies.
- A patched body-parser/fast-uri version cannot be resolved within the existing range.
- Any build, test, stdio, package, or behavior gate fails.
- Clearing Hono would require raising Node support or a major override.

## Expected Claude Report

Use `docs/agent-memory/agent-communication.md` and include files changed, exact dependency diff, commands/results, residual Hono risk, subagent outcomes, Harness artifacts, and confirmation that no Git or publication action occurred.
