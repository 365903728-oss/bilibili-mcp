# Execution Report: PR #39 verification CI

## Contract

- Task/source: user-authorized CI configuration on PR #39.
- Mode: `codex-direct`.
- Canonical worktree/base: isolated `7dcf` worktree at `bd8df8a20a1e403696edfae79b39f1f79f588692`.
- Writer/acceptance owner: Codex / Codex.
- Terminal state: accepted for commit and authorized push; the first live
  workflow run remains the delivery check and will be reported from GitHub.

## Summary

Added a read-only GitHub Actions `Verify` workflow. Product verification runs
on Ubuntu. Harness verification is split into core, adapters, and Evolution
and runs on both Ubuntu and Windows. A stable `Required` job fails unless all
product and matrix jobs succeed. Harness checkout retains full Git history so
the migration clean-room test can inspect its exact accepted #35 base.

## Files Changed And Diff Scope

- `.github/workflows/verify.yml`: PR/default-branch/manual triggers, minimal
  permissions, concurrency cancellation, product job, six Harness shards, and
  aggregate gate.
- `tests/publish-workflow-pins.test.ts`: enforce immutable action SHAs across
  every workflow rather than only publication.
- `docs/agent-memory/codemap.md` and `decisions.md`: durable CI ownership and
  rationale.
- This report. Product runtime, npm publication behavior, dependencies, and
  package contents are unchanged.

## Commands And Results

- YAML parse and required-job shape check: PASS.
- Focused workflow-pin Vitest: 1/1 PASS.
- Full Vitest: 41 files / 862 tests PASS.
- `npm run build`: PASS.
- `npm pack --dry-run`: PASS, 185 files; no Harness or agent-memory paths.
- Windows Harness core shard: 92 tests PASS, 11 expected platform skips.
- Migration conformance after durable-memory receipt refresh: 1/1 PASS.
- `git diff --check`: PASS.
- Windows adapters shard after the hosted-run repair: 153 tests PASS, 2
  expected platform skips.
- Typed-memory module after the final review repair: 40 tests PASS, 2 expected
  platform skips; migration conformance 1/1 PASS.
- Final Paseo/safe-I/O review repair: Paseo function tests 57/57 PASS; Windows
  Hook-event tests 23 PASS with 10 platform skips; WSL Hook-event tests plus
  the environment regression 24 PASS with 2 platform skips; migration
  conformance 1/1 PASS.
- After the first environment-isolation push, Paseo CLI tests pass 22/22 on
  both Windows and WSL with a file-backed disposable fake configuration.
- HEAD-bound startup-memory repair: the full Windows memory module passes
  42/42 with two expected platform skips; WSL projection tests pass 40/40 with
  one expected platform skip; accepted-gap Evolution checks pass 2/2 on
  Windows.
- MCP tools/list cursor repair: bounded schema test 1/1 and the real
  four-surface, three-adapter process-boundary lifecycle 1/1 PASS.
- Final hard-link/MCP frame repair: acceptance and canonical staging reject
  single-path hard links to external inodes; malformed UTF-8 and JSON frames
  are discarded while later valid initialize/ping frames complete. Adjacent
  CRLF, symlink, filter, index-recovery, and exact-commit regressions pass.

## Acceptance Criteria

- Pull requests and `master` pushes receive deterministic verification: PASS.
- Product build, tests, and package dry-run are covered: PASS.
- Harness core/adapters/Evolution run on Windows and Ubuntu without one
  monolithic job: PASS.
- Workflow has no secrets or write permission and uses `pull_request`, not
  `pull_request_target`: PASS.
- Official actions are pinned to verified full commit SHAs: PASS.
- Superseded branch runs are cancelled and one stable gate is exposed: PASS.

## Repairs And Failure Fingerprints

- Initial matrix composition mixed an `os` axis with partial `include` rows,
  which could create rows without an OS. It was corrected before execution to
  six explicit, complete matrix rows.
- First live run `31941296075` correctly failed both core jobs after this
  report's codemap/decision updates made their migration receipts stale. The
  same test reproduced locally; the two LF-normalized durable-memory digests
  and outer migration digest were refreshed and the focused test passed.
- Second live run `31941505324` passed product and five Harness matrix jobs but
  exposed that GitHub's Windows runner spells the same temporary directory as
  both `RUNNER~1` and `runneradmin`. The shared link guard now expands existing
  Windows 8.3 path prefixes before containment checks while retaining its
  junction/symlink rejection. Three focused regressions and the complete local
  adapters shard pass.
- Final Codex Review found one remaining pathname directory-creation race in
  typed memory. A Windows junction regression reproduced external
  `agent-memory` creation before the anchored writer rejected the path. Both
  tracked memory artifacts and transaction markers now reuse the shared
  no-follow directory creator; Windows focused checks pass 3/3 with one
  expected POSIX-only skip, and WSL passes 3/3.
- The next review found inherited credential exposure at the Paseo process
  boundary and missing POSIX directory durability after atomic replacement.
  Every Paseo call now receives one explicit platform/configuration allowlist,
  while `safe_io` fsyncs its verified parent descriptor after replacement.
  Synthetic credential and directory-fsync red tests reproduced both gaps;
  the repaired tests and a real read-only Paseo status/preflight call pass.
  Preflight reported the existing `daemon_not_running: stale_pid` without a
  restart, provider switch, fallback, or implementation write.
