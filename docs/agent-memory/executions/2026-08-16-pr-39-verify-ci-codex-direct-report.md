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
- Adapter and Evolution shards were not repeated locally; the current PR HEAD
  already carries their accepted evidence, and the new live workflow runs both
  shards on Windows and Ubuntu before delivery is declared complete.

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

## Risks, Skipped Checks, Recovery Bundle

- GitHub is authoritative for final workflow schema acceptance and hosted
  runner behavior. The repair push will be monitored; any failure is a
  blocking delivery result, not a green claim.
- Rollback is one scoped revert of the CI commit. No Recovery Bundle is needed.

## Capabilities Used

- Model-invoked Skills: `bilibili-mcp-memory`, `github-actions-docs`,
  `git-publish`.
- Agents/reviewers: none before commit; Codex cloud review will be requested
  after the authorized push because workflow files are a supply-chain surface.
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

Pending exact-diff acceptance.
