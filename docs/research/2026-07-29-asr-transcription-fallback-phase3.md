# Research Topic

- Topic: ASR Phase 3 playback and managed transcription contract
- Date: 2026-07-29
- Owner: Codex
- Related task: `docs/asr-transcription-fallback-prd.md`
- Refresh before: changing playback parameters, media host policy, runtime
  protocol, or publishing the feature

## Question

What first-party playback shape and official faster-whisper behavior should the
bounded Part-to-transcript implementation rely on?

## Context

Phase 1/2 already pin the runtime and three model snapshots. Phase 3 needs one
audio-only source and a strict local child protocol without exposing signed
URLs or depending on a real network/model in tests.

## Sources

| Source | Type | Date checked | Notes |
|---|---|---|---|
| `https://api.bilibili.com/x/web-interface/view` and `https://api.bilibili.com/x/player/playurl` | first-party live API output | 2026-07-29 | Read-only public probe for `BV1vL411G7N7`; no Cookie; signed URLs omitted from output and records. |
| One-byte Range request to the selected first-party-returned CDN URL | live media response | 2026-07-29 | Referer/User-Agent only, no Cookie; signed URL omitted. |
| [faster-whisper v1.2.1 README](https://github.com/SYSTRAN/faster-whisper/blob/v1.2.1/README.md) | official pinned source | 2026-07-29 | Retrieved through GitHub API at the exact pinned tag. |
| [Phase 1 official runtime/model research](2026-07-27-asr-model-installer-phase1.md) | cached official-source research | 2026-07-27 | Python 3.9+, PyAV decoding, CPU INT8, pinned runtime and small snapshot. |
| [Phase 2 official model research](2026-07-27-asr-model-selector-phase2.md) | cached official-source research | 2026-07-27 | Immutable tiny/base/small repositories and revisions. |

## Findings

### First-party Bilibili playback probe

- `/x/web-interface/view` returned one numeric CID for the selected public
  Video.
- `/x/player/playurl` with the exact BVID/CID plus `fnval=16`, `fnver=0`, and
  `fourk=1` returned `code: 0`, `timelength`, and `dash.audio`; it returned no
  legacy `durl` entries for this probe.
- The response contained three AAC-in-MP4 audio representations. Sorting by
  positive bandwidth then ID selected ID `30216` at `67,269` bits/s.
- The selected URL was HTTPS and query-signed. Its observed remaining lifetime
  was about 7,199 seconds. The raw URL and query were not printed or retained.
- A one-byte Range request with User-Agent and Bilibili Referer, but no Cookie,
  returned HTTP `206`, `Content-Range: bytes 0-0/5629437`, and no redirect.
- The playurl representation declared `audio/mp4`; the CDN response declared
  `video/mp4`. Validation must therefore accept the known MP4 container
  variation rather than require the header to equal the representation field.
- The playback metadata duration was `669,482` ms for this probe.

### Official faster-whisper v1.2.1

- The pinned README documents local CPU INT8 loading with
  `WhisperModel(..., device="cpu", compute_type="int8")`.
- `model.transcribe(audio_path, beam_size=5)` returns `segments, info`.
- Detected language is available as `info.language`; each segment exposes
  `start`, `end`, and `text`.
- `segments` is a generator and transcription starts/finishes only when it is
  iterated. The child must iterate to completion before reporting success.
- A local CTranslate2 directory can be passed directly to `WhisperModel`, so
  Phase 3 does not need a remote model ID or Hub lookup.

## Applicability To This Project

Applies:

- Keep the API Cookie on the playurl request only.
- Choose the lowest-bandwidth valid audio representation deterministically.
- Treat every returned media URL as short-lived sensitive data.
- Use manual bounded redirect validation and enforce byte limits while
  streaming.
- Pass only local model/audio paths through child argv.
- Emit language and segment start/end/text through bounded NDJSON.

Does not apply:

- The probe does not establish that every Video is anonymously accessible.
  Existing credential and Bilibili API errors remain authoritative.
- CDN hostname inventory and signed-query fields can change; do not assert one
  fixed host or query schema.
- GPU, batching, word timestamps, translation, remote model loading, and
  benchmark claims are outside Phase 3.

## Decision Impact

- Add a focused playback module that owns playurl parsing and representation
  selection.
- Add a focused transcription module that owns URL validation, transient audio,
  the managed child protocol, cleanup, limits, and concurrency.
- Keep fallback precedence in `subtitle.ts` so only definitive no-subtitle
  branches can invoke ASR.
- Add no npm dependency.

## Risks And Unknowns

- Some account-restricted Videos may require valid Cookies for playurl even
  though the public probe did not.
- CDN host families and response headers may vary. The implementation must keep
  a narrow reviewed host policy and fail closed on unknown targets.
- The live probe did not download a full file or transcribe it.
- A ready local model is currently absent, so live end-to-end ASR acceptance
  cannot run without a new large download.

## Staleness Notes

Refresh when Bilibili changes player endpoints/fields/CDN behavior,
faster-whisper changes from the pinned version, the model allowlist changes, or
the feature is prepared for release.

## Follow-Up

- [ ] Re-run a redacted live playurl structure probe before publication.
- [ ] Run one safe live ASR smoke only when `doctor --json` already reports a
      ready model.
