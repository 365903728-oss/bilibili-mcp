/**
 * 统一日志系统
 */

export type LogLevel = 'info' | 'warn' | 'error' | 'debug';

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  data?: any;
  context?: Record<string, any>;
}

export class Logger {
  private static log(level: LogLevel, message: string, data?: any, context?: Record<string, any>) {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      message,
      data,
      context
    };

    // 使用 console.error 确保输出到 stderr，避免干扰 MCP 协议
    console.error(JSON.stringify(entry));
  }

  static info(message: string, data?: any, context?: Record<string, any>) {
    this.log('info', message, data, context);
  }

  static warn(message: string, data?: any, context?: Record<string, any>) {
    this.log('warn', message, data, context);
  }

  static error(message: string, data?: any, context?: Record<string, any>) {
    this.log('error', message, data, context);
  }

  static debug(message: string, data?: any, context?: Record<string, any>) {
    this.log('debug', message, data, context);
  }

  /**
   * 记录 API 请求
   */
  static logAPIRequest(
    method: string,
    url: string,
    params?: Record<string, any>,
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
  static logToolCall(toolName: string, args?: Record<string, any>, duration?: number) {
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
  static withContext(context: Record<string, any>): Logger {
    return new Logger(context);
  }

  private context: Record<string, any>;

  constructor(context: Record<string, any> = {}) {
    this.context = context;
  }

  info(message: string, data?: any) {
    Logger.info(message, data, this.context);
  }

  warn(message: string, data?: any) {
    Logger.warn(message, data, this.context);
  }

  error(message: string, data?: any) {
    Logger.error(message, data, this.context);
  }

  debug(message: string, data?: any) {
    Logger.debug(message, data, this.context);
  }
}

// 导出默认实例
export const logger = Logger;