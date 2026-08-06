# Task Ticket: Official MCP Registry publication

## Ticket

- ID: `REGISTRY-001`
- Title: Prepare version 1.11.3 for the Official MCP Registry
- Status: `done`
- Owner: `Claude Code`
- Source: User request on 2026-08-06

## Objective

Prepare the smallest package-metadata release that lets `@xzxzzx/bilibili-mcp` pass Official MCP Registry npm ownership validation.

Fix the Registry namespace casing: the authenticated GitHub permission is exactly `io.github.XZXZZX-Ai/*` (case-sensitive), and the v1.11.2 publish attempt returned HTTP 403.

## Scope

In scope:

- Add the Registry `mcpName`.
- Add root `server.json` for the public npm stdio package.
- Correct `mcpName` and `server.json.name` casing to `io.github.XZXZZX-Ai/bilibili-mcp`.
- Bump package and lockfile versions to `1.11.3`.
- Add concise bilingual changelog entries.

Out of scope:

- MCP tool, ASR, credential, dependency, README, GitHub Actions, or runtime changes.
- Commit, push, tag, GitHub Release, npm publish, or Registry publish.

## Files To Inspect Or Edit

Expected edit:

- `package.json`
- `package-lock.json`
- `server.json`
- `CHANGELOG.md`
- `CHANGELOG_EN.md`

Do not touch:

- `src/`, `tests/`, `.github/workflows/`, README files, generated `dist/`, credentials, or unrelated memory files.

## Required Capabilities

- Claude Code subagent: `package-maintainer`
- CLI: npm, Node, `mcp-publisher`

## Acceptance Criteria

- [x] `package.json.mcpName` and `server.json.name` both equal `io.github.XZXZZX-Ai/bilibili-mcp`.
- [x] Package, lockfile, server metadata, and changelogs use `1.11.3` where applicable.
- [x] Live 403 evidence from the v1.11.2 publish attempt recorded in the research note.
- [x] `server.json` points to `@xzxzzx/bilibili-mcp` with stdio transport.
- [x] Public MCP tool behavior and dependencies are unchanged.
- [x] No secret, Cookie, token, or `.env` content is printed or committed.
- [x] Codemap is checked and left unchanged because module ownership does not change.

## Verification

```bash
npm ci
npm test
npm run build
npm pack --dry-run --json
```

Also validate `server.json` with the current official publisher CLI before release.

## Risks And Rollback

- Risk: namespace matching is case-sensitive; the v1.11.2 publish attempt returned 403 because the authenticated permission is exactly `io.github.XZXZZX-Ai/*`. Rollback: do not tag or publish until all local checks pass; discard this isolated branch if necessary.

## Stop And Report Conditions

- Stop if Registry requirements conflict with the official research note.
- Stop if runtime, dependency, workflow, credential, or broader documentation changes appear necessary.
- Do not perform Git or publishing actions.
