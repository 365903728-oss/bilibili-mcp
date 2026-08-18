# Verification Log

## 2026-07-20

- Command: `npm run build`
- Result: Passed. TypeScript compiled after dist/ clean.
- Area: v1.7.1 source preparation.

- Command: `npm test`
- Result: 23 files, 244 tests passed.
- Area: Full Vitest suite.

- Command: `npm pack --dry-run --json`
- Result: Version 1.7.1, 124 entries, no auth.* or sentinel artifacts.
- Area: npm package contents.

- Command: `git diff --check`
- Result: Clean (LF/CRLF warnings only, expected on Windows).
- Area: Whitespace/conflict validation.

- Command: scoped status/diff review of `docs/agent-memory/pending-learning-proposals.md`
- Result: Its pre-existing generated-date modification remains outside this task and is excluded from the commit.
- Area: Scope boundary enforcement and preservation of user/runtime changes.

## 2026-05-27

- Command: `npm run build`
- Result: Passed before memory-system work.
- Area: Stabilization baseline.
- Caveat: This result does not verify the memory-system files because they are documentation and skill configuration.

- Command: `git status --short`
- Result: Worktree contains intentional deletes for `smithery.json` and `smithery.yaml`, plus untracked `AGENTS.md`, `CLAUDE.md`, and `docs/`.
- Area: Repository state before memory-system implementation.
- Caveat: Do not assume all untracked files belong to a single commit without reviewing scope.

## 2026-05-28

- Command: `node -e "JSON.parse(require('fs').readFileSync('.codex/hooks.json','utf8')); JSON.parse(require('fs').readFileSync('.claude/settings.local.json','utf8')); console.log('all hook json ok')"`
- Result: Passed.
- Area: Claude Code and Codex app hook JSON configuration.
- Caveat: This validates JSON syntax, not the external app trust prompt.

- Command: `powershell -NoProfile -ExecutionPolicy Bypass -File .\.codex\scripts\session-start.ps1`
- Result: Passed and printed repository context, git status, active roadmap, and project memory previews.
- Area: SessionStart hook script.
- Caveat: Output is bounded by script line limits.

- Command: Synthetic failed `npm run build` hook payloads through `post_tool_use.py --agent codex` and `post_tool_use.py --agent claude`, followed by `stop_summary.py`.
- Result: Passed. Runtime observations and stop summaries were written, and sample `SESSDATA` / `bili_jct` values were redacted.
- Area: PostToolUse and Stop hook scripts.
- Caveat: Synthetic payloads verify the parser and storage path, not every possible hook payload field.

- Command: `npm run build`
- Result: Passed.
- Area: TypeScript project baseline after hook configuration.
- Caveat: `npm test` is still a stub until the real test baseline is added.

- Command: `python .\.codex\scripts\context_budget.py`
- Result: Passed and wrote `docs/agent-memory/context-budget-report.md`.
- Area: ECC-inspired context budget audit.
- Caveat: Token counts are estimates based on local file sizes.

- Command: `node -e "JSON.parse(require('fs').readFileSync('.codex/hooks.json','utf8')); JSON.parse(require('fs').readFileSync('.claude/settings.local.json','utf8')); console.log('all hook json ok')"`
- Result: Passed after adding `PreCompact`.
- Area: Claude Code and Codex app hook JSON configuration.
- Caveat: Codex app may still require trust confirmation for changed hooks.

- Command: `'{\"event\":\"PreCompact\"}' | python .\.codex\scripts\pre_compact.py --agent codex` and `'{\"event\":\"PreCompact\"}' | python .\.codex\scripts\pre_compact.py --agent claude`
- Result: Passed and wrote pre-compact checkpoints for both agents.
- Area: PreCompact checkpointing.
- Caveat: Synthetic payload verifies script behavior, not the external app trigger.

- Command: Synthetic failed `npm run build` hook payloads through `post_tool_use.py --agent codex` and `post_tool_use.py --agent claude`.
- Result: Passed. Candidate rows include `candidate_id`, `scope`, `evidence_count`, `confidence`, and `promote_after_review`; sample secret fields were redacted.
- Area: Candidate scoring.
- Caveat: Confidence is a review signal only and does not auto-promote formal memory.

- Command: `python .\.codex\scripts\stop_summary.py --agent codex` and `python .\.codex\scripts\stop_summary.py --agent claude`
- Result: Passed and wrote strategic compact advice into both stop summaries.
- Area: Strategic compact reminders.
- Caveat: The reminder does not run compaction automatically.

- Command: `python .\.codex\scripts\generate_learning_proposals.py --source manual`
- Result: Passed and wrote `docs/agent-memory/pending-learning-proposals.md`.
- Area: Automated controlled learning proposal generation.
- Caveat: The file is a review queue only and does not promote entries into formal memory.

- Command: Task 1 local credential cleanup - replaced hard-coded `SESSDATA`, `bili_jct`, `DedeUserID` in `get_subtitle.py` with `os.environ.get()`.
- Result: Passed. Credential literal scan returned `found: []`. `git status --short --ignored get_subtitle.py` confirmed `!! get_subtitle.py` (git-ignored).
- Area: Stabilization roadmap Task 1.
- Caveat: `get_subtitle.py` is an ignored local debug script; this is a local-only cleanup with no repository-tracked diff.

## 2026-05-28 Task 6 Final Baseline Verification

- Command: `git status --short`
- Result: Expected changes only. M .gitignore, M .npmignore, M package-lock.json, M package.json, D smithery.json, D smithery.yaml, D src/smithery-test.ts. Untracked: .claude/, .codex/, AGENTS.md, CLAUDE.md, docs/, tests/.
- Area: Stabilization final baseline.

- Command: `npm run build`
- Result: Passed.
- Area: TypeScript compilation.

- Command: `npm test`
- Result: Passed. 3 test files, 45 tests (vitest v3.2.4, Node >=18 compatible).
- Area: Real test baseline.

- Command: `npm pack --dry-run`
- Result: Passed. 74 files, 552.9 kB. Package includes dist/index.js, dist/index.d.ts, dist/cli.js. Excludes dist/debug_subtitle2.mjs, dist/smithery-test.*, tests/, smithery.json, smithery.yaml, .env files.
- Area: Package contents.

- Command: Package metadata check
- Result: main=dist/index.js, module=dist/index.js, types=dist/index.d.ts, bin.bilibili-mcp=dist/cli.js, type=module. All correct.
- Area: Package entry points.

- Command: Smithery removal check
- Result: dev (undefined), build:smithery (undefined), @smithery/cli (undefined). Fully removed.
- Area: Smithery runtime cleanup.

- Remaining non-blocking risks:
  - Old Bilibili Cookie values were present in repository history and should be rotated.
  - `get_subtitle.py` is local-only cleanup (git-ignored), not a tracked fix.
  - `dist/server.cjs/` bundle (1.7MB) may warrant review but is outside stabilization scope.
  - npm audit: 23 vulnerabilities not introduced or fixed by stabilization changes.

## 2026-05-28 Hook And Memory Health Check

- Command: `node -e "JSON.parse(require('fs').readFileSync('.codex/hooks.json','utf8')); JSON.parse(require('fs').readFileSync('.claude/settings.local.json','utf8')); console.log('hook config json ok')"`
- Result: Passed.
- Area: Codex and Claude Code hook configuration.
- Caveat: This validates JSON syntax, not external app trust prompts.

- Command: `powershell -NoProfile -ExecutionPolicy Bypass -File .\.codex\scripts\session-start.ps1`
- Result: Passed with exit code 0 and printed bounded project context.
- Area: SessionStart hook.
- Caveat: A previous piped preview using `Select-Object -First` returned exit code 1 because the output pipe was closed early; the direct command passed.

- Command: `post_tool_use.py`, `pre_compact.py`, `stop_summary.py`, and `generate_learning_proposals.py` synthetic health checks for both `codex` and `claude`.
- Result: Passed. File artifacts were written, secret-like sample values were redacted, and stdout returned JSON `{"suppressOutput": true}` for write-file hooks.
- Area: Runtime observations, pre-compact checkpoints, stop summaries, and controlled learning proposal generation.
- Caveat: Synthetic failure observations are ignored by learning proposal generation and should not be promoted as lessons.

- Command: `python .\.codex\scripts\generate_learning_proposals.py --source claude`
- Result: Passed. `docs/agent-memory/pending-learning-proposals.md` currently has no proposals.
- Area: Controlled learning.
- Caveat: No proposal means the learning pipeline is functioning but has no approved durable lesson to promote from runtime candidates.

## 2026-05-28 Phase 2 Task 1-2 Verification

- Command: `npm test -- tests/bilibili-video-api.test.ts`
- Result: Passed. 1 test file, 3 tests.
- Area: Phase 2 Task 1 subtitle API behavior baseline and Task 2 WBI extraction regression check.
- Caveat: Tests use mocked fetch and do not call live Bilibili APIs.

- Command: `npm test`
- Result: Passed. 4 test files, 48 tests.
- Area: Phase 2 Task 1 full test verification after adding API-level subtitle tests.
- Caveat: API behavior coverage currently focuses on subtitle fallback and subtitle content URL normalization.

- Command: `npm run build`
- Result: Passed after extracting WBI signing into `src/bilibili/wbi.ts`.
- Area: Phase 2 Task 2 TypeScript and Node ESM compatibility.
- Caveat: PowerShell displayed mojibake for Chinese comments, but Python UTF-8 reads showed `wbi.ts` content is valid UTF-8.

- Command: `npm test -- tests/bilibili-video-api.test.ts`
- Result: Passed after extracting buvid fingerprint handling into `src/bilibili/fingerprint.ts`.
- Area: Phase 2 Task 3 subtitle fallback regression check.
- Caveat: Tests use mocked fetch and do not call live Bilibili APIs.

- Command: `npm run build`
- Result: Passed after extracting buvid fingerprint handling into `src/bilibili/fingerprint.ts`.
- Area: Phase 2 Task 3 TypeScript and Node ESM compatibility.
- Caveat: PowerShell displayed mojibake for Chinese comments, but Python UTF-8 reads showed `fingerprint.ts` content is valid UTF-8.

- Command: `npm test`
- Result: Passed. 4 test files, 48 tests after extracting HTTP helpers into `src/bilibili/http.ts`.
- Area: Phase 2 Task 4 full regression check.
- Caveat: Tests use mocked fetch for subtitle API behavior and do not call live Bilibili APIs.

- Command: `npm run build`
- Result: Passed after extracting HTTP helpers into `src/bilibili/http.ts`.
- Area: Phase 2 Task 4 TypeScript and Node ESM compatibility.
- Caveat: `retryableFetch` and `throttledFetch` are temporarily exported because `getSubtitleContent()` still lives in `client.ts`; Task 5 should move that consumer into `video-api.ts`.

- Command: `npm test`
- Result: Passed. 4 test files, 48 tests after extracting video and subtitle API functions into `src/bilibili/video-api.ts`.
- Area: Phase 2 Task 5 full regression check.
- Caveat: Subtitle API tests use mocked fetch and do not call live Bilibili APIs.

- Command: `npm run build`
- Result: Passed after extracting video and subtitle API functions into `src/bilibili/video-api.ts`.
- Area: Phase 2 Task 5 TypeScript and Node ESM compatibility.
- Caveat: `client.ts` still contains comments API logic until Task 6.

- Command: `npm test`
- Result: Passed. 4 test files, 48 tests after extracting comments API logic into `src/bilibili/comments-api.ts`.
- Area: Phase 2 Task 6 full regression check.
- Caveat: Existing automated tests do not directly exercise comments API fallback behavior.

- Command: `npm run build`
- Result: Passed after converting `src/bilibili/client.ts` to compatibility re-exports.
- Area: Phase 2 Task 6 and Task 7 TypeScript and Node ESM compatibility.
- Caveat: Public export compatibility was also checked through built `dist/bilibili/client.js`.

- Command: `node -e "import('./dist/bilibili/client.js').then(...)"`
- Result: Passed. `checkLoginStatus`, `fetchWithWBI`, `fetchWithoutWBI`, `getVideoInfo`, `getVideoSubtitle`, `getSubtitleContent`, and `getVideoComments` are all functions.
- Area: Phase 2 Task 7 compatibility exports.
- Caveat: This verifies export presence, not live Bilibili API behavior.

## 2026-05-28 Phase 2 Final Verification

- Command: `npm run build`
- Result: Passed.
- Area: Final Phase 2 TypeScript compilation.

- Command: `npm test`
- Result: Passed. 4 test files, 48 tests.
- Area: Final Phase 2 regression suite.
- Caveat: Comments API fallback behavior remains a residual untested path.

- Command: `npm pack --dry-run`
- Result: Passed. 94 files, 554.9 kB. Package includes `dist/bilibili/client.*`, `http.*`, `wbi.*`, `fingerprint.*`, `video-api.*`, and `comments-api.*`.
- Area: Final Phase 2 package contents.
- Caveat: `dist/server.cjs/index.cjs.map` remains large but unchanged from the stabilization-era residual risk.

- Command: `node -e "import('./dist/bilibili/client.js').then(...)"`
- Result: Passed. All 7 compatibility exports are functions.
- Area: Final Phase 2 public import compatibility.

- Command: `git status --short`
- Result: Phase 2 files are present alongside pre-existing agent/hooks and memory/doc changes.
- Area: Final Phase 2 worktree scope.
- Caveat: Agent/hooks configuration changes are still unrelated to the code split and should be committed separately if the user wants separate history.

## 2026-05-28 Active Plan Tracking Verification

- Command: `python .codex/scripts/plan_tracker.py`
- Result: Returned `docs\superpowers\plans\2026-05-28-mcp-tool-surface-implementation-plan.md`.
- Area: Controlled learning active-plan resolution.
- Caveat: The tracker chooses the first incomplete implementation plan in project roadmap order and preserves an already-active incomplete plan.

- Command: `python .codex/scripts/generate_learning_proposals.py --source codex` and `python .codex/scripts/generate_learning_proposals.py --source claude`
- Result: Passed. Both Codex and Claude runtime `learning-proposal-phase-state.json` files now point at `2026-05-28-mcp-tool-surface-implementation-plan.md` with completed count `0`.
- Area: Phase-gated learning proposal reminders.
- Caveat: No learning proposal is generated unless runtime candidates meet the promotion threshold.

- Command: Synthetic PreCompact payload through `pre_compact.py --agent codex`
- Result: Passed. The pre-compact checkpoint now records the Phase 3 MCP tool surface implementation plan as the active roadmap.
- Area: PreCompact checkpointing.
- Caveat: Synthetic payload verifies script behavior, not the external app trigger.

## 2026-05-28 Phase 3 Task 1 Verification

- Command: `npm test -- tests/server-tools.test.ts`
- Result: Passed. 1 test file, 8 passed tests, 2 todo tests for planned Phase 3 tools.
- Area: Phase 3 Task 1 MCP tool surface baseline.
- Caveat: The test invokes the registered `tools/list` handler through the MCP SDK server's internal `_requestHandlers` map. This avoids starting stdio transport, but may need adjustment if the SDK internal shape changes.

- Command: `npm test`
- Result: Passed. 5 test files, 56 passed tests, 2 todo tests.
- Area: Phase 3 Task 1 full regression suite.
- Caveat: The 2 todo tests intentionally represent future `get_video_transcript` and `get_video_metadata` schema assertions.

- Command: `npm run build`
- Result: Passed.
- Area: Phase 3 Task 1 TypeScript compilation.

## 2026-05-28 Phase 3 Task 2 Verification

- Command: `npm test -- tests/validation.test.ts`
- Result: Passed. 30 validation tests.
- Area: Phase 3 Task 2 comment option validation.
- Caveat: `validateCommentSort("")` was initially accepted as falsy and then corrected to throw; `undefined` remains the only absent-value pass-through.

- Command: `npm test`
- Result: Passed. 5 test files, 69 passed tests, 2 todo tests.
- Area: Phase 3 Task 2 full regression suite.

- Command: `npm run build`
- Result: Passed.
- Area: Phase 3 Task 2 TypeScript compilation.

## 2026-05-28 Phase 3 Task 3 Verification

- Command: `npm test -- tests/bilibili-comments-tool.test.ts`
- Result: Passed. 12 comment wrapper tests.
- Area: Phase 3 Task 3 comment wrapper option controls.
- Caveat: The first test version introduced mojibake in test descriptions/comments; this was corrected and verified with `rg -n "鈥|鈫|�|—|→" tests/bilibili-comments-tool.test.ts` returning no matches.

- Command: `npm test`
- Result: Passed. 6 test files, 81 passed tests, 2 todo tests.
- Area: Phase 3 Task 3 full regression suite.

- Command: `npm run build`
- Result: Passed.
- Area: Phase 3 Task 3 TypeScript compilation.

## 2026-06-04 Phase 3 Task 4 Verification

- Command: `npm test -- tests/bilibili-metadata.test.ts`
- Result: Passed. 8 metadata wrapper tests.
- Area: Phase 3 Task 4 metadata-only wrapper.
- Caveat: Tests mock `getVideoInfo()` and do not call live Bilibili APIs.

- Command: `npm test`
- Result: Passed. 7 test files, 89 passed tests, 2 todo tests.
- Area: Phase 3 Task 4 full regression suite.

- Command: `npm run build`
- Result: Passed.
- Area: Phase 3 Task 4 TypeScript compilation.

- Command: `rg -n "鈥|鈫|�|—|→" src/bilibili/metadata.ts src/bilibili/types.ts tests/bilibili-metadata.test.ts`
- Result: No matches.
- Area: Phase 3 Task 4 encoding check.

## 2026-06-04 Phase 3 Task 5 Verification

- Command: `npm test -- tests/bilibili-transcript.test.ts`
- Result: Passed. 12 transcript wrapper tests.
- Area: Phase 3 Task 5 transcript-only wrapper.
- Caveat: Tests mock `getVideoInfo()`, `getVideoSubtitle()`, and `getSubtitleContent()` and do not call live Bilibili APIs.

- Command: `npm test`
- Result: Passed. 8 test files, 101 passed tests, 2 todo tests.
- Area: Phase 3 Task 5 full regression suite.

- Command: `npm run build`
- Result: Passed.
- Area: Phase 3 Task 5 TypeScript compilation.

- Command: `git diff -- src/bilibili/subtitle.ts tests/bilibili-transcript.test.ts src/bilibili/types.ts | Select-String -Pattern "→|—|鈥|鈫|�" -Context 1,1`
- Result: No output after replacing two newly added `→` arrows with `->`.
- Area: Phase 3 Task 5 new-content encoding check.

## 2026-06-04 Phase 3 Task 6 Verification

- Command: `npm test -- tests/server-tools.test.ts`
- Result: Passed. 17 MCP tool schema tests, 0 todo tests.
- Area: Phase 3 Task 6 MCP tool registration baseline.
- Caveat: These tests use the MCP SDK server's internal `_requestHandlers` map to inspect the `tools/list` response. Handler behavior is mostly covered through service-wrapper tests rather than direct MCP handler mocks.

- Command: `npm test`
- Result: Passed. 8 test files, 110 tests.
- Area: Phase 3 Task 6 full regression suite.

- Command: `npm run build`
- Result: Passed.
- Area: Phase 3 Task 6 TypeScript compilation and MCP server imports.

- Command: `npm pack --dry-run`
- Result: Passed. 98 files, 559.4 kB. Package includes updated `dist/server.*`, `dist/bilibili/metadata.*`, and Phase 3 wrapper outputs. No tests, `.env`, Smithery, or debug artifacts were reported in the tarball contents.
- Area: Phase 3 Task 6 package contents.

- Command: `bad-character scan for mojibake markers, replacement characters, em dash, and arrow in src/server.ts and tests/server-tools.test.ts`
- Result: No matches.
- Area: Phase 3 Task 6 new server/test encoding check.

## 2026-06-04 Phase 3 Task 7 Verification

- Command: `npm test`
- Result: Passed. 8 test files, 110 tests.
- Area: Phase 3 Task 7 documentation change regression suite.

- Command: `npm run build`
- Result: Passed.
- Area: Phase 3 Task 7 TypeScript compilation after updating `src/server.ts` schema descriptions.

- Command: `npm pack --dry-run`
- Result: Passed. 98 files, 560.1 kB. Package includes updated `README.md`, `README_EN.md`, and built `dist/server.*`.
- Area: Phase 3 Task 7 package contents.

- Command: `rg -n "detailed.*50|50.*detailed|前50|50 popular|#3-.*稳健性|#3-.*robustness" README.md README_EN.md src/server.ts`
- Result: No matches after review correction.
- Area: Phase 3 Task 7 stale documentation scan.

- Command: `git diff -U0 -- README.md README_EN.md src/server.ts | rg -n "^\\+.*(mojibake markers|replacement characters|em dash|arrow)"`
- Result: No matches for newly added bad characters. A full-file scan still matches pre-existing README Issue-contact punctuation outside the Phase 3 additions.
- Area: Phase 3 Task 7 new-content encoding check.

## 2026-06-04 Phase 3 Final Verification (Task 8)

- Command: `git status --short`
- Result: Expected changes — 14 modified (source, tests, docs, READMEs, config), 9 new untracked (plan/spec docs, new source modules, new test files). No unexpected artifacts.
- Area: Phase 3 final baseline.

- Command: `npm run build`
- Result: Passed.
- Area: TypeScript compilation with new MCP schemas and service wrappers.

- Command: `npm test`
- Result: Passed. 8 test files, 110 tests, 0 todo. All new wrapper tests pass. All existing tests pass (no regressions).
- Area: Phase 3 tool surface test baseline.

- Command: `npm pack --dry-run`
- Result: Passed. 98 files, 560.1 kB. Package includes new modules (metadata.ts, expanded server.ts). Excludes tests/, .env, Smithery artifacts, debug artifacts.
- Area: Package contents.

- Command: Contaminant scan (`smithery-test`, `debug_subtitle2`, `detailed=50` stale text)
- Result: Zero stale detailed=50 matches. Zero debug/Smithery artifacts in package. Only intentional `.npmignore` rule references `dist/smithery-test.*`.
- Area: Documentation and package hygiene.

- Command: Mojibake scan (new files and modified source/docs)
- Result: No new mojibake introduced. Pre-existing mojibake in `verification-log.md` (not Phase 3 scope).
- Area: Encoding check.

- Final tool list: `get_video_info` (unchanged), `get_video_comments` (expanded with limit/sort/include_replies), `get_video_transcript` (new), `get_video_metadata` (new).
- Phase 3 plan: Tasks 1-8 all marked complete.
- Remaining risks: No stdio-level MCP handler integration tests (wrapper behavior covered by unit tests). npm audit 23 vulnerabilities not introduced by Phase 3.

## 2026-06-04 Phase 4 Task 1 Public Surface Inspection

- Command: `git status --short`
- Result: Clean after removing generated `__pycache__/`.
- Area: Phase 4 Task 1 read-only inspection baseline.

- Command: `npm test`
- Result: Passed. 8 test files, 110 tests.
- Area: Release-polish baseline.

- Command: `npm run build`
- Result: Passed.
- Area: TypeScript compilation.

- Command: `npm pack --dry-run`
- Result: Passed. 98 files.
- Area: Package contents baseline.

- Finding: Actual MCP tool surface is `get_video_info`, `get_video_comments`, `get_video_transcript`, and `get_video_metadata`.
- Finding: `README.md` and `README_EN.md` already document all four tools and the expanded comment parameters.
- Finding: `CHANGELOG.md` and `CHANGELOG_EN.md` are missing a v1.3.8 entry for stabilization, client split, MCP tool expansion, Smithery removal, tests, and package cleanup.
- Finding: `package.json` metadata is publishable but description and keywords do not yet mention transcript and metadata.
- Finding: `.github/workflows/publish.yml` exists and appears to use trusted publishing/provenance, but lacks an `npm test` step before publish. Official docs verification is deferred to Phase 4 Task 5.

