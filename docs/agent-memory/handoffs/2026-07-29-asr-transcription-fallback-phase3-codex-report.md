# Codex Completion Report: ASR Transcription Fallback Phase 3

## Summary

Implemented and reviewed the complete default-off ASR fallback for
`get_video_transcript`. Native subtitles remain first priority; only definite
subtitle absence may fetch temporary audio for one resolved Part/CID and run the
already-ready project-managed faster-whisper model. All expensive and
security-sensitive boundaries are explicit and bounded.

## Files Changed

Runtime:

- `src/bilibili/playback.ts`
- `src/asr/transcription.ts`
- `src/bilibili/subtitle.ts`
- `src/bilibili/types.ts`
- `src/server/tool-schemas.ts`
- `src/server/tool-handlers.ts`
- `src/utils/errors.ts`
- `src/utils/error-guidance.ts`

Tests:

- `tests/asr-transcription.test.ts`
- `tests/bilibili-playback.test.ts`
- `tests/asr-installer.test.ts`
- `tests/bilibili-transcript.test.ts`
- `tests/server-tools.test.ts`
- `tests/server-handler-sanitization.test.ts`
- `tests/server-error-next-steps.test.ts`
- `tests/mcp-server-smoke.test.ts`

Documentation and project memory:

- bilingual README, setup guide, tool reference, and changelog files
- Phase 3 PRD, research note, task ticket, handoff, QA checklist, and this report
- `active-work.md`, `project-facts.md`, `decisions.md`,
  `lessons-learned.md`, `codemap.md`, `handoff-log.md`,
  `verification-log.md`, and `harness-eval.md`

## Commands Run

- `npm run build`
- exact 10-file Phase 3 focused Vitest command
- `npm test`
- `npm test -- tests/asr-installer.test.ts tests/asr-transcription.test.ts`
- `npm pack --dry-run --json --ignore-scripts`
- `npm audit --omit=dev --json`
- built CLI help, version, and `doctor --json` probes
- scoped high-confidence secret scan and package-boundary scan
- ASR OS-temp residue inventory before and after test-fixture repair
- bilingual UTF-8/link/parity checks and `git diff --check`

## Results

- Build: PASS.
- Focused Phase 3: 10 files / 356 tests PASS.
- Full regression: 29 files / 629 tests PASS.
- Post-cleanup ASR installer/transcription: 2 files / 126 tests PASS; zero
  `bilibili-mcp-asr-*` temp directories remain.
- Package: 156 files, 159,670 bytes packed, 630,098 bytes unpacked; no tests,
  QA, research, agent memory, `.env`, model, venv, state, audio, or temp path.
- CLI: help/version PASS; doctor is parseable and reports
  `asr.status: not_installed`, `asr.model: null` without secret values.
- MCP: exactly ten tools and original order; public JSON-clean legacy stdio
  initialize/list/representative-call PASS; text/structured parity PASS.
- Security: 282 scoped text files scanned. No private key, GitHub/npm/AWS token,
  or real Bilibili credential found. Three classified fixtures remain: one
  synthetic signed media URL and two synthetic CLI credential assignments.
  `gitleaks` is not installed.
- Audit: two known moderate production dependency nodes, zero high/critical.
  The reachable project is stdio-only and does not import Hono static serving;
  dependency remediation requires the explicitly excluded SDK/Hono major.

## Diff Notes

- `fallback_to_asr` is optional and defaults to false.
- Native subtitles win; errors never masquerade as absence.
- Playback accepts only one resolved BVID/CID, authenticated first-party API
  metadata, and Bilibili-specific HTTPS audio CDN hosts. CDN requests receive no
  Cookie.
- Runtime uses only ready managed paths, CPU INT8, `-I`, argv, `shell: false`,
  ignored stdin, a small allowlisted environment, strict NDJSON, hard resource
  limits, one active/no-queue concurrency, and guarded `finally` cleanup.
- ASR segments reuse the existing transcript transformation and evidence-link
  pipeline and return `data_source: "asr"`.

## Risks Or Skipped Checks

- Live ASR E2E was not run because no ready model exists. The user prohibited a
  large model download or selection change for acceptance.
- Codex Security app setup timed out twice before submission, so no independent
  app scan result is claimed. Top-level risk review used the handoff-authorized
  fallback and repaired all findings listed below.
- Paseo was unavailable/stale and was not restarted without user approval;
  therefore no Claude implementation agent or Claude subagent report exists.
- Production audit retains two moderate transitive nodes pending a separate
  authorized SDK/Hono major migration.

## Review Findings Repaired

- Missing/malformed DASH no longer looks like a valid empty audio set.
- Shared/generic CDN domains were narrowed to provider-specific Bilibili hosts.
- Redirect bodies are canceled and every hop is revalidated.
- Streaming writes no longer assume a single low-level write consumes a chunk.
- Custom ports, unsafe backup candidates, unsafe temp destinations, symlinked
  cleanup targets, blank protocol lines, and invalid output shapes fail closed.
- Phase 1/2 test fixtures now remove their containing temp directories; 119
  historical project-prefixed test directories were safely removed, then a
  126-test rerun left zero residue.

## Harness Artifacts

- Task ticket: used and accepted.
- Research note: created from first-party Bilibili behavior and official
  faster-whisper/Hugging Face material.
- QA checklist: completed with automated and live-boundary evidence.
- Codemap: updated for playback, transcription, shared transcript flow, and
  public stdio coverage.
- Harness security: reviewed; no secret or trust-boundary rule weakened.
- Harness eval: updated for Phase 3 orchestration and review outcomes.

Capabilities used: `product-requirements`, `system-design`, `codebase-design`,
`vitest`, `secret-scanning`, and `bilibili-mcp-memory`. The `code-review` skill
was inspected but not invoked because its mandatory parallel-agent workflow
conflicted with this repository's bounded single-agent/no-agent-tree rules.
The planned Claude `test-baseline-builder` and `risk-reviewer` subagents were
not available without Paseo; equivalent deterministic test design and top-level
risk review were completed directly.

## Decision Points

None remain inside Phase 3. A live ASR smoke becomes appropriate only when the
user already has a ready managed model. SDK v2/protocol modernization, audit
dependency remediation, Git delivery, versioning, and publication remain
separate authorization gates.

## Final Scope Confirmation

No commit, stage, push, pull request, tag, version bump, npm publish, GitHub
Release, SDK/protocol migration, Smithery restoration, model download/switch,
GPU/global-Python work, persistent audio, or learning-proposal promotion was
performed.
