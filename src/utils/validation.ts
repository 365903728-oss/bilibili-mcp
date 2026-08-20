/**
 * 输入验证模块
 * 提供统一的输入验证功能
 */

import {
  SUPPORTED_LANGUAGES,
  type SupportedLanguage,
} from "../bilibili/types.js";
import { ValidationError } from "./errors.js";

export interface ValidationOptions {
  maxLength?: number;
  minLength?: number;
  required?: boolean;
}

/**
 * 验证字符串长度
 */
export function validateLength(
  input: string | undefined,
  options: ValidationOptions = {}
): void {
  const { maxLength = 256, minLength = 1, required = true } = options;
  
  if (required && !input) {
    throw new ValidationError('Input is required');
  }
  
  if (input) {
    if (input.length < minLength) {
      throw new ValidationError(`Input must be at least ${minLength} characters long`);
    }
    
    if (input.length > maxLength) {
      throw new ValidationError(`Input must not exceed ${maxLength} characters`);
    }
  }
}

/**
 * 验证BV号或URL输入
 */
export function validateBVInput(input: unknown): void {
  if (typeof input !== "string") {
    throw new ValidationError("bvid_or_url must be a string");
  }

  validateLength(input, {
    maxLength: 256,
    minLength: 1,
    required: true
  });
  
  // 基本格式验证
  if (!input.includes('BV') && !input.includes('bilibili.com') && !input.includes('b23.tv')) {
    throw new ValidationError('Input must contain BV ID or Bilibili URL');
  }
}

/**
 * 验证语言参数
 */
export function isSupportedLanguage(lang: string): lang is SupportedLanguage {
  return SUPPORTED_LANGUAGES.some((supported) => supported === lang);
}

export function validateLanguage(
  lang?: string,
): SupportedLanguage | undefined {
  if (lang === undefined) return undefined;

  validateLength(lang, {
    maxLength: 10,
    minLength: 2,
    required: true
  });

  // 语言代码格式验证
  if (!/^[a-z]{2}(-[A-Za-z]{2,})?$/.test(lang)) {
    throw new ValidationError('Invalid language code format');
  }

  if (!isSupportedLanguage(lang)) {
    throw new ValidationError(
      `Unsupported language. Supported values: ${SUPPORTED_LANGUAGES.join(", ")}`,
    );
  }

  return lang;
}

/**
 * 验证评论详情级别
 */
export function validateDetailLevel(level?: string): void {
  if (level && !['brief', 'detailed'].includes(level)) {
    throw new ValidationError('Invalid detail level: must be "brief" or "detailed"');
  }
}

/**
 * 验证评论数量限制
 */
export function validateCommentLimit(limit?: number): void {
  if (limit === undefined) return;

  if (typeof limit !== "number" || !Number.isInteger(limit)) {
    throw new ValidationError("Comment limit must be an integer between 1 and 50");
  }

  if (limit < 1 || limit > 50) {
    throw new ValidationError("Comment limit must be between 1 and 50");
  }
}

/**
 * 验证评论排序方式
 */
export function validateCommentSort(sort?: string): void {
  if (sort === undefined) return;

  if (!["hot", "time"].includes(sort)) {
    throw new ValidationError('Invalid comment sort: must be "hot" or "time"');
  }
}

/**
 * 验证 page 参数（正整数）
 */
export function validatePage(page: unknown): void {
  if (page === undefined) return;

  if (typeof page !== "number" || !Number.isInteger(page) || page < 1) {
    throw new ValidationError("page must be a positive integer");
  }
}

/**
 * 验证时间戳范围参数
 */
export function validateTimestampRange(
  startSeconds: unknown,
  endSeconds: unknown,
): void {
  if (startSeconds !== undefined) {
    if (typeof startSeconds !== "number" || !isFinite(startSeconds) || startSeconds < 0) {
      throw new ValidationError("start_seconds must be a finite non-negative number");
    }
  }

  if (endSeconds !== undefined) {
    if (typeof endSeconds !== "number" || !isFinite(endSeconds) || endSeconds < 0) {
      throw new ValidationError("end_seconds must be a finite non-negative number");
    }
  }

  if (
    startSeconds !== undefined &&
    endSeconds !== undefined &&
    endSeconds < startSeconds
  ) {
    throw new ValidationError("end_seconds must be >= start_seconds");
  }
}

