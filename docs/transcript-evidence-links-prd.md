# Product Requirements Document: Transcript Evidence Links

**Version**: 1.0
**Date**: 2026-07-26
**Author**: Sarah (Product Owner)
**Quality Score**: 96/100

## Executive Summary

`get_video_transcript` can locate bounded subtitle evidence but still makes clients reconstruct Bilibili browser links from BVID, Part, and start time. This feature adds canonical source and timestamp links to the existing transcript result.

The change remains Bilibili-native and limited to one existing tool. It adds no tool, input, dependency, Bilibili request, search, danmaku, cursor, download, or cross-platform behavior.

## Problem Statement

**Current situation**: A caller can read a transcript match but cannot directly open the selected Part at the cited moment.

**Proposed solution**: Add a Part-aware `source_url` to every successful transcript result and a `timestamp_url` to every search match.

**Expected impact**: Agents can return evidence that a user can open and verify without guessing Bilibili URL parameters.

## Requirements Quality

- Business Value & Goals: 29/30
- Functional Requirements: 25/25
- User Experience: 19/20
- Technical Constraints: 15/15
- Scope & Priorities: 8/10

## Success Metrics

- Every successful `get_video_transcript` result contains the correct Part-aware `source_url`.
- Every returned `Transcript Match` contains a `timestamp_url` targeting its exact `start_seconds`.
- Ordinary and multi-Part generated links open the expected Bilibili Video/Part and start at or after the requested time.
- Exact BVID casing is preserved.
- No additional Bilibili request, dependency, MCP tool, or input is introduced.
- Existing errors and the other seven tools remain unchanged.

## User Personas

### Primary: Evidence Consumer

- **Role**: Uses an MCP client to research or learn from Bilibili videos.
- **Goal**: Open the original Video at the cited subtitle moment.
- **Pain point**: Current evidence requires manual URL construction and Part selection.
- **Technical level**: Any.

### Secondary: MCP Client Integrator

- **Role**: Renders transcript search results.
- **Goal**: Consume stable, structured browser URLs without platform-specific reconstruction.
- **Pain point**: BVID, Part, and time currently arrive as separate fields.
- **Technical level**: Advanced.

## User Stories And Acceptance Criteria

### Open the selected source

**As an** evidence consumer,
**I want** a canonical source link,
**so that** I can open the exact Bilibili Video Part used by the transcript.

**Acceptance criteria:**

- [ ] Every successful transcript or description result contains `source_url`.
- [ ] An ordinary Video URL contains the exact BVID and no unnecessary `p`.
- [ ] A multi-Part Video URL contains the resolved one-based `p`.

### Open a matching moment

**As an** evidence consumer,
**I want** each search match to contain a timestamp link,
**so that** I can verify the quoted subtitle in context.

**Acceptance criteria:**

- [ ] Every returned `matches[]` item contains `timestamp_url`.
- [ ] The URL contains the match's exact `start_seconds` as `t`.
- [ ] The URL retains the selected Part's `p` when the Video is multi-Part.

### Preserve compatibility

**As an** existing MCP user,
**I want** an additive response change,
**so that** existing transcript workflows continue to work.

**Acceptance criteria:**

- [ ] Existing fields and inputs retain their semantics.
- [ ] JSON text and `structuredContent` continue to represent the same object.
- [ ] Validation and runtime errors remain text-only.
- [ ] The other seven tools remain unchanged.

## Functional Requirements

### Domain contract

- `source_url` is a required string on `VideoTranscriptData`.
- `timestamp_url` is a required string on each `TranscriptMatch`.
- `timestamp_url` is not added at the top level because a non-search transcript does not identify one canonical evidence moment.
- Exact BVID casing returned by `extractBVId` must be preserved.

### URL construction

- Ordinary source: `https://www.bilibili.com/video/<bvid>/`
- Multi-Part source: ordinary source with `p=<resolved page>`
- Match timestamp: source URL with `t=<start_seconds>`
- Use the standard `URL` API.
- Do not preserve arbitrary input tracking parameters.
- Do not use the existing uppercasing URL helper.

### Result behavior

- Compute the resolved Part and source URL once after existing navigation.
- Include `source_url` in subtitle, no-subtitle description fallback, unsuitable-language fallback, empty-body fallback, `NoSubtitleError` fallback, and general-error fallback successes.
- Search mode includes `source_url` at the root and `timestamp_url` on every returned match.
- Do not add links to errors.

### Output schema

- Add required `source_url: { type: "string" }` to the existing transcript output schema.
- Add required `timestamp_url: { type: "string" }` to each match schema.
- Do not add `$schema`, URI format constraints, `oneOf`, or unrelated business constraints.

### Documentation

- Add a concise field description to the Chinese and English transcript documentation.
- Do not duplicate the full schema in README files.

## Technical Constraints

### Compatibility

- Keep `@modelcontextprotocol/sdk`, package metadata, lockfile, tool count, and tool order unchanged.
- Preserve TypeScript ESM and JSON-serializable results.

### Security

- Do not copy Cookie values or caller tracking parameters into output.
- Do not log or persist credentials.
- Generated URLs must use the fixed HTTPS Bilibili origin and validated BVID/Part/time data.

### Performance

- Zero new Bilibili requests.
- URL generation remains synchronous and local.

## MVP Scope

### Included

- `source_url` on successful transcript results.
- `timestamp_url` on transcript search matches.
- Exact output schema, tests, bilingual docs, research note, real browser and MCP client verification.

### Out Of Scope

- Search, danmaku, cursors, cross-video research, mobile deep links, ASR, visual frames, downloads, or new tools.
- Structured output migration for other tools.
- Changes to `get_video_info`, metadata, comments, or Chapters.
- Version, changelog, release, branch, commit, push, or pull request.

## Test And Verification Requirements

- Focused failing-first regressions for:
  - ordinary source URL
  - multi-Part source URL
  - exact decimal timestamp URL
  - description fallback source URL
  - exact output schema
  - handler text/structured equality
- Existing transcript, validation, error, tool-count, and tool-order regressions remain green.
- Run:
  - `npm test -- tests/bilibili-transcript.test.ts tests/server-tools.test.ts tests/server-handler-sanitization.test.ts`
  - `npm run build`
  - `npm test`
  - official SDK stdio discovery and successful ordinary/multi-Part calls
  - Playwright navigation of generated ordinary and multi-Part links
  - `npm pack --dry-run --json`
  - `git diff --check`

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| BVID casing is changed | Medium | High | Preserve `extractBVId` output and add a mixed-case regression. |
| Part link opens the wrong Part | Low | High | Derive `p` from existing resolved Part and run a live multi-Part browser check. |
| Bilibili changes `p` or `t` behavior | Low | Medium | Cache live evidence and state refresh conditions. |
| Response additions increase payload size | High | Low | Add only one root URL and one URL per already-bounded match. |

## Dependencies And Blockers

**Dependencies:**

- Existing `resolvePartCid`, `VideoTranscriptData`, `TranscriptMatch`, structured-output handler, and standard `URL` API.
- Valid external Bilibili credentials for live transcript acceptance.

**Known blockers:**

- None. Current replacement credentials are valid and live browser probes passed.

## References

- `CONTEXT.md`
- `docs/research/2026-07-26-bilibili-timestamp-link-contract.md`
- `docs/research/2026-07-25-cross-platform-video-content-mcp-landscape.md`
- `src/bilibili/subtitle.ts`
- `src/bilibili/types.ts`
- `src/server/tool-schemas.ts`
