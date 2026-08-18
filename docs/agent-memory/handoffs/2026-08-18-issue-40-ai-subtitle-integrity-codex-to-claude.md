# Codex To Claude Handoff: Issue #40 AI Subtitle Integrity

## Update Goal

Implement GitHub Issue #40 against clean `origin/master` `44ac1e717001aed59c4a3b475cf82f074d11e567`, and close the directly related Roadmap gap where a structurally valid but unstable `ai-zh` subtitle prevents explicit ASR fallback.

GitHub Issue #40 is the task ticket. Do not create a duplicate local ticket.

Expected report: `docs/agent-memory/handoffs/2026-08-18-issue-40-ai-subtitle-integrity-claude-report.md`.

## Current Judgment

- `ai-zh` is a Bilibili-generated AI subtitle, not the managed local ASR result and not a human subtitle. Its public source value must be `ai_subtitle`; reserve `asr` for `transcribeVideoPart()`.
- The source identity is currently lost because both transcript and video-info paths return literal `subtitle` after selecting any subtitle row.
- `fallback_to_asr` currently runs only for an empty subtitle list, no selected subtitle, or an empty body. A non-empty but inconsistent `ai-zh` body always short-circuits ASR.
- The observed Roadmap defect is six mutually different bodies for one `ai-zh` track. A deterministic cross-read stability check can catch that exact class when the caller explicitly enables ASR fallback. Do not invent semantic title matching, call an LLM, or add a dependency.
- `ASR_AUDIO_UNAVAILABLE` already tries up to three audio candidates and returns retryable bilingual next steps. Verify this with existing tests; do not add another retry layer without a red regression proving a gap.
- Non-TTY `setup` scripting is unrelated to Issue #40 and changes credential-input security. Leave it unchanged and report it as a separate follow-up.
- A live published-package repro on 2026-08-18 timed out while fetching subtitle content, so deterministic injected tests are the acceptance authority. Do not convert a transport timeout into an ASR gate.

## Recommended Approach

Keep the existing modules and positional compatibility. Make the smallest change at the shared subtitle-selection/result seam:

1. Centralize the `ai-zh` classification in one small helper used by transcript and video-info flows.
2. Add `ai_subtitle` to the relevant public `data_source` unions and the transcript output schema.
3. Add optional boolean `exclude_ai_subtitles` to `get_video_transcript` and `get_video_info`, default `false`.
   - Filter AI rows before selection.
   - Prefer a remaining human subtitle when present.
   - If only AI rows remain, use the existing definitive-absence behavior: transcript may use explicit ASR/description fallback; video-info returns description.
   - Include the option in any cache key whose output it changes.
4. Add optional boolean `force_asr` only to `get_video_transcript`, default `false`.
   - `true` is itself explicit authorization to run the already-installed local ASR and does not require `fallback_to_asr: true`.
   - It bypasses subtitle metadata/content selection, including valid human subtitles, but still resolves the selected Part and uses all existing ASR readiness, duration, audio, cancellation, limit, cleanup, error, range, timestamp, search, and source-link behavior.
   - `force_asr` wins over `exclude_ai_subtitles`; do not create a validation conflict for callers that send both.
5. When the selected source is `ai-zh` and `fallback_to_asr: true` (but not `force_asr`), read the same AI subtitle twice through the existing subtitle-content seam and compare a canonical representation of segment timing and text.
   - Stable bodies return `data_source: "ai_subtitle"` and remain native-first.
   - Two structurally valid but different bodies are treated as unusable and enter the existing definitive-absence path, which invokes ASR because fallback was explicitly enabled.
   - A transport, timeout, auth, parser, or HTTP failure on either read remains an error; it must not silently become an ASR gate.
   - Do not log subtitle text, signed URLs, body hashes, credentials, or private paths. A bounded warning may include BVID, page, and source category only.
6. Update bilingual public documentation and Unreleased changelogs. Clearly state that `ai_subtitle` is Bilibili AI transcription, may be inaccurate, and is not equivalent to a human-checked citation.

If a simpler implementation satisfies every acceptance criterion through the existing public seams, prefer it. Do not add a new module, dependency, class, factory, interface, or config surface unless an actual second implementation requires it.

