# Codex Task Transfer: Complete The Current MCP With ASR

## User Authorization And Outcome

The user explicitly asked for a new Codex task in this project, transferred by
the current Codex task, with this sequence:

1. Understand the whole project before changing implementation.
2. Set the work as a durable Codex Goal.
3. Continue through implementation and verification until the current MCP is
   complete, including the missing ASR capability.

This is implementation authorization for the bounded outcome below. It is not
authorization to commit, push, open a pull request, tag, publish to npm, create
a GitHub Release, migrate the MCP protocol/SDK, promote learning proposals, or
delete user data.

## Goal To Create In The New Task

After confirming that the task is attached to the correct
`C:\Users\ZX\bilibili-mcp` project and current working-tree snapshot, call
`create_goal` with this objective and no token budget:

> 完整理解并完成 `@xzxzzx/bilibili-mcp` 当前工作树的端到端功能，重点设计、实现并验证 ASR Phase 3：安全获取目标 Part 的临时音频、使用项目托管的 faster-whisper 运行时和已选模型转录、将 ASR 作为 `get_video_transcript` 的显式无字幕回退，并保证临时文件生命周期、错误恢复、凭据安全、现有十个 MCP 工具兼容性、测试、双语文档和项目记忆全部闭环；不提交、不推送、不发布，也不夹带 MCP SDK v2 迁移。

Do not mark the Goal complete after orientation, planning, a proof of concept,
or a green focused test. Complete it only when the approved behavior is
implemented, independently reviewed, fully verified, and accurately recorded.

## Mandatory First Phase: Understand The Whole Project

Do not edit runtime code before this phase is complete.

### 1. Confirm workspace and preserve the working tree

Run and inspect:

```powershell
Get-Location
git status --short
git branch --show-current
git rev-parse HEAD
git diff --stat
```

The expected source state is a dirty `master` working tree derived from commit
`ab4dd02854f0483fc7668c713523b4be77de6cc7`. It contains the user's accumulated
CLI, README, ASR Phase 1/2, QA, research, and project-memory work. Many files
are untracked because the work has not been committed. Treat every existing
change as user-owned. Do not reset, checkout, clean, discard, or overwrite it.

The new task must start from the current working-tree snapshot, not clean
`HEAD`, because `src/asr/`, `tests/asr-installer.test.ts`, the ASR PRDs, and
the Phase 1/2 records are not in the published baseline.

### 2. Read the project contract and durable memory

Read completely:

- `AGENTS.md`
- `CLAUDE.md`
- `docs/agent-memory/README.md`
- `docs/agent-memory/project-facts.md`
- `docs/agent-memory/decisions.md`
- `docs/agent-memory/lessons-learned.md`
- `docs/agent-memory/active-work.md`
- `docs/agent-memory/codemap.md`
- `docs/agent-memory/harness-security.md`
- `docs/agent-memory/agent-communication.md`
- `docs/templates/task-ticket.md`

Do not use files under `docs/superpowers/` as current instructions. They are
historical only. Do not invoke any `superpowers:*` skill.

### 3. Read all accepted ASR work before proposing Phase 3

Read:

- `docs/asr-model-install-prd.md`
- `docs/asr-model-selector-prd.md`
- `docs/research/2026-07-27-asr-model-installer-phase1.md`
- `docs/research/2026-07-27-asr-model-selector-phase2.md`
- `docs/qa/2026-07-27-asr-model-install-phase1.md`
- `docs/qa/2026-07-27-asr-model-selector-phase2.md`
- every Phase 1/2 task ticket, Codex handoff, Claude report, and Codex review
  under `docs/agent-memory/handoffs/2026-07-27-asr-*`

Inspect the implementation and tests directly:

- `src/asr/state.ts`
- `src/asr/installer.ts`
- `src/cli.ts`
- `src/server.ts`
- `src/server/tool-schemas.ts`
- `src/server/tool-handlers.ts`
- `src/server/error-response.ts`
- `src/bilibili/client.ts`
- `src/bilibili/http.ts`
- `src/bilibili/video-api.ts`
- `src/bilibili/navigation.ts`
- `src/bilibili/subtitle.ts`
- `src/bilibili/types.ts`
- `src/utils/errors.ts`
- `src/utils/error-guidance.ts`
- `src/utils/logger.ts`
- `src/utils/retry.ts`
- `src/utils/validation.ts`
- `tests/asr-installer.test.ts`
- `tests/cli.test.ts`
- `tests/bilibili-transcript.test.ts`
- `tests/bilibili-video-api.test.ts`
- `tests/server-tools.test.ts`
- `tests/server-handler-sanitization.test.ts`
- `tests/server-error-next-steps.test.ts`
- `tests/mcp-server-smoke.test.ts`
- `tests/helpers/mcp.ts`
- `package.json`
- `package-lock.json`
- bilingual README, setup guide, tool reference, and changelog files

