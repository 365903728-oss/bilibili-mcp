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
  ASR_FAILURE_CATEGORIES,
  readAsrState,
  deriveAsrPaths,
  resolveDevicePreference,
  resolveExecutionProfile,
  type AsrStateKind,
  type AsrDeviceReadiness,
  type AsrDevicePreference,
  type AsrExecutionProfile,
  type AsrFailureCategory,
  type AsrMigrationStatus,
  ASR_MODEL_SPECS,
  resolveModelSpec,
  type AsrModelKey,
  type AsrModelSpec,
} from "./asr/state.js";
import { runAsrInstallation, type InstallResult } from "./asr/installer.js";

const ASR_MODEL_TIER_DESCRIPTIONS: Record<AsrModelKey, string> = {
  tiny: "速度优先：适合快速提取和长视频初筛，准确率相对较低",
  base: "均衡：兼顾速度、质量和资源占用",
  small: "质量优先：耗时和内存占用更高",
};

type AsrSetupResult = Pick<
  InstallResult,
  | "success"
  | "error"
  | "executionProfile"
  | "failureCategory"
  | "failureDevice"
  | "gpuFailureCategory"
>;

const ASR_GPU_FAILURE_EXPLANATIONS: Record<AsrFailureCategory, string> = {
  no_nvidia_gpu: "当前环境没有检测到可用的 NVIDIA GPU",
  cuda_runtime_missing: "CUDA、cuBLAS 或 cuDNN 运行组件无法由当前 ASR 进程加载",
  runtime_version_mismatch: "NVIDIA 驱动、CUDA 组件或受控 ASR 运行时版本不兼容",
  model_probe_failed: "GPU 模型加载或最小推理没有成功完成",
};

const ASR_GPU_FAILURE_ACTIONS: Record<AsrFailureCategory, string> = {
  no_nvidia_gpu: "确认机器确有 NVIDIA GPU 且 nvidia-smi 可用；否则重新运行 setup 选择 cpu",
  cuda_runtime_missing: "按官方 GPU 说明安装与受控运行时兼容的 CUDA 12、cuBLAS 和 cuDNN 9，让启动 MCP 的同一环境可以加载它们，然后重启 MCP 客户端并重跑 setup：https://github.com/SYSTRAN/faster-whisper#gpu",
  runtime_version_mismatch: "升级 NVIDIA 驱动和兼容的 CUDA 12 组件，重启 MCP 客户端后重跑 setup；setup 会重新固定 Python 运行时版本",
  model_probe_failed: "先重跑 setup；若仍失败，可选择 cpu 继续使用，并携带 doctor --json 的脱敏类别报告问题",
};

function explainAsrFailure(
  category: AsrFailureCategory,
  device: "cpu" | "cuda",
): string {
  if (device === "cuda") return ASR_GPU_FAILURE_EXPLANATIONS[category];
  if (category === "runtime_version_mismatch") {
    return "受控 ASR Python 运行时版本不匹配";
  }
  return "CPU 模型加载或最小推理没有成功完成";
}

function actionForAsrFailure(
  category: AsrFailureCategory,
  device: "cpu" | "cuda",
): string {
  if (device === "cuda") return ASR_GPU_FAILURE_ACTIONS[category];
  return "重新运行 setup；若仍失败，请携带 doctor --json 的脱敏类别报告问题";
}

