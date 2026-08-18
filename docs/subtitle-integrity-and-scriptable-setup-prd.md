# Product Requirements Document: Subtitle Integrity And Scriptable Setup

**Version**: 1.2
**Date**: 2026-08-18
**Author**: Codex using `product-requirements`
**Quality Score**: 96/100

Revision 1.1 (2026-08-18): title-topic lexical overlap is removed as a hard
rejection gate — it false-accepted unrelated tracks (cooking video vs Python
tutorial) and false-rejected valid same-language discussion. Stability via
collision-free canonical comparison and the conservative language check remain;
a stable same-language semantic mismatch is an accepted limitation controlled
by the caller through `force_asr` / `exclude_ai_subtitles`.

Revision 1.2 (2026-08-18): AI classification widens from `ai-zh` to every
`ai-*` language code. Live authenticated read-only evidence: public
`BV15kyBB5Eg8` exposes subtitle languages `[ai-zh, ai-en, ai-ja, ai-es, ai-ar,
ai-pt]`, and the ai-zh-only classifier silently selected `ai-en` under
`exclude_ai_subtitles` — violating the AI-vs-human distinction. Every selected
`ai-*` track is double-read for stability; the conservative Han-ratio language
check applies to `ai-zh` only, and valid `ai-en`/`ai-ja` bodies are not
rejected for being non-Chinese.

## Executive Summary

Complete GitHub Issue #40 and the directly named Roadmap defects. Bilibili
`ai-*` tracks (`ai-zh`, `ai-en`, …) must remain visibly distinct from Human Subtitles, and their
content must be rejected when deterministic stability or conservative language
signals show that the track is unusable; a stable same-language semantic
mismatch is an accepted limitation. Explicit ASR fallback then handles the
selected Part, while `force_asr` remains the deterministic caller override.

Make `setup` scriptable without accepting credentials in argv. A new explicit
non-interactive mode uses credentials already supplied through the supported
environment/global-config sources and optionally installs one allowlisted ASR
model chosen by flag.

## Requirements Quality

- Business Value & Goals: 28/30
- Functional Requirements: 25/25
- User Experience: 18/20
- Technical Constraints: 15/15
- Scope & Priorities: 10/10

The observed failure, public behavior, security boundary, deterministic test
seams, compatibility rules, and delivery gates are explicit. No further product
choice is required before implementation.

## Problem Statement

Issue #40 shows that Bilibili AI tracks (`ai-zh` and other `ai-*` languages)
and Human Subtitles share the same public source label. The Roadmap adds a more serious failure: one Video returned unrelated,
changing AI subtitle bodies repeatedly, yet track presence prevented ASR and
the MCP returned the body unchanged.

The current candidate separates `ai_subtitle`, adds AI exclusion and
`force_asr`, but checks stability only with explicit ASR fallback. That still
allows a default transcript or video-info call to return a known-bad AI body.
It also does not address stable, high-confidence language mismatches;
title-topic lexical overlap is a documented accepted limitation, not a
rejection signal.

Separately, `setup` rejects all non-TTY invocations, so automation cannot use
the existing environment credential source and select an ASR model without
driving hidden prompts.

## Success Metrics

- No selected `ai-*` body is returned until it passes deterministic integrity
  assessment; Human Subtitles keep the existing single-read path.
- An unusable AI track never exposes its text and follows the existing explicit
  ASR/description fallback contract.
- A changing body, a canonical-normalization collision, and a high-confidence
  Chinese-language mismatch each have a red-before-green regression through
  transcript and/or video-info public interfaces; a stable same-language body
  is accepted regardless of title topic.
- Inconclusive short/generic titles and short bodies are accepted rather than
  guessed invalid.
- `setup --non-interactive` works with a non-TTY stdin when credentials are
  already loadable; `--asr-model tiny|base|small` selects the only optional ASR
  work.
- No credential value appears in argv, stdout, stderr, tests, docs, or reports.
- Existing interactive setup, ten MCP tools, defaults, dependencies, model
  allowlist, and release state remain unchanged.

## Public Contract

### AI subtitle integrity

`data_source`, `exclude_ai_subtitles`, and `force_asr` keep the Issue #40
candidate contract. Integrity assessment is not a new caller switch:

1. Every selected Bilibili AI Subtitle is read twice.
2. Different normalized timing/text bodies are unusable.
3. A stable body with at least 80 Unicode letters and under 10% Han letters is
   unusable as an `ai-zh` language mismatch. This language check applies to
   `ai-zh` only; other `ai-*` languages are not rejected for being
   non-Chinese.
4. Title-topic lexical overlap is not assessed. A stable same-language body is
   accepted even when it does not discuss the video title topic; callers
   control this residual risk with `force_asr` or `exclude_ai_subtitles`
   (accepted limitation, see Risks).
5. If a threshold is not met, the signal is inconclusive and must not reject
   the body.
6. Integrity processing never logs or returns comparison text, tokens, hashes,
   or signed subtitle URLs.

When unusable:

- `get_video_transcript` + `fallback_to_asr: true` runs existing ASR.
- Otherwise transcript follows existing `fallback_to_description`; without an
  authorized fallback it returns `SUBTITLE_UNAVAILABLE`.
- `get_video_info` returns its existing description result and does not cache
  the unusable result.
- Second-read HTTP, timeout, authentication, and parse errors remain visible;
  they are not converted to integrity failure or ASR.

### Scriptable setup

Add to `setup`:

```text
--non-interactive
--asr-model <tiny|base|small>
```

- Non-interactive mode never calls hidden prompts and never reads credentials
  from stdin or argv.
- Credentials must already be loadable through supported environment variables
  or global config. Missing/unloadable credentials produce exit code 1 and
  actionable value-free guidance.
- Without `--asr-model`, non-interactive setup performs no ASR installation and
  exits successfully once credential readiness is confirmed.
- With `--asr-model`, run the existing allowlisted installer exactly once.
- `--asr-model` without `--non-interactive` is rejected with value-free usage
  guidance rather than silently changing the interactive flow.
- Existing interactive setup behavior remains unchanged.

## Test Seams

- `getVideoTranscriptData()` and `getVideoInfoWithSubtitle()` with injected
  Bilibili/ASR boundaries; no private-helper tests.
- `setupCredentials()` plus the Commander `createCli()` interface for option
  declaration/validation.
- One post-build child-process smoke with piped stdin and synthetic environment
  credentials; output is checked not to contain their values.

## Out Of Scope

- LLM, embeddings, remote classifiers, new dependencies, configurable
  thresholds, public integrity scores, or arbitrary language detection.
- Validation of Human Subtitles, subtitle correction, multi-read voting, or
  persistence of subtitle fingerprints.
- Credentials on command lines or stdin, JSON credential import, new credential
  storage, model IDs outside the existing allowlist, or background installation.
- New MCP tools, package version, commit, push, PR, Issue mutation, release, or
  publication.

## Risks

| Risk | Mitigation |
|---|---|
| Semantic false positive | Accepted limitation: stability and conservative language checks only; title-topic lexical overlap is not a gate. Inconclusive means usable; callers control residual risk via `force_asr` / `exclude_ai_subtitles`; ASR remains explicit. |
| AI request cost doubles | Only Bilibili AI Subtitles are re-read; Human Subtitles remain one request. |
| Transport failure hidden as corruption | Exceptions remain visible and never authorize ASR. |
| Credential leakage in automation | Existing env/global sources only; no argv/stdin credential values; secret scan and child smoke. |
| Interactive setup regression | Preserve the old path and its tests; non-interactive behavior is explicit. |
