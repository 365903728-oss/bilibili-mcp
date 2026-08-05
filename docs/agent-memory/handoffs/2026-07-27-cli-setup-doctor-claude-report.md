# Claude To Codex Report: CLI Setup And Doctor (Repaired)

## Summary

Implemented the task ticket `2026-07-27-cli-setup-doctor-task-ticket.md` and applied independent review fixes. Simplified CLI dispatch to one Commander interface, added `setup` (human-facing interactive) and `doctor --json` (Agent-readable local status), fixed the duplicated `[command]` help placeholder, and addressed three review findings plus additional same-scope issues. No ASR, new dependencies, package metadata changes, or MCP tool changes.

## Repair Round Fixes

Independent review found three issues plus additional scope refinements, all addressed:

1. **ESM guard** (`src/cli.ts`): Added `import.meta.url === process.argv[1]` check before calling `main()`. Importing `src/cli.ts` (e.g. in tests) no longer triggers stdio startup or argument parsing.

2. **setupCredentials expired/unloadable** (`src/cli.ts`): Changed gate from `getCredentialSource() !== "none"` to `getCredentials() !== null`. Expired or unloadable credentials now enter hidden reconfiguration instead of incorrectly showing "already configured."

3. **Doctor exit code 2** (`src/cli.ts`): Wrapped `doctorCommand` body in try/catch. Internal local-check failures set `process.exitCode = 2` without emitting a misleading status JSON. `needs_credentials` remains exit code 1, `locally_ready` remains exit code 0.

4. **Doctor next_steps** (`src/cli.ts`): Changed from recommending `config` to recommending `setup`.

5. **Version command compatibility**: Preserved old `version` subcommand and `-v` flag alongside Commander's native `-V`/`--version`.

6. **Removed over-constrained test**: Deleted "has exactly 5 subcommands" test; replaced with softer version subcommand existence check.

7. **Deterministic env in tests** (`tests/cli.test.ts`): Added save/restore of `BILIBILI_SESSDATA`, `BILIBILI_BILI_JCT`, `BILIBILI_DEDEUSERID` in beforeEach/afterEach for all relevant describe blocks.

8. **Built-bin smoke tests** (`tests/mcp-server-smoke.test.ts`): Added 3 tests reusing the existing `beforeAll` build:
   - `dist/cli.js` no-arg starts stdio server
   - Isolated-HOME `doctor --json` emits single JSON object and exits 1
   - Non-TTY `setup` fast-fails with exit 1

9. **Docs npx consistency** (`docs/client-setup.md`, `docs/client-setup.en.md`): Changed bare `bilibili-mcp doctor --json` to `npx -y @xzxzzx/bilibili-mcp@latest doctor --json`.

## Files Changed

- `src/cli.ts` — ESM guard, version subcommand + `-v` flag, `setupCredentials` getCredentials check, doctor exit code 2 try/catch, next_steps recommends setup.
- `tests/cli.test.ts` — 19 deterministic tests: env save/restore, version subcommand, next_steps, expired credentials, setup reconfiguration, and exit codes 0/1/2.
- `tests/mcp-server-smoke.test.ts` — built-bin smoke for CLI stdio, isolated-HOME doctor, non-TTY setup, and all four version entries.
- `docs/client-setup.md` — Agent doctor example uses full npx command.
- `docs/client-setup.en.md` — Same.
- `CHANGELOG.md` — Unreleased entries (unchanged from initial implementation).
- `CHANGELOG_EN.md` — Same.
- `docs/agent-memory/codemap.md` — Updated CLI and test entries (unchanged from initial implementation).
- `docs/agent-memory/decisions.md`, `handoff-log.md`, `project-facts.md`, `verification-log.md` — Codex final-review memory updates for the accepted CLI contract and verification evidence.
- `docs/qa/2026-07-27-cli-setup-doctor.md` — Updated with repair round details and re-verification.

Preserved: `docs/agent-memory/pending-learning-proposals.md` — Unrelated generated learning proposal modification left untouched.

## Commands Run

```bash
npm run build                        # Passed
npm test                             # 431 passed (26 files)
npm pack --dry-run                   # 138 files, correct excludes
npx vitest run tests/cli.test.ts tests/mcp-server-smoke.test.ts  # 30 passed (2 files)
node dist/cli.js --help              # Clean, single [command], 6 subcommands
node dist/cli.js doctor --json       # Valid JSON, no secrets, exit 0
node dist/cli.js -V                  # 1.10.1
node dist/cli.js -v                  # 1.10.1
node dist/cli.js version             # 1.10.1
echo '{}' | node dist/cli.js setup   # Non-TTY fast-fail, exit 1
git diff --check                     # Clean
git status --short                   # Expected files only
```

## Results

