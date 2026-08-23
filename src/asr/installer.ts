import { spawn } from "child_process";
import { randomUUID } from "crypto";
import fs from "fs";
import os from "os";
import path from "path";
import {
  ASR_PINNED_RUNTIME,
  deriveAsrPaths,
  readAsrState,
  resolveModelSpec,
  type AsrModelKey,
  type AsrModelSpec,
  type AsrPaths,
  writeAsrState,
} from "./state.js";

export const PYTHON_MIN_MAJOR = 3;
export const PYTHON_MIN_MINOR = 9;
export const COMPUTE_TYPE = "int8";
export const DEVICE = "cpu";
const DIAG_MAX = 2000;
const MAX_INSTALLER_OUTPUT_BYTES = 64 * 1024;
const MAX_MODEL_FILES = 10_000;
const MODEL_BUDGET_MULTIPLIER = 1.5;
const MODEL_BUDGET_OVERHEAD_BYTES = 64 * 1024 * 1024;

export interface PythonCommand {
  executable: string;
  prefixArgs: string[];
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
): Promise<{ code: number | null; stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
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
    const timeout = setTimeout(() => {
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

export async function createVenv(
  python: PythonCommand,
  venvPath: string,
  spawnFn: typeof execFile = execFile,
  mkdirSyncFn: typeof fs.mkdirSync = fs.mkdirSync,
): Promise<PythonCommand> {
  mkdirSyncFn(path.dirname(venvPath), { recursive: true, mode: 0o700 });

  const result = await spawnFn(python.executable, toPythonArgs(python, "-m", "venv", venvPath));
  if (result.code !== 0) {
    throw new Error(`venv creation failed: ${result.stderr.slice(0, 500)}`);
  }

  const binDir = path.join(venvPath, process.platform === "win32" ? "Scripts" : "bin");
  const pythonExe = path.join(binDir, process.platform === "win32" ? "python.exe" : "python");

  return { executable: pythonExe, prefixArgs: [] };
}

export async function installRuntime(
  venvPython: PythonCommand,
  spawnFn: typeof execFile = execFile,
): Promise<void> {
  const result = await spawnFn(
    venvPython.executable,
    toPythonArgs(venvPython, "-m", "pip", "install", "--quiet", ASR_PINNED_RUNTIME),
      );
  if (result.code !== 0) {
    throw new Error(
      `pip install faster-whisper failed: ${result.stderr.slice(0, 500)}`,
    );
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
  spawnFn: typeof execFile = execFile,
): Promise<void> {
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
    "import sys",
    "from faster_whisper import WhisperModel",
    `model = WhisperModel(sys.argv[1], device="${DEVICE}", compute_type="${COMPUTE_TYPE}")`,
    "segments, _ = model.transcribe(sys.argv[2], beam_size=1)",
    "for _ in segments:",
    "    pass",
    "print('VERIFIED')",
  ].join("\n");

  let result: { code: number | null; stdout: string; stderr: string };
  let probeCreated = false;
  try {
    fs.writeFileSync(probePath, wav, { flag: "wx", mode: 0o600 });
    probeCreated = true;
    result = await spawnFn(
      venvPython.executable,
      toPythonArgs(venvPython, "-c", script, modelPath, probePath),
    );
  } finally {
    if (probeCreated) fs.unlinkSync(probePath);
  }
  if (result.code !== 0) {
    throw new Error(
      `Model verification failed: ${result.stderr.slice(0, 500)}`,
    );
  }

  if (result.stdout.trim() !== "VERIFIED") {
    throw new Error("Model verification did not confirm load");
  }
}

export interface InstallResult {
  success: boolean;
  error?: string;
  pythonPath?: string;
  asrPaths: AsrPaths;
}

function prepareModelStaging(asrPaths: AsrPaths): string {
  const root = path.resolve(asrPaths.root);
  const model = path.resolve(asrPaths.model);
  if (path.dirname(model) !== root || path.basename(model) !== "models") {
    throw new Error("ASR model path is outside the managed root");
  }
  const staging = path.join(root, `.models-staging-${randomUUID()}`);
  if (fs.existsSync(model)) {
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

export async function runAsrInstallation(
  options: {
    fsMkdirSync?: typeof fs.mkdirSync;
    fsLstatSync?: typeof fs.lstatSync;
    fsUnlinkSync?: typeof fs.unlinkSync;
    asrBase?: string;
    pythonOverride?: string;
    modelKey?: AsrModelKey;
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
  let modelStaging: string | undefined;

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
  let modelSpec: AsrModelSpec;
  try {
    modelSpec = resolveModelSpec(modelKey);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return { success: false, error: message, asrPaths };
  }

  // A legacy v1 state already owns a valid managed model and runtime. Promote
  // it in place only after the new end-to-end CPU readiness probe succeeds.
  const existingState = readAsrState(asrPaths.stateFile);
  const sameModel =
    existingState.kind === "ready" &&
    existingState.model === modelSpec.repository &&
    existingState.revision === modelSpec.revision;
  if (sameModel && existingState.migrationStatus === "pending") {
    const venvPython: PythonCommand = {
      executable: path.join(
        asrPaths.venv,
        process.platform === "win32" ? "Scripts" : "bin",
        process.platform === "win32" ? "python.exe" : "python",
      ),
      prefixArgs: [],
    };
    try {
      logStage("正在验证模型最小推理（CPU INT8）...");
      await verifyModel(venvPython, asrPaths.model, spawnFn);
      writeAsrState(asrPaths.stateFile, modelSpec.key);
      return { success: true, pythonPath: venvPython.executable, asrPaths };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return { success: false, error: message, asrPaths };
    }
  }

  // Idempotency: a same-model v2 CPU profile has already passed this probe.
  if (sameModel) {
    return { success: true, pythonPath: "already installed", asrPaths };
  }

  // ponytail: one active model reuses the Phase 1 directory; use per-model
  // directories only if retaining several installed models becomes a real need.

  // Invalidate stale state marker so a failed retry does not leave
  // behind a valid-looking marker alongside now-present artifacts.
  if (existingState.kind !== "not_installed") {
    try {
      unlinkSyncFn(asrPaths.stateFile);
    } catch (err: unknown) {
      const code = (err as NodeJS.ErrnoException)?.code;
      if (code !== "ENOENT") {
        return {
          success: false,
          error: `Cannot clear stale ASR state: ${(err as Error)?.message ?? String(err)}`,
          asrPaths,
        };
      }
    }
  }

  try {
    const pythonOverride = options.pythonOverride ?? process.env.BILIBILI_ASR_PYTHON;
    logStage("正在查找 Python 3.9+...");
    const python = await discoverPython(spawnFn, pythonOverride);

    logStage("正在创建虚拟环境...");
    const venvPython = await createVenv(python, asrPaths.venv, spawnFn, mkdirSyncFn);

    logStage("正在安装 faster-whisper...");
    await installRuntime(venvPython, spawnFn);

    const modelBudget = modelInstallBudgetBytes(modelSpec);
    assertInstallFreeSpace(asrPaths.root, modelBudget);
    modelStaging = prepareModelStaging(asrPaths);

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

    logStage("正在验证模型加载（CPU INT8）...");
    await verifyModel(venvPython, modelStaging, spawnFn);
    validateModelInstallTree(modelStaging, modelBudget);
    if (fs.existsSync(asrPaths.model)) {
      throw new Error("ASR model destination changed during setup");
    }
    fs.renameSync(modelStaging, asrPaths.model);
    modelStaging = undefined;

    writeAsrState(
      asrPaths.stateFile,
      modelSpec.key,
      fs.writeFileSync,
      fs.renameSync,
      fs.unlinkSync,
      mkdirSyncFn,
    );
    return { success: true, pythonPath: python.executable, asrPaths };
  } catch (error) {
    if (modelStaging !== undefined) {
      try {
        cleanupModelStaging(asrPaths, modelStaging);
      } catch {
        // Keep the original bounded setup error.
      }
    }
    const message = error instanceof Error ? error.message : String(error);
    return { success: false, error: message, asrPaths };
  }
}
