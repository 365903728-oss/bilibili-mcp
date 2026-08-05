# Codex To Claude Code Handoff: Bilingual README Full Redesign

## Update Goal

Implement the frozen task ticket:

`docs/agent-memory/handoffs/2026-07-27-readme-install-flow-task-ticket.md`

Rewrite both repository homepages against the current project, correct the paired Hero copy, and add paired GitHub-safe installation-flow SVGs without changing runtime behavior.

## Current Judgment

This is a full README redesign. Keep the verified Favorites evidence proof and existing Hero geometry, but rebuild the Markdown hierarchy around the current ten-tool MCP surface, CLI onboarding, explicit product limits, and the path from installation to verified login.

## Required Capabilities

- Follow the user-selected `beautify-github-readme` README mode contract captured in the task ticket.
- Reuse the current Hero's palette, type families, rounded technical cards, and status-flow motif.
- Use existing Markdown and hand-authored SVG patterns; add no dependency or generation tool.
- Write the implementation report to:
  `docs/agent-memory/handoffs/2026-07-27-readme-install-flow-claude-report.md`

## Files To Inspect Or Edit

Inspect:

- task ticket above
- `README.md`, `README_EN.md`
- `assets/readme/hero.svg`, `assets/readme/hero-en.svg`
- `src/server/tool-schemas.ts`, `src/server/tool-handlers.ts`, `src/cli.ts`
- `docs/client-setup.md`, `docs/client-setup.en.md`
- `docs/tool-reference.md`, `docs/tool-reference.en.md`
- `CHANGELOG.md`, `CHANGELOG_EN.md`
- `docs/agent-memory/codemap.md`

Edit only:

- `README.md`, `README_EN.md`
- `assets/readme/hero.svg`, `assets/readme/hero-en.svg`
- `assets/readme/install-flow.svg`, `assets/readme/install-flow-en.svg`
- `docs/client-setup.md`, `docs/client-setup.en.md`
- `CHANGELOG.md`, `CHANGELOG_EN.md`
- `docs/agent-memory/codemap.md`
- the task ticket status/checklist
- the Claude report

## Recommended Approach

1. Read the task ticket's factual inventory and required information architecture.
2. Rewrite both READMEs end to end. Keep only verified claims and natural bilingual equivalents.
3. Correct both existing Hero variants without changing geometry:
   - replace `MCP READY` with `LOCAL STDIO`;
   - narrow the Favorites claim to created/currently visible Folders and caller-driven `next_cursor` traversal;
   - keep the terminal/status visual grammar.
4. Add the paired `1200 × 640` installation SVGs exactly to the visual contract.
5. In each README installation section:
   - embed the matching SVG;
   - keep exact `setup`, `check`, and `doctor --json` commands copyable;
   - explain reconnect and `check_bilibili_credentials`;
   - put the first Favorites prompt only after the verification gate.
6. In both setup guides:
   - replace the four client-specific stale `bilibili-mcp config` reminders (Qoder, Kimi Code, Pi, Windsurf) with `bilibili-mcp setup`;
   - add the local-only doctor boundary and exit codes `0/1/2`;
   - recommend Node.js 20+;
   - clarify that inherited environment variables work, but the recommended npm CLI path does not automatically load a project `.env`.
7. Add one concise Unreleased changelog bullet per language.
8. Update the codemap README/asset description.
9. Run the task ticket's non-runtime checks and report exact results.

## Things To Avoid

- Do not redesign the Hero geometry.
- Do not rewrite exhaustive client configs beyond the named stale setup reminders and prerequisite/environment clarifications.
- Do not place Cookie field names/values or full package commands only inside SVG.
- Do not make `doctor` look like live Bilibili login validation.
- Do not claim the current npm `latest` already contains this CLI; publication is a later gate.
- Do not repeat `structuredContent`, cursor-decoding internals, request counts, or full error schemas on the homepage.
- Do not call the project a summarizer, downloader, knowledge base, or ASR tool.
- Do not claim Node 18+ support in new README/setup copy; recommend Node 20+ while leaving package metadata unchanged for the separate engine-floor task.
- Do not edit source, tests, generated output, package metadata/version, lockfile, workflow, or pending learning proposals.
- Do not commit, push, tag, publish, or create a release.

