# Active Work

Status: `v1.11.0` is published. Release commit `e43c247` contains ASR Phase 1–3,
the CLI setup/doctor flow, both security-remediation rounds, the bilingual
documentation refresh, and the README overview Hero. Annotated tag `v1.11.0`
points to that commit; GitHub Actions run `31003552987` passed and published npm
through trusted publishing. The GitHub Release title and notes are bilingual.

Release verification passed the TypeScript build, 39 files / 803 tests, 95
focused stdio/tool/handler tests, production audit with zero vulnerabilities,
an 181-file package containing all five README images and no forbidden paths,
diff check, value-free secret classification, and zero ASR state temp residue.
npm `latest` is 1.11.0 with registry integrity and SLSA provenance.

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
