# GitHub Issue #33 Codex Direct Execution Report

Execution date: 2026-08-13
Issue: [#33 `[Harness v2] Automatic typed memory from accepted evidence`](https://github.com/XZXZZX-Ai/bilibili-mcp/issues/33)
Mode: `codex-direct`
Branch: `codex/harness-v2-typed-memory-33`
Exact base: accepted #32 commit
`9cbb8de64ffedefd682517e203841dd137b75662`, whose direct parent is accepted
#31 commit `5e9de4bace35a2ca4b9c83b5a0d81ebb627df6fb`
Status: acceptance candidate; Harness creates the one focused local commit only
after every final gate and criterion below passes

## Outcome

- One shared `harness/memory.py` validates accepted evidence envelopes, applies
  promotion and supersession, writes a deterministic typed store and bounded
  current projection, and audits both changes and successful no-change replay.
- Thin `python -m harness memory digest|project|startup` routes expose the
  process boundary. The three accepted-ticket controllers and their state,
  authority, recovery, acceptance, and commit semantics are reused unchanged.
- Every record has stable identity, source/provenance, validation, sensitivity,
  validity/supersession, and evidence digest. Current facts supersede by
  meaningful validity time; equal-time conflicts fail closed.
- One verified user correction or eligible reproducible/accepted result may
  promote immediately. A general process lesson requires explicit user
  correction or support from two distinct accepted task IDs. External claims,
  model inference, and weak observations remain deferred/proposed and never
  enter startup.
- Unsafe operational content and secret-shaped values are rejected before
  writes. Existing state is revalidated on load, and startup reads only the
  bounded current projection rather than old append-only history.
- One canonical `bilibili-mcp-memory` source deterministically builds matching
  versioned Codex/Claude interfaces and evaluation metadata with host manifests.
  Installed external capability copies were not changed.

## Authority And Boundary

- The projector owns only `docs/agent-memory/typed-memory.json`,
  `docs/agent-memory/current-memory.json`, and ignored metadata-only audit state.
- It cannot modify Skills, Agents, MCP/product source, package metadata, CLI
  policy, Hooks, Loops/controllers, constitutional files, capability packages,
  or its evaluator. Capability compilation is an explicit developer operation,
  not a projection side effect.
- Product TypeScript runtime, ten-tool MCP surface, public CLI, package/lock,
  workflows, and npm contents are unchanged. Harness/agent-memory artifacts
  remain excluded from the package.
- The primary dirty checkout stayed outside this worktree. Its baseline
  fingerprint is HEAD `ab4dd02854f0483fc7668c713523b4be77de6cc7`, tracked
  diff `b3126a2f…c91e`, staged diff `e3b0c442…b855`, untracked manifest
  `5c3c24dd…ce04`, status `2af8ec3a…adcb`, and 44 untracked entries; final
  acceptance rechecks every value.
- The known legacy primary Codex Hook overlap remains
  `doctor=action-required`; no primary/user configuration was silently
  rewritten.
- Push, PR, Issue close, tag, release, publish, credentials/SSH, broad delete,
  and history rewrite were neither authorized nor performed.

## Real Accepted Memory-Only Pilot

- A disposable local repository started with no remote and ignored Harness
  runtime state. A source Codex Direct task recorded the canonical candidate
  digest, reached acceptance, and created commit
  `62caea4d73e0f88d81803ecd6abc70aae9faed54`.
- A second Codex Direct task projected that accepted envelope, replayed it with
  `changed=false`, loaded one bounded current record, passed its independent
  review gate, and created commit
  `a3e6fcabdd36849f46a738592a24d815b64d337b`.
- The second task advanced by exactly one commit and changed exactly
  `docs/agent-memory/current-memory.json` and
  `docs/agent-memory/typed-memory.json`. Store SHA-256 was
  `943fb9ff…e08`; projection SHA-256 was `711995c3…c54e`; audit line count was
  two; final status was clean and remote output was empty.

## Verification And Review

- Typed-memory suite: 33/33 pass in 69.134s; independent reviewer rerun 33/33
  in 65.681s.
- Exhaustive Harness discovery: 211 tests in 873.324s, one platform-permission skip;
  Codex Direct 61, Claude Direct 12, Paseo collaboration 73, typed memory 33,
  and core CLI/contracts/events 32.
- Legacy Hook/Stop compatibility: 6/6 and 8/8 pass. Python compileall passes.
- Product: TypeScript build passes; Vitest passes 41 files / 862 tests in
  11.61s; exact-lockfile install leaves package/lock unchanged.
- Package: production audit has zero vulnerabilities; dry-run pack contains 185
  files and zero forbidden Harness/agent-memory paths.
- Independent risk review passed with no remaining P0-P2 after focused
  regressions closed supersession replay, secret/raw variants, atomic target
  authority, startup/store/HEAD consistency, validity-time, and isolated-pilot
  findings. The reviewer independently reran the 33-test typed-memory suite.
- The frozen candidate has 23 changed paths, all under `harness/` or
  `docs/agent-memory/`; every changed file is UTF-8, the index is empty,
  `git diff --check` passes, product/package diffs are empty, and secret scans
  report no finding.
- Final Doctor remains the expected `action-required` result: tracked Codex
  Hook commands 4, primary legacy commands 5, user commands 0. The complete
  primary fingerprint, including all four SHA-256 values and 44 untracked
  entries, exactly matches the read-only baseline.

## Acceptance Mapping

1. Replay/no duplicate: canonical records and projection are idempotent; the
   pilot replay is an audited successful no-change.
2. Typed contract: stable ID, source/provenance, validation, sensitivity,
   validity/supersession, and digest are mandatory and load-validated.
3. Current supersession: newer valid facts close the former interval and only
   the new value enters startup; equal-time ambiguity is rejected.
4. One-occurrence evidence: explicit corrections and eligible verified facts or
   accepted results promote once.
5. General lessons: only explicit correction or two distinct accepted task IDs
   promote; duplicate lines in one task do not count twice.
6. Weak evidence: external/model/weak kinds remain deferred/proposed and are
   excluded from startup.
7. Secret/raw exclusion: forbidden keys and secret/raw operational patterns are
   rejected before storage and projection.
8. No-change: replay succeeds and appends bounded metadata-only audit evidence.
9. Bounded startup: only the current projection is read, under byte/count caps.
10. Canonical capability: Codex/Claude packages compile from one versioned
    source and expose interface, manifest, and evaluation metadata.
11. Boundary: projector output allowlist excludes product and every named
    governance/capability/evaluator surface.
12. Verification/pilot: unit, replay, redaction, supersession, idempotence,
    exhaustive Harness/product/package gates, and a real accepted zero-remote
    Codex Direct memory-only pilot pass.

## Local Commit

After final review and evidence are bound to the completed diff, the shared
Harness acceptance path creates exactly one #33-owned local commit. No remote
operation follows.