## Acceptance Criteria

Use every acceptance criterion in the task ticket. If a requirement cannot be met without leaving scope, stop and report the exact decision point.

## Verification Commands

```powershell
python C:\Users\ZX\.agents\skills\beautify-github-readme\scripts\audit_readme.py README.md
python C:\Users\ZX\.agents\skills\beautify-github-readme\scripts\audit_readme.py README_EN.md
npm pack --dry-run --json --ignore-scripts
git diff --check
git status --short
```

Do not run build or Vitest for this documentation-only implementation; Codex will run the final repository-level gates after review because runtime changes already exist in the shared worktree.

## Report Requirements

Report:

- exact files changed;
- commands and results;
- SVG dimensions and safety properties;
- whether any target was skipped;
- the npm publication boundary;
- unresolved risks or decision points;
- Harness Artifacts status.

## Codex Review: Repair Round 1

The first implementation pass has the right overall information architecture and visual direction. Apply the following same-scope corrections before marking the ticket complete:

1. Replace the tool-table goal `想让 AI 总结一个视频` / `Ask AI to summarize a video` with `快速获取字幕优先的视频上下文` / `Get subtitle-first video context`. The project retrieves context; it does not perform AI summarization.
2. Make the comments row say that `get_video_comments` supports hot or newest/time sorting, timestamped comments, and optional replies.
3. State consistently that `get_video_info` falls back to title, description, and tags when subtitles are unavailable.
4. State that `get_video_transcript` description fallback is incompatible with keyword search, timestamp output, and time-range filters.
5. Correct privacy copy: Bilibili content requests go only to official Bilibili interfaces; install/update checks may access the npm registry but never send the Cookie there. Restore the warning that the local global credential file does not promise operating-system-level encryption.
6. Remove the setup-guide advice to inject Cookies through a client `env` field. Say instead:
   - the recommended npm bin / `npx` path does not auto-load a project `.env`;
   - `setup` is the normal installation path;
   - inherited process variables work only when a controlled shell, service, or secret runtime supplies them;
   - the local `.env` example applies to source `npm start` / `dist/index.js`, or to a runtime that explicitly loads it.
7. Describe `doctor --json` exit code `1` as “需要配置或凭证不可加载” / “needs credentials or credentials are not loadable”, not only “missing credentials”.
8. In the installation section, cover both paths: an Agent can install it, while manual users can follow the client guide. Add the Node.js 20+ and `npx` prerequisite, plus the copyable stdio launch baseline `command: npx`, `args: ["-y", "@xzxzzx/bilibili-mcp@latest"]`; do not present this as a universal client configuration format.
9. Remove the separate `CLI 与状态入口` / `CLI and status gates` homepage table because it repeats the install section and uses bare commands that require a global installation. Retain one concise note in the install section: no arguments start stdio; `config` forces reconfiguration; `check-update` queries npm; bare `bilibili-mcp` commands require a global install, otherwise use the complete `npx` prefix.
10. Restore the Favorites `skipped_count` boundary: upstream rows that cannot be normalized safely are counted as skipped and no replacement row is fetched for that page.
11. Remove the redundant textual npm navigation link while keeping the npm badge and latest Release link.
12. Improve natural language: use `video candidates`, not `normal-video candidates`; replace the legalistic verified-example disclaimer with the concrete statement that Bilibili may remove or change the example video; use Chinese quotation marks or inline code around `函数`.
13. In both Hero completion cards, replace `全部可见标题 + BVID` / `ALL TITLES + BVIDS` with `标题 + BVID` / `TITLES + BVIDS`.
14. Fix English Hero overflow: use `VISIBLE FOLDERS` for the first card and a short second-card title such as `FOLDER · PAGE ≤ 20` or `ONE FOLDER · ONE PAGE`.
15. Remove the green circle that overlaps the fourth installation-flow title in both SVGs.
16. Redesign only the internal typography/content of the two installation-flow SVGs for 360px readability: keep the existing 1200 × 640 canvas, palette, four-stage stacked flow, safe SVG properties, and geometry-identical bilingual pair; remove nonessential body copy and tiny pills, and make the four essential stage titles approximately 36–40px or larger. Exact commands/details remain in adjacent Markdown.
17. Make installation stage 1 say Agent or user, rather than Agent-only.
18. Keep the two-column or three-column tool presentation only if it remains readable on mobile. Prefer a compact two-column `目标 / 工具` presentation and leave return details in the tool reference.
19. Preserve the frozen visual contract's optional Agent status entry in stage 2: `doctor --json` must remain visibly present in both installation-flow SVGs, but it may be a concise secondary line rather than a tiny pill. The adjacent Markdown remains the authoritative command explanation.
20. Correct the report's Harness Artifacts assessment. This task changes the public install documentation from `config` to `setup` and introduces the unpublished `doctor` path, so explicitly reference `docs/qa/2026-07-27-cli-setup-doctor.md` as the shared pre-release CLI/install QA checklist, state which bilingual README/client-guide checks this repair reran, and preserve the release binding. Do not claim that the install path was unchanged.

