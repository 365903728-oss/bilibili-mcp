# Bilibili MCP 工具参考

[返回中文 README](../README.md) · [English](./tool-reference.en.md) · [客户端接入](./client-setup.md)

本页保存 9 个 MCP 工具的详细行为、参数、示例、错误结构和运行时请求控制。安装与首次调用请先看项目 README。

## 快速选择

| 目标 | 推荐工具 | 返回重点 |
|---|---|---|
| 只有主题，还没有视频链接 | `search_bilibili_videos` | 最多 10 个普通视频候选及可继续调用的 BVID；不自动抓取字幕或评论 |
| 想让 AI 总结一个视频 | `get_video_info` | 字幕优先；无字幕时返回标题、简介、标签 |
| 只想拿完整转录文本或关键词定位 | `get_video_transcript` | 纯字幕文本、语言、数据来源；支持时间戳、区间过滤和关键词搜索 |
| 想查看标题、作者、播放量等结构化信息 | `get_video_metadata` | 标题、作者、时长、发布时间、标签、统计数据、多P分集列表（`pages`） |
| 想看观众反馈和热门评论 | `get_video_comments` | 热门评论、时间戳评论、可选回复 |
| 想看视频章节/进度条分段 | `get_video_chapters` | 章节标题、起止时间；无章节时返回空列表 |
| 让 agent 引导用户配置 Cookie | `get_credential_setup_instructions` | 安全配置步骤、推荐命令、注意事项 |
| 检查 Cookie 是否已配置/登录 | `check_bilibili_credentials` | configured、source、logged_in、next_steps、next_steps_zh |
| 检查 MCP 包是否需要更新 | `check_mcp_update` | current_version、latest_version、update_available、notes_zh、更新命令 |

## 工具能力与行为边界

### 1. 视频总结 (`get_video_info`)
- 优先获取视频的 CC 或 AI 字幕
- 无字幕时自动降级为视频标题、简介和标签
- 支持多语言字幕选择（默认优先简体中文）
- 可手动指定偏好字幕语言（如 `en`, `zh-Hant` 等）

### 2. 评论总结 (`get_video_comments`)
- 获取视频热门评论，辅助判断视频真实口碑
- 自动过滤表情占位符（如 `[doge]`）以保持文本整洁
- 优先保留包含时间戳的评论（如 `05:20`），方便定位高能片段
- 支持两种详细程度：
  - `brief`: 10 条热门评论速览
  - `detailed`: 20 条热门评论 + 高赞连带回复
- 可选参数：
  - `limit`: 显式评论数量 `1-50`，覆盖 `detail_level` 的默认数量
  - `sort`: 排序方式 `"hot"`（按热度，默认）或 `"time"`（按时间）
  - `include_replies`: 是否包含高赞回复（默认 `true`）

### 3. 视频转录 (`get_video_transcript`)
- 返回纯字幕文本，按行合并
- 支持指定偏好语言（默认按 `zh-Hans` > `ai-zh` > `zh-CN` > `zh-Hant` > `en` 优先级选择）
- 支持多P分集选择、时间戳输出和时间区间过滤
- 支持可选关键词搜索：返回带上下文的时间戳匹配列表（大小写不敏感字面匹配）
- 成功调用会同时返回向后兼容的格式化 JSON 文本和内容相同的 MCP `structuredContent`
- 可选参数：
  - `preferred_lang`: 偏好字幕语言代码
  - `fallback_to_description`: 字幕不可用时是否降级为视频描述（默认 `false`）
  - `page`: 多P视频分集编号（从1开始的正整数）
  - `include_timestamps`: 每行添加 `[HH:MM:SS --> HH:MM:SS]` 时间戳前缀
  - `start_seconds` / `end_seconds`: 只返回与此区间重叠的字幕段
  - `query`: 关键词搜索词（最多100字符，大小写不敏感字面匹配）
  - `max_matches`: 最大匹配数（1-20，默认10）
  - `context_segments`: 每个匹配前后的上下文段数（0-5，默认1）
