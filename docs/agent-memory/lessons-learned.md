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

## 2026-07-27

- Lesson: A normalized empty result is not the same as an empty upstream page.
- Evidence: A non-empty Favorites `medias` page whose rows all failed normalization was initially treated as Folder exhaustion, so `has_more=true` skipped later valid pages.
- Future behavior: Preserve raw page-exhaustion state separately from normalized output and regression-test an all-rejected non-empty page.

- Lesson: Strict cursor validation must preserve both canonical encoding and the public error category through the real MCP boundary.
- Evidence: Deep JSON/version failures initially escaped as plain errors, Node's permissive base64 decoder accepted a generated cursor with an ignored trailing sextet, and incrementing `Number.MAX_SAFE_INTEGER` could emit an undecodable next page.
- Future behavior: Throw `ValidationError` for every decode failure, enforce canonical base64url round trips and safe-integer emission, and test malformed/overflow cursors through the public boundary.

- Lesson: Debug logging can expose private identifiers even when credentials are correctly redacted.
- Evidence: Shared HTTP debug output would have printed `up_mid`, `media_id`, and `folder_id` in params or URLs during Favorites traversal.
- Future behavior: Treat account and private-container identifiers as sensitive in structured fields and query strings, and add redaction regressions whenever a new authenticated endpoint introduces identifier parameters.

- Lesson: A README can explain the product correctly while still failing first-run installation comprehension.
- Evidence: Persona walkthroughs found that the initial redesign linked to a long client guide but did not give Agents a complete safe prompt, did not show people how to locate the three browser Cookie fields, and could be read as asking users to run an MCP tool name in a shell.
- Future behavior: Validate onboarding separately as an Agent journey and a human journey. Each must reach live MCP login verification without inferred steps, distinguish shell commands from MCP tool calls, keep Cookie values out of chat and client configuration, and include explicit recovery branches.

- Lesson: A strong feature workflow is not automatically the right project introduction.
- Evidence: Putting the Favorites-to-evidence workflow in the Hero and before the basic feature list made the package look like a single-purpose Favorites tool, while the actual surface also covers search, transcripts, metadata, Parts, Chapters, and comments.
- Future behavior: Introduce the full user-visible capability boundary first, then use the strongest workflows as prominent proof. Keep workflow-specific visuals beside their matching examples.

- Lesson: Product outcomes and installation mechanics need separate layers in a README.
- Evidence: A rewrite still felt unclear when local configuration was presented as a core feature, Node.js was hidden inside collapsed manual instructions, and the quick start compressed registration, setup, reconnection, and live verification into one paragraph.
- Future behavior: Present user outcomes first; show prerequisites before commands; use a short numbered install path before Agent/manual detail; reserve exact tool names and protocol fields for the reference and configuration sections.

- Lesson: Subprocess environment tests must never inherit the real agent process environment.
- Evidence: An early ASR test asserted against a real environment object, and its failure output expanded unrelated external credential values into local agent logs even though the repository and package remained clean.
- Future behavior: Build child environments from synthetic fixtures in tests, filter sensitive keys again at the actual execution boundary, and never include full environment objects in assertion diagnostics.

- Lesson: Fallback systems need a typed distinction between confirmed absence and malformed upstream data.
- Evidence: Phase 3 risk review found that a missing DASH object could initially look like a valid empty audio set, which would have hidden an upstream response defect; the parser now accepts only an explicit empty `dash.audio` array as the no-audio condition.
- Future behavior: Before adding any fallback, enumerate the exact absence states and make every transport, schema, auth, and parse failure fail closed.

- Lesson: A host allowlist should name the provider-owned surface actually required, not a broader shared infrastructure domain.
- Evidence: Phase 3 review narrowed audio retrieval from generic/shared CDN suffixes to Bilibili-specific `bilivideo.com` and `bilivideo.cn`, while redirect tests revalidate every hop.
- Future behavior: Keep signed-resource allowlists provider-specific, reject custom ports/userinfo, and test unsafe primary and backup candidates independently.

- Lesson: Passing temp-file tests can still leave harness residue when fixture cleanup removes files but not their containing directories.
- Evidence: The final Phase 3 audit found 119 historical project-prefixed test directories. Adding suite-level directory cleanup, removing only validated direct children of the OS temp root, and rerunning 126 ASR tests produced zero residue.
- Future behavior: Treat before/after temp-root residue counts as an acceptance gate for filesystem-heavy test suites, not just runtime `finally` assertions.