After repair:

- render all four SVGs at both 900px and 360px and inspect for clipping, overlap, and essential-text readability;
- rerun both README audits, `npm pack --dry-run --json --ignore-scripts`, `git diff --check`, UTF-8/local-link/SVG-safety/credential-pattern checks;
- update the Claude report with the repair round and exact results;
- mark the task ticket complete only if every affected criterion is actually satisfied;
- do not edit runtime/package metadata, commit, push, publish, release, or touch `docs/agent-memory/pending-learning-proposals.md`.

## Codex Review: User Comprehension Repair Round

The user challenged whether the final README is actually sufficient for both Agent-assisted and manual installation. Three read-only persona reviews found that the project story is clear, but the installation paths are not yet independently complete. Make the smallest documentation-only repair:

### README opening

- Replace the technical first sentence with plain language that says the tool lets an Agent read Bilibili topic results or the user's Favorites, then retrieve video IDs, subtitle context, and timestamped evidence.
- Introduce `BVID` as “Bilibili video ID / B 站视频 ID” at first use.
- Keep the statement that this is a local MCP server and does not generate notes.

### README installation section

Keep the existing installation SVG, then split the Markdown into:

1. **Agent-assisted installation (recommended)** with one copyable prompt. The prompt must instruct the Agent to:
   - identify the current MCP client and ask the user if uncertain instead of guessing;
   - open the matching section in the canonical client setup guide;
   - add `bilibili-mcp` as local stdio with `command: npx` and args `["-y", "@xzxzzx/bilibili-mcp@latest"]`;
   - never request, receive, display, or ask the user to paste Cookie values into chat or client config;
   - stop and ask the user to run `setup` and `check` interactively in the user's own terminal;
   - ask the user to restart/reconnect when the Agent cannot do it;
   - after reconnect, call the MCP tool `check_bilibili_credentials`;
   - accept success only when `configured: true` and `logged_in: true`;
   - map `needs_credentials` to `setup`, live `logged_in: false` to forced `config` plus reconnect/recheck, and a missing MCP server to client-config/reconnect review.

2. **Manual installation** with:
   - the official Node.js link and copyable `node --version` / `npx --version` checks;
   - server name, command, and args as labeled fields rather than a code block that looks universally pasteable;
   - a direct link to the matching client-configuration section;
   - a direct link to the new browser-Cookie-field section;
   - the full `npx ... setup` and `check` commands;
   - a nearby warning that Cookie values go only into hidden local terminal prompts, never Agent chat or MCP client config;
   - Windows and macOS/Linux global config locations and the no-OS-encryption guarantee;
   - reconnect instructions;
   - a copyable client-chat prompt that explicitly says to call the MCP tool `check_bilibili_credentials` and report only `configured` / `logged_in`, never Cookie values.

