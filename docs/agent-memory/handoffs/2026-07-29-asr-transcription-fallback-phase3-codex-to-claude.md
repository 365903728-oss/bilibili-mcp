# Codex To Claude Handoff: ASR Transcription Fallback Phase 3

## Objective

Implement `ASR-TRANSCRIBE-03` against the current dirty worktree. Continue
through deterministic tests, scoped bilingual documentation, QA, codemap, and a
complete Claude report. Do not stop at a proof of concept.

## Current State

- Source snapshot is detached at
  `ab4dd02854f0483fc7668c713523b4be77de6cc7` with user-owned uncommitted
  CLI/README/ASR Phase 1/2/QA/research/memory changes.
- Build passes; focused 169, full 570, and pack 148 baseline pass.
- ASR Phase 1/2 is ready in source but the current machine reports
  `asr.status: not_installed`.
- Live redacted first-party research is recorded in
  `docs/research/2026-07-29-asr-transcription-fallback-phase3.md`.
- No runtime file has been edited for Phase 3 yet.

## Files To Inspect

- `AGENTS.md`, `CLAUDE.md`
- Phase 3 PRD, research, ticket, and QA
- Phase 1/2 PRDs, ASR modules, tests, reports, reviews, and QA
- transcript, Part/CID, video API, HTTP, schema/handler/error/logger modules
- relevant tests and bilingual docs

## Files To Edit

Use only the ticket's expected edit set. Prefer two new deep modules:

- `src/bilibili/playback.ts`
- `src/asr/transcription.ts`

Keep fallback orchestration in `src/bilibili/subtitle.ts`. Do not create a
general downloader, process framework, scheduler, or public ASR tool.

## Required Capability

- Read and use `vitest`, `secret-scanning`, and `codebase-design` from the
  Claude skill root.
- Invoke `test-baseline-builder` for deterministic test design.
- Invoke `risk-reviewer` after implementation; if it stalls, record that and
  perform the same bounded top-level review.
- Do not invoke Superpowers or create an agent tree.

## Constraints

- Freeze every public behavior and numerical limit from the PRD.
- ASR only from confirmed empty subtitle list/no selection/empty body.
- Existing Cookie/network/HTTP/timeout/parse/anti-bot errors never invoke ASR.
- Cookie goes to the Bilibili API only, never CDN/Python.
- Signed URLs stay in memory, are never logged or returned, and every redirect
  is revalidated.
- One active ASR, no queue.
- Managed ready venv/model only; Python argv, `-I`, `shell: false`, filtered
  synthetic env in tests.
- Unique OS temp directory; validated `finally` cleanup on every path.
- No real network, Cookie, Python, model, or audio in automated tests.

## Execution Steps

1. Add failing tests for gating, playback parsing/selection, media limits and
   redaction, readiness/argv/env/protocol/timeout/kill, cleanup, concurrency,
   fallback precedence, MCP schema/parity/order, and stdio.
2. Implement the minimum code behind the two internal module interfaces.
3. Reuse one transcript segment-result path for subtitle and ASR behavior.
4. Add the smallest domain error/guidance set needed by the PRD.
5. Update the relevant bilingual README/setup/tool-reference/changelog
   sections, QA, codemap, and ticket status.
6. Run focused and full verification, secret scan, and risk review; repair
   same-scope blockers.
7. Write
   `docs/agent-memory/handoffs/2026-07-29-asr-transcription-fallback-phase3-claude-report.md`.

## Verification Commands

```powershell
npm run build
npx vitest run tests/asr-installer.test.ts tests/asr-transcription.test.ts tests/bilibili-playback.test.ts tests/cli.test.ts tests/bilibili-transcript.test.ts tests/bilibili-video-api.test.ts tests/server-tools.test.ts tests/server-handler-sanitization.test.ts tests/server-error-next-steps.test.ts tests/mcp-server-smoke.test.ts
npm test
npm pack --dry-run --json --ignore-scripts
npm audit --omit=dev
git diff --check
```

Also run built doctor JSON, no-argument stdio, exact ten-tool discovery, one
representative public tools/call, package manifest leak checks, and a scoped
secret scan. Do not run a live model download or modify the user's model.

## Acceptance Criteria

All PRD, ticket, and QA items must be satisfied or accurately marked with a
specific untested boundary. `content[0].text` and `structuredContent` must
remain identical for every successful transcript source.

## Things Not To Change

No commit/stage/push/PR/tag/version/publish/release, SDK v2/protocol migration,
HTTP transport, Tasks/MRTR/annotations/icons, Smithery, dependency, package
workflow, model allowlist, GPU, global pip, permanent media, `dist/`, SVGs, or
learning-proposal promotion.

## Stop And Report If

Stop only for the ticket's material conditions: safe first-party audio-only
retrieval proves impossible, a new public tool is required, a real secret is
found, or new destructive/release/global-runtime authority is needed.

## Expected Claude Report

Use the project report template. Include files changed, commands and exact
counts, skipped checks, cleanup/schema/stdio/pack/audit/secret evidence,
subagent/skill outcomes, live ASR boundary, unresolved risks, and Harness
Artifacts status.
