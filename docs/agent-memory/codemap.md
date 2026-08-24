# Codemap

This file is a navigation index for `@xzxzzx/bilibili-mcp`. It is not a design spec and should stay concise. Update it when module ownership, tool flow, test layout, release flow, or agent harness structure changes in a way that would affect future handoffs.

## Runtime Entry Points

- `src/index.ts`: stdio startup entry point. Loads environment configuration
  and connects the reusable MCP server through the bounded stdio transport.
- `src/load-env.ts`: first-evaluated entrypoint side effect that loads the
  optional package-root `.env` before server dependencies freeze runtime config.
- `src/server.ts`: reusable MCP `Server` instance. Registers `tools/list` and
  `tools/call`, delegates schemas and handlers, installs per-request
  cancellation context, and applies bounded secret-free response handling.
- `src/cli.ts`: package CLI entry point. Exports a testable `createCli()`
  factory, uses the Commander root action for no-argument bounded stdio
  startup, and exposes `setup` (credentials plus optional ASR with three-model
  selector), `doctor` (credential status plus model, controlled execution
  Profile, Device Readiness, migration status, and optional sanitized failure
  category), `config`, `check`, `check-update`, and `version`.
- `src/config.ts`: runtime configuration with strict positive-safe-integer
  validation for rate limits, timeouts, and cache sizing, plus canonical
  supported-language selection that preserves `ai-zh` and rejects unknown values.

## Shared Security Boundaries

- `src/security/limits.ts`: fixed process-local byte, queue, waiter, cache, log,
  and response ceilings. These are containment invariants, not user settings.
- `src/security/operation-context.ts`: per-MCP-call `AbortSignal` propagation,
  linked abort helpers, and abortable delay.
- `src/security/pinned-https.ts`: final playback-media HTTPS sink with
  provider-host validation, all-answer public DNS checks, exact all-answer
  `198.18.0.0/15` Fake-IP classification, connection pinning, original-host TLS
  validation, manual redirect responses, and credential stripping. Callers
  must validate and pin every redirect hop.
- `src/server/bounded-stdio-transport.ts`: fixed-buffer JSON-RPC line framing
  with 1 MiB inbound and 4 MiB outbound ceilings and write backpressure.
- `src/server/error-response.ts`: shared successful/error response
  construction, exact text/structured parity, and 2 MiB payload / 4 MiB
  envelope enforcement.
- `src/utils/bounded-response.ts`: streamed decoded-byte-limited JSON parsing.
- `src/utils/bounded-text.ts`: UTF-8-safe truncation and unsafe-control /
  unpaired-surrogate handling.

## ASR Runtime (Phases 1-3)

- `src/asr/state.ts`: three-model allowlist (`tiny`/`base`/`small` with pinned
  revisions and approximate sizes), controlled Execution Profile/failure
  enums, derived user paths (`~/.bilibili-mcp/asr/`), strict v1/v2 state
  validation, v1 migration-pending projection, and atomic v2 verified
  `cpu/int8` or `cuda/float16` ready writes (parameterized by model key,
  defaults to `small`).
- `src/asr/installer.ts`: injectable Python 3.9+ discovery (with
  `BILIBILI_ASR_PYTHON` override), allowlisted child environment, subprocess
  deadlines/output caps, user-scoped venv creation, exact faster-whisper and
  CTranslate2 pins, staged/budgeted/no-symlink snapshot download, `auto | cpu |
  cuda` readiness with generated short-WAV inference and full generator
  consumption, abortable readiness subprocesses, sanitized GPU failure
  categories, temporary-audio cleanup,
  same-model v1 promotion, staged runtime/model publication with captured-error
  rollback, and fail-closed state invalidation when rollback is incomplete. One
  active model reuses the Phase 1 directory; a failed probe keeps the prior
  verified installation.
- `src/asr/transcription.ts`: explicit ready-state-only ASR orchestration. It
  requires trusted duration, owns one aggregate audio deadline/byte budget,
  unique temporary directories, one-active/no-queue concurrency, bounded
  Windows Job/POSIX `RLIMIT` managed-Python execution, strict NDJSON,
  cancellation/tree kill, validated `cpu/int8` or `cuda/float16` Profile-driven
  Python argv, one-time locked v1 auto migration with atomic Profile/failure
  persistence and same-request execution, guarded cleanup, and all-candidate Fake-IP failure aggregation
  without preventing later-candidate success. MCP requests never
  install or switch models.

