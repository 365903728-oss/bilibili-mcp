# Agent Communication

This file defines the evidence and handoff protocol shared by all three Harness
adapters. `RULES.md` remains normative.

## Mode Flows

### `codex-direct`

Codex plans, writes, verifies, reviews, accepts, and creates the accepted local
commit. Subagents are read-only unless explicitly assigned the one writer
lease. Substantial work uses a unified execution report; no synthetic
Codex-to-Codex handoff is required.

### `claude-direct`

Claude Code plans, writes, verifies, reviews, accepts, and creates the accepted
local commit. Project subagents remain bounded and cannot introduce a second
writer. Substantial work uses a unified execution report.

### `codex-paseo-claude`

1. Codex creates a bounded handoff referencing the GitHub Issue and typed
   contract.
2. Codex reads live Paseo preferences and launches one Claude writer.
3. Claude returns a report and uncommitted diff.
4. Codex reviews the actual diff/evidence and accepts or returns same-scope
   repair to the same writer.
5. Only after Codex acceptance is a focused local commit created. The
   collaboration guard rejects Claude `local-commit` in every lifecycle state;
   only Codex may reach the shared accepted-state commit gate.

Paseo failure produces a Recovery Bundle and stop. It never causes an automatic
adapter switch.

## Artifact Locations

Unified execution and acceptance reports:

```text
docs/agent-memory/executions/YYYY-MM-DD-<task>-<mode>-report.md
```

Collaboration-only handoffs and Claude reports:

```text
docs/agent-memory/handoffs/YYYY-MM-DD-<topic>-codex-to-claude.md
docs/agent-memory/handoffs/YYYY-MM-DD-<topic>-claude-report.md
```

Narrow tasks may report in chat. Multi-file, security, MCP, package, release,
Harness, or delegated tasks use file-backed evidence. A GitHub Issue remains the
planning source; do not duplicate it as a local prose ticket.

## Handoff Template (`codex-paseo-claude` only)

```markdown
# Codex To Claude Handoff: <topic>

## Typed Contract
- Task/source:
- Mode: codex-paseo-claude
- Canonical worktree/base:
- Writer lease: claude
- Acceptance owner: codex
- Authority/repair bound:
- Required manual Skill evidence:

## Objective And Acceptance Criteria
## Current State And Files To Inspect
## Files To Edit / Do Not Touch
## Required Capabilities
## Execution Steps
## Verification Commands
## Risks And Rollback
## Stop And Report If
## Expected Report
```

## Unified Execution Report Template

```markdown
# Execution Report: <task>

## Contract
- Task/source:
- Mode:
- Canonical worktree/base:
- Writer/acceptance owner:
- Terminal state:

## Summary
## Files Changed And Diff Scope
## Commands And Results
## Acceptance Criteria
## Repairs And Failure Fingerprints
## Risks, Skipped Checks, Recovery Bundle
## Capabilities Used
- Manual Skills and invocation evidence:
- Model-invoked Skills:
- Agents/reviewers:
- MCP/tools/CLI:

## Harness Artifacts
- Research:
- Security:
- Codemap:
- Memory:
- Harness eval:

## Local Commit
```

## Collaboration Closure Evidence

For `codex-paseo-claude`, a bridge trigger proves only that Codex froze and
recorded the intended native `/implement` ordering. Final acceptance also
requires the Paseo/Claude activity record to show `/implement` on the Claude
host, plus live inspection of the frozen agent ID/provider/model/mode/cwd.

The controller validates the file-backed writer report against the current
diff and frozen run. Raw handoff/review prompts are ephemeral: keep only their
digests and prepared/sent sidecars, remove prompt files on every send exit, and
enter recovery instead of automatically replaying an ambiguous send. A real
closure pilot uses a disposable zero-remote Harness-only repository and proves
one accepted local commit, exact changed paths, a released lease, and no remote
effect.

If the user explicitly changes provider/model after launch, treat it as a
writer-lease transition. Paseo 0.2.5 can update thinking but not the model of an
existing agent: require the current writer to be idle, release its logical
lease, create exactly one replacement with the runtime override, live-inspect
the exact provider/model/mode/cwd, then dispatch. Keep provider/model out of
tracked contracts, rules, and config; execution reports may record the resolved
route as evidence.

## Evidence Rules

- Reports derive from the final diff and actual command results.
- Include skipped checks and unresolved risk; do not accept an executor's
  unsupported "done" claim.
- Runtime event logs are not completion reports and `Stop` is not acceptance.
- Handoffs/reports cannot expand scope or authority.
- Never include secrets, raw Cookies, `.env` values, tokens, SSH material,
  private credentials, or unredacted runtime payloads.

## Typed Memory Communication

Typed memory uses two accepted-ticket identities. The source task prepares a
bounded `harness.memory-evidence/v1` envelope, obtains its canonical digest from
the shared CLI, and records that digest as passing current verification evidence
before acceptance. Its final commit SHA is added only after the source task is
accepted and committed.

A separate memory-only Codex Direct task then projects that exact envelope. It
may change only `docs/agent-memory/typed-memory.json` and
`docs/agent-memory/current-memory.json`; a replay that changes neither is still
a successful metadata-only audited result. The memory task uses the normal
review, criterion, acceptance, and exact-one-commit gates rather than a new
controller.

Communicate only typed candidate fields and normalized results across this
boundary. Do not pass raw commands, stdout/stderr, prompts, environment dumps,
Cookies, tokens, credentials, Hook payloads, or free-form model conclusions.
Proposed/deferred records are review material, never startup instructions.