Keep the existing first-use Favorites prompt after successful validation. Remove the redundant general CLI paragraph from the homepage; detailed CLI behavior already lives in the canonical guide.

### Canonical setup guides

In both `docs/client-setup.md` and `docs/client-setup.en.md`, add one concise browser credential-field subsection immediately before recommended interactive setup:

- sign in to the user's own account at `https://www.bilibili.com`;
- Chrome/Edge: DevTools → Application → Storage → Cookies → `https://www.bilibili.com`;
- Firefox: DevTools → Storage → Cookies → `https://www.bilibili.com`;
- copy only the exact values of `SESSDATA`, `bili_jct`, and `DedeUserID`;
- if missing, refresh the logged-in page and confirm the selected domain;
- paste values only into the local hidden-input `setup` prompts;
- never paste them into chat, screenshots, client config, Issues, PRs, logs, or examples.

Add stable bilingual heading anchors through normal Markdown headings and link to them from the READMEs.

### Scope and verification

- Edit only `README.md`, `README_EN.md`, `docs/client-setup.md`, `docs/client-setup.en.md`, the existing Unreleased README changelog bullets if clarification is needed, the task ticket, and the Claude report.
- Do not change SVGs, runtime source, tests, package metadata/version, lockfile, workflow, codemap, QA checklist, or pending learning proposals.
- Run both README audit scripts, bilingual heading/required-copy checks, local-link/anchor checks, strict UTF-8, high-confidence credential scanning, `npm pack --dry-run --json --ignore-scripts`, and `git diff --check`.
- Update the Claude report with this user-comprehension round and keep the npm `1.10.1` release boundary explicit.
- Mark the ticket complete only after every addendum checkbox is verified.

## Codex Same-Scope Information Architecture Correction

The user later clarified that the landing page must read from basic capability to concrete use. Codex applied the smallest same-scope repair:

1. Start with the project definition and a five-row capability overview.
2. Follow with three prominent, copyable use cases: Favorites traversal, topic search, and exact transcript lookup.
3. Move the existing Favorites Hero embed under its matching use case without editing or adding SVG assets.
4. Keep installation, tool coverage, limits, privacy, and development content after the examples.
5. Preserve the live-state and `skipped_count` boundaries; do not promise that every upstream row can be returned.

This correction does not authorize runtime, package metadata, version, dependency, test, SVG, workflow, commit, push, or release changes.

## DeepSeek Logic Rewrite Round

The user rejected the current README logic again and explicitly requested that DeepSeek write the next revision. Treat the current README as a draft to critique, not a structure to rubber-stamp.

### Objective

Rewrite `README.md` and `README_EN.md` so a first-time visitor experiences one continuous argument:

1. What this project is, in plain user language.
2. Why someone would use it.
3. The basic capabilities, grouped without duplicating the later tool reference.
4. A few prominent, attractive, copyable uses that prove the capabilities.
5. How an Agent or person installs and verifies it.
6. Tool detail, limits, privacy, development, and help.

Every section must answer the natural question raised by the previous section. Do not merely reorder headings.

### Required writing work

- Read the current bilingual READMEs, `src/server/tool-schemas.ts`, `docs/tool-reference.md`, `docs/client-setup.md`, and the current Unreleased changelog before writing.
- Read `C:/Users/ZX/.agents/skills/beautify-github-readme/SKILL.md` and `references/content-architecture.md` as the writing framework. The skill is not installed under `.claude/skills`, so use these exact source paths without copying or installing it.
- Make the first paragraph explain the user outcome before MCP/stdio/BVID jargon.
- Keep strong use cases prominent, but do not let Favorites define the whole product.
- Reduce or remove repetition between the high-level capability section and the ten-tool detail section.
- Preserve the existing Favorites and installation SVG files; move/embed them only where they serve the story. Do not edit or add assets.
- Preserve both independently complete installation paths and every safety handoff already accepted.
- Preserve all three complete commands:
  - `npx -y @xzxzzx/bilibili-mcp@latest setup`
  - `npx -y @xzxzzx/bilibili-mcp@latest check`
  - `npx -y @xzxzzx/bilibili-mcp@latest doctor --json`
