# Codex To Claude Handoff: CLI Setup And Doctor

## Update Goal

Implement task ticket `docs/agent-memory/handoffs/2026-07-27-cli-setup-doctor-task-ticket.md`: simplify the current CLI command interface and add local `setup` plus Agent-readable `doctor --json`, without implementing ASR.

## Current Judgment

`src/cli.ts` currently defines both a root `[command]` switch and explicit Commander subcommands. The observable result is duplicated help usage (`[command] [command]`) and two command-dispatch paths. The smallest root-cause fix is one Commander command interface with focused local status behavior.

## Recommended Approach

- Read the task ticket first and treat its public JSON shape and scope as frozen.
- Use the `codebase-design` skill to keep one small CLI interface and one test seam.
- Use the `vitest` skill and request the `test-baseline-builder` subagent for the focused regression.
- Prefer `new Command()` over Commander’s process-global singleton so tests do not share parser state.
- Keep `src/cli.ts` as the package binary entry. Export only the minimum functions needed for deterministic tests.
- Reuse the existing credential manager and hidden input flow. Do not add another credential store or accept secrets in flags.
- If one shared stdio start function removes the duplicate `src/cli.ts` / `src/index.ts` startup implementation cleanly, make that minimal change while preserving the default server export.
- Keep `doctor` local-only and deterministic.
- Keep `setup` human-facing and interactive. In a non-TTY process it must fail promptly with guidance to use `doctor --json`; do not add redundant `setup --json` or `setup --non-interactive` modes.

## Things To Avoid

- No ASR placeholders, provider interfaces, download managers, model config, client auto-detection, or installer scaffolding.
- No new dependencies.
- No network request in `doctor`.
- No raw secret value in stdout, stderr, tests, docs, handoff, or report.
- No command-line Cookie arguments.
- No ordinary CLI output during no-argument stdio startup; stdout remains JSON-RPC only.
- No edits to the existing generated `pending-learning-proposals.md` change.
- No commit, push, tag, publish, or version bump.

## Claude Code Execution Steps

1. Read `AGENTS.md`, `CLAUDE.md`, the task ticket, project memory files required by the repository, and `docs/agent-memory/agent-communication.md`.
2. Check `git status --short`; preserve the unrelated generated learning-proposal modification.
3. Read the installed `codebase-design`, `vitest`, and `secret-scanning` skill instructions. Request `test-baseline-builder` once for the focused CLI tests; use the documented bounded fallback if it stalls.
4. Add failing-first coverage for the duplicated help bug and the ticket’s setup/doctor behavior.
5. Refactor the CLI through one Commander interface and implement the frozen local status contract.
6. Update only the bilingual canonical setup guides, bilingual Unreleased changelogs, focused QA record, and codemap as required.
7. Run focused checks, full build/test, package dry run, and CLI smoke commands.
8. Review the diff for scope, credential leakage, stdio cleanliness, encoding, and unintended package contents.
9. Write the report to `docs/agent-memory/handoffs/2026-07-27-cli-setup-doctor-claude-report.md`.

## Files To Inspect

- `src/cli.ts`
- `src/index.ts`
- `src/utils/credentials.ts`
- `src/utils/credential-guidance.ts`
- `src/utils/update-check.ts`
- `tests/mcp-server-smoke.test.ts`
- `docs/client-setup.md`
- `docs/client-setup.en.md`
- `docs/agent-memory/codemap.md`
- `docs/templates/qa-checklist.md`

## Files To Edit

Follow the task ticket’s expected edit list. Adding one focused CLI module/file is allowed only if it clearly reduces the CLI interface or makes deterministic testing materially simpler.

## Required Capability

- Skills: `codebase-design`, `vitest`, `secret-scanning`
- Claude subagent: `test-baseline-builder`
- Local tools: `rg`, `git status/diff`, `npm`, `node`, `vitest`
- Intentionally skipped: `system-design` because this task does not add the ASR/runtime subsystem; `package-maintainer` because package metadata and dependencies are out of scope

## Verification Commands

```bash
npx vitest run tests/cli.test.ts tests/mcp-server-smoke.test.ts
npm run build
npm test
npm pack --dry-run
node dist/cli.js --help
node dist/cli.js doctor --json
git diff --check
git status --short
```

## Acceptance Criteria

All task-ticket acceptance criteria must pass. In particular:

- one Commander dispatch path
- no duplicated help placeholder
- no-argument stdio startup preserved
- frozen local-only JSON status shape using `locally_ready | needs_credentials`
- no prompts in `doctor --json` or non-TTY `setup`
- no network in local status commands
- no secret values in output or fixtures
- full build/test/package checks pass

## Risks

- Commander parsing changes can silently alter the default binary behavior.
- Global credential state on this machine can contaminate tests.
- A report based only on configured credentials does not prove live Bilibili login.

## Stop And Report If

- The public JSON shape in the ticket is insufficient or contradictory.
- A new dependency or package metadata change appears necessary.
- No-argument stdio behavior cannot be preserved with a small refactor.
- A test or command would expose, overwrite, or delete a real credential.
- ASR/client-installer work becomes necessary.

## Expected Claude Report

Use the report template in `docs/agent-memory/agent-communication.md`, including:

- files changed
- commands and exact results
- focused and full test counts
- CLI smoke outcomes
- secret-scan outcome
- unresolved risks/skipped checks
- subagent result or stall
- full `Harness Artifacts` section