## 2026-08-06

- Lesson: Official MCP Registry GitHub namespaces are case-sensitive even when
  the corresponding GitHub account is commonly treated case-insensitively.
- Evidence: lowercase v1.11.2 returned HTTP 403; the exact-cased v1.11.3 name
  published successfully.
- Future behavior: use the publisher-reported granted namespace verbatim.

- Lesson: the Registry authentication token is short-lived and should be
  acquired only after the npm artifact and metadata are ready.
- Evidence: a corrected publish attempt encountered an expired token after the
  preparation delay; re-authentication followed by immediate publish succeeded.
- Future behavior: complete npm availability and validation first, then login
  and publish without an avoidable delay.

## 2026-07-30

- Lesson: Item-count limits do not contain serialized-byte amplification.
- Evidence: Overlapping transcript context, long upstream strings, nested
  replies, and two-copy MCP text/structured output could stay within row counts
  while still producing multi-megabyte allocations.
- Future behavior: Bound exact UTF-8 serialization at the final response/cache
  boundary in addition to validating collections and individual fields.

- Lesson: Cancellation semantics differ for per-request work and shared
  single-flight work.
- Evidence: Propagating one MCP signal directly into a shared fingerprint, WBI,
  or update refresh would let one waiter abort every other caller; ignoring the
  signal for ASR would leave download and native child resources running.
- Future behavior: Link cancellation through per-request operation context,
  isolate shared-refresh lifetime from individual waiters, bound waiter counts,
  and test both cases together.

- Lesson: A provider hostname allowlist is not a complete SSRF control.
- Evidence: An allowlisted playback hostname could resolve to private, special,
  empty, or mixed address sets, or change between validation and connection.
- Future behavior: Validate every resolved address, reject mixed answers, pin an
  approved address in the connection lookup, preserve the original TLS
  hostname, and strip credentials again at the final network sink.

- Lesson: Redacting arbitrary failed-command text after capture is weaker than
  refusing to persist it.
- Evidence: Hook state previously retained representation-dependent command and
  diagnostic text that later crossed into generated proposals and SessionStart
  context.
- Future behavior: Store fixed enums, bounded IDs, counts, and booleans only;
  cap hook input/state structurally; keep learning proposals review-gated; and
  never preview raw candidate text into startup context.

- Lesson: A security scan's output directory and its process logs are separate
  trust and lifecycle surfaces.
- Evidence: The official CLI correctly refused a first launch when redirected
  log files made the requested output directory nonempty.
- Future behavior: Give every scan a fresh empty artifact directory, place
  stdout/stderr logs in a sibling path, and never delete or overwrite an
  existing scan merely to retry startup.

## 2026-08-11

- Lesson: A shared state machine still needs the invoked adapter as an explicit
  transaction invariant.
- Evidence: The first Claude Direct red test showed `codex-direct status` could
  read a valid Claude run when validation trusted only the persisted mode.
- Future behavior: Pass and validate `expected_mode` at the shared load boundary
  for every read and mutation, including recovery and commit, and test at least
  one cross-mode mutation as well as status.

- Lesson: One-shot state rollback must derive identity through the same helper
  as creation.
- Evidence: Source-scoped manual-Skill markers were created with
  `source:<digest>` but unstable-start rollback originally recomputed the marker
  from task ID, consuming a reminder the user never received.
- Future behavior: Centralize durable identity derivation and leave a red/green
  rollback test whenever lock or persistence code can fail after a one-shot
  effect.

## 2026-08-12

- Lesson: Public CLI tracer tests with disposable Git repositories survive
  implementation rewrites; private-function patches do not.
- Evidence: The original Issue #32 implementation patched private
  `_run_paseo_cli` and other internal functions. Round 3 review found 13
  defects that required a complete rewrite. The replacement vertical-slice
  CLI tracer tests exercise the public `python -m harness codex-paseo-claude`
  seam through process-boundary fixtures with fake Paseo executables.
- Future behavior: For new Harness adapters, start with one public-seam CLI
  tracer test that is red against the current implementation. Mock only the
  external system boundary. Private-function mocks couple tests to
  implementation details that reviews will change.

