// 视频元数据 wrapper
import { getVideoInfo, resolvePartCid } from "./client.js";
import { extractBVId } from "../utils/bvid.js";
import type { VideoMetadataData } from "./types.js";
import { boundedRemoteText } from "../utils/bounded-text.js";

/**
 * 获取视频元数据（不含字幕、评论），含多P pages 列表。
 */
export async function getVideoMetadataData(
  bvidOrUrl: string,
): Promise<VideoMetadataData> {
  const bvid = extractBVId(bvidOrUrl);
  const videoData = await getVideoInfo(bvid);
  const { pages } = await resolvePartCid(bvidOrUrl, undefined, videoData);

  const pubdate_timestamp = videoData.pubdate
    ? videoData.pubdate
    : undefined;
  const pubdate = pubdate_timestamp
    ? new Date(pubdate_timestamp * 1000).toISOString()
    : undefined;

  return {
    bvid,
    title: boundedRemoteText(videoData.title, 512),
    author: boundedRemoteText(videoData.owner?.name, 128) || undefined,
    duration: videoData.duration,
    pubdate,
    pubdate_timestamp,
    description: boundedRemoteText(videoData.desc, 20_000),
    tags:
      videoData.tag?.slice(0, 100).map((tag) =>
        boundedRemoteText(tag.tag_name, 128)
      ).filter(Boolean) || [],
    pages,
    stats: {
      view: videoData.stat?.view,
      like: videoData.stat?.like,
      coin: videoData.stat?.coin,
      favorite: videoData.stat?.favorite,
      share: videoData.stat?.share,
      reply: videoData.stat?.reply,
      danmaku: videoData.stat?.danmaku,
    },
  };
}
