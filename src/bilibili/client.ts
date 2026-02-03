// B站 API 客户端，包含 WBI 签名逻辑

const BASE_URL = "https://api.bilibili.com";

// WBI 缓存
let cachedWBI: { imgKey: string; subKey: string; mixKey: string; expireTime: number } | null = null;

// 请求限流 - 避免高频请求被 Bilibili 限制
const RATE_LIMIT_MS = 500; // 请求间隔 500ms
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
 * 带限流的请求包装器
 */
async function throttledFetch<T>(fetchFn: () => Promise<T>): Promise<T> {
  // 等待上一个请求完成
  if (pendingPromise) {
    await pendingPromise;
  }

  // 创建新的请求
  pendingPromise = (async () => {
    await waitForRateLimit();
  })();

  try {
    await pendingPromise;
    return await fetchFn();
  } finally {
    pendingPromise = null;
  }
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

  try {
    // 获取 nav 数据中的 wbi_img 字段
    const navRes = await fetch(`${BASE_URL}/x/web-interface/nav`, {
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.bilibili.com",
      },
    });

    if (!navRes.ok) {
      throw new Error(`Failed to fetch WBI: ${navRes.status}`);
    }

    const navData = await navRes.json();
    const wbiImg = navData.data?.wbi_img;

    if (!wbiImg) {
      throw new Error("WBI image data not found");
    }

    // 提取 img_key 和 sub_key
    // 格式类似: img_url: https://i0.hdslb.com/bfs/wbi/2608f8a68f3141d9_2.jpg
    const imgKeyMatch = wbiImg.img_url?.match(/([^\/_]+)(?=\.jpg)/);
    const subKeyMatch = wbiImg.sub_url?.match(/([^\/_]+)(?=\.jpg)/);

    if (!imgKeyMatch || !subKeyMatch) {
      throw new Error("Failed to extract WBI keys");
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
  } catch (error) {
    console.error("Error getting WBI:", error);
    throw error;
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

  // 计算 w_rid
  const strToSign = queryStr + mixKey;
  const w_rid = simpleHash(strToSign);

  return w_rid;
}

/**
 * 简单哈希函数（模拟 B站的哈希算法）
 */
function simpleHash(str: string): string {
  // 使用 Web Crypto API 的 MD5 或简单的自定义哈希
  // 这里使用一个简化的实现
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return Math.abs(hash).toString(16).padStart(8, "0");
}

/**
 * 带有 WBI 签名的 GET 请求
 */
export async function fetchWithWBI(
  path: string,
  params: Record<string, string | number>
): Promise<unknown> {
  return throttledFetch(async () => {
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
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
          "Referer": "https://www.bilibili.com",
          "Accept": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      if (data.code !== 0) {
        throw new Error(`API Error: ${data.message || "Unknown error"}`);
      }

      return data.data;
    } catch (error) {
      console.error(`Error fetching ${path}:`, error);
      throw error;
    }
  });
}

/**
 * 普通的 GET 请求（不需要 WBI 签名）
 */
export async function fetchWithoutWBI(
  path: string,
  params?: Record<string, string | number>
): Promise<unknown> {
  return throttledFetch(async () => {
    try {
      const url = new URL(path, BASE_URL);
      if (params) {
        Object.entries(params).forEach(([key, value]) => {
          url.searchParams.append(key, String(value));
        });
      }

      const response = await fetch(url.toString(), {
        headers: {
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
          "Referer": "https://www.bilibili.com",
          "Accept": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      if (data.code !== 0) {
        throw new Error(`API Error: ${data.message || "Unknown error"}`);
      }

      return data.data;
    } catch (error) {
      console.error(`Error fetching ${path}:`, error);
      throw error;
    }
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
  return throttledFetch(async () => {
    try {
      // 字幕 URL 可能是相对路径，需要补全
      const fullUrl = url.startsWith("http") ? url : `https:${url}`;

      const response = await fetch(fullUrl, {
        headers: {
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
          "Referer": "https://www.bilibili.com",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Error fetching subtitle content:", error);
      throw error;
    }
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
