// 字幕处理逻辑
import { getVideoInfo, getVideoSubtitle, getSubtitleContent } from "./client.js";

export interface SubtitleData {
  data_source: "subtitle" | "description";
  video_info: {
    title: string;
    description: string;
    tags: string[];
    subtitle_text?: string;
  };
}

/**
 * 字幕语言优先级
 */
const LANGUAGE_PRIORITY = ["zh-Hans", "zh-CN", "zh-Hant", "en"];

/**
 * 从 BV 号或 URL 中提取 BV 号
 */
function extractBVId(input: string): string {
  // 匹配 BV 号格式：BV1xx4x1x7xx 或类似格式
  const match = input.match(/(BV[a-zA-Z0-9]{10})/);
  if (!match) {
    throw new Error("Invalid Bilibili video ID or URL");
  }
  return match[1];
}

/**
 * 选择最佳字幕语言
 */
function selectBestSubtitle(
  subtitles: Array<{ id: number; lan: string; lan_doc: string; subtitle_url: string }>,
  preferredLang?: string
): { id: number; lan: string; lan_doc: string; subtitle_url: string } | null {
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
 * 合并字幕内容为文本
 */
function mergeSubtitleText(
  body: Array<{ from: number; to: number; content: string }>
): string {
  return body.map((item) => item.content).join("\n");
}

/**
 * 提取视频标签
 */
function extractTags(videoData: any): string[] {
  const tags = videoData.tag || [];
  return tags.map((tag: { tag_name: string }) => tag.tag_name);
}

/**
 * 获取视频信息及字幕
 */
export async function getVideoInfoWithSubtitle(
  bvidOrUrl: string,
  preferredLang?: string
): Promise<SubtitleData> {
  try {
    const bvid = extractBVId(bvidOrUrl);

    // 获取视频基本信息
    const videoData = await getVideoInfo(bvid);

    const title = videoData.title;
    const description = videoData.desc;
    const tags = extractTags(videoData);
    const cid = videoData.cid;

    // 尝试获取字幕
    try {
      const subtitleData = await getVideoSubtitle(bvid, cid);

      if (!subtitleData?.subtitle?.subtitles || subtitleData.subtitle.subtitles.length === 0) {
        // 没有字幕，使用简介作为降级方案
        console.error(`No subtitles available for video ${bvid}`);
        return {
          data_source: "description",
          video_info: {
            title,
            description,
            tags,
          },
        };
      }

      // 选择最佳字幕
      const bestSubtitle = selectBestSubtitle(subtitleData.subtitle.subtitles, preferredLang);

      if (!bestSubtitle) {
        return {
          data_source: "description",
          video_info: {
            title,
            description,
            tags,
          },
        };
      }

      // 获取字幕内容
      const subtitleContent = await getSubtitleContent(bestSubtitle.subtitle_url);

      if (!subtitleContent?.body || subtitleContent.body.length === 0) {
        return {
          data_source: "description",
          video_info: {
            title,
            description,
            tags,
          },
        };
      }

      // 合并字幕文本
      const subtitleText = mergeSubtitleText(subtitleContent.body);

      return {
        data_source: "subtitle",
        video_info: {
          title,
          description,
          tags,
          subtitle_text: subtitleText,
        },
      };
    } catch (error) {
      // 获取字幕失败，使用简介作为降级方案
      console.error(`Failed to fetch subtitles for video ${bvid}, using description as fallback:`, error);
      return {
        data_source: "description",
        video_info: {
          title,
          description,
          tags,
        },
      };
    }
  } catch (error) {
    console.error("Error getting video info with subtitle:", error);
    throw error;
  }
}
