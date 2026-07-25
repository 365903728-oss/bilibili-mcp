# Product Requirements Document: Structured Transcript Output

**Version**: 1.0
**Date**: 2026-07-25
**Author**: Sarah (Product Owner)
**Quality Score**: 96/100

## Executive Summary

`get_video_transcript` currently returns an existing `VideoTranscriptData` payload only as formatted JSON text. MCP clients that support structured tool results must parse that text again before they can reliably consume transcript metadata and search matches.

This pilot adds an accurate MCP `outputSchema` and returns the same payload as `structuredContent`, while preserving the existing formatted JSON text byte-for-byte. It is intentionally limited to one Bilibili-native tool so client compatibility can be proven without changing Bilibili requests, transcript behavior, dependencies, or the other seven tools.

## Problem Statement

**Current situation**: The transcript result is machine-readable JSON embedded in `content[0].text`, but the tool does not declare or return MCP structured output.

**Proposed solution**: Declare the current `VideoTranscriptData` shape as `get_video_transcript.outputSchema` and attach the same result object as `structuredContent` on successful calls.

**Expected impact**: Modern MCP clients can consume transcript evidence directly, while existing clients continue receiving exactly the text representation they already use.

## Requirements Quality

- Business Value & Goals: 28/30
- Functional Requirements: 25/25
- User Experience: 19/20
- Technical Constraints: 15/15
- Scope & Priorities: 9/10

## Success Metrics

- `tools/list` exposes the exact approved `outputSchema` for `get_video_transcript`.
- A successful transcript call returns identical data in `structuredContent` and parsed `content[0].text`.
- The literal `content[0].text` remains `JSON.stringify(result, null, 2)`.
- Validation and tool errors do not return `structuredContent`.
- Tool count, tool order, all other tool schemas, and all existing transcript behavior remain unchanged.
- Focused tests, full tests, build, local stdio smoke, package dry run, and `git diff --check` pass.
- One real Codex client call against the local build completes without output-schema validation failure.

## User Personas

### Primary: MCP Client Integrator

- **Role**: Connects Codex or another MCP client to the Bilibili server.
- **Goal**: Receive a predictable transcript object without reparsing presentation text.
- **Pain point**: The current response is JSON encoded inside a text content block.
- **Technical level**: Advanced.

### Secondary: Existing MCP User

- **Role**: Uses the current text response through an older or text-oriented client.
- **Goal**: Upgrade without changing existing prompts or parsing behavior.
- **Pain point**: A response-format migration could break established workflows.
- **Technical level**: Intermediate.

## User Stories And Acceptance Criteria

### Structured transcript consumption

**As an** MCP client integrator,
**I want** `get_video_transcript` to declare and return structured output,
**so that** I can consume transcript evidence through the MCP result contract.

**Acceptance criteria:**

- [ ] `get_video_transcript` declares the approved `outputSchema`.
- [ ] Successful calls include `structuredContent` equal to the existing `VideoTranscriptData` result.
- [ ] Search-mode fields and every `matches` item are represented by the schema.

### Backward-compatible text consumption

**As an** existing MCP user,
**I want** the current JSON text response to remain unchanged,
**so that** existing clients and prompts continue to work.

**Acceptance criteria:**

- [ ] `content[0].text` remains the same formatted JSON string.
- [ ] No existing result field is renamed, removed, or made newly required at runtime.
- [ ] The other seven tools return exactly their existing shapes.

### Predictable errors

**As an** MCP client integrator,
**I want** validation and runtime errors to keep their current error result,
**so that** successful structured data cannot be confused with an error payload.

**Acceptance criteria:**

- [ ] Validation errors retain `content + isError` and omit `structuredContent`.
- [ ] Subtitle/tool errors retain `content + isError` and omit `structuredContent`.

## Functional Requirements

### Output schema

The schema is declared inline on `get_video_transcript`:

- Required: `bvid`, `data_source`, `transcript`, `title`.
- Optional: `language`, `page`, `query`, `total_matches`, `returned_matches`, `truncated`, `matches`.
- `data_source` permits `subtitle` or `description`.
- Each `matches` item requires `start_seconds`, `end_seconds`, `content`, and `context`.
- The schema must not add `$schema`, `oneOf`, new fields, or extra business constraints.

### Successful result

- Reuse the existing `VideoTranscriptData` result object.
- Keep `toTextContent(result)` as the source of the text response.
- Add the same result object as `structuredContent`.
- Do not introduce a shared dual-output helper for this single-tool pilot.

### Documentation

- Add one concise sentence to the Chinese transcript documentation.
- Add one equivalent sentence to the English transcript documentation.
- Do not duplicate the full schema in either README.

### Error handling

- Preserve current validation, `NoSubtitleError`, and generic MCP error behavior.
- Do not add `structuredContent` to any error result.

## Technical Constraints

### Compatibility

- Keep `@modelcontextprotocol/sdk` and `package-lock.json` unchanged.
- Preserve TypeScript ESM and the reusable server export.
- Keep all returned values JSON-serializable.

### Security

- Do not print or store Bilibili Cookie values, `.env` contents, or credential fields.
- Credential checks may report only safe status metadata.
- Do not add or change credential storage or Bilibili request behavior.

### Performance

- No additional Bilibili request or transcript transformation is permitted.
- The accepted cost is duplicating the existing payload across text and structured MCP result fields.

## MVP Scope

### Included

- One `outputSchema` on `get_video_transcript`.
- One success-path `structuredContent` addition.
- Focused regression tests.
- Concise Chinese and English documentation.
- Local protocol, package, and client verification.

### Out Of Scope

- Structured output for the other seven tools.
- New transcript fields, cursors, confidence values, timestamp URLs, or arguments.
- Bilibili search, danmaku, ASR, or new upstream endpoints.
- Dependency upgrades, version changes, changelog, release, commit, push, branch, or pull request.
- Claude Desktop and Cursor runtime verification.

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Text and structured payloads increase response size | High | Low | Accept for this backward-compatible pilot; redesign only if measured client limits require it. |
| Hand-written schema drifts from `VideoTranscriptData` | Medium | Medium | Assert the full schema in the existing tool-list test and update both together in future work. |
| Client rejects a schema/result mismatch | Low | High | Run official SDK stdio smoke and a real local Codex client call. |
| Existing clients change behavior | Low | High | Preserve `content[0].text` exactly and leave all errors and other tools unchanged. |

## Dependencies And Blockers

**Dependencies:**

- Existing `VideoTranscriptData` produced by `getVideoTranscriptData`.
- Installed `@modelcontextprotocol/sdk` structured-output support.
- Existing Vitest handler and stdio test seams.

**Known blocker:**

- A valid, safely stored Bilibili credential is required for the real subtitle-backed client acceptance call. If credentials are invalid, implementation checks may pass but the ticket remains unaccepted until credentials are refreshed through the existing safe CLI flow.

## References

- `CONTEXT.md`
- `docs/agent-memory/decisions.md`
- `docs/research/2026-07-25-cross-platform-video-content-mcp-landscape.md`
- `src/server/tool-schemas.ts`
- `src/server/tool-handlers.ts`
- `src/bilibili/types.ts`
