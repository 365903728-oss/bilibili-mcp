# Codex Review: ASR Model Selector Phase 2

## Status

Changes requested. Core behavior is sound and the reported tests pass, but the
current documentation contradicts the selector and one switch-failure
acceptance path lacks direct evidence.

## Blocking Findings

### 1. Both README installation summaries still describe Phase 1

`README.md:48` and `README_EN.md:48` still say setup installs only fixed
`faster-whisper-small`, labels the feature Phase 1, and says no model selector
exists. Later sections correctly describe Phase 2, so a new reader receives two
conflicting installation contracts.

Required repair:

- Replace both stale paragraphs with the three choices, Enter/default small,
  Python/runtime/storage/CPU INT8/no-system-FFmpeg facts, doctor model/status,
  and the accurate remaining limit: installation only, no transcription or
  audio fallback.
- Run a focused stale-Phase-1 wording scan across both READMEs and setup guides.

### 2. Model-switch failure has no direct regression

The task requires a ready model switched to another model to lose the old ready
marker before mutation and remain `incomplete` if the new verification fails.
The new tests cover a successful switch and Phase 1 stale-state failure, but no
test starts from ready model A, selects model B, fails verification, and asserts
the state is incomplete.

Required repair:

- Add that exact deterministic regression.
- Also strengthen the invalid-key test to prove injected unlink, mkdir, and
  spawn functions are all untouched.

## Same-Scope Corrections

- Add a literal `AsrModelKey` union derived from the readonly allowlist and use
  it for parsed CLI choices, doctor output, and the injected setup runner.
- Let `readAsrState()` return the derived model key after validating the exact
  repository/revision pair so `src/cli.ts` does not reimplement allowlist
  lookup. Do not persist the derived key or change state version 1.
- Add focused cases for exact three-item order, cross-paired known
  repository/revision rejection, and malicious/invalid keys such as
  `medium`, URL-like input, `../tiny`, `constructor`, and `__proto__`.
- Prove the No branch does not print the selector, not only that the runner is
  skipped.
- Change the QA claim "allowlist is immutable at runtime" to the evidence
  actually implemented (a readonly, fixed source allowlist), unless runtime
  freezing is deliberately added.
- Correct the Claude report: Phase 1 exercised real Python discovery and
  temporary venv creation, but did not perform a real pip/model download or CPU
  model-load smoke.
- Actually invoke `test-baseline-builder` for the changed tests or accurately
  record why the required subagent could not complete. Keep the already
  documented risk-reviewer fallback.

## Completion Records

After repairs and independent verification:

- Mark Phase 2 PRD and task-ticket criteria complete.
- Set the task ticket status to `completed`.
- Update QA/report test counts and caveats.

## Verification

Run the full ticket commands again. Do not download a real model, modify
dependencies/version/MCP tools, commit, push, publish, touch SVGs, or touch
`pending-learning-proposals.md`.
