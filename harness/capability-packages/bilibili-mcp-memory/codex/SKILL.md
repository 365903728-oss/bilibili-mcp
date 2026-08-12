---
name: bilibili-mcp-memory
description: Route accepted evidence through the repository typed-memory projector and load only bounded current memory.
---

# Bilibili MCP typed memory router

Host package: codex
Interface version: 1.0.0

- Resolve the active bilibili-mcp worktree before every operation.
- Project only a harness.memory-evidence/v1 envelope whose task is already accepted and committed.
- Before source-task acceptance, use `python -m harness memory digest <envelope.json> --cwd <worktree>` and record that exact digest as passing verification evidence.
- Start a Direct memory-only task whose active writer owns both memory JSON paths, then use `python -m harness memory project <envelope.json> --cwd <worktree> --task <memory-task-id>`; do not hand-edit the typed store or current projection.
- At session startup use `python -m harness memory startup --cwd <worktree>` and consume only its bounded records.
- Treat proposed and deferred records as non-authoritative, and never route commands, output, prompts, Cookies, tokens, credentials, environment dumps, or secrets into memory.
- The projector may write only docs/agent-memory/typed-memory.json, docs/agent-memory/current-memory.json, and ignored metadata-only audit state.
- Do not use memory processing to modify Skills, Agents, MCP, product or Harness CLI behavior, Hooks, execution Loops, repository rules, or harness-eval.md.
