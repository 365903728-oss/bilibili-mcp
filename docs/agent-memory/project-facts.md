# Project Facts

## 2026-08-20

- Fact: `v1.13.0` is the current published product baseline on npm, GitHub Releases, and the Official MCP Registry, with twelve MCP tools.
- Evidence: release commit `da6c5f7b5747d8afb6bffae9b063b667d60ebd3a`, annotated tag `v1.13.0`, trusted-publish run `32347312191`, npm `latest`, the public bilingual GitHub Release, and the Official Registry API exact/latest responses.
- Impact: Creator Search plus bounded Creator Videos, Collections, Series, and Dynamics discovery are public package behavior; Official Registry `1.13.0` is `active` and `isLatest=true` with matching `@xzxzzx/bilibili-mcp@1.13.0` metadata.

- Fact: Issue #48 extends the existing Creator Content Discovery tool with one authenticated, bounded `dynamics` page at a time. The output preserves stable Dynamic identity, publication time, bounded text, image URL/dimensions, referenced BVID relationships, repost originals, skipped rows, and live non-snapshot continuation.
- Evidence: `src/bilibili/creator-content.ts`, public MCP schema, focused tests, and `docs/research/2026-08-20-bilibili-creator-dynamics-contract.md`.
- Impact: Agents can inspect Creator Dynamics without the MCP downloading or interpreting images, extracting dedicated article/Opus bodies, or automatically fetching referenced Video evidence.

- Fact: The current first-party space UI uses a flattened Opus feed, while the detailed Dynamic endpoint needed for full repost/image/BVID evidence returned API code `-352` to anonymous probes on 2026-08-20.
- Evidence: `docs/research/2026-08-20-bilibili-creator-dynamics-contract.md`.
- Impact: The implementation keeps the detailed endpoint behind the existing credential/login gate; authenticated live behavior remains a named verification gap rather than an empty-success fallback.

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

- Fact: The bilingual client setup guides document all five optional runtime variables, including `BILIBILI_CACHE_SIZE`, `USER_AGENT`, `BILIBILI_MCP_DEBUG`, and the restart requirement.
- Evidence: `docs/client-setup.md`, `docs/client-setup.en.md`, and `src/config.ts` environment variable loading.
- Impact: Users can discover request tuning and credential-redacted debug controls, plus the restart constraint, from the canonical installation guide without reading source code.

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

- Fact: `origin/master` contains the v1.8.0 source preparation and compatible dependency refresh without a runtime-source, test, direct-dependency, package-entry, Node-support, or publish-workflow change.
- Evidence: Commits `8cad77c` and `2c87750`, the 299-test suite, Node 18 and current-Node official SDK stdio acceptance, build, 124-file package dry run, and `docs/qa/2026-07-26-v1.8.0-release-prep.md`.
- Impact: Git delivery is complete. npm and the current GitHub Release remain `1.7.2` until publication receives separate authorization.

- Fact: The v1.8.0 lockfile resolves `body-parser` 2.3.0 and `fast-uri` 3.1.4, clearing three production advisories; one underlying moderate Hono advisory remains.
- Evidence: `npm ls`, `npm explain`, `npm audit --omit=dev --json`, upstream SDK Issues #2531/#2548, and the advisory research note.
- Impact: Preserve Node 18 instead of forcing Hono 2. The residual `serveStatic` path is absent from the SDK and this stdio-only server; re-evaluate when upstream widens its dependency range or if an HTTP/static-file surface is introduced.

- Fact: The root package declares Node `>=18.0.0`, while installed `@hono/node-server` 1.19.14 declares Node `>=18.14.1`; the verified shipped-runtime smoke used Node 18.20.8.
- Evidence: The two package manifests, the Node 18.20.8 official SDK stdio acceptance, independent Issue #19 risk review, and GitHub Issue #20.
- Impact: Do not claim the untested Node 18.0.0–18.14.0 range is verified. Resolve the public engine floor in its own bounded compatibility ticket rather than changing Issue #18/#19 scope.

- Fact: v1.8.0 was the published baseline immediately before authenticated Video Discovery.
- Evidence: Annotated tag `v1.8.0` at `4be845f`, successful Actions run `30193180970`, npm latest/provenance metadata for `@xzxzzx/bilibili-mcp@1.8.0`, exact-version CLI smoke, and the non-draft/non-prerelease GitHub Release.
- Impact: Retain this as historical release evidence; current install guidance uses the newer release recorded below.

- Fact: The Issue #21 working tree adds `search_bilibili_videos` as the ninth MCP tool, providing authenticated, bounded, normal-Video discovery with exact structured/text output.
- Evidence: `src/bilibili/search.ts`, tool schema/handler changes, 327 passing tests, the 128-file package dry run, official SDK 1.27.1 nine-tool discovery, and the real `BV1Eb411u7Fw` search-to-Part-4 timestamp workflow recorded in `docs/qa/2026-07-26-bilibili-video-search.md`.
- Impact: An Agent can start from a topic and pass a returned BVID into existing evidence tools without pagination, AI re-ranking, or automatic subtitle/comment requests. This behavior is published in `v1.9.0`; Issue #21 is closed.

- Fact: v1.9.0 was the published baseline immediately before the documentation-only v1.9.1 refresh.
- Evidence: Commit `b77c3fc`, annotated tag `v1.9.0`, successful Actions run `30195477401`, npm integrity/shasum and SLSA provenance metadata, isolated exact-package CLI version/help smoke, and the non-draft/non-prerelease GitHub Release.
- Impact: Retain this as historical release evidence; current install guidance uses the newer release recorded below. Issue #20 remains a separate compatibility follow-up.

