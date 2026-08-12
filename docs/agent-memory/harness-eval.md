# Harness Eval

This file tracks whether the agent-assisted development harness is improving the project or adding unnecessary process. Use it for periodic workflow reviews, not for ordinary code tasks.

## Evaluation Triggers

Create or update an evaluation entry when:

- a roadmap phase or multi-task optimization cycle completes
- a release completes, especially if release automation, QA, or security review was involved
- several harness changes land together, such as new templates, skills, subagents, hooks, MCP/tool rules, or memory rules
- a workflow feels slower, heavier, or more error-prone than before
- a skill, subagent, hook, template, or fixed trigger may be redundant or harmful
- the user asks whether the Codex + Claude Code workflow is working well

Do not update this file for routine small bug fixes, narrow tests-only changes, or one-off implementation reports.

## Current Evaluation Backlog

Use this section to list harness components that should be evaluated after real use.

- `docs/agent-memory/codemap.md`: check whether it reduces repeated file discovery and improves handoff quality.
- `docs/templates/task-ticket.md`: check whether the three-tier ticket standard prevents scope drift without slowing small tasks.
- `docs/templates/research-note.md` and `docs/research/`: check whether external findings are easier to reuse.
- `docs/templates/qa-checklist.md` and `docs/qa/`: check whether real user workflow issues are caught before or after releases.
- `docs/agent-memory/harness-security.md`: check whether harness-surface changes become safer without becoming bureaucratic.
- Fixed skill/subagent/MCP/CLI triggers in `AGENTS.md` and `CLAUDE.md`: check whether agents choose capabilities more predictably.
- Matt Pocock workflow integration: after several real tasks, check whether GitHub specs/tickets plus file-backed handoffs improve continuity without duplicated planning artifacts and confirm that no Superpowers skill was invoked.
- Paseo execution bridge: after several delegated tasks, check whether one-agent Codex-to-Claude execution removes manual handoff work without causing overlapping edits, hidden decision points, or noisy repair loops.

## Entry Template

Copy this section for each evaluation.

### YYYY-MM-DD Harness Eval: <topic>

#### Period

- Start:
- End:
- Related tasks, tickets, releases, or plans:

#### Harness Changes Under Review

-

#### Signals

Useful positive signals:

-

Useful negative signals:

-

Candidate metrics:

- repeated file-discovery steps avoided:
- task-ticket uses:
- task-ticket skips that were appropriate:
- task-ticket uses that felt too heavy:
- codemap updates:
- codemap checked-and-unchanged reports:
- research notes created and reused:
- QA checklists created:
- issues caught before release:
- issues missed until after release:
- subagent/skill trigger mismatches:
- failed or noisy hook observations:

#### Findings

-

#### Keep / Change / Remove

Keep:

-

Change:

-

Remove or stop using:

-

#### Decisions Or Follow-Up

- [ ]

#### Memory Updates Needed

- [ ] `project-facts.md`
- [ ] `decisions.md`
- [ ] `lessons-learned.md`
- [ ] `codemap.md`
- [ ] `harness-security.md`
- [ ] `AGENTS.md`
- [ ] `CLAUDE.md`

### 2026-07-20 Harness Eval: v1.6.4 multi-ticket release preparation

#### Period

- Start: 2026-07-19
- End: 2026-07-20 pre-release review
- Related tasks, tickets, releases, or plans: GitHub Issues #2-#15 and v1.6.4

#### Harness Changes Under Review

- Matt GitHub tickets, file-backed Codex-to-Claude handoffs, one-agent Paseo execution, project QA records, capability triggers, and stop-summary reminders.

#### Signals

Useful positive signals:

- Focused tickets kept thirteen reliability fixes independently testable and made the final release diff separable into scoped commits.
- File-backed handoffs and reports preserved exact commands, constraints, skipped checks, and decision points across repeated implementation runs.
- Release review found and fixed two missing WBI retry regressions, added direct hook-script tests, excluded the generated learning queue, and caught a production Hono advisory before publication.

