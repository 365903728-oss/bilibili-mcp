# Research Note: Bilibili MCP Peer Projects

## Research Topic

- Topic: Current Bilibili MCP and Agent projects as product and implementation references
- Date: 2026-09-04
- Owner: Codex
- Related task, PRD, ticket, or plan: `ROADMAP.md` reference projects and P2 Bilibili-native candidates
- Refresh before: promoting QR login, danmaku, Watch Later, or official Open Platform access into a PRD or GitHub Issue

## Question

Which currently discoverable Bilibili MCP or Agent projects add useful patterns beyond the peers reviewed on 2026-07-20, and what value, boundary changes, and risks would each pattern bring to this project?

## Context

Why this matters for `@xzxzzx/bilibili-mcp`:

- The checked worktree already covers credential guidance, login status, package freshness, video context, transcripts, metadata, Chapters, comments, Video search, and current-account Favorites.
- The user asked to search live GitHub and AgentKey/Exa results for additional projects, with particular interest in Bilibili QR login.

What decision or implementation this may affect:

- Reference-project coverage and candidate prioritization only. This note and the roadmap entry do not authorize a new MCP tool, implementation, dependency, commit, push, or release.

## Search Coverage

- GitHub CLI repository searches: `bilibili mcp`, `bilibili agent`, `B站 AI agent`, `bilibili MCP qrcode`, `bilibili transcript MCP`, `bilibili comments MCP`, and `bilibili favorites MCP`.
- AgentKey used the Exa Web search provider for `site:github.com Bilibili MCP server AI agent subtitles comments favorites QR login open source 2026`.
- The July peer review already covered `34892002/bilibili-mcp-js`, `adoresever/bilibili-mcp`, `huccihuang/bilibili-mcp-server`, and `222wcnm/BiliStalkerMCP`; they were not re-added as new findings.

## Sources

