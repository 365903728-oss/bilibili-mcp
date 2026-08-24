import { spawn } from "child_process";
import { randomUUID } from "crypto";
import fs from "fs";
import os from "os";
import path from "path";
import { createAbortError } from "../security/operation-context.js";
import {
  ASR_CUDA_EXECUTION_PROFILE,
  ASR_CPU_EXECUTION_PROFILE,
  ASR_FAILURE_CATEGORIES,
  ASR_PINNED_CTRANSLATE2,
  ASR_PINNED_RUNTIME,
  deriveAsrPaths,
  readAsrState,
  resolveDevicePreference,
  resolveExecutionProfile,
  resolveModelSpec,
  type AsrExecutionProfile,
  type AsrDevicePreference,
  type AsrFailureCategory,
  type AsrModelKey,
  type AsrModelSpec,
  type AsrPaths,
  writeAsrState,
} from "./state.js";

export const PYTHON_MIN_MAJOR = 3;
export const PYTHON_MIN_MINOR = 9;
export const COMPUTE_TYPE = ASR_CPU_EXECUTION_PROFILE.computeType;
export const DEVICE = ASR_CPU_EXECUTION_PROFILE.device;
const ASR_READINESS_EXIT_CODES: Record<AsrFailureCategory, number> = {
  no_nvidia_gpu: 20,
  cuda_runtime_missing: 21,
  runtime_version_mismatch: 22,
  model_probe_failed: 23,
};
const DIAG_MAX = 2000;
const MAX_INSTALLER_OUTPUT_BYTES = 64 * 1024;
const MAX_MODEL_FILES = 10_000;
const MODEL_BUDGET_MULTIPLIER = 1.5;
const MODEL_BUDGET_OVERHEAD_BYTES = 64 * 1024 * 1024;

export interface PythonCommand {
  executable: string;
  prefixArgs: string[];
}

export class AsrReadinessError extends Error {
  constructor(
    readonly category: AsrFailureCategory,
    readonly device?: AsrExecutionProfile["device"],
    readonly gpuFailureCategory?: AsrFailureCategory,
    readonly allowFallback = true,
  ) {
    super(`ASR device readiness failed (${category})`);
    this.name = "AsrReadinessError";
  }
}

function toPythonArgs(cmd: PythonCommand, ...extra: string[]): string[] {
  return [...cmd.prefixArgs, "-I", ...extra];
}

const ASR_CHILD_ENV_ALLOWLIST = new Set([
  "PATH",
  "SYSTEMROOT",
  "WINDIR",
  "COMSPEC",
  "PATHEXT",
  "TEMP",
  "TMP",
  "TMPDIR",
  "LANG",
  "LC_ALL",
  "LC_CTYPE",
  "NO_COLOR",
  "SSL_CERT_FILE",
  "SSL_CERT_DIR",
  "CUDA_PATH",
  "LD_LIBRARY_PATH",
]);

export function buildAsrChildEnv(
  source: Record<string, string | undefined>,
): Record<string, string | undefined> {
  const env: Record<string, string | undefined> = {
    PIP_DISABLE_PIP_VERSION_CHECK: "1",
    PIP_NO_INPUT: "1",
    PYTHONDONTWRITEBYTECODE: "1",
    PYTHONNOUSERSITE: "1",
    PYTHONUTF8: "1",
    HF_HUB_DISABLE_TELEMETRY: "1",
  };
  for (const [key, value] of Object.entries(source)) {
    const normalized = key.toUpperCase();
    if (
      value !== undefined &&
      ASR_CHILD_ENV_ALLOWLIST.has(normalized)
    ) {
      env[normalized] = value;
    }
  }
  return env;
}

function inferProcessTimeout(args: string[]): number {
  const joined = args.join("\n");
  if (args.includes("--version")) return 15_000;
  if (joined.includes("snapshot_download")) return 45 * 60 * 1_000;
  if (joined.includes("WhisperModel")) return 15 * 60 * 1_000;
  if (args.includes("venv")) return 5 * 60 * 1_000;
  if (args.includes("pip")) return 15 * 60 * 1_000;
  return 5 * 60 * 1_000;
}

