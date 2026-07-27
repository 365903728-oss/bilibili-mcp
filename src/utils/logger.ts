/**
 * 统一日志系统
 */

export type LogLevel = 'info' | 'warn' | 'error' | 'debug';

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  data?: unknown;
  context?: Record<string, unknown>;
}

const SENSITIVE_KEY_PATTERN =
  /cookie|authorization|sessdata|bili_jct|dedeuserid|token|secret|(?:^|_)(?:mid|media_id|folder_id)$/i;

function redactString(value: string): string {
  return value
    .replace(/(SESSDATA=)[^;\s",]+/gi, "$1***")
    .replace(/(bili_jct=)[^;\s",]+/gi, "$1***")
    .replace(/(DedeUserID=)[^;\s",]+/gi, "$1***")
    .replace(/(BILIBILI_SESSDATA=)[^;\s",]+/gi, "$1***")
    .replace(/(BILIBILI_BILI_JCT=)[^;\s",]+/gi, "$1***")
    .replace(/(BILIBILI_DEDEUSERID=)[^;\s",]+/gi, "$1***")
    .replace(
      /([?&](?:up_mid|media_id|folder_id)=)[^&\s"',]+/gi,
      "$1***",
    );
}

export function redactSecrets(value: unknown, seen = new WeakSet<object>()): unknown {
  if (typeof value === "string") {
    return redactString(value);
  }

  if (value === null || typeof value !== "object") {
    return value;
  }

  if (seen.has(value)) {
    return "[Circular]";
  }
  seen.add(value);

  if (value instanceof Error) {
    return {
      name: value.name,
      message: redactString(value.message),
    };
  }

  if (Array.isArray(value)) {
    return value.map((item) => redactSecrets(item, seen));
  }

  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>).map(([key, entryValue]) => [
      key,
      SENSITIVE_KEY_PATTERN.test(key) ? "***" : redactSecrets(entryValue, seen),
    ]),
  );
}

export class Logger {
  private static log(
    level: LogLevel,
    message: string,
    data?: unknown,
    context?: Record<string, unknown>,
  ) {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      message: redactString(message),
      data: redactSecrets(data),
      context: redactSecrets(context) as Record<string, unknown> | undefined,
    };

    // 使用 console.error 确保输出到 stderr，避免干扰 MCP 协议
    console.error(JSON.stringify(entry));
  }

  static info(message: string, data?: unknown, context?: Record<string, unknown>) {
    this.log('info', message, data, context);
  }

  static warn(message: string, data?: unknown, context?: Record<string, unknown>) {
    this.log('warn', message, data, context);
  }

  static error(message: string, data?: unknown, context?: Record<string, unknown>) {
    this.log('error', message, data, context);
  }

  static debug(message: string, data?: unknown, context?: Record<string, unknown>) {
    if (process.env.BILIBILI_MCP_DEBUG !== '1') {
      return;
    }
    this.log('debug', message, data, context);
  }

  /**
   * 记录 API 请求
   */
  static logAPIRequest(
    method: string,
    url: string,
    params?: Record<string, unknown>,
    duration?: number
  ) {
    this.info('API Request', {
      method,
      url,
      params,
      duration: duration ? `${duration}ms` : undefined
    }, { type: 'api-request' });
  }

  /**
   * 记录 API 响应
   */
  static logAPIResponse(
    method: string,
    url: string,
    status: number,
    duration?: number,
    error?: string
  ) {
    const level = status >= 400 ? 'error' : 'info';

    this.log(level, 'API Response', {
      method,
      url,
      status,
      duration: duration ? `${duration}ms` : undefined,
      error
    }, { type: 'api-response' });
  }

  /**
   * 记录 MCP 工具调用
   */
  static logToolCall(toolName: string, args?: Record<string, unknown>, duration?: number) {
    this.info('Tool Call', {
      toolName,
      args,
      duration: duration ? `${duration}ms` : undefined
    }, { type: 'tool-call' });
  }

  /**
   * 记录 MCP 工具结果
   */
  static logToolResult(toolName: string, success: boolean, duration?: number, error?: string) {
    const level = success ? 'info' : 'error';

    this.log(level, 'Tool Result', {
      toolName,
      success,
      duration: duration ? `${duration}ms` : undefined,
      error
    }, { type: 'tool-result' });
  }

  /**
   * 创建带上下文的新 Logger 实例
   */
  static withContext(context: Record<string, unknown>): Logger {
    return new Logger(context);
  }

  private context: Record<string, unknown>;

  constructor(context: Record<string, unknown> = {}) {
    this.context = context;
  }

  info(message: string, data?: unknown) {
    Logger.info(message, data, this.context);
  }

  warn(message: string, data?: unknown) {
    Logger.warn(message, data, this.context);
  }

  error(message: string, data?: unknown) {
    Logger.error(message, data, this.context);
  }

  debug(message: string, data?: unknown) {
    Logger.debug(message, data, this.context);
  }
}

// 导出默认实例
export const logger = Logger;
