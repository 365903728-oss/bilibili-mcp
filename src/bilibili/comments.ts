// 评论处理逻辑
import { getVideoComments } from "./client.js";
import {
  Comment,
  CommentOptions,
  ProcessedComment,
  CommentDetailLevel,
} from "./types.js";
import { extractBVId } from "../utils/bvid.js";
import { cacheManager } from "../utils/cache.js";
import {
  CommentsDisabledError,
  ResourceLimitError,
  UpstreamResponseError,
} from "../utils/errors.js";
import { logger, redactSecrets } from "../utils/logger.js";
import { SECURITY_LIMITS, utf8ByteLength } from "../security/limits.js";
import {
  boundedFiniteInteger,
  boundedRemoteText,
} from "../utils/bounded-text.js";

export interface CommentData {
  comments: ProcessedComment[];
  summary: {
    total_comments: number;
    comments_with_timestamp: number;
  };
}

const MAX_COMMENT_AUTHOR_BYTES = 128;
const MAX_COMMENT_MESSAGE_BYTES = 4_000;
const MAX_REPLIES_PER_COMMENT = 3;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizeRemoteComment(
  value: unknown,
  includeReplies: boolean,
): Comment | undefined {
  if (!isRecord(value)) return undefined;
  const member = isRecord(value.member) ? value.member : undefined;
  const content = isRecord(value.content) ? value.content : undefined;
  if (
    typeof member?.uname !== "string" ||
    typeof content?.message !== "string"
  ) {
    return undefined;
  }
  if (
    Buffer.byteLength(member.uname, "utf8") > MAX_COMMENT_AUTHOR_BYTES
  ) {
    throw new ResourceLimitError(
      "Comment author exceeded its byte limit",
      "comment_author",
      MAX_COMMENT_AUTHOR_BYTES,
    );
  }
  if (
    Buffer.byteLength(content.message, "utf8") > MAX_COMMENT_MESSAGE_BYTES
  ) {
    throw new ResourceLimitError(
      "Comment content exceeded its byte limit",
      "comment_content",
      MAX_COMMENT_MESSAGE_BYTES,
    );
  }

  const replies: Comment[] = [];
  if (includeReplies && Array.isArray(value.replies)) {
    for (const rawReply of value.replies.slice(0, MAX_REPLIES_PER_COMMENT)) {
      const reply = normalizeRemoteComment(rawReply, false);
      if (reply) replies.push(reply);
    }
  }

  return {
    rpid: boundedFiniteInteger(value.rpid),
    member: {
      uname: member.uname,
      avatar: "",
    },
    content: {
      message: content.message,
    },
    like: boundedFiniteInteger(value.like),
    replies,
  };
}

function acceptCommentPage(
  data: unknown,
  maxAcceptedItems: number,
  maxRawItems: number,
  includeReplies: boolean,
): { comments: Comment[]; rawIsEmpty: boolean } {
  if (!isRecord(data) || !Array.isArray(data.replies)) {
    throw new UpstreamResponseError(
      "Bilibili returned an invalid comments response",
    );
  }
  const rawReplies = data.replies.slice(0, maxRawItems);
  const accepted: Comment[] = [];
  for (const rawComment of rawReplies) {
    if (accepted.length >= maxAcceptedItems) break;
    const comment = normalizeRemoteComment(rawComment, includeReplies);
    if (comment) accepted.push(comment);
  }
  return { comments: accepted, rawIsEmpty: rawReplies.length === 0 };
}



/**
 * 过滤表情占位符（如 [doge]）
 */
function filterEmojis(text: string): string {
  // 移除所有中括号包裹的表情占位符
  return text.replace(/\[[a-zA-Z0-9_]+\]/g, "").trim();
}

/**
 * 检测评论中是否包含时间戳
 */
function extractTimestamp(text: string): string | null {
  // 匹配时间戳格式，如 05:20, 1:23:45, 00:10 等
  const timestampRegex = /\b(\d{1,2}:)?\d{1,2}:\d{2}\b/g;
  const matches = text.match(timestampRegex);

  if (matches) {
    // 返回第一个匹配的时间戳
    return matches[0];
  }

  return null;
}

/**
 * 处理单条评论
 */
function processComment(
  comment: Comment,
  includeReplies: boolean = false
): ProcessedComment {
  const author =
    boundedRemoteText(comment.member?.uname, MAX_COMMENT_AUTHOR_BYTES) ||
    "匿名用户";
  const rawContent = boundedRemoteText(
    comment.content?.message,
    MAX_COMMENT_MESSAGE_BYTES,
  );
  const filteredContent = filterEmojis(rawContent);
  const likes = boundedFiniteInteger(comment.like);
  const timestamp = extractTimestamp(filteredContent);

  return {
    author,
    content: filteredContent,
    likes,
    has_timestamp: !!timestamp,
    timestamp: timestamp || undefined,
  };
}

/**
 * 获取视频评论
 *
 * 支持旧式调用：
 *   getVideoCommentsData(bvidOrUrl)
 *   getVideoCommentsData(bvidOrUrl, "brief")
 *   getVideoCommentsData(bvidOrUrl, "detailed")
 *
 * 支持新式 options 调用：
 *   getVideoCommentsData(bvidOrUrl, { detailLevel: "detailed", limit: 5, sort: "time", includeReplies: false })
 */
