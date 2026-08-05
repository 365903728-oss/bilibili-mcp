# QA Checklist: Strix + DeepSeek Security Remediation

## QA Session

- Title: Strix + DeepSeek security remediation (SEC-2026-08-05-STRIX)
- Date: 2026-08-05
- Version or commit: package 1.10.1 (unreleased); worktree `0a1b`; HEAD `ab4dd02`
- Owner: Claude Code (implementation) / Codex (review)
- Related ticket, plan, PRD, or release: task ticket SEC-2026-08-05-STRIX; handoff `docs/agent-memory/handoffs/2026-08-05-strix-deepseek-security-remediation-codex-to-claude.md`
- QA type: `MCP tool change | credential flow | regression`

## Scope

In scope:

- Six validated Strix verdicts: V-01 bounded-text sanitization (C1, bidi overrides/embeds/isolates, zero-width/BOM, unpaired surrogates) for Bilibili-derived text with untrusted-data warnings; V-02 typed `ValidationError` for non-string `bvid_or_url` and genericized unexpected validation errors; V-05 subtitle URL exact-host/no-custom-port/no-userinfo enforcement; V-03/V-04 ASR root 0700, unique `wx`/0600 temp state file with atomic rename, lstat-based symlink rejection of managed paths in the ready gate; dependency SDK `^1.30.0` compatible lockfile refresh.
- Deterministic regression tests for all six verdicts.

Out of scope:

- Live Bilibili/Cookie acceptance; ready-model/live-ASR E2E; model or Python package downloads; published release; README/changelog updates (per handoff "Things Not To Change"); the pre-existing dirty baseline (127 entries preserved untouched).

## Preconditions

- [x] Current branch and commit recorded (HEAD `ab4dd02`, worktree `0a1b`).
- [x] Expected package version recorded (1.10.1, unchanged).
- [x] Required credentials are available only through approved external sources, not pasted into this file (no credentials used at all this session).
- [x] Test Bilibili video IDs or URLs are safe to share (no live requests made).
- [x] MCP client or local CLI environment is identified (local Vitest stdio smoke only; no external client).

## Automated Baseline

Run when relevant:

```bash
npm run build
npm test
npm pack --dry-run
```

Results:

- Build: **pass** — `npm run build` (tsc, Node16 ESM) exit 0, re-run after all four rounds.
- Tests: **pass** — full `npm test`: 39 test files, 803 tests, all passed (round 1: 765; repair round 1 added 5 → 770; repair round 2 added 18 → 788; repair round 3 added 5 → 793; round 4 added 10 matrix cases → 803). Focused runs: 7 touched files 347 tests (round 1); ASR files 152 tests (repair round 1); ASR files 170 tests (repair round 2); ASR files 175 tests (repair round 3); validation/handler files 150 tests (round 4).
- Pack: **pass** — `npm pack --dry-run --json --ignore-scripts`: 180 files, 788,704 unpacked bytes; contains `dist/` (built), LICENSE, README files, `assets/readme/`, `docs/client-setup*.md`, `docs/tool-reference*.md`; excludes `src/`, tests, `.env`, `.claude`, `.codex`.
- Audit: **pass** — `npm audit --omit=dev --json` reports **0 vulnerabilities** (total 0; 97 prod / 665 total dependencies; registry reachable again on 2026-08-05). `fast-uri` refreshed 3.1.4 → 3.1.5 via `npm update fast-uri` — the latest 3.x inside ajv@8.20.0's `^3.0.1` range, no override (the `latest` dist-tag 4.1.2 is a new major). Verified via `npm ls`: SDK `1.30.0`, `@hono/node-server@2.1.0`, `hono@4.13.0`, `express-rate-limit@8.6.2`, `ip-address@10.4.0`, `fast-uri@3.1.5`.

## Package And Install Path

- [x] `package.json` version matches the intended release or test version (1.10.1; no release in this task).
- [x] `npm pack --dry-run` includes expected files and excludes tests, local config, `.env`, `.claude`, `.codex`, and docs not meant for npm.
- [ ] `npm view @xzxzzx/bilibili-mcp version dist-tags --json` matches expected registry state — **skipped**: no publish in scope (registry reachable, but no publish was authorized).
- [ ] `npx -y @xzxzzx/bilibili-mcp@latest --help` or equivalent package smoke check — **skipped**: no publish in scope.
- [x] Local `bin`, `main`, `module`, and `types` still point to built `dist` output (verified in `package.json` and pack listing: `dist/cli.js`, `dist/index.js`, `dist/index.d.ts`).

Notes:

- `@modelcontextprotocol/sdk` raised `^1.30.0`; lockfile refreshed with compatible versions only (no overrides), including `fast-uri` 3.1.4 → 3.1.5 in round 4.

## MCP Stdio And Tool Discovery

- [x] Starting the MCP server does not print non-JSON logs to stdout before JSON-RPC traffic — covered by `tests/mcp-server-smoke.test.ts` (included in the 39 passing files).
- [x] `tools/list` returns the expected tool names — `tests/server-tools.test.ts` asserts the ten-tool registration and order.
- [x] Tool descriptions do not expose credentials or misleading setup instructions — descriptions only gained the appended untrusted-data warning (Chinese + English) on the 7 Bilibili text tools; `get_credential_setup_instructions`/`check_bilibili_credentials`/`check_mcp_update` unchanged.
- [x] Tool schemas match the intended public interface — no property/required/shape changes; description text only.

Expected tools:

- `get_credential_setup_instructions`, `check_bilibili_credentials`, `check_mcp_update`, `get_video_info`, `get_video_transcript`, `get_video_metadata`, `get_video_comments`, `get_video_chapters`, `search_bilibili_videos`, `list_bilibili_favorite_videos` (all 10 registered; order preserved).

Notes:

- `tests/server-tools.test.ts` adds an assertion that each of the 7 Bilibili text tools carries the untrusted-data warning.

## Credential States

Do not paste full Cookie values into this checklist.

- [x] No credentials: setup guidance is actionable and does not leak secrets — unchanged, still points at `get_credential_setup_instructions`.
- [x] Invalid or expired credentials: error code and `next_steps` are useful and do not leak secrets — pre-existing controls unchanged; this task made no credential-path behavior change.
- [x] Valid credentials: `check_bilibili_credentials` reports configured/login status without exposing Cookie values — unchanged.
- [x] Credential setup flow points users to `npx -y @xzxzzx/bilibili-mcp config` and `npx -y @xzxzzx/bilibili-mcp check` when relevant — unchanged.

Notes:

- No live credential states exercised (no real Cookie available/allowed this session); covered by existing credential-tool tests in the full suite.

## Tool Workflows

Use safe test videos and avoid recording private user data.

- [ ] `get_video_metadata` returns stable metadata fields — not run live; mocked tests pass.
- [ ] `get_video_info` returns expected video info and subtitle/description behavior — not run live; mocked tests pass.
- [ ] `get_video_transcript` handles available subtitles — not run live; mocked tests pass.
- [ ] `get_video_transcript` handles unavailable subtitles with clear fallback guidance — not run live; `NoSubtitleError` path tested.
- [ ] `get_video_comments` respects `detail_level`, `limit`, `sort`, and `include_replies` — not run live; mocked tests pass.
- [x] Validation errors are structured and useful for invalid BV IDs, URLs, language codes, or comment options — tool x input matrix (round 4): all 5 BVID tools × {number, boolean, object} `bvid_or_url` (15 cases) return `code: VALIDATION_ERROR`, `message: "bvid_or_url must be a string"` with stable wording (no engine text; `includes` never reflected) and the corresponding business mock asserted never called; genericized unexpected validation errors return the controlled `"Invalid input"` message.

Notes:

- No live Bilibili requests were made (handoff constraint); all workflow behavior verified through the deterministic test baseline (803 tests).

## Client Compatibility

Mark untested clients explicitly.

| Client | Version | Install method | Result | Notes |
|--------|---------|----------------|--------|-------|
| Claude Desktop | – | – | not tested | no publish, no client run |
| Cursor | – | – | not tested | no publish, no client run |
| Codex | – | – | not tested | no publish, no client run |
| Other | – | – | not tested | stdio smoke covered by tests/mcp-server-smoke.test.ts |

## Documentation Checks

- [ ] README install command matches actual package behavior — unchanged (out of scope).
- [ ] Credential setup docs do not suggest putting Cookie values in MCP client config — unchanged.
- [ ] README and README_EN agree on the supported setup path — unchanged.
- [ ] Changelog or release notes mention user-visible changes — not applicable: no release in this task; handoff forbids changelog edits.
- [x] Known limitations are documented when behavior is intentionally partial — residual boundaries (no live ASR E2E, no live Bilibili acceptance) are recorded in this checklist and the Claude report; the dependency closure (fast-uri 3.1.5, zero audit vulnerabilities) is documented in the research note.

Notes:

-

## Security And Privacy Checks