- Preserve the distinction between local `doctor --json` and live MCP `check_bilibili_credentials`.
- Keep Favorites traversal best-effort: currently visible created Folders, one upstream page per call, follow `next_cursor`, list successfully normalized rows, and report `skipped_count`.
- Keep the English transcript example on the literal verified keyword `函数`; the tool does not translate keyword searches.
- Keep all ten current MCP tools reachable, all important limits, Cookie safety, local credential paths, development commands, license, and support links.
- Write natural Chinese and natural English rather than mechanically translating one into the other.

### Files

Edit:

- `README.md`
- `README_EN.md`
- `CHANGELOG.md`
- `CHANGELOG_EN.md`
- `docs/agent-memory/handoffs/2026-07-27-readme-install-flow-claude-report.md`

Do not edit:

- `assets/readme/*.svg`
- `docs/client-setup*.md`
- `docs/tool-reference*.md`
- runtime source, tests, package metadata/version, dependencies, lockfile, workflow, QA checklist, codemap, or pending learning proposals

### Verification

Run:

```powershell
python C:\Users\ZX\.agents\skills\beautify-github-readme\scripts\audit_readme.py README.md
python C:\Users\ZX\.agents\skills\beautify-github-readme\scripts\audit_readme.py README_EN.md
npm pack --dry-run --json --ignore-scripts
git diff --check
```

Also verify section logic, bilingual equivalence, all ten tool names, all three complete CLI commands, local links, best-effort Favorites wording, the literal `函数` English example, and absence of real credential values.

### Stop and report

Do not change runtime behavior, SVGs, package/version metadata, or publication state. Do not commit, push, tag, or release. If a truthful logical rewrite would require one of those changes, stop and report the decision point.

## DeepSeek Logic Rewrite Round 2

The user rejected the first DeepSeek rewrite as still not good enough. Do not polish that draft. Replace its structure and opening copy.

### Root problem

The first rewrite still reads like a marketing sequence rather than a predictable tool README:

- the opening is slogan-like and ends in sentence fragments;
- BVID and workflow mechanics appear before the reader has a stable project model;
- examples appear before installation, so the page shows commands the reader cannot run yet;
- the installation wall interrupts the story;
- the high-level three-path explanation still overlaps the ten-tool table.

### Required final order

Use this conventional documentation order in both languages:

1. **Project introduction** — two short, grammatical sentences: what it connects and what users can accomplish. No BVID, cursor, stdio, Cookie field, or implementation jargon in the opening.
2. **Core features** — group basic capabilities into exactly three user-facing groups:
   - discover Videos: Favorites and topic search;
   - read Video content: transcript/context, metadata, Parts, Chapters, and comments;
   - configure and verify locally: credential guidance, login status, and update checks.
3. **Install and verify** — shortest universal path first, then the complete Agent-assisted and manual paths. Keep both paths self-contained, but use native GitHub `<details>` sections when that prevents the full prompt/manual detail from dominating the page.
4. **Usage examples** — after installation, show three prominent copyable prompts: Favorites traversal, topic search, and literal transcript keyword lookup with the verified timestamp link.
5. **Tool reference** — compact mapping of all ten tools; avoid re-explaining the feature groups.
6. **Limits, privacy, development, help/license**.

### Copy rules

