# Active Work

Status: `v1.11.1` is published. Release commit `ce480f0` is a direct child of
PR #25's merge commit `15bb5f8`; annotated tag `v1.11.1` points to the release
commit, so the contributor's merged work remains intact. GitHub Actions run
`31019814806` passed tests, build, and npm trusted publishing. npm `latest` is
`1.11.1` with integrity, shasum, signature, and SLSA provenance, and the
non-draft bilingual GitHub Release credits `@CYL-collab` for Issue #24 and
PR #25.

Release verification passed the TypeScript build, 39 files / 803 tests,
13 focused video-API tests, production audit with zero vulnerabilities, a
181-file package with required dist entry points and no forbidden paths,
diff/UTF-8/value-free secret checks, two independent read-only reviews, and an
isolated exact-version CLI smoke exposing `setup`, `doctor`, and `config`.
The main user worktree and its review-gated learning-proposal change remained
outside the clean release worktree.

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
