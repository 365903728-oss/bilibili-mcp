# Bilibili MCP 安装与客户端配置

[返回中文 README](../README.md) · [English](./client-setup.en.md) · [工具参考](./tool-reference.md)

本页是最终用户安装与配置 Bilibili MCP 的唯一完整入口，集中保存 Agent 安装提示词、全部客户端配置、凭证设置、登录验证和可选运行时配置。

**本页导航：**[用 Agent 安装](#用-agent-工具帮你安装) · [客户端配置](#客户端配置) · [凭证配置与验证](#凭证配置与验证) · [可选运行时配置](#可选运行时配置) · [从源码开发](#从源码开发)

## 安装前要求

- Node.js 20 或更高版本
- 随 Node.js 提供的 `npx`

### 推荐：按需运行最新版

所有客户端最终都启动同一个本地 stdio server：

```text
npx -y @xzxzzx/bilibili-mcp@latest
```

MCP 客户端优先使用这条命令，这样新会话会解析 npm 上的当前版本。

### 可选：全局安装

```bash
npm install -g @xzxzzx/bilibili-mcp@latest
bilibili-mcp --help
```

全局安装不会自动更新。可运行 `bilibili-mcp check-update` 检查版本，并重新执行安装命令更新。

## 用 Agent 工具帮你安装

把下面的提示词完整复制给 Codex、Claude Code、Cursor 或其他带 Agent 能力的工具：

```text
请帮我安装 Bilibili MCP server：@xzxzzx/bilibili-mcp。

1. 先确认我当前使用的 Agent / MCP 客户端。
   如果你无法从当前环境准确判断，请先询问我，不要猜测。

2. 打开并阅读完整安装指南：
   https://github.com/XZXZZX-Ai/bilibili-mcp/blob/master/docs/client-setup.md
   找到与当前客户端匹配的配置位置和格式，不要假设所有客户端都使用
   mcpServers JSON。

3. 确认本机已有 Node.js 20+ 和 npx，然后按指南添加 server。
   以下是启动基线，不是所有客户端通用的配置文件格式：
   - server 名称：bilibili-mcp
   - command：npx
   - args：["-y", "@xzxzzx/bilibili-mcp@latest"]

4. 不要要求我把真实 Bilibili Cookie 粘贴到聊天、项目文件、
   MCP 客户端配置、env 字段或 args 中。
   如果我需要字段说明，连接 server 后调用
   get_credential_setup_instructions。

5. 引导我本人在本地终端交互式运行：

   npx -y @xzxzzx/bilibili-mcp@latest setup
   npx -y @xzxzzx/bilibili-mcp@latest check

   setup 的输入必须由我在本地终端完成；不要代收或显示 Cookie。
   check 只确认本机凭证已加载，不等于已经验证 Bilibili 登录。
   如果你需要机器可读的本地状态，使用：
   npx -y @xzxzzx/bilibili-mcp@latest doctor --json

   完成凭证配置后，setup 会询问是否安装可选的本地 ASR 模型。
   这是纯本地操作——不要替我选择，也不要代收模型文件；让我自己按提示
   输入 y 继续，或直接回车跳过 [y/N]。选择安装后会显示三个模型选项，
   自行选择或按 Enter 选择推荐的 small。
   安装完成后，可在明确需要无字幕回退时调用 get_video_transcript 并设置
   fallback_to_asr=true；默认调用不会运行 ASR，也不会在 MCP 内下载或切换模型。
   自动化/无终端场景：bilibili-mcp setup --non-interactive 使用已有的环境变量或
   全局配置文件凭据，绝不从 stdin/argv 读取凭据值、绝不提示；无 --asr-model 时仅确认凭据可加载
   即成功退出（exit 0），加 --asr-model <tiny|base|small> 可安装指定模型
   （必须与 --non-interactive 同用）。

6. 配置完成后，重启或重连这个 MCP server，使其重新加载凭证。

7. 重连后必须调用 check_bilibili_credentials。
   只有 configured=true 且 logged_in=true，才报告凭证验证成功；
   否则按照 next_steps 指引我处理。需要检查版本时，再调用
   check_mcp_update。

8. 最后只报告：使用的客户端、修改的配置位置、MCP 连接状态、
   configured / logged_in 状态和版本检查结果。绝不输出 Cookie 值。
```

## 客户端配置

> [!NOTE]
> 各客户端的配置位置和结构不同，请只使用对应小节。不要把真实 Cookie 写进客户端配置、`env` 或 `args`；安装 server 后继续完成[凭证配置与验证](#凭证配置与验证)，再重启或重连 MCP server。

**快速跳转**

[Codex](#codex-app--codex-cli) · [Claude Code](#claude-code) · [Claude Desktop](#claude-desktop) · [GitHub Copilot](#github-copilot-vs-code) · [VS Code](#vs-code) · [Cursor](#cursor) · [OpenClaw](#openclaw) · [Hermes](#hermes) · [OpenCode](#opencode) · [Pi](#pi) · [Qoder / Qoder CN](#qoder--qoder-cn原通义灵码) · [Trae](#trae-cn) · [WorkBuddy](#workbuddy) · [DeepSeek Harness](#deepseek-harness) · [Antigravity](#antigravity--antigravity-cli) · [Gemini CLI](#gemini-cli) · [Kimi Code](#kimi-code--kimi-code-cli) · [MiniMax Code](#minimax-code--minimax-code-cli) · [CodeBuddy](#codebuddy) · [Qwen Code](#qwen-code) · [Kiro](#kiro-ide--kiro-cli) · [Cline](#cline) · [Kilo Code](#kilo-code) · [Devin Desktop](#devin-desktop--windsurf) · [Grok Build](#grok-build)

<details>
<summary>查看其他已覆盖客户端</summary>

[GitHub Copilot CLI](#github-copilot-cli) · [文心快码](#文心快码baidu-comate) · [Warp](#warp) · [Factory Droid](#factory-droid) · [JetBrains AI](#jetbrains-ai-assistant) · [Amazon Q Developer](#amazon-q-developer) · [Auggie](#augment-code--auggie-cli) · [Amp](#amp) · [Goose](#goose) · [CodeFlicker](#codeflicker) · [CodeArts Agent](#codearts-agent) · [Mistral Vibe](#mistral-vibe) · [Trae International](#trae-international) · [Trae SOLO CN](#trae-solo-cn) · [Trae SOLO International](#trae-solo-international) · [Oh My Pi](#oh-my-pi) · [Zed](#zed) · [Cherry Studio](#cherry-studio) · [LobeHub](#lobehub--lobechat) · [Crush](#crush) · [DeepSeek-TUI](#deepseek-tui) · [Deep Code](#deep-code) · [Reasonix](#reasonix) · [AstrBot](#astrbot) · [nanobot](#nanobot)

</details>

### Codex app / Codex CLI

Codex app、ChatGPT desktop app、Codex CLI 和 Codex IDE extension 在同一台主机上共用 MCP 配置。优先使用下面任一方式添加：

#### Codex app

打开 Settings → Integrations & MCP，添加自定义 MCP server：

- Command: `npx`
- Arguments: `["-y", "@xzxzzx/bilibili-mcp@latest"]`

#### Codex CLI

```bash
codex mcp add bilibili-mcp -- npx -y @xzxzzx/bilibili-mcp@latest
```

配置后，在 Codex CLI TUI 中运行 `/mcp` 查看 server 状态。

#### 手动配置

也可以直接编辑 Codex 配置文件：

- 用户级：`~/.codex/config.toml`
- 项目级：`.codex/config.toml`（仅在 Codex 信任该项目时加载）

```toml
[mcp_servers.bilibili-mcp]
command = "npx"
args = ["-y", "@xzxzzx/bilibili-mcp@latest"]
```

### Claude Code

```bash
claude mcp add bilibili-mcp -- npx -y @xzxzzx/bilibili-mcp@latest
```

默认会作为当前项目的本地 MCP server 保存。配置后可在 Claude Code 中运行 `/mcp`，或在终端运行 `claude mcp list` 检查连接状态。

如果希望所有项目都可用，可使用用户级 scope：

```bash
claude mcp add --scope user bilibili-mcp -- npx -y @xzxzzx/bilibili-mcp@latest
```

也可以手动编辑 `~/.claude.json`，在对应项目或用户配置下添加与 Claude Desktop 相同的 JSON。

### Claude Desktop

打开 Claude Desktop 的 Settings → Developer → Edit Config，或直接编辑：

- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

添加：

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

保存后重启 Claude Desktop。该配置适合本地 stdio MCP server；不要在 `env`、`args` 或配置文件里写真实 Cookie。

### GitHub Copilot (VS Code)

GitHub Copilot Chat 在 VS Code 中读取 VS Code MCP 配置。工作区配置可写入：

```text
.vscode/mcp.json
```

添加：

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

也可以用命令面板打开 `MCP: Open User Configuration` 配置全局 MCP。配置后在 Copilot Chat Agent Mode 中使用该 server 的工具。

### VS Code

VS Code 原生支持 MCP 配置。工作区配置可通过命令面板打开：

```text
MCP: Open Workspace Folder MCP Configuration
```

这会创建或打开：

```text
.vscode/mcp.json
```

添加：

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

用户级配置可用命令面板打开：

```text
MCP: Open User Configuration
```

VS Code MCP 还支持 HTTP、SSE、Windows named pipe 和 Unix socket。配置后可在 VS Code 的 MCP server 列表中启动、停止或查看 server 状态。使用本项目时不要把真实 Cookie 写进 `.vscode/mcp.json`。

### Cursor

Cursor 编辑器和 Cursor CLI (`cursor-agent`) 共用同一套 `mcp.json` 配置。CLI 会自动读取编辑器已配置的 MCP server。

#### 方式一：Cursor 编辑器

在 Cursor 设置中打开 MCP / MCP Servers，添加自定义 stdio server；也可以直接编辑配置文件。

项目级配置：

```text
.cursor/mcp.json
```

全局配置：

```text
~/.cursor/mcp.json
```

配置内容：

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

#### 方式二：Cursor CLI

Cursor CLI 使用同一份 `mcp.json`，无需单独再写一份配置。可用下面命令检查：

```bash
cursor-agent mcp list
cursor-agent mcp list-tools bilibili-mcp
```

如果 MCP server 需要认证，Cursor CLI 使用：

```bash
cursor-agent mcp login bilibili-mcp
```

### OpenClaw

使用 OpenClaw 的 MCP registry 注册本服务：

```bash
openclaw mcp set bilibili-mcp '{"command":"npx","args":["-y","@xzxzzx/bilibili-mcp@latest"]}'
```

检查配置并建立一次真实连接：

```bash
openclaw mcp status --verbose
openclaw mcp doctor bilibili-mcp --probe
```

也可以在 OpenClaw 配置中加入同等结构：

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

`openclaw mcp set` 只写入 OpenClaw 的 MCP server 定义；具体运行时是否启用，取决于你的 OpenClaw agent/runtime 配置。

### Hermes

编辑 `~/.hermes/config.yaml`，在 `mcp_servers` 下添加：

```yaml
mcp_servers:
  bilibili-mcp:
    command: "npx"
    args: ["-y", "@xzxzzx/bilibili-mcp@latest"]
```

如果你已经在运行 Hermes 会话，使用 `/reload-mcp` 重新加载 MCP 配置；也可以开启一个新的 Hermes 会话。

### OpenCode

编辑 OpenCode 配置文件 `~/.config/opencode/opencode.json`，在 `mcp` 下添加本地 MCP server：

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

OpenCode 会把 MCP tools 加入可用工具上下文。使用时可在提示词中明确要求使用 `bilibili-mcp`。

### Pi

Pi 通过 `pi-mcp-adapter` 使用 MCP。先安装 adapter：

```bash
pi install npm:pi-mcp-adapter
```

重启 Pi 后，优先使用项目级共享配置：

```text
.mcp.json
```

添加：

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

也可以使用用户级共享配置：

```text
~/.config/mcp/mcp.json
```

Pi 还支持 Pi 专属覆盖文件：

- 全局：`~/.pi/agent/mcp.json`
- 项目级：`.pi/mcp.json`

如果你已经在 Cursor、Claude Code、Codex、Windsurf 等客户端里配置过 MCP，可在 Pi 中运行 `/mcp setup` 导入或生成配置；终端也可运行：

```bash
pi-mcp-adapter init
```

Pi 默认 lazy 连接 MCP server，只有实际调用工具时才启动。进入 Pi 后使用 `/mcp` 查看 server 状态和工具列表。不要在 Pi 的 MCP 配置里写真实 Cookie；凭证请用 `bilibili-mcp setup` 或环境变量配置。

### Qoder / Qoder CN（原通义灵码）

通义灵码已更名为 Qoder CN；它与国际版 Qoder 使用不同账号与额度，但 MCP 配置方式相同。Qoder IDE / Qoder CN Desktop 在设置页配置，Qoder CLI 用 `qodercli mcp` 命令，QoderWork 桌面端在 MCP Servers 页面添加。

#### Qoder IDE

打开右上角用户图标 → Qoder Settings → MCP，在 My Servers 中点击 + Add，然后添加本地 STDIO server：

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

Qoder 文档说明 Streamable HTTP 可按 SSE endpoint 方式配置并自动检测；本项目是本地 stdio server，因此使用上面的 `command` / `args` 配置。

#### Qoder CLI

Qoder CLI 可直接添加 stdio MCP server：

```bash
qodercli mcp add bilibili-mcp -- npx -y @xzxzzx/bilibili-mcp@latest
```

常用检查命令：

```bash
qodercli mcp list
```

如果 Qoder CLI 已经在运行，添加或修改 MCP server 后在会话中执行 `/mcp reload` 重新发现工具。默认 scope 是当前项目本地配置；也可以用 `-s user` 保存到用户级配置，或用 `-s project` 写入项目级 `.mcp.json`。

常见配置文件位置：

- 用户级：`~/.qoder/settings.json`
- 当前项目本地：`.qoder/settings.local.json`
- 项目级共享：`.mcp.json`

#### QoderWork

打开 QoderWork desktop app → Settings → MCP Servers，点击右上角 + Add。

最快方式是选择 Paste JSON Config，并粘贴：

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

也可以选择 Fill in Config Manually，Server Type 选择 STDIO：

- Server Name: `bilibili-mcp`
- Command: `npx -y @xzxzzx/bilibili-mcp@latest`

添加后在 Custom Servers 中确认 server 已启用，并展开查看可用 tools。不要在 Qoder / QoderWork 的 MCP 配置中写真实 Cookie；凭证请使用 `bilibili-mcp setup` 或环境变量配置。

### Trae CN

在 Trae CN 中打开 AI 对话窗口右上角设置入口，进入 MCP 配置；也可以直接编辑 MCP 配置文件。

常见配置路径：

- Windows: `%APPDATA%\Trae\User\settings\mcp.json`
- macOS: `~/Library/Application Support/Trae/User/settings/mcp.json`
- 项目级：`.trae/mcp.json`

添加：

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

如果你使用项目级 `.trae/mcp.json`，请在 Trae 的 MCP 管理面板中确认项目配置导入已启用。

### Trae International

在 Trae 国际版中打开 AI 对话窗口右上角 Settings → MCP，选择 Add 或手动配置 MCP server。

如果需要直接编辑项目级配置，可创建 `.trae/mcp.json`：

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

Trae 支持 stdio MCP server；本项目使用 `npx` 启动 stdio server。

### Trae SOLO CN

Trae SOLO CN 是 Trae 中国版的 SOLO 工作方式。官方公开文档没有给出独立于 Trae MCP 的专属配置文件；当前可按 Trae 项目级 MCP 配置接入，然后在 SOLO Coder 中使用。

在项目根目录创建 `.trae/mcp.json`：

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

然后在 Trae 的 MCP 管理面板中确认项目配置导入已启用，并在 SOLO Coder 中使用该 MCP server。

### Trae SOLO International

Trae SOLO International 已存在，官方 FAQ 说明国际版 SOLO 面向 Pro 用户。没有找到单独的 SOLO 专属 MCP JSON 格式；可使用 Trae International 的 MCP 配置方式，然后在 SOLO Coder / Builder with MCP 中调用。

项目级配置同样使用 `.trae/mcp.json`：

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

如果使用 Trae International 的 UI，打开 AI 对话窗口右上角 Settings → MCP，手动添加同等 `mcpServers` 配置。

### WorkBuddy

WorkBuddy 官方文档推荐通过界面配置 MCP。进入侧边栏 插件 → MCP 服务器 → 配置 MCP，然后添加：

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

也可以按作用域编辑配置文件：

- 用户级：`~/.workbuddy/mcp.json`
- 项目级：`<项目目录>/.workbuddy/mcp.json`

### DeepSeek Harness

DeepSeek Harness 当前处于 developer preview。它通过 MCP client bridge 插件连接本地 stdio server；在当前组合使用的 `cordis.yml` 中加入：

```yaml
- id: mcp-bilibili
  name: '@deepseek-ai/dsh-mcp-client'
  config:
    serverName: bilibili-mcp
    transport: stdio
    command: npx
    args: ['-y', '@xzxzzx/bilibili-mcp@latest']
```

修改后会触发断开并重新连接。尚未安装时，可先用 `npx @deepseek-ai/dsh web` 启动本地 Web UI。参见 [DeepSeek Harness 官方仓库](https://github.com/deepseek-ai/deepseek-harness)和 [MCP client 官方文档](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/README.zh.md)。

### Antigravity / Antigravity CLI

Antigravity 与 Gemini CLI 是两个独立客户端，配置文件不能混用。Gemini CLI 请使用下方单独的小节。

Antigravity IDE 可通过 MCP Store → Manage MCP Servers → View raw config 打开配置；Antigravity CLI 可通过 `/mcp` 管理 MCP servers。

常见配置路径：

- 全局：`~/.gemini/config/mcp_config.json`
- 工作区：`.agents/mcp_config.json`

添加：

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

保存后在 Antigravity 中刷新 MCP 列表，或在 Antigravity CLI 中使用 `/mcp` 检查 server 是否加载。

### Gemini CLI

推荐使用 Gemini CLI 自带命令添加用户级 stdio server：

```bash
gemini mcp add --scope user bilibili-mcp npx -y @xzxzzx/bilibili-mcp@latest
```

也可以在用户级 `~/.gemini/settings.json` 或项目级 `.gemini/settings.json` 的 `mcpServers` 中加入：

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

配置后运行 `gemini mcp list`，或在 Gemini CLI 中使用 `/mcp` 检查状态。

### Kimi Code / Kimi Code CLI

Kimi Code CLI 可作为 MCP client 连接本地 stdio server。当前 Kimi Code 文档推荐把 MCP server 写入 `mcp.json`：

- 用户级：`~/.kimi-code/mcp.json`
- 项目级：`.kimi-code/mcp.json`

添加：

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

项目级 `.kimi-code/mcp.json` 只对当前仓库生效，并会覆盖同名用户级配置。进入 Kimi Code CLI 后，可以用：

```text
/mcp
/mcp-config
```

`/mcp` 查看连接状态和工具列表，`/mcp-config` 交互式添加、编辑或删除 MCP server。

旧版 Kimi CLI 文档也提供过 `kimi mcp add` 命令；如果你使用的安装版本仍支持该命令，可用：

```bash
kimi mcp add bilibili-mcp -- npx -y @xzxzzx/bilibili-mcp@latest
kimi mcp list
kimi mcp test bilibili-mcp
```

不要在 Kimi Code 的 `mcp.json`、`env` 或命令参数中写真实 Cookie；凭证请用 `bilibili-mcp setup` 或环境变量配置。

### MiniMax Code / MiniMax Code CLI

MiniMax Code 3.0.66 及以上版本提供独立的 MCP Servers 管理页。打开插件管理入口 → MCP Servers，可以使用表单模式添加，或在 JSON 模式粘贴：

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

本地配置通常保存在 `~/.minimax/mcp.json`。MiniMax Code CLI 用户可以检查连接和工具：

```bash
mcode mcp list --human
mcode mcp tools bilibili-mcp
```

参见 [MiniMax Code MCP 官方文档](https://agent.minimax.io/docs/code/agents/mcp)。

### CodeBuddy

#### 方式一：CodeBuddy CLI

CodeBuddy CLI 可以直接添加 stdio MCP server：

```bash
codebuddy mcp add --scope user bilibili-mcp -- npx -y @xzxzzx/bilibili-mcp@latest
```

检查配置：

```bash
codebuddy mcp list
codebuddy mcp get bilibili-mcp
```

#### 方式二：CodeBuddy IDE

在 CodeBuddy IDE 侧栏对话面板右上角打开 CodeBuddy Settings → MCP → Add MCP，填入：

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

如果使用项目级 `.mcp.json`，请确认 CodeBuddy settings 允许启用该项目 MCP server。

### Qwen Code

推荐使用 Qwen Code 自带命令添加用户级 stdio server：

```bash
qwen mcp add --scope user bilibili-mcp npx -y @xzxzzx/bilibili-mcp@latest
```

对应配置保存在 `~/.qwen/settings.json`；项目级配置可写入 `.qwen/settings.json`，结构与 Gemini CLI 的 `mcpServers` JSON 相同。配置后重启当前 Qwen Code 会话，并使用 `/mcp` 检查连接。

### Kiro IDE / Kiro CLI

Kiro IDE 与 Kiro CLI 共用 MCP 配置。通过命令面板运行 `Kiro: Open user MCP config (JSON)`，或选择 workspace 配置，然后加入：

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

用户级文件是 `~/.kiro/settings/mcp.json`，项目级文件是 `.kiro/settings/mcp.json`。保存后 Kiro 会自动重连；可在 MCP Servers 面板或 CLI 的 `/mcp` 中确认。

### Cline

Cline 支持本地 STDIO 和远程 MCP。编辑 Cline MCP 配置文件，加入：

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

Cline CLI 用户可用 JSON 方式查看或管理 MCP 设置：

```bash
cline config mcp --json
```

配置后在 Cline 的 MCP 面板确认 server 已启用。不要把真实 Cookie 写进 Cline 配置。

### Kilo Code

Kilo Code 的 MCP server 写在主配置文件的 `mcp` 对象下。

配置位置：

- 全局：`~/.config/kilo/kilo.jsonc`
- 项目级：`kilo.jsonc`
- 项目级：`.kilo/kilo.jsonc`

添加：

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

也可以在 Kilo Code 设置 UI 中打开 Agent Behaviour → MCP Servers 添加。项目级配置优先于全局配置。

### Devin Desktop / Windsurf

Windsurf 已更名为 Devin Desktop；现有安装、设置与 Cascade MCP 配置会继续保留。官方入口是 Settings → Tools → Windsurf Settings → Add Server。

#### 方式一：Cascade / MCP Servers UI

打开 MCP Servers 设置后，添加自定义 stdio MCP server：

- Command: `npx`
- Arguments: `["-y", "@xzxzzx/bilibili-mcp@latest"]`

Windsurf 也支持 MCP deeplink；如果你在文档或网页中提供安装入口，可以使用 `windsurf://windsurf-mcp-registry?serverName=<server-name>` 打开对应 MCP registry 页面。

#### 方式二：Raw config

直接编辑：

```text
~/.codeium/mcp_config.json
```

添加：

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

Devin Desktop 的 Cascade 兼容原 Windsurf MCP 配置，支持 `stdio`、Streamable HTTP 和 SSE。本项目使用本地 stdio server，因此不要把真实 Bilibili Cookie 写进该配置文件；凭证请用 `bilibili-mcp setup` 或环境变量配置。

### Grok Build

使用 Grok Build CLI 添加本地 stdio server：

```bash
grok mcp add bilibili-mcp -- npx -y @xzxzzx/bilibili-mcp@latest
grok mcp doctor
```

用户级配置保存在 `~/.grok/config.toml`；如需项目级配置，给 `grok mcp add` 添加 `--scope project`。参见 [Grok Build MCP 官方文档](https://docs.x.ai/build/features/mcp-servers)。

### GitHub Copilot CLI

GitHub Copilot CLI 可在交互模式里使用 `/mcp add` 添加 MCP server。按表单选择 `STDIO` 或 `Local`，然后填入：

- Server Name: `bilibili-mcp`
- Command: `npx`
- Args: `-y @xzxzzx/bilibili-mcp`

也可以编辑用户级配置：

```text
~/.copilot/mcp-config.json
```

添加：

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

项目级配置可用 `.mcp.json` 或 `.github/mcp.json`，并且会优先于用户级同名 server。进入 Copilot CLI 后可用 `/mcp show` 查看状态。

### 文心快码（Baidu Comate）

在文心快码的 Zulu 页面点击标题栏右侧更多按钮 → MCP → 手动配置。用户级配置位于 `~/.comate/mcp.json`，项目级配置位于 `.comate/mcp.json`。加入：

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

保存后回到 MCP 的已安装列表确认连接，并在需要使用它的 Agent 中启用该 server。参见[文心快码 MCP 官方文档](https://comate.baidu.com/docs/IDE%E5%8A%9F%E8%83%BD/MCP/)。

### Warp

在 Warp Settings → AI → MCP Servers 中点击 + Add，粘贴下面的 JSON；也可以写入用户级 `~/.warp/.mcp.json` 或项目级 `.warp/.mcp.json`：

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

项目级 server 首次启动需要确认信任。参见 [Warp MCP 官方文档](https://docs.warp.dev/agent-platform/capabilities/mcp/)。

### Factory Droid

使用 Droid CLI 添加本地 stdio server：

```bash
droid mcp add bilibili-mcp "npx -y @xzxzzx/bilibili-mcp@latest" --type stdio
```

进入 Droid 后运行 `/mcp` 检查状态。用户级配置保存在 `~/.factory/mcp.json`；不要把真实 Cookie 写进项目级 `.factory/mcp.json`。参见 [Factory Droid MCP 官方文档](https://docs.factory.ai/cli/configuration/mcp)。

### JetBrains AI Assistant

在 JetBrains IDE 中打开 Settings → Tools → AI Assistant → Model Context Protocol (MCP)，点击 Add，选择 JSON configuration，并粘贴：

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

按需要选择全局或当前项目级别，保存后点击 Apply，并在 Status 列确认连接成功。

### Amazon Q Developer

在 VS Code 或 JetBrains 中打开 Q Developer → Chat，点击 tools 图标和 `+`，选择 global 或 local scope，再填写：

- Name: `bilibili-mcp`
- Transport: `stdio`
- Command: `npx`
- Arguments: `-y`、`@xzxzzx/bilibili-mcp@latest`

保存后检查 MCP Servers 面板中的连接状态和工具权限。当前 GUI 会分别写入全局 `~/.aws/amazonq/default.json` 或项目级 `.amazonq/default.json`；已有旧版 `mcp.json` 可继续兼容，但新配置优先使用 GUI。

### Augment Code / Auggie CLI

使用 Auggie CLI 添加用户级 stdio server：

```bash
auggie mcp add bilibili-mcp -- npx -y @xzxzzx/bilibili-mcp@latest
auggie mcp list
```

配置保存在 `~/.augment/settings.json`。如需只对当前项目生效，可在 `mcp add` 后添加 `--local` 或 `--project`。参见 [Auggie MCP 官方文档](https://docs.augmentcode.com/cli/integrations)。

### Amp

在用户级 `~/.config/amp/settings.json`，或项目级 `.amp/settings.json` 中加入：

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

项目级 MCP server 首次运行需要批准。参见 [Amp MCP 官方手册](https://ampcode.com/manual/mcp.md)。

### Goose

运行 `goose configure`，依次选择 Add Extension → Command-Line Extension，然后填写：

- Name: `Bilibili MCP`
- Command: `npx -y @xzxzzx/bilibili-mcp@latest`
- Environment variables: `No`

Goose Desktop 也可以在 Extensions → Add custom extension 中选择 Standard IO 并填写同一命令。保存后确认该 extension 已启用。

### CodeFlicker

打开 CodeFlicker Settings → MCP 管理 → MCP 配置，点击手动配置并加入：

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

保存后确认连接状态，并在 Agent 模式的 MCP 按钮中启用。参见 [CodeFlicker MCP 官方文档](https://www.codeflicker.ai/docs/feats/corefeat/MCP.html)。

### CodeArts Agent

在 CodeArts Agent IDE 中打开 Settings → MCP → Configure MCP，编辑打开的 `mcp_settings.json`：

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

保存并等待 server 启动，然后在聊天面板切换到 Agent 模式使用。参见 [CodeArts Agent MCP 官方文档](https://support.huaweicloud.com/intl/en-us/usermanual-codeartsagent/codeartsagent_ug_0010.html)。

### Mistral Vibe

编辑用户级 `~/.vibe/config.toml`，或受信任项目中的 `.vibe/config.toml`，加入：

```toml
[[mcp_servers]]
name = "bilibili-mcp"
transport = "stdio"
command = "npx"
args = ["-y", "@xzxzzx/bilibili-mcp@latest"]
```

启动 Vibe 后使用 `/mcp` 检查 server；不要把真实 Cookie 写入 `config.toml`。

### Oh My Pi

Oh My Pi (`omp`) 原生支持 MCP，优先使用 OMP 专属配置文件：

- 项目级：`.omp/mcp.json`
- 用户级：`~/.omp/agent/mcp.json`

也可以使用可被其他 MCP client 复用的项目根配置：

- `mcp.json`
- `.mcp.json`

添加：

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

也可以在 OMP 会话中使用引导式配置：

```text
/mcp add
```

修改配置后使用：

```text
/mcp reload
/mcp list
/mcp test bilibili-mcp
```

OMP 支持 `stdio`、`http` 和 `sse` MCP。不要在 `env`、`args` 或配置文件中写真实 Cookie。

### Zed

Zed 使用 `context_servers` 配置 MCP，不使用 `mcpServers`。可以通过 Settings → AI → MCP Servers 添加自定义 server，也可以直接编辑 `settings.json`。

#### 方式一：MCP Servers UI

打开 Settings → AI → MCP Servers，点击 Add Custom Server，填入本项目的 stdio server 配置。

配置后，在 MCP Servers 列表中查看 server 名称旁边的状态圆点；绿色表示 server active。

#### 方式二：settings.json

用户级设置可通过 Zed 的 `zed: open settings` 打开。项目级设置可写入：

```text
.zed/settings.json
```

添加：

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

#### 方式三：Zed extension

Zed 也支持以 extension 的方式安装 MCP server。通用自定义 server 用上面的 `context_servers` 更直接；如果未来本项目发布 Zed MCP extension，再改用 extension 安装。

Zed 支持 MCP Tools 和 Prompts，也支持远程 MCP；远程 server 使用 `url` 和可选 `headers`。本项目是本地 stdio server，不要在 Zed 配置里写真实 Bilibili Cookie。

### Cherry Studio

Cherry Studio 在 Settings → MCP Server 中添加 MCP server。添加本项目时选择 `STDIO`：

- Name: `bilibili-mcp`
- Type: `STDIO`
- Command: `npx`
- Parameters: `-y @xzxzzx/bilibili-mcp`

保存后，Cherry Studio 会启动该 MCP server；在聊天窗口中启用对应 MCP server 后即可调用工具。

### LobeHub / LobeChat

LobeChat Desktop 支持导入 MCP server JSON。打开：

```text
Settings → Default Agent → Plugin Settings → Custom Plugins → Quick JSON Configuration Import
```

粘贴：

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

安装后，在对应 Agent 的插件设置中启用该 MCP server。不要把真实 Cookie 写进 LobeChat 配置；凭证请通过本项目 CLI 或环境变量配置。

### Crush

Crush 支持项目级和用户级 JSON 配置，MCP server 写在 `mcp` 对象下。

配置优先级：

- 项目级：`.crush.json`
- 项目级：`crush.json`
- 用户级：`~/.config/crush/crush.json`

添加：

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

Crush 也支持 HTTP 和 SSE MCP。不要在 `env` 或 `args` 中写真实 Cookie；凭证请使用本项目的 CLI 向导或环境变量。

### DeepSeek-TUI

DeepSeek-TUI 同时是 MCP client 和 MCP server。作为 MCP client 时，可用 `deepseek mcp add` 添加本项目：

```bash
deepseek mcp add bilibili-mcp -- npx -y @xzxzzx/bilibili-mcp@latest
```

也可以编辑：

```text
~/.deepseek/mcp.json
```

添加：

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

可用 `deepseek mcp list` 和 `deepseek mcp validate` 检查配置。DeepSeek-TUI 暴露的 MCP 工具通常以 `mcp_<server>_<tool>` 形式出现。

### Deep Code

Deep Code 使用 `~/.deepcode/settings.json` 配置 MCP server。把 `bilibili-mcp` 加到 `mcpServers`：

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

Deep Code 文档说明 `command` 为 `npx` 时会自动补充 `-y`。配置后启动 `deepcode`，输入 `/mcp` 查看 MCP server 状态和可用工具。

### Reasonix

Reasonix 支持原生 MCP。最简单的方式是启动时传入 `--mcp`：

```bash
npx reasonix code --mcp "bilibili=npx -y @xzxzzx/bilibili-mcp@latest"
```

也可以编辑全局配置：

```text
~/.reasonix/config.json
```

在 `mcp` 数组中添加：

```json
{
  "mcp": [
    "bilibili=npx -y @xzxzzx/bilibili-mcp@latest"
  ]
}
```

Reasonix 的格式是 `name=command arg1 arg2`。如果需要项目级覆盖，可放在项目的 `.reasonix/` 下。

### AstrBot

AstrBot 通过 WebUI 管理 MCP。先确保 AstrBot 运行环境可使用 `npm` 和 `node`，然后在 WebUI 的 MCP 服务器管理入口添加本地 MCP server：

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

如果 AstrBot 运行在 Docker 中，需要确保容器内已安装 Node.js / npm，且容器能访问运行 MCP server 所需的网络。

### nanobot

nanobot 的配置文件是：

```text
~/.nanobot/config.json
```

在 `tools.mcpServers` 下添加：

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

nanobot 的 MCP 配置兼容 Claude Desktop / Cursor 风格；也支持远程 MCP 的 `url` 和 `headers`。凭证仍应由本项目 CLI 或环境变量管理，不要写入 nanobot 配置。

## 凭证配置与验证

为了稳定获取视频搜索、字幕、转录和评论，请使用自己的 Bilibili 登录 Cookie。公开视频元数据在未登录时可能仍可用。

### 从浏览器获取凭证字段

1. 用自己的账号登录 [https://www.bilibili.com](https://www.bilibili.com)。
2. 打开浏览器开发者工具（`F12`），找到 Cookies：
   - Chrome / Edge：**Application** → **Storage** → **Cookies** → `https://www.bilibili.com`
   - Firefox：**Storage** → **Cookies** → `https://www.bilibili.com`
3. 只复制 `SESSDATA`、`bili_jct` 和 `DedeUserID` 的精确值。
4. 如果找不到，刷新已登录的 Bilibili 页面，确认选中的域是 `https://www.bilibili.com`。
5. 将值只粘贴到本地 `setup` 的隐藏输入提示符中。绝不粘贴到聊天、截图、客户端配置、Issue、PR、日志或示例代码中。

### 推荐：本地交互式配置

```bash
npx -y @xzxzzx/bilibili-mcp@latest setup
npx -y @xzxzzx/bilibili-mcp@latest check
```

- `setup` 在本地终端交互式收集 `SESSDATA`、`bili_jct` 和 `DedeUserID`，输入不会回显。未配置凭证时自动引导配置，已配置时显示当前状态。
- `config` 同样提供交互式配置，但不会检测已有凭证；适合需要强制重配的场景。
- 凭证保存在本机全局配置中，不会写入项目或 MCP 客户端配置。
- `check` 只确认当前进程能够加载凭证，不代表 Bilibili 登录仍然有效。
- 凭证配置完成后，`setup` 会询问是否安装可选的本地 ASR 语音识别模型（默认为否 `[y/N]`）。

`doctor --json` 是纯本地诊断工具，退出码 `0/1/2` 分别表示正常/需要配置或凭证不可加载/内部错误。它不发起网络请求，不能替代 `check_bilibili_credentials` 的实时登录验证。Agent 或非交互环境可使用：

```bash
npx -y @xzxzzx/bilibili-mcp@latest doctor --json
```

如果已全局安装，也可以运行：

```bash
bilibili-mcp setup
bilibili-mcp check
```

### 可选 ASR 语音识别模型安装

完成凭证配置后，`setup` 会询问是否安装可选的本地 ASR 模型（默认为否 `[y/N]`）。

- 选择 Yes 后，会显示三个可选模型：
  - `1. tiny`（约 78.2 MB）— 最小体积
  - `2. base`（约 148 MB）
  - `3. small`（约 486 MB）— [推荐]，Enter 默认选择
- 输入数字 `1/2/3` 或名称 `tiny/base/small` 选择；无效输入会重新提示，不会启动安装。
- runtime 固定为 `faster-whisper==1.2.1`，加上运行时库的总磁盘开销。
- 需要本机装有 Python 3.9+。可通过设置 `BILIBILI_ASR_PYTHON` 环境变量指定 Python 可执行文件。
- 安装内容存放在用户管理的 `~/.bilibili-mcp/asr/` 中；不修改系统 Python。
- 同一目录只保留一个活跃模型，切换模型时清空旧的就绪状态。
- 安装完成后通过 CPU INT8 加载模型进行验证；不需要系统 FFmpeg（PyAV 已捆绑 FFmpeg 库）。
- 安装失败不会留下就绪标记；已下载的部分文件保留，重新运行 `setup` 可从断点续传。
- `doctor --json` 的 `asr.status` 和 `asr.model` 字段为纯信息字段，不影响凭证退出状态。
- MCP 调用不会下载或切换模型；仅使用 `doctor --json` 显示 ready 的当前模型。
- `get_video_transcript` 只有显式设置 `fallback_to_asr: true` 且确认无可用字幕时才运行 ASR；原生字幕、Cookie/API/网络错误都不会触发。
- ASR 只处理一个已解析 Part，单 Part 最长 2 小时、临时音频最多 128 MiB，同时只允许一个转录任务且不排队。
- Cookie 只用于 Bilibili 播放 API，不发送给临时 CDN 或 Python；签名地址不写入结果/日志，临时目录在成功、失败和超时后清理。

### Docker、本地开发或受控运行环境

也可以在 MCP server 的运行环境中提供以下变量：

| 变量 | 内容 |
|---|---|
| `BILIBILI_SESSDATA` | 自己登录会话 Cookie 中的 `SESSDATA` |
| `BILIBILI_BILI_JCT` | 自己登录会话 Cookie 中的 `bili_jct` |
| `BILIBILI_DEDEUSERID` | 自己的 Bilibili 用户 ID |

进程继承的环境变量可以正常工作；但推荐的 `npx` 路径不会自动加载项目目录下的 `.env` 文件。`setup` 是正常的安装路径；继承的进程变量仅在受控 shell、服务或密钥运行时提供时才有效。本地 `.env` 示例适用于源码 `npm start` / `dist/index.js`，或显式加载 `.env` 的运行时。

本地 `.env` 示例：

```env
BILIBILI_SESSDATA=<your_sessdata>
BILIBILI_BILI_JCT=<your_bili_jct>
BILIBILI_DEDEUSERID=<your_dedeuserid>
```

只从自己的 Bilibili 登录会话获取 Cookie。不要把真实值粘贴到聊天、共享配置、README、Issue、PR、源码、测试或日志中，也不要提交 `.env`。如果 Cookie 曾泄露，请立即在 Bilibili 账号设置中使旧会话失效。

### 重连并验证登录

1. 完成凭证配置后，重启客户端或重连 `bilibili-mcp`，让新进程重新加载凭证。
2. 需要字段说明时，调用 `get_credential_setup_instructions`。
3. 必须调用 `check_bilibili_credentials` 验证登录。只有 `configured: true` 且 `logged_in: true` 才表示成功。
4. 需要确认版本时，再调用 `check_mcp_update`；版本检查不能替代登录验证。

## 可选运行时配置

这些变量由 MCP server 在进程启动时读取；修改后需要重启客户端或重连 server。

| 变量 | 默认值 | 用途 |
|---|---:|---|
| `BILIBILI_RATE_LIMIT_MS` | `500` | 两次 Bilibili API 请求启动之间的最小间隔（毫秒） |
| `BILIBILI_REQUEST_TIMEOUT_MS` | `10000` | 单次请求超时（毫秒） |
| `BILIBILI_CACHE_SIZE` | `100` | 内存缓存条目上限 |
| `USER_AGENT` | 项目默认值 | 覆盖请求使用的 User-Agent |
| `BILIBILI_MCP_DEBUG` | 未启用 | 设为 `1` 时向 `stderr` 输出经过凭证脱敏的 debug 日志 |

三个数值变量必须是完整的十进制正安全整数；空值、部分数字、`0`、负数及非安全整数会让 server 以配置错误拒绝启动。`BILIBILI_RATE_LIMIT_MS` 和 `BILIBILI_REQUEST_TIMEOUT_MS` 还不得超过 Node.js 计时器上限 `2147483647`。

请求重试、缓存和错误语义的完整说明见[工具参考：请求控制与缓存](./tool-reference.md#请求控制与缓存)。

## 从源码开发

```bash
git clone https://github.com/XZXZZX-Ai/bilibili-mcp.git
cd bilibili-mcp
npm install
npm run build
npm test
```

其他开发命令及 stdio 日志约束见[项目 README](../README.md)的“开发”部分。
