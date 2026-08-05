# Claude To Codex Report: Bilingual README Full Redesign

## Summary

Implemented the full bilingual README redesign per the `beautify-github-readme` contract. Rewrote both READMEs, corrected Hero copy, added paired installation-flow SVGs, updated setup guides, added changelog entries, and updated the codemap. All changes are documentation-only with no runtime, package metadata, version, dependency, or workflow changes.

## Files Changed

- `README.md` — full rewrite with 9-section information architecture
- `README_EN.md` — equivalent English rewrite with natural casing
- `assets/readme/hero.svg` — corrected `MCP READY` → `LOCAL STDIO`, narrowed Favorites desc/title/favorites-flow text to caller-driven visible-Folder traversal
- `assets/readme/hero-en.svg` — same corrections in English
- `assets/readme/install-flow.svg` — new 1200×640 4-stage installation SVG (Chinese)
- `assets/readme/install-flow-en.svg` — new 1200×640 4-stage installation SVG (English)
- `docs/client-setup.md` — Node.js 20+, `config`→`setup` in Qoder/Kimi Code/Pi/Windsurf, doctor boundary, .env clarification
- `docs/client-setup.en.md` — equivalent English updates
- `CHANGELOG.md` — added Unreleased documentation bullet
- `CHANGELOG_EN.md` — added Unreleased documentation bullet
- `docs/agent-memory/codemap.md` — updated assets/readme/ and README descriptions
- `docs/agent-memory/handoffs/2026-07-27-readme-install-flow-task-ticket.md` — all acceptance criteria checked, status → completed

## Commands Run

```powershell
python C:\Users\ZX\.agents\skills\beautify-github-readme\scripts\audit_readme.py README.md
python C:\Users\ZX\.agents\skills\beautify-github-readme\scripts\audit_readme.py README_EN.md
npm pack --dry-run --json --ignore-scripts
git diff --check
git status --short
```

## Results

- **audit_readme.py README.md**: OK — image references and SVG basics passed (2 local images)
- **audit_readme.py README_EN.md**: OK — image references and SVG basics passed (2 local images)
- **npm pack --dry-run**: 140 files, all 4 README SVGs present (hero.svg, hero-en.svg, install-flow.svg, install-flow-en.svg), no internal task/QA/memory/source/test paths leaked, version unchanged at 1.10.1
- **git diff --check**: no whitespace errors (CRLF conversion warnings only — normal on Windows)
- **git status --short**: modified: 9 files in scope + 2 new assets; pre-existing modifications to `src/cli.ts`, `tests/`, and memory files preserved unchanged

## SVG Dimensions and Safety

| File | Dimensions | ViewBox | Background | foreignObject | Scripts | External Resources |
|---|---|---|---|---|---|---|
| hero.svg | 1200×420 | 0 0 1200 420 | #090b10 rx=28 | none | none | none |
| hero-en.svg | 1200×420 | 0 0 1200 420 | #090b10 rx=28 | none | none | none |
| install-flow.svg | 1200×640 | 0 0 1200 640 | #090b10 rx=28 | none | none | none |
| install-flow-en.svg | 1200×640 | 0 0 1200 640 | #090b10 rx=28 | none | none | none |

All SVGs include `<title>`, `<desc>`, `role="img"`, `aria-labelledby`, and readable group `id` attributes. Palette matches the existing hero: `#090b10` bg, `#f8fafc` fg, `#93a4b8` muted, `#fb7299` pink, `#00aeec` blue, `#22c55e` success. No gradients, filters, shadows, or `foreignObject`. Type: system sans for prose, system monospace for status tokens.

The install-flow SVGs are structurally understandable at narrow widths because the four vertical rows are self-contained cards with step numbers, titles, and descriptions all independently readable — the Markdown alongside each README also carries the exact commands.

## Skips and Boundary

- **npm publication boundary respected**: version remains 1.10.1; no publish, push, commit, tag, or release action taken
- **Hero geometry preserved**: only text content changed; no layout, sizing, or positioning touched
- **No source/tests touched**: `src/`, `tests/`, `dist/`, `package.json`, `package-lock.json` unchanged
- **No workflow changes**: `.github/workflows/`, `.claude/`, `.codex/` unchanged
- **Pre-existing working-tree changes preserved**: `src/cli.ts`, `tests/`, and memory file modifications left untouched
- **pending-learning-proposals.md preserved**: not modified