function reportAsrSetupResult(
  result: AsrSetupResult,
  requestedDevice: AsrDevicePreference,
): boolean {
  if (result.success) {
    const profile = result.executionProfile === undefined
      ? "设备就绪"
      : result.executionProfile.device === "cuda"
        ? "CUDA Float16"
        : "CPU INT8";
    console.log(`✅ ASR 模型安装成功并通过 ${profile} 验证。`);
    if (result.failureCategory !== undefined) {
      console.log(
        `   GPU 未启用：${explainAsrFailure(result.failureCategory, "cuda")}（${result.failureCategory}）。`,
      );
      console.log("   已验证 CPU INT8，可以继续使用 ASR；也可以修复 GPU 环境后重新运行 setup。");
      console.log(`   若要启用 GPU：${actionForAsrFailure(result.failureCategory, "cuda")}。`);
      console.log("   bilibili-mcp 不会自动安装或修改 NVIDIA 驱动、CUDA、cuBLAS、cuDNN、PATH 或 LD_LIBRARY_PATH。");
    }
    console.log("   管理路径：~/.bilibili-mcp/asr/");
    console.log("   运行 bilibili-mcp doctor --json 可查看 ASR 状态。");
    return true;
  }

  console.error(`❌ ASR 安装失败：${redactSecrets(result.error) ?? "未知错误"}`);
  if (result.failureCategory !== undefined) {
    if (result.gpuFailureCategory !== undefined) {
      console.log(
        `   GPU 验证失败：${explainAsrFailure(result.gpuFailureCategory, "cuda")}（${result.gpuFailureCategory}）。`,
      );
      console.log(
        `   CPU 回退验证也失败：${explainAsrFailure(result.failureCategory, "cpu")}（${result.failureCategory}）。`,
      );
      console.log(`   GPU 处理方法：${actionForAsrFailure(result.gpuFailureCategory, "cuda")}。`);
      console.log(`   CPU 处理方法：${actionForAsrFailure(result.failureCategory, "cpu")}。`);
    } else {
      const failureDevice = result.failureDevice ?? (requestedDevice === "cpu" ? "cpu" : "cuda");
      const label = failureDevice === "cuda" ? "GPU" : "CPU";
      console.log(
        `   ${label} 验证失败：${explainAsrFailure(result.failureCategory, failureDevice)}（${result.failureCategory}）。`,
      );
      console.log(`   处理方法：${actionForAsrFailure(result.failureCategory, failureDevice)}。`);
    }
    console.log("   bilibili-mcp 不会自动安装或修改 NVIDIA 驱动、CUDA、cuBLAS、cuDNN、PATH 或 LD_LIBRARY_PATH。");
    if (requestedDevice === "cuda") {
      console.log("   你选择了 cuda，因此没有回退到 CPU；已有已验证配置（如有）保持不变。");
      console.log("   你可以修复 GPU 环境后重新运行 setup 并重新选择 cuda，或重新运行 setup 选择 cpu。");
    }
  } else {
    console.log("   已保留部分下载文件，重新运行 setup 可从断点续传。");
    console.log("   当前 MCP 服务不受影响，字幕回退为 SUBTITLE_UNAVAILABLE。");
  }
  return false;
}

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

export function parseDeviceChoice(input: string): AsrDevicePreference | null {
  const normalized = input.trim().toLowerCase();
  if (normalized === "") return "auto";
  return resolveDevicePreference(normalized) ?? null;
}

// Start MCP server
async function startServer() {
  const transport = new BoundedStdioServerTransport();
  await server.connect(transport);
  console.error("Bilibili MCP server running on stdio");
}

