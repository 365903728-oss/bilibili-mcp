# Claude Report — GitHub Issue #32: Codex–Paseo–Claude Collaboration Loop

## Frozen Contract

- **Task/source**: live GitHub Issue #32, `[Harness v2] Codex–Paseo–Claude accepted-ticket loop`
- **Mode**: `codex-paseo-claude`
- **Canonical worktree**: `C:\Users\ZX\.codex\worktrees\927b\bilibili-mcp`
- **Base**: `5e9de4bace35a2ca4b9c83b5a0d81ebb627df6fb`
- **Branch**: `codex/harness-v2-paseo-claude-32`
- **Writer lease**: Claude active; Paseo agent `72f2b418-f6e0-405f-bd7b-280cb97cf13b` is the sole implementation writer
- **Acceptance owner**: Codex
- **Authority**: scoped local read/write/test and disposable no-remote pilots; no commit until Codex acceptance; no push, PR, Issue mutation, tag, release, publish, credential/SSH use, broad deletion, or history rewrite
- **Repair bound**: at most two same-scope repairs; user authorized one additional recovery attempt (3/3)
- **Required manual Skill evidence**: the Codex controller recorded a bridge-trigger artifact before launch; the initial host prompt natively invoked `/implement`
- **Runtime contract**: `.harness/coordination/github-32/task-contract.json` (ignored, provider-neutral)

## Implementation Summary

Implemented the `codex-paseo-claude` collaboration adapter as a thin CLI-accessible seam on the shared `codex_direct.py` controller. The adapter reuses the accepted #30/#31 contract validation, repository mutex, sibling-worktree scan, state persistence, edit guards, recovery bundle, acceptance, and commit machinery. Collaboration-specific behavior (Paseo preflight, agent launch via `paseo run`, dispatch/report/bridge management) lives in `harness/paseo_collaboration.py`.

### Vertical Slice TDD

Each repair finding was addressed with a red CLI-tracer test first, then a minimal shared-root fix:

| Slice | Finding | Test |
|-------|---------|------|
| 1 | Freeze run.json BEFORE paseo run | `test_slice1_run_json_frozen_before_paseo_run` |
| 2 | Prompt file format: `/implement` then handoff | `test_slice2_prompt_file_format` |
| 3 | Inspect fail-closed on missing fields | `test_slice3_inspect_fail_closed_on_missing_field` |
| 4 | At-most-once dispatch with sidecar | `test_slice4_at_most_once_dispatch` |
| 5 | Guard blocks stage and unknown actor | `test_slice5_guard_blocks_stage_and_unknown_actor` |
| 6 | Report rejects forbidden command keys | `test_slice6_report_rejects_forbidden_command_keys` |
| 7 | Positive lifecycle: accept → commit → idempotent commit | `test_slice7_accept_and_commit_positive_lifecycle` |
| 8 | Dead-code removal, doc updates | (no new test; verified 36/36 unchanged) |

## Files Changed

### Modified (tracked)

| File | Lines | Change |
|------|-------|--------|
| `harness/cli.py` | +259/-2 | Added `codex-paseo-claude` subcommand with `bootstrap`, `dispatch`, `guard`, `report`, `repair`, `accept`, `commit`, `recover` actions |
| `harness/codex_direct.py` | +8/-12 | Small shared-controller adjustments for collaboration reuse |
| `docs/agent-memory/codemap.md` | +32/-0 | Updated test counts, collaboration module entries |

### New (untracked)

| File | Lines | Purpose |
|------|-------|---------|
| `harness/paseo_collaboration.py` | 1479 | Collaboration adapter: preflight, bootstrap, dispatch, guard, report, repair, acceptance, commit, recovery |
| `harness/tests/test_paseo_collaboration.py` | 1705 | 36 tests: 29 function tests + 7 CLI tracer tests |
| `docs/agent-memory/handoffs/2026-08-12-github-32-codex-to-claude.md` | — | Codex-authored handoff (not writer-owned) |
| `docs/agent-memory/handoffs/2026-08-12-github-32-claude-report.md` | — | This report |

