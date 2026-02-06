# 请求重试机制实现方案

## 问题分析

### 表现
- ❌ 网络不稳定时容易失败
- ❌ 无自动重试机制
- ❌ 单次请求失败后直接返回错误
- ❌ 网络波动导致用户体验差

### 影响
- **功能稳定性**：网络不稳定时功能失效
- **用户体验**：频繁遇到网络错误
- **系统可靠性**：依赖实时网络状态
- **API使用效率**：单次失败浪费API调用

### 根本原因
- 缺少重试逻辑：throttledFetch只处理超时和限流
- 无错误分类：所有错误都直接抛出
- 无退避策略：无智能重试间隔
- 无状态管理：无重试次数和状态跟踪

## 改进方案

### 1. 实现重试工具模块
**实施步骤**：
1. 创建 `src/utils/retry.ts` 文件
2. 实现指数退避重试函数
3. 配置重试策略

**具体实现**：
```typescript
// src/utils/retry.ts
import { logger } from './logger.js';

export interface RetryOptions {
  maxAttempts?: number;
  baseDelayMs?: number;
  maxDelayMs?: number;
  retryableErrors?: Array<(error: any) => boolean>;
  onRetry?: (attempt: number, error: any, delayMs: number) => void;
}

const DEFAULT_RETRY_OPTIONS: Required<RetryOptions> = {
  maxAttempts: 3,
  baseDelayMs: 1000,
  maxDelayMs: 10000,
  retryableErrors: [
    // 网络错误
    (error: any) => error && error.name === 'NetworkError',
    // 超时错误
    (error: any) => error && error.name === 'TimeoutError',
    // HTTP 5xx错误
    (error: any) => error && error.statusCode && error.statusCode >= 500,
    // 其他可重试错误
    (error: any) => error && error.code === 'ECONNRESET',
    (error: any) => error && error.code === 'ECONNREFUSED',
    (error: any) => error && error.code === 'ETIMEDOUT',
    (error: any) => error && error.code === 'ENOTFOUND'
  ],
  onRetry: (attempt: number, error: any, delayMs: number) => {
    logger.warn(`Retry attempt ${attempt} after ${delayMs}ms due to error: ${error.message}`);
  }
};

/**
 * 执行带重试的异步操作
 */
export async function retry<T>(
  fn: () => Promise<T>,
  options: RetryOptions = {}
): Promise<T> {
  const mergedOptions = { ...DEFAULT_RETRY_OPTIONS, ...options };
  const { maxAttempts, baseDelayMs, maxDelayMs, retryableErrors, onRetry } = mergedOptions;
  
  let lastError: any;
  
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      
      // 检查是否可重试
      const isRetryable = retryableErrors.some(check => check(error));
      
      if (!isRetryable || attempt >= maxAttempts) {
        throw error;
      }
      
      // 计算退避延迟（指数退避 + 抖动）
      const delayMs = Math.min(
        baseDelayMs * Math.pow(2, attempt - 1),
        maxDelayMs
      );
      
      // 添加抖动，避免重试风暴
      const jitterMs = Math.random() * (delayMs * 0.2); // ±10%
      const actualDelayMs = delayMs + jitterMs;
      
      // 通知重试
      onRetry(attempt, error, actualDelayMs);
      
      // 等待重试
      await new Promise(resolve => setTimeout(resolve, actualDelayMs));
    }
  }
  
  // 所有重试都失败
  throw lastError;
}

/**
 * 检查错误是否可重试
 */
export function isRetryableError(error: any): boolean {
  return DEFAULT_RETRY_OPTIONS.retryableErrors.some(check => check(error));
}

/**
 * 创建可重试的函数包装器
 */
export function makeRetryable<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  options: RetryOptions = {}
): (...args: Parameters<T>) => Promise<ReturnType<T>> {
  return async (...args: Parameters<T>): Promise<ReturnType<T>> => {
    return retry(() => fn(...args), options);
  };
}
```

### 2. 集成到throttledFetch
**实施步骤**：
1. 修改 `client.ts` 中的 throttledFetch 函数
2. 集成重试逻辑
3. 保持与现有代码的兼容性

