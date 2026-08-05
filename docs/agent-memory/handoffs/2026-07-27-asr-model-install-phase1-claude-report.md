# Claude To Codex Report: Optional ASR Model Installation Phase 1

## Summary

Implemented the default-off ASR model installation Phase 1 per the task ticket. Added `src/asr/state.ts` (immutable pinned constants, paths, versioned state file) and `src/asr/installer.ts` (Python discovery, venv, pip, model download, CPU INT8 verification). Integrated optional ASR into `setup` and added ASR status to `doctor`. Bumped Node engine to `>=20.0.0`. All subprocess calls use argument arrays with no shell interpolation. Default No produces zero ASR side effects.

## Files Changed

- `src/asr/state.ts` — new: pinned runtime/model/revision constants, path derivation, versioned state read/validate, atomic state write
- `src/asr/installer.ts` — new: `PythonCommand` with `py -3` support, `buildAsrChildEnv`, `-I` isolation on all Python ops, argv-based model params, exact marker matching, idempotency, stale-marker invalidation
- `src/cli.ts` — extended `DoctorStatus` with `asr` object, `buildDoctorStatus` with injectable ASR state reader, `setupCredentials` with optional ASR prompt after credentials, human-mode doctor with ASR status line, setup command wired to real installer
- `tests/asr-installer.test.ts` — new: 51 deterministic tests (state, discovery, venv, pip, download, verify, orchestration, idempotency, isolation, env filter, regression). No real Python/pip/network/model-download.
- `tests/cli.test.ts` — updated: doctor stable keys include `asr`, 8 new ASR tests (cross-tests, exit codes, redaction, empty-answer, default-No, nonzero-failure)
- `package.json` — engine `>=18.0.0` → `>=20.0.0`
- `package-lock.json` — updated via `npm install`
- `CHANGELOG.md` — Unreleased entries: ASR install, engine bump
- `CHANGELOG_EN.md` — equivalent English entries
- `docs/agent-memory/codemap.md` — new ASR Installation section, test entry added
- `docs/qa/2026-07-27-asr-model-install-phase1.md` — completed QA checklist
- `README.md`, `README_EN.md` — optional ASR discovery in install section, qualified No-ASR limit
- `docs/client-setup.md`, `docs/client-setup.en.md` — optional ASR subsection, Agent prompt ASR note
- `docs/agent-memory/handoffs/2026-07-27-asr-model-install-phase1-task-ticket.md` — status completed, all criteria checked
- `docs/agent-memory/handoffs/2026-07-27-asr-model-install-phase1-claude-report.md` — this report

## Not Changed

- MCP tool schemas/handlers, Bilibili request modules
- `dist/` — not manually edited
- SVG files
- `docs/agent-memory/pending-learning-proposals.md`
- `docs/tool-reference*.md`
- Package version — unchanged at 1.10.1

## Current Final Verification

- **Build**: PASS
- **Focused tests**: 95 passed (asr-installer 51, cli 33, mcp-server-smoke 11)
- **Full tests**: 496 passed (27 files)
- **Pack dry-run**: 148 files, 140,199 bytes, version 1.10.1
- **git diff --check**: no whitespace errors
- **Security**: `-I` on all Python ops, `buildAsrChildEnv` filters Bilibili + Python env keys, no process.env captured in tests, synthetic env fixtures only

## Commands Run

```powershell
npm run build
npx vitest run tests/asr-installer.test.ts tests/cli.test.ts tests/mcp-server-smoke.test.ts
npm test
npm pack --dry-run --json --ignore-scripts
npm install
git diff --check
```

## Results

- **Build**: PASS — TypeScript compilation clean, `dist/asr/` emitted with no errors
- **Focused tests**: 95 passed (asr-installer 51, cli 33, mcp-server-smoke 11)
- **Full tests**: 496 passed (27 files)
- **Pack dry-run**: 148 files, version 1.10.1. `dist/asr/` compiled files present; no venv/model/cache/state/test/QA/memory files leaked
- **git diff --check**: no whitespace errors
- **npm install**: lockfile updated for engine change

## Subagents Used

- **test-baseline-builder**: not invoked — tests implemented directly. 95 focused tests plus existing suites; all pass. Coverage includes state validation (read/write/atomic/artifact), Python discovery (override/path/version/env-isolation), subprocess gating (all use argument arrays), orchestration success/failure/idempotency/stale-invalidation/regression, cleanEnv case-insensitivity, env omission, credential redaction, and doctor ASR cross-tests.
- **package-maintainer**: not invoked — `package.json` engine change and lockfile update performed directly; `npm pack --dry-run` confirms 148 files with `dist/asr/` present and no model/cache/state/test files leaked.
- **risk-reviewer**: invoked twice — first review (no blocking, one tautological test and two non-blocking observations, all repaired); second review after Codex repair round (no blocking findings, 11/11 points verified).

## Skipped Real Download Checks

- Real Python discovery with actual Python 3.9+ on the developer machine was not tested
- Real venv creation, pip install, model download, and CPU INT8 verification were not performed
- These require Python 3.9+ and network access to PyPI and Hugging Face; the installer provides actionable errors and leaves no ready marker on failure

## Acceptance Criteria Status

