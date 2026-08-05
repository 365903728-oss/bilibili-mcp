# QA Checklist: CLI Setup And Doctor

- Title: CLI setup and doctor command QA
- Date: 2026-07-27
- Version or commit: 1.10.1 (Unreleased)
- Owner: Claude Code (DeepSeek) with Codex final review and repair
- Related ticket: `docs/agent-memory/handoffs/2026-07-27-cli-setup-doctor-task-ticket.md`
- QA type: `pre-release`

## Scope

In scope:

- CLI help output fix (no duplicated `[command]`)
- `setup` command (interactive, non-TTY fast-fail, expired/unloadable reconfiguration)
- `doctor --json` command (local-only, deterministic JSON, exit codes 0/1/2)
- `doctor` human-readable output
- `version` subcommand, `-v` flag, and Commander `-V`/`--version` compatibility
- No-argument stdio startup preserved (ESM guard, no import side-effects)
- Documentation updates (bilingual client-setup, changelogs)

Out of scope:

- ASR, model selection, audio download
- MCP tool schema/response changes
- Package version bump, commit, push, publish

## Preconditions

- [x] Current branch: `master`; task changes are present alongside the pre-existing unrelated `pending-learning-proposals.md` modification.
- [x] Expected package version: 1.10.1 (Unreleased).
- [x] Required credentials: available through global_config; not pasted into this file.
- [x] Test Bilibili video IDs or URLs: not needed (local-only commands).
- [x] MCP client or local CLI environment: Node.js v25.6.1, Windows 11.

## Automated Baseline

```bash
npm run build
npm test
npm pack --dry-run
```

Results:

- Build: Passed (TypeScript compilation clean).
- Tests: 431 passed across 26 files.
- Focused CLI and entrypoint tests: 30 passed (19 CLI unit tests plus 11 built-entrypoint/MCP smoke cases).
- Pack: 138 files, excludes tests, docs/qa, agent-memory, .env, .claude, .codex.
- Skipped checks: `npm view` registry check (publishing is out of scope).

## Package And Install Path

- [x] `package.json` version 1.10.1 matches intended Unreleased state.
- [x] `npm pack --dry-run` includes expected files and excludes tests, local config, `.env`, `.claude`, `.codex`, and docs not meant for npm.
- [x] `npm view` check skipped (not publishing).
- [x] `node dist/cli.js --help` works, lists setup, doctor, version, config, check, check-update. No duplicated `[command]`.
- [x] `node dist/cli.js -V` prints version.
- [x] `node dist/cli.js -v` prints version.
- [x] `node dist/cli.js version` prints version.
- [x] Local `bin`, `main`, `module`, and `types` still point to built `dist` output.

Notes:

- No package metadata changes; `npm pack --dry-run` shows same file count (138) as before.

## MCP Stdio And Tool Discovery

- [x] Stdio startup test passes (`tests/mcp-server-smoke.test.ts`).
- [x] `dist/cli.js` no-arg starts stdio server (new built-bin smoke test).
- [x] `tools/list` returns 10 expected tool names.
- [x] Tool descriptions unchanged; no credential exposure.
- [x] Tool schemas unchanged.

Expected tools (all present):

- `get_credential_setup_instructions`
- `check_bilibili_credentials`
- `check_mcp_update`
- `get_video_info`
- `get_video_comments`
- `get_video_transcript`
- `get_video_metadata`
- `get_video_chapters`
- `search_bilibili_videos`
- `list_bilibili_favorite_videos`

## Credential States

- [x] No raw Cookie values in `doctor --json` output (test: JSON contains no SESSDATA/bili_jct/DedeUserID values).
- [x] `doctor` JSON output stable: keys are `package_name`, `version`, `runtime`, `credentials`, `status`, `next_steps`.
- [x] `status` field only `locally_ready` or `needs_credentials`.
- [x] `credentials.source` only `env`, `global_config`, or `none`.
- [x] Non-TTY `setup` exits promptly with guidance (verified: piped input triggers fast-fail, exit code 1).
- [x] `doctor --json` exit code 0 for `locally_ready` (current machine has credentials).
- [x] `doctor --json` exit code 1 for `needs_credentials` (verified via isolated-HOME built-bin smoke test).
- [x] `doctor` exit code 2 for internal local-check failures (fault-injected unit regression).
- [x] An internal `doctor --json` failure emits a redacted stderr diagnostic and no misleading status JSON on stdout.
- [x] `setupCredentials` enters reconfiguration when credentials are expired/unloadable (injected loadability/configure regression).

