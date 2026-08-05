#!/usr/bin/env node

// CLI entry point
import { Command } from "commander";
import os from "os";
import { fileURLToPath } from "url";
import { server } from "./server.js";
import { credentialManager } from "./utils/credentials.js";
import { Writable } from "stream";
import { redactSecrets } from "./utils/logger.js";
import { buildPackageUpdateInfo } from "./utils/update-check.js";
import { BoundedStdioServerTransport } from "./server/bounded-stdio-transport.js";

import {
  readAsrState,
  deriveAsrPaths,
  type AsrStateKind,
  ASR_MODEL_SPECS,
  resolveModelSpec,
  type AsrModelKey,
  type AsrModelSpec,
} from "./asr/state.js";
import { runAsrInstallation } from "./asr/installer.js";

// Version info
import fs from "fs";
const packageJson = JSON.parse(
  fs.readFileSync(new URL("../package.json", import.meta.url), "utf8"),
);

async function askHidden(question: string): Promise<string> {
  const readline = await import("readline");
  const mutedOutput = new Writable({
    write(chunk, encoding, callback) {
      if (!(mutedOutput as Writable & { muted?: boolean }).muted) {
        process.stdout.write(chunk, encoding as BufferEncoding);
      }
      callback();
    },
  }) as Writable & { muted?: boolean };

  const rl = readline.createInterface({
    input: process.stdin,
    output: mutedOutput,
    terminal: true,
  });

  return new Promise<string>((resolve) => {
    mutedOutput.muted = false;
    rl.question(question, (answer) => {
      mutedOutput.muted = false;
      process.stdout.write("\n");
      rl.close();
      resolve(answer.trim());
    });
    mutedOutput.muted = true;
  });
}

export function parseModelChoice(input: string): AsrModelKey | null {
  const trimmed = input.trim().toLowerCase();
  if (trimmed === "") return "small"; // Enter defaults to recommended

  // Numeric choice
  if (trimmed === "1" || trimmed === "tiny") return "tiny";
  if (trimmed === "2" || trimmed === "base") return "base";
  if (trimmed === "3" || trimmed === "small") return "small";

  return null; // invalid, re-prompt
}

// Start MCP server
async function startServer() {
  const transport = new BoundedStdioServerTransport();
  await server.connect(transport);
  console.error("Bilibili MCP server running on stdio");
}

// Configure credentials
async function configureCredentials() {
  console.log("请输入您的 Bilibili 凭证信息（可从浏览器开发者工具中获取）：");
  console.log("输入内容不会在终端回显。");

  const sessdata = await askHidden("SESSDATA: ");
  const bili_jct = await askHidden("bili_jct: ");
  const dedeuserid = await askHidden("DedeUserID: ");

  try {
    const credentials = {
      sessdata,
      bili_jct,
      dedeuserid,
      expiresAt: Date.now() + 30 * 24 * 60 * 60 * 1000,
    };

    credentialManager.setCredentials(credentials);
    credentialManager.saveToFile(credentials);

    const { GLOBAL_CONFIG_FILE } = await import("./utils/credentials.js");

    console.log("");
    console.log("✅ 凭证配置成功，已永久保存至：");
    console.log(`   ${GLOBAL_CONFIG_FILE}`);
    console.log("");
    console.log("下次启动 MCP 服务器时将自动加载此凭证，无需重新配置。");
    console.log("⚠️  如需更新凭证，请重新运行 bilibili-mcp config");
  } catch (error) {
    console.error("配置失败：", redactSecrets(error));
    process.exit(1);
  }
}

// Check config status
function checkConfig() {
  const creds = credentialManager.getCredentials();
  if (creds) {
    console.log("配置状态：已配置");
    console.log("");
    console.log("凭证已加载。不会显示任何 Cookie 字段值。");
    if (credentialManager.isExpiringSoon()) {
      console.warn("警告：凭证将在7天内过期");
    }
  } else {
    console.log("配置状态：未配置");
    console.log("");
    console.log("请使用以下方法之一配置凭证：");
    console.log("1. bilibili-mcp setup");
    console.log("2. 设置环境变量");
    console.log("3. 创建 .env 文件");
  }
}