- Fact: Source version `1.9.1` is a documentation-only preparation that centralizes installation/configuration in bilingual guides and ships two GitHub-safe SVG heroes.
- Evidence: Bilingual README/setup/tool-reference documents, package version consistency, 327 passing tests, build, 134-file package dry run, README/SVG audits, and credential-pattern scanning.
- Impact: MCP tools and runtime behavior are unchanged. A source push alone does not change npm latest or create a GitHub Release; publication still requires the separate tag-driven workflow.

- Fact: v1.9.1 is the current npm latest and GitHub Release.
- Evidence: Annotated tag `v1.9.1` at `5cdd47b`, successful Actions run `30205162304`, npm integrity/shasum and SLSA provenance metadata, isolated exact-package CLI version/help smoke, and the non-draft/non-prerelease GitHub Release.
- Impact: Install/update guidance may target `@xzxzzx/bilibili-mcp@1.9.1` or `@latest`; all nine MCP tools and runtime behavior remain unchanged.

## 2026-07-27

- Fact: The Issue #22 working tree adds `list_bilibili_favorite_videos` as the tenth MCP tool for the currently authenticated account's created Favorite Folders.
- Evidence: `src/bilibili/favorites.ts`, tool schema/handler registration, 25 files / 405 passing tests, official SDK ten-tool discovery, and redacted real first/continuation calls recorded in `docs/qa/2026-07-27-bilibili-favorites-discovery.md`.
- Impact: An Agent can begin without a Folder ID and traverse every currently visible created Folder one upstream page at a time. Each call uses at most nav + created/list-all + one fixed 20-row resource request and returns identical JSON text/`structuredContent`.

- Fact: Favorites continuation uses an opaque, stateless, versioned base64url cursor containing only Folder ID and page; it is strictly and canonically decoded before credentials or network access.
- Evidence: `encodeFavoritesCursor`/`decodeFavoritesCursor`, the zero-network malformed/non-canonical cursor regressions, stale-cursor regressions, and MCP `VALIDATION_ERROR` smoke coverage.
- Impact: No Cookie, account ID, Folder title, or Video data is stored in the cursor. Traversal remains best-effort against live Bilibili state rather than snapshot-isolated.

- Fact: `v1.10.0` was the published baseline immediately before the documentation-only `v1.10.1` refresh, publishing authenticated all-Favorites Video discovery as the tenth MCP tool.
- Evidence: Release commit `7ff2257`, annotated tag `v1.10.0`, successful Actions run `30230653151`, npm integrity/shasum and SLSA provenance metadata, isolated exact-package CLI version/help smoke, the non-draft/non-prerelease GitHub Release, and closed Issue #22.
- Impact: Retain this as the runtime-feature release baseline; current install guidance uses the newer documentation patch recorded below.

- Fact: `v1.10.1` is the current npm latest and GitHub Release, publishing the Favorites-first bilingual README and four-step cursor-traversal Hero SVGs without runtime, schema, test, dependency, or workflow changes.
- Evidence: Release commit `3aee13d`, annotated tag `v1.10.1`, successful Actions run `30233179604`, npm integrity/shasum and SLSA provenance metadata, isolated exact-package CLI version/help smoke, and the public non-draft/non-prerelease GitHub Release.
- Impact: Install/update guidance may target `@xzxzzx/bilibili-mcp@1.10.1` or `@latest`. The package still exposes the same ten MCP tools; Issue #20 remains a separate compatibility follow-up.

- Fact: The verified post-v1.10.1 working tree replaces the duplicated CLI dispatch with one Commander interface and adds interactive `setup` plus local-only `doctor --json`.
- Evidence: `src/cli.ts`, 19 focused CLI unit tests, 11 built-entrypoint/MCP smoke cases, 431 passing tests, and `docs/qa/2026-07-27-cli-setup-doctor.md`.
- Impact: People can use hidden-input `setup`; Agents can inspect a stable secret-free local status object and distinguish locally ready, missing credentials, and internal failures through exit codes 0, 1, and 2. Live Bilibili login still requires `check_bilibili_credentials`. This working tree is not committed, versioned, or published yet.

- Fact: The post-v1.10.1 working tree fully redesigns both landing pages around a plain two-sentence outcome introduction, three product outcomes (browse current visible Favorites, search by topic, and explore a selected Video), a visible Node prerequisite and four-step install/login path before examples, three prominent real use cases, ten task-oriented MCP tools, explicit product limits, and local credential safety.
- Evidence: `README.md`, `README_EN.md`, four SVGs under `assets/readme/`, the paired setup guides, and `docs/agent-memory/handoffs/2026-07-27-readme-install-flow-claude-report.md`.
- Impact: The homepage now moves from product capability to a scannable installation path and then concrete use, with the Favorites visual scoped to its matching example rather than the whole project identity. It serves Agent-assisted and manual users without claiming AI summarization, ASR, audio download, automatic notes, guaranteed normalization of every upstream row, snapshot traversal, stable newest-comment ordering, or access bypass. Detailed client configuration and tool schemas remain in their canonical guides.

- Fact: npm latest remains `1.10.1` and does not contain the working-tree `setup` or `doctor` commands; Commander 14.0.3 requires Node `>=20` while the root package still declares Node `>=18.0.0`.
- Evidence: Live `npm view @xzxzzx/bilibili-mcp version`, live `npm view commander@14.0.3 engines`, `package.json`, and the built local CLI probes on 2026-07-27.
- Impact: The CLI implementation and rewritten documentation must ship together in a later version. Resolve the package engine floor before that release; do not publish the README alone or claim current `@latest` already supports the new onboarding commands.