## Tool Workflows

Not applicable (no MCP tool changes).

## Client Compatibility

Not applicable (local CLI changes only; no MCP protocol changes).

## Documentation Checks

- [x] README install command matches actual package behavior (unchanged).
- [x] Credential setup docs updated: recommend `setup`, mention `doctor --json` for Agents.
- [x] Agent-facing doctor example uses full npx command (`npx -y @xzxzzx/bilibili-mcp@latest doctor --json`), not bare global install command.
- [x] README and README_EN agree on the supported setup path.
- [x] Changelog (bilingual) mentions new `setup` and `doctor` commands, help fix, and doc guidance change.
- [x] Known limitations: `doctor` is local-only; it does not validate live Bilibili login. Documentation states `check_bilibili_credentials` is the authoritative live check.

## Security And Privacy Checks

- [x] No full Cookie values, npm tokens, GitHub tokens, `.env` content, or private credentials appear in CLI output.
- [x] `doctor --json` output contains no raw credential values (verified via test).
- [x] Error messages redact credential-like values (unchanged from existing `redactSecrets` usage).
- [x] No new external inputs or API calls in `doctor` command.
- [x] ESM guard prevents importing `src/cli.ts` from accidentally starting stdio server.
- [x] CLI tests save and restore BILIBILI_* env vars for determinism; no real credentials leak into test fixtures.

## Repair Round (2026-07-27)

Independent review fixes applied:

1. **ESM guard**: Added `import.meta.url === process.argv[1]` check before calling `main()`; importing `src/cli.ts` no longer starts stdio.
2. **setupCredentials expired check**: Changed from `getCredentialSource()` to `getCredentials()` null check; expired/unloadable credentials now enter reconfiguration instead of showing "already configured."
3. **Doctor exit code 2**: Wrapped `doctorCommand` body in try/catch; internal failures set `process.exitCode = 2` while `needs_credentials` stays 1 and `locally_ready` stays 0.
4. **Doctor next_steps**: Changed from recommending `config` to recommending `setup`.
5. **Version command compatibility**: Preserved old `version` subcommand and `-v` flag alongside Commander's `-V`/`--version`; both option forms now use Commander dispatch.
6. **Removed over-constrained test**: Deleted "has exactly 5 subcommands" test; replaced with softer version subcommand existence check.
7. **Deterministic env handling**: Added save/restore of BILIBILI_* env vars in test beforeEach/afterEach.
8. **Built-bin smoke**: Added `dist/cli.js` no-arg stdio, isolated-HOME `doctor --json` exit 1, non-TTY `setup` fast-fail, and four version-entry cases. Temporary HOME state is created under the system Temp directory and credential environment variables are removed from the child.
9. **Docs npx command**: Changed bare `bilibili-mcp doctor --json` to `npx -y @xzxzzx/bilibili-mcp@latest doctor --json` in both client setup guides.
10. **Non-TTY guidance**: The `setup` fast-fail message now uses complete `npx -y @xzxzzx/bilibili-mcp@latest ...` commands, so it does not assume a global install.
11. **Minimal test surface**: Internal CLI handlers remain module-private; only the CLI factory and deterministic doctor/setup test seams are exported.
12. **Internal-failure contract**: Exit `2` produces a redacted stderr diagnostic and no status JSON, covered by a regression assertion.

Post-repair verification:

```bash
npm run build                          # Passed
npm test                               # 431 passed (26 files)
npm pack --dry-run                     # 138 files
npx vitest run tests/cli.test.ts tests/mcp-server-smoke.test.ts  # 30 passed
node dist/cli.js --help                # Clean, single [command], 6 subcommands
node dist/cli.js doctor --json         # Valid JSON, no secrets
node dist/cli.js -V / -v / version     # All print 1.10.1
echo '{}' | node dist/cli.js setup     # Fast-fail, exit 1
```

## Result

- Overall result: `pass`
- Blocking issues: None
- Non-blocking caveats: None
- Follow-up tickets: None
- Codemap update status: Updated (CLI entry description and test file entries)
- Research note link: Not required (no external research needed)
