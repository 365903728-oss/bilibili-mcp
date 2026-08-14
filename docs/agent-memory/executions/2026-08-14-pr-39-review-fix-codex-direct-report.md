# PR #39 automated-review repair — Codex Direct execution report

## Scope and authority

- Source: PR #39 review on commit
  `2fd2b9b0141d536534c7e565aad9172bac72d9b5`.
- Frozen mode: `codex-direct`; Codex retained the only implementation writer
  lease. No adapter switch, daemon action, credential/SSH operation, push, PR
  mutation, tag, release, or publish occurred.
- Scope: the three reproducible review findings only—portable pilot/migration
  digests, an OS-native contract fixture, and reachable zero-candidate local
  Build—plus the evidence updates required to keep #36 migration acceptance
  truthful after the Evolution repair.

## Implementation

1. Pilot artifacts, migration, and durable-memory evidence are verified from
   LF-normalized repository bytes; their recorded digests no longer depend on a
   Windows CRLF checkout.
2. `valid_contract()` derives its canonical worktree from a resolved native
   absolute `Path`, passing the same suite under Windows and WSL/POSIX.
3. Empty candidates are accepted only for `decision=build` with no selected
   candidate and every source marked `no-match`. Candidate-specific pin
   verification is skipped only in that absence path. Local Build still passes
   the canonical compiler, frozen evaluator/holdout, rollback, terminal
   revalidation, and Direct acceptance gates.
4. #36 clean-room evidence keeps exact #35 comparisons for unchanged paths and
   records the reviewed `harness/evolution.py` repair with its own byte digest.

## TDD and verification

- Red cases reproduced all four line-ending-dependent artifact hashes, the
  POSIX absolute-path failure, the unreachable empty-candidate Build, and the
  inconsistent empty-candidate/`candidate`-source acceptance.
- Focused green cases cover Windows and POSIX contracts, migration/pilot bytes,
  zero-candidate Build through accepted commit, candidate-backed Search/Adapt,
  dangerous authorization, v2 version gating, and legacy Build rollback and
  promotion.
- Final risk-weighted verification and independent read-only review are recorded
  below after the evidence index is frozen.

## Recovery continuation

The first repair contract omitted the migration artifact that the review fix
needed to update. The controller entered `recovery-required`, captured a typed
five-path Recovery Bundle, and preserved the same Codex writer and mode. The
unchanged diff was stashed reversibly, a same-base continuation froze ten exact
owned paths including the migration artifact, and the stash was reapplied. No
implementation was lost or silently written outside the active lease.

## Final acceptance

- Final short Harness matrix: 27/27 in 12.814s. The migration/pilot test was
  rerun after formatting and passed 1/1 in 1.514s.
- POSIX contract proof: WSL passed 9/9 in 0.021s. The final zero-candidate
  Search→Build→Evaluate→Accept lifecycle passed 1/1 in 68.735s.
- Candidate-backed security regressions passed 5/5 in 118.430s; the legacy
  Build reject/rollback/promote/accept path passed 1/1 in 130.859s.
- Black check, Python compilation, strict UTF-8 over all changed files, JSON
  parsing, canonical digest recomputation, `git diff --check`, scoped path
  inspection, and high-confidence secret scanning passed. Ruff was unavailable
  in the environment and was neither installed nor reported green.
- Independent read-only risk review returned PASS with no reproducible P0–P3.
  It specifically rechecked normalized hashes, the OS-native fixture, the
  all-source `no-match` gate, non-empty candidate verification, Adapt/Deferred,
  rollback, terminal acceptance, and downstream `candidate=None` handling.
- Controller acceptance is authorized to create exactly one scoped local
  repair commit. Push and all other remote effects remain unapproved.
