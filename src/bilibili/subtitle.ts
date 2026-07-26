// 字幕处理逻辑
import { getVideoSubtitle, getSubtitleContent, checkLoginStatus, matchPartIdentity, resolvePartCid } from "./client.js";
import { extractBVId } from "../utils/bvid.js";
import { cacheManager } from "../utils/cache.js";
import { BilibiliAPIError, NoSubtitleError, PaidVideoError } from "../utils/errors.js";
import { logger, redactSecrets } from "../utils/logger.js";
import type {
  BilibiliSubtitleItem,
  PartInfo,
  SubtitleBodyItem,
  TranscriptMatch,
  TranscriptSearchOptions,
  VideoTranscriptData,
} from "./types.js";


export interface SubtitleData {
  data_source: "subtitle" | "description";
  video_info: {
    title: string;
    description: string;
    tags: string[];
    subtitle_text?: string;
    pubdate?: string;  // ISO 8601 格式的发布日期
    pubdate_timestamp?: number;  // Unix 时间戳
  };
}

/**
 * 字幕语言优先级
 */
const LANGUAGE_PRIORITY = ["zh-Hans", "ai-zh", "zh-CN", "zh-Hant", "en"];
const MAX_SUBTITLE_BODY_ITEMS = 5_000;
const MAX_SUBTITLE_TEXT_LENGTH = 500_000;

/**
 * 将 Unix 时间戳转换为 ISO 8601 格式日期字符串
 */
function formatPublishDate(timestamp: number): string {
  const date = new Date(timestamp * 1000); // B站返回的是秒级时间戳
  return date.toISOString();
}

/**
 * 字幕列表为空时验证登录状态，未登录则抛出 COOKIE_EXPIRED。
 */
async function verifyLoginForEmptySubtitles(bvid: string): Promise<void> {
  logger.warn(
    "Video returned no subtitles; verifying login status",
    { bvid },
    { type: "subtitle" },
  );
  const { isLogin } = await checkLoginStatus();
  if (!isLogin) {
    throw new BilibiliAPIError(
      `Video ${bvid} returned an empty subtitle list and current Bilibili credentials are not logged in. Run "npx -y @xzxzzx/bilibili-mcp@latest config", then "npx -y @xzxzzx/bilibili-mcp@latest check", or update environment variables.`,
      'COOKIE_EXPIRED',
      undefined,
      { code: -101, bvid }
    );
  }
}



/**
 * 选择最佳字幕语言
 */
function selectBestSubtitle(
  subtitles: BilibiliSubtitleItem[],
  preferredLang?: string,
): BilibiliSubtitleItem | null {
  if (!subtitles || subtitles.length === 0) {
    return null;
  }

  // 如果用户指定了偏好语言，优先使用
  if (preferredLang) {
    const preferred = subtitles.find((s) => s.lan === preferredLang || s.lan_doc.includes(preferredLang));
    if (preferred) {
      return preferred;
    }
  }

  // 按优先级选择
  for (const lang of LANGUAGE_PRIORITY) {
    const subtitle = subtitles.find((s) => s.lan === lang || s.lan.includes(lang));
    if (subtitle) {
      return subtitle;
    }
  }

  // 如果没有匹配的语言，返回第一个
  return subtitles[0];
}

/**
 * 格式化秒数为 HH:MM:SS 字符串
 */
