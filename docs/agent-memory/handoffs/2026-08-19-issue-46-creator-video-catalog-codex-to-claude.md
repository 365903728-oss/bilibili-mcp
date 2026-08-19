# Codex To Claude Handoff: Issue #46 Creator Video Catalog

## Update Goal

Implement only GitHub Issue #46 under parent specification #44: add the `overview` and `videos` sections of `get_bilibili_creator_content` so an Agent can inspect one selected numeric Creator `mid` and page through currently listable BVID metadata without automatic evidence crawling.

## Current Judgment

- Mode: `codex-paseo-claude`; Claude Code is the only writer after Harness bootstrap, Codex owns acceptance.
- Source base before this preparation commit: `fbfc13ee8b64af9b0529bcd43dd4112873311ef0` on `codex/issue-46-creator-video-catalog` in `C:\Users\ZX\.codex\worktrees\issue-46\bilibili-mcp`.
- The final frozen Harness base is the preparation commit containing this handoff and its research note; use the contract as runtime authority.
- The user invoked the Claude-host `/implement` bridge. No push, PR, tag, release, publish, credentials, SSH, daemon restart, or provider fallback is authorized.
- Anonymous official endpoint probes returned HTTP 412 and API `-352`; no Cookie was read or sent. Authenticated live smoke remains skipped without separate authority.

## Recommended Approach

Create one deep Creator Content module with one small public interface such as `getBilibiliCreatorContent(mid, section, cursor?)`. Reuse the existing credential/login, WBI HTTP, operation cancellation, bounded-response/text, resource-limit, validation, error, and structured-content modules. Reuse the Favorites cursor discipline, not its Folder payload or traversal semantics.

Public behavior:

- input: required positive-safe-integer `mid`; required section `overview` or `videos`; optional cursor only for `videos`
- cursor: canonical base64url JSON, versioned, maximum 256 characters, containing only the minimal Creator `mid`, section, and positive-safe-integer page; reject malformed, non-canonical, cross-Creator, cross-section, overview-with-cursor, and unsafe-next-page inputs before credentials/network
- `overview`: bounded Creator profile facts plus only upstream-provided section/count facts; no semantic summary and no catalog crawl
- `videos`: exactly one newest-first upstream page per call, `ps=20`, preserving row order; emit `next_cursor` only when continuation is proven
- each accepted row exposes BVID and bounded title, description, cover URL, category, duration, publication time, author, and only available engagement facts, plus conservative charge/access evidence
- access/entitlement defaults to `unknown`; listing visibility, charge markers, or a visible BVID alone never prove playback permission
- both sections explicitly identify live-state, non-snapshot semantics
- success returns equivalent JSON text and `structuredContent`; failures remain text-only through existing error handling

Use the established `/x/space/wbi/arc/search` Creator catalog path and `/x/space/wbi/acc/info` profile path through existing HTTP helpers. Do not add anonymous/webpage fallback. If the accepted ticket cannot be met without a new endpoint, public field, or product decision, stop and report rather than guess.

## Things To Avoid

- No generic discovery router, interface with one adapter, new dependency, cache/persistence layer, or speculative abstraction.
- No Collections/Series (#47), Dynamics (#48), courses, article/Opus bodies, native live/replay, OGV, comics, audio, OCR/vision, recommendations, or Creator scoring.
- No transcript, chapter, comment, image download, or per-row Video detail request.
- Do not edit generated `dist/`, package manifests, workflows, Harness code/config, Hooks, credential files, `.env`, or the dirty primary checkout.
- Do not commit, push, create a PR, or publish from Claude. Harness acceptance owns the final local implementation commit.

## Claude Code Execution Steps

1. Start natively with `/implement`; read Issue #46, parent #44, `RULES.md`, `CLAUDE.md`, `CONTEXT.md`, this handoff, and the research note.
2. Use `/tdd` and `/vitest` in vertical slices at the pre-agreed seams below. Use `/codebase-design` only as the vocabulary/reference for the Creator Content module seam.
3. Before each tracked file's first edit, run the Harness Claude-writer guard. Stop for owned-path expansion.
4. Add one failing integration-module test for pre-network validation/cursor binding, then the minimum implementation.
5. Add failing bounded overview and one-page Video normalization/request-count slices, then implement only enough to pass. Preserve explicit failures and skipped-row accounting.
6. Add one failing handler/schema structured-output slice, then register the twelfth tool without changing existing tool behavior.
7. Update only ticket-relevant bilingual README/tool reference, glossary, codemap, durable decision/active-work memory, and the named Claude report.
8. Run focused tests, build, full tests once, package dry-run, diff/scope checks, then `/code-review`. Repair only same-scope findings within the contract limit.
9. Return the uncommitted writer diff and file-backed report to Codex; do not perform Git remote operations.

Pre-agreed TDD seams:

1. `getBilibiliCreatorContent` through the mocked external Bilibili HTTP seam.
2. `handleToolCall("get_bilibili_creator_content", ...)` for pre-network validation and structured/text output.
3. MCP stdio `tools/list` / invalid `tools/call` through the existing smoke seam.

Do not test private helpers or mock inside the Creator Content module. The Bilibili HTTP module is the permitted mock adapter. The main Claude writer uses test capabilities directly; do not create a second editing subagent.

## Expected Files

The exact allowed list is frozen in `.harness/contracts/github-46.json`. It includes the new Creator Content module/test, shared types, server schema/handler, validation only if required, existing server/smoke/error tests, relevant bilingual docs/glossary, codemap/decision/active-work memory, research note, handoff, Claude report, and Harness execution report. Any other tracked path requires stop-and-report.

## Verification

```powershell
npm test -- --run tests/bilibili-creator-content.test.ts tests/server-handler-sanitization.test.ts tests/server-error-next-steps.test.ts tests/server-tools.test.ts tests/mcp-server-smoke.test.ts
npm run build
npm test
npm pack --dry-run --json
git diff --check
git status --short
```

`npm ci` is allowed only if dependencies are absent; it must not change dependency manifests.

## Acceptance Criteria

All eleven checkboxes in Issue #46 are binding. In addition:

- invalid input and locally detectable cursor misuse make zero credential/network calls
- a valid `videos` call makes no per-row request and no more than one catalog-page request after bounded authentication/WBI prerequisites
- overlong text/list payloads fail with existing resource-limit behavior; invalid identity/list rows are skipped conservatively with an explicit count
- tool schemas communicate safe integer/string/list bounds and the section-specific result contract
- all existing eleven tools remain compatible; the new tool is the twelfth
- actual diff, focused/full verification, `/code-review`, project risk review, and secret scan must be green before Harness acceptance

## Risks And Stop Conditions

- Stop for a new public contract decision, new dependency/endpoint, owned path, credential/live smoke, adapter/provider change, daemon restart, or repeated unchanged failure.
- Bilibili shape/risk-control drift is residual uncertainty; never translate HTTP 412, API `-352`, WBI, timeout, or malformed response into empty success.
- Writer report must enumerate files, red/green evidence, commands/results, every Issue #46 criterion, skipped live smoke, unresolved risk, and a `Harness Artifacts` section covering ticket, research, QA checklist, codemap, harness-security, and harness-eval.
- Rollback is the isolated branch and the Harness-owned final commit; do not reset, rebase, amend, or delete worktrees/stashes.
