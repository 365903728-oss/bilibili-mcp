# Lessons Learned

## 2026-05-27

- Lesson: Do not assume `.agents\skills` skills are available to Claude Code.
- Evidence: `vitest`, `secret-scanning`, and `github-actions-docs` were first installed under `.agents\skills`; Claude Code needed copies under `.claude\skills`.
- Future behavior: Check the target agent's actual skill directory before claiming a skill is installed for that agent.

- Lesson: Removing hard-coded Bilibili Cookie values must not remove Cookie-based subtitle access.
- Evidence: User clarified that subtitles may require Cookie access.
- Future behavior: Externalize credentials while preserving authenticated retrieval paths.

- Lesson: Some existing Markdown and terminal output can contain mojibake.
- Evidence: `AGENTS.md` and `CLAUDE.md` include encoding safety rules.
- Future behavior: Verify files as UTF-8 before copying or rewriting Chinese text.

## 2026-05-28

- Lesson: The project `.codex\` directory can be suitable for hook configuration but not necessarily for mutable runtime logs.
- Evidence: A dry run of `post_tool_use.py --agent codex` failed with Windows access denial when creating `.codex\memory`.
- Future behavior: Store Codex runtime hook observations under `C:\Users\ZX\.codex\memories\bilibili-mcp\`.

## 2026-06-04

- Lesson: Separate "memory capture worked" from "learning proposal promoted" when evaluating the agent memory system.
- Evidence: Phase 2 and Phase 3 verification entries were written to `docs/agent-memory/verification-log.md`, and both Codex and Claude hook runtime files existed, but `pending-learning-proposals.md` had no proposals above threshold.
- Future behavior: Report these as different states: formal verification memory can be complete even when controlled learning has no approved promotion.

- Lesson: Active-plan tracking should filter both candidate plans and previous runtime state through the same tracked-plan rule.
- Evidence: `plan_tracker.py` initially ignored non-implementation plans in fresh resolution but still preserved an old unchecked previous plan from runtime state; adding the same eligibility check to `previous_plan` fixed Codex and Claude runtime state.
- Future behavior: Before starting a new phase or relying on phase-gated learning reminders, run `python .codex/scripts/plan_tracker.py` and regenerate learning proposals for both `codex` and `claude` to confirm runtime state follows the intended plan.

- Lesson: Release workflow guidance must be refreshed from official documentation when touching npm trusted publishing or GitHub Actions OIDC.
- Evidence: Phase 4 Task 5 checked npm Trusted Publishers, npm provenance statements, GitHub Actions permissions, and GitHub Node.js package publishing docs before changing `.github/workflows/publish.yml`.
- Future behavior: Do not rely on stale memory for Node/npm minimums, provenance, OIDC permissions, or registry setup; re-check official docs before release workflow edits.

- Lesson: A polished publish workflow is not the same as a completed release.
- Evidence: Phase 4 updated README, changelogs, package metadata, and publish workflow, but final verification explicitly recorded no tag, no GitHub release, and no npm publish.
- Future behavior: When the user asks to start release execution, include npm trusted publishing setup confirmation, final local verification, tag push, Actions monitoring, and post-publish release notes as separate gates.

- Lesson: `npm install -g npm@latest` is acceptable as a trusted-publishing compatibility measure but remains a moving CI target.
- Evidence: Phase 4 kept this step to satisfy npm CLI trusted publishing support while recording it as a remaining release risk.
- Future behavior: Before long-term release automation hardening, consider pinning npm to a known compatible version instead of relying on `latest`.

## 2026-06-05

- Lesson: README-only credential guidance is insufficient for agent-driven MCP installation.
- Evidence: The user clarified that most users install MCP servers through agents, and that the installing agent should guide the user through Cookie setup.
- Future behavior: Credential-dependent MCP tools should advertise setup dependencies in `tools/list`, expose a dedicated setup-instructions tool, and include actionable `next_steps` on credential-related errors.

- Lesson: Generic MCP error handlers can silently drop structured recovery guidance.
- Evidence: Review found that content tools using the generic catch path did not initially return `code` and `next_steps` for `BilibiliAPIError("COOKIE_EXPIRED")`; a regression test was added in `tests/server-error-next-steps.test.ts`.
- Future behavior: When adding new error helpers, verify both specialized error branches and generic catch branches.

- Lesson: Separate generated learning queues from runtime caches when cleaning the worktree.
- Evidence: `pending-learning-proposals.md` belongs to the controlled-learning review queue, but `.codex/scripts/__pycache__/plan_tracker.cpython-311.pyc` is Python bytecode cache.
- Future behavior: Preserve and review generated memory files deliberately; ignore or remove runtime cache artifacts without treating them as formal memory.

- Lesson: Credential source reporting currently covers environment variables and global config, not in-memory-only credentials.
- Evidence: `CredentialManager.getCredentialSource()` returns `env`, `global_config`, or `none` based on environment and global config file state.
- Future behavior: If a future MCP login flow creates in-memory credentials, update credential status reporting so it does not falsely report `none`.

## 2026-06-14

- Lesson: Credential-status tests that assert `source: none` must hide the developer machine's global Bilibili config.
- Evidence: Focused credential guidance tests failed on a machine with global credentials configured because `credentialManager.clearCredentials()` only clears in-memory state and does not remove `~/.bilibili-mcp/config.json`.
- Future behavior: Mock or isolate global config file detection when testing the no-credential branch; do not depend on a developer machine having no configured Cookies.

## 2026-07-19

- Lesson: A single promise that represents only the current rate-limit wait does not form a concurrent request queue.
- Evidence: Three simultaneous `throttledFetch` calls produced a minimum start gap of about `0.155ms` against a configured `500ms` interval because multiple callers awaited the same old promise and then waited together.
- Future behavior: Reserve a caller's place synchronously in a normalized promise chain, test concurrent starts directly, and distinguish prior queue time from the caller's own timeout-covered wait.

- Lesson: A completed Paseo top-level task can remain `running` when a requested Claude subagent does not return.
- Evidence: Both `test-baseline-builder` and `risk-reviewer` invocations failed to return promptly even though the top-level agent completed the implementation, verification, and report; Codex explicitly stopped only that agent after preserving its output.
- Future behavior: Use bounded wait windows, let the top-level agent complete the same scoped work when a subagent stalls, and stop the finished agent without restarting the Paseo daemon or touching unrelated agents.

- Lesson: Adding a second public subtitle flow without reusing the existing empty-list credential policy caused documented behavior to drift.
- Evidence: `getVideoInfoWithSubtitle` verified login on an empty subtitle list, while `getVideoTranscriptData` silently returned description when fallback was enabled; the focused test reproduced the mismatch in 9ms.
- Future behavior: Keep credential interpretation in one private helper and test the documented public interface whenever a sibling flow is added or changed.

- Lesson: A fallback intended to keep an operation available must not be cached when the triggering error may be transient.
- Evidence: The general subtitle-error branch cached a description fallback for one hour, so a second call with a successful mocked subtitle response still returned `description` and never retried `getVideoSubtitle`.
- Future behavior: Test fallback cache policy with two calls using the same key: transient failure first, recovery second; preserve caching only for durable successful results.

- Lesson: Cache keys must include every option that changes post-processing, not only options sent to the upstream API.
- Evidence: With an explicit limit, brief and detailed comment calls shared `limit-5` even though detailed mode appends child replies; the second call returned the cached one-comment brief result instead of four processed comments.
- Future behavior: For option-sensitive caches, add paired-call tests that vary one output-affecting option while holding upstream pagination options constant.

- Lesson: Correcting always-loaded agent rules is incomplete if callable custom-agent definitions keep the same stale instruction.
- Evidence: After `AGENTS.md` and `CLAUDE.md` were corrected, completion audit found four `.claude/agents` and `.codex/agents` files still directing agents to treat `npm test` as a stub.
- Future behavior: When a durable harness fact changes, scan all current rule consumers while preserving dated historical records; do not limit verification to the two top-level instruction files.

- Lesson: Process readiness tests should wait for the observable ready event, not an elapsed-time guess.
- Evidence: The stdio smoke test killed the server after 300ms; 5 of 20 measured starts needed more than 300ms even though all succeeded, producing empty-stderr flakes.
- Future behavior: Use a bounded event-driven readiness promise, reject on spawn error or premature exit, register close observation before kill, and await cleanup; keep the internal timeout below the test framework timeout.

- Lesson: Wrapper layers should not prefetch data that the delegated API layer already owns, especially when the fetched value is unused.
- Evidence: `getVideoCommentsData` fetched video info and assigned `cid` without reading it, while `getVideoComments` immediately fetched the same metadata to compute the required oid.
- Future behavior: Trace ownership through compatibility re-exports before optimizing; lock the wrapper boundary with a dependency-call regression, then delete the unused request instead of adding metadata parameters.

- Lesson: A validated public maximum is not implemented if a lower layer silently caps one request below it and the orchestration never paginates.
- Evidence: Comment `limit` accepted 1-50, but the API capped `ps` at 20 and the wrapper requested only page 1; the failing-first regression observed one call instead of page sizes 20, 20, and 10.
- Future behavior: When public counts exceed upstream page sizes, test the boundary with sequential page calls, early exhaustion, defensive truncation, and any post-processing that can expand the final result.

- Lesson: A boolean status helper must not collapse transport failure into a definitive negative state.
- Evidence: `checkLoginStatus` returned `isLogin:false` for HTTP 503 and thrown fetch failures, causing credential callers to treat an unknown network state as logged out.
- Future behavior: Reuse the shared HTTP path, preserve successful false responses only, and verify both the low-level error type and the public MCP structured error shape.

- Lesson: A retry allowlist is ineffective when a later broad error-type check can override a rejected explicit status.
- Evidence: `NetworkError` with status 403 missed the transient status allowlist but then matched the generic `NetworkError` name branch and executed four attempts.
- Future behavior: Treat an explicit numeric status as a final allowlist decision; use name/code retries only when no HTTP status exists, and lock all three branches in one compact matrix.

- Lesson: A correct retry policy still fails when one HTTP caller omits status metadata while constructing its shared error type.
- Evidence: `getSubtitleContent` received HTTP 403 but created `NetworkError` without `response.status`, so the error looked status-less and retried four times.
- Future behavior: When adding an HTTP error call site, preserve the response status and test retry behavior through the real caller seam, not only through the retry utility.

- Lesson: Error metadata must survive both the original throw and any outer wrapping layer.
- Evidence: The WBI nav path omitted `navRes.status` at the source and its outer catch created another `NetworkError` without carrying nested status metadata.
- Future behavior: Trace shared errors end to end; a regression should assert both retry count and the final observable metadata.

- Lesson: Transport errors must be normalized before retry classification, and request timers need cleanup on failure as well as success.
- Evidence: Raw WBI `TypeError` reached `withRetry` unrecognized and stopped after one attempt, while `clearTimeout` was skipped because it followed the failed await.
- Future behavior: Put normalization and cleanup at the fetch boundary with `try/catch/finally`, then assert attempts, cleanup count, and final error metadata together.

- Lesson: Optional best-effort requests still need deterministic resource cleanup even when failure is intentionally swallowed.
- Evidence: `getBuvid` correctly returned `null` on fetch rejection but skipped `clearTimeout`, leaving the timer pending.
- Future behavior: Keep fallback semantics separate from cleanup guarantees, and assert both the fallback result and exact request/cleanup counts.

## 2026-07-20

- Lesson: An undocumented consumer response must be verified against a live first-party sample before finalizing fixtures and types.
- Evidence: The first Chapter implementation modeled `view_points[].title`, while the live player response uses `view_points[].content`; the incorrect fixture made the initial tests pass with empty real titles.
- Future behavior: Cache the live response shape in a research note, use the observed field as authoritative with defensive fallback, and include at least one fixture matching the real field names.

- Lesson: Shared navigation must not move cache checks behind a new network request or duplicate an existing view request.
- Evidence: The first implementation fetched video info inside the resolver and again in callers, and the first repair still checked the video-info cache after resolution.
- Future behavior: Add exact dependency-call regressions for default flows and cache hits whenever a shared fetch/selection seam is introduced.

- Lesson: Deleting a TypeScript source file is incomplete when `tsc` writes into an uncleared output directory used by `npm pack`.
- Evidence: After deleting unused `src/bilibili/auth.ts`, the first build and package dry run still included four stale `dist/bilibili/auth.*` artifacts; a guarded clean-before-compile step reduced the package from 128 to 124 entries.
- Future behavior: For source deletions, verify package contents as well as imports and compilation, and keep the build clean step portable rather than hard-coding a checkout path.

## 2026-07-26

- Lesson: An exact-version npm CLI smoke run from inside a repository with the same package name can resolve a globally installed shim instead of the requested temporary package.
- Evidence: `npm exec --package=@xzxzzx/bilibili-mcp@1.9.0` run at the repository root found only the global binary and reported stale version `1.3.7`; the same command from a dedicated empty temporary directory resolved the `_npx` binary first and correctly reported `1.9.0`.
- Future behavior: Run published-package CLI acceptance from an empty directory outside the checkout, record the resolved executable path, and only diagnose a package-version defect after that isolation gate.

- Lesson: Agent-guided installation is a primary onboarding path, but installation and configuration need one authoritative home.
- Evidence: The user first rejected hiding or deleting the Agent path, then explicitly chose the dedicated bilingual client setup guides as the complete source and asked the READMEs to link there without duplicating methods.
- Future behavior: Keep the complete Agent prompt prominent in `docs/client-setup.md` and `docs/client-setup.en.md`; keep the READMEs concise and link to those guides. The prompt must require client identification, client-specific syntax, local-only credential entry, MCP reconnection, mandatory login validation with `check_bilibili_credentials`, and separate optional version checking.

- Lesson: README SVG rows must not rely on fixed text-width offsets or share vertical space with overlapping modules.
- Evidence: The first bilingual heroes split adjacent text with fixed `x` coordinates and placed a footer timeline inside the right proof card's vertical range, producing visible font-dependent spacing and structural overlap.
- Future behavior: Keep titles as one text element, isolate proof modules on non-overlapping geometry, use system-font fallbacks, and inspect every full-width SVG at both 900px and 360px before acceptance.