## MCP Tool Surface

- `src/server/tool-schemas.ts`: MCP tool list plus input and declared output schemas.
- `src/server/tool-handlers.ts`: tool dispatch, input validation, sanitization, Bilibili API calls, and tool-specific recovery payloads.
- `src/server/error-response.ts`: shared text-content and structured error response helpers.

Current tool families:

- Credential setup, status, and package freshness: `get_credential_setup_instructions`, `check_bilibili_credentials`, `check_mcp_update`.
- Video content: `get_video_info`, `get_video_transcript` (transcript and keyword search), `get_video_metadata`.
- Video discovery: `search_bilibili_videos` (authenticated, bounded normal-Video candidates), `search_bilibili_creators` (authenticated, bounded Creator candidates keyed by stable numeric `mid`; display names are never identity and candidates are never auto-selected), `list_bilibili_favorite_videos` (authenticated current-account Favorites traversal with a stateless opaque cursor; one upstream 20-row resource page per call), and `get_bilibili_creator_content` (authenticated, caller-selected Creator `mid`; one live overview, video-catalog page, Collection/Series container-list page, selected-container Membership page, or Dynamic page; no automatic crawl or referenced-Video evidence fetch).
- Comments: `get_video_comments`.
- Chapters: `get_video_chapters`.

When adding or changing a public MCP tool, inspect both `tool-schemas.ts` and `tool-handlers.ts`, then update tests and user-facing docs.

## Bilibili Integration

- `src/bilibili/client.ts`: compatibility-oriented client layer and shared request behavior.
- `src/bilibili/http.ts`: bounded first-party HTTP helpers, active/queue
  admission, total deadlines/cancellation, redirect rejection,
  bounded JSON, retry ownership, and login-status behavior.
- `src/bilibili/wbi.ts`: WBI signing plus bounded single-flight nav-key
  bootstrap, waiter isolation, redirect rejection, and body/key validation.
- `src/bilibili/fingerprint.ts`: bounded single-flight buvid/fingerprint
  bootstrap with fixed waiters, shared admission, redirect rejection, and strict
  response validation.
- `src/bilibili/video-api.ts`: video/subtitle/player API calls and response safety checks.
- `src/bilibili/navigation.ts`: shared Part/CID resolution for multi-Part videos.
- `src/bilibili/subtitle.ts`: native subtitle selection (human `subtitle` vs Bilibili AI `ai_subtitle` for every `ai-*` language), explicit ASR/description fallback precedence, `exclude_ai_subtitles` filtering with AI-only treated as deterministic absence, `force_asr` bypass, unconditional ai-* integrity assessment (double-read; unusable → `handleDefinitiveSubtitleAbsence` or uncached description), shared segment formatting, timestamp output, range filtering, keyword/context search, and evidence-link behavior.
- `src/bilibili/subtitle-integrity.ts`: pure-function deterministic integrity module (no IO, no logging of comparison text/tokens): `assessAiSubtitleIntegrity` over canonical cross-read bodies (collision-free `JSON.stringify` of each [from,to,content] tuple), conservative language check limited to `ai-zh` (≥80 Unicode letters, <10% Han); other `ai-*` languages are not rejected for being non-Chinese. Title-topic lexical overlap is not assessed — a stable same-language semantic mismatch is an accepted limitation controlled by `force_asr` / `exclude_ai_subtitles` (PRD v1.1 → v1.2). Frozen PRD checks, not configurable, not exposed over MCP.
- `src/bilibili/playback.ts`: authenticated first-party playurl request for one
  resolved BVID/CID, 1 MiB JSON and representation/backup/candidate limits,
  strict duration/DASH/audio validation, Bilibili-specific HTTPS CDN
  allowlisting, and deterministic lowest-bandwidth candidate selection.
