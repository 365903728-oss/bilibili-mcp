# 更新日志 (Changelog)

所有关于 **Bilibili MCP Server** 的显著更改都将记录在此文件中。

---

## [Unreleased]

---

## [1.13.0] - 2026-08-20

### 新增
- 新增第 11 个工具 `search_bilibili_creators`，按关键词返回 Bilibili 平台排序的 Creator 候选。`limit` 默认 5、最大 10；每个候选包含稳定数字 `mid`（唯一身份）、名称、简介、头像 URL、粉丝数、视频数、等级和本地推导的来源链接。显示名称模糊且不唯一，候选仅作为候选返回，不自动选择某个 Creator，也不抓取候选内容。（Issue #45）
- 创作者搜索成功结果同时返回格式化 JSON 文本与内容相同的 MCP `structuredContent`；要求有效且已登录的 Bilibili Cookie，不提供匿名降级。
- 新增第 12 个工具 `get_bilibili_creator_content`，从选定 Creator 的稳定数字 `mid` 出发，读取 `overview`、`videos`、`collections`、`series` 或 `dynamics`。除概览外，每次调用最多返回一页 20 条结果，并通过绑定 Creator、分区和容器的不透明 `next_cursor` 继续遍历。（Issue #46-#48）
- 视频目录保留当前登录身份可列出的普通投稿、联合投稿与带充电标记的视频，返回可继续交给现有证据工具的 BVID 和有界元数据；列表可见性不等于播放授权，因此 `access` 保持 `unknown`，不会额外逐条探测。
- Collection 与 Series 保持为两种不同容器；可分别列出容器或读取一个容器的成员。同一 BVID 在多个上下文中的 membership 会分别保留，不做跨容器去重。
- Creator Dynamics 覆盖原发、转发、文字、图片、视频分享和未知类型，返回有界文字、图片 URL/尺寸、关联 BVID 与原动态关系。MCP 不下载或识别图片，不提取专门的长文/Opus 正文，也不自动读取关联视频。

### 安全与兼容性
- 两个 Creator 工具都要求已配置且有效的登录凭证，复用现有超时、限流、重试、响应大小与结构化错误边界；HTTP 412、认证、API 与畸形响应不会被转换为空成功。
- 所有发现调用保持有界，不自动批量抓取字幕、评论、OCR、视觉结果或逐行详情；分页反映 Bilibili 实时状态，不承诺快照一致性。

### 验证
- 通过 TypeScript 构建和 42 个文件 / 1058 项测试；193 文件 npm 打包检查、97 个生产依赖零漏洞审计、五处版本一致性、当前发布树与本轮变更的凭据扫描均通过。

---

## [1.12.0] - 2026-08-18

### 新增
- 区分 Bilibili AI 识别字幕与人工字幕：选中任意 Bilibili AI 字幕（`ai-zh`、`ai-en` 等 `ai-*` 语言）时，`get_video_transcript` 与 `get_video_info` 返回 `data_source: "ai_subtitle"`（不再是 `"subtitle"`；本地 ASR 仍为 `"asr"`）。`ai_subtitle` 是 Bilibili 的 AI 转录，可能不准确，不能当作人工校验过的引用。
- `get_video_transcript` 与 `get_video_info` 新增可选参数 `exclude_ai_subtitles`（默认 `false`）：过滤 AI 字幕、优先返回人工字幕；仅剩 AI 字幕时视为无字幕，transcript 可配合显式 ASR/描述降级，video-info 返回简介。video-info 缓存键包含该选项。
- `get_video_transcript` 新增可选参数 `force_asr`（默认 `false`）：绕过字幕选择直接用已就绪的本地 ASR 转录当前 Part，无需同时设置 `fallback_to_asr`，并优先于 `exclude_ai_subtitles`。
- 对每个选中的 `ai-*` 无条件双读并做确定性完整性评估，通过后才返回正文：跨读取稳定性（两次读取的正文不一致即不可用，适用于所有 `ai-*`）、语言（仅针对 `ai-zh`：正文含至少 80 个 Unicode 字母且 Han 占比低于 10% 视为不匹配；其他 `ai-*` 语言不因非中文正文被拒绝）。不通过时 `fallback_to_asr: true` 调用本地 ASR，否则遵循 `fallback_to_description`，无授权回退时返回 `SUBTITLE_UNAVAILABLE`；video-info 返回简介且不缓存。稳定但同语言语义不符的正文是已接受的限制，可用 `force_asr` / `exclude_ai_subtitles` 控制；第二次读取的传输/超时/认证/解析失败照常作为错误返回，不会被伪装成完整性失败或触发 ASR。
- `setup` 新增 `--non-interactive`（使用已有的环境变量或全局配置凭据，绝不提示、也绝不从 stdin/argv 读取凭据值；无 `--asr-model` 时仅确认凭据可加载即成功退出）与 `--asr-model <tiny|base|small>`（需与 `--non-interactive` 同用，安装指定模型）。