| Source | Type | Date checked | Notes |
|--------|------|--------------|-------|
| [Yotsuki2213/BiliBili_VideoRead_MCP at `5ba31d0`](https://github.com/Yotsuki2213/BiliBili_VideoRead_MCP/tree/5ba31d0f2004cf2073f03e10118f0485d15bb92e) | source and README | 2026-09-04 | Terminal QR login, credential validation, structured transcript/comment output, segmented danmaku parsing, bounded sampling, and tests |
| [`auth.py` QR flow](https://github.com/Yotsuki2213/BiliBili_VideoRead_MCP/blob/5ba31d0f2004cf2073f03e10118f0485d15bb92e/src/videoread_mcp/auth.py) | source | 2026-09-04 | First-party passport Web endpoints, terminal QR rendering, polling, Cookie extraction, `/nav` validation, and local persistence |
| [`danmaku.py`](https://github.com/Yotsuki2213/BiliBili_VideoRead_MCP/blob/5ba31d0f2004cf2073f03e10118f0485d15bb92e/src/videoread_mcp/danmaku.py) | source | 2026-09-04 | Segmented danmaku retrieval, minimal protobuf parsing, time ordering, and uniform sampling |
| [Iseenope/bilibili-mcp-server at `20eedd0`](https://github.com/Iseenope/bilibili-mcp-server/tree/20eedd09862aea2c160163007f45221c544651b2) | source and README | 2026-09-04 | Broad 31-tool surface including QR login, refresh, danmaku, live keyframes, downloads, and account write operations |
| [`login.ts`](https://github.com/Iseenope/bilibili-mcp-server/blob/20eedd09862aea2c160163007f45221c544651b2/src/api/login.ts) and [`config.ts`](https://github.com/Iseenope/bilibili-mcp-server/blob/20eedd09862aea2c160163007f45221c544651b2/src/config.ts) | source | 2026-09-04 | QR polling and Cookie extraction; also exposes gaps between the advertised refresh behavior and the inspected persistence path |
| [Ghpt6/bilibili-subtitle at `1ad6114`](https://github.com/Ghpt6/bilibili-subtitle/tree/1ad6114861255e9159e99c8b01c867e068c16dc7) | source and README | 2026-09-04 | Subtitle tracks, comments, read-only Watch Later listing, destructive Watch Later mutations, and Windows browser-Cookie import |
| [sandraschi/bilibili-mcp at `b53db5a`](https://github.com/sandraschi/bilibili-mcp/tree/b53db5afbd3151735415293ed03ee35ca08fec0d) | source and README | 2026-09-04 | Explicit anonymous versus account capability tiers, discovery prompts, transcripts, Favorites, and a separate HTTP/Web UI surface |
| [nameefef/bilibili-mcp at `f4339f5`](https://github.com/nameefef/bilibili-mcp/tree/f4339f5d24de105a9e873ea3f5909cd68a2a535b) | source and README | 2026-09-04 | OAuth access to the official Bilibili Open Platform, limited to the authorized user's OpenID, submissions, and scoped statistics |
| [DevinChen2014/bilibili-mcp at `2ebdc00`](https://github.com/DevinChen2014/bilibili-mcp/tree/2ebdc00e0bb0bbf402b0d64a365bf07a1b307966) | public connection metadata | 2026-09-04 | Hosted SocialDataX endpoint and tool card; implementation is private and requires a remote API key |
| [`2026-07-20-bilibili-mcp-feature-opportunities.md`](./2026-07-20-bilibili-mcp-feature-opportunities.md) | prior research note | 2026-09-04 | Baseline peer scan and the earlier decision not to prioritize QR login without stronger evidence or user demand |

## Findings

### 1. QR login is now the strongest onboarding candidate

- `BiliBili_VideoRead_MCP` provides the closest fit for this project: a CLI `login/status/logout` flow generates a terminal QR code, polls Bilibili's first-party passport Web endpoints, extracts `SESSDATA`, `bili_jct`, and `DedeUserID`, validates the result with `/x/web-interface/nav`, then saves it locally.
- The useful pattern is the CLI flow and validation order, not a copy of its storage. Its Windows `auth.json` is plaintext, while this project should continue through its existing `CredentialManager` and preserve the rule that secrets never enter MCP results, Agent chat, logs, tests, or client configuration.
- The passport QR endpoints are first-party but not treated here as a documented stable Open Platform contract. A future implementation must keep manual Cookie entry as a fallback and classify endpoint drift separately from invalid user credentials.
- `Iseenope/bilibili-mcp-server` demonstrates an alternative two-tool MCP flow, but it is not the preferred baseline. At the inspected commit the tool description promises a Base64 QR image while the handler returns only a text URL; the login path receives a `refresh_token`, but `updateCookie()` does not persist it and `getRefreshToken()` still reads configuration/environment state. Its advertised automatic refresh therefore requires fresh verification before reuse.
- Compared with the earlier browser-CDP pattern in VideoToNote, direct terminal QR login avoids launching and debugging a local browser. Browser-assisted login remains a fallback design if Bilibili's Web QR endpoints become unusable.

### 2. Bounded, time-aligned danmaku is the clearest new content tool

- Danmaku adds a Bilibili-native, playback-aligned audience signal that ordinary comments do not provide.
- `BiliBili_VideoRead_MCP` shows a small implementation shape: retrieve segmented danmaku, parse only the needed fields, sort by playback time, and uniformly sample when a limit is exceeded.
- Its default limit of 2,000 is too large for this project's token-conscious MCP responses. Any future candidate should require a small bounded limit and support a time range and optional text query, reusing existing transcript-style validation and evidence positioning where possible.

### 3. Watch Later has distinct read and write choices

- `Ghpt6/bilibili-subtitle` exposes a read-only Watch Later list alongside remove-one and clear-all operations.
- A bounded read-only Watch Later entry point could complement Favorites for a common temporary queue. Removal and especially clear-all are destructive account writes that would change the current read-only boundary and therefore need a separate product and safety decision.
- Its browser-Cookie import is Windows-specific, writes an `.env` file, and expects a separately authorized DevTools session. It is less direct than terminal QR login for this project's onboarding path.

### 4. Capability tiers and the official platform are boundary references

- `sandraschi/bilibili-mcp` clearly separates anonymous discovery/video access from a logged-in account tier. Its explicit capability matrix and error guidance are directly reusable references; its HTTP/Web UI and in-server summarization surface represent additional product-shape candidates.
- `nameefef/bilibili-mcp` uses official Open Platform OAuth and scopes. This is a stronger compliance boundary, but it can read only the authorizing user's scoped identity, submissions, and statistics; it is not a replacement for arbitrary public-video transcripts, comments, search, or Favorites.

### 5. Large or hosted surfaces represent broader product choices

- `Iseenope/bilibili-mcp-server` is useful as an inventory, but its commenting, deleting, liking, following, danmaku sending, downloading, and account-management actions materially expand side effects and credential risk.
- The SocialDataX repository publishes connection metadata rather than the implementation, requires a remote API key, and routes work through a hosted service. It is not a code-learning source for this local-first package.
- Bilibili RAG/chat projects and automated creator-operation Agents may duplicate reasoning or introduce persistent stores and irreversible actions. They remain candidates, but need separate requirements, cost, storage, and account-safety decisions before ranking.

## Applicability To This Project

Candidate roadmap applications:

1. Evaluate local CLI QR login inside `setup`, with manual Cookie entry retained as fallback and live login validation before saving.
2. Keep a bounded read-only danmaku tool as the strongest new content candidate after the current active work.
3. Consider bounded read-only Watch Later listing only after QR login and danmaku have real user demand or an approved ticket.
4. Make anonymous versus authenticated capabilities explicit in setup/status documentation and structured errors.
5. Keep official Open Platform OAuth as a separate future adapter question for creator-owned workflows, not as a replacement transport.

Requires separate product decisions:

- Automatic comments, replies, likes, follows, danmaku sending, uploads, destructive Watch Later actions, or other account writes.
- Video downloading, live-stream screenshot analysis, cross-platform media support, built-in RAG, embedded LLM summarization, or a new local HTTP/Web UI.

Security and evidence rules that still apply:

- Sending Bilibili Cookie values to hosted MCP services or returning credentials through MCP tools.
- Copying implementations without revalidating endpoint behavior, license obligations, error semantics, secret storage, and package/runtime impact.

## Decision Impact

Recommended project action:

- Promote CLI QR login from a reference-only idea to a high-priority P2 candidate, still inactive until a dedicated requirements pass and user authorization.
- Retain compact danmaku and read-only Watch Later as lower-priority Bilibili-native candidates.
- Use the peer scan as evidence for the roadmap. Any implementation or broader product direction remains a separate user decision.

Rules or files that may need updates if a candidate is later approved:

- QR login: credential PRD/ticket, `src/cli.ts`, `src/utils/credentials.ts`, secret-oriented tests, bilingual setup documentation, QA checklist, and package contents.
- Danmaku or Watch Later: tool schemas/handlers, a focused Bilibili module, validation/sanitization, deterministic tests, bilingual tool reference, and changelogs.

## Risks And Unknowns

- Bilibili Web endpoints can change or trigger risk controls; source presence in another repository is not stability evidence.
- QR login introduces short-lived login keys, polling, terminal rendering compatibility, credential persistence, expiry, cancellation, and redaction requirements.
- Automatic Cookie refresh is more sensitive and less well verified than first-time QR login. Keep it as a separate candidate requiring its own specification and tests.
- Danmaku volume can exceed MCP response budgets; compact limits and filtering are required before public-tool design.
- No candidate repository was installed or run, and no real account, Cookie, QR confirmation, write operation, or bulk request was used during this research.

## Staleness Notes

Refresh this research when:

- a candidate is promoted into a PRD, GitHub Issue, or Codex-to-Claude handoff
- Bilibili passport login, danmaku, Watch Later, or Open Platform behavior is used in an implementation decision
- any cited repository changes materially or the review is more than 60 days old

## Follow-Up

- [ ] If the user activates QR login, run a short requirements pass that freezes CLI-only versus MCP-visible UX, storage, fallback, cancellation, and validation behavior before implementation.
- [ ] If danmaku is activated, verify the live segmented response and define a token-bounded result contract before adding a public tool.
