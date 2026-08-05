# Codex Review: Optional ASR Model Installation Phase 1

## Status

Changes requested. The current test suite is green, but two blocking defects
would make the real managed installation contract unreliable.

## Blocking Findings

### 1. Download and verification use the system interpreter

`createVenv()` installs `faster-whisper==1.2.1` through the managed venv's pip,
but `runAsrInstallation()` passes the originally discovered system Python to
`downloadModel()` and `verifyModel()`. A normal machine without a global
`faster-whisper` install will then fail to import `huggingface_hub` or
`faster_whisper`.

Required repair:

- Derive the managed venv Python executable after venv creation.
- Run pip, model download, and model verification through that managed
  interpreter. Prefer `venvPython -m pip` instead of invoking a standalone pip
  executable.
- Tests must prove all post-venv operations use the venv interpreter.

### 2. Doctor can report false-ready state

`readAsrState()` validates only `state.json`. Deleting the venv or model files
still leaves `doctor` reporting `ready`, contrary to the PRD's explicit
"versioned state plus expected venv/model files" rule.

Required repair:

- Readiness must require the exact state schema and pinned values, the managed
  venv Python executable, and the fixed model's required runtime files
  (`model.bin`, `config.json`, `tokenizer.json`, and `vocabulary.txt`).
- A valid state file with missing managed artifacts must be `incomplete`.
- Keep the check local and do not load the model or expose absolute paths.
- Add deterministic tests for each missing-artifact case.

## Same-Scope Required Corrections

- Support the ordinary Windows Python Launcher route (`py -3`) without
  converting command arguments into a shell string. Represent a Python command
  as executable plus prefix arguments if needed. `BILIBILI_ASR_PYTHON` remains
  an executable-only override.
- Require an override version probe to exit successfully, not merely print a
  Python-looking string.
- Pass model paths/IDs/revisions to Python through argv rather than embedding
  the path in generated source.
- Match completion markers as exact output lines, not arbitrary substrings.
- Make a verified ready installation idempotent: rerunning must not redownload
  or fail while replacing an existing state file.
- Make atomic state replacement work on Windows and clean the temporary file if
  either writing or replacement fails. Never delete venv/model directories.
- When a user explicitly chooses Yes and installation fails, the `setup`
  command must finish nonzero while preserving configured credentials and
  partial ASR files.
- Add setup tests proving:
  - default No does not call the ASR runner;
  - already configured credentials still reach the ASR prompt;
  - failed opted-in installation sets a nonzero result;
  - success does not set a failure result.
- Keep subprocess diagnostic buffers bounded and do not forward the three
  Bilibili credential environment variables to Python/pip/model subprocesses.
- Show a few bounded installation stages to the user so a roughly 486 MB
  download does not look hung.

## Documentation Corrections

- The report must no longer claim risk-reviewer was not invoked if it was.
- Update README/README_EN or the bilingual setup guides so users can discover
  the optional installer, its default-No behavior, Python 3.9+ prerequisite,
  fixed model/size, user-scoped storage, no system FFmpeg requirement, and the
  Phase 1 limitation (installation only, no transcription fallback yet).
- Remove or qualify the current blanket README claim that the project performs
  no ASR/model download; the MCP transcript tool still does not perform ASR,
  but `setup` now can download a model after explicit opt-in.

## Verification

Run the complete ticket commands again. Do not perform a real model download,
commit, push, tag, publish, or touch unrelated existing changes.
