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
5. Only after Codex acceptance is a focused local commit created.

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

## Evidence Rules

- Reports derive from the final diff and actual command results.
- Include skipped checks and unresolved risk; do not accept an executor's
  unsupported "done" claim.
- Runtime event logs are not completion reports and `Stop` is not acceptance.
- Handoffs/reports cannot expand scope or authority.
- Never include secrets, raw Cookies, `.env` values, tokens, SSH material,
  private credentials, or unredacted runtime payloads.
