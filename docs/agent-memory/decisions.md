# Decisions

## 2026-07-26

- Decision: Add one bounded `search_bilibili_videos` Video Discovery entry before danmaku, creator navigation, or collection search.
- Reason: The current evidence tools are deep only after a BVID is known. A video-only first-page candidate list closes that user-journey gap without turning the server into a broad Bilibili API wrapper or automatically crawling candidate evidence.
- Evidence: User-confirmed `grill-with-docs` session, `docs/bilibili-video-search-prd.md`, first-party search contract research, and GitHub Issue #21.

- Decision: Require a configured and actively logged-in local Bilibili credential before Video Discovery, with no anonymous or webpage fallback.
- Reason: The current endpoint permits anonymous requests, but the user chose consistent authenticated behavior and existing bilingual credential recovery over silent access-mode changes; credential values remain local and are never returned.
- Evidence: User-confirmed requirements and `docs/research/2026-07-26-bilibili-video-search-contract.md`.

- Decision: Keep the first Video Discovery contract to a required query, a default-five/maximum-ten candidate limit, Bilibili comprehensive order, and identical structured/text output.
- Reason: Candidate metadata is sufficient to feed existing evidence tools. Pagination, filters, re-ranking, automatic transcript/comment retrieval, and non-Video search would add requests and product surface before the entry workflow is proven.
- Evidence: User-confirmed requirements, PRD, and GitHub Issue #21.

- Decision: Add browser evidence links only to `get_video_transcript`: require a Part-aware `source_url` on successful results and a `timestamp_url` on each returned search match.
- Reason: Transcript results already contain the validated BVID, resolved Part, and match start time, so both links can be derived locally with zero new Bilibili requests while keeping a single canonical source and exact evidence moment.
- Evidence: `docs/transcript-evidence-links-prd.md`, `docs/research/2026-07-26-bilibili-timestamp-link-contract.md`, GitHub Issue #17, and live ordinary/multi-Part Playwright acceptance.

## 2026-07-25

- Decision: Keep `@xzxzzx/bilibili-mcp` Bilibili-native instead of expanding this repository into a cross-platform video MCP.
- Reason: Generic platform adapters trade away Bilibili-specific depth while adding downloader, Cookie, anti-bot, ASR, privacy, and maintenance costs; this project's durable value is evidence grounded in Bilibili Videos, Parts, Chapters, subtitles, comments, and future Bilibili-native timeline signals.
- Evidence: User confirmation during the `ask-matt` / `grill-with-docs` direction session and `docs/research/2026-07-25-cross-platform-video-content-mcp-landscape.md`.

- Decision: Make a backward-compatible structured-evidence pilot for `get_video_transcript` the next development ticket before adding Bilibili search or changing the other seven tools.
- Reason: The existing transcript path already has source, Part, time-range, match-count, and truncation data, so it can validate `outputSchema` and `structuredContent` without a new Bilibili endpoint or a broad migration.
- Evidence: User confirmation during the `ask-matt` / `grill-with-docs` direction session and the Phase A recommendation in `docs/research/2026-07-25-cross-platform-video-content-mcp-landscape.md`.

- Decision: Keep the structured-output pilot payload-identical to the existing `VideoTranscriptData`; add only an accurate `outputSchema` and the same object as `structuredContent`, while preserving `content[].text` unchanged.
- Reason: This isolates MCP protocol compatibility from product behavior and avoids mixing unverified timestamp links, cursors, confidence fields, or new inputs into the pilot.
- Evidence: User confirmation during the `ask-matt` / `grill-with-docs` direction session.

- Decision: Accept the structured-output pilot with automated tests, build, stdio `tools/list` / `tools/call` smoke, and one real Codex-client call; record Claude Desktop and Cursor as untested rather than blocking the pilot.
- Reason: The change exists to validate real MCP client compatibility, but testing every documented client would add disproportionate work before the single-tool pilot proves useful.
- Evidence: User confirmation during the `ask-matt` / `grill-with-docs` direction session.

## 2026-07-20

- Decision: Implement keyword search as a backward-compatible extension of `get_video_transcript` rather than a new MCP tool.
- Reason: Reuses existing subtitle/cache/request paths; tool count stays at eight; no new endpoint or dependency.
- Evidence: `docs/transcript-keyword-search-prd.md`, implementation handoff at `docs/agent-memory/handoffs/2026-07-20-transcript-keyword-search-codex-to-claude.md`.

- Decision: Use case-insensitive literal matching only; no fuzzy, semantic, or regex search in the first version.
- Reason: Keeps implementation simple and predictable; literal matching covers the most common "where did they talk about X" use case without adding a search library.
- Evidence: PRD out-of-scope section and `searchTranscript` in `src/bilibili/subtitle.ts`.