- Start from a blank outline; do not reuse the current opening or "three paths" copy.
- Prefer plain nouns and verbs over slogans such as "Let your Agent read Bilibili."
- Explain MCP once, after the user outcome is clear.
- Introduce BVID only in the feature or usage section where it first becomes necessary.
- Keep the Favorites SVG beside the Favorites usage example and the install SVG beside installation; do not edit assets.
- Keep use cases prominent through clear headings and copyable prompts, not inflated claims.
- Preserve every accepted factual, safety, command, failure, and release boundary from the prior handoff.
- Preserve keyword-only `timestamp_url` wording and literal `函数` in the English verified example.
- Natural Chinese and English are required; do not translate sentence structure mechanically.

### Scope and verification

Use the same allowed files and forbidden files as the first DeepSeek round. Personally re-read the complete `beautify-github-readme` skill and required README-mode references before editing. Update the existing report and rerun every specified README, link, tool, command, secret, package, and diff check. Do not commit, push, tag, publish, or release.

## DeepSeek Reader-First Repair Round 3

Round 2 is structurally better, but Codex and two independent reviewers found
remaining reader and factual blockers. Treat this as a same-scope repair. Read
the exact `beautify-github-readme` skill and its content-architecture reference
again before editing.

### Reader-flow repairs

1. Replace the opening with two natural, user-facing sentences. Define this as
   a local tool for MCP-capable AI clients without saying `MCP server` in the
   Chinese copy. State the product boundary clearly: it retrieves Bilibili
   content and lets the user or Agent decide how to process it; it does not
   generate notes automatically.
2. Keep exactly three core feature groups, but make all three product outcomes:
   - read every currently visible Favorite Folder created by the logged-in account;
   - search for videos by topic;
   - read a selected video's transcript, metadata, Parts, Chapters, and comments.
   Remove `Configure and verify` from Core features because the following
   installation section already owns that workflow.
3. Use plain Chinese in the Chinese README. Do not use `Folder` in prose where
   `收藏夹` is sufficient. At the first user-facing use of BVID, explain it as
   `B 站视频 ID（BVID）`. Prefer `分 P` over `multi-Part`-style wording.
4. Make prerequisites visible before any `npx`, `stdio`, `command`, or `args`
   instruction. Keep Node.js 20+ as the documented conservative prerequisite.
5. Replace the long Quick start paragraph with a short numbered path that can
   be scanned:
   - confirm Node.js / npx;
   - add the MCP service to the client;
   - run setup and check locally;
   - reconnect and perform live MCP login verification.
   Keep the complete Agent-assisted and manual paths in their existing
   `<details>` blocks.
6. Make the English copy idiomatic: use sentence-case headings, `Favorite
   Folders`, and `multi-part videos`; avoid phrases such as `Read Video
   content`, `through Favorites`, and `multi-Part listings`.

### Factual repairs

1. Scope `skipped_count` precisely: it counts video entries in the current
   Favorite video page that cannot be safely normalized. Do not imply that
   malformed Folder rows are counted.
2. Do not claim that final comment output remains sorted by latest/time. The
   upstream request accepts `hot` or `time`, but the implementation then
   prioritizes comments containing timestamps and orders the remainder by likes.
   Prefer a concise user-facing statement such as reading comments and replies,
   with timestamp-bearing and higher-liked comments prioritized.
3. Preserve all previously verified boundaries: keyword matches only receive
   direct playback-moment links; Favorites traversal is caller-driven, one
   upstream page of at most 20 rows per call, follows `next_cursor`, and is
   live best effort; all ten tools and all three complete CLI commands remain.

### Scope and verification

- Allowed edits remain `README.md`, `README_EN.md`, `CHANGELOG.md`,
  `CHANGELOG_EN.md`, and the existing Claude report.
- Do not edit SVGs, setup/reference docs, runtime code, tests, package metadata,
  lockfiles, workflows, QA/codemap, or pending learning proposals.
- Rerun both README audits, `git diff --check`, and
  `npm pack --dry-run --json --ignore-scripts`.
- Append a Round 3 result to the existing Claude report.
- Do not commit, push, tag, publish, or release.
