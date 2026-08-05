# Product Requirements Document: ASR Transcription Fallback Phase 3

**Version**: 1.0
**Date**: 2026-07-29
**Author**: Codex using `product-requirements`
**Quality Score**: 97/100

## Executive Summary

Extend the existing `get_video_transcript` tool with an explicit,
default-off `fallback_to_asr` option. Native Bilibili CC/AI subtitles remain
first priority. Only a definitively unavailable subtitle state may start one
bounded local transcription of the already resolved Part/CID.

The fallback uses the existing ready, allowlisted faster-whisper installation.
It retrieves one temporary audio-only representation, transcribes it through
the managed Python environment on CPU INT8, converts validated segments into
the existing transcript segment pipeline, and removes every temporary artifact
on all exit paths.

## Requirements Quality

- Business Value & Goals: 28/30
- Functional Requirements: 25/25
- User Experience: 19/20
- Technical Constraints: 15/15
- Scope & Priorities: 10/10

The contract, fallback precedence, safety limits, error behavior, compatibility
rules, test matrix, and explicit exclusions are frozen. No further product
choice is required before implementation.

## Problem Statement

Phase 1 and Phase 2 can install and identify an allowlisted faster-whisper
model, but videos without usable Bilibili subtitles still end at
`SUBTITLE_UNAVAILABLE`. The missing capability is the safe end-to-end path from
one selected Bilibili Part to temporary audio, managed local transcription, and
the existing MCP transcript response.

The implementation must not make ordinary transcript calls expensive, hide
network or credential failures as "no subtitles", download or switch a model
inside MCP, retain media, or change the other nine tools.

## Success Metrics

- Existing callers that omit `fallback_to_asr` make zero ASR state, playback,
  media, temporary-file, or subprocess calls.
- Usable native subtitles always win, including when ASR is requested.
- A confirmed no-subtitle state plus `fallback_to_asr: true` reaches ASR once
  for exactly the resolved Part/CID.
- Successful ASR returns `data_source: "asr"` and reuses timestamp, range,
  keyword/context, source URL, and timestamp URL behavior.
- Cookie, HTTP, timeout, parse, anti-bot, and generic subtitle errors never
  trigger ASR.
- Every success, failure, timeout, and cancellation path removes its unique
  temporary directory and partial audio.
- No MCP call downloads, switches, or accepts a model ID.
- Deterministic tests require no real Cookie, network, Python, model, or audio.
- Build, focused/full tests, package, audit, stdio, schema, and secret gates
  pass without changing tool count or order.

## Users

- Agent user: explicitly opts into local ASR only when subtitle evidence is
  unavailable and receives the same structured transcript shape.
- Local operator: installs one allowlisted model through `setup`, diagnoses it
  through `doctor --json`, and controls the CPU/storage tradeoff.

## Public Contract

### Input

Add one optional boolean to `get_video_transcript`:

```json
{
  "fallback_to_asr": false
}
```

- Default is `false`.
- Invalid non-boolean input is rejected before network or process work.
- No new MCP tool is added.
- `get_video_info` never invokes ASR.

### Success

- Add `"asr"` to the successful `data_source` enum.
- Preserve `content[0].text` JSON equality with `structuredContent`.
- Reuse optional `language` for faster-whisper's detected language.
- Do not add model, path, runtime, confidence, or audio metadata to the public
  result.

### Precedence

1. Native usable Bilibili subtitle.
2. ASR, only when explicitly requested and the subtitle list, selected
   subtitle, or subtitle body is definitively empty.
3. Description, only when explicitly requested and ASR is not requested, or
   when both fallbacks are requested and playback reports a valid but empty
   audio-only set.

ASR readiness, limit, download, timeout, subprocess, or output-validation
failures remain visible. Generic subtitle/network/API failures remain visible
when ASR is requested and never become ASR input.

## Audio Acquisition

- Resolve one default/requested Part through the existing BVID/Part/CID path.
- Request the first-party `/x/player/playurl` DASH response for that BVID/CID
  with `fnval=16`, `fnver=0`, and `fourk=1`.
- Send the existing local Cookie only to the Bilibili API request. Never send
  it to the returned CDN URL or the Python child.
- Accept only HTTPS audio representations with a bounded Bilibili CDN host
  policy and supported MP4/AAC metadata.
- Choose deterministically by lowest positive bandwidth, then numeric ID.
  This is sufficient for speech recognition and minimizes temporary transfer.
- Try only the selected representation's base URL and at most two backups.
- Follow at most three validated HTTPS redirects.
- Never log, return, persist, or place a signed media URL in an error.

## Frozen Limits

