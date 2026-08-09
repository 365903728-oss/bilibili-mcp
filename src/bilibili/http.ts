// B站 API HTTP 层：限流、重试、WBI 签名请求、普通请求
import { config } from "../config.js";
import {
  BilibiliAPIError,
  CommentsDisabledError,
  NetworkError,
  PaidVideoError,
  ResourceLimitError,
  TimeoutError,
} from "../utils/errors.js";
import { logger } from "../utils/logger.js";
import { withRetry } from "../utils/retry.js";
import { credentialManager } from "../utils/credentials.js";
import { generateWBISign, getWBI } from "./wbi.js";
import { SECURITY_LIMITS } from "../security/limits.js";
import {
  abortableDelay,
  createAbortError,
  getOperationSignal,
  linkAbortSignal,
  throwIfAborted,
} from "../security/operation-context.js";
import { parseBoundedJsonResponse } from "../utils/bounded-response.js";

const BASE_URL = config.baseUrl;

// 请求限流 - 避免高频请求被 Bilibili 限制
const RATE_LIMIT_MS = config.rateLimitMs;
const REQUEST_TIMEOUT_MS = config.requestTimeoutMs;
const PAID_VIDEO_ENDPOINTS = new Set([
  "/x/web-interface/view",
  "/x/player/v2",
]);
let lastRequestTime: number | null = null;
let pendingAdmissions = 0;
let activeAndQueuedOperations = 0;

export interface HttpOperationContext {
  signal?: AbortSignal;
  deadlineAt: number;
}

function isExplicitPaidVideoDenial(path: string, message: unknown): boolean {
  return (
    PAID_VIDEO_ENDPOINTS.has(path) &&
    typeof message === "string" &&
    /(?:付费|购买后|需购买)/u.test(message)
  );
}

async function reserveAdmission(
  deadlineAt: number,
  signal?: AbortSignal,
): Promise<void> {
  throwIfAborted(signal);
  if (pendingAdmissions >= SECURITY_LIMITS.httpAdmissionQueue) {
    throw new ResourceLimitError(
      "Bilibili request admission queue is full",
      "http_admission_queue",
      SECURITY_LIMITS.httpAdmissionQueue,
    );
  }

  const now = Date.now();
  const scheduledAt =
    lastRequestTime === null
      ? now
      : Math.max(now, lastRequestTime + RATE_LIMIT_MS);
  const waitMs = scheduledAt - now;
  const maxWaitMs = Math.min(
    Math.max(0, deadlineAt - now),
    SECURITY_LIMITS.httpAdmissionWaitMs,
  );

  if (waitMs > maxWaitMs) {
    throw new ResourceLimitError(
      "Bilibili request admission deadline exceeded",
      "http_admission_wait_ms",
      maxWaitMs,
    );
  }

  lastRequestTime = scheduledAt;
  pendingAdmissions += 1;
  try {
    if (waitMs > 0) {
      await abortableDelay(waitMs, signal);
    }
    throwIfAborted(signal);
    if (Date.now() >= deadlineAt) {
      throw new TimeoutError(
        `Request timeout: ${REQUEST_TIMEOUT_MS}ms`,
        REQUEST_TIMEOUT_MS,
      );
    }
  } finally {
    pendingAdmissions -= 1;
  }
}

/**
 * 带限流和超时控制的请求包装器
 */
export async function throttledFetch<T>(
  fetchFn: (controller: AbortController) => Promise<T>,
  options: {
    signal?: AbortSignal;
    deadlineAt?: number;
  } = {},
): Promise<T> {
  const signal = getOperationSignal(options.signal);
  throwIfAborted(signal);
  if (
    activeAndQueuedOperations >= SECURITY_LIMITS.httpConcurrentOperations
  ) {
    throw new ResourceLimitError(
      "Bilibili request capacity is full",
      "http_operation_capacity",
      SECURITY_LIMITS.httpConcurrentOperations,
    );
  }
  activeAndQueuedOperations += 1;
  const deadlineAt = options.deadlineAt ??
    (Date.now() + REQUEST_TIMEOUT_MS);

  let controller: AbortController | undefined;
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  let unlinkAbort = () => {};
  let timedOut = false;

  try {
    await reserveAdmission(deadlineAt, signal);
    throwIfAborted(signal);
    const remainingMs = deadlineAt - Date.now();
    if (remainingMs <= 0) {
      throw new TimeoutError(
        `Request timeout: ${REQUEST_TIMEOUT_MS}ms`,
        REQUEST_TIMEOUT_MS,
      );
    }

    // 创建 AbortController 用于总操作截止时间控制
    controller = new AbortController();
    unlinkAbort = linkAbortSignal(signal, controller);
    timeoutId = setTimeout(() => {
      timedOut = true;
      controller?.abort();
      logger.error(
        `Request timeout after ${REQUEST_TIMEOUT_MS}ms`,
        {},
        { type: "request-timeout" },
      );
    }, remainingMs);
    return await fetchFn(controller);
  } catch (error) {
    if (signal?.aborted) {
      throw createAbortError();
    }
    if (
      timedOut &&
      error instanceof Error &&
      error.name === "AbortError"
    ) {
      throw new TimeoutError(
        `Request timeout: ${REQUEST_TIMEOUT_MS}ms`,
        REQUEST_TIMEOUT_MS,
      );
    }
    if (error instanceof TypeError) {
      throw new NetworkError("Network request failed", error);
    }
    throw error;
  } finally {
    if (timeoutId !== undefined) clearTimeout(timeoutId);
    unlinkAbort();
    controller?.abort(); // 确保 AbortController 被清理
    activeAndQueuedOperations -= 1;
  }
}