## Files To Inspect

- GitHub Issue #40 body and comments via `gh issue view 40 --comments`
- `CONTEXT.md`
- `docs/adr/0001-navigable-transcript-interface.md`
- `src/bilibili/subtitle.ts`
- `src/bilibili/video-api.ts`
- `src/bilibili/types.ts`
- `src/asr/transcription.ts`
- `src/bilibili/playback.ts`
- `src/server/tool-schemas.ts`
- `src/server/tool-handlers.ts`
- `src/utils/validation.ts`
- `src/utils/error-guidance.ts`
- the corresponding tests, README files, tool references, changelogs, codemap, and QA conventions

## Expected Files To Edit

Keep the set minimal, but expect:

- `src/bilibili/subtitle.ts`
- `src/bilibili/types.ts`
- `src/server/tool-schemas.ts`
- `src/server/tool-handlers.ts`
- relevant transcript/server/schema tests
- `README.md`, `README_EN.md`
- `docs/tool-reference.md`, `docs/tool-reference.en.md`
- `CHANGELOG.md`, `CHANGELOG_EN.md`
- `docs/qa/2026-08-18-issue-40-ai-subtitle-integrity.md`
- `docs/agent-memory/codemap.md` only if its navigation facts materially change
- the expected Claude report

Do not edit the primary worktree's untracked `ROADMAP.md`; Codex owns the final Roadmap reconciliation after verification.

## Required Capabilities

Use the native Claude-side skills and project agents that exist on this machine:

- `/implement` as the top-level bounded execution workflow. Repository rules disable its default commit step.
- `/diagnosing-bugs` to establish deterministic red-capable tests before changing implementation.
- `/codebase-design` to keep classification and fallback at the shared subtitle seam without broad refactoring.
- `/tdd` and `vitest` for vertical red-green slices at the pre-agreed public seams below.
- `/code-review` after implementation, with Issue #40 plus this handoff as the spec source and `44ac1e7` as the fixed point.
- `test-baseline-builder` for changed tests.
- `risk-reviewer` after the stable implementation because this affects MCP tools, ASR fallback, shared Bilibili behavior, caching, and untrusted remote text.
- `secret-scanning` for the changed diff and documentation. Never print matched values.

If a required subagent stalls, record that fact and complete the same bounded check at the top level; do not leave the Paseo task running indefinitely and do not spawn an autonomous team.

Pre-agreed test seams:

- MCP `tools/list` schema and `tools/call` handler behavior.
- Public `getVideoTranscriptData()` results and errors with only Bilibili/local-process boundaries injected.
- Public `getVideoInfoWithSubtitle()` results and cache behavior.
- Existing `transcribeVideoPart()` interface; do not expose private helpers just for tests.

## Things To Avoid

- No title/topic semantic heuristic, LLM call, fuzzy classifier, language library, or extra dependency.
- No broad ASR rewrite, model install/switch change, audio host relaxation, temp-file weakening, or background service.
- No automatic ASR unless `fallback_to_asr` or `force_asr` is explicitly true.
- No conversion of network/auth/parser failures into no-subtitle/ASR fallback.
- No Cookie values, subtitle bodies, signed playback URLs, full environment objects, local model paths, or private temp paths in logs/tests/reports.
- No SDK migration, new MCP tool, tool-order change, package version bump, dependency update, generated `dist/` edits, Smithery work, README redesign, or unrelated cleanup.
- No modification or promotion of `pending-learning-proposals.md`.
- No commit, push, PR, issue close/comment/edit, tag, release, or publication.

## Claude Code Execution Steps

1. Confirm clean branch/worktree fingerprint and read Issue #40 plus the listed local contracts.
2. Record baseline test count. If dependencies are absent, run `npm ci` before the test loop.
3. Use `/diagnosing-bugs` and TDD to create the first minimal failing tests. The report must include the exact red commands and failure summaries before implementation.
4. Work in vertical slices:
   - `ai_subtitle` classification for transcript and video-info;
   - `exclude_ai_subtitles` selection/absence/cache semantics;
   - `force_asr` bypass semantics;
   - unstable `ai-zh` + explicit fallback invokes ASR while stable AI remains native;
   - MCP schema, handler, output schema, and bilingual docs.