| Limit | Value |
|---|---:|
| One Part duration | 7,200 seconds |
| Audio bytes | 128 MiB |
| Media URL candidates | 3 |
| Redirects per candidate | 3 |
| Audio download timeout | 120 seconds |
| Transcription timeout | 30 minutes |
| Child stdout | 2 MiB |
| Child stderr retained | 2 KiB |
| ASR segments | 10,000 |
| Total transcript text | existing 500,000 characters |
| Concurrent active transcriptions | 1 |
| Waiting queue | 0 |

The byte limit is enforced from headers when possible and during streaming.
Duration is checked from both video metadata and playback metadata when
available. A concurrent ASR request receives a retryable busy error.

## Temporary File Lifecycle

- Use `mkdtemp` below the operating-system temporary directory with a fixed
  project prefix.
- Store only one partial/final audio file inside that request directory.
- In `finally`, resolve and validate the cleanup target as a direct child of
  the expected temp root before recursive removal.
- Cleanup runs after download, spawn, parse, validation, timeout, busy-free
  release, and success paths.
- Request cleanup must never target the managed venv, model/state directory,
  project checkout, home directory, or a path derived from BVID/CID.
- Absolute temp/model/credential paths never appear in MCP results.

## Managed Transcription

- Require `readAsrState()` to report `ready`; otherwise return actionable
  `setup` and `doctor --json` guidance.
- Use only `deriveAsrPaths().venv` and `.model`; accept no runtime/model input.
- Invoke managed Python with executable plus argv, `shell: false`, `-I`,
  filtered environment, ignored stdin, and piped stdout/stderr.
- Load the local model with `device="cpu"` and `compute_type="int8"`.
- Use a bounded newline-delimited JSON protocol: one metadata record, ordered
  segment records, and one completion record.
- Validate record order, exact allowed keys/types, finite non-negative
  timestamps, `end >= start`, monotonic ordering, segment/text/output limits,
  detected language length, process exit, and completion count.
- Kill the child on timeout or output overflow, await close, and then clean up.

## Error Contract

Use the existing text-only `isError` response path with bounded bilingual
guidance:

- `ASR_NOT_READY`
- `ASR_AUDIO_UNAVAILABLE`
- `ASR_LIMIT_EXCEEDED`
- `ASR_BUSY`
- `ASR_TRANSCRIPTION_TIMEOUT`
- `ASR_TRANSCRIPTION_FAILED`
- `ASR_OUTPUT_INVALID`

Errors include no Cookie, signed URL, child environment, raw unbounded stderr,
or absolute private path. Existing `COOKIE_EXPIRED`, validation, HTTP, timeout,
and retry semantics remain authoritative.

## Acceptance Criteria

- [ ] All ten tool names and their order remain unchanged.
- [ ] `fallback_to_asr` is optional boolean, default false.
- [ ] Native subtitles always prevent ASR work.
- [ ] Only definitive subtitle unavailability triggers ASR.
- [ ] Exactly one resolved Part/CID is used.
- [ ] ASR results reuse all existing transcript transformations and links.
- [ ] All frozen limits and error codes are directly tested.
- [ ] All temporary and partial files are removed on every exit path.
- [ ] Child env, argv, timeout/kill, stdout protocol, and concurrency are
      deterministic and tested.
- [ ] Successful text and structured output remain identical.
- [ ] `get_video_info` and the other nine tools make no ASR calls.
- [ ] No dependency, package version, SDK, transport, release, or model
      allowlist change occurs.

## Out Of Scope

- New MCP tools, MCP SDK v2/protocol migration, HTTP transport, Tasks, MRTR,
  annotations, or icons.
- Model download/switch during MCP, arbitrary model IDs, medium/large,
  multiple retained models, GPU/CUDA, global Python/pip, or bundled Python.
- Persistent audio, audio export, video download, multi-Part crawling,
  background jobs, queues, transcript caching, diarization, word timestamps,
  translation, or semantic search.
- Commit, push, PR, tag, version bump, npm publish, or GitHub Release.

## Risks

| Risk | Mitigation |
|---|---|
| Signed media URLs leak | Never log/return them; redact query-bearing CDN URLs defensively. |
| CDN redirects to unsafe target | Manual bounded redirects with HTTPS/host validation at every hop. |
| CPU exhaustion | One active transcription and no queue; duration/process limits. |
| Partial media remains | Unique temp directory and validated `finally` cleanup. |
| Child output is malformed or huge | Bounded NDJSON parser, kill on overflow, strict validation. |
| Upstream subtitle error triggers expensive fallback | ASR only from explicit definitive-unavailable branches. |
| Live endpoint changes | Dated first-party probe and refresh-before-release note. |
