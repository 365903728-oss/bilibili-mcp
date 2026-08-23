# Issue #65 CPU Execution Profile QA

Date: 2026-08-24
Worktree: `C:\Users\ZX\.codex\worktrees\issue-65\bilibili-mcp`
Branch: `codex/issue-65-cpu-execution-profile`
Base: `547b2bb170121bb7701d523e28f3a1f06b1224a8`

## Accepted

- State v2 writes only `cpu/int8`, `ready`, and `completed` after a real
  model-transcribe call and full segment-generator consumption.
- The generated one-second WAV is owner-only and removed before ready; deletion
  failure rejects setup.
- Legacy v1 keeps the existing model-ready fact but reports device migration
  pending. Same-model setup probes once and does not reinstall or redownload.
- Invalid keys, Profile pairs, readiness/migration values, failure categories,
  unexpected fields, symlinks, and wrong managed-path types fail closed.
- `doctor --json` exposes only controlled model/Profile/readiness fields and no
  stderr, command, environment, or local-path data.
- The runner receives only the validated Profile through argv. Transcript and
  MCP success schemas are unchanged.

## Evidence

- Focused: 4 files / 282 tests passed.
- Complete Vitest: 44 files / 1,104 tests passed.
- TypeScript build: passed.
- Package dry run: 193 files; tests, Harness, and agent memory excluded.
- Production dependency audit: zero vulnerabilities.
- Gitleaks 8.30.1: zero findings in the final diff and new evidence files.
- Harness canonical package/memory receipt conformance: passed after LF
  normalization of the generated package receipt.
- Standards, Spec, and risk review: no remaining findings.

## Deferred Boundary

- No user-managed ASR state or model was changed for a real CPU smoke. A
  sanitized real-model smoke remains a merge/release gate when an isolated
  disposable model/runtime is available.
- CUDA readiness/probe/fallback remains #66; first-ASR automatic migration and
  concurrency behavior remains #67.
