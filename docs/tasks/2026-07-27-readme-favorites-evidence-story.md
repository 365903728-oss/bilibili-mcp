# README Favorites-to-Evidence Story

- ID: `DOCS-README-2026-07-27`
- Status: `done`
- Owner: `Codex`
- Source: User-requested `beautify-github-readme` README mode

## Objective

Make both repository homepages explain, on the first screen, that an Agent can start from either a topic or every currently visible Video in the logged-in account's created Favorite Folders, then use the returned BVIDs for timestamped transcript evidence. After user review, keep the hero itself focused on the complete Favorites traversal.

## Scope

In scope:

- Restructure `README.md` and `README_EN.md` around value → proof → first use → detail.
- Refresh the two existing SVG heroes around one project-native motif: no-cursor start → bounded page → `next_cursor` continuation → completion.
- Keep the complete installation/configuration guides and detailed tool references as the canonical long-form sources.
- Record final README verification.
- After design approval, publish the documentation update as patch version `1.10.1` with bilingual changelogs and the existing tag-triggered workflow.

Out of scope:

- Runtime source, MCP schemas, tests, credentials, setup guides, tool references, dependencies, and release-workflow changes.
- New visual assets, animation, dependencies, screenshots, or generated marketing claims.

## Files To Inspect Or Edit

Expected edit:

- `README.md`
- `README_EN.md`
- `assets/readme/hero.svg`
- `assets/readme/hero-en.svg`
- this ticket
- `docs/agent-memory/verification-log.md`

Do not touch:

- `docs/agent-memory/pending-learning-proposals.md`
- runtime source, tests, `dist/`, credentials, setup guides, and tool references

## Acceptance Criteria

- [x] The first screen answers what the project is, what it does, and where to start.
- [x] Both heroes visibly represent no-cursor start → one Folder/page of at most 20 rows → `next_cursor` continuation → all currently visible titles and BVIDs.
- [x] Both READMEs state that an Agent follows `next_cursor` until it is absent to traverse all currently visible created Favorite Folders.
- [x] The real `BV1Eb411u7Fw` Part 4 → `?p=4&t=1.12` proof remains accurate and clickable.
- [x] All ten MCP tool names remain reachable without reproducing the detailed reference.
- [x] Chinese and English structure and claims remain equivalent.
- [x] Complete setup remains centralized in the bilingual client guides.
- [x] SVG, Markdown, links, UTF-8, package boundary, and 900px/360px previews pass.
- [x] No secret, Cookie value, private Favorite data, runtime behavior, or dependency is added.
- [x] `docs/agent-memory/codemap.md` is checked and left unchanged because module ownership and package layout do not change.

## Verification

```powershell
python C:\Users\ZX\.agents\skills\beautify-github-readme\scripts\audit_readme.py README.md
python C:\Users\ZX\.agents\skills\beautify-github-readme\scripts\audit_readme.py README_EN.md
npm pack --dry-run --json --ignore-scripts
git diff --check
```

Manual checks:

- Render both heroes at 900px and 360px.
- Validate local links and bilingual section parity.
- Inspect SVGs for scripts, `foreignObject`, remote resources, clipping, and contrast.

`npm run build` and `npm test` are intentionally not required because this task does not change runtime source, schemas, tests, or generated output.

## Stop And Report Conditions

Stop if the redesign would require changing public MCP behavior, duplicating the full setup/reference documents, introducing a new dependency, or touching the existing review-gated learning proposal.

## Completion Report

- Files changed: both READMEs, both existing hero SVGs, this task ticket, and the verification log.
- Verification: both Skill audits, 18 local links, bilingual heading parity, strict UTF-8, SVG XML/safety checks, 900px and 360px previews, no horizontal overflow, 138-file package dry run, high-confidence secret scan, and `git diff --check` passed.
- Skipped: build and Vitest because runtime source, schemas, tests, and generated output are unchanged.
- Capabilities: `beautify-github-readme`, `bilibili-mcp-memory`, and local Browser preview. A bounded read-only `final_diff_review` subagent did not return a report and was stopped; Codex completed the final diff review directly.
- Codemap: checked and unchanged.
- Git: the initial design pass made no Git change; the later user-authorized `v1.10.1` publication is tracked in `docs/qa/2026-07-27-v1.10.1-readme-release.md`.
