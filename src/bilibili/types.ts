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

// 创作者内容段（overview / videos）
export type CreatorContentSection = "overview" | "videos";

// 创作者内容概览（overview 段）：
// 有界实时上游档案事实与可用计数事实；不包含语义总结或目录爬取。
// live_state 标识当前实时上游状态，而非持久化存储状态。
export interface CreatorContentOverview {
  mid: number;
  section: "overview";
  name: string;
  bio: string;
  avatar_url: string;
  // 仅当上游提供有效 fans 事实时才出现，绝不编造为 0。
  follower_count?: number;
  level: number;
  // 上游档案提供，或由一次有界计数探测补充；绝不凭空编造。
  video_count: number;
  live_state: "live";
}

// 创作者视频目录行（videos 段）：
// 有界 BVID 元数据与可用的参与度事实；联合投稿行的行内 mid 可能与所选
// 创作者不同，保留并使用行内 author；访问/权益默认 unknown。
export interface CreatorVideoRow {
  bvid: string;
  title: string;
  description: string;
  cover_url: string;
  category_id?: number;
  category?: string;
  duration_seconds: number;
  published_at: string;
  author: string;
  // 仅当上游提供有效非负整数时才出现（不编造参与度）。
  // arc/search 语义：comment 是评论数，video_review 是弹幕数。
  view_count?: number;
  danmaku_count?: number;
  reply_count?: number;
  // 仅当上游显式真值证据（is_pay / is_charging_arc / elec_arc_type，
  // 或兼容字段 is_charge_video）存在时才为 true。
  is_charge_video?: boolean;
  // 列表可见性、付费标记或可见 BVID 本身永不证明播放权限。
  access: "unknown";
  source_url: string;
}

// 单次 videos 调用返回的有界结果：至多一页 20 行，仅在有上游证明时给出 next_cursor。
export interface CreatorVideoPage {
  mid: number;
  section: "videos";
  page: number;
  videos_total?: number;
  videos: CreatorVideoRow[];
  skipped_count: number;
  next_cursor?: string;
  live_state: "live";
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
