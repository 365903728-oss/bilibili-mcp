import fs from "fs";
import { SECURITY_LIMITS } from "../security/limits.js";
import {
  createAbortError,
  getOperationSignal,
  linkAbortSignal,
  throwIfAborted,
} from "../security/operation-context.js";
import { parseBoundedJsonResponse } from "./bounded-response.js";
import { ResourceLimitError } from "./errors.js";

const PACKAGE_NAME = "@xzxzzx/bilibili-mcp";
const LATEST_PACKAGE_SPEC = `${PACKAGE_NAME}@latest`;
const NPM_LATEST_URL = `https://registry.npmjs.org/${encodeURIComponent(PACKAGE_NAME)}/latest`;
const UPDATE_TIMEOUT_MS = 5_000;
const UPDATE_CACHE_MS = 5 * 60 * 1_000;

type FetchLike = typeof fetch;
let cachedUpdate:
  | { expiresAt: number; value: PackageUpdateInfo }
  | undefined;
let inFlightUpdate: Promise<PackageUpdateInfo> | null = null;
let activeUpdateWaiters = 0;

export interface PackageUpdateInfo {
  package_name: typeof PACKAGE_NAME;
  current_version: string;
  latest_version: string | null;
  update_available: boolean | null;
  checked_registry: string;
  recommended_mcp_config: {
    command: "npx";
    args: ["-y", typeof LATEST_PACKAGE_SPEC];
  };
  update_commands: {
    npx_config: string;
    npx_check: string;
    global_update: string;
  };
  notes: string[];
  notes_en: string[];
  notes_zh: string[];
}

function readCurrentVersion(): string {
  const packageJsonUrl = new URL("../../package.json", import.meta.url);
  const packageJson = JSON.parse(fs.readFileSync(packageJsonUrl, "utf8")) as {
    version?: unknown;
  };

  if (typeof packageJson.version !== "string") {
    throw new Error("package.json version is missing");
  }

  return packageJson.version;
}

