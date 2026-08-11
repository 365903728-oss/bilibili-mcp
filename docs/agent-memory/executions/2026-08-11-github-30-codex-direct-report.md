# GitHub Issue #30 Codex Direct Execution Report

Date: 2026-08-11
Issue: https://github.com/XZXZZX-Ai/bilibili-mcp/issues/30
Parent contracts: #28 and accepted #29
Mode: `codex-direct` (selected once and frozen)
Manual phase evidence: native `$implement` invocation supplied by the user
Baseline: `0ed8968bf94ea5b468e97665baac99e00c3b979e`
Branch: `codex/harness-v2-codex-direct-30`

## Contract

Codex is the sole planner, writer, verifier, reviewer, acceptance owner, and
accepted-commit owner. The canonical checkout is this linked worktree; Git
reports distinct worktree/common Git directories, proving it is isolated from
the dirty primary checkout. The frozen typed contract contains the base,
branch, owned paths, criteria, verification plan, repair bound, stop conditions,
authority envelope, Codex writer, and Codex acceptance owner. Runtime state
retains only the input contract digest and typed metadata: opaque repository/
worktree IDs, task-source digest, relative owned paths, semantic IDs, booleans,
exit codes, and digests. The ignored operator-supplied `contract.json` remains
an executable input and therefore contains its canonical path and commands;
generated run/evidence/Recovery records do not retain them.

## Summary

Issue #30 adds the first executable Harness v2 adapter loop. The shared CLI now
freezes a clean canonical worktree/branch and source-bound Codex-only writer,
serializes task state under the ignored worktree runtime, atomically scans
sibling worktree leases without creating common-Git state, bounds native Skill
reminders, classifies ordinary/protected actions, records append-only diff-bound
typed evidence and current risks, bounds same-scope repair, emits a complete
metadata-only Recovery Bundle, requires current review evidence, and creates
exactly one hermetic owned local commit as the automatic post-acceptance action.

No product source, public MCP/CLI behavior, package metadata, dependency,
workflow, tracked Hook registration, release surface, or remote GitHub state is
changed.

## Files Changed And Diff Scope

- `harness/codex_direct.py`: Codex Direct state machine, guards, evidence,
  repair/recovery, acceptance, and exact automatic commit.
- `harness/cli.py`: versioned process-boundary commands and automatic adapter-
  failure recovery routing.
- `harness/contracts.py` plus contract schema/example: executable branch/plan
  validation and bounded identifiers/paths/repair policy.
- `harness/context.py` and `harness/safe_io.py`: sanitized Git environment plus
  bounded descriptor-identity/link/hardlink-safe transactions and read-back.
- `harness/capabilities.py`: source-bound, concurrency-safe, count-bounded
  native manual-Skill markers.
- `harness/tests/test_codex_direct.py`, `test_contracts.py`, adapter/event tests:
  disposable Git and linked-worktree state/lease/guard/evidence/recovery/commit
  regressions plus the shared safety boundary.
- `harness/README.md` and project memory: operator contract, navigation,
  security/evaluation evidence, verification, and active-work state.

## Commands And Results

- TDD: six original red-to-green CLI slices plus review-driven red regressions
  for cross-worktree writers, raw-state retention, concurrent lost updates,
  command-result/diff binding, review evidence, automatic commit/recovery,
  symlink/malformed state, and altered commit recovery.
- `python -m unittest discover -s harness/tests -p "test_*.py"`: 92 tests ran
  in 388.397s; `OK (skipped=1)` for one platform-permission symlink case.
- Legacy compatibility: Hook safety 6/6 and Stop summary 8/8 pass.
- `python -m compileall -q harness .codex/scripts`: pass.
- Contract example and fresh v6 pilot contract validation: pass.
- `npm ci`: exact lockfile installed; dependency manifests stayed unchanged.
- `npm run build`: pass after the clean worktree dependency install.
- `npm test -- --run`: 41 files / 862 tests pass.
- `npm pack --dry-run --json`: 185 files; required `dist/index.js`,
  `dist/cli.js`, and `dist/index.d.ts` present; forbidden Harness/rules/project-
  memory paths 0; no tarball left behind.