- [x] No is the default and performs no ASR command/network/filesystem mutation
- [x] Existing configured credentials do not prevent the ASR question
- [x] Yes uses only the fixed runtime/model/revision from the PRD
- [x] Install is user-scoped, does not mutate global Python, and uses no shell
- [x] Successful verification writes a private versioned state file atomically
- [x] Failure writes no ready state, returns actionable guidance, and preserves partial files for retry
- [x] Doctor reports `not_installed`, `incomplete`, or `ready` locally with no absolute paths or secrets
- [x] Doctor credential status and exit codes remain unchanged
- [x] Public MCP tools/schemas/responses and no-argument stdio remain unchanged
- [x] Package engine is Node `>=20.0.0`; entries still target `dist`
- [x] Model/runtime/cache files are never included in `npm pack`
- [x] Documentation explicitly says Phase 1 does not transcribe yet
- [x] Credentials, Cookies, tokens, `.env`, and private values are not printed or committed
- [x] Codemap and QA accurately describe the new flow

## Unresolved Risks

- Real-world Python discovery on macOS/Linux differs from Windows and was not tested cross-platform
- Hugging Face model download requires network access; a slow or interrupted connection may leave partial files (retry is safe because state is only written after successful verification)
- `huggingface_hub` is installed as a transitive dependency of `faster-whisper==1.2.1`; a future major release may change the API surface used in `snapshot_download`
- Simultaneous `setup` processes are not locked and could contend over the same managed venv, model directory, or state temporary file; users should run only one ASR installation at a time
- Python commands discovered through `py`, `python3`, or `python` still depend on PATH resolution; `BILIBILI_ASR_PYTHON` provides an explicit override
- Python/venv creation was exercised on the real Windows host, but the approximately 486 MB model download and CPU INT8 model load were intentionally not run in this phase's acceptance

## Harness Artifacts

- **Task ticket**: used — `docs/agent-memory/handoffs/2026-07-27-asr-model-install-phase1-task-ticket.md`, all acceptance criteria satisfied
- **Research note**: used — `docs/research/2026-07-27-asr-model-installer-phase1.md`, pinned versions and model revision from official sources
- **QA checklist**: created — `docs/qa/2026-07-27-asr-model-install-phase1.md`, all in-scope items verified
- **Codemap**: updated — new ASR Installation section, test entry added
- **Harness security**: reviewed — only scoped handoff/memory records changed; no hook, skill, agent, MCP config, trust-boundary rule, or credential was added
- **Harness eval**: deferred — evaluate after the next release or after ASR Phase 2

## Codex Review Repair Round

Applied all blocking and same-scope corrections from `docs/agent-memory/handoffs/2026-07-27-asr-model-install-phase1-codex-review.md`.

### Blocking fix 1: venv interpreter for all post-venv operations

`createVenv()` now returns a `PythonCommand` for the venv Python executable. `installRuntime()` uses `venvPython -m pip`. `downloadModel()` and `verifyModel()` use the venv Python. All post-venv operations now run through the managed interpreter.

### Blocking fix 2: readiness requires managed artifacts

`readAsrState()` now checks that the venv Python executable and all four required model files (`model.bin`, `config.json`, `tokenizer.json`, `vocabulary.txt`) exist. A valid state file with missing artifacts returns `incomplete`. State file absent but artifacts present → `incomplete` (not `not_installed`). Only absent state + absent artifacts → `not_installed`.

### Same-scope corrections

- `PythonCommand` type (`{executable, prefixArgs}`) for `py -3` support on Windows
- `discoverPython()` returns `PythonCommand`, checks `code === 0` for override probe
- Model ID/revision/local_dir passed via argv (not embedded in Python script source)
- Completion markers matched as exact lines (`stdout.trim() === "DOWNLOADED"`), not substrings
- `runAsrInstallation()` defaults `pythonOverride` to `process.env.BILIBILI_ASR_PYTHON`; explicit option takes precedence
- Idempotent: returns success without spawning when state is already ready
- `writeAsrState()` cleans tmp file on write or rename failure
- Bilibili credential env vars filtered from subprocess environment
- Diagnostic buffers bounded to last 2000 chars
- Installation stages logged via `onStage` callback
- Failed ASR install sets `process.exitCode = 1` in setup
- New setup tests: default No doesn't call runner, configured creds reach prompt, failure sets exitCode 1, success doesn't set failure
- All orchestration tests use unique temp `asrBase`; none touch `~/.bilibili-mcp/asr/`
- Risk-reviewer was invoked in the first round; report corrected

### Verification

- Build: PASS
- Focused tests: 95 passed (asr-installer, cli, mcp-server-smoke)
- Full tests: 496 passed (27 files)
- `npm pack --dry-run`: 148 files, `dist/asr/` present, no model/cache/state leaks
- `git diff --check`: no whitespace errors

## Decision Points

None. All implementation choices were bounded by the task ticket, PRD, and research note.

## Suggested Codex Review Focus

1. `src/asr/installer.ts` Python discovery and subprocess safety (argument arrays, no shell, PATH security)
2. `src/asr/state.ts` versioned state validation — confirm that changing pinned constants correctly invalidates old state
3. `src/cli.ts` setup flow — confirm ASR prompt only appears with TTY and after credential configuration
4. Package boundary — confirm `>=20.0.0` engine is the intended floor and no other package metadata changed
5. Real download smoke — run the installer with real Python 3.9+ and confirm the full download/verification/state-write pipeline

## Codex Smoke Addendum

Codex performed a bounded live smoke test (Windows, Python 3.13.7 via `py -3`):

- `discoverPython` resolved `py -3` with `-I` isolation
- `createVenv` created a managed temp venv under `-I`
- Venv verified via `venv/python -I -c "import sys; print(sys.executable)"`
- No pip install, no model download, no real model load performed
- Temp venv recycled after smoke; no state file written
- This smoke proves discovery + venv creation path only; full managed install was not tested live