function terminateProcessTree(child: ReturnType<typeof spawn>): void {
  if (process.platform === "win32" && child.pid !== undefined) {
    try {
      const killer = spawn(
        "taskkill.exe",
        ["/PID", String(child.pid), "/T", "/F"],
        {
          env: buildAsrChildEnv(process.env) as NodeJS.ProcessEnv,
          shell: false,
          stdio: "ignore",
          windowsHide: true,
        },
      );
      killer.unref();
      child.kill("SIGKILL");
    } catch {
      child.kill("SIGKILL");
    }
    return;
  }
  if (child.pid !== undefined) {
    try {
      process.kill(-child.pid, "SIGKILL");
      return;
    } catch {
      // Fall through to the direct child.
    }
  }
  child.kill("SIGKILL");
}

function execFile(
  file: string,
  args: string[],
  signal?: AbortSignal,
): Promise<{ code: number | null; stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(createAbortError());
      return;
    }
    const child = spawn(file, args, {
      env: buildAsrChildEnv(process.env),
      shell: false,
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
      detached: process.platform !== "win32",
    });

    let stdout = "";
    let stderr = "";
    let outputBytes = 0;
    let timedOut = false;
    let overflowed = false;
    let settled = false;
    let timeout: NodeJS.Timeout | undefined;
    const onAbort = () => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      terminateProcessTree(child);
      reject(createAbortError());
    };
    signal?.addEventListener("abort", onAbort, { once: true });
    const cleanup = () => signal?.removeEventListener("abort", onAbort);
    timeout = setTimeout(() => {
      timedOut = true;
      terminateProcessTree(child);
    }, inferProcessTimeout(args));

    child.stdout?.on("data", (chunk: Buffer) => {
      outputBytes += chunk.byteLength;
      if (outputBytes > MAX_INSTALLER_OUTPUT_BYTES) {
        overflowed = true;
        terminateProcessTree(child);
        return;
      }
      stdout = (stdout + chunk.toString("utf8")).slice(-DIAG_MAX);
    });
    child.stderr?.on("data", (chunk: Buffer) => {
      outputBytes += chunk.byteLength;
      if (outputBytes > MAX_INSTALLER_OUTPUT_BYTES) {
        overflowed = true;
        terminateProcessTree(child);
        return;
      }
      stderr = (stderr + chunk.toString("utf8")).slice(-DIAG_MAX);
    });

    child.on("close", (code) => {
      clearTimeout(timeout);
      if (settled) return;
      settled = true;
      cleanup();
      if (timedOut) {
        reject(new Error("ASR installer subprocess exceeded its time limit"));
        return;
      }
      if (overflowed) {
        reject(new Error("ASR installer subprocess output exceeded its limit"));
        return;
      }
      resolve({ code, stdout, stderr });
    });
    child.on("error", (err) => {
      clearTimeout(timeout);
      if (settled) return;
      settled = true;
      cleanup();
      reject(err);
    });
  });
}

function defaultCandidates(): PythonCommand[] {
  const list: PythonCommand[] = [
    { executable: "python3", prefixArgs: [] },
    { executable: "python", prefixArgs: [] },
  ];
  if (process.platform === "win32") {
    list.unshift({ executable: "py", prefixArgs: ["-3"] });
  }
  return list;
}

export async function discoverPython(
  spawnFn: typeof execFile = execFile,
  envOverride?: string,
  candidates: PythonCommand[] = defaultCandidates(),
): Promise<PythonCommand> {
  if (envOverride && envOverride.trim().length > 0) {
    const exe = envOverride.trim();
    const result = await spawnFn(exe, ["-I", "--version"]);
    if (result.code !== 0) {
      throw new Error(
        `BILIBILI_ASR_PYTHON is set but failed to start: ${result.stderr.slice(0, 200)}`,
      );
    }
    const versionOutput = (result.stdout + result.stderr).trim();
    const match = versionOutput.match(/Python\s+(\d+)\.(\d+)/);
    if (!match) {
      throw new Error(
        `BILIBILI_ASR_PYTHON is set but does not appear to be Python: ${versionOutput.slice(0, 200)}`,
      );
    }
    const major = parseInt(match[1], 10);
    const minor = parseInt(match[2], 10);
    if (major < PYTHON_MIN_MAJOR || (major === PYTHON_MIN_MAJOR && minor < PYTHON_MIN_MINOR)) {
      throw new Error(
        `BILIBILI_ASR_PYTHON is Python ${major}.${minor}; Python ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}+ required`,
      );
    }
    return { executable: exe, prefixArgs: [] };
  }

  for (const candidate of candidates) {
    try {
      const fullArgs = toPythonArgs(candidate, "--version");
      const result = await spawnFn(candidate.executable, fullArgs);
      if (result.code === 0) {
        const versionOutput = (result.stdout + result.stderr).trim();
        const match = versionOutput.match(/Python\s+(\d+)\.(\d+)/);
        if (match) {
          const major = parseInt(match[1], 10);
          const minor = parseInt(match[2], 10);
          if (major >= PYTHON_MIN_MAJOR && (major > PYTHON_MIN_MAJOR || minor >= PYTHON_MIN_MINOR)) {
            return candidate;
          }
        }
      }
    } catch {
      // candidate not found, try next
    }
  }

  throw new Error(
    `Python ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}+ not found. Install Python or set BILIBILI_ASR_PYTHON environment variable.`,
  );
}

