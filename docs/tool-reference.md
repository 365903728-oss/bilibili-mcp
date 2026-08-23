# Bilibili MCP 工具参考

[返回中文 README](../README.md) · [English](./tool-reference.en.md) · [客户端接入](./client-setup.md)

本页保存 12 个 MCP 工具的详细行为、参数、示例、错误结构和运行时请求控制。安装与首次调用请先看项目 README。

## 快速选择

| 目标 | 推荐工具 | 返回重点 |
|---|---|---|
| 只有主题，还没有视频链接 | `search_bilibili_videos` | 最多 10 个普通视频候选及可继续调用的 BVID；不自动抓取字幕或评论 |
| 只有主题，想找 UP 主候选 | `search_bilibili_creators` | 最多 10 个 Creator 候选及其稳定数字 `mid`；显示名称模糊且不唯一，不做自动选择 |
| 从选定 UP 主（mid）读取概览、视频目录、合集、系列或动态 | `get_bilibili_creator_content` | 一个实时概览或有界内容页（最多 20 条），按 `next_cursor` 翻页；不下载图片或自动抓取视频证据 |
| 从我的 Bilibili 收藏夹开始读取 | `list_bilibili_favorite_videos` | 当前账号所有创建的收藏夹的一页视频（最多 20 条），按 `next_cursor` 翻页直到结束；不读取字幕、评论或下载 |
| 想让 AI 总结一个视频 | `get_video_info` | 字幕优先；无字幕时返回标题、简介、标签 |
| 只想拿完整转录文本或关键词定位 | `get_video_transcript` | 原生字幕优先，可显式 ASR 回退；支持时间戳、区间过滤和关键词搜索 |
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
- 可手动指定偏好字幕语言：`zh-Hans`、`zh-CN`、`zh-Hant`、`en`、`ja`、`ko`、`ai-zh`；`ai-zh` 会原样传入选择逻辑，未知值返回 `VALIDATION_ERROR`
- 选中任意 Bilibili AI 识别字幕（`ai-zh`、`ai-en` 等 `ai-*` 语言）时结果 `data_source` 为 `ai_subtitle`（不是 `subtitle`）；`ai_subtitle` 是 Bilibili 的 AI 转录，可能不准确，不能当作人工校验过的引用
- 每个选中的 `ai-*` 都会先做确定性完整性评估；不通过时返回简介结果（`data_source: "description"`）且不缓存，绝不返回不可用正文
- 可选参数 `exclude_ai_subtitles`：排除全部 AI 字幕（`ai-zh`、`ai-en` 等 `ai-*` 语言），只保留人工字幕；仅剩 AI 字幕时视为无字幕并返回简介降级（默认 `false`）

### 2. 评论总结 (`get_video_comments`)
- 获取视频热门评论，辅助判断视频真实口碑
- 自动过滤表情占位符（如 `[doge]`）以保持文本整洁
- 优先保留包含时间戳的评论（如 `05:20`），方便定位高能片段
- 支持两种详细程度：
  - `brief`: 10 条热门评论速览
  - `detailed`: 20 条热门评论 + 高赞连带回复
- 可选参数：
  - `limit`: 主评论数量，整数 `1-50`，覆盖 `detail_level` 的默认主评论数量；若包含子回复，扁平的 `comments[]` 总条数可超过 `limit`
  - `sort`: 排序方式 `"hot"`（按热度，默认）或 `"time"`（按时间）
  - `include_replies`: 是否包含高赞回复（默认 `true`）