- Fact: The post-v1.10.1 onboarding documentation now provides two independently complete first-run paths.
- Evidence: The copyable Agent prompt in both READMEs, the manual-install sections, the browser credential-field instructions in both setup guides, and the passing Agent/manual persona walkthroughs.
- Impact: An Agent can configure the correct MCP client while leaving private credential entry to the user, and a person can complete Node verification, client configuration, hidden local credential entry, reconnection, and live MCP login validation without inventing an omitted step.

- Fact: Phase 1 of the verified post-v1.10.1 working tree added optional ASR installation to `setup` with No as the default and one fixed `Systran/faster-whisper-small` model revision.
- Evidence: `src/asr/`, `src/cli.ts`, 95 focused tests, 27 files / 496 full tests, a clean TypeScript build, a 148-file package dry run, built help/doctor probes, and `docs/qa/2026-07-27-asr-model-install-phase1.md`.
- Impact: Choosing Yes creates a user-scoped managed Python environment, installs pinned `faster-whisper==1.2.1`, downloads the approximately 486 MB model snapshot, verifies CPU INT8 loading, and records readiness. Choosing No performs no ASR command, network, or filesystem work. At Phase 1 acceptance, model selection was still absent; the Phase 2 fact below supersedes that limitation. Audio retrieval, transcription, and subtitle fallback remain unimplemented.

- Fact: Phase 2 adds a three-model allowlisted selector (tiny 78 MB / base 148 MB / small 486 MB, Enter defaults to small) to the ASR setup flow. `AsrModelKey` and `AsrModelSpec` are derived from a literal `as const` allowlist.
- Evidence: `src/asr/state.ts` (allowlist, `resolveModelSpec`, `isAllowlistedModel`, `modelKeyForRepo`, derived `modelKey` in `readAsrState`), `src/asr/installer.ts` (model-key-aware idempotency and switch behavior), `src/cli.ts` (`parseModelChoice`, model selector UI, `asr.model` in doctor), 158 focused tests / 570 full tests, clean build, 148-file pack dry-run, built doctor JSON with `asr.model`, and `docs/qa/2026-07-27-asr-model-selector-phase2.md`.
- Impact: One active model in the existing shared directory; same-model idempotent, different-model switches and re-verifies. Audio retrieval, transcription, and subtitle fallback remain Phase 3.

- Fact: Node `>=20.0.0` is now the working-tree package engine floor, and the Phase 1 doctor reports ASR as `not_installed`, `incomplete`, or `ready` without changing credential readiness or its exit code.
- Evidence: `package.json`, `package-lock.json`, `src/asr/state.ts`, `src/cli.ts`, and focused CLI tests.
- Impact: The earlier Node engine mismatch is resolved in source, but npm latest remains `1.10.1`; none of these working-tree changes are committed, versioned, or published.

## 2026-07-29

- Fact: This worktree remains a legacy-era stdio MCP server after the stable `2026-07-28` protocol release: it uses the monolithic TypeScript SDK v1 line, a singleton low-level `Server`, and direct `StdioServerTransport` connections.
- Evidence: `package.json`, `package-lock.json`, `src/server.ts`, `src/index.ts`, `src/cli.ts`, the official dated specification and TypeScript SDK migration guidance summarized in `docs/research/2026-07-29-mcp-protocol-update.md`, and live npm registry checks showing `@modelcontextprotocol/sdk` latest `1.30.0` versus split-package v2 `2.0.0`.
- Impact: Existing dual-era clients may continue through legacy fallback. Claiming `2026-07-28` support requires a separate SDK v2 migration and explicit `serveStdio(factory)` entry with both modern `server/discover` and legacy `initialize` verification; do not infer modern conformance from a package upgrade alone.

- Fact: The current ten-tool surface implements the original MCP discovery/call/error model and the `2025-06-18` structured-output addition for three tools (`get_video_transcript`, `search_bilibili_videos`, and `list_bilibili_favorite_videos`), while keeping a deterministic static tool order.
- Evidence: `src/server.ts`, `src/server/tool-schemas.ts`, `src/server/tool-handlers.ts`, `src/server/error-response.ts`, `tests/server-tools.test.ts`, and the dated specification history summarized in `docs/research/2026-07-29-mcp-tools-evolution.md`.
- Impact: The project already uses the historical tool improvement most relevant to machine-readable Bilibili evidence. Tool annotations, icons, task augmentation, MRTR, discovery caching, and `x-mcp-header` remain unimplemented or inapplicable optional/new-era features; their absence alone is not evidence of a broken tool surface.

- Fact: ASR Phase 3 is implemented in the working tree as an explicit, default-off `fallback_to_asr` option on `get_video_transcript`; the ten-tool order and legacy stdio transport are unchanged.
- Evidence: `src/bilibili/playback.ts`, `src/asr/transcription.ts`, `src/bilibili/subtitle.ts`, schemas/handlers/types/errors, 10 focused files / 356 tests, 29 files / 629 full tests, and the public wire-level stdio smoke.
- Impact: Native subtitles always win. Only confirmed no-subtitle, no-selected-subtitle, or empty-subtitle-body states may invoke ASR for one resolved Part/CID; credential, HTTP, timeout, parse, and anti-bot errors remain visible and never become ASR gates.