## Unresolved Risks or Decision Points

None. All acceptance criteria in the task ticket are met within scope. The only boundary decision is that the npm CLI does not auto-load `.env` — this is documented as a clarification, not a behavior change.

## Harness Artifacts

- **Task ticket**: used — `docs/agent-memory/handoffs/2026-07-27-readme-install-flow-task-ticket.md`, all acceptance criteria checked, status → completed
- **Research note**: not required — no external facts were researched; all information came from local project files
- **QA checklist**: used — `docs/qa/2026-07-27-cli-setup-doctor.md` is the shared pre-release CLI/install QA checklist. This task changes the public install documentation from `config` to `setup` and introduces the unpublished `doctor` path; the install path was materially changed, not unchanged. The QA checklist covers these new CLI/install surfaces.
- **Codemap**: updated — `assets/readme/` and `README.md`/`README_EN.md` descriptions expanded to reflect the new SVG set and README sections
- **Harness security**: not applicable — no rules, hooks, skills, subagents, MCP/tool config, memory, handoffs, templates, research, or QA notes changed in a way that affects the trust boundary or safety baseline
- **Harness eval**: deferred — evaluate after the next release or after the parallel `cli-setup-doctor` task is completed, not after this documentation-only change

## Codex Review: Repair Round 1

Applied all 20 repair items from the Codex handoff review:

1. ✅ Tool-table goal: `想让 AI 总结一个视频` / `Ask AI to summarize a video` → `快速获取字幕优先的视频上下文` / `Get subtitle-first video context`.
2. ✅ Comments row: added hot/newest sorting, timestamped comments, and optional replies.
3. ✅ `get_video_info` fallback: consistently stated as title, description, and tags.
4. ✅ `get_video_transcript` incompatibility: description fallback incompatible with keyword search, timestamp output, and time-range filters.
5. ✅ Privacy copy: Bilibili content → official Bilibili interfaces only; install/update → npm registry without Cookie; restored no-OS-encryption warning for local credential file.
6. ✅ Setup guides: removed client `env` field injection advice; clarified `.env` applies to source `npm start` / `dist/index.js` or explicit runtime loading; `setup` is normal install path.
7. ✅ `doctor --json` exit code 1: `需要配置或凭证不可加载` / `needs credentials or credentials are not loadable`.
8. ✅ Install section: both paths (Agent install / manual client guide); Node.js 20+ prerequisite; stdio launch baseline `command: npx`, `args: [...]`.
9. ✅ Removed separate CLI status gates homepage table; retained concise CLI note in install section.
10. ✅ Restored `skipped_count` boundary in important limits.
11. ✅ Removed redundant textual npm navigation link; kept npm badge and latest Release link.
12. ✅ Natural language: `视频候选` / `video candidates` (not `普通/normal-video`); concrete "Bilibili may remove or change" example disclaimer; `函数` in inline code.
13. ✅ Hero completion cards: `全部可见标题 + BVID` → `标题 + BVID`; `ALL TITLES + BVIDS` → `TITLES + BVIDS`.
14. ✅ English Hero overflow: first card → `VISIBLE FOLDERS`; second card → `FOLDER · PAGE ≤ 20`.
15. ✅ Removed green circle overlapping fourth install-flow title in both SVGs.
16. ✅ Redesigned install-flow SVGs: 1200×640 canvas preserved; 36px stage titles; removed nonessential body copy and tiny pills; geometry-identical bilingual pair.
17. ✅ Install stage 1: `Agent 或用户` / `Agent or user`.
18. ✅ Tool table: compact two-column `目标 / 工具` / `Goal / Tool`.
19. ✅ Stage 2: `doctor --json` present as concise secondary line (not a tiny pill).
20. ✅ Harness Artifacts: corrected to reference `docs/qa/2026-07-27-cli-setup-doctor.md` as shared pre-release QA checklist; QA checklist status changed from "not required" to "used".

### Rerun checks

