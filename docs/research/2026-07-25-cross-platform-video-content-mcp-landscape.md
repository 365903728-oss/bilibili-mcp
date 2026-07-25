# Research Note: 跨平台视频内容 MCP 与 Agent 工具版图

## Research Topic

- Topic: YouTube、播客与通用视频理解工具对 `@xzxzzx/bilibili-mcp` 下一阶段方向的启示
- Date: 2026-07-25
- Owner: Codex
- Related task, PRD, ticket, or plan: 产品方向调研；Phase A 结构化输出试点已批准为 GitHub Issue #16
- Refresh before: 创建下一项公开工具行为的 spec/ticket，或 2026-10-25 之后再次使用本结论

## Question

其他平台的 MCP、CLI 和视频研究 Agent 实际解决了哪些问题？哪些能力适合直接迁移到本项目，哪些会破坏当前轻量、只读、隐私友好的产品边界？

## Context

当前项目已有 8 个工具，内容面覆盖视频信息、评论、完整/区间字幕、字幕关键词搜索、元数据、多 P 和章节；运维面覆盖凭证引导、凭证检查和版本检查。`get_video_transcript` 已支持时间戳、起止时间、关键词、匹配数和上下文段数，因此 2026-07-20 研究中“先做字幕关键词搜索”的建议已经完成，不能继续当作下一方向。

调研时更明显的缺口是：成功结果仍以 JSON 字符串放在 MCP `text` content 中，工具没有 `outputSchema` / `structuredContent`；字幕命中也还不是完整的“可引用证据”，缺少统一的原视频 URL、可点击时间链接、分页游标和来源/置信度契约。Issue #16 随后完成了仅针对 `get_video_transcript` 的结构化输出试点。

## Sources