- Decision: Return `transcript` in search mode as a compact concatenation of returned context segments, not the full transcript.
- Reason: The whole point of keyword search is to reduce context-token usage; returning the full transcript would defeat the purpose.
- Evidence: PRD success metrics and the `compactTranscript` assembly in `searchTranscript`.

## 2026-05-27

- Decision: Complete the stabilization roadmap before splitting `src/bilibili/client.ts` or adding new MCP tools.
- Reason: Security, package metadata, tests, and publish contents are higher-risk foundations.
- Evidence: `docs/superpowers/plans/2026-05-27-stabilization-roadmap.md`.

- Decision: Use Vitest for the minimal real test baseline.
- Reason: It handles TypeScript ESM tests cleanly and matches the installed `vitest` skill.
- Evidence: Stabilization roadmap Task 4 and installed Claude Code skill at `C:\Users\ZX\.claude\skills\vitest`.

- Decision: Start with repository-local memory files and a project memory skill, not ECC-style automatic hooks.
- Reason: The repository is still in stabilization, and hooks would change Claude Code runtime behavior.
- Evidence: `docs/superpowers/specs/2026-05-27-agent-memory-learning-system-design.md`.

## 2026-05-28

- Decision: Enable project-local hooks for Claude Code and Codex app after explicit user approval.
- Reason: The first memory-system phase is in place, and hooks can now improve startup context and failure capture without auto-promoting formal memory.
- Evidence: `docs/superpowers/specs/2026-05-28-agent-hooks-design.md`, `.claude/settings.local.json`, and `.codex/hooks.json`.

- Decision: Keep hook runtime observations separate from formal memory.
- Reason: Failed command records are useful review candidates but are too noisy to write directly into `docs/agent-memory/`.
- Evidence: `.codex/scripts/post_tool_use.py` writes observations and candidates only to runtime memory paths.

- Decision: Add only the lightweight ECC-inspired upgrades: PreCompact checkpointing, candidate scoring, context budget auditing, and strategic compact reminders.
- Reason: These improve continuity and review quality without installing the full ECC plugin, broad rules, or automatic skill evolution.
- Evidence: `.codex/scripts/pre_compact.py`, `.codex/scripts/context_budget.py`, `.codex/scripts/post_tool_use.py`, and `.codex/scripts/stop_summary.py`.

- Decision: Automate controlled learning by generating pending learning proposals, not by directly mutating formal memory.
- Reason: This preserves review control while reducing manual candidate triage work.
- Evidence: `.codex/scripts/generate_learning_proposals.py` and `docs/agent-memory/pending-learning-proposals.md`.

- Decision: Add a small Claude Code project subagent set adapted from ECC instead of copying the full ECC agent library.
- Reason: The stabilization roadmap needs focused execution and verification helpers, while the full ECC agent set would add unnecessary context and workflow surface area.
- Evidence: `.claude/agents/credential-sanitizer.md`, `.claude/agents/package-maintainer.md`, `.claude/agents/test-baseline-builder.md`, `.claude/agents/build-error-resolver.md`, `.claude/agents/risk-reviewer.md`, and `.claude/agents/release-verifier.md`.

- Decision: Add a smaller Codex custom agent set for planning, risk review, and release verification.
- Reason: Codex owns direction and review in the project workflow, so its agents should support decisions and verification rather than duplicate Claude Code's execution agents.
- Evidence: `.codex/agents/stabilization-reviewer.toml`, `.codex/agents/risk-reviewer.toml`, and `.codex/agents/release-verifier.toml`.

- Decision: Fold selected GitHub subagent patterns into the existing project agents instead of adding more agents.
- Reason: The roadmap benefits from AAA testing, systematic debugging, package risk checks, MCP compatibility review, and release gates, but adding more full-size agents would increase context and orchestration cost.
- Evidence: `.claude/agents/test-baseline-builder.md`, `.claude/agents/build-error-resolver.md`, `.claude/agents/package-maintainer.md`, `.codex/agents/risk-reviewer.toml`, and `.codex/agents/release-verifier.toml`.

- Decision: Add explicit capability invocation rules for skills, MCP/tool connectors, and subagents.
- Reason: The user observed inconsistent Codex and Claude Code use of skills, MCP tools, and subagents; repository instructions should require agents to check, invoke, name, or intentionally skip relevant capabilities instead of relying on implicit behavior.
- Evidence: `AGENTS.md` Capability Invocation Rules and `CLAUDE.md` Capability Invocation Rules.

- Decision: Keep hook stdout JSON-safe for Claude Code command hooks that write files.
- Reason: Claude Code reported `Stop hook error: JSON validation failed`; write-file hooks should avoid ordinary stdout and emit a minimal JSON control object instead.
- Evidence: `.codex/scripts/stop_summary.py`, `.codex/scripts/generate_learning_proposals.py`, `.codex/scripts/post_tool_use.py`, and `.codex/scripts/pre_compact.py` now print `{"suppressOutput": true}` after writing their artifacts.

