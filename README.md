<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="Bilibili MCP：自动读取当前账号的全部收藏夹，并通过 next_cursor 逐页遍历视频">
</p>

# Bilibili MCP

[![MCP Toplist](https://mcptoplist.com/badge/glama%2FXZXZZX-Ai%2Fbilibili-mcp.svg)](https://mcptoplist.com/server/glama%2FXZXZZX-Ai%2Fbilibili-mcp)

<p align="center">
  <a href="https://www.npmjs.com/package/@xzxzzx/bilibili-mcp"><img src="https://img.shields.io/npm/v/@xzxzzx/bilibili-mcp.svg" alt="npm version"></a>
  <a href="https://www.npmjs.com/package/@xzxzzx/bilibili-mcp"><img src="https://img.shields.io/npm/dm/@xzxzzx/bilibili-mcp.svg" alt="npm downloads"></a>
  <a href="https://www.gnu.org/licenses/gpl-3.0"><img src="https://img.shields.io/badge/License-GPLv3-blue.svg" alt="GPL-3.0 license"></a>
</p>

<p align="center">
  让 Codex、Claude、Cursor 等 AI 客户端从 Bilibili 主题或当前账号的收藏夹出发，获得可继续调用的 BVID、字幕上下文和可直达播放时刻的证据链接。
</p>

<p align="center">
  <a href="./README_EN.md">English</a> ·
  <a href="./docs/client-setup.md">全部 Agent / 客户端配置</a> ·
  <a href="./docs/tool-reference.md">工具参考</a> ·
  <a href="./CHANGELOG.md">更新日志</a> ·
  <a href="https://www.npmjs.com/package/@xzxzzx/bilibili-mcp">npm</a> ·
  <a href="https://github.com/XZXZZX-Ai/bilibili-mcp/releases/latest">最新 Release</a>
</p>

## 两个入口，一条证据链

- **从我的收藏夹开始**：首次调用无需 Folder ID；Agent 每次读取一个最多 20 条的上游页面，并把返回的 `next_cursor` 原样用于下一次调用，直到响应不再包含它。
- **从一个主题开始**：按关键词返回最多 10 个普通视频候选，不自动抓取候选的字幕或评论。
- **拿到 BVID 之后**：继续读取字幕、元数据、章节或热门评论；关键词命中可返回直达播放时刻的 `timestamp_url`。

> [!NOTE]
> **真实验收链路：**搜索视频 → 选择 `BV1Eb411u7Fw` 的 P4 → 在字幕中搜索“函数” → 返回上下文与可直达的 [`?p=4&t=1.12`](https://www.bilibili.com/video/BV1Eb411u7Fw/?p=4&t=1.12) 证据链接。视频搜索、收藏夹分页和转录的成功结果都同时提供兼容文本与 MCP `structuredContent`。

## 先让 Agent 帮你接入

Agent 安装提示词、全部客户端配置位置、CLI / JSON / TOML 示例、Cookie 配置与登录验证，都集中在唯一完整入口：

### [打开 Agent / 客户端安装指南 →](./docs/client-setup.md)

安装完成后，可以直接测试收藏夹遍历：

```text
读取我当前登录账号创建的全部收藏夹。每次拿到 next_cursor 就继续调用，
直到响应不再包含 next_cursor；按收藏夹列出视频标题和 BVID，不要生成笔记。
```

## 10 个工具，分成三层

### 发现入口

`search_bilibili_videos` · `list_bilibili_favorite_videos`

从主题或当前账号的全部收藏夹获得 BVID。

### 内容证据

`get_video_transcript` · `get_video_info` · `get_video_metadata` · `get_video_chapters` · `get_video_comments`

读取字幕、时间定位、视频信息、章节和观众反馈。

### 本机助手

`get_credential_setup_instructions` · `check_bilibili_credentials` · `check_mcp_update`

安全配置凭证、确认登录并检查版本。

完整参数、JSON 示例、结构化错误和请求控制见[工具参考](./docs/tool-reference.md)。

## 设计重点

- **Bilibili 原生**：保留多 P、平台章节、热门评论和收藏夹成员关系，不把项目扩成通用下载器。
- **证据优先**：字幕支持语言偏好、时间戳、时间区间与关键词上下文；命中项可以直接打开对应播放时刻。
- **按需调用**：收藏夹工具只返回 Folder 上下文和视频条目，不自动生成笔记，也不预取字幕、评论或章节。
- **凭证留在本机**：状态工具不会返回 `SESSDATA`、`bili_jct`、`DedeUserID` 或完整 Cookie。

## 行为边界

- “全部收藏夹”指当前登录账号创建、且 Bilibili API 当前可见的 Folder；遍历是实时 best-effort，不是快照。
- 每次收藏夹调用最多读取一个 20 条上游页面。Agent 必须持续跟随 `next_cursor`；失效或无法安全规范化的条目会计入 `skipped_count`。
- 视频搜索和收藏夹发现都要求有效登录凭证，不提供匿名降级。
- `get_video_transcript` 默认在无字幕时返回 `SUBTITLE_UNAVAILABLE`；只有显式设置 `fallback_to_description: true` 才会退回简介，时间定位与关键词搜索不会静默退回简介。
- 章节只使用 Bilibili 创作者或平台数据；项目不会绕过付费、会员、地区、私密、下架或其他访问限制。
- 所有请求由用户本机发起；本项目是第三方工具，不是 Bilibili 官方服务。

## 开发

源码开发环境的安装步骤也集中在[完整安装指南：从源码开发](./docs/client-setup.md#从源码开发)。

| 命令 | 用途 |
|---|---|
| `npm run build` | 清理并编译 TypeScript 到 `dist/` |
| `npm test` | 运行 Vitest 测试 |
| `npm run watch` | 监听 TypeScript 变更 |
| `npm start` | 启动已构建的 stdio MCP server |
| `npm pack --dry-run` | 检查 npm 发布包内容 |

MCP stdio 协议使用 `stdout`；调试日志必须写到 `stderr`。测试和日志中不要使用真实 Cookie。

## 安全与许可

- 请遵守 Bilibili 用户协议、接口访问规则和当地法律法规，不要用于大规模抓取、商业剥削、绕过权限或其他滥用场景。
- 高频调用、异常访问模式或 Cookie 泄露可能触发限流、风控或账号异常，相关风险由使用者承担。
- 本项目仅向 Bilibili 官方接口发送 Bilibili 凭证，不会把 Cookie 上传到第三方服务；本地配置文件不承诺系统级加密。
- 本项目基于 [GNU General Public License v3.0](./LICENSE) 开源。

## 反馈

遇到问题或有功能建议，请提交 [GitHub Issue](https://github.com/XZXZZX-Ai/bilibili-mcp/issues)；一般讨论可前往 [GitHub Discussions](https://github.com/XZXZZX-Ai/bilibili-mcp/discussions)。
