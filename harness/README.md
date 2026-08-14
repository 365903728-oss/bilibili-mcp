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
python -m harness evolution start evolution-request.json --cwd <worktree> --task <evolution-task> --mode codex-direct --actor codex
python -m harness capability discover --cwd <worktree> --adapter codex-direct
python -m harness capability smoke --cwd <worktree> --name <name> --adapter codex-direct
python -m harness capability loop-step loop-step.json --adapter codex-direct
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

## Direct accepted-ticket loops

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

Claude Direct uses the same commands and state machine with a Claude-owned
contract and the `claude-direct` prefix, for example:

```text
python -m harness claude-direct start .harness/tasks/github-31/contract.json
python -m harness claude-direct guard --task github-31 --action edit --path harness/codex_direct.py
python -m harness claude-direct status --task github-31
```

The command prefix must match the frozen mode; one direct adapter cannot inspect
or mutate the other adapter's run.

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

## Governed evolution

`evolution start|search|adapt|build|evaluate` is a thin capability-evolution
seam over the unchanged Direct accepted-ticket controller. `start` consumes
only a current accepted `capability-gap`, rechecks its accepted-and-committed
provenance, requires a clean linked worktree and active exact-path writer, and
freezes the evaluator, holdout, derived repository-local package paths, report,
rollback, and baseline.

Search derives the active host's installed `find-skills` route, records bounded
pinned official/live GitHub candidate metadata, and verifies the exact immutable
artifact and license bytes before Adapt or Build. Compatibility, smoke, and
installed-provenance fields supplied by a candidate are not trusted machine
evidence; without an independent provider, Adapt stops once with an idempotent
authorization request and no capability write or local resolution command. The
Harness cannot grant itself authority. One canonical declarative source compiles exact
Codex and Claude Skill/Agent packages and deploys them only to repository-local
host discovery paths; agents are read-only, require a writer lease for writes,
and have `max_children=0`.
The engine rejects protected product/kernel/evaluator/holdout outputs,
self-approval, drift, links, scripts, dependencies, executables, credentials,
elevation, daemons, ports, global policy, and unbounded packages. Failed smoke,
evaluation, holdout, or projection checks restore only the candidate namespace
from the frozen Git snapshot; unknown drift enters Recovery instead of being
deleted. The Harness runs the frozen evaluator and holdout cases itself.
Promotion and the exact local commit remain owned by the existing Direct
acceptance path.

Version 2 evolution candidates add one exact MCP/CLI/Hook/Loop surface and
Search evidence for official, registry, package-manager, and live-GitHub
channels. The governor fetches each candidate-bound HTTPS response and derives
its normalized candidate/no-match/rejected result from the bounded response;
caller-supplied result labels must match. Package-manager evidence binds a
separate npm name/version coordinate (including
scoped packages); only an exact 404 at that bound URL becomes `no-match`, while
authentication, rate-limit, and server failures remain errors.
Candidate compatibility/smoke/install claims still have no authority: only immutable canonical JSON fetched and
byte-verified by the governor can be compiled without execution into trusted
three-adapter projection evidence.
Safe repository-local candidates may then enter Adapt automatically. Credentials,
elevation, daemons, ports, global mutation, SSH, publishing, runtime writes, or
unsafe network/data combinations remain an idempotent user-authorization stop.

`capability discover|smoke|call|serve|hook-event` verifies or invokes the
installed canonical source, exact host packages, native repository-local
deployment, and all three execution adapters. `call` exposes the bounded CLI
operations; `serve` exposes the stable MCP stdio lifecycle. Hook smoke invokes
the deployed Hook handler twice, reads the capability-bound event ledger, proves
no-secret/no-diff and linked-worktree attribution, then restores the same
deployment/config/canary/ledger snapshots without editing Hook registrations.
`capability loop-step` is a stateless bounded decision seam: it
stops on repeated failure without new evidence or the attempt limit, yields to
new user input, and rejects automatic adapter switching. Hook and Loop sources
require accepted-gap provenance and remain candidates in their own Evolution
Run; Hooks still observe and never accept work.

## Conformance

```text
python -m unittest discover -s harness/tests -p "test_*.py"
python .codex/scripts/test_hook_safety.py
python .codex/scripts/test_stop_summary.py
```

The replay fixtures deliberately contain synthetic secret-like values. Tests
must prove those raw values never enter normalized events or ledgers.
`direct-adapter-conformance.json` freezes the mode, writer, acceptance owner,
manual Skill invocation, and run/control schemas shared by both direct adapters.
