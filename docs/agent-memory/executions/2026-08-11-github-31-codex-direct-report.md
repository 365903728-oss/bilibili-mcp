# GitHub Issue #31 Codex Direct Execution Report

Execution window: 2026-08-11–2026-08-12
Issue: [#31 `[Harness v2] Claude Direct accepted-ticket loop`](https://github.com/XZXZZX-Ai/bilibili-mcp/issues/31)
Parent contracts: #28 and accepted #30
Mode: `codex-direct` (selected once and frozen)
Real acceptance pilot mode: `claude-direct`
Manual phase evidence: native `$implement` invocation supplied by the user
Baseline: `cbd31b952aa9f820005e60852bcd2d4db886a31c`
Branch: `codex/harness-v2-claude-direct-31`
Status: accepted candidate; the focused local commit is created only after the
final verification and staged-scope gates below pass

## Contract

- Codex is the sole planner, writer, verifier, reviewer, acceptance owner, and
  focused-commit owner for this implementation worktree. No Paseo or Claude
  writer was launched into it; the required Claude writer ran only in the
  disposable pilot repository documented below.
- The user selected and froze `codex-direct`, natively invoked `$implement`,
  authorized scoped implementation/tests/review/the required disposable Claude
  pilot, and authorized one local acceptance commit only.
- Exact parent: `cbd31b952aa9f820005e60852bcd2d4db886a31c`, the accepted and pushed #30
  commit. The new worktree was clean before the Codex app later created
  untracked `.codex/config.toml`; that runtime file remains unchanged and is
  excluded from the ticket and commit.
- Live #31, rather than the stale local title, is authoritative. Its title is
  `Claude Direct accepted-ticket loop`; the next live dependency frontier is
  #32, `Codex–Paseo–Claude accepted-ticket loop`.
- `python -m harness doctor --json` remains the expected `action-required` with
  tracked/primary/user Codex Hook command counts `4/5/0` and no Claude-local
  conflict. No primary, user, or external configuration was rewritten.
- The dirty primary checkout `C:\Users\ZX\bilibili-mcp` remains at
  `ab4dd02854f0483fc7668c713523b4be77de6cc7`, status count 68 / hash
  `34ef9dee55da26ef977b54e795477f493e18dded`, tracked-diff hash
  `c9a4daa32c34115d3d443a52afa81301416b6082`, untracked count 44 / hash
  `2ec8b5fa42ed2cf4d684a5c7b9156998756abecb`, and staged count 0, exactly
  matching the #30 pre-write fingerprints.

## Summary

- `claude-direct` is a second public entrypoint to the accepted #30 controller,
  not a copied controller and not a fallback. Mode-specific run/control schemas,
  writer, acceptance owner, manual-Skill host/prefix, and Recovery Bundle mode
  are derived from the frozen contract.
- Every public state read or mutation supplies `expected_mode`; Codex commands
  cannot inspect or mutate Claude state and Claude commands cannot control Codex
  state. The shared sibling-worktree scan recognizes both run schemas and rejects
  same-source Codex/Claude writer collisions.
- Claude manual Skills retain native `/skill` syntax. Missing `/implement`
  emits one source-bound reminder, creates no run or repository diff, and remains
  deduplicated. Unstable-start rollback now uses the same source identity as
  marker creation.
- Guards, diff-bound typed evidence, criterion judgments, risk state, finite
  repair/failure fingerprints, complete Recovery Bundles, exact accepted
  snapshot, hermetic `commit-tree`/CAS `update-ref`, released writer lease, and
  idempotent commit recovery remain the single shared implementation.
- One frozen fixture now drives the complete public start → guard → verify →
  review → judge → accept/commit lifecycle for both Direct adapters. Existing
  Codex/Claude Hook replay fixtures continue to prove the shared typed
  projection and redaction boundary.

No product source, public MCP tool/CLI behavior, package metadata, dependency,
workflow, tracked Hook registration, release surface, or remote GitHub state is
changed.

## Files Changed And Diff Scope

- `harness/contracts.py`, `harness/cli.py`, and `harness/codex_direct.py`:
  shared typed Direct-mode validation, public Claude entrypoint, command-mode
  fencing, writer/owner projection, reminder rollback, and shared acceptance.
- `harness/fixtures/direct-adapter-conformance.json` and
  `harness/tests/test_claude_direct.py`: one frozen adapter mapping plus the
  Claude process/guard/lease/recovery/commit/conformance regressions. The test
  subprocess boundary uses a credential-free allowlisted environment.
- `harness/tests/test_contracts.py` and
  `harness/tests/test_cli_and_adapters.py`: fixture validation and documented
  public adapter projection.
- `CLAUDE.md` and `harness/README.md`: the Claude Direct prefix, lifecycle, and
  cross-adapter boundary.
- `docs/agent-memory/{active-work,codemap,context-budget-report,decisions,
  harness-eval,harness-security,lessons-learned,project-facts,verification-log}.md`
  plus this unified report: current frontier, design/security/eval evidence,
  verification, and accepted candidate state.
- Excluded: app-created untracked `.codex/config.toml`, ignored pilot/runtime
  data, dirty primary-checkout contents, `node_modules`, product/package files,
  and every remote operation.

## Commands And Results

### TDD Evidence

The process-boundary seam was fixed before the green implementation:

1. The first Claude start test failed because `claude-direct` was not a valid
   CLI choice; adding the shared parser/contract path made it green.
2. A Codex status command initially returned a Claude run with exit 0; the
   shared `expected_mode` load invariant made status and mutation rejection
   green.
3. The second missing-Skill attempt returned `/$implement`; the failing exact
   native-invocation assertion fixed it to `/implement`.
4. An unstable repository-lock test left a source-scoped reminder behind;
   central source identity derivation made rollback and a fresh reminder green.
5. The conformance test initially failed because the shared fixture did not
   exist. It now executes both public Direct lifecycles rather than checking
   only static mappings.

Focused Claude/contract/adapter groups passed 34 tests in 59.193 seconds before
the executable two-adapter conformance extension. The extension then passed
both targeted tests in 24.991 seconds. A later review-driven environment
hardening pass ran the full Claude module (11 tests in 65.114 seconds) and its
new credential-exclusion regression (1 test in 0.488 seconds); both passed.

### Real Claude Direct Pilot

#### Isolation And Launch

- Host: real `claude` CLI 2.1.212, authenticated through the installed OAuth
  route. No credential value was printed or stored in formal memory.
- Repository: ignored
  `.harness/pilots/github-31-claude-direct-real-v1`, containing only copied
  Harness policy/runtime/test surfaces, with zero Git remotes.
- Seed/base: `c4844708eebdaf4339feb26c0f91877a66321367` on `main`.
- Launch posture: `--permission-mode bypassPermissions`,
  `--setting-sources project`, strict empty MCP configuration,
  `--no-session-persistence`, stream Hook evidence, and USD 2.00 hard cap. No
  `--model`, fallback model, provider, credential, or remote flag was passed;
  the stream reported the live environment's resolved model as
  `deepseek-v4-flash`, which was not copied into repository configuration.
- The pilot contract used `required_manual_skills: []`. It therefore does not
  claim user-native `/implement` evidence; that gate is independently proven by
  the process tests above.

Attempt 1 exited before Harness start because `{}` was not a valid strict MCP
configuration; Claude required the explicit `{"mcpServers":{}}` envelope. The
repository remained clean and no run state existed. Attempt 2 completed in
190.481 seconds / 63 turns, reported USD 1.906883, and exited 0. The ignored raw
stream is retained only as local validation evidence. Claude made one read-only
status/remote inspection of the containing project before resolving the pilot
root; every write, Harness transition, and commit occurred in the disposable
repository, and the primary fingerprints remained unchanged.

#### Actual Commands And Results

| Step | Actual operation | Result |
| --- | --- | --- |
| Preflight | `git status --short`, `git remote -v`, branch/root checks | pilot clean, `main`, zero remotes |
| Start | `python -m harness claude-direct start .../contract.json` | `executing`, Claude lease active |
| Guards | `guard --action edit --path harness-only.txt`; `guard --action test` | both `allowed`, no approval prompt |
| Write | create `harness-only.txt` with `claude-direct pilot\n` | exact 20 UTF-8/LF bytes |
| Verify | strict Python byte/text assertion | PASS, exit 0 |
| Evidence | `record-check owned-file-check ... --source command --exit-code 0` | PASS, digest `236b2d25…e4c39` |
| Review | `git diff --check`, complete no-index diff, status inspection | PASS; only `harness-only.txt` |
| Review evidence | `record-check review-check ... --source review` | PASS, digest `e0763325…5293` |
| Judge | `judge claude-produced-owned-diff --status pass` | PASS against command evidence |
| Accept | `accept --message "test(harness): prove real Claude Direct pilot"` | one local commit created |
| Postconditions | log/parent/tree/blob/status/remote and Harness status | all PASS; accepted, clean, released lease, zero remotes |

Claude first supplied `--exit-code 0` to review-sourced evidence. The controller
correctly rejected it without mutating the evidence log; Claude removed the
invalid argument and continued. This was one bounded command correction, not a
Harness repair attempt.

#### Accepted Evidence

- Commit: `d4875bfe6b21e2e460d7fad2ebb59e3165a32c1e`.
- Parent: exact seed `c4844708eebdaf4339feb26c0f91877a66321367`.
- Commit count from base: 1; changed path count: 1; remote count: 0.
- Changed path: `harness-only.txt`; committed bytes are exactly
  `claude-direct pilot\n`.
- Opaque trailer: `Harness-Task: 8ea76b34ebcb6332832e71df`.
- Current diff digest:
  `822b59de95009f76c2663d2641e4754b19a4e979cb6a1a3c6a4fcfce59178166`.
- Accepted snapshot/index digests:
  `16720b9e797a9ff058e0eb5dd38f057dee195b2c8a9655fcbbdf903e38f49bb5` /
  `3c4cf5dc742af53b8014cd4b8cce655a60e5aacd82c41032fa1ebd080a102a94`.
- Evidence records: 2 passing; repairs: 0; risks: `{}`; Recovery Bundle: absent;
  criterion `claude-produced-owned-diff`: PASS.
- Skipped because unauthorized or unnecessary: push, PR, tag, release, publish,
  credentials/SSH, broad delete, history rewrite, agents, Paseo, MCP tools,
  `repair`, and `recover`.

### Final Verification

- `python -m unittest discover -s harness/tests -p "test_*.py"`: 105 tests
  ran in 339.095 seconds; `OK (skipped=1)` for one platform-permission case.
- `python -m compileall -q harness .codex/scripts`: pass. The frozen example
  contract validates as `harness.contract-validation/v1` for `github:#30`.
- Legacy compatibility: Hook safety 6/6 and Stop summary 8/8 pass.
- The fresh worktree initially lacked `node_modules`, so the first build could
  not resolve `tsc`. After exact-lockfile `npm ci`, `npm run build` passed and
  full Vitest passed 41 files / 862 tests in 8.50 seconds. Manifests and the
  dependency graph are unchanged.
- `npm audit --omit=dev --json`: zero production vulnerabilities. The full
  unchanged development graph retains eight advisories: one moderate, six high,
  and one critical.
- `npm pack --dry-run --json`: 185 files, 1,088,657 packed bytes, 1,718,671
  unpacked bytes, required `dist/index.js`, `dist/cli.js`, and `dist/index.d.ts`,
  zero forbidden Harness/rules/adapter/project-memory paths, and no tarball.
- Final 19-file strict UTF-8/BOM and added-U+FFFD checks, high-confidence
  added-content credential scan, and `git diff --check` pass with zero findings.
- `python -m harness doctor --json`: expected `action-required`, tracked/
  primary/user Codex Hook counts 4/5/0, tracked/local Claude counts 5/0, and no
  configuration rewrite.
- Context budget remains `Status: OK` at 8,271 estimated always-relevant tokens.
  The dirty primary checkout remains exactly at the #30 fingerprints recorded
  in Contract: HEAD `ab4dd028…`, status 68 / `34ef9dee…`, tracked diff
  `c9a4daa3…`, untracked 44 / `2ec8b5fa…`, staged 0.
- Frozen controller/Claude-test SHA-256 values are
  `a40b65dadbc44627a8771b58520916f3c24012e6884b5bfda9d45d7dcb979c29` /
  `595bd28601e31945d90f0b58c3e2737d880427ddb2c1503b2da0474c5579f69b`.
  Final Standards, Spec, and independent risk review are PASS with no remaining
  P0-P3.

## Acceptance Criteria

| Criterion | Judgment | Evidence |
| --- | --- | --- |
| Actual Claude Direct session completes the path | PASS | real Claude Code attempt 2 and exact accepted pilot commit |
| Shared mode/base/worktree/lease/authority/evidence/recovery/acceptance/commit semantics | PASS | one controller plus two-adapter executable conformance lifecycle |
| Mode frozen before write; second writer rejected | PASS | start state plus mixed Codex/Claude same-source collision test |
| Ordinary scoped work bypasses routine approvals | PASS | edit/test guards and zero pilot prompts |
| Exceptional-risk guards remain deterministic | PASS | Claude action matrix covers delete/history/credential/SSH and remote classes |
| Native manual Skill remains manual and one-shot | PASS | exact `/implement`, reminder deduplication, zero run/diff, rollback regression |
| Repair is finite and no-progress stops | PASS | Claude repeated-failure Recovery Bundle plus shared #30 repair-limit suite |
| Failure emits complete Recovery Bundle without switch | PASS | explicit and automatic Claude adapter-failure tests |
| Exactly one scoped local commit, no remote/unrelated dirt | PASS | test lifecycle and independently verified real pilot Git shape |
| Shared replay/conformance fixtures pass | PASS | existing typed Hook replay plus fixture-driven dual public lifecycle |
| Pilot records diff/commands/results/skips/risks/criteria | PASS | this report and ignored raw evidence |

## Repairs And Failure Fingerprints

The user-invoked two-axis `code-review` used fixed point `cbd31b9…` against the
pre-commit working candidate:

- Standards P1: required codemap/security/eval/verification/active-work and
  unified report were missing. Fixed by the #31 memory/report updates.
- Standards P3 judgment: shared functions retain Codex-oriented compatibility
  names. No action: renaming the accepted 2,800-line #30 module/API would add
  churn without changing authority; the new public seam, mode schemas, and docs
  are neutral while compatibility remains explicit.
- Spec P1: the reviewer could not see the ignored real pilot and no report yet
  existed. Fixed by this evidence-backed report; the pilot itself had already
  passed independently.
- Spec P2: the first conformance fixture checked static mappings only. Fixed by
  making that same fixture drive both complete public Direct lifecycles.
- Risk-review P2: the new subprocess tests inherited the full agent environment.
  Fixed with a platform-variable allowlist, disabled global/system Git config
  and prompts, and a credential-key exclusion regression at all new child
  process boundaries.
- Risk-review P2: the first report name described the pilot adapter and omitted
  unified sections. Fixed by naming this report for the frozen ticket mode and
  using the required Contract/Summary/Diff/Commands/Acceptance/Repairs/Risks/
  Capabilities/Artifacts/Commit structure.

Final Standards and Spec follow-ups returned PASS. The independent
risk-weighted review, including reconciliation of its separate standards axis,
returned PASS with no remaining P0-P3 after the two P2 repairs above.

## Risks, Skipped Checks, Recovery Bundle

- Primary legacy Codex Hooks still overlap the tracked v2 adapter. The expected
  `doctor=action-required` migration gate remains; #31 has no authority to
  rewrite primary/user configuration or perform a normal-config rollout.
- The first product build attempt found no `node_modules` in the fresh linked
  worktree (`tsc` unavailable). `npm ci` restored the exact lockfile graph; no
  dependency manifest changed. The full development graph reports the known
  eight advisories (one moderate, six high, one critical), while the shipped
  production graph reports zero vulnerabilities. No `npm audit fix` was run.
- Real pilot attempt 1 failed before Harness start because strict MCP config
  needed an explicit `mcpServers` object. It created no run or diff. Attempt 2
  passed; no repair or task Recovery Bundle was needed.
- Intentionally skipped because unauthorized or out of scope: normal-config
  rollout, push, PR, Issue close, tag, release, publish, credential/SSH action,
  history rewrite, broad deletion, Paseo launch, adapter fallback, and product
  QA/release validation beyond unchanged build/test/package gates.

## Capabilities Used

- Manual Skill: `$implement` (native user invocation).
- Model-invoked/project Skills: `bilibili-mcp-memory`, `tdd`, `vitest`,
  `code-review`, `secret-scanning`, and `git-local-commit` at commit time.
- Read-only agents: seam/test exploration, fixed-base Standards and Spec review,
  and one final independent risk-weighted review with a separate standards axis.
- Local/live tools: Git, `gh` Issue reads, Python/Harness CLI, npm, TypeScript,
  Vitest, and the real bounded Claude CLI pilot.
- Intentionally unused: Paseo/Claude implementation writer, adapter fallback,
  MCP application tools, AgentKey, credentials/SSH, and remote Git/release tools.

## Harness Artifacts

- Unified report: this file; no collaboration handoff was needed because the
  frozen mode was `codex-direct`.
- Research: no separate external research note was needed; the design derives
  from live Issues #28/#30/#31, the accepted local controller, and executable
  CLI/Git evidence.
- Security/codemap/memory/eval: `harness-security.md`, `codemap.md`, facts,
  decisions, lessons, `active-work.md`, `verification-log.md`, and
  `harness-eval.md` are updated together. The context-budget report remains OK.
- Runtime/pilot: ignored executable inputs and bounded generated state remain
  under `.harness/`; neither raw Claude streams nor pilot repository contents
  enter formal memory, the package, or the ticket commit.
- QA: no public product/install/MCP behavior changed, so a separate product or
  release QA checklist is not warranted.

## Local Commit

The accepted candidate changes no product runtime behavior and adds no package
dependency, model/provider config, tracked local permission file, or remote
state. The focused branch commit containing this report is the single #31
acceptance commit; if this report is not yet in HEAD, #31 remains an accepted
candidate. No push, PR, Issue close, tag, release, publish, credential/SSH
action, history rewrite, or broad deletion is authorized or performed.
