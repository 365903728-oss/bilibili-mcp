import fs from "fs";
import path from "path";
import os from "os";
import { randomUUID } from "crypto";

export const ASR_PINNED_RUNTIME = "faster-whisper==1.2.1";
export const ASR_PINNED_CTRANSLATE2 = "ctranslate2==4.8.0";
export const ASR_STATE_VERSION = 2;
const ASR_LEGACY_STATE_VERSION = 1;

export const ASR_EXECUTION_PROFILES = [
  { device: "cpu", computeType: "int8" },
  { device: "cuda", computeType: "float16" },
] as const;

export type AsrExecutionProfile = (typeof ASR_EXECUTION_PROFILES)[number];
export const ASR_CPU_EXECUTION_PROFILE = ASR_EXECUTION_PROFILES[0];
export const ASR_CUDA_EXECUTION_PROFILE = ASR_EXECUTION_PROFILES[1];
export const ASR_DEVICE_PREFERENCES = ["auto", "cpu", "cuda"] as const;
export type AsrDevicePreference = (typeof ASR_DEVICE_PREFERENCES)[number];
export type AsrDeviceReadiness = "not_ready" | "migration_pending" | "ready";
export type AsrMigrationStatus = "pending" | "completed";

export const ASR_FAILURE_CATEGORIES = [
  "no_nvidia_gpu",
  "cuda_runtime_missing",
  "runtime_version_mismatch",
  "model_probe_failed",
] as const;

export type AsrFailureCategory = (typeof ASR_FAILURE_CATEGORIES)[number];

export const ASR_MODEL_SPECS = [
  {
    key: "tiny",
    repository: "Systran/faster-whisper-tiny",
    revision: "d90ca5fe260221311c53c58e660288d3deb8d356",
    approximateMB: 78.2,
  },
  {
    key: "base",
    repository: "Systran/faster-whisper-base",
    revision: "ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66",
    approximateMB: 148,
  },
  {
    key: "small",
    repository: "Systran/faster-whisper-small",
    revision: "536b0662742c02347bc0e980a01041f333bce120",
    approximateMB: 486,
  },
] as const;

export type AsrModelKey = (typeof ASR_MODEL_SPECS)[number]["key"];
export type AsrModelSpec = (typeof ASR_MODEL_SPECS)[number];

// Phase 1 backward-compatible aliases
export const ASR_PINNED_MODEL = ASR_MODEL_SPECS[2].repository;
export const ASR_PINNED_REVISION = ASR_MODEL_SPECS[2].revision;

export function resolveModelSpec(key: AsrModelKey): AsrModelSpec {
  const spec = ASR_MODEL_SPECS.find(
    (s) => s.key.localeCompare(key, undefined, { sensitivity: "base" }) === 0,
  );
  if (!spec) {
    throw new Error(
      `Unknown ASR model key: ${key}. Expected one of: ${ASR_MODEL_SPECS.map((s) => s.key).join(", ")}`,
    );
  }
  return spec;
}

export function isAllowlistedModel(repository: string, revision: string): boolean {
  return ASR_MODEL_SPECS.some(
    (s) =>
      s.repository === repository &&
      s.revision === revision,
  );
}

const REQUIRED_MODEL_FILES = [
  "model.bin",
  "config.json",
  "tokenizer.json",
  "vocabulary.txt",
];

export type AsrStateKind = "not_installed" | "incomplete" | "ready";

export interface AsrState {
  kind: AsrStateKind;
  version?: number;
  runtime?: string;
  model?: string;
  revision?: string;
  modelKey?: AsrModelKey;
  executionProfile?: AsrExecutionProfile;
  deviceReadiness?: AsrDeviceReadiness;
  migrationStatus?: AsrMigrationStatus;
  failureCategory?: AsrFailureCategory;
}

export interface AsrStateWriteOptions {
  executionProfile?: AsrExecutionProfile;
  failureCategory?: AsrFailureCategory;
}

export function modelKeyForRepo(repository: string, revision: string): AsrModelKey | null {
  const spec = ASR_MODEL_SPECS.find(
    (s) => s.repository === repository && s.revision === revision,
  );
  return spec?.key ?? null;
}

export interface AsrPaths {
  root: string;
  venv: string;
  model: string;
  stateFile: string;
}

const DEFAULT_BASE = path.join(os.homedir(), ".bilibili-mcp", "asr");

export function deriveAsrPaths(
  base?: string,
): AsrPaths {
  const root = base ?? DEFAULT_BASE;
  return {
    root,
    venv: path.join(root, "venv"),
    model: path.join(root, "models"),
    stateFile: path.join(root, "state.json"),
  };
}

function venvPythonExe(venvPath: string): string {
  return path.join(
    venvPath,
    process.platform === "win32" ? "Scripts" : "bin",
    process.platform === "win32" ? "python.exe" : "python",
  );
}

type PathKind = "dir" | "file";

