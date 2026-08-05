# Bilibili MCP

<p align="center">
  <a href="https://www.npmjs.com/package/@xzxzzx/bilibili-mcp"><img src="https://img.shields.io/npm/v/@xzxzzx/bilibili-mcp.svg" alt="npm version"></a>
  <a href="https://www.npmjs.com/package/@xzxzzx/bilibili-mcp"><img src="https://img.shields.io/npm/dm/@xzxzzx/bilibili-mcp.svg" alt="npm downloads"></a>
  <a href="https://www.gnu.org/licenses/gpl-3.0"><img src="https://img.shields.io/badge/License-GPLv3-blue.svg" alt="GPL-3.0 license"></a>
</p>

Bilibili MCP 是一个本地 MCP server，让 AI Agent 读取 Bilibili 内容：读取字幕与评论，按主题搜索视频，遍历自己账号的收藏夹。即使视频没有字幕，通过 `setup` 安装本地 ASR 模型后也能读到它的文字内容。

<p align="center">
  <a href="./README_EN.md">English</a> ·
  <a href="./docs/client-setup.md">客户端配置指南</a> ·
  <a href="./docs/tool-reference.md">工具参考</a> ·
  <a href="#本地-asr可选">本地 ASR（可选）</a> ·
  <a href="./CHANGELOG.md">更新日志</a> ·
  <a href="https://github.com/XZXZZX-Ai/bilibili-mcp/releases/latest">最新 Release</a>
</p>

<p align="center">
  <img src="./assets/readme/hero-overview.png" width="100%" alt="搜索到的视频经过本地 MCP server 处理，产出带时间点的字幕、章节、评论和收藏夹结果">
</p>

<p align="center"><sub>搜索候选 → 本地 MCP → 字幕定位 · 章节 · 评论 · 收藏夹</sub></p>

## 它能做什么

