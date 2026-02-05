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

// 字幕信息类型
export interface SubtitleInfo {
  subtitle: {
    subtitles: Array<{
      id: number;
      lan: string;
      lan_doc: string;
      subtitle_url: string;
    }>;
  };
}

// 字幕内容类型
export interface SubtitleContent {
  body: Array<{
    from: number;
    to: number;
    location: number;
    content: string;
  }>;
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
  data_source: 'subtitle' | 'description';
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

// 支持的语言类型
export type SupportedLanguage = 'zh-Hans' | 'zh-CN' | 'zh-Hant' | 'en' | 'ja' | 'ko';

// 评论详细程度类型
export type CommentDetailLevel = 'brief' | 'detailed';

// API 错误类型
export interface APIError {
  code: number;
  message: string;
}