# Bilibili 字幕到本地 AI 知识库工作流调研

## Research Topic

- Topic: Bilibili Obsidian Clipper 与 Karpathy LLM Wiki Vault 的组合方式
- Date: 2026-09-04
- Owner: Codex
- Related task, PRD, ticket, or plan: `ROADMAP.md` 参考项目
- Refresh before: 将该工作流转为集成指南、示例或产品功能之前

## Question

视频“把B站视频转成本地AI知识库！新手也能3分钟上手”展示的项目如何工作，哪些部分值得 `@xzxzzx/bilibili-mcp` 借鉴？

## Context

这项参考用于判断 MCP 能力层如何进入用户的本地笔记与 Agent 工作流，不代表已经决定在本项目内置笔记、RAG 或 Obsidian 写入。

## Sources

| Source | Type | Date checked | Notes |
|--------|------|--------------|-------|
| [Bilibili 视频 BV1g1dLBPEHV](https://www.bilibili.com/video/BV1g1dLBPEHV/) | other | 2026-09-04 | 视频说明关联两个 GitHub 项目 |
| [Bilibili-Obsidian-Clipper @ `5073907`](https://github.com/haixiong1997/Bilibili-Obsidian-Clipper/tree/50739070de8b0dea272519ab71fa73321257fdc6) | source | 2026-09-04 | README、manifest、字幕抓取、设置与 Obsidian 写入实现 |
| [karpathy-llm-wiki-vault @ `18f4e71`](https://github.com/jason-effi-lab/karpathy-llm-wiki-vault/tree/18f4e71518af7d0c51a2fc65f5e3ec3043668e54) | source | 2026-09-04 | README、目录结构、ingest 与 query skills |

## Findings

- 这不是一个新的 Bilibili MCP 服务，而是两个松耦合项目组成的下游工作流：浏览器扩展负责取得字幕并写入 Obsidian，Vault 负责把原始转录编译为可检索、互相链接的知识页面。
- Clipper 在已登录的 Bilibili 页面内调用播放器字幕接口并携带浏览器凭据，支持分 P、字幕轨选择、预览、Markdown 复制、SRT/TXT 下载、章节化内容和 Obsidian Local REST API 写入；没有字幕轨时不会执行本地 ASR。
- Vault 明确区分 `raw/` 原始事实层与 `wiki/` 编译输出层，并通过 `ingest`、`query`、`lint` skills 管理归档、索引、双链和知识维护。
- 两个项目最值得借鉴的是能力分层：Bilibili 内容获取、知识库存储、Agent 编译与查询可以独立演进，用户只组合自己需要的部分。
- Clipper 使用 `chrome.storage.local` 保存 Obsidian 与 AI 服务密钥，并把 Obsidian 地址限制为 loopback；但扩展 manifest 同时申请了广泛的 HTTP/HTTPS host permissions。若未来推荐集成，应单独说明权限与本地密钥边界。
- Clipper 采用 MIT License；调研时 Vault 仓库未声明许可证，因此不能默认复制其文件或 skill 内容。

## Applicability To This Project

Applies:

- 把 `bilibili-mcp` 维持为可靠的 Bilibili 只读证据源，让外部 Agent、CLI 脚本或笔记工具负责持久化与知识编译。
- 将“从视频到可复用资料”的首次成功路径作为安装与示例体验参考。
- 未来可候选提供一份 Obsidian/本地知识库集成配方，保留时间戳、分 P、字幕来源与原视频链接等证据字段。

Does not automatically activate:

- 在 MCP 服务内内置 Obsidian 写入、RAG、向量库、AI 对话侧边栏或长期内容存储。
- 依赖或复制上述仓库的代码、Vault 模板或 skills。

## Decision Impact

Recommended project action:

- 先作为参考项目记录。出现真实用户需求时，优先评估轻量集成指南或示例工作流，再决定是否需要新的 MCP/CLI 公共能力。

Rules or files that may need updates:

- `ROADMAP.md`

## Risks And Unknowns

- Bilibili 页面接口、Cookie 行为与字幕签名地址不是稳定公开契约。
- Obsidian Local REST API、浏览器扩展权限和本地 API Key 会引入本项目当前没有的信任边界。
- Vault 的自动归档和 Agent 写入规则是否适合本项目用户，尚无需求证据。

## Staleness Notes

在引用仓库、Bilibili 字幕接口、浏览器扩展权限或 Obsidian 接口发生变化时刷新本记录。

## Follow-Up

- [ ] 有用户明确需要本地知识库工作流时，评估一份不增加核心依赖的集成示例。
