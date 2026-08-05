# MCP Server Tools 演进史（2024-10-07 至 2026-07-28）

## Research Topic

- Topic: MCP 规范中 server tools 能力的历史演进
- Date: 2026-07-29
- Owner: Codex research subagent
- Related task, PRD, ticket, or plan: 用户要求学习此前 MCP 工具更新历程
- Refresh before: 下一版稳定 MCP 规范发布，或本项目开始 MCP TypeScript SDK v2 / `2026-07-28` 协议迁移前

## Question

从官方仓库保留的 `2024-10-07` 前史，到 `2024-11-05`、`2025-03-26`、`2025-06-18`、`2025-11-25` 和 `2026-07-28`，MCP 的 `tools/list`、`tools/call`、工具 schema、annotations、结构化输出、图标与 `_meta`、Tasks 和 MRTR、缓存与无状态语义分别如何演进？哪些属于稳定核心协议，哪些曾是实验能力或现为扩展，哪些只是 SDK 提供的便利 API？

## Context

Why this matters for `@xzxzzx/bilibili-mcp`:

- 本项目是一个 stdio MCP server，核心公开面就是 10 个 Bilibili 工具。
- 当前项目已经使用 `inputSchema`、`content` / `isError`，并为 3 个工具提供 `outputSchema` + `structuredContent`；判断是否升级不能只看 SDK 版本号，还要知道这些能力分别来自哪一代协议。

What decision or implementation this may affect:

- 是否需要为了历史上某个 tools 增量立即修改项目。
- 将来升级到 MCP `2026-07-28` / TypeScript SDK v2 时，哪些是必要线协议变化，哪些只是可选的工具元数据或扩展能力。

## Sources

以下均为 MCP 官方规范站、官方 GitHub 仓库或官方 TypeScript SDK 文档。

