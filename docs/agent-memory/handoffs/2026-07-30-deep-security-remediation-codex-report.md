# Codex 报告：Deep Security 38 项修复

## 摘要

Codex 已直接完成原扫描
`6949ea8e-a129-43d6-9104-6edf7413a1ff` 的 4 项 Medium 与 34 项 Low
修复；未使用 Paseo 或 Claude Code，产品源码由 Codex 直接修改。最终证据
补强使用了三个受限 Codex 测试/复核子任务。十个 MCP 工具的名称、固定
顺序和产品边界不变。全部原始 `extensions.reportId` finding slug 已与 38 行 QA
矩阵一一自动核对，缺失 0、额外 0；canonical ID 为独立的 `csf_*` 值。

本地实现、构建、721 项全量测试、Hook 测试、stdio smoke、npm 打包和
不输出值的机密检查均已通过。第一次官方 CLI 复扫因 0.1.3 的 completion
顺序问题在收集 canonical artifacts 前失败且输出目录为空；将使用官方
0.1.4 对精确 `0a1b` 工作树发起全新 `deep` 复扫。复扫封存前，本报告
不声称最终关闭。

## 执行边界

- 执行者：Codex（用户明确要求不用 Paseo）。
- 工作树：
  `C:\Users\ZX\.codex\worktrees\0a1b\bilibili-mcp`
- 基线 HEAD：`ab4dd02854f0483fc7668c713523b4be77de6cc7`
- 保留所有继承的未提交/未跟踪 ASR、CLI、README 和项目记忆成果。
- 未使用真实 Cookie、签名播放 URL、ASR 模型或 Bilibili 联网验收。
- 未 stage、commit、push、PR、tag、version bump、publish 或 release。

## 主要实现

### MCP 与 stdio

- 固定缓冲的 1 MiB 入站 / 4 MiB 出站 JSON-RPC 行帧。
- SDK 取消信号通过操作上下文传入 HTTP 与 ASR。
- 成功 payload 2 MiB、完整 MCP envelope 4 MiB；文本 JSON 与
  `structuredContent` 保持一致。
- 未知工具名和内部异常使用固定、短小、无秘密的公开错误。

### Bilibili 网络与内容

- 活跃/排队请求、等待时间、总 deadline、重试、JSON body 和 bootstrap
  waiter 全部有界。
- 普通、WBI、fingerprint 和 update 请求拒绝重定向；WBI/fingerprint/
  update 使用单飞刷新。
- 播放媒体在最终 HTTPS sink 执行 provider host、全部 DNS 地址、
  public-range、连接 pin、TLS hostname 和 header stripping 检查。
- 字幕、视频信息、搜索、章节、评论、收藏夹、playback、字段和最终
  序列化结果都有本地形状/数量/UTF-8 字节上限。
- malformed subtitle 不再变成 ASR/description 成功回退。

### ASR 与安装器

- ASR 在任何状态、网络、临时文件或子进程前要求可信 Part 时长。
- 三个候选共用一个 120 秒 deadline 和一个 128 MiB 下载预算。
- Windows Job / POSIX `RLIMIT`、线程限制、进程组、tree kill、严格
  NDJSON、stdout/stderr/段数/字符上限和完整 cleanup。
- 安装器只传 allowlist 环境，限制子进程时间与输出，检查磁盘预算、
  文件数、字节、symlink，使用 staging、验证、原子激活和失败清理。

### Hook 与发布链

- Hook stdin/JSON/JSONL/行/字节/深度/节点均有界，使用锁、原子替换并
  拒绝 symlink。
- 失败工具只保存固定 metadata；不保存 command/stdout/stderr/error/
  env/path 文本，也不把候选正文预览到 SessionStart。
- issue、handoff、report、QA、research 和扫描文本被明确视为不可信数据。
- `actions/checkout` 与 `actions/setup-node` 均固定到官方验证的完整 commit
  SHA，并由测试禁止第三方 mutable tag。

## Finding 闭环

完整逐项表见：

- `docs/qa/2026-07-30-deep-security-remediation.md`

自动核对结果：

