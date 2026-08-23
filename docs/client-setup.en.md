# Bilibili MCP Installation and Client Setup

[Back to English README](../README_EN.md) · [简体中文](./client-setup.md) · [Tool reference](./tool-reference.en.md)

This page is the single complete source for end-user Bilibili MCP installation and configuration: the Agent prompt, every client setup, credentials, login verification, and optional runtime settings.

**On this page:** [Install with an Agent](#install-with-an-agent) · [Client configuration](#client-configuration) · [Credential setup and verification](#credential-setup-and-verification) · [Optional runtime configuration](#optional-runtime-configuration) · [Develop from source](#develop-from-source)

## Requirements

- Node.js 20 or later
- `npx`, included with Node.js

### Recommended: run the latest release on demand

Every client ultimately starts the same local stdio server:

```text
npx -y @xzxzzx/bilibili-mcp@latest
```

Prefer this command in MCP client configuration so a new session resolves the current npm release.

### Optional: global installation

```bash
npm install -g @xzxzzx/bilibili-mcp@latest
bilibili-mcp --help
```

A global installation does not update automatically. Run `bilibili-mcp check-update` to check its version, then repeat the installation command to update.

## Install with an Agent

Copy the complete prompt below into Codex, Claude Code, Cursor, or another Agent-capable tool:

```text
Please help me install the Bilibili MCP server: @xzxzzx/bilibili-mcp.

1. First identify the Agent / MCP client I am currently using.
   If you cannot determine it accurately from the environment, ask me instead
   of guessing.

2. Open and read the complete installation guide:
   https://github.com/XZXZZX-Ai/bilibili-mcp/blob/master/docs/client-setup.en.md
   Find the configuration location and format for this specific client.
   Do not assume every client uses mcpServers JSON.

3. Confirm that Node.js 20+ and npx are available, then add the server using
   the matching guide section. This is the launch baseline, not a universal
   client configuration format:
   - server name: bilibili-mcp
   - command: npx
   - args: ["-y", "@xzxzzx/bilibili-mcp@latest"]

4. Do not ask me to paste real Bilibili Cookie values into chat, project files,
   MCP client configuration, env fields, or args. If I need field guidance,
   call get_credential_setup_instructions after the server is connected.

5. Guide me to run these commands interactively in my own local terminal:

   npx -y @xzxzzx/bilibili-mcp@latest setup
   npx -y @xzxzzx/bilibili-mcp@latest check

   I must enter setup values locally; do not collect or display Cookies.
   check confirms only that local credentials can be loaded. It does not
   validate the Bilibili login.
   If you need machine-readable local status, use:
   npx -y @xzxzzx/bilibili-mcp@latest doctor --json

   After credentials are configured, setup asks whether to install the optional
   local ASR model. This is a local-only operation — do not answer for me or
   handle model files; let me follow the prompt, type y to continue or press
   Enter to skip [y/N]. After choosing to install, three model options are
   shown; I select on my own or press Enter for the recommended small.
   After installation, I may explicitly set fallback_to_asr=true on
   get_video_transcript when I need no-subtitle fallback. Default calls never
   run ASR, and MCP calls never download or switch models.
   For automated / terminal-less environments: bilibili-mcp setup --non-interactive
   uses already-loadable credentials from environment variables or the global
   config file, never reading credential values from stdin/argv and never prompting. Without
   --asr-model it confirms loadability and exits successfully (exit 0); adding
   --asr-model <tiny|base|small> installs that model (requires --non-interactive).

6. After configuration, restart or reconnect this MCP server so it reloads
   the credentials.

7. After reconnecting, you must call check_bilibili_credentials.
   Report credential success only when configured=true and logged_in=true.
   Otherwise, follow next_steps. Call check_mcp_update separately only when
   a version check is needed.

8. In the final report, include only the client used, configuration location,
   MCP connection state, configured / logged_in state, and version-check
   result. Never output Cookie values.
```

## Client configuration

> [!NOTE]
> Client locations and structures differ, so use only the matching section. Never put real Cookie values in client configuration, `env`, or `args`. After adding the server, complete [credential setup and verification](#credential-setup-and-verification), then restart or reconnect the MCP server.

**Quick jump**

[Codex](#codex-app--codex-cli) · [Claude Code](#claude-code) · [Claude Desktop](#claude-desktop) · [GitHub Copilot](#github-copilot-vs-code) · [VS Code](#vs-code) · [Cursor](#cursor) · [OpenClaw](#openclaw) · [Hermes](#hermes) · [OpenCode](#opencode) · [Pi](#pi) · [Qoder / Qoder CN](#qoder--qoder-cn-formerly-tongyi-lingma) · [Trae](#trae-cn) · [WorkBuddy](#workbuddy) · [DeepSeek Harness](#deepseek-harness) · [Antigravity](#antigravity--antigravity-cli) · [Gemini CLI](#gemini-cli) · [Kimi Code](#kimi-code--kimi-code-cli) · [MiniMax Code](#minimax-code--minimax-code-cli) · [CodeBuddy](#codebuddy) · [Qwen Code](#qwen-code) · [Kiro](#kiro-ide--kiro-cli) · [Cline](#cline) · [Kilo Code](#kilo-code) · [Devin Desktop](#devin-desktop--windsurf) · [Grok Build](#grok-build)

<details>
<summary>View other covered clients</summary>

[GitHub Copilot CLI](#github-copilot-cli) · [Baidu Comate](#baidu-comate) · [Warp](#warp) · [Factory Droid](#factory-droid) · [JetBrains AI](#jetbrains-ai-assistant) · [Amazon Q Developer](#amazon-q-developer) · [Auggie](#augment-code--auggie-cli) · [Amp](#amp) · [Goose](#goose) · [CodeFlicker](#codeflicker) · [CodeArts Agent](#codearts-agent) · [Mistral Vibe](#mistral-vibe) · [Trae International](#trae-international) · [Trae SOLO CN](#trae-solo-cn) · [Trae SOLO International](#trae-solo-international) · [Oh My Pi](#oh-my-pi) · [Zed](#zed) · [Cherry Studio](#cherry-studio) · [LobeHub](#lobehub--lobechat) · [Crush](#crush) · [DeepSeek-TUI](#deepseek-tui) · [Deep Code](#deep-code) · [Reasonix](#reasonix) · [AstrBot](#astrbot) · [nanobot](#nanobot)

</details>

### Codex app / Codex CLI

Codex app, the ChatGPT desktop app, Codex CLI, and the Codex IDE extension share MCP configuration on the same host. Use either setup path:

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

### OpenClaw

Register this server in OpenClaw's MCP registry:

```bash
openclaw mcp set bilibili-mcp '{"command":"npx","args":["-y","@xzxzzx/bilibili-mcp@latest"]}'
```

Inspect the saved definition and establish a real connection:

```bash
openclaw mcp status --verbose
openclaw mcp doctor bilibili-mcp --probe
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

Pi connects MCP servers lazily by default, so a server starts only when a tool is actually used. In Pi, run `/mcp` to inspect server status and available tools. Do not write real Cookie values in Pi MCP config; configure credentials with `bilibili-mcp setup` or environment variables.

### Qoder / Qoder CN (formerly TONGYI Lingma)

TONGYI Lingma has been renamed Qoder CN. It uses a different account and credit pool from the international Qoder product, but their MCP configuration is the same. Qoder IDE / Qoder CN Desktop uses Settings, Qoder CLI uses `qodercli mcp`, and QoderWork desktop uses the MCP Servers page.

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

After adding it, confirm the server is enabled under Custom Servers and expand it to inspect available tools. Do not write real Cookie values in Qoder / QoderWork MCP config; configure credentials with `bilibili-mcp setup` or environment variables.

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

### DeepSeek Harness

DeepSeek Harness is currently a developer preview. It connects local stdio servers through its MCP client bridge plugin. Add this to the active composition's `cordis.yml`:

```yaml
- id: mcp-bilibili
  name: '@deepseek-ai/dsh-mcp-client'
  config:
    serverName: bilibili-mcp
    transport: stdio
    command: npx
    args: ['-y', '@xzxzzx/bilibili-mcp@latest']
```

Editing the entry triggers disconnect and reconnect. If DeepSeek Harness is not installed yet, start its local Web UI with `npx @deepseek-ai/dsh web`. See the [official DeepSeek Harness repository](https://github.com/deepseek-ai/deepseek-harness) and [official MCP client documentation](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/README.md).

### Antigravity / Antigravity CLI

Antigravity and Gemini CLI are separate clients and do not share MCP configuration files. Use the dedicated Gemini CLI section below for Gemini CLI.

In Antigravity IDE, open MCP Store → Manage MCP Servers → View raw config. In Antigravity CLI, use `/mcp` to manage MCP servers.

Common config paths:

- Global: `~/.gemini/config/mcp_config.json`
- Workspace: `.agents/mcp_config.json`

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

Refresh the MCP list in Antigravity after saving, or use `/mcp` in Antigravity CLI to check whether the server is loaded.

### Gemini CLI

Use Gemini CLI's built-in command to add a user-scoped stdio server:

```bash
gemini mcp add --scope user bilibili-mcp npx -y @xzxzzx/bilibili-mcp@latest
```

You can also add the following `mcpServers` entry to the user-level `~/.gemini/settings.json` or project-level `.gemini/settings.json`:

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

Run `gemini mcp list`, or use `/mcp` inside Gemini CLI, to verify the connection.

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

Do not write real Cookie values in Kimi Code `mcp.json`, `env`, or command arguments. Configure credentials with `bilibili-mcp setup` or environment variables.

### MiniMax Code / MiniMax Code CLI

MiniMax Code 3.0.66 and later provides a dedicated MCP Servers page. Open Plugin Management → MCP Servers and either use Form mode or paste this in JSON mode:

```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"],
      "enabled": true
    }
  }
}
```

Local configuration is normally stored in `~/.minimax/mcp.json`. MiniMax Code CLI users can inspect the connection and tools with:

```bash
mcode mcp list --human
mcode mcp tools bilibili-mcp
```

See the [official MiniMax Code MCP documentation](https://agent.minimax.io/docs/code/agents/mcp).

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

### Qwen Code

Use Qwen Code's built-in command to add a user-scoped stdio server:

```bash
qwen mcp add --scope user bilibili-mcp npx -y @xzxzzx/bilibili-mcp@latest
```

The corresponding user configuration is stored in `~/.qwen/settings.json`; project configuration can use `.qwen/settings.json` with the same `mcpServers` JSON shape shown for Gemini CLI. Restart the current Qwen Code session and use `/mcp` to verify the connection.

### Kiro IDE / Kiro CLI

Kiro IDE and Kiro CLI share MCP configuration. Run `Kiro: Open user MCP config (JSON)` from the command palette, or open the workspace configuration, and add:

```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"],
      "disabled": false
    }
  }
}
```

The user file is `~/.kiro/settings/mcp.json`; the project file is `.kiro/settings/mcp.json`. Kiro reconnects after saving. Confirm the server in the MCP Servers panel or with `/mcp` in the CLI.

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

### Devin Desktop / Windsurf

Windsurf is now named Devin Desktop; existing installations, settings, and Cascade MCP configuration carry forward. Open Settings → Tools → Windsurf Settings → Add Server.

#### Option 1: Cascade / MCP Servers UI

Open MCP Servers settings, then add a custom stdio MCP server:

- Command: `npx`
- Arguments: `["-y", "@xzxzzx/bilibili-mcp@latest"]`

Windsurf also supports MCP deeplinks. If you provide an install entry in docs or a web page, use `windsurf://windsurf-mcp-registry?serverName=<server-name>` to open the matching MCP registry page.

