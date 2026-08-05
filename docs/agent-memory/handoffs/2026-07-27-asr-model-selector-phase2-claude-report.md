# Claude To Codex Report: ASR Model Selector Phase 2

## Summary

Implemented task ASR-SELECT-02: added a three-model allowlisted selector (`tiny`/`base`/`small`) after the existing Yes answer in the ASR setup flow, with Enter defaulting to recommended `small`. All acceptance criteria from the task ticket and PRD are satisfied with direct test or command evidence.

## Files Changed

- `src/asr/state.ts` — Added `as const` literal allowlist deriving `AsrModelKey` and `AsrModelSpec` types, `resolveModelSpec()`, `isAllowlistedModel()`, `modelKeyForRepo()`. Modified `readAsrState()` to accept any allowlisted repository/revision and return derived `modelKey`. Modified `writeAsrState()` to accept `AsrModelKey` (defaults to `"small"`). Phase 1 aliases `ASR_PINNED_MODEL`/`ASR_PINNED_REVISION` preserved.
- `src/asr/installer.ts` — `downloadModel()` now takes `modelId`/`revision` parameters. `runAsrInstallation()` accepts optional `modelKey`, resolves spec before any mutation, handles model-switch invalidation, shows correct model size in progress, and passes model key to `writeAsrState()`. Added "ponytail" comment at the one-active-model decision.
- `src/cli.ts` — Added `parseModelChoice()` pure function (accepts `1/2/3`, names, Enter=small, returns `AsrModelKey | null`). `setupCredentials()` shows model selector after Yes, re-prompts invalid input, passes `AsrModelKey` to installer. `buildDoctorStatus()` reads derived `modelKey` from `readAsrState()` directly. `DoctorStatus.asr` includes `model: AsrModelKey | null`. `doctorCommand()` text output shows model when installed.
- `tests/asr-installer.test.ts` — Updated existing tests for new function signatures. Added 23 Phase 2 tests: `resolveModelSpec`, `isAllowlistedModel`, `readAsrState` Phase 2 compatibility, `writeAsrState` with model keys, `runAsrInstallation` with modelKey (tiny/default/switch/idempotent/size).
- `tests/cli.test.ts` — Updated existing tests for new `runAsr` parameter. Added 25 Phase 2 tests: `parseModelChoice` (numbers/names/default/invalid), `buildDoctorStatus` model field (null/small/tiny/base/defensive), setup model selection flow (No/Enter/numbers/names/re-prompting).
- `docs/agent-memory/codemap.md` — Updated ASR and CLI sections for Phase 2.
- `README.md`, `README_EN.md` — Updated ASR limits section to mention three-model selector.
- `CHANGELOG.md`, `CHANGELOG_EN.md` — Updated ASR entry for three-model selector.
- `docs/client-setup.md`, `docs/client-setup.en.md` — Rewrote optional ASR model installation section and Agent prompt for Phase 2.
- `docs/qa/2026-07-27-asr-model-selector-phase2.md` — Created QA checklist.

## Commands Run

```bash
npm run build                          # PASS
npx vitest run tests/asr-installer.test.ts tests/cli.test.ts  # 158 tests PASS
npx vitest run tests/asr-installer.test.ts tests/cli.test.ts tests/mcp-server-smoke.test.ts  # 169 tests PASS
npm test                               # 570 tests PASS
npm pack --dry-run --json --ignore-scripts  # 148 files, no unexpected
git diff --check                       # only pre-existing LF/CRLF warnings
node dist/cli.js --help                # correct help output
node dist/cli.js doctor --json         # valid JSON, asr.model: null, no credentials
```

## Results (after Codex review repair)

| Check | Result |
|---|---|
| Build | PASS |
| Focused tests (asr + cli) | 158 PASS (+26 repair) |
| Focused + smoke | 169 PASS |
| Full test suite | 570 PASS (+26 repair) |
| npm pack dry-run | 148 files, no unexpected |
| git diff --check | PASS (LF/CRLF pre-existing) |
| Built CLI help | Correct |
| Built doctor --json | Valid, asr.model present, no credentials |
| Test-baseline-builder subagent | Invoked; found minor test naming issue (fixed) |

## Repair Summary (2026-07-27, per Codex review)

Following Codex review, all nine findings were addressed:

1. **AsrModelKey type** — added literal union derived from readonly allowlist; used in `resolveModelSpec`, `writeAsrState`, `runAsrInstallation`, `parseModelChoice`, `DoctorStatus.asr.model`, and `setupCredentials` runner.
2. **`readAsrState` derived key** — `readAsrState()` now returns `modelKey` via `modelKeyForRepo()`; CLI no longer reimplements allowlist lookup.
3. **Model-switch failure regression** — added test: ready tiny → switch to small → verify fails → state incomplete.
4. **Invalid-key untouched-mutation** — added test proving unlink/mkdir/spawn all untouched on invalid `modelKey` at runtime.
5. **Allowlist order tests** — added exact three-item order and count test.
6. **Cross-paired rejection** — added tests for tiny repo+small revision, base repo+tiny revision, small repo+base revision.
7. **Malicious key rejection** — added tests for `medium`, URL-like, `../tiny`, `constructor`, `__proto__` in `resolveModelSpec`.
8. **No-branch selector silence** — added tests proving model selector text is absent on No, present on Yes.
9. **Stale Phase 1 README wording** — replaced both `README.md:48` and `README_EN.md:48` installation summaries; full Phase 1 scan clean.
10. **QA claim corrected** — "immutable at runtime" → "readonly, fixed source allowlist (compile-time `AsrModelKey` union)".
11. **Phase 1 scope corrected in report** — noted that Phase 1 QA did not perform real pip/download/CPU load.
12. **Test-baseline-builder invoked** — confirmed test design; fixed one misleading test name and one duplicate empty-string test.

## Diff Notes

- State version 1 was kept backward compatible; no migration needed.
- `ASR_PINNED_MODEL` and `ASR_PINNED_REVISION` remain exported for Phase 1 consumers.
- `writeAsrState()` signature added `modelKey` before the filesystem function parameters (all default to `"small"`).
- `downloadModel()` signature added `modelId` and `revision` before the spawn/mkdir parameters.
- `setupCredentials()` `runAsr` parameter changed from `() => Promise<>` to `(modelKey: AsrModelKey) => Promise<>`.
- **Repair**: Added `AsrModelKey` literal union type, `modelKeyForRepo()` helper, and `modelKey` field on `AsrState`. `buildDoctorStatus()` now reads `asrState.modelKey` directly instead of reimplementing allowlist lookup. All `modelKey` parameters tightened from `string` to `AsrModelKey`.

## Risks Or Skipped Checks

- **Risk-reviewer subagent stalled** (Phase 2 initial) — no response after launch. Completed a top-level credential and security review manually.
- **Risk-reviewer subagent** (repair) — not re-invoked; manual top-level review confirms no credential leaks, no MCP tool changes, no package version/dependency changes, and Phase 1 backward compatibility verified through tests.
- **Test-baseline-builder subagent** (repair) — invoked successfully. Found one misleading test name and one duplicate empty-string test. Both fixed.
- **No real model download** — all tests use synthetic spawn functions. Phase 1 exercised real Python discovery and temporary venv creation during QA but did not perform a real pip/model download or CPU model-load smoke. Real download, pip install, and CPU INT8 verification remain untested against live Hugging Face infrastructure.
- **Concurrent setup** — remains documented as unsupported (one installer process at a time).
- **Per-model directories** — explicitly deferred with ponytail comment; one active model reuses the Phase 1 directory.

## Harness Artifacts

- **Task ticket**: used — `docs/agent-memory/handoffs/2026-07-27-asr-model-selector-phase2-task-ticket.md` (ASR-SELECT-02)
- **Research note**: not required — model allowlist research already completed by Codex in `docs/research/2026-07-27-asr-model-selector-phase2.md`
- **QA checklist**: created — `docs/qa/2026-07-27-asr-model-selector-phase2.md`
- **Codemap**: updated — ASR and CLI sections (initial); repair added `modelKeyForRepo` and `AsrModelKey` to ASR section
- **Harness security**: reviewed — no credential leaks, child-env filtering preserved, doctor JSON contains no secrets
- **Harness eval**: deferred — not a roadmap phase, release, or significant harness update
- **Test-baseline-builder**: invoked (repair) — confirmed test design is sound; two minor issues fixed

## Decision Points

None. All handoff constraints were satisfied without ambiguity.

## Suggested Codex Review Focus

1. `src/asr/state.ts` — verify the allowlist entries match the research note (repository, revision, approximateMB).
2. `src/cli.ts` — verify the `parseModelChoice()` function behavior for edge cases (whitespace-only input, case sensitivity).
3. Approval of `asr.model` as a stable doctor field name before publication.
