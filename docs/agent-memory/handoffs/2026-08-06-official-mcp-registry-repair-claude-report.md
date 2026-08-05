# Claude To Codex Report: Official MCP Registry repair (REGISTRY-001, v1.11.3)

## Summary

Same-scope repair of `REGISTRY-001` after the live Official Registry publish attempt returned HTTP 403. Root cause: the authenticated GitHub permission is exactly `io.github.XZXZZX-Ai/*` and namespace matching is **case-sensitive**, while the prepared `1.11.2` metadata used lowercase `io.github.xzxzzx-ai/bilibili-mcp`.

Prepared metadata-only `1.11.3` with the corrected namespace `io.github.XZXZZX-Ai/bilibili-mcp` across `package.json`, `package-lock.json`, `server.json`, and both changelogs; recorded the live 403 evidence in the task ticket and research note. No runtime, dependency, workflow, credential, or Git action performed.

## Files Changed

- `package.json` — `version` → `1.11.3`; `mcpName` → `io.github.XZXZZX-Ai/bilibili-mcp`. Nothing else.
- `package-lock.json` — root package version → `1.11.3` in exactly two places (top-level `version`, `packages[""].version`); `lockfileVersion` and all dependency versions untouched.
- `server.json` — `name` → `io.github.XZXZZX-Ai/bilibili-mcp`; top-level `version` and package-entry `version` → `1.11.3`. Nothing else.
- `CHANGELOG.md` — `[1.11.3] - 2026-08-06` entry (修复/验证) above `[1.11.2]`, documenting the namespace casing fix and the 403.
- `CHANGELOG_EN.md` — matching `[1.11.3]` entry (Fixed/Verified).
- `docs/agent-memory/handoffs/2026-08-06-official-mcp-registry-task-ticket.md` — Title → v1.11.3; Status → `in_progress` (was `done` after the 1.11.2 prep; reverted because the publish was rejected); Objective, Scope, Acceptance Criteria (corrected namespace, `1.11.3`, new 403-evidence criterion), and Risk/Rollback updated with the live evidence.
- `docs/research/2026-08-06-official-mcp-registry-publishing.md` — Context appended with the live 403 evidence; Findings corrected (GitHub auth permits `io.github.XZXZZX-Ai/bilibili-mcp` only, case-sensitive; `1.11.1`/`1.11.2` immutable and lowercase rejected → `1.11.3` required); Applicability, Decision impact, Follow-up updated to `1.11.3`.
- `docs/agent-memory/handoffs/2026-08-06-official-mcp-registry-repair-claude-report.md` — this report (separate from the v1.11.2 prep report, which remains as historical record).

Diff: 7 files modified, +44/−19 (plus this new report). Historical `1.11.1`/`1.11.2`/lowercase strings remain only in changelog history and the fix description itself (intentional).

## Commands Run

```bash
npm test
npm run build
npm pack --dry-run --json
git diff --check
grep -rn "io\.github\.xzxzzx-ai\|1\.11\.2\|1\.11\.1" package.json package-lock.json server.json
```

(`npm ci` not run — no dependency changes; node_modules already installed from the prior run.)

## Results

| Command | Result |
|---|---|
| `npm test` | exit 0 — 39 files / 803 tests passed (vitest 4.1.8) |
| `npm run build` | exit 0 — clean `dist`, TypeScript compilation passed |
| `npm pack --dry-run --json` | exit 0 — name `@xzxzzx/bilibili-mcp`, version `1.11.3`, 181 files, 1,706,251 bytes |
| Tarball content check (real tarball in temp dir, then deleted) | packed `package.json`: version `1.11.3`, `mcpName: io.github.XZXZZX-Ai/bilibili-mcp`; zero packed files containing `1.11.2`/`1.11.1`/`io.github.xzxzzx-ai` |
| `git diff --check` | clean |
| Remnant grep | zero matches in `package.json` / `package-lock.json` / `server.json` |

Independent re-verification by coordinator: read all five metadata files post-edit (versions, `mcpName`, `server.json` name), confirmed diff scope, ticket title/status/criteria/risk lines, research-note 403 evidence, and repo root free of stray tarballs.

## Diff Notes

All changes are metadata-only and confined to the eight files listed. No changes to `src/`, `tests/`, `.github/`, README files, `dist/`, credentials, or other memory files. One transient artifact (`xzxzzx-bilibili-mcp-1.11.3.tgz` left by an MSYS `/tmp` pack fallback) was detected and removed; repo root verified clean.

## Risks Or Skipped Checks

- **`server.json` not in the npm tarball** — unchanged from v1.11.2 prep and by design: the Registry reads `server.json` from the repository via `mcp-publisher`; npm-side ownership validation uses `mcpName` inside the packed `package.json` (verified present with corrected casing). If Registry validation at release time requires tarball inclusion, add `"server.json"` to `package.json` `files` (one line).
- **`mcp-publisher` CLI validation and Registry publish deferred to the release step** — requires download and GitHub device auth; explicitly out of scope for this prep run. The namespace lesson (case-sensitivity) is now recorded in the research note for the release step.
- **No Git actions** — no commit, push, tag, release, publish, or authentication performed.

## Harness Artifacts

- Task ticket: used and updated — `REGISTRY-001` status back to `in_progress`, title/criteria/risk updated with the 403 evidence.
- Research note: used and updated — `docs/research/2026-08-06-official-mcp-registry-publishing.md` now records the live 403 and the case-sensitivity finding; no new note created.
- QA checklist: not required — metadata-only repair; no install path, MCP stdio startup, tool discovery, public tool schema/response, credential setup, or README install guidance change. Tarball shape verified via `npm pack` dry-run and tarball inspection.
- Codemap: checked unchanged — module ownership and code navigation unchanged.
- Harness security: not applicable — no harness-surface change (`AGENTS.md`, `CLAUDE.md`, `.claude/`, `.codex/`, hooks, skills).
- Harness eval: deferred — belongs after the actual `1.11.3` publication, per cadence in `docs/agent-memory/harness-eval.md`.

## Decision Points

1. **Namespace casing is case-sensitive** — corrected to `io.github.XZXZZX-Ai/bilibili-mcp` everywhere (matches the granted permission `io.github.XZXZZX-Ai/*` exactly). Recorded in the research note so future releases do not regress to lowercase.
2. **npm `1.11.2` is immutable** — it stays on the registry with the lowercase `mcpName`; no retraction possible or needed (the 403 means no Registry metadata was published for it). `1.11.3` supersedes it for Registry validation.
3. **Ticket status** — set back to `in_progress` (was marked `done` after the 1.11.2 prep; the 403 means the task is not complete).

## Suggested Codex Review Focus

- Confirm no lowercase `io.github.xzxzzx-ai` or `1.11.2` remnants in `package.json`, `package-lock.json`, `server.json` (verified zero; changelog history and fix-description mentions are intentional).
- Confirm the ticket title/status/criteria and the research note's 403 evidence read correctly.
- At release time: publish npm `1.11.3`, then run `mcp-publisher` with the corrected namespace; add `"server.json"` to `package.json` `files` only if Registry validation requires tarball inclusion.

Subagent used: `package-maintainer` (resumed same-scope from the v1.11.2 run; no other skill or agent tree invoked).