- `src/bilibili/metadata.ts`: metadata retrieval, shaping, and Part summaries.
- `src/bilibili/chapters.ts`: Bilibili-provided Chapter (view_points) retrieval.
- `src/bilibili/search.ts`: authenticated first-page Video and Creator search, defensive normalization, and candidate shaping; `searchBilibiliCreators` shares the credential precheck, one-shape-retry fetch, resource item limit, and bounded-text helpers with the Video search path.
- `src/bilibili/favorites.ts`: authenticated current-account Favorites discovery. Stateless opaque base64url cursor encode/decode (versioned Folder ID + page only), strict canonical pre-network decoding and safe-integer emission, nav→created/list-all→at most one resource/list page per call, defensive Folder/Video normalization, and reported-count/skipped-count behavior.
- `src/bilibili/creator-content.ts`: authenticated Creator Content Discovery for one caller-selected `mid`. Versioned canonical base64url cursors bind mid/section plus either page and optional Collection/Series container ID or an opaque Dynamic offset before network access. The module normalizes bounded overview, video catalog, container/member pages, and one Dynamic page with text, Bilibili/CDN image metadata, referenced BVID relationships, explicit repost originals, unknown-type preservation, and `skipped_count`; no image download or per-item evidence request occurs.
- `src/bilibili/comments-api.ts`: raw comments API access.
- `src/bilibili/comments.ts`: comments retrieval, filtering, and response shaping.
- `src/bilibili/types.ts`: shared Bilibili-facing types and the runtime
  `SUPPORTED_LANGUAGES` tuple reused by config, validation, and public schemas.

## Utilities

- `src/utils/credentials.ts`: global credential storage and credential source detection.
- `src/utils/credential-guidance.ts`: safe credential setup instructions, status payloads, and next-step generation.
- `src/utils/error-guidance.ts`: unified structured MCP error payload mapper with bilingual recovery guidance and category/retry metadata, including the user-choice `ASR_FAKE_IP_DNS` cause, security boundary, exact proxy remedies, non-ASR alternative, and no-automatic-action constraints.
- `src/utils/validation.ts`: BV, language, detail-level, comment/search limits, sort, query, max_matches, context_segments, Favorites cursor (type/length/base64url charset), and Creator Content input (mid/section/cursor/container identity, including the Dynamic section) validation.
- `src/utils/sanitization.ts`: BV/URL sanitization and output sanitization helpers.
- `src/utils/errors.ts`: domain-specific error classes and codes.
- `src/utils/logger.ts`: prebounded, structurally capped, secret/path/query
  redacted stderr JSON logging.
- `src/utils/retry.ts`: retry behavior with redacted retry logging.
- `src/utils/cache.ts`: LRU cache wrapper with entry-count plus per-entry and
  aggregate serialized-byte budgets for Video and comment data.
- `src/utils/update-check.ts`: bounded, no-redirect, single-flight npm package
  freshness check with per-caller cancellation isolation.

## Tests

- `tests/mcp-server-smoke.test.ts`: built `index.js`/`cli.js` stdio coverage, Agent-facing doctor/setup/version CLI probes, MCP handler smoke coverage, and a public JSON-clean `initialize` → `tools/list` → representative `tools/call` wire test.
- `tests/cli.test.ts`: deterministic CLI tests for help output,
  `buildDoctorStatus` JSON contract (including ASR Profile/readiness/migration
  fields and sanitized failure category), credential-source priority, isolated
  blank-replacement protection, and no-leak checks.
- `tests/config.test.ts`: canonical-language behavior and table-driven strict
  validation for every user-facing numeric environment variable.
- `tests/index-env-order.test.ts`: mocked dotenv regression proving the entrypoint
  loads `.env` before runtime config is imported and validated.
- `tests/asr-installer.test.ts`: deterministic installer/state tests. Strict
  v1/v2 state validation, atomic writes, managed-path safety, Python discovery,
  venv/pip/download gates, generated-WAV inference/cleanup, same-model v1
  promotion, readiness cancellation, and full orchestration success/failure. No tests invoke real
  Python, pip, network, or model download.
- `tests/asr-installer-process.test.ts`: mocked default subprocess deadlines,
  output ceilings, argv, stdio, and platform process-group settings.
- `tests/asr-transcription.test.ts`: deterministic v1/v2 ready-state and
  first-request v1 migration, Profile-driven runner, atomic failure persistence,
  abort, and no-repeat coverage plus download, redirect, size/MIME, Fake-IP
  aggregation, child argv/environment, strict output, timeout/kill, cleanup,
  and concurrency tests with no real network, Python, audio, Cookie, or model.
- `tests/bilibili-playback.test.ts`: deterministic playurl auth/parameter, malformed-versus-empty DASH, duration, CDN allowlist, and candidate-order tests.
- `tests/bounded-stdio-transport.test.ts`: inbound/outbound framing ceilings,
  UTF-8 byte accounting, fixed-buffer chunking, and fail-closed overflow.
- `tests/bounded-response.test.ts`: decoded body/JSON byte ceilings and cleanup.
- `tests/bilibili-wbi-http-security.test.ts`: signed-request manual redirect and
  4 MiB response-body enforcement through the real WBI HTTP path.
