/**
 * 缓存管理模块
 * 使用LRU缓存实现视频信息和评论的缓存
 */
import QuickLRU from 'quick-lru';

interface CacheOptions {
  maxSize: number;
  maxAge: number;
}

export class CacheManager {
  private videoCache: QuickLRU<string, any>;
  private commentCache: QuickLRU<string, any>;
  private cacheStats = {
    hits: 0,
    misses: 0,
    sets: 0,
    deletes: 0
  };

  constructor() {
    const defaultOptions: CacheOptions = {
      maxSize: 100,
      maxAge: 60 * 60 * 1000 // 1 hour
    };

    this.videoCache = new QuickLRU({
      ...defaultOptions,
      maxSize: 100,
      maxAge: 60 * 60 * 1000 // 1 hour for video info
    });

    this.commentCache = new QuickLRU({
      ...defaultOptions,
      maxSize: 100,
      maxAge: 30 * 60 * 1000 // 30 minutes for comments
    });
  }

  // 视频信息缓存
  getVideoInfo(key: string): any {
    const value = this.videoCache.get(key);
    if (value) {
      this.cacheStats.hits++;
    } else {
      this.cacheStats.misses++;
    }
    return value;
  }

  setVideoInfo(key: string, value: any): void {
    this.videoCache.set(key, value);
    this.cacheStats.sets++;
  }

  deleteVideoInfo(key: string): void {
    this.videoCache.delete(key);
    this.cacheStats.deletes++;
  }

  // 评论缓存
  getCommentInfo(key: string): any {
    const value = this.commentCache.get(key);
    if (value) {
      this.cacheStats.hits++;
    } else {
      this.cacheStats.misses++;
    }
    return value;
  }

  setCommentInfo(key: string, value: any): void {
    this.commentCache.set(key, value);
    this.cacheStats.sets++;
  }

  deleteCommentInfo(key: string): void {
    this.commentCache.delete(key);
    this.cacheStats.deletes++;
  }

  // 缓存统计
  getStats(): typeof this.cacheStats {
    return { ...this.cacheStats };
  }

  // 清除所有缓存
  clear(): void {
    this.videoCache.clear();
    this.commentCache.clear();
    this.cacheStats = {
      hits: 0,
      misses: 0,
      sets: 0,
      deletes: 0
    };
  }

  // 生成缓存键
  generateKey(prefix: string, ...args: any[]): string {
    const keyParts = [prefix, ...args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : String(arg))];
    return keyParts.join(':');
  }
}

// 导出单例实例
export const cacheManager = new CacheManager();