### 3. 视频转录 (`get_video_transcript`)
- 返回按行合并的原生字幕或显式请求的本地 ASR 转录
- 支持指定偏好语言（默认按 `zh-Hans` > `ai-zh` > `zh-CN` > `zh-Hant` > `en` 优先级选择）
- 支持多P分集选择、时间戳输出和时间区间过滤
- 支持可选关键词搜索：返回带上下文的时间戳匹配列表（大小写不敏感字面匹配）
- 成功调用会同时返回向后兼容的格式化 JSON 文本和内容相同的 MCP `structuredContent`
- 可选参数：
  - `preferred_lang`: 偏好字幕语言代码，支持 `zh-Hans`、`zh-CN`、`zh-Hant`、`en`、`ja`、`ko`、`ai-zh`；`ai-zh` 会原样传入选择逻辑，未知值返回 `VALIDATION_ERROR`
  - `fallback_to_description`: 字幕不可用时是否降级为视频描述（默认 `false`）
  - `fallback_to_asr`: 确认无可用字幕时是否运行已就绪的本地 ASR（默认 `false`）
  - `exclude_ai_subtitles`: 排除 Bilibili AI 识别字幕（`ai-zh`、`ai-en` 等 `ai-*` 语言），只保留人工字幕；仅剩 AI 字幕时视为无字幕（默认 `false`）
  - `force_asr`: 绕过字幕元数据与内容选择，直接用已就绪的本地 ASR 转录当前 Part；无需同时设置 `fallback_to_asr`，优先于 `exclude_ai_subtitles`（默认 `false`）
  - `page`: 多P视频分集编号（从1开始的正整数）
  - `include_timestamps`: 每行添加 `[HH:MM:SS --> HH:MM:SS]` 时间戳前缀
  - `start_seconds` / `end_seconds`: 只返回与此区间重叠的字幕段
  - `query`: 关键词搜索词（最多100字符，大小写不敏感字面匹配）
  - `max_matches`: 最大匹配数（1-20，默认10）
  - `context_segments`: 每个匹配前后的上下文段数（0-5，默认1）
- 默认不降级：无字幕时返回 `SUBTITLE_UNAVAILABLE` 错误
- 回退顺序固定为原生字幕 → 显式 ASR → 仅在播放 API 返回有效空音频集合且同时显式请求时使用视频描述
- 选中任意 `ai-*` 时 `data_source` 为 `ai_subtitle`。每个选中的 `ai-*` 都会无条件双读并做确定性完整性评估，通过后才返回正文：跨读取稳定性（两次读取的正文不一致即不可用，适用于所有 `ai-*`）、语言（仅针对 `ai-zh`：正文含至少 80 个 Unicode 字母且 Han 占比低于 10% 视为不匹配；其他 `ai-*` 语言不因非中文正文被拒绝）。稳定但同语言语义不符的正文是已接受的限制，可用 `force_asr` / `exclude_ai_subtitles` 控制。人工字幕保持单读且不做评估
- 完整性评估不通过时绝不返回正文：`fallback_to_asr: true` 调用本地 ASR；否则遵循 `fallback_to_description`，无授权回退时返回 `SUBTITLE_UNAVAILABLE`；`get_video_info` 返回简介结果且不缓存。第二次读取的传输/超时/认证/解析错误照常可见，不会转化为完整性失败或触发 ASR
- 只有字幕列表、选中字幕或字幕正文被确认为空、完整性评估判定选中的 `ai-*` 不可用（稳定性；语言仅针对 `ai-zh`。仅在显式开启 `fallback_to_asr` 时触发 ASR），或 `force_asr` 显式请求时才触发 ASR；Cookie、HTTP、超时、解析、风控和其他 API 错误保持可见
- ASR 使用 setup 管理的 ready 模型、CPU INT8 和一个临时音频文件；MCP 调用不会下载或切换模型
- 有界限制：单 Part 最长 7200 秒、音频 128 MiB、3 个候选地址/每个 3 次重定向、下载 120 秒、转录 30 分钟、stdout 2 MiB、10000 段、同时一个任务且不排队
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

### 7. 创作者搜索 (`search_bilibili_creators`)