function isRealPath(
  lstatSync: typeof fs.lstatSync,
  candidate: string,
  kind: PathKind,
): boolean {
  try {
    const stat = lstatSync(candidate);
    if (stat.isSymbolicLink()) return false;
    return kind === "dir" ? stat.isDirectory() : stat.isFile();
  } catch {
    // Fail closed: a path that cannot be inspected is not ready.
    return false;
  }
}

function hasExactKeys(
  value: Record<string, unknown>,
  expected: readonly string[],
): boolean {
  const actual = Object.keys(value).sort();
  const wanted = [...expected].sort();
  return actual.length === wanted.length && actual.every((key, index) => key === wanted[index]);
}

export function resolveExecutionProfile(
  device: unknown,
  computeType: unknown,
): AsrExecutionProfile | undefined {
  return ASR_EXECUTION_PROFILES.find(
    (profile) => profile.device === device && profile.computeType === computeType,
  );
}

export function resolveDevicePreference(value: unknown): AsrDevicePreference | undefined {
  return typeof value === "string" &&
    (ASR_DEVICE_PREFERENCES as readonly string[]).includes(value)
    ? value as AsrDevicePreference
    : undefined;
}

function isFailureCategory(value: unknown): value is AsrFailureCategory {
  return typeof value === "string" &&
    (ASR_FAILURE_CATEGORIES as readonly string[]).includes(value);
}

export function readAsrState(
  stateFile: string,
  readFileSync: typeof fs.readFileSync = fs.readFileSync,
  existsSync: typeof fs.existsSync = fs.existsSync,
  lstatSync: typeof fs.lstatSync = fs.lstatSync,
): AsrState {
  const root = path.dirname(stateFile);

  // Fail closed before reading: the ASR root must be a real directory; a
  // symlinked or file-in-directory-slot root is never followed.
  if (existsSync(root) && !isRealPath(lstatSync, root, "dir")) {
    return { kind: "incomplete" };
  }

  if (!existsSync(stateFile)) {
    const hasArtifacts =
      existsSync(root) ||
      existsSync(path.join(root, "venv")) ||
      existsSync(path.join(root, "models"));
    return { kind: hasArtifacts ? "incomplete" : "not_installed" };
  }

  // Fail closed before reading: the state file must be a real file; a
  // symlinked or directory-in-file-slot state file is never read.
  if (!isRealPath(lstatSync, stateFile, "file")) {
    return { kind: "incomplete" };
  }

  let parsed: Record<string, unknown>;

  try {
    const raw = readFileSync(stateFile, "utf8");
    parsed = JSON.parse(raw);
  } catch {
    return { kind: "incomplete" };
  }

  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    return { kind: "incomplete" };
  }

  if (
    parsed.kind !== "ready" ||
    typeof parsed.version !== "number" ||
    typeof parsed.runtime !== "string" ||
    typeof parsed.model !== "string" ||
    typeof parsed.revision !== "string"
  ) {
    return { kind: "incomplete" };
  }

  if (
    parsed.runtime !== ASR_PINNED_RUNTIME ||
    typeof parsed.model !== "string" ||
    typeof parsed.revision !== "string" ||
    !isAllowlistedModel(parsed.model, parsed.revision)
  ) {
    return { kind: "incomplete" };
  }

  const legacy = parsed.version === ASR_LEGACY_STATE_VERSION;
  let executionProfile: AsrExecutionProfile | undefined;
  let deviceReadiness: AsrDeviceReadiness;
  let migrationStatus: AsrMigrationStatus;
  let failureCategory: AsrFailureCategory | undefined;

  if (legacy) {
    if (!hasExactKeys(parsed, ["kind", "version", "runtime", "model", "revision"])) {
      return { kind: "incomplete" };
    }
    deviceReadiness = "migration_pending";
    migrationStatus = "pending";
  } else if (parsed.version === ASR_STATE_VERSION) {
    const expectedKeys = [
      "kind",
      "version",
      "runtime",
      "model",
      "revision",
      "device",
      "compute_type",
      "device_readiness",
      "migration_status",
      ...(Object.prototype.hasOwnProperty.call(parsed, "failure_category")
        ? ["failure_category"]
        : []),
    ];
    if (!hasExactKeys(parsed, expectedKeys)) {
      return { kind: "incomplete" };
    }
    executionProfile = resolveExecutionProfile(parsed.device, parsed.compute_type);
    if (
      executionProfile === undefined ||
      parsed.device_readiness !== "ready" ||
      parsed.migration_status !== "completed" ||
      (Object.prototype.hasOwnProperty.call(parsed, "failure_category") &&
        (!isFailureCategory(parsed.failure_category) || executionProfile.device === "cuda"))
    ) {
      return { kind: "incomplete" };
    }
    deviceReadiness = "ready";
    migrationStatus = "completed";
    failureCategory = parsed.failure_category as AsrFailureCategory | undefined;
  } else {
    return { kind: "incomplete" };
  }

  // Verify managed artifacts exist and are not symlinks. Symlinked state,
  // venv, executable, executable parent, model directory, or model files
  // must never produce `ready`.
  const venvDir = path.join(root, "venv");
  const binDir = path.join(venvDir, process.platform === "win32" ? "Scripts" : "bin");
  const modelDir = path.join(root, "models");

  // Every managed slot must hold the expected path type: root/venv/bin/model
  // are real directories; state/python executable/model artifacts are real
  // files. Symlinks or type mismatches must never produce `ready`.
  const managedPaths: Array<[string, PathKind]> = [
    [stateFile, "file"],
    [venvDir, "dir"],
    [binDir, "dir"],
    [venvPythonExe(venvDir), "file"],
    [modelDir, "dir"],
    ...REQUIRED_MODEL_FILES.map(
      (file) => [path.join(modelDir, file), "file"] as [string, PathKind],
    ),
  ];

  for (const [candidate, kind] of managedPaths) {
    if (!existsSync(candidate)) return { kind: "incomplete" };
    if (!isRealPath(lstatSync, candidate, kind)) return { kind: "incomplete" };
  }

  // Derived key (not persisted, computed from exact repository+revision match)
  const derivedKey = modelKeyForRepo(
    parsed.model as string,
    parsed.revision as string,
  );

  return {
    kind: "ready",
    version: parsed.version as number,
    runtime: parsed.runtime as string,
    model: parsed.model as string,
    revision: parsed.revision as string,
    modelKey: derivedKey ?? undefined,
    executionProfile,
    deviceReadiness,
    migrationStatus,
    failureCategory,
  };
}

