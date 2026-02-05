/**
 * 统一错误处理定义
 */

// Bilibili API 错误
export class BilibiliAPIError extends Error {
  constructor(
    message: string,
    public readonly code: string = 'BILIBILI_API_ERROR',
    public readonly statusCode?: number,
    public readonly originalError?: any
  ) {
    super(message);
    this.name = 'BilibiliAPIError';
  }
}

// 网络错误
export class NetworkError extends Error {
  constructor(
    message: string,
    public readonly originalError?: Error,
    public readonly url?: string
  ) {
    super(message);
    this.name = 'NetworkError';
  }
}

// 超时错误
export class TimeoutError extends Error {
  constructor(
    message: string = 'Request timeout',
    public readonly timeoutMs?: number
  ) {
    super(message);
    this.name = 'TimeoutError';
  }
}

// 验证错误
export class ValidationError extends Error {
  constructor(
    message: string,
    public readonly field?: string
  ) {
    super(message);
    this.name = 'ValidationError';
  }
}

// 配置错误
export class ConfigError extends Error {
  constructor(
    message: string,
    public readonly configKey?: string
  ) {
    super(message);
    this.name = 'ConfigError';
  }
}

// 工具错误
export class ToolError extends Error {
  constructor(
    message: string,
    public readonly toolName?: string,
    public readonly originalError?: Error
  ) {
    super(message);
    this.name = 'ToolError';
  }
}

// 错误类型守卫
export function isBilibiliAPIError(error: unknown): error is BilibiliAPIError {
  return error instanceof BilibiliAPIError;
}

export function isNetworkError(error: unknown): error is NetworkError {
  return error instanceof NetworkError;
}

export function isTimeoutError(error: unknown): error is TimeoutError {
  return error instanceof TimeoutError;
}

export function isValidationError(error: unknown): error is ValidationError {
  return error instanceof ValidationError;
}

export function isConfigError(error: unknown): error is ConfigError {
  return error instanceof ConfigError;
}

export function isToolError(error: unknown): error is ToolError {
  return error instanceof ToolError;
}

// 错误处理工具
export class ErrorHandler {
  /**
   * 安全处理错误，返回标准化格式
   */
  static safeHandle(error: unknown): { error: boolean; message: string; code?: string; type?: string } {
    if (error instanceof Error) {
      return {
        error: true,
        message: error.message,
        code: (error as any).code,
        type: error.name
      };
    }

    return {
      error: true,
      message: 'Unknown error',
      type: 'UnknownError'
    };
  }

  /**
   * 包装 Promise 错误
   */
  static async wrap<T>(
    promise: Promise<T>,
    errorMessage: string = 'Operation failed'
  ): Promise<{ data: T; error?: never } | { error: true; message: string; data?: never }> {
    try {
      return { data: await promise };
    } catch (error) {
      const errorInfo = this.safeHandle(error);
      return {
        error: true,
        message: `${errorMessage}: ${errorInfo.message}`
      };
    }
  }

  /**
   * 检查并重试异步函数
   */
  static async withRetry<T>(
    fn: () => Promise<T>,
    maxRetries: number = 3,
    delayMs: number = 1000
  ): Promise<T> {
    let lastError: Error | undefined;

    for (let i = 0; i < maxRetries; i++) {
      try {
        return await fn();
      } catch (error) {
        lastError = error as Error;
        if (i < maxRetries - 1) {
          await new Promise(resolve => setTimeout(resolve, delayMs));
        }
      }
    }

    if (lastError) {
      throw lastError;
    }
    throw new Error('Unknown error in retry operation');
  }
}