### 验证
- 使用发布工作流同版本的 Node.js `22.14.0` 与 npm `11.18.0` 通过 TypeScript 构建和 41 个文件 / 906 项测试；189 文件 npm 打包检查、生产依赖零漏洞审计、版本一致性和凭据扫描均通过。

---

## [1.11.4] - 2026-08-09

### 修复
- 修正评论 `limit` 的主评论语义：上游分页固定使用 `ps=20`、请求次数保持有界，并在本地截断到调用方上限；缺失或非数组的 `replies` 容器不再被当作空页，而是安全失败。同时统一支持语言校验（保留 `ai-zh`）、阻止空凭据覆盖已有配置、严格解析数值环境配置，并按端点语义区分 Bilibili JSON `-403`。（PR #26）
- 加固搜索响应形状：显式 `result: []` 仍以一次请求正常返回空结果；缺失或非数组的 `result` 仅执行一次可中止的形状重试，仍畸形时返回 `UPSTREAM_RESPONSE_INVALID`。第二次合法响应可以恢复，网络、HTTP 状态与中止错误不会被搜索层额外重试。（PR #27）

### 验证
- 最终自动化回归通过 41 个测试文件 / 862 项测试，并覆盖评论分页边界、畸形回复容器、显式空搜索结果、畸形搜索响应恢复与 MCP 错误映射；TypeScript 构建、真实 MCP stdio 协议冒烟、185 文件 npm 打包检查、生产依赖审计和凭据扫描均通过。已登录 live 冒烟验证正常成功路径：连续搜索稳定返回结果，评论 `limit=21` 与 `limit=50` 均达到调用方上限；畸形、显式空结果和上游错误分支由确定性自动化测试覆盖。输出未包含 Cookie 值。

---

## [1.11.3] - 2026-08-06

### 修复
- 修复官方 MCP Registry 命名空间大小写：`mcpName` 与 `server.json.name` 从 `io.github.xzxzzx-ai/bilibili-mcp` 更正为 `io.github.XZXZZX-Ai/bilibili-mcp`，与 GitHub 认证授予的权限（区分大小写，`io.github.XZXZZX-Ai/*`）一致；v1.11.2 发布尝试因此返回 HTTP 403。无运行时、MCP 工具或依赖变更。

### 验证
- 通过 TypeScript 构建、39 个文件 / 803 项测试与 `npm pack --dry-run`（181 个文件，包含更正后的 `mcpName`）；`package.json` 与锁文件版本一致为 `1.11.3`。

---

## [1.11.2] - 2026-08-06

### 新增
- 新增官方 MCP Registry 元数据：`package.json` 中的 `mcpName` 与根目录 `server.json`，指向 npm 包 `@xzxzzx/bilibili-mcp` v1.11.2（stdio 传输）。无运行时、MCP 工具或依赖变更。

### 验证
- 通过 TypeScript 构建、39 个文件 / 803 项测试与 `npm pack --dry-run`（181 个文件，包含 `mcpName`；`server.json` 保留于仓库根目录，供官方 Registry 使用）；`package.json` 与锁文件版本一致为 `1.11.2`。

---

## [1.11.1] - 2026-08-05

### 修复
- 有效的 Bilibili AI 字幕数字 ID 大于 `Number.MAX_SAFE_INTEGER` 时不再被误判为无效元数据；公开响应结构与其余校验保持不变。（Issue #24，PR #25）

