# Active Work

Issue #40 + Roadmap (ROADMAP-2026-08-18-INTEGRITY-SETUP) have a verified,
uncommitted implementation candidate in isolated branch
`codex/issue-40-ai-subtitle-integrity`, based on `44ac1e7`. It separates
every Bilibili `ai-*` track (`ai-zh`, `ai-en`, `ai-ja`, …) as
`data_source: "ai_subtitle"`, adds default-off `exclude_ai_subtitles` to
transcript and video-info, adds transcript-only `force_asr`, and
unconditionally double-reads every selected `ai-*` body with a collision-free
canonical stability check plus a conservative language check (≥80 Unicode
letters and <10% Han → unusable) applied to `ai-zh` only — other `ai-*`
languages are not rejected for being non-Chinese. Title-topic lexical overlap
is not a rejection gate; a stable same-language semantic mismatch is an
accepted limitation controlled by `force_asr` / `exclude_ai_subtitles`. An
unstable body enters the existing ASR path; transport/parser errors remain
visible.
`setup --non-interactive` / `--asr-model <tiny|base|small>` is implemented:
it requires an env/global-config credential source with loadable credentials,
never prompts, and never reads credential values from stdin/argv. The candidate
passed the TypeScript build, 41 files / 906 tests, a 189-file package dry run,
and independent Codex standards/spec/risk reviews. It is not committed,
pushed, merged, released, or published.

The existing ASR download path already tries up to three bounded audio
candidates and exposes retryable bilingual `ASR_AUDIO_UNAVAILABLE` guidance,
so this candidate does not add another retry layer.

Status: `v1.11.4` is published to npm, GitHub Releases, and the Official MCP
Registry as `io.github.XZXZZX-Ai/bilibili-mcp`. Release commit `2a33520`
contains the five synchronized version fields, bilingual changelogs, and
release records for merged PR #26 and PR #27. Annotated tag `v1.11.4` peels to
that exact commit. GitHub Actions run `31296387097` passed tests, build, and npm
trusted publishing; npm `latest` is `1.11.4` with registry signature and SLSA
provenance. The public GitHub Release is non-draft/non-prerelease, and the
Official Registry reports `1.11.4` as `active` and `isLatest=true`.

The release publishes PR #26 for comments, language, credential, numeric-
config, dotenv-order, and endpoint-aware `-403` contracts, plus PR #27 for
fail-closed malformed search responses. Both remain merged through base commit
`1067e02`; the release metadata adds no runtime, dependency, workflow, README,
or ten-tool boundary change.

The local `1.11.4` candidate passed exact publish-runner Node `22.14.0` / npm
`11.18.0` clean install, build, 41 files / 862 tests, 2 files / 19 focused
stdio tests, a 185-file package, zero-vulnerability production audit, live
official Registry schema validation, strict UTF-8/diff checks, and scoped
credential scans. Credential-safe live MCP stdio calls reported a valid login,
three stable searches for `五道口纳什`, and real comment limits of 21 and 50
without printing Cookie values. Full development-tree audit findings remain
separately recorded in the release QA and are not production dependencies.
Independent release, standards/security, and specification reviews returned
PASS with no remaining P0-P3.

Post-publication verification installed exact npm package `1.11.4` in an
isolated directory, verified all 97 installed-package registry signatures and
10 attestations, and ran the package under Node `22.14.0`. MCP initialize
reported server `bilibili-mcp-server` version `1.11.4`, listed exactly ten tools,
and an authenticated live `五道口纳什` search returned five results containing
the target author. No credential value was recorded.

The published `v1.11.3` release verification passed the TypeScript build, 39 files / 803 tests,
production audit with zero vulnerabilities, a 181-file package with required
dist entry points and no forbidden paths, Registry metadata validation,
diff/UTF-8/value-free secret checks, two independent read-only reviews, and an
isolated exact-version CLI smoke. The main user worktree and its review-gated
learning-proposal change remained outside the clean release worktree.

The ten-tool product boundary and legacy stdio compatibility remain fixed. ASR
is explicit, default-off, native-subtitle-first, and ready-state-only. The local
doctor reports no ready model, so no model was downloaded or switched and no
live ASR end-to-end smoke was run. This is a documented validation boundary,
not unfinished Phase 3 implementation.

The pre-existing, review-gated `docs/agent-memory/pending-learning-proposals.md`
modification remains uncommitted and excluded from the release. Controlled
learning proposals remain manual. Files under `docs/superpowers/` are historical
records only and must not trigger any `superpowers:*` skill.

## Future Direction — Not Active

The ASR, CLI, documentation, and security work shipped in `v1.11.0`.
Revisit MCP protocol modernization only as a separate GitHub Issue:

1. Preserve the public wire-level legacy baseline now covered by `initialize` → `tools/list` → `tools/call`; extend it only as part of the separate migration ticket.
2. Convert the dated MCP research into a dual-era acceptance matrix covering modern `server/discover`, required result/cache fields, and legacy fallback.
3. Only then migrate to the TypeScript SDK v2 dual-era stdio path.
4. Evaluate optional annotations, icons, additional structured outputs, Tasks, MRTR, or HTTP transport features only when a real product need exists.

Sources: `docs/research/2026-07-29-mcp-protocol-update.md`, `docs/research/2026-07-29-mcp-tools-evolution.md`, and the 2026-07-29 entries in `docs/agent-memory/decisions.md`.

This direction is not active work and does not authorize a code change, GitHub Issue, implementation-agent launch, commit, release, or protocol-support claim.
