// B站 buvid 指纹模块
import { config } from "../config.js";
import { logger } from "../utils/logger.js";
import { throttledFetch } from "./http.js";
import { SECURITY_LIMITS } from "../security/limits.js";
import { parseBoundedJsonResponse } from "../utils/bounded-response.js";
import {
  createAbortError,
  getOperationSignal,
  runWithOperationSignal,
  throwIfAborted,
} from "../security/operation-context.js";
import { ResourceLimitError } from "../utils/errors.js";

const BASE_URL = config.baseUrl;

// buvid 指纹缓存（用于规避反爬验证）
let cachedBuvid: {
  buvid3: string;
  buvid4: string;
  expireTime: number;
} | null = null;
let inFlightBuvid: Promise<{ buvid3: string; buvid4: string } | null> | null =
  null;
let activeBuvidWaiters = 0;

async function fetchAndCacheBuvid(): Promise<{
  buvid3: string;
  buvid4: string;
} | null> {
  try {
    return await throttledFetch(async (controller) => {
      const resp = await fetch(`${BASE_URL}/x/frontend/finger/spi`, {
        headers: {
          "User-Agent": config.userAgent,
          Referer: config.referer,
        },
        redirect: "manual",
        signal: controller.signal,
      });

      if (!resp.ok) return null;

      const data = await parseBoundedJsonResponse<{
        code?: unknown;
        data?: { b_3?: unknown; b_4?: unknown };
      }>(resp, SECURITY_LIMITS.fingerprintBytes, "bilibili_fingerprint_json");
      const buvid3 = data.data?.b_3;
      const buvid4 = data.data?.b_4;
      if (
        data.code !== 0 ||
        typeof buvid3 !== "string" ||
        typeof buvid4 !== "string" ||
        buvid3.length < 1 ||
        buvid4.length < 1 ||
        buvid3.length > 256 ||
        buvid4.length > 256 ||
        !/^[A-Za-z0-9._~-]+$/.test(buvid3) ||
        !/^[A-Za-z0-9._~-]+$/.test(buvid4)
      ) {
        return null;
      }

      cachedBuvid = {
        buvid3,
        buvid4,
        expireTime: Date.now() + 24 * 60 * 60 * 1000,
      };

      logger.info("Buvid fingerprint fetched", {
        buvid3: buvid3.substring(0, 8) + "...",
      });
      return { buvid3: cachedBuvid.buvid3, buvid4: cachedBuvid.buvid4 };
    });
  } catch (error) {
    logger.warn(
      "Failed to fetch buvid fingerprint, continuing without it",
      { error: error instanceof Error ? error.message : error },
    );
    return null;
  }
}

/**
 * 获取 buvid 指纹 Cookie（规避 Bilibili 反爬 -352 错误）
 * buvid3/buvid4 是 Bilibili 用来识别浏览器的指纹 Cookie，
 * 无需登录即可从 /x/frontend/finger/spi 接口获取
 */
export async function getBuvid(): Promise<{
  buvid3: string;
  buvid4: string;
} | null> {
  const signal = getOperationSignal();
  throwIfAborted(signal);
  const now = Date.now();

  if (cachedBuvid && cachedBuvid.expireTime > now) {
    return { buvid3: cachedBuvid.buvid3, buvid4: cachedBuvid.buvid4 };
  }

  if (!inFlightBuvid) {
    inFlightBuvid = runWithOperationSignal(
      undefined,
      async () => await fetchAndCacheBuvid(),
    ).finally(() => {
        inFlightBuvid = null;
      });
  }

  if (activeBuvidWaiters >= SECURITY_LIMITS.bootstrapWaiters) {
    throw new ResourceLimitError(
      "Fingerprint waiter capacity is full",
      "fingerprint_waiters",
      SECURITY_LIMITS.bootstrapWaiters,
    );
  }
  activeBuvidWaiters += 1;
  try {
    if (!signal) return await inFlightBuvid;
    return await new Promise((resolve, reject) => {
      const onAbort = () => reject(createAbortError());
      signal.addEventListener("abort", onAbort, { once: true });
      inFlightBuvid!.then(
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
  } finally {
    activeBuvidWaiters -= 1;
  }
}