### Not Touched

`src/`, product tests, `package.json`, `package-lock.json`, workflows, release files, `dist/`, `.git`, `.paseo`, user settings, primary checkout, the Codex handoff file, any path outside the canonical worktree.

## Verification Evidence

### Focused Collaboration Suite

```text
$ PATH="/d/Git/cmd:$PATH" python -m pytest harness/tests/test_paseo_collaboration.py -v
======================= 36 passed in 115.11s (0:01:55) ========================
```

All 36 tests pass (29 PaseoCollaborationFunctionTests + 7 PaseoCollaborationCLITests).

### Combined Suite (Blocked/Hung — Pending Codex Verification)

The combined `test_paseo_collaboration.py + test_codex_direct.py + test_contracts.py + test_cli_and_adapters.py` run hung in a Git child process (PID 45224) and was terminated by Codex. The process did not complete. Recorded as `blocked/hung`, not pass. Codex will run the full acceptance gates independently after review.

### Compile And Diff

- `python -m compileall -q harness .codex/scripts` — **PASS**
- `git diff --check` — **PASS** (CRLF warnings only, expected on Windows)
- Diff scope: 3 tracked files, 289 insertions, 14 deletions

### Dead-Code Removal (Slice 8)

Removed `_validate_collaboration_contract` (~66 lines) from `paseo_collaboration.py`. This function duplicated `validate_task_contract()` checks already performed by the shared `contracts.py` validator called in `paseo_bootstrap`. The active collaboration-specific assertions (branch, plan, state, lease, acceptance owner, manual Skill gate) remain inline in `paseo_bootstrap` at lines 527-543. All 36 tests continued to pass after removal.

## Issue #32 Criterion Evidence

| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | Read-only Paseo/provider preflight | `test_preflight_read_only_no_daemon_restart`, `test_preflight_fails_closed_when_paseo_unavailable`, `test_preflight_daemon_not_running` — all pass. Preflight reads daemon health and provider preferences without restarting daemon or picking a fallback. |
| 2 | Freeze mode/base/worktree/ownership before launch | `test_bootstrap_freezes_authority_with_bridge_trigger` — verifies run.json exists with active Claude lease, frozen base/branch/worktree, Codex acceptance owner, and pending agent state BEFORE `paseo run` is called. |
| 3 | Provider from preferences or override, never persisted in governance inputs | `test_preflight_respects_provider_override`, `test_preflight_provider_not_claude_rejected` — provider resolved from live preferences or explicit override; never written to tracked contracts, rules, or config. |
| 4 | Bridge trigger before native manual-Skill evidence | `test_bootstrap_without_bridge_trigger_reminds_once` — missing bridge emits one deduplicated reminder and writes no state. `test_bootstrap_rejects_bridge_mismatch` — digest mismatch fails closed. |
| 5 | One writer, owned paths, Codex non-overlap | `test_guard_blocks_claude_write_outside_owned`, `test_guard_blocks_codex_write_of_owned_path`, `test_guard_blocks_claude_accept`, `test_guard_allows_codex_read_of_owned_path`, `test_slice5_guard_blocks_stage_and_unknown_actor` — all pass. |
| 6 | Validate bounded file-backed handoff and return report | `test_report_validates_and_persists`, `test_report_rejects_missing_keys`, `test_report_rejects_outside_owned_paths`, `test_report_rejects_wrong_agent_id`, `test_report_requires_exact_criterion_coverage`, `test_slice6_report_rejects_forbidden_command_keys` — all pass. |
| 7 | Route finite repair to same Paseo agent ID | `test_repair_routes_to_same_agent` — verifies same agent ID, bounded review file, and repair limit. |
| 8 | Adapter failure preserves lease and mode in Recovery Bundle | `test_recovery_preserves_lease_and_mode` — active lease, mode, and adapter policy survive failure. |
| 9 | Codex-only acceptance, exact one local commit | `test_slice7_accept_and_commit_positive_lifecycle` — acceptance creates exactly one commit above baseline; first explicit commit returns `already-committed` (idempotent); second explicit commit also `already-committed`; `git rev-list --count baseline..HEAD` stays at 1; no push. |
| 10 | Real testable CLI path for disposable pilot | `test_cli_subcommand_is_registered`, `test_cli_contract_validation`, and all 7 CLI tracer tests — the `python -m harness codex-paseo-claude` subcommand is registered and testable through process-boundary fixtures. |

