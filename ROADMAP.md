# 项目路线图

最后更新：2026-09-04

本文件是 `@xzxzzx/bilibili-mcp` 的统一长期路线入口，汇总已经完成的开发路线、当前候选方向和未来规划。

它不是执行授权：真正开始一项工作前，仍需形成边界明确的 GitHub Issue；当前正在执行的任务以 `docs/agent-memory/active-work.md` 为准。

## 产品方向

项目继续专注于 Bilibili 原生内容证据能力：视频发现、分 P 与章节、字幕、时间定位、评论和收藏夹。优先深化这些能力的可靠性、可引用性和 Agent 使用体验，不把本仓库扩展成通用跨平台视频下载、自动笔记、RAG 或内容持久化系统。

下一阶段增长面向学生、普通内容用户，以及把 MCP 组合进 Agent 自动化工作流的开发者。第一增长问题已经确定为降低安装、登录和首次成功使用的门槛；CLI 是否增加内容读取命令、以及如何与 MCP 协同，保留到后续单独决策。增长只观察 GitHub Stars、npm 聚合下载、Fork 和用户主动反馈等公开信号，不在 MCP 或 CLI 中加入产品遥测。

## 状态说明

- **已完成**：已有发布、关闭的 GitHub Issue 或正式验证记录。
- **开发树中**：已经实现并验证，但仍位于当前未发布工作树中。
- **未来候选**：已经记录方向，但没有因此自动获得实现、提交或发布授权。
- **按需评估**：只有出现明确产品或客户端需求时才进入 PRD 与 Issue 阶段。

## 当前路线

### P0：完成可选 ASR 闭环

状态：**开发树中 / 下一阶段候选**

已经完成：

- CLI `setup` / `doctor --json` 的安装与诊断入口。
- 可选 ASR 安装 Phase 1。
- `tiny`、`base`、`small` 三模型白名单选择器 Phase 2，默认推荐 `small`。
- 用户目录中的托管 Python 环境、固定模型版本、安装状态和 CPU INT8 加载验证。

下一阶段：

1. 实现真实音频转写回退，并保持默认关闭、由调用方显式启用。
2. 明确临时音频下载、使用和清理的完整生命周期。
3. 保持 Cookie、临时音频、模型路径和子进程环境不进入日志或 MCP 响应。
4. 用聚焦测试、构建、stdio MCP smoke 和真实本地验收锁定回退语义。

边界：不自动下载或切换模型，不把 ASR 变成后台常驻服务，不在本阶段扩展任意 Hugging Face 仓库或多模型同时保留。

已知缺陷（2026-08-18 现场发现，GitHub Issue #41 已删除转本地记录）：

- **损坏字幕被原样透传**：BV1ybuQ62EfK 的 `ai-zh`/`zh-Hans`/`zh-CN` 字幕连续 6 次返回 6 份互不相关的错乱内容（与视频主题无关），MCP 未做内容校验直接返回。
- **fallback_to_asr 永不触发**：B 站 API 始终返回损坏的 `ai-zh` 字幕时，MCP 判定「有字幕」，`fallback_to_asr: true` 不生效，ASR 从未被调用；用户只能绕过 MCP 手动请求 playurl 获取音频再自行转录。
- **修复方向**：字幕内容校验（跨请求一致性/与标题主题匹配度/语言一致性），损坏时自动降级 ASR；提供 `force_asr` 参数绕过字幕存在性检测；`ASR_AUDIO_UNAVAILABLE` 时增加重试或可操作错误信息。
- **次要**：`setup` 命令强制交互式 TTY，管道输入被拒绝，无法脚本化安装。

本轮对齐（2026-08-18，Issue #40 隔离候选，尚未提交/发布）：

