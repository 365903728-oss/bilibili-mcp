# Agent Memory

This directory is the repository-local learning and memory system for `@xzxzzx/bilibili-mcp`.

It exists so Codex and Claude Code can preserve durable project facts, decisions, lessons, handoffs, and verification history across update cycles.

Project-local hooks project bounded metadata through the shared Harness CLI.
They write ignored runtime observations but cannot accept tasks or promote
entries into this directory.

## Files

- `project-facts.md`: stable facts that are currently true.
- `decisions.md`: durable decisions and the reason behind each decision.
- `lessons-learned.md`: corrections, mistakes, and reusable operating lessons.
- `handoff-log.md`: Codex-to-Claude execution handoffs and Claude-to-Codex reports.
- `verification-log.md`: important command results and verification caveats.
- `codemap.md`: concise navigation index for runtime entry points, MCP tool flow, Bilibili integration, tests, package/release files, and agent harness files.
- `harness-security.md`: security baseline and review checklist for agent harness surfaces such as rules, hooks, skills, subagents, MCP/tool config, memory, handoffs, templates, research, and QA notes.
- `harness-eval.md`: periodic evaluation record for whether skills, subagents, hooks, templates, memory, handoffs, and fixed triggers improve the workflow or add unnecessary process.
- `context-budget-report.md`: lightweight context overhead audit for always-relevant agent docs and project hooks.
- `executions/`: unified execution and acceptance reports for all three adapters.
- `handoffs/`: collaboration-only Codex/Paseo/Claude handoffs and reports.
- `pending-learning-proposals.md`: legacy v1 generated proposal queue; not formal memory.

## Update When

- The user corrects an assumption or workflow.
- A project-specific rule becomes clear.
- A durable technical decision is made.
- A stabilization task is completed or reprioritized.
- A verification result changes the known project state.
- A repeated pitfall is discovered.
- Broad hooks, MCP servers, rules, skills, or always-loaded instructions are added and context overhead should be rechecked.
- A roadmap phase, release, or significant harness update completes and the agent workflow itself should be evaluated.

## Do Not Store

- Full Bilibili Cookie strings.
- `SESSDATA`, `bili_jct`, or `DedeUserID` values.
- npm tokens, GitHub tokens, or `.env` content.
- Private user credentials.
- Unverified guesses or transient command output.

## Entry Format

Use dated entries:

```markdown
## 2026-05-27

- Fact: ...
- Evidence: ...
- Impact: ...
```

Keep entries concise and evidence-backed.

## Memory Projection Status

Runtime events remain non-authoritative. During Harness v2 ticket #29 they are
not automatically promoted. Verified durable facts, decisions, lessons, and
navigation changes may be written by the task's acceptance owner as scoped
artifacts.

Ticket #33 will replace the legacy proposal-only path with typed,
acceptance-owned projection, supersession, deduplication, and automatic
rejection of unsafe or unverified candidates. That future automation does not
give hooks or raw observations instruction authority.

The active-work pointer is `docs/agent-memory/active-work.md`. GitHub Issues are
the planning source.
