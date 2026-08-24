// B站 视频/字幕 API
import { config } from "../config.js";
import { credentialManager } from "../utils/credentials.js";
import {
  NetworkError,
  ResourceLimitError,
  UpstreamResponseError,
  ValidationError,
} from "../utils/errors.js";
import { logger } from "../utils/logger.js";
import {
  boundedFiniteInteger,
  boundedRemoteText,
  sanitizeRemoteText,
} from "../utils/bounded-text.js";
import { getBuvid } from "./fingerprint.js";
import {
  fetchWithWBI,
  fetchWithoutWBI,
  retryableFetch,
  throttledFetch,
} from "./http.js";

const MAX_SUBTITLE_RESPONSE_BYTES = 1_000_000;

import type { RawPageEntry } from "./types.js";

const MAX_VIDEO_PAGES = 1_000;
const MAX_VIDEO_TAGS = 100;
const MAX_PLAYER_CHAPTERS = 200;

type SubtitleResponse = {
  subtitle: {
    subtitles: Array<{
      id: number;
      lan: string;
      lan_doc: string;
      subtitle_url: string;
    }>;
  };
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseVideoInfoResponse(raw: unknown): {
  title: string;
  desc: string;
  pic?: string;
  owner: { name: string; face: string };
  stat: {
    view: number;
    danmaku: number;
    reply: number;
    favorite: number;
    coin: number;
    share: number;
    like: number;
  };
  cid: number;
  aid: number;
  duration: number;
  pubdate: number;
  pages?: RawPageEntry[];
  tag?: { tag_name: string }[];
} {
  if (!isRecord(raw)) {
    throw new UpstreamResponseError("Bilibili returned invalid video metadata");
  }
  const owner = isRecord(raw.owner) ? raw.owner : {};
  const stat = isRecord(raw.stat) ? raw.stat : {};
  const title = boundedRemoteText(raw.title, 512);
  if (!title || !Number.isSafeInteger(raw.cid) || (raw.cid as number) <= 0) {
    throw new UpstreamResponseError("Bilibili returned invalid video metadata");
  }
  if (!Number.isSafeInteger(raw.aid) || (raw.aid as number) <= 0) {
    throw new UpstreamResponseError("Bilibili returned invalid video metadata");
  }

  let pages: RawPageEntry[] | undefined;
  if (raw.pages !== undefined) {
    if (!Array.isArray(raw.pages)) {
      throw new UpstreamResponseError("Bilibili returned invalid Part metadata");
    }
    if (raw.pages.length > MAX_VIDEO_PAGES) {
      throw new ResourceLimitError(
        "Video Part list exceeded its item limit",
        "video_parts",
        MAX_VIDEO_PAGES,
      );
    }
    pages = raw.pages.map((entry) => {
      if (
        !isRecord(entry) ||
        !Number.isSafeInteger(entry.cid) ||
        (entry.cid as number) <= 0 ||
        !Number.isSafeInteger(entry.page) ||
        (entry.page as number) <= 0 ||
        typeof entry.duration !== "number" ||
        !Number.isFinite(entry.duration) ||
        entry.duration <= 0
      ) {
        throw new UpstreamResponseError(
          "Bilibili returned invalid Part metadata",
        );
      }
      return {
        cid: entry.cid as number,
        page: entry.page as number,
        part: boundedRemoteText(entry.part, 256),
        duration: entry.duration,
      };
    });
  }

  let tag: { tag_name: string }[] | undefined;
  if (raw.tag !== undefined) {
    if (!Array.isArray(raw.tag)) {
      throw new UpstreamResponseError("Bilibili returned invalid tag metadata");
    }
    if (raw.tag.length > MAX_VIDEO_TAGS) {
      throw new ResourceLimitError(
        "Video tag list exceeded its item limit",
        "video_tags",
        MAX_VIDEO_TAGS,
      );
    }
    tag = raw.tag
      .filter(isRecord)
      .map((entry) => ({ tag_name: boundedRemoteText(entry.tag_name, 128) }))
      .filter((entry) => entry.tag_name.length > 0);
  }

  return {
    title,
    desc: boundedRemoteText(raw.desc, 20_000),
    pic: boundedRemoteText(raw.pic, 2_048) || undefined,
    owner: {
      name: boundedRemoteText(owner.name, 128),
      face: boundedRemoteText(owner.face, 2_048),
    },
    stat: {
      view: boundedFiniteInteger(stat.view),
      danmaku: boundedFiniteInteger(stat.danmaku),
      reply: boundedFiniteInteger(stat.reply),
      favorite: boundedFiniteInteger(stat.favorite),
      coin: boundedFiniteInteger(stat.coin),
      share: boundedFiniteInteger(stat.share),
      like: boundedFiniteInteger(stat.like),
    },
    cid: raw.cid as number,
    aid: raw.aid as number,
    duration:
      typeof raw.duration === "number" &&
      Number.isFinite(raw.duration) &&
      raw.duration > 0
        ? raw.duration
        : 0,
    pubdate: boundedFiniteInteger(raw.pubdate),
    pages,
    tag,
  };
}

function parseSubtitleResponse(raw: unknown): SubtitleResponse {
  if (!isRecord(raw) || !isRecord(raw.subtitle)) {
    throw new NetworkError("Bilibili returned invalid subtitle metadata");
  }
  const rows = raw.subtitle.subtitles;
  if (!Array.isArray(rows) || rows.length > 100) {
    throw new NetworkError("Bilibili returned invalid subtitle metadata");
  }
  const subtitles: SubtitleResponse["subtitle"]["subtitles"] = [];
  for (const row of rows) {
    if (
      !isRecord(row) ||
      typeof row.id !== "number" ||
      !Number.isInteger(row.id) ||
      row.id < 0 ||
      typeof row.lan !== "string" ||
      row.lan.length < 1 ||
      row.lan.length > 64 ||
      typeof row.lan_doc !== "string" ||
      row.lan_doc.length > 128 ||
      typeof row.subtitle_url !== "string" ||
      row.subtitle_url.length < 1 ||
      row.subtitle_url.length > 8_192
    ) {
      throw new NetworkError("Bilibili returned invalid subtitle metadata");
    }
    subtitles.push({
      id: row.id,
      lan: row.lan,
      lan_doc: row.lan_doc,
      subtitle_url: row.subtitle_url,
    });
  }
  return { subtitle: { subtitles } };
}

function parseSubtitleContent(raw: unknown): {
  body: Array<{
    from: number;
    to: number;
    location: number;
    content: string;
  }>;
} {
  if (!isRecord(raw) || !Array.isArray(raw.body) || raw.body.length > 5_000) {
    throw new NetworkError("Bilibili returned invalid subtitle content");
  }
  let totalCharacters = 0;
  const body: Array<{
    from: number;
    to: number;
    location: number;
    content: string;
  }> = [];
  for (const row of raw.body) {
    if (
      !isRecord(row) ||
      typeof row.from !== "number" ||
      !Number.isFinite(row.from) ||
      row.from < 0 ||
      typeof row.to !== "number" ||
      !Number.isFinite(row.to) ||
      row.to < row.from ||
      typeof row.content !== "string" ||
      row.content.length > 10_000
    ) {
      throw new NetworkError("Bilibili returned invalid subtitle content");
    }
    totalCharacters += row.content.length;
    if (totalCharacters > 500_000) {
      throw new NetworkError("Bilibili returned invalid subtitle content");
    }
    body.push({
      from: row.from,
      to: row.to,
      location:
        typeof row.location === "number" && Number.isFinite(row.location)
          ? row.location
          : 0,
      content: sanitizeRemoteText(row.content),
    });
  }
  return { body };
}

/**
 * 获取视频基本信息（含多P pages）
 */
export async function getVideoInfo(bvid: string) {
  return parseVideoInfoResponse(
    await fetchWithoutWBI("/x/web-interface/view", { bvid }),
  );
}

/**
 * 获取视频字幕信息
 *
 * 策略：优先使用带 WBI 签名的 /x/player/wbi/v2 接口。
 * 若该接口返回空字幕或 HTTP 412（部分环境下的登录态风控），
 * 自动降级到 /x/player/v2 重试一次。
 */
export async function getVideoSubtitle(bvid: string, cid: number) {
  const authHeaders = credentialManager.getAuthHeaders();

  // 获取 buvid 指纹 Cookie，规避 B站近期将 -352 风控扩展到播放器接口的问题
  const buvidFingerprint = await getBuvid();
  const headersWithBuvid: Record<string, string> = { ...authHeaders };
  if (buvidFingerprint) {
    const existingCookie = headersWithBuvid["Cookie"] || "";
    const buvidCookie = `buvid3=${buvidFingerprint.buvid3}; buvid4=${buvidFingerprint.buvid4}`;
    headersWithBuvid["Cookie"] = existingCookie
      ? `${existingCookie}; ${buvidCookie}`
      : buvidCookie;
  }

  // 第一次尝试：WBI 签名接口
  let wbiResult: SubtitleResponse | undefined;
  try {
    wbiResult = parseSubtitleResponse(await fetchWithWBI(
      "/x/player/wbi/v2",
      { bvid, cid },
      headersWithBuvid,
    ));
  } catch (error) {
    if (!(error instanceof NetworkError && error.statusCode === 412)) {
      throw error;
    }
    logger.warn(
      "WBI subtitle API returned HTTP 412, falling back to /x/player/v2",
      { bvid, cid },
      { type: "video-api", operation: "getVideoSubtitle" },
    );
  }

  if (
    wbiResult?.subtitle?.subtitles &&
    wbiResult.subtitle.subtitles.length > 0
  ) {
    return wbiResult;
  }

  if (wbiResult) {
    logger.debug(
      "WBI subtitle API returned empty subtitles, falling back to /x/player/v2",
      { bvid, cid },
      { type: "video-api", operation: "getVideoSubtitle" },
    );
  }
  const fallbackResult = parseSubtitleResponse(await fetchWithoutWBI(
    "/x/player/v2",
    { bvid, cid },
    headersWithBuvid,
  ));

  if (
    fallbackResult?.subtitle?.subtitles &&
    fallbackResult.subtitle.subtitles.length > 0
  ) {
    logger.info(
      "Subtitle fallback succeeded",
      { bvid, cid, subtitleCount: fallbackResult.subtitle.subtitles.length },
      { type: "video-api", operation: "getVideoSubtitle" },
    );
  } else {
    logger.info(
      "Subtitle fallback also returned no subtitles",
      { bvid, cid },
      { type: "video-api", operation: "getVideoSubtitle" },
    );
  }

  return fallbackResult;
}

/**
 * 获取播放器数据（用于章节等不需要字幕的场景）
 */
export async function getPlayerData(bvid: string, cid: number): Promise<{
  view_points?: Array<{
    content?: string;
    title?: string;
    from: number;
    to: number;
  }>;
}> {
  const authHeaders = credentialManager.getAuthHeaders();
  const buvidFingerprint = await getBuvid();
  const headers: Record<string, string> = { ...authHeaders };
  if (buvidFingerprint) {
    const existingCookie = headers["Cookie"] || "";
    const buvidCookie = `buvid3=${buvidFingerprint.buvid3}; buvid4=${buvidFingerprint.buvid4}`;
    headers["Cookie"] = existingCookie ? `${existingCookie}; ${buvidCookie}` : buvidCookie;
  }

  const raw = await fetchWithoutWBI("/x/player/v2", { bvid, cid }, headers);
  if (!isRecord(raw)) {
    throw new UpstreamResponseError("Bilibili returned invalid player metadata");
  }
  if (raw.view_points === undefined) return {};
  if (!Array.isArray(raw.view_points)) {
    throw new UpstreamResponseError("Bilibili returned invalid chapter metadata");
  }
  if (raw.view_points.length > MAX_PLAYER_CHAPTERS) {
    throw new ResourceLimitError(
      "Video chapter list exceeded its item limit",
      "video_chapters",
      MAX_PLAYER_CHAPTERS,
    );
  }
  return {
    view_points: raw.view_points.map((entry) => {
      if (
        !isRecord(entry) ||
        typeof entry.from !== "number" ||
        !Number.isFinite(entry.from) ||
        entry.from < 0 ||
        typeof entry.to !== "number" ||
        !Number.isFinite(entry.to) ||
        entry.to < entry.from
      ) {
        throw new UpstreamResponseError(
          "Bilibili returned invalid chapter metadata",
        );
      }
      return {
        content: boundedRemoteText(entry.content, 500),
        title: boundedRemoteText(entry.title, 500),
        from: entry.from,
        to: entry.to,
      };
    }),
  };
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
  const allowedSubtitleHosts = new Set([
    "aisubtitle.hdslb.com",
    "subtitle.bilibili.com",
  ]);
  const fullUrl = new URL(url, "https://www.bilibili.com");
  if (
    fullUrl.protocol !== "https:" ||
    !allowedSubtitleHosts.has(fullUrl.hostname)
  ) {
    throw new ValidationError(
      "Unsupported subtitle URL host",
    );
  }
  if (
    fullUrl.port !== "" ||
    fullUrl.username !== "" ||
    fullUrl.password !== ""
  ) {
    throw new ValidationError(
      "Unsupported subtitle URL port or userinfo",
    );
  }

  async function readSubtitleResponse(response: Response): Promise<string> {
    const contentLength = response.headers.get("content-length");
    if (
      contentLength !== null &&
      Number.isFinite(Number(contentLength)) &&
      Number(contentLength) > MAX_SUBTITLE_RESPONSE_BYTES
    ) {
      throw new ValidationError("Subtitle response is too large");
    }

    if (!response.body) {
      const text = await response.text();
      if (new TextEncoder().encode(text).byteLength > MAX_SUBTITLE_RESPONSE_BYTES) {
        throw new ValidationError("Subtitle response is too large");
      }
      return text;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const chunks: string[] = [];
    let receivedBytes = 0;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      receivedBytes += value.byteLength;
      if (receivedBytes > MAX_SUBTITLE_RESPONSE_BYTES) {
        await reader.cancel();
        throw new ValidationError("Subtitle response is too large");
      }
      chunks.push(decoder.decode(value, { stream: true }));
    }

    chunks.push(decoder.decode());
    return chunks.join("");
  }

  return retryableFetch(async () => {
    return throttledFetch(async (controller) => {
      try {
        const response = await fetch(fullUrl.toString(), {
          headers: {
            "User-Agent": config.userAgent,
            Referer: config.referer,
          },
          redirect: "manual",
          signal: controller.signal,
        });

        if (response.status >= 300 && response.status < 400) {
          throw new ValidationError("Unsupported subtitle URL redirect");
        }

        if (!response.ok) {
          throw new NetworkError(
            `HTTP ${response.status}: ${response.statusText}`,
            undefined,
            url.toString(),
            response.status,
          );
        }

        const responseText = await readSubtitleResponse(response);
        let parsed: unknown;
        try {
          parsed = JSON.parse(responseText);
        } catch {
          throw new NetworkError("Bilibili returned invalid subtitle content");
        }
        return parseSubtitleContent(parsed);
      } catch (error) {
        logger.error(
          "Error fetching subtitle content",
          { error: error instanceof Error ? error.name : "UnknownError" },
          { type: "subtitle-error" },
        );
        throw error;
      }
    });
  });
}
