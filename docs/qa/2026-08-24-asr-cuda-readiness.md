# Issue #66 CUDA Readiness QA

Date: 2026-08-24
Worktree: `C:\Users\ZX\.codex\worktrees\issue-66\bilibili-mcp`
Branch: `codex/issue-66-cuda-readiness`
Base: `6199142cb35a5d3b12f70ee1c41a65e60d3ca696`

## Accepted Code Contract

- Interactive and non-interactive setup accept only `auto`, `cpu`, or `cuda`;
  Enter defaults to `auto`.
- `cpu` probes only `cpu/int8`. `auto` saves `cuda/float16` only after a real
  model inference; otherwise it explains a sanitized GPU category and saves
  CPU only after the CPU probe succeeds.
- Explicit `cuda` never silently falls back. A failed probe preserves the
  previous verified state, model, and managed runtime.
- Every setup rerun builds the exact `faster-whisper==1.2.1` and
  `ctranslate2==4.8.0` pair in staging, probes the selected local model with a
  generated WAV, consumes the generator, then publishes artifacts and their
  matching ready state. Captured activation errors roll back; incomplete
  rollback leaves state inactive so the runner fails closed. An explicit
  Python override remains authoritative.
- Public diagnostics expose only `no_nvidia_gpu`, `cuda_runtime_missing`,
  `runtime_version_mismatch`, or `model_probe_failed`; no raw stderr, command,
  environment, or local library path is returned.
- The project does not install or modify NVIDIA drivers, CUDA, cuBLAS, cuDNN,
  `PATH`, `LD_LIBRARY_PATH`, or global Python. Transcript and MCP success shapes,
  concurrency, resource limits, temporary-media cleanup, and pinned HTTPS are
  unchanged.

## Evidence

- TDD: the final Python-override repair failed 2/2 before implementation and
  passed 181/181 afterward; earlier device, transaction, and diagnostics
  regressions followed the same red-to-green route.
- Focused Vitest: 3 files / 321 tests passed.
- Complete Vitest: 44 files / 1,145 tests passed.
- TypeScript build: passed.
- Package dry run: 193 files; tests, Harness, research, QA, agent memory,
  credential files, and local runtime data excluded; entries still target
  `dist`.
- Production dependency audit: zero vulnerabilities.
- `git diff --check`: passed with Windows line-ending warnings only.
- Gitleaks 8.30.1: zero findings in the tracked diff, all three untracked
  evidence files, and rebuilt `dist`.
- Isolated Windows CPU smoke: exact pins installed, setup published `cpu/int8`,
  and the actual managed runner completed a generated-WAV transcript.
- Isolated explicit-CUDA failure without external libraries returned
  `cuda_runtime_missing`, preserved the prior state and runtime marker,
  performed no CPU fallback, and left no staging residue.
- Fresh Windows GPU acceptance on an RTX 5060 Laptop GPU / driver 592.19: with
  CUDA 12 libraries supplied from a disposable external environment through
  process-local `PATH`, exact
  `faster-whisper==1.2.1` + `ctranslate2==4.8.0` setup published
  `cuda/float16`; the actual managed runner produced one non-empty 46-character
  segment from a locally synthesized speech WAV.
- GPU acceptance left zero staging/backup/probe-WAV residue and did not modify
  the user's existing v1 ASR state, global Python, persistent `PATH`, or
  `CUDA_PATH`.
- Standards and Spec review: no remaining code or scope finding after repairs;
  final independent hardware-evidence review accepted the Windows GPU gate.
- Final risk repairs deterministically cover state-publication plus rollback
  failure, probe-WAV cleanup failure under `auto`, and first-backup-rename
  failure without deleting the prior runtime.

## Residual Boundaries

- The Issue #66 fresh Windows GPU gate is satisfied. No real Linux GPU machine
  was exercised, so Linux GPU execution remains documented but not
  machine-verified.
- Users must still install or expose compatible NVIDIA libraries themselves;
  the project does not persist the temporary acceptance environment or mutate
  host loader configuration.
- Concurrent setup processes are outside the supported #66 path. The code does
  not claim a cross-process atomic transaction; it guarantees staged readiness,
  captured-error rollback, and fail-closed state when rollback is incomplete.
- The Codex Security CLI cloud scan did not complete because its stored login
  could not be refreshed. Gitleaks and the bounded reviewer checks remain the
  completed security evidence; this is not represented as a Codex Security
  pass.
