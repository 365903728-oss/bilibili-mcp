# Active Work

## Harness v2

GitHub Issue #28 is the approved Harness v2 specification. Issues #29-#36 are
the dependency-ordered implementation tickets. Issues #29 and #30 are accepted;
#30's accepted and pushed commit `cbd31b952aa9f820005e60852bcd2d4db886a31c`
is the exact base for Issue #31, `Claude Direct accepted-ticket loop`. The
focused local commit containing this record is #31's acceptance commit; before
that commit exists in HEAD, #31 remains a final acceptance candidate. The live
Issues remain open because no Issue-close, push, or PR authority was granted
for this ticket.

#31 froze `codex-direct` for the implementation worktree, the clean
`cbd31b9…` base, branch `codex/harness-v2-claude-direct-31`, Codex's sole writer
and acceptance ownership, and the user's native `$implement` invocation. The
shared Direct controller now gives `claude-direct` the same typed contract,
state, canonical writer exclusion, authority guards, diff-bound evidence,
bounded repair, Recovery Bundle, acceptance, and exact automatic local-commit
semantics as `codex-direct`, while rejecting cross-adapter control.

A real Claude Code 2.1.212 session completed the full Claude Direct loop in an
ignored zero-remote Harness-only repository, changing only `harness-only.txt`
and creating exactly one accepted commit. Its pilot contract required no
manual Skill; `/implement` one-reminder/zero-write behavior is proven separately
at the public process boundary and is not claimed as native pilot evidence.

Issue #32 is a Codex-accepted candidate; the focused local commit containing
this record is its acceptance commit. The collaboration adapter
(`harness/paseo_collaboration.py`, ~2072 lines) reuses the shared #30/#31
controller for contracts, locking, state, guards, recovery, acceptance, and
commit. Collaboration-specific behavior (read-only Paseo/provider preflight,
bridge-triggered native `/implement`, one frozen writer, bounded dispatch and
report, same-agent repair, and recovery) remains a thin public CLI seam.

The focused collaboration module contains 73 tests. Attempt 6 passed the full
module 71/71 before the final CLI-boundary proof was added; attempt 7 then
passed that new public-process proof independently, and the final full Harness
suite covered the resulting 72-test snapshot. Attempt 8 added one focused
accepted-state authority regression; the new proof passed independently and
with all seven guard tests. The proofs include
trust-boundary proofs for frozen handoff/agent/diff identity, every recorded
repair delivery, metadata-only reports, and unconditional prompt cleanup after
failed sends. A real public-path Paseo pilot resolved the live preference
`claude/deepseek-v4-flash`, recorded native `/implement`, changed only
`harness-only.txt`, and advanced from seed `eb0205b…` to exactly one accepted
local commit `291ad721…`; it finished clean with a released lease and zero
remotes. Full Harness, legacy Hook, TypeScript, Vitest, package, secret, scope,
and dirty-primary gates are recorded in the Issue #32 execution report.
The user explicitly authorized a sequential writer transfer for repair attempt
7: the original idle writer released its lease, one replacement
`claude/deepseek-v4-pro[1m]` writer was live-inspected at thinking `max`,
closed the last malformed-contract CLI boundary, reverified it on a max-thinking
turn, and returned idle. The route is execution evidence only, not tracked
governance configuration.
The user then authorized repair attempt 8 on the same replacement writer. It
closed the final staged-review finding by rejecting Claude `local-commit`
before the actor-agnostic shared guard while preserving Codex's accepted-state
commit gate. The writer returned idle, Codex reran the focused proof, and both
original reviewers returned PASS.
No push, PR, Issue close, tag, release, or publish was authorized or performed.
The implementation branch remains `codex/harness-v2-paseo-claude-32` from exact
base `5e9de4bace35a2ca4b9c83b5a0d81ebb627df6fb`.

The dependency frontier advances to Issue #33 once Codex accepts #32. A new
ticket still requires one frozen mode decision and its own native manual Skill
evidence. The primary legacy Codex Hook overlap remains an explicit
`doctor=action-required` rollout gate and was not rewritten.

