# GitHub Issue #36 Codex Direct Execution Report

Execution date: 2026-08-14  
Issue: [#36 `[Harness v2] Three-adapter conformance, real pilots, and migration acceptance`](https://github.com/XZXZZX-Ai/bilibili-mcp/issues/36)  
Mode: `codex-direct`  
Branch: `codex/harness-v2-three-adapter-conformance-36`  
Exact base: accepted #35 commit
`8de058e772e97a6ab8d16d65386081db76953320`  
Status: migration convergence; all three real pilots accepted

## Outcome

- `three-adapter-conformance.json` replaces the two-Direct-only fixture with
  one project-owned matrix for `codex-direct`, `claude-direct`, and
  `codex-paseo-claude`. It freezes one task-contract schema, `RULES.md` kernel,
  public mode command, lifecycle kind, writer, acceptance owner, native manual
  invocation, run/control schema, eleven pilot checks, and four migration
  checks.
- The implementation reuses the accepted Direct controller and Paseo seam. No
  fourth controller, provider/model policy, product runtime, package metadata,
  dependency, or public MCP change was introduced.
- Shared Hook events now bind adapter/host-event provenance, metadata
  sensitivity, a full SHA-256 digest, and active/stopped terminal state before
  persistence. Raw payloads, commands, stdout/stderr, environment data,
  credentials, and host session identity remain excluded.
- Real bounded Codex Direct, Claude Direct, and Paseo-managed Claude pilots
  completed in isolated zero-remote repositories. None is substituted with a
  mocked adapter test.

## Live Source And Baseline Audit

- Live GitHub Issues #28 and #30–#36 were re-read. #36 is open, parented by
  #28, and blocked by #31, #32, and #35; the live body is the acceptance source.
- The independent worktree began detached and clean at exact #35 commit
  `8de058e772e97a6ab8d16d65386081db76953320`. Local and origin #35 refs matched,
  and #30–#35 form an exact linear ancestry.
- Branch `codex/harness-v2-three-adapter-conformance-36` was created only after
  the baseline check. The user selected `codex-direct` once. The first draft
  was removed to restore the exact clean baseline, then the public controller
  froze the branch/base and acquired the sole active Codex writer lease before
  the implementation patch was replayed.
- The primary checkout stayed at `ab4dd02854f0483fc7668c713523b4be77de6cc7`
  on `master` with 68 dirty status rows and frozen status digest
  `a4bbfb6dc821d203291ec664843d23f818db293aad8af1975f1190f33e5f8423`.

## Authority And Security Boundaries

- The normal doctor was not run because it would enumerate an explicitly
  prohibited Skill. Tests that exercise doctor behavior are reserved for a
  blank isolated home. The prohibited Skill was not read, invoked, installed,
  bridged, or used.
- The real Claude Direct writer ran with `--safe-mode`, slash commands
  disabled, strict empty MCP configuration, and only the bounded Read/Write or
  Bash/Read tools required by its two phases. Skills, plugins, hooks, MCP,
  agents, network tools, and session persistence were disabled.
- Ordinary `test` and owned-file `edit` guards were allowed without prompts;
  `ssh` was blocked and `publish` required user authorization. A second start
  was rejected while each writer lease was active.
- Missing native `$implement` and `/implement` gates each emitted one actionable
  reminder, deduplicated the second attempt, left the lease inactive, and made
  zero implementation writes.
- An intentional Claude Direct adapter failure produced
  `harness.recovery-bundle/v1`, state `recovery-required`, retained the Claude
  lease, recorded zero changed paths, and preserved
  `adapter_switch_policy=stop-and-report`.
- No push, PR, Issue close, tag, release, publish, credential/SSH use, broad
  delete, history rewrite, global configuration mutation, or product release
  effect occurred.

## Real Pilot Evidence

### Codex Direct

- Frozen base: `a7b0aba49c59e807cdd5a63b28d238c8e041d668`
- Accepted commit: `0cadc18c9cd85733875929e49130b847a204e1be`
- Scope: only `pilot.txt`; exactly one commit above base; clean status; no remote
- Typed events: worktree `wt-4684bb5255c08311`, redacted active and stopped
  records with full digests

### Claude Direct

- Frozen base: `e60b0b2a651990ff9c6b4c25fa6874741f151831`
- Accepted commit: `a81fef21b17330613729b5a67f13386c4ad651ec`
- Scope: only `pilot.txt`; exactly one commit above base; clean status; no remote
- Actual runtime: Claude Code 2.1.228 using provider/model
  `deepseek-v4-flash`, reported total cost USD 0.08317 across bounded write and
  acceptance phases
- Typed events: worktree `wt-3d9d0d16eabd6136`, redacted active and stopped
  records with full digests

### Paseo-managed Claude

- Preferences resolve implementation provider `claude/deepseek-v4-flash`.
- After explicit user authority, one `paseo start` launched daemon 0.3.1. The
  provider moved from one observed `loading` state to a successful preflight
  with `restarted_daemon=false` and `fallback_chosen=false`.
- Agent `f4a4fec4-fb93-4a84-8c8c-556aeb08488c` ran the frozen
  `claude/deepseek-v4-flash` handoff, changed only `pilot.txt`, read it back,
  stopped idle, and reported no prohibited effect. Report validation bound the
  live inspect, launch digest, current diff, agent identity, criterion, and
  frozen worktree.
- Frozen base: `041ee7eff85ff57893c5dd2a39fac11974e5493d`
- Accepted commit: `27fba0dce64fb591a30f0651979940089c667fb0`
- Scope: only `pilot.txt`; exactly one commit above base; clean status; no
  remote; Claude lease released
- Actual usage: 750 input, 844 output, 206848 cached tokens; USD 0.473404

## Focused TDD And Verification

- Red before green: missing unified fixture, missing shared pilot/migration
  matrix, absent event provenance/sensitivity/digest/terminal state, and the
  wrong Paseo public command each failed at the public fixture/event seam.
- Shared contract/events/Direct fixture: 21/21 pass in 22.343s.
- Writer, authority, Recovery, and exact-commit slice: 7/7 pass in 33.230s.
- Typed memory idempotence, raw/secret rejection, and real zero-remote pilot:
  3/3 pass in 21.834s.
- Three-adapter CLI/MCP/Hook/Loop surface promotion: 1/1 pass in 170.520s.
- Evolution promotion/rejection/rollback: 1/1 pass in 98.519s.
- Evaluator/projection-drift rollback without self-approval: 1/1 pass in
  41.808s.
- One parallel parent batch timed out after 304s and returned no child results;
  it is not counted. Required short shards and long Evolution cases were then
  run independently once and returned explicit results.
- Final product boundary: exact-lock `npm ci --ignore-scripts` restored the
  worktree-local toolchain; `npm run build` passed; Vitest passed 41 files / 862
  tests in 6.82s; and the dry-run package contained 185 files with zero Harness,
  runtime-event, Recovery, or agent-memory paths.
- `npm audit --omit=dev --json` was inconclusive because the registry advisory
  endpoint disconnected before TLS establishment. Per the network-evidence
  rule it was not retried; no green audit claim is made. Product source and
  lockfile are unchanged from accepted #35.
- Final risk-weighted Harness shard: 26/26 pass in 75.307s across shared
  contracts/events, Direct conformance/authority/exact-commit/Recovery, and
  Paseo lifecycle/duplicate-dispatch/Recovery. Earlier current-diff typed-memory
  and long governed-Evolution receipts remain valid and were reused.
- Main acceptance initially failed closed because broad frozen ownership of
  `harness/` overlapped immutable governed-Evolution roots. The run emitted a
  Recovery Bundle. Without editing or bypassing the kernel/evaluator/holdout,
  the same Codex writer froze a recovery continuation on the same exact base,
  mode, branch, and worktree with the actual 23 Issue-owned paths, then restored
  the unchanged diff from a reversible local stash. No second implementation
  actor, adapter switch, commit, or remote effect occurred.

## Independent Risk Review

- The first review found two High gaps: the shared matrix did not drive the
  public Paseo lifecycle, and a single summary JSON could self-certify claimed
  pilot/migration results. The Paseo regression now runs the real shared
  bootstrap/dispatch/report/review/accept controller seam.
- The evidence root cause is closed: a thin index binds independent artifacts;
  native controller and Recovery snapshots pass the production validators;
  accepted commits are reconstructed from Git commit/tree/blob bytes; event
  rows are schema-closed and digest-recomputed; command receipts bind fixed
  argv and output digests; package output is compared to a live local dry run;
  durable files are rehashed; and clean-room bytes are read from exact #35 Git
  objects. Raw command/stdout/stderr/environment/credential fields fail closed.
- Independent re-review reports both High findings closed. The real Paseo
  artifact is present, and migration/final-index verification passes against
  the current independent artifacts and durable-file hashes.

## Acceptance Mapping

- Shared contract/kernel/matrix: implemented and focused green.
- Actual Codex Direct and Claude Direct pilots: accepted and committed.
- Actual Paseo-managed Claude pilot: accepted and committed.
- Mode freeze, second-writer rejection, manual reminder/no-write, authority,
  exact commit/no remote, worktree attribution, typed events, typed memory, and
  governed Evolution rollback: evidenced.
- Product build/test/package and independent risk review: pass; production
  audit is explicitly TLS-inconclusive. Evidence-index, secret/diff, and exact
  primary fingerprint gates pass. Harness acceptance and the final local
  commit remain the convergence gates.

## Local Commit

The execution report is included in the exact #36-owned commit created by the
shared controller only after every migration check passes. Its SHA is Git
metadata and is intentionally not self-referential inside this committed file.