/**
 * 验证布尔类型参数
 */
export function validateBoolean(value: unknown, name: string): void {
  if (value !== undefined && typeof value !== "boolean") {
    throw new ValidationError(`${name} must be a boolean`);
  }
}

/**
 * 验证搜索 query：trim 后非空，最多 100 字符
 */
export function validateQuery(query: unknown): void {
  if (query === undefined) return;
  if (typeof query !== "string") {
    throw new ValidationError("query must be a string");
  }
  const trimmed = query.trim();
  if (trimmed.length === 0) {
    throw new ValidationError("query must not be empty");
  }
  if (trimmed.length > 100) {
    throw new ValidationError("query must not exceed 100 characters");
  }
}

/**
 * 验证视频搜索候选数量：整数 1-10
 */
export function validateSearchLimit(value: unknown): void {
  if (value === undefined) return;
  if (typeof value !== "number" || !Number.isInteger(value)) {
    throw new ValidationError("limit must be an integer between 1 and 10");
  }
  if (value < 1 || value > 10) {
    throw new ValidationError("limit must be between 1 and 10");
  }
}

/**
 * 验证 max_matches：整数 1-20
 */
export function validateMaxMatches(value: unknown): void {
  if (value === undefined) return;
  if (typeof value !== "number" || !Number.isInteger(value)) {
    throw new ValidationError("max_matches must be an integer between 1 and 20");
  }
  if (value < 1 || value > 20) {
    throw new ValidationError("max_matches must be between 1 and 20");
  }
}

/**
 * 验证 context_segments：整数 0-5
 */
export function validateContextSegments(value: unknown): void {
  if (value === undefined) return;
  if (typeof value !== "number" || !Number.isInteger(value)) {
    throw new ValidationError("context_segments must be an integer between 0 and 5");
  }
  if (value < 0 || value > 5) {
    throw new ValidationError("context_segments must be between 0 and 5");
  }
}

/**
 * 验证 Favorites Discovery 游标的公开 schema：
 * 字符串、长度 1-256、仅 base64url 字符。
 * 不解码 payload；由 favorites 模块在副作用前完成严格解码。
 */
export function validateFavoritesCursor(cursor: unknown): void {
  if (cursor === undefined) return;
  if (typeof cursor !== "string") {
    throw new ValidationError("cursor must be a string");
  }
  if (cursor.length < 1 || cursor.length > 256) {
    throw new ValidationError("cursor length must be between 1 and 256");
  }
  if (!/^[A-Za-z0-9_-]+$/.test(cursor)) {
    throw new ValidationError("cursor must contain only base64url characters");
  }
}

/**
 * 验证 Creator Content 输入：mid 必填正整数安全整数、section 必填枚举、
 * cursor 可选字符串 1-256 且仅 base64url 字符；container_id 仅在
 * Collection/Series 成员遍历时接受正整数安全整数。
 * 不解码 payload；由 creator-content 模块在凭据/网络副作用前完成严格解码与绑定校验。
 */
export function validateCreatorContentInput(
  mid: unknown,
  section: unknown,
  cursor?: unknown,
  containerId?: unknown,
): void {
  if (typeof mid !== "number" || !Number.isSafeInteger(mid) || mid < 1) {
    throw new ValidationError("mid must be a positive safe integer");
  }
  if (
    section !== "overview" &&
    section !== "videos" &&
    section !== "collections" &&
    section !== "series" &&
    section !== "dynamics"
  ) {
    throw new ValidationError("section is not supported");
  }
  if (containerId !== undefined) {
    if (
      typeof containerId !== "number" ||
      !Number.isSafeInteger(containerId) ||
      containerId < 1
    ) {
      throw new ValidationError(
        "container_id must be a positive safe integer",
      );
    }
    if (section !== "collections" && section !== "series") {
      throw new ValidationError(
        "container_id is only supported for collections or series",
      );
    }
  }
  validateFavoritesCursor(cursor);
}