| Check | Result |
|---|---|
| Build (TypeScript) | Passed |
| Full test suite | 431 passed (26 files) |
| Focused CLI tests | 19 passed (env-safe, deterministic) |
| Built-entrypoint/MCP smoke | 11 passed |
| Package dry-run | 138 files, correct excludes |
| `--help` output | Single `[command]`, 6 subcommands, `-v` option listed |
| `doctor --json` | Valid JSON, no secrets, exit 0 |
| `-V` / `-v` / `version` | All print version correctly |
| Non-TTY `setup` | Fast-fail with guidance, exit 1 |
| Isolated-HOME `doctor --json` | Single JSON object, status `needs_credentials`, exit 1 |
| ESM guard | Verified: tests import from cli.ts without triggering stdio |
| Secret scan (manual) | No real credentials in changed source/docs/tests |
| MCP tool list | Unchanged (10 tools) |
| Stdio startup (dist/index.js) | Preserved |
| Stdio startup (dist/cli.js) | Preserved (new smoke test) |

## Diff Notes

- `src/cli.ts`: Net ~70 lines added. ESM guard wraps main(), `-v` option + handler, version subcommand, setupCredentials uses `getCredentials()` for loadability check, doctorCommand has try/catch for exit code 2, next_steps recommends `setup`.
- `tests/cli.test.ts`: 19 tests with env save/restore in beforeEach/afterEach. Removed the over-constrained exact-count test and added setup loadability plus exit-code 2 fault injection.
- `tests/mcp-server-smoke.test.ts`: built-bin coverage piggybacks on the existing `beforeAll` build; no second build hook was added.
- No changes to `src/index.ts`, `src/server.ts`, `src/bilibili/`, `src/utils/credentials.ts`, `src/utils/credential-guidance.ts`, `src/utils/update-check.ts`, or any MCP tool handler.
- No new dependencies.
- No package metadata or lockfile changes.

## Risks Or Skipped Checks

- **Doctor exit code 2**: Covered through deterministic fault injection at the command seam rather than a platform-fragile broken-environment subprocess.
- **Global credential state**: This machine has a valid `global_config` credential, so `doctor --json` reported `locally_ready`. The test suite uses mocked filesystem and isolated HOME to cover `needs_credentials`, `env`, and `global_config` paths independently.
- **Live Bilibili login**: Not validated. `doctor` is documented as local-only; `check_bilibili_credentials` remains the authoritative live check.
- **CLI test isolation**: `createCli()` returns a fresh `Command` instance. Tests save/restore BILIBILI_* env vars and do not share parser state.
- **CRLF warnings**: Windows-native line-ending warnings on `git diff --check` for changed Markdown/TS files; harmless and expected.

## Harness Artifacts

- **Task ticket**: Used — `docs/agent-memory/handoffs/2026-07-27-cli-setup-doctor-task-ticket.md` defines the frozen contract.
- **Research note**: Not required — no external research was needed.
- **QA checklist**: Updated — `docs/qa/2026-07-27-cli-setup-doctor.md` with repair round details and full re-verification evidence.
- **Codemap**: Updated in initial implementation — CLI entry description now mentions setup/doctor; test file entry covers CLI and smoke tests.
- **Harness security**: Reviewed — manual grep confirmed no real credentials in changed files. Test fixtures use obviously fake values. Env save/restore prevents test contamination.
- **Harness eval**: Deferred — this is a focused implementation + repair task, not a roadmap phase or release.

## Decision Points

None. The independent review findings were consistent with the task ticket and Codex handoff. No scope expansion was needed.

## Suggested Codex Review Focus

1. Verify the public JSON shape (`locally_ready`/`needs_credentials`, exit codes 0/1/2) matches expectations.
2. Confirm the expired/unloadable credential reconfiguration path in `setupCredentials` is correct.
3. Review the bilingual documentation npx command change for Agent-facing consistency.
4. Verify the ESM guard behavior: importing `src/cli.ts` should not trigger side effects.

## Codex Final Review Addendum

After the Claude repair report, Codex made these same-scope review corrections:

- routed lowercase `-v` through Commander's option event rather than a manual `process.argv` check
- moved no-argument stdio startup into the Commander root action so every CLI route uses one parser
- added injectable status/configure seams solely for deterministic exit-code-2 and expired-credential setup regressions
- moved isolated-HOME smoke state under the system Temp directory, removed inherited `BILIBILI_*` variables, and guarded recursive cleanup
- added the four-entry built version matrix and reran build, 30 focused tests, all 431 tests, the 138-file package dry run, CLI probes, diff integrity, and high-confidence secret scanning
- kept internal CLI handlers module-private while exporting only the CLI factory and deterministic doctor/setup test seams
- changed non-TTY setup guidance to complete `npx -y @xzxzzx/bilibili-mcp@latest ...` commands
- clarified and tested that an internal doctor failure emits a redacted stderr diagnostic, no misleading status JSON, and exit code `2`

These Codex additions are not represented as Claude-authored work. The unrelated `pending-learning-proposals.md` modification remained untouched.
