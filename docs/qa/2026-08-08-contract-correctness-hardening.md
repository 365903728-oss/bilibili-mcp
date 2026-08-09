# QA: Contract Correctness Hardening

## QA Session

- Title: Comments, language, credential, numeric-config, and JSON `-403` contract hardening
- Date: 2026-08-08
- Version or commit: `1.11.3` baseline at `1b97183c70145eaf273bbddef4e0474e53bc177e`
- Owner: Codex
- Related ticket: `docs/agent-memory/handoffs/2026-08-08-contract-correctness-hardening-task-ticket.md`
- QA type: `MCP tool change | credential flow | regression`

## Scope

In scope:

- Comments `limit` schema and main-comment semantics.
- Canonical supported languages, `ai-zh` preservation, and unknown-language rejection.
- Blank credential replacement protection using an isolated temporary home and synthetic fixtures.
- Strict numeric environment parsing, including `.env`-before-config entrypoint ordering.
- Endpoint-aware plain JSON `-403` classification and resource-generic recovery guidance.
- Full build, test, stdio, package, audit, diff, lockfile, and scoped secret verification.

Out of scope:

- Live Bilibili or real-Cookie validation, ready-model ASR, third-party desktop clients, dependency upgrades, commits, publication, deployment, and remote writes.

## Preconditions

- [x] Detached implementation baseline and commit recorded.
- [x] Package version `1.11.3` recorded.
- [x] Tests use only synthetic credentials; no real credential source is read or recorded.
- [x] The shareable synthetic BVID fixture is used only with mocked business/network paths.
- [x] Node `v25.6.1`, npm `11.16.0`, Vitest, and the built stdio entrypoint were identified.

## Automated Baseline

- Build: `npm run build` passed.
- Tests: final `npm test` passed, 41 files / 857 tests.
- Focused contract tests: 10 files / 358 tests passed before the final bootstrap regression was added; the final full suite includes all focused coverage.
- Post-review focus: comments/config/validation/server tests passed, 5 files / 212 tests; the comments file alone passed 29 tests after the pagination regressions ran red then green.
- Stdio: real child-process `initialize` → exact `tools/list` → representative `tools/call` passed, including an unsupported-language wire assertion.
- Pack: `npm pack --dry-run --json --ignore-scripts` passed with 185 files, 1,088,447 packed bytes, and 1,717,397 unpacked bytes; all required entrypoints were present and forbidden paths were zero.
- Audit: `npm audit --omit=dev --json` passed with zero production vulnerabilities across 97 production dependencies.
- Skipped: live Bilibili, real credentials, ASR E2E, external `npx`, and desktop-client QA were intentionally not run.

## Package And Install Path

- [x] Package version remains `1.11.3`; the isolated source branch is not a release candidate.
- [x] Dry-run package includes `dist/index.js`, `dist/index.d.ts`, `dist/cli.js`, `dist/load-env.js`, `package.json`, and `LICENSE`.
- [x] Dry-run package excludes source, tests, agent memory, QA records, local config, `.env`, keys, and credential files.
- [x] Existing `bin`, `main`, `module`, and `types` targets resolve to built `dist` output.
- Registry and external exact-version smoke were not rerun because no publication or registry state is in scope.

## MCP Stdio And Tool Discovery

- [x] The built server keeps stdout JSON-clean before protocol traffic.
- [x] `tools/list` returns the unchanged ten-tool set.
- [x] Comments and language descriptions match their public schemas.
- [x] `get_video_comments.limit` is `integer`, minimum 1, maximum 50.
- [x] Both `preferred_lang` schemas use the canonical supported-language enum.

Expected tools:

- `get_credential_setup_instructions`
- `check_bilibili_credentials`
- `check_mcp_update`
- `get_video_info`
- `get_video_transcript`
- `get_video_metadata`
- `get_video_comments`
- `search_bilibili_videos`
- `list_bilibili_favorite_videos`
- `get_video_chapters`

## Credential States

- [x] A trimmed-empty synthetic field leaves the existing file bytes and in-memory credentials unchanged, reports failure, and stops setup before the ASR prompt.
- [x] A complete synthetic credential set is trimmed and persisted only under an isolated temporary home.
- [x] HTTP tests mock credential headers as empty and assert the nav request contains no Cookie.
- Live no-credential, expired, and valid-login checks were not run because they require an external user session.

## Tool Workflows

- [x] `limit: 1` with replies returns one main comment plus bounded child replies.
- [x] Multi-page requests keep upstream `ps=20`, slice the caller-visible main-comment limit locally, and continue across a non-empty short page without exceeding `ceil(limit / 20)` requests.
- [x] Raw-page exhaustion is tracked separately from normalized output, so rejected rows cannot hide later valid rows or pages.
- [x] Only an explicit empty `replies` array means exhaustion; a missing or non-array container fails closed as `UpstreamResponseError`.
- [x] Video-info and transcript handlers pass `ai-zh` unchanged and reject unsupported languages before business work.
- [x] Nav and Favorites JSON `-403` map to `ACCESS_DENIED`; only an explicitly paid video endpoint/message maps to `PAID_VIDEO`.
- [x] HTTP status 403 remains a separate `NetworkError` path.
- [x] Successful response shapes and tool names remain unchanged.

## Client Compatibility

| Client | Version | Install method | Result | Notes |
|---|---|---|---|---|
| Claude Desktop | not tested | not tested | not tested | No external client launch in scope |
| Cursor | not tested | not tested | not tested | No external client launch in scope |
| Codex | local test harness | built stdio | pass | Public JSON-RPC child-process smoke |

## Documentation Checks

- [x] Bilingual tool references define comments `limit`, supported languages, and resource-generic `ACCESS_DENIED` guidance consistently.
- [x] Bilingual client setup and tool references document strict numeric values and timer bounds.
- [x] Credential docs remain secret-safe; no README or changelog update is needed before a future release decision.

## Security And Privacy Checks

- [x] Scoped value-free scan found zero private-key, GitHub-token, npm-token, AWS-key, or JWT patterns.
- [x] Credential-shaped matches are limited to bilingual placeholder documentation, verification prose, and explicitly synthetic CLI fixtures.
- [x] No real credential, `.env` content, or private value was read into test output.
- [x] Runtime input validation occurs before Bilibili business calls for unsupported languages.
- [x] Existing network, response, and stdio budgets remain covered by the full regression suite.

## Result

- Overall result: `pass with caveats`
- Blocking issues: none
- Non-blocking caveats: no real Cookie, ready-model ASR, or external desktop-client QA; no version bump, tag, package publication, or release is part of this source delivery.
- Follow-up tickets: none required for this batch.
- Codemap update status: updated for `src/load-env.ts`, strict config, and new tests.
- Research note: not required; no external facts affected implementation.
- Independent review: the initial `risk-reviewer` passed. The 2026-08-09 two-axis review then found and drove the pagination, raw-exhaustion, malformed-container, shared-language, and ticket-status corrections; final standards and specification re-reviews both returned PASS with no remaining P0–P3.