- Decision: Use a compatibility-first staged split for Phase 2 `src/bilibili/client.ts` refactoring.
- Reason: Subtitle retrieval depends on WBI, Cookie headers, buvid fallback, and `/x/player/v2` fallback behavior; tests should pin this behavior before moving code.
- Evidence: `docs/superpowers/specs/2026-05-28-bilibili-client-split-design.md` and `docs/superpowers/plans/2026-05-28-bilibili-client-split-implementation-plan.md`.

- Decision: Plan Phase 3 as an additive MCP tool surface expansion, not a breaking replacement of existing tools.
- Reason: Existing MCP clients may already depend on `get_video_info` and `get_video_comments`; transcript, metadata, and explicit comment controls can be added without breaking those callers.
- Evidence: `docs/superpowers/specs/2026-05-28-mcp-tool-surface-design.md` and `docs/superpowers/plans/2026-05-28-mcp-tool-surface-implementation-plan.md`.

- Decision: Plan Phase 4 as a documentation and release-gate phase, with GitHub Actions/npm publish behavior verified against official docs at implementation time.
- Reason: npm trusted publishing, provenance, Node, and npm CLI requirements can change; release workflow should be documentation-backed and should not restore Smithery or introduce tokens by default.
- Evidence: `docs/superpowers/specs/2026-05-28-documentation-release-polish-design.md` and `docs/superpowers/plans/2026-05-28-documentation-release-polish-implementation-plan.md`.

- Decision: Make controlled-learning reminders automatically track the current incomplete implementation plan instead of hard-coding the original stabilization roadmap.
- Reason: After Phase 2, phase-gated learning reminders still pointed at the completed stabilization plan, so Phase 3/4 work would not trigger review reminders correctly.
- Evidence: `.codex/scripts/plan_tracker.py`, `.codex/scripts/generate_learning_proposals.py`, `.codex/scripts/pre_compact.py`, and `.codex/scripts/session-start.ps1`.

## 2026-06-05

- Decision: Add credential setup guidance as explicit MCP tools plus actionable error `next_steps`, rather than relying only on README install instructions.
- Reason: Most users install MCP servers through agents; the installing agent needs a machine-discoverable way to tell the user how to configure Cookies after registration.
- Evidence: `get_credential_setup_instructions`, `check_bilibili_credentials`, `buildCredentialNextSteps()`, and the `COOKIE_EXPIRED` / `SUBTITLE_UNAVAILABLE` response paths in `src/server.ts`.

- Decision: Keep Cookie values out of MCP client configuration examples and guide users to `npx -y @xzxzzx/bilibili-mcp config` followed by `npx -y @xzxzzx/bilibili-mcp check`.
- Reason: MCP client config files are easy to share or commit accidentally; the project already has a safer credential helper and global credential flow.
- Evidence: README credential notes, `buildCredentialSetupInstructions()`, and secret-oriented regression tests in `tests/credential-guidance.test.ts`.

- Decision: Treat generated learning proposal files as review queues and Python bytecode caches as ignored local artifacts.
- Reason: `pending-learning-proposals.md` is meaningful project state only as a generated queue, while `__pycache__` contains no durable learning.
- Evidence: `docs/agent-memory/README.md` controlled-learning section and `.gitignore` entries for `__pycache__/` and `*.py[cod]`.

## 2026-06-14

- Decision: Add fixed invocation triggers for recurring Codex and Claude Code project work.
- Reason: The user wants predictable skill and subagent use in stable scenarios instead of ad hoc capability selection.
- Evidence: `AGENTS.md` and `CLAUDE.md` now define fixed triggers for tests, credentials/secrets, build failures, package maintenance, release verification, GitHub Actions, Git workflows, risk review, and project memory updates.

- Decision: Add fixed MCP/tool connector triggers for recurring remote-state, documentation, registry, and local MCP verification work.
- Reason: The user wants Codex and Claude Code to consistently verify live external state and current docs in stable scenarios instead of relying on memory.
- Evidence: `AGENTS.md` and `CLAUDE.md` now define fixed MCP/tool triggers for live GitHub state, failing Actions checks, GitHub Actions/npm publishing docs, OpenAI/Codex/MCP SDK docs, npm registry metadata, local MCP server behavior, remote owner/name changes, and explicitly requested external app workflows.

- Decision: Add fixed CLI triggers and CLI-vs-MCP boundaries for recurring repository work.
- Reason: The user wants Codex and Claude Code to consistently choose CLI for local authoritative facts and MCP/connectors for live platform or structured external workflows.
- Evidence: `AGENTS.md` and `CLAUDE.md` now define CLI triggers for local git facts, local file/code inspection, npm/node/tsc/vitest verification, npm registry metadata, quick GitHub checks through `gh`, project hook health scripts, MCP package credential smoke tests, and external service CLIs only when explicitly in scope.