- 默认不降级：无字幕时返回 `SUBTITLE_UNAVAILABLE` 错误
- 时间戳/区间过滤/关键词搜索与描述降级不兼容：请求 timed 输出或搜索时不会静默降级
- Cookie 失效时始终返回 `COOKIE_EXPIRED`，不静默降级
- 证据链接：
  - 成功结果根字段 `source_url`：指向当前选中 Part 的 Bilibili 浏览器源 URL（多 P 视频附加 `p=<page>`）
  - 关键词搜索的每个 `matches[]` 项附带 `timestamp_url`：在 `source_url` 基础上叠加 `t=<start_seconds>`，直达命中字幕的播放时刻

### 4. 视频元数据 (`get_video_metadata`)
- 返回视频标题、作者、时长、发布时间、描述、标签、播放/点赞/投币等统计信息
- 返回多P分集列表（`pages`），含分集编号、CID、标题和时长
- 不获取字幕或评论

### 5. 视频章节 (`get_video_chapters`)
- 返回 Bilibili 创作者/平台定义的视频章节（进度条分段），含章节标题和起止时间
- 无章节时返回空列表（`chapters: []`），不推断章节
- 可选参数 `page`：多P视频分集编号

### 6. 视频发现 (`search_bilibili_videos`)

- 按关键词返回 Bilibili 综合排序的普通视频候选；默认 5 条，最多 10 条。
- 候选只包含可选择和传给现有工具的元数据，不自动获取字幕、评论，也不进行 AI 重排。
- 必须先配置且登录 Bilibili Cookie；成功结果同时提供格式化 JSON 文本和内容相同的 MCP `structuredContent`。

### 7. 凭证助手工具

- `get_credential_setup_instructions`: 返回安全的 Bilibili Cookie 配置命令和说明。AI agent 安装此 MCP 后可调用此工具引导用户完成配置。
- `check_bilibili_credentials`: 检查凭证是否已配置并处于登录状态，不返回任何 Cookie 值。配置缺失或失效时返回下一步操作指引。
- `check_mcp_update`: 检查本地包版本与 npm latest 是否一致，并返回 `npx @latest` 或全局安装的安全更新指引。

### 8. 行为说明与错误处理

- **Cookie 过期智能检测**：当字幕获取为空时自动验证登录状态，区分“无字幕视频”与“凭证失效”，并抛出明确的 `COOKIE_EXPIRED` 错误，避免静默降级。

#### 无 Cookie 行为

- 部分公开视频元数据（`get_video_metadata`）可能在未登录状态下工作。
- 字幕（`get_video_info`、`get_video_transcript`）在未登录时可能无法获取、不完整或返回空结果。
- 评论（`get_video_comments`）在未登录时可能不完整、被限流或返回空列表。
- 视频发现（`search_bilibili_videos`）强制检查已配置且有效的登录凭证；不提供匿名降级。
- 不建议依赖无 Cookie 模式获取字幕或评论。

#### Cookie 凭据来源

- Cookie 凭据应通过 `.env` 文件、环境变量或凭据管理工具提供。
- 支持的环境变量：`BILIBILI_SESSDATA`、`BILIBILI_BILI_JCT`、`BILIBILI_DEDEUSERID`。
- **切勿**在源码、脚本、文档、测试、日志或示例中硬编码 Cookie 值。
- 如果 Cookie 值曾出现在仓库历史中，应尽快到 Bilibili 账号设置中轮换/失效旧 Cookie。

<details>
<summary><strong>查看结构化错误格式与错误码</strong></summary>

所有 MCP 工具的错误响应都使用统一的结构化 payload，同时保留向后兼容的 `error`、`message`、`code`、`next_steps` 字段，并新增中英双语与分类字段：

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

字段含义：