- Lesson: Freeze authority before any external launch, not after.
- Evidence: The original bootstrap called `paseo run` before persisting
  authority. A Paseo failure after launch but before persistence would leave
  invisible state. Slice 1's red test proved run.json did not exist before
  the fake Paseo CLI recorded `run`.
- Future behavior: Persist the complete frozen authority (mode, base, branch,
  worktree, owners, lease, owned paths, pending state) as a durable run record
  BEFORE any external side effect. Make every post-freeze failure recoverable
  from that record.

- Lesson: Dead code that duplicates a shared seam is a review finding, not a
  style preference.
- Evidence: `_validate_collaboration_contract` (~66 lines) duplicated
  `validate_task_contract()` checks already performed by the shared
  `contracts.py` validator. Removing it reduced audit surface and eliminated
  the risk of the two validators drifting apart.
- Future behavior: Before freezing a new adapter, grep for functions that
  reimplement shared-controller semantics and replace them with thin wrappers
  plus adapter-specific inline assertions.

- Lesson: A manual-Skill bridge record is not native invocation evidence.
- Evidence: The Issue #32 bridge froze `/implement`, contract, handoff, owner,
  lease, worktree, base, and branch before dispatch, while the real Paseo log
  separately showed `/implement` as the Claude host user message.
- Future behavior: Keep bridge evidence for ordering and digest binding, then
  require host activity evidence before claiming a native manual Skill ran.

- Lesson: On Windows, a Git Bash command can find `git` while a child Windows
  Python process cannot resolve it from the inherited POSIX-style `PATH`.
- Evidence: The real pilot's first public guard returned
  `unable to inspect Git worktree`; the same-agent retry with a process-local
  Git `cmd` PATH prefix passed without changing config, tracked files, or the
  frozen provider.
- Future behavior: Use a command-scoped, verified Git PATH for Harness Python
  processes on Windows; never hard-code it in repository contracts or rules.

- Lesson: A live model switch is a lease transition, not a label edit.
- Evidence: Paseo 0.2.5 exposed thinking updates on an existing agent but no
  model-update command. Issue #32 therefore released the idle original writer,
  created one replacement with the official runtime route, verified its
  identity, and kept the old agent idle. Paseo also reported that a new thinking
  level applies on the next turn, so a second bounded verification turn proved
  `max` was active.
- Future behavior: Resolve the official model ID live, never encode it in
  governance contracts, and require inspect evidence plus a non-overlapping
  lease transfer before the replacement can write.

- Lesson: Actor-specific authority must be decided before an actor-agnostic
  shared state guard.
- Evidence: The shared `local-commit` guard correctly allowed accepted runs,
  but the collaboration wrapper originally applied no Claude-specific denial.
  Final staged review therefore found that Claude could inherit Codex's commit
  permission. Attempt 8 moved the denial ahead of shared delegation and proved
  both actors in one accepted-lifecycle regression.
- Future behavior: When a shared controller intentionally lacks actor identity,
  enforce host ownership at the adapter boundary before calling it, then retain
  the shared state gate for the authorized actor.

- Lesson: Ephemeral prompt cleanup belongs in `finally`, not only after a
  successful adapter call.
- Evidence: Independent review found failed `paseo send` paths could retain raw
  handoff/review text. The final regression proves cleanup on send exceptions
  while keeping prepared intent and withholding success evidence.
- Future behavior: For any file-backed external send, persist only bounded
  metadata, clean the content file unconditionally, and treat ambiguous sends
  as recovery rather than automatic retry.

## 2026-08-13

- Lesson: Acceptance metadata proves a task passed; it does not supply the
  semantic memory candidate.
- Evidence: The shared Direct run stores current digests, statuses, criteria,
  risks, accepted paths, and commit identity, but deliberately stores no fact
  text or raw command output. Issue #33 therefore added a bounded typed envelope
  whose semantic digest must already be present in passing accepted evidence.
- Future behavior: Never infer durable memory by scraping execution reports,
  Hook ledgers, stdout/stderr, or adapter sidecars. Require an exact typed
  candidate and an accepted digest binding.

- Lesson: Repetition inside one task is deduplication evidence, not independent
  support for a general process lesson.
- Evidence: Replaying or duplicating a process observation under one task ID
  leaves the lesson proposed; the same lesson becomes accepted only after a
  second independently accepted task ID, unless the source is an explicit user
  correction.
