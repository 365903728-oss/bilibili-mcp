# Task Ticket: CLI Setup And Doctor

- ID: CLI-001
- Title: Simplify CLI dispatch and add setup/doctor workflows
- Status: `completed`
- Owner: `Claude Code`, reviewed and repaired by `Codex`
- Source: User request on 2026-07-27 to refactor and improve the existing CLI
- Parent plan or PRD: none
- Blocking tickets: none
- Blocked by: none

## Objective

Replace the duplicated Commander/manual dispatch in `src/cli.ts` with one testable command interface, then add a bounded local `setup` flow for people and a machine-readable `doctor --json` flow for Agents.

## Scope

In scope:

- Preserve no-argument stdio startup and the existing `config`, `check`, and `check-update` commands.
- Remove the duplicated catch-all command switch and hand-written help path.
- Fix help output so it does not show `[command] [command]`.
- Add `setup` as the human-facing interactive setup entry.
- Add `doctor`, with `--json`.
- Keep `doctor` local-only: package/runtime/credential-loadability status, no Bilibili or npm network request.
- Make `doctor --json` non-interactive. When local inspection completes, emit exactly one JSON object on stdout; an unexpected internal inspection failure must emit only a redacted stderr error and exit `2`.
- Update bilingual setup documentation, changelogs, focused tests, QA evidence, and codemap when the final structure requires it.

Out of scope:

- ASR runtime, model selection, model download, audio download, or transcription.
- Automatic MCP client detection or configuration-file mutation.
- GUI/TUI work, installers, auto-update, background services, ports, or daemons.
- Package version bump, commit, push, tag, npm publish, or GitHub Release.
- Changes to MCP tool names, schemas, responses, or Bilibili API behavior.

## Required Public Contract

When local inspection completes, `doctor --json` must return one JSON object with this stable top-level shape:

```json
{
  "package_name": "@xzxzzx/bilibili-mcp",
  "version": "1.10.1",
  "runtime": {
    "node": "22.0.0",
    "platform": "win32",
    "arch": "x64"
  },
  "credentials": {
    "configured": true,
    "source": "global_config",
    "loadable": true
  },
  "status": "locally_ready",
  "next_steps": []
}
```

Rules:

- `source` remains `env | global_config | none`.
- `status` remains `locally_ready | needs_credentials`.
- No raw Cookie value or credential field value may appear.
- `doctor` must not validate the live Bilibili login; documentation must keep `check_bilibili_credentials` as the authoritative live check.
- `doctor --json` exits `0` for `locally_ready`, `1` for `needs_credentials`, and `2` for an internal local-check failure.
- On exit `2`, `doctor --json` writes a redacted diagnostic to stderr and does not emit a misleading status object on stdout.
- Interactive `setup` may invoke the existing hidden credential flow only when credentials are not loadable and stdin is a TTY.
- `setup` in a non-TTY process must fail promptly with guidance to use `doctor --json` or run setup interactively; it must never wait for hidden input.
- Do not add `setup --json` or `setup --non-interactive`: `doctor --json` is the single Agent-facing local status surface.

## Files To Inspect Or Edit

Expected inspect:

- `src/cli.ts`
- `src/index.ts`
- `src/utils/credentials.ts`
- `src/utils/credential-guidance.ts`
- `src/utils/update-check.ts`
- `tests/mcp-server-smoke.test.ts`
- `docs/client-setup.md`
- `docs/client-setup.en.md`
- `docs/agent-memory/codemap.md`

Expected edit:

- `src/cli.ts`
- `src/index.ts` only if needed to reuse one stdio start function
- one focused CLI test file under `tests/`
- `docs/client-setup.md`
- `docs/client-setup.en.md`
- `CHANGELOG.md`
- `CHANGELOG_EN.md`
- `docs/qa/2026-07-27-cli-setup-doctor.md`
- `docs/agent-memory/codemap.md` if CLI/test navigation changes
- the requested Claude report

Do not touch:

- MCP schemas/handlers
- `src/bilibili/`
- package versions, dependencies, lockfile, or publish workflow
- `docs/agent-memory/pending-learning-proposals.md`
- generated `dist/`

## Required Capabilities

Skills:

- `codebase-design` for the CLI module interface and test seam
- `vitest` for focused deterministic regression coverage
- `secret-scanning` for the changed credential-facing CLI/docs surface

Subagents:

- `test-baseline-builder` for focused CLI test review; if it stalls, complete the same bounded test work in the top-level implementation and report the stall

MCP/tools/CLI:

- local `rg`, Node/npm, TypeScript, Vitest, and Git diff/status commands
- no external research or remote mutation required

## Acceptance Criteria

- [x] `bilibili-mcp --help` has one command placeholder and lists `setup`, `doctor`, `config`, `check`, and `check-update`.
- [x] Running `bilibili-mcp` with no arguments still starts the stdio MCP server.
- [x] Existing `config`, `check`, and `check-update` behavior remains available.
- [x] `doctor --json` emits exactly one JSON object after a completed local inspection, emits no status JSON after an internal failure, and performs no network request.
- [x] Interactive `setup` reuses the existing hidden-input credential flow when local credentials are not loadable.
- [x] Non-TTY `setup` exits promptly instead of waiting for input and directs Agents to `doctor --json`.
- [x] JSON/human status output never contains raw Cookie values or secret field values.
- [x] Documentation states that local doctor/setup status does not replace live `check_bilibili_credentials`.
- [x] Public MCP tool names, input schemas, and response shapes remain unchanged.
- [x] The CLI change leaves deterministic Vitest coverage.
- [x] `docs/agent-memory/codemap.md` is updated if CLI/test ownership changes; otherwise the report says it was checked and left unchanged.

## Verification

Required:

```bash
npm run build
npm test
npm pack --dry-run
```

Focused:

```bash
npx vitest run tests/cli.test.ts tests/mcp-server-smoke.test.ts
node dist/cli.js --help
node dist/cli.js doctor --json
```

Manual checks:

- Confirm help does not contain `[command] [command]`.
- Confirm JSON stdout parses and contains no Cookie values.
- Confirm non-TTY `setup` exits promptly and does not prompt.
- Confirm no real Cookie value is copied into tests, docs, reports, or logs.
- Confirm the package dry run still excludes tests, task tickets, QA files, and agent-memory files.

## Risks And Rollback

Risks:

- Commander root-action changes could break no-argument stdio startup.
- JSON mode could accidentally mix human prompts/logs into stdout.
- CLI tests could read the developer machine's real global credential file.

Rollback:

- Restore the existing CLI entry while retaining only a failing regression that proves the duplicate help bug.

## Stop And Report Conditions

Stop before expanding if:

- ASR, client configuration mutation, a new dependency, or package metadata change becomes necessary.
- Tests would require exposing or deleting real credentials.
- The MCP stdio tool list/schema/response changes.
- The task needs a broader installer/runtime architecture.