function pythonCommandForVenv(venvPath: string): PythonCommand {
  const binDir = path.join(venvPath, process.platform === "win32" ? "Scripts" : "bin");
  return {
    executable: path.join(binDir, process.platform === "win32" ? "python.exe" : "python"),
    prefixArgs: [],
  };
}

export async function createVenv(
  python: PythonCommand,
  venvPath: string,
  spawnFn: typeof execFile = execFile,
  mkdirSyncFn: typeof fs.mkdirSync = fs.mkdirSync,
): Promise<PythonCommand> {
  mkdirSyncFn(path.dirname(venvPath), { recursive: true, mode: 0o700 });

  const result = await spawnFn(
    python.executable,
    toPythonArgs(python, "-m", "venv", "--copies", venvPath),
  );
  if (result.code !== 0) {
    throw new Error(`venv creation failed: ${result.stderr.slice(0, 500)}`);
  }

  return pythonCommandForVenv(venvPath);
}

export async function installRuntime(
  venvPython: PythonCommand,
  spawnFn: typeof execFile = execFile,
): Promise<void> {
  const result = await spawnFn(
    venvPython.executable,
    toPythonArgs(
      venvPython,
      "-m",
      "pip",
      "install",
      "--quiet",
      ASR_PINNED_RUNTIME,
      ASR_PINNED_CTRANSLATE2,
    ),
  );
  if (result.code !== 0) {
    throw new Error("pip install for the managed ASR runtime failed");
  }
}

export function modelInstallBudgetBytes(modelSpec: AsrModelSpec): number {
  return Math.ceil(
    modelSpec.approximateMB * 1024 * 1024 * MODEL_BUDGET_MULTIPLIER +
    MODEL_BUDGET_OVERHEAD_BYTES,
  );
}

function assertInstallFreeSpace(root: string, requiredBytes: number): void {
  fs.mkdirSync(root, { recursive: true, mode: 0o700 });
  const stats = fs.statfsSync(root);
  const availableBytes = Number(stats.bavail) * Number(stats.bsize);
  if (
    !Number.isFinite(availableBytes) ||
    availableBytes < requiredBytes
  ) {
    throw new Error("Insufficient free space for bounded ASR model setup");
  }
}

export function validateModelInstallTree(
  modelPath: string,
  maxBytes: number,
  maxFiles: number = MAX_MODEL_FILES,
): { bytes: number; files: number } {
  const root = path.resolve(modelPath);
  const rootStat = fs.lstatSync(root);
  if (!rootStat.isDirectory() || rootStat.isSymbolicLink()) {
    throw new Error("ASR model staging path is unsafe");
  }

  const stack = [root];
  let bytes = 0;
  let files = 0;
  while (stack.length > 0) {
    const current = stack.pop()!;
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const absolute = path.join(current, entry.name);
      const stat = fs.lstatSync(absolute);
      if (stat.isSymbolicLink()) {
        throw new Error("ASR model staging contains a symbolic link");
      }
      if (stat.isDirectory()) {
        stack.push(absolute);
        continue;
      }
      if (!stat.isFile()) {
        throw new Error("ASR model staging contains an unsupported entry");
      }
      files += 1;
      bytes += stat.size;
      if (files > maxFiles || bytes > maxBytes) {
        throw new Error("ASR model staging exceeded its storage budget");
      }
    }
  }
  return { bytes, files };
}

