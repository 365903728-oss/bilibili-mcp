# Task Ticket: Bilingual README Full Redesign

- ID: `DOCS-README-INSTALL-2026-07-27`
- Status: `completed` — user comprehension repair round verified
- Owner: `Claude Code`, reviewed by `Codex`
- Source: User-selected `beautify-github-readme` full README redesign
- Parent plan or PRD: none
- Blocking tickets: none
- Blocked by: none

## Objective

Rewrite `README.md` and `README_EN.md` against the current source, tests, CLI, package, and canonical guides. Preserve the real Favorites evidence proof, correct outdated or misleading claims, and add one GitHub-safe installation-flow SVG per language.

## Current Judgment

The current Favorites-first proof is valid, but the homepage is fragmented:

- the Hero's static `MCP READY` label overstates local/login readiness;
- installation omits the `setup → reconnect → live credential check` gates;
- the "local helpers" grouping includes two networked MCP tools while omitting the local CLI doctor;
- design, behavior, and security copy repeats itself;
- the homepage does not clearly say that it has no ASR, audio download, automatic note generation, or server-side all-Favorites snapshot;
- English copy over-capitalizes ordinary nouns.

A full rewrite is clearer than adding more patches. Reuse the current Hero geometry and verified evidence example, but rewrite the Markdown story and correct the Hero text.

The published npm `latest` is still `1.10.1` and does not include `setup` or `doctor`. These README changes must remain unpublished until they ship with the CLI implementation in a later package version.

## Audience And Story

- Audience: people using Codex, Claude Code, Cursor, or another MCP-capable Agent/client.
- One-sentence value: discover Bilibili videos from a topic or the current account's created Favorites, then retrieve transcript evidence and supporting metadata without generating notes.
- Primary proof: caller-driven Favorites traversal and a real transcript keyword match with a playback timestamp URL.
- First successful action: identify the actual MCP client and add the local stdio server using `npx`.
- Visual theme: the existing dark technical Bilibili palette and status-flow grammar.

## Required Information Architecture

Use equivalent Chinese/English sections:

1. Opening — existing Favorites Hero, H1, concise badges/navigation, one plain-language product sentence.
2. From Favorites to citable evidence — created/visible Favorites or topic search → BVID → transcript keyword/timestamp evidence; retain the real `BV1Eb411u7Fw` acceptance example but label it as a verified example rather than a permanent external guarantee.
3. Install and verify — paired installation SVG, exact Markdown commands, reconnect gate, local doctor versus live Bilibili login, then the first Favorites prompt.
4. Choose tools by task — a compact goal-oriented table covering all ten MCP tools and the important `get_video_info` versus strict `get_video_transcript` distinction.
5. CLI and status gates — distinguish no-argument stdio, `setup`, `config`, `check`, `doctor --json`, and live MCP validation without turning the homepage into a full reference.
6. Important limits — caller-driven cursor traversal, created/currently visible Folders, best-effort live state, no cross-Folder dedupe, no ASR/audio download/note generation/automatic evidence prefetch, subtitle fallback rules, and no access bypass.
7. Privacy and security — local credential entry, no Cookie in chat/client config, official Bilibili endpoints, throttling/account risk, third-party status.
8. Development.
9. Help and license.

Move detailed schemas, `structuredContent`, cursor validation internals, error payload fields, and request-count implementation into the existing tool reference instead of repeating them on the homepage.

## Scope

In scope:

- Fully rewrite `README.md` and `README_EN.md` with equivalent bilingual structure.
- Correct the copy/alt text in `assets/readme/hero.svg` and `assets/readme/hero-en.svg` without redesigning their geometry.
- Add `assets/readme/install-flow.svg` and `assets/readme/install-flow-en.svg`.
- Keep exact copyable `setup`, `check`, and `doctor --json` commands in Markdown.
- Explain that `doctor --json` is local-only and that `check_bilibili_credentials` is the live-login authority.
- Replace eight stale client-guide recommendations from `bilibili-mcp config` to the preferred `bilibili-mcp setup`; retain `config` only in the explicit force-reconfiguration explanation.
- Recommend Node.js 20+ in homepage/setup copy because the installed Commander runtime declares that floor; do not change package metadata or resolve the separate engine-floor issue in this task.
- Clarify that inherited process environment variables work, while the recommended npm bin path does not automatically load a project `.env`.
- Add a short bilingual Unreleased changelog entry.
- Update the codemap only as needed for the expanded README asset set.

Out of scope:

- Rebuilding the existing Hero geometry or adding decorative section assets.
- Image generation, animation, GIFs, screenshots, new dependencies, or a new installer.
- Runtime, MCP schemas/tools, package metadata/version, lockfile, release workflow, commit, push, tag, npm publish, or GitHub Release.
- Rewriting exhaustive client configuration sections beyond the named stale setup reminders and prerequisite/environment clarifications.

## Visual Contract

Create two geometry-identical static SVGs:

- Canvas: `1200 × 640`, full-width, complete dark background.
- Files: `install-flow.svg` and `install-flow-en.svg`.
- Title: `从安装到登录验证` / `FROM INSTALL TO VERIFIED LOGIN`.
- Four vertical rows:
  1. Add MCP server — Agent identifies the current client and adds the stdio server.
  2. Local setup — user runs `setup → check`; optional Agent status uses `doctor --json`.
  3. Reconnect — restart the client or reconnect the MCP server.
  4. Verify login — Agent calls `check_bilibili_credentials`; success is `configured + logged_in`.
- Palette: `#090b10` background, `#f8fafc` foreground, `#93a4b8` muted, `#fb7299` pink, `#00aeec` blue, `#22c55e` success.
- Shape: `rx=18/28`, thin strokes, no gradients, filters, shadows, external resources, scripts, or `foreignObject`.
- Type: system sans for prose, system monospace for status tokens.
- Include `<title>`, `<desc>`, `viewBox`, and readable SVG group names.
- Full package commands remain in Markdown rather than only in the SVG.

## Expected Files

- `README.md`
- `README_EN.md`
- `assets/readme/hero.svg`
- `assets/readme/hero-en.svg`
- `assets/readme/install-flow.svg`
- `assets/readme/install-flow-en.svg`
- `docs/client-setup.md`
- `docs/client-setup.en.md`
- `CHANGELOG.md`
- `CHANGELOG_EN.md`
- `docs/agent-memory/codemap.md`
- this ticket
- `docs/agent-memory/handoffs/2026-07-27-readme-install-flow-claude-report.md`

Do not touch:

- `src/`, `tests/`, `dist/`, `package.json`, or `package-lock.json`
- `docs/agent-memory/pending-learning-proposals.md`

## Acceptance Criteria

- [x] Both READMEs are fully rewritten with equivalent bilingual headings and natural English.
- [x] The first screen states that this is a local stdio MCP server for Bilibili discovery and evidence extraction, not a note generator.
- [x] Both Heroes retain their geometry while removing `MCP READY` and narrowing “all Favorites” to caller-driven traversal of created/currently visible Folders.
- [x] Both READMEs embed the matching local installation-flow SVG with meaningful alt text.
- [x] Markdown, not the SVG alone, contains the exact `setup`, `check`, and `doctor --json` commands.
- [x] The four-stage flow distinguishes local status from live login verification.
- [x] The tool-selection section covers all ten current MCP tools without repeating detailed schemas or implementation internals.
- [x] The READMEs clearly state that no ASR, audio download, automatic note generation, automatic downstream prefetch, snapshot isolation, or access bypass exists.
- [x] Both setup guides recommend `setup` in client-specific credential reminders; `config` remains only for force reconfiguration.
- [x] README/setup copy recommends Node.js 20+ without changing package metadata, and does not claim the npm CLI automatically loads a project `.env`.
- [x] Both new SVGs are valid, GitHub-safe, readable at 900px, and structurally understandable at 360px with adjacent Markdown preserving every essential detail.
- [x] No secret value, private Bilibili data, runtime behavior change, version bump, or publication action is introduced.
- [x] npm package dry-run contains all four README SVGs and excludes internal task, QA, memory, source, and test paths.

## Verification

```powershell
python C:\Users\ZX\.agents\skills\beautify-github-readme\scripts\audit_readme.py README.md
python C:\Users\ZX\.agents\skills\beautify-github-readme\scripts\audit_readme.py README_EN.md
npm pack --dry-run --json --ignore-scripts
git diff --check
```

Manual checks:

- Render all four SVGs at 900px and 360px.
- Check local links, bilingual structure, UTF-8, SVG safety, and high-confidence credential patterns.
- Confirm every current MCP tool and CLI state boundary is represented accurately.
- Confirm `npm view @xzxzzx/bilibili-mcp version` remains a release boundary rather than a reason to publish this documentation alone.

## Stop And Report Conditions

Stop if the work requires changing runtime behavior, inventing a universal MCP-client config, exposing credentials, rebuilding the Hero, adding a dependency, resolving package engine metadata, or publishing any artifact.