- 原始 finding：38
- QA 闭环行：38
- Medium / Low：4 / 34
- 缺失：0
- 额外：0

## 验证结果

- `npm run build`：通过。
- 定向安全回归：22 files / 407 tests，通过。
- `npm test`：38 files / 721 tests，通过。
- `.codex/scripts/test_hook_safety.py`：6/6，通过。
- `.codex/scripts/test_stop_summary.py`：8/8，通过。
- 改动 Hook Python byte-compile：通过。
- built CLI help 与真实 JSON-RPC stdio initialize/list/call/stdout-clean：
  通过。
- `npm pack --dry-run --json --ignore-scripts`：180 files，
  190,267 packed bytes，776,730 unpacked bytes；禁止结构路径 0。
- 全树/包内容高置信 private key、GitHub token、npm token、AWS key：
  0。
- Bilibili 凭据形状命中仅以文件/长度/类别复核，未输出值；未分类可疑
  命中 0。
- `git diff --check`：无空白错误；仅 Windows 既有 LF→CRLF 提示。

## 依赖审计与残余风险

- `npm audit --omit=dev --json` 仍返回 2 个 moderate 节点：
  `@modelcontextprotocol/sdk@1.27.1` 经
  `@hono/node-server@1.19.14` 对应 GHSA-frvp-7c67-39w9。
- 当前项目只导入 SDK server/types/shared stdio；Hono 只被 SDK
  `server/streamableHttp.js` 和示例导入。本项目没有 HTTP、SSE、
  `serveStatic` 或 listener 路径。
- 因而这是“已安装但当前不可达”的残余风险，不是 clean audit，也不是
  当前 stdio 产品的已确认可利用漏洞。SDK/Hono 更新留给独立兼容任务。
- 本机无 ready ASR 模型，真实音频/CDN/native decoder/转录 E2E 未验证。
- Bilibili 标题、简介、字幕、评论等仍是语义上不可信的数据；实现已做
  长度、结构、控制字符和序列化约束，但不能替 MCP 客户端判断内容真假。

## Codex Security 复扫

- 官方 CLI scan ID：
  `c93dd212-6e9c-4ed0-a0c6-36bc93f9769b`
- target：精确 `0a1b` 工作树
- target snapshot：
  `codex-security-snapshot/v1:sha256:afd04dcbdc0578c0ec4f364bf501f32fdf8a10f6112f53e5c422329287739624`
- mode/scope：`deep` / `.`
- bundled plugin：0.1.14
- 状态：失败，未生成 artifact。CLI 0.1.3 在收集 canonical 文件前调用
  completion，随后报告 `scan-manifest.json` 不是扫描目录中的普通文件。
- 后续：使用官方 CLI 0.1.4 的 prepare → collect/validate → complete
  顺序发起全新扫描；完成后补充 finding 数、canonical artifacts 和
  `report.md` 路径。

## Harness Artifacts

- Codex 子任务：`add_mcp_security_tests` 补 MCP/stdio 直接边界；
  `add_asr_security_tests` 补 ASR runtime/installer 进程边界；
  `review_security_docs` 先只读复核，再补 Bilibili/WBI/update 直接回归。
  三者均未修改产品源码、未执行 Git/发布操作。
- Task ticket：已更新。
- Research note：新增
  `docs/research/2026-07-30-security-remediation-dependency-and-action-pins.md`。
- QA checklist：新增 38 行闭环矩阵。
- Codemap：已更新新 security、stdio、ASR、Hook 和测试入口。
- Harness security：已更新并通过 14 项 Hook 回归。
- Harness eval：已记录直接 Codex、Desktop UI gate、官方 CLI 和包/
  依赖分类经验。
- Pending learning proposals：保持 review-gated，未提升。

## 未完成项

- [ ] 使用官方 Codex Security CLI 0.1.4 完成全新扫描。
- [ ] 核验 canonical `scan-manifest.json`、`findings.json`、
  `coverage.json` 与生成报告。
- [ ] 若复扫发现新/残余可报告路径，继续直接修复并重验。
- [ ] 只有复扫和报告完成后才把当前 Goal 标为 complete。