#### Option 2: Raw config

Edit:

```text
~/.codeium/mcp_config.json
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

Cascade in Devin Desktop remains compatible with the former Windsurf MCP configuration and supports `stdio`, Streamable HTTP, and SSE. This project uses a local stdio server, so do not write real Bilibili Cookie values in this config file; configure credentials with `bilibili-mcp setup` or environment variables.

### Grok Build

Add the local stdio server with the Grok Build CLI:

```bash
grok mcp add bilibili-mcp -- npx -y @xzxzzx/bilibili-mcp@latest
grok mcp doctor
```

User configuration lives at `~/.grok/config.toml`. Add `--scope project` to `grok mcp add` for project-level configuration. See the [official Grok Build MCP documentation](https://docs.x.ai/build/features/mcp-servers).

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

### Baidu Comate

In the Comate Zulu view, open the title-bar More menu → MCP → Manual configuration. User-level configuration lives at `~/.comate/mcp.json`; project-level configuration lives at `.comate/mcp.json`. Add:

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

Save, confirm the connection in the Installed list, and enable the server for the Agent that should use it. See the [official Comate MCP documentation](https://comate.baidu.com/docs/IDE%E5%8A%9F%E8%83%BD/MCP/).

### Warp

In Warp, open Settings → AI → MCP Servers, click + Add, and paste the JSON below. You can also write it to user-level `~/.warp/.mcp.json` or project-level `.warp/.mcp.json`:

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

Project-level servers require trust approval before first launch. See the [official Warp MCP documentation](https://docs.warp.dev/agent-platform/capabilities/mcp/).

### Factory Droid

Add the local stdio server with the Droid CLI:

```bash
droid mcp add bilibili-mcp "npx -y @xzxzzx/bilibili-mcp@latest" --type stdio
```

Run `/mcp` inside Droid to inspect its status. User configuration lives at `~/.factory/mcp.json`; never put real Cookie values in project-level `.factory/mcp.json`. See the [official Factory Droid MCP documentation](https://docs.factory.ai/cli/configuration/mcp).

### JetBrains AI Assistant

In a JetBrains IDE, open Settings → Tools → AI Assistant → Model Context Protocol (MCP), click Add, choose JSON configuration, and paste:

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

Choose global or project scope as needed, save, click Apply, and confirm the connection in the Status column.

### Amazon Q Developer

In VS Code or a JetBrains IDE, open Q Developer → Chat, select the tools icon and `+`, choose global or local scope, and enter:

- Name: `bilibili-mcp`
- Transport: `stdio`
- Command: `npx`
- Arguments: `-y` and `@xzxzzx/bilibili-mcp@latest`

Save, then review the connection and tool permissions in the MCP Servers panel. The current GUI stores global configuration in `~/.aws/amazonq/default.json` and project configuration in `.amazonq/default.json`; legacy `mcp.json` files remain compatible, but new setups should use the GUI.

### Augment Code / Auggie CLI

Add a user-level stdio server with Auggie CLI:

```bash
auggie mcp add bilibili-mcp -- npx -y @xzxzzx/bilibili-mcp@latest
auggie mcp list
```

The configuration is stored in `~/.augment/settings.json`. To scope it to the current project, add `--local` or `--project` after `mcp add`. See the [official Auggie MCP documentation](https://docs.augmentcode.com/cli/integrations).

### Amp

Add this to user-level `~/.config/amp/settings.json` or project-level `.amp/settings.json`:

```json
{
  "amp.mcpServers": {
    "bilibili-mcp": {
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp@latest"]
    }
  }
}
```

Workspace MCP servers require approval before their first run. See the [official Amp MCP manual](https://ampcode.com/manual/mcp.md).

### Goose

Run `goose configure`, then select Add Extension → Command-Line Extension and enter:

- Name: `Bilibili MCP`
- Command: `npx -y @xzxzzx/bilibili-mcp@latest`
- Environment variables: `No`

In Goose Desktop, you can instead open Extensions → Add custom extension, select Standard IO, and enter the same command. Save and confirm the extension is enabled.

### CodeFlicker

Open CodeFlicker Settings → MCP Management → MCP Configuration, choose Manual Configuration, and add:

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

Save, confirm the connection, and enable it from the MCP button in Agent mode. See the [official CodeFlicker MCP documentation](https://www.codeflicker.ai/docs/en/feats/corefeat/MCP.html).

### CodeArts Agent

In CodeArts Agent IDE, open Settings → MCP → Configure MCP and edit the opened `mcp_settings.json`:

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

Save and wait for the server to start, then switch the chat panel to Agent mode. See the [official CodeArts Agent MCP documentation](https://support.huaweicloud.com/intl/en-us/usermanual-codeartsagent/codeartsagent_ug_0010.html).

### Mistral Vibe

Edit the user-level `~/.vibe/config.toml`, or `.vibe/config.toml` in a trusted project, and add:

```toml
[[mcp_servers]]
name = "bilibili-mcp"
transport = "stdio"
command = "npx"
args = ["-y", "@xzxzzx/bilibili-mcp@latest"]
```

Start Vibe and use `/mcp` to verify the server. Do not place real Cookies in `config.toml`.

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

### Zed

Zed configures MCP with `context_servers`, not `mcpServers`. You can add a custom server from Settings → AI → MCP Servers, or edit `settings.json` directly.

#### Option 1: MCP Servers UI

Open Settings → AI → MCP Servers, click Add Custom Server, then enter this project's stdio server configuration.

After setup, check the indicator dot next to the server name in the MCP Servers list. Green means the server is active.

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

## Credential setup and verification

Use Cookies from your own Bilibili login for reliable video search, subtitles, transcripts, and comments. Public video metadata may still work without a login.

### Finding credential fields in your browser

1. Sign in to your own account at [https://www.bilibili.com](https://www.bilibili.com).
2. Open browser DevTools (`F12`) and locate Cookies:
   - Chrome / Edge: **Application** → **Storage** → **Cookies** → `https://www.bilibili.com`
   - Firefox: **Storage** → **Cookies** → `https://www.bilibili.com`