| Source | Type | Date checked | Notes |
|--------|------|--------------|-------|
| [2024-10-07 release](https://github.com/modelcontextprotocol/modelcontextprotocol/releases/tag/2024-10-07) | official release | 2026-07-29 | 官方仓库保留的早期已标记版本 |
| [2024-10-07 tools 专章（tag 内原文）](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2024-10-07/docs/spec/tools.md) | official tagged spec | 2026-07-29 | `tools/list` 文档形态及 `toolResult` |
| [2024-10-07 TypeScript schema](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2024-10-07/schema/schema.ts) | official tagged schema | 2026-07-29 | 发现与 tools 专章有关分页的内部不一致 |
| [2024-11-05 release](https://github.com/modelcontextprotocol/modelcontextprotocol/releases/tag/2024-11-05) | official release | 2026-07-29 | 官方称其为 initial revision |
| [2024-11-05 tools](https://modelcontextprotocol.io/specification/2024-11-05/server/tools) | official spec | 2026-07-29 | content blocks、`isError`、分页、list changed |
| [2024-11-05 TypeScript schema](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2024-11-05/schema.ts) | official schema | 2026-07-29 | Tool、CallToolResult、通用 `_meta` |
| [2025-03-26 changelog](https://modelcontextprotocol.io/specification/2025-03-26/changelog) | official changelog | 2026-07-29 | tool annotations、audio |
| [2025-03-26 tools](https://modelcontextprotocol.io/specification/2025-03-26/server/tools) | official spec | 2026-07-29 | annotations 的信任边界和返回内容类型 |
| [2025-03-26 TypeScript schema](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2025-03-26/schema.ts) | official schema | 2026-07-29 | annotation 字段的精确定义 |
| [2025-06-18 changelog](https://modelcontextprotocol.io/specification/2025-06-18/changelog) | official changelog | 2026-07-29 | structured tool output、resource links |
| [2025-06-18 tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) | official spec | 2026-07-29 | `structuredContent`、`outputSchema`、兼容文本 |
| [2025-06-18 TypeScript schema](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2025-06-18/schema.ts) | official schema | 2026-07-29 | `title` / `_meta` 和 object-root 限制 |
| [2025-11-25 changelog](https://modelcontextprotocol.io/specification/2025-11-25/changelog) | official changelog | 2026-07-29 | icons、tool naming、sampling tool calls、实验 Tasks |
| [2025-11-25 tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) | official spec | 2026-07-29 | icons、JSON Schema 默认版本、`execution.taskSupport` |
| [2025-11-25 Tasks](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/tasks) | official experimental spec | 2026-07-29 | Tasks 的实验状态、轮询和延迟结果 |
| [2026-07-28 changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog) | official changelog | 2026-07-29 | 无状态、MRTR、Tasks 扩展、缓存、schema 放宽 |
| [2026-07-28 tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools) | official spec | 2026-07-29 | 当前稳定 tools 线协议 |
| [2026-07-28 TypeScript schema](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2026-07-28/schema.ts) | official schema | 2026-07-29 | `resultType`、CacheableResult、任意 JSON 输出 |
| [TypeScript SDK server tools 文档](https://github.com/modelcontextprotocol/typescript-sdk/blob/main/docs/server.md#tools) | official SDK docs | 2026-07-29 | `registerTool`、schema 转换和 handler 行为属于 SDK 层 |

## Findings

### Executive summary

MCP tools 的主干并没有反复推倒重来。`tools` capability、`tools/list`、`tools/call` 和 `notifications/tools/list_changed` 自早期版本延续至今；演进主要是逐层增加：

1. 把任意 JSON 工具结果收敛为模型可消费的 content blocks 和显式 `isError`。
2. 增加工具行为 hints（annotations）和多模态结果。
3. 增加可校验的结构化输出、资源链接、展示标题和可扩展元数据。
4. 增加图标、命名约束，以及一套后来被重新设计的实验 Tasks。
5. 在 `2026-07-28` 把协议改为无状态，把缓存、MRTR 和更完整的 JSON Schema 语义纳入核心，同时把 Tasks 移出核心成为扩展。

因此，“历史上增加了很多工具字段”不等于每个 MCP server 都必须实现它们。多数元数据和结果类型是按需使用；真正需要在协议代际迁移时成套处理的是 `2026-07-28` 的无状态请求上下文、`resultType`、可缓存列表结果等线协议要求。

### Timeline

| Version | `tools/list` | `tools/call` / result | Schema and metadata | Protocol status |
|---------|--------------|-----------------------|---------------------|-----------------|
| `2024-10-07`（前史） | tools 专章将请求写成 `Params: None`，响应只列 `tools`；支持 `listChanged` | 返回 `toolResult: any JSON-serializable value`；工具执行错误放在成功的 CallToolResult 内 | Tool 只有 `name`、`description`、object-shaped `inputSchema`；通用请求/通知/结果 envelope 已有 `_meta` | 官方仓库保留的早期已标记版本；不要与后续 release 页面称为 initial revision 的 `2024-11-05` 混同 |
| `2024-11-05` | 明确 cursor pagination；保留 capability 和 list-changed notification | 结果改为 `content[]`，支持 text、image、embedded resource，并增加 `isError` | Tool 仍是 `name`、`description`、`inputSchema`；没有 tool annotations、output schema 或 icons | 首个被官方 release 页面称为 initial revision 的版本 |
| `2025-03-26` | 方法和分页形态不变 | content 新增 audio | 新增 `ToolAnnotations`: `title`、`readOnlyHint`、`destructiveHint`、`idempotentHint`、`openWorldHint`；全部只是来自 server 的不可信 hints | 稳定核心 tools 增量 |
| `2025-06-18` | 方法形态不变 | 新增 `structuredContent`（当时必须是 JSON object）和 `resource_link`; 若返回结构化内容，兼容性上 SHOULD 同时给序列化 TextContent | 新增可选 `outputSchema`（当时 root 必须是 object）；声明后 server MUST 让结构化结果符合 schema，client SHOULD 校验。Tool 也具有直接 `title` 和 `_meta` | 稳定核心 tools 增量 |
| `2025-11-25` | 方法形态不变；新增工具名长度/字符指导 | 普通调用形态不变；可实验性地做 task-augmented call | Tool 新增 `icons`；input/output schema 可写 `$schema`，未写时默认 JSON Schema 2020-12，但 input/output root 仍限制为 object；新增 `execution.taskSupport` | icons / naming 是核心；Tasks 明确标为 experimental |
| `2026-07-28` | 工具集合不得按连接或连接内副作用变化，可按每请求 authorization 变化；SHOULD 稳定排序；结果必须有 `ttlMs`、`cacheScope` 和 `resultType`；list-changed 通过订阅流投递 | 普通结果带 `resultType: "complete"`；也可返回 `resultType: "input_required"`，通过 MRTR 的 `inputRequests` / retry `inputResponses` 继续同一逻辑请求 | input 仍要求 object root，但可使用完整 JSON Schema 2020-12 keywords；output schema 和 `structuredContent` 可为任意 JSON 值；增加 `$ref` 规则、`x-mcp-header`；`_meta` 承担每请求版本/能力和结果 server info | MRTR / cache / stateless 是核心；2025 Tasks 从核心移出，改为官方 `io.modelcontextprotocol/tasks` 扩展 |

### 2024-10-07：有价值的前史，但官方资料内部存在分页不一致

- [release](https://github.com/modelcontextprotocol/modelcontextprotocol/releases/tag/2024-10-07) 说明这是 `2024-10-07` 版本的最终更新。
- tag 内 [tools 专章](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2024-10-07/docs/spec/tools.md) 将 `tools/list` 写成无 params 请求，响应字段只描述 `tools`，没有展示 `cursor` / `nextCursor`；`tools/call` 的结果是一个不限定结构的 `toolResult`。
- 但是同 tag 的 [TypeScript schema](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2024-10-07/schema/schema.ts) 已让 `ListToolsRequest` / `ListToolsResult` 继承通用 `PaginatedRequest` / `PaginatedResult`，因此 schema 层已经允许 `cursor` / `nextCursor`。
- 最准确的说法是：**2024-10 的工具专章和 wire examples 仍是“无分页列表 + 任意 JSON toolResult”的早期形态；同期 schema 已预埋通用分页。** 不能把“专章未记录分页”扩大成“该 tag 的所有官方定义都禁止分页”。

### 2024-11-05：建立延续至今的 tools 基线

- 官方 [release](https://github.com/modelcontextprotocol/modelcontextprotocol/releases/tag/2024-11-05) 把它称为 MCP 的 initial `2024-11-05` revision。
- `tools/list` 明确支持 cursor pagination；server 可通过 `tools.listChanged` capability 和 `notifications/tools/list_changed` 通知工具集合变化。
- `tools/call` 不再返回不透明 `toolResult`，而是返回一组模型可读的 content blocks。执行错误通过 `isError: true` 留在 tool result 中，未知工具、协议级无效参数等仍走 JSON-RPC error。
- 这一代已经在通用 `Result` 上保留 `_meta`，所以 `_meta` 不是 2025 年 icons 出现后才有的概念；只是当时 Tool 本身没有 `_meta`、title、annotations 或 icons。

### 2025-03-26：行为注解与 audio

- changelog 把 “comprehensive tool annotations” 列为 major change。
- `annotations` 包括人类可读 `title`，以及 read-only、destructive、idempotent、open-world 四个行为 hints。规范明确要求 client 把来自不可信 server 的 annotations 当作不可信信息，不能把它们当授权或安全策略。
- 工具结果 content 新增 audio。`tools/list` / `tools/call` 的 RPC 名称和基本形态没有改变。
- 此时仍没有 `outputSchema` 或 `structuredContent`。

### 2025-06-18：结构化输出成为核心协议能力

- changelog 明确新增 structured tool output 和 tool result 中的 `resource_link`。
- Tool 可声明 `outputSchema`。一旦声明，server **MUST** 返回符合它的 `structuredContent`，client **SHOULD** 校验。
- 当时 `outputSchema` 和 `structuredContent` 都限制为 JSON object。规范建议同时返回 JSON 序列化的 TextContent，保持旧 client / 模型消费路径兼容。
- schema 同时让 Tool 继承通用 metadata，具有直接 `title`；显示优先级是 `title`、`annotations.title`、`name`。Tool 和 content blocks 也获得各自 `_meta` 扩展位。这里的 `_meta` 与模型可见的 `content` / 业务结构化数据不同，不应把业务结果塞进 `_meta`。

### 2025-11-25：展示元数据成熟，Tasks 只是实验方案

- 核心 Tool 增加 `icons`，规范也给出工具名 1–128 字符及建议字符集。图标是 UI metadata，并不改变执行语义。
- schema 开始明确 `$schema`，缺省按 JSON Schema 2020-12；但这一版 input/output root 仍为 object。
- Tasks 被加入核心规范目录，但页面开头明确写着 **experimental**。支持方需声明 tasks capability，工具还可用 `execution.taskSupport` 表示 `"forbidden"`（默认）、`"optional"` 或 `"required"`。
- task-augmented `tools/call` 先返回 task handle，再通过 `tasks/get` 轮询、`tasks/result` 取最终结果；还存在 `tasks/list` / `tasks/cancel`。这套设计不能视为后来版本仍保持不变的稳定契约。
- 同版还允许 `sampling/createMessage` 携带 `tools` / `toolChoice`。这是 client sampling 能力的扩展，不是 `tools/list` / `tools/call` server API 的替代。

### 2026-07-28：无状态、MRTR、缓存与通用 JSON 输出

- 协议移除 session 和 initialize handshake。请求通过 `_meta` 携带协议版本与 client capabilities；server 通过 `server/discover` 暴露支持信息。对 tools 而言，工具列表不能再依赖隐式连接状态。
- `tools/list` 的工具集合不得因同一连接中的其他请求而变化，也不得按连接本身变化；但可以基于每次请求携带的 authorization 过滤。规范建议稳定排序。
- `ListToolsResult` 现在继承 `CacheableResult`，`ttlMs` 和 `cacheScope` 都是必填字段。`cacheScope` 区分可跨授权上下文共享的 `"public"` 与只能在相同授权上下文复用的 `"private"`。
- 所有成功结果都要求 `resultType`。旧协议结果缺失时，client 必须按 `"complete"` 处理，提供了向后兼容规则。
- MRTR（Multi Round-Trip Requests）是新的核心模式。`tools/call` 可返回 `InputRequiredResult`，用 `inputRequests` 表达所需 elicitation 等输入；client 使用新的 JSON-RPC id 重试原请求，并带回 `inputResponses` 和可选 `requestState`。
- 2025 的实验 Tasks 被移出核心，重做为官方 `io.modelcontextprotocol/tasks` 扩展；同时核心 Tool 不再有 `execution.taskSupport`。**MRTR 解决“继续当前请求需要额外输入”，Tasks 扩展解决“持久、可轮询的长任务”，两者不是同一功能。**
- `inputSchema` 仍必须是 object root，因为 tool arguments 始终是对象，但可以使用完整 JSON Schema 2020-12 关键字；`outputSchema` 可描述任意 JSON 值，`structuredContent` 也可为 object、array、scalar 或 null。
- `x-mcp-header` 允许把指定 tool argument 映射成 Streamable HTTP header，服务于 proxy / load balancer / WAF 路由；它不是 stdio server 的通用参数传递机制。

### Core、experimental / extension 与 SDK convenience 的边界

| Category | Examples | What it means |
|----------|----------|---------------|
| Stable core protocol | `tools/list`, `tools/call`, `inputSchema`, `content`, `isError`, annotations, structured output, icons；在 `2026-07-28` 还包括 `resultType`、MRTR、list cache fields | 这些字段和 RPC 写在线协议规范 / schema 中；实现某一协议版本时按该版本的 MUST / SHOULD 执行 |
| Experimental in a historical core revision | `2025-11-25` Tasks、`execution.taskSupport`、`tasks/result` 等 | 当时可试用，但规范明确不保证设计不变；不能据此推断当前核心协议 |
| Official extension | `2026-07-28` 的 `io.modelcontextprotocol/tasks` | 由核心的 `extensions` 协商机制启用，不是所有 tools server 的默认义务 |
| Adjacent client feature | sampling 中的 `tools` / `toolChoice` | 让 server 请求 client 采样时可提供工具，不改变 server tools discovery/call RPC |
| TypeScript SDK convenience | `McpServer.registerTool(...)`、Zod / Standard Schema 转 JSON Schema、入参校验、handler exception 转 tool error | 帮开发者生成和验证核心协议消息；不是新的 wire method，也不能替代协议版本协商 |

## Applicability To This Project

Applies:

- `src/server.ts` 使用低层 `Server` 注册 `ListToolsRequestSchema` 和 `CallToolRequestSchema`；`src/server/tool-schemas.ts` 静态列出 10 个工具。因此项目已实现从 `2024-11-05` 延续至今的核心 discovery / call 基线。
- 10 个工具都提供 object-root `inputSchema`。当前固定数组顺序也已经满足 `2026-07-28` 的 deterministic-order 建议。
- `get_video_transcript`、`search_bilibili_videos` 和 `list_bilibili_favorite_videos` 已提供 `outputSchema`，成功时同时返回 TextContent 和 `structuredContent`，正是 `2025-06-18` 建立的兼容模式。
- 工具级失败通过 TextContent + `isError: true` 返回，沿用 `2024-11-05` 建立的可由模型读取和自我修正的错误路径。
- 项目没有 tool annotations、直接 title、icons、Tool `_meta`、Tasks / MRTR、`resultType`、`ttlMs` / `cacheScope` 或 `x-mcp-header`。其中前四类大多是可选 metadata；后几项属于升级到 `2026-07-28` 协议时需要由新版 SDK / server architecture 成套处理的线协议变化。

Does not apply:

- 当前只有 stdio transport，`x-mcp-header` 和 HTTP intermediary cache routing 没有直接用途。
- 当前 Bilibili 查询工具以一次调用返回结果，没有已经证实需要持久轮询和延迟取回的工具；不应只因 Tasks 曾经出现过就引入任务存储。
- annotations / icons 不影响工具是否可调用，也不构成权限控制，不能把缺失这些字段判定为协议错误。
- 当前 object-shaped structured outputs 已是 `2026-07-28` 任意 JSON 输出能力的合法子集；没有业务需要时，不必为了“用上新能力”改成数组或 scalar output。

## Decision Impact

Recommended project action:

- **不因这段历史单独立即改代码。** 当前工具行为不是停留在最早期：它已经覆盖稳定基线，并选择性采用了 2025-06 的结构化输出。
- 把 `2026-07-28` 迁移作为独立、成套的 SDK v2 / protocol-era 工作，而不是给现有 `toolSchemas` 零散补 `resultType` 或缓存字段。
- 真正迁移时，优先验证 wire-level 必需项：stateless request context、`server/discover`、`resultType`、`ListToolsResult.ttlMs/cacheScope`、订阅式 list-changed；然后再评估 annotations / icons 这类可选 UX metadata。
- 只有出现真实的持久长任务，才评估官方 Tasks extension；只有工具在完成前确实需要用户 / client 补充输入，才评估 MRTR。

Rules or files that may need updates:

- 未来迁移候选：`package.json` / lockfile、`src/server.ts`、协议级测试 helper 和真实 handshake / discovery integration tests。
- 可选 UX 改进候选：`src/server/tool-schemas.ts` 的准确 annotations / title / icons；它们不是本轮必改项。

## Risks And Unknowns

- `2024-10-07` 的 tools 专章与同 tag TypeScript schema 对 pagination 的描述不一致，本文已分别记录，后续引用时不要只摘一句“无分页”而省略 schema 证据。
- MCP release 页面明确提醒 SDK 会按自己的节奏采用新规范；“规范已发布”不等于当前安装的 SDK 或所有 client 已支持。
- annotations 是 hints，client 支持程度和 UI 呈现并不统一；即使项目添加，也不能假定 client 一定展示。
- `2026-07-28` 是一次协议代际变更。将其字段机械地加入旧版 SDK 返回对象，不等同于完成协议兼容。

## Staleness Notes

Refresh this research when:

- MCP 发布 `2026-07-28` 之后的新稳定规范
- 官方 Tasks extension 再次修订或进入不同生命周期状态
- TypeScript SDK v2 改变 `2026-07-28` tools / MRTR / cache 的实现 API
- 本项目准备新增 HTTP transport、持久长任务或需要多轮输入的工具

## Follow-Up

- [ ] 在独立 MCP v2 迁移 issue 中，把本时间线转成 wire-compatibility acceptance matrix
- [ ] 迁移前用真实 client/server 协议测试验证 `server/discover`、`tools/list` cache fields、`resultType` 和 MRTR，而不是依赖 SDK 私有 handler
- [ ] 若产品需要更好的工具选择和 UI 展示，再逐工具审核 annotations / title / icons 的真实性