- Scoped high-confidence secret scan: no finding; values were never printed.
- `harness doctor --json`: expected `action-required`, tracked/primary/user
  Codex Hook counts 4/5/0; no configuration was rewritten.
- Final `git diff --check`, strict UTF-8/BOM/added-U+FFFD review, dirty-primary
  fingerprints, and both final read-only review axes pass.
- Final controller/test SHA-256 values are
  `d2c21c9d9fbc301d5531f0038b21ffdf2e88f8659fbee30da98f6467b031e2f0` /
  `cf07d4bb4368ed58b9435413ee7506adc73ca370eb3295372a7e2bed36a52f59`;
  Standards, adversarial security, and final independent risk reviewers report
  no remaining P0-P2.

## Real Bounded Codex Direct Pilot

This Codex completed a fresh isolated Harness-only repository run against the
final controller under `.harness/pilots/github-30-real-v6/`; no second
implementation client or normal
Codex configuration was invoked.

- Base / accepted commit:
  `3b93fe44379bd827e9c687ec59a219268648984b` /
  `1a326b9760ca9b23bb2ba25f6c0704941713b5b5`.
- Guards: read/edit allowed without prompts; push entered explicit user-
  authorization state; pre-acceptance commit was blocked.
- Accepted diff: only `harness-only.txt`; snapshot digest
  `e8837d20c4ee3cbb6a196e44e4883bcc877ef7a7af923c4183af106a7d48db0c`;
  index digest
  `4763b2413f680cf415e1cba34e59f0c31fc30cfe44cb43ad10221f352630bd34`;
  file digest
  `a6a36ac190fb79f5d4cf996a1c94608ca6b3950ca03ded10bd7c43bc438b11e1`.
- Required evidence: content command exit 0 and result digest
  `25db26e8a1896f1dc40eb5b5b1737125f255e28b6220f5bb932c58b989a7b484`;
  current diff review
  `ed084aa32c356a49aa15ec1c8f74441eb018f33cca8bef83d2a1cb7a9e192c37`;
  zero-remotes inspection
  `03a219524697b1e803568bf5afedfa9ee3f6ba4b94faebfda7807e132e565d9d`.
  All three reference runtime diff digest
  `df61b7d467d241cd08dae76212cee52b6d81c454c1929a09752268f10e3e99ee`.
- Skipped check: normal-config smoke, reason `doctor-action-required`, digest
  `df5e9419b734446ec5efb33aafe486f67bcfc67433765cd84eee43b39f349215`.
  It was not required and did not substitute for another gate.
- Accepted risk: external Hook overlap, low, digest
  `538a6cd210000592b19640fabeea714858c577e859a661e2d02d5cb7672626ac`.
- Criteria: owned diff, verified diff, and local-only effect all pass with
  explicit evidence references. Repairs 0; user interventions 0; routine
  permission prompts 0; configured remotes 0; implementation-client handoffs 0;
  handoff overhead 0; context cost not measured.
- Acceptance created exactly one commit touching exactly the owned file;
  repeated acceptance returned `already-committed`; repository status is clean.
- Persisted runtime contains neither the canonical private path nor raw command
  text, and the nested common Git directory contains no Harness lease marker.

## Acceptance Criteria

| Criterion | Judgment |
| --- | --- |
| Mode selected once and frozen before implementation | PASS |
| Typed contract records worktree/base/writer/owner/authority/verification/repair | PASS |
| Second writer rejected, including another linked worktree | PASS |
| Missing `$implement` produces one reminder and no implementation write | PASS |
| Ordinary reads/scoped edits/builds/tests remain prompt-free | PASS |
| Dangerous, credential/SSH, history, and external actions stop deterministically | PASS |
| Repair is finite and repeated no-progress fingerprint stops early | PASS |
| Adapter failure writes Recovery Bundle and never switches | PASS |
| Commit before acceptance is rejected | PASS |
| Acceptance creates one exact owned local commit and never pushes | PASS |
| Disposable-repository process tests cover the complete boundary | PASS |
| Real bounded Harness-only pilot records diff/results/skips/risks/criteria | PASS |

