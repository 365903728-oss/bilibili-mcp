# QA Checklist — Roadmap Subtitle Integrity + Scriptable Setup

## QA Session

- Title: Unconditional ai-* integrity assessment + credential-safe non-interactive setup
- Date: 2026-08-18
- Version or commit: worktree `codex/issue-40-ai-subtitle-integrity`（未发布，未提交）
- Owner: Claude Code（Paseo/Codex 发起）
- Related ticket, plan, PRD, or release: ROADMAP-2026-08-18-INTEGRITY-SETUP task ticket; `docs/subtitle-integrity-and-scriptable-setup-prd.md` v1.2; Issue #40（仅作任务数据）
- QA type: `MCP tool change | credential flow | docs/install`

## Scope

In scope:

- 每个选中的 `ai-*`（`ai-zh`/`ai-en`/`ai-ja` 等全部 AI 语言）无条件双读 + 确定性完整性评估（稳定性适用于所有 `ai-*`，语言仅针对 `ai-zh`），同语言语义偏差为接受限制（由 `force_asr`/`exclude_ai_subtitles` 控制），不可用正文绝不返回
- transcript 的 absence 路径（ASR → description → `SUBTITLE_UNAVAILABLE`）与 video-info 的 uncached description 路径
- `setup --non-interactive` / `--asr-model <tiny|base|small>`：非交互、凭据安全、无模型时 credential-only
- 双语用户文档、CHANGELOG、codemap、本 QA checklist 同步

Out of scope:

- 真实模型安装/转录（本任务明确不安装模型，不执行 live ASR）
- 真实 ASR 安装/转录与 live corrupt-body 拒绝、ASR 回退（`BV1ybuQ62EfK` 当前无目标字幕暴露；未授权安装或运行真实模型）
- Issue #40 的其余历史修复（已由前序工作完成并保持）
- 提交 / push / PR / Issue / release

## Preconditions

- [x] Current branch and commit recorded: `codex/issue-40-ai-subtitle-integrity`，base `44ac1e7`
- [x] Expected package version recorded: 沿用当前 `package.json` 版本（未改包元数据）
- [x] Required credentials are available only through approved external sources, not pasted into this file.
- [x] Test Bilibili video IDs or URLs are safe to share（本检查不使用真实视频；无字幕/异常路径用 mock）
- [x] MCP client or local CLI environment is identified: 本地 CLI（`setup`/`doctor`）+ vitest mock 矩阵 + post-build child smoke（piped/closed stdin + synthetic env creds）

## Automated Baseline

Run when relevant:

```bash
npm run build
npm test
npm pack --dry-run
```

Results（2026-08-18 回填）：

- Build: `npm run build` passed（tsc 全量通过，7-file vitest 之外的编译期验证）
- Tests: 聚焦 7-file vitest 323/323 通过；全量 `npm test` 41 files / 906 tests 通过
- Pack: `npm pack --dry-run --json --ignore-scripts` 189 entries，无 forbidden 项；`dist/bilibili/subtitle-integrity.js` 在列
- Smoke: post-build child smoke 4/4 通过（credential-only 成功、无凭据 exit 1 + 字段名引导、model 无 non-interactive exit 1、无效 model exit 1），stdin 全部关闭/管道
- Live evidence (Codex authenticated read-only, 2026-08-18): public video `BV15kyBB5Eg8` returns subtitle languages `[ai-zh, ai-en, ai-ja, ai-es, ai-ar, ai-pt]` — confirming upstream now exposes non-`ai-zh` AI languages. Pre-fix candidate with `exclude_ai_subtitles: true` filtered only `ai-zh`, silently selected `ai-en`, and returned `data_source: "subtitle"` (root-cause confirmation of the ai-zh-only classification gap). No subtitle text or credential values recorded.
- Skipped checks and reason: live 分类/排除/双读已由 Codex post-build 鉴权只读运行验证（`BV15kyBB5Eg8`：默认 transcript → `ai_subtitle`/`ai-zh`/正文非空；`exclude_ai_subtitles=true` → `NoSubtitleError`；默认 video-info → `ai_subtitle` 含 `subtitle_text`；exclude=true → description 不含 `subtitle_text`）。live corrupt-body 拒绝与真实 ASR 回退仍未验证（`BV1ybuQ62EfK` 当前无目标字幕；明确不安装模型）；以 mock 矩阵 + post-build child smoke 替代。`runAsr` 恰好一次仅在 vitest 层验证（child smoke 不触达真实安装器）。

## Package And Install Path

- [ ] `package.json` version matches the intended release or test version.（未修改包元数据；`npm pack --dry-run` 确认 contents 无回归）
- [x] `npm pack --dry-run` includes expected files and excludes tests, local config, `.env`, `.claude`, `.codex`, and docs not meant for npm.
- [ ] `npm view @xzxzzx/bilibili-mcp version dist-tags --json` matches expected registry state when checking a published release.（未发布，跳过）
- [ ] `npx -y @xzxzzx/bilibili-mcp@latest --help` or equivalent package smoke check works when relevant.（未发布，跳过）
- [ ] Local `bin`, `main`, `module`, and `types` still point to built `dist` output.

Notes:

- 本次不改 `package.json` / lockfile / 包入口。

## MCP Stdio And Tool Discovery

- [x] Starting the MCP server does not print non-JSON logs to stdout before JSON-RPC traffic.（server 相关测试全绿）
- [x] `tools/list` returns the expected tool names.
- [ ] Tool descriptions do not expose credentials or misleading setup instructions.（人工检查：无新增 MCP 工具与 schema；CLI 错误信息不含凭据值）
- [x] Tool schemas match the intended public interface.（本任务不新增/修改 MCP 工具 schema；server-tools 等 3 个 server 测试文件在矩阵中）

