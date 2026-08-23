# Execution Report: GitHub Issue #65

## Contract

- Task/source: GitHub Issue #65; parent #55; no blocker.
- Mode: `codex-direct`, following the user's explicit no-Paseo direction.
- Canonical worktree/base: `C:\Users\ZX\.codex\worktrees\issue-65\bilibili-mcp`
  at `547b2bb170121bb7701d523e28f3a1f06b1224a8`.
- Terminal state: locally accepted and uncommitted; every remote effect remains
  a separate authority gate.

## Summary

CPU setup now persists an actual ASR Execution Profile only after the selected
local model completes a generated short-WAV inference and the result generator
and temporary file are fully consumed/cleaned. State v2, legacy v1 projection,
doctor reporting, and the Python runner share one controlled Profile contract.

CUDA execution, GPU readiness/fallback, first-ASR automatic migration,
concurrency changes, transcript shape, MCP schemas, dependencies, and network
security boundaries did not change.

## Files Changed

- Runtime: `src/asr/state.ts`, `src/asr/installer.ts`,
  `src/asr/transcription.ts`, and `src/cli.ts`.
- Tests: `tests/asr-installer.test.ts`, `tests/asr-transcription.test.ts`, and
  `tests/cli.test.ts`.
- Evidence: active work, project facts, decisions, codemap, verification log,
  this report, QA record, and mechanically refreshed Harness receipts.

## Verification

- Focused Vitest: 4 files / 282 tests passed.
- Complete Vitest: 44 files / 1,104 tests passed.
- `npm run build`: passed.
- `npm pack --dry-run --json --ignore-scripts`: 193 files; package exclusions
  preserved.
- `npm audit --omit=dev --json`: zero production vulnerabilities.
- Full audit: two unchanged high development-chain findings (`nanoid`,
  `postcss`); no dependency change or auto-fix.
- Gitleaks 8.30.1: zero findings in the tracked diff and both untracked evidence
  files.
- Harness core first identified one canonical-LF `LICENSE` receipt mismatch;
  the package/durable-memory/outer receipt chain was regenerated and the exact
  real-pilot conformance rerun passed 1/1.
- `git diff --check`: passed with Windows line-ending warnings only.
- Standards, Spec, and risk review: no remaining finding after same-scope
  repairs.

## Review Repairs

- Rejected contradictory CUDA-ready/failure states, then kept CUDA disk state
  non-ready until #66 so doctor/setup/transcription report the same fact.
- Restored real coverage in missing-artifact, symlink, and wrong-path-type tests
  after the v2 schema change.
- Made temporary-WAV deletion failure block ready publication.

## Residual Risk

- A real `faster-whisper` CPU smoke was not run because using the existing
  user-managed model would mutate or depend on state outside the isolated
  worktree. Deterministic subprocess tests cover the contract, but a small
  Python/PyAV compatibility risk remains for merge/release QA.

## Capabilities Used

- User-invoked manual Skill: Matt `implement` for #65.
- Model-invoked Skills: Matt `tdd`, `code-review`, `codebase-design`, Vitest,
  and `bilibili-mcp-memory`.
- `secret-scanning` was not exposed in this runtime; installed gitleaks 8.30.1
  is the bounded fallback.
- Reviewers: independent Standards, Spec, and project risk axes; no reviewer
  edited files.

## Harness Artifacts

- Task ticket: live GitHub Issue #65; no duplicate local ticket.
- Research note: not required; no external research changed implementation.
- QA checklist: `docs/qa/2026-08-24-asr-cpu-execution-profile.md`.
- Codemap and durable memory: updated for v2 state, CPU probe, Profile runner,
  doctor fields, decisions, active work, and verification.
- Harness security: reviewed; no credential, new authority, or external effect.
- Harness eval: unchanged; #65 does not redesign an adapter or workflow.

## Git And Remote State

No commit, push, PR, merge, Issue close, tag, release, or npm publication was
performed.