- Future behavior: Count distinct accepted tasks at promotion boundaries and
  preserve all bounded provenance without inflating support counts.

- Lesson: Determinism must fail closed when evidence cannot order two current
  truths.
- Evidence: A newer `valid_from` supersedes the old current fact; two different
  values at the same timestamp are rejected instead of being ordered by hash or
  replay sequence.
- Future behavior: Require meaningful temporal precedence for supersession;
  never turn an implementation tie-breaker into factual authority.

- Lesson: An accepted capability gap is authority to start a separate governed
  run, not authority to install the first plausible candidate.
- Evidence: The #34 Search pilot found an installed and upstream `vitest`
  capability but their bytes/provenance did not match; the run deferred and
  produced only a bounded report.
- Future behavior: Preserve Search evidence and choose Adapt only after pinned
  source, immutable license/artifact evidence, compatibility, smoke, effects,
  and rollback all pass. Never run an unpinned package-manager discovery route
  merely to satisfy a search checkbox.

- Lesson: Candidate-owned paths are not a sufficient evolution sandbox.
- Evidence: The generic Direct contract correctly permits arbitrary declared
  repository-relative paths, but #34 derives one strict capability/report path
  set, rejects Windows aliases and ignored outputs, keeps evaluator/holdout
  outside it, and revalidates ignored runtime state against the live Direct
  contract on every transition.
- Future behavior: At any privileged subsystem seam, validate both the general
  writer lease and a narrow derived allowlist plus frozen independent evidence.

- Lesson: Rollback evidence must restore the previous Git object bytes and
  modes, not merely remove newly generated files.
- Evidence: #34 freezes bounded `ls-tree` entries for the candidate namespace,
  rejects links/submodules and oversized output, preserves sibling capabilities,
  restores exact blobs/modes for known failure, and enters Recovery rather than
  deleting unknown drift.
- Future behavior: Bind rollback to an immutable baseline and route restoration
  failure to the existing Recovery Bundle rather than declaring rejection.

- Lesson: A candidate's `pass` fields are not independent machine evidence.
- Evidence: The first #35 slice could have treated compatibility, smoke, and
  installed provenance as trusted input. The final seam derives eligibility
  from exact fetched canonical bytes plus governor-compiled projections and
  leaves those candidate fields untrusted.
- Future behavior: When automation may grant authority, bind the decision to
  evidence produced inside the trusted boundary, not a claimed result adjacent
  to the candidate.

- Lesson: Naming Hook phases or Loop limits does not prove their behavior.
- Evidence: #35 added public smoke/step checks after the initial declarative
  surface schema. Hook evidence now observes replay, no-secret, no-diff,
  worktree, canary, and rollback boundaries; Loop behavior is exercised through
  the CLI for no-progress, user-input, and adapter-switch cases.
- Future behavior: For each safety label in an acceptance criterion, leave one
  runnable check whose failure changes promotion outcome.

- Lesson: A fetched channel response is evidence only after the governor derives
  its meaning; a caller-owned `result` label remains a claim.
- Evidence: Independent #35 review showed that valid bytes from an allowed host
  could still be labelled `no-match`. Search now parses candidate-bound official,
  Registry, npm, and GitHub responses and rejects any label mismatch.
- Future behavior: Bind both evidence identity and its security-relevant semantic
  conclusion inside the trusted boundary.

- Lesson: A package-manager `no-match` is a transport status, not a synthetic
  200 error document, and capability identity is not an npm coordinate.
- Evidence: Final #35 re-review found real npm 404s were rejected before parsing
  and scoped MCP packages could not equal the capability ID. Surface candidates
  now bind a separate scoped-capable name/version and only their exact 404 URL is
  normalized to `no-match`.
- Future behavior: Model package coordinates separately and test the real HTTP
  status path; keep 401, 429, and 5xx fail-closed.

- Lesson: A Hook rollback canary must exercise the deployed Hook and the state it
  actually mutates.
- Evidence: Independent #35 review rejected a temporary unrelated file as
  rollback proof. The final smoke invokes the public deployed handler twice,
  reads the capability-bound ledger, and restores the deployment, configuration,
  canary, and ledger snapshots.
- Future behavior: Test rollback against the same objects used by the real
  operation, not a structurally similar scratch file.