function parseVersion(version: string): number[] | null {
  const match = /^(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$/.exec(version);
  if (!match) return null;
  return match.slice(1).map(Number);
}

function isNewerVersion(latestVersion: string, currentVersion: string): boolean | null {
  const latest = parseVersion(latestVersion);
  const current = parseVersion(currentVersion);
  if (!latest || !current) return null;

  for (let index = 0; index < latest.length; index += 1) {
    if (latest[index] > current[index]) return true;
    if (latest[index] < current[index]) return false;
  }

  return false;
}

function buildBaseInfo(currentVersion: string): Omit<
  PackageUpdateInfo,
  "latest_version" | "update_available"
> {
  const notesEn = [
    "Use the @latest MCP config so new client sessions resolve the latest npm version.",
    "Restart or reload the MCP client after changing package versions or MCP configuration.",
    "Do not print update hints during stdio startup; stdout must stay reserved for JSON-RPC.",
  ];
  const notesZh = [
    "建议在 MCP 配置中使用 @latest，这样新的客户端会话会解析 npm 最新版本。",
    "修改包版本或 MCP 配置后，请重启或重新加载 MCP 客户端。",
    "不要在 stdio 启动时打印更新提示；stdout 必须保留给 JSON-RPC。",
  ];

  return {
    package_name: PACKAGE_NAME,
    current_version: currentVersion,
    checked_registry: NPM_LATEST_URL,
    recommended_mcp_config: {
      command: "npx",
      args: ["-y", LATEST_PACKAGE_SPEC],
    },
    update_commands: {
      npx_config: `npx -y ${LATEST_PACKAGE_SPEC} config`,
      npx_check: `npx -y ${LATEST_PACKAGE_SPEC} check`,
      global_update: `npm install -g ${LATEST_PACKAGE_SPEC}`,
    },
    notes: notesEn,
    notes_en: notesEn,
    notes_zh: notesZh,
  };
}

async function fetchPackageUpdateInfo(
  fetchImpl: FetchLike,
  callerSignal?: AbortSignal,
): Promise<PackageUpdateInfo> {
  throwIfAborted(callerSignal);
  const currentVersion = readCurrentVersion();
  const baseInfo = buildBaseInfo(currentVersion);
  const controller = new AbortController();
  const unlinkAbort = linkAbortSignal(callerSignal, controller);
  const timer = setTimeout(() => controller.abort(), UPDATE_TIMEOUT_MS);

  try {
    const response = await fetchImpl(NPM_LATEST_URL, {
      headers: { Accept: "application/json" },
      redirect: "manual",
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`npm registry returned HTTP ${response.status}`);
    }

    const payload = await parseBoundedJsonResponse<{ version?: unknown }>(
      response,
      SECURITY_LIMITS.updateCheckBytes,
      "npm_update_json",
    );
    const latestVersion =
      typeof payload.version === "string" &&
      payload.version.length <= 64 &&
      parseVersion(payload.version) !== null
        ? payload.version
        : null;

    return {
      ...baseInfo,
      latest_version: latestVersion,
      update_available:
        latestVersion === null ? null : isNewerVersion(latestVersion, currentVersion),
    };
  } catch {
    if (callerSignal?.aborted) {
      throw createAbortError();
    }
    return {
      ...baseInfo,
      latest_version: null,
      update_available: null,
      notes: [
        ...baseInfo.notes,
        "Could not reach the npm registry; retry later or run npm view @xzxzzx/bilibili-mcp version.",
      ],
      notes_en: [
        ...baseInfo.notes_en,
        "Could not reach the npm registry; retry later or run npm view @xzxzzx/bilibili-mcp version.",
      ],
      notes_zh: [
        ...baseInfo.notes_zh,
        "无法连接 npm registry；请稍后重试，或运行 npm view @xzxzzx/bilibili-mcp version。",
      ],
    };
  } finally {
    clearTimeout(timer);
    unlinkAbort();
    controller.abort();
  }
}

function waitForCaller<T>(
  promise: Promise<T>,
  signal?: AbortSignal,
): Promise<T> {
  if (!signal) return promise;
  if (signal.aborted) {
    return Promise.reject(createAbortError());
  }
  return new Promise<T>((resolve, reject) => {
    const onAbort = () => {
      reject(createAbortError());
    };
    signal.addEventListener("abort", onAbort, { once: true });
    promise.then(
      (value) => {
        signal.removeEventListener("abort", onAbort);
        resolve(value);
      },
      (error) => {
        signal.removeEventListener("abort", onAbort);
        reject(error);
      },
    );
  });
}

async function waitForSharedUpdate(
  promise: Promise<PackageUpdateInfo>,
  signal?: AbortSignal,
): Promise<PackageUpdateInfo> {
  throwIfAborted(signal);
  if (activeUpdateWaiters >= SECURITY_LIMITS.updateCheckWaiters) {
    throw new ResourceLimitError(
      "Package update check waiter capacity is full",
      "update_check_waiters",
      SECURITY_LIMITS.updateCheckWaiters,
    );
  }
  activeUpdateWaiters += 1;
  try {
    return await waitForCaller(promise, signal);
  } finally {
    activeUpdateWaiters -= 1;
  }
}

export async function buildPackageUpdateInfo(
  fetchImpl: FetchLike = globalThis.fetch,
  signal?: AbortSignal,
): Promise<PackageUpdateInfo> {
  const operationSignal = getOperationSignal(signal);
  throwIfAborted(operationSignal);
  const useSharedState = fetchImpl === globalThis.fetch;
  if (!useSharedState) {
    return await waitForCaller(
      fetchPackageUpdateInfo(fetchImpl, operationSignal),
      operationSignal,
    );
  }

  if (cachedUpdate && cachedUpdate.expiresAt > Date.now()) {
    return cachedUpdate.value;
  }
  if (!inFlightUpdate) {
    // The underlying single-flight is process-owned. Cancelling one caller
    // releases only that waiter and must not abort work still needed by others.
    inFlightUpdate = fetchPackageUpdateInfo(fetchImpl)
      .then((value) => {
        cachedUpdate = {
          expiresAt: Date.now() + UPDATE_CACHE_MS,
          value,
        };
        return value;
      })
      .finally(() => {
        inFlightUpdate = null;
      });
  }
  return await waitForSharedUpdate(inFlightUpdate, operationSignal);
}