## Risks And Unresolved Limits

- **Combined suite hang (pending Codex verification)**: The `test_codex_direct.py` + `test_contracts.py` + `test_cli_and_adapters.py` combined run hung in a Git child process. The 36/36 focused collaboration suite passes independently. Codex will run the full acceptance gates after review.
- **Real Paseo pilot not launched**: Codex owns the required disposable no-remote pilot through the final public controller. Claude has not launched a real Paseo agent.
- **Provider/model not persisted in governance inputs**: Verified; no tracked contract, rule, or config hard-codes a provider or model. Execution evidence may record the resolved runtime route.
- **No commit, push, PR, tag, release, publish, credential/SSH use**: Confirmed. All changes remain uncommitted.
- **Primary checkout dirty state preserved**: Not touched. The legacy Codex Hook overlap remains an explicit `doctor=action-required` migration gate.

## Skipped Checks

- Full TypeScript/Vitest/pack suite: not run. No product files changed; Codex owns full acceptance gates.
- `harness/tests/test_claude_direct.py`: not run. Collaboration adapter does not touch Claude Direct code paths; shared controller tests cover the reused seams.
- Real Paseo-managed Claude pilot: Codex-owned, not Claude-launched.

## Repair History

| Attempt | Scope | Outcome |
|---------|-------|---------|
| 1 | Initial implementation | Partial; several findings required correction |
| 2 | First recovery repair | Progress on findings, but remaining issues |
| 3 (final) | Complete rewrite with vertical-slice TDD | All 8 repair findings addressed; 36/36 tests green; dead code removed; docs updated |

No further repair attempts remain authorized.

## Harness Artifact Status

| Artifact | Status |
|----------|--------|
| `codemap.md` | Updated — collaboration modules and test counts |
| `harness-security.md` | Updated — collaboration validation section, Round 4 corrections |
| `harness-eval.md` | Updated — Issue #32 eval entry |
| `verification-log.md` | Updated — Round 3 and Round 4 verification entries |
| `active-work.md` | Updated — Issue #32 status |
| `decisions.md` | Updated — collaboration architecture decisions |
| `project-facts.md` | Updated — Issue #32 implementation facts |
| `lessons-learned.md` | Updated — TDD seam and shared-controller reuse lessons |
| `agent-communication.md` | Checked — unchanged; handoff/report protocol already documented |

## Round 4 (scope-compressed closure, user-authorized extension past 3/3)

Same lease, agent, mode, base, branch, and worktree. Production closure only:

1. **Unlocked acceptance seam** — `accept_codex_direct` body extracted into
   `_accept_codex_direct_unlocked`; `collaboration_accept` holds
   `bounded_file_lock(task_dir / "run.lock")`, performs collaboration checks
   (no pending dispatch/repair, launch/report evidence, live same-agent
   idle/stopped identity) under that lock, then calls the unlocked core. The
   unlocked precheck TOCTOU is gone; Direct callers keep the `@_serialized`
   wrapper unchanged.
2. **Shared complete recovery path** — every `PaseoCollaborationError` and all
   four bootstrap failure sites route through `_enter_recovery_unlocked`,
   which for `codex-paseo-claude` runs adds a bounded secret-free
   `collaboration` section to the bundle: last-persisted agent
   ID/state/provider from the run record (not a live inspect claim), the
   frozen bridge handoff digest (strict 64-hex, identity-bound), the
   bridge-trigger digest, and sidecar digests (dispatch pending/launch,
   repair pending/dispatch, report) — digests only, never contents — plus
   lease-preserved/no-daemon-restart/no-adapter-switch policy flags.
   Candidate agent identity is stored before entering recovery. Raw failure
   text is never persisted in the run record (the shared run shape has no
   error key); only the hashed category/fingerprint reach the bundle.
   `_validate_recovery_bundle_shape` is now mode-conditional: Direct modes
   keep the exact old key set; `codex-paseo-claude` requires exactly one
   additional `collaboration` key with validated exact shape, digest
   formats, identity binding, and policy.
