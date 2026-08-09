# Task Ticket: Contract Correctness Hardening

## Ticket

- ID: `CONTRACT-2026-08-08`
- Title: Harden comments, language, credential, numeric-config, and JSON `-403` contracts
- Status: `done`
- Owner: `Codex`
- Source: User-authorized implementation task on 2026-08-08, with Git delivery authorized on 2026-08-09

## Objective

Make five bounded correctness fixes on live `master` without changing the ten-tool product boundary: define comment `limit` as a bounded main-comment count, preserve explicit `ai-zh`, reject blank credential replacement, strictly validate numeric environment configuration, and classify plain JSON `-403` by endpoint semantics.

## Scope

In scope:

- Comments schema, bilingual tool-reference wording, and focused pagination/reply tests.
- Shared supported-language validation and handler-level `ai-zh` preservation tests.
- CLI credential configuration with synthetic temporary-user tests.
- Strict positive safe-integer parsing for every current user-facing numeric environment variable, without inventing unsupported upper bounds.
- Plain JSON business-code `-403` mapping for non-video endpoints, with synthetic endpoint tests.
- Focused red/green evidence, full build/test/pack/audit/stdio verification, and a public-flow QA record.

Out of scope:

- New MCP tools, dependency upgrades, lockfile changes, live credential use, ASR changes, protocol modernization, release workflow changes, tags, npm/MCP Registry publication, GitHub Releases, and deployment.
- Direct edits or history rewrites in the pre-existing dirty main worktree.

Delivery extension:

- On 2026-08-09 the user explicitly authorized creating the isolated branch, committing, pushing, opening a PR, and merging it after green checks.
- Version bumping and publication remain separate decisions; this ticket keeps package version `1.11.3`.

## Files To Inspect Or Edit

Expected edit areas:

- `src/server/tool-schemas.ts`, `docs/tool-reference.md`, `docs/tool-reference.en.md`, and comments/schema tests.
- `src/config.ts`, language validation/selection call sites when required, and handler/config tests.
- `src/cli.ts`, `src/bilibili/http.ts`, and focused CLI/HTTP tests.
- `docs/qa/2026-08-08-contract-correctness-hardening.md`.

Do not touch:

- `package-lock.json`, dependency declarations, generated `dist/`, workflows, release metadata, the original worktree, or the da51 review worktree.

## Required Capabilities

- Skills: `tdd`, `vitest`, `secret-scanning`, `code-review`, `bilibili-mcp-memory`.
- Subagents: up to three bounded Codex workers with mutually exclusive file ownership; final `risk-reviewer` coverage before acceptance.
- CLI: `git`, `rg`, `npm`, `node`, `tsc`, and existing Vitest/MCP smoke tests.

## Acceptance Criteria

- [x] `get_video_comments.limit` is an integer from 1 through 50 and is documented as the main-comment count; child replies may expand the flat result.
- [x] `preferred_lang: "ai-zh"` reaches both video-info and transcript selection unchanged; unsupported languages fail explicitly.
- [x] Any trimmed-empty credential field leaves an existing synthetic credential file unchanged and does not report success.
- [x] All current user-facing numeric environment variables reject empty, partial, non-numeric, zero, negative, and unsafe-integer values with actionable secret-free errors.
- [x] HTTP 200 JSON `code: -403` from nav/Favorites-like non-video endpoints is not reported as `PAID_VIDEO`; HTTP status 403 behavior is preserved.
- [x] Focused tests demonstrate red before implementation and green after implementation.
- [x] `npm test`, `npm run build`, the existing real stdio smoke, `npm pack --dry-run --json`, and `npm audit --omit=dev` are run and reported.
- [x] `package-lock.json` and the tracked diff fingerprints of the original and da51 worktrees remain unchanged.
- [x] Public MCP tool names and successful response shapes remain stable except for the explicitly tightened comments schema.
- [x] No credential, Cookie, token, `.env` content, or private value is printed or committed.
- [x] `docs/agent-memory/codemap.md` is checked and updated for the new environment bootstrap and config-test navigation.

## Risks And Rollback

- Risk: rejecting values that were previously silently coerced can expose startup errors. Mitigation: validate only documented numeric variables and provide variable-specific guidance.
- Risk: changing the generic `-403` branch can lose paid-video specificity. Mitigation: keep paid mapping only at endpoints whose semantics establish it and preserve HTTP-status handling.
- Rollback: before merge, abandon only the isolated branch; after merge, use a normal revert PR. The pre-existing dirty main worktree remains untouched.

## Stop And Report Conditions

Stop and report if the fix requires a new dependency, lockfile mutation, a new public tool/response shape beyond this ticket, a real credential, a live write beyond the explicitly authorized Git branch/PR delivery, or a broader architecture change.
