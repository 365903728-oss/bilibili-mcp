<p align="center">
  <img src="./assets/readme/hero-en.svg" width="100%" alt="Bilibili MCP: from video discovery to timestamped transcript evidence">
</p>

# Bilibili MCP

<p align="center">
  <a href="https://www.npmjs.com/package/@xzxzzx/bilibili-mcp"><img src="https://img.shields.io/npm/v/@xzxzzx/bilibili-mcp.svg" alt="npm version"></a>
  <a href="https://www.npmjs.com/package/@xzxzzx/bilibili-mcp"><img src="https://img.shields.io/npm/dm/@xzxzzx/bilibili-mcp.svg" alt="npm downloads"></a>
  <a href="https://www.gnu.org/licenses/gpl-3.0"><img src="https://img.shields.io/badge/License-GPLv3-blue.svg" alt="GPL-3.0 license"></a>
</p>

<p align="center">
  Search Bilibili or read the current account's Favorite Folders from Codex, Claude, Cursor, and other AI clients, then retrieve transcripts, timestamps, metadata, chapters, and popular comments.
</p>

<p align="center">
  <a href="./README.md">简体中文</a> ·
  <a href="./docs/client-setup.en.md">All agent / client setups</a> ·
  <a href="./docs/tool-reference.en.md">Tool reference</a> ·
  <a href="./CHANGELOG_EN.md">Changelog</a> ·
  <a href="https://www.npmjs.com/package/@xzxzzx/bilibili-mcp">npm</a> ·
  <a href="https://github.com/XZXZZX-Ai/bilibili-mcp/releases/latest">Latest release</a>
</p>

> [!NOTE]
> **Verified workflow:** search → select Part 4 of `BV1Eb411u7Fw` → search its transcript for “函数” → receive bounded context and a direct [`?p=4&t=1.12`](https://www.bilibili.com/video/BV1Eb411u7Fw/?p=4&t=1.12) evidence link. Successful search and transcript calls provide both compatible text and MCP `structuredContent`.

## ⚡ Installation and configuration

The copyable Agent prompt, every client configuration location, CLI / JSON / TOML examples, Cookie setup, and login-verification flow are centralized in:

### [Open the complete Agent / client installation guide →](./docs/client-setup.en.md)

> [!IMPORTANT]
> This README no longer duplicates installation or configuration methods. Treat the installation guide as the complete source.

After installation, ask your AI client:

```text
Search Bilibili for an introductory MCP video, select one candidate,
then find “tool call” in its transcript and give me a timestamp link.
```

## 🧰 Tool overview

| Goal | Tool | What it returns |
|---|---|---|
| Start with a topic, not a video URL | `search_bilibili_videos` | Up to 10 normal-video candidates with reusable BVIDs |
| Start from my Bilibili Favorites | `list_bilibili_favorite_videos` | One bounded page of videos from the current account's created Favorite Folders; follow `next_cursor` until it is absent |
| Get a transcript or locate a keyword | `get_video_transcript` | Text, language, timestamps, range filters, keyword context, and evidence links |
| Ask AI to summarize a video | `get_video_info` | Subtitles first; title, description, and tags when subtitles are unavailable |
| Inspect structured video information | `get_video_metadata` | Title, creator, duration, publish time, tags, statistics, and multi-Part listing |
| Read video chapters | `get_video_chapters` | Creator- or platform-defined chapter titles and time ranges |
| Inspect viewer feedback | `get_video_comments` | Popular comments, timestamped comments, and optional replies |
| Get safe credential instructions | `get_credential_setup_instructions` | Local setup commands and bilingual security notes |
| Check login credentials | `check_bilibili_credentials` | Source, login status, and recovery steps without Cookie values |
| Check for package updates | `check_mcp_update` | Current/latest versions and safe update commands |

See the [tool reference](./docs/tool-reference.en.md) for complete parameters, JSON examples, structured errors, and request controls.

### Key capabilities

- **Discover, then inspect:** search by topic, or page through the current account's Favorite Folders, then pass a returned BVID to transcript, metadata, chapter, or comment tools.
- **Verifiable transcript evidence:** select a Part and language, include timestamps, filter time ranges, or search with bounded context; each match can include a direct `timestamp_url`.
- **Structured output:** successful video search, transcript, and Favorites-page calls provide compatible text plus MCP `structuredContent`.
- **Explicit failures:** distinguish expired credentials, missing subtitles, access restrictions, rate limits, timeouts, and other API errors, with actionable recovery steps.
- **Credential-safe helpers:** status checks never return `SESSDATA`, `bili_jct`, `DedeUserID`, or a complete Cookie.

## 🧭 Behavior boundaries

- Video search requires a configured, valid Bilibili login Cookie and does not fall back to anonymous search.
- Favorites discovery requires the current logged-in account identity, returns at most one upstream 20-row resource page per call, and the `next_cursor` is a stateless, versioned opaque token that encodes only the next Folder and page number — never Cookie values, account IDs, Folder titles, or Video data.
- `get_video_transcript` returns `SUBTITLE_UNAVAILABLE` by default when no subtitle exists; it falls back to the description only when `fallback_to_description: true` is explicit.
- Timestamp output, time-range filtering, and keyword search never silently fall back to a description.
- Chapters come from Bilibili creator/platform data. The tool returns an empty list when no chapter data exists; it does not infer chapters.
- This project does not bypass paid, member-only, regional, private, removed, or other access restrictions.
- Requests originate on the user's machine. This is a third-party project, not an official Bilibili service.

## 🛠️ Development

Source-development setup is also centralized in the [complete installation guide: develop from source](./docs/client-setup.en.md#develop-from-source).

| Command | Purpose |
|---|---|
| `npm run build` | Clean and compile TypeScript into `dist/` |
| `npm test` | Run the Vitest suite |
| `npm run watch` | Watch TypeScript sources |
| `npm start` | Start the built stdio MCP server |
| `npm pack --dry-run` | Inspect npm package contents |

MCP stdio protocol data uses `stdout`; diagnostics must go to `stderr`. Never use real Cookie values in tests or logs.

## ⚖️ Safety and license

- Follow Bilibili's terms, interface-access rules, and applicable law. Do not use this project for bulk scraping, commercial exploitation, permission bypass, or other abuse.
- High request volume, unusual access patterns, or leaked Cookies may trigger throttling, risk controls, or account issues. Users accept those risks.
- The project sends Bilibili credentials only to official Bilibili interfaces and does not upload Cookies to third-party services. Local credential files do not promise operating-system-level encryption.
- This project is licensed under the [GNU General Public License v3.0](./LICENSE).

## 💬 Feedback

For bugs and feature requests, open a [GitHub Issue](https://github.com/XZXZZX-Ai/bilibili-mcp/issues). Use [GitHub Discussions](https://github.com/XZXZZX-Ai/bilibili-mcp/discussions) for general questions.
