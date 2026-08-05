# Product Requirements Document: ASR Model Selector Phase 2

**Version**: 1.0
**Date**: 2026-07-27
**Author**: Codex using `product-requirements`
**Quality Score**: 94/100

## Executive Summary

Extend the existing default-off ASR setup flow with one small allowlisted model
selector. After choosing Yes, the user selects `tiny`, `base`, or `small`;
pressing Enter selects the recommended `small` model.

This phase reuses the Phase 1 managed Python environment, download, CPU INT8
verification, state, and doctor flow. It does not add transcription or custom
model IDs.

## Problem Statement

Phase 1 always installs `faster-whisper-small`. Users with limited storage or
CPU need a smaller option, but an open-ended model browser would complicate
validation, support, and installation.

The solution is a three-model multilingual allowlist with pinned revisions and
one recommended default.

## Success Metrics

- Choosing No still performs no ASR subprocess, network, or filesystem work.
- Choosing Yes shows exactly three models and defaults to `small`.
- Each valid choice reaches the existing installer with the correct pinned
  repository, revision, and displayed approximate size.
- Invalid input is rejected locally and re-prompted without starting install.
- An existing valid Phase 1 `small` state remains ready and idempotent.
- Switching models replaces the active selection and writes ready state only
  after CPU INT8 verification.
- Build, focused Vitest, full Vitest, CLI smoke, package dry-run, and scoped
  secret review pass.

## Users

- Manual user who wants a clear storage tradeoff without researching models.
- Agent-assisted user who leaves interactive local choices and credentials to
  the person operating the terminal.

## User Stories And Acceptance Criteria

### Choose a model

As a user who opted into ASR, I want a short list with one recommended default.

- [x] Show `tiny` (~78 MB), `base` (~148 MB), and `small` (~486 MB).
- [x] Mark `small` as recommended and select it on Enter.
- [x] Accept `1`, `2`, `3`, or the corresponding model name.
- [x] Re-prompt invalid input without invoking the installer.

### Install the selected model

As a user, I want the selected model to use the already verified Phase 1
installation path.

- [x] Keep `faster-whisper==1.2.1`, Python 3.9+, user-scoped venv, CPU INT8,
      isolated Python mode, filtered child environment, and no shell.
- [x] Pass only an allowlisted model identifier and immutable revision to
      `snapshot_download`.
- [x] Keep one active model in the existing managed model directory.
- [x] Preserve partial files and never leave a false ready state after failure.
- [x] A same-model reinstall remains idempotent; selecting another model runs
      installation and records the new choice only after verification.

### Diagnose the active model

As a user or Agent, I want local doctor output to identify the ready model.

- [x] `doctor --json` keeps `asr.status` and adds a non-secret model key or
      `null`.
- [x] ASR remains informational and does not change credential exit codes.
- [x] Existing Phase 1 `small` state remains readable without migration.

## Functional Requirements

1. Reuse the existing `setup` command and Phase 1 installer.
2. Define the allowlist once in the ASR state module.
3. Resolve and validate the selected key before any installation mutation.
4. Keep state schema version 1 because the persisted fields already contain
   model repository and revision.
5. Validate ready state against any current allowlisted repository/revision.
6. Keep one active model directory; do not add model management commands.
7. Update bilingual README, setup guide, changelog, codemap, QA, and report.

## Out Of Scope

- Custom Hugging Face repository IDs or revisions.
- `medium`, `large`, English-only, distilled, GPU, or CUDA choices.
- Keeping several installed models or switching at transcription time.
- Model removal, migration UI, background update, or download progress bar.
- Audio retrieval, transcription, or automatic subtitle fallback.
- New MCP tools or schema changes.

## Risks

| Risk | Mitigation |
|---|---|
| Invalid or injected model identifier | Resolve only local allowlist keys before filesystem or subprocess work. |
| Phase 1 state becomes unreadable | Keep schema v1 and include the exact existing `small` repository/revision in the allowlist. |
| Failed model switch | Remove the old ready marker before mutation; preserve partial files and report `incomplete`. |
| Concurrent setup runs | Document one installer process at a time; add locking only if real usage requires it. |
| Documentation implies transcription exists | State explicitly that Phase 2 selects/installs only. |

## Phasing

- Phase 1: fixed recommended model installation and readiness — completed.
- Phase 2: three-model allowlisted selector — this document.
- Phase 3: explicit no-subtitle transcription fallback and temporary-audio
  lifecycle.