5. Run focused tests after each slice. Do not refactor unrelated code during red-green.
6. Run the final verification matrix and invoke required test/risk review.
7. Write the requested Claude report from final stable command output. Do not claim live semantic correctness from mocked tests; distinguish deterministic coverage from live Bilibili evidence.

## Acceptance Criteria

1. Human subtitles still return `data_source: "subtitle"`.
2. Selected Bilibili `ai-zh` returns `data_source: "ai_subtitle"` in both transcript and video-info public results.
3. Managed local ASR remains `data_source: "asr"`; description remains `description`.
4. Default input behavior remains native-first and does not invoke ASR automatically.
5. `exclude_ai_subtitles: true` is type-checked and published on both tools, prefers an available human subtitle, and treats AI-only as definitive absence without cache collision.
6. `force_asr: true` is type-checked and published on transcript, bypasses both human and AI subtitle content, works without also setting `fallback_to_asr`, and preserves existing ASR result/error/search/range/timestamp behavior.
7. With `fallback_to_asr: true`, two different well-formed reads of the same selected `ai-zh` body invoke ASR; two identical reads return stable `ai_subtitle` and do not invoke ASR.
8. Network, auth, timeout, HTTP, and parse failures remain visible and never become silent ASR fallback.
9. Transcript structured-output enum and text payload stay mutually consistent; the ten-tool count/order and legacy text compatibility remain unchanged.
10. Bilingual docs warn that `ai_subtitle` is Bilibili AI transcription and may not be citation-accurate, document both new inputs and exact defaults, and do not claim title-semantic validation.
11. Existing ASR audio-candidate retry and `ASR_AUDIO_UNAVAILABLE` recovery guidance remain covered. Add code only if a red public-seam regression proves the current behavior insufficient.
12. `setup` TTY behavior is unchanged and reported as an unrelated follow-up.
13. No secrets or remote text enter logs/reports; no dependency/version/tool-count change; no temp residue.

## Verification Commands

At minimum:

```powershell
npx vitest run tests/bilibili-transcript.test.ts tests/server-tools.test.ts tests/server-handler-sanitization.test.ts tests/server-error-next-steps.test.ts
npx vitest run tests/asr-transcription.test.ts tests/bilibili-playback.test.ts
npm test
npm run build
npm pack --dry-run --json --ignore-scripts
git diff --check
git status --short
```

Also run a built stdio `tools/list` / `tools/call` smoke proving the two new boolean inputs and `ai_subtitle` output schema without printing transcript bodies or credentials. Check before/after counts for `bilibili-mcp-asr-*` direct children of the OS temp root if ASR filesystem tests run.

Use `secret-scanning` on the changed diff/package surface and report only classifications/counts, never values.

## Risks And Rollback Points

- Public enum expansion can break consumers that assumed three values; documentation and output schema must change atomically.
- Extra AI-body reads can increase latency. Restrict stability checking to selected `ai-zh` when `fallback_to_asr` is explicitly enabled; do not duplicate human-subtitle fetches.
- Cache keys must include output-affecting options.
- Cross-read mismatch proves instability, not semantic wrongness. Do not overclaim broader content validation.
- Rollback is the scoped diff from fixed point `44ac1e7`; no Git delivery is authorized.

## Stop And Report If

- The implementation requires a new dependency, model, service, arbitrary subtitle classifier, credential transport change, or relaxed network/filesystem security.
- Existing public behavior makes `force_asr` semantics materially ambiguous beyond the rules above.
- A test can reproduce only through real credentials or by persisting real subtitle content.
- The latest Issue #40 changed materially after this handoff.
- The stable worktree contains unrelated edits or the fixed point changed.

## Expected Claude Report

Use the repository template and include:

- red tests/commands before implementation;
- files changed;
- focused/full/build/pack/stdio results from the final tree;
- exact source classification and option semantics;
- Roadmap overlap addressed versus unrelated/deferred items;
- unresolved live-network or semantic-validation limits;
- secret/temp/package findings without values;
- subagents/skills actually invoked and their results;
- `Harness Artifacts` covering Issue #40 ticket, research note, QA checklist, codemap, harness-security, and harness-eval.
