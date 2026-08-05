# Codex To Claude Handoff: ASR Model Selector Phase 2

## Objective

Implement task `ASR-SELECT-02` from
`docs/agent-memory/handoffs/2026-07-27-asr-model-selector-phase2-task-ticket.md`.
Add a minimal allowlisted `tiny` / `base` / `small` selector after the existing
Yes answer, with Enter selecting recommended `small`.

## Current State

- Phase 1 is implemented but uncommitted/unpublished.
- `src/asr/state.ts` accepts only one exact small repository/revision.
- `runAsrInstallation()` uses one managed venv/model directory and is
  idempotent for ready small state.
- `setupCredentials()` asks only Yes/No and injects a zero-argument installer.
- Baseline: build passes, 95 focused tests and 496 full tests pass, package dry
  run contains 148 files.

## Files To Inspect

- `docs/asr-model-selector-prd.md`
- `docs/research/2026-07-27-asr-model-selector-phase2.md`
- Phase 1 PRD/task/report/QA
- `src/asr/state.ts`
- `src/asr/installer.ts`
- `src/cli.ts`
- existing ASR/CLI/MCP smoke tests and bilingual docs

## Files To Edit

Only the files listed in the Phase 2 task ticket. Create:

- `docs/qa/2026-07-27-asr-model-selector-phase2.md`
- `docs/agent-memory/handoffs/2026-07-27-asr-model-selector-phase2-claude-report.md`

## Required Capability

- Read and use `vitest`, `secret-scanning`, and `codebase-design` from
  `C:\Users\ZX\.claude\skills`.
- Use `.claude/agents/test-baseline-builder.md` for test design and
  `.claude/agents/risk-reviewer.md` after implementation.
- Do not use Superpowers or create an agent tree.

## Recommended Approach

Keep the existing ASR module seam:

1. Define one readonly model-spec allowlist in `state.ts` with key, repository,
   revision, and approximate MB. Retain small aliases if that keeps Phase 1
   tests/readers compatible.
2. Let `readAsrState()` accept any allowlisted repository/revision and return
   the derived key. Keep state version 1.
3. Pass a selected model key into `runAsrInstallation()`. Resolve it before any
   mutation. Same selected ready model skips; a different model clears the
   ready marker and runs the existing pipeline.
4. Pass the resolved spec into download/state writing and use its size in the
   progress line. Keep the existing shared model directory.
5. Add a pure choice parser or equally small testable branch. Setup accepts
   `1/2/3` and `tiny/base/small`, Enter defaults to small, invalid input
   re-prompts, and No never reaches it.
6. Add `asr.model` as key or `null` to doctor while preserving top-level status
   and exit codes.

Add this comment at the one-active-model decision:

```ts
// ponytail: one active model reuses the Phase 1 directory; use per-model
// directories only if retaining several installed models becomes a real need.
```

## Constraints

- Allowlist:
  - tiny: `Systran/faster-whisper-tiny`,
    `d90ca5fe260221311c53c58e660288d3deb8d356`, 78.2 MB
  - base: `Systran/faster-whisper-base`,
    `ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66`, 148 MB
  - small: `Systran/faster-whisper-small`,
    `536b0662742c02347bc0e980a01041f333bce120`, 486 MB, default
- No custom repository/revision, shell string, real model download, real
  credential, environment dump, dependency, package version, new command, MCP
  change, model deletion, or `dist/` edit.
- Preserve Python isolated mode, child-env filtering, bounded diagnostics,
  atomic ready state, retry behavior, Phase 1 state, and credential exit codes.
- Do not edit overlapping unrelated README/SVG/learning-proposal work.

## Execution Steps

1. Add failing focused tests for model resolution, Phase 1 compatibility,
   selected download/state, switching, invalid runtime key, CLI default/name/
   number/re-prompt, No short-circuit, and doctor model/null.
2. Implement the minimum state/installer/CLI changes.
3. Update bilingual docs/changelogs and codemap without rewriting unrelated
   sections.
4. Run required checks and subagent reviews; repair same-scope findings.
5. Write QA and the Claude report.

## Verification Commands

```bash
npm run build
npx vitest run tests/asr-installer.test.ts tests/cli.test.ts tests/mcp-server-smoke.test.ts
npm test
npm pack --dry-run --json --ignore-scripts
git diff --check
```

Also inspect built help and parse built `doctor --json` without printing any
credential value. Use synthetic environments in all tests.

## Acceptance Criteria

Every unchecked criterion in the Phase 2 task ticket and PRD must be satisfied
with direct test or command evidence.

## Things Not To Change

MCP tools/schemas, Bilibili modules, package version/dependencies/workflow,
SVGs, `dist/`, Phase 1 model/runtime pins, credential storage, and
`pending-learning-proposals.md`.

## Stop And Report If

- State version 1 cannot remain backward compatible.
- Supporting model switch safely requires deleting user data.
- Any source/test/handoff contains a real secret or full environment.
- Required checks fail outside this scope.

## Expected Claude Report

Use the project report template, name subagents/skills actually used, include
baseline/final counts, pack boundary, skipped real download, risks, and
Harness Artifacts.
