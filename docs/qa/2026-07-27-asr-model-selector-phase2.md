# QA Checklist: ASR Model Selector Phase 2

**Date**: 2026-07-27
**Scope**: Three-model allowlisted selector in `setup` flow
**PRD**: `docs/asr-model-selector-prd.md`
**Task**: ASR-SELECT-02

## CLI Setup Flow

- [x] `setup` help text mentions ASR installation
- [x] No/Enter skip ASR without reaching model selector
- [x] Yes shows three model choices with sizes and recommended marker
- [x] Enter defaults to small
- [x] Numeric 1/2/3 selects corresponding model
- [x] Name tiny/base/small selects corresponding model (case-insensitive)
- [x] Invalid input re-prompts without starting installation
- [x] `setup` passes selected model key to installer

## Doctor Output

- [x] `doctor --json` includes `asr.model` field (string or null)
- [x] `asr.model` is null when no model installed
- [x] `asr.model` is the key (tiny/base/small) when ready
- [x] `doctor` text output shows model when installed
- [x] Doctor credential exit codes unchanged (ASR is informational only)
- [x] Doctor JSON contains no credentials, paths, or secrets

## Model Validation

- [x] Only tiny/base/small accepted
- [x] Invalid model key returns error before any filesystem mutation
- [x] Model resolution is case-insensitive
- [x] Allowlist is a literal `as const` source; `AsrModelKey` and `AsrModelSpec` are derived from `(typeof ASR_MODEL_SPECS)[number]`

## State Compatibility

- [x] Phase 1 small state remains readable as ready
- [x] State version stays at 1
- [x] Phase 1 ASR_PINNED_MODEL/REVISION aliases preserved

## Idempotency and Switching

- [x] Same-model ready state skips reinstall
- [x] Different-model ready state triggers reinstall
- [x] Failed install leaves no ready marker
- [x] Partial files preserved for resume

## Build and Package

- [x] `npm run build` passes
- [x] Focused tests pass (158 asr-installer + cli)
- [x] `npm test` passes (570 tests)
- [x] `npm pack --dry-run` shows 148 files, no unexpected additions
- [x] No new dependencies, commands, or MCP tool changes

## Documentation

- [x] Bilingual README updated
- [x] Bilingual client-setup updated
- [x] Bilingual CHANGELOG updated
- [x] Codemap updated
- [x] Phase 2 still states "no transcription"

## Security

- [x] No credentials in doctor output
- [x] No credentials in ASR state or model prompts
- [x] Child env filtering preserved (BILIBILI_SESSDATA, BILIBILI_BILI_JCT, BILIBILI_DEDEUSERID, PYTHONPATH, PYTHONHOME stripped)
- [x] No shell interpolation in subprocess calls