- **已覆盖 Issue #40**：`ai-zh` 以及当前上游暴露的 `ai-en`、`ai-ja` 等全部 `ai-*` 字幕不再与人工字幕共用 `subtitle`，而是返回 `ai_subtitle`；`get_video_info` 与 `get_video_transcript` 均新增默认关闭的 `exclude_ai_subtitles`，开启后会排除整个 `ai-*` 集合。
- **已覆盖直接相关缺陷**：`get_video_transcript` 新增默认关闭的 `force_asr`；每个选中的 `ai-*` 都会无条件双读取，并以无碰撞的 `[from,to,content]` 归一化做稳定性校验；保守的 Han 比例语言一致性检查只用于 `ai-zh`，避免误杀正常 `ai-en` 等轨道。判定不可用后，只有显式授权 `fallback_to_asr` 才进入现有 ASR 路径，否则按既有简介降级或 `SUBTITLE_UNAVAILABLE` 契约处理。
- **已有能力，无需重复实现**：音频下载已经按最多 3 个候选地址有界尝试；`ASR_AUDIO_UNAVAILABLE` 已返回可重试标记和双语操作建议，本轮不再叠加新的重试层。
- **已确认的边界**：标题词面重合无法可靠证明语义一致，曾验证会同时误收无关内容和误杀正常内容，因此不作为硬拒绝门。稳定、同语言但语义离题的字幕仍可能通过；调用方可用 `exclude_ai_subtitles` 或 `force_asr` 明确控制。
- **已覆盖次要缺陷**：新增 `setup --non-interactive`，只接受 env/global config 中可加载的凭据，可选 `--asr-model <tiny|base|small>`；不会提示，也不会从 stdin/argv 读取凭据值。未指定模型时只验证凭据，不下载模型。
- **实时验证状态**：使用已登录全局凭据对 `BV15kyBB5Eg8` 完成只读验证：默认 transcript/video-info 均返回 `ai_subtitle` 且存在正文，开启排除后分别返回 `NoSubtitleError` 与无字幕正文的 description。损坏正文拒绝与真实 ASR 回退仍只由自动化覆盖，因为 `BV1ybuQ62EfK` 当前不再暴露目标字幕，且本轮未授权真实模型运行。

### P1：MCP 协议现代化

状态：**未来候选，尚未激活**

在 ASR 与 CLI 工作达到稳定边界后，作为独立 GitHub Issue 推进：

1. 先增加真实 wire-level stdio 集成测试，覆盖 `initialize` → `tools/list` → `tools/call`。
2. 将现有研究整理成新旧协议双时代验收矩阵，覆盖现代发现流程、结果与缓存字段以及旧客户端回退。
3. 验收矩阵冻结后，再评估迁移到 TypeScript SDK v2 的双时代 stdio 路径。
4. annotations、icons、更多 structured output、Tasks、MRTR 和 HTTP transport 仅在出现真实需求时评估。

研究依据：

- `docs/research/2026-07-29-mcp-protocol-update.md`
- `docs/research/2026-07-29-mcp-tools-evolution.md`
- `docs/agent-memory/decisions.md` 中 2026-07-29 的协议决策

### P2：继续深化 Bilibili 原生能力

状态：**按需评估**

后续功能必须先证明真实使用价值，并优先复用现有工具和数据流。候选方向包括：

- 提升现有搜索、收藏夹遍历、字幕证据和评论读取的稳定性与可诊断性。
- 为更多已有工具补充 structured output，但必须保持现有文本结果兼容。
- 在 Bilibili 提供可靠原生数据时，增加新的时间线或证据定位能力。
- 评估“非生成式本地资料导出”：把字幕及其标题、BV 号、分 P、语言、时间戳、字幕来源和原视频链接完整保存为 Markdown 或 JSON，补齐从读取结果到可靠本地资料的最后一公里。优先从单视频字幕开始，复用现有读取逻辑；它不等同于 Bilibili 账号写操作、AI 笔记生成或内置知识库。
- 在保留手动 Cookie 回退、登录后实时校验和秘密不进入 MCP 响应的前提下，优先评估 `setup` 内的本地终端扫码登录。
- 根据真实客户端兼容性反馈改进安装、诊断和错误恢复指引。

尚未激活的扩展候选包括：跨平台视频适配、自动生成学习笔记、内置 RAG/向量库、长期保存用户内容，以及无明确需求的 HTTP 服务化。它们没有被排除；出现真实需求后再分别进入产品发现和取舍。

## 参考项目

### OpenBiliClaw

状态：**已记录，仅供产品参考**

