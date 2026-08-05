# Task Ticket: Optional ASR Model Installation Phase 1

- ID: ASR-INSTALL-01
- Title: Install and verify fixed faster-whisper-small through setup
- Status: `completed`
- Owner: Claude Code via Paseo; Codex review
- Source: User-authorized ASR implementation
- Parent PRD: `docs/asr-model-install-prd.md`
- Blocking tickets: none
- Blocked by: none

## Objective

Add a default-off setup choice that can install and verify the fixed
`Systran/faster-whisper-small` model in a private user-managed environment.
Expose local readiness through doctor without implementing transcription or a
model selector.

## Scope

In scope:

- ASR path/state/runtime discovery module.
- Python 3.9+ discovery with an executable override.
- User-scoped venv, pinned runtime install, pinned snapshot download, CPU INT8
  model-load verification, atomic ready state.
- Existing `setup` orchestration with No default.
- `doctor` ASR status.
- Node engine metadata correction to `>=20.0.0`.
- Deterministic tests, CLI smoke, bilingual docs/changelog, codemap, QA/report.

Out of scope:

- Model selector, GPU/CUDA, bundled Python, audio retrieval, transcription,
  automatic subtitle fallback, new MCP tools, model deletion, release/Git work.

## Files To Inspect Or Edit

Expected inspect:

- `src/cli.ts`
- `src/utils/credentials.ts`
- `tests/cli.test.ts`
- `tests/mcp-server-smoke.test.ts`
- current READMEs/setup guides/package metadata/codemap

Expected edit:

- `src/asr/installer.ts`
- `src/asr/state.ts`
- `src/cli.ts`
- focused tests
- `package.json`, `package-lock.json`
- bilingual README/setup/changelog
- `docs/agent-memory/codemap.md`
- `docs/qa/2026-07-27-asr-model-install-phase1.md`
- phase report

Do not touch:

- MCP tool schemas/handlers and Bilibili request modules
- `dist/`
- publish workflow or package version
- SVG files
- `docs/agent-memory/pending-learning-proposals.md`

## Required Capabilities

Skills:

- `vitest`
- package maintenance rules

Subagents:

- `test-baseline-builder` for deterministic installer/CLI tests
- `package-maintainer` for engine/lock/pack verification
- `risk-reviewer` after implementation

CLI:

- `npm run build`
- focused `vitest`
- `npm test`
- `npm pack --dry-run --json --ignore-scripts`

## Execution Steps

1. Add immutable ASR constants, derived user paths, state validation, and
   atomic state writing.
2. Implement injectable Python discovery and subprocess runner using no shell.
3. Implement idempotent installation into the managed venv; write ready state
   only after pinned snapshot download and CPU INT8 model load succeeds.
4. Orchestrate credentials then optional ASR from the existing setup command.
5. Add ASR status to human/JSON doctor without changing overall exit semantics.
6. Correct package Node engine floor and update the root lock metadata with npm.
7. Add deterministic tests; no tests may invoke Python, pip, network, or real
   model download.
8. Update bilingual user docs, codemap, QA, and report.
9. Run review and all verification.

## Acceptance Criteria

- [x] No is the default and performs no ASR command/network/filesystem mutation.
- [x] Existing configured credentials do not prevent the ASR question.
- [x] Yes uses only the fixed runtime/model/revision from the PRD.
- [x] Install is user-scoped, does not mutate global Python, and uses no shell.
- [x] Successful verification writes a private versioned state file atomically.
- [x] Failure writes no ready state, returns actionable guidance, and preserves
      partial files for retry.
- [x] Doctor reports `not_installed`, `incomplete`, or `ready` locally with no
      absolute paths or secrets.
- [x] Doctor credential status and exit codes remain unchanged.
- [x] Public MCP tools/schemas/responses and no-argument stdio remain unchanged.
- [x] Package engine is Node `>=20.0.0`; entries still target `dist`.
- [x] Model/runtime/cache files are never included in `npm pack`.
- [x] Documentation explicitly says Phase 1 does not transcribe yet.
- [x] Credentials, Cookies, tokens, `.env`, and private values are not printed
      or committed.
- [x] Codemap and QA accurately describe the new flow.

## Verification

```powershell
npm run build
npx vitest run tests/asr-installer.test.ts tests/cli.test.ts tests/mcp-server-smoke.test.ts
npm test
npm pack --dry-run --json --ignore-scripts
git diff --check
```

Manual checks:

- Help still exposes existing commands and setup remains TTY-only.
- Default No makes no ASR calls.
- Injected success/failure flows prove state gating without downloading.
- Built `doctor --json` is parseable, secret-free, local-only, and includes ASR.
- Built no-argument CLI stdio remains clean.

## Risks And Rollback

- Rollback is deletion of the new ASR modules/tests/docs and restoration of the
  setup/doctor/package engine changes; user-downloaded directories are never
  deleted automatically.

## Stop And Report Conditions

Stop if implementation requires shell interpolation, global pip mutation,
unbounded model IDs, a new MCP tool, audio download/transcription, package
publication, or deletion of user cache/model files.