- `tests/bootstrap-single-flight.test.ts`: fingerprint, WBI, and update
  single-flight cancellation/deadline/waiter behavior.
- `tests/mcp-response-budget.test.ts`: exact successful payload/envelope
  boundaries and text/structured parity.
- `tests/pinned-https.test.ts`: DNS/public-address rejection, exact Fake-IP
  range and mixed-answer classification, connection pinning, TLS hostname
  retention, header stripping, and host enforcement.
- `tests/publish-workflow-pins.test.ts`: full immutable SHA enforcement for
  every third-party Action across all repository workflows.
- `tests/subtitle-fallback-security.test.ts`: malformed subtitle fail-closed
  behavior and exact ASR eligibility.
- `tests/helpers/mcp.ts`: centralized test access to MCP request handlers.
- `tests/server-tools.test.ts`: MCP tool discovery and public input/output schema coverage.
- `tests/server-credential-tools.test.ts`: credential tool behavior and non-leak checks.
- `tests/update-check.test.ts`: package update guidance behavior and registry-failure fallback.
- `tests/server-error-next-steps.test.ts`: structured recovery guidance in tool errors, including bounded bilingual Fake-IP cause and remedy choices.
- `tests/fake-ip-guidance-docs.test.ts`: bilingual tool-reference regression for the Fake-IP cause, exact proxy rules, alternatives, and explicit user-choice boundary.
- `tests/fake-ip-node-matrix.test.ts`: regression for the focused package
  script, Node 20/22/25 Verify matrix, and Required-gate dependency.
- `tests/server-handler-sanitization.test.ts`: handler-level sanitization plus transcript/search structured-output contract checks.
- `tests/credential-guidance.test.ts`: credential setup/status guidance.
- `tests/bilibili-video-api.test.ts`: video/subtitle API safety and behavior checks.
- `tests/bilibili-navigation.test.ts`: Part normalization, page resolution, ValidationError behavior, and preFetchedVideoData path.
- `tests/bilibili-transcript.test.ts`: transcript fallback, size-limit, range filtering, timestamp, keyword search matching/context, search compatibility, and search-description-rejection behavior.
- `tests/bilibili-metadata.test.ts`: metadata and Part-listing behavior (pages as required array).
- `tests/bilibili-chapters.test.ts`: Chapter retrieval, content→title mapping, error propagation, and empty-list fallback.
- `tests/bilibili-search.test.ts`: authenticated request gating, bounded search parameters, result normalization, and empty-result behavior for Video and Creator search, including `search_type=bili_user` requests, mid/name acceptance rules, malformed-fact normalization, order preservation, resource item limit, and retry/error integrity.
- `tests/bilibili-favorites.test.ts`: cursor encode/decode round-trip and strict validation, credential/identity gates, exact Favorites endpoints/params/headers/request counts, no-Folder/empty-Folder/same-Folder/next-Folder/final/stale-cursor behavior, raw-empty versus filtered-empty page handling, malformed or mismatched Folder rows, reported-count/visible discrepancy, malformed Video rows and skipped_count, duplicate BVID across two Folder contexts, timestamp/duration fallbacks, and order preservation.
- `tests/bilibili-creator-content.test.ts`: Creator Content Discovery cursor and credential gates; exact overview/video/container/member/Dynamic endpoint parameters and request counts; profile/catalog/Collection/Series/member and Dynamic normalization; page/offset continuation, selected-container/Creator cursor binding, overlapping Memberships, repost/image/BVID relationships, unknown/skipped rows, ownership mismatch, byte/resource limits, structured/text parity, and error integrity.
- `tests/bilibili-request-count.test.ts`: verifies exactly 1 view-api request per default flow; cache-hit prevents subtitle requests.
- `tests/bilibili-comments-tool.test.ts`: comments tool behavior.
- `tests/cache.test.ts`: cache behavior.
- `tests/validation.test.ts`: input validation behavior.
- `tests/sanitization.test.ts`: sanitization helpers.
- `tests/logger-redaction.test.ts`: log redaction and retry-message safety, including account/Favorite Folder identifiers embedded in params and URLs.
- `tests/bvid.test.ts`: BV parsing and validation behavior.

Default verification:

- `npm run build`
- `npm test`
- `npm pack --dry-run` when package metadata, publish contents, release flow, or package entry points change.

## Package And Release

