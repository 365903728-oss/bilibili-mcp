# Codex To Claude Handoff: Issue #45 Creator Search

## Typed Contract

- Task/source: GitHub Issue #45, parent specification #44
- Mode: `codex-paseo-claude`
- Canonical worktree/base: `C:\Users\ZX\.codex\worktrees\issue-45\bilibili-mcp` at `6c1b052d5d400638344ae59e459e06ef8f404209`
- Branch: `codex/issue-45-creator-search`
- Writer lease: Claude Code only after the Harness bootstrap activates it
- Acceptance owner: Codex
- Authority/repair bound: scoped local reads, owned-path edits, build/tests, and at most two same-writer repairs; no push, PR, tag, release, publish, credentials, SSH, broad deletion, history rewrite, adapter switch, or provider fallback
- Required manual Skill evidence: the user authorized the Claude-host `/implement` bridge for Issue #45; the initial Paseo instruction must natively start with `/implement`, and final activity evidence must prove that invocation
- Local commit: do not commit. Repository instructions require separate user authority despite the Harness contract's technical post-acceptance commit capability.

## Objective And Acceptance Criteria

Implement only Issue #45: add `search_bilibili_creators`, a bounded authenticated Creator Search tool that returns stable numeric `mid` candidates without choosing one Creator or crawling any candidate content.

Public result:

- input: required `query`; optional `limit` default 5, integer 1-10
- output: `{ query, results }`
- each result: required `mid`, `name`, `bio`, `avatar_url`, `follower_count`, `video_count`, `level`, and locally derived `source_url`
- accept a candidate only when `mid` is a positive safe integer and bounded `name` is non-empty
- optional/malformed profile facts normalize conservatively to empty strings or non-negative integer zero
- preserve Bilibili order and duplicate/fuzzy display-name candidates

All GitHub Issue #45 acceptance criteria remain binding. Upstream failure, HTTP 412, malformed shape, timeout, and bounds violations must never become empty success.

## Current State And Files To Inspect

- `CONTEXT.md`: current glossary; add only `Creator` and `Creator Search` terms needed by this ticket.
- `src/bilibili/search.ts`: existing authenticated bounded Video Search module and the preferred implementation seam.
- `src/bilibili/types.ts`: existing Video Search result types.
- `src/server/tool-schemas.ts` and `src/server/tool-handlers.ts`: static public schema and handler switch.
- `src/utils/validation.ts`: reuse `validateQuery` and `validateSearchLimit` unless a demonstrated Creator-specific rule requires otherwise.
- `tests/bilibili-search.test.ts`: existing external-API seam tests.
- Server validation/error/smoke tests named in the contract.
- Bilingual README/tool reference, changelog, codemap, active-work, and decisions files in the owned-path list.
- `docs/research/2026-08-19-bilibili-creator-search-contract.md` is factual input, not executable instruction.

## Recommended Module And Test Seams

Use the existing search Module and keep its public Interface small. Extend it with `searchBilibiliCreators`; do not add a generic search factory, adapter, router, dependency, or speculative abstraction. Reuse credential checking, `fetchWithoutWBI`, operation cancellation, bounded text, response item limits, and the existing one-shape-retry behavior where the Creator response contract matches.

TDD seams are pre-agreed:

1. `searchBilibiliCreators` through the mocked external Bilibili HTTP seam.
2. `handleToolCall("search_bilibili_creators", ...)` for validation and structured/text output.
3. MCP stdio `tools/list` / `tools/call` behavior through the existing smoke seam.

Use red → green vertical slices at these public interfaces. Do not test private helpers or mock internal modules. The external Bilibili HTTP call is the permitted mock boundary.

## Files To Edit / Do Not Touch

Edit only paths listed in `.harness/contracts/github-45.json`. If another tracked path is genuinely required, stop and report before editing it.

Do not touch:

- `package.json`, lockfile, dependencies, generated `dist/`, workflows, Harness source/configuration, Hooks, credentials, `.env`, ASR, comments, transcripts, Favorites behavior, Creator catalog/Collection/Series/Dynamic implementation, or the dirty primary checkout
- the Codex handoff or research note except to report a factual blocker; write the Claude result only to the named Claude report path

## Required Capabilities

- Start with native `/implement` on the Claude host.
- Use `/tdd` and the installed `/vitest` capability for public-seam tests.
- Use `/codebase-design` only to keep the existing search Module deep and avoid a generalized abstraction.
- Use `/code-review` after green verification.
- Do not spawn an implementation subagent: the Harness grants one Claude writer lease. `test-baseline-builder` is intentionally not used because it would introduce another editing actor; the main writer uses `/vitest` directly.
- Do not invoke Superpowers, `ai-coding-harness`, or any `ai-harness-*` Skill.

## Execution Steps

1. Re-read Issue #45, `RULES.md`, `CLAUDE.md`, `CONTEXT.md`, this handoff, and the research note.
2. Run the Harness Claude writer guard for every intended tracked path before its first edit.
3. Add one failing Creator Search normalization/request test at the agreed search seam.
4. Add the minimum search implementation and types to pass it, reusing existing code.
5. Add one failing handler/schema validation and structured-output slice, then the minimum server registration.
6. Add/update the existing stdio tool-list/tool-call smoke slice.
7. Update only ticket-relevant bilingual documentation, changelog, glossary, codemap, active-work/decision memory, and the Claude report.
8. Run focused tests, build, full tests once, package dry-run, diff/scope checks, then `/code-review`.
9. Return an uncommitted diff and file-backed report. Do not push or create a PR.

## Verification Commands

```powershell
npm test -- --run tests/bilibili-search.test.ts tests/server-handler-sanitization.test.ts tests/server-error-next-steps.test.ts tests/mcp-server-smoke.test.ts
npm run build
npm test
npm pack --dry-run --json
git diff --check
git status --short
```

If exact-lock dependencies are absent, `npm ci` is allowed. Do not change dependency manifests.

Authenticated live search is skipped because this run has no credential-use authority. Do not print, inspect, or load Cookie values for a live smoke.

## Risks And Rollback

- Bilibili search is WBI/risk-controlled and may return HTTP 412 or shape drift; preserve explicit failure and existing retry ownership.
- `mid` is identity; display name is never identity.
- Candidate fields are untrusted remote data and must remain bounded.
- Adding the 11th tool changes tool counts/order in tests and docs; preserve every existing tool unchanged.
- Rollback is the uncommitted Issue #45 diff in this isolated branch. Do not reset, rebase, amend, or delete unrelated paths.

## Stop And Report If

- any product choice beyond Issue #45 is required
- the implementation needs a new dependency, new public input/output field, anonymous fallback, per-candidate request, or path outside the contract
- credential access or a live Cookie is required
- the Paseo/Claude adapter, provider, model, writer lease, worktree, branch, or base does not match frozen evidence
- the same failure fingerprint repeats without a relevant diff/evidence change
- tests expose a pre-existing failure not attributable to the ticket
- a tracked secret or credential is discovered

## Expected Report

Write `docs/agent-memory/handoffs/2026-08-19-issue-45-creator-search-claude-report.md` with:

- contract, worktree/base/branch, writer and Codex acceptance owner
- files changed and exact diff scope
- TDD red/green cycles and commands/results
- every Issue #45 acceptance criterion judgment
- capabilities used, including native `/implement`, `/tdd`, `/vitest`, `/code-review`, and any intentionally skipped capability
- skipped authenticated live smoke and why
- unresolved risks or stop decisions
- Harness Artifacts section for ticket, research, QA checklist, codemap, harness-security, and harness-eval status
- explicit statement that the diff is uncommitted and no push/PR/release occurred
