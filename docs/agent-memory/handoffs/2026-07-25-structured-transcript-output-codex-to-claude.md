# Codex To Claude Handoff: Structured Transcript Output

## Objective

Implement GitHub Issue [#16](https://github.com/XZXZZX-Ai/bilibili-mcp/issues/16): add backward-compatible MCP structured output to `get_video_transcript` only.

The existing `VideoTranscriptData` must remain the product payload. Successful calls should return it both as the current formatted JSON text and as `structuredContent`.

## Current State

- Branch: `master`.
- Package version: `1.7.2`.
- Installed MCP SDK: `@modelcontextprotocol/sdk@1.27.1`; do not upgrade it.
- Public tool count: 8.
- Focused baseline passed before implementation: 2 files, 35 tests.
- `get_video_transcript` currently has no `outputSchema`.
- Its success handler currently returns only `toTextContent(result)`.
- The installed SDK types already expose `Tool.outputSchema` and `CallToolResult.structuredContent`.

Planning sources:

- `docs/structured-transcript-output-prd.md`
- GitHub Issue #16
- `CONTEXT.md`
- `docs/agent-memory/decisions.md`

## Files To Inspect

- `AGENTS.md`
- `CLAUDE.md`
- `CONTEXT.md`
- `docs/adr/0001-navigable-transcript-interface.md`
- `docs/structured-transcript-output-prd.md`
- `src/server/tool-schemas.ts`
- `src/server/tool-handlers.ts`
- `src/server/error-response.ts`
- `src/bilibili/types.ts`
- `tests/server-tools.test.ts`
- `tests/server-handler-sanitization.test.ts`
- `tests/helpers/mcp.ts`
- `README.md`
- `README_EN.md`
- `docs/agent-memory/agent-communication.md`
- `docs/agent-memory/codemap.md`
- `docs/agent-memory/harness-security.md`

## Files To Edit

Only these implementation files are expected:

- `src/server/tool-schemas.ts`
- `src/server/tool-handlers.ts`
- `tests/server-tools.test.ts`
- `tests/server-handler-sanitization.test.ts`
- `README.md`
- `README_EN.md`

Write the final report to:

- `docs/agent-memory/handoffs/2026-07-25-structured-transcript-output-claude-report.md`

## Required Capability

- Use the installed `vitest` skill for the regression tests.
- Use the project `test-baseline-builder` subagent for focused test review.
- Use the project `risk-reviewer` subagent after implementation.
- If either subagent stalls, use a bounded wait, complete the same checklist at top level, and report the stall truthfully. Do not create an agent tree.

## Constraints

- Only `get_video_transcript` may gain structured output.
- Preserve `content[0].text` exactly as `JSON.stringify(result, null, 2)`.
- Add the same successful `VideoTranscriptData` object as `structuredContent`.
- Error results must continue to return only existing `content + isError`.
- Do not add `$schema`, `oneOf`, new result fields, new arguments, or extra business constraints.
- Do not create a shared dual-output helper.
- Do not modify shared `toTextContent`, `VideoTranscriptData`, `src/server.ts`, Bilibili request/fetch logic, package metadata, lockfile, version, changelog, or `dist/`.
- Do not add dependencies, tools, upstream requests, branches, commits, pushes, releases, or pull requests.
- Do not print, fixture, or record Cookie values, `.env` contents, tokens, or credentials.
- Preserve all pre-existing uncommitted files. In particular, do not edit:
  - `CONTEXT.md`
  - `docs/agent-memory/decisions.md`
  - `docs/agent-memory/pending-learning-proposals.md`
  - `docs/research/2026-07-25-cross-platform-video-content-mcp-landscape.md`
  - `docs/structured-transcript-output-prd.md`
  - this handoff
- Do not run a real credentialed Bilibili or Codex client call. Codex owns that final acceptance step.

## Exact Output Schema

Inline this schema on `get_video_transcript`:

- Object required fields: `bvid`, `data_source`, `transcript`, `title`.
- `bvid`: string.
- `data_source`: string enum `subtitle`, `description`.
- `language`: optional string.
- `transcript`: string.
- `title`: string.
- `page`: optional integer.
- `query`: optional string.
- `total_matches`: optional integer.
- `returned_matches`: optional integer.
- `truncated`: optional boolean.
- `matches`: optional array of objects.
- Each match object requires:
  - `start_seconds`: number.
  - `end_seconds`: number.
  - `content`: string.
  - `context`: string.

Do not add fields or constraints beyond this list.

## Execution Steps

1. Re-check `git status --short` and the scoped files before editing.
2. Add failing focused assertions first:
   - The public tool count is exactly 8 and order remains unchanged.
   - The transcript tool exposes the complete exact `outputSchema`.
   - A full search-mode fixture returns identical `structuredContent`.
   - Its text is exactly `JSON.stringify(fixture, null, 2)`.
   - Validation and transcript error paths do not contain `structuredContent`.
3. Run the focused tests and record the expected failure.
4. Add the inline transcript `outputSchema`.
5. In only the transcript success branch, reuse `toTextContent(result)` and attach:

   ```ts
   structuredContent: result as unknown as Record<string, unknown>
   ```

6. Add one concise sentence to each README explaining that successful calls return both the backward-compatible formatted JSON text and the same MCP `structuredContent`.
7. Run all verification commands below and fix only same-scope failures.
8. Invoke `test-baseline-builder`, then `risk-reviewer`.
9. Inspect `docs/agent-memory/codemap.md`; report `checked unchanged` unless navigation ownership actually changed. Do not edit it merely to record this small change.
10. Write the required Claude report using the repository report template.

## Verification Commands

Run:

```powershell
npm test -- tests/server-tools.test.ts tests/server-handler-sanitization.test.ts
npm run build
npm test
npm pack --dry-run --json
git diff --check
```

Also run an official SDK stdio smoke against local `dist/index.js` using `Client` and `StdioClientTransport`:

- `tools/list` must report 8 tools and the transcript `outputSchema`.
- `tools/call` must exercise a deterministic, credential-free error input such as an invalid BVID.
- The error call must remain an MCP error result without `structuredContent`.
- Use an inline or temporary command only; do not add a persistent smoke script.
- Close the client/transport cleanly and report exact results.

## Acceptance Criteria

- [ ] `get_video_transcript.outputSchema` exactly matches the approved current payload.
- [ ] Successful transcript results include `structuredContent` equal to the business result.
- [ ] Existing formatted JSON text is unchanged.
- [ ] Validation and runtime errors omit `structuredContent`.
- [ ] All other public tools and schemas are unchanged.
- [ ] Focused tests, full tests, build, official SDK stdio smoke, package dry run, and diff check pass.
- [ ] README and README_EN each contain one concise dual-return statement.
- [ ] No dependency, package, lockfile, credential, Bilibili request, Git, or release change occurred.
- [ ] Test-baseline and risk review outcomes are recorded.
- [ ] Claude Desktop and Cursor are recorded as untested and non-blocking.

## Things Not To Change

- The payload fields or optionality in `VideoTranscriptData`.
- Any Bilibili API call, caching, subtitle selection, fallback, validation, or error guidance.
- Any response shape of the other seven tools.
- Shared response helpers.
- Historical plans or controlled-learning artifacts.
- Git state beyond the requested unstaged file changes.

## Stop And Report If

- The installed SDK cannot support the exact contract without an upgrade.
- Schema validation requires changing the current runtime payload.
- A test failure indicates pre-existing unrelated work rather than this change.
- A credential, secret, package, architecture, or broader public-interface decision is required.
- Any requested change would exceed the six expected implementation files.

## Expected Claude Report

Use the template in `docs/agent-memory/agent-communication.md` and include:

- Files changed.
- Commands run and exact results.
- Focused red/green evidence.
- SDK stdio smoke evidence.
- Test-baseline-builder and risk-reviewer outcomes.
- Risks, skipped checks, and decision points.
- A `Harness Artifacts` section covering:
  - Task ticket: GitHub Issue #16 used.
  - Research note: existing note used; no new note needed.
  - QA checklist: not required unless a new reusable workflow is discovered.
  - Codemap: checked unchanged or updated with reason.
  - Harness security: reviewed because the report/handoff are harness surfaces.
  - Harness eval: deferred; this is not a release or significant harness upgrade.
