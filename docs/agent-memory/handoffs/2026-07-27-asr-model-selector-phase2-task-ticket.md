# Task Ticket: ASR Model Selector Phase 2

- ID: ASR-SELECT-02
- Title: Add a three-model allowlisted selector to setup
- Status: `completed`
- Owner: Claude Code via Paseo; Codex review
- Source: User-authorized continuation after Phase 1
- Parent PRD: `docs/asr-model-selector-prd.md`
- Blocking tickets: ASR-INSTALL-01
- Blocked by: none

## Objective

After a user opts into ASR, let them choose `tiny`, `base`, or `small`, with
Enter selecting recommended `small`. Reuse the existing installer and preserve
Phase 1 state compatibility.

## Scope

In scope:

- One fixed, pinned three-model allowlist.
- Local input parsing and invalid-input re-prompt.
- Selected model passed through download, state, and doctor.
- Same-model idempotency and model-switch behavior.
- Focused tests, bilingual docs, codemap, QA, report, and project memory.

Out of scope:

- Custom model IDs, extra models, multiple active installs, model removal,
  audio retrieval, transcription, subtitle fallback, new MCP tools, Git, or
  release work.

## Files To Inspect Or Edit

Expected edit:

- `src/asr/state.ts`
- `src/asr/installer.ts`
- `src/cli.ts`
- `tests/asr-installer.test.ts`
- `tests/cli.test.ts`
- bilingual README/setup/changelog files
- `docs/agent-memory/codemap.md`
- Phase 2 QA/report/PRD status

Do not touch:

- Bilibili request modules, MCP tool schemas/handlers, `dist/`, package
  dependencies/version/workflow, SVGs, or
  `docs/agent-memory/pending-learning-proposals.md`.

## Required Capabilities

- Skills: `vitest`, `secret-scanning`, `codebase-design`
- Claude subagents: `test-baseline-builder`, then `risk-reviewer`
- CLI: build, focused Vitest, full Vitest, built CLI probes, pack dry-run,
  diff check, and scoped secret scan

## Acceptance Criteria

- [x] The selector offers only tiny (~78 MB), base (~148 MB), and small
      (~486 MB).
- [x] Enter defaults to small; numeric and name inputs work; invalid input
      re-prompts with zero installer calls.
- [x] No remains side-effect free and does not show the model selector.
- [x] Model/revision validation occurs before install mutation.
- [x] Phase 1 small state remains ready and same-model install is idempotent.
- [x] Switching models invalidates old readiness, runs the existing pipeline,
      and writes selected state only after verification.
- [x] Doctor reports status plus selected model key/null without changing
      credential exit codes.
- [x] No new dependency, CLI command, MCP tool/schema, or package version.
- [x] Build, focused tests, full tests, CLI probes, pack, diff, and scoped
      secret checks pass.
- [x] Documentation says Phase 2 still does not transcribe.

## Verification

```bash
npm run build
npx vitest run tests/asr-installer.test.ts tests/cli.test.ts tests/mcp-server-smoke.test.ts
npm test
npm pack --dry-run --json --ignore-scripts
git diff --check
```

Manual checks:

- Built setup text shows exactly three choices and the recommended default.
- Built doctor JSON is parseable and contains no paths or credentials.
- No real model download is required for deterministic acceptance.

## Risks And Rollback

- Keep one active model in the existing model directory. If multiple retained
  models become a real requirement, introduce per-model directories in a
  separate migration.
- Concurrent setup remains unsupported; run one installer process at a time.
- Rollback is removal of selector plumbing while retaining the Phase 1 default.

## Stop And Report Conditions

Stop if implementation needs a state-schema migration, model deletion, custom
remote input, dependency/package version change, MCP behavior change, or real
credential/model data.

## Completion Report

Return changed files, exact commands/results, skipped real-network checks,
capabilities used, codemap/harness status, unresolved risks, and decision
points.