- Lesson: Authorization payload ordering is part of deterministic idempotence.
- Evidence: The dangerous-surface red test saw two semantically identical
  requests serialize effect blocks in different orders because an input object
  crossed a process boundary. Sorting fixed the shared root.
- Future behavior: Canonicalize all set-like evidence before hashing,
  persisting, or presenting an idempotent authorization request.

## 2026-08-14 — Harness v2 Issue #36 checkpoint

- Lesson: Acquire the formal writer lease before preserving TDD edits, even
  after the user has selected the mode and the branch exists.
- Evidence: The first red/green draft preceded `codex-direct start`; it was
  reverted to the exact clean #35 tree, the run froze the baseline and acquired
  the lease, and the verified patch was then replayed unchanged.
- Future behavior: Treat branch creation and controller writer acquisition as
  one pre-write gate, then begin the first red test.

- Lesson: Parallel long verification can erase useful evidence when the parent
  batch times out even if shorter shards finished.
- Evidence: One three-shard batch reached its 304-second parent limit without
  returning child results. Subsequent short shards and each Evolution case were
  run once independently and returned explicit green results.
- Future behavior: Parallelize only similarly bounded checks; give long
  Evolution cases their own process and timeout.

- Lesson: A collaboration contract's canonical worktree is a byte-exact host
  path, not merely a path that resolves to the same directory.
- Evidence: The first real Paseo bootstrap rejected a forward-slash Windows
  path before agent creation. Rewriting only that field to the canonical
  backslash form and recomputing the bridge contract digest produced a valid
  launch; no duplicate agent or implementation write existed.
- Future behavior: Derive collaboration `canonical_worktree` from the same
  resolved `Path` representation used by worktree discovery before freezing
  the bridge trigger.

## 2026-08-14 — PR #39 automated-review corrections

- Lesson: Evidence digests must bind repository bytes, not a platform-specific
  checkout transformation. Normalize CRLF to LF at the verification seam and
  record the canonical Git-byte digest, including durable migration memory.
- Lesson: A test fixture's canonical worktree must be native to the executing
  OS. Building it from a resolved absolute `Path` preserves the intended
  contract assertion on both Windows and POSIX.
- Lesson: Search and Build are different trust boundaries. An all-`no-match`
  Search has no candidate to pin, so Build must represent that absence
  explicitly while still rejecting candidate/rejected source results and
  preserving repository-local compiler, evaluator, holdout, rollback, and
  acceptance gates.

## 2026-08-14 — PR #39 automated-review round 2

- Lesson: Canonical identity must use the normalized value returned by the
  trust-boundary validator. Validating a trimmed view while hashing the original
  string can split one ticket into multiple writer identities.
- Lesson: Conformance tests must inject host preferences and compare the
  invariant they own. A developer HOME or pre-generated `dist/` directory is
  not portable test evidence; deterministic provider input and package
  exclusion properties are.
- Lesson: A per-message input bound is not a session lifetime bound. MCP stdio
  should retain byte/shape/lifecycle limits while serving until EOF.
- Lesson: Inspect formatter diff size before accepting it. A formatter version
  can expose historical style debt; restore unrelated churn and verify only the
  scoped change rather than laundering a broad rewrite into a repair.

## 2026-08-15 — PR #39 automated-review round 3

- Lesson: A pathname check is not a bounded read. Open untrusted JSONL once,
  verify the descriptor against the no-follow path identity before and after
  one byte-budgeted read, and never grant a fresh budget after discarding a
  partial tail. Otherwise a short concurrent append can evade the limit.
- Lesson: Two individually atomic files do not form one transaction. A
  metadata-only prepared marker plus same-process rollback keeps a typed store
  and its digest-bound projection recoverable across ordinary write failure.
- Lesson: A recovery marker is intent, not authority. Its fields and digests are
  attacker-computable, so interrupted recovery must anchor the prior pair to an
  independent trusted source. Restore the internally consistent pair committed
  at Git `HEAD`, then run the same accepted envelope normally; if no exact
  trusted baseline exists, fail closed for explicit recovery.

## 2026-08-15 — PR #39 automated-review round 4

- Lesson: A zero-candidate Build removes candidate-specific pinning, not Search
  evidence authentication. Bind repository/revision/artifact, Registry query,
  and the exact unversioned package coordinate before re-fetching every V2
  channel; a missing version does not prove a missing package. Replay the same
  check at acceptance.