The Harness target is one `RULES.md` core with `codex-direct`,
`codex-paseo-claude`, and `claude-direct` adapters. Local commit is automatic
after acceptance; push/PR/tag/release/publish remain separate user gates.
Manual Matt Skills stay native manual and receive one deduplicated reminder
when required but not invoked.

## Published Product Baseline

Status: `v1.11.4` is published to npm, GitHub Releases, and the Official MCP
Registry as `io.github.XZXZZX-Ai/bilibili-mcp`. Release commit `2a33520`
contains the five synchronized version fields, bilingual changelogs, and
release records for merged PR #26 and PR #27. Annotated tag `v1.11.4` peels to
that exact commit. GitHub Actions run `31296387097` passed tests, build, and npm
trusted publishing; npm `latest` is `1.11.4` with registry signature and SLSA
provenance. The public GitHub Release is non-draft/non-prerelease, and the
Official Registry reports `1.11.4` as `active` and `isLatest=true`.

The release publishes PR #26 for comments, language, credential, numeric-
config, dotenv-order, and endpoint-aware `-403` contracts, plus PR #27 for
fail-closed malformed search responses. Both remain merged through base commit
`1067e02`; the release metadata adds no runtime, dependency, workflow, README,
or ten-tool boundary change.

The local `1.11.4` candidate passed exact publish-runner Node `22.14.0` / npm
`11.18.0` clean install, build, 41 files / 862 tests, 2 files / 19 focused
stdio tests, a 185-file package, zero-vulnerability production audit, live
official Registry schema validation, strict UTF-8/diff checks, and scoped
credential scans. Credential-safe live MCP stdio calls reported a valid login,
three stable searches for `五道口纳什`, and real comment limits of 21 and 50
without printing Cookie values. Full development-tree audit findings remain
separately recorded in the release QA and are not production dependencies.
Independent release, standards/security, and specification reviews returned
PASS with no remaining P0-P3.

Post-publication verification installed exact npm package `1.11.4` in an
isolated directory, verified all 97 installed-package registry signatures and
10 attestations, and ran the package under Node `22.14.0`. MCP initialize
reported server `bilibili-mcp-server` version `1.11.4`, listed exactly ten tools,
and an authenticated live `五道口纳什` search returned five results containing
the target author. No credential value was recorded.

The published `v1.11.3` release verification passed the TypeScript build, 39 files / 803 tests,
production audit with zero vulnerabilities, a 181-file package with required
dist entry points and no forbidden paths, Registry metadata validation,
diff/UTF-8/value-free secret checks, two independent read-only reviews, and an
isolated exact-version CLI smoke. The main user worktree and its review-gated
learning-proposal change remained outside the clean release worktree.

The ten-tool product boundary and legacy stdio compatibility remain fixed. ASR
is explicit, default-off, native-subtitle-first, and ready-state-only. The local
doctor reports no ready model, so no model was downloaded or switched and no
live ASR end-to-end smoke was run. This is a documented validation boundary,
not unfinished Phase 3 implementation.

The pre-existing learning-proposal queue is legacy v1 state and remains outside
the clean #29 worktree. Typed accepted-evidence memory automation is scoped to
#33; #29 hooks only write ignored redacted events. Files under
`docs/superpowers/` are historical records only and must not trigger any
`superpowers:*` skill.

## Future Direction — Not Active

The ASR, CLI, documentation, and security work shipped in `v1.11.0`.
Revisit MCP protocol modernization only as a separate GitHub Issue:

1. Preserve the public wire-level legacy baseline now covered by `initialize` → `tools/list` → `tools/call`; extend it only as part of the separate migration ticket.
2. Convert the dated MCP research into a dual-era acceptance matrix covering modern `server/discover`, required result/cache fields, and legacy fallback.
3. Only then migrate to the TypeScript SDK v2 dual-era stdio path.
4. Evaluate optional annotations, icons, additional structured outputs, Tasks, MRTR, or HTTP transport features only when a real product need exists.

Sources: `docs/research/2026-07-29-mcp-protocol-update.md`, `docs/research/2026-07-29-mcp-tools-evolution.md`, and the 2026-07-29 entries in `docs/agent-memory/decisions.md`.

This direction is not active work and does not authorize a code change, GitHub Issue, implementation-agent launch, commit, release, or protocol-support claim.