Useful negative signals:

- Repeated per-ticket reports created substantial documentation volume, and several delegated risk-review subagents stalled or needed top-level fallback review.
- The final release still required a separate consolidation pass to distinguish production blockers from development-only audit findings.

Candidate metrics:

- task-ticket uses: 14 GitHub Issues
- QA checklists created: release plus focused comment-pagination QA
- issues caught before release: missing WBI retry coverage, untested hook branching, production Hono advisory, generated learning queue exclusion
- issues missed until after release: 0 at pre-release cutoff
- subagent/skill trigger mismatches: 0; stalled reviews were completed through bounded fallback

#### Findings

- The workflow improved containment and auditability for a multi-ticket release, but the per-ticket reporting layer is heavier than necessary for future low-risk changes.
- One Paseo implementation agent remains the right default. Independent release verification adds value at the final boundary; additional autonomous agent trees would add noise.

#### Keep / Change / Remove

Keep:

- GitHub ticket as planning source, file-backed handoff for substantial implementation, one Paseo agent, focused tests, and independent final release verification.

Change:

- Use lighter reports for single-file, behavior-preserving fixes and consolidate repeated verification evidence into the release QA record.

Remove or stop using:

- Do not retry stalled review subagents indefinitely; use the documented top-level bounded fallback and record the gap.

#### Decisions Or Follow-Up

- [ ] Address development-only npm audit findings in a separate tooling-maintenance task rather than broadening v1.6.4.
- [ ] Re-evaluate report volume after the next multi-ticket release.

#### Memory Updates Needed

- [x] `project-facts.md`
- [ ] `decisions.md`
- [x] `lessons-learned.md`
- [x] `codemap.md`
- [x] `harness-security.md`
- [x] `AGENTS.md`
- [x] `CLAUDE.md`

### 2026-07-20 Harness Eval: v1.7.1 patch release

#### Period

- Start/End: 2026-07-20
- Related task: README/config cleanup patch and `v1.7.1` release

#### Signals And Finding

- One bounded Paseo release-verifier found and corrected a stale changelog claim before tagging.
- Independent Codex gates and the existing tag-triggered trusted-publishing workflow completed without repair.
- The existing one-agent handoff plus top-level verification remains sufficient for a patch release; no additional agent or workflow layer is needed.

#### Keep / Change / Remove

- Keep: bounded release handoff, explicit exclusion of generated learning state, and post-publish npm/provenance/CLI checks.
- Change: none.
- Remove: no additional release scaffolding.

### 2026-07-20 Harness Eval: v1.7.2 feature release

- The existing one-agent preparation plus Codex release gates caught a missing text-length guard before publication and kept the generated learning queue out of both commits.
- Current official npm/GitHub checks confirmed the existing OIDC workflow needed no edit; the tag-triggered release passed without repair.
- Keep the same bounded handoff and independent final verification. Do not add another release layer; report accuracy and scoped staging remain the useful controls.

### 2026-07-26 Harness Eval: v1.8.0 source preparation

#### Period

- Start/End: 2026-07-26
- Related task: GitHub Issue #18

#### Signals

Useful positive signals:

- Commit-pinned source-learning and current official docs prevented an unnecessary semantic-release migration or GitHub Actions upgrade.
- The explicit GLM override was honored even though Paseo's default implementation preference pointed elsewhere.
- The handoff's narrow file list made the quota-interrupted GLM diff easy to attribute and complete without overlapping runtime work.
- Independent package/release review confirmed version parity, unchanged dependency graph and entry points, and the 124-file publish boundary.
- The production audit gate caught four new advisories; explicit source-to-sink triage separated installed vulnerability metadata from current product exploitability.
- The SDK contract check caught a wrong harness expectation for tool order before it could be misreported as a product regression.

Useful negative signals:

- GLM's five-hour quota stopped the agent before README_EN, subagent reviews, verification, and the required Claude report.
- The npm CLI's response-decoding failure made a nominal one-command audit gate insufficient; the official advisory payload and reachability conclusion needed separate evidence.
- The release-preparation documentation layer is substantial for six bounded release-file edits, although most of the extra volume came from new security evidence and the provider failure.

#### Keep / Change / Remove

Keep:

- One bounded Paseo implementation agent, user-selected provider override, file-backed handoff, independent Codex verification, official SDK acceptance, package inspection, and explicit generated-learning exclusion.
- Current official documentation and commit-pinned source-learning before modifying a release mechanism.

Change:

- Treat a failed audit transport as an unresolved gate until the official advisory payload is recovered and triaged; never translate command failure into “zero vulnerabilities.”
- When a provider quota stops a bounded agent, retain the provider choice, preserve its logs, use a clearly named top-level same-scope fallback report, and do not fabricate a provider-authored report.
- Validate custom smoke-test expectations against existing contract tests before diagnosing product behavior.

Remove or stop using:

- Do not retry a quota-limited provider indefinitely or silently switch to another implementation model.

#### Candidate Metrics

- task-ticket uses: 1 GitHub Issue
- research notes created: 2
- QA checklists created: 1
- independent read-only reviews: 2
- production advisories caught before publication: 4
- codemap checks unchanged: 1
- provider failures requiring documented fallback: 1
- generated learning proposals promoted: 0

### 2026-08-06 Harness Eval: Official MCP Registry publication

- The official publisher's live authorization response caught a namespace
  casing assumption that local schema validation could not detect.
- Keep: isolated release worktree, one bounded package-maintainer handoff,
  official CLI validation, exact npm smoke, two independent reviews, and final
  public Registry API verification.
- Change: finish npm publication and metadata checks before Registry login,
  then publish immediately because the authentication token is short-lived.
- Remove: do not require `server.json` inside the npm tarball; the Registry
  publisher reads repository metadata while npm ownership validation uses the
  packed `package.json.mcpName`.

### 2026-08-05 Harness Eval: v1.11.1 publication

- The clean release worktree and exact fast-forward parent check kept the main
  dirty worktree out while proving the release commit extended, rather than
  overwrote, contributor PR #25.
- Paseo's bounded `package-maintainer` preparation plus independent
  `release-verifier` and `risk-reviewer` checks caught only two record-accuracy
  issues (new-file count and baseline U+FFFD wording); both were corrected
  before commit without expanding product scope.
- The existing tag-triggered OIDC workflow passed 803 tests, build, trusted npm
  publication, provenance, remote tag dereference, and isolated exact-version
  CLI checks. The repeated Node 20 action-runtime deprecation warning remains a
  separate workflow-maintenance concern, not a reason to modify an otherwise
  successful patch release.
- Keep: clean release worktrees for dirty repositories, direct PR-ancestor and
  remote-SHA checks before fast-forward push, tag-after-version sequencing,
  value-free secret classification, live npm provenance, and bilingual
  contributor credit. No additional release layer is needed.

#### Memory Updates Needed

- [x] `project-facts.md`
- [x] `decisions.md`
- [ ] `lessons-learned.md`
- [x] `handoff-log.md`
- [x] `verification-log.md`
- [ ] `codemap.md` — checked unchanged
- [ ] `harness-security.md` — checklist applied; no rule change required

### 2026-07-26 Harness Eval: Issue #19 dependency remediation

