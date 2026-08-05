# QA Session

- Title: Optional ASR model installation Phase 1
- Date: 2026-07-27
- Version or commit: 1.10.1 working tree (Unreleased)
- Owner: DeepSeek implementation with Codex final review
- Related: `docs/asr-model-install-prd.md`,
  `docs/agent-memory/handoffs/2026-07-27-asr-model-install-phase1-task-ticket.md`
- QA type: `package/install`

## Scope

In scope:

- Default-No setup choice.
- Fixed small managed install contract.
- Local ASR state and doctor output.
- Node engine/package boundary.
- No-regression CLI/MCP behavior.

Out of scope:

- Real model download in automated tests.
- Transcription, audio download, model selector, GPU.

## Preconditions

- [x] Current dirty worktree preserved.
- [x] Package version remains 1.10.1 Unreleased.
- [x] Tests use isolated temporary directories and synthetic process runners.
- [x] No credentials or private paths are recorded.

## Automated Baseline

```powershell
npm run build
npx vitest run tests/asr-installer.test.ts tests/cli.test.ts tests/mcp-server-smoke.test.ts
npm test
npm pack --dry-run --json --ignore-scripts
```

- Build: PASS — TypeScript compilation clean, `dist/asr/` emitted
- Focused tests (asr-installer 51, cli 33, mcp-server-smoke 11): 95 passed
- Full tests: 496 passed (27 files)
- Pack: 148 files, 140,199 bytes, `dist/asr/` included, no test/model/cache/state files leaked

## Installation Contract

- [x] Setup defaults to No (prompts `[y/N]`, "n" skips).
- [x] No path invokes no ASR runner and creates no ASR state.
- [x] Configured credentials still reach the ASR choice.
- [x] Yes uses pinned runtime/model/revision and private managed paths (`~/.bilibili-mcp/asr/`).
- [x] Python missing/failure is actionable and creates no ready marker.
- [x] Successful injected verification writes versioned state atomically (tmp + rename).
- [x] Rerun is safe (venv/pip re-runs idempotently; download retries).

## Doctor And CLI

- [x] `doctor --json` remains parseable and local-only.
- [x] ASR states are `not_installed`, `incomplete`, or `ready`.
- [x] No absolute user paths or secrets appear in doctor output.
- [x] Credential status/exit codes are unchanged (0=ready, 1=needs_credentials, 2=internal failure).
- [x] Help/version/no-argument stdio smoke passes.

## Package And Security

- [x] Node engine is `>=20.0.0` in package.json; `package-lock.json` updated via `npm install`.
- [x] No npm dependency added.
- [x] Pack contains no venv/model/cache/state/test/QA/memory files.
- [x] No Cookie, token, `.env`, private path, or real model artifact is tracked.
- [x] Child processes use executable + argument arrays (`shell: false`), never shell strings.

## Documentation

- [x] Chinese and English changelogs describe the same default-off fixed-model flow.
- [x] Phase 1 limitation says installation/readiness only, no transcription yet.
- [x] System FFmpeg is not listed as a prerequisite (PyAV bundles FFmpeg libraries).
- [x] Changelog, codemap, QA checklist, and report are current.

## Result

- Overall result: PASS — all automated and checklist items verified within scope
- Blocking issues: none
- Non-blocking caveats: real Python/model download not tested in CI (requires Python 3.9+ and network access)
- Phase 2 follow-up: bounded model selector after this phase passes review