export async function downloadModel(
  venvPython: PythonCommand,
  modelPath: string,
  modelId: string,
  revision: string,
  spawnFn: typeof execFile = execFile,
  mkdirSyncFn: typeof fs.mkdirSync = fs.mkdirSync,
  maxBytes: number = 2 * 1024 * 1024 * 1024,
): Promise<void> {
  mkdirSyncFn(modelPath, { recursive: true });

  const script = [
    "import os, sys, threading",
    "from huggingface_hub import snapshot_download",
    "model_id, revision, local_dir = sys.argv[1], sys.argv[2], sys.argv[3]",
    "byte_budget, file_budget = int(sys.argv[4]), int(sys.argv[5])",
    "stop = threading.Event()",
    "def validate_tree():",
    "    total = 0",
    "    count = 0",
    "    for base, dirs, files in os.walk(local_dir, followlinks=False):",
    "        for name in dirs + files:",
    "            target = os.path.join(base, name)",
    "            if os.path.islink(target):",
    "                os._exit(86)",
    "        for name in files:",
    "            count += 1",
    "            total += os.path.getsize(os.path.join(base, name))",
    "            if count > file_budget or total > byte_budget:",
    "                os._exit(86)",
    "def watch():",
    "    while not stop.wait(0.25):",
    "        validate_tree()",
    "watcher = threading.Thread(target=watch, daemon=True)",
    "watcher.start()",
    "snapshot_download(model_id, revision=revision, local_dir=local_dir, local_dir_use_symlinks=False)",
    "stop.set()",
    "validate_tree()",
    "print('DOWNLOADED')",
  ].join("\n");

  const result = await spawnFn(
    venvPython.executable,
    toPythonArgs(
      venvPython,
      "-c",
      script,
      modelId,
      revision,
      modelPath,
      String(maxBytes),
      String(MAX_MODEL_FILES),
    ),
      );
  if (result.code !== 0) {
    throw new Error(
      `Model download failed: ${result.stderr.slice(0, 500)}`,
    );
  }

  if (result.stdout.trim() !== "DOWNLOADED") {
    throw new Error("Model download did not confirm completion");
  }
}