- The security gate prevented a misleading “zero vulnerabilities” claim and separated compatible lock refreshes from an unsafe Hono major override.
- Two read-only Codex reviewers converged on the same minimal fix before mutation; no new test or abstraction was needed.
- GLM produced no activity during bounded waits. After the user explicitly selected Codex, continuing directly avoided another artificial stop while preserving the provider decision in the report.
- Node 18 Vitest failed for a development-tool reason; switching to the official SDK runtime boundary proved the supported user path without weakening the check.
- Keep: ticket, bounded handoff, source-to-sink triage, package graph evidence, real stdio check, and explicit residual risk.
- Change: when the user supplies a fallback executor, continue through the same handoff rather than ending at the provider boundary. Require reports to enumerate the complete lockfile closure, and keep README release links on the latest real Release until publication creates the new one.
- Follow-up: Issue #20 records the pre-existing difference between the root Node `>=18.0.0` declaration and Hono's Node `>=18.14.1` floor.
- Delivery: explicit Git authorization produced separate #18/#19 commits, preserving the reviewer's scope boundary; publication remained a distinct authorization gate.

### 2026-07-26 Harness Eval: v1.8.0 publication

- The final release-verifier plus exact tag-SHA check kept two excluded dirty documents out of the immutable release.
- The unchanged tag-triggered OIDC workflow passed install, 299 tests, build, and npm publication; live registry provenance and exact-version CLI checks closed the external delivery loop.
- Keep tag, npm, Release, README-link, and project-memory updates as ordered gates. Do not pre-link a nonexistent Release or create the GitHub Release before npm publication succeeds.

### 2026-07-26 Harness Eval: v1.9.0 publication

- Direct Codex execution honored the user's explicit executor override while retaining the same ticket, file-backed contract, test, security, package, and release-verifier gates.
- Explicit staged-file enumeration kept the review-gated learning proposal out of the 30-file immutable release commit; the unchanged trusted-publishing workflow passed without repair.
- The post-publish CLI check initially produced a false alarm because same-repository `npm exec` resolved a global shim. Repeating it from an empty external directory and recording `where.exe` output distinguished harness contamination from a package defect before an unnecessary patch release.
- Keep: direct-executor overrides, tag-SHA checks, live npm provenance, delayed README links, and isolated published-package CLI checks. Change: require the CLI smoke to run outside the checkout. Remove: no additional release layer.

### 2026-07-26 Harness Eval: v1.9.1 publication

- One read-only release-verifier plus exact tag-SHA, package, production-audit, and secret gates was sufficient for this documentation-only patch.
- Current official npm/GitHub guidance confirmed the existing OIDC workflow remained valid; the tag-triggered run published with provenance without a workflow change.
- The isolated published-package smoke avoided same-repository binary contamination. Keep the current release sequence; track newly disclosed development-tool advisories separately instead of broadening a documentation release.

### 2026-07-27 Harness Eval: Issue #22 Favorites discovery

- The user's actual `GLM`/`DeepSeek` terminal functions were more authoritative than two possibly stale configuration skills. Resolving those functions prevented another incorrect model assumption. GLM was used first and DeepSeek only after a real five-hour quota response.
- The file-backed Issue #22 handoff kept the provider switch within one frozen scope and prevented note generation, RAG, persistence, or automatic subtitle work from entering the implementation.
- Claude's first review and report missed multiple correctness/privacy gaps and misstated the baseline test count. Independent Standards/Spec review plus failing-first Codex regressions caught filtered-page data loss, error-category drift, stale cursors, permissive/overflowing cursor encoding, Folder-title contract drift, debug identifier leakage, and false coverage claims.
- The initial account-backed smoke verifier could have produced a false green and was not a durable product artifact. Codex hardened it, reran the real SDK path, then removed it after recording only bounded aggregate evidence.
- Keep: one bounded implementation agent, explicit user-terminal provider semantics, GitHub Issue + handoff, redacted live SDK acceptance, independent two-axis review, and final package/privacy gates.
- Change: capability reports must distinguish what Claude actually invoked from what Codex later supplied; test baselines must come from HEAD, and temporary live verifiers must fail closed before their evidence is accepted.
- Remove: do not rely on provider configuration skills when the user says their terminal wrappers define reality; do not preserve account-backed smoke scripts after acceptance unless they are intentionally designed as maintained, privacy-safe tests.

### 2026-07-27 Harness Eval: v1.10.0 publication

