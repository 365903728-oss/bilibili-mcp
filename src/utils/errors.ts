/**
 * 错误处理模块
 * 提供详细的错误类型和错误处理功能
 */

export class ValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ValidationError';
  }
}

export class BVIdError extends ValidationError {
  constructor(message: string) {
    super(message);
    this.name = 'BVIdError';
  }
}

export class InputLengthError extends ValidationError {
  constructor(message: string) {
    super(message);
    this.name = 'InputLengthError';
  }
}

export class UnsafeInputError extends ValidationError {
  constructor(message: string) {
    super(message);
    this.name = 'UnsafeInputError';
  }
}

export class NetworkError extends Error {
  constructor(
    message: string,
    public originalError?: Error,
    public url?: string,
    public statusCode?: number
  ) {
    super(message);
    this.name = 'NetworkError';
  }
}

export class TimeoutError extends Error {
  constructor(message: string, public timeoutMs: number) {
    super(message);
    this.name = 'TimeoutError';
  }
}

export class BilibiliAPIError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode?: number,
    public originalError?: any
  ) {
    super(message);
    this.name = 'BilibiliAPIError';
  }
}

/**
 * 分类错误类型
 */
export function categorizeError(error: any): Error {
  if (error instanceof Error) {
    if (error.name === 'AbortError') {
      return new TimeoutError('Request aborted due to timeout', 30000);
    }
    if (error.name === 'FetchError' || (error as any).code === 'ECONNRESET') {
      return new NetworkError('Network error', error);
    }
  }
  return error;
}

/**
 * 安全地处理输入验证错误
 */
export function handleValidationError(error: unknown): never {
  if (error instanceof ValidationError) {
    throw error;
  }
  
  if (error instanceof Error) {
    throw new ValidationError(`Validation failed: ${error.message}`);
  }
  
  throw new ValidationError('Unknown validation error');
}
