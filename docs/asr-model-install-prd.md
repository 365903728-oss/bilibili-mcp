# Product Requirements Document: Optional ASR Model Installation

**Version**: 1.0
**Date**: 2026-07-27
**Author**: Codex using `product-requirements`
**Quality Score**: 92/100

## Executive Summary

Add an opt-in local installation path for speech-to-text support. The first
phase offers only two choices: skip ASR, or install the recommended
`Systran/faster-whisper-small` model. It reuses the existing CLI and keeps all
runtime/model files outside the npm package and project checkout.

This phase proves installation and readiness only. Automatic audio retrieval,
transcription fallback, and the multi-model selector follow after this
installer contract is verified.

## Problem Statement

Videos without Bilibili CC/AI subtitles currently return
`SUBTITLE_UNAVAILABLE`. Users want a local fallback, but forcing Python,
runtime packages, and roughly 486 MB of model weights on every MCP install
would make the default package heavier and less predictable.

The solution is an explicit, default-off setup choice that installs a fixed,
verified model into a user-scoped managed environment.

## Success Metrics

- Choosing No performs no ASR subprocess, network request, or filesystem write.
- Choosing Yes creates a managed Python environment, installs the pinned
  runtime, downloads the pinned model snapshot, loads it successfully on CPU
  INT8, then records ready state.
- `doctor --json` reports ASR state without network access, absolute paths,
  credentials, or private values.
- Existing MCP tools and stdio behavior remain unchanged.
- Build, focused Vitest, full Vitest, CLI smoke, and package dry-run pass.

## Users

- Agent-assisted user: gives the Agent control of client configuration but
  performs the interactive setup locally.
- Manual user: runs the same CLI and needs clear prerequisites, progress, and
  recovery guidance.

## User Stories

### Optional installation

As a user, I want setup to default to no ASR download so the ordinary MCP
installation stays lightweight.

Acceptance:

- [x] Prompt is explicit and defaults to No.
- [x] No selection leaves existing setup behavior unchanged.
- [x] Re-running setup with credentials already configured still reaches the
      optional ASR question.

### Fixed recommended model

As a user with no-subtitle videos, I want one recommended local model installed
without making model-quality decisions yet.

Acceptance:

- [x] Phase 1 installs only `Systran/faster-whisper-small`.
- [x] Runtime is pinned to `faster-whisper==1.2.1`.
- [x] Model revision is pinned to
      `536b0662742c02347bc0e980a01041f333bce120`.
- [x] Python environment and model files live under
      `~/.bilibili-mcp/asr/`, not global Python or the project checkout.
- [x] Interrupted installs can be rerun; readiness is recorded only after a
      successful model load.

### Local diagnosis

As a user or Agent, I want a secret-free local status so I know whether ASR is
not installed, ready, or incomplete.

Acceptance:

- [x] `doctor --json` adds a stable `asr` object.
- [x] Overall credential readiness and exit-code semantics remain unchanged
      because ASR is optional.
- [x] Doctor performs no network or model load.

## Functional Requirements

1. Reuse the existing `setup` CLI command; do not add a second installer.
2. Check Python 3.9+ without shell interpolation. Allow an explicit
   `BILIBILI_ASR_PYTHON` executable override.
3. Create a private user-scoped venv and install the pinned runtime inside it.
4. Download the pinned model snapshot from Hugging Face and load it with
   `device="cpu"` and `compute_type="int8"`.
5. Save a versioned, non-secret state file atomically only after success.
6. Preserve partial files after failure so a retry can resume; report a clear
   nonzero result without deleting user data.
7. Document that system FFmpeg is not required by faster-whisper because PyAV
   supplies decoding libraries.

## Out Of Scope For Phase 1

- Model selector or custom model IDs.
- Automatic ASR fallback in `get_video_transcript`.
- Bilibili audio retrieval or persistent audio files.
- GPU/CUDA detection and selection.
- Bundled Python distribution.
- Model removal, migration, or background updates.
- New MCP tools or schema changes.

## Phasing

- Phase 1: fixed `small` opt-in install, readiness state, doctor integration.
- Phase 2: bounded model selector using an allowlist and the Phase 1 installer.
- Phase 3: explicit no-subtitle transcription fallback and temporary-audio
  lifecycle.

## Risks

| Risk | Mitigation |
|---|---|
| Python unavailable | Detect first and show a clear Python 3.9+ prerequisite; do not mutate PATH. |
| Download interrupted | No ready marker until verification; preserve resumable files. |
| Shell injection/path errors | Use `execFile`/`spawn` argument arrays only. |
| False-ready status | Require versioned state plus expected venv/model files. |
| Default install becomes heavy | No is the default and triggers no ASR work. |
| Public package mismatch | Keep this Unreleased until CLI, docs, Node engine, tests, and package verification ship together. |