- Fact: Phase 3 audio and runtime execution are bounded and fail closed: Bilibili-specific HTTPS CDN candidates, at most three redirects/candidates, 128 MiB audio, two-hour Part duration, 30-minute child timeout, 2 MiB stdout, 10,000 segments, 500,000 transcript characters, one active job with no queue, strict NDJSON, and guarded unique-temp cleanup.
- Evidence: `src/bilibili/playback.ts`, `src/asr/transcription.ts`, deterministic playback/transcription tests, scoped secret scan, and zero ASR temp directories after the 126-test ASR installer/transcription run.
- Impact: Cookies are sent only to the first-party playback API, never CDN/Python; signed URLs and private paths do not enter results or diagnostics; MCP calls cannot install or switch models.

- Fact: The current machine still reports `asr.status: not_installed` and `asr.model: null`.
- Evidence: built `doctor --json` after Phase 3 acceptance.
- Impact: No model was downloaded or changed and no live end-to-end ASR transcription was run; automated injectable coverage is the acceptance evidence until a user-managed ready model already exists.

## 2026-07-30

- Fact: The current uncommitted working tree implements closing controls for
  all 38 validated findings from Codex Security scan
  `6949ea8e-a129-43d6-9104-6edf7413a1ff` without changing the fixed ten-tool
  order or adding a tool. Successful in-limit response shapes remain
  compatible, while the Favorites output schema now declares tighter
  collection and string bounds.
- Evidence: The 38-row matrix in
  `docs/qa/2026-07-30-deep-security-remediation.md`, 22 files / 407 focused
  tests, 38 files / 721 full tests, clean TypeScript build, built stdio smoke,
  hook tests, and package inspection.
- Impact: Security limits are now enforced at shared stdio, MCP serialization,
  HTTP, bootstrap, cache, logger, playback, ASR, installer, hook, and publish
  boundaries. These changes remain uncommitted and unpublished.

- Fact: Shared process-local stdio, MCP, HTTP, cache, and log budgets are
  centralized in `src/security/limits.ts`; ASR- and installer-specific budgets
  remain owned by those modules. Request cancellation context lives in
  `src/security/operation-context.ts`; playback HTTPS performs public-address
  DNS validation and connection pinning in `src/security/pinned-https.ts`; and
  stdio uses `src/server/bounded-stdio-transport.ts`.
- Evidence: Exact boundary, cancellation, mixed-DNS, credential stripping,
  SNI, and oversized response/frame regressions in
  `tests/bounded-stdio-transport.test.ts`,
  `tests/mcp-response-budget.test.ts`, and `tests/pinned-https.test.ts`.
- Impact: Future network, response, or transport work must reuse these shared
  controls rather than reintroduce per-call unbounded paths.

- Fact: The npm package dry run contains 180 expected entries and no source,
  tests, internal security reports, hooks, agent memory, local config, model,
  audio, or credential files.
- Evidence: `npm pack --dry-run --json --ignore-scripts`, structural-path
  validation, and package-content private-key/GitHub/npm/AWS-token scanning.
- Impact: Runtime credential modules remain included as compiled code, but no
  credential values or private configuration are packaged.

- Fact: Production audit is not clean: the installed
  `@modelcontextprotocol/sdk@1.27.1` brings
  `@hono/node-server@1.19.14`, producing two moderate audit nodes for
  GHSA-frvp-7c67-39w9.
- Evidence: `npm audit --omit=dev --json`, `npm ls`, live npm metadata, and
  import reachability showing Hono only in the SDK Streamable HTTP module while
  this project imports stdio/shared server paths.
- Impact: Treat this as installed-but-unreachable residual risk. Re-open it if
  an HTTP/static-file transport appears or in a separate SDK compatibility
  upgrade; do not claim a zero-advisory audit.

- Fact: The user explicitly selected direct Codex remediation and rejected
  Paseo for this task.
- Evidence: Current user instruction and the task ticket status.
- Impact: No Paseo or other implementation agent is part of the 38-finding
  remediation evidence.

## 2026-08-05

- Fact: `v1.11.0` is the current npm latest and GitHub Release, published from
  release commit `e43c247` through annotated tag `v1.11.0` and trusted-publishing
  Actions run `31003552987`.
- Evidence: npm registry version, integrity and SLSA provenance metadata; the
  successful GitHub Actions run; the bilingual GitHub Release; and isolated
  `npx -y @xzxzzx/bilibili-mcp@1.11.0` version/help smoke.
- Impact: ASR Phase 1–3, CLI setup/doctor, both security-remediation rounds,
  SDK 1.30.0, and the bilingual README overview are public. MCP protocol
  modernization remains a separate inactive future direction.

- Fact: `v1.11.1` is the current npm latest and GitHub Release, published from
  release commit `ce480f0` through annotated tag `v1.11.1` and trusted-
  publishing Actions run `31019814806`.
- Evidence: the remote annotated tag dereferences to `ce480f0`; npm reports
  version/latest `1.11.1`, integrity, shasum, signature, and SLSA provenance;
  the isolated exact-version CLI smoke returned `1.11.1`; and the bilingual
  non-draft Release credits `@CYL-collab` for Issue #24 and PR #25.
- Impact: the AI subtitle large-ID validation fix from merged PR #25 is public.
  `ce480f0` directly follows merge commit `15bb5f8`, so normal release delivery
  did not overwrite or rewrite the contributor's work.

## 2026-08-06

- Fact: `v1.11.3` is npm `latest`, a public GitHub Release, and the active latest
  Official MCP Registry version under `io.github.XZXZZX-Ai/bilibili-mcp`.
- Evidence: annotated tag `v1.11.3` at `ac58a4b`; Actions run `31032259381`;
  npm integrity, signature, and SLSA provenance; exact-version npx smoke; and
  the Official Registry API exact match with `status=active` and `isLatest=true`.
- Impact: future Official Registry updates must preserve the case-sensitive
  namespace and publish the matching npm version before Registry metadata.

