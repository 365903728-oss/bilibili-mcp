# Research Topic

- Topic: Phase 1 faster-whisper runtime and model installation
- Date: 2026-07-27
- Owner: Codex
- Related task: `docs/asr-model-install-prd.md`
- Refresh before: implementation changes model/runtime versions or the next release

## Question

What current upstream requirements and immutable artifacts should the first
optional ASR installer use?

## Context

The project needs a default-off local model installation path without adding a
global Python mutation, system FFmpeg prerequisite, npm runtime dependency, or
unbounded moving model target.

## Sources

| Source | Type | Date checked | Notes |
|---|---|---|---|
| [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper/tree/ed9a06cd89a93e47838f564998a6c09b655d7f43) | official source | 2026-07-27 | Default branch commit inspected with `gh`; README requirements checked. |
| [faster-whisper v1.2.1](https://github.com/SYSTRAN/faster-whisper/releases/tag/v1.2.1) | official release | 2026-07-27 | Live GitHub release metadata. |
| [Systran/faster-whisper-small](https://huggingface.co/Systran/faster-whisper-small/tree/536b0662742c02347bc0e980a01041f333bce120) | official model repo/API | 2026-07-27 | CTranslate2 model, MIT, immutable revision and file sizes. |
| PyPI `pip index versions faster-whisper` | registry CLI output | 2026-07-27 | Latest and installed version both 1.2.1. |

## Findings

- Upstream requires Python 3.9 or newer and documents
  `pip install faster-whisper`.
- System FFmpeg is not required; faster-whisper decodes through PyAV, which
  bundles the relevant FFmpeg libraries.
- CPU INT8 is an upstream-supported loading mode.
- Current faster-whisper release/latest is 1.2.1.
- `Systran/faster-whisper-small` revision
  `536b0662742c02347bc0e980a01041f333bce120` contains six files totaling
  486,215,847 bytes; `model.bin` is 483,546,902 bytes.
- The model repo is CTranslate2 format and MIT licensed.

## Applicability To This Project

Applies:

- Pin runtime and model revision for a deterministic first installer.
- Use a project-managed user venv and CPU INT8 verification.
- Do not add a system FFmpeg prerequisite.

Does not apply:

- CUDA library requirements, GPU selection, batched transcription benchmarks,
  and automatic transcription are outside Phase 1.

## Decision Impact

- Add no npm runtime dependency.
- Derive all ASR paths below `~/.bilibili-mcp/asr/`.
- Use Node standard-library child-process APIs with argument arrays.
- Keep model download explicitly opt-in and display the approximate model size.

## Risks And Unknowns

- Python executable discovery differs by OS and must be deterministically tested.
- Runtime wheels may not exist for every future Python/platform combination;
  installation failure must remain recoverable and must not mark ASR ready.

## Follow-Up

- [ ] Refresh upstream versions and model revision before publication.
- [ ] Re-evaluate allowed models when implementing Phase 2 selection.