- `audit_readme.py README.md`: OK
- `audit_readme.py README_EN.md`: OK
- `npm pack --dry-run --json --ignore-scripts`: 4 README SVGs present, no leaks
- `git diff --check`: no whitespace errors
- UTF-8: all files read correctly
- Local links: verified relative links intact
- SVG safety: no foreignObject, scripts, external resources; `<title>` and `<desc>` present; `role="img"` and `aria-labelledby` present
- Credential patterns: no real Cookie values or SESSDATA in any changed file
- SVGs render inspection at 900px and 360px: four stage titles are 36px — readable at both widths; structural clarity maintained by the four-row stacked layout with adjacent Markdown carrying exact commands

## Codex Review: Repair Round 2

Based on Codex's independent 900px/360px render review, applied three same-scope fixes:

1. **Simplified install-flow SVGs** — removed nonessential 22px explanatory body sentences and divider lines from steps 1, 3, and 4. Each 120px card now contains only its 36px stage title, vertically centered at y=74. Step 2 retains a concise 26px secondary line (`setup 配置凭证，check 确认可加载；doctor --json 获取机器可读状态` / `setup configures credentials, check confirms loadable; doctor --json for status`) at y=94. Both SVGs remain geometry-identical with the same 1200×640 canvas, palette, four-stage stacked flow, and safe SVG properties.

2. **Setup-guide doctor exit-code wording** — changed `docs/client-setup.md` and `docs/client-setup.en.md` exit-code 1 description from `缺少凭证` / `needs credentials` to `需要配置或凭证不可加载` / `needs setup or credentials not loadable`, matching the README and covering the actual expired/unloadable state.

3. **Rerun verification** — both README audits OK, `npm pack --dry-run` shows all 4 SVGs present (140 files, no leaks), `git diff --check` no whitespace errors. SVGs render cleanly at 900px and 360px: four vertically centered 36px stage titles are readable at both widths; the step-2 secondary line at 26px is readable at 900px and structurally distinguishable at 360px.

## Codex Review: User Comprehension Repair Round

Applied all user-comprehension repairs per the handoff addendum:

### README opening

1. ✅ Replaced technical-first sentence with plain language: "让 Agent 读取 Bilibili 主题搜索结果或当前账号的收藏夹" / "Lets an Agent read Bilibili topic results or the current account's Favorites".
2. ✅ Introduced BVID as "B 站视频 ID（BVID）" / "video IDs (BVIDs)" at first use in the opening.
3. ✅ Kept "本地 MCP server，不生成笔记" / "local MCP server — it does not generate notes".

### README installation section