- Decision: Plan the next optimization cycle as six separate phases instead of one broad refactor.
- Reason: Package health, logging, MCP handler structure, type/cache hardening, encoding cleanup, and MCP integration tests have different risks and verification gates.
- Evidence: `docs/superpowers/plans/2026-06-14-project-optimization-roadmap.md` defines one independently verifiable task per optimization direction, with capability triggers, commands, acceptance gates, and rollback points.

- Decision: Use Markdown files as the default Codex-to-Claude communication channel for substantial implementation work.
- Reason: The user wants Codex and Claude Code to coordinate through durable Markdown artifacts instead of relying on transient chat context.
- Evidence: `docs/agent-memory/agent-communication.md` defines the handoff/report protocol and templates; `AGENTS.md` and `CLAUDE.md` require file-backed handoffs for release, package, credential, MCP tool, and multi-file implementation work.

- Decision: Do not name DeepSeek V4 as the fixed Claude Code execution model.
- Reason: The user clarified that Claude Code may no longer be using DeepSeek V4, and the concrete model can change by user choice or runtime configuration.
- Evidence: `AGENTS.md` and older planning prompts were updated to describe Claude Code as the implementation tool without hard-coding a model.

## 2026-06-18

- Decision: Sync `domain-modeling` and `codebase-design` to both Codex and Claude Code, with narrow fixed triggers.
- Reason: These skills complement the existing release, security, test, package, and Git workflows only when terminology, durable decisions, module interfaces, seams, adapters, testability structure, or non-trivial refactors are actually in scope.
- Evidence: `AGENTS.md` and `CLAUDE.md` now define when these skills must be used and when they should not be invoked.

- Decision: Add narrow fixed triggers for `product-requirements` and `system-design`.
- Reason: New user-facing features and ambiguous MCP tool behavior need requirements clarification before implementation, while broad cross-module architecture changes need system design; neither should run for routine scoped fixes.
- Evidence: `AGENTS.md` and `CLAUDE.md` now require `product-requirements` for unclear/new feature scope and `system-design` for broad architecture work only.

- Decision: Add explicit `codex-security` security-scan triggers alongside the existing secret-scanning and project risk-review rules.
- Reason: Credential scanning, project risk review, and Codex Security cover different layers; repository-wide MCP security scans, attack-path analysis, security diff review, validation, and validated finding fixes should use the dedicated Codex Security skills when available.
- Evidence: `AGENTS.md` and `CLAUDE.md` now define when to use `codex-security` and how Claude Code should fall back when that runtime does not expose the skill.

- Decision: Treat `docs/agent-memory/codemap.md` as a structural navigation artifact that must be checked after relevant code or harness changes.
- Reason: Codex and Claude Code need a durable, low-cost map of runtime entry points, MCP tool flow, tests, release files, and harness files; stale navigation causes repeated exploration and weaker handoffs.
- Evidence: `AGENTS.md` and `CLAUDE.md` now require updating the codemap when structural changes would make it stale, or explicitly reporting that it was checked and left unchanged.

- Decision: Add `docs/templates/task-ticket.md` as an optional execution-ticket template.
- Reason: Roadmaps and PRDs sometimes need smaller independently executable tickets with dependencies, acceptance criteria, verification gates, capability triggers, and stop/report conditions, but small already-scoped fixes should still use a direct Codex handoff.
- Evidence: `docs/templates/task-ticket.md` defines the template; `AGENTS.md` and `CLAUDE.md` define when Codex and Claude Code should use it.

- Decision: Use a three-tier standard for task tickets.
- Reason: The user wants task tickets available for consistency without turning small scoped fixes into unnecessary paperwork.
- Evidence: `AGENTS.md`, `CLAUDE.md`, and `docs/templates/task-ticket.md` now define: no ticket for <=30 minute tasks without public behavior change; use a ticket for multi-file, test, security, package/release, or MCP tool work; require a ticket for PRD, roadmap, multi-task split, or Claude Code loop work.

- Decision: Add a research-note template and `docs/research/` cache for external facts.
- Reason: External documentation, SDK/API behavior, third-party repositories, npm/GitHub release behavior, and security guidance can drift; material findings should be cached with sources and staleness conditions instead of being buried in chat.
- Evidence: `docs/templates/research-note.md`, `docs/research/README.md`, `AGENTS.md`, and `CLAUDE.md` now define when to create research notes and when local worktree facts should be verified directly instead.

- Decision: Add an optional QA checklist template for real user workflow validation.
- Reason: Automated build, tests, pack, and security checks do not fully cover MCP client installation, stdio cleanliness, credential states, README install accuracy, npm latest behavior, or post-release client smoke checks.
- Evidence: `docs/templates/qa-checklist.md`, `docs/qa/README.md`, `AGENTS.md`, and `CLAUDE.md` now define when QA checklists should be used and when they are unnecessary.

