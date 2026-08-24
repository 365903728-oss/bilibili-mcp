# Issue #67 Codex Direct Execution Report

## Scope

- Ticket: GitHub Issue #67 under #55; blocked-by #66 was already closed.
- Branch: `codex/issue-67-v1-migration` from
  `4ad276cf28f01a519d1b848c1afe36cdcaeeface`.
- Actor: Codex direct, explicitly without Paseo.
- Product files: `src/asr/installer.ts`, `src/asr/transcription.ts`,
  `tests/asr-installer.test.ts`, and `tests/asr-transcription.test.ts`.

## Result

- The first explicit ASR request with v1 migration-pending state owns the
  existing ASR slot, reuses the installed model, runs auto readiness, atomically
  writes the v2 Profile/fixed failure category, and continues on that Profile.
- Completed v2 requests do not probe again. Setup remains the retry path.
- Abort propagates through the readiness subprocess, terminates its process
  tree, preserves `AbortError`, and cannot publish a ready state.
- Public transcript and MCP schemas remain unchanged.

## Commands And Results

- `npm run build`: pass.
- Focused Vitest: 2 files / 235 tests pass.
- `npm test`: 44 files / 1,152 tests pass.
- `npm pack --dry-run --json --ignore-scripts`: pass, 193 files.
- `npm audit --omit=dev --json`: zero production vulnerabilities.
- Gitleaks 8.30.1 on the current diff: zero findings.
- GitHub MCP secret scan: attempted; transport failed, so not claimed.
- Core Harness before receipt refresh: 102 tests, 15 skips, one expected stale
  package-receipt failure at `dist/asr/installer.d.ts`.
- Canonical-LF receipt check after refresh: 1/1 pass.
- Core Harness after refresh: 102 tests pass, 15 existing environment skips.

## Real Smoke And Boundaries

- The unchanged user v1 runtime had `ctranslate2 4.8.1`, so exact-pin readiness
  correctly failed without state publication.
- A disposable copied venv was pinned to `4.8.0` and reused the installed model.
  On a Windows NVIDIA host, auto classified `cuda_runtime_missing`, verified
  CPU, atomically saved completed `cpu/int8`, and emitted one sanitized log.
  An explicit CPU-path migration also completed. The disposable copy was
  removed and the user v1 state remained unchanged.
- This is a real GPU-attempt/fallback smoke, not a fresh CUDA-success claim.
  Linux GPU was unavailable; deterministic automation is the only Linux claim
  until Hosted CI and/or real Linux GPU evidence exists.

## Review

- Standards review found missing cancellation propagation. The repair threads
  AbortSignal into the subprocess tree killer and adds production-seam tests.
- Spec review found no behavior error or scope creep. The same-request CUDA test
  now uses the real migration function with readiness/write seams and a complete
  v1 model fixture.

## Harness Artifacts

- Task ticket: GitHub Issue #67.
- Research note: not required; no external behavior research changed design.
- QA checklist: Issue acceptance plus this report and verification log.
- Codemap: updated for one-time migration and abortable readiness.
- Harness security: unchanged; no raw stderr, paths, environment contents,
  Cookie, audio, or transcript body stored.
- Harness eval: not changed; this is a product ticket, not a Harness update.

## Remaining Gates

- Wait for GitHub Hosted product/Node/Harness matrices after a later push.
- Commit, push, PR, merge, Issue close, release, and publication require
  separate user authorization.