3. Copy only the exact values of `SESSDATA`, `bili_jct`, and `DedeUserID`.
4. If you can't find them, refresh the logged-in Bilibili page and confirm the selected domain is `https://www.bilibili.com`.
5. Paste the values only into the local hidden-input `setup` prompts. Never paste them into chat, screenshots, client config, Issues, PRs, logs, or examples.

### Recommended: interactive local setup

```bash
npx -y @xzxzzx/bilibili-mcp@latest setup
npx -y @xzxzzx/bilibili-mcp@latest check
```

- `setup` collects `SESSDATA`, `bili_jct`, and `DedeUserID` interactively in your local terminal without echoing the input. When no credentials are configured it guides you through setup; when already configured it shows current state.
- `config` also provides interactive configuration but skips the already-configured check; use it when you need to force reconfiguration.
- Credentials are saved in the local global config, not in the repository or MCP client configuration.
- `check` confirms only that the current process can load credentials; it does not prove that the Bilibili login is still valid.
- After credentials are configured, `setup` asks whether to install an optional local ASR speech-recognition model (defaults to No `[y/N]`).

`doctor --json` is a local-only diagnostic tool with exit codes `0/1/2` (ok / needs setup or credentials not loadable / internal error). It makes no network requests and cannot replace `check_bilibili_credentials` for live login validation. Agents or non-interactive environments can use:

```bash
npx -y @xzxzzx/bilibili-mcp@latest doctor --json
```

If the package is installed globally, you can instead run:

```bash
bilibili-mcp setup
bilibili-mcp check
```

### Optional ASR speech-recognition model

After credentials are configured, `setup` asks whether to install an optional local ASR model (defaults to No `[y/N]`).

- After choosing Yes, three model choices are displayed:
  - `1. tiny` (~78.2 MB) — Speed-first: suited to quick extraction and initial review of long videos, with relatively lower accuracy
  - `2. base` (~148 MB) — Balanced: balances speed, quality, and resource use
  - `3. small` (~486 MB) — Quality-first: higher CPU time and memory use; [recommended], selected on Enter
- Enter `1/2/3` or `tiny/base/small` to choose; invalid input re-prompts without starting installation.
- Runtime is fixed at `faster-whisper==1.2.1` plus runtime library overhead.
- Requires Python 3.9+ on the machine. Set the `BILIBILI_ASR_PYTHON` environment variable to override the Python executable.
- Installation lives in the user-managed `~/.bilibili-mcp/asr/` directory; it does not mutate the system Python.
- One active model per directory; switching models clears the old ready state.
- After installation, the model is verified through a CPU INT8 load; system FFmpeg is not required (PyAV bundles the relevant FFmpeg libraries).
- A failed installation leaves no ready marker; partial downloads are preserved and `setup` can resume from them.
- The `doctor --json` `asr.status` and `asr.model` fields are informational only; they do not affect credential exit codes.
- MCP calls never download or switch models; they use only the current model reported ready by `doctor --json`.
- `get_video_transcript` runs ASR only with explicit `fallback_to_asr: true` after subtitles are definitively unavailable. Native subtitles and Cookie/API/network failures never trigger it.
- ASR processes one resolved Part, capped at two hours and 128 MiB of temporary audio, with one active job and no queue.
- The Cookie goes only to Bilibili's playback API, never the temporary CDN or Python child. Signed URLs are not logged or returned, and the unique temp directory is removed after success, failure, or timeout.