**具体修改**：
```typescript
// src/bilibili/client.ts
import { retry } from '../utils/retry.js';

/**
 * 带限流和超时控制的请求包装器
 * @param fetchFn - 执行 fetch 的函数，支持 AbortController
 * @returns Promise<T>
 */
async function throttledFetch<T>(
  fetchFn: (controller: AbortController) => Promise<T>,
  retryOptions: any = {}
): Promise<T> {
  // 等待上一个请求完成
  if (pendingPromise) {
    await pendingPromise;
  }

  // 创建新的请求
  pendingPromise = (async () => {
    await waitForRateLimit();
  })();

  try {
    await pendingPromise;
    
    // 使用重试机制
    return await retry(() => {
      // 创建 AbortController 用于超时控制
      const controller = new AbortController();
      const timeoutId = setTimeout(() => {
        controller.abort();
        logger.error(`Request timeout after ${REQUEST_TIMEOUT_MS}ms`, {}, { type: 'request-timeout' });
      }, REQUEST_TIMEOUT_MS);

      return fetchFn(controller).finally(() => {
        clearTimeout(timeoutId);
        controller.abort(); // 确保 AbortController 被清理
      });
    }, {
      maxAttempts: 3,
      baseDelayMs: 1000,
      maxDelayMs: 5000,
      ...retryOptions
    });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new TimeoutError(`Request timeout: ${REQUEST_TIMEOUT_MS}ms`, REQUEST_TIMEOUT_MS);
    }
    throw error;
  } finally {
    pendingPromise = null;
  }
}
```

### 3. 分类错误类型
**实施步骤**：
1. 增强错误类型定义
2. 实现错误分类函数
3. 集成到错误处理流程

**具体实现**：
```typescript
// src/utils/errors.ts
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
      return new TimeoutError('Request aborted due to timeout', REQUEST_TIMEOUT_MS);
    }
    if (error.name === 'FetchError' || error.code === 'ECONNRESET') {
      return new NetworkError('Network error', error);
    }
  }
  return error;
}
```

### 4. 配置重试策略
**实施步骤**：
1. 在配置文件中添加重试相关配置
2. 实现可配置的重试策略
3. 支持环境变量覆盖

**具体修改**：
```typescript
// src/config.ts
export interface Config {
  // 现有配置...
  
  // 重试配置
  maxRetryAttempts: number;
  baseRetryDelayMs: number;
  maxRetryDelayMs: number;
}

// 默认配置
export const DEFAULT_CONFIG: Config = {
  // 现有配置...
  
  // 重试配置
  maxRetryAttempts: 3,
  baseRetryDelayMs: 1000,
  maxRetryDelayMs: 10000
};

// 从环境变量加载配置（可选）
function loadConfigFromEnv(): Partial<Config> {
  const envConfig: Partial<Config> = {};
  
  // 现有环境变量...
  
  if (process.env.BILIBILI_MAX_RETRY_ATTEMPTS) {
    envConfig.maxRetryAttempts = parseInt(process.env.BILIBILI_MAX_RETRY_ATTEMPTS, 10);
  }
  
  if (process.env.BILIBILI_BASE_RETRY_DELAY_MS) {
    envConfig.baseRetryDelayMs = parseInt(process.env.BILIBILI_BASE_RETRY_DELAY_MS, 10);
  }
  
  if (process.env.BILIBILI_MAX_RETRY_DELAY_MS) {
    envConfig.maxRetryDelayMs = parseInt(process.env.BILIBILI_MAX_RETRY_DELAY_MS, 10);
  }
  
  return envConfig;
}
```

### 5. 集成到API调用
**实施步骤**：
1. 修改 fetchWithWBI 和 fetchWithoutWBI 函数
2. 集成重试逻辑
3. 保持API兼容性

**具体修改**：
```typescript
// src/bilibili/client.ts
export async function fetchWithWBI(
  path: string,
  params: Record<string, string | number>
): Promise<unknown> {
  return throttledFetch(async (controller) => {
    try {
      const { mixKey } = await getWBI();

      // 添加时间戳参数
      params = { ...params, timestamp: Date.now() };

      // 生成签名
      const w_rid = generateWBISign(params, mixKey);

      // 构建 URL
      const url = new URL(path, BASE_URL);
      Object.entries({ ...params, w_rid }).forEach(([key, value]) => {
        url.searchParams.append(key, String(value));
      });

      const response = await fetch(url.toString(), {
        headers: {
          "User-Agent": config.userAgent,
          "Referer": config.referer,
          "Accept": "application/json",
        },
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new NetworkError(`HTTP ${response.status}: ${response.statusText}`, undefined, url.toString(), response.status);
      }

      const data = await response.json();

      if (data.code !== 0) {
        throw new BilibiliAPIError(data.message || "Unknown error", 'API_ERROR', undefined, data);
      }

      return data.data;
    } catch (error) {
      logger.error(`Error fetching ${path}`, { error: error instanceof Error ? error.message : error }, { type: 'fetch-error', path });
      throw error;
    }
  });
}

// fetchWithoutWBI 类似修改
```