/**
 * 带重试机制的请求包装器
 */
export async function retryableFetch<T>(
  fetchFn: (context: HttpOperationContext) => Promise<T>,
  signal?: AbortSignal,
): Promise<T> {
  const operationSignal = getOperationSignal(signal);
  const deadlineAt = Date.now() + REQUEST_TIMEOUT_MS;
  return withRetry(
    () => fetchFn({ signal: operationSignal, deadlineAt }),
    {
    maxRetries: 3,
    baseDelay: 1000,
    maxDelay: 10000,
    retryableStatusCodes: [408, 429, 500, 502, 503, 504],
    retryableErrorTypes: ["NetworkError", "TimeoutError"],
    signal: operationSignal,
    deadlineAt,
    },
  );
}

/**
 * 检查当前 Cookie 是否处于登录状态。
 * 该函数不会在日志或错误信息中输出任何 Cookie 内容。
 */
export async function checkLoginStatus(): Promise<{ isLogin: boolean }> {
  const authHeaders = credentialManager.getAuthHeaders();
  const data = await fetchWithoutWBI("/x/web-interface/nav", undefined, authHeaders);
  return { isLogin: (data as { isLogin?: unknown } | undefined)?.isLogin === true };
}

/**
 * 带有 WBI 签名的 GET 请求
 */
export async function fetchWithWBI(
  path: string,
  params: Record<string, string | number>,
  additionalHeaders: Record<string, string> = {},
  signal?: AbortSignal,
): Promise<unknown> {
  const baseParams = { ...params };
  return retryableFetch(async (operation) => {
    throwIfAborted(operation.signal);
    const { mixKey } = await getWBI(operation);
    return throttledFetch(async (controller) => {
      try {
        // 添加时间戳参数（WBI 要求 Unix 秒级时间戳，不是毫秒）
        const attemptParams = {
          ...baseParams,
          timestamp: Math.floor(Date.now() / 1000),
        };

        // 生成签名
        const w_rid = generateWBISign(attemptParams, mixKey);

        // 构建 URL
        const url = new URL(path, BASE_URL);
        Object.entries({ ...attemptParams, w_rid }).forEach(([key, value]) => {
          url.searchParams.append(key, String(value));
        });

        const finalHeaders = {
          "User-Agent": config.userAgent,
          Referer: additionalHeaders.Referer || config.referer,
          Accept: "application/json",
          ...additionalHeaders,
        };

        logger.debug(
          "Sending WBI request",
          {
            url: url.toString(),
            headers: finalHeaders,
          },
          { type: "bilibili-http", operation: "fetchWithWBI" },
        );

        const response = await fetch(url.toString(), {
          headers: finalHeaders,
          redirect: "manual",
          signal: controller.signal,
        });

        if (!response.ok) {
          const errorMsg = `HTTP ${response.status}: ${response.statusText}`;
          logger.warn(
            "WBI request failed",
            {
              error: errorMsg,
              url: url.toString(),
              status: response.status,
              statusText: response.statusText,
            },
            { type: "bilibili-http", operation: "fetchWithWBI" },
          );
          throw new NetworkError(errorMsg, undefined, url.toString(), response.status);
        }

        const data = await parseBoundedJsonResponse<{
          code?: unknown;
          message?: unknown;
          data?: unknown;
        }>(
          response,
          SECURITY_LIMITS.httpJsonBytes,
          "bilibili_wbi_json",
        );

        if (data.code !== 0) {
          // Detect specific error types
          if (data.code === -101) {
            logger.warn(
              "Bilibili credentials appear expired",
              { url: url.toString(), code: data.code },
              { type: "bilibili-http", code: "COOKIE_EXPIRED" },
            );
            throw new BilibiliAPIError(
              "Current Bilibili credentials are expired or not logged in. Run \"npx -y @xzxzzx/bilibili-mcp@latest config\", then \"npx -y @xzxzzx/bilibili-mcp@latest check\", or update environment variables.",
              "COOKIE_EXPIRED",
              undefined,
              { code: data.code },
            );
          }

          if (data.code === -404 && data.message === "啥都木有") {
            logger.warn(
              "Bilibili API returned an error",
              {
                code: data.code,
                message: data.message,
                url: url.toString(),
                params: attemptParams,
              },
              { type: "bilibili-http", operation: "fetchWithWBI" },
            );
            throw new CommentsDisabledError(
              "该视频的评论功能已被禁用或限制访问",
            );
          }
          if (data.code === -403) {
            logger.warn(
              "Bilibili API returned an error",
              {
                code: data.code,
                message: data.message,
                url: url.toString(),
                params,
              },
              { type: "bilibili-http", operation: "fetchWithWBI" },
            );
            throw new BilibiliAPIError(
              "Bilibili denied access to this resource.",
              "ACCESS_DENIED",
              undefined,
              data,
            );
          }

          logger.warn(
            "Bilibili API returned an error",
            {
              code: data.code,
              message: data.message,
              url: url.toString(),
              params: attemptParams,
            },
            { type: "bilibili-http", operation: "fetchWithWBI" },
          );
          throw new BilibiliAPIError(
            "Bilibili API returned an error.",
            "API_ERROR",
            undefined,
            data,
          );
        }

        return data.data;
      } catch (error) {
        // 构建URL用于错误日志
        const tempUrl = new URL(path, BASE_URL);
        Object.entries(baseParams).forEach(([key, value]) => {
          tempUrl.searchParams.append(key, String(value));
        });

        logger.error(
          "WBI request threw",
          {
            error: error instanceof Error ? error.message : String(error),
            path,
            params: baseParams,
            url: tempUrl.toString(),
          },
          { type: "bilibili-http", operation: "fetchWithWBI" },
        );

        logger.error(
          `Error fetching ${path}`,
          { error: error instanceof Error ? error.message : error },
          { type: "fetch-error", path },
        );
        throw error;
      }
    }, operation);
  }, signal);
}