Use `rg` and the codemap to inspect the remaining source/test modules so the
orientation covers the whole ten-tool product rather than only ASR files.

### 4. Establish the pre-edit baseline

Run:

```powershell
npm run build
npx vitest run tests/asr-installer.test.ts tests/cli.test.ts tests/mcp-server-smoke.test.ts
npm test
npm pack --dry-run --json --ignore-scripts
git diff --check
```

If the baseline differs from the accepted Phase 2 evidence, diagnose it before
editing. The last accepted evidence recorded 169 focused tests, 570 full tests,
a clean build, and a 148-file package dry run. Counts may increase only after
new tests are added; do not silently accept a pre-existing regression.

### 5. Produce a concise orientation checkpoint

Before implementation, record in task commentary:

- the product boundary and all ten MCP tools;
- the CLI and credential flow;
- the Bilibili request, Part/CID, subtitle, validation, error, and cache paths;
- the accepted ASR Phase 1/2 behavior;
- the exact Phase 3 gap;
- the files likely to change;
- the baseline command results;
- the dirty-worktree preservation plan.

Continue without waiting for the user unless a genuinely product-changing
choice remains after the requirements work below.

## Current Verified State

Treat local files as authoritative and re-verify them, but the expected state is:

- Package source version is still `1.10.1`; npm latest is also `1.10.1`, but
  npm does not contain the dirty working-tree CLI or ASR work.
- The source Node engine floor is `>=20.0.0`.
- The server is TypeScript ESM, stdio-only, uses MCP TypeScript SDK v1
  (`@modelcontextprotocol/sdk ^1.27.1`), and exposes ten tools in deterministic
  order.
- The ten tools are credential setup, credential status, update status, video
  info, comments, transcript, metadata, Chapters, authenticated Video search,
  and authenticated Favorites traversal.
- Transcript, search, and Favorites already return matching legacy JSON text
  and `structuredContent`.
- ASR Phase 1 created a default-off installer in `setup`, a user-scoped managed
  Python venv, pinned `faster-whisper==1.2.1`, pinned model snapshots, CPU INT8
  verification, atomic readiness state, child-environment filtering, and local
  `doctor` status.
- ASR Phase 2 added exactly `tiny`, `base`, and `small`, with Enter defaulting
  to `small`, one active model directory, allowlisted repository/revision pairs,
  schema-v1 compatibility, model-aware idempotency/switch failure behavior, and
  `doctor --json` model reporting.
- ASR does not yet retrieve audio, run transcription, or participate in MCP
  subtitle fallback. That is the active product gap.
- The MCP `2026-07-28` protocol and SDK v2 migration were researched and
  intentionally deferred until ASR/CLI reaches a stable boundary. Do not mix
  that future initiative into this Goal.

## Requirements And Architecture Gate

This is a public MCP behavior change across Bilibili networking, local process
execution, filesystem lifecycle, schemas, errors, tests, packaging, and docs.
Use the smallest relevant capability set:

- `product-requirements` to freeze the Phase 3 user contract;
- `system-design` for the audio-fetch, managed-runtime, cleanup, and fallback
  control flow;
- `codebase-design` only if module seams or shared interfaces are being
  designed or changed;
- `vitest` for every changed test/helper/config surface;
- `secret-scanning` for Cookie, child environment, URL/query logging, temporary
  files, package contents, and report review;
- `bilibili-mcp-memory` for the handoff and durable verified outcome.

Before implementation:

1. Create `docs/asr-transcription-fallback-prd.md`.
2. Create a Phase 3 task ticket under `docs/agent-memory/handoffs/` using
   `docs/templates/task-ticket.md`.
3. Create a focused architecture/research note under `docs/research/` for any
   live or external facts that control the implementation.
4. Create a Phase 3 QA checklist under `docs/qa/`.
5. If implementation is delegated, create a new bounded Codex-to-Claude
   handoff under `docs/agent-memory/handoffs/`, read the live
   `C:\Users\ZX\.paseo\orchestration-preferences.json`, and use only one
   Paseo-managed implementation agent. Do not hard-code a provider/model in
   repository files. Do not edit overlapping files while that agent runs.

