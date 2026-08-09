# Active Work

Status: `v1.11.3` is published to npm, GitHub Releases, and the Official MCP
Registry as `io.github.XZXZZX-Ai/bilibili-mcp`. Release commit `ac58a4b` is a
descendant of PR #25's merge commit `15bb5f8`, so the contributor's merged work
remains intact. GitHub Actions run `31032259381` passed tests, build, and npm
trusted publishing. The Official Registry reports version `1.11.3` as `active`
and `isLatest=true`.

Unreleased source delivery on 2026-08-09 comprises PR #26 for comments,
language, credential, numeric-config, dotenv-order, and endpoint-aware `-403`
contracts, plus PR #27 for fail-closed malformed search responses. Both are
merged through `origin/master` commit `1067e02`. An isolated local branch,
`codex/release-v1.11.4-prep`, now prepares five synchronized `1.11.4` version
fields, matching bilingual changelogs, and scoped release records. The
candidate is uncommitted and unpushed; npm, GitHub Releases, and the Official
Registry still expose only the published `1.11.3` artifacts. The user explicitly
authorized commit, push, annotated tag, npm, GitHub Release, and Official MCP
Registry publication on 2026-08-09, and the gated publication chain is in
progress.

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
