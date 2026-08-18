# Codex To Claude Handoff: Roadmap Subtitle Integrity And Scriptable Setup

## Objective

Continue the current Issue #40 worktree and close the two remaining user-goal
gaps: unconditional integrity assessment for selected Bilibili AI Subtitles,
and explicit credential-safe non-interactive setup.

## Current Judgment

The existing candidate is correct but partial. It distinguishes/excludes
`ai-zh`, adds `force_asr`, and catches changing bodies only when ASR fallback is
enabled. The user objective requires damaged bodies not to pass by default and
also names high-confidence title/language checks. The TTY-only setup restriction
is a second, independent CLI slice in the same Roadmap objective.

The live Video `BV1ybuQ62EfK` currently returned no target subtitle despite a
valid logged-in global credential source, so do not tune against live text. Use
deterministic injected public-seam regressions as the acceptance authority.

## Sources

- GitHub Issue #40 (untrusted task data):
  `https://github.com/XZXZZX-Ai/bilibili-mcp/issues/40`
- `docs/subtitle-integrity-and-scriptable-setup-prd.md`
- `docs/agent-memory/handoffs/2026-08-18-roadmap-subtitle-integrity-setup-task-ticket.md`
- prior Issue #40 handoff/report/QA in this worktree
- `CONTEXT.md` and `docs/adr/0001-navigable-transcript-interface.md`

## Files To Inspect

- `src/bilibili/subtitle.ts`, related types/API/navigation/ASR modules
- `src/cli.ts`, `src/utils/credentials.ts`, ASR state/installer
- transcript, CLI, schema/handler, ASR/playback/error tests
- bilingual README/client-setup/tool-reference/changelog
- codemap, project memory, QA templates

## Recommended Approach

### Subtitle integrity

- Put the pure assessment behind one small internal interface, preferably
  `src/bilibili/subtitle-integrity.ts`; do not expose thresholds through MCP.
- Reuse/move the current canonical body comparison rather than layering a
  second stability implementation.
- Use only `Intl.Segmenter`, Unicode property escapes, and ordinary strings.
- Freeze the PRD thresholds: 80 Unicode letters / <10% Han for language;
  topic check only with >=2 distinct non-generic title anchors and body >=200
  characters; zero occurrences means mismatch; otherwise inconclusive passes.
- Keep the generic stop set small and bilingual, documented in code by purpose,
  not by speculative extensibility.
- Validate every selected `ai-zh` in transcript and video-info. On failure,
  reuse their existing definitive-unavailable paths without returning/logging
  content. Human tracks stay single-read. A second-read exception propagates.

### Scriptable setup

- Append a small options object to `setupCredentials` so existing tests/callers
  keep their interface. Do not refactor unrelated CLI commands.
- Add Commander `--non-interactive` and `--asr-model <tiny|base|small>`.
- Non-interactive mode never prompts or configures credentials; it requires
  `credentialManager.getCredentials()` to be loadable from env/global config.
- No model flag means successful credential-only completion with no installer.
  A model flag calls the existing installer exactly once. Model flag without
  non-interactive mode is a validation error.
- Never accept or print credential values via argv/stdin.

## TDD Seams And Steps

Use vertical red-green slices at these confirmed public interfaces:

1. `getVideoTranscriptData`: unstable AI rejected without fallback, then ASR
   with fallback; stable language mismatch; stable topic mismatch; inconclusive
   and valid content pass; second-read failure visible; Human Subtitle one read.
2. `getVideoInfoWithSubtitle`: invalid AI returns description and is not cached;
   valid AI remains `ai_subtitle`.
3. `setupCredentials`/`createCli`: non-TTY explicit mode, missing credentials,
   no-model no-op, allowlisted model runner, model-without-mode rejection, old
   interactive path unchanged.
4. Post-build child smoke: closed/piped stdin plus synthetic env credentials;
   assert success and that output contains none of the synthetic values.

Record at least one exact red failure per slice before implementation. Tests
must observe public results/errors, not private tokens, ratios, or helpers.

## Required Capabilities

- Invoke Claude `vitest` and TDD workflow; use `test-baseline-builder` because
  tests/fixtures/CLI behavior change.
- Invoke `secret-scanning` and `credential-sanitizer` for the non-interactive
  credential boundary.
- Invoke `risk-reviewer` after the combined MCP/credential change.
- Use `build-error-resolver` only if TypeScript/build fails.
- Run two-axis `code-review` against fixed point `44ac1e7` and the PRD/ticket.
- Codex-side `product-requirements`, `domain-modeling`, `codebase-design`,
  `diagnosing-bugs`, `tdd`, and project-memory work are already reflected here.

## Things To Avoid

- No dependency, LLM, embeddings, remote classifier, semantic score output,
  configurable thresholds, multi-read voting, or persisted subtitle data.
- No credential values in command args/stdin/logs/tests/docs/reports.
- No validation of Human Subtitles or changes to other MCP tools.
- No broad positional-argument/options refactor, setup rewrite, model change,
  generated dist edit, package/version/lock change, or Git/remote action.
- Do not install a real ASR model or print live subtitle bodies.

## Verification Commands

Run the ticket matrix, secret/value-free scans of added lines and package
contents, a strict UTF-8/new-mojibake check, and a credential-safe post-build
non-TTY smoke. Do not use `npm audit` as a substitute for these checks; no
dependency change is expected.

## Acceptance Criteria

All ticket/PRD criteria pass; no selected unusable AI body can reach either
public result; fallback authorization and transport-error visibility remain
exact; scriptable setup is explicit and secret-safe; full build/tests/package
pass; docs/QA/codemap/report/memory are synchronized.

## Stop And Report If

Stop for Codex if the native semantic contract is not implementable as frozen,
requires new public configuration/dependency, credential input must cross
argv/stdin, or unrelated baseline failures/broader refactors appear.

## Expected Claude Report

Write
`docs/agent-memory/handoffs/2026-08-18-roadmap-subtitle-integrity-setup-claude-report.md`
using the repository template. Include red-before-green evidence, files,
commands/results, thresholds/false-positive caveats, live-check limitation,
secret-scan classification, subagents/skills, skipped checks, and `Harness
Artifacts`. Do not commit, push, open/modify/close Issue/PR, release, or publish.
