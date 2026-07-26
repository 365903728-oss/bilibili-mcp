# Bilibili MCP Tool

[![npm version](https://img.shields.io/npm/v/@xzxzzx/bilibili-mcp.svg)](https://www.npmjs.com/package/@xzxzzx/bilibili-mcp)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![npm downloads](https://img.shields.io/npm/dm/@xzxzzx/bilibili-mcp.svg)](https://www.npmjs.com/package/@xzxzzx/bilibili-mcp)

MCP server that gives AI clients access to Bilibili video subtitles, transcripts, metadata, and popular comments.

View in [简体中文](https://github.com/XZXZZX-Ai/bilibili-mcp/blob/master/README.md) · 📜 [Changelog](https://github.com/XZXZZX-Ai/bilibili-mcp/blob/master/CHANGELOG_EN.md) · 📦 [npm](https://www.npmjs.com/package/@xzxzzx/bilibili-mcp) · 🚀 [Release v1.8.0](https://github.com/XZXZZX-Ai/bilibili-mcp/releases/tag/v1.8.0)

> [!TIP]
> ⚠️ You can copy the "Install With Your Agent" prompt below to Codex, Claude Code, Cursor, or another agent and let it add this MCP server to your client and guide Cookie setup. For reliable subtitles, transcripts, and comments, you still need to configure Bilibili Cookies after installation; do not write Cookies into MCP client config. Metadata may work without cookies. See [**Credential Configuration**](#-credential-configuration).

---

## ⚡ Quick Start

Choose your AI client and jump directly to the detailed setup instructions:

### Install With Your Agent

If you use an agent-based tool such as Codex, Claude Code, Cursor, Qoder, Kimi Code, Antigravity, Windsurf, or Cline, copy the prompt below to your agent. Ask it to find the matching client setup section in this README and write the MCP config for that client:

```text
Please help me install the Bilibili MCP server: @xzxzzx/bilibili-mcp.

First go to https://github.com/XZXZZX-Ai/bilibili-mcp and read the project's README, especially the "Quick Start" and "Client Setup" sections. Find the MCP setup method that matches my current agent/client, then add this server in that client's official configuration location.

MCP server config requirements:
- server name: bilibili-mcp
- command: npx
- args: ["-y", "@xzxzzx/bilibili-mcp@latest"]

Do not write real Bilibili Cookie values into MCP client config files, client-config env fields, args, or chat messages.
After adding the MCP server, continue guiding me to run the commands below. They save Cookies to the local credential config; the MCP server will read those credentials automatically when it starts:

npx -y @xzxzzx/bilibili-mcp@latest config
npx -y @xzxzzx/bilibili-mcp@latest check

After the MCP server is connected, if available, call get_credential_setup_instructions, check_bilibili_credentials, or check_mcp_update to confirm Cookie setup and package freshness.
```

- [Codex app / Codex CLI](#codex-app--codex-cli)
- [Claude Code](#claude-code)
- [Claude Desktop](#claude-desktop)
- [OpenCode](#opencode)
- [OpenClaw](#openclaw)
- [Hermes](#hermes)
- [WorkBuddy](#workbuddy)
- [CodeBuddy](#codebuddy)
- [Trae CN](#trae-cn)
- [Trae International](#trae-international)
- [Trae SOLO CN](#trae-solo-cn)
- [Trae SOLO International](#trae-solo-international)
- [Qoder IDE / Qoder CLI / QoderWork](#qoder-ide--qoder-cli--qoderwork)
- [Kimi Code / Kimi Code CLI](#kimi-code--kimi-code-cli)
- [Antigravity / Antigravity CLI](#antigravity--antigravity-cli)
- [Pi](#pi)
- [Oh My Pi](#oh-my-pi)
- [Crush](#crush)
- [DeepSeek-TUI](#deepseek-tui)
- [Deep Code](#deep-code)
- [Reasonix](#reasonix)
- [GitHub Copilot CLI](#github-copilot-cli)
- [Cursor](#cursor)
- [Cline](#cline)
- [Kilo Code](#kilo-code)
- [VS Code](#vs-code)
- [GitHub Copilot (VS Code)](#github-copilot-vs-code)
- [Windsurf](#windsurf)
- [Zed](#zed)
- [Cherry Studio](#cherry-studio)
- [LobeHub / LobeChat](#lobehub--lobechat)
- [AstrBot](#astrbot)
- [nanobot](#nanobot)

---

## 📑 Table of Contents

- [⚡ Quick Start](#-quick-start)
- [🌟 Features](#-features)
  - [1. Video Summarization (`get_video_info`)](#1-video-summarization-get_video_info)
  - [2. Comment Summarization (`get_video_comments`)](#2-comment-summarization-get_video_comments)
  - [3. Video Transcript (`get_video_transcript`)](#3-video-transcript-get_video_transcript)
  - [4. Video Metadata (`get_video_metadata`)](#4-video-metadata-get_video_metadata)
  - [5. Video Chapters (`get_video_chapters`)](#5-video-chapters-get_video_chapters)
  - [6. Credential Helper Tools](#6-credential-helper-tools)
  - [7. Behavior and Error Handling](#7-behavior-and-error-handling)
- [📋 Requirements](#-requirements)
- [🚀 Client Setup](#-client-setup)
- [⚙️ Credential Configuration](#-credential-configuration)
- [🧭 Which tool should I use?](#-which-tool-should-i-use)
- [💡 Tool Call Examples](#-tool-call-examples)
- [🛡️ API Rate Limiting](#️-api-rate-limiting)
- [🛠️ Development Guide](#️-development-guide)
- [⚖️ Safety & Disclaimer](#️-safety--disclaimer)
- [💬 Feedback & Suggestions](#-feedback--suggestions)

---

## 🌟 Features

### 1. Video Summarization (`get_video_info`)
- Prioritizes retrieving CC or AI subtitles.
- Automatically falls back to video title, description, and tags if no subtitles are available.
- Supports multi-language subtitle selection (defaults to Simplified Chinese).
- Supports manual preference for subtitle languages (e.g., `en`, `zh-Hant`).

### 2. Comment Summarization (`get_video_comments`)
- Retrieves popular comments to help gauge video sentiment.
- Filters emoji placeholders (e.g., `[doge]`) for cleaner text.
- Prioritizes comments with timestamps (e.g., `05:20`) for quick highlight location.
- Supports two levels of detail:
  - `brief`: 10 popular comments summary.
  - `detailed`: 20 popular comments + high-quality replies.
- Optional parameters:
  - `limit`: Explicit comment count `1-50`, overrides `detail_level` default.
  - `sort`: Sort order `"hot"` (default) or `"time"`.
  - `include_replies`: Whether to include top replies (default `true`).

### 3. Video Transcript (`get_video_transcript`)
- Returns clean subtitle text, joined by newlines.
- Supports preferred language selection (defaults to `zh-Hans` > `ai-zh` > `zh-CN` > `zh-Hant` > `en` priority).
- Supports multi-Part selection, timestamp output, time-range filtering, and optional keyword search.
- Successful calls return both the backward-compatible formatted JSON text and the same data as MCP `structuredContent`.
- Optional parameters:
  - `preferred_lang`: Preferred subtitle language code.
  - `fallback_to_description`: Fall back to video description if subtitles unavailable (default `false`).
  - `page`: Multi-Part video page number (1-based positive integer).
  - `include_timestamps`: Prefix each line with `[HH:MM:SS --> HH:MM:SS]`.
  - `start_seconds` / `end_seconds`: Only return segments overlapping this range.
  - `query`: Keyword search term (max 100 chars, case-insensitive literal matching).
  - `max_matches`: Maximum matches to return (1-20, default 10).
  - `context_segments`: Context segments per match side (0-5, default 1).
- By default, returns `SUBTITLE_UNAVAILABLE` error when no subtitles exist.
- Timestamps/range filtering/keyword search is incompatible with description fallback.
- Cookie expiration always returns `COOKIE_EXPIRED`, never silently falls back.
- Evidence links:
  - Root `source_url` on every successful result: browser URL of the selected Part (multi-Part videos append `p=<page>`).
  - `timestamp_url` on each search `matches[]` item: same as `source_url` plus `t=<start_seconds>`, opening the player at the matched subtitle.

### 4. Video Metadata (`get_video_metadata`)
- Returns video title, author, duration, publish date, description, tags, and stats (views, likes, coins, etc.).
- Returns multi-Part listing (`pages`) with page number, CID, title, and duration.
- Does not fetch subtitles or comments.

### 5. Video Chapters (`get_video_chapters`)
- Returns Bilibili creator-defined Chapter intervals (view_points) with title, start, and end seconds.
- Returns empty `chapters` array when no Chapters exist; never infers Chapters.
- Accepts optional `page` parameter for multi-Part videos.

### 6. Credential Helper Tools

- `get_credential_setup_instructions`: Returns safe setup commands for Bilibili Cookie configuration. AI agents installing this MCP can call this tool to guide users through setup.
- `check_bilibili_credentials`: Checks whether credentials are configured and logged in without returning Cookie values. Returns next steps when credentials are missing or invalid.
- `check_mcp_update`: Checks the local package version against npm latest and returns safe update guidance for `npx @latest` or global installs.

### 7. Behavior and Error Handling

- **Intelligent Cookie Expiration Detection**: Automatically verifies login status when subtitles are empty, distinguishing between "videos without subtitles" and "invalid credentials," and throwing a clear `COOKIE_EXPIRED` error to prevent silent degradation.

#### Without Cookie

- Some public video metadata (`get_video_metadata`) may work without authentication.
- Subtitles (`get_video_info`, `get_video_transcript`) may be unavailable, incomplete, or fail without authentication.
- Comments (`get_video_comments`) may be incomplete, empty, or rate-limited without authentication.
- Do not rely on cookie-less mode for reliable subtitle or comment access.

#### Credential Sources

- Credentials should be supplied via `.env` file, environment variables, or the credential helper.
- Supported environment variables: `BILIBILI_SESSDATA`, `BILIBILI_BILI_JCT`, `BILIBILI_DEDEUSERID`.
- **Never** hard-code Cookie values in source code, scripts, docs, tests, logs, or examples.
- If Cookie values were previously exposed in repository history, rotate them immediately via Bilibili account settings.

#### Expected Error Codes

All MCP tool error responses use a unified structured payload. The backward-compatible `error`, `message`, `code`, and `next_steps` fields remain, alongside explicit bilingual fields:

```json
{
  "error": true,
  "message": "Network request failed.",
  "message_en": "Network request failed.",
  "message_zh": "网络请求失败。",
  "code": "NETWORK_ERROR",
  "category": "network",
  "retryable": true,
  "user_action_required": false,
  "next_steps": ["Retry later.", "Check local network, proxy, firewall, or VPN settings if the problem repeats."],
  "next_steps_en": ["Retry later.", "Check local network, proxy, firewall, or VPN settings if the problem repeats."],
  "next_steps_zh": ["稍后重试。", "如果问题反复出现，请检查本机网络、代理、防火墙或 VPN 设置。"],
  "details": {
    "status_code": 503
  }
}
```

Field meaning:

- `error` / `message` / `code` / `next_steps`: backward-compatible fields; `next_steps` mirrors `next_steps_en`.
- `message_en` / `message_zh` / `next_steps_en` / `next_steps_zh`: explicit English and Chinese copies for clients that render by language.
- `category`: classification (`validation` / `credentials` / `content` / `network` / `access` / `rate_limit` / `api` / `unknown`).
- `retryable`: whether automatic retry is reasonable.
- `user_action_required`: whether the user must act before the call can succeed.
- `details`: optional metadata such as HTTP status, timeout in milliseconds, or Bilibili API code; never includes Cookie values or full URLs.

Supported error codes:

| Code | Meaning | Caller Action |
|------|---------|---------------|
| `VALIDATION_ERROR` | Invalid input parameter | Fix the `bvid_or_url` or other parameter |
| `COOKIE_EXPIRED` | Cookie expired or not logged in | User should refresh/rotate Bilibili credentials |
| `SUBTITLE_UNAVAILABLE` | No subtitles available for this video | For `get_video_transcript`, retry with `fallback_to_description: true` |
| `NETWORK_ERROR` | Network request failed (HTTP 5xx, connection errors, etc.) | Retry later; check network/proxy/firewall if it keeps happening |
| `NETWORK_TIMEOUT` | Request to Bilibili timed out | Retry later; check network/proxy/firewall if it keeps happening |
| `API_RATE_LIMITED` | Bilibili API rate limit hit (HTTP 429) | Wait and retry; reduce request frequency or raise `BILIBILI_RATE_LIMIT_MS` |
| `ACCESS_DENIED` | Bilibili denied access (permissions, private, region-locked, removed) | Verify the video access permissions; run the credential check if needed |
| `PAID_VIDEO` | Video may require payment, membership, or extra permissions | Confirm in Bilibili; this MCP will not bypass paid or restricted access |
| `COMMENTS_DISABLED` | Comments are disabled or restricted | Use transcript or metadata tools; confirm on the Bilibili page |
| `BILIBILI_API_ERROR` | Other Bilibili API errors | Retry if it looks temporary; include the code when reporting repeated issues |
| `UNKNOWN_ERROR` | Unknown failure | Retry later; never include Cookie values when reporting |

## 📋 Requirements

- **Node.js**: v18.0.0 or higher.
- Bilibili Account Credentials (Cookies).

---

## 🚀 Client Setup

> [!NOTE]
> Do not write real Cookie values in MCP client config files. Prefer `bilibili-mcp config` to save credentials to the local credential config, or provide environment variables in the runtime environment; the MCP server will read those credentials automatically when it starts. See [⚙️ Credential Configuration](#-credential-configuration).

> [!IMPORTANT]
> If you are an AI agent installing this MCP for a user: do not stop after writing the MCP client config. After adding the `bilibili-mcp` server, you must remind and guide the user to configure Bilibili Cookies separately. After connecting the MCP server, agents can also call `get_credential_setup_instructions`, `check_bilibili_credentials`, or `check_mcp_update` to guide the user.
>
> Recommended commands:
>
> ```bash
> npx -y @xzxzzx/bilibili-mcp@latest config
> npx -y @xzxzzx/bilibili-mcp@latest check
> ```
>
> For MCP client configuration, prefer `npx -y @xzxzzx/bilibili-mcp@latest` so new client sessions resolve the current npm release. Existing global installs must be updated manually with `npm install -g @xzxzzx/bilibili-mcp@latest`, or checked with `bilibili-mcp check-update`.
>
> If the package is already installed globally, use:
>
> ```bash
> bilibili-mcp config
> bilibili-mcp check
> ```
>
> `config` collects `SESSDATA`, `bili_jct`, and `DedeUserID`; `check` verifies that credentials can be loaded. Do not ask users to paste Cookie values into Claude, Cursor, Codex, Qoder, Kimi, or any other MCP client configuration file.

### Codex app / Codex CLI

Codex app, Codex CLI, and the Codex IDE extension share MCP configuration. Use either setup path:

#### Codex app

Open Settings → Integrations & MCP, then add a custom MCP server:

- Command: `npx`
- Arguments: `["-y", "@xzxzzx/bilibili-mcp@latest"]`

#### Codex CLI

```bash
codex mcp add bilibili-mcp -- npx -y @xzxzzx/bilibili-mcp@latest
```

After setup, run `/mcp` in the Codex CLI TUI to inspect server status.

#### Manual config

You can also edit Codex configuration directly:

- User-level: `~/.codex/config.toml`
- Project-level: `.codex/config.toml` (loaded only when Codex trusts the project)

```toml
[mcp_servers.bilibili-mcp]
command = "npx"
args = ["-y", "@xzxzzx/bilibili-mcp@latest"]
```

### Claude Code

```bash
claude mcp add bilibili-mcp -- npx -y @xzxzzx/bilibili-mcp@latest
```

This saves the server as a local MCP server for the current project by default. After setup, run `/mcp` inside Claude Code or `claude mcp list` in your terminal to check the connection.

To make it available across all projects, use user scope:

```bash
claude mcp add --scope user bilibili-mcp -- npx -y @xzxzzx/bilibili-mcp@latest
```

You can also edit `~/.claude.json` and add the same JSON block shown for Claude Desktop under the matching project or user configuration.

### Claude Desktop

Open Claude Desktop Settings → Developer → Edit Config, or edit directly:

- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

Add:

```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
    }
  }
}
```

Save the file, then restart Claude Desktop. This setup is for local stdio MCP servers; do not write real Cookie values in `env`, `args`, or the config file.

### OpenCode

Edit the OpenCode config file at `~/.config/opencode/opencode.json` and add this local MCP server under `mcp`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "bilibili-mcp": {
      "type": "local",
      "command": ["npx", "-y", "@xzxzzx/bilibili-mcp@latest"],
      "enabled": true
    }
  }
}
```

OpenCode adds MCP tools to the available tool context. When prompting, explicitly ask OpenCode to use `bilibili-mcp` if needed.

### OpenClaw

Register this server in OpenClaw's MCP registry:

```bash
openclaw mcp set bilibili-mcp '{"command":"npx","args":["-y","@xzxzzx/bilibili-mcp@latest"]}'
```

Check the registered server:

```bash
openclaw mcp list
openclaw mcp show bilibili-mcp
```

You can also add the same structure to your OpenClaw configuration:

```json
{
  "mcp": {
    "servers": {
      "bilibili-mcp": {
        "command": "npx",
        "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
      }
    }
  }
}
```

`openclaw mcp set` only writes the MCP server definition into OpenClaw's configuration. Whether a runtime enables it depends on your OpenClaw agent/runtime setup.

### Hermes

Edit `~/.hermes/config.yaml` and add this entry under `mcp_servers`:

```yaml
mcp_servers:
  bilibili-mcp:
    command: "npx"
    args: ["-y", "@xzxzzx/bilibili-mcp@latest"]
```

If you already have a Hermes session running, use `/reload-mcp` to reload MCP configuration, or start a fresh Hermes session.

### WorkBuddy

WorkBuddy's official docs recommend configuring MCP from the UI. Open Sidebar → Plugins → MCP Server → Configure MCP, then add:

```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
    }
  }
}
```

You can also edit the scoped config file:

- User scope: `~/.workbuddy/mcp.json`
- Project scope: `<project>/.workbuddy/mcp.json`

### CodeBuddy

#### Option 1: CodeBuddy CLI

CodeBuddy CLI can add this stdio MCP server directly:

```bash
codebuddy mcp add --scope user bilibili-mcp -- npx -y @xzxzzx/bilibili-mcp@latest
```

Check the registered server:

```bash
codebuddy mcp list
codebuddy mcp get bilibili-mcp
```

#### Option 2: CodeBuddy IDE

Open CodeBuddy Settings → MCP → Add MCP from the top-right of the IDE chat panel, then add:

```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"],
      "description": "Bilibili MCP server"
    }
  }
}
```

If you use project-level `.mcp.json`, make sure CodeBuddy settings allow this project MCP server to be enabled.

### Trae CN

In Trae CN, open the settings entry in the top-right of the AI chat window, then go to MCP configuration. You can also edit the MCP config file directly.

Common config paths:

- Windows: `%APPDATA%\Trae\User\settings\mcp.json`
- macOS: `~/Library/Application Support/Trae/User/settings/mcp.json`
- Project scope: `.trae/mcp.json`

Add:

```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
    }
  }
}
```

If you use project-level `.trae/mcp.json`, confirm project config import is enabled in Trae's MCP management panel.

### Trae International

In Trae International, open Settings → MCP from the top-right of the AI chat window, then choose Add or manually configure an MCP server.

For project-level configuration, create `.trae/mcp.json`:

```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
    }
  }
}
```

Trae supports stdio MCP servers; this project starts its stdio server with `npx`.

### Trae SOLO CN

Trae SOLO CN is the SOLO workflow for Trae China. Public official docs do not show a standalone SOLO-specific MCP config file; use Trae's project-level MCP config, then use the server from SOLO Coder.

Create `.trae/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
    }
  }
}
```

Then confirm project config import is enabled in Trae's MCP management panel and use this MCP server from SOLO Coder.

### Trae SOLO International

Trae SOLO International exists; the official FAQ says international SOLO is available to Pro users. I did not find a separate SOLO-specific MCP JSON format, so use Trae International's MCP setup and call it from SOLO Coder / Builder with MCP.

Project-level config also uses `.trae/mcp.json`:

```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
    }
  }
}
```

If using the Trae International UI, open Settings → MCP from the top-right of the AI chat window and add the same `mcpServers` configuration manually.

### Qoder IDE / Qoder CLI / QoderWork

Qoder has multiple surfaces, and each uses a slightly different MCP entry point: Qoder IDE configures MCP from settings, Qoder CLI uses `qodercli mcp`, and QoderWork adds servers from its MCP Servers page.

#### Qoder IDE

Open the top-right user icon → Qoder Settings → MCP. On the My Servers tab, click + Add, then add this local STDIO server:

```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
    }
  }
}
```

Qoder documents that Streamable HTTP can be configured like an SSE endpoint and auto-detected. This project is a local stdio server, so use the `command` / `args` setup above.

#### Qoder CLI

Qoder CLI can add this stdio MCP server directly:

```bash
qodercli mcp add bilibili-mcp -- npx -y @xzxzzx/bilibili-mcp@latest
```

Useful check:

```bash
qodercli mcp list
```

If Qoder CLI is already running, run `/mcp reload` in the session after adding or changing an MCP server. The default scope is local to the current project; use `-s user` for user-level config or `-s project` for project-level `.mcp.json`.

Common config files:

- User level: `~/.qoder/settings.json`
- Local project-specific: `.qoder/settings.local.json`
- Project-level shared: `.mcp.json`

#### QoderWork

Open QoderWork desktop app → Settings → MCP Servers, then click + Add.

The fastest path is Paste JSON Config:

```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
    }
  }
}
```

You can also choose Fill in Config Manually, set Server Type to STDIO, and enter:

- Server Name: `bilibili-mcp`
- Command: `npx -y @xzxzzx/bilibili-mcp@latest`

After adding it, confirm the server is enabled under Custom Servers and expand it to inspect available tools. Do not write real Cookie values in Qoder / QoderWork MCP config; configure credentials with `bilibili-mcp config` or environment variables.

### Kimi Code / Kimi Code CLI

Kimi Code CLI can act as an MCP client for local stdio servers. Current Kimi Code docs recommend declaring MCP servers in `mcp.json`:

- User level: `~/.kimi-code/mcp.json`
- Project level: `.kimi-code/mcp.json`

Add:

```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
    }
  }
}
```

Project-level `.kimi-code/mcp.json` applies only to the current repository and overrides a same-named user-level server. Inside Kimi Code CLI, use:

```text
/mcp
/mcp-config
```

`/mcp` shows server connection status and tools. `/mcp-config` opens the interactive MCP server manager for adding, editing, or deleting servers.

Legacy Kimi CLI docs also documented `kimi mcp add`; if your installed version still supports it, you can use:

```bash
kimi mcp add bilibili-mcp -- npx -y @xzxzzx/bilibili-mcp@latest
kimi mcp list
kimi mcp test bilibili-mcp
```

Do not write real Cookie values in Kimi Code `mcp.json`, `env`, or command arguments. Configure credentials with `bilibili-mcp config` or environment variables.

### Antigravity / Antigravity CLI

Gemini CLI has migrated to Antigravity CLI. New MCP setup no longer lives in `~/.gemini/settings.json`; Antigravity uses a standalone `mcp_config.json`.

In Antigravity IDE, open MCP Store → Manage MCP Servers → View raw config. In Antigravity CLI, use `/mcp` to manage MCP servers.

Common config paths:

- Antigravity IDE: `~/.gemini/antigravity/mcp_config.json`
- Antigravity CLI global: `~/.gemini/antigravity-cli/mcp_config.json`
- Antigravity CLI workspace: `.agents/mcp_config.json`

Add:

```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
    }
  }
}
```

After saving, restart Antigravity / Antigravity CLI, or use `/mcp` in the CLI to check whether the server is loaded.

### Pi

Pi uses MCP through `pi-mcp-adapter`. Install the adapter first:

```bash
pi install npm:pi-mcp-adapter
```

After restarting Pi, prefer project-level shared config:

```text
.mcp.json
```

Add:

```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
    }
  }
}
```

You can also use user-global shared config:

```text
~/.config/mcp/mcp.json
```

Pi also supports Pi-owned override files:

- Global: `~/.pi/agent/mcp.json`
- Project-level: `.pi/mcp.json`

If you already configured MCP in Cursor, Claude Code, Codex, Windsurf, or similar clients, run `/mcp setup` in Pi to import or scaffold configuration. From the terminal, you can also run:

```bash
pi-mcp-adapter init
```

Pi connects MCP servers lazily by default, so a server starts only when a tool is actually used. In Pi, run `/mcp` to inspect server status and available tools. Do not write real Cookie values in Pi MCP config; configure credentials with `bilibili-mcp config` or environment variables.

### Oh My Pi

Oh My Pi (`omp`) supports MCP natively. Prefer OMP-owned config files:

- Project-level: `.omp/mcp.json`
- User-level: `~/.omp/agent/mcp.json`

You can also use portable project-root config files shared by other MCP clients:

- `mcp.json`
- `.mcp.json`

Add:

```json
{
  "$schema": "https://raw.githubusercontent.com/can1357/oh-my-pi/main/packages/coding-agent/src/config/mcp-schema.json",
  "mcpServers": {
    "bilibili-mcp": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
    }
  }
}
```

You can also use guided setup from an OMP session:

```text
/mcp add
```

After changing config, use:

```text
/mcp reload
/mcp list
/mcp test bilibili-mcp
```

OMP supports `stdio`, `http`, and `sse` MCP. Do not write real Cookie values in `env`, `args`, or config files.

### Crush

Crush supports project-level and user-level JSON configuration. MCP servers live under the `mcp` object.

Config precedence:

- Project-level: `.crush.json`
- Project-level: `crush.json`
- User-level: `~/.config/crush/crush.json`

Add:

```json
{
  "$schema": "https://charm.land/crush.json",
  "mcp": {
    "bilibili-mcp": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
    }
  }
}
```

Crush also supports HTTP and SSE MCP. Do not put real Cookie values in `env` or `args`; configure credentials with this project's CLI wizard or environment variables.

### DeepSeek-TUI

DeepSeek-TUI is both an MCP client and an MCP server. As an MCP client, add this project with:

```bash
deepseek mcp add bilibili-mcp -- npx -y @xzxzzx/bilibili-mcp@latest
```

Or edit:

```text
~/.deepseek/mcp.json
```

Add:

```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
    }
  }
}
```

Use `deepseek mcp list` and `deepseek mcp validate` to check configuration. DeepSeek-TUI usually exposes MCP tools as `mcp_<server>_<tool>`.

### Deep Code

Deep Code configures MCP servers in `~/.deepcode/settings.json`. Add `bilibili-mcp` under `mcpServers`:

```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "command": "npx",
      "args": ["@xzxzzx/bilibili-mcp@latest"]
    }
  }
}
```

Deep Code documents that it automatically prepends `-y` when `command` is `npx`. After saving the config, start `deepcode` and run `/mcp` to inspect server status and available tools.

### Reasonix

Reasonix supports native MCP. The fastest setup is the `--mcp` flag:

```bash
npx reasonix code --mcp "bilibili=npx -y @xzxzzx/bilibili-mcp@latest"
```

You can also edit the global config:

```text
~/.reasonix/config.json
```

Add an entry to the `mcp` array:

```json
{
  "mcp": [
    "bilibili=npx -y @xzxzzx/bilibili-mcp@latest"
  ]
}
```

Reasonix uses `name=command arg1 arg2` strings. Project-level overrides live under `.reasonix/`.

### GitHub Copilot CLI

In GitHub Copilot CLI interactive mode, use `/mcp add`. Choose `STDIO` or `Local`, then fill in:

- Server Name: `bilibili-mcp`
- Command: `npx`
- Args: `-y @xzxzzx/bilibili-mcp`

You can also edit user-level config:

```text
~/.copilot/mcp-config.json
```

Add:

```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "type": "local",
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"],
      "env": {},
      "tools": ["*"]
    }
  }
}
```

Project-level `.mcp.json` or `.github/mcp.json` takes precedence over same-named user-level servers. Use `/mcp show` in Copilot CLI to inspect status.

### Cursor

Cursor editor and Cursor CLI (`cursor-agent`) share the same `mcp.json` configuration. The CLI automatically detects MCP servers configured for the editor.

#### Option 1: Cursor Editor

Open MCP / MCP Servers from Cursor settings and add a custom stdio server. You can also edit the config file directly.

Project-level config:

```text
.cursor/mcp.json
```

Global config:

```text
~/.cursor/mcp.json
```

Config:

```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
    }
  }
}
```

#### Option 2: Cursor CLI

Cursor CLI uses the same `mcp.json`, so you do not need a second config file. Check the configured server with:

```bash
cursor-agent mcp list
cursor-agent mcp list-tools bilibili-mcp
```

If an MCP server requires authentication, Cursor CLI uses:

```bash
cursor-agent mcp login bilibili-mcp
```

### Cline

Cline supports local STDIO and remote MCP. Edit the Cline MCP config and add:

```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

Cline CLI users can inspect or manage MCP settings as JSON:

```bash
cline config mcp --json
```

After setup, confirm the server is enabled in Cline's MCP panel. Do not write real Cookie values in Cline config.

### Kilo Code

Kilo Code stores MCP servers under the `mcp` object in its main config file.

Config locations:

- Global: `~/.config/kilo/kilo.jsonc`
- Project-level: `kilo.jsonc`
- Project-level: `.kilo/kilo.jsonc`

Add:

```jsonc
{
  "mcp": {
    "bilibili-mcp": {
      "type": "local",
      "command": ["npx", "-y", "@xzxzzx/bilibili-mcp@latest"],
      "enabled": true,
      "timeout": 10000
    }
  }
}
```

You can also use Kilo Code Settings UI → Agent Behaviour → MCP Servers. Project-level config takes precedence over global config.

### VS Code

VS Code supports MCP configuration natively. Open workspace MCP configuration from the command palette:

```text
MCP: Open Workspace Folder MCP Configuration
```

This creates or opens:

```text
.vscode/mcp.json
```

Add:

```json
{
  "servers": {
    "bilibili-mcp": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
    }
  }
}
```

User-level config can be opened from the command palette:

```text
MCP: Open User Configuration
```

VS Code MCP also supports HTTP, SSE, Windows named pipes, and Unix sockets. After setup, use VS Code's MCP server list to start, stop, or inspect server status. Do not write real Cookie values in `.vscode/mcp.json`.

### GitHub Copilot (VS Code)

GitHub Copilot Chat in VS Code reads VS Code MCP configuration. Workspace config can be stored at:

```text
.vscode/mcp.json
```

Add:

```json
{
  "servers": {
    "bilibili-mcp": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
    }
  }
}
```

You can also open global MCP config from the command palette with `MCP: Open User Configuration`. After setup, use the server from Copilot Chat Agent Mode.

### Windsurf

Windsurf MCP is used by Cascade. The official entry points are the `MCPs` icon in the top-right of the Cascade panel, or Windsurf Settings → Cascade → MCP Servers.

#### Option 1: Cascade / MCP Servers UI

Open MCP Marketplace or MCP Servers settings, then add a custom stdio MCP server:

- Command: `npx`
- Arguments: `["-y", "@xzxzzx/bilibili-mcp@latest"]`

Windsurf also supports MCP deeplinks. If you provide an install entry in docs or a web page, use `windsurf://windsurf-mcp-registry?serverName=<server-name>` to open the matching MCP registry page.

#### Option 2: Raw config

Edit:

```text
~/.codeium/windsurf/mcp_config.json
```

Add:

```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
    }
  }
}
```

Windsurf/Cascade supports `stdio`, Streamable HTTP, and SSE MCP. This project uses a local stdio server, so do not write real Bilibili Cookie values in this config file; configure credentials with `bilibili-mcp config` or environment variables.

### Zed

Zed configures MCP with `context_servers`, not `mcpServers`. You can add a custom server from the Agent Panel settings view, or edit `settings.json` directly.

#### Option 1: Agent Panel UI

Open the Agent Panel settings view, click Add Custom Server, then enter this project's stdio server configuration.

After setup, check the indicator dot next to the server name in the Agent Panel settings view. Green means the server is active.

#### Option 2: settings.json

Open user settings with Zed's `zed: open settings` action. For project-level settings, use:

```text
.zed/settings.json
```

Add:

```json
{
  "context_servers": {
    "bilibili-mcp": {
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
    }
  }
}
```

#### Option 3: Zed extension

Zed can also install MCP servers as extensions. For a generic custom server, `context_servers` is more direct; if this project later publishes a Zed MCP extension, use the extension path instead.

Zed supports MCP Tools and Prompts, and it also supports remote MCP servers. Remote servers use `url` and optional `headers`. This project is a local stdio server, so do not write real Bilibili Cookie values in Zed configuration.

### Cherry Studio

Cherry Studio adds MCP servers from Settings → MCP Server. For this project, choose `STDIO`:

- Name: `bilibili-mcp`
- Type: `STDIO`
- Command: `npx`
- Parameters: `-y @xzxzzx/bilibili-mcp`

After saving, Cherry Studio starts the MCP server. Enable it in the chat box before calling its tools.

### LobeHub / LobeChat

LobeChat Desktop can import MCP server JSON. Open:

```text
Settings → Default Agent → Plugin Settings → Custom Plugins → Quick JSON Configuration Import
```

Paste:

```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
    }
  }
}
```

After installing it, enable this MCP server in the target Agent's plugin settings. Do not write real Cookie values in LobeChat config; configure credentials with this project's CLI or environment variables.

### AstrBot

AstrBot manages MCP from its WebUI. Make sure the AstrBot runtime can use `npm` and `node`, then add this local MCP server from the MCP server management page:

```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
    }
  }
}
```

If AstrBot runs in Docker, install Node.js / npm inside the container and make sure the container has the network access needed by this MCP server.

### nanobot

nanobot's config file is:

```text
~/.nanobot/config.json
```

Add this under `tools.mcpServers`:

```json
{
  "tools": {
    "mcpServers": {
      "bilibili-mcp": {
        "command": "npx",
        "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
      }
    }
  }
}
```

nanobot's MCP config is compatible with Claude Desktop / Cursor style config. It also supports remote MCP with `url` and `headers`. Credentials should still be managed by this project's CLI or environment variables, not written into nanobot config.

## ⚙️ Credential Configuration

If you use the "Install With Your Agent" prompt above, the agent should guide you through this section; you usually do not need to read the full setup manually. This section explains where Cookies are stored, the safety boundary, and manual scenarios such as Docker or local development. For reliable subtitles, transcripts, and comments, configure Bilibili Cookies; public video metadata may work without cookies.

### Recommended: Agent-Guided Credential Setup

```bash
npx -y @xzxzzx/bilibili-mcp@latest config
npx -y @xzxzzx/bilibili-mcp@latest check
```

If you use the "Install With Your Agent" prompt above, the agent should guide you to run these commands after it adds the MCP server. `config` input is not echoed in the terminal and saves Cookies to the local credential config, which the MCP server reads automatically when it starts; it does not write Cookies into MCP client config or the repository.

If the package is already installed globally, you can also run:

```bash
bilibili-mcp config
bilibili-mcp check
```

### Environment Variables

For Docker, local development, or cases where you explicitly control the MCP server runtime environment. Do not put real Cookies in shareable MCP client config files.

| Variable | Description |
|---|---|
| `BILIBILI_SESSDATA` | SESSDATA from your Bilibili login cookie |
| `BILIBILI_BILI_JCT` | bili_jct from your Bilibili login cookie |
| `BILIBILI_DEDEUSERID` | Your Bilibili user ID |

`.env` example:

```env
BILIBILI_SESSDATA=<your_sessdata>
BILIBILI_BILI_JCT=<your_bili_jct>
BILIBILI_DEDEUSERID=<your_dedeuserid>
```

### Obtaining Cookies

Get cookies from your own Bilibili login session only. Browser developer tools vary; follow your browser"s actual interface.

Do not share cookies with others. Do not paste them into public chats, issues, PRs, READMEs, logs, or test files.

### Security Notice

- Keep cookies in local config, environment variables, or `.env` only.
- `.env` is excluded by `.gitignore`, but always avoid committing it.
- If cookies are leaked, invalidate the old session on Bilibili"s account settings immediately.
- This project does not upload cookies to any third-party service other than Bilibili"s official API.

---

## 🧭 Which tool should I use?

| Goal | Recommended tool | What you get |
|---|---|---|
| Summarize a video | `get_video_info` | Subtitles first; falls back to title, description, tags |
| Get clean transcript text or locate keywords | `get_video_transcript` | Plain subtitle text, language, data source; supports timestamps, range filtering, and keyword search |
| See structured metadata | `get_video_metadata` | Title, author, duration, publish date, tags, stats, multi-Part listing |
| View audience reactions | `get_video_comments` | Popular comments, timestamped highlights, optional replies |
| See video Chapters | `get_video_chapters` | Chapter titles, start/end seconds; empty list when absent |
| Guide users through Cookie setup | `get_credential_setup_instructions` | Safe setup steps, recommended commands, security notes |
| Check whether Cookies are configured/logged in | `check_bilibili_credentials` | configured, source, logged_in, next_steps, next_steps_zh |
| Check whether the MCP package needs an update | `check_mcp_update` | current_version, latest_version, update_available, notes_zh, update commands |

## 💡 Tool Call Examples

> Your AI client will automatically turn your natural-language intent into the corresponding JSON call.

### `get_credential_setup_instructions`

**Best for**: letting an agent guide Cookie setup after installing the MCP server.

Request:

```json
{
  "name": "get_credential_setup_instructions",
  "arguments": {}
}
```

Returns: recommended setup commands, global-install commands, required Cookie fields, and bilingual `security_notes_en` / `security_notes_zh`; never returns Cookie values.

### `check_bilibili_credentials`

**Best for**: checking whether the current environment has Cookies configured and whether they are logged in.

Request:

```json
{
  "name": "check_bilibili_credentials",
  "arguments": {}
}
```

Returns: `configured`, `source` (`env` / `global_config` / `none`), `logged_in`, backward-compatible `next_steps`, and bilingual `next_steps_en` / `next_steps_zh`; never returns Cookie values.

### `check_mcp_update`

**Best for**: checking whether the installed MCP package is behind npm latest and showing safe update commands.

Request:

```json
{
  "name": "check_mcp_update",
  "arguments": {}
}
```

Returns: `current_version`, `latest_version`, `update_available`, `recommended_mcp_config`, `update_commands`, and bilingual `notes_en` / `notes_zh`; never updates packages automatically.

### `get_video_transcript`

**Best for**: feeding video content into AI for summarization, note-taking, Q&A, or knowledge management.

Request:

```json
{
  "name": "get_video_transcript",
  "arguments": {
    "bvid_or_url": "https://www.bilibili.com/video/BV1xx411c7mD",
    "preferred_lang": "en",
    "fallback_to_description": false
  }
}
```

Returns: `bvid`, `title`, `language`, `transcript` (newline-joined), `data_source` (`subtitle` or `description`), `page`.

> Returns `SUBTITLE_UNAVAILABLE` when no subtitles exist. Set `fallback_to_description: true` to fall back.

**Keyword search example**:

```json
{
  "name": "get_video_transcript",
  "arguments": {
    "bvid_or_url": "BV1xx411c7mD",
    "query": "machine learning",
    "max_matches": 5,
    "context_segments": 1
  }
}
```

Search mode returns: `query`, `total_matches`, `returned_matches`, `truncated`, `matches` (with `start_seconds`, `end_seconds`, `content`, `context`), and compact `transcript`.

**Timed range example**:

```json
{
  "name": "get_video_transcript",
  "arguments": {
    "bvid_or_url": "BV1xx411c7mD",
    "page": 1,
    "include_timestamps": true,
    "start_seconds": 120,
    "end_seconds": 300
  }
}
```

### `get_video_metadata`

**Best for**: quickly checking video basics without subtitles or comments.

Request:

```json
{
  "name": "get_video_metadata",
  "arguments": {
    "bvid_or_url": "BV1xx411c7mD"
  }
}
```

Returns: `bvid`, `title`, `author`, `duration`, `pubdate` / `pubdate_timestamp`, `description`, `tags`, `pages` (multi-Part listing), and `stats` (views, likes, coins, favorites, shares, replies, danmaku).

### `get_video_chapters`

**Best for**: getting Bilibili creator-defined Chapter intervals for navigation.

Request:

```json
{
  "name": "get_video_chapters",
  "arguments": {
    "bvid_or_url": "BV1vL411G7N7"
  }
}
```

Returns: `bvid`, `page`, `cid`, `title`, `chapters` (array with `title`, `start_seconds`, `end_seconds`). Empty array when no Chapters exist.

### `get_video_info`

**Best for**: letting AI summarize a video -- attempts subtitles first, falls back to description and tags.

Request:

```json
{
  "name": "get_video_info",
  "arguments": {
    "bvid_or_url": "https://www.bilibili.com/video/BV1xx411c7mD",
    "preferred_lang": "en"
  }
}
```

Returns: `data_source` (`subtitle` or `description`), `video_info` (title, description, tags, subtitle text, publish date).

> Videos without subtitles automatically degrade to description and tags (`data_source: "description"`).

### `get_video_comments`

**Best for**: gauging audience sentiment and finding highlight timestamps.

Request:

```json
{
  "name": "get_video_comments",
  "arguments": {
    "bvid_or_url": "BV1xx411c7mD",
    "detail_level": "detailed",
    "limit": 10,
    "sort": "hot",
    "include_replies": true
  }
}
```

Returns: `comments[]` (author, content, likes, timestamp, has_timestamp), `summary` (total count, timestamp count).

> Expired or missing cookies may result in empty comments. Use `sort: "time"` for newest comments, `include_replies: false` to skip replies.

---

## 🛡️ API Rate Limiting

Built-in request controls reduce the chance of triggering Bilibili risk checks or API rate limits:

- **Request start interval**: defaults to 500ms (0.5s), configurable with `BILIBILI_RATE_LIMIT_MS`.
- **Execution model**: throttles API request starts to avoid burst concurrency; intended for local single-user MCP usage.
- **Retry strategy**: retries 408, 429, 5xx, network errors, and timeouts up to 3 times with exponential backoff.
- **Timeout**: defaults to 10 seconds, configurable with `BILIBILI_REQUEST_TIMEOUT_MS`.
- **Cache capacity**: defaults to 100 entries, configurable with `BILIBILI_CACHE_SIZE`.
- **User-Agent**: overridable via `USER_AGENT`.

All of the above environment variables are read at MCP server process startup. After changing them, restart the MCP client or reconnect the MCP server for the new values to take effect.

---

## 🛠️ Development Guide

```bash
# 1. Clone the repository
git clone https://github.com/XZXZZX-Ai/bilibili-mcp.git
cd bilibili-mcp

# 2. Install dependencies
npm install

# 3. Run tests
npm test

# 4. Build TypeScript
npm run build

# 5. Watch and rebuild during development
npm run watch
```

Common commands:

| Command | Purpose |
|---|---|
| `npm run build` | Clean `dist/` then compile TypeScript |
| `npm test` | Run the Vitest unit tests |
| `npm run watch` | Continuously compile during development |
| `npm start` | Run the compiled stdio MCP server |
| `npm pack --dry-run` | Inspect which files would be included in the npm package |

Local debugging notes:

- The MCP server entry point is `dist/index.js`, and the CLI entry point is `dist/cli.js`; run `npm run build` after changing source files.
- For stdio MCP servers, `stdout` must be reserved for MCP protocol data. Runtime logs and errors should go to `stderr`, so this project uses `console.error` for operational logs.
- Do not put real Cookies in tests, logs, examples, or commits. To verify credentials, use `npx -y @xzxzzx/bilibili-mcp@latest check` or local environment variables.

---

## ⚖️ Safety and Disclaimer

- **Unofficial project**: Bilibili is a registered trademark of Bilibili Inc. This is a third-party open-source helper tool. It is not affiliated with, endorsed by, or representative of Bilibili.
- **Usage boundary**: This project is intended for personal learning, assisted reading, and content understanding. Follow Bilibili's terms, robots/interface access rules, and applicable laws. Do not use it for commercial exploitation, large-scale scraping, permission bypassing, or other abusive scenarios.
- **Account risk**: Requests are initiated from the user's local machine. High-frequency access, abnormal request patterns, Cookie leaks, or account-specific state may trigger risk controls, rate limits, or account issues. Users are responsible for their own usage and consequences.
- **Cookie safety**: Do not put real Cookies in MCP client config, public chats, issues, PRs, READMEs, logs, or test files. Prefer this project's local credential config, runtime environment variables, or a local `.env` file. If Cookies leak, invalidate the old Bilibili login session immediately.
- **Privacy**: This project does not upload Cookies to any third-party service other than Bilibili's official API. Credentials are stored or read locally according to the user's chosen setup. The current local config file does not promise system-level encryption; protect your device, account, and config file permissions.

### License
Open-sourced under **GNU General Public License v3.0**. When using, copying, modifying, or distributing this project, follow the GPL-3.0 license requirements.

---

## 🛠️ Development Process

This project is a crystal of AI-collaborative development, spanning from prototype to refinement:

1.  **Initial Generation**: Core architecture and base logic were rapidly built by **Claude Code** (powered by **GLM-4.7** model).
2.  **Debugging & Optimization**: Bugs were fixed and features enhanced using **Claude** and **Gemini** models within the **Antigravity** environment, ensuring stable subtitle extraction and comment analysis.
3.  **Iteration & Expansion**: **Codex** handles architectural decisions and planning, launching **Claude Code** via **Paseo** for implementation; now covers 30+ AI client MCP configurations, 8 MCP tools, and 299 unit tests.

---

## 💬 Feedback & Suggestions

If you encounter any issues or have feature suggestions, feel free to reach out:

- **Submit an Issue**: [GitHub Issues](https://github.com/XZXZZX-Ai/bilibili-mcp/issues) — **Recommended**, I check and respond regularly.
- **Discussions**: Join our [GitHub Discussions](https://github.com/XZXZZX-Ai/bilibili-mcp/discussions) for general chat.

Thank you for your support!
