# Codemap

This file is a navigation index for `@xzxzzx/bilibili-mcp`. It is not a design spec and should stay concise. Update it when module ownership, tool flow, test layout, release flow, or agent harness structure changes in a way that would affect future handoffs.

## Runtime Entry Points

- `src/index.ts`: stdio startup entry point. Loads environment configuration
  and connects the reusable MCP server through the bounded stdio transport.
- `src/server.ts`: reusable MCP `Server` instance. Registers `tools/list` and
  `tools/call`, delegates schemas and handlers, installs per-request
  cancellation context, and applies bounded secret-free response handling.
- `src/cli.ts`: package CLI entry point. Exports a testable `createCli()`
  factory, uses the Commander root action for no-argument bounded stdio
  startup, and exposes `setup` (credentials plus optional ASR with three-model
  selector), `doctor` (credential and ASR status plus `asr.model` key),
  `config`, `check`, `check-update`, and `version`.
- `src/config.ts`: runtime configuration (rate limits, timeouts, cache sizing) and preferred subtitle language normalization.

## Shared Security Boundaries

- `src/security/limits.ts`: fixed process-local byte, queue, waiter, cache, log,
  and response ceilings. These are containment invariants, not user settings.
- `src/security/operation-context.ts`: per-MCP-call `AbortSignal` propagation,
  linked abort helpers, and abortable delay.
- `src/security/pinned-https.ts`: final playback-media HTTPS sink with
  provider-host validation, all-answer public DNS checks, connection pinning,
  original-host TLS validation, manual redirect responses, and credential
  stripping. Callers must validate and pin every redirect hop.
- `src/server/bounded-stdio-transport.ts`: fixed-buffer JSON-RPC line framing
  with 1 MiB inbound and 4 MiB outbound ceilings and write backpressure.
- `src/server/error-response.ts`: shared successful/error response
  construction, exact text/structured parity, and 2 MiB payload / 4 MiB
  envelope enforcement.
- `src/utils/bounded-response.ts`: streamed decoded-byte-limited JSON parsing.
- `src/utils/bounded-text.ts`: UTF-8-safe truncation and unsafe-control /
  unpaired-surrogate handling.

## ASR Runtime (Phases 1-3)

- `src/asr/state.ts`: three-model allowlist (`tiny`/`base`/`small` with pinned revisions and approximate sizes), model-spec resolution and validation, derived user paths (`~/.bilibili-mcp/asr/`), versioned state read/validation (accepts any allowlisted repository/revision), and atomic state write (parameterized by model key, defaults to `small`).
- `src/asr/installer.ts`: injectable Python 3.9+ discovery (with
  `BILIBILI_ASR_PYTHON` override), allowlisted child environment, subprocess
  deadlines/output caps, user-scoped venv creation, pinned pip install,
  staged/budgeted/no-symlink snapshot download, CPU INT8 model-load
  verification, atomic activation, and failure cleanup. One active model reuses
  the Phase 1 directory.
- `src/asr/transcription.ts`: explicit ready-state-only ASR orchestration. It
  requires trusted duration, owns one aggregate audio deadline/byte budget,
  unique temporary directories, one-active/no-queue concurrency, bounded
  Windows Job/POSIX `RLIMIT` managed-Python execution, strict NDJSON,
  cancellation/tree kill, and guarded cleanup. MCP requests never install or
  switch models.

## MCP Tool Surface

- `src/server/tool-schemas.ts`: MCP tool list plus input and declared output schemas.
- `src/server/tool-handlers.ts`: tool dispatch, input validation, sanitization, Bilibili API calls, and tool-specific recovery payloads.
- `src/server/error-response.ts`: shared text-content and structured error response helpers.

Current tool families:

- Credential setup, status, and package freshness: `get_credential_setup_instructions`, `check_bilibili_credentials`, `check_mcp_update`.
- Video content: `get_video_info`, `get_video_transcript` (transcript and keyword search), `get_video_metadata`.
- Video discovery: `search_bilibili_videos` (authenticated, bounded normal-Video candidates) and `list_bilibili_favorite_videos` (authenticated current-account Favorites traversal with a stateless opaque cursor; one upstream 20-row resource page per call).
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
- `src/bilibili/subtitle.ts`: native subtitle selection plus explicit ASR/description fallback precedence, shared segment formatting, timestamp output, range filtering, keyword/context search, and evidence-link behavior.
- `src/bilibili/playback.ts`: authenticated first-party playurl request for one
  resolved BVID/CID, 1 MiB JSON and representation/backup/candidate limits,
  strict duration/DASH/audio validation, Bilibili-specific HTTPS CDN
  allowlisting, and deterministic lowest-bandwidth candidate selection.
