# Active Work

## Harness v2

GitHub Issue #28 is the approved Harness v2 specification. Issues #29-#36 are
the dependency-ordered implementation tickets. Accepted implementation lineage
is #30 `cbd31b952aa9f820005e60852bcd2d4db886a31c` → #31
`5e9de4bace35a2ca4b9c83b5a0d81ebb627df6fb` → #32
`9cbb8de64ffedefd682517e203841dd137b75662`. The live Issues remain open
because Issue-close and remote-write authority were not granted.

Issue #33, `Automatic typed memory from accepted evidence`, is the current
acceptance candidate on branch `codex/harness-v2-typed-memory-33` from the exact
#32 commit. It adds one shared, host-neutral typed-memory projector and thin
shared-CLI routes without changing the three accepted-ticket controllers.
Stable records carry source/provenance, validation, sensitivity, validity or
supersession, and an evidence digest. Replay is deterministic; current facts
supersede older values; weak claims stay proposed/deferred; and general lessons
need explicit correction or two independent accepted task IDs.

The source task must be accepted and committed, and its passing current evidence
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

The final dependency frontier becomes Issue #34 after #33 acceptance. The
known primary legacy Codex Hook overlap remains an explicit
`doctor=action-required` rollout gate and was not rewritten. No push, PR, Issue
close, tag, release, publish, credential/SSH use, or history rewrite is part of
#33.

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