function formatTimestamp(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

/**
 * 按时间范围过滤 Subtitle Segments。
 * start-only: segments where to >= startSeconds
 * end-only: segments where from <= endSeconds
 * both: overlap (to >= startSeconds AND from <= endSeconds)
 */
function filterSegmentsByRange(
  body: SubtitleBodyItem[],
  startSeconds?: number,
  endSeconds?: number,
): SubtitleBodyItem[] {
  return body.filter((seg) => {
    if (startSeconds !== undefined && seg.to < startSeconds) return false;
    if (endSeconds !== undefined && seg.from > endSeconds) return false;
    return true;
  });
}

/**
 * 合并字幕内容为文本
 */
function mergeSubtitleText(
  body: SubtitleBodyItem[],
  includeTimestamps?: boolean,
): string {
  if (body.length > MAX_SUBTITLE_BODY_ITEMS) {
    throw new Error("Subtitle body item count exceeds maximum limit");
  }

  const parts: string[] = [];
  let totalLength = 0;

  for (const item of body) {
    const content = item.content ?? "";
    const line = includeTimestamps
      ? `[${formatTimestamp(item.from)} --> ${formatTimestamp(item.to)}] ${content}`
      : content;
    totalLength += line.length;
    if (parts.length > 0) {
      totalLength += 1;
    }
    if (totalLength > MAX_SUBTITLE_TEXT_LENGTH) {
      throw new Error("Subtitle text exceeds maximum length");
    }
    parts.push(line);
  }

  return parts.join("\n");
}

/**
 * 在过滤后的字幕段中搜索关键词，返回 Transcript Match 列表和紧凑 transcript。
 */
function searchTranscript(
  body: SubtitleBodyItem[],
  query: string,
  maxMatches: number,
  contextSegments: number,
  sourceUrl: string,
): {
  matches: TranscriptMatch[];
  totalMatches: number;
  compactTranscript: string;
} {
  if (body.length > MAX_SUBTITLE_BODY_ITEMS) {
    throw new Error("Subtitle body item count exceeds maximum limit");
  }

  const lowerQuery = query.toLowerCase();
  const matchIndices: number[] = [];
  for (let i = 0; i < body.length; i++) {
    if (body[i].content.toLowerCase().includes(lowerQuery)) {
      matchIndices.push(i);
    }
  }

  const totalMatches = matchIndices.length;
  const limited = matchIndices.slice(0, maxMatches);

  const matches: TranscriptMatch[] = [];
  const contextIndices = new Set<number>();

  for (const idx of limited) {
    const hit = body[idx];
    const start = Math.max(0, idx - contextSegments);
    const end = Math.min(body.length - 1, idx + contextSegments);

    for (let j = start; j <= end; j++) {
      contextIndices.add(j);
    }

    const timestampUrl = new URL(sourceUrl);
    timestampUrl.searchParams.set("t", String(hit.from));

    matches.push({
      start_seconds: hit.from,
      end_seconds: hit.to,
      content: hit.content,
      context: mergeSubtitleText(body.slice(start, end + 1), true),
      timestamp_url: timestampUrl.toString(),
    });
  }

  const sortedIndices = [...contextIndices].sort((a, b) => a - b);
  const compactBody = sortedIndices.map((idx) => body[idx]);

  return {
    matches,
    totalMatches,
    compactTranscript: mergeSubtitleText(compactBody, true),
  };
}

/**
 * 构建 Part-aware Bilibili 浏览器源 URL。
 * 单 P 视频不附加 `p`；多 P 视频附加 `p=<resolved page>`。
 * 保留 extractBVId 返回的精确大小写。
 */
function buildTranscriptSourceUrl(
  bvid: string,
  pages: PartInfo[],
  resolvedPage: number,
): string {
  const url = new URL(`https://www.bilibili.com/video/${bvid}/`);
  if (pages.length > 1) {
    url.searchParams.set("p", String(resolvedPage));
  }
  return url.toString();
}

/**
 * 获取纯视频转录文本
 *
 * 不自动降级到描述。如果字幕不可用：
 * - fallbackToDescription=false -> throw NoSubtitleError
 * - fallbackToDescription=true -> return description text
 * - COOKIE_EXPIRED 错误始终向上传播
 * - 当 timestamps 或 range 被请求时，拒绝 description fallback
 * - searchOptions 存在时拒绝 description fallback，只搜索真实字幕
 */
export async function getVideoTranscriptData(
  bvidOrUrl: string,
  preferredLang?: string,
  fallbackToDescription?: boolean,
  page?: number,
  includeTimestamps?: boolean,
  startSeconds?: number,
  endSeconds?: number,
  searchOptions?: TranscriptSearchOptions,
): Promise<VideoTranscriptData> {
  const bvid = extractBVId(bvidOrUrl);
  const wantsTimedOutput = includeTimestamps || startSeconds !== undefined || endSeconds !== undefined;
  const wantsSearch = searchOptions !== undefined;
  const { cid, pages, videoData } = await resolvePartCid(bvidOrUrl, page);
  const title = videoData.title;
  const description = videoData.desc || "";
  const resolvedPage = page ?? matchPartIdentity(videoData.cid, pages, videoData.title).page;
  const sourceUrl = buildTranscriptSourceUrl(bvid, pages, resolvedPage);

  // 获取字幕列表
  try {
    const subtitleData = await getVideoSubtitle(bvid, cid);

    if (
      !subtitleData?.subtitle?.subtitles ||
      subtitleData.subtitle.subtitles.length === 0
    ) {
      await verifyLoginForEmptySubtitles(bvid);
      if (fallbackToDescription && !wantsSearch) {
        if (wantsTimedOutput) {
          throw new NoSubtitleError(
            `Video ${bvid} has no subtitles available; description fallback is incompatible with timestamps or range`,
          );
        }
        return {
          bvid,
          data_source: "description",
          transcript: description,
          title,
          source_url: sourceUrl,
          page: resolvedPage,
        };
      }
      throw new NoSubtitleError(
        `Video ${bvid} has no subtitles available`,
      );
    }

    const bestSubtitle = selectBestSubtitle(
      subtitleData.subtitle.subtitles,
      preferredLang,
    );

    if (!bestSubtitle) {
      if (fallbackToDescription && !wantsSearch) {
        if (wantsTimedOutput) {
          throw new NoSubtitleError(
            `No suitable subtitle found for video ${bvid}; description fallback is incompatible with timestamps or range`,
          );
        }
        return {
          bvid,
          data_source: "description",
          transcript: description,
          title,
          source_url: sourceUrl,
          page: resolvedPage,
        };
      }
      throw new NoSubtitleError(
        `No suitable subtitle found for video ${bvid}`,
      );
    }

    const subtitleContent = await getSubtitleContent(
      bestSubtitle.subtitle_url,
    );

    if (!subtitleContent?.body || subtitleContent.body.length === 0) {
      if (fallbackToDescription && !wantsSearch) {
        if (wantsTimedOutput) {
          throw new NoSubtitleError(
            `Subtitle body is empty for video ${bvid}; description fallback is incompatible with timestamps or range`,
          );
        }
        return {
          bvid,
          data_source: "description",
          transcript: description,
          title,
          source_url: sourceUrl,
          page: resolvedPage,
        };
      }
      throw new NoSubtitleError(
        `Subtitle body is empty for video ${bvid}`,
      );
    }

    const body = filterSegmentsByRange(subtitleContent.body, startSeconds, endSeconds);

    if (wantsSearch) {
      const { query, max_matches, context_segments } = searchOptions!;
      const { matches, totalMatches, compactTranscript } = searchTranscript(
        body,
        query,
        max_matches,
        context_segments,
        sourceUrl,
      );

      return {
        bvid,
        data_source: "subtitle",
        language: bestSubtitle.lan,
        transcript: compactTranscript,
        title,
        source_url: sourceUrl,
        page: resolvedPage,
        query,
        total_matches: totalMatches,
        returned_matches: matches.length,
        truncated: totalMatches > max_matches,
        matches,
      };
    }

    const transcript = mergeSubtitleText(body, includeTimestamps);

    return {
      bvid,
      data_source: "subtitle",
      language: bestSubtitle.lan,
      transcript,
      title,
      source_url: sourceUrl,
      page: resolvedPage,
    };
  } catch (error) {
    // COOKIE_EXPIRED must propagate
    if (
      error instanceof BilibiliAPIError &&
      error.code === "COOKIE_EXPIRED"
    ) {
      throw error;
    }
    // NoSubtitleError: only rethrow if fallback disabled
    if (error instanceof NoSubtitleError) {
      if (!fallbackToDescription || wantsSearch) throw error;
      if (wantsTimedOutput) throw error;
      return {
        bvid,
        data_source: "description",
        transcript: description,
        title,
        source_url: sourceUrl,
        page: resolvedPage,
      };
    }
    // Other errors: fallback to description if enabled, else rethrow
    if (fallbackToDescription && !wantsSearch) {
      if (wantsTimedOutput) {
        throw new NoSubtitleError(
          `Subtitle fetch failed for video ${bvid}; description fallback is incompatible with timestamps or range`,
        );
      }
      return {
        bvid,
        data_source: "description",
        transcript: description,
        title,
        source_url: sourceUrl,
        page: resolvedPage,
      };
    }
    throw error;
  }
}

/**
 * 获取视频信息及字幕
 */
export async function getVideoInfoWithSubtitle(
  bvidOrUrl: string,
  preferredLang?: string,
  page?: number,
): Promise<SubtitleData> {
  try {
    const bvid = extractBVId(bvidOrUrl);

    // 生成缓存键（包含 page）— 在 resolvePartCid 之前检查以避免网络请求
    const cacheKey = cacheManager.generateKey('video', bvid, preferredLang, page);
    const cachedData = cacheManager.getVideoInfo(cacheKey) as SubtitleData | undefined;
    if (cachedData) {
      logger.debug("Video cache hit", { bvid, cacheKey }, { type: "subtitle" });
      return cachedData;
    }

    logger.debug("Video cache miss", { bvid, cacheKey }, { type: "subtitle" });

    const { cid, videoData } = await resolvePartCid(bvidOrUrl, page);

    const title = videoData.title;
    const description = videoData.desc || "";
    const tags = (videoData.tag || []).map((t) => t.tag_name);
    const pubdate = videoData.pubdate;
    const formattedDate = pubdate ? formatPublishDate(pubdate) : undefined;

    // 尝试获取字幕
    try {
      const subtitleData = await getVideoSubtitle(bvid, cid);

      if (!subtitleData?.subtitle?.subtitles || subtitleData.subtitle.subtitles.length === 0) {
        await verifyLoginForEmptySubtitles(bvid);

        // 已登录但视频本身无字幕，使用简介降级
        logger.info(
          "Video has no subtitles while credentials are logged in",
          { bvid },
          { type: "subtitle" },
        );

        const result: SubtitleData = {
          data_source: "description",
          video_info: {
            title,
            description: description || "该视频没有可用的简介",
            tags: tags.length > 0 ? tags : ["无标签"],
            pubdate: formattedDate,
            pubdate_timestamp: pubdate,
          },
        };
        // 不缓存无字幕结果，以便下次重试时能拉取最新生成的字幕
        logger.debug(
          "Not caching fallback result to allow future retries",
          { bvid },
          { type: "subtitle" },
        );
        return result;
      }

      // 选择最佳字幕
      const bestSubtitle = selectBestSubtitle(subtitleData.subtitle.subtitles, preferredLang);

      if (!bestSubtitle) {
        const result: SubtitleData = {
          data_source: "description",
          video_info: {
            title,
            description: description || "该视频没有可用的简介",
            tags: tags.length > 0 ? tags : ["无标签"],
            pubdate: formattedDate,
            pubdate_timestamp: pubdate,
          },
        };
        // 不缓存无字幕结果，以便下次重试时能拉取最新生成的字幕
        logger.debug(
          "Not caching fallback result to allow future retries",
          { bvid },
          { type: "subtitle" },
        );
        return result;
      }

      // 获取字幕内容
      const subtitleContent = await getSubtitleContent(bestSubtitle.subtitle_url);

      if (!subtitleContent?.body || subtitleContent.body.length === 0) {
        const result: SubtitleData = {
          data_source: "description",
          video_info: {
            title,
            description: description || "该视频没有可用的简介",
            tags: tags.length > 0 ? tags : ["无标签"],
            pubdate: formattedDate,
            pubdate_timestamp: pubdate,
          },
        };
        // 不缓存无字幕结果，以便下次重试时能拉取最新生成的字幕
        logger.debug(
          "Not caching fallback result to allow future retries",
          { bvid },
          { type: "subtitle" },
        );
        return result;
      }

      // 合并字幕文本
      const subtitleText = mergeSubtitleText(subtitleContent.body);

      const result: SubtitleData = {
        data_source: "subtitle",
        video_info: {
          title,
          description,
          tags,
          subtitle_text: subtitleText,
          pubdate: formattedDate,
          pubdate_timestamp: pubdate,
        },
      };
      // 存入缓存
      cacheManager.setVideoInfo(cacheKey, result);
      return result;
    } catch (error) {
      // COOKIE_EXPIRED 错误必须向上传播，不能静默降级
      if (error instanceof BilibiliAPIError && error.code === 'COOKIE_EXPIRED') {
        throw error;
      }
      // 其他字幕获取失败，使用简介作为降级方案
      logger.warn(
        "Failed to fetch subtitles, using description fallback",
        { bvid, error: error instanceof Error ? error.message : error },
        { type: "subtitle" },
      );

      const result: SubtitleData = {
        data_source: "description",
        video_info: {
          title,
          description: description || "该视频没有可用的简介",
          tags: tags.length > 0 ? tags : ["无标签"],
          pubdate: formattedDate,
          pubdate_timestamp: pubdate,
        },
      };
      // 不缓存降级结果，以便下次重试时能拉取字幕
      return result;
    }
  } catch (error) {
    logger.error(
      "Error getting video info with subtitle",
      { error: redactSecrets(error) },
      { type: "subtitle" },
    );
    throw error;
  }
}
