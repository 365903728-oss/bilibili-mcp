# Codex To Claude Handoff: Transcript Evidence Links

## Objective

Implement GitHub Issue [#17](https://github.com/XZXZZX-Ai/bilibili-mcp/issues/17): add citation-ready Bilibili browser links to `get_video_transcript` only.

Every successful transcript result must gain a Part-aware `source_url`. Every returned search match must gain a `timestamp_url` targeting that match's exact `start_seconds`.

## Current State

- Branch: `master`.
- Base HEAD and `origin/master`: `d4b06e5`.
- Package version: `1.7.2`; no version or release change is authorized.
- Public MCP tool count: 8.
- Focused baseline before implementation: 3 files / 78 tests passed.
- Issue #16 structured output is already accepted and closed.
- Research and product contract:
  - `docs/research/2026-07-26-bilibili-timestamp-link-contract.md`
  - `docs/transcript-evidence-links-prd.md`
- Live Playwright evidence confirms:
  - ordinary `?t=<seconds>` links start playback at that time
  - multi-Part `?p=<page>&t=<seconds>` links select the Part and time
  - decimal seconds work
  - BVID casing must be preserved

## Files To Inspect

- `AGENTS.md`
- `CLAUDE.md`
- `CONTEXT.md`
- `docs/transcript-evidence-links-prd.md`
- `docs/research/2026-07-26-bilibili-timestamp-link-contract.md`
- `src/bilibili/types.ts`
- `src/bilibili/subtitle.ts`
- `src/bilibili/navigation.ts`
- `src/server/tool-schemas.ts`
- `src/server/tool-handlers.ts`
- `tests/bilibili-transcript.test.ts`
- `tests/server-tools.test.ts`
- `tests/server-handler-sanitization.test.ts`
- `README.md`
- `README_EN.md`
- `docs/agent-memory/agent-communication.md`
- `docs/agent-memory/codemap.md`
- `docs/agent-memory/harness-security.md`

## Files To Edit

Expected implementation scope:

- `src/bilibili/types.ts`
- `src/bilibili/subtitle.ts`
- `src/server/tool-schemas.ts`
- `tests/bilibili-transcript.test.ts`
- `tests/server-tools.test.ts`
- `tests/server-handler-sanitization.test.ts`
- `README.md`
- `README_EN.md`

Write the final report to:

- `docs/agent-memory/handoffs/2026-07-26-transcript-evidence-links-claude-report.md`

## Required Capability

- Use the installed `vitest` skill.
- Use the project `test-baseline-builder` subagent for focused test review.
- Use the project `risk-reviewer` subagent after implementation.
- Follow the repository's bounded-wait fallback if a subagent stalls; record the result truthfully.

`domain-modeling` has already been applied by Codex to freeze `Source URL` and `Timestamp URL` in `CONTEXT.md`. Consume those terms; do not edit the glossary.

## Constraints

- Only `get_video_transcript` may change.
- Add required `source_url: string` to `VideoTranscriptData`.
- Add required `timestamp_url: string` to `TranscriptMatch`.
- Ordinary source URL: `https://www.bilibili.com/video/<exact-bvid>/`.
- Multi-Part source URL adds `p=<resolved page>`.
- Match timestamp URL adds `t=<start_seconds>` to the Part source URL.
- Preserve exact BVID casing returned by `extractBVId`.
- Do not use or change the existing uppercasing `normalizeBVId` / `createVideoUrl` helpers.
- Do not copy arbitrary query parameters from caller input.
- Do not add a top-level `timestamp_url`.
- Do not add URL format constraints, `$schema`, `oneOf`, or unrelated schema rules.
- Keep JSON text and `structuredContent` equal to the same result.
- Errors remain text-only.
- Add no tool, input, dependency, Bilibili request, cache entry, or shared response helper.
- Do not modify `src/server.ts`, Bilibili HTTP/API modules, package files, lockfile, version, changelog, or `dist/`.
- Do not create a branch, commit, push, PR, tag, release, or publication.
- Do not print or persist Cookie values, `.env` contents, tokens, or credentials.

Preserve and do not edit these pre-existing or Codex-owned working-tree files:

- `CONTEXT.md`
- `docs/agent-memory/active-work.md`
- `docs/agent-memory/pending-learning-proposals.md`
- `docs/agent-memory/verification-log.md`
- `docs/agent-memory/handoffs/2026-07-26-transcript-evidence-links-codex-to-claude.md`
- `docs/qa/2026-07-25-structured-transcript-output.md`
- `docs/research/2026-07-26-bilibili-timestamp-link-contract.md`
- `docs/transcript-evidence-links-prd.md`

Codex owns live Bilibili, Playwright, SDK client, QA, issue-state, and final-memory verification.

## Recommended Approach

Use the smallest local implementation:

1. Compute the existing resolved Part once immediately after `resolvePartCid`.
2. Build `source_url` with the standard `URL` API:
   - preserve `bvid`
   - add `p` only when `pages.length > 1`
3. Pass `source_url` into the existing private search path.
4. For each match, clone that URL, set `t` to `hit.from`, and return it as `timestamp_url`.
5. Reuse the same root `source_url` in every successful subtitle or description return.

Do not introduce a new module, class, dependency, general evidence abstraction, or cross-tool helper.

## Execution Steps

1. Re-check `git status --short` and the scoped files.
2. Add failing regressions first:
   - ordinary successful transcript has exact source URL
   - multi-Part selected transcript has exact `?p=<page>` source URL
   - search match has exact decimal `timestamp_url`
   - description fallback has source URL
   - output schema requires root `source_url` and match `timestamp_url`
   - handler fixture proves text/structured equality with both new fields
3. Run the focused test command and record the expected red result.
4. Implement the minimum type, URL, result, and schema changes.
5. Add one concise field sentence or bullets to each README.
6. Run focused tests, build, full tests, package dry run, and diff check.
7. Run `test-baseline-builder`, then `risk-reviewer`.
8. Check `docs/agent-memory/codemap.md`; leave it unchanged unless navigation ownership truly changes.
9. Write the required Claude report.

## Verification Commands

```powershell
npm test -- tests/bilibili-transcript.test.ts tests/server-tools.test.ts tests/server-handler-sanitization.test.ts
npm run build
npm test
npm pack --dry-run --json
git diff --check
```

## Acceptance Criteria

- [ ] All successful transcript paths include `source_url`.
- [ ] Ordinary source URLs preserve exact BVID casing and omit unnecessary `p`.
- [ ] Multi-Part source URLs include the resolved `p`.
- [ ] Every returned search match includes `timestamp_url` with exact `start_seconds`.
- [ ] Transcript output schema requires the two approved fields in their approved locations.
- [ ] Text and structured results remain equal.
- [ ] Errors and the other seven tools remain unchanged.
- [ ] No new request, dependency, tool, input, cache behavior, or release change occurs.
- [ ] Focused tests, build, full tests, package dry run, and diff check pass.
- [ ] README and README_EN document the links concisely.
- [ ] Subagent outcomes and harness artifacts are reported.

## Things Not To Change

- Shared BVID normalization helpers.
- Bilibili API, navigation, credential, cache, validation, retry, or error behavior.
- Search matching, context, truncation, or transcript formatting.
- Structured output for other tools.
- Historical plans, generated learning proposals, prior QA, or release state.

## Stop And Report If

- A generated link requires another Bilibili request.
- The current result cannot supply a resolved Part or start time.
- Correctness appears to require changing BVID normalization globally.
- A schema/result mismatch requires broader response changes.
- A test failure is unrelated to this issue.
- Any request would exceed the listed public fields or Git authority.

## Expected Claude Report

Use the template in `docs/agent-memory/agent-communication.md` and include:

- Files changed.
- Focused red/green evidence.
- Commands run and exact results.
- Request-count and compatibility reasoning.
- `test-baseline-builder` and `risk-reviewer` outcomes.
- Risks, skipped checks, and decision points.
- `Harness Artifacts` status for Issue #17, research note, QA checklist, codemap, harness security, and harness eval.