- Lesson: Process-boundary test launchers must be native to the executing OS.
  Emit a batch launcher on Windows and an executable shell launcher on POSIX,
  and resolve only the native launcher so WSL cannot select a Windows shim.
- Lesson: Trust-boundary fixtures must fail for the intended reason on every
  platform. Write canonical bytes and corrupt only the receipt authority being
  tested so checkout line endings cannot provide a false green.
## 2026-08-18

- Lesson: Subtitle presence is not equivalent to subtitle usability, but
  semantic correctness cannot be established by a cheap title-overlap rule.
- Evidence: the reported `ai-zh` failure returned different unrelated bodies
  across repeated reads, while stable AI captions can still contain ordinary
  vocabulary or code terms that do not overlap a title.
- Future behavior: expose provenance, use deterministic stability checks only
  under explicit ASR fallback, preserve transport errors, and provide
  `force_asr` for cases that require caller judgment. (Superseded for
  stability-gating by the 2026-08-18 roadmap decision: selected `ai-zh` is now
  assessed unconditionally with frozen thresholds.)

- Lesson: A stable default mock can mask a sequential-read test by satisfying
  the second read.
- Evidence: the video-info integrity test first passed the stability gate on
  the second call because `mockGetSubtitleContent`'s stable default body
  consumed the third/fourth `mockResolvedValueOnce` reads and returned
  `ai_subtitle`; re-configuring the mock before the second call produced the
  intended uncached-description result.
- Future behavior: when a test depends on N sequential reads, configure every
  read explicitly or re-mock between calls; never rely on a stable default for
  an assertion that requires instability.

- Lesson: An unconstrained CLI mock in a red test can hang instead of failing.
- Evidence: slice-3 red tests with `askHiddenFn` always returning "y" drove the
  existing `while (modelKey === null)` model selector into a vitest heap OOM.
- Future behavior: for CLI tests that must terminate existing prompt loops,
  make mocks choose a terminating branch (for example "n" to skip ASR) and run
  each red test in isolation.

## 2026-08-24 — ASR runtime replacement

- Lesson: A readiness probe cannot protect a working installation if setup
  mutates that installation before probing. Build runtime and model candidates
  in sibling staging directories and probe there. Before activation, move the
  old ready state out of the active slot; restore it only if every artifact
  rollback succeeds, otherwise keep state inactive so the runner fails closed.
- Evidence: Issue #66 review reproduced explicit-CUDA and model-switch failures
  that otherwise left the previous Profile pointing at changed runtime bytes.
- Future behavior: any ASR dependency, model, or device migration must preserve
  the exact prior verified state/runtime/model until the replacement probe has
  succeeded.

- Lesson: Probe cleanup failure is not a normal device-readiness failure. Auto
  fallback must stop rather than publish CPU ready while a generated WAV from
  the failed GPU attempt remains undeleted.
- Evidence: Issue #66 risk review reproduced a successful CPU fallback with an
  orphaned GPU probe before the cleanup failure became non-fallbackable.
- Future behavior: every readiness attempt must complete its own cleanup before
  another device probe or ready-state publication is allowed.

## 2026-08-24 — ASR migration cancellation

- Lesson: Checking cancellation only before and after a native readiness probe
  preserves state correctness but can retain the single ASR slot until the
  subprocess timeout. The signal must terminate the probe process tree, and
  probe error mapping must preserve `AbortError` instead of converting it into
  a device failure.
- Evidence: Issue #67 Standards review found the production-seam gap after the
  initial no-persistence abort test passed; signal propagation and focused
  regressions then passed.
- Future behavior: any new ASR Python subprocess owned by a request must accept
  the request signal, terminate its tree on abort, clean temporary artifacts,
  and keep cancellation distinct from readiness/runtime failures.

## 2026-09-04

- Lesson: A peer-project inventory must not turn unselected features into rejected product directions.
- Evidence: The user corrected a roadmap scan that labeled write operations, downloads, built-in RAG, and hosted MCP as explicitly excluded even though no such product decision had been made.
- Future behavior: Distinguish “not currently authorized or activated” from “rejected”; preserve unselected ideas as candidates, document their tradeoffs and risks, and leave the product choice to the user.