- GitHub run `31995957515` then exposed that legacy CLI tests configured their
  disposable fake Paseo through inherited `PASEO_FAKE_*` variables. Production
  code correctly removed those variables, so the test fake was moved to an
  adjacent private JSON config instead of weakening the allowlist. The exact
  Ubuntu failure reproduced in WSL; Windows and WSL CLI suites now pass 22/22.
- The next Codex review reproduced a POSIX task-directory replacement between
  pending-intent persistence and anonymous prompt creation. Prompt files now
  use the active lock directory descriptor for exclusive creation and unlink,
  and the task directory is revalidated immediately before and after send.
  A post-send identity failure is converted to the collaboration error family,
  preserving the existing CLI recovery-required transition.
  The focused race test fails on the old path and passes after the repair;
  Windows and WSL Paseo function suites pass 59/59 (one Windows-only skip).
- The following review found a redundant pathname `mkdir` after Direct start
  had already acquired its task-directory lock. A POSIX ancestor-swap red test
  proved the old path created the task hash outside the worktree. Removing that
  one call leaves directory creation to the descriptor-safe lock helper; the
  existing link check now rejects the swap before state or external writes.
- The next review found that startup memory trusted `git status`, whose clean
  comparison may apply configured filters. A self-consistent forged pair with
  a simulated clean status reproduced the bypass. Startup now compares both
  bounded raw working-tree artifacts byte-for-byte with their Git `HEAD` blobs
  before parsing. Independent review then reproduced a legitimate Windows
  `core.autocrlf=true` checkout whose CRLF working bytes would fail that strict
  comparison. Repository attributes now fix both formal-memory paths to LF;
  fresh-checkout and forged-pair regressions cover both sides of the boundary.
- The following MCP review found that `tools/list` rejected the pinned SDK's
  optional pagination cursor. The Harness now accepts a control-free cursor up
  to 2048 characters and deliberately returns the complete tool set as one
  page without `nextCursor`; malformed and oversized cursors fail closed.
- The latest review found that an owned file created as a hard link after the
  pre-write guard could be reopened by acceptance and Git staging, and that a
  malformed MCP frame ended the stdio process. Acceptance now performs one
  parent-anchored, descriptor-bound, single-link read and constructs the
  isolated Git index only from those captured bytes. POSIX holds a no-follow
  parent descriptor and Windows holds the verified directory HANDLE chain, so
  ancestor replacement cannot redirect the read. MCP decoding/JSON failures
  are contained to the offending frame, matching the pinned SDK transport's
  session behavior.
- The next review required accepted snapshots to retain metadata-change time
  and all bounded structural/protocol MCP failures to remain per-frame. Direct
  snapshots now persist POSIX ctime or Windows `FILE_BASIC_INFO.ChangeTime`,
  and MCP returns `-32600`/`-32602` when an ID is safely available before
  continuing. The failing Windows adapters shard also reproduced locally: the
  controller removed the test's safe null-device Git-config disable markers,
  read host `core.autocrlf`, and installed an LF index beside a CRLF worktree.
  Git environment sanitization now preserves only those exact disable sentinels;
  all three failed Direct/Claude lifecycle assertions pass locally.
- Hosted Windows adapters then exposed one error-shape regression: the verified
  directory chain correctly rejected a linked parent, but leaked the shared
  safe-I/O `ValueError`. The accepted-path snapshot entry now converts parent
  chain failures into one bounded `CodexDirectAdapterError`; the cross-platform
  regression asserts that public adapter boundary.
- After the repair push, PR #39 became merge-conflicted with the already accepted
  product v1.12.0 lineage on `master`, so GitHub did not create a new check suite.
  A non-rewriting merge retains the Harness history and the newer product/release
  facts; the five durable-memory conflicts are append-only factual unions. The
  package receipt is regenerated from the merged v1.12.0 dry-run bytes.

## Risks, Skipped Checks, Recovery Bundle

- GitHub is authoritative for final workflow schema acceptance and hosted
  runner behavior. The repair push will be monitored; any failure is a
  blocking delivery result, not a green claim.
- Rollback is one scoped revert of the CI commit. No Recovery Bundle is needed.

## Capabilities Used

- Model-invoked Skills: `bilibili-mcp-memory`, `github-actions-docs`,
  `git-publish`.
- Agents/reviewers: one independent read-only risk reviewer returned PASS with
  no reproducible P0-P3; Codex cloud review will be requested after the
  authorized push because Harness/CI files are security-sensitive surfaces.
- MCP/tools/CLI: local Git/npm/Node/Python, official GitHub documentation, and
  read-only `gh` action-ref/PR inspection.

## Harness Artifacts

- Research: current official GitHub workflow/security/concurrency docs and
  live official action tag resolution.
- Security: `contents: read`, no persisted checkout credentials, no secrets,
  no privileged PR trigger, immutable third-party actions.
- Codemap/memory: updated.
- Harness eval: no evaluator or holdout change.

## Local Commit

- `f77db023ef351ab452a566d3ee561df0405bfbb4`: CI workflow and durable record.
- `70fe1b644a32269163a05d873009af0275c37363`: migration receipt refresh.
- This report is committed with the final Windows 8.3 compatibility repair.