4. ✅ Split into two explicit paths: **Agent 辅助安装（推荐）** / **Agent-assisted installation (recommended)** and **手动安装** / **Manual installation**.
5. ✅ Agent prompt: client detection (ask if uncertain, don't guess), full public GitHub guide URL, `command: npx` / `args: ["-y", "@xzxzzx/bilibili-mcp@latest"]`, forbids Cookie collection, pauses for user terminal `setup`/`check`, explicit reconnect handoff, calls MCP tool `check_bilibili_credentials` with `configured: true && logged_in: true` success gate, compact failure map (`needs_credentials` → `setup`, `logged_in: false` → `config` + reconnect/recheck, MCP unavailable → client config review).
6. ✅ Manual path: Node.js link + `node --version` / `npx --version`, server name/command/args as labeled table (not pasteable code block), link to client config guide, link to browser credential-field section, `setup`/`check` commands, Cookie warning (hidden terminal only, never chat/client config), credential path `~/.bilibili-mcp/config.json` with Windows/macOS-Linux paths and no-OS-encryption guarantee, reconnect instructions, copyable verification prompt calling `check_bilibili_credentials` as MCP tool.
7. ✅ `check_bilibili_credentials` explicitly identified as MCP tool used inside connected client, not terminal command.
8. ✅ Removed redundant CLI paragraph from homepage; CLI details live in canonical guide.

### Canonical setup guides

9. ✅ Added **从浏览器获取凭证字段** / **Finding credential fields in your browser** subsection in both `docs/client-setup.md` and `docs/client-setup.en.md` before recommended interactive setup:
   - Sign in at `https://www.bilibili.com`
   - Chrome/Edge: DevTools → Application → Storage → Cookies → `https://www.bilibili.com`
   - Firefox: DevTools → Storage → Cookies → `https://www.bilibili.com`
   - Copy only `SESSDATA`, `bili_jct`, `DedeUserID`
   - Refresh page / confirm domain if missing
   - Paste only into local hidden `setup` prompts; never chat, screenshots, client config, Issues, PRs, logs, examples.
10. ✅ Stable bilingual heading anchors (`#从浏览器获取凭证字段` / `#finding-credential-fields-in-your-browser`) used in README links.

### Scope compliance

- ✅ Edited only `README.md`, `README_EN.md`, `docs/client-setup.md`, `docs/client-setup.en.md`, the task ticket, and this Claude report.
- ✅ Did not change SVGs, runtime source, tests, package metadata/version, lockfile, workflow, codemap, QA checklist, or pending learning proposals.
- ✅ Changelog bullets unchanged (existing Unreleased entries already cover the documentation rewrite).

### Verification rerun

- `audit_readme.py README.md`: OK
- `audit_readme.py README_EN.md`: OK
- `npm pack --dry-run --json --ignore-scripts`: all 4 README SVGs present, no leaks
- `git diff --check`: no whitespace errors
- UTF-8: all files read correctly
- Local links: verified relative links and heading anchors intact
- Credential patterns: no real Cookie values or SESSDATA in any changed file
- npm release boundary: `1.10.1` explicit; no publish/push action taken

### Acceptance addendum

All 10 User Comprehension Acceptance Addendum criteria checked in the task ticket. The npm release gate (`1.10.1` lacks `setup`/`doctor`) remains explicit in this report.

## Codex Review: Same-Scope Fixes Before Final Acceptance

Applied eight targeted corrections across both READMEs without touching any other file:

1. ✅ Agent prompt URLs: replaced `./docs/client-setup.md` / `./docs/client-setup.en.md` with full public GitHub URLs (`https://github.com/XZXZZX-Ai/bilibili-mcp/blob/master/docs/client-setup.md` / `...client-setup.en.md`) inside copyable Agent prompts, so the prompt works outside a cloned repo. Ordinary README links remain relative.
2. ✅ CN prompt step 3 strengthened: `不要要求、接收、收集或显示我的 Cookie 值，也不要自行将其写入聊天或客户端配置中` — explicitly forbids requesting, receiving, collecting, or displaying Cookie values, matching EN.
3. ✅ Both Agent prompts: failure commands are now full `npx` commands (`npx -y @xzxzzx/bilibili-mcp@latest setup` / `npx -y @xzxzzx/bilibili-mcp@latest config`).
4. ✅ Manual client guide links point directly to `#客户端配置` / `#client-configuration` anchor.
5. ✅ Replaced nested `###` browser-guide heading link with normal bold/inline link sentence in both READMEs.
6. ✅ Windows credential path documented as the generic environment-variable form `%USERPROFILE%\.bilibili-mcp\config.json` in both languages (not a hard-coded machine username).
7. ✅ Added compact manual failure map after the live-check prompt in both READMEs: MCP tool unavailable → config/reconnect; `configured: false` / `needs_credentials` → full setup command; `configured: true` + `logged_in: false` → full config command, reconnect, recheck.
8. ✅ Report updated.

### Rerun verification

- `audit_readme.py README.md`: OK
- `audit_readme.py README_EN.md`: OK
- `npm pack --dry-run --json --ignore-scripts`: 140 files, 4 SVGs present, version 1.10.1, no leaks
- `git diff --check`: no whitespace errors
- Credential patterns: field names only, no real values
- Anchor links: `#客户端配置` / `#client-configuration` / `#从浏览器获取凭证字段` / `#finding-credential-fields-in-your-browser` all verified present in target files

## Codex Review: Final Command Completeness Fix

A final fact review found that both landing pages referred to `doctor --json` without retaining its complete copyable package command. Codex restored:

```text
npx -y @xzxzzx/bilibili-mcp@latest doctor --json
```

to both the Agent-assisted and manual paths in `README.md` and `README_EN.md`. Both languages explicitly state that this command reports local, secret-free configuration status and does not replace the live `check_bilibili_credentials` MCP-tool verification. The targeted re-review confirms that this documentation blocker is resolved. The separate publication blocker remains: npm `1.10.1` lacks `setup` and `doctor`, so the README, CLI, and Node 20 engine correction must ship together.

## Codex Review: Information Architecture Correction

The user correctly identified that the prior opening treated one Favorites-to-evidence workflow as the project definition and delayed the basic capability overview until after installation.

Codex used the `beautify-github-readme` README-mode content architecture to make a bounded correction:

- The page now opens with a plain project definition and five core capability groups.
- Three prominent, copyable use cases follow: traverse every currently visible Favorite Folder, find Videos from a topic, and locate the verified literal keyword `函数` in a long Video with a timestamp link.
- The existing Favorites Hero is unchanged and moved under the matching use case.
- The duplicate post-install Favorites prompt was removed.
- Independent review caught and resolved two overclaims: the Favorites example now lists successfully read rows and reports `skipped_count`, and the English transcript example uses the literal verified keyword `函数` rather than an untranslated English query.
- Both installation paths, all three complete CLI commands, all ten tools, explicit limits, and Cookie safety remain intact.

Verification passes both README audits, bilingual section order, all-ten-tool coverage, exact CLI command checks, nine local links, best-effort Favorites wording, the literal `函数` keyword, high-confidence secret scanning, the 140-file / 128,346-byte package boundary, and `git diff --check`.

No SVG, runtime, test, package metadata/version, dependency, lockfile, workflow, QA checklist, codemap, or pending learning proposal was changed in this correction. Build and Vitest were not rerun for this documentation-only correction. The npm `1.10.1` publication boundary remains unchanged.

## DeepSeek Logic Rewrite Round

The user rejected the current README logic and explicitly requested that DeepSeek write the next revision per the handoff's "DeepSeek Logic Rewrite Round" section.

### Design

Read `SKILL.md`, `references/content-architecture.md`, `src/server/tool-schemas.ts`, `docs/tool-reference.md`, `docs/tool-reference.en.md`, `docs/client-setup.md`, `docs/client-setup.en.md`, and the current bilingual READMEs before writing.

Replaced the previous information architecture with one continuous argument where each section answers the natural question raised by the previous:

1. **Opening** — plain-language user outcome before MCP/stdio jargon. Introduces BVID at first use.
2. **What it can do** — three narrative paths (from Favorites, from a topic, from a BVID) instead of a five-row table that overlaps with the tool reference.
3. **See it in action** — three copyable use cases. The Favorites SVG embeds under its matching use case rather than defining the whole opening.
4. **Install and verify** — both Agent-assisted and manual paths, the install-flow SVG, all three complete `npx` commands, and every safety handoff preserved.
5. **Tool reference** — compact ten-tool table with notes.
6. **Important limits** — best-effort Favorites, `skipped_count`, no ASR/audio/note-generation/bypass.
7. **Privacy and security** — credential storage, Cookie safety, npm boundary.
8. **Development** — clone/build/test commands.
9. **Help and license** — GitHub Issues/Discussions, GPL-3.0.

Both READMEs were written as natural Chinese and natural English rather than mechanical translations. The English transcript example preserves the literal verified keyword `函数`.

### Files changed

- `README.md` — restructured as continuous argument; three-path narrative replaces capability table; Favorites SVG under matching use case
- `README_EN.md` — equivalent English restructure with natural idioms
- `CHANGELOG.md` — updated Unreleased documentation bullet
- `CHANGELOG_EN.md` — updated Unreleased documentation bullet
- `docs/agent-memory/handoffs/2026-07-27-readme-install-flow-claude-report.md` — this appending

### Not changed

- `assets/readme/*.svg` — all four SVGs preserved exactly as-is
- `docs/client-setup*.md` — not edited
- `docs/tool-reference*.md` — not edited
- Runtime source, tests, package metadata/version, dependencies, lockfile, workflow, QA checklist, codemap, pending learning proposals — not edited

### Verification

```powershell
python C:\Users\ZX\.agents\skills\beautify-github-readme\scripts\audit_readme.py README.md
python C:\Users\ZX\.agents\skills\beautify-github-readme\scripts\audit_readme.py README_EN.md
npm pack --dry-run --json --ignore-scripts
git diff --check
```

Results:

- **audit_readme.py README.md**: OK — image references and SVG basics passed (2 local images)
- **audit_readme.py README_EN.md**: OK — image references and SVG basics passed (2 local images)
- **npm pack --dry-run**: 140 files, 128,503 bytes, version 1.10.1, all 4 README SVGs present (hero.svg, hero-en.svg, install-flow.svg, install-flow-en.svg), no test/QA/memory/source paths leaked
- **git diff --check**: no whitespace errors (CRLF conversion warnings only — normal on Windows)

Manual verification:

- **Section logic**: each section answers the question raised by the previous, forming one continuous argument from user outcome to help/license
- **Bilingual equivalence**: same 9 sections in same order; natural idioms in each language
- **All 10 tool names**: `search_bilibili_videos`, `list_bilibili_favorite_videos`, `get_video_info`, `get_video_transcript`, `get_video_metadata`, `get_video_comments`, `get_video_chapters`, `get_credential_setup_instructions`, `check_bilibili_credentials`, `check_mcp_update` — all present in both READMEs
- **All 3 complete CLI commands**: `npx -y @xzxzzx/bilibili-mcp@latest setup`, `npx -y @xzxzzx/bilibili-mcp@latest check`, `npx -y @xzxzzx/bilibili-mcp@latest doctor --json` — all present with full `npx` prefix in both READMEs
- **Local links**: relative paths to client-setup, tool-reference, changelog, and cross-language README links all verified
- **Best-effort Favorites**: "遍历是实时 best-effort，不是快照" / "Traversal is live best effort, not a snapshot" — preserved
- **Literal `函数`**: present in English transcript example as verified keyword
- **Credential safety**: no real Cookie values, SESSDATA values, or credential field values in any changed file
- **BVID introduction**: first use explained as "BVID（B 站视频 ID）" / "BVIDs (Bilibili video IDs)" in opening paragraphs
- **No SVG edits**: all four SVGs untouched
- **npm publication boundary**: version remains 1.10.1; no commit, push, tag, publish, or release

### Harness Artifacts

- **Task ticket**: used — `docs/agent-memory/handoffs/2026-07-27-readme-install-flow-task-ticket.md`, all acceptance criteria and user-comprehension addendum already verified in prior rounds
- **Research note**: not required — no external facts researched
- **QA checklist**: used — `docs/qa/2026-07-27-cli-setup-doctor.md`, bilingual README/client-guide install-path checks rerun and still passing
- **Codemap**: not applicable — README section headers and asset descriptions unchanged from prior round; codemap already reflects the current file layout
- **Harness security**: not applicable — no rules, hooks, skills, subagents, MCP/tool config, memory, handoffs, templates, research, or QA notes changed
- **Harness eval**: deferred — evaluate after the next release or after `cli-setup-doctor` completes

## Same-Scope Factual Repair: Playback-Link Claim

The third capability path in both READMEs claimed that "transcript results" / "字幕结果" generally include direct playback-moment links. The implementation only sets `timestamp_url` for literal keyword-search matches; full transcript, time-range, and `include_timestamps` results carry only `source_url`.

### Changes

- `README.md` line 27: `字幕结果附带可直接跳转的时刻链接。` → `关键词匹配结果附带可直接跳转的时刻链接。`
- `README_EN.md` line 27: `Transcript results include links to exact playback moments.` → `Keyword matches include direct playback-moment links.`

### Verification

- `audit_readme.py README.md`: OK
- `audit_readme.py README_EN.md`: OK
- `git diff --check`: no whitespace errors

## DeepSeek Logic Rewrite Round 2

The user rejected the first DeepSeek rewrite. This is a from-scratch structural replacement, not a polish pass.

### Root problems addressed

1. Opening was slogan-like with sentence fragments → replaced with two grammatical sentences using plain nouns and verbs
2. BVID and workflow mechanics appeared before the reader had a project model → BVID now first appears in usage examples, MCP explained once in opening
3. Examples appeared before installation → installation now precedes usage examples
4. Installation wall interrupted the story → `<details>` blocks collapse the full Agent/manual paths; quick-start paragraph gives the essential commands immediately
5. Three-path capability explanation overlapped the tool table → replaced with three user-facing feature groups (Discover, Read, Configure) that describe outcomes without duplicating tool names

### New structure

1. **Project introduction** — two grammatical sentences: what it connects, what users can accomplish
2. **Core features** — three groups: Discover Videos, Read Video content, Configure and verify
3. **Install and verify** — quick-start paragraph first, then `<details>` blocks for complete Agent-assisted and manual paths; install SVG beside installation
4. **Usage examples** — Favorites traversal (with hero SVG), topic search, transcript keyword lookup (with literal `函数` and verified timestamp link); keyword-only `timestamp_url` wording preserved
5. **Tool reference** — compact ten-tool table
6. **Limits, privacy, development, help/license** — unchanged

### Files changed

- `README.md` — full structural rewrite per Round 2 order
- `README_EN.md` — equivalent English rewrite with natural idioms
- `CHANGELOG.md` — updated Unreleased documentation bullet
- `CHANGELOG_EN.md` — updated Unreleased documentation bullet
- `docs/agent-memory/handoffs/2026-07-27-readme-install-flow-claude-report.md` — this appending

### Not changed

- `assets/readme/*.svg` — all four SVGs untouched
- `docs/client-setup*.md` — not edited
- `docs/tool-reference*.md` — not edited
- Runtime source, tests, package metadata/version, dependencies, lockfile, workflow, QA checklist, codemap, pending learning proposals — not edited

### Verification

- `audit_readme.py README.md`: OK
- `audit_readme.py README_EN.md`: OK
- `npm pack --dry-run --json --ignore-scripts`: 140 files, 128,440 bytes, version 1.10.1, all 4 SVGs present, no leaks
- `git diff --check`: no whitespace errors

Manual checks:
- Section order: intro → features → install → usage → tools → limits → privacy → dev → help — matches required order
- Bilingual equivalence: same 9 sections in same order; natural idioms in each language
- All 10 tool names: all present and correct in both READMEs
- All 3 CLI commands: `setup`, `check`, `doctor --json` — all present with full `npx` prefix
- `<details>` blocks: both READMEs use collapsed sections for Agent-assisted and manual installation paths
- Favorites SVG: beside Favorites usage example; install SVG: beside installation section
- Best-effort Favorites wording: preserved
- Literal `函数`: preserved in English transcript example
- Keyword-only `timestamp_url`: "关键词匹配结果附带可直接跳转的时刻链接" / "Keyword matches include direct playback-moment links"
- Credential safety: no real values in any changed file
- npm publication boundary: version 1.10.1; no commit, push, tag, publish, or release

### Harness Artifacts

- **Task ticket**: used — all acceptance criteria already verified in prior rounds
- **Research note**: not required
- **QA checklist**: used — `docs/qa/2026-07-27-cli-setup-doctor.md`
- **Codemap**: not applicable — unchanged
- **Harness security**: not applicable — no trust-boundary or safety-baseline changes
- **Harness eval**: deferred — evaluate after next release or after `cli-setup-doctor` completes

## DeepSeek Reader-First Repair Round 3

Codex and two independent reviewers found remaining reader and factual blockers. Same-scope repair per the handoff addendum.

### Reader-flow changes

1. **Opening** — "Bilibili MCP 是供 MCP 兼容 AI 客户端使用的本地工具" / "local tool for MCP-capable AI clients". No `MCP server` in Chinese. Product boundary: retrieves content; user or Agent decides how to process it; does not generate notes automatically.
2. **Core features** — removed "Configure and verify" group (installation section owns it). Three product-outcome groups: browse Favorites, search by topic, explore a video.
3. **Plain Chinese** — no `Folder` in prose; `收藏夹` throughout. BVID explained as "B 站视频 ID（BVID）" at first use in usage examples. `分 P` used over multi-Part hybrid wording.
4. **Prerequisites visible** — Node.js 20+ requirements placed before any `npx`, `stdio`, `command`, or `args` instruction.
5. **Scannable install** — replaced Quick start paragraph with numbered 4-step path: check toolchain → add service → configure locally → verify login. Full Agent/manual paths remain in `<details>` blocks.
6. **Idiomatic English** — sentence-case headings ("Browse favorites", "Search by topic", "Explore a video"). "Favorite Folders", "multi-part structure", "multi-part videos". Removed "Read Video content", "through Favorites", "multi-Part listings".

### Factual changes

1. **`skipped_count`** — narrowed to "当前收藏夹视频页中无法安全规范化的视频条目" / "video entries in the current Favorites page that cannot be safely normalized". Does not imply malformed Folder rows are counted.
2. **Comment ordering** — replaced "按热度或时间排序" / "sorted by popularity or time" with "优先展示带时间戳和获赞较高的评论" / "with timestamp-bearing and higher-liked comments prioritized" in feature groups. Tool reference note now reads "接受按热门或最新排序的请求...最终输出优先展示带时间戳和获赞较高的评论" / "accepts hot or newest sort requests...final output prioritizes timestamp-bearing and higher-liked comments".
3. **Preserved boundaries** — keyword-only `timestamp_url`, caller-driven Favorites traversal, one page/20 rows/`next_cursor`, live best-effort, all ten tools, all three CLI commands, `函数` literal keyword, all safety/cookie/storage/encryption/npm disclosures.

### Files changed

- `README.md` — all Round 3 reader and factual repairs
- `README_EN.md` — all Round 3 reader and factual repairs
- `CHANGELOG.md` — updated Unreleased documentation bullet
- `CHANGELOG_EN.md` — updated Unreleased documentation bullet
- `docs/agent-memory/handoffs/2026-07-27-readme-install-flow-claude-report.md` — this appending

### Not changed

SVGs, client-setup docs, tool-reference docs, runtime, tests, package metadata/version, lockfile, workflow, QA checklist, codemap, pending learning proposals.

### Verification

- `audit_readme.py README.md`: OK
- `audit_readme.py README_EN.md`: OK
- `npm pack --dry-run --json --ignore-scripts`: 140 files, 128,733 bytes, version 1.10.1, all 4 SVGs present, no leaks
- `git diff --check`: no whitespace errors

Manual checks:
- **Opening**: two grammatical sentences, no `MCP server` in Chinese, product boundary stated ✓
- **Feature groups**: three product outcomes, no "Configure and verify" ✓
- **Plain Chinese**: no `Folder` in prose, BVID explained as B 站视频 ID, 分 P used ✓
- **Prerequisites**: Node.js 20+ visible before any npx/stdio/command/args ✓
- **Numbered install**: 4-step scannable path with full `<details>` blocks preserved ✓
- **Sentence-case English headings**: Browse favorites, Search by topic, Explore a video ✓
- **`skipped_count`**: precisely scoped to video entries in current Favorites page ✓
- **Comments**: timestamp-bearing and higher-liked prioritized; no claim of sorted-by-time output ✓
- **Keyword-only `timestamp_url`**: preserved ✓
- **Literal `函数`**: preserved in English example ✓
- **All 10 tools**: all present ✓
- **All 3 CLI commands**: all present with full `npx` prefix ✓
- **Credential safety**: no real values ✓

### Harness Artifacts

- **Task ticket**: used — all criteria already verified
- **Research note**: not required
- **QA checklist**: used — `docs/qa/2026-07-27-cli-setup-doctor.md`
- **Codemap**: not applicable — unchanged
- **Harness security**: not applicable
- **Harness eval**: deferred

## Decision Points

None. All implementation choices were bounded by the task ticket and handoff. The user selected "beautify-github-readme Full redesign / README mode" before the handoff, and Codex froze the scope in the task ticket.

## Suggested Codex Review Focus

1. Bilingual parity: confirm the Chinese and English README sections convey equivalent information with natural idioms (especially the "Important limits" section and the "No ASR / audio download" negation).
2. Tool table accuracy: verify all 10 MCP tools are listed with correct names and that the `get_video_info` vs `get_video_transcript` distinction is clear.
3. SVG rendering: render the new install-flow SVGs at 900px and 360px to confirm readability at both widths.
4. The npm publication boundary: confirm the Unreleased changelog entries will be moved under a dated version header when the CLI implementation ships.

## BVID First-Use Fix

The first visible BVID occurrence was in the Favorites prompt without explanation; the Chinese explanation appeared later in the search example, and the English README had no explanation at all.

- `README.md`: Favorites prompt `BVID` → `B 站视频 ID（BVID）`; removed now-redundant `（B 站视频 ID）` from search example.
- `README_EN.md`: Favorites prompt `BVIDs` → `Bilibili video IDs (BVIDs)`.

Audits OK, `git diff --check` no whitespace errors. No other content changed.

## Opening De-Jargon Fix

Replaced the still-technical "MCP 兼容 AI 客户端 / MCP-capable AI clients" in both openings with plain language: "让 AI 客户端可以读取 Bilibili 视频和当前账号的收藏夹 / lets AI clients read Bilibili videos and the current account's Favorite Folders". Both now read as two natural sentences with no protocol terminology. Audits OK, `git diff --check` clean.
