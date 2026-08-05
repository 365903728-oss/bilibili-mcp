// B站 WBI 签名模块
import { createHash } from "crypto";
import { config } from "../config.js";
import {
  BilibiliAPIError,
  NetworkError,
  ResourceLimitError,
  TimeoutError,
} from "../utils/errors.js";
import { logger } from "../utils/logger.js";
import { SECURITY_LIMITS } from "../security/limits.js";
import {
  createAbortError,
  getOperationSignal,
  linkAbortSignal,
  runWithOperationSignal,
  throwIfAborted,
} from "../security/operation-context.js";
import { parseBoundedJsonResponse } from "../utils/bounded-response.js";

// WBI 缓存
let cachedWBI: {
  imgKey: string;
  subKey: string;
  mixKey: string;
  expireTime: number;
} | null = null;
let inFlightWBI: Promise<{
  imgKey: string;
  subKey: string;
  mixKey: string;
}> | null = null;
let activeWbiWaiters = 0;

const REQUEST_TIMEOUT_MS = config.requestTimeoutMs;
const BASE_URL = config.baseUrl;
const CACHE_EXPIRATION_MS = config.wbiCacheExpirationMs;

/**
 * 生成 WBI 签名所需的混合密钥
 */
function getMixKey(imgKey: string, subKey: string): string {
  // WBI 签名使用特定的混合顺序
  const saltTable = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5,
    49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55,
    40, 61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57,
    62, 11, 36, 20, 34, 44, 52,
  ];
  const mixKey = imgKey + subKey;
  return saltTable.map((i) => mixKey[i]).join("");
}

/**
 * MD5 哈希函数 - 使用 Node.js crypto 模块
 * 这是 B 站 WBI 签名算法真正需要的哈希函数
 */
function md5Hash(str: string): string {
  return createHash("md5").update(str).digest("hex");
}

/**
 * 获取 WBI 签名密钥
 */
interface WbiOperationContext {
  signal?: AbortSignal;
  deadlineAt?: number;
}

async function fetchAndCacheWBI(
  operation: WbiOperationContext = {},
): Promise<{
  imgKey: string;
  subKey: string;
  mixKey: string;
}> {
  const signal = getOperationSignal(operation.signal);
  throwIfAborted(signal);
  const controller = new AbortController();
  const unlinkAbort = linkAbortSignal(signal, controller);
  const timeoutMs = Math.min(
    REQUEST_TIMEOUT_MS,
    operation.deadlineAt === undefined
      ? REQUEST_TIMEOUT_MS
      : Math.max(0, operation.deadlineAt - Date.now()),
  );
  if (timeoutMs <= 0) {
    unlinkAbort();
    throw new TimeoutError("WBI request deadline exceeded", REQUEST_TIMEOUT_MS);
  }
  const timeoutId = setTimeout(() => {
    controller.abort();
  }, timeoutMs);
  try {
    const navRes = await fetch(`${BASE_URL}/x/web-interface/nav`, {
      headers: {
        "User-Agent": config.userAgent,
        Referer: config.referer,
      },
      redirect: "manual",
      signal: controller.signal,
    });

    if (!navRes.ok) {
      throw new NetworkError(
        `Failed to fetch WBI: ${navRes.status}`,
        undefined,
        undefined,
        navRes.status,
      );
    }

    const navData = await parseBoundedJsonResponse<{
      data?: { wbi_img?: { img_url?: unknown; sub_url?: unknown } };
    }>(navRes, SECURITY_LIMITS.wbiBootstrapBytes, "wbi_bootstrap_json");
    const wbiImg = navData.data?.wbi_img;
    if (
      !wbiImg ||
      typeof wbiImg.img_url !== "string" ||
      typeof wbiImg.sub_url !== "string" ||
      wbiImg.img_url.length > 2_048 ||
      wbiImg.sub_url.length > 2_048
    ) {
      throw new BilibiliAPIError(
        "WBI image data was invalid",
        "WBI_DATA_MISSING",
      );
    }

    const imgKeyMatch = wbiImg.img_url.match(/([^\/_]+)(?=\.[a-zA-Z]+$)/);
    const subKeyMatch = wbiImg.sub_url.match(/([^\/_]+)(?=\.[a-zA-Z]+$)/);
    const imgKey = imgKeyMatch?.[0];
    const subKey = subKeyMatch?.[0];
    if (
      !imgKey ||
      !subKey ||
      !/^[A-Za-z0-9]{32}$/.test(imgKey) ||
      !/^[A-Za-z0-9]{32}$/.test(subKey)
    ) {
      throw new BilibiliAPIError(
        "Failed to extract valid WBI keys",
        "WBI_KEY_EXTRACT_FAILED",
      );
    }

    const mixKey = getMixKey(imgKey, subKey);
    cachedWBI = {
      imgKey,
      subKey,
      mixKey,
      expireTime: Date.now() + CACHE_EXPIRATION_MS,
    };
    return { imgKey, subKey, mixKey };
  } catch (error) {
    if (signal?.aborted) {
      throw createAbortError();
    }
    if (error instanceof Error && error.name === "AbortError") {
      throw new TimeoutError(
        `WBI request timeout: ${REQUEST_TIMEOUT_MS}ms`,
        REQUEST_TIMEOUT_MS,
      );
    }
    if (error instanceof TypeError) {
      throw new NetworkError("Network request failed", error);
    }
    logger.error(
      "Error getting WBI",
      { error: error instanceof Error ? error.name : "UnknownError" },
      { type: "wbi-error" },
    );
    throw error;
  } finally {
    clearTimeout(timeoutId);
    unlinkAbort();
    controller.abort();
  }
}