- `package.json`: npm metadata, binary mapping, scripts, dependencies, and publish file allowlist.
- `package-lock.json`: npm lockfile; update through npm tooling, not manual edits.
- `.github/workflows/verify.yml`: read-only pull-request/default-branch CI for
  product build/test/package checks, the focused Node 20/22/25 Fake-IP contract
  matrix, and sharded Windows/Linux Harness tests. `Required` aggregates all
  three groups.
- `.github/workflows/publish.yml`: trusted-publishing npm release workflow for version tags.
- `README.md`, `README_EN.md`: concise bilingual landing pages with project value, verified evidence workflow, installation and verification flow, task-oriented tool selection, CLI status gates, product limits, privacy and safety boundaries, plus prominent links to the canonical setup and tool references; they do not duplicate exhaustive installation or configuration methods.
- `docs/client-setup.md`, `docs/client-setup.en.md`: canonical bilingual source for the Agent installation prompt, npm/global/source installation, all supported MCP client configurations, credential setup and login validation, and optional runtime configuration.
- `docs/tool-reference.md`, `docs/tool-reference.en.md`: exhaustive bilingual tool behavior, examples, errors, and request-control reference.
- `assets/readme/`: local bilingual README artwork (hero and installation-flow SVGs) shipped with the npm package.
- `CHANGELOG.md`, `CHANGELOG_EN.md`: bilingual release notes.

Before release-oriented work, verify local package state with `npm pack --dry-run`, live registry state with `npm view`, and remote release/Actions state with `gh` or GitHub tooling.

## Agent Harness

- `RULES.md`: single shared constitutional/workflow core for all three execution adapters.
- `AGENTS.md`: thin Codex adapter for `codex-direct` and Codex's controller/acceptance role in `codex-paseo-claude`.
- `CLAUDE.md`: thin Claude adapter; imports `RULES.md` and defines `claude-direct` plus Paseo-managed writer behavior.
- `harness/cli.py`: shared diagnostics, typed-contract validation, hook
  ingestion/replay, manual-Skill gate, and mode-fenced `codex-direct` /
  `claude-direct` control commands.
- `harness/contracts.py`: three-mode owners, writer lease, authority, state,
  terminal, no-switch, executable plan, owned-path, verification, and repair
  invariants.
- `harness/codex_direct.py`: shared persistent controller for both Direct
  adapters, retaining the #30 compatibility module name. It freezes a clean
  canonical worktree/branch/base and the mode-specific sole writer, rejects
  cross-adapter control, uses a repository-scoped Windows mutex or POSIX
  existing-config advisory lock to scan source-bound sibling worktree leases
  atomically, guards fixed action classes, records an append-only bounded
  evidence log plus current checks/criteria/risks, bounds repairs by fingerprint
  and progress, writes Recovery Bundles, accepts the exact owned snapshot, and
  creates one hermetic, idempotent `commit-tree`/`update-ref` post-acceptance
  local commit.
- `harness/memory.py`: host-neutral Issue #33 typed-memory boundary. It validates
  bounded evidence envelopes, binds their semantic digest to a passing current
  check on an accepted-and-committed Direct run, applies promotion and current-
  fact supersession rules, rejects unsafe payloads and tampered state, writes
  the deterministic typed store/current projection atomically, and records
  metadata-only no-change/change audit outcomes. Startup reads only the bounded
  current projection.
- `harness/context.py`: dynamic Git repository/worktree attribution and opaque IDs.
- `harness/events.py`: Codex/Claude payload projection into `harness.hook-event/v1`.
- `harness/safe_io.py`: bounded JSON/JSONL, rotation, atomic replacement, and
  descriptor-identity/link/hardlink-safe file-lock primitives.