## 2026-06-04 Phase 4 Task 2 README Documentation Verification

- Command: `npm test`
- Result: Passed. 8 test files, 110 tests.
- Area: README documentation update regression check.

- Command: `npm run build`
- Result: Passed.
- Area: TypeScript compilation after README-only changes.

- Command: `npm pack --dry-run`
- Result: Passed. 98 files; updated `README.md` and `README_EN.md` are included.
- Area: Package contents check.

- Command: `rg -n '区分”|与”|鈥|鈫|�' README.md README_EN.md`
- Result: No matches after correcting the README Chinese quote pairing.
- Area: README encoding and typography check.

- Finding: README files now document no-cookie limitations, Cookie-backed credential sources, and caller behavior for `VALIDATION_ERROR`, `COOKIE_EXPIRED`, and `SUBTITLE_UNAVAILABLE`.
- Finding: Review follow-up fixed README TOC anchor drift for the behavior/error section and restored the environment requirements anchor.

## 2026-06-04 Phase 4 Task 3 Changelog Verification

- Command: `npm test`
- Result: Passed. 8 test files, 110 tests.
- Area: Changelog update regression check.

- Command: `npm run build`
- Result: Passed.
- Area: TypeScript compilation after changelog-only changes.

- Command: `npm pack --dry-run`
- Result: Passed. 98 files.
- Area: Package contents check.

- Command: `rg -n "hard-coded|硬编码|source code|源码|npm publish|GitHub release|tag pushed|SESSDATA=|bili_jct=|DedeUserID=|npm_[A-Za-z0-9]|ghp_[A-Za-z0-9]|鈥|鈫|�" CHANGELOG.md CHANGELOG_EN.md`
- Result: No matches after review correction.
- Area: Changelog overclaim, secret, and bad-character scan.

- Finding: `CHANGELOG.md` and `CHANGELOG_EN.md` now include a 1.3.8 section for Phase 1 stabilization, Phase 2 client split, Phase 3 MCP tool expansion, Smithery removal, Vitest baseline, package cleanup, and README updates.
- Finding: Credential-hardening wording avoids claiming npm publication, GitHub release/tag creation, or tracked source credential removal.

## 2026-06-04 Phase 4 Task 4 Package Metadata Verification

- Command: `node -e "const p=require('./package.json'); ..."`
- Result: Confirmed publish-critical fields unchanged: name `@xzxzzx/bilibili-mcp`, version `1.3.8`, `main`/`module` `dist/index.js`, `types` `dist/index.d.ts`, `bin.bilibili-mcp` `dist/cli.js`, `files` `[dist, README.md, README_EN.md, LICENSE]`, Node engine `>=18.0.0`.
- Area: Package metadata inspection.

- Command: `git diff -- package.json package-lock.json`
- Result: Only `package.json` description and keywords changed. `package-lock.json` unchanged.
- Area: Metadata diff review.

- Command: `rg -n "smithery|Smithery|debug_subtitle2|SESSDATA=|bili_jct=|DedeUserID=|npm_[A-Za-z0-9]|ghp_[A-Za-z0-9]" package.json package-lock.json`
- Result: No matches.
- Area: Package metadata secret and stale artifact scan.

- Command: `npm test`
- Result: Passed. 8 test files, 110 tests.
- Area: Package metadata regression check.

- Command: `npm run build`
- Result: Passed.
- Area: TypeScript compilation after metadata-only changes.

- Command: `npm pack --dry-run`
- Result: Passed. 98 files.
- Area: Package contents check.

- Finding: Description now mentions video metadata, transcripts, subtitles, and comment summarization.
- Finding: Keywords now include `transcript` and `metadata`.

## 2026-06-04 Phase 4 Task 5 Publish Workflow Verification

- Official docs checked: npm Trusted Publishers, npm provenance statements, GitHub Actions workflow syntax permissions, and GitHub Publishing Node.js packages documentation.
- Result: Trusted publishing requires npm CLI `11.5.1+` and Node `22.14.0+`; `id-token: write` is required for OIDC; `contents: read` is sufficient repository read permission; `registry-url: https://registry.npmjs.org/` is required for npm publishing setup.
- Area: Publish workflow documentation freshness.

- Command: `git diff -- .github/workflows/publish.yml`
- Result: Workflow now uses Node `22.14.0`, keeps `id-token: write` and `contents: read`, keeps npm registry setup, installs npm latest for trusted publishing support, runs `npm test` after `npm ci`, and keeps `npm publish --provenance --access public`.
- Area: Publish workflow diff review.

- Command: local YAML parse with PyYAML.
- Result: Parsed steps and permissions correctly. Caveat: PyYAML YAML 1.1 parsed the `on` key as boolean `True`; this is a local parser quirk and not a GitHub Actions syntax issue.
- Area: Workflow syntax sanity check.

- Command: `rg -n "NPM_TOKEN|NODE_AUTH_TOKEN|npm_[A-Za-z0-9]|ghp_[A-Za-z0-9]|smithery|Smithery|鈥|鈫|�" .github/workflows/publish.yml`
- Result: No matches.
- Area: Workflow token, Smithery, and bad-character scan.

- Command: `npm test`
- Result: Passed. 8 test files, 110 tests.
- Area: Publish workflow update regression check.

- Command: `npm run build`
- Result: Passed.
- Area: TypeScript compilation after workflow-only changes.

- Command: `npm pack --dry-run`
- Result: Passed. 98 files.
- Area: Package contents check.

- Finding: Workflow remains tag-triggered for `v*.*.*` and manually runnable via `workflow_dispatch`. No publish, tag, or release was performed.

## 2026-06-04 Phase 4 Task 6 Secret And Package Content Verification

- Command: secret scan over README files, changelogs, `package.json`, publish workflow, release-polish plan, and verification log.
- Result: Matches were limited to verification-log scan commands, plan placeholders such as `BILIBILI_SESSDATA=your_sessdata`, and plan checklist patterns such as `SESSDATA=...`; no real Cookie, npm token, or GitHub token values were found.
- Area: Secret scan.

- Command: `npm pack --dry-run`
- Result: Passed. 98 files. Included expected `package.json`, `README.md`, `README_EN.md`, `LICENSE`, `dist/index.js`, `dist/index.d.ts`, `dist/cli.js`, `dist/server.js`, and Bilibili dist modules.
- Area: Package contents.

- Finding: Tarball excludes tests, `.env`, local debug scripts, Smithery artifacts, `.claude`, `.codex`, `docs/agent-memory`, and runtime cache files.
- Finding: Hygiene scan hits for `.env`, `.codex`, `.claude`, `smithery-test`, and Smithery were documentation references or `.npmignore` exclusion rules, not package contents.

- Command: `npm test`
- Result: Passed. 8 test files, 110 tests.
- Area: Security/package review regression check.

- Command: `npm run build`
- Result: Passed.
- Area: TypeScript compilation.

## 2026-06-04 Phase 4 Final Verification (Task 7)

- Command: `git status --short`
- Result: Expected Phase 4 changes only (READMEs, changelogs, package.json, publish.yml, plan doc, verification log). No unexpected artifacts.
- Area: Phase 4 final baseline.

- Command: `npm run build`
- Result: Passed.
- Area: TypeScript compilation.

- Command: `npm test`
- Result: Passed. 8 test files, 110 tests, 0 todo.
- Area: Phase 4 release polish test baseline.

- Command: `npm pack --dry-run`
- Result: Passed. 98 files. Includes all expected dist and docs. Excludes tests/, .env, debug artifacts, Smithery artifacts, .claude/, .codex/, docs/agent-memory/.
- Area: Package contents.

- Command: Schema alignment scan (all 4 tools in READMEs and server.ts)
- Result: Confirmed. get_video_info, get_video_comments, get_video_transcript, get_video_metadata all present with correct params.
- Area: Documentation alignment.

- Command: Stale text scan (detailed=50, overclaims, hard-coded source code removal)
- Result: Only legitimate security best-practice warnings in READMEs ("Never hard-code Cookie values"). Changelogs clean. No overclaims.
- Area: Documentation accuracy.

- Command: Secret scan (NPM_TOKEN, NODE_AUTH_TOKEN, real tokens)
- Result: Zero matches in all Phase 4 files.
- Area: Security review.

- Command: Bad-char scan (Phase 4 files)
- Result: All clean.
- Area: Encoding review.

- Phase 4 plan: Tasks 1-7 all marked complete.
- Remaining risks: No publish/tag/release has been performed. Trusted publishing OIDC setup on npm side must be configured before first publish. Workflow uses `npm install -g npm@latest` which is a moving target on CI.

## 2026-06-04 Learning Sedimentation Review

- Command: `Select-String -Path docs/agent-memory/verification-log.md -Pattern 'Phase 2|Phase 3|learning|hook|proposal|plan' -Context 1,3`
- Result: Confirmed formal verification memory exists for Phase 2 final verification, Phase 3 Task 1-8 verification, and active-plan tracking.
- Area: Project memory completeness.

- Command: `Get-Content docs/agent-memory/pending-learning-proposals.md`
- Result: Current generated queue reports `No Proposals`.
- Area: Controlled learning proposal state.
- Caveat: This means no runtime candidate currently meets the promotion threshold; it does not mean the learning pipeline failed.

- Command: `Get-Content .claude/runtime/learning-proposal-phase-state.json` and `Get-Content C:\Users\ZX\.codex\memories\bilibili-mcp\runtime\learning-proposal-phase-state.json`
- Result: Both Claude and Codex runtime state files exist and currently point at `docs/superpowers/plans/2026-05-27-agent-memory-learning-system.md`.
- Area: Agent runtime learning state.
- Caveat: The current active plan differs from Phase 2/3 because `plan_tracker.py` selects the first incomplete plan.

- Command: `python .codex/scripts/plan_tracker.py`
- Result: Returned `docs\superpowers\plans\2026-05-27-agent-memory-learning-system.md`.
- Area: Active-plan tracking.
- Caveat: Future phase-gated learning reminders should confirm this is the intended active plan before relying on reminder timing.

- Formal memory updates: added 2026-06-04 entries to `project-facts.md` and `lessons-learned.md`.
- Conclusion: Phase 2/3 memory capture worked. Controlled learning operated as review-gated proposal generation, and no automatic promotion occurred because no proposal currently met the threshold.

## 2026-06-04 Active Plan Tracker Drift Fix

- Command: `python .codex/scripts/plan_tracker.py`
- Result: Returned `docs\superpowers\plans\2026-05-28-documentation-release-polish-implementation-plan.md`.
- Area: Active-plan resolution.

- Command: `python .codex/scripts/generate_learning_proposals.py --source codex` and `python .codex/scripts/generate_learning_proposals.py --source claude`
- Result: Passed with JSON-safe stdout `{"suppressOutput": true}`.
- Area: Controlled learning runtime state refresh.

- Command: `Get-Content C:\Users\ZX\.codex\memories\bilibili-mcp\runtime\learning-proposal-phase-state.json` and `Get-Content .claude\runtime\learning-proposal-phase-state.json`
- Result: Both state files now point at `docs/superpowers/plans/2026-05-28-documentation-release-polish-implementation-plan.md` with `completed_phase_count` 7.
- Area: Codex and Claude Code learning state.

- Command: Python UTF-8 read of `docs/agent-memory/pending-learning-proposals.md` approval phrase line.
- Result: File content is `Approval phrase: `批准本轮 learning proposals`.`. PowerShell may display this line as mojibake, but the file itself is valid UTF-8.
- Area: Encoding check.

- Change: `.codex/scripts/plan_tracker.py` now filters candidate plans and previous active plans to the stabilization roadmap or `*-implementation-plan.md` files.
- Conclusion: The active-plan drift is fixed. Non-implementation plans such as `2026-05-27-agent-memory-learning-system.md` and `2026-05-28-agent-hooks.md` no longer take over phase-gated learning reminders.

## 2026-06-04 Phase 4 Learning Sedimentation

- Source reviewed: Phase 4 verification entries in `docs/agent-memory/verification-log.md` and the Phase 4 final commit report.
- Result: Added formal memory entries for Phase 4 release-polish lessons and current release status.
- Area: Project learning sedimentation.

- Fact promoted: Phase 4 completed source-level documentation and release workflow polish, but no tag, GitHub release, or npm publish has been performed.
- Lesson promoted: npm trusted publishing and GitHub Actions OIDC guidance must be refreshed from official docs when workflow behavior is touched.
- Lesson promoted: A publish workflow update is not a release execution; release execution needs separate gates for trusted publishing setup, final verification, tag push, Actions monitoring, and release notes.
- Lesson promoted: `npm install -g npm@latest` is a moving CI target even though it was kept in Phase 4 for trusted publishing compatibility.

- Files updated: `project-facts.md`, `lessons-learned.md`, and `verification-log.md`.
- Conclusion: Phase 4 now has both verification memory and explicit reusable learning entries.

## 2026-06-04 Phase 5 Release Execution Verification

- Command: `git tag --list v1.4.0`, `git ls-remote --tags origin v1.4.0`, and `git show --no-patch --pretty=fuller v1.4.0`
- Result: Annotated tag `v1.4.0` exists locally and remotely. The tag targets commit `021a2a1f96fcbac30d5c4bcc030cd0212a6b7130`.
- Area: Release tag verification.

- Command: `gh run list --workflow publish.yml --limit 1`
- Result: Latest publish workflow run completed successfully for `v1.4.0`, event `push`, run id `26944676803`, duration 38s, created `2026-06-04T09:57:32Z`.
- Area: GitHub Actions publish workflow.
- Caveat: `gh run view 26944676803 --json ...` returned an API EOF once, but `gh run list` and npm registry metadata both confirmed success.

- Command: `npm view @xzxzzx/bilibili-mcp@1.4.0 name version description keywords gitHead dist-tags time --json`
- Result: npm registry shows `@xzxzzx/bilibili-mcp@1.4.0`, `latest` dist-tag points to `1.4.0`, description includes metadata/transcripts/subtitles/comment summarization, keywords include `transcript` and `metadata`, and `gitHead` is `021a2a1f96fcbac30d5c4bcc030cd0212a6b7130`.
- Area: npm publication verification.

- Command: `npm view @xzxzzx/bilibili-mcp version dist-tags gitHead --json`
- Result: npm registry reports version `1.4.0`, `latest: 1.4.0`, and gitHead `021a2a1f96fcbac30d5c4bcc030cd0212a6b7130`.
- Area: Post-publish package state.

- Previous recovery context: `v1.3.8` was already present on npm from 2026-03-11 and did not represent the current Phase 1-5 code. The current release was retargeted to `v1.4.0`; `v1.3.8` tag remains preserved for forensic trace and should not be deleted without explicit user approval.
- Remaining release step: GitHub Release for `v1.4.0` has not been created yet.

## 2026-06-05 Credential Guidance Verification

- Scope: Agent-facing Bilibili Cookie setup guidance for MCP clients and credential-dependent tools.
- Result: Added MCP tools for setup instructions and credential status, added credential `next_steps` to relevant error paths, and updated tool descriptions so agents can discover the credential dependency.
- Area: MCP tool surface and credential UX.

- Command: `npm test`
- Result: Passed with 11 test files and 122 tests.
- Area: Unit and server tool regression tests.

- Command: `npm run build`
- Result: Passed.
- Area: TypeScript build.

- Command: `npm pack --dry-run`
- Result: Passed. Dry-run package contents include the generated `dist/utils/credential-guidance.*` files.
- Area: Package contents.

- Command: `git diff --check`
- Result: Passed with only line-ending warnings.
- Area: Patch hygiene.

- Command: Secret and stale-client scan over README, source, and tests for Cookie assignment patterns and unsupported client names.
- Result: No real Cookie values found; README no longer contains Coze, Langcli, MiniMax, Mavis, or Kimi Work setup sections.
- Area: Credential safety and documentation cleanup.

- Review finding fixed: The generic `src/server.ts` catch path initially omitted structured `code` and `next_steps` for `BilibiliAPIError("COOKIE_EXPIRED")`; Codex added the fix and `tests/server-error-next-steps.test.ts`.
- Remaining caveat: `getCredentialSource()` reports `env`, `global_config`, or `none`; it does not currently report in-memory-only credentials.

## 2026-06-05 Agent Memory And Learning System Health Check

- Command: JSON parse of `.codex/hooks.json` and `.claude/settings.local.json`.
- Result: Both parsed successfully.
- Area: Codex and Claude Code hook configuration.

- Command: `python .codex/scripts/plan_tracker.py`
- Result: Returned `docs\superpowers\plans\2026-06-04-release-execution-implementation-plan.md`.
- Area: Active-plan tracking.

- Command: `python .codex/scripts/context_budget.py`
- Result: Passed and refreshed `docs/agent-memory/context-budget-report.md`.
- Area: Context budget reporting.

- Command: `python .codex/scripts/generate_learning_proposals.py --source claude` and `python .codex/scripts/generate_learning_proposals.py --source codex`.
- Result: Both passed with JSON-safe stdout `{"suppressOutput": true}`.
- Area: Controlled learning proposal generation.

- Runtime state: Codex runtime files exist under `C:\Users\ZX\.codex\memories\bilibili-mcp\`; Claude runtime files exist under `.claude\memory\` and `.claude\runtime\`.
- Result: Both sides had stop summaries and learning phase state updated on 2026-06-05.
- Area: Runtime observation storage.

- Conclusion: The Codex and Claude Code memory/learning systems are operational. Current `pending-learning-proposals.md` reports no proposals above threshold, which is a normal controlled-learning state rather than a failure.

## 2026-06-14 Active Plan Sync

- Command: `gh release view v1.4.0 --json tagName,name,url,publishedAt,isDraft,isPrerelease`
- Result: GitHub Release `v1.4.0` exists, is not draft or prerelease, and was published at `2026-06-04T10:02:43Z`.
- Area: Release execution plan synchronization.

- Command: `gh release view v1.4.0 --json body --jq .body`
- Result: Release notes mention the new transcript and metadata tools, expanded comment controls, client module split, Smithery removal, 110-test baseline, and npm package link.
- Area: GitHub Release acceptance criteria.

- Command: `npm test -- tests/credential-guidance.test.ts tests/server-credential-tools.test.ts tests/server-error-next-steps.test.ts tests/server-tools.test.ts`
- Result: Passed. 4 test files, 29 tests.
- Area: Credential guidance focused regression.
- Caveat: The no-credential tests now hide the local global credential config so a developer machine with configured Cookies does not contaminate the `source: none` branch.

- Command: `npm test`
- Result: Passed. 12 test files, 125 tests.
- Area: Full regression suite after active-plan synchronization.

- Command: `npm run build`
- Result: Passed.
- Area: TypeScript build after active-plan synchronization.

- Command: `npm pack --dry-run`
- Result: Passed for `@xzxzzx/bilibili-mcp@1.4.6`, 102 files.
- Area: Package contents sanity check.

- Command: `python .codex/scripts/plan_tracker.py`
- Result: Returned `docs\superpowers\plans\2026-06-05-credential-guidance-mcp-tools-implementation-plan.md`.
- Area: Active-plan tracking.

- Command: `python .codex/scripts/generate_learning_proposals.py --source codex` and `python .codex/scripts/generate_learning_proposals.py --source claude`
- Result: Both passed with JSON-safe stdout `{"suppressOutput": true}`; both runtime `learning-proposal-phase-state.json` files now point to the credential guidance implementation plan with `completed_phase_count` 8.
- Area: Codex and Claude Code learning proposal state.

- Change: Marked completed/verified checkboxes in the release execution and credential guidance implementation plans so phase-gated reminders no longer treat old release work as active.
- Conclusion: Active plan tracking and both Codex/Claude learning states are synchronized to the latest completed implementation plan. `pending-learning-proposals.md` still reports no proposals above threshold, which is expected.

## 2026-06-14 Task 1 Package Dependency Health

- Commands: `npm audit --json`; `npm test`; `npm run build`; `npm pack --dry-run`; package/workflow secret scan with `rg`.
- Result: `package-lock.json` root version matches `package.json` version `1.4.6`, `esbuild` is outside the audited vulnerable range, tests/build/package dry-run pass, and no package-surface secret leak was found.
- Caveat: No npm publish, tag, push, or GitHub release was performed.

## 2026-06-14 Task 2 Logging Debug Output Cleanup

- Commands: `npm test -- tests/logger-redaction.test.ts tests/bilibili-video-api.test.ts tests/bilibili-transcript.test.ts tests/bilibili-comments-tool.test.ts`; `npm test`; `npm run build`; logger debug smoke check; logging and secret scans with `rg`.
- Result: Debug logs are silent unless `BILIBILI_MCP_DEBUG=1`, debug output remains redacted when enabled, Bilibili API diagnostics route through the redacting logger, tests/build pass, and no real credential value was found.
- Caveat: No MCP tool contract, credential loading behavior, package metadata, tag, push, publish, or GitHub release was changed.

## 2026-06-14 Task 3 MCP Server Handler Refactor

- Commands: `npm test -- tests/server-tools.test.ts tests/server-credential-tools.test.ts tests/server-error-next-steps.test.ts tests/server-handler-sanitization.test.ts`; `npm test`; `npm run build`; server contract scan with `rg`.
- Result: `src/server.ts` now only constructs/registers the MCP server, tool schemas and handlers are extracted, public tool order/schema/error contracts remain covered by tests, sanitized inputs are passed downstream without changing URL-to-BVID extraction ownership, and tests/build pass.
- Caveat: No MCP tool was added, removed, renamed, or intentionally changed; no package, README, credential loading, release, tag, push, or publish action was performed.

## 2026-06-14 Task 4 Type And Cache Hardening

- Commands: `npm test -- tests/cache.test.ts tests/bilibili-metadata.test.ts tests/bilibili-comments-tool.test.ts tests/bilibili-transcript.test.ts`; `npm test`; `npm run build`; type-hardening scan with `rg`.
- Result: `CacheManager` now uses generic value types and preserves cache key/stat behavior, selected Bilibili wrapper casts are replaced with typed response interfaces, focused behavior tests and full tests/build pass.
- Caveat: No cache key format, MCP public contract, credential loading, logging behavior, source encoding, package metadata, tag, push, publish, or GitHub release was changed.

## 2026-06-14 Active Plan Tracker Commit-Boundary Fix

- Commands: `python .codex/scripts/plan_tracker.py`; `python .codex/scripts/generate_learning_proposals.py --source codex`; `python .codex/scripts/generate_learning_proposals.py --source claude`; `python -m py_compile .codex/scripts/plan_tracker.py .codex/scripts/generate_learning_proposals.py`.
- Result: Active plan tracking now ignores unchecked commit-boundary steps that require explicit user approval, so Task 1 no longer blocks phase-gated learning after implementation verification is complete. Codex and Claude runtime phase state both point to `docs/superpowers/plans/2026-06-14-task3-mcp-server-handler-refactor-implementation-plan.md` with completed phase count 6.
- Caveat: This does not mark a commit as completed and does not stage, commit, push, or modify Task 3 source behavior.

## 2026-06-15 Task 5 Source Comment And Metadata Encoding Cleanup

- Commands: UTF-8 source/metadata scan with Python; `node -e` package metadata check; `npm run build`; `npm test`; behavior-neutral diff review.
- Result: Scoped source comments and package metadata were verified as clean UTF-8 or already acceptable; no source or package metadata cleanup was required.
- Caveat: PowerShell terminal mojibake was not treated as file corruption; only UTF-8 file reads were used for encoding judgment.

## 2026-06-15 Task 6 MCP Integration Test Hardening

- Commands: `npm run build`; `npm test -- tests/server-tools.test.ts tests/server-credential-tools.test.ts tests/server-error-next-steps.test.ts tests/server-handler-sanitization.test.ts tests/mcp-server-smoke.test.ts`; `npm test`; `npm pack --dry-run`; MCP test helper scan with `rg`.
- Result: MCP server tests now share a single registered-handler helper, stdio entrypoint smoke coverage verifies startup logging stays on stderr, public tool-list smoke coverage remains stable, and build/tests/package dry-run pass.
- Caveat: One Task 6 scoped exception — `src/index.ts:16` now passes `quiet: true` to dotenv to stop dotenv 17 from polluting MCP stdio stdout with `[dotenv@...] injecting env` log; without this 1-line production fix the stdio smoke `stdout === ""` assertion cannot pass and real MCP clients would see non-JSON output on the JSON-RPC channel. No MCP public contract, credential loading, logger behavior, cache behavior, package metadata, release workflow, tag, push, publish, or GitHub release was changed.

## 2026-06-18 MCP Update Guidance

- Commands: `npm run build`; `npm test -- tests/update-check.test.ts tests/server-tools.test.ts tests/server-credential-tools.test.ts tests/mcp-server-smoke.test.ts tests/credential-guidance.test.ts tests/server-error-next-steps.test.ts`; `npm test`; `node dist/cli.js check-update`; `npm pack --dry-run`; stale unversioned command scan with `rg --pcre2`.
- Result: Added explicit package freshness guidance through `check_mcp_update` and `bilibili-mcp check-update`; README and README_EN now prefer `npx -y @xzxzzx/bilibili-mcp@latest` for MCP configs and credential helper commands; build, focused tests, full tests, real CLI update check, package dry-run, and stale command scan passed.
- Caveat: No automatic package update, npm publish, tag, push, GitHub Release, release workflow change, credential loading change, Bilibili API behavior change, or real MCP client UI smoke was performed.

## 2026-06-18 Version 1.6.0 Commit Verification

- Commands: `npm version 1.6.0 --no-git-tag-version`; `npm run build`; `npm test`; `npm pack --dry-run`; `node dist/cli.js check-update`; `git diff --check`.
- Result: `package.json` and `package-lock.json` now report `1.6.0`; build and full Vitest suite pass; package dry-run reports `@xzxzzx/bilibili-mcp@1.6.0`; CLI update check reports local current `1.6.0` against npm latest `1.5.3`; diff check has only CRLF warnings.
- Caveat: No npm publish, tag creation, GitHub Release creation, or release workflow execution was performed in this commit step.

## 2026-06-18 Bilingual MCP Guidance Fields

- Commands: `npm run build`; `npm test -- tests/credential-guidance.test.ts tests/server-credential-tools.test.ts tests/server-error-next-steps.test.ts tests/update-check.test.ts`; `npm test`; bilingual field scan with `rg`; added-diff secret-pattern scan with `git diff -- ... | Select-String`.
- Result: Credential setup/status, cookie-expired guidance, subtitle-unavailable guidance, and MCP update checks now keep existing English-compatible fields while adding explicit `*_en` and `*_zh` fields for clients that render either language; README and README_EN document the bilingual fields; build, focused tests, and full Vitest suite pass.
- Caveat: This is a source/documentation change only; no package version bump, tag, release, npm publish, push, credential loading behavior change, or Bilibili network behavior change was performed.

## 2026-06-19 Structured Error Guidance Codex Review

- Commands: `npm test -- tests/server-error-next-steps.test.ts tests/bilibili-comments-tool.test.ts`; `npm test`; `npm run build`; structured error-code scan with `rg`; added-diff secret-pattern scan with `git diff -- ... | Select-String`; UTF-8 source check with Python.
- Result: Codex review found and fixed two gaps after Claude implementation: handler-level plain `Error` validation failures now still return `VALIDATION_ERROR`, and generic `BilibiliAPIError("...", "API_ERROR")` now returns the documented `BILIBILI_API_ERROR` while preserving the original token in `details.api_code`. Focused tests now pass at 23 tests, full Vitest suite passes at 16 files / 155 tests, and build passes.
- Caveat: Live MCP client compatibility, npm package dry-run, version bump, tag, release, npm publish, push, and live Bilibili API calls were not performed in this review.

## 2026-06-19 Structured Error Guidance Package Dry Run

- Commands: `npm pack --dry-run --json`; package file scan over the JSON output for `tests`, `docs/qa`, `docs/agent-memory`, `docs/research`, `docs/templates`, `.codex`, `.claude`, `.env`, Smithery files, `src`, and raw `.ts` files excluding expected `.d.ts` type declarations.
- Result: Package dry-run reports `@xzxzzx/bilibili-mcp@1.6.1`, `xzxzzx-bilibili-mcp-1.6.1.tgz`, 120 entries, 102709 bytes packed, 389208 bytes unpacked, shasum `bc2dbd3e2c03ee72dde6c2ee503ce601d65870d8`; abnormal file scan returned `badCount=0`.
- Caveat: This is a dry run only; no npm publish, tag, release, push, live MCP client test, or live Bilibili API call was performed.

## 2026-06-19 Structured Error Guidance Stdio Smoke

- Commands: Node child-process stdio smoke against `node dist/index.js` with `initialize`, `notifications/initialized`, `tools/list`, and `tools/call get_video_info` using an empty `bvid_or_url`.
- Result: Process exited 0; stdout had 3 JSON-RPC response lines and no non-JSON noise; raw stderr was exactly `Bilibili MCP server running on stdio`; `tools/list` returned 7 expected tools; invalid input returned an MCP `isError: true` response whose JSON text payload had `code: VALIDATION_ERROR`, `category: validation`, `message_zh`, `next_steps_zh`, and `next_steps` matching `next_steps_en`.
- Caveat: This is an equivalent local stdio smoke, not a GUI MCP client smoke; no live Bilibili API call, package publish, tag, release, or push was performed.

## 2026-06-19 Version 1.6.3 Publish Verification

- Commands: `npm test`; `npm run build`; `npm pack --dry-run --json`; `git push origin master`; `git push origin v1.6.3`; `gh run watch 27803425317 --repo XZXZZX-Ai/bilibili-mcp --exit-status`; `npm view @xzxzzx/bilibili-mcp version dist-tags --json`; `gh release view v1.6.3`.
- Result: Release commit `ee22eb9` and annotated tag `v1.6.3` were pushed; GitHub Actions run `27803425317` completed successfully through `Publish to npm`; npm registry reports version `1.6.3` and `latest: 1.6.3`; GitHub Release `v1.6.3 - Publish Fix / 发布修复` is published at `https://github.com/XZXZZX-Ai/bilibili-mcp/releases/tag/v1.6.3`.
- Caveat: The previous `v1.6.2` tag and failed workflow were left intact; unrelated local harness and memory working-tree changes remain uncommitted.

