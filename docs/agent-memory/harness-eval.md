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
