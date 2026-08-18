# Task Ticket: Roadmap Subtitle Integrity And Scriptable Setup

- ID: `ROADMAP-2026-08-18-INTEGRITY-SETUP`
- Title: Complete AI subtitle integrity and non-TTY setup gaps
- Status: `ready`
- Owner: `Claude Code`
- Source: user objective, GitHub Issue #40, local `ROADMAP.md`
- Parent PRD: `docs/subtitle-integrity-and-scriptable-setup-prd.md`
- Blocking tickets: none
- Blocked by: none

## Objective

Prevent every selected `ai-zh` track from returning before deterministic
integrity assessment, route unusable content through existing explicit
fallbacks, and add a credential-safe non-interactive setup mode.

## Scope

In scope:

- AI stability, high-confidence language, and high-confidence title-topic
  assessment in transcript and video-info.（Amended 2026-08-18 by Codex
  blocker review: title-topic lexical overlap is removed as a hard rejection
  gate — stable same-language semantic mismatch is an accepted limitation
  controlled by `force_asr` / `exclude_ai_subtitles`; see PRD v1.1.）
- Default-off ASR/description behavior already frozen by Issue #40.
- `setup --non-interactive [--asr-model tiny|base|small]` using existing
  credential sources and installer.
- Public-interface regressions, bilingual docs/changelog, QA/report/memory.

Out of scope:

- New dependencies, LLM/remote semantics, configurable thresholds, Human
  Subtitle validation, stdin/argv credentials, new models, Git/release actions.

## Files To Inspect Or Edit

Expected inspect: `CONTEXT.md`, the new PRD, Issue #40 handoff/report,
`src/bilibili/subtitle.ts`, `src/cli.ts`, ASR/credential modules, relevant
tests/docs/memory.

Expected edit: smallest coherent set under `src/bilibili/`, `src/cli.ts`,
`tests/`, bilingual user docs/changelog, codemap/QA/report.

Do not touch: dependencies, versions, lockfile, generated `dist/`, workflows,
hooks, provider config, user credentials, Git history.

## Required Capabilities

- Skills: `vitest`, `tdd`, `secret-scanning`, `code-review`.
- Subagents: `test-baseline-builder`, `credential-sanitizer`, `risk-reviewer`.
- CLI: `npm`, `node`, `git`; no remote mutation.
- If a named capability is unavailable, report it and use the closest safe
  fallback without weakening credential checks.

## Acceptance Criteria

- [ ] Every selected `ai-zh` is assessed twice in both relevant tools; Human
  Subtitles remain single-read.
- [ ] Stability/language/topic failures never return their body.
- [ ] Transcript follows existing ASR/description authorization; video-info
  returns uncached description.
- [ ] Inconclusive semantic signals do not reject.
- [ ] Second-read boundary errors remain visible.
- [ ] Non-TTY setup works only through explicit non-interactive mode and
  existing credential sources; optional model flag uses the allowlist.
- [ ] Interactive setup remains unchanged.
- [ ] No credential value is printed or committed.
- [ ] MCP tools/defaults and dependency/package/release state remain stable.
- [ ] Codemap and project memory reflect the final verified state.

## Verification

```bash
npx vitest run tests/bilibili-transcript.test.ts tests/cli.test.ts tests/server-tools.test.ts tests/server-handler-sanitization.test.ts tests/server-error-next-steps.test.ts
npx vitest run tests/asr-transcription.test.ts tests/bilibili-playback.test.ts
npm run build
npm test
npm pack --dry-run --json --ignore-scripts
git diff --check
```

Manual: post-build child-process setup smoke with non-TTY stdin and synthetic
environment credentials; print only exit/status/redaction assertions.

## Stop And Report Conditions

Stop if thresholds cannot be implemented with native deterministic behavior,
credential values would need stdin/argv, the change requires a new dependency
or model, a real secret is found, or a broader interface/refactor is required.