- `src/bilibili/metadata.ts`: metadata retrieval, shaping, and Part summaries.
- `src/bilibili/chapters.ts`: Bilibili-provided Chapter (view_points) retrieval.
- `src/bilibili/search.ts`: authenticated first-page Video search, defensive normalization, and candidate shaping.
- `src/bilibili/favorites.ts`: authenticated current-account Favorites discovery. Stateless opaque base64url cursor encode/decode (versioned Folder ID + page only), strict canonical pre-network decoding and safe-integer emission, nav→created/list-all→at most one resource/list page per call, defensive Folder/Video normalization, and reported-count/skipped-count behavior.
- `src/bilibili/comments-api.ts`: raw comments API access.
- `src/bilibili/comments.ts`: comments retrieval, filtering, and response shaping.
- `src/bilibili/types.ts`: shared Bilibili-facing types.

## Utilities

- `src/utils/credentials.ts`: global credential storage and credential source detection.
- `src/utils/credential-guidance.ts`: safe credential setup instructions, status payloads, and next-step generation.
- `src/utils/error-guidance.ts`: unified structured MCP error payload mapper with bilingual recovery guidance and category/retry metadata.
- `src/utils/validation.ts`: BV, language, detail-level, comment/search limits, sort, query, max_matches, context_segments, and Favorites cursor (type/length/base64url charset) validation.
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
- `tests/cli.test.ts`: deterministic CLI tests for help output, `buildDoctorStatus` JSON contract (including ASR object), credential-source priority, and no-leak checks.
- `tests/asr-installer.test.ts`: deterministic installer/state tests. State read/validation/write, Python discovery (override/path/version), venv/pip/download/verify subprocess gating, and full orchestration success/failure. No tests invoke real Python, pip, network, or model download.
- `tests/asr-installer-process.test.ts`: mocked default subprocess deadlines,
  output ceilings, argv, stdio, and platform process-group settings.
- `tests/asr-transcription.test.ts`: deterministic ready-state, download, redirect, size/MIME, child argv/environment, strict output, timeout/kill, cleanup, and concurrency tests with no real network, Python, audio, Cookie, or model.
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
- `tests/pinned-https.test.ts`: DNS/public-address rejection, connection
  pinning, TLS hostname retention, header stripping, and host enforcement.
- `tests/publish-workflow-pins.test.ts`: full immutable SHA enforcement for
  every third-party publish Action.
- `tests/subtitle-fallback-security.test.ts`: malformed subtitle fail-closed
  behavior and exact ASR eligibility.
- `tests/helpers/mcp.ts`: centralized test access to MCP request handlers.
- `tests/server-tools.test.ts`: MCP tool discovery and public input/output schema coverage.
- `tests/server-credential-tools.test.ts`: credential tool behavior and non-leak checks.
- `tests/update-check.test.ts`: package update guidance behavior and registry-failure fallback.
- `tests/server-error-next-steps.test.ts`: structured recovery guidance in tool errors.
- `tests/server-handler-sanitization.test.ts`: handler-level sanitization plus transcript/search structured-output contract checks.
- `tests/credential-guidance.test.ts`: credential setup/status guidance.
- `tests/bilibili-video-api.test.ts`: video/subtitle API safety and behavior checks.
- `tests/bilibili-navigation.test.ts`: Part normalization, page resolution, ValidationError behavior, and preFetchedVideoData path.
- `tests/bilibili-transcript.test.ts`: transcript fallback, size-limit, range filtering, timestamp, keyword search matching/context, search compatibility, and search-description-rejection behavior.
- `tests/bilibili-metadata.test.ts`: metadata and Part-listing behavior (pages as required array).
- `tests/bilibili-chapters.test.ts`: Chapter retrieval, content→title mapping, error propagation, and empty-list fallback.
- `tests/bilibili-search.test.ts`: authenticated request gating, bounded search parameters, result normalization, and empty-result behavior.
- `tests/bilibili-favorites.test.ts`: cursor encode/decode round-trip and strict validation, credential/identity gates, exact Favorites endpoints/params/headers/request counts, no-Folder/empty-Folder/same-Folder/next-Folder/final/stale-cursor behavior, raw-empty versus filtered-empty page handling, malformed or mismatched Folder rows, reported-count/visible discrepancy, malformed Video rows and skipped_count, duplicate BVID across two Folder contexts, timestamp/duration fallbacks, and order preservation.
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
- `.github/workflows/publish.yml`: trusted-publishing npm release workflow for version tags.
- `README.md`, `README_EN.md`: concise bilingual landing pages with project value, verified evidence workflow, installation and verification flow, task-oriented tool selection, CLI status gates, product limits, privacy and safety boundaries, plus prominent links to the canonical setup and tool references; they do not duplicate exhaustive installation or configuration methods.
- `docs/client-setup.md`, `docs/client-setup.en.md`: canonical bilingual source for the Agent installation prompt, npm/global/source installation, all supported MCP client configurations, credential setup and login validation, and optional runtime configuration.
- `docs/tool-reference.md`, `docs/tool-reference.en.md`: exhaustive bilingual tool behavior, examples, errors, and request-control reference.
- `assets/readme/`: local bilingual README artwork (hero and installation-flow SVGs) shipped with the npm package.
- `CHANGELOG.md`, `CHANGELOG_EN.md`: bilingual release notes.