3. **Bounded I/O reuse** — `_run_paseo_cli` replaced post-allocation
   `subprocess.run(capture_output=True)` with concurrent bounded stdout/stderr
   drains that kill the process on byte overflow or timeout and surface
   metadata-only errors (raw stderr never leaves the adapter). Handoff,
   review-file, and orchestration-preference reads now use
   `read_bounded_bytes` with symlink refusal and size bounds.

### Round 4 Verification

- `python -m py_compile harness/codex_direct.py harness/paseo_collaboration.py harness/cli.py harness/tests/test_paseo_collaboration.py` — **PASS**
- Focused tracers (`slice8_accept` + `slice35_repair` + `slice4_at_most`): **3/3 PASS** (18.57s)
- Full focused suite `PATH=/d/Git/cmd:$PATH python -m pytest harness/tests/test_paseo_collaboration.py -v`: **52/52 PASS** (251.37s)
- Second-audit targeted run (`test_slice3_inspect_fail_closed_on_missing_field`
  + `test_recovery_bundle_roundtrip_status`): **2/2 PASS** (15.72s) — proves
  exit 6 with no raw error persisted in run.json and the full collaboration
  evidence round-trip (bridge handoff digest + sidecars + policy) through the
  public status path. py_compile re-run after the audit fixes: **PASS**.
- Combined shared-controller suite: still not rerun; remains pending Codex
  verification.

### Round 4 Remaining Risks

- Combined suite hang from Round 3 remains unresolved; the 52/52 focused
  run predates the second-audit fixes, so the full focused suite was not
  rerun after them (only the two targeted tests, per controller).
- Real Paseo pilot and full release gates are Codex-owned and not started.

## Final Review Closure (repair attempt 4, 2026-08-13)

Same lease, agent, mode, base, branch, and worktree. Six release blockers
fixed; one regression proof per root cause:

1. **Paseo 0.2.5 daemon spelling** — preflight accepts
   `connectedDaemon: reachable` as healthy and still rejects
   unreachable/disconnected (`test_fix1_preflight_accepts_reachable_daemon`).
2. **No raw runtime prompts / report extras** — dispatch and repair prompt
   files are removed in `finally` after `paseo send`; report nested objects
   enforce exact key sets and persist normalized projections only
   (`test_fix2_report_rejects_risk_extra_keys`; `test_slice2_prompt_file_format`
   now proves the format from the fake Paseo's send-time capture and that no
   prompt file survives).
3. **Finite multi-repair semantics** — repair delivery evidence is
   attempt-keyed (`repair-pending-{n}` / `repair-dispatch-{n}`): a completed
   prior attempt never blocks the next authorized one, a prepared
   current-attempt intent blocks replay, and acceptance blocks any pending-N
   lacking dispatch-N. Recovery exposes two logical digests
   (`repair-pending-attempts` / `repair-dispatch-attempts`) over a canonical
   sorted name→digest map (`test_fix3_two_sequential_repairs_attempt_keyed`).
4. **Acceptance identity/digest binding** — under the task lock, launch and
   report schema/task/agent IDs must equal `run["agent_id"]`; report
   `launch_digest`, launch `handoff_digest`, and the bridge trigger's
   `handoff_digest` must equal the frozen run's `bridge_handoff_digest`. The
   expected agent never comes from mutable launch.json alone
   (`test_fix4_accept_rejects_tampered_launch_agent_id`). One shared
   serialization seam (`_launch_digest`) is used by report persistence and
   acceptance.
5. **Post-launch malformed Paseo JSON** — bootstrap `run`/`inspect` call
   sites require a dict; a list/malformed object routes to the shared
   Recovery Bundle path with the candidate agent ID preserved and no raw
   error persisted (`test_fix5_bootstrap_inspect_list_enters_recovery`).
