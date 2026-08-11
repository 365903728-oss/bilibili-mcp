# Harness v2

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

## Codex Direct

An executable contract adds `execution.branch` plus a typed `plan` containing
owned paths, acceptance criteria, verification commands, repair limits, and
stop conditions. The process-boundary loop is:

```text
python -m harness codex-direct start .harness/tasks/github-30/contract.json
python -m harness codex-direct guard --task github-30 --action edit --path harness/codex_direct.py
python -m harness codex-direct advance --task github-30 --to verifying
python -m harness codex-direct record-check --task github-30 --source command --exit-code 0 ...
python -m harness codex-direct advance --task github-30 --to reviewing
python -m harness codex-direct judge --task github-30 ...
python -m harness codex-direct accept --task github-30
python -m harness codex-direct status --task github-30
```

`repair` stops at the ticket limit or on a repeated failure fingerprint with
no new diff/evidence. `recover` writes a metadata-only Recovery Bundle and
never switches adapters. Guards classify fixed action names rather than raw
commands. The frozen canonical worktree/branch and source digest identify the
only writer. A repository-scoped named OS mutex on Windows, or a non-mutating
advisory lock on the existing Git config on POSIX, serializes the scan of
sibling worktrees' task state; identity probes fail closed if that existing
file changes. Per-task lease/run records and transaction locks still live only
under each worktree's `.harness/runtime/`. This rejects task-ID aliases and
concurrent altered contracts without a common-Git marker or config rewrite.
Evidence records an append-only bounded result log plus current check state and
diff digest without retaining commands or private paths.
Acceptance requires current review evidence and automatically creates the one
scoped local commit.
That commit uses an isolated temporary Git directory/index, frozen-base
attributes, `commit-tree`, a compare-and-swap `update-ref`, and Git's native
`index.lock`; configured filters, Hooks, signing, and a mutable caller index do
not enter the protected effect. It verifies the exact accepted index, path set,
snapshot, branch, parent, trailer, and clean postcondition. The retained
`commit` command is only an idempotent crash-recovery seam.

## Conformance

```text
python -m unittest discover -s harness/tests -p "test_*.py"
python .codex/scripts/test_hook_safety.py
python .codex/scripts/test_stop_summary.py
```

The replay fixtures deliberately contain synthetic secret-like values. Tests
must prove those raw values never enter normalized events or ledgers.