## 2026-07-19 Matt Pocock Skills Workflow Integration

- Commands: live GitHub API listing for upstream engineering/productivity skill names; local existence comparison against Codex and Claude Code skill roots; `gh label list`; creation of the four missing default triage labels; UTF-8 replacement-character check; scoped credential-pattern scan; duplicate-heading checks; `git diff --check`; `python .codex/scripts/context_budget.py`.
- Result: All 22 current upstream skill names are present in both runtimes; GitHub Issues, five default triage labels, and a single-context domain-doc layout are configured; all five labels exist remotely; Codex and Claude routing preserve file-backed handoffs and explicit Git authorization; encoding, secret-pattern, duplicate-heading, and diff checks passed.
- Caveat: No GitHub Issue, commit, push, source code, MCP behavior, package metadata, test, release, hook registration, or global skill file was changed. The initial context budget was `HIGH`; the subsequent Superpowers runtime removal reduced the current status to `REVIEW`.

## 2026-07-19 Superpowers Runtime Removal

- Commands: scoped `rg` scans; Python compilation for context-budget, plan-tracker, learning-proposal, and pre-compact scripts; live `plan_tracker.py`; learning proposal regeneration; session-start output check; context budget regeneration; `git diff --check`.
- Result: Current Codex and Claude rules prohibit all `superpowers:*` skills; active work resolves to `docs/agent-memory/active-work.md`; startup, pre-compact, learning-state, and context-budget scripts no longer load `docs/superpowers/`; always-relevant context dropped from `HIGH` 23254 tokens to `REVIEW` 17685 tokens.
- Caveat: Historical files and evidence references under `docs/superpowers/` were intentionally retained. No source code, MCP behavior, package, test, GitHub Issue, label, commit, push, or release state changed in this removal step.

## 2026-07-19 Paseo Claude Code Workflow Integration

- Commands: `Get-Command paseo`; read `C:\Users\ZX\.paseo\orchestration-preferences.json`; `paseo --help`; `paseo run --help`; `GET http://127.0.0.1:6767/api/health`; scoped workflow-rule scans; added-diff UTF-8/secret-value scan; `git diff --check`; `python .codex/scripts/context_budget.py`.
- Result: Paseo CLI resolves to `C:\Users\ZX\.local\bin\paseo.cmd`; the daemon health endpoint returns `status: ok`; the live `providers.impl` preference selects a Claude provider; repository rules now let Codex launch and review one bounded Claude Code implementation agent from a file-backed handoff without user-operated prompt transfer. Workflow checks passed and the context budget remains `REVIEW` at an estimated 18226 tokens.
- Caveat: No Claude implementation agent was launched because no bounded implementation ticket was selected in this workflow-only change. Paseo daemon restart, source changes, tests, package operations, Git commits, pushes, and releases were not performed.

## 2026-07-19 Concurrent HTTP Throttling Fix

- Commands: temporary red-capable `tests/.tmp-http-throttle-repro.test.ts`; `npm test -- tests/bilibili-http.test.ts`; `npm test`; `npm run build`; `git diff --check`; temporary/debug-file scans; scoped source/test diff review; Paseo-managed Claude implementation and same-scope repair prompts; focused risk review.
- Result: The red repro measured a minimum concurrent request-start gap of about `0.155ms` against a configured `500ms` interval. `throttledFetch` now reserves FIFO admission turns with a normalized promise chain, excludes prior callers' queue time from the current caller's timeout, includes the current caller's own rate-limit wait, and allows response bodies to overlap. Codex independently verified 2/2 focused tests, 157/157 full-suite tests across 17 files, TypeScript build, diff format, and clean concurrency/timeout/recovery/determinism/scope risk findings.
- Caveat: The Paseo `test-baseline-builder` and `risk-reviewer` subagents did not return promptly; the top-level Claude agent completed their scoped work and Codex stopped the otherwise-finished agent. No real Bilibili network call, package dry run, commit, push, release, or Issue close was performed. GitHub Issue #2 is labeled `ready-for-human` pending Git authorization.

## 2026-07-19 Empty Transcript Credential Detection

- Commands: focused red/green `npm test -- tests/bilibili-transcript.test.ts -t "checks login status when an empty subtitle list would otherwise fall back"`; full transcript file; full `npm test`; `npm run build`; `git diff --check`; debug-marker and scoped-diff review; Paseo Claude implementation; `test-baseline-builder` and `risk-reviewer` reviews.
- Result: The red test showed a logged-out empty subtitle list resolving to description instead of rejecting. A private `verifyLoginForEmptySubtitles` helper now holds the existing safe login check and is reused by both transcript and video-info flows. Codex independently verified 1/1 focused, 15/15 transcript, and 158/158 full-suite tests across 17 files; build and diff/debug checks passed; logged-in fallback and `NoSubtitleError` behavior remain covered and unchanged.
- Caveat: No real Bilibili network call, package dry run, commit, push, release, or Issue close was performed. GitHub Issue #3 is labeled `ready-for-human` pending Git authorization. The risk reviewer noted that `getVideoInfoWithSubtitle` still lacks a dedicated direct unit test, but the moved block is byte-identical and no blocking issue was found.

## 2026-07-19 Transient Subtitle Error Retry

- Commands: focused red/green `npm test -- --run tests/bilibili-transcript.test.ts -t "retries subtitle retrieval after a temporary error fallback"`; full transcript file; full `npm test`; `npm run build`; `git diff --check`; scoped source/test diff review; Paseo Claude implementation; `test-baseline-builder` and `risk-reviewer` reviews.
- Result: The red test showed a first-call temporary subtitle error being cached as `description`, so the second call did not retry. The general-error catch branch no longer writes that fallback to the video cache. Codex independently verified 1/1 focused, 16/16 transcript, and 159/159 full-suite tests across 17 files; build and diff checks passed. Successful subtitle caching and `COOKIE_EXPIRED` propagation remain intact.
- Caveat: No real Bilibili network call, package dry run, commit, push, release, or Issue close was performed. GitHub Issue #4 is labeled `ready-for-human` pending Git authorization; CRLF conversion warnings remain informational.

## 2026-07-19 Comment Cache Detail-Level Separation

- Commands: focused red/green `npm test -- --run tests/bilibili-comments-tool.test.ts -t "does not share cached results between brief and detailed modes with the same limit"`; full comments test file; full `npm test`; `npm run build`; `git diff --check`; scoped source/test diff review; Paseo Claude implementation; `test-baseline-builder` and `risk-reviewer` reviews.
- Result: The red test showed `{ detailLevel: "detailed", limit: 5 }` reusing the cached one-comment brief result. The explicit-limit cache component now includes `detailLevel`. Codex independently verified 1/1 focused, 13/13 comments, and 160/160 full-suite tests across 17 files; build and diff checks passed. Identical options still reuse cache and public response shapes remain unchanged.
- Caveat: No real Bilibili network call, package dry run, commit, push, release, or Issue close was performed. GitHub Issue #5 is labeled `ready-for-human` pending Git authorization; CRLF conversion warnings remain informational.

## 2026-07-19 Real npm Test Guidance

- Commands: `npm test`; `npm run build`; expanded stale-guidance `rg` scan across `AGENTS.md`, `CLAUDE.md`, `.claude/agents`, and `.codex/agents`; exact-path secret and replacement-character scans; `git diff --check`; `python .codex/scripts/context_budget.py`; two bounded harness-security risk reviews.
- Result: Six current agent-rule files now treat `npm test` as the real unconditional Vitest gate. Codex's final run passed 17 files and 160 tests; build and all scoped scans passed. Always-loaded context decreased to an estimated 18,127 tokens, and no execution authority, hooks, permissions, trust boundaries, or historical records changed.
- Caveat: Repeated agent-side verification exposed a pre-existing intermittent failure in `tests/mcp-server-smoke.test.ts` (one failure among four runs, followed by a pass). It is separate from the documentation correction and requires its own diagnosis. No package dry run, commit, push, release, or Issue close was performed; Issue #6 is `ready-for-human` pending Git authorization.

## 2026-07-19 Stdio Smoke Readiness

- Commands: original 20-run focused loop; direct 20-process readiness-latency probe; post-fix focused test; agent and Codex 20-run focused loops; full `tests/mcp-server-smoke.test.ts`; full `npm test`; `npm run build`; `git diff --check`; fixed-sleep/debug-marker, replacement-character, and secret-pattern scans; `test-baseline-builder` and `risk-reviewer` reviews.
- Result: The original test failed at iteration 6 because stderr was still empty after its fixed 300ms sleep. The direct probe showed all 20 servers became ready, but 5 exceeded 300ms and the maximum was 453ms. The final test waits for the exact accumulated stderr signal with a 3s timeout, rejects on error/early exit, and awaits process closure. Codex independently verified 20/20 focused iterations, 2/2 smoke tests, 160/160 full-suite tests, build, and all scoped scans.
- Caveat: This is a test-only stabilization; no production stdio behavior, package contents, dependency, real client workflow, commit, push, release, or Issue close changed. Issue #7 is `ready-for-human` pending Git authorization; CRLF warnings remain informational.

## 2026-07-19 Redundant Comment Metadata Removal

- Commands: focused red/green `npm test -- --run tests/bilibili-comments-tool.test.ts -t "does not fetch video metadata before delegating to the comments API"`; full comments test file; full `npm test`; `npm run build`; `git diff --check`; `rg -n "getVideoInfo|const cid" src/bilibili/comments.ts src/bilibili/comments-api.ts`; `test-baseline-builder` and `risk-reviewer` reviews.
- Result: The red test observed one outer `getVideoInfo` call. `comments.ts` no longer imports or calls it, while `comments-api.ts` still fetches metadata and computes `aid || cid`. Codex independently verified 1/1 focused, 14/14 comments, and 161/161 full-suite tests across 17 files; build and diff/ownership checks passed.
- Caveat: The test mocks the delegated comments API and guards outer-layer ownership; required lower-layer metadata ownership is additionally verified by direct source inspection. No live Bilibili request, package dry run, interface, commit, push, release, or Issue close changed. Issue #8 is `ready-for-human` pending Git authorization.

## 2026-07-19 Comment Limit Pagination

- Commands: failing-first `npx vitest run tests/bilibili-comments-tool.test.ts`; final focused comment tests; full `npm test`; `npm run build`; `git diff --check`; scoped source/test review; Paseo Claude implementation; `test-baseline-builder` and `risk-reviewer` reviews.
- Result: Three red regressions observed one request where pagination and early-stop behavior required multiple calls. The final implementation sequentially requests page sizes 20, 20, and 10 for `limit: 50`, stops on empty/short pages, truncates defensively, and preserves single requests at or below 20. Codex independently verified 20/20 comments tests and 167/167 full-suite tests across 17 files; build and diff checks passed.
- Caveat: `limit` counts top-level comments, so detailed-mode child reply expansion can make the final processed array longer; a deterministic regression verifies 50 top-level comments plus 50 child replies. No live Bilibili request, package dry run, schema, validation, response shape, commit, push, release, or Issue close changed. Issue #9 is `ready-for-human` pending Git authorization.

## 2026-07-19 Login Status Network Error Preservation

- Commands: pre-fix and post-fix no-file HTTP 503 harness; focused `tests/bilibili-http.test.ts` and `tests/server-error-next-steps.test.ts`; credential/subtitle/error regression group; full `npm test`; `npm run build`; `git diff --check`; scoped debug/credential scan; Paseo Claude implementation; `test-baseline-builder` and `risk-reviewer` reviews.
- Result: The pre-fix harness failed because HTTP 503 resolved as logged out. `checkLoginStatus` now delegates to `fetchWithoutWBI`, and `throttledFetch` maps native fetch `TypeError` to `NetworkError` with its original error. The same 503 harness now rejects with `NetworkError` and status 503. Codex independently verified 17/17 focused and 171/171 full-suite tests across 17 files; the MCP credential tool returns structured retryable `NETWORK_ERROR`; build and diff/scoped scans passed.
- Caveat: Immediate repeated connection failures inherit roughly 14-17 seconds of existing retry backoff, and repeated default 10-second timeouts may take roughly 54-57 seconds. Live Bilibili credentials, clients, package contents, release, commit, push, and Issue close were not exercised. QA is `pass with caveats`; Issue #10 is `ready-for-human` pending Git authorization.

## 2026-07-19 Non-Retryable HTTP Status Precedence

- Commands: pre-fix/post-fix zero-backoff 403 harness; focused `tests/retry.test.ts`, logger-redaction, and HTTP tests; full `npm test`; `npm run build`; `git diff --check`; scoped debug scan; Paseo Claude implementation; `test-baseline-builder` and `risk-reviewer` reviews.
- Result: The pre-fix harness observed four attempts for explicit HTTP 403. `shouldRetry` now immediately returns the status allowlist decision for numeric statuses and only applies name/code checks to status-less errors. The compact matrix verifies 403→1, 503→4, and status-less `NetworkError`→4. Codex independently verified 13/13 focused and 174/174 full-suite tests across 18 files; build, original harness, and diff/debug scans passed.
- Caveat: `src/bilibili/video-api.ts` has a pre-existing `NetworkError` construction without `statusCode`, so an HTTP 403 on that path still behaves like a status-less connection error; it was not changed under Issue #11. No package dry run, public interface, commit, push, release, or Issue close changed. Issue #11 is `ready-for-human` pending Git authorization.

## 2026-07-19 Subtitle HTTP Status Propagation

- Commands: focused pre-fix/post-fix `tests/bilibili-video-api.test.ts` 403 regression; full `npm test`; `npm run build`; `git diff --check`; scoped source/test review; Paseo Claude implementation; `test-baseline-builder` and `risk-reviewer` reviews.
- Result: The pre-fix regression completed in about 0.6 seconds and observed four fetches with `statusCode: undefined`. `getSubtitleContent` now passes `response.status` into `NetworkError`. Codex independently verified 1/1 focused and 175/175 full-suite tests across 18 files; build and diff checks passed.
- Caveat: No live Bilibili 403, public schema, package contents, commit, push, release, or Issue close was exercised. Issue #12 is `ready-for-human` pending Git authorization.

## 2026-07-19 WBI HTTP Status Propagation

- Commands: focused pre-fix/post-fix `tests/bilibili-wbi.test.ts`; combined WBI/video/retry tests; full `npm test`; `npm run build`; `git diff --check`; scoped diff review; Paseo Claude implementation; `test-baseline-builder` and `risk-reviewer` reviews.
- Result: The pre-fix test completed in about 0.3 seconds and observed four fetches plus `statusCode: undefined`. The WBI path now passes `navRes.status` into the original `NetworkError` and carries it through the outer typed wrapper. Codex independently verified 11/11 focused and 176/176 full-suite tests across 19 files; build and diff checks passed.
- Caveat: No live Bilibili 403, package contents, public interface, commit, push, release, or Issue close was exercised. Issue #13 is `ready-for-human` pending Git authorization.

## 2026-07-19 WBI Transport Retry And Timeout Cleanup

- Commands: focused pre-fix/post-fix WBI transport regression; combined WBI/video/retry tests; full `npm test`; `npm run build`; `git diff --check`; scoped diff review; Paseo Claude implementation; `test-baseline-builder` review and top-level fallback risk review.
- Result: The pre-fix test observed one fetch and zero timeout cleanups. The WBI fetch boundary now converts native `TypeError` to status-less `NetworkError` before `withRetry` and clears the timeout in `finally`. Codex independently verified four attempts, four cleanup calls, explicit `statusCode: undefined`, preserved 403 behavior, 12/12 focused tests, and 177/177 full-suite tests across 19 files; build and diff checks passed.
- Caveat: The project `risk-reviewer` stalled after bounded waits, so its checklist was completed by the top-level Claude agent and independently rechecked by Codex. No live transport failure, package contents, public interface, commit, push, release, or Issue close was exercised. Issue #14 is `ready-for-human` pending Git authorization.

## 2026-07-19 Fingerprint Timeout Cleanup

- Commands: pre-fix/post-fix focused fingerprint test; combined fingerprint/video/comment tests; full `npm test`; `npm run build`; `git diff --check`; scoped caller/diff review; Paseo Claude implementation; `test-baseline-builder` and `risk-reviewer` reviews.
- Result: The pre-fix test observed a `null` fallback with zero timeout cleanups. `getBuvid` now clears the existing timer in `finally`. Codex independently verified one fetch, one cleanup, preserved `null`, 28/28 related tests, and 178/178 full-suite tests across 20 files; build and diff checks passed.
- Caveat: No live Bilibili fingerprint failure, package contents, public interface, commit, push, release, or Issue close was exercised. Issue #15 is `ready-for-human` pending Git authorization.

## 2026-07-20 v1.6.4 Pre-Release Gates

- Commands: `npm ci`; `npm run build`; `npm test`; focused MCP stdio smoke; `.codex/scripts/test_stop_summary.py`; `npm audit --omit=dev --json`; `npm pack --dry-run --json`; package-entry existence checks; high-confidence tracked-file secret scan; `git diff --check`.
- Result: Build passed; 20 Vitest files and 180 tests passed; the focused stdio smoke passed 2/2; hook tests passed 8/8; the production dependency audit reported zero vulnerabilities; the 1.6.4 tarball contains 120 expected files and excludes tests, local agent configuration, internal docs, and credential files; built main/types/bin targets exist; no high-confidence credential or token pattern was found.
- Caveat: The full development dependency audit reports four transitive development-tooling advisories (three moderate and one high). They are not production dependencies and are excluded from the published tarball, so they are recorded as non-blocking follow-up maintenance rather than expanded into the v1.6.4 reliability release. Live Bilibili and desktop-client matrix checks were not run.