- 按关键词返回 Bilibili 平台排序的 Creator 候选；默认 5 条，最多 10 条。
- 每个候选携带稳定数字 `mid`（唯一身份）、显示名称、简介、头像 URL、粉丝数、视频数、等级和本地推导的 `source_url`；`mid` 是正安全整数且名称非空时才接受该候选，畸形字段规范化为空字符串或 0。
- 显示名称模糊且不唯一：重名/近似名保持为独立候选，按 Bilibili 原始顺序返回；本工具不自动选择某个 Creator，也不抓取候选内容。
- 必须先配置且登录 Bilibili Cookie；成功结果同时提供格式化 JSON 文本和内容相同的 MCP `structuredContent`。

### 8. 收藏夹发现 (`list_bilibili_favorite_videos`)

- 从当前已登录账号自动发现所有创建的收藏夹，逐 Folder 逐页返回其中的视频成员。
- 每次调用最多返回上游一页（固定 20 条）；`next_cursor` 是不透明、无状态、版本化的 base64url 令牌，仅包含下一个 Folder 与页码。
- 游标在所有网络请求前严格校验：类型、长度（1-256）、字符集（仅 base64url）、JSON 结构、版本、正整数 Folder ID 与页码。
- 续读规则：当前 Folder 的 `has_more=true` 时游标指向同 Folder 下一页；上游返回空 `medias`（即使 `has_more=true`）或 `has_more=false` 时，游标指向下一个 Folder 的第 1 页；最后一个 Folder 的最后页省略 `next_cursor`。
- 同一 BVID 出现在多个 Folder 中时，会在各自 Folder 上下文中各返回一次（“收藏成员关系”语义）；本 MCP 不做跨 Folder 去重。
- `skipped_count` 报告上游返回但无法安全规范化的行数（如无效 BVID、空标题）；不会触发额外的替换请求。
- 上游的 `media_count` 只是 Bilibili 报告的计数，可能高于当前可见或可调用的行数，结果只保证返回上游当前页面内容。
- 遍历是对 Bilibili 当前实时状态的 best-effort 读取，不提供快照隔离；续读期间新增、删除或移动收藏成员可能导致顺序或可见结果变化。
- 不持久化、不缓存、不下载、不抓取字幕/评论/章节/搜索结果；不会发起匿名降级请求。
- 必须先配置且登录 Bilibili Cookie；成功结果同时提供格式化 JSON 文本和内容相同的 MCP `structuredContent`。
- 可选参数：
  - `cursor`: 上一次成功调用返回的不透明续读令牌。首次调用请省略。

### 9. 创作者内容发现 (`get_bilibili_creator_content`)

- 从调用方选定且已验证的一个 Creator `mid` 出发，读取 Bilibili 空间页面当前可见的实时内容，`section` 五选一：
  - `overview`：返回一个受字节限制的实时主页概览（名称、简介、头像、等级、`video_count` 和 `live_state`；`follower_count` 仅在上游提供有效 `fans` 事实时出现，绝不编造为 0）。`video_count` 优先取 `acc/info` 上游值；上游不提供时才允许一次有界的 `arc/search` 计数探测（`pn=1, ps=1, order=pubdate`），绝不自行编造计数。
  - `videos`：返回当前可列出的视频目录的一页（最多 20 条 BVID 元数据行）；`next_cursor` 是不透明、无状态、版本化的 base64url 令牌，仅编码 mid 与下一页号。
  - `collections` / `series`：不传 `container_id` 时分别列出 Collection 或 Series 容器；传入该段返回的容器 ID 时，只遍历所选容器的一页 `members`。两类容器保持独立，不与多 Part Video 或 Favorite Folder 混用。
  - `dynamics`：返回一页 Creator Dynamic（最多 20 条），包括有界文字、图片 URL 与可用尺寸、关联 BVID、发布时间和转发时的原动态关系。普通动态即使浏览器 URL 使用 `/opus/` 仍是 Dynamic；不提取专门的长文/Opus 正文。
