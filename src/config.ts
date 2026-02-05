/**
 * 配置文件 - 集中管理所有配置项
 */

export interface Config {
  // 请求限流配置
  rateLimitMs: number;

  // WBI 缓存配置
  wbiCacheExpirationMs: number;

  // 请求超时配置
  requestTimeoutMs: number;

  // 缓存大小配置
  maxCacheSize: number;

  // 支持的语言列表
  supportedLanguages: string[];

  // API 基础 URL
  baseUrl: string;

  // 用户代理字符串
  userAgent: string;

  // 引用页面
  referer: string;
}

// 默认配置
export const DEFAULT_CONFIG: Config = {
  rateLimitMs: 500, // 请求间隔 500ms
  wbiCacheExpirationMs: 60 * 60 * 1000, // 1小时缓存过期
  requestTimeoutMs: 10000, // 10秒超时
  maxCacheSize: 100, // 最大缓存条目
  supportedLanguages: ['zh-Hans', 'zh-CN', 'zh-Hant', 'en', 'ja', 'ko'],
  baseUrl: 'https://api.bilibili.com',
  userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
  referer: 'https://www.bilibili.com'
};

// 从环境变量加载配置（可选）
function loadConfigFromEnv(): Partial<Config> {
  const envConfig: Partial<Config> = {};

  if (process.env.BILIBILI_RATE_LIMIT_MS) {
    envConfig.rateLimitMs = parseInt(process.env.BILIBILI_RATE_LIMIT_MS, 10);
  }

  if (process.env.BILIBILI_REQUEST_TIMEOUT_MS) {
    envConfig.requestTimeoutMs = parseInt(process.env.BILIBILI_REQUEST_TIMEOUT_MS, 10);
  }

  if (process.env.BILIBILI_CACHE_SIZE) {
    envConfig.maxCacheSize = parseInt(process.env.BILIBILI_CACHE_SIZE, 10);
  }

  return envConfig;
}

// 合并配置：默认配置 + 环境变量配置
export const config: Config = {
  ...DEFAULT_CONFIG,
  ...loadConfigFromEnv()
};

// 语言验证函数
export function isValidLanguage(lang: string): boolean {
  return config.supportedLanguages.includes(lang);
}

// 获取首选语言（如果没有提供或无效，返回默认）
export function getPreferredLanguage(preferredLang?: string): string {
  if (preferredLang && isValidLanguage(preferredLang)) {
    return preferredLang;
  }
  return config.supportedLanguages[0]; // 默认第一个语言
}