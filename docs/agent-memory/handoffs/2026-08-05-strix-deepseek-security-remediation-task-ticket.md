# Task Ticket: Strix + DeepSeek Security Remediation

## Ticket

- ID: `SEC-2026-08-05-STRIX`
- Title: Close the validated Strix follow-up findings
- Status: `ready`
- Owner: Claude Code through Paseo; Codex reviews
- Source: Strix run `bilibili-mcp_e8df` and Codex validation
- Parent plan: 2026-07-30 deep-security remediation follow-up
- Blocking tickets: none
- Blocked by: none

## Objective

Close the two confirmed, three conditional, and one grouped dependency verdict
from the validated Strix report with the smallest compatible changes, while
preserving the ten-tool legacy stdio product boundary and every prior
38-finding remediation control.

## Scope

In scope:

- Remove C1, bidi-control, and zero-width/BOM output pollution from all bounded
  Bilibili-derived text, and sanitize native/ASR transcript lines consistently.
- Mark affected tool descriptions as returning untrusted Bilibili data without
  changing tool names, order, schemas, or successful result shapes.
- Reject non-string BVID input before string methods and prevent unexpected
  validation exceptions from reaching MCP callers verbatim.
- Reject subtitle URLs with non-default ports or userinfo.
- Make ASR state writes owner-only, unique, exclusive, atomic, and symlink-safe;
  fail the ready gate for symlinked state/runtime/model paths.
- Raise the v1 MCP SDK minimum to 1.30.0, refresh the lockfile normally, and
  remove the current production audit findings if compatible resolution allows.
- Add deterministic regressions, QA, and a Claude report.

Out of scope:

- MCP SDK v2 or protocol migration; HTTP/SSE transport; new tools or fields.
- ASR model download/switch, real transcription, live Bilibili traffic, or real
  Cookie use.
- Commit, stage, push, PR, version bump, tag, release, or npm publication.
- Refactoring unrelated modules, changing limits, or promoting learning
  proposals.

## Files To Inspect Or Edit

Expected inspect:

- `src/utils/bounded-text.ts`, `src/utils/validation.ts`
- `src/server/error-response.ts`, `src/server/tool-schemas.ts`
- `src/bilibili/subtitle.ts`, `src/bilibili/video-api.ts`, `src/bilibili/comments.ts`
- `src/asr/state.ts`, `src/asr/installer.ts`, `src/asr/transcription.ts`
- `package.json`, `package-lock.json`
- relevant tests and the validated report path in the handoff

Expected edit:

- only directly affected source and deterministic test files
- `package.json`, `package-lock.json`
- `docs/qa/2026-08-05-strix-deepseek-security-remediation.md`
- the expected Claude report

Do not touch:

- `dist/`, public version/changelog/release files, Git state, workflow YAML,
  credentials, `.env`, hooks, `pending-learning-proposals.md`, or historical
  scan artifacts.

## Required Capabilities

Skills:

- `vitest` for regression coverage
- `secret-scanning` for value-free source/package review
- `code-review` for the final changed diff
- `codex-security` if available; otherwise report it unavailable and use the
  bounded `risk-reviewer` fallback

Subagent:

- at most one `risk-reviewer` after implementation; no subagent tree

CLI:

- local `git`, `rg`, `npm`, `node`, `tsc`, and Vitest

## Execution Steps

1. Record the 127-entry dirty baseline and never normalize or revert it.
2. Add failing deterministic tests for each verdict before or with the fix.
3. Implement shared/root-cause fixes using existing utilities and patterns.
4. Refresh SDK/lockfile without overrides; stop if an override or v2 migration
   appears necessary.
5. Run focused tests, then build/full suite/audit/pack/stdio/secret/diff gates.
6. Run one bounded `risk-reviewer`, repair same-scope concrete findings, rerun
   affected checks, and write the required report/QA.

## Acceptance Criteria

- [ ] C1, bidi-control, and zero-width/BOM test payloads do not survive bounded
  remote text or native/ASR transcript output; tabs/newlines/CJK/emoji remain.
- [ ] A plain natural-language subtitle remains data and is not wrapped into a
  new public response shape; affected tool descriptions warn that Bilibili text
  is untrusted.
- [ ] Number/boolean/object `bvid_or_url` values return a stable controlled
  validation error across all five BVID tools, with no engine wording.
- [ ] Subtitle URLs with custom ports or userinfo fail before fetch; legitimate
  protocol-relative HTTPS URLs on the two exact hosts still work.
- [ ] ASR state temp writes use unique exclusive owner-only files and atomic
  rename; symlinked state, venv, executable parent, model directory, or model
  files never produce `ready`.
- [ ] SDK is 1.30.0-compatible and production audit findings are removed or any
  remaining advisory is explicitly classified before completion.
- [ ] Public MCP tool names, exact order, input schemas, and successful response
  shapes remain stable.
- [ ] Credentials and private values are never printed or stored.
- [ ] Existing 127-entry dirty baseline is preserved; no unrelated file is
  reverted, deleted, staged, or committed.
- [ ] Codemap is checked and left unchanged unless navigation-relevant structure
  actually changes.

## Verification

Required:

```powershell
npm run build
npm test
npm audit --omit=dev --json
npm pack --dry-run --json --ignore-scripts
git diff --check
```

Also run focused Vitest for changed modules, the existing public stdio
initialize/tools-list/tools-call smoke, value-free changed-file/package secret
classification, and ASR temp-residue checks. Do not run live Bilibili or model
tests.

## Risks And Rollback

- Over-filtering legitimate Unicode; protect with CJK/emoji/whitespace tests.
- SDK minor compatibility drift; protect with full suite and public stdio smoke.
- Windows/Unix state-file semantics; use Node-supported exclusive flags and
  deterministic tests without weakening fail-closed behavior.
- Rollback is the exact task-scoped diff only; never reset the worktree.

## Stop And Report Conditions

Stop for Codex if:

- an SDK v2 migration, dependency override, public response-shape change, new
  module architecture, or live credential/model/network operation is required;
- a real secret is found;
- required checks fail for a reason outside this scope;
- preserving existing callers conflicts with a proposed fix.

## Completion Report

Return the exact files changed, commands/results, skipped checks, capabilities,
subagent result, QA/codemap/harness status, residual risks, and suggested Codex
review focus in the report path named by the handoff.