export async function verifyModel(
  venvPython: PythonCommand,
  modelPath: string,
  executionProfile: AsrExecutionProfile = ASR_CPU_EXECUTION_PROFILE,
  spawnFn: typeof execFile = execFile,
): Promise<void> {
  const profile = resolveExecutionProfile(
    executionProfile.device,
    executionProfile.computeType,
  );
  if (profile === undefined) {
    throw new AsrReadinessError("model_probe_failed");
  }
  const probePath = path.join(os.tmpdir(), `.bilibili-mcp-asr-probe-${randomUUID()}.wav`);
  const sampleRate = 16_000;
  const sampleCount = sampleRate;
  const wav = Buffer.alloc(44 + sampleCount * 2);
  wav.write("RIFF", 0, "ascii");
  wav.writeUInt32LE(wav.length - 8, 4);
  wav.write("WAVEfmt ", 8, "ascii");
  wav.writeUInt32LE(16, 16);
  wav.writeUInt16LE(1, 20);
  wav.writeUInt16LE(1, 22);
  wav.writeUInt32LE(sampleRate, 24);
  wav.writeUInt32LE(sampleRate * 2, 28);
  wav.writeUInt16LE(2, 32);
  wav.writeUInt16LE(16, 34);
  wav.write("data", 36, "ascii");
  wav.writeUInt32LE(sampleCount * 2, 40);
  const script = [
    "import ctypes, importlib.metadata, sys",
    "def fail(category, code):",
    "    print('FAILED:' + category, flush=True)",
    "    raise SystemExit(code)",
    "try:",
    "    model_path, probe_path, pinned_ct2, device, compute_type = sys.argv[1:6]",
    "    if importlib.metadata.version('ctranslate2') != pinned_ct2:",
    "        fail('runtime_version_mismatch', 22)",
    "    if device == 'cuda':",
    "        try:",
    "            cuda = ctypes.WinDLL('nvcuda.dll') if sys.platform == 'win32' else ctypes.CDLL('libcuda.so.1')",
    "        except OSError:",
    "            fail('cuda_runtime_missing', 21)",
    "        status = int(cuda.cuInit(0))",
    "        if status in (35, 803):",
    "            fail('runtime_version_mismatch', 22)",
    "        if status == 100:",
    "            fail('no_nvidia_gpu', 20)",
    "        if status != 0:",
    "            fail('model_probe_failed', 23)",
    "        count = ctypes.c_int()",
    "        status = int(cuda.cuDeviceGetCount(ctypes.byref(count)))",
    "        if status in (35, 803):",
    "            fail('runtime_version_mismatch', 22)",
    "        if status == 100 or (status == 0 and count.value == 0):",
    "            fail('no_nvidia_gpu', 20)",
    "        if status != 0:",
    "            fail('model_probe_failed', 23)",
    "    from faster_whisper import WhisperModel",
    "    model = WhisperModel(model_path, device=device, compute_type=compute_type)",
    "    segments, _ = model.transcribe(probe_path, beam_size=1)",
    "    for _ in segments:",
    "        pass",
    "except Exception as error:",
    "    message = str(error).lower()",
    "    if device == 'cuda':",
    "        if any(token in message for token in ('insufficient driver', 'driver mismatch', 'unsupported cuda version')):",
    "            fail('runtime_version_mismatch', 22)",
    "        if any(token in message for token in ('cublas', 'cudnn', 'nvcuda', 'libcuda', 'cuda runtime', 'cannot be loaded', 'library not found', 'dll not found')):",
    "            fail('cuda_runtime_missing', 21)",
    "    fail('model_probe_failed', 23)",
    "print('VERIFIED', flush=True)",
  ].join("\n");

  let result: { code: number | null; stdout: string; stderr: string } | undefined;
  let probeCreated = false;
  let cleanupFailed = false;
  try {
    fs.writeFileSync(probePath, wav, { flag: "wx", mode: 0o600 });
    probeCreated = true;
    result = await spawnFn(
      venvPython.executable,
      toPythonArgs(
        venvPython,
        "-c",
        script,
        modelPath,
        probePath,
        ASR_PINNED_CTRANSLATE2.split("==", 2)[1],
        profile.device,
        profile.computeType,
      ),
    );
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw error;
    }
    // Map subprocess and local probe failures after cleanup so a cleanup
    // failure can prevent auto fallback from publishing a ready Profile.
  } finally {
    if (probeCreated) {
      try {
        fs.unlinkSync(probePath);
      } catch {
        cleanupFailed = true;
      }
    }
  }
  if (cleanupFailed) {
    throw new AsrReadinessError(
      "model_probe_failed",
      profile.device,
      undefined,
      false,
    );
  }
  if (result === undefined) {
    throw new AsrReadinessError("model_probe_failed", profile.device);
  }

  if (result.code === 0 && result.stdout.trim() === "VERIFIED") {
    return;
  }

  const match = /^FAILED:([a-z_]+)$/.exec(result.stdout.trim());
  const matchedCategory = match !== null &&
      (ASR_FAILURE_CATEGORIES as readonly string[]).includes(match[1])
    ? match[1] as AsrFailureCategory
    : undefined;
  const category = matchedCategory !== undefined &&
      result.code === ASR_READINESS_EXIT_CODES[matchedCategory]
    ? matchedCategory
    : "model_probe_failed";
  throw new AsrReadinessError(category, profile.device);
}

export interface InstallResult {
  success: boolean;
  error?: string;
  pythonPath?: string;
  executionProfile?: AsrExecutionProfile;
  failureCategory?: AsrFailureCategory;
  failureDevice?: AsrExecutionProfile["device"];
  gpuFailureCategory?: AsrFailureCategory;
  asrPaths: AsrPaths;
}

async function verifyDeviceReadiness(
  venvPython: PythonCommand,
  modelPath: string,
  preference: AsrDevicePreference,
  spawnFn: typeof execFile,
  logStage: (stage: string) => void,
): Promise<{
  executionProfile: AsrExecutionProfile;
  failureCategory?: AsrFailureCategory;
}> {
  if (preference === "cpu") {
    logStage("正在验证模型最小推理（CPU INT8）...");
    await verifyModel(venvPython, modelPath, ASR_CPU_EXECUTION_PROFILE, spawnFn);
    return { executionProfile: ASR_CPU_EXECUTION_PROFILE };
  }

  try {
    logStage("正在验证 NVIDIA GPU 最小推理（CUDA Float16）...");
    await verifyModel(venvPython, modelPath, ASR_CUDA_EXECUTION_PROFILE, spawnFn);
    return { executionProfile: ASR_CUDA_EXECUTION_PROFILE };
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw error;
    }
    const readinessError = error instanceof AsrReadinessError
      ? error
      : new AsrReadinessError("model_probe_failed", "cuda");
    if (preference === "cuda" || !readinessError.allowFallback) {
      throw readinessError;
    }

    logStage(`GPU 验证未通过（${readinessError.category}），正在验证 CPU INT8 回退...`);
    try {
      await verifyModel(venvPython, modelPath, ASR_CPU_EXECUTION_PROFILE, spawnFn);
    } catch (cpuError) {
      if (cpuError instanceof Error && cpuError.name === "AbortError") {
        throw cpuError;
      }
      const cpuReadinessError = cpuError instanceof AsrReadinessError
        ? cpuError
        : new AsrReadinessError("model_probe_failed", "cpu");
      throw new AsrReadinessError(
        cpuReadinessError.category,
        "cpu",
        readinessError.category,
      );
    }
    return {
      executionProfile: ASR_CPU_EXECUTION_PROFILE,
      failureCategory: readinessError.category,
    };
  }
}

