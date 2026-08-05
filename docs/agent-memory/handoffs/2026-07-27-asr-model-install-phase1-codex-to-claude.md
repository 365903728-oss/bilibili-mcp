# Codex To Claude Handoff: Optional ASR Model Installation Phase 1

## Update Goal

Implement ticket
`docs/agent-memory/handoffs/2026-07-27-asr-model-install-phase1-task-ticket.md`
against the current dirty working tree. Preserve all existing user changes.

## Current Judgment

The minimum real first phase is a default-off, fixed-model installer that proves
runtime/model readiness. A menu without a working managed installation is not
acceptable; transcription and multi-model selection are deliberately later.

## Recommended Approach

- Reuse the existing `setup` and `doctor` seams.
- Add focused `src/asr/` modules rather than growing `src/cli.ts`.
- Use only Node standard library for filesystem/process orchestration.
- Managed root: `~/.bilibili-mcp/asr/`.
- Runtime: `faster-whisper==1.2.1`.
- Model: `Systran/faster-whisper-small`.
- Revision: `536b0662742c02347bc0e980a01041f333bce120`.
- Verification: load the downloaded local path on CPU INT8.
- Allow `BILIBILI_ASR_PYTHON` as an executable override; never log secrets or
  environment contents.

## Things To Avoid

- No model selector, custom model ID, GPU logic, system FFmpeg prerequisite,
  global pip, shell strings, audio download, transcription, MCP tool changes,
  background download, automatic deletion, package version/release/Git action.
- Do not edit `pending-learning-proposals.md` or SVGs.
- Do not overwrite or revert the existing CLI/README work.

## Claude Code Execution Steps

1. Read the ticket, PRD, research note, `AGENTS.md`, `CLAUDE.md`, and current
   relevant source/tests/docs.
2. Invoke `test-baseline-builder` for deterministic Vitest coverage and
   `package-maintainer` for engine/lock/package checks.
3. Implement state/path logic with strict version/schema checks and atomic
   write-after-verification.
4. Implement Python discovery and process execution through injected,
   argument-array boundaries. Tests must never start Python/pip/network.
5. Integrate with setup so configured credentials continue to the explicit
   default-No ASR prompt.
6. Extend doctor with a stable ASR object while preserving credential status
   and exit codes.
7. Change root Node engine to `>=20.0.0` and update lockfile using npm tooling;
   add no npm dependency.
8. Update bilingual docs, changelog, codemap, QA.
9. Run the required checks and invoke `risk-reviewer`; repair same-scope
   blocking findings.
10. Write
    `docs/agent-memory/handoffs/2026-07-27-asr-model-install-phase1-claude-report.md`.

## Acceptance Criteria

All ticket checkboxes must be satisfied with direct evidence. In particular:

- default No produces zero ASR side effects;
- only exact pinned runtime/model/revision values can be installed;
- no global Python mutation or shell interpolation;
- incomplete/failed install cannot appear ready;
- doctor is local and safe;
- no MCP behavior changes;
- build, focused/full tests, pack, and diff checks pass.

## Risks

- Existing worktree is intentionally dirty. Do not infer unrelated files are
  disposable.
- Interactive setup and long-running downloads require injected test seams.
- Python/package/model support may fail on some platforms; return actionable
  error and leave no false-ready marker instead of guessing.

## Expected Report

Use the project Claude report template. Include files changed, exact commands
and results, skipped real download checks, subagents used/results, unresolved
risks, and `Harness Artifacts` status for ticket, research note, QA, codemap,
harness-security, and harness-eval. Do not commit, push, tag, publish, or
release.