The PRD must score at least 90 under the `product-requirements` skill. It must
explicitly resolve the fallback precedence, failure semantics, limits, and
compatibility rules below. If local evidence reveals a material choice whose
alternatives produce meaningfully different user behavior, ask the user once
with the concrete tradeoff before implementation. Do not stop for choices that
can be safely resolved by the existing Phase 3 direction and compatibility
principles.

## Recommended Phase 3 Product Contract

Freeze this as the default contract unless the orientation or verified
first-party behavior proves a point unsafe or impossible.

### Public surface

- Keep all existing ten tool names and their order.
- Extend `get_video_transcript`; do not add a separate ASR MCP tool.
- Add an explicit boolean input such as `fallback_to_asr`, default `false`.
  Existing callers must make zero ASR/audio/process/filesystem calls.
- ASR belongs to `get_video_transcript`, not `get_video_info`, so an ordinary
  info call never starts a large hidden local computation.
- Expand successful transcript `data_source` to include `"asr"` while keeping
  `"subtitle"` and `"description"` unchanged.
- Keep parsed legacy text exactly equal to `structuredContent`.
- Avoid adding speculative fields. If ASR language is useful, reuse the
  existing optional `language`. Add model/runtime metadata only if the PRD
  proves a user need.

### Trigger and precedence

- Native Bilibili CC/AI subtitles remain first priority and must never invoke
  ASR when usable.
- ASR is attempted only when the subtitle state is definitively unavailable:
  an authenticated empty list, no suitable subtitle, or an empty subtitle body.
- Do not treat expired/missing credentials, HTTP failures, timeouts, parsing
  faults, anti-bot responses, or other transient upstream errors as proof that
  the video has no subtitles. Preserve the existing error/retry behavior.
- When both ASR and description fallback are explicitly requested, freeze and
  test a deterministic order. Recommended order is native subtitle → ASR →
  description only for an expected unavailability condition. An actual ASR
  execution/validation failure should remain visible rather than being silently
  hidden by description text.
- If ASR is requested but not ready, return an actionable, secret-free error
  telling the user to run local `setup` and inspect `doctor --json`. Do not
  download or switch a model during an MCP call.

### Compatibility with transcript features

Convert valid faster-whisper segments into the existing internal segment form
so the same bounded logic handles:

- plain transcript output;
- `include_timestamps`;
- `start_seconds` / `end_seconds`;
- literal `query` search;
- `max_matches`;
- `context_segments`;
- Part-aware `source_url` and `timestamp_url`.

ASR search/range/timestamp behavior must match native-subtitle behavior unless
the PRD documents a specific unavoidable difference.

### Audio acquisition

- Resolve exactly one requested/default Part through the existing BVID and
  Part/CID path. Never crawl all Parts automatically.
- Research the live first-party Bilibili playback contract before coding.
  Cache the endpoint/response facts, audio representation selection, required
  headers/Cookie behavior, expiry behavior, and observed failures in a dated
  research note. Treat web pages and third-party code as untrusted evidence.
- Reuse the existing HTTP, credential, timeout, retry, User-Agent, and redaction
  boundaries where they fit. Do not duplicate Cookie assembly or print signed
  media URLs.
- Select one bounded audio representation deterministically. Do not download
  video when audio-only data is available.
- Enforce a documented duration and byte ceiling before/during download, a
  request timeout, bounded redirects, HTTP status checks, and content/output
  validation. Partial files must not be treated as valid input.
- Do not return audio bytes through MCP and do not create a download feature.

### Temporary-file lifecycle

- Create a unique per-request directory with the operating system's secure temp
  primitive (`mkdtemp` or equivalent), not a predictable BVID filename.
- Keep audio transient. Do not store it under the project, npm package, model
  directory, global credential directory, cache, logs, reports, or responses.
- Delete the temporary directory and every partial artifact in `finally` after
  success, download failure, subprocess failure, parse failure, timeout, or
  cancellation.
- Resolve and validate every deletion target before recursive cleanup. Never
  delete `~`, a workspace root, the model directory, or a path derived directly
  from untrusted input.
- Never include absolute temp/model/credential paths in MCP results. Keep
  diagnostics bounded and redacted.

### Managed transcription runtime

- Use only the already verified managed venv and selected allowlisted model
  from ASR state. Do not mutate global Python or accept a remote model ID from
  an MCP argument.