- `harness/paseo_collaboration.py`: Codex–Paseo–Claude collaboration seam for
  `codex-paseo-claude` mode (Issue #32). Two-phase preflight/bootstrap gate
  (Paseo daemon probe → bridge-trigger verification → frozen run state) with
  accepted `start_direct` lock protocol (repository_lock identity →
  bounded_file_lock → _repository_mutex → recheck). Live Git authority checks
  (HEAD, branch, porcelain status) before agent creation. PascalCase Paseo
  inspect field handling, blocking model-list failures, frozen bridge/handoff
  digest validation. Single-agent serialized dispatch, writer-scoped
  metadata-only report validation, attempt-keyed same-agent repair delivery,
  unconditional ephemeral-prompt cleanup, and recovery delegation.
  Acceptance binds launch/report/live identity to the frozen run and the
  current diff. Collaboration guard reuses
  `guard_codex_direct` with actor-aware passthrough for read-like actions and
  rejects Claude `local-commit` before actor-agnostic shared delegation.
  Thin lifecycle wrappers delegate to shared codex_direct machinery. CLI
  routes `PaseoCollaborationError` through recovery.
- `harness/tests/test_paseo_collaboration.py`: ~4474 lines, 73 tests (function
  + CLI) for the collaboration seam. Git resolution via command-scoped PATH
  (`shutil.which("git")`). Mock Paseo CLI with real PascalCase shapes. Covers
  preflight (including Paseo 0.2.5 `connectedDaemon: reachable`), bootstrap
  (including accepted lock protocol, repository-lock rejection, malformed
  inspect output routing to recovery), dispatch (at-most-once sidecar,
  persistence, rejection, oversized rejection, handoff digest validation,
  ephemeral prompt files removed after send), collaboration guard (actor
  validation, stage blocking, Claude local-commit denial in accepted state,
  unknown-action fail-closed, non-zero response normalization), report (strict
  command-key allowlist/blocklist,
  duplicate-ID detection, agent state check, summary hashing, schema,
  owned-path, agent-id, criterion-coverage, missing-key and extra-key
  validation, normalized projection persistence), repair (same-agent,
  begin_repair, attempt-keyed pending/dispatch evidence enabling sequential
  repairs and blocking undelivered attempts), acceptance (identity/digest and
  current-diff binding to the frozen run record, tampered/stale-sidecar
  rejection), send-exception prompt cleanup, recovery, and the full lifecycle
  (bootstrap → dispatch → report → accept → one-commit idempotent). The public
  CLI boundary also rejects non-object `task` values as bounded JSON before
  any run record or Paseo call.
- `harness/capabilities.py`: provider/model-neutral adapter, Skill, and agent
  discovery plus source-bound, concurrency-safe, count-bounded native-manual-
  Skill reminder markers.
- `harness/capability-packages/bilibili-mcp-memory/canonical.json`: canonical
  versioned capability source. The adjacent `codex/` and `claude/` packages are
  deterministic thin builds with matching interface/evaluation metadata and
  host-specific manifest hashes; the runtime projector never rewrites them.
- `harness/tests/test_memory.py`: typed contract, promotion, replay,
  redaction/rejection, supersession, tamper, bounded startup, capability build,
  and real disposable zero-remote Codex Direct memory-only pilot coverage.
- `harness/fixtures/`, `harness/tests/`: replay/conformance fixtures plus
  stdlib-only disposable-Git tests for session events, both Direct adapters'
  state/lease/guard/recovery/acceptance/commit boundary, and the
  `codex-paseo-claude` collaboration seam. The shared Direct conformance
  fixture drives the same public lifecycle for Codex and Claude.
- `docs/agent-memory/agent-communication.md`: three-mode execution/handoff/report protocol.
- `docs/agent-memory/executions/`: unified execution and acceptance reports.
- `docs/agent-memory/handoffs/`: durable Codex-to-Claude handoffs, Claude reports, and task-ticket-backed handoff artifacts.
- `docs/agent-memory/project-facts.md`: durable current facts.
- `docs/agent-memory/decisions.md`: durable workflow and technical decisions.
- `docs/agent-memory/lessons-learned.md`: repeated pitfalls and reusable lessons.
- `docs/agent-memory/verification-log.md`: important verification outcomes and caveats.
- `docs/agent-memory/codemap.md`: this navigation index; update when code, test, release, or harness structure changes.
- `docs/agent-memory/harness-security.md`: trust-boundary and safety baseline for rules, hooks, skills, subagents, MCP/tool config, memory, handoffs, templates, research, and QA notes.
- `docs/agent-memory/harness-eval.md`: periodic workflow evaluation file for deciding whether harness components reduce risk/rework or add overhead.
- `docs/agent-memory/pending-learning-proposals.md`: generated learning proposal queue; not formal memory until reviewed and approved.
- `docs/agent-memory/active-work.md`: current Matt/GitHub work pointer and explicit no-Superpowers rule.
- `C:\Users\ZX\.paseo\orchestration-preferences.json`: live provider routing for Paseo-managed implementation; read before launch and do not copy model choices into repository config.
- `docs/agent-memory/context-budget-report.md`: context overhead audit for always-loaded rules and hooks.
- `docs/templates/task-ticket.md`: optional execution-ticket template used under the three-tier ticket standard.
- `docs/templates/research-note.md`: external-fact research cache template.
- `docs/templates/qa-checklist.md`: human-facing QA checklist template for release/install/MCP/credential/client flows.
- `docs/agents/issue-tracker.md`: GitHub issue operations and remote-write boundaries for Matt Pocock skills.
- `docs/agents/triage-labels.md`: canonical Matt triage roles mapped to GitHub labels.
- `docs/agents/domain.md`: single-context `CONTEXT.md` and `docs/adr/` consumption rules.
- `docs/research/`: cached research notes for external facts that affect project decisions.
- `docs/qa/`: human-facing QA checklist instances.

Claude reports must include a `Harness Artifacts` section covering task ticket, research note, QA checklist, codemap, harness-security, and harness-eval status.

## Hooks And Runtime Memory

- `.claude/settings.json`: tracked portable Claude Hook adapter using `${CLAUDE_PROJECT_DIR}`. Machine-local `bypassPermissions` remains in ignored settings.
- `.codex/hooks.json`: portable Codex Hook adapter that resolves `git rev-parse --show-toplevel` at invocation time.
- `python -m harness doctor`: inventories both Codex Skill roots and reports
  overlapping primary/user Codex or machine-local Claude Hook registrations
  without echoing commands or rewriting external configuration.
- `.harness/runtime/<worktree-id>/<session-id>/events.jsonl`: ignored, redacted, bounded runtime ledger scoped to the invoking worktree.
- `.codex/scripts/`: legacy Hook utilities retained for compatibility while registrations use the shared CLI.
- `.codex/scripts/hook_safety.py`: compatibility re-export of the canonical `harness/safe_io.py` safety implementation.
- `.codex/scripts/test_hook_safety.py`: deterministic hook input, retention,
  prompt-injection, and fixed-metadata regressions.
- `.codex/scripts/plan_tracker.py`: active implementation-plan tracking for phase-gated learning reminders.
- `.codex/scripts/generate_learning_proposals.py`: generated proposal queue writer.
- `.codex/scripts/context_budget.py`: context budget auditing.
- `.codex/scripts/stop_summary.py`: lightweight stop summaries, strategic compact advice, phase learning reminders, and non-mutating harness artifact reminders for codemap, harness-security, and harness-eval checks.
- `.codex/scripts/test_stop_summary.py`: deterministic stdlib-only tests for path matching and all three reminder branches.
- `.codex/scripts/pre_compact.py`: pre-compact checkpoint support.
- `.codex/scripts/post_tool_use.py`: failed shell observation capture and candidate scoring.

Runtime observations are intentionally separate from formal memory and are now
attributed to the invoking worktree rather than a machine-specific main checkout.

Governed capability evolution:

- `harness/evolution.py`: accepted-gap gate, independent Direct-writer binding,
  Search/Adapt/Build state, bounded and byte-verified candidate schema,
  canonical Skill/Agent compiler, derived repository-local host deployment,
  fixed machine-run evaluator/holdout cases, candidate-scoped rollback/Recovery,
  and rejected/deferred/promotable reports.
- `harness/fixtures/evolution-build-capability.json`: safe, dependency-free,
  repository-local Build fixture with read-only zero-child agent policy.
- `harness/tests/test_evolution.py`: public CLI and compiler coverage including
  accepted-gap provenance, linked worktree writer, protected paths, pinned
  Search/Adapt, one authorization stop with no local resolution, Build
  success/failure, exact host-schema/discovery-path conformance, drift,
  self-approval denial, scoped
  rollback, sibling preservation, and exact-one-commit zero-remote pilots.
- `harness/evolution.py` also owns v2 MCP/CLI/Hook/Loop surface validation,
  four-channel Search records, immutable canonical-JSON verification, safe
  auto-Adapt eligibility, three-adapter repository-local discovery/smoke,
  Hook evidence checks, and bounded Loop step decisions. It extends the #34
  state machine rather than adding a controller.
- `harness/cli.py::capability discover|smoke|call|serve|hook-event|loop-step`:
  public process seam for exact deployment discovery, behavior-derived smoke,
  bounded CLI calls, stable MCP stdio, capability-bound Hook event persistence,
  and stateless Loop decisions. These are Harness-only commands and do not
  change `src/cli.ts` or the npm package.
- `harness/fixtures/evolution-build-surface.json`: dependency/script/executable-
  free v2 CLI Build fixture; tests derive MCP, Hook, and Loop variants from the
  same canonical safe source.
- `harness/fixtures/three-adapter-conformance.json`: #36 shared matrix for the
  typed contract, constitutional kernel, per-pilot checks, migration checks,
  public mode commands, writers, acceptance owners, native manual invocations,
  and run/control schemas. Direct and collaboration lifecycles reuse their
  existing controllers; this fixture adds no fourth controller.
- `harness/fixtures/three-adapter-pilot-evidence.json` and
  `harness/fixtures/pilot-artifacts/*.json`: thin migration index plus native
  controller/Recovery snapshots, recomputable Git commit/tree/blob objects,
  typed event rows, and bounded authority receipts for all three real pilots.
  The migration artifact binds command receipts, canonical package output and
  LF-normalized packaged-text sizes, durable file hashes, dirty-primary
  isolation, and exact-#35 clean-room bytes.
- `harness/events.py::normalize_hook_event`: shared #36 redaction seam that
  binds adapter/host-event provenance, metadata sensitivity, terminal state,
  and a full digest before persistence under the canonical worktree identity.
- `harness/tests/test_evolution.py`, `test_events.py`, and
  `test_cli_and_adapters.py`: v2 Search/Adapt/Build, dangerous-effect authority,
  all-three-adapter discovery/smoke, Hook policy/evidence, Loop stop/yield/no-
  switch, rollback, package-boundary and package-receipt freshness, zero-remote,
  and exact-one-commit coverage.
- `harness/memory.py::compile_host_package`: shared deterministic host-manifest
  seam used by typed memory and governed evolution; it does not grant the memory
  projector capability-write authority.

## Project Agents And Skills

Claude Code subagents:

- `.claude/agents/credential-sanitizer.md`: credential cleanup and leak checks.
- `.claude/agents/package-maintainer.md`: package metadata, scripts, lockfile, and pack contents.
- `.claude/agents/test-baseline-builder.md`: deterministic Vitest baseline and test helpers.
- `.claude/agents/build-error-resolver.md`: TypeScript, ESM, MCP, and build failures.
- `.claude/agents/risk-reviewer.md`: post-change bug/security/regression review.
- `.claude/agents/release-verifier.md`: release readiness and package verification.

Codex custom agents:

- `.codex/agents/stabilization-reviewer.toml`: plan and scope review.
- `.codex/agents/risk-reviewer.toml`: focused risk review.
- `.codex/agents/release-verifier.toml`: release readiness verification.

Fixed phase routing and manual-Skill boundaries live in `RULES.md`; adapter
deltas live in `AGENTS.md` and `CLAUDE.md`. Do not assume Codex skills,
`.agents\skills`, and Claude Code skills are shared unless the Skill is
discovered in the target runtime.

Matt Pocock workflow Skills remain native manual when their metadata says so.
The Harness emits one reminder but never imitates them. GitHub Issues hold Matt
specs/tickets. Do not invoke Superpowers or `ai-coding-harness` Skills unless
the user explicitly reintroduces them.

## Common Change Routes

- New MCP tool: `product-requirements` if scope is unclear, `domain-modeling` if terminology changes, `codebase-design` or `system-design` if interfaces/architecture change, then edit schemas, handlers, tests, README/changelog as needed.
- Credential behavior: inspect `credentials.ts`, `credential-guidance.ts`, server handlers, and secret-oriented tests; use secret/risk review before commit or release.
- Subtitle/transcript behavior: inspect `video-api.ts`, `subtitle.ts`, validation/sanitization utilities, transcript tests, and security limits.
- Comments behavior: inspect `comments-api.ts`, `comments.ts`, handler validation, and comments tool tests.
- Package/release behavior: inspect `package.json`, lockfile, publish workflow, README/changelog, and run build/test/pack verification.
- Harness/rules work: inspect `AGENTS.md`, `CLAUDE.md`, `docs/agent-memory/README.md`, `docs/agent-memory/harness-security.md`, `docs/agent-memory/harness-eval.md`, relevant memory files, templates, hook scripts, and context budget impact.
- External research-dependent work: create a note from `docs/templates/research-note.md` under `docs/research/` when external facts materially affect the decision.
- Release/install/client QA work: create a checklist from `docs/templates/qa-checklist.md` under `docs/qa/` when public install, credential, stdio, package, or client behavior is affected.
