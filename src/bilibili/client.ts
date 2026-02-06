// B站 API 客户端，包含 WBI 签名逻辑
import { config } from '../config.js';
import { BilibiliAPIError, NetworkError, TimeoutError } from '../utils/errors.js';
import { logger } from '../utils/logger.js';
import { retryManager, withRetry } from '../utils/retry.js';
import { createHash } from 'crypto';

const BASE_URL = config.baseUrl;

// WBI 缓存
let cachedWBI: { imgKey: string; subKey: string; mixKey: string; expireTime: number } | null = null;
const CACHE_EXPIRATION_MS = config.wbiCacheExpirationMs;

// 请求限流 - 避免高频请求被 Bilibili 限制
const RATE_LIMIT_MS = config.rateLimitMs;
const REQUEST_TIMEOUT_MS = config.requestTimeoutMs;
let lastRequestTime = 0;
let pendingPromise: Promise<void> | null = null;

/**
 * 等待到下一个允许请求的时间
 */
async function waitForRateLimit(): Promise<void> {
  const now = Date.now();
  const timeSinceLastRequest = now - lastRequestTime;

  if (timeSinceLastRequest < RATE_LIMIT_MS) {
    const waitTime = RATE_LIMIT_MS - timeSinceLastRequest;
    await new Promise<void>((resolve) => setTimeout(resolve, waitTime));
  }

  lastRequestTime = Date.now();
}

/**
 * 带限流和超时控制的请求包装器
 * @param fetchFn - 执行 fetch 的函数，支持 AbortController
 * @returns Promise<T>
 */
async function throttledFetch<T>(fetchFn: (controller: AbortController) => Promise<T>): Promise<T> {
  // 等待上一个请求完成
  if (pendingPromise) {
    await pendingPromise;
  }

  // 创建 AbortController 用于超时控制
  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    controller.abort();
    logger.error(`Request timeout after ${REQUEST_TIMEOUT_MS}ms`, {}, { type: 'request-timeout' });
  }, REQUEST_TIMEOUT_MS);

  // 创建新的请求
  pendingPromise = (async () => {
    await waitForRateLimit();
  })();

  try {
    await pendingPromise;
    return await fetchFn(controller);
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new TimeoutError(`Request timeout: ${REQUEST_TIMEOUT_MS}ms`, REQUEST_TIMEOUT_MS);
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
    controller.abort(); // 确保 AbortController 被清理
    pendingPromise = null;
  }
}

/**
 * 带重试机制的请求包装器
 * @param fetchFn - 执行 fetch 的函数
 * @returns Promise<T>
 */
async function retryableFetch<T>(fetchFn: () => Promise<T>): Promise<T> {
  return withRetry(() => fetchFn(), {
    maxRetries: 3,
    baseDelay: 1000,
    maxDelay: 10000,
    retryableStatusCodes: [408, 429, 500, 502, 503, 504],
    retryableErrorTypes: ['NetworkError', 'TimeoutError', 'AbortError']
  });
}

/**
 * 生成 WBI 签名所需的混合密钥
 */
function getMixKey(imgKey: string, subKey: string): string {
  // WBI 签名使用特定的混合顺序
  const saltTable = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
  ];
  const mixKey = imgKey + subKey;
  return saltTable.map((i) => mixKey[i]).join("");
}

/**
 * 获取 WBI 签名密钥
 */
