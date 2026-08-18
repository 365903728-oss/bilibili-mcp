# Claude To Codex Report: Issue #40 AI Subtitle Integrity

## Summary

Issue #40 (ai-zh 与人工字幕混标) 已按冻结契约实现完毕:ai-zh 在两个工具上独立分类为 `ai_subtitle`;新增 `exclude_ai_subtitles`(两工具,默认 false)与 `force_asr`(仅 transcript,默认 false);显式 `fallback_to_asr` 时对 ai-zh 做跨读取稳定性检查,不一致走确定性缺失路径调 ASR。实现全程垂直 TDD(每切片先红后绿),13 项验收标准均有确定性注入测试。三方审查(risk-reviewer、code-review 两轴)均无阻塞发现;唯一流程缺口(Claude 报告)由本文件闭合。未做任何 commit/push/PR/release,未变更 GitHub。

## Files Changed

源码(4):
- `src/bilibili/subtitle.ts` — `isAiSubtitle`(lan === "ai-zh")、`canonicalSubtitleBody`(仅比较用)、`SubtitleData.data_source` 加 `ai_subtitle`;`getVideoTranscriptData` 追加 `excludeAiSubtitles`、`forceAsr`(fallbackToAsr 之后、signal 之前);`getVideoInfoWithSubtitle` 追加 `excludeAiSubtitles`(第 4 参);force_asr 早退到 `handleDefinitiveSubtitleAbsence(reason, true)`;exclude 过滤 + AI-only 确定性缺失(不走登录验证路径);稳定性双读;缓存键含 exclude 标志;AI-only 结果不缓存。
- `src/bilibili/types.ts` — `VideoSummary.data_source` / `VideoTranscriptData.data_source` 联合类型扩展。
- `src/server/tool-schemas.ts` — 两个新布尔输入(描述文本声明默认 false,沿用无 JSON `default` 字段的原有风格);transcript outputSchema 枚举 `[subtitle, ai_subtitle, description, asr]`。
- `src/server/tool-handlers.ts` — 两个工具的读取、类型校验(`VALIDATION_ERROR`)与参数转发;transcript 11 参元组与签名逐位一致。

测试(3):`tests/bilibili-transcript.test.ts`(新增 19 测试 / 5 块)、`tests/server-tools.test.ts`(schema 断言 + 3 新测试)、`tests/server-handler-sanitization.test.ts`(转发 + it.each 非布尔拒绝,3 新测试)。

文档(6):`README.md` / `README_EN.md`、`docs/tool-reference.md` / `docs/tool-reference.en.md`、`CHANGELOG.md` / `CHANGELOG_EN.md`([Unreleased] 4 条目)。

Harness 文件(3):`docs/qa/2026-08-18-issue-40-ai-subtitle-integrity.md`(新建)、`docs/agent-memory/codemap.md`(subtitle.ts 条目更新)、本报告。

未改:`package.json` / lockfile(零新依赖)、`src/utils/validation.ts`(复用既有 `validateBoolean` 模式)、`ROADMAP.md`(Codex 所有)、`setup` TTY 路径。

## Commands Run

实现前红测试(每切片一次,均已先红后绿):

```bash
npx vitest run tests/bilibili-transcript.test.ts
# 切片A红灯: 3 failed — expected 'subtitle' to be 'ai_subtitle' (ai-zh 分类)
# 切片B红灯: AI-only+exclude 未触发缺失路径(未调 ASR、未返回 description)
# 切片B红灯: 缓存键不含 exclude(exclude=true/false 串缓存)
# 切片C红灯: expected 'ai_subtitle' to be 'asr'(force_asr 未绕过)
# 切片D红灯: 双读不一致未调 ASR;第二次读取异常未传播
```

(切片 B–D 的精确失败摘要在此前上下文压缩前已捕获;切片 C 后还修复过一次 signal 参数错位——AbortSignal 曾落到第 11 参位置被误当作 force_asr,修复后重跑绿。)

实现后验证矩阵:

```bash
npx vitest run tests/bilibili-transcript.test.ts tests/server-tools.test.ts tests/server-handler-sanitization.test.ts tests/server-error-next-steps.test.ts   # 4 文件 / 194 通过
npx vitest run tests/asr-transcription.test.ts tests/bilibili-playback.test.ts                                                                            # 2 文件 / 44 通过
npm test                                                                                                                                                # 41 文件 / 885 通过(基线 862 + 新增 23)
npm run build                                                                                                                                           # tsc 通过
npm pack --dry-run --json --ignore-scripts                                                                                                              # 185 文件,dist 齐全
git diff --check                                                                                                                                        # 无输出
```

内置 stdio smoke(临时脚本,已删):`dist/index.js` 上 `tools/list` 证明两个新布尔输入(描述声明默认 false)、transcript outputSchema 枚举含 `ai_subtitle`、工具数/顺序不变(10);`tools/call` 传 `force_asr: "yes"` → `VALIDATION_ERROR`,未打印任何字幕正文或凭据。

## Results