async function checkUpdate() {
  const result = await buildPackageUpdateInfo();

  console.log(`Package: ${result.package_name}`);
  console.log(`Current version: ${result.current_version}`);
  console.log(
    `Latest version: ${result.latest_version ?? "unknown"}`,
  );
  console.log(
    `Update available: ${
      result.update_available === null
        ? "unknown"
        : result.update_available
          ? "yes"
          : "no"
    }`,
  );
  console.log("");
  console.log("Recommended MCP config:");
  console.log(`  command: ${result.recommended_mcp_config.command}`);
  console.log(
    `  args: ${JSON.stringify(result.recommended_mcp_config.args)}`,
  );
  console.log("");
  console.log("Manual update commands:");
  console.log(`  ${result.update_commands.global_update}`);
  console.log(`  ${result.update_commands.npx_config}`);
  console.log(`  ${result.update_commands.npx_check}`);
}

export interface DoctorStatus {
  package_name: string;
  version: string;
  runtime: {
    node: string;
    platform: string;
    arch: string;
  };
  credentials: {
    configured: boolean;
    source: "env" | "global_config" | "none";
    loadable: boolean;
  };
  asr: {
    status: AsrStateKind;
    model: AsrModelKey | null;
  };
  status: "locally_ready" | "needs_credentials";
  next_steps: string[];
}

export function buildDoctorStatus(
  readAsrStateFn: typeof readAsrState = readAsrState,
  asrPaths = deriveAsrPaths(),
): DoctorStatus {
  const source = credentialManager.getCredentialSource();
  const configured = source !== "none";
  const creds = configured ? credentialManager.getCredentials() : null;
  const loadable = creds !== null;
  const isReady = configured && loadable;

  const asrState = readAsrStateFn(asrPaths.stateFile);
  const asrModelKey: AsrModelKey | null = asrState.modelKey ?? null;

  return {
    package_name: "@xzxzzx/bilibili-mcp",
    version: packageJson.version,
    runtime: {
      node: process.version,
      platform: os.platform(),
      arch: os.arch(),
    },
    credentials: {
      configured,
      source,
      loadable,
    },
    asr: {
      status: asrState.kind,
      model: asrModelKey,
    },
    status: isReady ? "locally_ready" : "needs_credentials",
    next_steps: isReady
      ? []
      : [
          "Run: npx -y @xzxzzx/bilibili-mcp@latest setup",
          "Then run: npx -y @xzxzzx/bilibili-mcp@latest check",
        ],
  };
}

export function doctorCommand(
  json: boolean,
  statusBuilder: () => DoctorStatus = buildDoctorStatus,
) {
  try {
    const status = statusBuilder();
    if (json) {
      console.log(JSON.stringify(status));
    } else {
      console.log(`Package: ${status.package_name}`);
      console.log(`Version: ${status.version}`);
      console.log(
        `Runtime: Node ${status.runtime.node} / ${status.runtime.platform} / ${status.runtime.arch}`,
      );
      console.log(`Credentials configured: ${status.credentials.configured}`);
      console.log(`Credential source: ${status.credentials.source}`);
      console.log(`Credentials loadable: ${status.credentials.loadable}`);
      console.log(`ASR: ${status.asr.status}`);
      if (status.asr.model) {
        console.log(`ASR model: ${status.asr.model}`);
      }
      console.log(`Status: ${status.status}`);
      if (status.next_steps.length > 0) {
        console.log("Next steps:");
        for (const step of status.next_steps) {
          console.log(`  ${step}`);
        }
      }
    }

    if (status.status === "needs_credentials") {
      process.exitCode = 1;
    }
  } catch (error) {
    console.error("Doctor internal error:", redactSecrets(error));
    process.exitCode = 2;
  }
}