- The independent read-only release verifier and explicit 38-file staging list kept the review-gated learning proposal out of the immutable release tag.
- Current official npm/GitHub OIDC checks confirmed the existing trusted-publishing workflow remained valid; the tag-triggered run passed 405 tests, build, publication, provenance, and isolated published-package CLI gates without repair.
- The bilingual README update shipped in the release commit, while the post-publication evidence remained a separate documentation commit.
- Keep: exact staged-scope checks, tag-SHA verification, live npm provenance, isolated CLI smoke, and post-publish Issue closure.
- Change: `actions/checkout@v4` and `actions/setup-node@v4` now emit a deprecated Node 20 action-runtime warning and were forced to Node 24. Refresh them in a separate bounded workflow-maintenance task; do not churn a successful immutable release.

### 2026-07-27 Harness Eval: v1.10.1 documentation patch

- One independent release verifier plus an explicit 11-file staged set was sufficient; the review-gated learning proposal stayed outside the commit and immutable tag.
- The unchanged tag-triggered workflow passed 405 tests, build, trusted publication, provenance, remote tag dereference, and isolated exact-package CLI gates without repair.
- Keep the current documentation-patch release sequence. The 360px Hero is an overview rather than a detail surface; adjacent Markdown and alt text preserve the complete workflow, so no extra mobile asset is justified unless users need the image itself to carry every label.

### 2026-07-27 Harness Eval: ASR installation Phases 1 and 2

- The two bounded phase contracts kept runtime installation, model choice, and future transcription separate; no audio or MCP fallback behavior entered the installer work.
- The first implementation reports repeatedly drifted from the stable tree: stale README claims, old test counts, unchecked criteria, and an inaccurate test name survived until independent review. Re-running review only after the writer became idle prevented transient TypeScript and test failures from being accepted as final defects.
- Keep: one Paseo implementation agent, pinned allowlists, fail-closed state tests, package/secret gates, and stable-tree independent review. Change: completion reports must be regenerated from the final command outputs and checked against task, PRD, QA, README, and project memory before claiming all findings are closed.
- The project subagent attempt was useful for test-baseline review, but the risk-reviewer stall did not justify waiting indefinitely; independent Codex review covered the same bounded scope without spawning an autonomous implementation tree.

### 2026-07-29 Harness Eval: ASR transcription fallback Phase 3

- The full-thread handoff, scored PRD, task ticket, source research, and QA matrix kept a cross-network/subprocess/filesystem/MCP change within one explicit default-off tool option and excluded model download, SDK migration, Git, and release work.
- The existing Paseo daemon was unavailable and could not be restarted without new authority. Direct Codex execution preserved the same file-backed contract; two unchanged Codex Security setup waits produced no submitted scan, so top-level bounded risk review supplied the required fallback without inventing an independent result.
- The final review materially improved safety: it distinguished malformed DASH from valid empty audio, narrowed CDN hosts, canceled redirect bodies, guarded temp paths and cleanup, rejected custom ports/unsafe backups, tightened NDJSON, and found historical test-temp residue that ordinary assertions missed.
- Keep: frozen phase artifacts, deterministic injection seams, exact focused/full/package/public-stdio gates, secret classification without printing values, and explicit live-model boundary. Change: after one repeated external setup failure, record capability unavailability and use the authorized local fallback instead of waiting again. Add temp-root before/after counts to future filesystem-heavy acceptance matrices.

### 2026-07-30 Harness Eval: 38-finding security remediation

- The original sealed Codex Security report supplied concrete source-to-sink
  findings instead of a generic checklist. Converting all 38 IDs into one
  ticket and one QA matrix prevented low-severity network, output, hook, and
  installer issues from disappearing behind the four Medium items.
- The user explicitly selected direct Codex execution. Keeping the same frozen
  ticket, test gates, project memory, and Git/release exclusions made that
  executor change safe; Paseo would have added delay without adding authority.
