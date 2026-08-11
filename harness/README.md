# Harness v2 Session Spine

This package is repository-local tooling, not part of the published
`@xzxzzx/bilibili-mcp` npm package.

## CLI

Run from any directory inside the worktree:

```text
python -m harness doctor --json
python -m harness contract validate harness/contracts/task-contract-v1.example.json
python -m harness hook replay --adapter codex --event post-tool-use --payload harness/fixtures/codex-post-tool-use.json
python -m harness hook replay --adapter claude --event post-tool-use-failure --payload harness/fixtures/claude-post-tool-use-failure.json
python -m harness manual-skill check --task github-29 --adapter codex-direct --host codex --skill implement --invoked
```

Hook adapters call `harness/cli.py` directly so they remain usable without
installing a Python package. Host payloads are normalized to fixed metadata and
stored under the ignored, worktree-scoped `.harness/runtime/` ledger.
`doctor` inventories both `.agents/skills` and `.codex/skills` for Codex and
reports `action-required` when tracked Hooks would overlap primary/user Codex
Hooks or legacy machine-local Claude Hooks. It reports only bounded counts and
conflict flags; it does not echo commands or rewrite external configuration.
Claude's separate `PostToolUse` and `PostToolUseFailure` events project into the
same canonical tool-completion event without treating ordinary response
`message` fields as failures.

## Conformance

```text
python -m unittest discover -s harness/tests -p "test_*.py"
python .codex/scripts/test_hook_safety.py
python .codex/scripts/test_stop_summary.py
```

The replay fixtures deliberately contain synthetic secret-like values. Tests
must prove those raw values never enter normalized events or ledgers.
