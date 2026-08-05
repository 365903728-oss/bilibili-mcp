// Bilibili 视频章节（view_points）检索
import { getPlayerData, matchPartIdentity, resolvePartCid } from "./client.js";
import { extractBVId } from "../utils/bvid.js";
import type { ChapterInfo, VideoChaptersData } from "./types.js";
import { boundedRemoteText } from "../utils/bounded-text.js";

const MAX_CHAPTER_TITLE_BYTES = 500;

/**
 * 获取 Bilibili 提供的视频章节（进度条分段）。
 * 无章节时返回 chapters: []。
 * 播放器/网络错误向上传播，不静默吞掉。
 */
export async function getVideoChaptersData(
  bvidOrUrl: string,
  page?: number,
): Promise<VideoChaptersData> {
  const bvid = extractBVId(bvidOrUrl);
  const { cid, pages, videoData } = await resolvePartCid(bvidOrUrl, page);

  const { page: displayPage, title: displayTitle } = matchPartIdentity(cid, pages, videoData.title);

  const playerData = await getPlayerData(bvid, cid);
  const viewPoints = playerData?.view_points;
  const chapters: ChapterInfo[] = [];

  if (viewPoints && viewPoints.length > 0) {
    for (const vp of viewPoints) {
      chapters.push({
        title: boundedRemoteText(
          vp.content || vp.title,
          MAX_CHAPTER_TITLE_BYTES,
        ),
        start_seconds: vp.from,
        end_seconds: vp.to,
      });
    }
  }

  return {
    bvid,
    page: displayPage,
    cid,
    title: boundedRemoteText(displayTitle, 512),
    chapters,
  };
}