export function writeAsrState(
  stateFile: string,
  modelKey: AsrModelKey = "small",
  options: AsrStateWriteOptions = {},
  writeFileSync: typeof fs.writeFileSync = fs.writeFileSync,
  renameSync: typeof fs.renameSync = fs.renameSync,
  unlinkSync: typeof fs.unlinkSync = fs.unlinkSync,
  mkdirSync: typeof fs.mkdirSync = fs.mkdirSync,
  randomId: () => string = randomUUID,
  lstatSync: typeof fs.lstatSync = fs.lstatSync,
  chmodSync: typeof fs.chmodSync = fs.chmodSync,
): void {
  const spec = resolveModelSpec(modelKey);
  const executionProfile = options.executionProfile ?? ASR_CPU_EXECUTION_PROFILE;
  const resolvedProfile = resolveExecutionProfile(
    executionProfile.device,
    executionProfile.computeType,
  );
  if (resolvedProfile === undefined) {
    throw new Error("Invalid ASR execution profile");
  }
  if (
    options.failureCategory !== undefined &&
    (!isFailureCategory(options.failureCategory) || resolvedProfile.device === "cuda")
  ) {
    throw new Error("Invalid ASR failure category for execution profile");
  }
  const state = {
    kind: "ready",
    version: ASR_STATE_VERSION,
    runtime: ASR_PINNED_RUNTIME,
    model: spec.repository,
    revision: spec.revision,
    device: resolvedProfile.device,
    compute_type: resolvedProfile.computeType,
    device_readiness: "ready",
    migration_status: "completed",
    ...(options.failureCategory === undefined
      ? {}
      : { failure_category: options.failureCategory }),
  };

  const dir = path.dirname(stateFile);

  // Reject a symlinked or non-directory root before any write; never follow
  // a symlink. An absent root is created owner-only below.
  try {
    const rootStat = lstatSync(dir);
    if (rootStat.isSymbolicLink()) {
      throw new Error("Failed to write ASR state: root is a symlink");
    }
    if (!rootStat.isDirectory()) {
      throw new Error("Failed to write ASR state: root is not a directory");
    }
    // Enforce owner-only permissions on the existing real root where supported.
    try {
      chmodSync(dir, 0o700);
    } catch (error) {
      const code = (error as NodeJS.ErrnoException).code;
      const unsupported =
        code === "ENOSYS" ||
        code === "EOPNOTSUPP" ||
        // EINVAL: Windows chmod can reject mode bits the filesystem does not
        // support; treated as unsupported there, a failure elsewhere.
        (code === "EINVAL" && process.platform === "win32");
      if (!unsupported) {
        // Permission/I/O failures (EPERM/EACCES/...) fail closed before
        // mkdir/write/rename; only explicitly unsupported cases are skipped.
        throw error;
      }
    }
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") {
      throw error;
    }
  }

  // Create the ASR root owner-only (mode only applies to new directories).
  mkdirSync(dir, { recursive: true, mode: 0o700 });

  // Unpredictable exclusive owner-only temp file, then atomic rename.
  const tmpFile = path.join(dir, `.state-${randomId()}.tmp`);
  try {
    writeFileSync(tmpFile, JSON.stringify(state, null, 2), {
      encoding: "utf8",
      flag: "wx",
      mode: 0o600,
    });
  } catch {
    try { unlinkSync(tmpFile); } catch { /* best-effort */ }
    throw new Error("Failed to write ASR state file");
  }

  try {
    renameSync(tmpFile, stateFile);
  } catch {
    try {
      unlinkSync(tmpFile);
    } catch {
      // best-effort cleanup
    }
    throw new Error("Failed to write ASR state atomically");
  }
}