6. **Docs truth** — removed the stray blank line at EOF in
   `verification-log.md` (`git diff --check` clean); updated stale
   file/test/line counts in `codemap.md`, `active-work.md`,
   `project-facts.md`, `harness-eval.md`, and `harness-security.md`. The
   frozen contract, bridge, and `owned_paths` were not touched; the
   untracked Codex-authored handoff file is stale (its file SHA
   `19fccbff…` does not match the bridge `handoff_digest` `19ffcbff…`) and
   is Codex's to remove after the lease returns idle.

### Final Review Verification

- `python -m py_compile harness/paseo_collaboration.py harness/codex_direct.py harness/tests/test_paseo_collaboration.py` — **PASS**
- Five new fix proofs + three updated regression tracers (targeted run): **8/8 PASS**
- Full focused suite `PATH=/d/Git/cmd:$PATH python -m pytest harness/tests/test_paseo_collaboration.py -v`: **58/58 PASS** (186.35s)
- `git diff --check` — **PASS**

Skipped: npm build/test gates, `npm pack --dry-run`, combined full Harness
suite, and the real Paseo pilot (Codex-owned next gates).

## Stop Declaration

All implementation and repair work is complete, including the final-review
closure of repair attempt 4. The diff is **uncommitted** and ready for Codex
acceptance review. The real Paseo pilot and full acceptance gates remain
Codex-owned. No commit, stage, push, PR, tag, release, publish, credential,
SSH, or remote operation was performed.

## Repair Attempt 5 Closure (2026-08-13)

Same lease, agent, mode, base, branch, and worktree.

1. **Five root fixes closed** — frozen dispatch handoff binding; frozen
   writer/report identity; acceptance current-diff binding; delivery evidence
   for every repair; strict metadata-only report trust boundary.
2. **Six new proofs** — `test_fix6` through `test_fix11` jointly **6/6 PASS**.
3. **Controller verification** — controller independently ran `py_compile`
   (**PASS**) and the full focused collaboration unittest suite:
   **64/64 PASS in 209.659s**.
4. **Provider interruption** — a temporary provider 402 interrupted the
   attempt; the same Paseo agent and lease resumed after balance restoration.
5. **NOT DONE** — real pilot, full release gates, acceptance, commit, and all
   remote effects remain NOT DONE. No final acceptance is claimed.

## Repair Attempt 5 — Final P1 Fix (2026-08-13)

Same lease, agent, mode, base, branch, and worktree. Codex retains review and
acceptance ownership.

**P1 finding**: a `paseo send` exception was rethrown before ephemeral prompt
cleanup, so a timeout/non-zero/output-bound failure could leave raw handoff or
review text under the task dir, violating the metadata-only boundary.

**Fix**: `_unlink_ephemeral_prompt` now runs on an unconditional `finally`
path for both `paseo_dispatch` and `paseo_repair` sends. Fail-closed behavior
is preserved: no launch/repair-dispatch success sidecar after a send or
cleanup failure; the prepared pending intent stays for recovery; no automatic
resend.

**New proof**: `test_fix12_send_exception_removes_prompt_files` — an injected
send exception removes both prompt files while keeping the corresponding
prepared intent, writes no success sidecar, performs no resend, and leaves
HEAD unchanged.

### Verification

- `python -m py_compile harness/paseo_collaboration.py harness/tests/test_paseo_collaboration.py` — **PASS**
- New proof alone: **1/1 PASS** (4.96s)
- fix6–fix12 seven proofs (targeted run): **7/7 PASS** (41.14s)

Skipped: broad suites, real pilot, and full release gates — per controller.

### NOT DONE

Real pilot, full release gates, acceptance, commit, and all remote effects
remain NOT DONE. No final acceptance is claimed.



## Repair Attempt 6 (2026-08-13)

Authority: repair limit extended 5 -> 6 for the same Paseo Claude writer
(agent `72f2b418-f6e0-405f-bd7b-280cb97cf13b`). Mode, base, branch, worktree,
provider/model, sole writer, and Codex acceptance ownership unchanged. TDD:
focused failing tests written first, then minimal shared-root fixes.