export async function getVideoCommentsData(
  bvidOrUrl: string,
  detailLevelOrOptions?: CommentDetailLevel | CommentOptions,
  legacySort?: number,
  legacyIncludeReplies?: boolean,
): Promise<CommentData> {
  // Resolve options from old or new API shape
  const isOldApi =
    detailLevelOrOptions === undefined ||
    typeof detailLevelOrOptions === "string";

  const detailLevel: CommentDetailLevel = isOldApi
    ? (detailLevelOrOptions ?? "brief")
    : (detailLevelOrOptions.detailLevel ?? "brief");

  const limit: number | undefined = isOldApi
    ? undefined
    : (detailLevelOrOptions as CommentOptions).limit;

  const sort: number = isOldApi
    ? (legacySort ?? 1)
    : ((detailLevelOrOptions as CommentOptions).sort === "time" ? 0 : 1);

  const includeReplies: boolean = isOldApi
    ? (legacyIncludeReplies ?? true)
    : ((detailLevelOrOptions as CommentOptions).includeReplies ?? true);

  const bvid = extractBVId(bvidOrUrl);

  // 生成缓存键：包含有效的 detailLevel/limit/sort/includeReplies
  const cacheDetail = limit !== undefined ? `${detailLevel}-limit-${limit}` : detailLevel;
  const cacheKey = cacheManager.generateKey(
    "comments",
    bvid,
    cacheDetail,
    sort.toString(),
    includeReplies.toString(),
  );

  try {
    // 尝试从缓存获取
    const cachedData = cacheManager.getCommentInfo(cacheKey) as CommentData | undefined;
    if (cachedData) {
      logger.debug("Comments cache hit", { bvid, cacheKey }, { type: "comments" });
      return cachedData;
    }

    logger.debug("Comments cache miss", { bvid, cacheKey }, { type: "comments" });

    // 评论数量：优先使用显式 limit，否则根据 detailLevel 决定
    const commentCount = limit ?? (detailLevel === "brief" ? 10 : 20);

    // 获取评论：limit ≤ 20 单次请求，> 20 顺序分页拉取
    let rawComments: Comment[];
    if (commentCount <= 20) {
      const commentsData = await getVideoComments(
        bvidOrUrl,
        1,
        commentCount,
        sort,
        includeReplies,
      );
      rawComments = acceptCommentPage(
        commentsData,
        commentCount,
        commentCount,
        includeReplies,
      ).comments;
    } else {
      rawComments = [];
      let page = 1;
      let remaining = commentCount;
      // Bilibili uses page-number/page-size pagination. Changing ps on the
      // final request changes that page's offset, so keep ps stable and
      // enforce the caller-visible limit locally.
      const pageSize = 20;
      const maxPages = Math.ceil(commentCount / pageSize);
      while (remaining > 0 && page <= maxPages) {
        const pageData = await getVideoComments(
          bvidOrUrl,
          page,
          pageSize,
          sort,
          includeReplies,
        );
        const acceptedPage = acceptCommentPage(
          pageData,
          remaining,
          pageSize,
          includeReplies,
        );
        if (acceptedPage.rawIsEmpty) break;
        rawComments.push(...acceptedPage.comments);
        remaining -= acceptedPage.comments.length;
        page++;
      }
      rawComments = rawComments.slice(0, commentCount);
    }

    // 处理评论
    let processedComments = rawComments.map((comment) =>
      processComment(comment, includeReplies),
    );

    // 如果是详细模式且包含回复，添加高赞回复
    if (detailLevel === "detailed" && includeReplies) {
      const replies: Comment[] = [];
      for (const comment of rawComments) {
        if (comment.replies && comment.replies.length > 0) {
          // 取前3条高赞回复
          const topReplies = comment.replies.slice(
            0,
            MAX_REPLIES_PER_COMMENT,
          );
          replies.push(...topReplies);
        }
      }
      const processedReplies = replies.map((reply) => processComment(reply));
      processedComments.push(...processedReplies);
    }

    // 优先排序：有时间戳的评论排在前面
    processedComments.sort((a, b) => {
      if (a.has_timestamp && !b.has_timestamp) return -1;
      if (!a.has_timestamp && b.has_timestamp) return 1;
      return b.likes - a.likes; // 都有或都没有时间戳，按点赞数排序
    });

    // 统计
    const commentsWithTimestamp = processedComments.filter(
      (c) => c.has_timestamp,
    ).length;

    const result: CommentData = {
      comments: processedComments,
      summary: {
        total_comments: processedComments.length,
        comments_with_timestamp: commentsWithTimestamp,
      },
    };
    if (
      utf8ByteLength(JSON.stringify(result)) >
      SECURITY_LIMITS.commentResultBytes
    ) {
      throw new ResourceLimitError(
        "Comment result exceeded its byte limit",
        "comment_result",
        SECURITY_LIMITS.commentResultBytes,
      );
    }

    // 存入缓存
    cacheManager.setCommentInfo(cacheKey, result);

    return result;
  } catch (error) {
    if (error instanceof CommentsDisabledError) {
      logger.warn("Comments disabled for video", { bvid }, { type: "comments" });
      throw error;
    }
    logger.error(
      "Error getting video comments",
      { error: redactSecrets(error) },
      { type: "comments" },
    );
    throw error;
  }
}
