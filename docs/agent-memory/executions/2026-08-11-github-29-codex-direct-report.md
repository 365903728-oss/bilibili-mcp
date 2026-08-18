# Execution Report: GitHub Issue #29

## Contract

- Task/source: GitHub Issue #29, blocked-by-none child of approved spec #28
- Mode: `codex-direct`
- Canonical worktree: `C:\Users\ZX\.codex\worktrees\harness-v2-29\bilibili-mcp`
- Base: `44ac1e717001aed59c4a3b475cf82f074d11e567`
- Writer/acceptance owner: Codex / Codex
- Authority: scoped repository writes, local verification, and one accepted
  local commit; no push, PR, Issue mutation, tag, release, publish, credential,
  SSH, history rewrite, broad deletion, or adapter fallback
- Manual Skill evidence: user invoked `$implement` for #29
- Terminal state: `ACCEPTED`

## Summary

Issue #29 establishes the portable Harness v2 session substrate without
starting any execution loop. One shared `RULES.md` governs three adapters;
`AGENTS.md` and `CLAUDE.md` contain only host deltas. A stdlib-only shared CLI
provides diagnostics, contract validation, Hook normalization/replay, native
manual-Skill reminders, dynamic Git attribution, and bounded redacted runtime
persistence under the invoking worktree.

## Files Changed And Diff Scope

- Shared core and adapters: `RULES.md`, `AGENTS.md`, `CLAUDE.md`
- Portable client translators: `.codex/hooks.json`, `.claude/settings.json`
- Shared runtime: `harness/` package, schema/example, fixtures, and tests
- Compatibility: `.codex/scripts/hook_safety.py`, context-budget script, and
  existing legacy Hook tests retained
- Governance: project-memory protocol, security, codemap, active work, context
  budget, task template, research note, and this execution report
- Package boundary: `.gitignore` ignores `.harness/`; npm package inputs and
  product sources are unchanged

## Commands And Results

| Check | Result |
| --- | --- |
| `python -m unittest discover -s harness/tests -p "test_*.py"` | PASS, 26/26 |
| `python .codex/scripts/test_hook_safety.py` | PASS, 6/6 |
| `python .codex/scripts/test_stop_summary.py` | PASS, 8/8 |
| `python -m compileall -q harness .codex/scripts` | PASS |
| `npm run build` | PASS |
| `npm test -- --run` | PASS, 41 files / 862 tests |
| example typed-contract validation | PASS, `valid: true` |
| `python -m harness doctor --json` | Correct gate: `action-required`; Codex tracked/primary/user `4/5/0` |
| `npm pack --dry-run --json` | PASS, 185 files, required entries present, forbidden Harness entries 0 |
| scoped high-confidence secret scan | PASS, 37 files, findings 0 |
| `git diff --check` | PASS |
| final Spec and Standards reviews | PASS, no P0-P3 |

Host evidence also includes clean Codex and Claude rule discovery, all four
Codex translator commands at a process boundary with exact stdin forwarding, a
trusted Codex lifecycle observation, and a real Claude failure lifecycle with
exit code 7. Synthetic replay inputs contain no real credential.

## Acceptance Criteria

| Criterion | Judgment |
| --- | --- |
| Clean Codex and Claude discover shared rules plus only host delta | PASS |
| Diagnostics report three adapters/capabilities without provider/model pin | PASS |
| Codex and Claude replay fixtures produce equivalent semantic events | PASS |
| Nested directory and second worktree attribution avoid dirty main | PASS |
| Runtime input is bounded/redacted and excludes raw sensitive payloads | PASS |
| Existing Hook safety is retained and extended | PASS |
| Dirty primary checkout remains outside ticket changes | PASS; six fingerprints match |
| npm package excludes Harness/runtime/project memory | PASS; forbidden count 0 |
| Contract records mode/worktree/writer/authority/acceptance/terminal/no-switch | PASS |
| Missing native manual Skill emits one bounded reminder without imitation | PASS, including concurrency |

## Repairs And Failure Fingerprints

- Replaced path-bound Hook commands with dynamic Git-root translators and fixed
  PowerShell/stdin process-boundary behavior.
- Added missing `.codex/skills` inventory and host-bound `$` versus `/` manual
  invocation validation.
- Registered Claude success and failure events separately; successful response
  `message` fields no longer imply failure.
- Opaque-hashed session identifiers, truthful persistence results, bounded
  advisory locking, and stale-lock behavior now have regressions.
- Added deterministic diagnosis for overlapping primary/user Codex Hooks and
  machine-local Claude Hooks without command/path disclosure or auto-rewrite.
- Moved manual reminder check-and-append under one OS lock after the red
  concurrency test produced 24 duplicate reminders; green evidence is one
  emitted reminder, 23 deduplicated results, and one ledger row.

## Risks, Skipped Checks, Recovery Bundle

- The primary checkout still has five legacy Codex Hook commands that overlap
  four tracked v2 commands in the linked worktree. Rollout is intentionally
  gated by `doctor=action-required`; migration is not authorized in #29.
- A normal-config Codex smoke waited on unrelated user MCP shutdown after
  returning its marker. Clean rule discovery therefore uses user configuration
  disabled, while Hook command behavior is independently process-tested.
- The full real three-adapter execution/pilot matrix is #36. No adapter loop,
  accepted-memory projection, or self-evolution runtime was built early.
- No Recovery Bundle is required because the selected adapter completed and the
  task reached acceptance. No adapter switch occurred.

One live trusted Codex smoke activated a primary legacy Stop Hook and changed a
date-only queue line in the dirty main checkout. The exact captured baseline was
restored immediately. Final primary-checkout evidence matches HEAD
`ab4dd028…`, status 68 / `a4bbfb6d…`, tracked diff `78271fe3…`, untracked 44 /
manifest `cf938aa3…`, and no `.harness` directory.

## Capabilities Used

- Manual Skills: `$implement` (explicitly invoked by the user)
- Model-invoked/project Skills: `tdd`, `vitest`, `secret-scanning`,
  `code-review`, `bilibili-mcp-memory`, `git-local-commit`
- Reviewers: `ticket29_spec_review`, `ticket29_standards_review`; both final
  results PASS with no P0-P3
- CLI/tools: `git`, `gh` for live Issue/remote identity reads, Python unittest
  and Harness CLI, npm/TypeScript/Vitest, clean Codex/Claude host smokes
- Intentionally unused: Paseo/Claude implementation writer, AgentKey, and the
  `ai-coding-harness` Skill; the user selected direct Codex and had explicitly
  excluded that Skill during design

## Harness Artifacts

- Research: portable rules/Hook note refreshed with current official semantics
  and live evidence
- Security: worktree attribution, redaction, external Hook overlap, locks, and
  no-secret boundary recorded
- Codemap: shared core/CLI/runtime/Hook surfaces recorded
- Memory: facts, decisions, verification, active work, and this report updated
- Harness eval: #29 usefulness, caught failures, overhead, and next changes
  recorded
- QA checklist: no public product/install/MCP behavior changed, so no separate
  human-facing QA instance was needed

## Local Commit

Acceptance authorizes one focused local commit containing only #29-owned files.
The commit does not push, close the Issue, publish, or absorb the dirty primary
checkout. Its SHA is the branch HEAD containing this report.