### 致谢
- 感谢 [@CYL-collab](https://github.com/CYL-collab) 报告该问题并贡献修复。

### 验证
- 通过 TypeScript 构建、39 个文件 / 803 项测试、生产依赖审计零漏洞、181 文件 package dry-run（包含 dist 入口与公开文档，不含源码、测试、内部记录、本地配置、凭据或 Smithery 文件）、`git diff --check`、严格 UTF-8 与机密分类检查；`package.json` 与锁文件版本一致为 `1.11.1`。

---

## [1.11.0] - 2026-08-05

### 新增
- 新增 `setup` 命令：交互式凭证配置，未配置时自动引导，已配置时显示当前状态。完成后提供可选 ASR 模型安装（默认为否）。
- 新增 `doctor` 命令及 `doctor --json`：纯本地状态检查（包信息、运行时、凭证可加载性、ASR 状态），不发起网络请求。`--json` 输出为 Agent 可读的机器格式。
- 新增可选 ASR 模型安装：默认关闭，选择安装时提供三个可选模型（tiny 78 MB / base 148 MB / small 486 MB），Enter 默认推荐 small。安装到用户管理的 `~/.bilibili-mcp/asr/` 目录，通过 CPU INT8 加载验证。
- `get_video_transcript` 新增显式 `fallback_to_asr`（默认 `false`）：原生字幕优先，只有确认无可用字幕时才为已解析的一个 Part 获取临时音频，并使用 ready 的项目托管 faster-whisper 模型转录。ASR 结果返回 `data_source: "asr"`，复用时间戳、区间、关键词、上下文和证据链接。

### 修复
- 修复 CLI 帮助输出中重复的 `[command]` 占位符，统一为单一 Commander 命令派发路径。
- 修复非字符串视频输入可能暴露内部校验错误的问题，并收紧字幕地址的主机、端口和 userinfo 校验。

### 变更
- 将配置文档中的推荐引导命令从 `config` 更新为 `setup`（`config` 仍可用于强制重配）。
- Package Node.js 引擎最低版本调整为 `>=20.0.0`。
- MCP TypeScript SDK 升级至兼容的 `1.30.0`，锁文件同步到无生产依赖公告的版本集合。

### 安全
- ASR 只接受 Bilibili 专用 HTTPS CDN 主机并逐跳验证最多三次重定向；Cookie 仅发送给播放 API，不发送给 CDN 或 Python，签名播放地址不写入结果、错误或日志。
- ASR 使用唯一系统临时目录、128 MiB/2 小时/30 分钟/2 MiB/10000 段硬限制、一个活动任务且不排队、隔离子进程环境和严格 NDJSON；所有成功、失败和超时路径清理临时音频。
- 为 stdio、MCP 响应、Bilibili HTTP、缓存、日志、播放音频和 ASR 增加共享的大小、时间、数量与并发上限；播放下载使用公共地址 DNS 校验、连接固定和逐跳凭据剥离。
- 清理来自 Bilibili 的控制字符、双向覆盖、零宽字符和非法代理项；ASR 状态目录使用仅所有者权限、不可预测的独占临时文件和原子替换，并拒绝符号链接或错误路径类型。

### 文档
- 重构中英文 README：前置条件可见、可扫读安装步骤、核心功能均以产品结果表述。修正 skipped_count 仅计视频条目，修正评论排序为优先展示带时间戳和获赞较高评论。中文首屏和核心功能介绍避免不必要的 MCP server 和 Folder 术语，首次出现 BVID 时解释为 B 站视频 ID。
- 新增无文字的项目总览 Hero，展示视频搜索经本地 MCP 形成字幕定位、章节、评论和收藏夹结果；原安装流程图与收藏夹分页示例保持独立。

### 验证
- ASR Phase 3 通过 TypeScript 构建、10 个 focused 文件 / 356 项测试、29 个文件 / 629 项全量测试、156 文件 package dry-run、公开 stdio 初始化/工具列表/工具调用、机密扫描和零临时目录残留检查。当前本机没有 ready 模型，因此未下载模型，也未运行真实 ASR 转录。
- 最终安全回归通过 TypeScript 构建、39 个文件 / 803 项测试、95 项 stdio/工具/handler focused 测试、180 文件 package dry-run、`npm audit --omit=dev` 零漏洞、机密分类和零 ASR 状态临时文件残留。

---

## [1.10.1] - 2026-07-27

### 文档
- 重构中英文 README 的首屏叙事，突出从当前账号的收藏夹或主题发现视频、取得 BVID，并由用户按需继续处理字幕、元数据、章节或评论。
- 将两张 GitHub-safe SVG Hero 收窄为完整收藏夹遍历：首次调用不传 `cursor`，每次读取最多 20 条，Agent 持续传入 `next_cursor`，直到该字段不再返回；最终保留 Folder 上下文、视频标题和 BVID。
- 重新组织十个 MCP 工具、安装入口、设计重点与行为边界，明确本项目不自动生成知识笔记。

### 验证
- 通过双语 README 审计、本地链接与标题层级检查、SVG XML/安全检查、900px/360px 渲染、npm package dry-run、凭据模式扫描、TypeScript 构建和完整测试。

---

## [1.10.0] - 2026-07-27

### 新增
- 新增 `list_bilibili_favorite_videos`（第 10 个工具），从当前已登录账号自动发现所有创建的收藏夹，并按 Folder/页 返回其中的视频成员。每次调用最多返回上游一页（固定 20 条）；可选 `cursor` 是不透明、无状态、版本化的 base64url 令牌，仅编码下一个 Folder ID 与页码，不含 Cookie、账号 ID、Folder 标题或视频数据。Agent 按 `next_cursor` 翻页直到结束。（Issue #22）
- 成功结果同时返回格式化 JSON 文本和内容相同的 MCP `structuredContent`；账号无收藏夹时只返回 `folders_total: 0`、`videos: []`、`skipped_count: 0`。
- 新增 `validateFavoritesCursor` 公共输入校验，配合 favorites 模块在网络请求前完成类型/长度/字符集/JSON/版本/正整数 Folder ID 与页码的严格解码。

### 安全
- 收藏夹发现必须从已登录的当前账号身份开始；不提供匿名降级，也不读取其他账号的公开收藏。每次调用最多 1 次 nav + 1 次 created/list-all + 0 或 1 次 resource/list；不发起字幕/评论/章节/搜索/下载或任何持久化、缓存、写入请求。
- 游标在所有副作用前严格校验；同 BVID 出现在多个 Folder 时保留 Folder 上下文（不做跨 Folder 去重）；`skipped_count` 报告无法安全规范化的上游行数，且不会触发补漏请求。

### 验证
- 通过 25 个文件中的 405 项测试、TypeScript 构建、官方 MCP SDK stdio 十工具顺序与真实分页续读验收、npm package dry-run（138 个文件）和凭据/私密数据扫描。

---

## [1.9.1] - 2026-07-26

### 文档
- 将中英文 README 精简为项目首页，把 Agent 安装提示词、33 个客户端配置、凭证验证、运行时环境变量和源码安装集中到双语安装指南。
- 将完整工具参数、调用示例、错误语义与请求控制集中到双语工具参考，并确保这些文档随 npm package 分发。
- 重绘中英文 GitHub-safe SVG Hero，使用稳定的单标题和三步证据链布局，修复字体回退与固定坐标导致的错位。

### 验证
- 通过双语 README 审计、SVG 桌面与窄屏渲染、客户端与环境变量覆盖检查、凭证相关测试、npm package dry-run、链接与凭据模式扫描。

---

## [1.9.0] - 2026-07-26

### 新增
- 新增 `search_bilibili_videos`，按关键词返回 Bilibili 平台综合排序的普通视频候选。`limit` 默认 5、最大 10；每个候选包含 BVID、标题、作者、时长、发布时间、播放量、简介和来源链接。（Issue #21）
- 搜索成功结果同时返回格式化 JSON 文本与内容相同的 MCP `structuredContent`，可将候选 BVID 直接交给现有字幕、元数据、章节和评论工具。

### 安全
- 视频搜索要求有效且已登录的 Bilibili Cookie，不提供匿名降级；凭据错误继续使用现有安全配置指引，响应和日志不暴露 Cookie。

### 验证
- 通过 327 项测试、TypeScript 构建、官方 MCP SDK 1.27.1 九工具 stdio 验收、真实搜索到字幕时间链接工作流、npm package dry-run 与凭据模式扫描。

---

## [1.8.0] - 2026-07-26

### 新增
- `get_video_transcript` 在原有格式化 JSON 文本基础上，对成功结果同步返回内容相同的 MCP `structuredContent`，并声明与完整现有结果一致的 `outputSchema`。旧文本格式保持不变，错误结果仍仅返回 `content + isError`，其他七个工具与 Bilibili 请求数量不变。（Issue #16）
- 成功的 transcript 结果在根级新增 `source_url`，关键词搜索的每个 `Transcript Match` 新增 `timestamp_url`，可直接定位 Bilibili 视频/分集与字幕时刻。BVID 大小写保留不变。（Issue #17）

### 安全
- 在现有兼容范围内将锁文件中的 `body-parser` 刷新至 2.3.0、`fast-uri` 刷新至 3.1.4，清除三条生产依赖告警，不新增直接依赖或 override。保留 Node 18 支持；未使用的 Hono `serveStatic` 告警继续按上游修复进度跟踪。（Issue #19）

### 验证
- 通过 299 项测试、TypeScript 构建、npm package dry-run、生产依赖告警审计与可达性分诊，以及凭据模式扫描。

---

## [1.7.2] - 2026-07-20

### 新增
- `get_video_transcript` 支持可选关键词搜索：新增 `query`、`max_matches`、`context_segments` 参数，返回带上下文的 `Transcript Match` 列表和紧凑 transcript。大小写不敏感字面匹配，不增加额外网络请求。
- 新增验证函数：`validateQuery`、`validateMaxMatches`、`validateContextSegments`。

### 变更
- 关键词搜索与描述降级不兼容：搜索模式下不会静默降低到视频描述。
- `getVideoTranscriptData` 接受可选的 `TranscriptSearchOptions` 对象（第8参数），保留所有现有调用兼容性。

### 验证
- 通过 286 项测试（新增 42 项）、TypeScript 构建、npm package dry-run、MCP smoke test 和 git diff --check。

---

## [1.7.1] - 2026-07-20

### 文档
- 中英文 README 发布链接更新为 `v1.7.1`。
- 补充运行时调节环境变量 `BILIBILI_CACHE_SIZE` 与 `USER_AGENT` 的说明，并标注重启生效。
- 构建命令措辞更新为“清理 `dist/` 后编译 TypeScript”。
- 开发过程统计更新为 8 个 MCP 工具、244 个单元测试，并明确 Codex/Paseo/Claude 协作流程。

### 维护
- 删除遗留的认证模块 (`src/bilibili/auth.ts`) 和惰性包配置代码。
- 运行时缓存容量接入 `config.maxCacheSize`，不再硬编码。
- `npm run build` 在 TypeScript 编译前清理 `dist/`，避免已删除模块在构建产物中残留。

### 验证
- 通过 23 个 Vitest 文件中的 244 项测试、TypeScript 构建、npm package dry-run 与凭据模式扫描。
---

## [1.7.0] - 2026-07-20

### 新增
- 视频转录 (`get_video_transcript`) 支持多P分集选择 (`page`)、时间戳输出 (`include_timestamps`) 和时间区间过滤 (`start_seconds` / `end_seconds`)。
- 视频元数据 (`get_video_metadata`) 支持多P分集列表 (`pages`)。
- 新增 `get_video_chapters` 工具，返回 Bilibili 创作者/平台定义的视频章节（进度条分段）。
- `get_video_info` 支持 `page` 参数选择多P分集。

### 修复
- 多P视频 CID 选择由共享导航模块统一解析，避免各工具重复实现。
- 缓存键包含分集编号，防止不同 Part 间缓存互串。

### 验证
- 通过 23 个 Vitest 文件中的 243 项测试、TypeScript 构建、npm 生产依赖审计与 package dry-run。

---

## [1.6.4] - 2026-07-20

### 修复
- 并发 HTTP 请求现在按配置间隔依次获得启动时机，同时仍允许响应体处理重叠。
- 空字幕列表会统一验证登录状态；瞬时字幕失败产生的简介降级结果不再进入缓存。
- 评论缓存键包含详细程度与显式数量，移除重复元数据请求，并通过有界分页兑现 `limit: 1-50`。
- 登录状态、字幕和 WBI 请求保留 HTTP 状态以正确区分可重试错误；补齐传输错误归一化与请求计时器清理。
- MCP stdio 启动测试改为等待实际 ready 信号，消除固定 300ms 延迟造成的偶发失败。

### 安全
- 将间接依赖 Hono 从 4.12.23 更新至 4.12.31，清除生产依赖审计中的高危告警。

### 验证
- 通过 20 个 Vitest 文件中的 180 项测试、TypeScript 构建、npm 生产依赖审计、package dry-run、MCP stdio smoke 与凭据模式扫描。

---

## [1.6.5] - 2026-07-20

### 修复
- MCP 服务端元数据版本号由硬编码 `"1.0.0"` 改为从 `package.json` 动态读取，避免工具发现时展示过期版本。

### 验证
- 通过 20 个 Vitest 文件中的 181 项测试、TypeScript 构建、npm 生产依赖审计、package dry-run 与凭据模式扫描。

---

## [1.6.3] - 2026-06-19

### 修复
- 补齐结构化错误响应依赖的中英文凭据操作建议 helper，修复 v1.6.2 发布工作流在干净 checkout 中测试失败的问题。
- 补齐 MCP 更新检查响应的 `notes_en` / `notes_zh` 字段实现与测试，使发布包行为与 README 文档一致。

### 验证
- 重新通过完整 Vitest 测试、TypeScript 构建、npm package dry-run 和等价 MCP stdio smoke。

---

## [1.6.1] - 2026-06-18

### 文档
- 中文 README 补充 `@latest` MCP 配置、全局安装更新和 `bilibili-mcp check-update` 的明确说明。
- 英文 README 的 agent 安装引导补充 `check_mcp_update`。
- 英文工具选择表补充 `check_mcp_update`，并补充中英文工具调用示例。

---

## [1.6.0] - 2026-06-18

### 新增
- 新增 `check_mcp_update` MCP 工具，用于安全返回本地包版本、npm latest 版本、是否需要更新，以及推荐更新命令。
- 新增 `bilibili-mcp check-update` CLI 命令，用于在终端检查包版本新鲜度。

### 改进
- MCP 客户端接入示例统一优先使用 `npx -y @xzxzzx/bilibili-mcp@latest`，让新会话解析 npm latest 版本。
- 凭证配置引导和凭证相关错误的 next steps 改为使用 `@latest` 包规格。
- README 状态说明更新为 7 个 MCP 工具、145 个单元测试。

### 测试
- 新增包更新引导测试，并更新 MCP 工具列表契约测试以覆盖新的公开工具。

---

## [1.4.1] - 2026-06-04

### 🔧 改进 (Changed)
- README 重构：优化首屏快速开始、AI 客户端接入指南、工具调用示例的可读性

## [1.4.0] - 2026-06-04

### 🚀 新增 (Added)
- **两个新 MCP 工具**：
  - `get_video_transcript`：返回纯字幕文本，默认不降级到视频描述；字幕不可用时返回 `SUBTITLE_UNAVAILABLE` 错误。
  - `get_video_metadata`：返回标题、作者、时长、发布日期、描述、标签和统计信息，不获取字幕或评论。
- `get_video_comments` 扩展参数：`limit`（1-50）、`sort`（hot/time）、`include_replies`（boolean），旧调用方式仍兼容。

### 🔧 改进 (Changed)
- **安全加固**：保留 Cookie 型字幕获取能力，同时明确凭据应来自环境变量或凭据管理工具；发布包、文档、测试和示例不包含真实 Cookie 值。
- **包入口修正**：`package.json` 的 `main`/`module`/`types` 均指向 `dist` 构建产物。
- **Smithery 移除**：删除 `smithery.json`、`smithery.yaml`、`@smithery/cli` 依赖及相关脚本。
- **Bilibili 模块拆分**：将大型 `client.ts` 拆分为 `http.ts`、`wbi.ts`、`fingerprint.ts`、`video-api.ts`、`comments-api.ts` 等聚焦模块，保持公共 API 兼容。
- 字幕 fallback、WBI 签名和 buvid 指纹行为不变。

### 🧪 测试 (Tests)
- 引入 Vitest 测试基线：110 个单元测试，覆盖验证工具、BVID、输入清洗、字幕 fallback、评论 wrapper、MCP schema 和 API 行为。
- 测试不依赖真实网络、Cookie 或外部 API。

### 📝 文档 (Docs)
- README 更新：记录全部 4 个工具、新评论参数、no-cookie/Cookie-backed 行为、错误码和标准降级策略。

## [1.3.7] - 2026-03-09

### 🚀 新增 (Added)
- **Cookie 过期智能检测机制**：当字幕接口返回空列表时，工具会先调用 `/x/web-interface/nav` 核实当前登录状态，再决定是否触发 `COOKIE_EXPIRED` 错误。
  - 若**已登录**但视频无字幕 → 正常降级为简介（合法现象）
  - 若**未登录**（Cookie 过期）→ 抛出明确的错误，拒绝静默降级，方便用户和 AI 快速定位问题
- *安全提示*：错误信息仅包含状态说明，**严格脱敏，绝不泄露真实 Cookie 内容**。


---

## [1.3.5] - 2026-03-08
- 初始稳定版本，支持基础视频信息与评论抓取。
