import { describe, expect, it, vi, afterAll } from "vitest";

const envCleanup = vi.hoisted(() => {
  const prev = process.env.BILIBILI_CACHE_SIZE;
  process.env.BILIBILI_CACHE_SIZE = "3";
  return () => {
    if (prev === undefined) {
      delete process.env.BILIBILI_CACHE_SIZE;
    } else {
      process.env.BILIBILI_CACHE_SIZE = prev;
    }
  };
});
// ponytail: hoisted env set for this file's eviction test; cleanup via return

import { CacheManager } from "../src/utils/cache.js";
import { SECURITY_LIMITS } from "../src/security/limits.js";

describe("CacheManager", () => {
  it("keeps primitive key generation stable", () => {
    const cache = new CacheManager();

    expect(
      cache.generateKey("comments", "BV1T6PQzQErF", "limit-5", "1", "true"),
    ).toBe("comments:BV1T6PQzQErF:limit-5:1:true");
  });

  it("keeps current object insertion-order serialization stable", () => {
    const cache = new CacheManager();

    expect(cache.generateKey("video", { lang: "zh-Hans" })).toBe(
      'video:{"lang":"zh-Hans"}',
    );
  });

  it("tracks video cache hits, misses, sets, deletes, and clear", () => {
    const cache = new CacheManager<{ title: string }>();

    expect(cache.getVideoInfo("missing")).toBeUndefined();
    cache.setVideoInfo("video-key", { title: "Test Video" });

    expect(cache.getVideoInfo("video-key")).toEqual({ title: "Test Video" });
    cache.deleteVideoInfo("video-key");
    expect(cache.getVideoInfo("video-key")).toBeUndefined();

    expect(cache.getStats()).toEqual({
      hits: 1,
      misses: 2,
      sets: 1,
      deletes: 1,
    });

    cache.clear();
    expect(cache.getStats()).toEqual({
      hits: 0,
      misses: 0,
      sets: 0,
      deletes: 0,
    });
  });

  it("tracks comment cache values with a separate generic type", () => {
    const cache = new CacheManager<unknown, { comments: string[] }>();

    cache.setCommentInfo("comment-key", { comments: ["first"] });

    expect(cache.getCommentInfo("comment-key")).toEqual({
      comments: ["first"],
    });
  });

  it("refuses values above each per-entry byte budget", () => {
    const cache = new CacheManager<string, string>();
    const exactVideo = "v".repeat(
      SECURITY_LIMITS.videoCacheEntryBytes - 2,
    );
    const oversizedVideo = `${exactVideo}x`;
    const exactComment = "c".repeat(
      SECURITY_LIMITS.commentCacheEntryBytes - 2,
    );
    const oversizedComment = `${exactComment}x`;

    cache.setVideoInfo("video-exact", exactVideo);
    cache.setVideoInfo("video-over", oversizedVideo);
    cache.setCommentInfo("comment-exact", exactComment);
    cache.setCommentInfo("comment-over", oversizedComment);

    expect(cache.getVideoInfo("video-exact")).toBe(exactVideo);
    expect(cache.getVideoInfo("video-over")).toBeUndefined();
    expect(cache.getCommentInfo("comment-exact")).toBe(exactComment);
    expect(cache.getCommentInfo("comment-over")).toBeUndefined();
  });

  it("evicts weighted video entries before crossing the aggregate byte budget", () => {
    const cache = new CacheManager<{ value: string }>();
    const value = { value: "x".repeat(3 * 1024 * 1024) };

    cache.setVideoInfo("first", value);
    cache.setVideoInfo("second", { ...value });
    cache.setVideoInfo("third", { ...value });

    expect(cache.getVideoInfo("first")).toBeUndefined();
    expect(cache.getVideoInfo("second")).toEqual(value);
    expect(cache.getVideoInfo("third")).toEqual(value);
  });

  it("accounts for replacement and clear without retaining stale weight", () => {
    const cache = new CacheManager<{ value: string }>();

    cache.setVideoInfo("same", { value: "x".repeat(3 * 1024 * 1024) });
    cache.setVideoInfo("same", { value: "small" });
    cache.setVideoInfo("second", { value: "y".repeat(3 * 1024 * 1024) });
    cache.setVideoInfo("third", { value: "z".repeat(3 * 1024 * 1024) });

    expect(cache.getVideoInfo("same")).toEqual({ value: "small" });
    cache.clear();
    expect(cache.getVideoInfo("second")).toBeUndefined();
    expect(cache.getVideoInfo("third")).toBeUndefined();
  });
});

describe("CacheManager LRU capacity (env-driven)", () => {
  it("evicts oldest entries when configured maxCacheSize is small", () => {
    const cache = new CacheManager();

    // ponytail: QuickLRU v7 two-gen — maxSize=3 holds 6, 7th insert evicts oldest
    for (let i = 0; i < 7; i++) {
      cache.setVideoInfo(`key-${i}`, { title: `Video ${i}` });
    }

    expect(cache.getVideoInfo("key-0")).toBeUndefined();
    expect(cache.getVideoInfo("key-6")).toEqual({ title: "Video 6" });
  });
});

afterAll(() => {
  envCleanup();
});
