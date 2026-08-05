/**
 * 缓存管理模块
 * 使用LRU缓存实现视频信息和评论的缓存
 */
import QuickLRU from 'quick-lru';
import { config } from '../config.js';
import { SECURITY_LIMITS } from "../security/limits.js";

export class CacheManager<VideoValue = unknown, CommentValue = unknown> {
  private videoCache: QuickLRU<string, VideoValue>;
  private commentCache: QuickLRU<string, CommentValue>;
  private videoWeights = new Map<
    string,
    { value: VideoValue; bytes: number }
  >();
  private commentWeights = new Map<
    string,
    { value: CommentValue; bytes: number }
  >();
  private videoBytes = 0;
  private commentBytes = 0;
  private cacheStats = {
    hits: 0,
    misses: 0,
    sets: 0,
    deletes: 0
  };

  constructor() {
    this.videoCache = new QuickLRU({
      maxSize: config.maxCacheSize,
      maxAge: 60 * 60 * 1000, // 1 hour for video info
      onEviction: (key, value) => this.removeVideoWeight(key, value),
    });

    this.commentCache = new QuickLRU({
      maxSize: config.maxCacheSize,
      maxAge: 30 * 60 * 1000, // 30 minutes for comments
      onEviction: (key, value) => this.removeCommentWeight(key, value),
    });
  }

  private estimateBytes(value: unknown): number | null {
    try {
      const serialized = JSON.stringify(value);
      return serialized === undefined
        ? null
        : Buffer.byteLength(serialized, "utf8");
    } catch {
      return null;
    }
  }

  private removeVideoWeight(key: string, value?: VideoValue): void {
    const current = this.videoWeights.get(key);
    if (!current || (value !== undefined && !Object.is(current.value, value))) {
      return;
    }
    this.videoBytes = Math.max(0, this.videoBytes - current.bytes);
    this.videoWeights.delete(key);
  }

  private removeCommentWeight(key: string, value?: CommentValue): void {
    const current = this.commentWeights.get(key);
    if (!current || (value !== undefined && !Object.is(current.value, value))) {
      return;
    }
    this.commentBytes = Math.max(0, this.commentBytes - current.bytes);
    this.commentWeights.delete(key);
  }

  private makeVideoRoom(bytes: number): void {
    while (
      this.videoBytes + bytes > SECURITY_LIMITS.videoCacheBytes &&
      this.videoCache.size > 1
    ) {
      this.videoCache.evict(1);
    }
    if (this.videoBytes + bytes > SECURITY_LIMITS.videoCacheBytes) {
      this.videoCache.clear();
      this.videoWeights.clear();
      this.videoBytes = 0;
    }
  }

  private makeCommentRoom(bytes: number): void {
    while (
      this.commentBytes + bytes > SECURITY_LIMITS.commentCacheBytes &&
      this.commentCache.size > 1
    ) {
      this.commentCache.evict(1);
    }
    if (this.commentBytes + bytes > SECURITY_LIMITS.commentCacheBytes) {
      this.commentCache.clear();
      this.commentWeights.clear();
      this.commentBytes = 0;
    }
  }

  // 视频信息缓存
  getVideoInfo(key: string): VideoValue | undefined {
    const value = this.videoCache.get(key);
    if (value) {
      this.cacheStats.hits++;
    } else {
      this.cacheStats.misses++;
    }
    return value;
  }

  setVideoInfo(key: string, value: VideoValue): void {
    this.removeVideoWeight(key);
    this.videoCache.delete(key);
    const bytes = this.estimateBytes(value);
    if (bytes === null || bytes > SECURITY_LIMITS.videoCacheEntryBytes) {
      return;
    }
    this.makeVideoRoom(bytes);
    this.videoCache.set(key, value);
    this.videoWeights.set(key, { value, bytes });
    this.videoBytes += bytes;
    this.cacheStats.sets++;
  }

  deleteVideoInfo(key: string): void {
    this.removeVideoWeight(key);
    this.videoCache.delete(key);
    this.cacheStats.deletes++;
  }

  // 评论缓存
  getCommentInfo(key: string): CommentValue | undefined {
    const value = this.commentCache.get(key);
    if (value) {
      this.cacheStats.hits++;
    } else {
      this.cacheStats.misses++;
    }
    return value;
  }

  setCommentInfo(key: string, value: CommentValue): void {
    this.removeCommentWeight(key);
    this.commentCache.delete(key);
    const bytes = this.estimateBytes(value);
    if (bytes === null || bytes > SECURITY_LIMITS.commentCacheEntryBytes) {
      return;
    }
    this.makeCommentRoom(bytes);
    this.commentCache.set(key, value);
    this.commentWeights.set(key, { value, bytes });
    this.commentBytes += bytes;
    this.cacheStats.sets++;
  }

  deleteCommentInfo(key: string): void {
    this.removeCommentWeight(key);
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
    this.videoWeights.clear();
    this.commentWeights.clear();
    this.videoBytes = 0;
    this.commentBytes = 0;
    this.cacheStats = {
      hits: 0,
      misses: 0,
      sets: 0,
      deletes: 0
    };
  }

  // 生成缓存键
  generateKey(prefix: string, ...args: unknown[]): string {
    const keyParts = [
      prefix,
      ...args.map((arg) =>
        typeof arg === "object" && arg !== null ? JSON.stringify(arg) : String(arg),
      ),
    ];
    return keyParts.join(":");
  }
}

// 导出单例实例
export const cacheManager = new CacheManager();
