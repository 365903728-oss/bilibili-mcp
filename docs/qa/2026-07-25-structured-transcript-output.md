# QA Checklist: Structured Transcript Output

## QA Session

- Title: `get_video_transcript` structured output pilot
- Date: 2026-07-25
- Version or commit: package `1.7.2`; implementation commit `29f663a` on `master`
- Owner: Codex
- Related ticket, plan, PRD, or release: GitHub Issue #16; `docs/structured-transcript-output-prd.md`
- QA type: `MCP tool change`

## Scope

In scope:

- `get_video_transcript.outputSchema`
- Successful dual text and `structuredContent` results
- Text-only validation and runtime errors
- Local stdio discovery/call, package contents, and Codex client compatibility

Out of scope:

- Other tools gaining structured output
- New transcript data or Bilibili requests
- Claude Desktop, Cursor, commit, push, version, changelog, and release

## Preconditions

- [x] Current branch and commit recorded.
- [x] Expected package version recorded.
- [x] Valid credentials are available to a newly started local MCP process.
- [x] Test Bilibili video ID is safe to share: `BV1vL411G7N7`.
- [x] Client environments identified: MCP SDK `1.27.1`; Codex CLI `0.144.6`.

No Cookie value or credential field is stored in this checklist.

## Automated Baseline

- Build: pass, `npm run build`.
- Focused tests: pass, 2 files / 39 tests. The two new contract assertions failed before implementation and passed afterward.
- Full tests: pass, 23 files / 290 tests.
- Pack: pass, 124 files; `dist/index.js` included; `src/` and `.env` files excluded.
- Diff: pass, `git diff --check`.
- Credentialed client checks: pass with a fresh local process through the official SDK and Codex CLI.

## Package And Install Path

- [x] Package version remains `1.7.2`; no release preparation was requested.
- [x] `npm pack --dry-run --json` contains expected built output and excludes source and environment files.
- [x] Local `bin`, `main`, `module`, and `types` still point to `dist`.
- [x] Package metadata, dependencies, and lockfile are unchanged.

## MCP Stdio And Tool Discovery

- [x] Existing stdio startup regression passes in the full suite.
- [x] Official SDK `tools/list` returns exactly eight tools in the existing order.
- [x] Only `get_video_transcript` declares an `outputSchema`.
- [x] Its required output fields are `bvid`, `data_source`, `transcript`, and `title`.
- [x] Credential-free invalid-input `tools/call` returns `isError` and omits `structuredContent`.
- [x] Credentialed successful `tools/call` returns both legacy JSON text and structured content in a fresh process.

Expected tools:

- `get_credential_setup_instructions`
- `check_bilibili_credentials`
- `check_mcp_update`
- `get_video_info`
- `get_video_comments`
- `get_video_transcript`
- `get_video_metadata`
- `get_video_chapters`

## Credential States

- [x] Invalid/expired credentials return `COOKIE_EXPIRED` with safe next steps and no raw Cookie values.
- [x] The supplied Netscape Cookie export was parsed from the system clipboard; only the three required fields were saved through the existing credential manager and exact round-trip equality was confirmed without displaying values.
- [x] Valid credentials are confirmed by a newly started local MCP process with `source: global_config` and `logged_in: true`.
- [x] Existing setup guidance points to the safe `config` and `check` CLI flow.

The initial fresh-process failure was caused by three stale credential lines in the ignored repository `.env`, which took precedence over the newly saved global configuration. Removing only those stale lines made the fresh process use `global_config`; the Bilibili login check then passed.

## Tool Workflow

- [x] Synthetic success fixture proves `structuredContent` equals the full search-mode `VideoTranscriptData`.
- [x] The legacy text is exactly `JSON.stringify(result, null, 2)`.
- [x] Validation, `NoSubtitleError`, and generic transcript failures omit `structuredContent`.
- [x] Existing transcript behavior and all other tool regressions pass.
- [x] Live subtitle-backed success is confirmed against `BV1vL411G7N7` from a fresh local process.

## Client Compatibility

| Client | Version | Connection | Result | Notes |
|---|---|---|---|---|
| Official TypeScript SDK | 1.27.1 | `Client` + `StdioClientTransport` to local `dist/index.js` | pass | Eight-tool discovery and credentialed subtitle call passed; parsed legacy JSON equals `structuredContent`, and the formatted text is exact. |
| Codex CLI | 0.144.6 | ephemeral inline `bilibili_local` stdio config | pass | Credentialed call succeeded, displayed the legacy JSON text, and raised no output-schema validation error. The model-facing Codex surface did not separately expose `structuredContent`; the SDK contract check is authoritative for that field. |
| Claude Desktop | not tested | not tested | not tested | Non-blocking for this pilot. |
| Cursor | not tested | not tested | not tested | Non-blocking for this pilot. |

The inline Codex probe did not modify global MCP configuration.

## Documentation Checks

- [x] README and README_EN each contain one equivalent dual-return sentence.
- [x] No duplicated schema reference was added to either README.
- [x] No changelog entry was added because versioning and release are out of scope.

## Security And Privacy Checks

- [x] No Cookie value, `.env` content, npm token, or GitHub token was written to source, tests, docs, or reports.
- [x] Credential diagnostics used only redacted status/error payloads.
- [x] Stale ignored `.env` credential lines were removed so the global credential source is authoritative.
- [x] Package dry run excludes `.env` files.
- [x] Existing input validation remains ahead of Bilibili calls.

## Result

- Overall result: `pass`
- Blocking issue: none.
- Required security follow-up: completed on 2026-07-26. A fresh MCP process verified the replacement session from `global_config` without displaying Cookie values.
- Non-blocking caveats: Claude Desktop and Cursor are untested; dual return increases response size; Codex displayed the legacy text but did not separately expose structured content to the model.
- Codemap update status: updated for declared output schemas and structured-output contract tests.
- Research note: `docs/research/2026-07-25-cross-platform-video-content-mcp-landscape.md`.