- [x] No full Cookie values, npm tokens, GitHub tokens, `.env` content, or private credentials appear in logs, reports, docs, tests, or package output — full-diff scan for `SESSDATA=`/`bili_jct=`/`DedeUserID=`/`Cookie:` found only value-free patterns (redaction output `***`, placeholder `configured=1`, `Cookie: expect.anything()` test assertions, prompt text); no real values.
- [x] Error messages and retry logs redact credential-like values — pre-existing redaction preserved; `buildValidationErrorPayload` now genericizes unexpected exceptions so engine wording never leaks.
- [x] External inputs are validated before Bilibili API calls — non-string `bvid_or_url` rejected with typed `ValidationError` before any business/network call (asserted `not.toHaveBeenCalled()` on mocks); subtitle URLs validated (exact host, no custom port, no userinfo) before fetch.
- [x] Network responses that may be large or redirected are bounded or rejected according to current policy — pre-existing response-size and redirect controls preserved; subtitle line sanitization strips C1/bidi/zero-width without truncating legitimate long lines.

Notes:

- ASR state writes: root created 0700, state written via `.state-<randomUUID()>.tmp` with `wx`/0600 (stdlib `crypto.randomUUID`, injectable `randomId` for tests; PID+counter naming removed), atomic rename, no temp residue (checked `~/.bilibili-mcp/asr` and repo — none found). Repair round 2: `writeAsrState` independently rejects a symlinked or non-directory root *before* any write/rename (never follows a symlink; no-side-effect tests assert write/rename/unlink/mkdir/chmod never called), enforces owner-only 0700 on an existing real root via `chmodSync`, and creates an absent root owner-only without a chmod attempt. Repair round 3: chmod failures fail closed — `EPERM`/`EACCES` rethrow before mkdir/write/rename (no-side-effect tests); only explicitly unsupported codes (`ENOSYS`/`EOPNOTSUPP`, plus `EINVAL` on Windows) skip the 0700 enforcement.
- Ready gate rejects symlinked managed paths (state file, venv dir, bin dir, venv python, model dir, model.bin, config.json, tokenizer.json, vocabulary.txt) and fails closed when a path cannot be inspected. Repair round 1: `readAsrState` lstat/fail-closes on the ASR root and `stateFile` *before* any read — a symlinked root or state file is never followed/read and never `ready`; tests assert `readFileSync` is never called in those cases (real-fs root-symlink test included). Repair round 2: the ready gate verifies expected *path types*, not merely non-symlink — root/venv/bin/model are real directories, state/python executable/required model artifacts are real files; a directory in a file slot or a file in a directory slot never returns `ready` (18 new tests, including state-as-directory and root-as-file with `readFileSync` asserted never called).
- ASR install root guard (repair rounds 2 + 3): `runAsrInstallation` fails with `success: false` *before* any unlink/mkdir/spawn/download/mutation when an existing ASR root is a symlink or not a real directory ("Refusing ASR install: root is a symlink or not a directory"), fails closed on uninspectable roots, and allows an absent root through — only `ENOENT` means absent; an `ENOTDIR` (invalid/non-directory path component) also fails closed before any spawn or mutation (regression test asserts spawnFn/fsMkdirSync/fsUnlinkSync never called); tests assert spawnFn/fsMkdirSync/fsUnlinkSync are never called for symlink/non-directory roots and that an absent root reaches spawn.

## Result

- Overall result: `pass with caveats`
- Blocking issues: none.
- Non-blocking caveats:
  - No live Bilibili/Cookie acceptance and no ready-model/live-ASR E2E were run (handoff constraint); behavior verified through 803 deterministic tests.
  - Round 4 closed the earlier `fast-uri` caveat: the registry became reachable, `fast-uri` was refreshed 3.1.4 → 3.1.5 inside the compatible `^3.0.1` range (no override), and `npm audit --omit=dev --json` now reports zero vulnerabilities; the obsolete "4.1.2 / unreachable" claim is corrected in the research note and Claude report.
  - The round-1 risk-reviewer subagent was cancelled by the user before producing a result (not relaunched); all three same-scope repair rounds were instead issued directly by the user — round 2 from an independent review (P1 install/write root guards, P2 path-type ready gate), round 3 final minimal repair (ENOTDIR fails closed; chmod fails closed except unsupported codes) — and are fully implemented and tested (see Security And Privacy Checks).
- Follow-up tickets: none in scope.
- Codemap update status: checked — no structural code change (no new modules, no moved boundaries); `docs/agent-memory/codemap.md` left unchanged.
- Research note link, if external facts affected QA: `docs/research/2026-08-05-strix-deepseek-security-remediation-dependencies.md` (dependency advisory classification; Resolution section records the fast-uri 3.1.5 compatible closure and zero-vulnerability audit).
