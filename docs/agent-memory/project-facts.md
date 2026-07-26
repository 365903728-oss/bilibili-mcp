# Project Facts

## 2026-05-27

- Fact: This repository is `@xzxzzx/bilibili-mcp`, a TypeScript MCP server for extracting Bilibili video subtitles, metadata, and popular comments.
- Evidence: `AGENTS.md` project role section.
- Impact: Preserve MCP server compatibility and user-facing tool behavior during stabilization.

- Fact: Cookie-based Bilibili access must remain supported, but Cookie values must not be hard-coded.
- Evidence: User correction during stabilization planning and `docs/superpowers/plans/2026-05-27-stabilization-roadmap.md`.
- Impact: Replace literal credentials with `.env`, environment variables, or the credential helper instead of removing authenticated access.

- Fact: Smithery runtime config is no longer part of the active project workflow.
- Evidence: User instruction to delete Smithery config and roadmap Task 3.
- Impact: Do not recreate `smithery.json`, `smithery.yaml`, `dev: smithery dev`, `build:smithery`, or `@smithery/cli`.

- Fact: Claude Code skills live under `C:\Users\ZX\.claude\skills`, which is separate from `C:\Users\ZX\.agents\skills` and `C:\Users\ZX\.codex\skills`.
- Evidence: Local directory inspection on 2026-05-27.
- Impact: When preparing Claude Code skills, install or sync them into `.claude\skills`.

## 2026-05-28

- Fact: Project-local hooks are enabled for both Claude Code and Codex app.
- Evidence: `.claude/settings.local.json`, `.codex/hooks.json`, and `docs/superpowers/specs/2026-05-28-agent-hooks-design.md`.
- Impact: Startup context, failed shell observations, and stop summaries can be generated automatically, but formal memory updates remain review-gated.

