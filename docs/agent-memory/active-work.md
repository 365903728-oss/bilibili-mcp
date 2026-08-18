# Active Work

There is no active implementation or release task.

Status: `v1.12.0` is published to npm and GitHub Releases. Release commit
`a31fafb1f27ddb52cbca0abb0111dc4a73664da3` is on `master`; annotated tag
`v1.12.0` peels to that exact commit. GitHub Actions run `32107346010` passed
install, 41 files / 906 tests, build, and trusted npm publishing. npm `latest`
is `1.12.0` with registry signatures and SLSA provenance. The bilingual public
GitHub Release is non-draft, non-prerelease, and latest.

The release ships merged PR #42 / Issue #40 plus the related locally recorded
Issue #41 defects: every Bilibili `ai-*` track is distinguishable as
`ai_subtitle`; callers can exclude AI subtitles or force local ASR; selected
AI subtitle bodies are double-read for deterministic stability with a
conservative `ai-zh` language guard; and `setup` supports non-interactive,
credential-safe scripted use. The existing bounded ASR audio candidates and
actionable `ASR_AUDIO_UNAVAILABLE` guidance remain unchanged.

Known boundary: stable, same-language but semantically unrelated AI subtitle
bodies may still pass the deterministic integrity guard. This is documented
and controllable with `force_asr` or `exclude_ai_subtitles`; the release does
not claim general semantic topic validation.

Post-publication verification installed exact npm package `1.12.0` under Node
`22.14.0`, verified 97 registry signatures and 10 attestations, reported MCP
server version `1.12.0` with protocol `2025-06-18`, and listed the unchanged
ten-tool surface. No credential value was printed or recorded.

The Official MCP Registry now reports `1.12.0` as `active` and
`isLatest=true`, with the npm identifier and package version both matching the
public package. The dirty primary worktree and its future-only CI/CD roadmap
note remain outside the release.

## Future Direction — Not Active

The ASR, CLI, documentation, and security work shipped in `v1.11.0`.
Revisit MCP protocol modernization only as a separate GitHub Issue:

1. Preserve the public wire-level legacy baseline now covered by `initialize` → `tools/list` → `tools/call`; extend it only as part of the separate migration ticket.
2. Convert the dated MCP research into a dual-era acceptance matrix covering modern `server/discover`, required result/cache fields, and legacy fallback.
3. Only then migrate to the TypeScript SDK v2 dual-era stdio path.
4. Evaluate optional annotations, icons, additional structured outputs, Tasks, MRTR, or HTTP transport features only when a real product need exists.

Sources: `docs/research/2026-07-29-mcp-protocol-update.md`, `docs/research/2026-07-29-mcp-tools-evolution.md`, and the 2026-07-29 entries in `docs/agent-memory/decisions.md`.

This direction is not active work and does not authorize a code change, GitHub Issue, implementation-agent launch, commit, release, or protocol-support claim.