## 2026-07-20 v1.6.4 Publication

- Commands: annotated tag push; GitHub Actions run inspection; `npm view @xzxzzx/bilibili-mcp`; post-publish `npx -y @xzxzzx/bilibili-mcp@1.6.4 --help`; npm attestation lookup; GitHub Release inspection; GitHub Issue closure checks.
- Result: The initial tag-triggered run failed before install because `npm@latest` resolved to npm 12.0.1, whose Node engine excluded the workflow's Node 22.14.0. Commit `3fd6f6f` pins npm 11.18.0, whose engine supports Node 22.14.0; the manual rerun `29695975757` then passed install, tests, build, and trusted publication. npm reports version/latest 1.6.4 with SLSA provenance, the fresh CLI help smoke passes, the non-draft GitHub Release exists, and Issues #2-#15 are closed.
- Caveat: The annotated `v1.6.4` tag remains on release commit `47b5486`; the workflow-only compatibility fix is the next commit on `master` and was used by the successful manual publish. The Actions runtime emitted a non-blocking notice that `actions/checkout@v4` and `actions/setup-node@v4` are forced from Node 20 to Node 24 by GitHub.

## 2026-07-20 MCP Server Version Synchronization

- Commands: Paseo-managed Claude Code implementation; `npm run build`; `npm test`; compiled `dist/server.js` metadata comparison against `package.json.version`; `git diff --check`; narrow `test-baseline-builder` and `risk-reviewer` reviews.
- Result: `src/server.ts` now reuses the root package version through the same Node ESM file-loading pattern already used by the CLI. The regression compares MCP SDK server metadata with `package.json.version`. Codex independently verified 20 test files and 181 tests, a clean build, and compiled server metadata version `1.6.4`.
- Caveat: The regression reads the SDK's private `_serverInfo` field, matching the repository's existing test-only `_requestHandlers` access. No dependency, package version, tool schema, response shape, release action, commit, or push changed; CRLF warnings remain informational.

## 2026-07-20 v1.6.5 Source Preparation

- Commands: `npm version 1.6.5 --no-git-tag-version`; `npm run build`; `npm test`; `npm audit --omit=dev --json`; `npm pack --dry-run --json`; compiled entry checks; clean-UTF-8 checks; intended-added-content credential scan; `git diff --check`; live `npm view`; `git fetch origin master`; Paseo `release-verifier` review.
- Result: Package and lockfile now report `1.6.5`; Chinese and English changelogs describe the MCP metadata version fix. Codex independently verified 20 files and 181 tests, a clean build, zero production vulnerabilities, 120 expected tarball entries with main/types/bin present and tests/internal handoffs excluded, zero high-confidence secret hits in intended added content, and no local/remote master divergence before commit.
- Caveat: The requested Paseo `package-maintainer` repair could not finish because the Paseo daemon stopped and repository rules prohibit restarting it without approval; Codex completed the same package metadata, dependency-diff, tarball-content, and lockfile checklist directly. No tag, npm publish, GitHub Release, or workflow change was performed.

## 2026-07-20 Navigable Transcript v1.7.0

- Commands: 93-test focused Vitest run; full `npm test`; `npm run build`; `npm audit --omit=dev --json`; `npm pack --dry-run --json`; real stdio initialize/tools-list; live read-only metadata/Chapter calls; UTF-8 strict decoding; intended-added-content high-confidence secret scan; `git diff --check`; Codex Standards/Spec review; four bounded Claude subagent reviews.
- Result: Codex independently verified 23 files and 243 tests, a clean build, zero production vulnerabilities, 128 expected tarball entries with navigation/Chapter output and no internal docs, server version `1.7.0`, eight tools in stable order, zero high-confidence secret matches, and no UTF-8 failures. Live examples returned 19 Parts and 6 non-empty Chapters with valid ranges.
- Caveat: Bilibili consumer webpage endpoints remain undocumented and may drift; parsing is defensive and Chapters are never inferred. This verification does not authorize or perform a tag, npm publish, GitHub Release, or workflow change.

## 2026-07-20 v1.7.0 Publication

- Commands: annotated tag creation/push; GitHub Actions run inspection; `npm view @xzxzzx/bilibili-mcp@1.7.0`; npm attestation inspection; published `npx -y @xzxzzx/bilibili-mcp@1.7.0 --help`; GitHub Release creation and inspection.
- Result: Tag `v1.7.0` points to `bd15438`; Actions run `29704348924` passed install, 243 tests, build, and trusted publication. npm latest is `1.7.0` with SLSA provenance, the published CLI help smoke passes, and the GitHub Release is non-draft and non-prerelease.
- Caveat: The release uses undocumented Bilibili consumer endpoints for Part/Chapter reads; the defensive parsing and empty-Chapter behavior remain the compatibility boundary.

## 2026-07-20 Legacy Auth And Config Cleanup

- Commands: Paseo-managed Claude Code implementation; `package-maintainer` build/package repair; sentinel clean-build check; `npm run build`; full `npm test`; `npm pack --dry-run --json`; `git diff --check`; scoped `rg` checks for `BilibiliAuth`, `src/bilibili/auth`, and Smithery wording.
- Result: `src/bilibili/auth.ts` is deleted with no live references; `config.maxCacheSize` controls both QuickLRU instances; the stale Smithery comment and inert `package.json.config.bilibili` block are gone. Codex independently verified 23 files and 244 tests, a clean TypeScript build, and 124 package entries with zero `dist/bilibili/auth.*` or sentinel artifacts.
- Caveat: The cache regression uses a file-scoped hoisted `BILIBILI_CACHE_SIZE=3` and restores the previous value after the file. No live Bilibili request, MCP public behavior, credential behavior, dependency, version, commit, push, release, or publish changed.

## 2026-07-20 v1.7.1 Publication

- Commands: independent build; full `npm test`; production audit; package dry run; scoped secret and UTF-8 scans; annotated tag push; Actions run inspection; live npm metadata and attestation lookup; published CLI help smoke; GitHub Release creation and inspection.
- Result: 23 files and 244 tests passed; production audit reported zero vulnerabilities; the 124-entry package contained the expected entry points and no credential/Smithery artifacts. Actions run `29723831279` succeeded, npm latest is `1.7.1` with SLSA provenance, and the non-draft GitHub Release is available at `https://github.com/XZXZZX-Ai/bilibili-mcp/releases/tag/v1.7.1`.
- Caveat: Actions emitted the existing non-blocking notice that `actions/checkout@v4` and `actions/setup-node@v4` are forced from Node 20 to Node 24 by GitHub.

## 2026-07-20 Transcript Keyword Search

- Commands: Paseo-managed Claude Code implementation with `test-baseline-builder` and `risk-reviewer`; Codex same-scope size-guard repair after Paseo HTTP 402; 154-test focused Vitest run; full `npm test`; `npm run build`; MCP schema/stdio smoke; `npm pack --dry-run --json`; strict UTF-8 decoding; intended-file high-confidence secret scan; `git diff --check`.
- Result: `get_video_transcript` now supports bounded, case-insensitive literal keyword location with timestamped contexts, range-first filtering, structured counts, and a compact transcript. Codex independently verified 23 files and 286 tests, a clean build, eight unchanged MCP tools, zero extra Bilibili requests in search mode, 124 expected package files, zero UTF-8 failures, and zero high-confidence secret hits.
- Caveat: Search is intentionally literal and limited to one selected Part's real subtitles; description fallback is rejected. No live Bilibili request, version change, commit, push, tag, npm publication, or GitHub Release was performed.

## 2026-07-20 v1.7.2 Publication

- Commands: official GitHub/npm trusted-publishing review; Paseo `package-maintainer`/`release-verifier` preparation; independent `npm ci`, build, 286-test suite, stdio smoke, production audit, package dry run, UTF-8/diff/secret gates; focused commit/push; annotated tag push; Actions monitoring; live npm metadata/provenance and exact-version CLI smoke; GitHub Release creation and inspection.
- Result: Commit `b05001b` reached `origin/master`; annotated tag `v1.7.2` triggered successful Actions run `29728674803`. npm latest is `1.7.2` with SLSA provenance, the published CLI help works, and the GitHub Release is non-draft and non-prerelease.
- Caveat: `npm ci` still reports the known development-only tooling advisories (three moderate, one high), while `npm audit --omit=dev` reports zero production vulnerabilities. The existing GitHub notice about v4 actions being forced from Node 20 to Node 24 remains non-blocking.

## 2026-07-25 Structured Transcript Output

- Commands: focused red/green `npm test -- tests/server-tools.test.ts tests/server-handler-sanitization.test.ts`; `npm run build`; full `npm test`; official SDK `Client` + `StdioClientTransport` discovery/error/success attempts against local `dist/index.js`; `npm pack --dry-run --json`; `git diff --check`; ephemeral inline-config Codex CLI `0.144.6` probe; independent Standards and Spec reviews.
- Result: The two new contract assertions failed before implementation and the final focused suite passes 39/39. Full Vitest passes 23 files / 290 tests; build passes; the 124-file package includes `dist/index.js` and excludes `src/` and `.env`; diff check passes. SDK discovery reports eight tools with the exact transcript output schema, and validation/error calls omit `structuredContent`. Codex CLI reached `bilibili_local.get_video_transcript` and reported no output-schema validation error.
- Initial credential caveat: a fresh local process reported `COOKIE_EXPIRED` for both credential status and bounded `BV1vL411G7N7` transcript calls. The already-running published MCP process returned a 0–5 second subtitle sample, but that cached process was not accepted as fresh-process evidence.
- Client caveat: Claude Desktop and Cursor were not tested and are non-blocking. Claude Code itself was not logged in, so the Paseo implementation agent made no changes; Codex performed the same scoped implementation and two-axis review. No commit, push, version, changelog, release, or publication occurred.
- Tracker state: GitHub Issue #16 was closed as completed on 2026-07-26 after replacement-credential verification; the temporary `ready-for-human` label was removed.
- Credential refresh attempts: Codex parsed user-supplied Netscape Cookie exports from the system clipboard, saved only `SESSDATA`, `bili_jct`, and `DedeUserID` through the existing global `CredentialManager`, and confirmed exact round-trip equality without displaying values. The second session was valid in a direct three-field Bilibili check; the remaining MCP `COOKIE_EXPIRED` was traced to three stale credential lines in the ignored repository `.env`, which had higher priority than the global file. Removing only those stale lines made a fresh MCP process report `source: global_config` and `logged_in: true`.
- Final credentialed acceptance: SDK 1.27.1 listed eight tools, found the transcript output schema, and successfully called `BV1vL411G7N7` for 0–5 seconds with `data_source: subtitle`. Parsed legacy JSON equaled `structuredContent`, the formatted text was exact, and no schema error occurred. Ephemeral inline-config Codex CLI 0.144.6 then called the same local tool successfully, displayed legacy JSON text, and raised no output-schema validation error; its model-facing result did not separately expose `structuredContent`. No global MCP configuration was modified. The session exposed in chat was replaced and reverified on 2026-07-26.
- Git delivery: the verified implementation, research, decision, PRD, handoff, tests, and user-facing documentation were committed on `master` as `29f663a` (`feat: add structured transcript output`) for the user-authorized push to `origin/master`. The generated `pending-learning-proposals.md` date-only change remains excluded.

## 2026-07-26 Issue #16 Credential Rotation And Closure

- Commands: fresh official SDK `Client` + `StdioClientTransport` connection to local `dist/index.js`; safe `check_bilibili_credentials`; bounded `get_video_transcript` call for `BV1vL411G7N7` from 0–5 seconds; GitHub Issue comment, label cleanup, and completed closure.
- Result: the replacement credentials report `configured: true`, `source: global_config`, and `logged_in: true`. The MCP server lists eight tools, declares the transcript output schema, returns a successful subtitle result with `structuredContent`, and preserves exact parsed and formatted legacy-text equality. Issue #16 is closed as completed.
- Security: no Cookie value or credential field was printed, stored in project files, or posted to GitHub.

## 2026-07-26 Transcript Evidence Links

- Commands: Paseo `claude/glm-5.2[1m]` implementation; focused red/green Vitest; Codex-focused `npm test -- tests/bilibili-transcript.test.ts tests/server-tools.test.ts tests/server-handler-sanitization.test.ts`; `npm run build`; full `npm test`; official SDK 1.27.1 `Client` + `StdioClientTransport` discovery and credentialed ordinary/multi-Part calls; live Playwright ordinary and multi-Part navigation; `npm pack --dry-run --json`; `git diff --check`; scoped secret review; two independent read-only reviews.
- Result: focused tests pass 87/87 and the full suite passes 23 files / 299 tests. SDK discovery preserves eight tools and exact schema requirements; formatted JSON text equals `structuredContent`. `BV1vL411G7N7` returns the case-preserving ordinary source URL, while `BV1Eb411u7Fw` Part 4 returns `?p=4` and a bounded search match at `?p=4&t=1.12`. Playwright opened the expected ordinary Video at 42.5 seconds and the expected Part 4 after 1.12 seconds. Build, 124-entry package dry run, diff check, and both independent reviews passed.
- Security: credentials reported only `configured: true`, `source: global_config`, and `logged_in: true`; no Cookie value was printed or persisted. Generated URLs use the fixed Bilibili HTTPS origin plus validated BVID, resolved Part, and subtitle time only.
- Client caveat: Claude Desktop, Cursor, and Codex CLI were not tested because official SDK stdio plus live browser acceptance are the Issue #17 gates.
- Git delivery: commit `7a6f79d` (`feat: add transcript evidence links`) was pushed to `origin/master`, and Issue #17 was closed as completed. No version, changelog, tag, release, or publication occurred.

## 2026-07-26 v1.8.0 Source Preparation

- Commands: commit-pinned GitHub source-learning; current official npm/GitHub release-documentation review; Paseo `claude/glm-5.2[1m]`; `npm ci`; `npm run build`; full `npm test`; installed npm and npm 11.18.0 production audit attempts; exact official npm bulk-advisory request; `npm pack --dry-run --json`; official SDK 1.27.1 stdio discovery and credentialed calls; safe CLI credential check; strict UTF-8, added-content secret-pattern, dependency-diff, package-content, and `git diff --check` gates; package-maintainer/release-verifier reviews; Codex Security advisory triage.
- Result: Package, lockfile, and lockfile root report `1.8.0`; dependency graph, scripts, entry points, source, tests, and workflow are unchanged. Build passed; full Vitest passed 23 files / 299 tests; the dry run contained 124 expected files with no internal docs or credential material. SDK discovery returned the stable eight-tool order and server version 1.8.0. Credential status was safely reported as configured/global_config/logged-in; ordinary `BV1vL411G7N7` and multi-Part `BV1Eb411u7Fw` Part 4 transcript calls preserved exact text/structured equality and expected evidence URLs.
- Audit caveat: The npm CLI failed to decode the official registry's compressed audit response, so the exact omit-dev inventory was submitted directly to the official bulk endpoint. It returned four advisories: Hono moderate, body-parser low, and two fast-uri high. Static `triage-finding/v0` review marked all four currently not actionable because the HTTP sinks are unused and no untrusted URI reaches a security-sensitive fast-uri consumer. This is not a zero-advisory result; GitHub Issue #19 tracks dependency refresh separately.
- Harness caveat: The first SDK probe contained the wrong expected tool order and was corrected against the repository contract. The GLM agent stopped on HTTP 429 before producing its report; Codex retained the provider choice, created a truthful fallback report, and used two independent reviewers. The agent was archived and Issue #18 moved to `ready-for-human`. No publication or Git action occurred.

## 2026-07-26 Production Dependency Refresh

- Commands: targeted lock-only npm update; clean install; `npm ls`/`npm explain`; build; full Vitest; Node 18.20.8 official SDK stdio smoke; current-Node official SDK credentialed ordinary/multi-Part transcript acceptance; safe CLI check; production audit; package dry run; strict UTF-8, intended-addition secret-pattern, sensitive-package-artifact, and diff checks.
- Result: body-parser resolves to 2.3.0, fast-uri to 3.1.4, type-is to 2.1.0, and two nested content-type copies to 2.0.0 through existing parent ranges. Build and 23 files / 299 tests pass. Node 18 and current Node both observe server 1.8.0 and eight tools; credentialed transcript text equals structured content with the expected evidence URLs. The package remains 124 files.
- Security: Three advisories are cleared. Audit has zero low, high, or critical findings and reports one underlying moderate Hono advisory through two dependency nodes. The vulnerable static-file export is unused; Hono 2 would require dropping Node 18.
- Caveat: Vitest itself cannot start under Node 18 because its current Rolldown dependency imports `node:util.styleText`; the shipped runtime was therefore tested directly with the official SDK under Node 18.20.8 and passed.
- Independent review: package and risk reviews passed after the complete lockfile closure and README publication ordering were corrected. Issue #20 records the separate Node engine-floor mismatch.
- Completion audit: after the final build, a fresh official SDK client again listed eight tools, confirmed the exact transcript schema, observed only safe credential status fields, and passed ordinary plus multi-Part credentialed transcript calls with exact text/structured equality. An initial audit assertion omitted the contractually tested trailing URL slash; correcting the audit expectation made the unchanged product pass.
- Git delivery: `8cad77c` and `2c87750` were pushed to `origin/master` after a fresh build and 299-test pass. Issues #18 and #19 were closed; no tag, workflow dispatch, npm publication, or GitHub Release occurred.

## 2026-07-26 v1.8.0 Publication

- Commands: release-verifier preflight; clean install; build; 299-test suite; production audit; 124-file package dry run; release-range secret scan; official SDK stdio smoke; annotated tag creation/push; Actions run watch; live npm metadata/provenance; exact-version CLI help; GitHub Release creation/inspection.
- Result: Tag `v1.8.0` points to `4be845f`; Actions run `30193180970` succeeded. npm latest is `1.8.0`, integrity/shasum and SLSA provenance are present, the published CLI works, and the GitHub Release is non-draft/non-prerelease.
- Caveat: Production audit still maps one unreachable Hono `serveStatic` advisory to two moderate nodes. GitHub Issue #20 separately tracks the pre-existing Node engine-floor mismatch. No workflow or runtime-source repair was needed.

## 2026-07-26 Bounded Authenticated Bilibili Video Discovery

- Commands: failing-first focused Vitest; direct Codex implementation; final 155-test focused suite; `npm run build`; full `npm test`; official SDK 1.27.1 `Client + StdioClientTransport` nine-tool discovery and credentialed search/transcript calls; `npm pack --dry-run --json`; `git diff --check`; scoped 151-file changed/package secret scan; direct code review.
- Result: The failing-first run exposed the missing module/tool/validator with 22 expected failures. Final build passes, 24 files / 327 tests pass, and the 128-file package includes `dist/bilibili/search.js` with no internal, test, or credential paths. A real Chinese-title search returned four normal Video candidates including `BV1Eb411u7Fw`; the selected candidate's bounded Part 4 query `函数` returned one match at `https://www.bilibili.com/video/BV1Eb411u7Fw/?p=4&t=1.12`. Search and transcript text/structured payloads were identical and SDK output-schema validation passed.
- Security: Credentials were reported only as configured/global_config/logged-in. Missing/logged-out/network/search-failure regressions passed; the final scan found zero high-confidence secrets and no Cookie value was printed or persisted.
- Review: Direct Codex review found no scope, schema, credential, request-count, or normalization blocker; it added one regression proving upstream search failures cannot become empty success. The user explicitly disabled Claude Code/Paseo implementation, so no Claude report or implementation subagent was used.
- Implementation-phase tracker state: Issue #21 moved to `ready-for-human`; no Git or publication action occurred until the user separately authorized the release.

## 2026-07-26 v1.9.0 Publication

- Commands: version/changelog preparation; `npm ci`; `npm run build`; full `npm test`; production audit; `npm pack --dry-run --json`; strict added-text UTF-8 and 154-file secret scans; official SDK 1.27.1 authenticated stdio acceptance; explicit staged-scope review; commit/push; annotated tag push; Actions run inspection; live npm integrity/provenance lookup; isolated exact-package CLI version/help smoke; GitHub Release creation and Issue closure.
- Result: Commit `b77c3fc` is on `master`; tag `v1.9.0` points to it; Actions run `30195477401` passed; npm latest is `1.9.0` with SLSA provenance; the GitHub Release is non-draft/non-prerelease; and Issue #21 is closed. The package remains 128 files, with 24 files / 327 tests and nine-tool real-client acceptance passing.
- Caveat: Running `npm exec` from inside this same-name package repository initially resolved the machine's global `bilibili-mcp` shim and falsely reported version `1.3.7`. Re-running from a dedicated empty temporary directory resolved the `_npx` package binary and correctly reported `1.9.0`; no package defect or patch release was required. The accepted unreachable Hono advisory remains two moderate audit nodes, with zero low/high/critical findings.
- Scope: README Release links changed only after the Release existed. The workflow and Issue #20 were unchanged; `pending-learning-proposals.md` remained unstaged and unpromoted.

## 2026-07-26 README Information Architecture

- Commands: bilingual `beautify-github-readme` audits; six-file Markdown structure and 102-local-link/anchor validation; SVG XML and external-resource checks; desktop/narrow hero raster review; 20-point bilingual Agent-install prompt contract check; 33-client bilingual preservation check; eight-runtime-variable bilingual coverage check; focused credential-guidance and credential-tool Vitest; high-confidence secret and credential-assignment scan; `npm pack --dry-run --json --ignore-scripts`; `git diff --check`.
- Result: `README.md` and `README_EN.md` are concise bilingual landing pages of 101 lines each and only link to the canonical setup guides instead of duplicating end-user installation or configuration methods. `docs/client-setup.md` and `docs/client-setup.en.md` now contain the complete Agent prompt, npx and global installation, all 33 client configurations, credential setup and login validation, every current credential/runtime environment variable, optional runtime settings, and source-development setup. All 20 prompt assertions, all 66 client-section checks, all 102 local links, and 9 focused tests passed. Both local hero variants render cleanly, all eight required README/reference assets are present in the 134-file dry run, and no internal task/memory path or credential material is packaged.
- Scope: Runtime source, schemas, tests, generated `dist/`, version, release workflow, and public MCP behavior were unchanged, so build and Vitest were not rerun. The pre-existing date-only change in `pending-learning-proposals.md` was preserved and not promoted.

## 2026-07-26 v1.9.1 README Documentation Preparation

- Commands: live `origin/master` and npm-latest checks; package/changelog version consistency; `npm run build`; full `npm test`; production audit; bilingual README audits; 102-link validation; SVG XML, external-resource, 900px, and 360px checks; added-line credential scan; `npm pack --dry-run --json --ignore-scripts`; compiled CLI version smoke; `git diff --check`.
- Result: Source version is `1.9.1`; 24 files / 327 tests pass; compiled CLI reports `1.9.1`; both 1200×380 SVG heroes use non-overlapping three-card geometry; the 134-file package contains all eight required README/reference assets and excludes internal task, memory, test, credential, and discarded-variant paths. Added-line credential findings are zero.
- Caveat: Production audit retains the accepted two moderate Hono nodes with zero low/high/critical findings. This preparation does not create a tag, GitHub Release, Actions publication run, or npm publication; live npm latest remains `1.9.0`.

## 2026-07-26 v1.9.1 Publication