- Shared enforcement points materially reduced review surface: one limits
  module, operation-cancellation context, bounded response parser, bounded
  stdio transport, and pinned HTTPS sink close multiple findings and make
  boundary tests reusable.
- The Desktop scan setup gate timed out without submission and cannot be
  automated. The newly public official Codex Security CLI provided a
  non-UI, same-vendor full-worktree scan path using stored credentials. The
  first 0.1.3 run exposed a completion-order bug and produced no artifacts;
  package 0.1.4 corrects the order to prepare, collect/validate, then complete.
  Each CLI scan remains independent and must not be described as completing
  the earlier Desktop scan ID.
- The package and audit gates prevented two misleading conclusions. Compiled
  `credentials.*` modules are expected runtime code, not packaged credential
  files; conversely, the unreachable Hono sink still means the production
  audit is nonzero and must remain a named residual.
- Keep: original-scan ID binding, 38-row closure matrix, focused plus full
  tests, built wire-level stdio acceptance, value-free secret classification,
  pack inspection, and independent sealed re-scan before completion.
- Change: when the native scan UI requires a human confirmation, tell the user
  once and continue local work. If an official CLI is available and the user
  selects it, validate with dry-run, use a fresh empty artifact directory,
  place logs beside it, pin the intended CLI version, validate canonical
  artifacts before acceptance, and preserve the existing Desktop workspace.
- Remove: do not repeatedly reopen setup, create duplicate Desktop workspaces,
  or treat an unsubmitted workspace as a running scan.

Candidate metrics:

- validated findings remediated locally: 38
- Medium / Low: 4 / 34
- focused security tests: 407
- full tests: 721
- hook tests: 14
- package entries: 180
- product-source implementation agents: 0
- bounded Codex test/review subtasks: 3
- generated learning proposals promoted: 0

### 2026-08-11 Harness Eval: Harness v2 Issue #29 session spine

- The shared CLI and replay seam exposed host-shape mistakes without duplicating
  normalization logic. Independent Spec and Standards review caught two real
  cross-boundary defects that ordinary green tests missed: linked-worktree
  primary Codex Hook overlap and non-atomic one-shot manual reminders.
- Keep: one constitutional core, thin adapters, typed contract, worktree-scoped
  redacted ledger, real process-boundary fixtures, dirty-primary fingerprints,
  package exclusion, and risk-weighted independent review.
- Change: run `harness doctor` before any normal-config live client smoke. Use a
  user-config-disabled session only for clean rule discovery, and require a
  concurrent regression whenever runtime state promises one-shot behavior.
- Remove: do not use a normal client smoke as proof of isolation until external
  Hook layers are inventoried; do not implement read-check-write deduplication
  outside the existing ledger lock.
- Residual: the primary checkout's legacy Codex Hooks require an explicit later
  migration. Issue #29 reports the gate but correctly leaves external
  configuration untouched; the complete three-adapter pilot remains #36.

Candidate metrics:

- shared Harness tests: 26
- legacy Hook compatibility tests: 14
- product tests: 862
- package entries / forbidden Harness entries: 185 / 0
- independent final reviewers: 2
- accepted repair findings: 2
- product-source files changed: 0
- remote operations performed: 0

### 2026-08-11 Harness Eval: Harness v2 Issue #31 Claude Direct loop

- Parameterizing the accepted #30 controller was lower risk than copying its
  state machine. The first failing process test nevertheless exposed a hidden
  cross-adapter control seam: persisted mode alone is insufficient unless the
  invoked command is checked on every state transaction. A second red test
  found that unstable-start rollback used a different identity than the
  source-scoped manual-Skill marker.
- Keep: one Direct controller, adapter-specific run/control schemas and owners,
  command-mode fencing, source-bound writer exclusion, native manual-Skill
  gates, bounded repair/recovery, exact automatic commit, disposable Git tests,
  dirty-primary fingerprints, package exclusion, and a real host pilot.
