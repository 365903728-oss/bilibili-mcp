# Active Work

## Harness v2

GitHub Issue #28 is the approved Harness v2 specification. Issues #29-#36 are
the dependency-ordered implementation tickets. Accepted implementation lineage
is #30 `cbd31b952aa9f820005e60852bcd2d4db886a31c` → #31
`5e9de4bace35a2ca4b9c83b5a0d81ebb627df6fb` → #32
`9cbb8de64ffedefd682517e203841dd137b75662` → #33
`1cd12c8a6edab272bd16ad5ecb8ba2ae4bd90cf8` → #34
`493393c9ef4941e5ff8dc7b66acaa6cd9d06d7ce` → #35
`8de058e772e97a6ab8d16d65386081db76953320`. The live Issues remain open
because Issue-close and remote-write authority were not granted.

Issue #36, `Three-adapter conformance, real pilots, and migration acceptance`,
was accepted and pushed on branch
`codex/harness-v2-three-adapter-conformance-36`; PR #39 is the current
integration gate. Its review repairs continue in `codex-direct` from exact
pushed PR heads, with one writer lease per bounded round. The shared
conformance fixture now names all three public modes against one typed contract
and `RULES.md` kernel, while the shared Hook-event projection carries explicit
provenance, metadata sensitivity, a full digest, and active/stopped terminal
state without raw host payloads. Real bounded Codex Direct and Claude Direct
pilots are accepted in isolated zero-remote repositories with one scoped commit
each. After explicit user authority for one `paseo start`, the third real pilot
used Paseo 0.3.1 with `claude/deepseek-v4-flash`, created only `pilot.txt`, and
was accepted as commit `27fba0dce64fb591a30f0651979940089c667fb0` with a
released Claude lease and zero remote effects. No restart, adapter switch, or
fallback occurred. Migration/index, package exclusion, secret/diff, and dirty-
primary isolation gates are green. Current PR review repairs preserve those
accepted boundaries while adding cross-platform and trust-boundary regressions
only.

The first main acceptance run stopped in a Recovery Bundle because its frozen
owned path `harness/` overlapped immutable governed-Evolution roots. No kernel,
evaluator, holdout, or runtime record was edited to bypass that gate. The same
Codex writer restored the unchanged diff under a recovery continuation with
the same mode/base/worktree and 23 exact Issue-owned paths; no second
implementation actor or adapter switch was introduced.

The accepted #33 typed-memory substrate requires the source task to be accepted
and committed, and its passing current evidence
must contain the canonical semantic envelope digest. Projection writes only
`docs/agent-memory/typed-memory.json`, the bounded
`docs/agent-memory/current-memory.json`, and ignored metadata-only audit state.
It rejects secrets, raw operational payloads, tampered stores, ambiguous
same-time facts, and invalid provenance. No product source, MCP surface, Hooks,
Loop/controller, constitutional rule, installed Skill/Agent package, or
evaluator is a projector output.

`harness/capability-packages/bilibili-mcp-memory/canonical.json` is the single
versioned capability source. Deterministic Codex and Claude packages expose the
same interface, manifest hashes, and evaluation metadata; installed external
copies were not rewritten. A real disposable zero-remote Codex Direct pilot
accepted a source task and then exactly one memory-only commit containing only
the typed store and current projection; replay was a successful auditable
no-change outcome.

Every run freezes its linked worktree, exact-path writer, evaluator, holdout,
derived repository-local outputs, report, and candidate-scoped rollback
snapshot. Search binds the active host's installed `find-skills` route and
re-fetches pinned official/live GitHub artifact and license bytes before Adapt
or Build. Candidate-supplied compatibility, smoke, and installed provenance are
not trusted machine evidence, so Adapt stops once with zero capability writes
and no self-authorizing resolution route. A canonical
Skill/Agent source compiles drift-checked Codex/Claude packages into actual
repository discovery paths; subagents remain read-only with no children.
Failure restores only known candidate files and records rejected/deferred;
unknown drift enters Recovery. Promotion and the one local commit still pass
through the shared Direct acceptance path.

Safe declarative v2 candidates are fetched at immutable source revisions. Four
candidate-bound Search responses are re-fetched and their results are derived
by the governor rather than trusted from caller labels. Candidates are compiled
without executing candidate code and become auto-Adapt eligible only after the
governor itself creates three-adapter projection evidence. Unsafe
credentials/elevation/daemon/port/global-mutation/SSH/publish effects remain an
idempotent user-authorization stop. No-candidate runs can Build an MCP, CLI,
Hook, or Loop capability entirely under repository-local Harness paths. Hook
smoke invokes the deployed public handler, replays and reads its attributed
ledger, verifies shadow/no-diff, secret removal and linked-worktree identity,
then restores the deployment/config/canary/ledger snapshot; Loop decisions enforce
attempt/no-progress bounds, yield to user input, and stop adapter switches.

The known primary legacy Codex Hook overlap remains an explicit
`doctor=action-required` rollout gate and was not rewritten. No push, PR, Issue
close, tag, release, publish, credential/SSH use, or history rewrite is part of
#35.

Final current-diff evidence is green: Harness shards execute 230 tests with one
platform-permission skip, legacy Hook/Stop compatibility is 6/6 and 8/8,
product Vitest is 41 files/862 tests, and npm pack contains 185 files with zero
Harness paths. The independent reviewer reports no remaining live #35 blocker.

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