- Commands: current official GitHub/npm trusted-publishing review; independent release-verifier; clean install; build; 327-test suite; production and full audit inspection; 134-file package dry run; release-range secret scan; annotated tag creation/push; Actions run watch; live npm integrity/provenance lookup; isolated exact-package CLI version/help smoke; GitHub Release creation/inspection.
- Result: Tag `v1.9.1` points to `5cdd47b`; Actions run `30205162304` passed install, tests, build, and trusted publication. npm latest is `1.9.1` with integrity, shasum, and SLSA provenance; the published CLI reports `1.9.1`; and the GitHub Release is non-draft/non-prerelease.
- Caveat: Production audit remains two accepted moderate Hono nodes with zero low/high/critical findings. The full development tree also reports advisories in semantic-release/npm, Vitest/Vite, and related tooling, but those packages are not shipped in the 134-file runtime package. `pending-learning-proposals.md` remained unstaged and outside the release tag.

## 2026-07-27 Authenticated Bilibili Favorites Discovery

- Commands: focused red/green Favorites, MCP-boundary, validation, handler, error-guidance, and logger-redaction Vitest; `npm run build`; full `npm test`; ephemeral official SDK `Client + StdioClientTransport` first/continuation calls; `npm pack --dry-run --json`; independent Standards/Spec review; `git diff --check`; scoped credential/private-identifier scan; `git status --short`.
- Result: The focused suite passes 7 files / 229 tests; the full suite passes 25 files / 405 tests; TypeScript builds cleanly; and the package has 138 entries with zero scripts, tests, agent-memory, QA, or research paths.
- SDK evidence: Ten tools appear in the frozen order. A redacted live first call returned one fixed 20-row page and a cursor; one continuation advanced to page 2. Parsed legacy JSON exactly matched `structuredContent`, and the SDK accepted the output schema. The one-off verifier was removed after acceptance.
- Boundary evidence: Invalid/non-canonical cursors use zero credentials/network; emitted cursors cannot overflow safe integers; an authenticated call uses nav + created/list-all + at most one resource/list request; raw-empty and filtered-empty pages differ correctly; stale cursors, malformed Folder rows, string Folder titles, cross-Folder duplicate BVIDs, reported-count discrepancies, and debug identifier redaction have regressions.
- Scope: No Cookie, account ID, Folder ID/title, Video title, cursor value, or secret is persisted in durable evidence. No Git, version, release, publication, learning-promotion, or Issue #20 operation occurred.

## 2026-07-27 v1.10.0 Source Preparation

- Commands: current npm/GitHub/OIDC checks; `npm ci`; `npm audit --omit=dev --json`; full development audit summary; `npm run build`; `npm test`; `npm pack --dry-run --json`; official SDK server-version/tool-order and real Favorites first/continuation calls; version/tag availability; strict UTF-8, high-confidence secret, diff, package-boundary, and README checks; independent `release-verifier`.
- Result: Source and compiled server report `1.10.0`; 25 files / 405 tests pass; the 138-entry package contains required main/types/CLI/Favorites outputs and public bilingual docs with zero internal/test/source/environment paths. The official SDK sees ten tools and exact text/structured parity on both real Favorites calls.
- Security and workflow: 38 intended files have zero high-confidence secret findings and zero new replacement characters. Production audit has two known moderate nodes and zero high/critical; the unchanged dependency graph and stdio-only reachability conclusion remain accepted. Current official docs confirm the existing Ubuntu, Node 22.14.0, npm 11.18.0, `id-token: write`, `contents: read`, test/build/publish workflow needs no edit.
- Release boundary: npm `1.10.0` and local/remote tag `v1.10.0` were available. The verifier reported no blocker if `docs/agent-memory/pending-learning-proposals.md` remained unstaged.

## 2026-07-27 v1.10.0 Publication

- Commands: exact staged-file review; scoped commit and `master` push; annotated tag creation/push; GitHub Actions run watch; remote tag dereference; live npm latest/integrity/shasum/provenance lookup; isolated exact-package CLI version/help smoke; GitHub Release creation/inspection; Issue #22 evidence comment, label cleanup, and completed closure.
- Result: Commit `7ff225784abe426f64bd658fd8a23112e24b1265` is the remote tag target. Actions run `30230653151` passed install, 25 files / 405 tests, build, and trusted publication. npm latest is `1.10.0`; integrity is `sha512-Np2jIaorvp8bri4QV3Mm2XHj9ZoIARbzIaFQ1OR+rOgX+L9U8AD0SE/Dap3ck2jMenBEfhlpO5qxseYrguaWQA==`, shasum is `6442761a91adf93cd0b70c248cd464b276c47be5`, and SLSA provenance is present. The published CLI reports `1.10.0`, help works, the GitHub Release is public, and Issue #22 is closed.
- Scope and security: The immutable tag contains exactly the 38 intended files, including both README updates, and excludes `pending-learning-proposals.md`. No Cookie or private account/Favorites data was printed, committed, packaged, or posted.
- Caveat: The successful workflow emitted a deprecation annotation for the Node 20 action runtime used by `actions/checkout@v4` and `actions/setup-node@v4`; GitHub forced Node 24. Treat action-version refresh as future workflow maintenance, not a reason to rewrite this successful release.

## 2026-07-27 README Favorites-to-Evidence Story

- Commands: `beautify-github-readme` audits for both READMEs; 18-local-link and bilingual heading-level checks; strict UTF-8; SVG XML, `viewBox`, title/description, and unsafe-feature checks; local Browser previews at 900px and 360px; mobile overflow inspection; ten-tool coverage; high-confidence added-text secret scan; `npm pack --dry-run --json --ignore-scripts`; `git diff --check`.
- Result: Both landing pages present Favorites/topic discovery → BVID → timestamped transcript evidence before installation detail. After user review, both heroes were narrowed to the exact Favorites traversal: start without `cursor`, read one Folder/page of at most 20 rows, pass `next_cursor` into the next call, and finish with visible titles and BVIDs when that field is absent. The real `BV1Eb411u7Fw` Part 4 and `?p=4&t=1.12` proof remains in adjacent Markdown. Both widths render without document-level horizontal overflow, all links and ten tool names remain reachable, and the 138-file package contains both READMEs and both heroes with no task, memory, source, test, preview, or environment paths.
- Scope: Runtime source, schemas, tests, generated output, setup guides, tool references, release workflow, and credentials are unchanged. Build and Vitest were intentionally skipped for the design pass; the later `v1.10.1` release preparation runs the full release gates separately. `pending-learning-proposals.md` remains untouched, and the codemap was checked and left unchanged.
- Review: A bounded read-only `final_diff_review` subagent did not return a report before interruption; Codex completed the final bilingual, factual, visual, and scope review directly.

## 2026-07-27 v1.10.1 Source Preparation

- Commands: bilingual README audits; 18-local-link, heading-parity, strict UTF-8, SVG XML/safety, 900px/360px, added-line secret, version/tag-availability, and diff checks; `npm run build`; `npm test`; focused MCP tests; built-server SDK stdio discovery; `npm pack --dry-run --json --ignore-scripts`; independent `release-verifier`.
- Result: Package/lock, compiled CLI, and built MCP server report `1.10.1`; 25 files / 405 tests pass; the MCP surface remains ten tools in the frozen order, with 37/37 focused tests passing. The 138-file package contains both READMEs, both Hero SVGs, and required main/types/CLI output while excluding source, tests, tasks, QA, agent memory, previews, environment files, and obsolete Smithery content.
- Security and boundary: Release additions and package contents have zero credential findings; four repository-wide matches are unchanged synthetic logger-redaction fixtures. Runtime source, schemas, tests, dependencies, and publish workflow are unchanged. npm `1.10.1` and local/remote tag `v1.10.1` are available.
- Release boundary: The verifier reports no blocker if the exact 11-file staged set excludes `docs/agent-memory/pending-learning-proposals.md`.

## 2026-07-27 v1.10.1 Publication

- Commands: exact 11-file staged review; scoped commit and `master` push; annotated tag creation/push; GitHub Actions run watch; remote annotated-tag dereference; live npm latest/integrity/shasum/provenance lookup; isolated exact-package CLI version/help smoke; GitHub Release creation/inspection.
- Result: Release commit `3aee13d9111feb7342b3a287baf4c1cb81741a04` is the remote tag target. Actions run `30233179604` passed install, 25 files / 405 tests, build, and trusted publication. npm latest is `1.10.1`; integrity is `sha512-Q08jBSAoEDYbbzlf52zMFhg9HcKCQ2guGBR7JtT1CcraFW2vvwwXu9dSUy4OsqGwDi6D1wT3D7DoBxN1TCcWpQ==`, shasum is `f52621b9ab575b43bc8c4b93be907e8df6432b6b`, SLSA provenance is present, the published CLI reports `1.10.1`, help works, and the GitHub Release is public.
- Scope and security: The immutable tag contains exactly the 11 intended documentation/version files and excludes `pending-learning-proposals.md`. Runtime source, MCP schemas, tests, dependencies, and workflow are unchanged.
- Caveat: The successful workflow repeated the existing Node 20 action-runtime deprecation annotation for `actions/checkout@v4` and `actions/setup-node@v4`; GitHub forced Node 24. Keep that as separate bounded workflow maintenance.

## 2026-07-27 CLI Setup And Doctor

- Commands: `npm run build`; focused `tests/cli.test.ts` plus `tests/mcp-server-smoke.test.ts`; full `npm test`; `npm pack --dry-run --json`; built CLI help, doctor, setup, no-argument stdio, and version probes; `git diff --check`; scoped high-confidence secret scanning.
- Result: Build passes; the focused suite passes 30 tests; the full suite passes 26 files / 431 tests; and the package remains 138 files with zero test, QA, agent-memory, `.env`, `.claude`, or `.codex` entries. Built CLI no-argument startup keeps stdout empty and ready signaling on stderr.
- CLI evidence: Help has no duplicated `[command]`; `doctor --json` emits one parseable secret-free object; isolated HOME returns `needs_credentials` with exit 1; current local credentials return `locally_ready` with exit 0; deterministic fault injection proves exit 2; non-TTY setup exits 1 without prompting; expired/unloadable credentials reach reconfiguration; `-V`, `--version`, `-v`, and `version` all report 1.10.1.
- Scope: MCP tools/schemas/handlers, Bilibili requests, dependencies, package metadata, generated `dist/`, and release workflow are unchanged. The pre-existing `pending-learning-proposals.md` modification remains untouched. No commit, push, tag, release, or publication was performed.

## 2026-07-27 Bilingual README Full Redesign

- Commands: both `beautify-github-readme` audits; bilingual heading/tool coverage; local-link and strict UTF-8 checks; SVG XML, accessibility, external-resource, and unsafe-feature checks; independent ImageMagick renders at 900px and 360px; scoped high-confidence secret scan; `npm run build`; 30 focused CLI/entrypoint tests; full `npm test`; built CLI help and secret-free doctor probe; `npm pack --dry-run --json --ignore-scripts`; live npm/Commander engine lookups; `git diff --check`.
- Result: Both READMEs pass with seven equivalent top-level sections and all ten MCP tools. All four SVGs render without clipping or overlap; the installation pair remains readable at 360px and keeps `doctor --json` visible. Build passes, 2 focused files / 30 tests pass, and 26 files / 431 tests pass.
- Package and security: The 140-file, 126,320-byte dry run contains all four README SVGs and excludes source, tests, QA, agent-memory, environment, Claude, and Codex paths. Local links pass, SVGs have no scripts, `foreignObject`, or external resources, and the changed worktree has zero high-confidence credential findings.
- Release boundary: npm latest is still `1.10.1`; the rewritten `@latest setup`/`doctor` guidance is intentionally Unreleased and must ship with the CLI. Commander 14.0.3 requires Node 20 while package metadata still says Node 18, so the engine-floor mismatch remains a release blocker. No commit, push, version bump, tag, release, or publication occurred.

## 2026-07-27 README User Comprehension Repair

- Commands: independent Agent-install and Windows manual-install persona walkthroughs; bilingual `beautify-github-readme` audits; strict UTF-8, required onboarding content, local-link, high-confidence secret, package-boundary, and `git diff --check` checks.
- Result: After final fact review caught and repaired a missing copyable `doctor --json` invocation, both persona walkthroughs report no blocking ambiguity. The READMEs now contain independently complete Agent-assisted and manual paths, all three exact `setup` / `check` / `doctor --json` commands, and the setup guides explain how to locate only `SESSDATA`, `bili_jct`, and `DedeUserID` in Chrome, Edge, or Firefox before hidden local entry. The bounded documentation check reports `COMPREHENSION_DOC_CHECK=PASS`.
- Package and security: The final dry run contains 140 files / 127,990 bytes and no source, test, QA, agent-memory, environment, Claude, or Codex paths. High-confidence secret findings remain zero; no Cookie value is requested in chat, placed in MCP client configuration, or printed in documentation.
- Scope: This repair changes only bilingual onboarding documentation and its task/report records. Runtime code, MCP schemas, tests, package metadata, version, SVGs, and release workflow are unchanged, so build and Vitest were not rerun after this documentation-only repair. No commit, push, tag, release, or publication occurred.

## 2026-07-27 README Information Architecture Correction

- Commands: both `beautify-github-readme` audits; bilingual section-order and ten-tool checks; exact CLI command, Favorites best-effort, literal-keyword, local-link, high-confidence secret, package-boundary, and `git diff --check` checks; two independent read-only reviews.
- Result: Both READMEs now follow project definition → five core capability groups → three prominent use cases → installation → tool detail → limits/security. Independent review confirms that moving the unchanged Favorites SVG beside its matching example improves the opening. The two review findings—overclaiming every Favorite row and using untranslated `"function"` for a literal transcript search—were repaired and rechecked.
- Package and security: `README_INFORMATION_ARCHITECTURE_GATES=PASS`; 9 local links resolve; both READMEs retain all ten tools and complete `doctor --json` commands; high-confidence secret findings are zero. The 140-file / 128,346-byte dry run contains no source, tests, QA, agent memory, environment, Claude, or Codex paths.
- Scope: README ordering/copy, bilingual Unreleased changelog copy, and existing task/memory records changed. SVG files, runtime, tests, package metadata/version, dependencies, lockfile, workflow, QA checklist, and codemap are unchanged. Build and Vitest were not rerun for this documentation-only correction. No commit, push, tag, release, or publication occurred.

## 2026-07-27 DeepSeek README Logic Rewrite

- Commands: both `beautify-github-readme` audits; bilingual section-order, ten-tool, and three-command checks; Favorites best-effort/`skipped_count`, literal `函数`, keyword-only playback-link, local-link, high-confidence secret, package-boundary, and `git diff --check` checks; independent narrative and fact reviews.
- Result: `DEEPSEEK_README_GATES=PASS`. Both READMEs now flow from a user-outcome opening through three capability paths, three copyable examples, installation, tool detail, limits, privacy, development, and help. Narrative review found no blocker; the only factual review finding was repaired in both languages.
- Package and security: 9 local links resolve; all ten tools and all three complete CLI commands remain present; high-confidence secret findings are zero. The 140-file / 128,501-byte dry run contains no source, tests, QA, agent memory, environment, Claude, or Codex paths.
- Scope: DeepSeek changed only the bilingual READMEs, bilingual Unreleased changelog entries, and the existing Claude report. Codex updated the task and durable memory records after acceptance. SVGs, setup/reference guides, runtime, tests, package metadata/version, dependencies, lockfile, workflow, QA checklist, codemap, and pending learning proposals are unchanged. Build and Vitest were not rerun for this documentation-only rewrite. No commit, push, tag, release, or publication occurred.

## 2026-07-27 DeepSeek README Reader-First Repair

- Commands: both `beautify-github-readme` audits; custom bilingual section-order, ten-tool, three-command, local-target, first-use BVID, literal `函数`, Favorites best-effort/`skipped_count`, and comment-order contract checks; scoped high-confidence secret scan with redacted false-positive classification; `npm pack --dry-run --json --ignore-scripts`; `git diff --check`; two independent final reviews.
- Result: `README_CONTRACT_CHECK=PASS`. The final pages use a plain two-sentence introduction, three product outcomes, a visible Node.js prerequisite and four numbered install/verify steps, then three copyable examples. Both reviewers report no narrative or factual blocker.
- Package and security: Both image audits pass. The 140-file / 128,755-byte package contains all four README SVGs and excludes source, tests, QA, agent memory, environment, Claude, and Codex paths. Primary high-confidence secret patterns are zero; five `SESSDATA`-shaped matches were classified without printing values as four synthetic CLI fixtures and one historical scan placeholder.
- Scope: The final repair changed only the bilingual README/changelog copy, existing handoff/report/task records, and durable project memory. Build and Vitest were not rerun because runtime and tests were unchanged. No commit, push, tag, release, or publication occurred.

## 2026-07-27 Optional ASR Model Installation Phase 1

- Commands: `npm run build`; focused ASR/CLI/MCP smoke Vitest; full `npm test`; built CLI help and secret-free `doctor --json`; real local Python discovery and temporary managed-venv creation; `npm pack --dry-run --json --ignore-scripts`; scoped credential-pattern review; `git diff --check`; independent final-diff review.
- Result: Build passes; 95 focused tests and 27 files / 496 full tests pass; the package contains 148 files / 140,199 bytes with compiled ASR modules but no model, venv, state, test, QA, or agent-memory data. The real Windows smoke discovered Python 3.13.7 through `py -3`, created and rediscovered a temporary isolated venv, then moved that temporary venv to the Recycle Bin.
- CLI evidence: Default No has no ASR side effects. Yes uses the managed venv for pip, pinned snapshot download, and CPU INT8 verification; state becomes `ready` only after verification. Doctor currently reports `not_installed` on this machine and keeps credential status semantics unchanged.
- Security: Child processes use argv arrays, `shell: false`, Python isolated mode, bounded diagnostics, and filtered environment variables. An early failed test accidentally expanded the parent process environment into local agent logs; no value entered source or package output, the test seam was repaired to use synthetic environments, and external credentials present in that process should be assessed and rotated.
- Caveats: No real model download or CPU model-load smoke was run, and simultaneous `setup` processes are not locked. Model selection, audio retrieval, transcription, fallback integration, Git delivery, version bump, release, and publication remain out of scope.

## 2026-07-27 ASR Model Selector Phase 2

- Commands: `npm run build`; focused ASR/CLI/MCP smoke Vitest; full `npm test`; built selector mapping and CLI help probes; built secret-free `doctor --json`; `npm pack --dry-run --json --ignore-scripts`; scoped high-confidence secret scan with test-fixture classification; `git diff --check`; independent stable-tree review.
- Result: Build passes; 3 focused files / 169 tests and 27 files / 570 full tests pass. The selector exposes exactly `tiny` (~78.2 MB), `base` (~148 MB), and `small` (~486 MB); Enter and `3` resolve to `small`, invalid input resolves to no selection, and the built doctor reports `asr.status: not_installed` plus `asr.model: null` on this machine.
- State and failure evidence: The Phase 1 `small` marker remains readable under state version 1; exact repository/revision pairs are allowlisted; same-model setup is idempotent; cross-paired or malicious keys fail before mutation; switching models clears old readiness; and a failed switch is read as `incomplete`.
- Package and security: The dry run contains 148 files / 563,026 bytes, includes the compiled ASR modules, and excludes tests, QA, agent memory, local model data, venvs, state, `.env`, `.claude`, and `.codex` paths. Forty-seven changed or untracked files have zero high-confidence token/private-key findings; two Bilibili-shaped assignments are synthetic fixtures in `tests/cli.test.ts`. `gitleaks` is unavailable.
- Caveats: No real model weights were downloaded and no real CPU model-load smoke was run. Concurrent setup processes remain unlocked. Audio retrieval, transcription, automatic subtitle fallback, commit, push, version bump, release, and publication remain outside this phase. npm latest remains `1.10.1`, so the working-tree commands are not yet available through `@latest`.

## 2026-07-29 ASR Transcription Fallback Phase 3

- Commands: `npm run build`; the exact 10-suite Phase 3 focused command; full `npm test`; `npm pack --dry-run --json --ignore-scripts`; `npm audit --omit=dev --json`; built CLI help, version, and doctor; public stdio initialize/list/call tests; scoped high-confidence secret scan; UTF-8/link/parity checks; ASR temp residue count; `git diff --check`.
- Result: Build passes; 10 focused files / 356 tests and 29 files / 629 full tests pass. After repairing Phase 1/2 test-fixture directory cleanup, 2 ASR files / 126 tests pass and leave zero `bilibili-mcp-asr-*` temp directories.
- MCP evidence: Exactly ten tools remain in their original order. `get_video_transcript` alone accepts optional `fallback_to_asr` defaulting false, returns `data_source: "asr"` on ASR success, keeps text JSON equal to `structuredContent`, and shares timestamp/range/query/context/source-link transformations. The public legacy stdio flow initializes, lists, and calls a representative safe tool with JSON-only stdout.
- Playback/runtime evidence: Exact BVID/CID playurl parameters and Cookie ownership, deterministic audio ordering, malformed-versus-empty DASH, provider-specific HTTPS hosts, redirect revalidation, byte/duration/time/output/segment limits, filtered child env, `-I`, `shell: false`, timeout kill/close, strict NDJSON, concurrency, and every cleanup path are deterministic tests with no real network, Cookie, Python, audio, or model.
- Package and security: The package dry run contains 156 files / 159,670 bytes (630,098 unpacked) and excludes `.env`, tests, QA, research, agent memory, models, venvs, state, audio, and temp paths. A 282-file scoped scan found no private key, GitHub/npm/AWS token, or real credential; its three matches are one synthetic signed URL and two synthetic CLI credential fixtures. `gitleaks` is unavailable. Production audit reports two known moderate dependency nodes and zero high/critical; fixing them requires the separately excluded SDK/Hono major migration.
- Live boundary: Built doctor reports `asr.status: not_installed` and `asr.model: null`; no model was downloaded/switched and no live ASR E2E was run. No Git/release/protocol/learning-proposal action occurred.

## 2026-07-30 Deep Security Remediation

- Commands: original sealed-scan finding inventory; direct Codex remediation;
  22-file focused Vitest; full `npm test`; `npm run build`; Python
  byte-compilation; `.codex/scripts/test_hook_safety.py`;
  `.codex/scripts/test_stop_summary.py`; built CLI help and public stdio smoke;
  `npm pack --dry-run --json --ignore-scripts`; value-free full-tree and package
  secret classification; `npm audit --omit=dev --json`; `npm ls`; live npm
  metadata; SDK/project import reachability; official GitHub Action ref
  resolution; official `@openai/codex-security` CLI dry run and full-worktree
  deep scan.
- Result: All 38 original `extensions.reportId` finding slugs have implemented
  closing controls and rows in
  `docs/qa/2026-07-30-deep-security-remediation.md`. Focused security
  tests pass 22 files / 407 tests; full Vitest passes 38 files / 721 tests;
  TypeScript build passes; hook suites pass 6/6 and 8/8; built CLI and JSON-only
  stdio behavior pass.
- Network/resource boundary: stdio, MCP payload/envelope, outbound admission,
  decoded JSON, redirects, bootstrap waiters, caches, logs, comments,
  Favorites, playback, transcript search, ASR download/runtime/installer, and
  hook retention now have explicit process-local byte/time/count/concurrency
  ceilings. Playback DNS tests prove all-answer public validation, connection
  pinning, original-host TLS, and credential stripping using synthetic
  resolvers only.
- Package/security: the dry run contains 180 files / 190,267 packed bytes /
  776,730 unpacked bytes. Structural forbidden paths and high-confidence
  private-key/GitHub/npm/AWS-token package matches are zero. Whole-tree
  Bilibili-shaped assignments were classified without printing values as
  synthetic tests, scanner patterns, or redacted historical examples;
  suspicious unclassified matches are zero.