## Repairs And Failure Fingerprints

Initial Standards review found five concrete boundaries: raw contract/private-
path persistence, altered-diff commit recovery, worktree identity, unlocked
state updates, and silent symlink/invalid-state persistence. Initial Spec review
additionally found missing review-source enforcement, missing command-result
metadata, incomplete project records, and an isolation-evidence gap; altered
commit recovery overlapped Standards.

Later read-only rounds rejected a common-Git lease marker, found an
accepted-snapshot/index recovery hole, proved the shared 2,000-node reader was
smaller than the declared controller maxima and could overwrite the last good
state, showed configured Hooks/signing/filters could escape the protected
commit boundary, found alias/malformed sibling writer leases and reminder/lock
bounds, and caught premature/incomplete memory evidence.

Each finding received a regression or explicit repository evidence. The final
implementation binds the writer to the frozen canonical worktree/branch and
task source, atomically scans sibling worktree-local leases under a Windows
named mutex or POSIX non-writing existing-config lock, uses per-task and shared
reminder transaction locks, preflights/read-backs the same state bound, retains
digested runtime plan fields and append-only evidence, and binds exit-code/
review evidence to the current diff. The protected commit derives the tree in a
temporary Git directory/index with frozen-base attributes, holds native
`index.lock`, calls `commit-tree`, moves only the frozen ref with CAS
`update-ref`, and proves exact recovery/postconditions. Late filters, Hooks,
signing, and caller-staged content cannot enter it.

## Risks, Skipped Checks, Recovery Bundle

- Primary legacy Codex Hooks still overlap tracked v2 Hooks. This remains an
  explicit `doctor=action-required` rollout gate; #30 had no authority to edit
  primary/user configuration or run a normal-config client smoke.
- `npm ci` repeated the known unchanged development-tree advisory count (one
  moderate, six high, one critical). Product dependencies and manifests are
  outside #30 and the product build/tests/package gate pass.
- The ignored pilot repositories remain under `.harness/pilots/` because the
  environment rejected the previously attempted verified recursive cleanup.
  They are Git-ignored, excluded from the package and acceptance diff, contain
  no credential value, and preserve reproducible pilot evidence.
- Successful #30 execution needed no task Recovery Bundle. Disposable tests
  prove adapter failure, repeated fingerprint, and repair-limit bundles while
  preserving the active writer and `stop-and-report` adapter policy.

## Capabilities Used

- Manual Skill: `$implement` (native user invocation).
- Model-invoked/project Skills: `bilibili-mcp-memory`, `tdd`, `vitest`,
  `code-review`, `secret-scanning`, and `git-local-commit`.
- Read-only agents: `issue30_harness_map`, `issue30_test_map`,
  `issue30_standards_review`, `issue30_spec_review`, followed by an independent
  risk-weighted reviewer after repairs.
- Local/live tools: Git, `gh` Issue reads, Python/Harness CLI, npm,
  TypeScript, and Vitest.
- Intentionally unused: Paseo/Claude writer, adapter fallback, AgentKey,
  credentials/SSH, and every remote Git/release operation.

## Harness Artifacts

- Unified report: this file.
- Memory: facts, decisions, verification, security, evaluation, codemap, and
  active-work records updated together.
- Runtime/pilot: ignored executable input contracts plus bounded metadata-only
  generated run/evidence under `.harness/`; no generated runtime or nested
  pilot file enters the ticket commit/package.
- QA: no public product/install/MCP behavior changed, so no separate product QA
  checklist instance is needed.

## Local Commit

Acceptance authorizes one focused local commit containing only #30-owned files.
The focused branch commit containing this report is that acceptance commit; if
this report is not yet in HEAD, #30 is still a candidate. The commit does not
push, close the Issue, create a PR, tag, release, publish, or absorb the dirty
primary checkout.
