# QA Checklist: Issue #40 AI Subtitle Integrity

## QA Session

- Title: `ai_subtitle` 数据源区分、`exclude_ai_subtitles` 与 `force_asr` 开关、ai-zh 稳定性检查
- Date: 2026-08-18
- Version or commit: worktree `28eefzkq`, branch `codex/issue-40-ai-subtitle-integrity`, fixed point `44ac1e717001aed59c4a3b475cf82f074d11e567`
- Owner: Claude Code (implementation worker), Codex (review/acceptance)
- Related ticket, plan, PRD, or release: GitHub Issue #40 (XZXZZX-Ai/bilibili-mcp)
- QA type: `MCP tool change`

## Scope

In scope:

- `data_source` 分类:`ai-zh` → `ai_subtitle`(transcript 与 video-info),人工字幕保持 `subtitle`,本地 ASR 保持 `asr`。
- `exclude_ai_subtitles`(两个工具,默认 `false`):过滤、人工优先、AI-only 视为确定性缺失、video-info 缓存键含该选项。
- `force_asr`(仅 transcript,默认 `false`):绕过字幕选择、无需 `fallback_to_asr`、优先于 `exclude_ai_subtitles`。
- 显式 `fallback_to_asr` 时 ai-zh 跨读取稳定性检查:不同 → 确定性缺失路径调 ASR;一致 → 保持 `ai_subtitle`;读取失败照常为错误。
- MCP `tools/list` schema、`tools/call` handler、transcript outputSchema 枚举、双语文档与 Unreleased changelog。

Out of scope:

- 实时 Bilibili 网络验证(确定性注入测试为验收权威,交接约定)、`setup` TTY 行为(独立后续项)、Roadmap 主树文件、发布/版本/依赖变更、GitHub 变更。

## Preconditions

- [x] 干净 worktree 指纹与 `44ac1e7` 固定点已确认。
- [x] 基线测试数已记录:41 文件 / 862 测试通过(`npm ci` 后)。
- [x] 测试使用合成数据与 mock 边界,无真实凭据值。

## Automated Baseline

- Build: `npm run build` 通过。注意:首跑发现并修复一处类型错误(本地 `SubtitleData.data_source` 缺 `ai_subtitle`,TS2322),修复后重跑通过。
- Focused tests: `npx vitest run tests/bilibili-transcript.test.ts tests/server-tools.test.ts tests/server-handler-sanitization.test.ts tests/server-error-next-steps.test.ts` → 4 文件 / 194 通过。
- ASR/playback 回归:`npx vitest run tests/asr-transcription.test.ts tests/bilibili-playback.test.ts` → 2 文件 / 44 通过。
- Full tests: `npm test` → 41 文件 / 885 通过(基线 862 + 新增 23;修复类型错误前 smoke 套件因 build 失败而红,修复后全绿)。
- Pack: `npm pack --dry-run --json --ignore-scripts` → 185 文件,`dist/` 与双语文档齐全,无 tests/src 泄漏,无新依赖。
- Stdio smoke: built `dist/index.js` 上 `tools/list` 证明 transcript 与 video-info 的新布尔输入(描述声明默认 false)、transcript outputSchema 枚举 `[subtitle, ai_subtitle, description, asr]`、video-info 保持原有无 outputSchema 设计;`tools/call` 非布尔 `force_asr` → `VALIDATION_ERROR`,未打印任何字幕正文或凭据。
- Skipped checks and reason: 真实 Bilibili 网络验证按交接约定跳过(注入测试为验收权威);`npm audit` 未跑(无新依赖,pack 内容与基线一致)。

(最终验证矩阵执行后回填 — 已完成)

## MCP And Transcript Behavior

- [x] 人工字幕仍返回 `data_source: "subtitle"`。
- [x] 选中 `ai-zh` 时 transcript 与 video-info 均返回 `data_source: "ai_subtitle"`,search 模式同样成立。
- [x] 本地 ASR 仍为 `data_source: "asr"`,description 仍为 `description`。
- [x] 默认输入保持原生优先,不自动调用 ASR。
- [x] `exclude_ai_subtitles: true` 在两个工具的 schema 中发布并类型校验;混合字幕优先人工;AI-only 走确定性缺失路径(transcript 可 ASR/description,video-info 返回 description 且不缓存)。
- [x] video-info 缓存键区分 `exclude_ai_subtitles`(同输入不同选项不串缓存)。
- [x] `force_asr: true` 发布在 transcript schema 并类型校验;绕过有效人工字幕;无需 `fallback_to_asr`;与 `exclude_ai_subtitles` 同传时不冲突、force 生效。
- [x] `fallback_to_asr: true` 时同一 ai-zh 两次读取不同 → 调用 ASR;两次一致 → `ai_subtitle` 且不调 ASR;未显式开启时不双读。
- [x] 任一读取的网络/HTTP 错误照常传播,不成为静默 ASR 门槛。
- [x] transcript outputSchema 枚举与文本载荷一致(`subtitle`、`ai_subtitle`、`description`、`asr`);十工具数量/顺序与旧文本兼容不变。
- [x] 非布尔 `exclude_ai_subtitles` / `force_asr` 在业务调用前返回 `VALIDATION_ERROR`。
- [x] 双语文档与 changelog 警告 `ai_subtitle` 是 Bilibili AI 转录、可能不准确、不承诺标题语义校验,并记录两个新输入与精确默认值。

## Security And Privacy Checks

- [x] 日志/测试/报告不含 Cookie 值、字幕正文、签名 URL、正文哈希、本地路径。
- [x] 稳定性检查的比较只使用规范化表示,不落日志。
- [x] 无新依赖、版本、工具数量或模型变更;`bilibili-mcp-asr-*` 临时目录本次验证前后计数不变(2 → 2,为历史残留,无新增)。
- [x] `git diff --check` 通过。

## Result

- Overall result: `pass with caveats`
- Blocking issues:
- Non-blocking caveat: live 语义正确性依赖注入测试;真实 Bilibili 不稳定 ai-zh 现场未复现。
- Follow-up tickets:
- Codemap update status: 已更新 —— `src/bilibili/subtitle.ts` 条目补充 ai_subtitle 分类、exclude/force 开关与稳定性检查;MCP Tool Surface 无结构变化,其余条目 unchanged。
- Research note: not required (本地源码、测试与交付契约为权威)。
- Independent review: risk-reviewer 子代理结果见 Claude 报告。