Expected tools: 无新增（`get_video_transcript` / `get_video_info` 行为变化在 mock 层验证）

Notes:

- 完整性阈值不通过 MCP 暴露、不可配置（PRD 冻结）。

## Credential States

Do not paste full Cookie values into this checklist.

- [x] No credentials: `setup --non-interactive` 报错且引导含字段名（`BILIBILI_SESSDATA` 等）与替代路径，不含值。
- [x] Invalid or expired credentials: 非交互路径只做可加载性检查（env/global config 存在即可加载），不校验格式（与现有 `getCredentials()` 契约一致）；live 校验不在本任务范围。
- [x] Valid credentials: 交互路径不变；`doctor --json` 依旧不含值。
- [x] Credential setup flow points users to `npx -y @xzxzzx/bilibili-mcp config` and `npx -y @xzxzzx/bilibili-mcp check` when relevant.

Notes:

- 非交互路径绝不 prompt、绝不从 stdin/argv 读取凭据值（smoke 以 piped/closed stdin 验证）；错误输出经 `redactSecrets`。

## Tool Workflows

Use safe test videos and avoid recording private user data.

- [ ] `get_video_info` returns expected video info and subtitle/description behavior.（mock 层验证：unusable ai-* → description 且不缓存；`exclude_ai_subtitles` 过滤 ai-zh+ai-en 全集 → description；真实调用未验证）
- [ ] `get_video_transcript` handles available subtitles.（mock 层验证：稳定 ai-*（含 ai-en 回归）双读后返回 `ai_subtitle`；人工字幕单读；真实调用未验证）
- [ ] `get_video_transcript` handles unavailable subtitles with clear fallback guidance.（mock 层验证：unusable → ASR（授权时）/description/`SUBTITLE_UNAVAILABLE`；第二读异常传播）
- [ ] Validation errors are structured and useful for invalid BV IDs, URLs, language codes, or comment options.（回归：server-handler-sanitization / server-error-next-steps 在矩阵中）

Notes:

- Live 验证（Codex post-build 鉴权只读，`BV15kyBB5Eg8`，无字幕文本/凭据值记录）：默认 `get_video_transcript` → `data_source: "ai_subtitle"`、language `ai-zh`、正文非空；`exclude_ai_subtitles=true` → `NoSubtitleError`；默认 `get_video_info` → `ai_subtitle` 含 `subtitle_text`；exclude=true → description 不含 `subtitle_text`。live 分类、排除与双读成功已验证。live corrupt-body 拒绝与 ASR 回退未验证——`BV1ybuQ62EfK` 当前无目标字幕暴露，且未授权真实 ASR/模型运行；以 mock 矩阵 + post-build child smoke 替代。

## Client Compatibility

Mark untested clients explicitly.

| Client | Version | Install method | Result | Notes |
|--------|---------|----------------|--------|-------|
| Claude Desktop |  |  | not tested | 本任务不接入客户端 |
| Cursor |  |  | not tested | 本任务不接入客户端 |
| Codex |  |  | not tested | 由 Paseo 编排，不接入 MCP 客户端 |
| Other |  |  | not tested |  |

## Documentation Checks

- [x] README install command matches actual package behavior.
- [x] Credential setup docs do not suggest putting Cookie values in MCP client config.
- [x] README and README_EN agree on the supported setup path（含 `--non-interactive` 新增说明与 unconditional integrity 描述）。
- [x] Changelog or release notes mention user-visible changes（CHANGELOG.md/EN.md Unreleased：integrity bullet 重写 + setup flags bullet）。
- [x] Known limitations are documented when behavior is intentionally partial.（inconclusive pass / 阈值冻结 / 无授权回退 → `SUBTITLE_UNAVAILABLE` 均已写入 tool-reference）

Notes:

- tool-reference.md/.en.md、client-setup.md/.en.md、README.md/EN.md、CHANGELOG.md/EN.md 已同步；`docs/agent-memory/codemap.md` 已更新。

## Security And Privacy Checks

- [x] No full Cookie values, npm tokens, GitHub tokens, `.env` content, or private credentials appear in logs, reports, docs, tests, or package output.（secret-scanning 分类/计数报告；文档仅含 field-name 引用）
- [x] Error messages and retry logs redact credential-like values（`redactSecrets`）。
- [x] External inputs are validated before Bilibili API calls.（回归，无改动）
- [x] Network responses that may be large or redirected are bounded or rejected according to current policy.（回归，无改动；完整性处理不记录/返回比较文本、token、hash、签名地址）

Notes:

- 完整性评估为纯函数模块，不产生网络/IO；不可用正文绝不进入结果与日志。

## Result

- Overall result: `pass with caveats`（以 mock 矩阵 + smoke 验证；live Bilibili 与真实 ASR 未验证）
- Blocking issues: 无
- Non-blocking caveats: live 分类/排除/双读已由 `BV15kyBB5Eg8` 验证；live corrupt-body 拒绝与真实 ASR 回退仍需人工 live check（`BV1ybuQ62EfK` 当前无目标字幕；未授权模型运行）；完整性阈值为冻结启发式，存在理论误判（inconclusive 时通过）
- Follow-up tickets: 无（超出范围的问题另行提出）
- Codemap update status: 已更新（subtitle.ts 条目修订 + 新增 subtitle-integrity.ts）
- Research note link, if external facts affected QA: 不适用（无外部研究依赖）