- 游标在任何网络请求前严格校验，并绑定请求 mid、section，以及正安全整数页码与可选容器 ID，或 `dynamics` 的不透明上游 offset；不匹配或越界时返回 `VALIDATION_ERROR`，不会发出任何请求。
- `continuationProven` 决定 `next_cursor`：有 `videos_total` 且 `page * 20 < videos_total` 时返回下一页；无总数但当前页的原始上游行数恰好 20 行时也返回下一页，避免单条畸形行截断遍历；发出 `page + 1` 前会证明其 `page * 20` 算术仍为安全整数。
- `skipped_count` 报告上游返回但无法安全规范化的行数（如无效 BVID、空标题），不会触发额外的替换请求；联合投稿行的行内 mid 可能与所选创作者不同，保留该行并使用行内作者。
- 每行只含可继续传给现有证据工具的元数据：`bvid`、标题、简介、封面、分类、时长、发布时间、作者、播放/弹幕/评论计数和 `source_url`；时长解析上游 `length`（分钟可大于 59）并兼容数值 `duration`，发布时间以 `created` 为准；`arc/search` 语义下 `comment` 是评论数、`video_review` 是弹幕数；`is_charge_video` 仅在上游显式真值证据（`is_pay`/`is_charging_arc`/`elec_arc_type` 或兼容字段 `is_charge_video`）存在时为 `true`；`access` 恒为 `"unknown"`（本工具不做访问探测）。
- Collection/Series 列表和成员页保留 Bilibili 顺序、最多 20 条，并用 `skipped_count` 报告无法安全规范化的目标类型行；同一 BVID 在不同容器中保留不同 Membership，不做全局去重。结果都是实时非快照状态。
- Dynamic 保留上游顺序，并把原发、转发、纯文字、图片、视频分享或未知类型明确标为 `text`、`image`、`video`、`repost` 或 `unknown`；每行含 `dynamic_id`、`upstream_type`、`published_at`、有界 `text`、最多 9 个 `images[]`、最多 20 个 `referenced_bvids[]`、`source_url`，转发另含有界 `original`。关联 BVID 只表示动态中的关系，不证明该视频归动态作者所有。
- 不持久化、不缓存、不下载/代理图片、不做 OCR、图片描述或视觉模型推理；不自动抓取字幕/评论/章节/搜索结果、关联视频详情，也不自动读取其他容器成员或爬取完整目录。
- 必须先配置且登录 Bilibili Cookie；成功结果同时提供格式化 JSON 文本和内容相同的 MCP `structuredContent`。
- 参数：
  - `mid`（必填）：要读取的 Creator 数字 `mid`（正安全整数）。
  - `section`（必填）：`"overview"`、`"videos"`、`"collections"`、`"series"` 或 `"dynamics"`。
  - `container_id`（可选）：仅用于 `collections` 或 `series`；省略时列容器，提供时读取所选容器成员。
  - `cursor`（可选）：上一次同 mid、同 section、同容器模式成功调用返回的不透明令牌。`overview` 不接受游标。

### 10. 凭证助手工具

- `get_credential_setup_instructions`: 返回安全的 Bilibili Cookie 配置命令和说明。AI agent 安装此 MCP 后可调用此工具引导用户完成配置。
- `check_bilibili_credentials`: 检查凭证是否已配置并处于登录状态，不返回任何 Cookie 值。配置缺失或失效时返回下一步操作指引。
- `check_mcp_update`: 检查本地包版本与 npm latest 是否一致，并返回 `npx @latest` 或全局安装的安全更新指引。

### 11. 行为说明与错误处理

- **Cookie 过期智能检测**：当字幕获取为空时自动验证登录状态，区分“无字幕视频”与“凭证失效”，并抛出明确的 `COOKIE_EXPIRED` 错误，避免静默降级。

#### 无 Cookie 行为