// Configure credentials
export async function configureCredentials(
  askHiddenFn: (question: string) => Promise<string> = askHidden,
): Promise<boolean> {
  console.log("请输入您的 Bilibili 凭证信息（可从浏览器开发者工具中获取）：");
  console.log("输入内容不会在终端回显。");

  const sessdata = (await askHiddenFn("SESSDATA: ")).trim();
  const bili_jct = (await askHiddenFn("bili_jct: ")).trim();
  const dedeuserid = (await askHiddenFn("DedeUserID: ")).trim();

  if (!sessdata || !bili_jct || !dedeuserid) {
    console.error("配置未保存：SESSDATA、bili_jct 和 DedeUserID 均不能为空；已有凭证保持不变。");
    process.exitCode = 1;
    return false;
  }

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
    return true;
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
    device: AsrExecutionProfile["device"] | null;
    compute_type: AsrExecutionProfile["computeType"] | null;
    device_readiness: AsrDeviceReadiness;
    migration_status: AsrMigrationStatus | null;
    failure_category: AsrFailureCategory | null;
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
  const executionProfile = asrState.kind === "ready" && asrState.executionProfile !== undefined
    ? resolveExecutionProfile(
        asrState.executionProfile.device,
        asrState.executionProfile.computeType,
      )
    : undefined;
  const profileReady = executionProfile !== undefined &&
    asrState.deviceReadiness === "ready" &&
    asrState.migrationStatus === "completed";
  const migrationPending = asrState.kind === "ready" &&
    executionProfile === undefined &&
    (asrState.version === 1 ||
      (asrState.deviceReadiness === "migration_pending" &&
        asrState.migrationStatus === "pending"));
  const failureCategory = profileReady &&
    typeof asrState.failureCategory === "string" &&
    (ASR_FAILURE_CATEGORIES as readonly string[]).includes(asrState.failureCategory)
    ? asrState.failureCategory
    : null;

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
      device: profileReady ? executionProfile.device : null,
      compute_type: profileReady ? executionProfile.computeType : null,
      device_readiness: profileReady
        ? "ready"
        : migrationPending
          ? "migration_pending"
          : "not_ready",
      migration_status: profileReady
        ? "completed"
        : migrationPending
          ? "pending"
          : null,
      failure_category: failureCategory,
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
      console.log(`ASR device readiness: ${status.asr.device_readiness}`);
      if (status.asr.device && status.asr.compute_type) {
        console.log(`ASR execution profile: ${status.asr.device}/${status.asr.compute_type}`);
      }
      if (status.asr.migration_status) {
        console.log(`ASR migration status: ${status.asr.migration_status}`);
      }
      if (status.asr.failure_category) {
        console.log(`ASR failure category: ${status.asr.failure_category}`);
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

export interface SetupCredentialsOptions {
  /** 非交互模式：绝不提示，也绝不从 stdin/argv 读取凭据值 */
  nonInteractive?: boolean;
  /** 允许列表内的 ASR 模型（仅非交互模式可用） */
  asrModel?: AsrModelKey;
  /** 受控的 ASR 设备偏好（仅与非交互模型选择同用） */
  asrDevice?: AsrDevicePreference;
}

export async function setupCredentials(
  configure: () => Promise<boolean | void> = configureCredentials,
  runAsr: (modelKey: AsrModelKey, devicePreference: AsrDevicePreference) => Promise<AsrSetupResult> = async () => ({ success: false, error: "installer not injected" }),
  askHiddenFn: (question: string) => Promise<string> = askHidden,
  options: SetupCredentialsOptions = {},
) {
  // --asr-model 未与 --non-interactive 同时使用：验证错误，绝不静默改变交互流程
  if (options.asrModel !== undefined && !options.nonInteractive) {
    console.error("Error: --asr-model requires --non-interactive.");
    console.error(
      "Run: bilibili-mcp setup --non-interactive --asr-model <tiny|base|small>",
    );
    process.exitCode = 1;
    return;
  }
  if (options.asrDevice !== undefined && !options.nonInteractive) {
    console.error("Error: --asr-device requires --non-interactive.");
    process.exitCode = 1;
    return;
  }
  if (options.asrDevice !== undefined && options.asrModel === undefined) {
    console.error("Error: --asr-device requires --asr-model.");
    process.exitCode = 1;
    return;
  }

  // 非交互模式：只接受 env/global config 来源的可加载凭据（内存中已有值不算，
  // 进程内不可复现），绝不提示、也绝不从 stdin/argv 读取凭据值
  if (options.nonInteractive) {
    const source = credentialManager.getCredentialSource();
    const creds = credentialManager.getCredentials();
    if (source === "none" || creds === null) {
      console.error(
        "Error: setup --non-interactive requires loadable credentials from environment variables or the global config file.",
      );
      console.error(
        "Set BILIBILI_SESSDATA, BILIBILI_BILI_JCT, and BILIBILI_DEDEUSERID, or run 'bilibili-mcp setup' once interactively.",
      );
      process.exitCode = 1;
      return;
    }
    console.log(
      "Credentials are loadable; non-interactive setup proceeds without prompting.",
    );
    if (options.asrModel === undefined) {
      console.log("No --asr-model given; setup complete without ASR installation.");
      return;
    }
    const devicePreference = options.asrDevice ?? "auto";
    const result = await runAsr(options.asrModel, devicePreference);
    if (!reportAsrSetupResult(result, devicePreference)) {
      process.exitCode = 1;
    }
    return;
  }

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
    const configured = await configure();
    if (configured === false) {
      process.exitCode = 1;
      return;
    }
  }

  // Optional ASR installation prompt
  console.log("");
  console.log(
    "ASR 语音识别（可选）：安装本地 faster-whisper 模型，",
  );
  console.log(
    "用于后续在没有 CC/AI 字幕时提供本地语音识别。setup 会用程序生成的短 WAV 验证设备，不访问 Bilibili。",
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
    console.log(
      `  ${i + 1}. ${spec.key}（约 ${spec.approximateMB} MB）${marker} — ${ASR_MODEL_TIER_DESCRIPTIONS[spec.key]}`,
    );
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
  console.log("");
  console.log("请选择执行设备（Enter 默认 auto）：");
  console.log("  auto：优先验证 NVIDIA GPU；失败时解释原因并验证 CPU 回退");
  console.log("  cpu：仅验证 CPU INT8，不探测 GPU");
  console.log("  cuda：必须通过 CUDA Float16 验证；失败时不回退 CPU");
  let devicePreference: AsrDevicePreference | null = null;
  while (devicePreference === null) {
    devicePreference = parseDeviceChoice(await askHiddenFn("> "));
    if (devicePreference === null) {
      console.log("无效选择，请输入 auto、cpu 或 cuda，或直接按 Enter 选择 auto。");
    }
  }
  console.log("正在安装 ASR 模型，可能需要几分钟...");
  const result = await runAsr(modelKey, devicePreference);

  if (!reportAsrSetupResult(result, devicePreference)) {
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
    .action(async () => {
      await configureCredentials();
    });

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
    .description("配置 Bilibili 凭证和可选 ASR（交互式需要终端，--non-interactive 供自动化使用）")
    .option("--non-interactive", "非交互模式：使用已有的 env/global config 凭据，绝不提示")
    .option("--asr-model <tiny|base|small>", "非交互模式下的 ASR 模型（需与 --non-interactive 同用）")
    .option("--asr-device <auto|cpu|cuda>", "非交互模式下的 ASR 设备偏好（默认 auto，需与 --asr-model 同用）")
    .action(async (cmdOptions: { nonInteractive?: boolean; asrModel?: string; asrDevice?: string }) => {
      const options: SetupCredentialsOptions = {
        nonInteractive: Boolean(cmdOptions.nonInteractive),
      };
      if (cmdOptions.asrModel !== undefined) {
        const key = cmdOptions.asrModel.trim().toLowerCase() as AsrModelKey;
        let resolvedKey: AsrModelKey | undefined;
        try {
          resolvedKey = resolveModelSpec(key).key;
        } catch {
          resolvedKey = undefined;
        }
        if (resolvedKey === undefined) {
          console.error("Error: --asr-model must be one of: tiny, base, small");
          process.exitCode = 1;
          return;
        }
        options.asrModel = resolvedKey;
      }
      if (cmdOptions.asrDevice !== undefined) {
        const devicePreference = resolveDevicePreference(cmdOptions.asrDevice.trim().toLowerCase());
        if (devicePreference === undefined) {
          console.error("Error: --asr-device must be one of: auto, cpu, cuda");
          process.exitCode = 1;
          return;
        }
        options.asrDevice = devicePreference;
      }
      await setupCredentials(
        configureCredentials,
        async (modelKey: AsrModelKey, devicePreference: AsrDevicePreference) =>
          runAsrInstallation({ modelKey, devicePreference, onStage: (s) => console.log(`  ${s}`) }),
        askHidden,
        options,
      );
    });

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