/**
 * 普通的 GET 请求（不需要 WBI 签名）
 */
export async function fetchWithoutWBI(
  path: string,
  params?: Record<string, string | number>,
  additionalHeaders: Record<string, string> = {},
  signal?: AbortSignal,
  maxResponseBytes: number = SECURITY_LIMITS.httpJsonBytes,
): Promise<unknown> {
  logger.debug(
    "fetchWithoutWBI request",
    { path, params },
    { type: "bilibili-http", operation: "fetchWithoutWBI" },
  );
  return retryableFetch(async (operation) => {
    return throttledFetch(async (controller) => {
      try {
        const url = new URL(path, BASE_URL);
        if (params) {
          Object.entries(params).forEach(([key, value]) => {
            url.searchParams.append(key, String(value));
          });
        }
        logger.debug(
          "fetchWithoutWBI URL",
          { url: url.toString() },
          { type: "bilibili-http", operation: "fetchWithoutWBI" },
        );

        const response = await fetch(url.toString(), {
          headers: {
            "User-Agent": config.userAgent,
            Referer: config.referer,
            Accept: "application/json",
            ...additionalHeaders,
          },
          redirect: "manual",
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new NetworkError(
            `HTTP ${response.status}: ${response.statusText}`,
            undefined,
            url.toString(),
            response.status,
          );
        }

        const data = await parseBoundedJsonResponse<{
          code?: unknown;
          message?: unknown;
          data?: unknown;
        }>(
          response,
          Math.min(maxResponseBytes, SECURITY_LIMITS.httpJsonBytes),
          "bilibili_plain_json",
        );

        if (data.code !== 0) {
          // Detect specific error types
          if (data.code === -101) {
            logger.warn(
              "Bilibili credentials appear expired",
              { url: url.toString(), code: data.code },
              { type: "bilibili-http", code: "COOKIE_EXPIRED" },
            );
            throw new BilibiliAPIError(
              "Current Bilibili credentials are expired or not logged in. Run \"npx -y @xzxzzx/bilibili-mcp@latest config\", then \"npx -y @xzxzzx/bilibili-mcp@latest check\", or update environment variables.",
              "COOKIE_EXPIRED",
              undefined,
              { code: data.code },
            );
          }

          if (data.code === -404 && data.message === "啥都木有") {
            throw new CommentsDisabledError(
              "该视频的评论功能已被禁用或限制访问",
            );
          }
          if (data.code === -403) {
            if (isExplicitPaidVideoDenial(path, data.message)) {
              throw new PaidVideoError(
                "该视频为付费内容，无法获取完整信息",
              );
            }
            throw new BilibiliAPIError(
              "Bilibili denied access to this resource.",
              "ACCESS_DENIED",
              undefined,
              data,
            );
          }
          throw new BilibiliAPIError(
            "Bilibili API returned an error.",
            "API_ERROR",
            undefined,
            data,
          );
        }

        return data.data;
      } catch (error) {
        logger.error(
          `Error fetching ${path}`,
          { error: error instanceof Error ? error.message : error },
          { type: "fetch-error", path },
        );
        throw error;
      }
    }, operation);
  }, signal);
}
