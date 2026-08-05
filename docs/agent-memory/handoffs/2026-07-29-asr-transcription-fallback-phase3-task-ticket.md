# Task Ticket: ASR Transcription Fallback Phase 3

- ID: ASR-TRANSCRIBE-03
- Title: Add bounded managed ASR fallback to video transcript
- Status: `accepted`
- Owner: Codex direct implementation and review; Paseo unavailable and not restarted
- Source: user-authorized complete-MCP Goal
- Parent PRD: `docs/asr-transcription-fallback-prd.md`
- Blocking tickets: ASR-INSTALL-01, ASR-SELECT-02
- Blocked by: none

## Objective

Add explicit, default-off ASR fallback to `get_video_transcript` for one
definitively subtitle-less Part/CID, using the existing ready managed runtime
and model, transient bounded audio, strict child output, complete cleanup, and
the existing transcript feature pipeline.

## Scope

In scope:

- First-party playurl parsing and deterministic audio-only selection.
- Bounded HTTPS media download into one unique temp directory.
- Managed faster-whisper CPU INT8 child process and strict NDJSON validation.
- One-active/no-queue concurrency gate.
- Transcript fallback precedence, schema, errors, tests, bilingual docs, QA,
  report, codemap, and project memory inputs.

Out of scope:

- New tool, hidden ASR in info, runtime/model installation during MCP,
  persistent media, multiple Parts, GPU, new dependency, version/release/Git,
  SDK/protocol/transport migration, or learning-proposal promotion.

## Files To Inspect Or Edit

Expected edit:

- `src/bilibili/playback.ts` (new)
- `src/asr/transcription.ts` (new)
- `src/bilibili/subtitle.ts`
- `src/bilibili/types.ts`
- `src/server/tool-schemas.ts`
- `src/server/tool-handlers.ts`
- `src/utils/validation.ts`
- `src/utils/errors.ts`
- `src/utils/error-guidance.ts`
- `src/utils/logger.ts`
- focused deterministic tests
- relevant bilingual README/setup/tool-reference/changelog sections
- Phase 3 QA/report and `docs/agent-memory/codemap.md`

Do not touch:

- `dist/`, package version/dependencies/workflow, model allowlist/revisions,
  Smithery, SVGs, SDK/transport, unrelated tools, or
  `pending-learning-proposals.md`.

## Required Capabilities

- Skills: `vitest`, `secret-scanning`, `codebase-design`
- Subagents: `test-baseline-builder` for test design; `risk-reviewer` after
  implementation
- CLI: build, focused/full Vitest, pack, audit, diff, doctor, stdio, public
  protocol smoke, and scoped secret/manifest checks

## Execution Steps

1. Add failing deterministic tests for all QA gates.
2. Implement the playback module with existing auth/API request ownership,
   strict response validation, and deterministic selection.
3. Implement the transcription module with readiness, limits, URL validation,
   transient download, managed child protocol, kill/close, concurrency, and
   validated cleanup.
4. Refactor only the local transcript segment-result seam needed for native and
   ASR to share formatting/range/search/link behavior.
5. Extend schema/handler/types/errors without changing tool count/order or
   success parity.
6. Update scoped bilingual docs, codemap, QA, and Claude report.
7. Run secret and risk reviews, repair same-scope blocking findings, then run
   all final gates.

## Acceptance Criteria

- [x] Every PRD and QA gate is directly evidenced.
- [x] Existing false/omitted behavior performs zero ASR side effects.
- [x] Native subtitles remain first priority.
- [x] Errors are never reclassified as no subtitles.
- [x] Signed URLs, Cookies, child env, and private paths never escape.
- [x] Cleanup is complete and deletion targets are validated.
- [x] All ten tools, stdio cleanliness, and structured/text parity remain.
- [x] No dependency, version, release, Git, model, or protocol change occurs.

## Verification

Use the complete command matrix in the Phase 3 QA checklist. Automated tests
must not use real Cookie, network, Python, audio, or model files.

## Risks And Rollback

- Risk: playback response/CDN behavior changes. Fail closed and refresh the
  dated research before release.
- Risk: CPU work is expensive. One active call, no queue, duration/process
  limits.
- Rollback: remove the two new modules and the optional schema/handler/fallback
  wiring. Never delete user-managed model/venv/state data.

## Stop And Report Conditions

Stop if safe audio-only retrieval is impossible, a new public tool is required,
a real secret is found, or completion requires model download, global runtime
mutation, persistence, SDK migration, release, or destructive user-data work.
Ordinary defects and failing tests remain same-scope repair work.