- `error` / `message` / `code` / `next_steps`：向后兼容字段；`next_steps` 与 `next_steps_en` 内容一致。
- `message_en` / `message_zh` / `next_steps_en` / `next_steps_zh`：显式中英文版本，便于客户端按语言渲染。
- `category`：错误分类（`validation` / `credentials` / `content` / `network` / `access` / `rate_limit` / `api` / `unknown`）。
- `retryable`：是否建议自动重试。
- `user_action_required`：是否需要用户介入才能解决。
- `details`：可选的附加信息（如 HTTP 状态码、超时毫秒数、Bilibili API 错误码），不包含 Cookie 或完整 URL。

支持的错误码：

| 错误码 | 含义 | 调用方建议 |
|--------|------|-----------|
| `VALIDATION_ERROR` | 输入参数不合法 | 检查并修正 `bvid_or_url` 或其他参数 |
| `COOKIE_EXPIRED` | Cookie 已失效或未登录 | 用户应更新/轮换 Bilibili 凭据 |
| `SUBTITLE_UNAVAILABLE` | 视频无可用的字幕 | 对 `get_video_transcript` 可重试并设置 `fallback_to_description: true` |
| `NETWORK_ERROR` | 网络请求失败（HTTP 5xx、连接错误等） | 稍后重试；如反复出现请检查网络/代理/防火墙 |
| `NETWORK_TIMEOUT` | 请求 Bilibili 超时 | 稍后重试；如反复出现请检查网络/代理/防火墙 |
| `API_RATE_LIMITED` | 触发 Bilibili API 频率限制（HTTP 429） | 等待一段时间后重试；降低调用频率或调大 `BILIBILI_RATE_LIMIT_MS` |
| `ACCESS_DENIED` | Bilibili 拒绝访问（权限不足、私密、地区限制、已下架等） | 检查视频访问权限，必要时运行凭据检查 |
| `PAID_VIDEO` | 视频可能需要付费、会员或额外权限 | 在 Bilibili 端确认；本 MCP 不会绕过付费或受限访问 |
| `COMMENTS_DISABLED` | 视频评论已关闭或访问受限 | 改用字幕或元数据工具；也可在 Bilibili 页面确认 |
| `BILIBILI_API_ERROR` | 其他 Bilibili API 错误 | 临时问题可稍后重试；持续出现请带错误码反馈 |
| `UNKNOWN_ERROR` | 未知错误 | 稍后重试；反馈时请勿包含 Cookie 或凭据 |

</details>

## 调用示例

> AI 客户端会自动将你的自然语言意图转换为对应的 JSON 调用。

### `get_credential_setup_instructions`

**适合**：agent 安装 MCP server 后，引导用户完成 Cookie 配置。

请求示例：

```json
{
  "name": "get_credential_setup_instructions",
  "arguments": {}
}
```

返回内容：推荐配置命令、全局安装命令、所需 Cookie 字段，以及 `security_notes_en` / `security_notes_zh` 双语安全提醒；不会返回任何 Cookie 值。

### `check_bilibili_credentials`

**适合**：检查当前环境是否已配置 Cookie，以及是否处于登录状态。

请求示例：

```json
{
  "name": "check_bilibili_credentials",
  "arguments": {}
}
```

返回内容：`configured`、`source`（`env` / `global_config` / `none`）、`logged_in`、兼容旧调用方的 `next_steps`，以及双语 `next_steps_en` / `next_steps_zh`；不会返回任何 Cookie 值。

### `check_mcp_update`

**适合**：检查当前安装的 MCP 包是否落后于 npm latest，并给出安全更新命令。

请求示例：

```json
{
  "name": "check_mcp_update",
  "arguments": {}
}
```

返回内容：`current_version`、`latest_version`、`update_available`、`recommended_mcp_config`、`update_commands`，以及双语 `notes_en` / `notes_zh`；不会自动更新包。

### `search_bilibili_videos`

**适合**：只有一个主题，需要先在 Bilibili 内找到少量候选视频。

请求示例：

```json
{
  "name": "search_bilibili_videos",
  "arguments": {
    "query": "MCP 入门",
    "limit": 5
  }
}
```

返回内容：综合排序的普通视频候选及其 `bvid`、标题、作者、时长、发布时间、播放量、简介片段和源链接。搜索需要有效登录凭证，且不会自动读取候选视频的字幕或评论。