## 2026-08-08

- Fact: An isolated, uncommitted implementation worktree based on live master
  `1b97183` hardens five public contracts: comments `limit` counts main
  comments, `ai-zh` is canonical and preserved, blank credential replacement
  is rejected without mutation, numeric runtime settings are strictly
  validated, and plain JSON `-403` is classified by endpoint semantics.
- Evidence: schemas, handlers, bilingual references, synthetic CLI/HTTP tests,
  the public stdio language-validation assertion, 41 files / 853 full tests,
  and `docs/qa/2026-08-08-contract-correctness-hardening.md`.
- Impact: Child replies may legitimately make flat `comments[]` exceed
  `limit`; unsupported languages and malformed numeric settings now fail
  explicitly; Favorites/nav access denial no longer masquerades as paid video.

- Fact: The stdio entrypoint now evaluates `src/load-env.ts` before importing
  the server, so optional project-local `.env` numeric values are loaded before
  runtime config is frozen and validated; the reusable default server export
  remains unchanged.
- Evidence: the old-order red and fixed-order green in
  `tests/index-env-order.test.ts`, clean TypeScript build, real stdio smoke,
  package inspection, and independent risk-reviewer PASS.
- Impact: The documented source `npm start` / `dist/index.js` `.env` path is
  now real for runtime settings. This work is not on master or npm until a
  separately authorized commit and release occur.

## 2026-08-09

- Fact: Bilibili comments pagination must keep the upstream page size fixed;
  incrementing `pn` while shrinking `ps` changes the offset and can overlap
  rows. A non-empty short page is also not sufficient evidence of completion.
- Evidence: public-seam `limit: 21` and 19-row-page regressions, both observed
  red before the bounded fixed-`ps` implementation and green afterward; final
  raw-exhaustion and malformed-container regressions; and final full suite 41
  files / 857 tests.
- Impact: Requests above 20 main comments use `ps=20`, stop on an empty page
  or after `ceil(limit / 20)` pages, and slice locally. Child replies may still
  expand the flat result beyond the requested main-comment limit. A page whose
  raw rows are non-empty continues even when every row is rejected during
  normalization; a missing or non-array `replies` container fails closed.

- Fact: The 2026-08-09 delivery authorization covers an isolated branch,
  commit, push, PR, and merge for the verified source changes only.
- Evidence: user instruction in the active task and the delivery extension in
  `docs/agent-memory/handoffs/2026-08-08-contract-correctness-hardening-task-ticket.md`.
- Impact: package version remains `1.11.3`; tag, npm publication, Official MCP
  Registry publication, GitHub Release, and deployment require a separate
  release decision.

- Fact: The search adapter distinguishes an explicit empty result array from
  a missing or non-array result container. Only the malformed shape receives
  one endpoint-local retry and then fails as `UpstreamResponseError`.
- Evidence: direct search regressions for explicit empty, missing, non-array,
  transient recovery, NetworkError, HTTP 503, raw `ECONNRESET`, and abort
  passthrough; plus the MCP text-only `UPSTREAM_RESPONSE_INVALID` regression.
- Impact: malformed HTTP-200/code-0 search payloads can no longer silently
  masquerade as no matches. Explicit empty arrays and non-empty arrays whose
  rows all normalize away retain their previous successful-empty semantics.

## 2026-08-11

- Fact: Harness v2 Issue #29 supersedes the earlier path-bound Hook/runtime
  layout with one shared `RULES.md`, thin Codex/Claude adapters, tracked
  portable Hook registrations, and a worktree-scoped `.harness/runtime/`
  ledger using opaque worktree and session IDs.
- Evidence: `RULES.md`, `AGENTS.md`, `CLAUDE.md`, `.codex/hooks.json`,
  `.claude/settings.json`, `harness/`, replay/conformance tests, clean Codex and
  Claude rule-discovery smokes, all four Codex translator process-boundary
  tests, a trusted Codex lifecycle observation, and a real Claude failure
  lifecycle in the isolated #29 worktree.