export async function setupCredentials(
  configure: () => Promise<void> = configureCredentials,
  runAsr: (modelKey: AsrModelKey) => Promise<{ success: boolean; error?: string }> = async () => ({ success: false, error: "installer not injected" }),
  askHiddenFn: (question: string) => Promise<string> = askHidden,
) {
  if (!process.stdin.isTTY) {
    console.error(
      "Error: setup requires an interactive terminal (TTY).",
    );
    console.error(
      "For non-interactive local status, use: npx -y @xzxzzx/bilibili-mcp@latest doctor --json",
    );
    console.error(
      "To configure credentials interactively, run: npx -y @xzxzzx/bilibili-mcp@latest setup",
    );
    process.exit(1);
  }

  const creds = credentialManager.getCredentials();
  if (creds !== null) {
    const source = credentialManager.getCredentialSource();
    console.log("Credentials are already configured.");
    console.log(`Source: ${source}`);
    console.log(
      "To reconfigure, run: bilibili-mcp config",
    );
    // Fall through to ASR question even with existing credentials
  } else {
    await configure();
  }

  // Optional ASR installation prompt
  console.log("");
  console.log(
    "ASR 语音识别（可选）：安装本地 faster-whisper 模型，",
  );
  console.log(
    "用于后续在没有 CC/AI 字幕时提供本地语音识别。当前阶段仅安装模型，不执行转录。",
  );

  const answer = await askHiddenFn("是否现在安装？[y/N] ");
  if (answer.toLowerCase() !== "y" && answer.toLowerCase() !== "yes") {
    console.log("已跳过 ASR 安装。稍后可重新运行 setup 来安装。");
    return;
  }

  // Model selector
  console.log("");
  console.log("请选择模型（输入数字或名称，Enter 默认推荐 small）：");
  for (let i = 0; i < ASR_MODEL_SPECS.length; i++) {
    const spec = ASR_MODEL_SPECS[i];
    const marker = spec.key === "small" ? " [推荐]" : "";
    console.log(`  ${i + 1}. ${spec.key}（约 ${spec.approximateMB} MB）${marker}`);
  }

  let modelKey: AsrModelKey | null = null;
  while (modelKey === null) {
    const choice = await askHiddenFn("> ");
    modelKey = parseModelChoice(choice);
    if (modelKey === null) {
      console.log(`无效选择，请输入 1/2/3 或 tiny/base/small，或直接按 Enter 选择 small。`);
    }
  }

  // TS narrows after while (modelKey === null) exits
  const resolvedKey: AsrModelKey = modelKey;
  const spec = resolveModelSpec(resolvedKey);
  console.log(`已选择：${spec.key}（约 ${spec.approximateMB} MB）`);
  console.log("正在安装 ASR 模型，可能需要几分钟...");
  const result = await runAsr(modelKey);

  if (result.success) {
    console.log("✅ ASR 模型安装成功并通过 CPU INT8 验证。");
    console.log(`   管理路径：~/.bilibili-mcp/asr/`);
    console.log(
      "   运行 bilibili-mcp doctor --json 可查看 ASR 状态。",
    );
  } else {
    console.error(`❌ ASR 安装失败：${redactSecrets(result.error) ?? "未知错误"}`);
    console.log("   已保留部分下载文件，重新运行 setup 可从断点续传。");
    console.log("   当前 MCP 服务不受影响，字幕回退为 SUBTITLE_UNAVAILABLE。");
    process.exitCode = 1;
  }
}

export function createCli() {
  const cli = new Command()
    .name("bilibili-mcp")
    .version(packageJson.version, "-V, --version")
    .description("Bilibili MCP 工具 - 视频和评论总结")
    .option("-v", "输出版本号");

  cli.on("option:v", () => {
    console.log(packageJson.version);
    process.exit(0);
  });

  cli.action(startServer);

  cli
    .command("config")
    .description("配置 Bilibili 凭证信息")
    .action(configureCredentials);

  cli
    .command("check")
    .description("检查配置状态")
    .action(checkConfig);

  cli
    .command("check-update")
    .description("检查 npm 最新版本")
    .action(() => checkUpdate());

  cli
    .command("setup")
    .description("交互式配置 Bilibili 凭证和可选 ASR（需要终端）")
    .action(async () =>
      setupCredentials(configureCredentials, async (modelKey: AsrModelKey) =>
        runAsrInstallation({ modelKey, onStage: (s) => console.log(`  ${s}`) }),
      ),
    );

  cli
    .command("version")
    .description("输出版本号")
    .action(() => console.log(packageJson.version));

  cli
    .command("doctor")
    .description("本地状态检查（Agent 可用 --json）")
    .option("--json", "输出 JSON 格式")
    .action((options: { json?: boolean }) => doctorCommand(Boolean(options.json)));

  return cli;
}

// Main entry point
async function main() {
  const cli = createCli();
  await cli.parseAsync(process.argv);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main().catch((error) => {
    console.error("Fatal error in main():", redactSecrets(error));
    process.exit(1);
  });
}