- Decision: Add `docs/agent-memory/harness-security.md` as the security baseline for the agent harness.
- Reason: The repository now contains rules, hooks, skills, subagents, generated learning queues, handoffs, templates, research notes, and QA notes that can influence agent behavior; these surfaces need explicit trust-boundary, no-secret, and review rules.
- Evidence: `docs/agent-memory/harness-security.md`, `docs/agent-memory/README.md`, `AGENTS.md`, and `CLAUDE.md` now define when harness security review applies.

- Decision: Add `docs/agent-memory/harness-eval.md` for periodic evaluation of the agent workflow.
- Reason: The harness now includes multiple rules, skills, subagents, hooks, templates, memory files, handoffs, research notes, and QA notes; the project needs a way to decide which parts reduce risk or repeated work and which parts add unnecessary overhead.
- Evidence: `docs/agent-memory/harness-eval.md`, `docs/agent-memory/README.md`, `AGENTS.md`, and `CLAUDE.md` now define when workflow evaluation should happen.

- Decision: Add non-mutating Stop hook reminders for harness artifacts.
- Reason: Codemap, harness-security, and harness-eval require contextual judgment and should not be auto-edited by hooks, but lightweight path-based reminders can reduce missed checks after relevant code or harness changes.
- Evidence: `.codex/scripts/stop_summary.py` now adds stop-summary reminders based on `git status --short` path patterns while preserving JSON-safe stdout and avoiding automatic artifact mutation.

- Decision: Require Claude reports to include explicit harness artifact status.
- Reason: Hooks can only provide path-based reminders; the executing agent must make the contextual judgment about whether task tickets, research notes, QA checklists, codemap updates, harness-security review, or harness-eval apply.
- Evidence: `docs/agent-memory/agent-communication.md`, `CLAUDE.md`, and `AGENTS.md` now require a `Harness Artifacts` section in Claude reports.

## 2026-07-19

- Decision: Use the installed `mattpocock/skills` collection as the feature-development workflow and do not invoke Superpowers skills.
- Reason: Matt's discovery, specification, dependency-aware ticketing, implementation, diagnosis, and review flow fits the existing manual Codex-to-Claude model when project-specific safeguards remain authoritative.
- Evidence: `AGENTS.md`, `CLAUDE.md`, and `docs/agents/` define the routing and repository setup.

- Decision: Store Matt specifications and tickets in GitHub Issues while keeping file-backed Codex-to-Claude handoffs as execution contracts.
- Reason: Issues provide durable dependencies and triage state; handoffs carry repository-specific file scope, verification, rollback, security, and stop conditions without duplicating a second local ticket.
- Evidence: `docs/agents/issue-tracker.md` and `docs/agent-memory/agent-communication.md`.

- Decision: Repository Git authorization overrides the upstream `implement` skill's default commit step.
- Reason: This project only commits, pushes, or opens pull requests after explicit user authorization.
- Evidence: Matt workflow sections in `AGENTS.md` and `CLAUDE.md`.

- Decision: Remove historical Superpowers plans from active runtime context without deleting the historical files.
- Reason: The user explicitly chose not to use Superpowers; startup, plan tracking, pre-compact checkpoints, learning-state pointers, and context-budget accounting must not treat old Superpowers artifacts as current work.
- Evidence: `docs/agent-memory/active-work.md`, `.codex/scripts/plan_tracker.py`, `session-start.ps1`, `pre_compact.py`, `generate_learning_proposals.py`, and `context_budget.py`.

- Decision: Let Codex drive Claude Code through the Paseo CLI instead of requiring manual user orchestration.
- Reason: The user wants the existing Codex-decides, Claude-implements split without manually moving prompts or supervising Claude Code.
- Evidence: `AGENTS.md`, `CLAUDE.md`, `docs/agent-memory/agent-communication.md`, and the live Paseo orchestration preference file.

- Decision: Limit default Paseo execution to one bounded Claude Code implementation agent and preserve all existing scope, security, verification, and Git authorization gates.
- Reason: Paseo should remove handoff friction without introducing autonomous teams, concurrent overlapping edits, hard-coded models, or broader mutation authority.
- Evidence: Paseo execution rules in `AGENTS.md` and `docs/agent-memory/agent-communication.md`.

## 2026-07-20

- Decision: Keep Part discovery in `get_video_metadata`, Part selection on transcript/video-info/Chapters, and Chapter retrieval as a dedicated eighth tool.
- Reason: This keeps existing defaults compatible, avoids automatic whole-series crawling, and makes the one extra player request explicit only for Chapter calls.
- Evidence: `docs/adr/0001-navigable-transcript-interface.md`, `docs/navigable-transcript-prd.md`, and the accepted implementation in `src/bilibili/navigation.ts`, `subtitle.ts`, `metadata.ts`, and `chapters.ts`.

