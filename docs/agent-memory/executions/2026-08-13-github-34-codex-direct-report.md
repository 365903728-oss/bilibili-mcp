# GitHub Issue #34 Codex Direct Execution Report

Execution date: 2026-08-13
Issue: [#34 `[Harness v2] Governed Skill and Agent evolution`](https://github.com/XZXZZX-Ai/bilibili-mcp/issues/34)
Mode: `codex-direct`
Branch: `codex/harness-v2-skill-agent-evolution-34`
Exact base: accepted and pushed #33 commit
`1cd12c8a6edab272bd16ad5ecb8ba2ae4bd90cf8`, whose direct parent is accepted
#32 commit `9cbb8de64ffedefd682517e203841dd137b75662`
Status: acceptance candidate; Harness creates the one focused #34 local commit
only after every final gate and criterion below passes

## Outcome

- `harness/evolution.py` adds a bounded state seam over the unchanged Direct
  accepted-ticket controller. It consumes only a current accepted
  `capability-gap`, rechecks accepted-and-committed origins, requires a clean
  linked worktree and active exact-path writer, and freezes evaluator, holdout,
  host outputs, report, rollback, branch, and base.
- Search records the installed `find-skills` route, sources consulted, and
  pinned official/live GitHub candidate metadata. Candidates carry immutable
  source/revision and artifact/license digests, permissions, network/data
  behavior, compatibility, smoke, effects, installed provenance, and
  repository-local rollback. Search fetches exact immutable artifact and license
  bytes with bounded no-credential HTTPS reads and verifies their digests before
  choosing Adapt or Build.
- Candidate-supplied compatibility, smoke, and installed provenance are not
  trusted machine evidence. Adapt therefore stops once as
  `authorization-required`; it records a candidate-bound request and safe
  alternatives but exposes no local command that can forge user authority.
- Build compiles one canonical declarative Skill/Agent source into deterministic
  Codex/Claude packages through the shared manifest compiler. The same compiler
  seam cannot apply an Adapt source until a future independent evidence provider
  makes that candidate eligible.
  Trigger positives/negatives/near-neighbor conflicts, invocation semantics,
  interface, governance, trust, packaging, and read-only zero-child agent policy
  remain explicit and drift-checked.
- Candidate paths are derived from a validated capability name and cannot own
  product/kernel/evolution/evaluator/holdout paths. Canonical packages are
  synchronized to actual repository-local Codex and Claude discovery paths.
  The writer cannot supply evaluator/holdout results: the Harness runs fixed
  frozen cases. Projection, evaluator, holdout, or test failure restores only
  the candidate namespace from its frozen snapshot before a rejected report is
  recorded; unknown drift enters Recovery without deletion. Existing Direct
  acceptance owns promotion and the exact local commit.

## Controlled Pilots

- Search pilot: a disposable zero-remote source task accepted a verified
  capability gap; a separate memory task projected it; an independent linked
  Evolution worktree then compared installed `vitest` SHA-256
  `3dcdc45f…6375` with `antfu/skills` at verified immutable commit
  `a74f281a27dadc02397bc1a174b0f2c97531b6ae`, artifact SHA-256
  `2da9b15c…8968`, MIT license blob `29f64e…a43`, and license SHA-256
  `2a596f69…1cb2`. Because installed provenance/content did not match the pinned
  candidate and the installed route would require unpinned `npx`, the truthful
  outcome was deferred with zero installation and zero capability files. The
  live disposable run stopped after validating its report because the pilot
  wrapper used an incorrect short-status assertion; the hermetic public CLI
  fixture separately proves the report-only acceptance/commit path.
- Adapt boundary fixture: even a structurally safe pinned candidate cannot turn
  its own compatibility/smoke assertions into adoption authority. Exact upstream
  bytes are verified, the result is `authorization-required`, and zero
  capability files are written.
- Safe Build fixture: a dependency/script/executable/network/credential-free
  repository-local canonical source generated both host packages and their
  native discovery projections. Fixed-artifact drift caused rejection and
  restored the exact candidate namespace while preserving a non-empty sibling
  capability. A separate Harness-computed evaluator/holdout pass reached
  promotion-ready and the existing Harness path created exactly one
  capability/report commit; repeated acceptance was `already-committed`.
  Every disposable repository had zero remotes.

## Authority And Boundary

- Product `src/`, ten MCP tools, package/lock, dependencies, Hooks, Direct and
  collaboration controllers, constitutional files, installed user/global
  catalogs, and primary/user configuration are unchanged.
- External GitHub/Skill content is bounded candidate data, never execution
  authority. No installer, dependency, script, executable, daemon, port,
  elevation, new credential, global policy, or user-root write was used.
- The dirty primary checkout remains outside the current worktree. Its frozen
  baseline is HEAD `ab4dd02854f0483fc7668c713523b4be77de6cc7`, tracked diff
  `b3126a2f…c91e`, staged diff `e3b0c442…b855`, untracked manifest
  `5c3c24dd…ce04`, status `2af8ec3a…adcb`, and 44 untracked entries; final
  acceptance rechecks every value.
- Doctor remains the known `action-required` Codex Hook overlap
  (tracked/primary/user `4/5/0`). The exact command was run with an isolated
  empty home because the existing default Doctor enumerates every home Skill;
  capability inventory was therefore intentionally empty and not treated as
  live catalog evidence. No configuration was rewritten.
- Push, PR, Issue close, tag, release, publish, credentials/SSH, broad delete,
  and history rewrite were neither authorized nor performed.

## Verification And Review

- TDD red-to-green: ten public CLI/compiler tests pass in 481.432s. They cover accepted
  gap provenance, independent writer/worktree, protected product/kernel paths,
  Windows path aliases, exact persisted-state validation, pinned Search/Adapt
  with upstream byte verification, deferred and idempotent authorization stops,
  canonical/manual/model projections, exact discovery-path deployment and
  deterministic host-schema conformance, fixed
  Harness-computed evaluator/holdout cases, candidate-scoped rollback, unknown
  drift Recovery, sibling preservation, report-only rejected/deferred commits,
  promotable exact-one commit, and zero remotes.
- Typed-memory regression suite remains 33/33 pass in 71.401s. The shared manifest helper
  preserves the existing canonical memory package byte contract.
- Legacy Hook/Stop compatibility passes 6/6 and 8/8; Python compileall,
  `py_compile`, Ruff, and `git diff --check` pass. TypeScript build passes;
  Vitest passes 41 files / 862 tests; the package dry run contains 185 files
  and zero forbidden Harness/internal paths. A production audit attempt ended
  before advisory data at the npm-registry TLS boundary; package inputs are
  byte-unchanged from the accepted #33 zero-vulnerability baseline.
- The isolated risk review closed the accepted-gap receipt, forged Adapt state,
  and post-acceptance writer-lease findings under the repository-process trust
  model. The monolithic full Harness discovery exceeded its 30-minute ceiling
  without failure output and was not rerun; current-diff shards all pass:
  Direct/Claude 73 (one skip), Paseo 73, CLI/contracts/events 32, typed memory
  33, and Evolution 10 (221 executed / one skip, zero failures).
- Final independent release review found one actionable terminal rollback gap.
  The shared acceptance gate now restores known candidate output and records a
  rejected report when promotion-ready revalidation fails; unknown/drifted
  output still enters Recovery. The focused public-CLI proof passes 1/1 in
  146.898s and the reviewer closed the finding.

## Acceptance Mapping

1. Accepted gap only: startup supplies only accepted current records and the
   origin commit is rechecked as a HEAD ancestor distinct from the run task.
2. Independent run: the existing Direct contract owns task/worktree/writer/
   evidence/acceptance/commit; Evolution freezes the additional evaluator,
   holdout, report, rollback, and canonical outputs.
3. Search before Adapt/Build: no apply state exists before a bounded installed
   route plus pinned live GitHub candidate record chooses a strategy.
4. Candidate contract: source/revision/license/artifact/permissions/network/
   data/compatibility/smoke/effects/installed provenance/rollback are exact.
5. Safe adoption: pinned bytes and safety fields are necessary but insufficient;
   Adapt remains fail-closed until an independent trusted machine-evidence
   provider supplies compatibility, smoke, and installed-provenance receipts.
6. Risk stop: unsafe/unverified Adapt becomes one idempotent
   `authorization-required` request and performs no capability write; there is
   no writer-callable resolution route that can fabricate user authority.
7. Canonical Skill: all requested trigger/interface/manifest/governance/trust/
   packaging/invocation fields compile into exact host packages.
8. Bounded agents: both projections are read-only, writer-lease-aware, have
   only read/inspect/report capability, and set maximum children to zero.
9. Invocation semantics: manual metadata stays manual and native; model
   invocation remains enabled only for model-invoked canonical Skills.
10. Host synchronization: both packages share canonical/interface digests,
    synchronize to actual repository-local Codex/Claude discovery paths, and
    receive exact-file/byte plus host-parser conformance verification.
11. Protected authority: product/kernel/engine/evaluator/holdout outputs and
    writer/candidate self-approval fail closed.
12. Rollback: failed evaluation/holdout/smoke/projection restores the frozen
    candidate namespace without touching sibling capabilities; unknown drift
    enters Recovery rather than being deleted.
13. Controlled evidence: zero-install Search/Adapt-boundary and safe Build success plus
    rollback fixtures execute through disposable linked worktrees.

## Local Commit

After final current-diff checks, independent review, risk closure, and
criterion-by-criterion evidence binding, the shared Harness acceptance path
creates exactly one #34-owned local commit. No remote operation follows.