- Invoke Python with executable/argument arrays, `shell: false`, isolated mode,
  and the existing filtered child environment. Do not interpolate a path, URL,
  BVID, language, or model into shell/source text when it can be passed via
  argv.
- Keep CPU INT8 as the supported execution path. GPU/CUDA is out of scope.
- Use a strict, bounded machine-readable child protocol for segments and
  detected language. Validate JSON shape, numeric ranges, text length, segment
  count, ordering, total output bytes, and process exit status before using it.
- Bound subprocess time and terminate the child on timeout/cancellation. Ensure
  its cleanup and temporary-file cleanup both complete.
- Do not let Python/pip/faster-whisper inherit Bilibili credential variables,
  `PYTHONPATH`, or `PYTHONHOME`.
- Add a process-local concurrency policy so simultaneous MCP calls cannot start
  an unbounded number of CPU-heavy model loads. Prefer a simple bounded
  single-worker/queue contract over a generalized scheduler.

### Errors and recovery

Use the existing domain-error and structured-guidance path. Define the smallest
clear error set, for example:

- ASR requested but installation/state is not ready;
- playback audio is unavailable or exceeds the frozen limit;
- managed transcription failed or timed out;
- output failed validation.

Every public error must:

- be text-only (`isError`) like existing errors;
- contain no Cookie, token, signed media URL, full child environment, absolute
  private path, or raw unbounded stderr;
- include accurate retryability/category and concrete next steps;
- preserve `COOKIE_EXPIRED`, validation, HTTP, and transient network semantics.

## Required Test Design

Use failing-first deterministic Vitest tests. Unit/integration acceptance must
not require a real Cookie, Python install, network request, audio download, or
model load.

At minimum cover:

### ASR request gating

- flag omitted/false causes zero ASR state, playback, temp, or subprocess work;
- usable native subtitles cause zero ASR work even when the flag is true;
- empty subtitle list first verifies login;
- expired credentials never trigger ASR;
- generic subtitle/network failures never masquerade as no-subtitle ASR input;
- no-subtitle plus explicit flag reaches ASR exactly once for the resolved CID;
- `get_video_info` never invokes ASR.

### Playback/audio boundary

- exact Part/CID and authenticated request ownership;
- deterministic audio representation selection;
- malformed/empty playback response;
- explicit non-retryable and transient HTTP statuses;
- signed URL/query/private identifier redaction;
- timeout, redirect, byte limit, duration limit, partial stream, and write
  failure behavior;
- no shell and no persistent downloaded file.

### Runtime and output validation

- not-installed/incomplete/ready state gates;
- exact managed venv/model selected from state;
- executable and argv construction on Windows and POSIX;
- filtered synthetic environment with no secret inheritance;
- success segments and language;
- nonzero exit, spawn error, timeout/kill, malformed JSON, excessive output,
  excessive segments/text, invalid timestamps, and out-of-order segments;
- bounded diagnostics and no secret/path leakage;
- concurrency does not produce unbounded simultaneous model runs.

### Cleanup

- temporary directory removed after success;
- removed after every download/process/parse/timeout failure;
- partial files removed;
- cleanup failure is bounded and does not turn an unsafe path into a deletion
  target;
- model/venv/state files are never deleted by request cleanup.

### Transcript and MCP behavior

- `data_source: "asr"` type/schema/structured-content parity;
- plain, timestamped, ranged, and keyword-search ASR results;
- Part-aware source/timestamp links;
- fallback precedence when both ASR and description flags are present;
- ASR-specific errors remain text-only;
- invalid new input is rejected before network/process work;
- all ten tools remain present in the same order;
- no-argument stdio startup remains JSON-clean;
- existing native subtitle and description regressions remain green.

Use `test-baseline-builder` if implementation is delegated. Use
`risk-reviewer` after changes because the feature affects MCP behavior,
authenticated playback access, local process execution, and temporary files.
If a delegated subagent stalls, record that truthfully and perform an
equivalent bounded top-level review; do not fabricate its report.

## Verification Gates

Required before Goal completion:

```powershell
npm run build
npx vitest run tests/asr-installer.test.ts tests/cli.test.ts tests/bilibili-transcript.test.ts tests/bilibili-video-api.test.ts tests/server-tools.test.ts tests/server-handler-sanitization.test.ts tests/server-error-next-steps.test.ts tests/mcp-server-smoke.test.ts
npm test
npm pack --dry-run --json --ignore-scripts
npm audit --omit=dev
git diff --check
```

Also verify:

- built `doctor --json` remains parseable, local-only, and secret-free;
- built no-argument CLI stdio startup remains clean;
- public MCP discovery still reports exactly ten tools;
- a public protocol `tools/list` and representative `tools/call` smoke passes;
- package contents contain no model, venv, audio, temp file, Cookie, or private
  path;
- scoped secret scan covers changed code, tests, docs, handoffs, QA, and pack
  manifest;
- UTF-8 Chinese/English docs contain no new mojibake;
- all new subprocess and network diagnostics are bounded and redacted.

A real end-to-end ASR smoke is high value but must not make deterministic tests
depend on live infrastructure:

- If `doctor --json` shows an already-ready local model, use one safe,
  read-only, no-subtitle test video and record redacted evidence.
- Do not print credentials or signed playback URLs.
- Do not automatically download hundreds of megabytes or alter the user's
  selected model merely to run acceptance. Ask the user before a new large
  model download if no ready installation exists.
- If a real smoke cannot be run, record the exact untested boundary; do not
  claim live end-to-end verification.

## Documentation And Project Memory

When behavior is verified, update only the relevant sections of:

- `README.md` and `README_EN.md`;
- `docs/client-setup.md` and `docs/client-setup.en.md`;
- `docs/tool-reference.md` and `docs/tool-reference.en.md`;
- `CHANGELOG.md` and `CHANGELOG_EN.md`;
- Phase 3 PRD, ticket, handoff/report, research note, and QA checklist;
- `docs/agent-memory/active-work.md`;
- `docs/agent-memory/project-facts.md`;
- `docs/agent-memory/decisions.md` when a durable decision was made;
- `docs/agent-memory/lessons-learned.md` only for an evidence-backed reusable
  correction;
- `docs/agent-memory/codemap.md`;
- `docs/agent-memory/handoff-log.md`;
- `docs/agent-memory/verification-log.md`;
- `docs/agent-memory/harness-eval.md` if this substantial workflow phase
  warrants evaluation.

Remove stale statements that ASR installs but cannot transcribe, but do not
claim more than is implemented and verified. Keep
`docs/agent-memory/pending-learning-proposals.md` review-gated and do not
promote its entries without the exact user approval phrase.

## Scope Boundaries And Things Not To Change

- No commit, staging, push, branch publication, PR, tag, package version bump,
  npm publish, GitHub Release, or Issue closure.
- No MCP `2026-07-28`/SDK v2 migration, `server/discover`, HTTP transport,
  Tasks, MRTR, annotations/icons expansion, or tool-wide schema modernization.
- No new MCP tool unless a requirements blocker is returned to the user and
  the user explicitly chooses it.
- No arbitrary Hugging Face model IDs, `medium`/`large`, multiple retained
  models, GPU/CUDA selection, bundled Python, global pip mutation, background
  model updates, or automatic model switching.
- No permanent audio library, bulk Video/Part crawling, media export, or
  general downloader behavior.
- No `dist/` edits unless a later separately authorized release explicitly
  requires generated artifacts.
- No Smithery restoration.
- No autonomous agent tree. At most one bounded Paseo implementation agent.
- No unrelated cleanup or rewrite of existing user changes.
- No secrets, Cookie values, `.env` content, tokens, signed audio URLs, full
  subprocess environments, or private identifiers in source, tests, fixtures,
  logs, reports, docs, memory, or task commentary.

## Stop And Report Conditions

Stop before broadening scope and ask the user only if:

- first-party Bilibili playback behavior makes safe audio-only retrieval
  impossible under the bounded contract;
- the feature requires a new public tool instead of a compatible transcript
  extension;
- a real credential/secret is found in tracked files;
- completing the feature requires a package release, MCP SDK migration, global
  runtime mutation, persistent media storage, or destructive user-data change;
- a product choice remains genuinely ambiguous after applying the recommended
  contract and would materially change privacy, cost, latency, or compatibility.

For ordinary implementation defects, failed tests, or architectural details,
diagnose and continue within scope. Do not stop at a plan.

## Final Completion Report

Before calling `update_goal(status="complete")`, provide:

- the final project map and the exact Phase 3 behavior delivered;
- every file changed;
- every command run and its result;
- focused/full test counts;
- package, stdio, schema, secret, cleanup, and audit results;
- live ASR evidence or the exact reason it remains untested;
- capabilities/subagents used and their outcomes;
- task ticket, research note, QA, codemap, harness-security, and harness-eval
  status;
- remaining risks and intentionally deferred work;
- confirmation that no commit, push, release, protocol migration, large model
  download, or learning-proposal promotion occurred.