- 部分公开视频元数据（`get_video_metadata`）可能在未登录状态下工作。
- 字幕（`get_video_info`、`get_video_transcript`）在未登录时可能无法获取、不完整或返回空结果。
- 评论（`get_video_comments`）在未登录时可能不完整、被限流或返回空列表。
- 视频发现（`search_bilibili_videos`）强制检查已配置且有效的登录凭证；不提供匿名降级。
- 创作者搜索（`search_bilibili_creators`）同样强制检查已配置且有效的登录凭证；不提供匿名降级。
- 收藏夹发现（`list_bilibili_favorite_videos`）必须从已登录的当前账号身份开始；不提供匿名降级，也不读取其他账号的公开收藏。
- 创作者内容发现（`get_bilibili_creator_content`）需要已配置且有效的登录凭证；不提供匿名降级，`access` 恒为 `"unknown"`，不探测资源是否可访问。
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
- `category`：错误分类（`validation` / `credentials` / `content` / `network` / `access` / `rate_limit` / `api` / `runtime` / `unknown`）。
- `retryable`：是否建议自动重试。
- `user_action_required`：是否需要用户介入才能解决。
- `details`：可选的附加信息（如 HTTP 状态码、超时毫秒数、Bilibili API 错误码），不包含 Cookie 或完整 URL。

支持的错误码：

| 错误码 | 含义 | 调用方建议 |
|--------|------|-----------|
| `VALIDATION_ERROR` | 输入参数不合法 | 检查并修正 `bvid_or_url` 或其他参数 |
| `COOKIE_EXPIRED` | Cookie 已失效或未登录 | 用户应更新/轮换 Bilibili 凭据 |
| `SUBTITLE_UNAVAILABLE` | 视频无可用的字幕 | 对 `get_video_transcript` 可重试并设置 `fallback_to_description: true` |
| `ASR_NOT_READY` | 本地 ASR 未就绪 | 在本地运行 `setup`，并用 `doctor --json` 确认 ready |
| `ASR_AUDIO_UNAVAILABLE` | 无法安全获取临时纯音频 | 稍后重试；Bilibili 播放地址是临时的 |
| `ASR_FAKE_IP_DNS` | 代理 DNS 为 Bilibili 音频媒体域名返回标准 Fake-IP | 向用户解释三个安全方案，并等待用户明确选择；不要自动重试 |
| `ASR_LIMIT_EXCEEDED` | 分集、音频或输出超过安全限制 | 选择更短的 Part 或使用原生字幕 |
| `ASR_BUSY` | 已有一个本地 ASR 任务 | 当前任务完成后重试；不会排队 |
| `ASR_TRANSCRIPTION_TIMEOUT` | 本地转录超过 30 分钟 | 稍后重试或选择更短的 Part |
| `ASR_TRANSCRIPTION_FAILED` | 托管 Python/模型运行失败 | 检查 `doctor --json` 后重试 |
| `ASR_OUTPUT_INVALID` | 托管 ASR 返回无效或超限的 NDJSON | 检查本地 ASR 状态并反馈重复错误 |
| `NETWORK_ERROR` | 网络请求失败（HTTP 5xx、连接错误等） | 稍后重试；如反复出现请检查网络/代理/防火墙 |
| `NETWORK_TIMEOUT` | 请求 Bilibili 超时 | 稍后重试；如反复出现请检查网络/代理/防火墙 |
| `API_RATE_LIMITED` | 触发 Bilibili API 频率限制（HTTP 429） | 等待一段时间后重试；降低调用频率或调大 `BILIBILI_RATE_LIMIT_MS` |
| `ACCESS_DENIED` | Bilibili 拒绝访问资源（权限不足、私密、地区或账号限制、已下架等） | 检查资源与账号访问权限，必要时运行凭据检查 |
| `PAID_VIDEO` | 视频可能需要付费、会员或额外权限 | 在 Bilibili 端确认；本 MCP 不会绕过付费或受限访问 |
| `COMMENTS_DISABLED` | 视频评论已关闭或访问受限 | 改用字幕或元数据工具；也可在 Bilibili 页面确认 |
| `BILIBILI_API_ERROR` | 其他 Bilibili API 错误 | 临时问题可稍后重试；持续出现请带错误码反馈 |
| `UNKNOWN_ERROR` | 未知错误 | 稍后重试；反馈时请勿包含 Cookie 或凭据 |

### ASR Fake-IP DNS 诊断