- Audit caveat: production audit remains two moderate nodes through
  `@modelcontextprotocol/sdk@1.27.1` →
  `@hono/node-server@1.19.14` and GHSA-frvp-7c67-39w9. Current project imports
  do not reach the SDK's Streamable HTTP/static-file module. This is
  installed-but-unreachable residual risk, not a zero-advisory result.
- Live boundary: no Bilibili request, real Cookie, signed media URL, ASR model,
  audio, Python transcription, stage, commit, push, PR, tag, version, release,
  publication, or persistent Codex config mutation was used.
- Independent scan: the official open-source Codex Security CLI resolved the
  exact `0a1b` worktree and passed deep-mode dry run using stored Codex
  credentials. Scan `c93dd212-6e9c-4ed0-a0c6-36bc93f9769b` then failed before
  artifact collection because CLI 0.1.3 completed the workbench scan before
  collecting canonical files; its output directory is empty. A fresh official
  CLI 0.1.4 scan and sealed result/report are required before completion.

## 2026-08-05 Strix + DeepSeek Follow-Up Remediation

- Executor: one Paseo-managed Claude Code agent using the live
  `claude/deepseek-v4-flash` provider; Codex independently reviewed the final
  state and returned four bounded same-scope repair rounds to the same agent.
- Closed boundaries: unsafe C1/bidi/zero-width remote text, non-string BVID
  engine-error disclosure, subtitle custom-port/userinfo admission, ASR state
  temp predictability/symlink/path-type/root-permission weaknesses, and the
  compatible SDK/transitive dependency advisories.
- Final commands: `npm run build`; `npm test`; focused stdio/tool/handler
  Vitest; `npm audit --omit=dev --json`; `npm pack --dry-run --json
  --ignore-scripts`; `git diff --check`; value-free secret classification; ASR
  state-temp residue count; Git stage/HEAD checks.
- Result: build passes; 39 files / 803 tests and 3 focused files / 95 tests pass;
  production audit reports zero vulnerabilities; `fast-uri` is compatibly
  locked at 3.1.5 without overrides; the dry-run package contains 180 files /
  788,704 unpacked bytes with zero forbidden paths; diff check passes; staged
  files, suspicious literal credential assignments, and ASR state temp residue
  are all zero.
- Boundary: no live Bilibili/Cookie or ready-model ASR E2E was run; no model,
  Python package, Git, version, release, publication, or learning-proposal
  action occurred. HEAD remains `ab4dd02854f0483fc7668c713523b4be77de6cc7`.

## 2026-08-05 v1.11.0 Publication

- Source: release commit `e43c247` was fast-forward pushed to `origin/master`;
  annotated tag `v1.11.0` points to the same commit. The GitHub Release title
  and body are bilingual Chinese/English.
- Local gates: TypeScript build passed; 39 test files / 803 tests and 95/95
  focused stdio/tool/handler tests passed; `git diff --check` passed; production
  audit, secret classification, and ASR state-temp residue were all zero.
- Package: dry run contained 181 files / 1,085,303 packed bytes / 1,706,096
  unpacked bytes, included all five README images, and contained zero forbidden
  source, test, internal report, local config, model, or credential paths.
- Publication: GitHub Actions run `31003552987` passed install, tests, build,
  and npm trusted publishing. npm `latest` and exact version are 1.11.0 with
  registry integrity, shasum, and SLSA provenance. An isolated exact-version
  npx smoke returned 1.11.0 and exposed setup, doctor, and config.
- Boundary: no ready local ASR model existed, so no model download/switch or
  live ASR end-to-end transcription was performed. The review-gated
  `pending-learning-proposals.md` change remained excluded from the release.

## 2026-08-05 v1.11.1 Source Preparation

