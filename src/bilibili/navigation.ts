// 共享 Part/CID 解析模块 — 所有 page 选择工具共用
import { getVideoInfo } from "./video-api.js";
import { extractBVId } from "../utils/bvid.js";
import { ValidationError } from "../utils/errors.js";
import { boundedRemoteText } from "../utils/bounded-text.js";
import type { PartInfo, RawPageEntry } from "./types.js";

/**
 * 将 Bilibili 原始 pages 条目规范化为 PartInfo 列表。
 */
export function normalizePages(rawPages: RawPageEntry[] | undefined): PartInfo[] {
  if (!rawPages || rawPages.length === 0) return [];
  return rawPages.map((p) => ({
    page: p.page,
    cid: p.cid,
    title: boundedRemoteText(p.part, 256) || `P${p.page}`,
    duration: p.duration,
  }));
}

/**
 * 根据可选 page 解析出目标 CID 和完整的 Part 列表。
 * page 为 undefined 时使用 top-level videoData.cid。
 * 接受可选的 preFetchedVideoData 以避免重复请求。
 */
export async function resolvePartCid(
  bvidOrUrl: string,
  page?: number,
  preFetchedVideoData?: Awaited<ReturnType<typeof getVideoInfo>>,
): Promise<{
  cid: number;
  pages: PartInfo[];
  videoData: Awaited<ReturnType<typeof getVideoInfo>>;
}> {
  const bvid = extractBVId(bvidOrUrl);
  const videoData = preFetchedVideoData ?? await getVideoInfo(bvid);
  const pages = normalizePages(videoData.pages);

  if (page !== undefined) {
    if (!Number.isInteger(page) || page < 1) {
      throw new ValidationError("page must be a positive integer");
    }
    const part = pages.find((p) => p.page === page);
    if (!part) {
      throw new ValidationError(
        `Page ${page} not found. Valid pages: ${pages.length > 0 ? `1-${pages.length}` : "none (single-Part video)"}`,
      );
    }
    return { cid: part.cid, pages, videoData };
  }

  return { cid: videoData.cid, pages, videoData };
}

/**
 * 在 Part 列表中匹配给定 CID 的条目，返回其 page 和 title。
 * 无匹配时返回 page=1 和 fallbackTitle。
 */
export function matchPartIdentity(
  cid: number,
  pages: PartInfo[],
  fallbackTitle: string,
): { page: number; title: string } {
  const match = pages.find((p) => p.cid === cid);
  if (match) return { page: match.page, title: match.title };
  return { page: 1, title: boundedRemoteText(fallbackTitle, 512) };
}