- Decision: Preserve the top-level video CID when no page is supplied and centralize page-to-CID validation in the shared navigation module.
- Reason: Existing callers must retain the prior default Part, while explicit out-of-range pages need a structured validation error before any player/subtitle request.
- Evidence: `resolvePartCid`, request-count/navigation regressions, and the MCP handler validation regression.

## 2026-07-26

- Decision: Refresh body-parser and fast-uri inside their existing compatible ranges, but do not override the MCP SDK's Hono 1.x dependency with Hono 2.
- Reason: The compatible refresh clears three advisories without changing declarations or runtime support. Hono 2 fixes the remaining advisory but requires Node 20; the project supports Node 18 and does not import the vulnerable `serveStatic` path.
- Evidence: GitHub Issue #19, official npm metadata, upstream MCP SDK Issues #2531/#2548, Node 18 official SDK stdio acceptance, and `docs/research/2026-07-26-v1.8.0-production-dependency-advisory-triage.md`.

- Decision: Use `docs/client-setup.md` and `docs/client-setup.en.md` as the single complete source for end-user installation and configuration; the READMEs only provide prominent entry links.
- Reason: Keeping Agent prompts, client-specific syntax, credential setup, validation, and runtime settings in one guide prevents drift while preserving a concise project homepage.
- Evidence: The user explicitly selected this information architecture; the bilingual READMEs and client setup guides implement it.

## 2026-07-27

- Decision: Keep Issue #22 limited to read-only Favorites discovery and membership traversal.
- Reason: The user only needs the MCP to expose all saved videos and their Folder context; once BVIDs are available, users or Agents can call existing subtitle/evidence tools and process the results however they choose.
- Evidence: GitHub Issue #22, `docs/bilibili-favorites-discovery-prd.md`, and the accepted tool schema. There is no note generation, AI summarization, RAG, download, persistence, cache, or write operation.

- Decision: Start Favorites discovery from the current authenticated identity, enumerate all created Folders automatically, and expose one fixed upstream page per stateless cursor call.
- Reason: This removes the need for users to know Folder IDs while respecting Bilibili's observed 20-row resource-page limit and keeping each MCP call bounded.
- Evidence: The nav → created/list-all → optional resource/list flow, exact request-count tests, and redacted official SDK continuation acceptance.

- Decision: Preserve Favorite Membership rather than globally deduplicating BVIDs, and document traversal as live-state best effort rather than a snapshot.
- Reason: The same Video can be intentionally saved in multiple Folders; Folder context is meaningful, while concurrent account changes can legitimately alter later pages.
- Evidence: The two-Folder duplicate-BVID regression and bilingual tool-reference semantics.

- Decision: Split CLI onboarding into human-facing `setup` and Agent-facing `doctor --json`.
- Reason: Cookie entry must remain hidden and interactive, while automation needs a deterministic, local-only, secret-free status surface. A redundant non-interactive setup mode would duplicate doctor without safely configuring credentials.
- Evidence: `src/cli.ts`, the frozen CLI task ticket, bilingual setup guides, and 30 focused CLI/entrypoint tests.

- Decision: Keep ASR runtime and model installation outside this CLI refactor.
- Reason: The current task establishes a reliable installer-facing command seam first; model selection, downloads, transcription runtime, and MCP fallback behavior require their own bounded architecture and acceptance contract.
- Evidence: `docs/agent-memory/handoffs/2026-07-27-cli-setup-doctor-task-ticket.md` and its completed verification.

- Decision: Let the bilingual READMEs carry the minimum universal install-and-verification path while keeping exhaustive client-specific configuration in the canonical setup guides.
- Reason: Both Agent-assisted and manual users need a visible first-success path on the homepage, but duplicating 30-plus client configurations would recreate documentation drift. The homepage therefore contains the Node.js 20+ prerequisite, stdio launch baseline, local `setup`/`check`/`doctor` gates, reconnect step, and live-login check only.
- Evidence: `README.md`, `README_EN.md`, `docs/client-setup.md`, `docs/client-setup.en.md`, and the completed README redesign task ticket.

- Decision: Use paired, hand-authored static SVGs for the README installation flow instead of generated raster artwork.
- Reason: The flow is procedural UI documentation whose text must stay bilingual, versionable, accessible, GitHub-safe, and readable at both 900px and 360px.
- Evidence: `assets/readme/install-flow.svg`, `assets/readme/install-flow-en.svg`, and the independent render review.

- Decision: Treat Agent-assisted installation and human manual installation as two independently complete README paths.
- Reason: An Agent needs a copyable, credential-safe execution contract with explicit stop-and-handoff points, while a person needs an end-to-end path that includes Node verification, MCP client configuration, browser credential-field discovery, local hidden input, reconnection, and live login validation.
- Evidence: `README.md`, `README_EN.md`, `docs/client-setup.md`, `docs/client-setup.en.md`, and the user-comprehension acceptance addendum in the README task ticket.

