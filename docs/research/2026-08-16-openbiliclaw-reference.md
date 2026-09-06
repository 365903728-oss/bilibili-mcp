# Research Note: OpenBiliClaw Reference Project

## Research Topic

- Topic: OpenBiliClaw as product inspiration for `@xzxzzx/bilibili-mcp`
- Date: 2026-08-16
- Owner: Codex
- Related task, PRD, ticket, or plan: `ROADMAP.md` reference projects
- Refresh before: any installation, specification, dependency adoption, or implementation decision

## Question

What does OpenBiliClaw currently implement, and which product ideas are useful references without changing `bilibili-mcp` into a cross-platform recommendation system?

## Context

Why this matters for `@xzxzzx/bilibili-mcp`:

- The user identified OpenBiliClaw as a useful reference for user-directed content discovery, explainable recommendations, and local-first data handling.

What decision or implementation this may affect:

- Product-language and UX inspiration only. This note does not authorize installation, specification, planning, or implementation.

## Sources

| Source | Type | Date checked | Notes |
|--------|------|--------------|-------|
| [whiteguo233/OpenBiliClaw](https://github.com/whiteguo233/OpenBiliClaw) | official source and README | 2026-08-16 | Repository description, MIT license, supported platforms, local SQLite claim, user-model design, recommendation explanations, installation surfaces, and current release links |
| [OpenBiliClaw v0.3.207](https://github.com/whiteguo233/OpenBiliClaw/releases/tag/openbiliclaw-v0.3.207) | official release | 2026-08-16 | Latest release reported by the repository at review time |
| [whiteguo233/dsh-openbiliclaw](https://github.com/whiteguo233/dsh-openbiliclaw) | official plugin source | 2026-08-16 | Separate DSH client plugin; repository license is BSD-3-Clause |
| [Pinned DSH plugin commit](https://github.com/whiteguo233/dsh-openbiliclaw/commit/5cde8b54a628777ae1c7fa153ea90a61d0b91136) | official source commit | 2026-08-16 | The user-supplied commit exists; commit message is `fix(client): proxy recommendation cover images` |
| [Chrome Web Store listing](https://chromewebstore.google.com/detail/openbiliclaw/cdfjfkdjjhdaccbldipkjhpibnfbiamg) | store listing linked by official README | 2026-08-16 | Link and extension ID are advertised by the main repository; direct store contents were not independently retrieved |
| [Bilibili space 222156](https://space.bilibili.com/222156) | user-supplied author link | 2026-08-16 | Author identity, real name, BIP participation, and “daily Star rank third” were not independently verified from a primary source |

## Findings

- The core repository describes a local-first content-discovery Agent spanning Bilibili, Xiaohongshu, Douyin, YouTube, X, Zhihu, Reddit, Weibo, additional communities, and the open Web.
- The product builds a five-level user model from behavior, feedback, and conversation, then uses it for active discovery and explainable recommendations.
- The README states that core behavior, recommendation, and conversation data are stored locally in SQLite. This should not be simplified to “nothing is uploaded”: the product can still call content platforms and user-selected external LLM providers with the user's API key.
- The main repository is MIT licensed. The separate DSH plugin is BSD-3-Clause, so “the whole integration is MIT” would be inaccurate.
- The repository separates the local backend from browser, Web/mobile, native Flutter, and DSH client surfaces. The DSH plugin advertises a dedicated UI area and Agent Bridge tools over the local API.
- At review time the main repository reported release `v0.3.207`; repository state and feature counts are fast-moving and must be refreshed before reuse.
- The user-supplied installation fragment ends in an incomplete shell redirection. It must not be treated as a runnable installation guide.

## Applicability To This Project

Applies:

- User-directed discovery is a useful product framing: let users or Agents state an information goal before searching.
- Explain why a result is relevant and preserve evidence that lets the user verify it.
- Keep private identifiers, credentials, and derived user context local and minimized.
- Separate core data capabilities from optional client or harness adapters.

Does not apply:

- Cross-platform crawling, a recommendation engine, psychological profiling, MBTI inference, five-layer persistent user memory, automated exploration, and a long-lived content library are outside the current `bilibili-mcp` boundary.
- OpenBiliClaw's installer, backend runtime, Chrome extension, and DSH plugin are not dependencies or approved integration targets.

## Decision Impact

Recommended project action:

- Keep OpenBiliClaw in `ROADMAP.md` as a reference project only. Reuse its user-agency, recommendation-explanation, and local-first principles where they fit existing Bilibili-native tools.

Rules or files that may need updates:

- None beyond the roadmap and this research note unless the user later advances a concrete idea.

## Risks And Unknowns

- Running a remotely fetched installation script, binding a local service to `0.0.0.0`, or adding a DSH plugin changes the machine and expands the local network/trust surface; none of these actions were performed.
- The supplied shell fragment is incomplete and should not be copied into project documentation.
- Claims about the author's real name, BIP participation, Bilibili identity, and daily Star ranking remain user-provided context rather than verified facts.
- “Local-first” does not mean every network interaction stays local; platform requests and configured LLM providers still require a separate privacy review.

## Staleness Notes

Refresh this research when:

- OpenBiliClaw is considered for installation or integration
- its architecture, license, DSH plugin, browser extension, or data-flow claims affect a new project decision
- a concrete idea is promoted into a PRD or GitHub Issue

## Follow-Up

- [ ] If the user later advances a specific idea, compare it with the existing Bilibili-native tool boundary before writing a PRD.
