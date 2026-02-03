// 评论处理逻辑
import { getVideoInfo, getVideoComments } from "./client.js";

export interface CommentData {
  comments: Array<{
    author: string;
    content: string;
    likes: number;
    has_timestamp: boolean;
    timestamp?: string;
  }>;
  summary: {
    total_comments: number;
    comments_with_timestamp: number;
  };
}

/**
 * 从 BV 号或 URL 中提取 BV 号
 */
function extractBVId(input: string): string {
  const match = input.match(/(BV[a-zA-Z0-9]{10})/);
  if (!match) {
    throw new Error("Invalid Bilibili video ID or URL");
  }
  return match[1];
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
  comment: any,
  includeReplies: boolean = false
): {
  author: string;
  content: string;
  likes: number;
  has_timestamp: boolean;
  timestamp?: string;
} {
  const author = comment.member?.uname || "匿名用户";
  const rawContent = comment.content?.message || "";
  const filteredContent = filterEmojis(rawContent);
  const likes = comment.like || 0;
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
 */
export async function getVideoCommentsData(
  bvidOrUrl: string,
  detailLevel: "brief" | "detailed" = "brief"
): Promise<CommentData> {
  try {
    const bvid = extractBVId(bvidOrUrl);

    // 获取视频基本信息以获取 CID
    const videoData = await getVideoInfo(bvid);
    const cid = videoData.cid;

    // 根据详情级别确定评论数量
    const commentCount = detailLevel === "brief" ? 10 : 50;

    // 获取评论
    const commentsData = await getVideoComments(cid, 1, commentCount);

    const rawComments = commentsData?.replies || [];

    // 处理评论
    let processedComments = rawComments.map((comment) => processComment(comment));

    // 如果是详细模式，添加高赞回复
    if (detailLevel === "detailed") {
      const replies: any[] = [];
      for (const comment of rawComments) {
        if (comment.replies && comment.replies.length > 0) {
          // 取前3条高赞回复
          const topReplies = comment.replies.slice(0, 3);
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
    const commentsWithTimestamp = processedComments.filter((c) => c.has_timestamp).length;

    return {
      comments: processedComments,
      summary: {
        total_comments: processedComments.length,
        comments_with_timestamp: commentsWithTimestamp,
      },
    };
  } catch (error) {
    console.error("Error getting video comments:", error);
    throw error;
  }
}
