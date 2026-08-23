# Execution Report: GitHub Issue #66

## Contract

- Task/source: GitHub Issue #66; parent #55; depends on merged #65 behavior.
- Mode: `codex-direct`, following the user's explicit no-Paseo direction.
- Canonical worktree/base: `C:\Users\ZX\.codex\worktrees\issue-66\bilibili-mcp`
  at `6199142cb35a5d3b12f70ee1c41a65e60d3ca696`.
- Terminal state: locally accepted and uncommitted. The fresh Windows GPU
  setup-to-transcript gate is satisfied; remote effects remain a separate
  authority gate.

## Summary

Setup now owns a three-value device preference and publishes only an actual
verified Execution Profile. The exact managed runtime is built in staging and
the selected local model must complete generated-WAV inference before staged
runtime/model publication and the matching ready-state write. Captured
activation errors roll back; incomplete rollback leaves state inactive. Auto
can fall back to verified CPU with a
sanitized explanation; explicit CUDA cannot.

First-ASR automatic migration and its concurrency behavior remain #67. Public
transcript/MCP schemas, playback security, limits, and credential behavior did
not change.

## Files Changed

- Runtime: `src/asr/state.ts`, `src/asr/installer.ts`,
  `src/asr/transcription.ts`, and `src/cli.ts`.
- Tests: `tests/asr-installer.test.ts`, `tests/asr-transcription.test.ts`, and
  `tests/cli.test.ts`.
- User docs: bilingual README and client setup guidance.
- Evidence: research, QA, active work, project facts, decisions, codemap,
  verification log, handoff log, and this report.

## Verification

- Focused Vitest: 3 files / 321 tests passed.
- Complete Vitest: 44 files / 1,145 tests passed.
- `npm run build`: passed.
- `npm pack --dry-run --json --ignore-scripts`: 193 files with all package
  exclusions and `dist` entry points preserved.
- `npm audit --omit=dev --json`: zero production vulnerabilities.
- `git diff --check`: passed; Gitleaks 8.30.1 found zero secrets in the tracked
  diff, three untracked evidence files, and rebuilt `dist`.
- Isolated exact-pin CPU setup and actual runner smoke: passed.
- Isolated explicit-CUDA failure: `cuda_runtime_missing`; previous state and
  runtime preserved, no CPU fallback, zero staging residue.
- Fresh Windows exact-pin GPU setup on RTX 5060 Laptop GPU / driver 592.19:
  published `cuda/float16`; the actual managed runner produced one non-empty
  segment / 46 characters from synthetic speech, with zero staging, backup, or
  probe-WAV residue.
- Standards and Spec reviewers: no remaining finding after same-scope repairs.
- Codex Security did not complete because local auth refresh failed; no scan
  pass or finding conclusion is claimed from that tool.

## Review Repairs

- Made runtime and model replacement one transaction so any failed probe keeps
  the old verified installation intact.
- Kept post-publication backup deletion best-effort so cleanup cannot report a
  false setup failure after activation.
- Distinguished CPU probe failures and preserved both sanitized categories when
  auto GPU and CPU probes fail.
- Honored explicit/environment Python overrides for ready same-model and
  model-switch rebuilds while retaining managed-Python reuse without override.
- Made probe cleanup failure non-fallbackable and moved the prior state out of
  the active slot during artifact activation, so incomplete rollback cannot
  expose a stale ready Profile.

## Residual Risk

- The host does not expose CUDA inference libraries by default. The successful
  acceptance used official NVIDIA wheels in a disposable external environment
  and process-local `PATH`; end users still own that prerequisite.
- No real Linux GPU machine was exercised, so Linux support is not claimed as
  machine-verified.
- Best-effort deletion can leave a bounded backup directory when the OS denies
  cleanup; the active verified runtime remains correct, but repeated external
  denial could consume disk until the user removes stale backups.
- Concurrent setup processes remain unsupported; this implementation does not
  claim cross-process atomicity across runtime, model, and state.

## Capabilities Used

- User-invoked manual Skill: Matt `implement` for #66.
- Model-invoked Skills: Matt `tdd`, `code-review`, `codebase-design`, Vitest,
  `secret-scanning`, and `bilibili-mcp-memory`.
- Reviewers: independent Standards/Spec axes and the project risk-review role;
  no reviewer edited files.

## Harness Artifacts

- Task ticket: live GitHub Issue #66; no duplicate local ticket.
- Research note: `docs/research/2026-08-24-asr-cuda-readiness.md`.
- QA checklist: `docs/qa/2026-08-24-asr-cuda-readiness.md`.
- Codemap and durable memory: updated for device preference, exact pins,
  staged/fail-closed activation, failure categories, and the external GPU gate.
- Harness security: reviewed; no credential or new authority boundary.
- Harness eval: unchanged; #66 does not redesign the Harness or adapter flow.

## Git And Remote State

No commit, push, PR, merge, Issue close, tag, release, or npm publication was
performed.
