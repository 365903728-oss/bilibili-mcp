/**
 * 输入验证模块
 * 提供统一的输入验证功能
 */

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
    throw new Error('Input is required');
  }
  
  if (input) {
    if (input.length < minLength) {
      throw new Error(`Input must be at least ${minLength} characters long`);
    }
    
    if (input.length > maxLength) {
      throw new Error(`Input must not exceed ${maxLength} characters`);
    }
  }
}

/**
 * 验证BV号或URL输入
 */
export function validateBVInput(input: string): void {
  validateLength(input, {
    maxLength: 256,
    minLength: 1,
    required: true
  });
  
  // 基本格式验证
  if (!input.includes('BV') && !input.includes('bilibili.com') && !input.includes('b23.tv')) {
    throw new Error('Input must contain BV ID or Bilibili URL');
  }
}

/**
 * 验证语言参数
 */
export function validateLanguage(lang?: string): void {
  if (lang) {
    validateLength(lang, {
      maxLength: 10,
      minLength: 2,
      required: false
    });
    
    // 语言代码格式验证
    if (!/^[a-z]{2}(-[A-Za-z]{2,})?$/.test(lang)) {
      throw new Error('Invalid language code format');
    }
  }
}

/**
 * 验证评论详情级别
 */
export function validateDetailLevel(level?: string): void {
  if (level && !['brief', 'detailed'].includes(level)) {
    throw new Error('Invalid detail level: must be "brief" or "detailed"');
  }
}

/**
 * 验证评论数量限制
 */
export function validateCommentLimit(limit?: number): void {
  if (limit === undefined) return;

  if (typeof limit !== "number" || !Number.isInteger(limit)) {
    throw new Error("Comment limit must be an integer between 1 and 50");
  }

  if (limit < 1 || limit > 50) {
    throw new Error("Comment limit must be between 1 and 50");
  }
}

/**
 * 验证评论排序方式
 */
export function validateCommentSort(sort?: string): void {
  if (sort === undefined) return;

  if (!["hot", "time"].includes(sort)) {
    throw new Error('Invalid comment sort: must be "hot" or "time"');
  }
}

/**
 * 验证 page 参数（正整数）
 */
export function validatePage(page: unknown): void {
  if (page === undefined) return;

  if (typeof page !== "number" || !Number.isInteger(page) || page < 1) {
    throw new Error("page must be a positive integer");
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
      throw new Error("start_seconds must be a finite non-negative number");
    }
  }

  if (endSeconds !== undefined) {
    if (typeof endSeconds !== "number" || !isFinite(endSeconds) || endSeconds < 0) {
      throw new Error("end_seconds must be a finite non-negative number");
    }
  }

  if (
    startSeconds !== undefined &&
    endSeconds !== undefined &&
    endSeconds < startSeconds
  ) {
    throw new Error("end_seconds must be >= start_seconds");
  }
}

/**
 * 验证布尔类型参数
 */
export function validateBoolean(value: unknown, name: string): void {
  if (value !== undefined && typeof value !== "boolean") {
    throw new Error(`${name} must be a boolean`);
  }
}

/**
 * 验证搜索 query：trim 后非空，最多 100 字符
 */
export function validateQuery(query: unknown): void {
  if (query === undefined) return;
  if (typeof query !== "string") {
    throw new Error("query must be a string");
  }
  const trimmed = query.trim();
  if (trimmed.length === 0) {
    throw new Error("query must not be empty");
  }
  if (trimmed.length > 100) {
    throw new Error("query must not exceed 100 characters");
  }
}

/**
 * 验证视频搜索候选数量：整数 1-10
 */
export function validateSearchLimit(value: unknown): void {
  if (value === undefined) return;
  if (typeof value !== "number" || !Number.isInteger(value)) {
    throw new Error("limit must be an integer between 1 and 10");
  }
  if (value < 1 || value > 10) {
    throw new Error("limit must be between 1 and 10");
  }
}

/**
 * 验证 max_matches：整数 1-20
 */
export function validateMaxMatches(value: unknown): void {
  if (value === undefined) return;
  if (typeof value !== "number" || !Number.isInteger(value)) {
    throw new Error("max_matches must be an integer between 1 and 20");
  }
  if (value < 1 || value > 20) {
    throw new Error("max_matches must be between 1 and 20");
  }
}

/**
 * 验证 context_segments：整数 0-5
 */
export function validateContextSegments(value: unknown): void {
  if (value === undefined) return;
  if (typeof value !== "number" || !Number.isInteger(value)) {
    throw new Error("context_segments must be an integer between 0 and 5");
  }
  if (value < 0 || value > 5) {
    throw new Error("context_segments must be between 0 and 5");
  }
}