- Fact: Codex app runtime hook observations for this repository are stored outside the project `.codex\` directory at `C:\Users\ZX\.codex\memories\bilibili-mcp\`.
- Evidence: Dry run failed with a Windows access denial when writing `.codex\memory`; the script was updated to use the writable Codex memory root.
- Impact: Do not assume project `.codex\` is suitable for mutable runtime logs.

- Fact: ECC-inspired hook upgrades are configured as lightweight project-local scripts, not as a full ECC installation.
- Evidence: `.codex/scripts/pre_compact.py`, `.codex/scripts/context_budget.py`, `.codex/scripts/post_tool_use.py`, and `.codex/scripts/stop_summary.py`.
- Impact: The project gets PreCompact checkpoints, candidate scoring, context budget reports, and strategic compact reminders without broad global rules or automatic skill evolution.

- Fact: Controlled learning proposals are generated automatically but require user approval before promotion.
- Evidence: `.codex/scripts/generate_learning_proposals.py` writes `docs/agent-memory/pending-learning-proposals.md`.
- Impact: Pending proposals should be reviewed by Codex and promoted only after the user approves with `批准本轮 learning proposals`.

## 2026-06-04

- Fact: Phase 2 and Phase 3 work produced formal verification memory, while hook learning remained review-gated.
- Evidence: `docs/agent-memory/verification-log.md` contains Phase 2 final verification, Phase 3 Task 1-8 verification, and active-plan tracking verification; `docs/agent-memory/pending-learning-proposals.md` currently reports no proposals above the promotion threshold.
- Impact: Treat Phase 2/3 memory capture as successful, but do not assume absence of learning proposals means hooks failed.

- Fact: The automatic active-plan tracker only tracks the stabilization roadmap and `*-implementation-plan.md` implementation plans.
- Evidence: `.codex/scripts/plan_tracker.py` filters candidate plans and previous active plans through the same tracked-plan rule; `python .codex/scripts/plan_tracker.py` returns the Phase 4 implementation plan instead of the older unchecked `2026-05-27-agent-memory-learning-system.md`.
- Impact: Phase-gated learning reminders no longer drift to non-implementation design/history plans, while future phase plans can be tracked automatically if they use the `*-implementation-plan.md` naming pattern.

- Fact: Phase 4 completed source-level documentation and release workflow polish but did not perform an actual release.
- Evidence: Phase 4 final verification records no tag, no GitHub release, and no npm publish; commit `f777980` was pushed to `origin/master` as source changes only.
- Impact: Treat the next step as release execution, not another documentation-polish phase.

## 2026-06-05

- Fact: Agent-facing credential guidance is now part of the MCP tool surface.
- Evidence: `src/server.ts` registers `get_credential_setup_instructions` and `check_bilibili_credentials`; `src/utils/credential-guidance.ts` centralizes setup instructions, status reporting, and credential next steps.
- Impact: Agents installing this MCP server can discover credential setup instructions through MCP tools instead of relying only on README text.

- Fact: Credential guidance responses must not expose Cookie values.
- Evidence: `check_bilibili_credentials` reports only `configured`, `source`, `logged_in`, `next_steps`, and security notes; tests assert setup/status responses do not contain secret-like Cookie assignments.
- Impact: Future credential UX changes should keep secrets out of MCP responses, logs, tests, README examples, and client configuration snippets.

- Fact: Python `__pycache__` files under project hook scripts are runtime cache artifacts, not project memory.
- Evidence: `.codex/scripts/__pycache__/plan_tracker.cpython-311.pyc` was generated by script execution and is ignored through `.gitignore`.
- Impact: Keep formal memory in `docs/agent-memory/`, Codex runtime observations under `C:\Users\ZX\.codex\memories\bilibili-mcp\`, and Claude runtime observations under `.claude\memory\` / `.claude\runtime\`; do not commit Python bytecode caches.

## 2026-06-14

- Fact: Codex and Claude Code learning proposal runtime state is synchronized to the completed credential guidance implementation plan.
- Evidence: `python .codex/scripts/plan_tracker.py` returns `docs\superpowers\plans\2026-06-05-credential-guidance-mcp-tools-implementation-plan.md`; both Codex and Claude `learning-proposal-phase-state.json` files point to that plan with `completed_phase_count` 8.
- Impact: Phase-gated learning reminders no longer treat the old `v1.4.0` release execution plan as active work; `pending-learning-proposals.md` reporting `No Proposals` remains a normal controlled-learning state.

## 2026-06-18

- Fact: `domain-modeling` and `codebase-design` are installed for both Codex and Claude Code.
- Evidence: Codex copies live under `C:\Users\ZX\.codex\skills\domain-modeling` and `C:\Users\ZX\.codex\skills\codebase-design`; Claude Code copies live under `C:\Users\ZX\.claude\skills\domain-modeling` and `C:\Users\ZX\.claude\skills\codebase-design`.
- Impact: Handoffs may name these skills for appropriate domain-language or module-design work, but ordinary bug fixes, package maintenance, releases, and narrow edits should not invoke them by default.

- Fact: `product-requirements` and `system-design` are available to Claude Code and documented in the project workflow.
- Evidence: Claude Code skill copies exist under `C:\Users\ZX\.claude\skills\product-requirements` and `C:\Users\ZX\.claude\skills\system-design`; `AGENTS.md` and `CLAUDE.md` define narrow fixed triggers for them.
- Impact: Use `product-requirements` for unclear or new user-facing feature scope, and `system-design` for broad cross-module architecture decisions; skip both for already-scoped bug fixes, releases, package maintenance, and local refactors.

## 2026-07-19

- Fact: The current upstream Matt Pocock engineering and productivity skill names are present in both Codex and Claude Code skill roots.
- Evidence: Live GitHub API directory listing for `mattpocock/skills` was compared with `C:\Users\ZX\.codex\skills` and `C:\Users\ZX\.claude\skills`; no current name was missing.
- Impact: Repository integration requires routing and configuration, not another global installation.

- Fact: The Matt workflow is configured for GitHub Issues, the default five triage labels, and a single-context domain-doc layout.
- Evidence: User decisions on 2026-07-19, `docs/agents/issue-tracker.md`, `triage-labels.md`, and `domain.md`; live `gh label list` verification found all five labels after the four missing labels were created.
- Impact: Matt skills can use a consistent tracker and vocabulary; absent `CONTEXT.md` and ADRs are created lazily when needed.

- Fact: Superpowers skills are disabled for this repository by explicit user decision.
- Evidence: `AGENTS.md`, `CLAUDE.md`, and `docs/agent-memory/active-work.md`; runtime scripts resolve active work without reading `docs/superpowers/`.
- Impact: Historical files under `docs/superpowers/` remain for audit only and cannot be used as current instructions or skill triggers.

- Fact: Paseo CLI is the execution bridge from Codex handoffs to Claude Code.
- Evidence: `paseo` resolves to `C:\Users\ZX\.local\bin\paseo.cmd`; `C:\Users\ZX\.paseo\orchestration-preferences.json` maps `providers.impl` to a Claude provider; `AGENTS.md` and `docs/agent-memory/agent-communication.md` define the bounded launch contract.
- Impact: Codex launches, monitors, and reviews Claude Code work; the user no longer transfers handoffs or operates Claude Code manually.

- Fact: Concurrent `throttledFetch` calls now reserve FIFO admission turns and start at the configured rate-limit interval while response bodies may overlap.
- Evidence: `src/bilibili/http.ts`, `tests/bilibili-http.test.ts`, and Codex verification recorded in `docs/agent-memory/verification-log.md`.
- Impact: Shared WBI and non-WBI request callers no longer batch concurrent starts after waiting on the same stale promise.

- Fact: Both transcript and video-info subtitle flows use one private empty-list credential verification helper.
- Evidence: `verifyLoginForEmptySubtitles` in `src/bilibili/subtitle.ts`, the regression in `tests/bilibili-transcript.test.ts`, and GitHub Issue #3.
- Impact: A logged-out empty subtitle list now produces `COOKIE_EXPIRED` before transcript description fallback, while logged-in fallback and `NoSubtitleError` behavior remain unchanged.

- Fact: `getVideoInfoWithSubtitle` does not cache description fallbacks created by transient/general subtitle retrieval errors.
- Evidence: GitHub Issue #4, the retry regression in `tests/bilibili-transcript.test.ts`, and the error-fallback branch in `src/bilibili/subtitle.ts`.
- Impact: A later call can retry subtitle retrieval after a temporary failure, while successful subtitle results remain cached and `COOKIE_EXPIRED` still propagates.

- Fact: Explicit-limit comment cache entries include `detailLevel` as well as limit, sort, and reply inclusion.
- Evidence: GitHub Issue #5, `src/bilibili/comments.ts`, and the brief-versus-detailed collision regression in `tests/bilibili-comments-tool.test.ts`.
- Impact: Brief and detailed comment requests no longer reuse incompatible processed results when their explicit limits match.

- Fact: `npm test` is the repository's real Vitest verification gate, not a stub.
- Evidence: `package.json` maps `test` to `vitest run`; Issue #6 corrected current rules in `AGENTS.md`, `CLAUDE.md`, and four callable agent definitions; Codex verified 17 files and 160 tests.
- Impact: Codex, Claude Code, build/package agents, and release verifiers now require and report the actual test result.

- Fact: The MCP stdio startup smoke test waits for the actual stderr ready signal with bounded failure and child-process cleanup.
- Evidence: GitHub Issue #7 and `tests/mcp-server-smoke.test.ts`; Codex's original loop failed at iteration 6, the latency probe measured up to 453ms, and the final event-driven test passed 20/20 stress iterations.
- Impact: Full-suite verification no longer depends on a fixed 300ms startup guess while stdout cleanliness and startup logging remain covered.

- Fact: Comment metadata lookup is owned only by `comments-api.ts`, where `aid || cid` is required for the upstream oid.
- Evidence: GitHub Issue #8, `src/bilibili/comments.ts`, `src/bilibili/comments-api.ts`, and the focused no-outer-metadata-call regression.
- Impact: Each uncached processed-comment request avoids one redundant Bilibili video-info request without changing comment API arguments, caching, or response shaping.

- Fact: The documented comment `limit` range of 1-50 is implemented through bounded sequential pagination above the upstream per-page maximum of 20.
- Evidence: GitHub Issue #9, `src/bilibili/comments.ts`, and the pagination regressions in `tests/bilibili-comments-tool.test.ts`.
- Impact: Requests above 20 fetch pages of at most 20 until the requested top-level count or upstream exhaustion, while detailed-mode child reply expansion and public response shape remain unchanged.

- Fact: Bilibili login-status checks distinguish a successful logged-out response from HTTP, timeout, and connection failures.
- Evidence: GitHub Issue #10, `checkLoginStatus` and `throttledFetch` in `src/bilibili/http.ts`, HTTP regressions, and the MCP-level `NETWORK_ERROR` regression.
- Impact: Credential checks no longer misreport an unavailable nav endpoint as invalid credentials; network failures use the existing structured retryable error path without exposing Cookie values.

- Fact: Explicit HTTP status codes are authoritative in the shared retry policy.
- Evidence: GitHub Issue #11, `src/utils/retry.ts`, and the 403/503/status-less matrix in `tests/retry.test.ts`.
- Impact: Allowed transient statuses still retry, explicit non-retryable statuses fail immediately, and connection errors without an HTTP status retain type/code-based retries.

- Fact: Subtitle-content HTTP failures preserve the upstream response status on `NetworkError`.
- Evidence: GitHub Issue #12, `src/bilibili/video-api.ts`, and the focused 403 regression in `tests/bilibili-video-api.test.ts`.
- Impact: Non-retryable subtitle statuses fail after one request, while the shared transient-status and status-less transport retry rules remain effective.

- Fact: WBI nav HTTP failures preserve their response status before retry classification and through the final wrapped error.
- Evidence: GitHub Issue #13, `src/bilibili/wbi.ts`, and the focused 403 regression in `tests/bilibili-wbi.test.ts`.
- Impact: Non-retryable WBI statuses fail after one fetch and remain diagnosable, while existing transient and transport retries are unchanged.

- Fact: Native WBI fetch `TypeError` failures are normalized before shared retry classification, and each attempt clears its request timeout.
- Evidence: GitHub Issue #14, the local fetch-boundary `try/catch/finally` in `src/bilibili/wbi.ts`, and the focused transport regression in `tests/bilibili-wbi.test.ts`.
- Impact: Connection failures receive the configured four attempts without leaking per-attempt timeout timers or inventing an HTTP status.

- Fact: Optional buvid fingerprint requests clear their timeout on both success and failure.
- Evidence: GitHub Issue #15, the `finally` cleanup in `src/bilibili/fingerprint.ts`, and `tests/bilibili-fingerprint.test.ts`.
- Impact: A rejected fingerprint fetch still performs one attempt and resolves `null` without leaving its request timer pending.

- Fact: Version `1.7.1` combines the README synchronization with the legacy auth/config/cache/build cleanup and is published to npm with provenance.
- Evidence: annotated tag `v1.7.1`, Actions run `29723831279`, npm attestation metadata, and the non-draft GitHub Release.
- Impact: npm latest and the current GitHub Release are `1.7.1`; later release work should start from this baseline.

- Fact: Both READMEs now document `BILIBILI_CACHE_SIZE`, `USER_AGENT`, and the restart requirement for runtime tuning environment variables.
- Evidence: `README.md` and `README_EN.md` API rate limiting sections, `src/config.ts` environment variable loading.
- Impact: Users can discover all four runtime-tuning variables and the restart constraint from the README without reading source code.

## 2026-07-20

- Fact: Version `1.7.2` publishes transcript keyword search through the existing tag-triggered npm trusted-publishing workflow.
- Evidence: Commit `b05001b`, annotated tag `v1.7.2`, Actions run `29728674803`, npm latest/provenance metadata, exact-version CLI smoke, and the non-draft GitHub Release.
- Impact: Users can locate literal subtitle keywords with bounded timestamped context through `get_video_transcript`; the public tool count remains eight.

- Fact: `get_video_transcript` supports optional keyword search (`query`, `max_matches`, `context_segments`), returning case-insensitive literal `Transcript Match` results with bounded timestamped context. Eight MCP tools preserved; zero extra Bilibili requests.
- Evidence: `src/bilibili/subtitle.ts` searchTranscript helper, `src/bilibili/types.ts` TranscriptMatch/TranscriptSearchOptions types, `src/utils/validation.ts` query/max_matches/context_segments validators, 286-test suite, and the PRD at `docs/transcript-keyword-search-prd.md`.
- Impact: Search mode requires real subtitles and rejects description fallback; no-query behavior, request counts, and public tool list are unchanged.

- Fact: Source version `1.7.0` exposes eight MCP tools, adding navigable transcripts, multi-Part selection, and Bilibili-provided Chapters.
- Evidence: `src/server/tool-schemas.ts`, `src/bilibili/navigation.ts`, `src/bilibili/chapters.ts`, the 243-test Vitest suite, real stdio `tools/list`, and live read-only Part/Chapter checks.
- Impact: Metadata callers can discover normalized Parts; transcript and video-info callers can select a one-based Part; transcript callers can request one-sided or bounded time ranges and timestamped lines; Chapter callers receive only bounded platform-provided intervals.

- Fact: Version `1.7.0` is the current npm latest and GitHub Release.
- Evidence: annotated tag `v1.7.0`, successful GitHub Actions run `29704348924`, npm registry metadata and SLSA provenance, the published CLI help smoke, and the non-draft GitHub Release.
- Impact: Install/update guidance may now target `@xzxzzx/bilibili-mcp@1.7.0` or `@latest`.

- Fact: MCP server initialization metadata reads its version from the root `package.json` instead of maintaining a separate hard-coded value.
- Evidence: `src/server.ts`, the version regression in `tests/mcp-server-smoke.test.ts`, and Codex verification against compiled `dist/server.js`.
- Impact: Future package version updates automatically remain aligned with the version reported to MCP clients.

- Fact: v1.6.4 is the current published npm and GitHub release.
- Evidence: npm registry metadata and SLSA attestation for `@xzxzzx/bilibili-mcp@1.6.4`, successful GitHub Actions run `29695975757`, and GitHub Release `v1.6.4`.
- Impact: Issues #2 through #15 are released and closed; future work starts from npm/latest 1.6.4 and `master` after commit `3fd6f6f`.

- Fact: The npm publish workflow pins npm 11.18.0 while using Node 22.14.0.
- Evidence: The initial v1.6.4 tag run failed when `npm@latest` selected npm 12.0.1, whose engine requires a newer Node version; npm 11.18.0 supports Node 22.14.0 and completed trusted publishing successfully.
- Impact: Do not restore an unbounded `npm@latest` install without also updating and verifying the workflow Node version; keep the trusted-publishing minimum and engine compatibility explicit.

- Fact: Runtime cache capacity is owned by `src/config.ts`, and `BILIBILI_CACHE_SIZE` controls both video and comment QuickLRU instances.
- Evidence: `src/utils/cache.ts` uses `config.maxCacheSize`; the env-driven regression in `tests/cache.test.ts` verifies eviction with a small configured capacity.
- Impact: Do not duplicate cache capacity in package metadata or hard-code a second value in the cache wrapper.

- Fact: The normal package build removes the guarded repository `dist` directory before TypeScript compilation.
- Evidence: `package.json` uses a Node stdlib clean step before `tsc`; a sentinel and the deleted module's stale compiled files were absent after the build and from the 124-entry package dry run.
- Impact: Deleted source modules no longer survive as publishable stale artifacts, without adding a cleanup dependency.

## 2026-07-25

- Fact: The current source implementation declares the existing `VideoTranscriptData` shape as `get_video_transcript.outputSchema` and returns the same successful result as both formatted JSON text and MCP `structuredContent`.
- Evidence: `src/server/tool-schemas.ts`, `src/server/tool-handlers.ts`, the exact schema/text/error regressions in `tests/server-tools.test.ts` and `tests/server-handler-sanitization.test.ts`, and GitHub Issue #16.
- Impact: Structured-output clients can consume transcript evidence directly while text-oriented clients keep the existing JSON representation; the other seven tools and all error results remain text-only. Credentialed SDK 1.27.1 and Codex CLI 0.144.6 acceptance passed against `BV1vL411G7N7`; the accepted implementation is commit `29f663a` on `master`, while npm publication remains unchanged.

## 2026-07-26

- Fact: The source implementation adds a Part-aware `source_url` to every successful `get_video_transcript` result and a `timestamp_url` to every returned `Transcript Match`.
- Evidence: Commit `7a6f79d`, `src/bilibili/subtitle.ts`, `src/bilibili/types.ts`, `src/server/tool-schemas.ts`, 299 passing tests, official SDK 1.27.1 credentialed calls, live Playwright checks, and `docs/qa/2026-07-26-transcript-evidence-links.md`.
- Impact: Agents can open the exact Bilibili Video or Part and cited subtitle moment without reconstructing browser URLs. BVID casing is preserved, the other seven tools and all errors remain unchanged; Issue #17 is closed while npm publication remains at `1.7.2`.