- Decision: Order the landing-page story as project definition → core capabilities → prominent use cases → installation → tool detail.
- Reason: A specific Favorites workflow is useful proof but cannot explain the whole package; first-time visitors need the broad product boundary before deciding whether an example or installation path matters to them.
- Evidence: The user's information-architecture correction, the `beautify-github-readme` first-screen test, and the completed information-architecture addendum in the README task ticket.

- Decision: Introduce ASR in phases, beginning with a default-off fixed `faster-whisper-small` installer inside the existing `setup` command.
- Reason: A single recommended path keeps the first installation experience understandable while establishing the managed Python environment, pinned model revision, readiness state, and local diagnostics needed by a later selector and transcription fallback.
- Evidence: `docs/asr-model-install-prd.md`, `src/asr/installer.ts`, `src/asr/state.ts`, and `docs/qa/2026-07-27-asr-model-install-phase1.md`.

- Decision: Keep ASR files in the user's `~/.bilibili-mcp/asr/` directory, use a managed virtual environment, verify the model through CPU INT8 loading before recording `ready`, and treat ASR doctor status as informational.
- Reason: The package must not mutate global Python, package model weights into npm, trust a stale marker, or make optional ASR change existing credential exit-code semantics.
- Evidence: The Phase 1 task ticket, installer/state tests, built CLI probes, and independent final-diff review.

- Decision: Limit the Phase 2 ASR selector to pinned multilingual `tiny`, `base`, and `small` models, default Enter to recommended `small`, and retain only one active model in the existing managed directory.
- Reason: Three bounded choices expose useful storage and CPU tradeoffs without accepting arbitrary remote repositories, adding model-management commands, migrating the state schema, or complicating the first-run path. The one-active-model rule reuses the Phase 1 layout until retaining several models becomes a demonstrated need.
- Evidence: `docs/asr-model-selector-prd.md`, the literal allowlist in `src/asr/state.ts`, selector and switch regressions, and `docs/qa/2026-07-27-asr-model-selector-phase2.md`.

- Decision: Keep persisted ASR state at version 1 and derive the public model key from the exact pinned repository/revision pair.
- Reason: Phase 1 already persisted enough information to identify `small`; deriving the key preserves compatibility and prevents a second source of truth while allowing `doctor --json` to report `tiny`, `base`, `small`, or `null`.
- Evidence: `readAsrState`, `modelKeyForRepo`, Phase 1 compatibility tests, cross-pair rejection tests, and built doctor output.

## 2026-07-29

- Decision: Treat MCP `2026-07-28` and TypeScript SDK v2 support as a future, independent compatibility initiative after the current ASR and CLI work reaches a stable boundary.
- Reason: The existing ten-tool stdio server remains usable and already adopts the `2025-06-18` structured-output pattern where it provides clear value. The 2026 protocol changes are cross-cutting and should not be approximated by adding isolated fields to the SDK v1 implementation.
- Evidence: `docs/research/2026-07-29-mcp-protocol-update.md`, `docs/research/2026-07-29-mcp-tools-evolution.md`, and the 2026-07-29 entries in `docs/agent-memory/project-facts.md`.

- Decision: Make a real wire-level stdio compatibility test the first step of future MCP modernization, then freeze a dual-era acceptance matrix before changing the SDK or server architecture.
- Reason: Current tests call SDK-private `_requestHandlers`; validating the public legacy flow (`initialize` → `tools/list` → `tools/call`) is the smallest reusable safety net and provides a baseline for later `server/discover` plus legacy-fallback verification.
- Evidence: `tests/helpers/mcp.ts`, `tests/mcp-server-smoke.test.ts`, and the local tool-surface audit summarized in `docs/research/2026-07-29-mcp-tools-evolution.md`.

- Decision: Add tool annotations, titles, icons, more structured-output schemas, Tasks, MRTR, or HTTP-specific `x-mcp-header` only when a concrete product or client requirement appears.
- Reason: These optional metadata and extension capabilities do not repair a current defect. Tasks and MRTR do not match the present bounded read-only tool calls, and `x-mcp-header` does not apply to the current stdio-only transport.
- Evidence: The applicability and decision-impact sections of `docs/research/2026-07-29-mcp-tools-evolution.md`.

- Decision: Add ASR only as explicit `fallback_to_asr` on `get_video_transcript`, default it to `false`, keep native subtitles first, and trigger it only after a definite empty/unsuitable subtitle result.
- Reason: ASR changes latency, CPU cost, and media handling. Credential, HTTP, timeout, parse, or anti-bot errors must remain distinguishable from legitimate subtitle absence, and `get_video_info` must stay free of hidden heavy work.
- Evidence: Phase 3 PRD, transcript gating tests, schema/order tests, and public wire-level stdio test.

