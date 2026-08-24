# Execution Report: Issue #53 WBI HTTP 412 Subtitle Fallback

## Contract

- Task/source: GitHub Issue #53
- Mode: `codex-direct`
- Canonical worktree: `C:/Users/ZX/.codex/worktrees/issue-53-diagnosis/bilibili-mcp`
- Base: `afb362905f4899f971e3e69d05236de70ee4f59e`
- Branch: `codex/issue-53-wbi-412-fallback`
- Writer/acceptance owner: Codex / Codex
- Terminal state: acceptance pending at report creation

## Summary

`getVideoSubtitle()` now reuses its existing `/x/player/v2` fallback when the
WBI subtitle endpoint fails with `NetworkError.statusCode === 412`. Every other
transport, API, authentication, parser, timeout, abort, and retry boundary is
unchanged.

## Files Changed And Diff Scope

- `src/bilibili/video-api.ts`: catch only WBI HTTP 412 and flow into the
  existing non-WBI fallback block.
- `tests/bilibili-video-api.test.ts`: deterministic 412 success regression,
  exact request-count assertions, and a 403 negative control.
- This execution report.

No MCP schema, public error code, retry policy, credential storage, Cookie
construction, package, release, workflow, or generated Harness file changed.

## Commands And Results

- Red: focused 412 regression failed with `NetworkError: HTTP 412`; the fallback
  endpoint was not reached.
- Green: focused 412 regression passed after the shared guard.
- `npx vitest run tests/bilibili-video-api.test.ts`: 15/15 passed.
- `npx vitest run tests/subtitle-fallback-security.test.ts tests/retry.test.ts`:
  7/7 passed.
- Final focused boundary run: 3 files / 22 tests passed.
- Final `npm run build`: passed.
- Final `npm test`: 44 files / 1154 tests passed.
- `git diff --check`: passed; Git emitted only existing Windows LF-to-CRLF
  working-copy warnings.
- Added-line secret pattern check: zero private-key, GitHub, npm, AWS, or full
  Bilibili Cookie-pattern matches.

No live Bilibili request or real credential was used.

## Acceptance Criteria

- `wbi-412-fallback`: pass; exactly one WBI request and one non-WBI fallback.
- `non-412-propagation`: pass; HTTP 403 preserves `NetworkError`/403 and makes
  zero non-WBI requests.
- `api-auth-preserved`: pass by narrow `NetworkError`/412 guard and existing
  API/auth regressions.
- `malformed-fail-closed`: pass; existing malformed-response test remains green.
- `verification-green`: pass; focused tests, build, and full suite are green.
- `scope-secret-clean`: pass; three ticket-owned files only and scoped scan
  reports no credential material.

## Repairs And Failure Fingerprints

- One planned TDD cycle: WBI 412 escaped before fallback, then passed after the
  status-specific guard.
- No review repair was required.

## Risks, Skipped Checks, Recovery Bundle

- No live WSL2 plus real-Cookie HTTP 412 reproduction was run. The reporter's
  environment-dependent observation is covered by deterministic transport
  injection at the shared API seam.
- No new direct abort or `COOKIE_EXPIRED` `getVideoSubtitle()` regression was
  added; the status-specific type guard and existing lower-layer tests leave
  low residual risk.
- No Recovery Bundle was needed.

## Capabilities Used

- Manual Skill: `implement`, explicitly invoked by the user for Codex direct
  execution and recorded through the Codex `$implement` manual gate.
- Model-invoked Skills: `diagnosing-bugs`, `tdd`, `secret-scanning`, and
  `code-review`.
- `vitest` Skill was not exposed in the active Codex catalog; existing Vitest
  CLI commands and repository test conventions were used as the fallback.
- Read-only agents: Standards-axis reviewer (no findings), Spec-axis reviewer
  (no findings), and project `risk-reviewer` (no findings).
- External tools: live `gh issue view` for Issue #53; local Git, npm, TypeScript,
  Vitest, and Harness CLI for authoritative worktree evidence.

## Harness Artifacts

- Task ticket: live GitHub Issue #53; no duplicate local ticket.
- Research: none; no external design fact was needed beyond reporter evidence,
  which was verified against source and deterministic tests.
- Security: scoped credential-pattern scan passed; no real Cookie used.
- QA checklist: not created; no install, release, client configuration, or live
  credential workflow changed.
- Codemap: checked; module ownership/navigation is unchanged.
- Memory: this execution report only; no durable project fact is promoted before
  acceptance.
- Harness security: checked for the report surface; no secret or new authority.
- Harness eval: checked; no workflow change or new evaluation entry needed.

## Local Commit

Pending Harness acceptance and the focused automatic local commit. No push, PR,
Issue close, tag, release, or publication is authorized.