出现 `ASR_FAKE_IP_DNS` 时，代理 DNS 返回的是 `198.18.0.0/15` 标准 Fake-IP 占位地址，不是真实的 Bilibili 音频 CDN 公网地址；具体公网地址会因用户、域名、缓存和时间不同而变化。服务会停止下载，以避免连接本地、私有或特殊用途地址。这通常不是 Cookie、ASR 模型、BVID 或普通的临时播放故障。

AI Agent 应先解释原因，列出以下选择，然后等待用户明确选择：

1. **推荐：保留 TUN 和规则模式。** 编辑当前生效的代理配置，把精确规则 `+.bilivideo.com` 和 `+.bilivideo.cn` 加入 `fake-ip-filter`。保存并重新加载配置，或重启代理内核，然后重试 ASR。此方案仅让这些域名返回真实 IP，其他 TUN 行为和路由规则保持不变。
2. **改用真实公网 IP DNS 模式。** 切换到 `redir-host` 或等效模式。这会改变代理客户端的 DNS 行为；应用并重新加载设置后，再重试 ASR。
3. **不改变网络。** 改用 Human Subtitle（人工字幕）、Bilibili AI 字幕或视频简介；此时无法获得 Local ASR Transcript（本地 ASR 转录）。

Agent 不得自动关闭 TUN、修改代理配置、使用公共 DoH 绕过用户的 DNS 策略，或在设置未改变时盲目重试。不要在 MCP 服务中放行 `198.18.0.0/15`。

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

### `search_bilibili_creators`

**适合**：让 Agent 从主题/关键词出发，获得 Bilibili UP 主候选及其稳定数字 `mid`，用于需要"按创作者身份继续"的场景。显示名称模糊且不唯一，每个候选都只是候选而非已解析身份；本工具不自动选择某个 Creator，也不抓取候选内容。

请求示例：

```json
{
  "name": "search_bilibili_creators",
  "arguments": {
    "query": "UP主",
    "limit": 5
  }
}
```

参数：

- `query`（必填）：搜索关键词。trim 后必须非空，最多 100 字符。
- `limit`（可选）：候选 Creator 数量，整数 1-10，默认 5。

返回内容：`query` 和按 Bilibili 原始顺序排列的 `results[]`。每项含稳定数字 `mid`（正安全整数，唯一身份）、`name`、`bio`、`avatar_url`、`follower_count`、`video_count`、`level` 和本地推导的 `source_url`。只有 `mid` 为正安全整数且名称非空时才接受该候选；畸形字段规范化为空字符串或 0。重名/近似名保持为独立候选。搜索需要有效登录凭证，不会自动读取候选的视频、动态、字幕、评论或其他详情。

### `list_bilibili_favorite_videos`

**适合**：让 Agent 从你已登录的 Bilibili 账号开始读取全部创建的收藏夹中的视频。MCP 协议始终分页：每次调用返回上游一页（最多 20 条），Agent 按返回的 `next_cursor` 继续调用直到没有该字段为止。**不要假设一次响应包含整个账号的收藏。**

请求示例（首次调用，不传 `cursor`）：

```json
{
  "name": "list_bilibili_favorite_videos",
  "arguments": {}
}
```

返回内容：`folders_total`、`folder`（当前 Folder 的 `id`、`title`、`media_count`）、`page`、`videos[]`（每项含 `bvid`、`title`、`author`、`duration_seconds`、`published_at`、`favorited_at`、`source_url`）、`skipped_count`，以及可选的 `next_cursor`。账号无任何有效收藏夹时只返回 `folders_total: 0`、`videos: []`、`skipped_count: 0`。

续读示例：

```json
{
  "name": "list_bilibili_favorite_videos",
  "arguments": {
    "cursor": "<上一次响应中的 next_cursor>"
  }
}
```

> 上游返回空 `medias` 时，即使 `has_more=true`，本工具仍会把当前 Folder 视为已结束并跳到下一个 Folder 的第 1 页，避免游标循环。若游标对应的 Folder 已不再属于当前账号（例如被删除或转移），返回 `VALIDATION_ERROR` 并提示“restart without a cursor”。