| Source | Type | Date checked | Notes |
|---|---|---|---|
| [`src/server/tool-schemas.ts`](../../src/server/tool-schemas.ts) 与 [`tool-handlers.ts`](../../src/server/tool-handlers.ts) | local source | 2026-07-25 | 当前 8 工具、参数和 JSON-as-text 返回方式的权威事实。 |
| [kimtaeyoon83/mcp-server-youtube-transcript](https://github.com/kimtaeyoon83/mcp-server-youtube-transcript) | live source / GitHub API | 2026-07-25 | 574 stars / 97 forks；完整字幕、时间戳、章节标记去广告、可选 TwelveLabs；有 `outputSchema` 和 `structuredContent`。 |
| [jkawamoto/mcp-youtube-transcript](https://github.com/jkawamoto/mcp-youtube-transcript) 与 [v0.7.0](https://github.com/jkawamoto/mcp-youtube-transcript/releases/tag/v0.7.0) | live source / release / issue | 2026-07-25 | 458 / 69；普通/定时字幕、语言、元数据、cursor 分页和响应上限。 |
| [ZubeidHendricks/youtube-mcp-server](https://github.com/ZubeidHendricks/youtube-mcp-server) 与 [v1.0.2](https://github.com/ZubeidHendricks/youtube-mcp-server/releases/tag/v1.0.2) | live source / release | 2026-07-25 | 555 / 127；搜索、频道发现、播放列表、字幕；stdio + Streamable HTTP。 |
| [kevinwatt/yt-dlp-mcp](https://github.com/kevinwatt/yt-dlp-mcp) 与 [v0.9.0](https://github.com/kevinwatt/yt-dlp-mcp/releases/tag/v0.9.0) | live source / release | 2026-07-25 | 262 / 60；依靠 yt-dlp 跨平台，覆盖字幕、元数据、评论和下载。 |
| [supadata-ai/mcp](https://github.com/supadata-ai/mcp) | live source | 2026-07-25 | 61 / 10；YouTube、TikTok、Instagram、X、文件 URL；云端转录、抽取和异步轮询。 |
| [ZeroPointRepo/youtube-mcp](https://github.com/ZeroPointRepo/youtube-mcp) | vendor documentation | 2026-07-25 | 7 / 2；远程 OAuth/API key MCP，搜索→频道/播放列表→字幕；仓库没有服务端源码。 |
| [JCodesMore/youtube-for-ai-agents](https://github.com/JCodesMore/youtube-for-ai-agents) | live source | 2026-07-25 | 44 / 15；工具 + skills + video-watcher agent，支持区间/段数控制、下载和剪辑。 |
| [ixex/tubepilot](https://github.com/ixex/tubepilot) 与 [v1.0.1](https://github.com/ixex/tubepilot/releases/tag/v1.0.1) | live source / release | 2026-07-25 | 2 / 1；用 YouTube storyboard sprite 提取指定时刻画面，并与字幕一起返回 MCP image content。 |
| [coyaSONG/youtube-mcp-server](https://github.com/coyaSONG/youtube-mcp-server) | live source | 2026-07-25 | 15 / 3；citation-ready research：先过滤再分页、时间链接、跨视频有界证据、结构化输出和 HTTP 安全限制。 |
| [video-db/skills](https://github.com/video-db/skills) | official source | 2026-07-25 | “See → Understand → Act”：采集/直播、语音/场景/OCR/对象索引、时刻检索、剪辑/HLS。 |
| [TwelveLabs MCP documentation](https://docs.twelvelabs.io/docs/advanced/model-context-protocol) | official docs | 2026-07-25 | 单视频搜索/分析/embedding 与跨视频 Jockey 工作流；依赖上传、索引和云 API。 |
| [bramdehart/podcast-mcp](https://github.com/bramdehart/podcast-mcp) | live source | 2026-07-25 | RSS → Faster Whisper + pyannote → pgvector；跨集语义检索、说话人和 `speaker_confidence`。 |
| [jonathanmoore/tldl](https://github.com/jonathanmoore/tldl) | live source | 2026-07-25 | Spotify/Apple 元数据匹配 YouTube 原生字幕，返回 `match_confidence`，低于 0.55 拒绝。 |
| [r266-tech/xiaoyuzhou](https://github.com/r266-tech/xiaoyuzhou) 与 [akshayvkt/lenny-mcp](https://github.com/akshayvkt/lenny-mcp) | live source | 2026-07-25 | 前者从 MCP 转向 CLI + JSONL/字段投影；后者用静态垂直语料库提供搜索。 |

## Findings

### 样本分型

| 类型 | 代表 | 真正解决的问题 | 对本项目的含义 |
|---|---|---|---|
| 可靠字幕连接器 | kimtaeyoon83、jkawamoto | 无需复杂工作流，稳定取得全文、定时段和语言信息 | 极简工具仍有强传播力；字幕可靠性是基本盘。 |
| 平台研究连接器 | ZubeidHendricks、coyaSONG | 搜索/频道/列表后，对字幕和评论做有界证据检索 | 下一竞争点不是“再加摘要”，而是从发现到引用的闭环。 |
| 跨平台适配层 | yt-dlp-mcp、Supadata | 用通用抓取器或云 API 统一多个平台 | 扩面快，但把二进制、Cookie、上传、计费和平台变更带入核心。 |
| 视频理解基础设施 | VideoDB、TwelveLabs、podcast-mcp | ASR、说话人、画面/OCR/对象、向量索引和跨视频检索 | 已是独立子系统，不适合直接塞进轻量 stdio 包。 |
| 工作流/语料产品 | youtube-for-ai-agents、xiaoyuzhou CLI、lenny-mcp | 工具之外提供研究流程，或针对批量/垂直语料优化交互 | MCP 不是所有批量任务的最佳界面；垂直语料和技能层可以独立演进。 |

### 代表项目比较

| Project | 工具面与输出 | 传输/依赖 | 可借鉴点 | 限制 |
|---|---|---|---|---|
| kimtaeyoon83 | 2 tools；全文/时间戳；结构化输出 | stdio；InnerTube；视觉分析另接 TwelveLabs | 小而可靠、协议契约清楚 | 全文 dump 有 token 风险；无发现和评论。 |
| jkawamoto | 4 tools；typed timed segments；cursor | stdio、Docker、MCPB；yt-dlp + transcript API | 响应上限、游标和代理支持 | 当前仍有分页易用性 Issue；无平台探索。 |
| ZubeidHendricks | 10 tools；视频/频道/playlist/字幕 | stdio + HTTP；Data API key 轮换 | discovery 路径完整、HTTP 部署成熟 | 返回 JSON text；源码中私有方法不等于已暴露工具。 |
| yt-dlp-mcp | 10 tools；搜索、字幕、评论、下载 | stdio；yt-dlp/deno/cookies | 评论树、平台适配器思路 | 写盘、二进制和平台 churn 明显扩大边界。 |
| Supadata | 9 tools；转录、metadata、抽取、crawl | stdio + 云 HTTP；付费 API | 大任务 job/status 模式、跨平台 | 上传隐私、成本和供应商锁定；不是本地轻量连接器。 |
| coyaSONG | research-video 支持关键词/word/substring/时间范围/offset；有结构化结果 | stdio/HTTP；Bearer、CORS、session 限制 | 每条证据含标题、频道、源 URL、时间戳链接、total/returned/nextOffset；跨视频限 2–5 个且每源有界 | 15 stars，成熟度仍需时间检验。 |
| TubePilot | 49 tools；字幕、章节、评论、单帧/时刻 | stdio；InnerTube storyboard + sharp | “字幕 + 同时刻画面”是很好的证据单元 | 低采用度；大量所谓分析只是启发式格式化。 |
| podcast-mcp / tldl | 说话人检索或跨平台元数据匹配 | 本地 ASR/向量库，或平台原生字幕 | `source`、`match_confidence`、`speaker_confidence` 都是一等字段 | 采集/索引复杂；跨平台映射会产生误配。 |

### 横向判断

- **工具越多并不代表产品越强。** 574-star 的 kim 项目主要仍是完整字幕，而 49-tool TubePilot 只有 2 stars。成熟项目的共同基本盘是“可靠取得内容”，不是在 server 内复制模型的摘要、情感和关键词推理。
- **结构化 MCP 输出是现实空档。** 多数样本把 JSON stringify 到 `text`；kim 与 coyaSONG 证明 `outputSchema` + `structuredContent` 可以让客户端稳定消费字段，同时保留文本兼容层。
- **长视频控制是产品契约。** cursor、detail level、`start/end`、`maxSegments`、`offset/nextOffset` 和每源上限，决定 Agent 能否在不淹没上下文的情况下研究视频。
- **“moment / evidence”比“transcript”更接近下一代抽象。** 一条证据应至少包含来源、标题/分 P、命中文本、起止秒数、原 URL 和可点击时间链接；可选再附同时刻单帧、章节和观众反应。
- **跨平台不等于把 yt-dlp 放进核心。** yt-dlp 适合作为可替换适配器或独立 sidecar；云 ASR/视觉索引则应是显式 opt-in 服务。二者都改变安装、隐私、成本和维护模型。
- **发现是入口，Bilibili 原生信号才是护城河。** 搜索、UP 主/系列和跨视频查询很常见；章节、多 P、时间戳评论、未来的弹幕密度/热词与字幕同时间轴结合，才是本项目独特价值。
- **批量浏览未必适合 MCP。** 小宇宙项目改用 CLI + JSONL、真正 cursor 分页和字段投影，说明大列表、管道和批处理应与交互式 MCP 分开设计。

## Applicability To This Project

### 可直接借鉴

- 为现有成功响应补 `outputSchema` 和 `structuredContent`，同时保留当前 `content[].text` 以兼容旧客户端。
- 建立统一证据契约：`source`、`bvid`、`page/cid`、标题/作者、`start_seconds`、`end_seconds`、`source_url`、`timestamp_url`、`total`、`returned`、`truncated`、`next_offset/cursor`。
- 延续已有“先 query/时间范围过滤，再限制返回”的路线；不要先生成全文再让模型自己找。
- 若未来做跨视频研究，先限制为 2–5 个明确视频、每源独立上限和独立分页；持久化索引另立子系统。
- 任何跨平台映射、ASR 或说话人识别都显式返回 `source` 和 `confidence`；低于阈值时拒绝伪装成确定结果。
- 视觉能力从一个候选时刻的一张预览帧开始，而不是先建设完整视频下载和视觉向量库。

### 不应照搬

- 不复制 40–50 个细碎工具，也不在 server 内加入通用摘要、情感、技术栈提取等 LLM 已能完成的推理。
- 不把视频/音频下载、剪辑、上传、评论发布或账号写操作纳入当前只读核心。
- 不默认上传用户视频到第三方 ASR/视觉服务；不能只写“可选”而隐去计费、保留期和隐私边界。
- 不把 README 中存在但 MCP 工具列表未注册的方法当成产品能力。
- 不把 GitHub stars 或供应商性能宣称当作质量结论；它们只用于观察传播和活跃度。

## Decision Impact

### 对现有路线的修正

2026-07-20 的方向排序需要更新：字幕关键词搜索已经实现，不再是候选；下一步也不应直接跳到通用跨平台或重型 ASR。主线应从“Bilibili 内容提取器”收敛为 **Bilibili citation-ready evidence server**：

`发现视频 → 有界定位片段 → 返回可点击、可验证证据 → 叠加章节/评论/弹幕等平台信号`

### 分阶段建议

1. **Phase A：证据与协议契约。** 不增加新上游接口；给现有工具补结构化输出和统一 `source` 字段，为字幕命中补原视频/时间链接、返回计数和游标。先做兼容性 spec 与客户端验证。
2. **Phase B：单视频 research mode。** 在现有 transcript/metadata/chapters/comments 之上形成一个有界研究结果；优先复用现有 handler，不重复抓取。是否新增 `research_video` 工具，应在 PRD 中比较“组合现有工具”与“稳定聚合契约”。
3. **Phase C：发现与 B 站原生证据。** 依次评估 `search_bilibili_videos`、UP 主/系列导航和限量/时间范围弹幕。搜索负责入口，弹幕与时间戳评论负责差异化。
4. **Phase D：有界跨视频研究。** 先支持用户显式给出的 2–5 个视频、每视频有上限的证据合并；规模扩大后再拆出独立索引/CLI，而不是让一个 MCP 调用吞入整个频道。
5. **Phase E：可选视觉/ASR sidecar。** 先验证时间点单帧；只有无字幕需求被证实时，再设计本地或云 ASR provider。默认核心仍使用平台原生字幕，不上传视频。

Recommended project action:

- 下一张产品 ticket 应先定义“证据契约与结构化输出”，而不是新增第 9 个内容 API。
- 随后的 discovery/danmaku ticket 必须有真实 Bilibili 接口探针、分页上限、缓存/风控策略和 token 预算。
- 跨平台、持久索引、下载剪辑和 ASR 不进入同一 ticket；需要单独架构决策与明确用户授权。

Rules or files that may need updates after approval:

- `src/server/tool-schemas.ts`
- `src/server/tool-handlers.ts`
- 对应 TypeScript 类型、测试、README/README_EN
- 新功能的 GitHub Issue、Codex-to-Claude handoff 与 `docs/agent-memory/` 中的正式决策记录

## Risks And Unknowns

- Issue #16 已验证 MCP SDK 1.27.1 的 `outputSchema` / `structuredContent` 双轨契约和 Codex CLI 0.144.6 的旧 JSON 兼容路径；Claude Desktop 与 Cursor 仍未测试。
- Bilibili 时间参数深链在普通视频、多 P、移动端和不同客户端中的行为尚未实测，不能先承诺统一 URL 格式。
- 搜索、弹幕、storyboard/预览帧接口的稳定性、登录要求和风控成本仍需单独 live probe。
- GitHub 活跃度和 stars 会变化；ZeroPoint 的后端能力只有厂商文档，无法用源码独立复核。
- 单视频聚合工具可能重复现有工具并增加响应体；是否新增必须用真实 Agent 任务比较调用次数、token 和引用质量。
- ASR、说话人和视觉置信度不是同一概念；未来不能用一个含糊的 `confidence` 掩盖不同模型与来源。

## Staleness Notes

Refresh this research when:

- 任何代表仓库改变工具面、传输或结构化输出方式
- MCP SDK 的 tool result/output schema 或任务机制发生变化
- 项目准备实现搜索、弹幕、跨视频研究、ASR 或视觉能力
- Bilibili 页面时间链接、字幕、评论、弹幕或预览图接口发生变化

## Follow-Up

- [x] 用 `product-requirements` 明确证据契约、旧客户端兼容和成功指标。
- [ ] 对 Bilibili 时间深链做普通视频/多 P/桌面与移动端的真实验证。
- [x] 将 Phase A 拆成 GitHub Issue #16 与有界 Codex-to-Claude handoff，并完成单工具试点。