Six root fixes, all in `harness/paseo_collaboration.py`:

1. Post-launch repository-lock drift preserves the writer: public `bootstrap()`
   no longer calls Direct rollback when `paseo_bootstrap` already returned
   exit code 0 (the agent may be launched); it enters the collaboration
   Recovery Bundle path via `_enter_recovery_unlocked`, preserving
   run.json/agent/lease. Non-zero results keep the old rollback + error.
2. Manual-skill reminder reuses the hardened shared seam
   (`harness.capabilities.check_manual_skill`) instead of raw
   mkdir/write_text: link/junction refusal, bounded lock, dedup, <=1024-byte
   durable marker. Refusal now returns a bounded rejected payload (exit 2),
   never a traceback.
3. Malformed bootstrap contracts reject structurally: `{}`, missing/non-object
   task, and missing/invalid task.id return bounded JSON (exit 2) before any
   nested indexing, lock, or Paseo call.
4. Prompt content is ephemeral across every exit: dispatch persists the
   metadata-only prepared intent BEFORE prompt creation; prompt creation +
   send are wrapped in unconditional fail-closed `finally` cleanup (dispatch
   and repair). Pending-write failure -> no prompt; partial prompt write ->
   removed; send failure -> intent retained, no success sidecar.
5. Launch runtime metadata no longer retains the absolute private cwd:
   `canonical_worktree` removed; opaque `worktree_id` is the identity.
6. `accept` guard is deterministic: handled before shared delegation as
   Codex-only authorization (Claude denied with `accept_is_codex_owned`);
   the public acceptance command remains fully gated. Removed the dead
   post-delegation fallback.

Proofs: six new focused tests fix13-fix18, jointly 6/6 PASS
(18.83s focused run). `py_compile` PASS for both changed Python files.
Full collaboration module: 71/71 PASS in 274.79s, run exactly once.
`git diff --check` PASS.

### NOT DONE

Real pilot, full release gates, acceptance, commit, and all remote effects
remain NOT DONE. No final acceptance is claimed.

## Repair Attempt 7 (2026-08-13)

Authority: the user authorized repair attempt 7 and explicitly replaced the
prior model freeze with DeepSeek V4 Pro. The old Paseo writer
`72f2b418-f6e0-405f-bd7b-280cb97cf13b` is idle and its logical writer lease
released without stop/archive/delete; the replacement
`claude/deepseek-v4-pro[1m]` agent is the sole implementation writer. Mode,
base, branch, worktree, provider/model, and Codex acceptance ownership are
otherwise unchanged.

**One remaining blocker fixed**: `harness/cli.py` evaluated
`contract_value.get("task", {}).get("id")` at the public process boundary
before calling the repaired collaboration `bootstrap()` wrapper. For a valid
JSON object whose `task` is `null`, a string, or a list, this raised an
uncaught `AttributeError` (traceback, exit 1) instead of bounded rejected
JSON.

1. **Red proof first** — new focused public-CLI subprocess test
   `test_cli_bootstrap_rejects_non_object_task_without_traceback` in
   `harness/tests/test_paseo_collaboration.py`. It covers
   `{"task": null}`, `{"task": "bad"}`, and `{"task": []}` end to end through
   `python -m harness codex-paseo-claude bootstrap` and requires: exit 2,
   parseable rejected JSON (`state == "rejected"`, non-empty `error` string),
   no `Traceback`/`AttributeError` in stdout or stderr, no `run.json` under
   `.harness/runtime`, and no Paseo launch (a disposable fake Paseo CLI on
   PATH records every invocation; its events file must never be created).
   Red run confirmed the exact failure: exit 1 with
   `AttributeError: 'NoneType' object has no attribute 'get'` at
   `harness/cli.py:466`.
2. **Fix** — the `bootstrap` branch in `harness/cli.py` now type-checks the
   `task` value (`isinstance(task_value, dict)`) before reading `id`; the
   rejection itself is delegated to the already-repaired `bootstrap()`
   wrapper, which returns its bounded rejected JSON (exit 2) before any
   nested indexing, lock, or Paseo call. No new helper, no change to any
   other exception handling.

