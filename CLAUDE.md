@RULES.md

# Claude Code Adapter

<!-- harness-adapter: claude; shared-core: RULES.md; contract: harness.task-contract/v1 -->

The imported `RULES.md` is the shared and authoritative Harness core. This file
contains only Claude Code-specific behavior.

## Claude Direct

When the user starts in Claude Code and requests end-to-end execution, treat the
entrypoint as selection of `claude-direct`: Claude plans, holds the only writer
lease, implements, verifies, reviews, accepts, and creates the focused local
commit. Do not ask for a redundant mode confirmation.

Use `python -m harness claude-direct` for `start`, guards, lifecycle evidence,
recovery, acceptance, and commit recovery. Never control a Claude Direct task
through `codex-direct` or fall back to that adapter after failure.

Use project agents under `.claude/agents/` only for bounded matching work. A
subagent that edits must be the recorded active writer, not an additional
writer. Read-only reviewers may run risk-weighted checks without a lease.

## Paseo-Managed Claude

When launched from a Codex/Paseo handoff, the mode is
`codex-paseo-claude`. The handoff, GitHub Issue, and typed contract define the
bounded task. Claude is the sole implementation writer; Codex is the acceptance
owner.

Return files changed, actual commands/results, skipped checks, risks, and all
acceptance evidence. If Codex requests same-scope repair, keep the existing
lease. Stop for scope expansion, product decisions, new authority, or adapter
failure. Do not commit until Codex has accepted the implementation and requests
the commit-only finalization.

## Permissions And Skills

`bypassPermissions` is the expected local runtime posture, but it does not
authorize remote writes, releases, credentials/SSH, broad deletion, history
rewrites, or scope expansion.

A Skill marked `disable-model-invocation: true` requires the user's native
`/skill` invocation. When a required manual Skill is missing, emit one bounded
reminder through the shared gate with host `claude` and stop before governed
writes. Never imitate or silently invoke it.

## Hook Adapter

`.claude/settings.json` is the tracked portable hook translator and uses
`${CLAUDE_PROJECT_DIR}`. Machine-local permission preferences may live in the
ignored `.claude/settings.local.json`, but local settings must not weaken the
shared constitutional boundary. The shared CLI owns normalization, redaction,
worktree attribution, and persistence.

Run `python -m harness doctor` before enabling tracked Hooks in an existing
checkout. An overlapping legacy local Hook registration is a migration conflict
and must not run beside the tracked translator.
