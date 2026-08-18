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
- `typed-memory.json`: generated durable typed records. It is absent until the
  first accepted evidence envelope changes memory and must never be hand-edited.
- `current-memory.json`: generated bounded current startup projection. It is
  absent until the first accepted projection and is the only typed startup
  context source.

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
not automatically promoted. Harness v2 ticket #33 adds a separate accepted-
task projector: a source task first records the canonical digest of a bounded
`harness.memory-evidence/v1` envelope, reaches accepted-and-committed state,
and only then may a memory-only task project it.

Use `python -m harness memory digest`, `memory project`, and `memory startup`
through the shared CLI. The projector owns only `typed-memory.json`,
`current-memory.json`, and ignored metadata-only audit state. Replay is
idempotent, current facts supersede older values, general lessons require an
explicit user correction or support from two independent accepted task IDs,
and proposed/deferred records never enter startup context. Unsafe operational
payloads and secrets are rejected rather than stored or projected. Hooks, raw
observations, free-form reports, and the legacy proposal file remain outside
this authority path.

The active-work pointer is `docs/agent-memory/active-work.md`. GitHub Issues are
the planning source.