### Docker, local development, or a controlled runtime

You may instead provide these variables in the MCP server runtime environment:

| Variable | Value |
|---|---|
| `BILIBILI_SESSDATA` | `SESSDATA` from your own Bilibili login Cookie |
| `BILIBILI_BILI_JCT` | `bili_jct` from your own Bilibili login Cookie |
| `BILIBILI_DEDEUSERID` | Your Bilibili user ID |

Inherited process environment variables work as expected, but the recommended `npx` path does not automatically load a project `.env` file. `setup` is the normal installation path; inherited process variables work only when a controlled shell, service, or secret runtime supplies them. The local `.env` example applies to source `npm start` / `dist/index.js`, or to a runtime that explicitly loads it.

Local `.env` example:

```env
BILIBILI_SESSDATA=<your_sessdata>
BILIBILI_BILI_JCT=<your_bili_jct>
BILIBILI_DEDEUSERID=<your_dedeuserid>
```

Obtain Cookies only from your own Bilibili login session. Never paste real values into chat, shared configuration, READMEs, issues, pull requests, source code, tests, or logs, and never commit `.env`. If a Cookie leaks, invalidate the old session from your Bilibili account settings immediately.

### Reconnect and validate the login

1. After configuring credentials, restart the client or reconnect `bilibili-mcp` so the new process reloads them.
2. Call `get_credential_setup_instructions` when field guidance is needed.
3. You must call `check_bilibili_credentials` to validate the login. Success requires both `configured: true` and `logged_in: true`.
4. Call `check_mcp_update` separately when you need a version check; a version check does not validate the login.