- 完整测试 885/885 通过;构建通过;pack 内容 185 文件(双语文档 + dist,无 tests/src 泄漏)。
- 修复过一处 tsc 错误:本地 `SubtitleData.data_source` 缺 `ai_subtitle`(TS2322)——vitest(esbuild)不做类型检查,首跑 `npm run build` 才暴露;修复后全绿。此前 smoke 套件因 build 失败而红,属同一根因。
- 临时目录:`bilibili-mcp-asr-*` 验证前后计数不变(2→2,均为历史残留,本次无新增)。
- 三方审查:risk-reviewer **pass**(0 bug;4 条 low:双读条件中 `!forceAsr` 不可达但符合契约字面、`?? []` 防御不可达、空 body 第二次读取→ASR 为契约允许的显式决策、报告文件缺失);code-review Spec 轴 **通过**(10/10 验收标准,无 scope creep);Standards 轴 **无硬违规**(4 条判断性:AI-only description 块与既有 3 处重复、位置参数增长与 2026-07-20 的 options-object 方向相左——但契约明确指定 append、`typeof` 校验级联 5 处为既有模式延续、`handleDefinitiveSubtitleAbsence` 名称被 force_asr 拉伸)。
- secret-scanning:0 凭据值;4 处字段名引用均为原有文档行(非本次变更引入)。risk-reviewer 的凭据模式扫描同样零命中。

## Diff Notes

- 精确分类:`lan === "ai-zh"` → `ai_subtitle`(transcript 与 video-info 共用 `isAiSubtitle` 单点);人工字幕保持 `subtitle`;本地 ASR 保持 `asr`;description 保持 `description`。
- 选项语义:`exclude_ai_subtitles` 过滤后人工优先;AI-only 时两工具都走确定性缺失(transcript 按既有 fallback 链,可 ASR/description;video-info 返回 description 且不缓存),且不触发登录验证路径(与"空字幕"路径刻意分离)。`force_asr` 早退、绕过全部字幕选择(含有效人工字幕)、不依赖 `fallback_to_asr`、优先于 exclude。稳定性双读仅当 ai-zh 选中 && `fallback_to_asr` 显式 true && 非 force_asr;两次正文规范化比较不同 → 确定性缺失路径调 ASR;一致 → 保持 `ai_subtitle` 且不调 ASR;任一次传输/超时/认证/解析失败仍为错误,绝不成为 ASR 门槛。
- 兼容性:位置参数一律追加;transcript 签名 `(…, fallbackToAsr, excludeAiSubtitles, forceAsr, signal)` 与 handler 元组逐位一致;video-info 第 4 参。唯一破坏面是枚举扩展 `subtitle` → `ai_subtitle`,与 schema/handler/文档原子发布。

## Risks Or Skipped Checks

- 未解决:真实 Bilibili 现场的不稳定 ai-zh(六种互异正文)无法复现——按契约以注入测试为验收权威,已在 QA 文件记录;搜索模式 + 不稳定 ai-zh(对 ASR 输出做 search)无独立测试,共享已测的 `buildSegmentResult` 机制,不阻塞。
- 未跑:`npm audit`(零新依赖,pack 内容与基线一致)。
- 决策点(交回 Codex):Standards 轴的两条判断性发现——(a) AI-only description 返回块与既有 3 处重复,可抽共享 helper 或维持现状;(b) 位置参数追加与 2026-07-20 handoff 的"options-object"方向相左,本次按冻结契约执行 append,若 Roadmap 想收敛可做后续重构。
- 延期项(按契约):非 TTY `setup` 脚本化(独立后续项,与凭据输入安全相关,未触碰);Roadmap 最终对齐由 Codex 完成(`ROADMAP.md` 未改)。

## Harness Artifacts

- Task ticket: used —— GitHub Issue #40 为 ticket,handoff 为冻结执行契约(仓库规则要求 MCP 工具变更使用 ticket)。
- Research note: not required —— 本地源码、注入测试与交付契约为权威,无外部行为研究。
- QA checklist: created —— `docs/qa/2026-08-18-issue-40-ai-subtitle-integrity.md`(13 项行为检查全绿、安全/临时目录/凭据扫描记录、Automated Baseline 含 build 修复注记)。
- Codemap: updated —— `src/bilibili/subtitle.ts` 条目补充 ai_subtitle 分类、exclude/force 开关与稳定性检查;MCP Tool Surface 无结构变化。
- Harness security: reviewed —— 变更面(handler 验证、缓存键、稳定性比较)不触及信任边界;稳定性比较仅用规范化表示不落日志;无新凭据路径;`docs/agent-memory/harness-security.md` 规则未受影响。
- Harness eval: deferred —— 非 Roadmap 阶段/发布节点,harness 本身无变化。

## Decision Points

1. `!forceAsr` 在双读条件中不可达(force_asr 早退):保留作为契约字面守卫,无行为影响;删除与否由 Codex 定夺。
2. 空 body 的第二次读取按契约视为"不同正文"→ ASR;与传输失败(抛错)严格区分,已是显式决策。
3. AI-only description 块重复与位置参数风格收敛:见 Risks 决策点 (a)/(b),均建议作为独立后续,不影响本变更验收。

## Suggested Codex Review Focus

- 双读条件(契约 §5 的字面符合性)与 `handleDefinitiveSubtitleAbsence(reason, runAsr)` 复用是否如契约预期。
- 缓存键 `generateKey('video', bvid, preferredLang, page, excludeAiSubtitles ?? false)` 与 AI-only 不缓存的行为。
- 枚举扩展的原子发布与双语文档措辞。
- 若认可后续收敛,评估 (a) description 块共享 helper、(b) transcript 参数 options-object 化的独立票。