[OpenBiliClaw](https://github.com/whiteguo233/OpenBiliClaw) 是一个本地优先的跨平台个性化内容发现 Agent。它先根据用户行为、反馈和对话形成分层用户模型，再主动寻找内容，并为推荐提供解释。项目另有 [DSH 插件](https://github.com/whiteguo233/dsh-openbiliclaw) 和浏览器扩展。

值得参考：

- 从“平台替用户决定内容”转向“用户先表达目标，Agent 再主动发现内容”的产品叙事。
- 推荐理由与反馈闭环，降低仅凭标题、封面和历史点击作判断的问题。
- 核心用户数据本地优先保存，并把后端、浏览器扩展和 DSH 客户端适配器分开。

当前边界与待选项：

- `bilibili-mcp` 当前仍保持 Bilibili 原生证据工具定位；是否扩展为跨平台推荐系统尚未进入产品决策。
- 心理画像、MBTI 推断、五层用户模型、推荐池、自动探索和长期行为数据库均作为未激活候选保留。
- OpenBiliClaw 的远程安装脚本、`0.0.0.0` 服务绑定和 DSH 插件安装命令仅作风险参考，若未来采用需单独评估。

研究记录：`docs/research/2026-08-16-openbiliclaw-reference.md`。记录参考项目不授权安装、规格设计或实现；若未来要吸收具体能力，必须重新核对上游并单独确认产品边界。

### VideoToNote

状态：**已记录，仅供产品参考**

[介绍视频（BV1Qwby6DEu1）](https://www.bilibili.com/video/BV1Qwby6DEu1) 展示了开源项目 [video-to-note](https://github.com/like-attract/video-to-note)：把 B 站、YouTube 或本地视频整理为带时间轴、要点和点评分析的 Markdown 笔记，并支持本地字幕转写与多格式导出。

值得参考：

- 从视频链接到可回看笔记的完整交付形态，以及真实时间轴与原视频之间的定位关系。
- 在“结论、要点、时间戳、点评”之间形成清晰层次，而不是只输出一段摘要。
- 本地优先处理、无字幕时转写、Markdown 等可迁移格式，以及通过 MCP 接入 AI 客户端的组合方式。

当前边界与待选项：

- 该项目当前作为竞品和交互参考；自动生成笔记、下载媒体、支持 YouTube、本地文件和多格式导出继续作为未激活候选保留。
- 若未来吸收具体能力，应先比较其时间轴证据、字幕来源、长视频分块和点评生成方式与本项目现有工具边界，再单独确认需求与实现计划。

### Bilibili Obsidian Clipper + Karpathy LLM Wiki Vault

状态：**已调研，作为下游知识工作流参考**

[介绍视频（BV1g1dLBPEHV）](https://www.bilibili.com/video/BV1g1dLBPEHV/) 展示了 [Bilibili Obsidian Clipper](https://github.com/haixiong1997/Bilibili-Obsidian-Clipper) 与 [Karpathy LLM Wiki Vault](https://github.com/jason-effi-lab/karpathy-llm-wiki-vault) 的组合：浏览器扩展从已登录的 Bilibili 页面获取字幕并写入 Obsidian，Vault 再由 Agent 把原始转录编译成可索引、互相链接的本地知识页面。

值得参考：

- 将 Bilibili 内容读取、资料持久化和 Agent 知识编译拆成可独立替换的层，而不是全部塞进一个 MCP 服务。
- 用 `raw/` 原始事实层与 `wiki/` 编译输出层分离来源和生成内容，并保留原视频、分 P、字幕轨与时间戳等证据。
- 把“视频链接到可查询本地资料”包装为短而清晰的首次成功路径，帮助非开发者理解产品价值。
- 对本项目而言，更轻量的吸收方式是未来提供 Obsidian/本地知识库集成配方，让 MCP 继续负责可靠读取，由用户选择的 Agent 或工具负责写入。

当前边界与待选项：

- 这项参考不自动激活内置 Obsidian 写入、RAG、向量库、AI 侧边栏或长期内容存储；这些能力仍可在出现需求后单独评估。
- Clipper 依赖浏览器登录态且只处理已有字幕轨的视频；本项目现有 Cookie、可选 ASR 和证据能力仍有不同价值。
- 若未来提供集成示例，需要重新核对浏览器扩展权限、本地 API Key、Bilibili 页面接口和 Vault 许可证，不直接复制上游实现。

完整源码证据、固定版本与风险见 `docs/research/2026-09-04-bilibili-obsidian-knowledge-workflow.md`。本次记录只增加项目参考，不授权安装、实现、依赖变更、提交、推送或发布。

### 同类 Bilibili MCP 项目扫描（2026-09-04）

状态：**已调研，候选尚未激活**

通过 GitHub CLI 与 AgentKey/Exa 交叉搜索，并核对候选仓库的当前源码后，新增以下参考：

- [BiliBili_VideoRead_MCP](https://github.com/Yotsuki2213/BiliBili_VideoRead_MCP)：最值得借鉴的是终端二维码登录、登录后实时校验，以及分段读取、按时间排序并限量采样弹幕。
- [Iseenope/bilibili-mcp-server](https://github.com/Iseenope/bilibili-mcp-server)：可用于观察扫码轮询、Cookie 刷新、直播关键帧与大工具面的取舍，但其文档、返回形态和刷新持久化存在需要重新验证的差异。
- [Ghpt6/bilibili-subtitle](https://github.com/Ghpt6/bilibili-subtitle)：只读“稍后再看”列表可作为收藏夹之后的轻量入口；删除单项和清空列表属于会改变现有只读边界的写操作候选，需要单独评估。
- [sandraschi/bilibili-mcp](https://github.com/sandraschi/bilibili-mcp)：匿名能力与登录后账号能力的分层表达值得用于安装、状态和错误指引；其额外 HTTP/Web UI 与服务内总结层作为不同产品形态保留待选。
- [nameefef/bilibili-mcp](https://github.com/nameefef/bilibili-mcp)：官方开放平台 OAuth 适合作为未来“本人投稿与数据”适配器的合规边界参考，不能替代任意公开视频、字幕、评论、搜索和收藏夹读取。

优先级判断：

1. **高优先级候选：本地 CLI 扫码登录。** 放入现有 `setup`，成功后复用当前凭据管理与登录检查；保留手动 Cookie 方式。Bilibili Web 扫码接口虽为第一方端点，但不视为稳定公开契约，必须有清晰降级。
2. **中优先级候选：紧凑弹幕读取。** 只读、限量，并支持时间范围或关键词过滤；不照搬 2,000 条默认输出。
3. **低优先级候选：“稍后再看”。** 读取可先独立评估；删除与清空会产生账号副作用，需要另行确认需求、安全边界和撤销方案。

尚未取舍的扩展方向：自动评论、点赞、关注、发送弹幕、上传、下载、清空账号列表、内置 RAG/LLM 总结、远程付费 MCP，以及额外 HTTP/Web UI。这些方向继续作为候选保留；若要进入实施，应分别确认真实需求、账号与凭据风险、成本和验收标准，不因本次调研自动激活或打包实施。

完整源码证据、版本固定点、差异与风险见 `docs/research/2026-09-04-bilibili-mcp-peer-projects.md`。本次记录不授权实现、依赖变更、提交、推送或发布。

方向决定（2026-09-04）：先解决安装、登录和首次成功体验，因此本地扫码登录是下一项产品发现候选；这项决定尚未授权规格、实现或发布。CLI 内容读取与 MCP 的协同方式暂未决定。

容量切换规则（2026-09-04）：时间较少时可以选择一个有证据、能独立收口的维护事项；出现完整开发时间时，默认回到扫码登录的产品发现与规格路线。短期维护不视为替代或完成新功能路线，也不自动授权宽泛架构重构或安全改造。“优化项目”可执行到什么范围暂未决定，留待具体任务出现时确认。

## 工程工作流路线

Harness v2 是独立的工程治理路线，不等同于产品功能路线，也不应改变 MCP 公共行为。GitHub Issue #28 是总规范，#29–#36 与 #38 记录可移植会话骨架、三种执行适配器、受控记忆与演进以及完整闭环验证。

这些 Issue 当前仍以 GitHub 实时状态为准。它们不能绕过写入租约、用户授权、凭据安全、验证、提交、推送和发布边界。

### 未来候选：完整 CI/CD 工作流

状态：**未来候选，尚未激活**

在产品行为和 MCP 协议边界稳定后，以独立 GitHub Issue 设计并建设一套可维护的 CI/CD 工作流：

1. PR 持续集成统一运行依赖安装、构建、全量测试、`npm pack --dry-run`、包内容与凭据泄漏检查，并将稳定检查设为受保护分支的 required checks。
2. 根据 `package.json` 的受支持 Node 范围建立最小但有效的版本矩阵；跨平台问题有真实证据时，再增加 Windows smoke，避免无依据扩张矩阵。
3. 将 PR/分支验证与发布工作流分离；普通 push 不得发布，只有明确授权的版本标签或 Release 事件才能进入发布门。
4. npm 发布继续使用 trusted publishing/OIDC、最小 `GITHUB_TOKEN` 权限和 provenance，不引入长期 npm token；发布 job 使用受保护 environment，并保持 tag、commit 与包版本一一对应。
5. 发布成功后自动核对 npm registry 版本与 provenance、包内容、精确版本 CLI/MCP smoke、远端 tag SHA 和 GitHub Release；失败时提供可重跑、可诊断且不会重复发布的恢复路径。
6. 为工作流增加并发取消、超时、有限缓存与有限 artifact 保留；固定并定期审查第三方 Actions，工作流文件变更需单独审查。

边界：开始前先审计现有 `.github/workflows/` 和分支保护状态，再冻结验收矩阵；不与产品功能 PR 混做，不使用公共仓库自托管 runner，不让 CI 自动批准或合并 PR，也不因路线记录自动获得发布授权。

## 历史路线

### 2026-05：稳定化基础

状态：**已完成**

- 移除硬编码 Bilibili 凭据，同时保留 Cookie 登录能力。
- 修正 npm 包入口并清理发布内容。
- 移除已废止的 Smithery 运行配置。
- 建立真实 Vitest 基线、构建和 `npm pack --dry-run` 验证。
- 完成 `src/bilibili/client.ts` 拆分、MCP 工具面整理、文档和发布流程加固。

历史来源：`docs/superpowers/plans/2026-05-27-stabilization-roadmap.md` 及同目录的 Phase 2–4 计划。它们只作为历史证据，不再是现行指令。

### 2026-06：可靠性、可维护性和 Agent 安装体验

状态：**已完成**

- 建立项目记忆、受控学习提案和轻量项目 hooks。
- 增加 Agent 可发现的凭据配置与检查工具，以及结构化错误 `next_steps`。
- 完成依赖健康、日志脱敏、MCP handler 拆分、类型与缓存加固、编码清理和 stdio 集成测试基线。
- 完成可信发布、provenance、发布后 npm 与 CLI 验证流程。

历史来源：`docs/superpowers/plans/2026-06-14-project-optimization-roadmap.md` 及对应的独立实施计划。总路线图中的未勾选项不代表未完成；后续独立计划、验证记录和发布结果是更高优先级证据。

### 2026-07：从字幕读取扩展为可导航证据工作流

状态：**已完成至 v1.10.1 发布基线**

- v1.7.x：分 P、时间范围字幕、Bilibili 原生章节和字幕关键词搜索。
- v1.8.0：字幕 structured output 与可引用证据链接。
- v1.9.0：有界、需登录的 Bilibili 视频搜索。
- v1.10.0：当前账号全部收藏夹的游标遍历和来源上下文。
- v1.10.1：双语首页与收藏夹证据工作流文档完善。

对应 PRD：

- `docs/navigable-transcript-prd.md`
- `docs/transcript-keyword-search-prd.md`
- `docs/structured-transcript-output-prd.md`
- `docs/transcript-evidence-links-prd.md`
- `docs/bilibili-video-search-prd.md`
- `docs/bilibili-favorites-discovery-prd.md`
- `docs/comment-limit-pagination-prd.md`

### 2026-07 至今：CLI 与可选本地 ASR

状态：**Phase 1、Phase 2 已在开发树中验证；Phase 3 尚未开始**

- 将首次配置整理为人类使用的 `setup` 和 Agent 使用的 `doctor --json`。
- Phase 1 建立固定推荐模型的安全安装、诊断和状态记录。
- Phase 2 增加三个固定模型的选择与切换。
- Phase 3 留给真实转写回退和临时音频生命周期，不与安装器阶段混做。

对应 PRD：

- `docs/asr-model-install-prd.md`
- `docs/asr-model-selector-prd.md`

## 维护规则

1. 本文件只维护路线级别的目标、顺序、边界和历史里程碑，不复制任务级实现步骤。
2. `docs/agent-memory/active-work.md` 只记录当前工作树和正在执行的任务，并链接回本文件。
3. GitHub Issues 是 PRD、规格和可执行任务的实时来源；开始工作前必须读取完整 Issue、依赖和评论。
4. 路线完成后，将其移入“历史路线”，并附上发布、Issue 或验证证据。
5. `docs/superpowers/` 永久保持历史档案身份，不能因为被本文件引用而重新成为现行计划。
6. 新方向只有在用户确认、形成必要 PRD/规格并创建边界明确的 Issue 后，才能进入执行。