- Decision: Run Phase 3 through the already-ready managed venv/model with CPU INT8, one resolved Part/CID, one active job and no queue, unique OS temp storage, strict bounded NDJSON, and no runtime model install or switch.
- Reason: This keeps expensive work opt-in and deterministic, preserves the Phase 1/2 trust boundary, prevents uncontrolled CPU/memory/disk use, and makes every cleanup target locally provable.
- Evidence: `src/asr/transcription.ts`, playback/runtime/cleanup/concurrency tests, and post-test zero-residue verification.

- Decision: Accept only provider-specific Bilibili audio CDN host suffixes and distinguish a missing/malformed DASH object from a valid explicit empty audio array.
- Reason: Generic CDN ownership assumptions are too broad, while treating malformed responses as empty would silently convert upstream errors into fallback behavior.
- Evidence: `src/bilibili/playback.ts`, risk review findings, and malformed-versus-empty playback tests.

## 2026-07-30

- Decision: Close the 38 scan findings through shared, fixed process-local
  security budgets instead of adding caller-configurable security limits.
- Reason: stdio framing, successful serialization, outbound HTTP, bootstrap
  concurrency, caches, logs, and ASR resource ceilings are containment
  invariants. Letting an MCP caller raise them would recreate the original
  source-to-sink paths.
- Evidence: `src/security/limits.ts`, bounded transport/response/HTTP/cache/log
  implementations, and the 38-row remediation matrix.

- Decision: A cancelling MCP caller stops its own Bilibili/ASR operation, while
  one caller cancelling a shared fingerprint, WBI, or update refresh does not
  abort work still needed by other bounded waiters.
- Reason: cancellation must release expensive per-call resources without
  allowing one waiter to poison a process-owned single-flight refresh.
- Evidence: `src/security/operation-context.ts`,
  `tests/bootstrap-single-flight.test.ts`, HTTP cancellation tests, MCP signal
  propagation tests, and ASR download/runtime cancellation tests.

- Decision: Resolve playback media through provider-specific HTTPS allowlists,
  validate every DNS answer as public, pin one approved address at connection
  time, retain the original hostname for TLS, and strip credential-bearing
  headers at the final sink.
- Reason: hostname string validation alone is insufficient against DNS rebinding
  or mixed public/private answers, and signed CDN URLs must never inherit the
  first-party Cookie.
- Evidence: `src/security/pinned-https.ts` and
  `tests/pinned-https.test.ts`.

- Decision: Pin publish Actions to the currently verified full commit SHAs,
  while leaving the package version, dependency graph, and release state
  unchanged.
- Reason: immutable workflow execution closes the validated supply-chain
  finding without broadening remediation into a release or dependency update.
- Evidence: `.github/workflows/publish.yml`,
  `tests/publish-workflow-pins.test.ts`, and official GitHub ref resolution
  cached in the 2026-07-30 research note.

- Decision: Keep the Hono advisory as a named residual rather than upgrading
  the MCP SDK inside this remediation or calling the audit clean.
- Reason: current imports do not reach the SDK Streamable HTTP/static-file
  module, but changing the SDK/lockfile is a separate compatibility and release
  decision.
- Evidence:
  `docs/research/2026-07-30-security-remediation-dependency-and-action-pins.md`.

- Decision: Honor the user's direct-Codex executor choice for all remediation
  edits and validation; do not invoke Paseo.
- Reason: executor selection was explicit and does not weaken the frozen task,
  test, security, Git, or release boundaries.
- Evidence:
  `docs/agent-memory/handoffs/2026-07-30-deep-security-remediation-task-ticket.md`.

## 2026-08-05

- Decision: Execute the validated Strix follow-up security fixes through one
  Paseo-managed Claude Code implementation agent using the live
  `providers.impl` preference, then require Codex to review the report, diff,
  and verification evidence.
- Reason: The user explicitly changed the executor choice for this new
  follow-up task and asked Codex to operate Claude Code through Paseo. This
  supersedes only the 2026-07-30 task-specific direct-Codex choice and preserves
  the single-agent, frozen-scope, no-Git-action model.
- Evidence:
  `docs/agent-memory/handoffs/2026-08-05-strix-deepseek-security-remediation-task-ticket.md`,
  the matching Codex-to-Claude handoff, and the live Paseo preference resolving
  `providers.impl` to `claude/deepseek-v4-flash`.

## 2026-08-06

- Decision: Use the exact GitHub-owner casing
  `io.github.XZXZZX-Ai/bilibili-mcp` in both `package.json.mcpName` and
  `server.json.name`, and publish the matching npm version before Registry
  metadata.
- Reason: the live v1.11.2 publish attempt with a lowercase namespace returned
  HTTP 403, while the publisher authorization explicitly granted
  `io.github.XZXZZX-Ai/*`.
- Evidence: the v1.11.2 403 response and the successful v1.11.3 publication and
  exact-match Official Registry API response.
