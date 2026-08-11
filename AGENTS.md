# Codex Adapter

<!-- harness-adapter: codex; shared-core: RULES.md; contract: harness.task-contract/v1 -->

Codex does not currently provide a repository-file import directive. Before any
substantive work, read `RULES.md` completely; it is the shared and authoritative
Harness core. This file contains only Codex-specific behavior.

## Modes Owned By This Adapter

In `codex-direct`, Codex plans, holds the only writer lease, implements,
verifies, reviews, accepts, and then creates the focused local commit.

In `codex-paseo-claude`, Codex plans and owns acceptance while one
Paseo-managed Claude Code agent holds the implementation writer lease. Codex
must not edit overlapping files while Claude runs and must return review
findings to that same writer for bounded repair.

Codex must ask the user once before the first implementation write when no mode
was already selected. It must not launch Claude, restart Paseo, or fall back to
another adapter without authority.

## Codex Capability Rules

- Use the active Codex Skill catalog; do not assume `.agents/skills`,
  `.codex/skills`, and Claude's Skills are synchronized.
- A Matt Skill marked `allow_implicit_invocation: false` requires the user's
  native `$skill` invocation. When required but missing, use the shared CLI gate
  with host `codex` to emit one reminder and stop before governed writes.
- Use `.codex/agents/` for bounded planning, risk review, and release
  verification. These agents are read-only unless a ticket explicitly assigns
  a compatible writer lease.
- Explorers and reviewers do not become writers. Keep at most one active writer
  for a ticket.

For local facts use `rg`, Git, npm, Node, TypeScript, Vitest, and the shared
Harness CLI. Use live GitHub tooling for Issues/PRs/runs and current official
documentation for behavior that may have changed.

## Paseo Controller Delta

Before a collaboration launch:

1. resolve the current user's home directory, read
   `.paseo/orchestration-preferences.json`, and use `providers.impl` unless the
   user selected a provider;
2. check Paseo availability without restarting its daemon;
3. create a bounded file-backed handoff referencing the Issue and typed task
   contract;
4. launch one implementation agent;
5. preserve the writer lease until the agent stops and its diff/report are
   captured;
6. review the actual diff and verification evidence before acceptance.

Do not encode the resolved provider/model in repository rules or contracts.
If Paseo or Claude fails, capture a Recovery Bundle and stop; do not silently
switch to `codex-direct`.

## Hook Adapter

`.codex/hooks.json` is a thin portable translator. It resolves the current Git
worktree and sends bounded stdin JSON to `harness/cli.py`. The shared CLI owns
normalization, redaction, context attribution, and persistence.