async function getWBI(): Promise<{ imgKey: string; subKey: string; mixKey: string }> {
  // 检查缓存是否有效（1小时过期）
  const now = Date.now();
  if (cachedWBI && cachedWBI.expireTime > now) {
    return { imgKey: cachedWBI.imgKey, subKey: cachedWBI.subKey, mixKey: cachedWBI.mixKey };
  }

  // 缓存已过期，会创建新的

  try {
    const result = await retryableFetch(async () => {
      // 获取 nav 数据中的 wbi_img 字段
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

      const navRes = await fetch(`${BASE_URL}/x/web-interface/nav`, {
        headers: {
          "User-Agent": config.userAgent,
          "Referer": config.referer,
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!navRes.ok) {
        throw new NetworkError(`Failed to fetch WBI: ${navRes.status}`, undefined, `${BASE_URL}/x/web-interface/nav`);
      }

      const navData = await navRes.json();
      const wbiImg = navData.data?.wbi_img;

      if (!wbiImg) {
        throw new BilibiliAPIError("WBI image data not found", 'WBI_DATA_MISSING');
      }

      // 提取 img_key 和 sub_key
      // 格式类似: img_url: https://i0.hdslb.com/bfs/wbi/2608f8a68f3141d9_2.png
      const imgKeyMatch = wbiImg.img_url?.match(/([^\/_]+)(?=\.[a-zA-Z]+$)/);
      const subKeyMatch = wbiImg.sub_url?.match(/([^\/_]+)(?=\.[a-zA-Z]+$)/);

      if (!imgKeyMatch || !subKeyMatch) {
        throw new BilibiliAPIError("Failed to extract WBI keys", 'WBI_KEY_EXTRACT_FAILED');
      }

      const imgKey = imgKeyMatch[0];
      const subKey = subKeyMatch[0];
      const mixKey = getMixKey(imgKey, subKey);

      // 缓存 WBI（1小时后过期）
      cachedWBI = {
        imgKey,
        subKey,
        mixKey,
        expireTime: now + 60 * 60 * 1000,
      };

      return { imgKey, subKey, mixKey };
    });

    return result;
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new TimeoutError(`WBI request timeout: ${REQUEST_TIMEOUT_MS}ms`, REQUEST_TIMEOUT_MS);
    }
    logger.error("Error getting WBI", { error: error instanceof Error ? error.message : error }, { type: 'wbi-error' });
    throw new NetworkError("Failed to fetch WBI", error instanceof Error ? error : undefined, `${BASE_URL}/x/web-interface/nav`);
  }
}

/**
 * 生成 WBI 签名
 */
function generateWBISign(params: Record<string, string | number>, mixKey: string): string {
  // 将参数按字典序排序
  const sortedParams = Object.keys(params)
    .sort()
    .reduce((result, key) => {
      result[key] = params[key];
      return result;
    }, {} as Record<string, string | number>);

  // 构建 query 字符串
  const queryStr = Object.entries(sortedParams)
    .map(([key, value]) => `${key}=${value}`)
    .join("&");

  // 计算 w_rid（使用 MD5 哈希）
  const strToSign = queryStr + mixKey;
  const w_rid = md5Hash(strToSign);

  return w_rid;
}

/**
 * MD5 哈希函数 - 使用 Node.js crypto 模块
 * 这是 B 站 WBI 签名算法真正需要的哈希函数
 */
function md5Hash(str: string): string {
  return createHash('md5').update(str).digest('hex');
}

/**
 * 带有 WBI 签名的 GET 请求
 */
export async function fetchWithWBI(
  path: string,
  params: Record<string, string | number>
): Promise<unknown> {
  return retryableFetch(async () => {
    return throttledFetch(async (controller) => {
      try {
        const { mixKey } = await getWBI();

        // 添加时间戳参数
        params = { ...params, timestamp: Date.now() };

        // 生成签名
        const w_rid = generateWBISign(params, mixKey);

        // 构建 URL
        const url = new URL(path, BASE_URL);
        Object.entries({ ...params, w_rid }).forEach(([key, value]) => {
          url.searchParams.append(key, String(value));
        });

        const response = await fetch(url.toString(), {
          headers: {
            "User-Agent": config.userAgent,
            "Referer": config.referer,
            "Accept": "application/json",
          },
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new NetworkError(`HTTP ${response.status}: ${response.statusText}`, undefined, url.toString());
        }

        const data = await response.json();

        if (data.code !== 0) {
          throw new BilibiliAPIError(data.message || "Unknown error", 'API_ERROR', undefined, data);
        }

        return data.data;
      } catch (error) {
        logger.error(`Error fetching ${path}`, { error: error instanceof Error ? error.message : error }, { type: 'fetch-error', path });
        throw error;
      }
    });
  });
}

/**
 * 普通的 GET 请求（不需要 WBI 签名）
 */
export async function fetchWithoutWBI(
  path: string,
  params?: Record<string, string | number>
): Promise<unknown> {
  return retryableFetch(async () => {
    return throttledFetch(async (controller) => {
      try {
        const url = new URL(path, BASE_URL);
        if (params) {
          Object.entries(params).forEach(([key, value]) => {
            url.searchParams.append(key, String(value));
          });
        }

        const response = await fetch(url.toString(), {
          headers: {
            "User-Agent": config.userAgent,
            "Referer": config.referer,
            "Accept": "application/json",
          },
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new NetworkError(`HTTP ${response.status}: ${response.statusText}`, undefined, url.toString());
        }

        const data = await response.json();

        if (data.code !== 0) {
          throw new BilibiliAPIError(data.message || "Unknown error", 'API_ERROR', undefined, data);
        }

        return data.data;
      } catch (error) {
        logger.error(`Error fetching ${path}`, { error: error instanceof Error ? error.message : error }, { type: 'fetch-error', path });
        throw error;
      }
    });
  });
}

/**
 * 获取视频基本信息
 */
export async function getVideoInfo(bvid: string) {
  return fetchWithoutWBI("/x/web-interface/view", { bvid }) as Promise<{
    title: string;
    desc: string;
    pic?: string;
    owner: { name: string; face: string };
    stat: { view: number; danmaku: number; reply: number; favorite: number; coin: number; share: number; like: number };
    cid: number;
    duration: number;
    pubdate: number;
    tag?: { tag_name: string }[];
  }>;
}

/**
 * 获取视频字幕信息
 */
export async function getVideoSubtitle(bvid: string, cid: number) {
  return fetchWithWBI("/x/player/wbi/v2", { bvid, cid }) as Promise<{
    subtitle: {
      subtitles: Array<{
        id: number;
        lan: string;
        lan_doc: string;
        subtitle_url: string;
      }>;
    };
  }>;
}

/**
 * 获取字幕内容
 */
export async function getSubtitleContent(url: string): Promise<{
  body: Array<{
    from: number;
    to: number;
    location: number;
    content: string;
  }>;
}> {
  return retryableFetch(async () => {
    return throttledFetch(async (controller) => {
      try {
        // 字幕 URL 可能是相对路径，需要补全
        const fullUrl = url.startsWith("http") ? url : `https:${url}`;

        const response = await fetch(fullUrl, {
          headers: {
            "User-Agent": config.userAgent,
            "Referer": config.referer,
          },
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new NetworkError(`HTTP ${response.status}: ${response.statusText}`, undefined, url.toString());
        }

        return await response.json();
      } catch (error) {
        logger.error("Error fetching subtitle content", { error: error instanceof Error ? error.message : error }, { type: 'subtitle-error', url });
        throw error;
      }
    });
  });
}

/**
 * 获取视频评论
 */
export async function getVideoComments(
  oid: number,
  page: number = 1,
  pageSize: number = 20
) {
  return fetchWithoutWBI("/x/v2/reply", {
    oid,
    type: "1",
    mode: "3", // 3表示按热度排序
    pagination_str: JSON.stringify({ offset: "" }),
  }) as Promise<{
    replies: Array<{
      rpid: number;
      member: { uname: string; avatar: string };
      content: { message: string };
      like: number;
      reply_control: { sub_reply_entry_text?: string; show_status?: number };
      replies?: Array<{
        member: { uname: string; avatar: string };
        content: { message: string };
        like: number;
      }>;
    }>;
    page: { num: number; size: number };
  }>;
}
