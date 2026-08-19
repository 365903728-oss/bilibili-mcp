/**
 * Bilibili API 相关类型定义
 */

// 视频信息类型
export interface VideoInfo {
  title: string;
  desc: string;
  pic?: string;
  owner: {
    name: string;
    face: string;
  };
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
  duration: number;
  pubdate: number;
  tag?: { tag_name: string }[];
}

export interface BilibiliVideoInfoData extends VideoInfo {
  bvid?: string;
  aid?: number;
  need_login_subtitle?: boolean;
  preview_toast?: string;
}

export interface BilibiliSubtitleItem {
  id: number;
  lan: string;
  lan_doc: string;
  subtitle_url: string;
}

// 字幕信息类型
export interface SubtitleInfo {
  subtitle: {
    subtitles: BilibiliSubtitleItem[];
  };
}

export interface SubtitleBodyItem {
  from: number;
  to: number;
  location?: number;
  content: string;
}

// 字幕内容类型
export interface SubtitleContent {
  body: SubtitleBodyItem[];
}

// 评论类型
export interface Comment {
  rpid: number;
  member: {
    uname: string;
    avatar: string;
  };
  content: {
    message: string;
  };
  like: number;
  reply_control?: {
    sub_reply_entry_text?: string;
    show_status?: number;
  };
  replies?: Comment[];
}

// 评论回复类型
export interface CommentReply {
  member: {
    uname: string;
    avatar: string;
  };
  content: {
    message: string;
  };
  like: number;
}

// 评论列表响应类型
export interface CommentsResponse {
  replies: Comment[];
  page: {
    num: number;
    size: number;
  };
}

// 处理后的评论类型
export interface ProcessedComment {
  author: string;
  content: string;
  likes: number;
  has_timestamp: boolean;
  timestamp?: string;
  replies?: ProcessedComment[];
}

// 视频总结响应类型
export interface VideoSummary {
  data_source: 'subtitle' | 'ai_subtitle' | 'description';
  video_info: {
    title: string;
    description: string;
    tags: string[];
    subtitle_text?: string;
  };
}

// 评论总结响应类型
export interface CommentsSummary {
  comments: ProcessedComment[];
  summary: {
    total_comments: number;
    comments_with_timestamp: number;
  };
}

// 支持的语言列表与类型（运行时验证与公开 schema 共用）
export const SUPPORTED_LANGUAGES = [
  "zh-Hans",
  "zh-CN",
  "zh-Hant",
  "en",
  "ja",
  "ko",
  "ai-zh",
] as const;

export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

// 评论详细程度类型
export type CommentDetailLevel = 'brief' | 'detailed';

// 评论排序类型
export type CommentSort = "hot" | "time";

// Part 类型（多P视频的单集）
export interface PartInfo {
  page: number;
  cid: number;
  title: string;
  duration: number;
}

// Bilibili 原始 pages 条目
export interface RawPageEntry {
  cid: number;
  page: number;
  part?: string;
  duration: number;
}

// Chapter 类型（Bilibili 提供的章节/进度条分段）
export interface ChapterInfo {
  title: string;
  start_seconds: number;
  end_seconds: number;
}

// Transcript Match：一个字幕段命中关键词的结果
export interface TranscriptMatch {
  start_seconds: number;
  end_seconds: number;
  content: string;
  context: string;
  timestamp_url: string;
}

// 视频转录数据类型
export interface VideoTranscriptData {
  bvid: string;
  data_source: "subtitle" | "ai_subtitle" | "description" | "asr";
  language?: string;
  transcript: string;
  title: string;
  source_url: string;
  page?: number;
  // search mode fields（仅当 query 存在时返回）
  query?: string;
  total_matches?: number;
  returned_matches?: number;
  truncated?: boolean;
  matches?: TranscriptMatch[];
}

// Bilibili 视频搜索候选
export interface VideoSearchCandidate {
  bvid: string;
  title: string;
  author: string;
  duration_seconds: number;
  published_at: string;
  view_count: number;
  description: string;
  source_url: string;
}

// 有界视频搜索结果
export interface VideoSearchData {
  query: string;
  results: VideoSearchCandidate[];
}

// Bilibili 创作者搜索候选
export interface CreatorSearchCandidate {
  mid: number;
  name: string;
  bio: string;
  avatar_url: string;
  follower_count: number;
  video_count: number;
  level: number;
  source_url: string;
}

// 有界创作者搜索结果
export interface CreatorSearchData {
  query: string;
  results: CreatorSearchCandidate[];
}

// 内部搜索选项（仅供 getVideoTranscriptData 使用）
export interface TranscriptSearchOptions {
  query: string;
  max_matches: number;
  context_segments: number;
}

// 收藏夹文件夹
export interface FavoriteFolder {
  id: number;
  title: string;
  media_count: number;
}

// 收藏夹中的视频成员
export interface FavoriteVideo {
  bvid: string;
  title: string;
  author: string;
  duration_seconds: number;
  published_at: string;
  favorited_at: string;
  source_url: string;
}

// 单次 Favorites Discovery 调用返回的有界结果
export interface FavoriteVideoPage {
  folders_total: number;
  folder?: FavoriteFolder;
  page?: number;
  videos: FavoriteVideo[];
  skipped_count: number;
  next_cursor?: string;
}

// 视频章节数据类型
export interface VideoChaptersData {
  bvid: string;
  page: number;
  cid: number;
  title: string;
  chapters: ChapterInfo[];
}

// 视频元数据类型
export interface VideoMetadataData {
  bvid: string;
  title: string;
  author?: string;
  duration?: number;
  pubdate?: string;
  pubdate_timestamp?: number;
  description: string;
  tags: string[];
  pages: PartInfo[];
  stats: {
    view?: number;
    like?: number;
    coin?: number;
    favorite?: number;
    share?: number;
    reply?: number;
    danmaku?: number;
  };
}

// 评论选项（新 API）
export interface CommentOptions {
  detailLevel?: CommentDetailLevel;
  limit?: number;
  sort?: CommentSort;
  includeReplies?: boolean;
}

// API 错误类型
export interface APIError {
  code: number;
  message: string;
}