- Source: HEAD `15bb5f8` (merge commit of PR #25) contains the merged AI
  subtitle ID fix in `src/bilibili/video-api.ts`; no source or test was edited.
- Version: `npm version 1.11.1 --no-git-tag-version` set `package.json` and
  both `package-lock.json` version fields to `1.11.1`; the diff touches only
  the version lines. npm `latest` remained 1.11.0; `v1.11.1` is free.
- Changelogs: `CHANGELOG.md` and `CHANGELOG_EN.md` gained matching `v1.11.1`
  sections describing only the merged fix (Issue #24, PR #25) and crediting
  `@CYL-collab`; a verification bullet records only actually run gates.
- Gates: `npm ci` (466 packages) and `npm run build` passed; 39 test files /
  803 tests passed; `npm audit --omit=dev --json` reported zero findings
  (info/low/mod/high/critical all 0); `npm pack --dry-run --json
  --ignore-scripts` reported `@xzxzzx/bilibili-mcp@1.11.1`, 181 files,
  1,706,201 unpacked bytes, with `dist/index.*`, `dist/cli.*`, `dist/server.*`,
  both READMEs, LICENSE, and the five README images, and zero source, test,
  internal-report, local-config, credential, model, or Smithery paths;
  `git diff --check` passed; strict UTF-8 decoding passed and added lines
  introduced zero U+FFFD characters (the log retains six baseline characters);
  value-free secret classification found only the
  pre-existing `test:env` environment-variable-name reference.
- Scope: `git status --short` lists seven modified files (both changelogs,
  package files, and `docs/agent-memory/active-work.md`,
  `docs/agent-memory/handoff-log.md`, `docs/agent-memory/verification-log.md`)
  and five untracked/new files (handoff, task ticket, research note, QA
  record, and this Claude report); source, tests, dependencies, workflow,
  READMEs, tool surface, `dist/`, and `pending-learning-proposals.md` are
  unchanged.
- Review: independent `release-verifier` and `risk-reviewer` checks both
  returned PASS with no release blocker. They confirmed PR #25 remains the
  candidate's ancestor, a normal fast-forward push cannot overwrite it, and
  the package, credential, changelog, workflow, and dirty-worktree boundaries
  are intact. Their two documentation-only findings (new-file count and
  baseline U+FFFD wording) were corrected before commit.
- Boundary: no Git commit, push, tag, npm publication, or GitHub Release was
  performed; publication remains Codex-owned and pending.

## 2026-08-05 v1.11.1 Publication

- Git: release commit `ce480f0` has PR #25 merge commit `15bb5f8` as its direct
  parent and was fast-forward pushed to `origin/master`. Remote annotated tag
  `v1.11.1` dereferences to `ce480f0`; PR #25 remains MERGED and Issue #24
  remains CLOSED.
- Automation: GitHub Actions run `31019814806` completed successfully; install,
  803 tests, build, and npm trusted publishing all passed. The existing Node 20
  action-runtime deprecation warning was non-blocking and caused no failed step.
- Registry: npm exact version and `latest` are `1.11.1`; integrity, shasum,
  tarball metadata, one signature, and SLSA provenance are present. Registry
  file count is 181.
- Public smoke: from an external temporary directory,
  `npx -y @xzxzzx/bilibili-mcp@1.11.1 --version` returned `1.11.1`; help output
  exposed `setup`, `doctor`, and `config`, and created no files in that directory.
- Release: GitHub Release `v1.11.1` is public, non-draft, non-prerelease, and
  bilingual; its notes thank `@CYL-collab` and link Issue #24 and PR #25.

## 2026-08-06 v1.11.3 Official MCP Registry Publication

- Source: annotated tag `v1.11.3` points to release commit `ac58a4b`, which was
  fast-forward pushed to `origin/master`; PR #25's merge commit remains an
  ancestor.
- Local gates: 39 files / 803 tests, TypeScript build, production audit with
  zero vulnerabilities, 181-file package inspection, value-free secret-pattern
  classification, and official `server.json` validation all passed.
- Automation: Actions run `31032259381` passed install, tests, build, and npm
  trusted publishing. npm reports `1.11.3` as `latest` with integrity, shasum,
  signature, and SLSA provenance; isolated npx smoke returned `1.11.3`.
- Release: GitHub Release `v1.11.3` is public, non-draft, and non-prerelease.
- Registry: `mcp-publisher` v1.8.0 published
  `io.github.XZXZZX-Ai/bilibili-mcp` version `1.11.3`; the public Registry API
  returned one exact match with `status=active` and `isLatest=true`.
- Boundary: npm v1.11.2 remains immutable but its lowercase Registry namespace
  was rejected with HTTP 403. v1.11.3 is the corrected public latest version.

## 2026-08-08 Contract Correctness Hardening (Uncommitted)

- Baseline: detached isolated worktree at
  `1b97183c70145eaf273bbddef4e0474e53bc177e`; Node `v25.6.1`, npm `11.16.0`.
- TDD: focused failures reproduced the old comments number schema, missing
  language enums, silent unsupported-language fallback, blank credential
  mutation path, permissive numeric parsing, non-video `-403` paid mapping,
  video-only access guidance, and late dotenv evaluation. Each targeted test
  passed after the corresponding minimum fix.
- Command: focused integrated Vitest run for comments, config, validation,
  handlers, cache, CLI, HTTP, WBI, and error guidance.
- Result: 10 files / 358 tests passed.
- Command: `npm run build`.
- Result: passed; TypeScript compiled the final source including
  `src/load-env.ts`.
- Command: `npm test`.
- Result: 41 files / 853 tests passed.
- Command: real child-process stdio protocol smoke for `initialize` → exact
  `tools/list` → representative `tools/call` plus unsupported language.
- Result: passed, 1 selected test / 11 skipped.
- Command: `npm pack --dry-run --json --ignore-scripts`.
- Result: 185 files, 1,088,165 packed bytes, 1,716,461 unpacked bytes; required
  index, CLI, declarations, dotenv bootstrap, package metadata, and license
  present; forbidden paths zero.
- Command: `npm audit --omit=dev --json`.
- Result: zero info/low/moderate/high/critical production vulnerabilities;
  97 production dependencies reported.
- Command: `git diff --check`, package-lock blob check, scoped secret-pattern
  classification, and independent `risk-reviewer` review.
- Result: diff check passed; `package-lock.json` remained
  `70cee9306932ebb2d32bc1cce4016770cd2963d4`; no private-key, provider-token,
  AWS-key, JWT, or real credential finding; reviewer returned PASS with no
  P0/P1/P2 blocker.
- Boundary: no live Bilibili/Cookie, ASR E2E, external desktop client, commit,
  push, tag, Issue/PR write, release, publication, or deployment occurred.

## 2026-08-09 Contract Correctness Hardening Review Correction

- Review correction: a two-axis pre-delivery review found that the original
  multi-page comments loop changed `ps` on its final request. Under Bilibili's
  page-number/page-size semantics that overlapped earlier rows and could omit
  requested main comments. The old mock's hard-coded 20-row offset had hidden
  the defect.
- TDD: a public-seam regression using real `pn`/`ps` offset semantics failed
  with 20 unique rows for `limit: 21`, then passed after requests kept
  `ps=20` and sliced locally. A second regression reproduced non-empty
  19-row pages and passed after pagination stopped only on an empty page or
  the bounded `ceil(limit / 20)` request count.
- Normalization correction: final standards review found that normalized-empty
  rows were still being used as the page-exhaustion signal. A `remaining=1`
  case with a rejected first row and valid later row failed before the raw and
  normalized states were separated, then passed. An all-rejected non-empty
  page regression confirms traversal continues to later pages.
- Malformed-container correction: a missing or non-array `replies` value first
  reproduced a silent empty success, then failed closed as
  `UpstreamResponseError`. Only an explicit empty array now represents
  confirmed page exhaustion.
- Refactor: supported-language membership and its error path now live in
  `src/utils/validation.ts`; `src/config.ts` delegates to that shared path.
  The task ticket status also uses the canonical `done` value.
- Gates: TypeScript build passed; 41 files / 857 tests passed; the selected
  real stdio JSON-RPC test passed; production audit reported zero
  vulnerabilities across 97 dependencies; the 185-file dry-run package had
  all required entrypoints and zero forbidden paths; `git diff --check`
  passed; and `package-lock.json` retained blob
  `70cee9306932ebb2d32bc1cce4016770cd2963d4`.
- Secret classification: private-key, GitHub-token, npm-token, AWS-key, JWT,
  and secret-filename checks were zero. Cookie-shaped matches were confined
  to bilingual placeholders, verification prose, and synthetic CLI tests;
  no credential value was printed or accepted as evidence.
- Final review: independent standards and specification reviewers returned
  PASS with no remaining P0-P3. Their final focused comments/error run passed
  51/51 tests, and both confirmed the explicit-empty versus malformed-response
  distinction at the public error boundary.
- Delivery boundary: branch/commit/push/PR/merge was explicitly authorized;
  version bumping, tags, npm publication, MCP Registry publication, and a
  GitHub Release remain outside this work.

## 2026-08-09 Search Response Hardening (Candidate)

- Baseline: isolated branch from merge commit `741dcf0`, which delivered the
  contract-correctness source changes through PR #26. Package version remains
  `1.11.3` and no release metadata changed.
- TDD: a missing `result` first reproduced the old successful-empty behavior,
  then failed closed after exactly one search-specific retry. Explicit empty,
  non-array, recovery-on-second-response, network-error, and public MCP error
  boundary regressions all pass.
- Result: focused 2 files / 36 tests; full 41 files / 862 tests; TypeScript
  build; selected real stdio smoke; zero-vulnerability production audit; and
  a 185-file package with required entrypoints and zero forbidden paths all
  passed.
- Boundary: an explicit `result: []` remains a one-request successful empty
  result. The original transient envelope was not captured, so this change
  does not claim that every observed empty array is an upstream defect.
- Final checks: `git diff --check` passed; `package-lock.json` retained blob
  `70cee9306932ebb2d32bc1cce4016770cd2963d4`; high-signal value-free scans
  found no private key, provider token, AWS key, JWT, or secret filename.
- Risk correction: an additional reviewer proved that shared `withRetry`
  always retries raw `ECONNRESET`/`ETIMEDOUT` codes even with a narrow type
  list. A raw-code regression failed at two calls, then passed at one after the
  search layer adopted a local shape-only loop. HTTP 503 and abort-during-
  backoff regressions also pass, preventing nested retry multiplication.
- Final review: risk, standards, and specification re-reviews returned PASS
  with no remaining P0-P3 after the local loop correction.

## 2026-08-09 v1.11.4 Local Release Candidate

- Baseline: isolated branch `codex/release-v1.11.4-prep` at unmodified HEAD
  `1067e02d3c906d62c4ec1bc48335b8e1dbec70f4`; merge-base and live
  `origin/master` match that commit.
- Metadata: `package.json`, both root `package-lock.json` version fields, and
  both `server.json` version fields report `1.11.4`; Registry name remains
  `io.github.XZXZZX-Ai/bilibili-mcp`. Candidate package/lock blobs
  `f42ace07d2f31859b2da1d773b4d7c9c001d35c4` and
  `c83866634e37a1ba1761c9a09902399ea5be9f9d` remained stable across clean
  install and build.
- Environment: publish-workflow-equivalent Node `22.14.0` and npm `11.18.0`
  on the Windows preflight host.
- Commands: `npm ci`, `npm run build`, and `npm test` through those exact
  runtime versions.
- Result: clean install passed; TypeScript build passed; full Vitest passed
  41 files / 862 tests; candidate CLI and MCP `initialize` each reported
  `1.11.4`.
- Stdio: `tests/mcp-server-smoke.test.ts` plus
  `tests/bounded-stdio-transport.test.ts` passed 2 files / 19 tests. Candidate
  `initialize` negotiated protocol `2025-06-18`; the exact ten-tool surface
  and JSON-clean stdout boundary remain covered.
- Package: exact-runtime `npm pack --dry-run --json --ignore-scripts` reported
  185 files, 1,088,656 packed bytes, and 1,718,670 unpacked bytes. Required
  index/types/CLI/package/license entries were present, forbidden paths were
  zero, and no `.tgz` remained.
- Audit: `npm audit --omit=dev --json` exited zero with 97 production
  dependencies and zero findings. Full-tree audit separately exited one with
  eight transitive dev-only findings: 1 moderate, 6 high, and 1 critical in
  `brace-expansion`, `ip-address`, `js-yaml`, `nanoid`, `npm`, `postcss`,
  `tar`, and `undici`; dependencies are unchanged in this patch release.
- Registry: repository `server.json` passed the live official 2025-12-11 JSON
  schema at version `1.11.4`, while its name matches packed
  `package.json.mcpName`. The manifest stays outside the tarball by existing
  publisher design.
- Live MCP: Node `22.14.0` candidate stdio loaded external `global_config`
  credentials and reported logged-in status. Three `五道口纳什` searches each
  returned 5 candidates with the target author. `黑神话悟空` returned 5
  candidates; public BVID `BV1AE4m1d7XT` returned 21 and 50 main comments for
  the corresponding limits with replies disabled. No Cookie value was printed.
- Secret and encoding boundary: changed release files and 183 package text
  files had zero high-confidence private-key/provider-token/AWS/JWT/literal-
  Cookie matches. The one tracked-tree literal-Cookie-shaped match is
  `tests/cli.test.ts`, classified as isolated synthetic test data and excluded
  from the package. All newly added files and candidate-added lines are strict
  UTF-8, introduce no BOM, and add no replacement characters;
  `verification-log.md` retains six historical baseline U+FFFD characters
  unchanged. `git diff --check` passed.
- Remote state: live checks found no tag, GitHub Release, or npm version
  `1.11.4`; npm `latest` and the Official Registry remain `1.11.3`.
- Final review: independent release-verifier, standards/security, and
  specification reviews returned PASS with no remaining P0-P3. The initial
  encoding-wording P2 was corrected and re-reviewed against zero replacement
  characters in candidate-added lines and new files.
- Boundary: candidate files are not yet committed, pushed, tagged, or published.
  The user explicitly authorized the full delivery/publication chain on
  2026-08-09; execution is now in progress behind the recorded gates.

## 2026-08-09 — v1.11.4 Publication And Public Artifact Verification

- Authorization: the user explicitly authorized commit, push, annotated tag,
  npm, GitHub Release, and Official MCP Registry publication.
- Git delivery: scoped release commit
  `2a33520739aa96187ad25b36c1e4247dbf8ff640` has parent
  `1067e02d3c906d62c4ec1bc48335b8e1dbec70f4` and was fast-forwarded to
  `origin/master` without force. Annotated tag object `390cd8d` peels to the
  release commit. A first HTTPS push attempt timed out before any remote write;
  a live remote recheck still found the parent, and the bounded retry passed.
- Trusted publication: GitHub Actions run `31296387097` concluded `success`.
  Its `publish` job passed checkout, npm install, `npm ci`, 41 files / 862
  tests, build, and `npm publish --provenance --access public`.
- npm public state: `@xzxzzx/bilibili-mcp@1.11.4` is `latest`; integrity is
  `sha512-B4SRRu4wYL5yGvVy/gp/XQSNvMW8UDk56Bx6WnU6YvTbislvg1EaQFwlqLkb/IyfOcEeusKSQpW4XXAaAEEXzg==`
  and shasum is `f693ce356c81725c7093e61ce03465c5d041a868`. Registry
  signature metadata is present, and the attestation predicate is
  `https://slsa.dev/provenance/v1`.
- Exact npm artifact: isolated installation added 97 packages. The
  `npm audit signatures` command verified 97 registry signatures and 10
  attestations. Node
  `22.14.0` executed the published CLI at version `1.11.4`; official SDK stdio
  reported server `bilibili-mcp-server` version `1.11.4` and the exact ten-tool
  list. A credential-safe live `五道口纳什` call returned five results and
  included the target author, with no Cookie value printed.
- GitHub Release: `v1.11.4 - Contract and search response hardening` is public,
  latest, non-draft, and non-prerelease at
  `https://github.com/XZXZZX-Ai/bilibili-mcp/releases/tag/v1.11.4`.
- Official Registry: official `mcp-publisher` `1.8.1` archive SHA-256 matched
  upstream digest
  `399ad0d6e00a50812b563a71d8bfbff5160c085e6b13aac6ec083d98d5ff7c45`.
  The saved Registry JWT was expired and was refreshed through the documented
  GitHub device flow without recording the device code or token. Publish then
  succeeded. Public API verification reports `1.11.3` active/not-latest and
  `1.11.4` active/latest, with the npm identifier and package version both
  matching `@xzxzzx/bilibili-mcp@1.11.4`.
- Non-blocking caveats: the successful Actions run warns that the pinned
  checkout/setup-node action bundles target deprecated Node 20 and are forced
  by GitHub to run on Node 24; the workflow still configures project commands
  with Node `22.14.0`. Full-tree development audit retains eight transitive
  dev-only findings, while production audit remains zero. Both belong to
  separate maintenance work rather than this immutable patch release.
- Result: `PASS`; every authorized public release surface is published and
  independently queryable. The immutable release tag remains on `2a33520`;
  this post-publication section belongs in a separate docs-only master update
  and does not move the tag.

## 2026-08-11 Harness v2 Issue #29

- Scope: isolated branch `codex/harness-v2-session-spine-29` at base
  `44ac1e717001aed59c4a3b475cf82f074d11e567`; shared rules, thin adapters,
  typed contract, portable Hook translators, shared CLI, bounded runtime
  ledger, capability diagnostics, replay fixtures, and project-memory updates.
  Product `src/`, package metadata, dependencies, workflows, and `dist/` are
  outside the diff.
- Commands: Harness unittest discovery; legacy Hook-safety and Stop-summary
  suites; Python compileall; `npm run build`; full Vitest; contract validation;
  `harness doctor`; `npm pack --dry-run --json`; scoped high-confidence secret
  scan; `git diff --check`; clean Codex/Claude rule-discovery smokes; Codex Hook
  process-boundary tests; real Claude failure lifecycle; two final read-only
  reviews.
- Result: Harness 26/26, legacy 6/6 and 8/8, build, 41 files / 862 Vitest tests,
  and typed contract validation passed. Package dry run contains 185 files,
  required `dist` entrypoints, and zero Harness/rules/project-memory paths.
  Thirty-seven changed files have zero high-confidence secret findings. Both
  final reviewers returned PASS with no P0-P3.
- Manual-Skill evidence: the user explicitly invoked `$implement` for #29.
  Host-bound reminder tests pass; the concurrency regression produces exactly
  one `reminder-emitted`, 23 `already-reminded`, and one ledger row.
- Worktree evidence: the dirty primary checkout remains at HEAD `ab4dd028…`
  with status 68 / `a4bbfb6d…`, tracked diff `78271fe3…`, untracked 44 / manifest
  `cf938aa3…`, and no `.harness`; all six values match the resume baseline.
- Caveat: a trusted normal-config Codex smoke proved live lifecycle dispatch but
  also triggered the primary worktree's legacy Hook in the linked worktree. Its
  date-only queue mutation was restored from the captured baseline and all
  primary-checkout fingerprints then matched exactly. `harness doctor` now
  reports this overlap as `action-required` and never rewrites it.
- Boundary: Issue #29 deliberately does not implement adapter execution loops,
  accepted-evidence memory projection, Harness evolution, remote Issue changes,
  push, PR, release, or publication. Full three-adapter pilot/release
  conformance belongs to #36.

## 2026-08-11 Harness v2 Issue #30

- Scope: isolated branch `codex/harness-v2-codex-direct-30` at exact parent
  `0ed8968bf94ea5b468e97665baac99e00c3b979e`; executable Codex Direct contract,
  state machine, canonical writer lease, action guards, typed evidence,
  fingerprint-bounded repair, Recovery Bundle, current-diff acceptance, and
  protected automatic local commit. Product `src/`, package/dependency/workflow,
  tracked Hooks, external configuration, and remote GitHub state are excluded.
- TDD/result: disposable repositories cover mode/base freeze, missing native
  `$implement`, concurrent transactions, linked-worktree rejection, guards,
  typed results/skips/risks/criteria, stale-diff review, repair fingerprint/
  limit, automatic adapter-failure recovery, malformed/symlink state, declared
  maximum state, bounded reminders, lock identity/hardlinks, task-source aliases,
  malformed sibling state, external/late Git filters, concurrent caller-index
  injection, Hook/signing suppression, CRLF/symlink conversion, exact index/
  snapshot and post-ref crash recovery, and one-commit/no-remote postconditions.
  Red races for two writers, executed late filters, and an injected staged path
  are green at the shared boundary. Harness discovery ran 92 tests in
  388.397s with `OK (skipped=1)` for one platform-permission symlink case;
  legacy Hook safety passes
  6/6; legacy Stop summary passes 8/8; compileall and example contract
  validation pass. Final controller/test SHA-256 values are
  `d2c21c9d9fbc301d5531f0038b21ffdf2e88f8659fbee30da98f6467b031e2f0` /
  `cf07d4bb4368ed58b9435413ee7506adc73ca370eb3295372a7e2bed36a52f59`.
- Product/package: `npm run build` passes; full Vitest passes 41 files / 862
  tests. `npm pack --dry-run --json` reports 185 files, 1,088,657 packed bytes,
  1,718,671 unpacked bytes, all three required `dist` entrypoints, zero
  forbidden Harness/rules/project-memory paths, and no emitted tarball.
- Real pilot: ignored disposable repository `github-30-real-v6` advanced from
  base `3b93fe44379bd827e9c687ec59a219268648984b` to the single accepted commit
  `1a326b9760ca9b23bb2ba25f6c0704941713b5b5`, changing only
  `harness-only.txt`. It has zero remotes and a clean tree; repeated acceptance
  is `already-committed`. The accepted snapshot digest is
  `e8837d20c4ee3cbb6a196e44e4883bcc877ef7a7af923c4183af106a7d48db0c`,
  accepted index digest is
  `4763b2413f680cf415e1cba34e59f0c31fc30cfe44cb43ad10221f352630bd34`;
  all required evidence binds to diff digest
  `df61b7d467d241cd08dae76212cee52b6d81c454c1929a09752268f10e3e99ee`.
  Runtime contains no canonical path/raw command and the common Git directory
  contains no Harness lease marker.
- Security/text: 21 candidate files have zero high-confidence token/private-key
  matches, UTF-8 decode errors, or BOMs; added diff lines contain zero U+FFFD.
  Historical verification commands intentionally retain U+FFFD as a search
  sentinel, so the whole-file count is not used as a corruption claim.
  `git diff --check` passes. Automatic commit tests prove configured Hooks/
  signing and late filters have no execution path, caller-staged content cannot
  enter the accepted tree, and post-ref index installation failure recovers
  without a second commit.
- Diagnostics: `python -m harness doctor --json` remains the expected
  `action-required`, with tracked/primary/user Codex Hook command counts 4/5/0.
  No external configuration was rewritten and the normal-config smoke stayed
  skipped with reason `doctor-action-required`.
- Dirty-primary isolation: `C:\Users\ZX\bilibili-mcp` remains at HEAD
  `ab4dd02854f0483fc7668c713523b4be77de6cc7`, status count 68 / hash
  `34ef9dee55da26ef977b54e795477f493e18dded`, tracked-diff hash
  `c9a4daa32c34115d3d443a52afa81301416b6082`, untracked count 44 / hash
  `2ec8b5fa42ed2cf4d684a5c7b9156998756abecb`, and staged count 0. All match
  the #30 pre-write baseline.
- Acceptance/review boundary: Spec review passed its final code axis; the final
  Standards and adversarial security axes independently returned PASS with no
  P0-P2 at the frozen controller/test hashes. A separate final risk-weighted
  acceptance review also returned PASS with no executable P0-P2. The focused
  commit containing this record exists only after the exact staged scope passes
  reinspection. Before that commit, these results describe the accepted
  candidate. No push, PR,
  Issue close, tag, release, publish, credential/SSH action, history rewrite,
  or broad deletion is authorized or performed.

## 2026-08-12 Harness v2 Issue #31

- Scope: isolated branch `codex/harness-v2-claude-direct-31` at exact parent
  `cbd31b952aa9f820005e60852bcd2d4db886a31c`; shared Claude Direct entrypoint,
  adapter-specific typed schemas/ownership, cross-adapter mode fencing,
  source-bound writer collision checks, native manual-Skill gate, shared guards,
  finite repair/Recovery Bundle, exact automatic local commit, executable
  conformance fixture, and synchronized project memory. Product `src/`, package
  metadata/dependencies/workflows, external configuration, and remote GitHub
  state are excluded.
- TDD/result: initial failures proved the missing public Claude command, a
  cross-adapter control seam, malformed `/$implement` reminder, mismatched
  reminder rollback identity, and static-only conformance. Review then added a
  credential-free child-process environment regression. Final Harness discovery
  ran 105 tests in 339.095 seconds with `OK (skipped=1)`; focused Claude module
  passed 11/11 after the repair. Legacy Hook safety passes 6/6, Stop summary
  passes 8/8, compileall and example contract validation pass.
- Product/package: exact-lockfile install enabled the initially dependency-empty
  worktree; build passes and full Vitest passes 41 files / 862 tests. Production
  audit reports zero vulnerabilities. Package dry run reports 185 files,
  1,088,657 packed bytes, 1,718,671 unpacked bytes, required dist entrypoints,
  zero forbidden Harness/rules/adapter/project-memory paths, and no tarball.
- Real Claude pilot: real Claude Code 2.1.212 attempt 2 completed the public
  Claude Direct loop in ignored zero-remote repository
  `github-31-claude-direct-real-v1`, advancing seed `c4844708…` to the single
  accepted commit `d4875bfe…`. It changed only `harness-only.txt`, finished
  clean with a released Claude lease, recorded two passing evidence records and
  one passing criterion, used zero repairs, and emitted no Recovery Bundle.
  Attempt 1 failed before Harness start on malformed strict MCP configuration
  and created no run or diff.
- Security/text: all 19 candidate files pass strict UTF-8/BOM and added-U+FFFD
  checks, the scoped high-confidence added-content scan has zero findings, and
  `git diff --check` passes. New subprocess tests allowlist only platform/process
  location keys, disable global/system Git config and credential prompts, and
  prove synthetic Bilibili/npm/GitHub credential keys cannot enter children.
- Diagnostics/isolation: `harness doctor` remains the expected
  `action-required`, with tracked/primary/user Codex Hook counts 4/5/0 and
  tracked/local Claude counts 5/0. App-created untracked `.codex/config.toml`
  remains unchanged and outside the commit. Dirty primary checkout
  `C:\Users\ZX\bilibili-mcp` still matches #30 exactly: HEAD `ab4dd028…`,
  status 68 / `34ef9dee…`, tracked diff `c9a4daa3…`, untracked 44 /
  `2ec8b5fa…`, and staged 0.
- Review/acceptance: fixed-base Standards and Spec follow-ups and the final
  independent risk reconciliation return PASS with no remaining P0-P3. Frozen
  controller/test SHA-256 values are `a40b65da…` / `595bd286…`. The single
  focused commit containing this record exists only after exact staged-scope
  reinspection; before then these results describe the accepted candidate. No
  push, PR, Issue close, tag, release, publish, credential/SSH action, history
  rewrite, or broad deletion is authorized or performed.

## 2026-08-12 Issue #32 Paseo Collaboration Verification

- Command: `PATH="/d/Git/cmd:$PATH" python -m pytest harness/tests/test_paseo_collaboration.py -v`
- Result: 36/36 passed in 115.11s (29 function tests + 7 CLI tracer tests).
- Area: Paseo collaboration adapter focused suite.

- Command: `python -m compileall -q harness .codex/scripts`
- Result: Passed.
- Area: Python byte-compilation of harness and hook scripts.

- Command: `git diff --check`
- Result: Passed (CRLF warnings only, expected on Windows).
- Area: Whitespace/conflict validation.

- Command: `git diff --stat`
- Result: 3 tracked files, +289/-14. New untracked: `harness/paseo_collaboration.py` (1479 lines), `harness/tests/test_paseo_collaboration.py` (1705 lines).
- Area: Diff scope.

- Command: combined `test_paseo_collaboration.py + test_codex_direct.py + test_contracts.py + test_cli_and_adapters.py`
- Result: **Blocked/hung**. The combined pytest process (PID 45224) hung in a Git child process and was terminated by Codex without touching the Paseo daemon or agent. Recorded as `blocked/hung`, pending Codex verification. The 36/36 focused collaboration suite, compileall, and diff-check remain valid writer evidence.
- Area: Combined shared-controller acceptance gates.

- Dead-code removal: `_validate_collaboration_contract` (~66 lines) removed from `paseo_collaboration.py`. This function duplicated shared `validate_task_contract()` checks. 36/36 tests continued to pass after removal.
- Area: Slice 8 deduplication.

- Remaining risks:
  - Combined suite hang requires independent Codex investigation and rerun.
  - Real Paseo-managed Claude pilot is Codex-owned and has not been launched.
  - Full TypeScript/Vitest/pack suite not run (no product changes; Codex-owned).
  - All changes remain uncommitted for Codex acceptance review.

## 2026-08-12 Round 4 same-agent repair (scope-compressed closure)

- Command: `python -m py_compile harness/codex_direct.py harness/paseo_collaboration.py harness/cli.py`
- Result: Passed.
- Area: Round 4 production changes (unlocked-core extraction, acceptance lock,
  recovery bundle collaboration section, bounded subprocess/file reads).

- Command: `PATH=/d/Git/cmd:$PATH python -m pytest harness/tests/test_paseo_collaboration.py -v`
- Result: 52/52 passed in 251.37s (function tests + CLI tracer tests).
- Area: Full focused Paseo collaboration suite after Round 4 changes.

- Command: focused tracer selection (`-k "slice8_accept or slice35_repair or slice4_at_most"`)
- Result: 3/3 passed in 18.57s (acceptance pending-dispatch block, repair
  prepared-intent block, at-most-once dispatch).
- Area: Strongest new dispatch/repair/acceptance regression proofs.

- Round 4 production changes: extracted `_accept_codex_direct_unlocked` shared
  seam (acceptance now holds `run.lock` in `collaboration_accept` and calls the
  unlocked core — no TOCTOU precheck); `_enter_recovery_unlocked` emits a
  bounded secret-free collaboration evidence section (last-persisted agent
  identity/state, frozen bridge handoff digest, bridge + sidecar digests) for
  `codex-paseo-claude` runs only; all four bootstrap failure sites route
  through the shared recovery path so `recovery-required` always has a
  durable bundle; raw failure text is never persisted in the run record
  (hashed category/fingerprint only); `_run_paseo_cli` replaced
  post-allocation capture with concurrent bounded drain + kill on overflow/
  timeout and metadata-only errors; handoff/review/preferences reads use
  `read_bounded_bytes`.
- Area: Round 4 controller scope compression (Slices 3+5, 4+8, recovery).

- Second controller audit fixes: removed `run["error"]` persistence in
  `_bootstrap_recovery` (run shape has no error key; the reload in
  `_enter_recovery_unlocked` rejected it, so inspect-failure bootstrap
  exited 2 instead of 6); collaboration evidence now binds the frozen
  `bridge_handoff_digest` and validates its strict 64-hex shape; evidence
  identity is documented as last-persisted run-record state, not live.

- Command: `PATH=/d/Git/cmd:$PATH python -m pytest harness/tests/test_paseo_collaboration.py -v -k "test_slice3_inspect_fail_closed_on_missing_field or test_recovery_bundle_roundtrip_status"`
- Result: 2/2 passed in 15.72s (exit 6 without raw error persistence; full
  collaboration evidence round-trip through the public status path).
- Area: Second-audit targeted regression proof.

- Command: `python -m py_compile harness/codex_direct.py harness/paseo_collaboration.py harness/tests/test_paseo_collaboration.py`
- Result: Passed (re-run after second-audit fixes).

- Remaining risks:
  - Combined shared-controller suite not rerun; pending Codex verification.
  - The 52/52 focused run predates the second-audit fixes; only the two
    targeted tests were rerun after them (per controller instruction).
  - Real Paseo pilot and full release gates are Codex-owned and not started.
- All Round 4 changes remain uncommitted for Codex acceptance review.

## 2026-08-13 Issue #32 final controller acceptance

- Repair attempt 6: same original Paseo writer closed six independently
  reviewed root findings. Six new focused proofs passed 6/6, `py_compile`
  passed, and the then-full collaboration module passed 71/71 in 274.79s.
- Repair attempt 7: the user explicitly changed the model freeze. The idle
  original writer released its logical lease before replacement agent
  `0bdef442-14db-4f35-9e0d-c1516bb38166` became the sole writer. Live inspect
  proved `claude/deepseek-v4-pro[1m]`, thinking `max`,
  `bypassPermissions`, and canonical cwd. The public-CLI malformed-contract
  proof passed 1/1 in 2.27s, 1/1 in 2.00s on the max-thinking verification turn,
  and 1/1 in 2.31s under independent Codex rerun. Both agents ended idle; the
  replacement lease was released to Codex acceptance.
- Independent acceptance and Standards re-reviews: PASS with no remaining
  P0–P2 finding. The analogous Direct-start expression is unchanged from the
  accepted #31 base and is recorded as a nonblocking follow-up, not expanded
  into Issue #32.
- Final staged review then found one actor-authority gap: an accepted Claude
  caller could pass `local-commit` through the actor-agnostic shared guard. The
  user authorized repair attempt 8 on the same DeepSeek V4 Pro writer at
  thinking `max`. RED reproduced `AssertionError: 0 == 0` because Claude was
  allowed. The minimum early denial made the new accepted-lifecycle proof PASS
  1/1 in 17.19s and all seven guard tests PASS in 31.84s; `py_compile` passed.
  Codex independently reran the proof 1/1 in 15.377s. The two reviewers that
  found the gap independently reran/reviewed the repair and both returned PASS
  with no P0–P2 blocker. The writer ended idle and released its lease.
- Command: `python -m unittest discover -s harness/tests -p "test_*.py"`
- Result: 177 tests ran in 845.622s; OK (skipped=1). This full-suite snapshot
  includes the first 72 collaboration tests. The subsequent attempt-8 delta is
  the isolated actor guard plus one focused regression described above; it was
  intentionally not followed by another broad suite.
- Command: `python -m compileall -q harness .codex/scripts`
- Result: PASS.
- Command: `python .codex/scripts/test_hook_safety.py`
- Result: 6/6 PASS.
- Command: `python .codex/scripts/test_stop_summary.py`
- Result: 8/8 PASS.
- Node/package evidence reuse: `git diff --quiet -- package.json
  package-lock.json tsconfig.json src tests .github` returned zero, so the
  already-passing build, 41 files / 862 Vitest tests, and 185-file pack remain
  current. No product/package input changed.
- Real pilot reconciliation: the zero-remote pilot predates attempts 6–7 and
  is retained as real integration evidence for Paseo/provider resolution,
  native `/implement`, bounded write/report, one accepted commit, and zero
  remotes. Later changes are negative-path/input/metadata/guard hardening proven
  by current public-process tests and the final suite; no hash-identical pilot
  claim is made.
- Diagnostics/isolation: `doctor` remains the expected `action-required`
  legacy Hook-overlap state with no config rewrite. Base/parent/branch remain
  `5e9de4b…` / `cbd31b9…` /
  `codex/harness-v2-paseo-claude-32`. The dirty primary remains HEAD
  `ab4dd028…`, status count 68, joined-line digest `a4bbfb6d…f8423`, staged
  0. No daemon restart, push, PR, Issue close, tag, release, publish, SSH,
  credential action, or history rewrite occurred.

## 2026-08-13 Final review closure (repair attempt 4)

Six release blockers fixed; one regression proof per root cause (new tests
`test_fix1`–`test_fix5`):

1. Preflight accepts Paseo 0.2.5 `connectedDaemon: reachable`; unreachable
   still rejected (`test_fix1_preflight_accepts_reachable_daemon`).
2. Dispatch/repair prompt files are ephemeral (removed in `finally` after
   send); report nested objects (commands/skips/risks/evidence) allow exact
   key sets only and persist normalized projections, never the caller's raw
   object (`test_fix2_report_rejects_risk_extra_keys`). The fake Paseo now
   captures the prompt at send time; `test_slice2_prompt_file_format` proves
   format from the send event and that no prompt file survives.
3. Repair delivery evidence is attempt-keyed (`repair-pending-{n}` /
   `repair-dispatch-{n}`); a completed attempt never blocks the next,
   a prepared current-attempt intent blocks replay, and acceptance blocks any
   pending-N lacking dispatch-N (`test_fix3_two_sequential_repairs_attempt_keyed`).
   Recovery folds the attempts into two logical sidecar digests
   (`repair-pending-attempts` / `repair-dispatch-attempts`) over a canonical
   sorted name→digest map.
4. Acceptance binds launch/report/task/agent IDs and launch/bridge/handoff
   digests to the frozen run record under the task lock; the expected agent
   never comes from mutable launch.json alone
   (`test_fix4_accept_rejects_tampered_launch_agent_id`). The launch digest
   uses one shared serialization seam (`_launch_digest`).
5. Post-launch malformed (list) inspect output routes to the shared Recovery
   Bundle path with the candidate agent ID preserved; no AttributeError, no
   raw error persisted (`test_fix5_bootstrap_inspect_list_enters_recovery`).
   The two inspect CLI tracers now assert the no-raw-error contract.

- Command: `python -m py_compile harness/paseo_collaboration.py harness/codex_direct.py harness/tests/test_paseo_collaboration.py`
- Result: Passed.
- Command: five fix proofs + three updated tracers (targeted): 8/8 passed.
- Command: `PATH=/d/Git/cmd:$PATH python -m pytest harness/tests/test_paseo_collaboration.py -v`
- Result: 58/58 passed in 186.35s (function tests + CLI tracer tests).
- Command: `git diff --check`
- Result: Passed after removing the stray blank line at EOF in
  `docs/agent-memory/verification-log.md`.
- Docs: codemap.md, active-work.md, project-facts.md, harness-eval.md, and
  harness-security.md test/line counts updated to the final-review truth.

- Remaining risks:
  - Combined shared-controller suite not rerun; pending Codex verification.
  - npm gates, `npm pack --dry-run`, and the real Paseo pilot remain
    Codex-owned and were not run.
  - All changes remain uncommitted for Codex acceptance review.

## 2026-08-13 Issue #33 Typed Memory Verification

- Baseline: clean independent worktree at exact accepted #32 commit
  `9cbb8de64ffedefd682517e203841dd137b75662`; its direct parent is accepted #31
  commit `5e9de4bace35a2ca4b9c83b5a0d81ebb627df6fb`. Branch is
  `codex/harness-v2-typed-memory-33`.
- Live scope: GitHub #33 is open with title `[Harness v2] Automatic typed
  memory from accepted evidence`; live dependency metadata still names open
  #30, while the accepted implementation chain through #32 satisfies the
  ticket's specified commit baseline. No live Issue or remote state changed.
- Doctor: `action-required` only for the known primary legacy Codex Hook
  overlap. No primary/user Hook, Skill, Agent, MCP, or configuration rewrite
  was performed.
- TDD: focused typed-memory tests progressed from missing-module/schema failures
  to 33/33 pass in 69.134s. Coverage includes record shape, replay/no-change,
  semantic digest binding, supersession and equal-time conflict, correction and
  independent-task lesson thresholds, weak evidence, secret/raw payload
  rejection, six record types, invalid dates/writers, tamper checks, bounded
  startup, deterministic capability builds, and the real memory-only pilot.
- Shared Harness modules: Codex Direct 61/61 in 427.367s (one platform-
  permission skip), Claude Direct 12/12 in 84.850s, Paseo collaboration 73/73 in
  263.526s, and CLI/contracts/events core 32/32. Final unified discovery passed
  211 tests in 873.324s with one skip.
- Legacy compatibility: Hook safety 6/6 and Stop-summary 8/8 passed. Python
  compileall passed.
- Product isolation: exact-lockfile `npm ci` was required because this fresh
  worktree had no dependencies; it changed no package metadata. TypeScript
  build passed and full Vitest passed 41 files / 862 tests in 11.61s.
- Package/security: production audit reports zero vulnerabilities across 97
  production dependencies. Dry-run pack is version 1.11.4 with 185 files,
  1,088,657 packed bytes, and zero Harness, `.harness`, agent-memory, RULES,
  AGENTS, or CLAUDE entries. `package.json` and `package-lock.json` are
  unchanged.
- Real process-boundary pilot: disposable zero-remote source task commit
  `62caea4d73e0f88d81803ecd6abc70aae9faed54`, followed by exactly one
  memory-only commit `a3e6fcabdd36849f46a738592a24d815b64d337b`. Its two paths were exactly the
  typed store and current projection; replay was no-change, audit line count was
  two, final status was clean, and no remote existed.
- Independent risk review: PASS with no remaining P0-P2. Review-driven red/green
  repairs cover A→B→A facts, different-time lesson support, secret/raw key and
  command variants, exact Direct memory-only writer locking, source/target
  identity, projection/store/HEAD binding, node bounds, future validity, and
  isolated pilot environment.
- Frozen candidate gates: 23 paths, all under `harness/` or
  `docs/agent-memory/`; strict UTF-8 passed; the index and product/package diffs
  are empty; `git diff --check` and tracked/untracked secret scans pass.
- Final Doctor remains the known `action-required` Hook-overlap result with
  tracked/primary/user Codex command counts 4/5/0. Primary HEAD, tracked diff,
  empty staged diff, untracked manifest, status digest, and count 44 exactly
  match the recorded baseline.

## 2026-08-13 — Harness v2 Issue #34 governed Skill and Agent evolution

- Baseline: clean independent worktree, branch
  `codex/harness-v2-skill-agent-evolution-34`, exact #33 HEAD
  `1cd12c8a6edab272bd16ad5ecb8ba2ae4bd90cf8`, direct parent #32
  `9cbb8de64ffedefd682517e203841dd137b75662`, and pushed #33 remote ref exact.
- Live scope: GitHub #34 remains open, parent #28, blocked by #33, and titled
  `[Harness v2] Governed Skill and Agent evolution`. No remote state changed.
- Mode: the user explicitly selected `codex-direct`; the typed contract froze
  the base/branch/owned paths and Codex acquired the only writer lease. No
  Paseo/Claude adapter was launched or used as a writer.
- Doctor: isolated-home exact command returned expected `action-required` with
  tracked/primary/user Codex Hook counts 4/5/0. The isolated capability lists
  were intentionally empty and were not used as catalog evidence; no external
  configuration was rewritten.
- TDD: focused evolution suite progressed from missing CLI/module behavior to
  final 10/10 pass in 481.432s. Coverage includes accepted-gap provenance, independent
  worktree/writer, exact ignored-state validation, protected paths, pinned
  candidate contract, Search/Adapt/Build ordering, idempotent authorization,
  canonical host packages, manual/model invocation, bounded read-only agents,
  drift/self-approval denial, rollback, reports, zero remotes, and exact-one
  local commits. Typed-memory regressions pass 33/33 in 62.953s.
- Search evidence: installed `find-skills` route was inspected without running
  its unpinned `npx` command; installed `vitest` SHA-256 is `3dcdc45f…6375`.
  Live `antfu/skills` is MIT at verified commit
  `a74f281a27dadc02397bc1a174b0f2c97531b6ae`; pinned Skill SHA-256 is
  `2da9b15c…8968`, LICENSE SHA-256 `2a596f69…1cb2`. Mismatch/unknown installed
  provenance caused deferred/no-install.
- Current-diff focused evidence: Evolution 10/10 in 481.432s; typed memory
  33/33 in 71.401s; legacy Hook 6/6; legacy Stop 8/8; Python compileall,
  `py_compile`, Ruff, and `git diff --check` pass.
- Product/package: TypeScript build passes in 2.619s; Vitest passes 41 files /
  862 tests in 9.986s; `npm pack --dry-run --json --ignore-scripts` reports
  185 files and zero forbidden Harness/internal paths. The production audit
  attempt reached no advisory result because TLS failed before the npm registry
  request; package/dependency inputs are unchanged from accepted #33.
- Boundary checks: all 16 intended paths are strict UTF-8; added diff lines have
  zero high-confidence secret-pattern hits. Product/package inputs, shared
  controllers, constitutional files, and staged index have zero diff. Primary
  HEAD/status/tracked/staged/untracked fingerprints match the #33 frozen values.
- Independent risk review passes the accepted-gap receipt, forged Adapt state,
  and terminal writer-lease audit under the existing repository-process trust
  model. One monolithic Harness discovery process exceeded its 30-minute ceiling
  without failure output; it was not rerun. Current-diff shards all pass:
  Direct/Claude 73 (one skip), Paseo 73, CLI/contracts/events 32, typed memory
  33, and Evolution 10, for 221 executed tests / one skip with no failure.
- Final release review found one actionable terminal seam: promotion-ready
  revalidation failure previously stopped without restoring known candidate
  output. The shared acceptance gate now rolls that state back to a rejected
  report while unknown/drifted files still enter Recovery. Its focused
  public-CLI rollback/commit proof passes 1/1 in 146.898s; the reviewer closed
  the finding after the rejected-reason invariant was added.

## 2026-08-13 — Harness v2 Issue #35 MCP/CLI/Hook/Loop evolution

- Baseline: independent clean worktree on branch
  `codex/harness-v2-mcp-cli-hook-loop-evolution-35`, exact accepted #34 HEAD
  `493393c9ef4941e5ff8dc7b66acaa6cd9d06d7ce`. The dirty primary checkout stays
  isolated. The user selected `codex-direct`; one Codex writer lease is active
  and no Paseo/Claude writer was launched.
- Live source audit: Issue #35 remains open with parent #28 and blocker #34.
  Official npm reports `@modelcontextprotocol/inspector@2.2.0` MIT metadata,
  integrity `sha512-IUyZ…RxA==`, GitHub release/tag commit
  `672f9f41c548487a468b9e7007d2f9de14da5a69`, Node `>=22.19.0`, and a
  `postinstall` plus browser/listener surface, so it is not eligible for silent
  auto-adoption. Official `@modelcontextprotocol/conformance@0.1.16` is MIT and
  executable but has runtime dependencies/network behavior, so it is Search
  evidence rather than a repository-local no-effect candidate.
- TDD: safe byte-canonical CLI Adapt, dangerous MCP authorization, four surface
  Build/promotion/three-adapter/commit, Hook/Loop policy, public Loop decisions,
  and authorization canonical-order tests progressed red to green. The legacy
  executable candidate remains authorization-required.
- Focused current evidence: Evolution 13/13 pass in 853.936s; Hook events 9/9
  pass in 2.422s; CLI/adapters 16/16 pass in 10.655s; the four-kind surface
  zero-remote pilot passes in 289.367s. Python `py_compile`, Black, and
  `git diff --check` pass at this checkpoint.
- Final shared Harness shards, Hook/Stop regressions, product build/Vitest,
  package-content checks, secret/diff checks, independent review, Direct
  evidence binding, acceptance, and exact local commit are recorded below in
  the final convergence update.

### 2026-08-14 — Issue #35 independent-review repair checkpoint

- Review closure: v1 surface Search fails closed; four candidate-bound channel
  results are derived from bounded fetched responses; CLI/MCP use actual shared
  Harness operations; Loop decisions call the public step seam; Hook runtime
  points to the public event handler and smoke replays/reads/restores its actual
  deployment/config/canary/ledger state.
- Focused evidence: forged channel-result and response-digest regressions pass
  2/2 in 50.570s; the complete MCP/CLI/Hook/Loop disposable lifecycle across
  all three adapter mappings, including local acceptance commits, passes 1/1 in
  189.195s. Black, Ruff, `py_compile`, and strict diff checks pass after repair.
- Evidence boundary: no external Claude/Paseo process was launched under the
  frozen `codex-direct` mode; no candidate code, installer, daemon, port,
  credential, product source, tracked Hook registration, or remote state was
  used or changed.
- Final reviewer edge: package-manager evidence now separates capability ID from
  scoped npm name/version and handles an exact bound urllib HTTPError 404 as
  `no-match`; the scoped safe auto-Adapt regression passes in 36.959s. Other npm
  status classes remain fail-closed.

### 2026-08-14 — Issue #35 final current-diff verification

- Harness shards: Evolution 17/17 in 677.525s; Direct/Claude Direct 73 in
  448.405s (one platform-permission skip); Paseo 73/73 in 240.077s; typed
  memory/contracts/events/CLI core 67/67 in 94.093s. Hook safety 6/6 and Stop
  summary 8/8 pass.
- Product/package: exact-lock isolated dependencies install 466 packages with
  `@modelcontextprotocol/sdk@1.30.0`; build passes; Vitest passes 41 files/862
  tests in 7.54s; dry-run npm pack contains 185 files and zero Harness paths.
  Junction, temporary dependencies, and `dist` cleanup all verify absent.
- Static/boundary: Black, Ruff, `py_compile`, `git diff --check`, and strict
  UTF-8 over all 16 intended paths pass. Independent risk re-review closes all
  findings and reports no remaining live #35 blocker.

## 2026-08-14 — Harness v2 Issue #36 checkpoint

- Baseline/mode: clean independent worktree froze exact #35 HEAD
  `8de058e772e97a6ab8d16d65386081db76953320` on branch
  `codex/harness-v2-three-adapter-conformance-36`; `codex-direct` is frozen and
  a repeated start is rejected while its writer lease is active.
- TDD: missing three-adapter fixture, missing per-pilot/migration matrix,
  missing explicit event provenance/sensitivity/digest/terminal state, and an
  incorrect Paseo public-command label each failed before the shared fix.
- Focused current-diff checks: contract/events/Direct fixture 21/21 in 22.343s;
  writer/authority/recovery/exact-commit 7/7 in 33.230s; typed memory 3/3 in
  21.834s; three-adapter Evolution surface 1/1 in 170.520s;
  promotion/rejection/rollback 1/1 in 98.519s; evaluator/projection-drift
  rollback 1/1 in 41.808s.
- Real Direct pilots: Codex accepted commit `0cadc18c...`; Claude safe-mode
  implementation and acceptance produced `a81fef21...`. Each pilot is one
  commit above its seed, changes only `pilot.txt`, is clean after acceptance,
  has no remote, rejects a second start, emits one deduplicated missing-manual-
  Skill reminder with zero writes, and records attributed redacted active/stop
  events. Intentional Claude adapter failure entered `recovery-required` with
  `adapter_switch_policy=stop-and-report` and no changed paths.
- Paseo pilot: after explicit user authority, one `paseo start` launched 0.3.1.
  Provider initialization moved from `loading` to a green preflight for frozen
  `claude/deepseek-v4-flash`, with no restart or fallback. Agent
  `f4a4fec4-fb93-4a84-8c8c-556aeb08488c` received the digest-bound handoff,
  changed only `pilot.txt`, stopped idle, and returned a validated report.
  Codex review accepted commit `27fba0dce64fb591a30f0651979940089c667fb0`:
  exactly one commit above base, clean, released lease, and no remote.
- Inconclusive evidence: an initial parallel parent batch timed out at 304s and
  returned no child results, so it is not counted as green. Its required short
  shards were rerun independently; long Evolution cases were run separately.
- Independent risk review: the shared fixture now drives the public Paseo
  lifecycle, and pilot evidence is no longer a self-certified summary. Native
  controller/Recovery state passes production validation, Git objects and
  event digests are recomputed, package contents are compared with a live dry
  run, durable files are rehashed, and clean-room bytes are compared directly
  with exact #35 Git objects. The same reviewer closed both High findings;
  the three pilot artifacts now carry that production/Git/ledger evidence.
  Migration/index verification passes against the independent artifacts,
  current durable-file hashes, live package dry run, and exact clean-room Git
  objects.
- Product/package checkpoint: after worktree-local `npm ci --ignore-scripts`,
  build passed, Vitest passed 41 files / 862 tests in 6.82s, and `npm pack
  --dry-run --json --ignore-scripts` returned 185 files with zero forbidden
  Harness/runtime/Recovery/memory paths. A production-only audit was
  inconclusive on a registry TLS disconnect and was not retried or reported as
  green; the product and lockfile remain unchanged from accepted #35.
- Final risk-weighted Harness shard passed 26/26 in 75.307s across the shared
  contracts/events, Direct conformance/authority/exact-commit/Recovery, and
  Paseo shared lifecycle/duplicate-dispatch/Recovery cases. Valid earlier typed
  memory and governed-Evolution receipts were reused rather than rerunning the
  long cases without an implementation change.
- Final byte/scope gates: formatting-only churn in the two historical lifecycle
  test files was removed, leaving only the shared-matrix deltas. The two
  affected lifecycle tests and migration evidence test pass 3/3. Strict UTF-8
  covers 22 paths; focused Black, Python compilation, git diff --check, and the
  high-confidence secret-value scan pass. The dirty primary fingerprint remains
  exact: 68 status rows, SHA-256
  a4bbfb6dc821d203291ec664843d23f818db293aad8af1975f1190f33e5f8423,
  zero staged paths, and 44 untracked paths.
- Independent final risk review: PASS after correcting this durable-state
  wording. Both earlier High findings remain closed; no reproducible
  acceptance, security, or data-integrity defect remains.
- Acceptance contract recovery: the first main run failed closed before
  verifying because broad owned path `harness/` overlapped immutable
  governed-Evolution roots. It produced a typed Recovery Bundle with
  fingerprint
  `ea11fa7123898b0e3e8d5a231daa408abc55529fa2814126dd810349f046b940`.
  The same Codex writer used a reversible local stash to freeze a recovery
  continuation on the exact #35 base with the same mode/worktree and 23 exact
  Issue-owned paths, then restored all 23 changes. No kernel/evaluator/holdout
  edit, adapter switch, second implementation actor, commit, or remote effect
  occurred.

## 2026-08-14 — PR #39 automated-review repair pre-acceptance

- Baseline: branch `codex/harness-v2-three-adapter-conformance-36` was clean at
  pushed PR HEAD `2fd2b9b0141d536534c7e565aad9172bac72d9b5`; the task-local mode was newly
  frozen as `codex-direct` before implementation writes.
- TDD red evidence: canonical LF hashing produced four expected digest failures
  for the three pilot artifacts and migration artifact; WSL contract discovery
  produced three assertion failures and six errors because the Windows literal
  was not POSIX-absolute; zero-candidate Build was rejected as an invalid
  selection; and an empty candidate list paired with a `candidate` source result
  was initially accepted before the all-`no-match` guard was added.
- Focused green evidence: pilot migration digest test 1/1; Windows contract tests
  9/9; WSL contract tests 9/9; zero-candidate Search→Build→Evaluate→Accept 1/1
  in 58.951s; five candidate Search/Adapt/authorization/version-gate tests 5/5
  in 118.430s; and legacy Build reject/rollback/promote/accept 1/1 in 130.859s.
- A 27-test contract/CLI batch intentionally stopped at the old migration
  clean-room assertion after `harness/evolution.py` changed. It is not counted
  green; the migration model now separates exact #35 paths from the reviewed
  PR repair and normalizes durable-memory bytes before hashing.
- Governance recovery: the first exact-path contract omitted
  `harness/fixtures/pilot-artifacts/migration.json`. It entered a typed Recovery
  Bundle with five changed paths and no staged files; a reversible stash carried
  the identical diff into the same-mode, same-base recovery continuation with
  the migration artifact explicitly owned.

## 2026-08-14 — PR #39 automated-review round-2 pre-acceptance

- Baseline/mode: the isolated worktree was clean at pushed PR HEAD
  `58c23136d808e4be81a3c63ebffdcf36af8ee715`; `codex-direct` was frozen and
  acquired the only writer lease before the first test edit.
- Red evidence: empty-HOME Paseo preflight failed 1/1; clean-checkout migration
  package comparison failed 1/1; WSL CRLF preservation failed 1/1; canonical
  source identity and a 35-message MCP session failed 2/2.
- Focused green evidence: source/MCP plus five empty-HOME Paseo cases passed
  7/7 in 10.188s; WSL CRLF passed 1/1 in 1.743s; package migration acceptance
  with `dist/` moved aside passed 1/1 in 2.457s; MCP lifetime plus per-message
  bound passed 2/2 in 0.477s.
- Final risk-weighted verification: contracts, CLI/adapters, writer aliases,
  malformed sibling state, and Windows CRLF passed 34/34 in 34.121s. The
  Paseo function class passed 51/51 with empty HOME in 129.414s.
- Static boundary: `py_compile`, `git diff --check`, and focused Black for
  `harness/cli.py` pass. Installed Black 24.10.0 would reformat historical test
  style, so that churn was removed and no full-file Black result is claimed.
- Independent risk review: PASS with no reproducible P0-P3. Reviewer reruns
  passed source/MCP/CRLF 4/4, clean-checkout migration/package 1/1, empty-HOME
  Paseo 51/51 in 130.825s, `git diff --check`, and migration/repair/durable-
  memory digest recomputation.

## 2026-08-15 — PR #39 automated-review round-3 pre-acceptance

- Baseline/mode: the isolated worktree was clean at pushed PR HEAD
  `80e893b1d0e0a8078cb3c7a0dd8f91f2e11e9fb6`; the existing `codex-direct`
  mode was retained and the round-3 contract acquired the only writer lease.
  The dirty primary checkout remained isolated with 58 status rows.
- Red evidence: concurrent growth bypassed the stale JSONL size check; a
  synthetic second-file failure left the new store beside the old projection;
  and a synthetic process stop left no recoverable transaction marker. The
  focused loop failed 3/4 with the symlink case skipped only because Windows
  denied symlink creation.
- Focused green evidence: the same four tests pass on Windows with one symlink
  permission skip; the two JSONL race tests pass 2/2 under WSL/POSIX; and the
  complete events plus typed-memory modules pass 47 tests with the same single
  Windows symlink skip in 42.156s.
- Independent review reproduced two successive recovery defects: self-reported
  after digests admitted an unrelated shape-valid record, and a fully forged
  before/after marker remained self-consistent while duplicate candidates could
  break reverse replay. Automatic recovery no longer trusts marker-derived
  state: it requires the exact internally consistent prior pair committed at
  Git `HEAD`, restores it, and runs the same accepted envelope normally. The
  three focused transaction regressions pass 3/3; unanchored state fails closed
  for explicit recovery.
- Final risk-weighted matrix passed 49 tests in 47.689s with one Windows-only
  symlink-permission skip. Independent re-review then reproduced a short-append
  P2 because partial-tail discard and payload read each received a byte budget.
  The shared reader now performs one bounded descriptor read and revalidates
  descriptor/path identity and size afterward. The exact red regression now
  passes; the complete event module passes 12 tests in 1.155s with the same
  Windows skip, and both descriptor races pass 2/2 under WSL in 0.003s.
- Static boundary: Python compile, JSON parsing, strict UTF-8 decode,
  `git diff --check`, high-confidence secret scan, and debug-marker scan pass;
  the latter two report zero matches. Ruff is unavailable and was not installed.
- Independent final review: PASS with no reproducible P0-P3. Short and long
  append probes each read exactly 64 configured bytes and failed closed;
  post-read replacement/growth, forged-marker, duplicate-candidate, rollback,
  migration, durable-memory, repair-hash, and diff checks all passed. Full
  Harness and npm suites were intentionally not repeated because this bounded
  repair did not touch product or package code.

## 2026-08-15 — PR #39 automated-review round-4 pre-acceptance

- Baseline/mode: the isolated worktree was clean at pushed PR HEAD
  `1f638b5085568e1c87e46057df915f2ba53c348a`; `codex-direct` acquired the
  only writer lease. The dirty primary checkout remained isolated with 58
  status rows.
- Red evidence: a V2 zero-candidate Search with a forged channel digest entered
  `build-ready`; the POSIX Paseo process-boundary test returned preflight exit
  1 because no executable native launcher existed; and the forged-receipt test
  failed only on POSIX because checkout line endings changed its failure path.
- Focused green: the V1 and V2 zero-candidate paths plus forged-receipt
  rejection passed 3/3 on Windows in 89.680s. WSL passed the POSIX launcher,
  V2 zero-result verification, and forged-receipt rejection 3/3 in 13.364s.
- Risk-weighted final verification: six Evolution checks covering authentic
  and forged channel results, V1 and V2 zero-candidate Build, all three adapter
  projections, and receipt rejection passed 6/6 in 323.104s. Four POSIX Paseo
  process-boundary checks passed 4/4 in 3.224s.
- Independent review reproduced two P1 end-to-end gaps: allowed-host but
  unrelated no-match URLs could still reach an accepted zero-candidate Build,
  and WSL selected a later Windows `paseo.cmd` before the native disposable
  launcher. A red URL/query/path regression reproduced the first 1/1.
- The initial round-4 contract omitted the shared Paseo resolver. It entered a
  Recovery Bundle with fingerprint
  `cedc3edc5b54bf15ad3eb3b04133fc11186487dfe3ec255c52ebe5beb24b7f83`;
  a reversible local stash transferred the identical ten-file diff to the
  same-base, same-mode continuation with the resolver explicitly owned.
- Recovery green: the full forged-coordinate Search→Build→Evaluate→Accept
  regression passed 1/1 in 57.435s. WSL with its ordinary inherited PATH now
  resolves the native stub and passes 1/1 in 1.563s; candidate and zero-result
  channel checks passed 3/3 on Windows in 84.995s and 2/2 on WSL in 9.876s.
- Re-review found that a version-scoped npm 404 proved only a missing version,
  not a missing package. The isolated red regression reached `build-ready`;
  zero-candidate npm evidence now requires the exact unversioned query path.
  The end-to-end zero-result test plus both candidate channel tests pass 3/3 in
  97.449s, and ordinary-path WSL Paseo remains green 1/1 in 0.838s.
- Independent final re-review: PASS with no remaining P0-P3. It confirmed the
  exact unversioned npm path, unchanged candidate name/version binding, legal
  end-to-end acceptance, migration hashes, package exclusion, diff cleanliness,
  product isolation, and zero remote effects.
## 2026-08-18 — Issue #40 AI Subtitle Integrity Candidate

- Command: `npx vitest run tests/bilibili-transcript.test.ts tests/server-tools.test.ts tests/server-handler-sanitization.test.ts tests/server-error-next-steps.test.ts`
- Result: 4 files / 194 tests passed under independent Codex execution.
- Area: AI source classification, exclusion/force inputs, fallback stability,
  schema, handler validation, and error guidance.

- Command: `npm run build` and `npm test`
- Result: TypeScript build passed; 41 files / 885 tests passed.
- Area: full candidate regression matrix.

- Command: `npm pack --dry-run --json --ignore-scripts` and `git diff --check`
- Result: 185 package files; diff check clean; no new dependency or package
  boundary change.
- Area: package contents and repository hygiene.

- Command: post-review `npx vitest run tests/bilibili-transcript.test.ts`
- Result: 1 file / 76 tests passed after strengthening the explicit
  `preferred_lang: ai-zh` exclusion assertion; documentation contradiction was
  corrected in both languages.
- Caveat: the live Bilibili field case timed out before returning a transcript,
  so deterministic injected regressions are the acceptance authority. No local
  ready ASR model was installed or changed.

## 2026-08-18 Roadmap Subtitle Integrity + Scriptable Setup (vertical slices)

- Command: `npx vitest run tests/bilibili-transcript.test.ts` (slice 1 red to
  green)
- Result: red-capable — 2 integrity tests failed while language/topic checks
  were temporarily neutralized; green — 83/83 passed with the pure-function
  module and the transcript unconditional double-read.
- Area: `src/bilibili/subtitle-integrity.ts` + transcript integration.

- Command: `npx vitest run tests/bilibili-transcript.test.ts` (slice 2 red to
  green)
- Result: red — unstable `ai-zh` failed the `NoSubtitleError` expectation;
  green — 85/85 passed including the video-info uncached-description describe.
- Area: `getVideoInfoWithSubtitle` integrity block.

- Command: `npx vitest run tests/cli.test.ts` (slice 3 red to green)
- Result: red — 4 non-interactive tests failed before implementation (one
  earlier vitest OOM came from a non-terminating `askHiddenFn` mock, fixed by
  returning "n"); green — 69/69 passed.
- Area: `SetupCredentialsOptions` + Commander `--non-interactive` /
  `--asr-model`.

- Command: post-build child smoke (`node dist/cli.js setup --non-interactive`
  variants) with piped/closed stdin and synthetic environment credentials.
- Result: 4/4 cases passed; no prompt, no stdin/argv read, no synthetic
  credential value in stdout or stderr.
- Area: slice 4 non-TTY smoke.

- Command: `npm run build`
- Result: passed after all four slices.
- Area: TypeScript compilation.

## 2026-08-18 — v1.12.0 Publication And Public Artifact Verification

- Release commit: `a31fafb1f27ddb52cbca0abb0111dc4a73664da3` on
  `master`; annotated `v1.12.0` peels to the same commit.
- Local candidate: Node `22.14.0` / npm `11.18.0` build passed; 41 files / 906
  tests passed; 189-file package dry run passed; 97 production dependencies
  audited with zero vulnerabilities; scoped secret and Smithery checks passed.
- Independent release-verifier: PASS after correcting one stale Chinese README
  limitation sentence; no remaining candidate blocker.
- Trusted publication: GitHub Actions run `32107346010` completed successfully;
  npm `latest=1.12.0` exposes integrity, shasum, and SLSA provenance.
- Exact public artifact: isolated install verified 97 registry signatures and
  10 attestations; under Node `22.14.0`, CLI reported `1.12.0`, MCP initialize
  reported server `bilibili-mcp-server` `1.12.0` / protocol `2025-06-18`, and
  tools/list returned exactly ten tools.
- GitHub Release: bilingual `v1.12.0 - AI 字幕完整性 / AI Subtitle Integrity`
  is public, latest, non-draft, and non-prerelease at
  `https://github.com/XZXZZX-Ai/bilibili-mcp/releases/tag/v1.12.0`.
- Official Registry follow-up: after explicit user authorization, official
  `mcp-publisher` v1.8.1 archive SHA-256 matched upstream digest
  `399ad0d6e00a50812b563a71d8bfbff5160c085e6b13aac6ec083d98d5ff7c45`;
  live schema and `mcp-publisher validate` checks passed. The saved Registry
  JWT was expired; GitHub authentication refreshed it without recording token
  values. Publish succeeded, and the public API reports `1.12.0` active/latest
  with matching npm identifier and package version.
- Boundary: the dirty primary worktree and future CI/CD roadmap note stayed out
  of the immutable release tag; Registry publication did not move the tag,
  republish npm, or change the workflow.

## 2026-08-18 — PR #39 post-CI Codex review repair

- Red evidence: WSL reproduced zero parent-directory fsyncs after two
  descriptor-relative `mkdir` calls and after one descriptor-relative unlink;
  Windows and WSL both proved Paseo passed a symlinked/junction home path to the
  bounded reader instead of the resolved home.
- Green evidence: the three focused regressions pass on their applicable
  platforms. The complete affected events, Paseo preferences, and Paseo
  function matrix passes 85 tests on Windows with 13 platform skips and 85 on
  WSL with 2 platform skips.
- Boundary: only shared Harness persistence, Paseo preference discovery, tests,
  and durable receipts changed. Product runtime, dependencies, package output,
  credentials, daemon state, adapter selection, and release state are unchanged.