- Impact: Earlier facts naming `C:\Users\ZX\.codex\memories\bilibili-mcp\`,
  `.claude\memory\`, or `.claude\runtime\` describe the legacy v1 collectors,
  not the v2 canonical event ledger. Existing primary/user Codex Hooks and
  ignored `.claude/settings.local.json` Hooks are not rewritten automatically;
  when they conflict with tracked Hooks, `harness doctor` reports
  `action-required` so the legacy registration can be migrated before rollout.

- Fact: Harness v2 Issue #30 adds the complete executable `codex-direct`
  accepted-ticket loop on top of #29's shared session spine.
- Evidence: 92 Harness tests (one platform-permission skip), 14 legacy Hook
  tests, 862 product tests, a
  185-file package with zero Harness paths, two-axis code review, independent
  risk review, and the accepted real Harness-only pilot recorded in
  `executions/2026-08-11-github-30-codex-direct-report.md`.
- Impact: Codex Direct now freezes one typed canonical worktree/mode/base/branch
  and Codex writer, atomically excludes same-source/task aliases in sibling
  worktrees without common-Git state or config changes, serializes worktree-
  local state, guards protected effects, binds an append-only evidence log and
  current review to the current diff, bounds repair, produces Recovery Bundles,
  and automatically creates one exact local accepted commit through an isolated
  index plus `commit-tree`/CAS `update-ref`. Hooks, signing, external filters,
  and caller-staged entries cannot enter that commit. Push, PR, tag, release,
  publish, credentials/SSH, history rewrite, and broad delete remain outside
  normal authority.

- Fact: Codex Direct runtime persistence is metadata-only even though the
  input task contract contains an absolute canonical worktree and verification
  commands.
- Evidence: runtime regressions reject malformed/symlink state, omit raw paths
  and commands, retain only opaque worktree/repository IDs plus semantic
  metadata/digests, preflight the declared maximum state before replacement,
  and verify every state write by bounded read-back.
- Impact: Recovery and acceptance remain auditable without copying private
  checkout paths, command text, prompts, output, or credential-bearing values
  into `.harness/runtime/`.

- Fact: Harness v2 Issue #31 adds the executable `claude-direct` accepted-ticket
  loop as a mode-fenced entrypoint to the same controller used by Codex Direct.
- Evidence: the shared two-adapter lifecycle conformance fixture, Claude process
  tests for mode/owner/manual-host tampering, cross-adapter status and mutation
  rejection, mixed-writer collision, authority guards, repeated-failure and
  adapter-failure recovery, and exact one-commit/no-remote acceptance.
- Impact: Claude Code can now plan, hold the sole Claude writer lease, write,
  verify, review, judge criteria, accept, and create the exact local ticket
  commit without Paseo or Codex fallback. Public commands must match the frozen
  mode; the constitutional remote/credential/delete/history gates are unchanged.

- Fact: A real Claude Code 2.1.212 session completed the bounded Claude Direct
  path in a disposable Harness-only repository.
- Evidence: ignored pilot base `c4844708eebdaf4339feb26c0f91877a66321367`,
  accepted commit `d4875bfe6b21e2e460d7fad2ebb59e3165a32c1e`,
  only path `harness-only.txt`, exact released Claude lease, two passing evidence
  records, one passing criterion, clean tree, and zero remotes. The first CLI
  attempt failed before start because its empty MCP JSON lacked the required
  `mcpServers` object; the corrected strict-empty configuration succeeded.
- Impact: The actual host path is proven without modifying product source, the
  implementation worktree, global settings, external Hooks, or remote state.
  The pilot required no manual Skill and therefore is not evidence of native
  `/implement`; that one-reminder/zero-write behavior is independently tested.

## 2026-08-12

- Fact: Harness v2 Issue #32 implements the `codex-paseo-claude` collaboration
  adapter as a thin seam on the shared #30/#31 Direct controller.
- Evidence: `harness/paseo_collaboration.py` (~2072 lines) reuses
  `validate_task_contract()`, `start_direct`, `_commit_unlocked`,
  `accept_codex_direct`, and shared safe-I/O/locking/recovery machinery. The
  collaboration module has 73 tests. Its final proofs bind dispatch to the
  frozen handoff digest, reports to the frozen writer, acceptance to the
  current diff, every repair to delivery evidence, and runtime state to
  metadata-only projections; both send paths remove ephemeral prompts on every
  exit. A real public-path pilot used the live resolved
  `claude/deepseek-v4-flash` writer, recorded native `/implement`, accepted one
  exact `harness-only.txt` commit (`291ad721…`), released the lease, finished
  clean, and retained zero remotes. The focused local Issue #32 commit is made
  only after the full acceptance gates pass on branch
  `codex/harness-v2-paseo-claude-32`.
- Impact: Codex can now plan, freeze a collaboration contract, launch one
  Paseo-managed Claude writer, receive a validated report, review diff/evidence,
  accept, and create one exact local commit — all through the public CLI seam.
  The adapter does not duplicate the Direct controller and does not persist
  provider/model in tracked contracts, rules, or config. Push, PR, tag,
  release, publish, and other
  remote operations remain separate user authority gates.
- Evidence: Repair attempt 7 used an explicit user-authorized sequential lease
  transfer from the idle original writer to one live-inspected
  `claude/deepseek-v4-pro[1m]` writer at thinking `max`. It added the final
  public-CLI malformed-contract proof, changed only the authorized three-file
  repair scope, returned idle, and released the lease to Codex acceptance.
  This runtime route is not persisted in tracked contracts, rules, or config.
- Evidence: Repair attempt 8 reused that same live-inspected writer at thinking
  `max`. It added an accepted-lifecycle regression and the minimum adapter guard
  that rejects Claude `local-commit` before shared delegation while preserving
  Codex's accepted-state behavior. The focused proof, all seven guard tests,
  Codex rerun, and both independent re-reviews passed; the writer returned idle.

- Fact: The collaboration adapter uses vertical-slice CLI tracer tests with
  disposable Git repositories and command-scoped `PATH` for Git resolution.
- Evidence: All 7 CLI tracer tests (`test_slice1` through `test_slice5` plus
  `test_cli_contract_validation` and `test_cli_subcommand_is_registered`) use
  `PATH="/d/Git/cmd:$PATH"` prefixed on test commands only. No tracked file
  hard-codes a machine-specific Git path. The fake Paseo CLI executable records
  events and returns bounded JSON for daemon/provider/model/run/inspect.
- Impact: Tests are portable across machines with different Git installations.
  The command-scoped PATH pattern isolates Git resolution to the test command
  without mutating global process state.

## 2026-08-13

- Fact: Harness v2 Issue #33 adds a typed-memory projector at
  `harness/memory.py` without changing the accepted #30/#31/#32 execution
  controllers.
- Evidence: The projector reads the shared strict Direct status seam, requires
  an accepted-and-committed source task plus a passing current evidence entry
  whose digest equals the canonical semantic envelope digest, and owns only
  the typed store, bounded current projection, and ignored audit ledger.
- Impact: Hooks, free-form reports, model inference, and old append-only lines
  cannot silently become authoritative project memory.

- Fact: Every durable typed record has a stable content identity, source and
  provenance, validation state, sensitivity class, validity fields and/or a
  supersession link, and an evidence digest.
- Evidence: Replay, content-binding, tamper, semantic-date, supersession,
  same-time-conflict, promotion-threshold, weak-evidence, secret/raw-payload,
  and bounded-startup tests pass. Current startup loads only accepted current
  records from `current-memory.json`.
- Impact: Replaying accepted evidence creates neither duplicate records nor a
  duplicate projection; conflicting current facts are deterministically
  superseded or rejected when ordering is ambiguous.

- Fact: The repository now has one canonical `bilibili-mcp-memory` capability
  source and deterministic thin Codex/Claude packages at version `1.0.0`.
- Evidence: The capability test recompiles both host packages byte-for-byte and
  verifies their interface, evaluation metadata, and manifest hashes. No
  externally installed capability copy is a projector output or was rewritten.
- Impact: Both hosts route through the same shared CLI and memory contract
  without duplicating projection policy in Skill prose.

- Fact: The real Issue #33 pilot used two accepted Codex Direct tasks in a
  disposable repository with no remote: a source commit
  `62caea4d73e0f88d81803ecd6abc70aae9faed54`, followed by memory-only commit
  `a3e6fcabdd36849f46a738592a24d815b64d337b`.
- Evidence: The second commit changed exactly
  `docs/agent-memory/current-memory.json` and
  `docs/agent-memory/typed-memory.json`; replay returned no change, two audit
  outcomes were retained, final Git status was clean, and remote output was
  empty.
- Impact: Automatic projection is proven through the accepted-ticket process
  boundary without product credentials, SSH, remote writes, or controller
  changes.

- Fact: Harness v2 Issue #34 adds governed Skill and Agent evolution at
  `harness/evolution.py` without changing the accepted-ticket controllers or
  product runtime.
- Evidence: Evolution consumes only a current accepted `capability-gap`, binds
  its accepted-and-committed origins, and requires an independent linked
  worktree plus an active Direct writer whose exact derived owned paths exclude
  the fixed evaluator, holdout, product, kernel, and engine.
- Impact: Typed memory may authorize a bounded Evolution Run but still cannot
  itself modify capabilities, evaluate a candidate, or approve promotion.

- Fact: One canonical evolution capability compiles deterministic Codex and
  Claude Skill/Agent projections with explicit invocation, triggers,
  interface, governance, trust, packaging, and read-only zero-child authority.
- Evidence: Host compiler, native discovery-path/schema parser, and exact projection tests
  cover manual/model semantics, shared interface and canonical digests, bounded
  manifests, and extra-file/byte drift rejection.
- Impact: Host packages cannot silently diverge or grant subagents autonomous
  delegation or a second writer.

- Fact: Controlled #34 fixtures exercise Search, Build, Reject,
  rollback, promotion-ready, and exact-one local commit in disposable linked
  worktrees with no remotes.
- Evidence: The real Search candidate is pinned `antfu/skills` commit
  `a74f281a27dadc02397bc1a174b0f2c97531b6ae`; the installed `vitest` content
  differs and has unknown immutable provenance, so the zero-install pilot is
  deferred. Candidate-provided machine claims cannot authorize Adapt; the safe
  repository-local Build fixture runs without executing or installing external
  code.
- Impact: Search evidence can reject or defer a candidate without turning
  external Skill prose into execution authority; the Adapt seam remains
  fail-closed pending trusted machine evidence, and Build remains a
  repository-local fixture.

## 2026-08-13 — Harness v2 Issue #35

- Fact: Governed Evolution now supports exact MCP, CLI, Hook, and Loop surface
  contracts without a second controller or any product-runtime change.
- Evidence: v2 canonical sources compile through the existing deterministic
  Codex/Claude package seam; public Harness discovery and smoke validate
  `codex-direct`, `claude-direct`, and `codex-paseo-claude` projections.
- Impact: Surface capabilities remain repository-local Harness artifacts and
  stay outside `src/`, `src/cli.ts`, `package.json` files, and the npm package.

- Fact: A safe v2 Adapt decision trusts only governor-created evidence from
  immutable canonical JSON, not candidate-supplied compatibility, smoke, or
  installed-provenance fields.
- Evidence: Search re-fetches the exact pinned artifact/license bytes, parses a
  byte-canonical v2 source, derives all four candidate-bound channel results
  from the fetched response formats, and compiles all adapter projections
  without executing candidate code. Dangerous effects produce one stable
  authorization request and zero capability files.
- Impact: Safe repository-local adoption is possible without weakening the #34
  fail-closed boundary for executable or legacy candidates.

- Fact: Hook and Loop surfaces have executable Harness-only safety seams.
- Evidence: The public Hook handler validates the installed capability and host,
  persists an attributed redacted event, replays it, and reads the ledger.
  Smoke proves shadow/no-diff, secret removal, linked-worktree identity, and
  exact deployment/config/canary/ledger restoration. `capability loop-step` stops at attempt/no-progress
  limits, yields to new user input, and prohibits adapter switches.
- Impact: Declaring a policy is insufficient; promotion evidence is generated
  by the shared CLI and remains subordinate to Direct acceptance.

## 2026-08-14 — Harness v2 Issue #36 checkpoint

- Fact: All three execution adapters now share one versioned conformance
  matrix in addition to the existing typed task contract and constitutional
  kernel.
- Evidence: `three-adapter-conformance.json` enumerates the three public mode
  commands, lifecycle kind, writer, acceptance owner, native invocation,
  run/control schemas, eleven pilot checks, and four migration checks. Direct
  contract/lifecycle tests consume the same fixture; no controller was copied.
- Impact: Adapter comparison is an explicit project-owned acceptance surface,
  while mode-specific transport remains in the accepted Direct/Paseo seams.

- Fact: Real Codex Direct, Claude Direct, and Paseo-managed Claude #36 pilots
  are accepted with one scoped local commit each and no remote.
- Evidence: Disposable clean repositories accepted only `pilot.txt` as commits
  `0cadc18c9cd85733875929e49130b847a204e1be` and
  `a81fef21b17330613729b5a67f13386c4ad651ec`, and
  `27fba0dce64fb591a30f0651979940089c667fb0`. Claude Direct ran in safe mode;
  the Paseo agent used the frozen provider, handoff digest, worktree, writer
  lease, and acceptance owner after one user-authorized daemon start.
- Impact: Mocked adapter tests are not used as substitutes for any of the three
  required real runtime pilots.
## 2026-08-18

- Fact: An isolated, uncommitted Issue #40 + Roadmap candidate classifies
  every selected Bilibili `ai-*` track (`ai-zh`, `ai-en`, `ai-ja`, …) as
  `ai_subtitle`, supports default-off AI exclusion in transcript/video-info,
  supports transcript-only `force_asr`, and unconditionally double-reads every
  selected `ai-*` body.
- Evidence: deterministic handler/schema/subtitle regressions, TypeScript build,
  41 files / 906 tests, 189-file package dry run, Codex diff review, and live
  read-only evidence (public `BV15kyBB5Eg8` exposes `[ai-zh, ai-en, ai-ja,
  ai-es, ai-ar, ai-pt]`).
- Impact: callers can distinguish or exclude Bilibili AI subtitles; ASR
  fallback can transcribe an `ai-*` body that fails the unconditional
  integrity checks. The candidate is not on master or npm yet.

- Fact: The existing ASR audio path already bounds playback to three candidate
  URLs and maps `ASR_AUDIO_UNAVAILABLE` to retryable bilingual guidance.
- Evidence: `src/asr/transcription.ts`, `src/utils/error-guidance.ts`, and the
  existing ASR/playback and structured-error regressions.
- Impact: Issue #40 does not need an additional nested retry layer for this
  Roadmap item; stable-but-semantically-wrong AI text remains a named residual
  (now a documented accepted limitation controlled by `force_asr` /
  `exclude_ai_subtitles`).

- Fact: The isolated roadmap worktree adds unconditional ai-* integrity
  assessment to both transcript and video-info flows, plus credential-safe
  `setup --non-interactive` / `--asr-model <tiny|base|small>`.
- Evidence: `src/bilibili/subtitle-integrity.ts` (pure-function assessment, no
  IO), the transcript/video-info double-read regressions, `src/cli.ts`
  `SetupCredentialsOptions`, focused CLI tests, and the post-build child smoke
  (4/4 cases) with piped/closed stdin and synthetic environment credentials.
- Impact: every selected `ai-*` is double-read and deterministically assessed
  (canonical stability for all `ai-*`; conservative language check limited to
  `ai-zh`; PRD v1.1 removed the title-topic lexical-overlap gate, PRD v1.2
  widened AI classification to every `ai-*` language — a stable same-language
  semantic mismatch is an accepted limitation controlled by `force_asr` /
  `exclude_ai_subtitles`);
  unusable bodies are never returned or cached (video-info returns an uncached
  description; transcript follows `handleDefinitiveSubtitleAbsence`), human
  subtitles stay single-read, and second-read failures remain errors.
  Non-interactive setup never prompts and never reads credential values from
  stdin/argv, and requires an env/global-config source with loadable
  credentials; `--asr-model` without `--non-interactive` is a validation error
  with value-free guidance. Integrity processing never logs or returns
  comparison text, tokens, hashes, or signed subtitle URLs.

- Fact: `v1.12.0` publishes the merged AI subtitle integrity and scriptable
  setup work to npm and GitHub Releases.
- Evidence: release commit `a31fafb`, annotated tag `v1.12.0`, successful
  Actions run `32107346010`, npm `latest=1.12.0` with SLSA provenance, and the
  public bilingual GitHub Release.
- Impact: Issue #40 and the related locally recorded Issue #41 defects are now
  available from npm and the Official MCP Registry. After follow-up user
  authorization, Registry `1.12.0` is `active` and `isLatest=true`.

## 2026-08-24

- Fact: The isolated Issue #65 candidate upgrades managed ASR state to v2 and
  persists a ready Profile only after the selected local model completes a
  generated short-WAV inference on `cpu/int8` and the temporary WAV is removed.
- Evidence: `src/asr/state.ts`, `src/asr/installer.ts`, deterministic state and
  installer regressions, 282 focused tests, and 44 files / 1,104 full tests.
- Impact: New CPU setup records actual execution facts instead of intent. A
  same-model v1 install can be promoted with one probe and no reinstall or model
  download; failure preserves the exact previous v1 state.

- Fact: `doctor --json` now derives model, device, compute type, Device
  Readiness, migration status, and optional sanitized failure category from the
  controlled state. The Python runner receives its Profile through validated
  argv, while the public transcript and MCP schemas remain unchanged.
- Evidence: `src/cli.ts`, `src/asr/transcription.ts`, CLI/transcription tests,
  build, package dry run, production audit, and three-axis review.
- Impact: v1 reports migration pending without claiming a device; v2 currently
  accepts only verified `cpu/int8` as ready. `cuda/float16` remains a controlled
  future Profile but cannot become disk-ready until #66 implements GPU
  readiness; #67 still owns first-ASR automatic migration.
