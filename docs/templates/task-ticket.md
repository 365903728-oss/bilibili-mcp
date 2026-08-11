# Task Ticket Template

Use this template when a PRD, roadmap phase, or broad plan needs to be split into independently executable tickets.

Project standard:

- Task takes 30 minutes or less and has no public behavior change: no task ticket required; a direct Codex handoff is enough.
- Task touches multiple files, tests, security, package/release workflow, or MCP tool behavior: use a task ticket.
- Task comes from a PRD, roadmap, multi-task split, or Claude Code loop workflow: task ticket is required.

Use a light ticket for medium tasks by filling only objective, scope, files, acceptance criteria, verification, and stop/report conditions. Use the full template for broad, dependent, risky, or loop-executed work.

## Ticket

- ID:
- Title:
- State: `draft | ready | mode-frozen | baselined | executing | verifying | reviewing | repairing | accepted | blocked | cancelled | recovery-required`
- Source:
- Parent plan or PRD:
- Blocking tickets:
- Blocked by:

## Execution Contract

- Execution adapter: `codex-direct | codex-paseo-claude | claude-direct`
- Canonical worktree (absolute):
- Base SHA (full):
- Active writer lease: `none | codex | claude`
- Acceptance owner: `codex | claude`
- Adapter switch policy: `stop-and-report`
- Repair bound and early-stop fingerprint:
- Required manual Skills, host (`codex | claude`), and native invocation evidence:
- Authority: local read/write/build/test allowed; local commit after acceptance;
  push/PR/tag/release/publish require user approval; credentials/SSH/broad
  deletion/history rewrite blocked.

## Objective

State the smallest user-visible or maintainer-visible outcome this ticket must produce.

## Scope

In scope:

-

Out of scope:

-

## Files To Inspect Or Edit

Expected inspect:

-

Expected edit:

-

Do not touch:

-

## Required Capabilities

Skills:

-

Subagents:

-

MCP/tools/CLI:

-

If a listed capability is unavailable, report it and use the closest safe fallback.

## Execution Steps

1.
2.
3.

## Acceptance Criteria

- [ ]
- [ ]
- [ ] Public MCP tool names, input schemas, and response shapes remain stable unless explicitly changed.
- [ ] Credentials, Cookies, tokens, `.env` content, and private values are not printed or committed.
- [ ] `docs/agent-memory/codemap.md` is updated if module ownership, MCP tool flow, tests, package/release files, or harness structure changed; otherwise the report says it was checked and left unchanged.

## Verification

Required commands:

```bash
npm run build
npm test
```

Additional commands when relevant:

```bash
npm pack --dry-run
```

Manual checks:

-

## Risks And Rollback

Risks:

-

Rollback:

-

## Stop And Report Conditions

Stop before editing or continue only after user/Codex decision if:

- the implementation requires a public behavior change not described in this ticket
- a real credential or secret is found in tracked files
- required verification fails for unclear reasons
- the task requires a broader refactor than the ticket describes
- a required capability or subagent is unavailable and no safe fallback exists
- the frozen execution adapter fails or would need to change
- the active writer lease cannot be proven exclusive

## Completion Report

Return:

- files changed
- commands run and results
- skipped checks and why
- subagent/skill/tool capabilities used
- codemap update status
- unresolved risks or decision points
- selected adapter, base SHA, canonical worktree, writer, and acceptance owner
- acceptance-criteria judgment and local commit status