## 技术实现细节

### 关键修改点
- **新增文件**：`src/utils/retry.ts`
- **修改文件**：
  - `src/bilibili/client.ts` (集成重试逻辑)
  - `src/utils/errors.ts` (增强错误类型)
  - `src/config.ts` (添加重试配置)

### 重试策略参数

| 参数 | 默认值 | 描述 | 环境变量 |
|------|--------|------|----------|
| maxRetryAttempts | 3 | 最大重试次数 | BILIBILI_MAX_RETRY_ATTEMPTS |
| baseRetryDelayMs | 1000 | 基础重试延迟 | BILIBILI_BASE_RETRY_DELAY_MS |
| maxRetryDelayMs | 10000 | 最大重试延迟 | BILIBILI_MAX_RETRY_DELAY_MS |

### 重试条件

| 错误类型 | 重试 | 原因 |
|---------|------|------|
| NetworkError | ✅ | 网络连接问题 |
| TimeoutError | ✅ | 临时超时 |
| HTTP 5xx | ✅ | 服务器临时错误 |
| ECONNRESET | ✅ | 连接重置 |
| ECONNREFUSED | ✅ | 连接被拒绝 |
| ETIMEDOUT | ✅ | 连接超时 |
| ENOTFOUND | ✅ | DNS解析失败 |
| 400 Bad Request | ❌ | 客户端错误 |
| 401 Unauthorized | ❌ | 认证失败 |
| 403 Forbidden | ❌ | 权限不足 |
| 404 Not Found | ❌ | 资源不存在 |
| API_ERROR | ❌ | 业务逻辑错误 |

### 测试策略
1. **单元测试**：测试重试函数基本功能
2. **集成测试**：测试与API调用的集成
3. **模拟测试**：模拟网络错误和重试场景
4. **边界测试**：测试最大重试次数、延迟限制
5. **性能测试**：测试重试对性能的影响

## 预期效果

### 稳定性改进
- ✅ **网络容错**：网络波动时自动重试
- ✅ **错误恢复**：临时错误自动恢复
- ✅ **智能退避**：指数退避避免重试风暴
- ✅ **状态管理**：跟踪重试次数和状态

### 功能改进
- 🎯 **可靠性**：显著提高网络环境下的可靠性
- 🎯 **用户体验**：减少网络错误的出现
- 🎯 **系统稳定性**：网络不稳定时仍能工作
- 🎯 **API使用效率**：提高API调用成功率

### 系统改进
- 📈 **稳定性指标**：错误率降低60-80%
- 📈 **可靠性指标**：功能可用率显著提升
- 📈 **用户满意度**：减少网络错误投诉
- 📈 **系统韧性**：增强对网络波动的抵抗能力

## 风险评估

### 潜在风险
- **性能影响**：重试可能增加响应时间
- **API限流**：重试可能触发API限流
- **无限重试**：配置不当可能导致无限重试
- **错误掩盖**：重试可能掩盖真正的问题

### 应对策略
- **性能优化**：智能退避，避免长时间等待
- **限流协调**：重试与限流机制协调
- **安全保障**：最大重试次数限制
- **监控增强**：详细的重试日志和监控

## 实施时间

### 时间估计
- **重试模块实现**：45分钟
- **集成到client.ts**：30分钟
- **错误处理增强**：20分钟
- **配置和测试**：45分钟

### 优先级
**高优先级**：直接影响系统稳定性和用户体验

## 成功指标

- ✅ **错误率降低**：网络错误减少 ≥ 60%
- ✅ **重试成功率**：重试成功比例 ≥ 70%
- ✅ **用户体验**：网络错误投诉减少 ≥ 80%
- ✅ **系统稳定性**：功能可用率提升 ≥ 20%
- 📈 **性能影响**：平均响应时间增加 ≤ 10%