function waitForCaller<T>(
  promise: Promise<T>,
  signal?: AbortSignal,
  deadlineAt?: number,
): Promise<T> {
  throwIfAborted(signal);
  const remainingMs =
    deadlineAt === undefined ? undefined : deadlineAt - Date.now();
  if (remainingMs !== undefined && remainingMs <= 0) {
    return Promise.reject(
      new TimeoutError("WBI request deadline exceeded", REQUEST_TIMEOUT_MS),
    );
  }
  if (!signal && remainingMs === undefined) return promise;
  return new Promise<T>((resolve, reject) => {
    let settled = false;
    const timer =
      remainingMs === undefined
        ? undefined
        : setTimeout(() => {
            if (settled) return;
            settled = true;
            signal?.removeEventListener("abort", onAbort);
            reject(
              new TimeoutError(
                "WBI request deadline exceeded",
                REQUEST_TIMEOUT_MS,
              ),
            );
          }, remainingMs);
    const cleanup = () => {
      if (timer !== undefined) clearTimeout(timer);
      signal?.removeEventListener("abort", onAbort);
    };
    const onAbort = () => {
      if (settled) return;
      settled = true;
      cleanup();
      reject(createAbortError());
    };
    signal?.addEventListener("abort", onAbort, { once: true });
    promise.then(
      (value) => {
        if (settled) return;
        settled = true;
        cleanup();
        resolve(value);
      },
      (error) => {
        if (settled) return;
        settled = true;
        cleanup();
        reject(error);
      },
    );
  });
}

export async function getWBI(
  operation: WbiOperationContext = {},
): Promise<{
  imgKey: string;
  subKey: string;
  mixKey: string;
}> {
  const signal = getOperationSignal(operation.signal);
  throwIfAborted(signal);
  const now = Date.now();
  if (operation.deadlineAt !== undefined && now >= operation.deadlineAt) {
    throw new TimeoutError(
      "WBI request deadline exceeded",
      REQUEST_TIMEOUT_MS,
    );
  }
  if (cachedWBI && cachedWBI.expireTime > now) {
    return {
      imgKey: cachedWBI.imgKey,
      subKey: cachedWBI.subKey,
      mixKey: cachedWBI.mixKey,
    };
  }
  if (!inFlightWBI) {
    inFlightWBI = runWithOperationSignal(
      undefined,
      async () => await fetchAndCacheWBI(),
    ).finally(() => {
        inFlightWBI = null;
      });
  }
  if (activeWbiWaiters >= SECURITY_LIMITS.bootstrapWaiters) {
    throw new ResourceLimitError(
      "WBI waiter capacity is full",
      "wbi_waiters",
      SECURITY_LIMITS.bootstrapWaiters,
    );
  }
  activeWbiWaiters += 1;
  try {
    return await waitForCaller(
      inFlightWBI,
      signal,
      operation.deadlineAt,
    );
  } finally {
    activeWbiWaiters -= 1;
  }
}

/**
 * 生成 WBI 签名
 */
export function generateWBISign(
  params: Record<string, string | number>,
  mixKey: string,
): string {
  // 将参数按字典序排序
  const sortedParams = Object.keys(params)
    .sort()
    .reduce(
      (result, key) => {
        result[key] = params[key];
        return result;
      },
      {} as Record<string, string | number>,
    );

  // 构建 query 字符串
  const queryStr = Object.entries(sortedParams)
    .map(([key, value]) => `${key}=${value}`)
    .join("&");

  // 计算 w_rid（使用 MD5 哈希）
  const strToSign = queryStr + mixKey;
  const w_rid = md5Hash(strToSign);

  return w_rid;
}