## User Comprehension Acceptance Addendum

The user clarified that the README must independently serve three readers:

1. An Agent reading the README must know how to install safely and when to hand control back to the user.
2. A person installing manually must be able to complete every step without guessing what a Bilibili credential field is or mistaking an MCP tool for a shell command.
3. A first-time visitor must quickly understand what the project does, what evidence it returns, and what it deliberately does not do.

Additional acceptance criteria:

- [x] The opening uses plain language before `stdio`, `MCP`, and `BVID` jargon.
- [x] The install section has two explicit paths: Agent-assisted and manual.
- [x] The Agent path includes a copyable prompt that requires client detection, forbids guessing the client format, forbids collecting Cookie values, pauses for the user to run interactive setup in their own terminal, handles reconnect handoff, and performs live MCP validation.
- [x] The manual path includes Node/npm verification commands, the official Node.js entry link, server name/command/args, a direct link to the matching client section, local credential setup, reconnect, and a copyable MCP-client verification prompt.
- [x] `check_bilibili_credentials` is explicitly identified as an MCP tool used inside the connected client, not a PowerShell/shell command.
- [x] The canonical setup guides explain how to locate only `SESSDATA`, `bili_jct`, and `DedeUserID` in the user's own logged-in Chrome/Edge or Firefox session and warn that the values must only be pasted into local hidden terminal input.
- [x] The local config location and lack of an operating-system-level encryption guarantee are visible near credential setup.
- [x] A compact failure map covers missing/unloadable credentials, live login failure, and MCP reconnect/configuration failure.
- [x] Chinese and English remain equivalent and natural.
- [x] The npm release gate remains explicit in the implementation report: current public `1.10.1` lacks `setup`/`doctor`, so docs and CLI must ship together.

## Information Architecture Acceptance Addendum

The user corrected the final story order: the README must introduce the project and its basic capabilities before any one workflow or installation procedure. Strong real use cases should remain prominent, but they must support the product overview rather than replace it.

- [x] The first screen states what the project is and names its broad content capabilities.
- [x] A compact core-capability overview appears before examples and installation.
- [x] Three prominent examples cover Favorites traversal, topic search, and transcript keyword-to-timestamp lookup.
- [x] The existing Favorites SVG is reused under the matching example instead of defining the whole project opening.
- [x] The Favorites example says traversal is best effort, lists successfully read rows, and reports `skipped_count`.
- [x] The English transcript example uses the verified literal keyword `函数` rather than implying translation.
- [x] Agent/manual installation, ten-tool coverage, limits, and security content remain intact.

## DeepSeek Logic Rewrite Round

The user explicitly requested DeepSeek to write the next revision after finding the current presentation still illogical.

- [x] The first paragraph explains the user outcome before protocol jargon.
- [x] Section transitions form one continuous path from project value to capabilities, proof, installation, detail, and boundaries.
- [x] High-value uses are prominent without making Favorites the whole project identity.
- [x] High-level capability copy does not duplicate the ten-tool table.
- [x] Both accepted installation journeys and safety boundaries remain complete.
- [x] Chinese and English read naturally and convey equivalent claims.
- [x] Independent Codex review finds no factual or narrative blocker.

## DeepSeek Logic Rewrite Round 2

The user rejected the first DeepSeek result and requested another rewrite.

- [x] Opening is two short grammatical sentences with no protocol or identifier jargon.
- [x] Core features are three product outcomes: browse Favorites, search by topic, and explore a selected video.
- [x] Installation appears before detailed usage examples.
- [x] Complete Agent and manual paths remain self-contained without dominating the page.
- [x] Three high-value prompts remain visually prominent after installation.
- [x] The ten-tool table maps names without duplicating the core-feature prose.
- [x] Independent review finds the result clearer than the first DeepSeek draft and factually complete.

## DeepSeek Reader-First Repair Round 3

- [x] Node.js 20+ and the four-step install path are visible before collapsed detail.
- [x] Configuration and verification no longer compete with product capabilities in the core-feature section.
- [x] Chinese prose avoids unnecessary `Folder`/`MCP server` jargon and explains `BVID` at first use.
- [x] English headings and multi-part/Favorites terminology read naturally.
- [x] `skipped_count` is limited to invalid video entries on the current Favorites page.
- [x] Comment documentation distinguishes the requested hot/time page from the final timestamp/likes prioritization.
- [x] Two independent final reviews report no narrative or factual blocker.