export async function verifyInstalledDeviceReadiness(
  paths: Pick<AsrPaths, "venv" | "model">,
  preference: AsrDevicePreference = "auto",
  signal?: AbortSignal,
  spawnFn: typeof execFile = execFile,
): Promise<{
  executionProfile: AsrExecutionProfile;
  failureCategory?: AsrFailureCategory;
}> {
  return await verifyDeviceReadiness(
    pythonCommandForVenv(paths.venv),
    paths.model,
    preference,
    (file, args) => spawnFn(file, args, signal),
    () => undefined,
  );
}

function prepareModelStaging(asrPaths: AsrPaths, preserveExistingModel: boolean): string {
  const root = path.resolve(asrPaths.root);
  const model = path.resolve(asrPaths.model);
  if (path.dirname(model) !== root || path.basename(model) !== "models") {
    throw new Error("ASR model path is outside the managed root");
  }
  const staging = path.join(root, `.models-staging-${randomUUID()}`);
  if (fs.existsSync(model) && !preserveExistingModel) {
    const stat = fs.lstatSync(model);
    if (!stat.isDirectory() || stat.isSymbolicLink()) {
      throw new Error("Existing ASR model path is unsafe");
    }
    fs.renameSync(model, staging);
  } else {
    fs.mkdirSync(staging, { recursive: false, mode: 0o700 });
  }
  return staging;
}

function cleanupModelStaging(asrPaths: AsrPaths, staging: string): void {
  const root = path.resolve(asrPaths.root);
  const target = path.resolve(staging);
  if (
    path.dirname(target) !== root ||
    !path.basename(target).startsWith(".models-staging-")
  ) {
    throw new Error("Refused unsafe ASR model staging cleanup");
  }
  fs.rmSync(target, { recursive: true, force: true });
}

function prepareRuntimeStaging(asrPaths: AsrPaths): string {
  const root = path.resolve(asrPaths.root);
  const venv = path.resolve(asrPaths.venv);
  if (path.dirname(venv) !== root || path.basename(venv) !== "venv") {
    throw new Error("ASR runtime path is outside the managed root");
  }
  const staging = path.join(root, `.venv-staging-${randomUUID()}`);
  fs.mkdirSync(staging, { recursive: false, mode: 0o700 });
  return staging;
}

function cleanupRuntimeStaging(asrPaths: AsrPaths, staging: string): void {
  const root = path.resolve(asrPaths.root);
  const target = path.resolve(staging);
  if (
    path.dirname(target) !== root ||
    !path.basename(target).startsWith(".venv-staging-")
  ) {
    throw new Error("Refused unsafe ASR runtime staging cleanup");
  }
  fs.rmSync(target, { recursive: true, force: true });
}