## Optional runtime configuration

The MCP server reads these variables at process startup. Restart the client or reconnect the server after changing them.

| Variable | Default | Purpose |
|---|---:|---|
| `BILIBILI_RATE_LIMIT_MS` | `500` | Minimum delay in milliseconds between Bilibili API request starts |
| `BILIBILI_REQUEST_TIMEOUT_MS` | `10000` | Per-request timeout in milliseconds |
| `BILIBILI_CACHE_SIZE` | `100` | Maximum in-memory cache entries |
| `USER_AGENT` | Project default | Override the request User-Agent |
| `BILIBILI_MCP_DEBUG` | Disabled | Set to `1` to emit credential-redacted debug logs to `stderr` |

All three numeric variables must be complete decimal positive safe integers. Empty, partial, zero, negative, or unsafe-integer values make the server reject startup with a configuration error. `BILIBILI_RATE_LIMIT_MS` and `BILIBILI_REQUEST_TIMEOUT_MS` must also not exceed the Node.js timer limit of `2147483647`.

See [Tool reference: Request controls and cache](./tool-reference.en.md#request-controls-and-cache) for retry, cache, and error semantics.

## Develop from source

```bash
git clone https://github.com/XZXZZX-Ai/bilibili-mcp.git
cd bilibili-mcp
npm install
npm run build
npm test
```

See the “Development” section in the [project README](../README_EN.md) for the remaining commands and stdio logging constraints.