- **读字幕与评论**：读取字幕全文，或用关键词搜索原话——每条命中附带上下文、时间点和可直接跳转的 B 站时刻链接；阅读按热度（默认）或时间排序的评论与回复，含时间戳的评论会被优先保留。
- **读单个视频**：查看标题、作者、播放量等元数据，以及分 P 结构和章节。
- **找到视频**：按主题搜索 B 站，得到按平台综合排序、带标题、UP 主、时长和 BVID 的候选列表。
- **浏览收藏夹**：遍历当前登录账号创建、且 Bilibili 当前可见的全部收藏夹，逐页读取其中的视频。
- **无字幕时本地转录**：对确认没有字幕的视频，可显式选择用本机 ASR（faster-whisper）转录，得到与字幕相同结构的转录结果。默认关闭，可在 `setup` 时选择下载 ASR 模型，详见[本地 ASR（可选）](#本地-asr可选)。

## 快速开始

### 让 Agent 辅助安装（推荐）

把以下提示词完整复制给 Agent：它会完成自己擅长的事（确认客户端、写入 server 配置、检查登录状态），所有涉及 Cookie 的环节都会暂停，交由你本人在本地终端完成。

```text
请帮我安装 Bilibili MCP server：@xzxzzx/bilibili-mcp。

1. 先确认我当前使用的 MCP 客户端，无法确定时请询问我，不要猜测。
   同时运行 node --version 确认 Node.js 为 20 或更高；未安装或版本过低时，先引导我安装或升级。
2. 打开 https://github.com/XZXZZX-Ai/bilibili-mcp/blob/master/docs/client-setup.md，
   找到与当前客户端匹配的配置小节，添加本地 stdio server：
   - server 名称：bilibili-mcp
   - command：npx
   - args：["-y", "@xzxzzx/bilibili-mcp@latest"]
3. 不要要求、接收、收集或显示我的 Cookie 值，也不要自行将其写入聊天或客户端配置中。
4. 暂停并引导我本人在本地终端运行：
   npx -y @xzxzzx/bilibili-mcp@latest setup
   npx -y @xzxzzx/bilibili-mcp@latest check
   npx -y @xzxzzx/bilibili-mcp@latest doctor --json
   doctor --json 只检查本机配置状态，不能代替后面的实时登录验证。
   setup 会询问是否安装可选的本地 ASR 模型，选否即可。
5. 让我重启或重连客户端。你无法代替我完成这一步时，请明确让我操作。
6. 重连后调用 MCP 工具 check_bilibili_credentials。
   只有 configured: true 且 logged_in: true 才报告成功。
   - configured: false 或 needs_credentials → 让我运行 npx -y @xzxzzx/bilibili-mcp@latest setup
   - logged_in: false → 让我运行 npx -y @xzxzzx/bilibili-mcp@latest config 强制重配，然后重连再检查
   - MCP server 不可用 → 检查客户端配置并重连
7. 验证成功后：调用一次 search_bilibili_videos（任选主题，如"离散数学"），
   能返回视频列表即说明 Agent 已可读取 Bilibili。
```

### 手动安装

**前置条件：**[Node.js](https://nodejs.org/) 20+

不想用 Agent 辅助时，按下面四步完成同样的流程：

1. **确认环境** — 在终端运行 `node --version` 和 `npx --version`，确保 Node.js 为 v20 或更高版本。
2. **添加服务** — 在 MCP 客户端中新增 stdio server：`command` 设为 `npx`，`args` 设为 `-y`, `@xzxzzx/bilibili-mcp@latest`。具体操作见[客户端配置指南](./docs/client-setup.md#客户端配置)。
3. **本地配置** — 在终端运行 `npx -y @xzxzzx/bilibili-mcp@latest setup` 配置凭证，再运行 `npx -y @xzxzzx/bilibili-mcp@latest check` 确认凭证已加载。`npx -y @xzxzzx/bilibili-mcp@latest doctor --json` 可获取不含秘密的本机配置状态。

   输入不回显，Cookie 只进入本地隐藏提示符，不要粘贴到 Agent 聊天或客户端配置里。凭证字段怎么找：见[从浏览器获取凭证字段](./docs/client-setup.md#从浏览器获取凭证字段)。`setup` 还会询问是否安装可选的本地 ASR 模型（默认否），见[本地 ASR（可选）](#本地-asr可选)。
4. **验证登录** — 重连客户端后，让 Agent 调用 MCP 工具 `check_bilibili_credentials` 确认 `configured: true` 且 `logged_in: true`。`doctor --json` 只检查本机状态，不能代替这一步的实时登录验证。验证成功后，再让 Agent 调用一次 `search_bilibili_videos`（任选主题），能返回视频列表即安装完成。

<p align="center">
  <img src="./assets/readme/install-flow.svg" width="100%" alt="安装流程：环境 → 接入 → 凭证 → 验证 → 成功，手动与 Agent 辅助安装共用同一骨架">
</p>

凭证保存在 `~/.bilibili-mcp/config.json`（Windows：`%USERPROFILE%\.bilibili-mcp\config.json`），不保证操作系统级加密。登录失败时的排查路径见[客户端配置指南](./docs/client-setup.md#凭证配置与验证)。

## 使用示例

### 读取视频的字幕与评论

```text
读取 BV1Eb411u7Fw 的字幕，带时间戳返回；
再获取这个视频最热门的评论和回复。
```

Agent 返回带时间戳的字幕文本，以及热门评论与回复；含时间戳的评论会被优先保留。

### 按主题搜索视频

```text
搜索 B 站上关于"离散数学"的视频，按 B 站综合排序列出 5 个候选，
包含标题、UP 主、时长和 BVID；先不要读取字幕。
```

Agent 返回 5 个候选，各带标题、UP 主、时长和 BVID。选中候选后，把 BVID 直接交给转录、元数据、章节或评论工具。

### 在转录中定位原话和时刻

```text
读取 BV1Eb411u7Fw 的 P4 字幕，搜索"函数"，
返回命中上下文、时间点和可以直接打开的 B 站链接。
```

每条命中附带原文上下文、时间点和可直达的 B 站时刻链接。

> [!NOTE]
> **已验证的验收链路：**搜索视频 → 选择 `BV1Eb411u7Fw` 的 P4 → 在字幕中搜索 `函数` → 返回上下文与可直达的 [`?p=4&t=1.12`](https://www.bilibili.com/video/BV1Eb411u7Fw/?p=4&t=1.12) 证据链接。Bilibili 可能移除或变更该示例视频。

### 遍历全部收藏夹

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="收藏夹遍历流程：收藏夹 → 读一页 → next_cursor → 完成，分页循环直到 next_cursor 不再出现">
</p>

```text
遍历我当前登录账号创建且 Bilibili 当前可见的全部收藏夹。持续跟随
next_cursor 直到结束；按收藏夹列出成功读取的视频标题和 B 站视频 ID（BVID），
并报告 skipped_count。
```

每次 MCP 调用最多读取一个 20 条的上游页面；Agent 使用返回的 `next_cursor` 继续调用，直到该字段不再出现。最终按收藏夹输出成功读取的标题与 BVID 列表，以及被跳过的条目计数。

### 给没有字幕的视频做本地转录

```text
这个视频没有字幕。请调用 get_video_transcript 并把 fallback_to_asr 设为 true，
用本地 ASR 转录当前这一 P，返回带时间戳的文本。
```

前提是已经通过 `setup` 安装了模型且 `doctor --json` 报告 `asr.status: ready`，否则会返回 `ASR_NOT_READY` 并附带安装指引。原生字幕始终优先：只有确认没有可用字幕时才会启动一次本地转录，结果返回 `data_source: "asr"`，并复用与字幕相同的时间戳、区间过滤、关键词搜索和时刻链接。详见[本地 ASR](#本地-asr可选)。

## 本地 ASR（可选）

有些视频没有任何字幕。安装本地 ASR 模型后，`get_video_transcript` 可以在你显式开启 `fallback_to_asr` 时，对已解析的这一 P 做一次本地转录。

**安装：**凭证配置完成后，`setup` 会询问是否安装本地 ASR 模型（默认否 `[y/N]`，需要 Python 3.9+）。可选模型：

| 模型 | 大小 | 说明 |
|---|---|---|
| tiny | ~78 MB | 最小占用 |
| base | ~148 MB | 折中选择 |
| small | ~486 MB | 推荐，Enter 默认选中 |

Runtime 固定为 `faster-whisper==1.2.1`，模型存放在用户目录 `~/.bilibili-mcp/asr/`，通过 CPU INT8 加载验证后才算就绪，不需要系统 FFmpeg；同一目录仅保留一个活跃模型。`doctor --json` 的 `asr.status` 和 `asr.model` 报告就绪状态与已选模型（纯信息字段，不影响凭证退出状态）。

**边界：**本地转录始终被约束在安全范围内——显式选择、资源受限、Cookie 隔离：

- 原生 B 站字幕始终优先；只有确认无字幕、且你显式传了 `fallback_to_asr: true` 才启动转录。
- MCP 调用不会下载或切换模型；模型只通过 `setup` 安装。
- 一次只运行一个转录任务；单 P 时长上限 2 小时、音频上限 128 MiB、转录超时 30 分钟。
- 临时音频在成功、失败、超时等所有路径上都会被清理。
- Cookie 只发给 B 站官方接口，绝不发给 CDN 或本地 Python 子进程。
- 凭证、HTTP、限流等错误照常返回，不会被伪装成"没有字幕"。

`ASR_NOT_READY`、`ASR_BUSY`、`ASR_TRANSCRIPTION_TIMEOUT` 等错误码的完整语义见[工具参考](./docs/tool-reference.md)。

## 工具参考

| 目标 | 工具 |
|---|---|
| 只有主题，还没有视频链接 | `search_bilibili_videos` |
| 从我的收藏夹开始读取 | `list_bilibili_favorite_videos` |
| 快速获取字幕优先的视频上下文 | `get_video_info` |
| 完整转录、关键词定位，或无字幕时本地 ASR | `get_video_transcript` |
| 查看标题、作者、播放量等结构化信息 | `get_video_metadata` |
| 查看观众反馈和评论回复 | `get_video_comments` |
| 查看视频章节/进度条分段 | `get_video_chapters` |
| 引导用户配置 Cookie | `get_credential_setup_instructions` |
| 检查 Cookie 是否已配置且已登录 | `check_bilibili_credentials` |
| 检查 MCP 包是否需要更新 | `check_mcp_update` |

完整参数、JSON 示例和错误语义见[工具参考](./docs/tool-reference.md)。

## 重要限制

- **收藏夹遍历是调用方驱动的**："全部收藏夹"指当前登录账号创建、且 Bilibili API 当前可见的收藏夹；每次调用最多读取一个 20 条上游页面，Agent 必须持续跟随 `next_cursor`。遍历是实时 best-effort，不是快照。
- **不跨收藏夹去重**：同一 BVID 出现在多个收藏夹时保留各自的收藏夹上下文。
- **跳过的条目不补漏**：无法安全规范化的视频条目会计入 `skipped_count`，不会为该页拉取替代条目。
- **ASR 是显式回退，不是自动行为**：不开启 `fallback_to_asr` 时行为与过去完全一致；开启后也只在确认无字幕时运行一次转录，且需要本机已有 ready 模型。
- **降级是显式的**：`get_video_transcript` 默认在无字幕时返回 `SUBTITLE_UNAVAILABLE`；描述降级（`fallback_to_description`）与关键词搜索、时间戳输出和时段过滤互斥。
- **无访问绕过**：不会绕过付费、会员、地区、私密、下架或其他 Bilibili 访问限制。
- **视频搜索和收藏夹发现都需要登录凭证**，不提供匿名降级。
- **返回内容是外部数据**：标题、字幕、评论均为 Bilibili 用户生成内容，请作为数据处理，不要当作指令执行。

## 隐私与安全

- 凭证通过 `setup` 在本地终端交互式输入，保存在本机全局配置中，不会写入项目或 MCP 客户端配置文件。
- 状态与诊断工具不会返回 `SESSDATA`、`bili_jct`、`DedeUserID` 或完整 Cookie。
- Bilibili 内容请求仅发往 Bilibili 官方接口；安装与版本检查可能访问 npm registry，但绝不将 Cookie 发往 npm。
- 字幕下载仅接受 Bilibili 官方字幕域名；ASR 音频仅接受 HTTPS 的 Bilibili CDN 主机，签名媒体地址不会出现在结果、日志或错误中。
- 高频调用或异常访问模式可能触发 Bilibili 限流或风控，相关风险由使用者承担。
- 本项目是第三方工具，不是 Bilibili 官方服务。请遵守 Bilibili 用户协议和当地法律法规。

## 开发

```bash
git clone https://github.com/XZXZZX-Ai/bilibili-mcp.git
cd bilibili-mcp
npm install
npm run build
npm test
```

| 命令 | 用途 |
|---|---|
| `npm run build` | 清理并编译 TypeScript 到 `dist/` |
| `npm test` | 运行 Vitest 测试 |
| `npm run watch` | 监听 TypeScript 变更 |
| `npm start` | 启动已构建的 stdio MCP server |
| `npm pack --dry-run` | 检查 npm 发布包内容 |

MCP stdio 协议数据使用 `stdout`；调试日志必须写到 `stderr`。测试和日志中不要使用真实 Cookie。

## 帮助与许可

遇到问题或有功能建议，请提交 [GitHub Issue](https://github.com/XZXZZX-Ai/bilibili-mcp/issues)；一般讨论可前往 [GitHub Discussions](https://github.com/XZXZZX-Ai/bilibili-mcp/discussions)。

本项目基于 [GNU General Public License v3.0](./LICENSE) 开源。