### `get_bilibili_creator_content`

**适合**：从 `search_bilibili_creators`（或任何来源）得到一个选定 Creator 的稳定数字 `mid` 后，读取主页概览、视频目录、Collection、Series 或动态。每次调用最多返回上游一页（最多 20 条），Agent 按返回的 `next_cursor` 继续调用直到没有该字段为止。**不要假设一次响应包含完整目录，也不要自动爬取全部页。**

概览请求示例：

```json
{
  "name": "get_bilibili_creator_content",
  "arguments": {
    "mid": 2088259175,
    "section": "overview"
  }
}
```

返回内容：`mid`、`section: "overview"`、`name`、`bio`、`avatar_url`、`level`、`video_count` 和 `live_state`；`follower_count` 为可选字段，仅在上游提供有效 `fans` 事实时出现，绝不编造为 0。`video_count` 优先取上游 `acc/info` 提供的值；上游不提供时才允许一次有界的计数探测，绝不编造计数。

视频目录请求示例（首次调用，不传 `cursor`）：

```json
{
  "name": "get_bilibili_creator_content",
  "arguments": {
    "mid": 2088259175,
    "section": "videos"
  }
}
```

返回内容：`mid`、`section: "videos"`、`page`、`videos_total`（有界时提供）、`videos[]`（每项含 `bvid`、`title`、`description`、`cover_url`、分类、`duration_seconds`、`published_at`、`author`、播放/弹幕/评论计数、`access: "unknown"`、`source_url`）、`skipped_count`、`live_state`，以及可选的 `next_cursor`。

续读示例：

```json
{
  "name": "get_bilibili_creator_content",
  "arguments": {
    "mid": 2088259175,
    "section": "videos",
    "cursor": "<上一次响应中的 next_cursor>"
  }
}
```

> 游标只接受上一次同 mid、同 `videos` section 返回的令牌；跨 mid、跨 section、`overview` 携带游标、页码越界或格式非法的游标都会在发出任何网络请求前返回 `VALIDATION_ERROR`。

合集列表与成员请求示例：

```json
{"name":"get_bilibili_creator_content","arguments":{"mid":2088259175,"section":"collections"}}
```

```json
{"name":"get_bilibili_creator_content","arguments":{"mid":2088259175,"section":"collections","container_id":1903592}}
```

Series 使用相同模式但 `section` 为 `"series"`，且必须使用 Series 列表返回的 `series_id`。容器列表返回 `collections[]` 或 `series[]`；成员页返回 `selected_collection` 或 `selected_series` 以及 `members[]`。成员游标绑定 mid、section 和 `container_id`，不得跨容器复用。

动态请求示例：

```json
{"name":"get_bilibili_creator_content","arguments":{"mid":2088259175,"section":"dynamics"}}
```

返回 `dynamics[]`、`skipped_count`、`live_state: "live"` 和可选 `next_cursor`。每项只提供有界文字、图片 URL/尺寸、关联 BVID 与转发关系；MCP 不下载或识别图片，也不自动读取关联视频。续读时把上次的 `next_cursor` 原样传回同一 mid 的 `dynamics` 请求；游标绑定 Creator 与 section，遍历期间上游内容变化可能影响顺序或可见结果。

### `get_video_transcript`

**适合**：需要把视频内容交给 AI 做摘要、笔记、问答或知识整理。

请求示例：

```json
{
  "name": "get_video_transcript",
  "arguments": {
    "bvid_or_url": "https://www.bilibili.com/video/BV1xx411c7mD",
    "preferred_lang": "zh-Hans",
    "fallback_to_description": false,
    "fallback_to_asr": false
  }
}
```

返回内容：`bvid`、`title`、`language`、`transcript`（按行合并）、`data_source`（`subtitle`、`ai_subtitle`、`asr` 或 `description`）、`page`（分集编号）。