### Verification

- New focused test only: **1/1 PASS** (2.27s) —
  `PATH="/d/Git/cmd:$PATH" python -m pytest harness/tests/test_paseo_collaboration.py::PaseoCollaborationCLITests::test_cli_bootstrap_rejects_non_object_task_without_traceback -v`
- `python -m py_compile harness/cli.py harness/tests/test_paseo_collaboration.py` — **PASS**
- `git diff --check` — **PASS** (pre-existing Windows CRLF normalization
  warnings only)
- Full focused suite and broader gates: **not run** — the handoff limits
  verification to the new focused test plus the two checks above; Codex owns
  the wider acceptance gates.

**Codex-requested re-verification (same session)**: the attempt-7 diff and the
new process-boundary test were re-read; the fix remains the smallest root fix
(type guard at the single public-boundary read site, rejection delegated to
the repaired `bootstrap()`). Re-ran: focused test **1/1 PASS** (2.00s),
`py_compile` of both changed Python files **PASS**, `git diff --check` **PASS**
(pre-existing Windows CRLF normalization warnings only). No new failures, no
further changes made. Still uncommitted, stopped idle for Codex acceptance.

### Observed Sibling Risk (not touched — out of scope)

The `codex-direct`/`claude-direct` `start` branch in `harness/cli.py` uses the
same `contract_value.get("task", {}).get("id")` expression shape for
`recovery_task_id` derivation, so a non-object `task` would raise the same
`AttributeError` before `start_direct` is reached. This attempt's described
blocker covers only the collaboration `bootstrap` path; fixing the Direct
`start` site would be an implementation change outside the authorized scope.
Flagged for Codex.

### Files Changed This Attempt

- `harness/cli.py` — bootstrap branch only (type-check `task` before reading
  `id`).
- `harness/tests/test_paseo_collaboration.py` — one new CLI subprocess test.
- This report.

### NOT DONE

Real pilot, full release gates, acceptance, commit, and all remote effects
remain NOT DONE. No final acceptance is claimed. All changes are left
**uncommitted**; the writer stops idle for Codex review.

## Final Codex Controller Reconciliation

Codex independently reran the attempt-7 public process proof (1/1 PASS in
2.31s), the final full Harness discovery (177 tests, OK, skipped=1, 845.622s),
compileall (PASS), Hook safety (6/6 PASS), and Stop summary (8/8 PASS).
Independent acceptance and Standards follow-ups both returned PASS for that
snapshot. The replacement DeepSeek V4 Pro writer was
live-inspected idle at thinking `max` and its lease released to Codex
acceptance. The real zero-remote pilot remains a pre-attempt-6 integration
snapshot; no hash-identical final-candidate pilot claim is made. Final staged
scope/security and local commit are Codex-owned and recorded in the unified
execution report.

## Repair Attempt 8 (2026-08-13)

Final staged release and risk review found one authority gap: an accepted
`actor=claude`, `action=local-commit` request inherited the actor-agnostic
shared guard's allowed result. The user extended the repair limit to 8 for the
same replacement agent `0bdef442-14db-4f35-9e0d-c1516bb38166`; live inspect
again proved `claude/deepseek-v4-pro[1m]`, thinking `max`, canonical cwd, and
idle pre-dispatch state. No model/provider/adapter switch or overlapping lease
occurred.

The writer added an accepted-lifecycle regression first. RED failed with
`AssertionError: 0 == 0`, proving Claude was allowed. The minimum production
change rejects Claude `local-commit` before shared delegation, leaving Codex to
the existing accepted-state gate. The new proof passed 1/1 in 17.19s, all seven
guard tests passed in 31.84s, and `py_compile` passed. Codex independently
reran the proof 1/1 in 15.377s. Both reviewers that found the gap returned PASS
with no remaining P0–P2 blocker. The writer returned idle, released the lease,
and performed no commit or remote action.

**Report path**: `docs/agent-memory/handoffs/2026-08-12-github-32-claude-report.md`