### `get_video_transcript`

**适合**：需要把视频内容交给 AI 做摘要、笔记、问答或知识整理。

请求示例：

```json
{
  "name": "get_video_transcript",
  "arguments": {
    "bvid_or_url": "https://www.bilibili.com/video/BV1xx411c7mD",
    "preferred_lang": "zh-Hans",
    "fallback_to_description": false
  }
}
```

返回内容：`bvid`、`title`、`language`、`transcript`（按行合并）、`data_source`（`subtitle` 或 `description`）、`page`（分集编号）。

> 默认无字幕时返回 `SUBTITLE_UNAVAILABLE`。如需降级，设置 `fallback_to_description: true`。

**关键词搜索示例**：

```json
{
  "name": "get_video_transcript",
  "arguments": {
    "bvid_or_url": "BV1xx411c7mD",
    "query": "深度学习",
    "max_matches": 5,
    "context_segments": 1
  }
}
```

搜索模式返回：`query`、`total_matches`、`returned_matches`、`truncated`、`matches`（含 `start_seconds`、`end_seconds`、`content`、`context`）和紧凑 `transcript`。

**定时区间转录示例**：

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

**适合**：想快速了解视频基本信息，不需要字幕或评论内容。

请求示例：

```json
{
  "name": "get_video_metadata",
  "arguments": {
    "bvid_or_url": "BV1xx411c7mD"
  }
}
```

返回内容：`bvid`、`title`、`author`、`duration`、`pubdate` / `pubdate_timestamp`、`description`、`tags`、`pages`（多P分集列表）和 `stats`（播放、点赞、投币、收藏、分享、评论、弹幕）。

### `get_video_chapters`

**适合**：获取 Bilibili 创作者定义的视频章节，用于导航或定位。

请求示例：

```json
{
  "name": "get_video_chapters",
  "arguments": {
    "bvid_or_url": "BV1vL411G7N7"
  }
}
```

返回内容：`bvid`、`page`、`cid`、`title`、`chapters`（数组，每项含 `title`、`start_seconds`、`end_seconds`）。无章节时 `chapters` 为空数组。

### `get_video_info`

**适合**：让 AI 总结视频核心内容——会优先尝试字幕，无字幕时回退到简介和标签。

请求示例：

```json
{
  "name": "get_video_info",
  "arguments": {
    "bvid_or_url": "https://www.bilibili.com/video/BV1xx411c7mD",
    "preferred_lang": "zh-Hans"
  }
}
```

返回内容：`data_source`（`subtitle` 或 `description`）、`video_info`（标题、描述、标签、字幕文本、发布时间）。

> 无字幕视频会自动降级返回描述和标签（即 `data_source: "description"`）。

### `get_video_comments`

**适合**：想了解观众对视频的真实评价、找精彩时间点。

请求示例：

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

返回内容：`comments[]`（含 `author`、`content`、`likes`、`timestamp`、`has_timestamp`）、`summary`（总数和时间戳评论数）。

> Cookie 过期或未登录可能导致评论为空。`sort: "time"` 可获取最新评论，`include_replies: false` 不返回子回复。

---

## 请求控制与缓存

为降低触发 Bilibili 风控和接口限流的概率，已内置以下请求控制策略：

- **请求启动间隔**：默认 500ms（0.5 秒），可通过 `BILIBILI_RATE_LIMIT_MS` 调整。
- **执行方式**：对 API 请求启动做节流，避免瞬时大并发；适合本地单用户 MCP 使用。
- **重试策略**：对 408、429、5xx、网络错误和超时进行最多 3 次指数退避重试。
- **超时控制**：默认 10 秒，可通过 `BILIBILI_REQUEST_TIMEOUT_MS` 调整。
- **缓存容量**：默认 100 条，可通过 `BILIBILI_CACHE_SIZE` 调整。
- **User-Agent**：可通过 `USER_AGENT` 覆盖默认请求头。

以上环境变量均在 MCP server 进程启动时读取，修改后需重启 MCP 客户端或重连 MCP server 才能生效。

---