> `preferred_lang` 仅接受 `zh-Hans`、`zh-CN`、`zh-Hant`、`en`、`ja`、`ko`、`ai-zh`；显式传入 `ai-zh` 不会被改写为其他语言，未知值返回 `VALIDATION_ERROR`。默认无字幕时返回 `SUBTITLE_UNAVAILABLE`。如需降级，设置 `fallback_to_description: true`。`data_source: "ai_subtitle"` 表示选中了 Bilibili AI 识别字幕——它是 AI 转录，可能不准确，不能当作人工校验过的引用。

**显式 ASR 回退示例**：

```json
{
  "name": "get_video_transcript",
  "arguments": {
    "bvid_or_url": "BV1xx411c7mD",
    "page": 1,
    "fallback_to_asr": true,
    "include_timestamps": true
  }
}
```

原生字幕始终优先。只有确认没有可用字幕且 `doctor --json` 报告 ready 时，结果才返回 `data_source: "asr"`；ASR 段继续使用相同的区间、关键词、上下文、`source_url` 和 `timestamp_url` 管线。`force_asr: true` 可绕过字幕选择、无条件使用本地 ASR（无需同时设置 `fallback_to_asr`）。

**排除 AI 字幕示例**：

```json
{
  "name": "get_video_transcript",
  "arguments": {
    "bvid_or_url": "BV1xx411c7mD",
    "exclude_ai_subtitles": true
  }
}
```

`exclude_ai_subtitles: true` 时只从人工字幕中选择；仅剩 AI 字幕（`ai-zh`、`ai-en` 等 `ai-*` 语言）时视为无字幕，可配合 `fallback_to_asr` 或 `fallback_to_description`。

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

返回内容：`data_source`（`subtitle`、`ai_subtitle` 或 `description`）、`video_info`（标题、描述、标签、字幕文本、发布时间）。

> `preferred_lang` 仅接受 `zh-Hans`、`zh-CN`、`zh-Hant`、`en`、`ja`、`ko`、`ai-zh`；显式传入 `ai-zh` 不会被改写为其他语言，未知值返回 `VALIDATION_ERROR`。无字幕视频会自动降级返回描述和标签（即 `data_source: "description"`）。`data_source: "ai_subtitle"` 表示选中了 Bilibili AI 识别字幕——它是 AI 转录，可能不准确，不能当作人工校验过的引用。需要纯人工字幕时传 `exclude_ai_subtitles: true`。

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

> `limit` 只限制主评论数量；当 `include_replies: true` 且 `detail_level: "detailed"` 时，扁平的 `comments[]` 还包含子回复，因此总条数可超过 `limit`。Cookie 过期或未登录可能导致评论为空。`sort: "time"` 可获取最新评论，`include_replies: false` 不返回子回复。

---

## 请求控制与缓存

为降低触发 Bilibili 风控和接口限流的概率，已内置以下请求控制策略：

- **请求启动间隔**：默认 500ms（0.5 秒），可通过 `BILIBILI_RATE_LIMIT_MS` 调整。
- **执行方式**：对 API 请求启动做节流，避免瞬时大并发；适合本地单用户 MCP 使用。
- **重试策略**：对 408、429、5xx、网络错误和超时进行最多 3 次指数退避重试。
- **超时控制**：默认 10 秒，可通过 `BILIBILI_REQUEST_TIMEOUT_MS` 调整。
- **缓存容量**：默认 100 条，可通过 `BILIBILI_CACHE_SIZE` 调整。
- **User-Agent**：可通过 `USER_AGENT` 覆盖默认请求头。

三个数值变量必须是完整的十进制正安全整数；空值、部分数字、`0`、负数及非安全整数会触发配置错误并阻止启动。两个毫秒变量还必须不超过 Node.js 计时器上限 `2147483647`；缓存容量没有额外的人为上限。

以上环境变量均在 MCP server 进程启动时读取，修改后需重启 MCP 客户端或重连 MCP server 才能生效。

---
