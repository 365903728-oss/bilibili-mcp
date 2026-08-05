# QA Checklist: ASR Transcription Fallback Phase 3

**Date**: 2026-07-29
**Scope**: Explicit `get_video_transcript` ASR fallback
**PRD**: `docs/asr-transcription-fallback-prd.md`
**Task**: ASR-TRANSCRIBE-03

## Preconditions

- [x] Dirty working tree and commit `ab4dd02854f0483fc7668c713523b4be77de6cc7` recorded.
- [x] Package remains `1.10.1` Unreleased.
- [x] Phase 1/2 artifacts and all user changes preserved.
- [x] Live playback probe was public, read-only, no-Cookie, and redacted.
- [x] `doctor --json` reports `asr.status: not_installed`; no model download is
      authorized for QA.

## Pre-Edit Baseline

- [x] Build: PASS after using the version-matched existing dependency install.
- [x] Focused tests: 169 passed.
- [x] Full tests: 570 passed in 27 files.
- [x] Package dry run: 148 files, 143,620 bytes.
- [x] `git diff --check`: PASS.
- [x] Caveat recorded: the new worktree initially lacked `node_modules`, and
      npm 25 reports the current package/lock pair missing `@colors/colors`;
      the lockfile was not changed during baseline.

## Request Gating

- [x] Omitted/false flag causes zero ASR work.
- [x] Native subtitle success causes zero ASR work.
- [x] Empty subtitle list verifies login before ASR.
- [x] Expired credentials never invoke ASR.
- [x] HTTP/timeout/parse/anti-bot failures never invoke ASR.
- [x] Definitive no-subtitle invokes ASR once for the resolved CID.
- [x] `get_video_info` never invokes ASR.

## Playback And Audio

- [x] Exact BVID/CID and authenticated playurl request are tested.
- [x] Lowest-bandwidth-then-ID selection is deterministic.
- [x] Empty versus malformed playback responses are distinguished.
- [x] HTTPS/CDN validation, redirects, timeout, status, byte and duration
      limits are tested.
- [x] CDN download receives no Cookie.
- [x] Signed URLs and private query values are absent from diagnostics.
- [x] Partial files are never treated as complete.

## Managed Runtime

- [x] Not-installed/incomplete/ready gates are tested.
- [x] Exact managed venv Python and model directory come from readiness state.
- [x] Windows/POSIX argv, `-I`, `shell: false`, ignored stdin, and filtered
      synthetic environment are tested.
- [x] Meta/segment/done NDJSON success is tested.
- [x] Nonzero exit, spawn error, timeout/kill, overflow, malformed JSON,
      invalid ordering/timestamps/text/count, and missing done are tested.
- [x] Only one active transcription is allowed; a second receives busy.

## Cleanup

- [x] Temp directory is removed after success.
- [x] Temp directory and partial audio are removed after every download,
      process, timeout, parse, and validation failure.
- [x] Unsafe cleanup targets are rejected.
- [x] Managed model, venv, state, project, and home paths are never deleted.

## Transcript And MCP

- [x] `data_source: "asr"` is in types and schema.
- [x] Plain/timestamp/range/query/context/source/timestamp URL results match
      native segment behavior.
- [x] Both-fallback precedence is deterministic.
- [x] ASR errors are text-only and bilingual.
- [x] Text JSON equals `structuredContent`.
- [x] Ten tools and their order are unchanged.
- [x] Public wire-level stdio list/call smoke remains JSON-clean.

## Final Verification

```powershell
npm run build
npx vitest run tests/asr-installer.test.ts tests/asr-transcription.test.ts tests/bilibili-playback.test.ts tests/cli.test.ts tests/bilibili-transcript.test.ts tests/bilibili-video-api.test.ts tests/server-tools.test.ts tests/server-handler-sanitization.test.ts tests/server-error-next-steps.test.ts tests/mcp-server-smoke.test.ts
npm test
npm pack --dry-run --json --ignore-scripts
npm audit --omit=dev
git diff --check
```

- [x] Built `doctor --json` is parseable, local-only, and secret-free.
- [x] Built no-argument CLI stdio is clean.
- [x] Public `tools/list` reports exactly ten tools.
- [x] Representative public `tools/call` succeeds.
- [x] Pack contains no model, venv, audio, temp, Cookie, or private path.
- [x] Scoped secret scan covers code, tests, docs, handoffs, QA, and manifest.
- [x] UTF-8 bilingual docs contain no new mojibake.

## Live ASR

- [x] Run only if an already-ready model exists.
- [x] Current boundary: not run because ASR is not installed; no large model
      download or selection change performed.

## Result

- Overall result: `pass with documented live-smoke and audit caveats`
- Automated evidence: build PASS; 10 focused files / 356 tests PASS; 29 files /
  629 full tests PASS; 156-file package dry run; 126 ASR install/transcription
  tests PASS with zero post-test ASR temp directories.
- Blocking issues: none
- Non-blocking caveat: live full audio/transcription remains unavailable until
  a ready user-managed model already exists
- Residual audit caveat: two known moderate production dependency nodes, zero
  high/critical; remediation requires the separately excluded SDK/Hono major.
- Codemap update status: complete
- Research note: `docs/research/2026-07-29-asr-transcription-fallback-phase3.md`