Before release-oriented work, verify local package state with `npm pack --dry-run`, live registry state with `npm view`, and remote release/Actions state with `gh` or GitHub tooling.

## Agent Harness

- `AGENTS.md`: Codex/project-wide operating rules, fixed skill/MCP/CLI/subagent triggers, and Codex-to-Claude collaboration model.
- `CLAUDE.md`: Claude Code execution rules, fixed skill/subagent triggers, and report expectations.
- `docs/agent-memory/agent-communication.md`: file-backed Codex handoff and Claude report protocol, including the required `Harness Artifacts` report section.
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

- `.claude/settings.local.json`: Claude Code project hook registration.
- `.codex/hooks.json`: Codex app hook registration.
- `.codex/scripts/`: shared hook scripts and local harness utilities.
- `.codex/scripts/hook_safety.py`: bounded hook JSON/JSONL readers, locks,
  atomic writes, state retention, and symlink refusal.
- `.codex/scripts/test_hook_safety.py`: deterministic hook input, retention,
  prompt-injection, and fixed-metadata regressions.
- `.codex/scripts/plan_tracker.py`: active implementation-plan tracking for phase-gated learning reminders.
- `.codex/scripts/generate_learning_proposals.py`: generated proposal queue writer.
- `.codex/scripts/context_budget.py`: context budget auditing.
- `.codex/scripts/stop_summary.py`: lightweight stop summaries, strategic compact advice, phase learning reminders, and non-mutating harness artifact reminders for codemap, harness-security, and harness-eval checks.
- `.codex/scripts/test_stop_summary.py`: deterministic stdlib-only tests for path matching and all three reminder branches.
- `.codex/scripts/pre_compact.py`: pre-compact checkpoint support.
- `.codex/scripts/post_tool_use.py`: failed shell observation capture and candidate scoring.

Runtime observations are intentionally separate from formal memory:

- Codex runtime observations: `C:\Users\ZX\.codex\memories\bilibili-mcp\`.
- Claude runtime observations: `.claude\memory\` and `.claude\runtime\`.

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

Fixed skill trigger details live in `AGENTS.md` and `CLAUDE.md`. Do not assume Codex skills, `.agents\skills`, and Claude Code skills are shared unless the skill exists in the target runtime.

Matt Pocock workflow skills are installed in both Codex and Claude Code. GitHub Issues hold Matt specs and tickets, substantial Claude implementation continues through file-backed handoffs, and Codex uses Paseo CLI to launch one bounded implementation agent. Do not invoke Superpowers skills; project Git, security, verification, and no-autonomous-team rules override conflicting skill defaults.

## Common Change Routes

- New MCP tool: `product-requirements` if scope is unclear, `domain-modeling` if terminology changes, `codebase-design` or `system-design` if interfaces/architecture change, then edit schemas, handlers, tests, README/changelog as needed.
- Credential behavior: inspect `credentials.ts`, `credential-guidance.ts`, server handlers, and secret-oriented tests; use secret/risk review before commit or release.
- Subtitle/transcript behavior: inspect `video-api.ts`, `subtitle.ts`, validation/sanitization utilities, transcript tests, and security limits.
- Comments behavior: inspect `comments-api.ts`, `comments.ts`, handler validation, and comments tool tests.
- Package/release behavior: inspect `package.json`, lockfile, publish workflow, README/changelog, and run build/test/pack verification.
- Harness/rules work: inspect `AGENTS.md`, `CLAUDE.md`, `docs/agent-memory/README.md`, `docs/agent-memory/harness-security.md`, `docs/agent-memory/harness-eval.md`, relevant memory files, templates, hook scripts, and context budget impact.
- External research-dependent work: create a note from `docs/templates/research-note.md` under `docs/research/` when external facts materially affect the decision.
- Release/install/client QA work: create a checklist from `docs/templates/qa-checklist.md` under `docs/qa/` when public install, credential, stdio, package, or client behavior is affected.