- Change: a shared conformance fixture must drive both public adapter
  lifecycles, not merely compare static mappings. Real pilot reports must
  distinguish user-native Skill evidence from an empty pilot Skill requirement
  and record preflight failures rather than hiding them.
- Remove: do not add a copied Claude controller, do not let one adapter inspect
  another adapter's state, do not pass or persist a model/provider/fallback,
  and do not promote raw Claude stream output into formal memory.
- Residual: the primary legacy Codex Hook overlap remains the deliberate
  `doctor=action-required` migration gate. The real pilot used project settings
  only; normal-config rollout remains out of scope.

Candidate metrics:

- focused pre-review Harness tests: 34
- final shared Harness tests: 105 (1 platform-permission skip)
- legacy Hook compatibility tests: 14
- product tests: 862
- package entries / forbidden Harness entries: 185 / 0
- shared public lifecycle fixture adapters: 2
- real Claude CLI attempts / accepted runs: 2 / 1
- pre-start configuration failures / Recovery Bundles: 1 / 0
- pilot repairs / evidence-command corrections: 0 / 1
- routine approval prompts / user interventions: 0 / 0
- accepted pilot commits / changed paths / remotes: 1 / 1 / 0
- pilot elapsed / reported cost cap usage: 190.481s / USD 1.906883 of 2.00
- implementation-client handoffs / Paseo launches: 0 / 0
- final independent review axes: 3, all PASS with no remaining P0-P3
- accepted review repairs: 4 (report/evidence, executable conformance,
  subprocess environment, unified report contract)
- product-source files changed: 0
- remote operations performed: 0

### 2026-08-11 Harness Eval: Harness v2 Issue #30 Codex Direct loop

- The public process-boundary seam kept adapter behavior testable without
  launching another writer. Disposable repositories exposed state, Git, and
  authority effects directly; linked-worktree fixtures forced the writer state
  back under the frozen canonical worktree while a Windows named mutex/POSIX
  existing-config advisory lock makes the source-bound sibling-state scan
  atomic without a common-Git marker.
- Initial green behavior was insufficient. Two-axis review and focused red
  regressions found that raw contract persistence, unlocked state updates,
  caller-asserted command results, stale diff evidence, and trailer-only commit
  recovery could all produce false auditability or false acceptance.
- Keep: one frozen typed contract, fixed action classes, diff-bound typed
  evidence, current review gate, bounded fingerprint repair, metadata-only
  Recovery Bundle, exact automatic local commit, real Harness-only pilot,
  dirty-primary fingerprints, package exclusion, and independent final risk
  review.
- Change: future adapter loops should reuse the shared lock, metadata projection,
  frozen canonical/source-bound writer identity, append-only evidence/result
  fields, hermetic index plus `commit-tree`/CAS `update-ref`, state preflight
  limit, and accepted snapshot rather than rebuilding host-specific state. Run
  the cross-worktree alias/malformed-state, concurrent-index, late-filter,
  Hook/signing, crash-recovery, and maximum-state cases from the first red suite.
- Remove: do not persist a complete executable contract as runtime history, do
  not implement load-modify-save without one transaction lock, and do not treat
  a task trailer or model-reported pass as sufficient evidence.
- Residual: the primary legacy Codex Hook overlap remains a deliberate
  `doctor=action-required` migration gate. A normal-config client smoke remains
  skipped until that external configuration receives separate authority.

Candidate metrics:

- shared Harness tests: 92 (1 platform-permission skip)
- legacy Hook compatibility tests: 14
- product tests: 862
- package entries / forbidden Harness entries: 185 / 0
- real pilot repairs / user interventions / routine prompts: 0 / 0 / 0
- accepted pilot commits / remotes: 1 / 0
- implementation-client handoffs / handoff overhead: 0 / 0
- context cost: not measured
- final independent review axes: 2, both PASS with no P0-P2
- product-source files changed: 0
- remote operations performed: 0