export async function runAsrInstallation(
  options: {
    fsMkdirSync?: typeof fs.mkdirSync;
    fsLstatSync?: typeof fs.lstatSync;
    fsUnlinkSync?: typeof fs.unlinkSync;
    asrBase?: string;
    pythonOverride?: string;
    modelKey?: AsrModelKey;
    devicePreference?: AsrDevicePreference;
    spawnFn?: typeof execFile;
    onStage?: (stage: string) => void;
  } = {},
): Promise<InstallResult> {
  const mkdirSyncFn = options.fsMkdirSync ?? fs.mkdirSync;
  const lstatSyncFn = options.fsLstatSync ?? fs.lstatSync;
  const unlinkSyncFn = options.fsUnlinkSync ?? fs.unlinkSync;
  const spawnFn = options.spawnFn ?? execFile;
  const logStage = options.onStage ?? (() => {});
  const asrPaths = deriveAsrPaths(options.asrBase);
  let venvStaging: string | undefined;
  let venvBackup: string | undefined;
  let modelStaging: string | undefined;
  let modelBackup: string | undefined;
  let stateBackup: string | undefined;

  // Fail before ANY mutation when an existing ASR root is a symlink or not
  // a real directory; an absent root is created owner-only later.
  try {
    const rootStat = lstatSyncFn(asrPaths.root);
    if (rootStat.isSymbolicLink() || !rootStat.isDirectory()) {
      return {
        success: false,
        error: "Refusing ASR install: root is a symlink or not a directory",
        asrPaths,
      };
    }
  } catch (error) {
    const code = (error as NodeJS.ErrnoException)?.code;
    // Only ENOENT means absent; ENOTDIR is an invalid path component and must
    // fail closed before any spawn or mutation.
    if (code !== "ENOENT") {
      return {
        success: false,
        error: `Cannot inspect ASR root: ${(error as Error)?.message ?? String(error)}`,
        asrPaths,
      };
    }
  }

  // Resolve model before any mutation
  const modelKey = options.modelKey ?? "small";
  const devicePreference = resolveDevicePreference(options.devicePreference ?? "auto");
  if (devicePreference === undefined) {
    return {
      success: false,
      error: "Invalid ASR device preference. Expected auto, cpu, or cuda.",
      asrPaths,
    };
  }
  let modelSpec: AsrModelSpec;
  try {
    modelSpec = resolveModelSpec(modelKey);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return { success: false, error: message, asrPaths };
  }

  const existingState = readAsrState(asrPaths.stateFile);
  const sameModel =
    existingState.kind === "ready" &&
    existingState.model === modelSpec.repository &&
    existingState.revision === modelSpec.revision;
  const hasReadyInstallation = existingState.kind === "ready";

  // ponytail: one active model reuses the Phase 1 directory; use per-model
  // directories only if retaining several installed models becomes a real need.

  try {
    let python: PythonCommand;
    let targetVenv: string;
    const pythonOverride = options.pythonOverride ?? process.env.BILIBILI_ASR_PYTHON;
    if (hasReadyInstallation) {
      if (pythonOverride?.trim()) {
        logStage("正在查找 Python 3.9+...");
        python = await discoverPython(spawnFn, pythonOverride);
      } else {
        python = pythonCommandForVenv(asrPaths.venv);
      }
      venvStaging = prepareRuntimeStaging(asrPaths);
      targetVenv = venvStaging;
      logStage("正在创建隔离的 ASR 运行时...");
    } else {
      logStage("正在查找 Python 3.9+...");
      python = await discoverPython(spawnFn, pythonOverride);
      targetVenv = asrPaths.venv;
      logStage("正在创建虚拟环境...");
    }

    const venvPython = await createVenv(python, targetVenv, spawnFn, mkdirSyncFn);

    logStage("正在安装受控 ASR 运行时...");
    await installRuntime(venvPython, spawnFn);

    let candidateModel = asrPaths.model;
    let modelBudget: number | undefined;
    if (!sameModel) {
      modelBudget = modelInstallBudgetBytes(modelSpec);
      assertInstallFreeSpace(asrPaths.root, modelBudget);
      modelStaging = prepareModelStaging(asrPaths, hasReadyInstallation);

      logStage(`正在下载模型（约 ${modelSpec.approximateMB} MB）...`);
      await downloadModel(
        venvPython,
        modelStaging,
        modelSpec.repository,
        modelSpec.revision,
        spawnFn,
        mkdirSyncFn,
        modelBudget,
      );
      candidateModel = modelStaging;
    }

    const readiness = await verifyDeviceReadiness(
      venvPython,
      candidateModel,
      devicePreference,
      spawnFn,
      logStage,
    );
    if (modelStaging !== undefined && modelBudget !== undefined) {
      validateModelInstallTree(modelStaging, modelBudget);
    }

    if (hasReadyInstallation) {
      const candidateStateBackup = path.join(
        asrPaths.root,
        `.state-backup-${randomUUID()}.json`,
      );
      fs.renameSync(asrPaths.stateFile, candidateStateBackup);
      stateBackup = candidateStateBackup;

      const venvStat = fs.lstatSync(asrPaths.venv);
      if (!venvStat.isDirectory() || venvStat.isSymbolicLink()) {
        throw new Error("Existing ASR runtime path is unsafe");
      }
      const candidateVenvBackup = path.join(asrPaths.root, `.venv-backup-${randomUUID()}`);
      fs.renameSync(asrPaths.venv, candidateVenvBackup);
      venvBackup = candidateVenvBackup;
      fs.renameSync(venvStaging!, asrPaths.venv);
      venvStaging = undefined;
    }

    if (modelStaging !== undefined) {
      if (fs.existsSync(asrPaths.model)) {
        const modelStat = fs.lstatSync(asrPaths.model);
        if (!modelStat.isDirectory() || modelStat.isSymbolicLink()) {
          throw new Error("Existing ASR model path is unsafe");
        }
        const candidateModelBackup = path.join(
          asrPaths.root,
          `.models-backup-${randomUUID()}`,
        );
        fs.renameSync(asrPaths.model, candidateModelBackup);
        modelBackup = candidateModelBackup;
      }
      fs.renameSync(modelStaging, asrPaths.model);
      modelStaging = undefined;
    }

    writeAsrState(
      asrPaths.stateFile,
      modelSpec.key,
      readiness,
      fs.writeFileSync,
      fs.renameSync,
      unlinkSyncFn,
      mkdirSyncFn,
    );

    // Publication is complete. Backup deletion is best-effort and cannot turn
    // an already-active verified Profile into a reported failure.
    if (modelBackup !== undefined) {
      try { fs.rmSync(modelBackup, { recursive: true, force: true }); } catch { /* best-effort */ }
      modelBackup = undefined;
    }
    if (venvBackup !== undefined) {
      try { fs.rmSync(venvBackup, { recursive: true, force: true }); } catch { /* best-effort */ }
      venvBackup = undefined;
    }
    if (stateBackup !== undefined) {
      try { unlinkSyncFn(stateBackup); } catch { /* best-effort */ }
      stateBackup = undefined;
    }
    return {
      success: true,
      pythonPath: hasReadyInstallation
        ? pythonCommandForVenv(asrPaths.venv).executable
        : python.executable,
      executionProfile: readiness.executionProfile,
      failureCategory: readiness.failureCategory,
      asrPaths,
    };
  } catch (error) {
    let rollbackFailed = false;
    if (modelBackup !== undefined) {
      try {
        if (fs.existsSync(asrPaths.model)) {
          fs.rmSync(asrPaths.model, { recursive: true, force: true });
        }
        if (fs.existsSync(modelBackup)) {
          fs.renameSync(modelBackup, asrPaths.model);
        }
        modelBackup = undefined;
      } catch {
        rollbackFailed = true;
      }
    }
    if (venvBackup !== undefined) {
      try {
        if (fs.existsSync(asrPaths.venv)) {
          fs.rmSync(asrPaths.venv, { recursive: true, force: true });
        }
        if (fs.existsSync(venvBackup)) {
          fs.renameSync(venvBackup, asrPaths.venv);
        }
        venvBackup = undefined;
      } catch {
        rollbackFailed = true;
      }
    }
    if (stateBackup !== undefined) {
      if (!rollbackFailed) {
        try {
          if (fs.existsSync(asrPaths.stateFile)) {
            unlinkSyncFn(asrPaths.stateFile);
          }
          fs.renameSync(stateBackup, asrPaths.stateFile);
          stateBackup = undefined;
        } catch {
          rollbackFailed = true;
        }
      }
      if (rollbackFailed) {
        // The previous state must not describe partially restored artifacts.
        // Leaving its backup inactive makes all future reads fail closed.
        try {
          if (fs.existsSync(asrPaths.stateFile)) {
            unlinkSyncFn(asrPaths.stateFile);
          }
        } catch {
          // The bounded rollback error below remains authoritative.
        }
      }
    }
    if (modelStaging !== undefined) {
      try {
        cleanupModelStaging(asrPaths, modelStaging);
      } catch {
        // Keep the original bounded setup error.
      }
    }
    if (venvStaging !== undefined) {
      try {
        cleanupRuntimeStaging(asrPaths, venvStaging);
      } catch {
        // Keep the original bounded setup error.
      }
    }
    const message = error instanceof Error ? error.message : String(error);
    const readinessError = error instanceof AsrReadinessError ? error : undefined;
    return {
      success: false,
      error: rollbackFailed
        ? "ASR setup failed and the previous installation could not be restored"
        : message,
      failureCategory: readinessError?.category,
      failureDevice: readinessError?.device,
      gpuFailureCategory: readinessError?.gpuFailureCategory,
      asrPaths,
    };
  }
}
