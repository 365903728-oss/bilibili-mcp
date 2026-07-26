import { beforeEach, describe, expect, it, vi } from "vitest";

const mockGetVideoInfo = vi.fn();
const mockGetVideoSubtitle = vi.fn();
const mockGetSubtitleContent = vi.fn();
const mockCheckLoginStatus = vi.fn();
const mockResolvePartCid = vi.fn();

vi.mock("../src/bilibili/client.js", () => ({
  getVideoInfo: (...args: unknown[]) => mockGetVideoInfo(...args),
  getVideoSubtitle: (...args: unknown[]) => mockGetVideoSubtitle(...args),
  getSubtitleContent: (...args: unknown[]) => mockGetSubtitleContent(...args),
  checkLoginStatus: (...args: unknown[]) => mockCheckLoginStatus(...args),
  resolvePartCid: (...args: unknown[]) => mockResolvePartCid(...args),
  matchPartIdentity: (cid: number, pages: Array<{ cid: number; page: number; title: string }>, fallback: string) => {
    const match = pages.find((p) => p.cid === cid);
    return match ? { page: match.page, title: match.title } : { page: 1, title: fallback };
  },
}));

import {
  getVideoInfoWithSubtitle,
  getVideoTranscriptData,
} from "../src/bilibili/subtitle.js";
import type { TranscriptSearchOptions } from "../src/bilibili/types.js";
import { cacheManager } from "../src/utils/cache.js";
import { BilibiliAPIError, NoSubtitleError } from "../src/utils/errors.js";

function makeFakeSubtitles(subs: Array<Record<string, unknown>>) {
  return {
    subtitle: { subtitles: subs },
  };
}

function makeFakeSubtitleContent(body: Array<{ from: number; to: number; content: string }>) {
  return { body };
}

function defaultPages() {
  return [{ page: 1, cid: 12345, title: "Part 1", duration: 120 }];
}

function defaultVideoData() {
  return {
    title: "Test Video",
    desc: "Video description text",
    cid: 12345,
    pages: undefined,
  };
}

beforeEach(() => {
  cacheManager.clear();
  mockGetVideoInfo.mockReset();
  mockGetVideoSubtitle.mockReset();
  mockGetSubtitleContent.mockReset();
  mockCheckLoginStatus.mockReset();
  mockResolvePartCid.mockReset();

  mockGetVideoInfo.mockResolvedValue({
    title: "Test Video",
    desc: "Video description text",
    cid: 12345,
  });

  mockResolvePartCid.mockResolvedValue({
    cid: 12345,
    pages: defaultPages(),
    videoData: defaultVideoData(),
  });

  mockGetVideoSubtitle.mockResolvedValue(
    makeFakeSubtitles([
      { id: 1, lan: "zh-Hans", lan_doc: "Chinese", subtitle_url: "//example.test/zh.json" },
      { id: 2, lan: "en", lan_doc: "English", subtitle_url: "//example.test/en.json" },
    ]),
  );

  mockGetSubtitleContent.mockResolvedValue(
    makeFakeSubtitleContent([
      { from: 0, to: 1, content: "Hello" },
      { from: 1, to: 2, content: "World" },
    ]),
  );

  mockCheckLoginStatus.mockResolvedValue({ isLogin: true });
});

describe("getVideoInfoWithSubtitle - transient subtitle errors", () => {
  it("retries subtitle retrieval after a temporary error fallback", async () => {
    mockGetVideoSubtitle
      .mockRejectedValueOnce(new Error("Temporary network failure"))
      .mockResolvedValueOnce(
        makeFakeSubtitles([
          {
            id: 1,
            lan: "zh-Hans",
            lan_doc: "Chinese",
            subtitle_url: "//example.test/zh.json",
          },
        ]),
      );

    const firstResult = await getVideoInfoWithSubtitle("BV1R6PQzQErF");
    const secondResult = await getVideoInfoWithSubtitle("BV1R6PQzQErF");

    expect(firstResult.data_source).toBe("description");
    expect(secondResult.data_source).toBe("subtitle");
    expect(mockGetVideoSubtitle).toHaveBeenCalledTimes(2);
  });
});

describe("getVideoTranscriptData - subtitle success", () => {
  it('returns data_source "subtitle"', async () => {
    const result = await getVideoTranscriptData("BV1T6PQzQErF");

    expect(result.data_source).toBe("subtitle");
  });

  it("returns merged transcript with newlines", async () => {
    const result = await getVideoTranscriptData("BV1T6PQzQErF");

    expect(result.transcript).toBe("Hello\nWorld");
  });

  it("returns title and bvid", async () => {
    const result = await getVideoTranscriptData("BV1T6PQzQErF");

    expect(result.title).toBe("Test Video");
    expect(result.bvid).toBe("BV1T6PQzQErF");
    expect(result.language).toBe("zh-Hans");
  });
});

describe("getVideoTranscriptData - language selection", () => {
  it("prefers explicit preferredLang match", async () => {
    await getVideoTranscriptData("BV1T6PQzQErF", "en");

    expect(mockGetSubtitleContent).toHaveBeenCalledWith("//example.test/en.json");
  });

  it("uses default priority: zh-Hans before en", async () => {
    // Remove zh-Hans from fake data to test priority
    mockGetVideoSubtitle.mockResolvedValue(
      makeFakeSubtitles([
        { id: 2, lan: "en", lan_doc: "English", subtitle_url: "//example.test/en.json" },
        { id: 3, lan: "ai-zh", lan_doc: "AI Chinese", subtitle_url: "//example.test/ai-zh.json" },
      ]),
    );

    await getVideoTranscriptData("BV1T6PQzQErF");

    // ai-zh has higher priority than en
    expect(mockGetSubtitleContent).toHaveBeenCalledWith("//example.test/ai-zh.json");
  });
});

describe("getVideoTranscriptData - fallback disabled (default)", () => {
  it("throws NoSubtitleError when subtitle list is empty", async () => {
    mockGetVideoSubtitle.mockResolvedValue(
      makeFakeSubtitles([]),
    );

    await expect(
      getVideoTranscriptData("BV1T6PQzQErF"),
    ).rejects.toThrow(NoSubtitleError);
  });

  it("throws NoSubtitleError when subtitle body is empty", async () => {
    mockGetSubtitleContent.mockResolvedValue(
      makeFakeSubtitleContent([]),
    );

    await expect(
      getVideoTranscriptData("BV1T6PQzQErF"),
    ).rejects.toThrow(NoSubtitleError);
  });

  it("rejects oversized merged subtitle text", async () => {
    mockGetSubtitleContent.mockResolvedValue(
      makeFakeSubtitleContent([
        { from: 0, to: 1, content: "x".repeat(500_001) },
      ]),
    );

    await expect(
      getVideoTranscriptData("BV1T6PQzQErF"),
    ).rejects.toThrow("Subtitle text exceeds maximum length");
  });

  it("rejects excessive subtitle body item counts", async () => {
    mockGetSubtitleContent.mockResolvedValue(
      makeFakeSubtitleContent(
        Array.from({ length: 5_001 }, (_, index) => ({
          from: index,
          to: index + 1,
          content: "x",
        })),
      ),
    );

    await expect(
      getVideoTranscriptData("BV1T6PQzQErF"),
    ).rejects.toThrow("Subtitle body item count exceeds maximum limit");
  });
});

describe("getVideoTranscriptData - fallback enabled", () => {
  it("returns description when subtitle list is empty", async () => {
    mockGetVideoSubtitle.mockResolvedValue(
      makeFakeSubtitles([]),
    );

    const result = await getVideoTranscriptData("BV1T6PQzQErF", undefined, true);

    expect(result.data_source).toBe("description");
    expect(result.transcript).toBe("Video description text");
    expect(result.title).toBe("Test Video");
  });

  it("returns description when subtitle body is empty", async () => {
    mockGetSubtitleContent.mockResolvedValue(
      makeFakeSubtitleContent([]),
    );

    const result = await getVideoTranscriptData("BV1T6PQzQErF", undefined, true);

    expect(result.data_source).toBe("description");
  });

  it("returns description on general fetch error", async () => {
    mockGetVideoSubtitle.mockRejectedValue(new Error("Network down"));

    const result = await getVideoTranscriptData("BV1T6PQzQErF", undefined, true);

    expect(result.data_source).toBe("description");
    expect(result.transcript).toBe("Video description text");
  });
});

describe("getVideoTranscriptData - COOKIE_EXPIRED propagation", () => {
  it("checks login status when an empty subtitle list would otherwise fall back", async () => {
    mockGetVideoSubtitle.mockResolvedValue(makeFakeSubtitles([]));
    mockCheckLoginStatus.mockResolvedValue({ isLogin: false });

    await expect(
      getVideoTranscriptData("BV1T6PQzQErF", undefined, true),
    ).rejects.toMatchObject({ code: "COOKIE_EXPIRED" });

    expect(mockCheckLoginStatus).toHaveBeenCalledOnce();
  });

  it("rethrows COOKIE_EXPIRED even when fallback is enabled", async () => {
    mockGetVideoSubtitle.mockRejectedValue(
      new BilibiliAPIError("Cookie expired", "COOKIE_EXPIRED"),
    );

    await expect(
      getVideoTranscriptData("BV1T6PQzQErF", undefined, true),
    ).rejects.toThrow(BilibiliAPIError);

    await expect(
      getVideoTranscriptData("BV1T6PQzQErF", undefined, true),
    ).rejects.toThrow("Cookie expired");
  });

  it("rethrows COOKIE_EXPIRED when fallback is disabled", async () => {
    mockGetVideoSubtitle.mockRejectedValue(
      new BilibiliAPIError("Cookie expired", "COOKIE_EXPIRED"),
    );

    await expect(
      getVideoTranscriptData("BV1T6PQzQErF"),
    ).rejects.toThrow(BilibiliAPIError);
  });
});

describe("getVideoTranscriptData - range filtering", () => {
  it("filters segments overlapping the requested range", async () => {
    mockGetSubtitleContent.mockResolvedValue(
      makeFakeSubtitleContent([
        { from: 0, to: 5, content: "early" },
        { from: 5, to: 10, content: "middle" },
        { from: 10, to: 15, content: "late" },
      ]),
    );

    const result = await getVideoTranscriptData(
      "BV1T6PQzQErF",
      undefined,
      false,
      undefined,
      false,
      6,
      12,
    );

    expect(result.transcript).toBe("middle\nlate");
  });

  it("includes segment that overlaps start boundary", async () => {
    mockGetSubtitleContent.mockResolvedValue(
      makeFakeSubtitleContent([
        { from: 5, to: 10, content: "middle" },
      ]),
    );

    const result = await getVideoTranscriptData(
      "BV1T6PQzQErF",
      undefined,
      false,
      undefined,
      false,
      7,
      12,
    );

    expect(result.transcript).toBe("middle");
  });

  it("start-only range includes segments to >= start_seconds", async () => {
    mockGetSubtitleContent.mockResolvedValue(
      makeFakeSubtitleContent([
        { from: 0, to: 5, content: "early" },
        { from: 5, to: 10, content: "middle" },
        { from: 10, to: 15, content: "late" },
      ]),
    );

    const result = await getVideoTranscriptData(
      "BV1T6PQzQErF",
      undefined,
      false,
      undefined,
      false,
      10,
      undefined,
    );

    expect(result.transcript).toBe("middle\nlate");
  });

  it("end-only range includes segments from <= end_seconds", async () => {
    mockGetSubtitleContent.mockResolvedValue(
      makeFakeSubtitleContent([
        { from: 0, to: 5, content: "early" },
        { from: 5, to: 10, content: "middle" },
        { from: 10, to: 15, content: "late" },
      ]),
    );

    const result = await getVideoTranscriptData(
      "BV1T6PQzQErF",
      undefined,
      false,
      undefined,
      false,
      undefined,
      5,
    );

    expect(result.transcript).toBe("early\nmiddle");
  });
});

describe("getVideoTranscriptData - timestamps", () => {
  it("prefixes lines with HH:MM:SS timestamps", async () => {
    mockGetSubtitleContent.mockResolvedValue(
      makeFakeSubtitleContent([
        { from: 0, to: 2.5, content: "Hi" },
      ]),
    );

    const result = await getVideoTranscriptData(
      "BV1T6PQzQErF",
      undefined,
      false,
      undefined,
      true,
    );

    expect(result.transcript).toMatch(/\[00:00:00 --> 00:00:02\] Hi/);
  });

  it("rejects description fallback when timestamps requested and no subtitles available", async () => {
    mockGetVideoSubtitle.mockResolvedValue(makeFakeSubtitles([]));

    await expect(
      getVideoTranscriptData(
        "BV1T6PQzQErF",
        undefined,
        true,
        undefined,
        true,
      ),
    ).rejects.toThrow(NoSubtitleError);
  });

  it("rejects description fallback when range requested and no subtitles available", async () => {
    mockGetVideoSubtitle.mockResolvedValue(makeFakeSubtitles([]));

    await expect(
      getVideoTranscriptData(
        "BV1T6PQzQErF",
        undefined,
        true,
        undefined,
        false,
        10,
        30,
      ),
    ).rejects.toThrow(NoSubtitleError);
  });
});

function searchOpts(
  query: string,
  max_matches = 10,
  context_segments = 1,
): TranscriptSearchOptions {
  return { query, max_matches, context_segments };
}

describe("getVideoTranscriptData - keyword search", () => {
  it("finds case-insensitive literal matches", async () => {
    mockGetSubtitleContent.mockResolvedValue(
      makeFakeSubtitleContent([
        { from: 0, to: 2, content: "Hello World" },
        { from: 2, to: 4, content: "goodbye" },
        { from: 4, to: 6, content: "hello again" },
      ]),
    );

    const result = await getVideoTranscriptData(
      "BV1T6PQzQErF",
      undefined,
      false,
      undefined,
      false,
      undefined,
      undefined,
      searchOpts("hello"),
    );

    expect(result.data_source).toBe("subtitle");
    expect(result.total_matches).toBe(2);
    expect(result.returned_matches).toBe(2);
    expect(result.truncated).toBe(false);
    expect(result.matches).toHaveLength(2);
    expect(result.matches![0].content).toBe("Hello World");
    expect(result.matches![1].content).toBe("hello again");
  });

  it("counts each matching segment once regardless of occurrences", async () => {
    mockGetSubtitleContent.mockResolvedValue(
      makeFakeSubtitleContent([
        { from: 0, to: 2, content: "hello hello hello" },
      ]),
    );

    const result = await getVideoTranscriptData(
      "BV1T6PQzQErF",
      undefined,
      false,
      undefined,
      false,
      undefined,
      undefined,
      searchOpts("hello"),
    );

    expect(result.total_matches).toBe(1);
    expect(result.matches).toHaveLength(1);
  });

  it("includes timestamped context around each match", async () => {
    mockGetSubtitleContent.mockResolvedValue(
      makeFakeSubtitleContent([
        { from: 0, to: 2, content: "before" },
        { from: 2, to: 4, content: "MATCH" },
        { from: 4, to: 6, content: "after" },
      ]),
    );

    const result = await getVideoTranscriptData(
      "BV1T6PQzQErF",
      undefined,
      false,
      undefined,
      false,
      undefined,
      undefined,
      searchOpts("match"),
    );

    expect(result.matches![0].context).toContain("before");
    expect(result.matches![0].context).toContain("MATCH");
    expect(result.matches![0].context).toContain("after");
  });

  it("respects context_segments=0", async () => {
    mockGetSubtitleContent.mockResolvedValue(
      makeFakeSubtitleContent([
        { from: 0, to: 2, content: "before" },
        { from: 2, to: 4, content: "MATCH" },
        { from: 4, to: 6, content: "after" },
      ]),
    );

    const result = await getVideoTranscriptData(
      "BV1T6PQzQErF",
      undefined,
      false,
      undefined,
      false,
      undefined,
      undefined,
      searchOpts("match", 10, 0),
    );

    const ctx = result.matches![0].context;
    expect(ctx).toContain("MATCH");
    expect(ctx).not.toContain("before");
    expect(ctx).not.toContain("after");
  });

  it("respects max_matches limit", async () => {
    mockGetSubtitleContent.mockResolvedValue(
      makeFakeSubtitleContent([
        { from: 0, to: 1, content: "hit 1" },
        { from: 1, to: 2, content: "hit 2" },
        { from: 2, to: 3, content: "hit 3" },
        { from: 3, to: 4, content: "hit 4" },
        { from: 4, to: 5, content: "hit 5" },
      ]),
    );

    const result = await getVideoTranscriptData(
      "BV1T6PQzQErF",
      undefined,
      false,
      undefined,
      false,
      undefined,
      undefined,
      searchOpts("hit", 3),
    );

    expect(result.returned_matches).toBe(3);
    expect(result.total_matches).toBe(5);
    expect(result.truncated).toBe(true);
    expect(result.matches).toHaveLength(3);
  });

  it("returns empty matches and transcript on no match", async () => {
    mockGetSubtitleContent.mockResolvedValue(
      makeFakeSubtitleContent([
        { from: 0, to: 2, content: "Hello" },
        { from: 2, to: 4, content: "World" },
      ]),
    );

    const result = await getVideoTranscriptData(
      "BV1T6PQzQErF",
      undefined,
      false,
      undefined,
      false,
      undefined,
      undefined,
      searchOpts("xyzzy"),
    );

    expect(result.data_source).toBe("subtitle");
    expect(result.total_matches).toBe(0);
    expect(result.matches).toHaveLength(0);
    expect(result.transcript).toBe("");
  });

  it("applies range filter before searching", async () => {
    mockGetSubtitleContent.mockResolvedValue(
      makeFakeSubtitleContent([
        { from: 0, to: 5, content: "hello early" },
        { from: 5, to: 10, content: "hello middle" },
        { from: 10, to: 15, content: "hello late" },
      ]),
    );

    const result = await getVideoTranscriptData(
      "BV1T6PQzQErF",
      undefined,
      false,
      undefined,
      false,
      6,
      9,
      searchOpts("hello"),
    );

    expect(result.total_matches).toBe(1);
    expect(result.matches![0].content).toBe("hello middle");
  });

  it("context stays inside the requested range", async () => {
    mockGetSubtitleContent.mockResolvedValue(
      makeFakeSubtitleContent([
        { from: 0, to: 3, content: "outside left" },
        { from: 3, to: 6, content: "hello match" },
        { from: 6, to: 9, content: "outside right" },
      ]),
    );

    const result = await getVideoTranscriptData(
      "BV1T6PQzQErF",
      undefined,
      false,
      undefined,
      false,
      3.5,
      5.5,
      searchOpts("hello"),
    );

    const ctx = result.matches![0].context;
    expect(ctx).toContain("hello match");
    expect(ctx).not.toContain("outside left");
    expect(ctx).not.toContain("outside right");
  });

  it("matches Chinese queries", async () => {
    mockGetSubtitleContent.mockResolvedValue(
      makeFakeSubtitleContent([
        { from: 0, to: 2, content: "你好世界" },
        { from: 2, to: 4, content: "Hello World" },
      ]),
    );

    const result = await getVideoTranscriptData(
      "BV1T6PQzQErF",
      undefined,
      false,
      undefined,
      false,
      undefined,
      undefined,
      searchOpts("你好"),
    );

    expect(result.total_matches).toBe(1);
    expect(result.matches![0].content).toBe("你好世界");
  });

  it("builds compact transcript from returned contexts", async () => {
    mockGetSubtitleContent.mockResolvedValue(
      makeFakeSubtitleContent([
        { from: 0, to: 2, content: "before" },
        { from: 2, to: 4, content: "HIT ONE" },
        { from: 4, to: 6, content: "after" },
        { from: 6, to: 8, content: "HIT TWO" },
        { from: 8, to: 10, content: "trailing" },
      ]),
    );

    const result = await getVideoTranscriptData(
      "BV1T6PQzQErF",
      undefined,
      false,
      undefined,
      false,
      undefined,
      undefined,
      searchOpts("HIT"),
    );

    expect(result.transcript).toContain("HIT ONE");
    expect(result.transcript).toContain("HIT TWO");
  });

  it("exposes hit start/end seconds and content", async () => {
    mockGetSubtitleContent.mockResolvedValue(
      makeFakeSubtitleContent([
        { from: 10, to: 15, content: "target" },
      ]),
    );

    const result = await getVideoTranscriptData(
      "BV1T6PQzQErF",
      undefined,
      false,
      undefined,
      false,
      undefined,
      undefined,
      searchOpts("target"),
    );

    expect(result.matches![0].start_seconds).toBe(10);
    expect(result.matches![0].end_seconds).toBe(15);
    expect(result.matches![0].content).toBe("target");
  });

  it("rejects an oversized matching context", async () => {
    mockGetSubtitleContent.mockResolvedValue(
      makeFakeSubtitleContent([
        { from: 0, to: 2, content: `target${"a".repeat(500_001)}` },
      ]),
    );

    await expect(
      getVideoTranscriptData(
        "BV1T6PQzQErF",
        undefined,
        false,
        undefined,
        false,
        undefined,
        undefined,
        searchOpts("target"),
      ),
    ).rejects.toThrow("Subtitle text exceeds maximum length");
  });
});

describe("getVideoTranscriptData - search rejects description fallback", () => {
  it("throws when subtitles are empty even with fallback enabled", async () => {
    mockGetVideoSubtitle.mockResolvedValue(makeFakeSubtitles([]));

    await expect(
      getVideoTranscriptData(
        "BV1T6PQzQErF",
        undefined,
        true,
        undefined,
        false,
        undefined,
        undefined,
        searchOpts("hello"),
      ),
    ).rejects.toThrow(NoSubtitleError);
  });

  it("throws when subtitle body is empty even with fallback enabled", async () => {
    mockGetSubtitleContent.mockResolvedValue(makeFakeSubtitleContent([]));

    await expect(
      getVideoTranscriptData(
        "BV1T6PQzQErF",
        undefined,
        true,
        undefined,
        false,
        undefined,
        undefined,
        searchOpts("hello"),
      ),
    ).rejects.toThrow(NoSubtitleError);
  });
});

describe("getVideoTranscriptData - evidence links", () => {
  it("builds ordinary source URL preserving exact BVID casing", async () => {
    const result = await getVideoTranscriptData("BV1T6PQzQErF");

    expect(result.source_url).toBe("https://www.bilibili.com/video/BV1T6PQzQErF/");
  });

  it("omits p query for single-Part videos", async () => {
    const result = await getVideoTranscriptData("BV1T6PQzQErF");

    expect(result.source_url).not.toContain("?");
  });

  it("includes resolved p query for multi-Part videos", async () => {
    mockResolvePartCid.mockResolvedValue({
      cid: 77777,
      videoData: defaultVideoData(),
      pages: [
        { page: 1, cid: 12345, title: "P1", duration: 120 },
        { page: 2, cid: 77777, title: "P2", duration: 180 },
      ],
    });

    const result = await getVideoTranscriptData("BV1T6PQzQErF", undefined, false, 2);

    expect(result.source_url).toBe("https://www.bilibili.com/video/BV1T6PQzQErF/?p=2");
  });

  it("resolves p from CID when page is omitted on a multi-Part video", async () => {
    mockResolvePartCid.mockResolvedValue({
      cid: 77777,
      videoData: { title: "Test Video", desc: "Video description text", cid: 77777 },
      pages: [
        { page: 1, cid: 12345, title: "P1", duration: 120 },
        { page: 2, cid: 77777, title: "P2", duration: 180 },
      ],
    });

    const result = await getVideoTranscriptData("BV1T6PQzQErF");

    expect(result.source_url).toBe("https://www.bilibili.com/video/BV1T6PQzQErF/?p=2");
  });

  it("adds exact decimal timestamp_url per search match", async () => {
    mockGetSubtitleContent.mockResolvedValue(
      makeFakeSubtitleContent([
        { from: 12.5, to: 15, content: "target" },
      ]),
    );

    const result = await getVideoTranscriptData(
      "BV1T6PQzQErF",
      undefined,
      false,
      undefined,
      false,
      undefined,
      undefined,
      searchOpts("target"),
    );

    expect(result.matches![0].timestamp_url).toBe(
      "https://www.bilibili.com/video/BV1T6PQzQErF/?t=12.5",
    );
  });

  it("timestamp_url inherits resolved p on a multi-Part search", async () => {
    mockResolvePartCid.mockResolvedValue({
      cid: 77777,
      videoData: defaultVideoData(),
      pages: [
        { page: 1, cid: 12345, title: "P1", duration: 120 },
        { page: 2, cid: 77777, title: "P2", duration: 180 },
      ],
    });
    mockGetSubtitleContent.mockResolvedValue(
      makeFakeSubtitleContent([
        { from: 17, to: 19, content: "target" },
      ]),
    );

    const result = await getVideoTranscriptData(
      "BV1T6PQzQErF",
      undefined,
      false,
      2,
      false,
      undefined,
      undefined,
      searchOpts("target"),
    );

    expect(result.matches![0].timestamp_url).toBe(
      "https://www.bilibili.com/video/BV1T6PQzQErF/?p=2&t=17",
    );
  });

  it("includes source_url on description fallback when subtitle list is empty", async () => {
    mockGetVideoSubtitle.mockResolvedValue(makeFakeSubtitles([]));

    const result = await getVideoTranscriptData("BV1T6PQzQErF", undefined, true);

    expect(result.data_source).toBe("description");
    expect(result.source_url).toBe("https://www.bilibili.com/video/BV1T6PQzQErF/");
  });

  it("includes source_url on description fallback when subtitle body is empty", async () => {
    mockGetSubtitleContent.mockResolvedValue(makeFakeSubtitleContent([]));

    const result = await getVideoTranscriptData("BV1T6PQzQErF", undefined, true);

    expect(result.data_source).toBe("description");
    expect(result.source_url).toBe("https://www.bilibili.com/video/BV1T6PQzQErF/");
  });

  it("includes source_url on general-error description fallback", async () => {
    mockGetVideoSubtitle.mockRejectedValue(new Error("Network down"));

    const result = await getVideoTranscriptData("BV1T6PQzQErF", undefined, true);

    expect(result.data_source).toBe("description");
    expect(result.source_url).toBe("https://www.bilibili.com/video/BV1T6PQzQErF/");
  });
});

describe("getVideoTranscriptData - page selection", () => {
  it("calls resolvePartCid with the page number", async () => {
    await getVideoTranscriptData(
      "BV1T6PQzQErF",
      undefined,
      false,
      2,
    );

    expect(mockResolvePartCid).toHaveBeenCalledWith("BV1T6PQzQErF", 2);
  });

  it("uses the resolved CID for subtitle fetching", async () => {
    mockResolvePartCid.mockResolvedValue({
      cid: 77777,
      videoData: defaultVideoData(),
      pages: [
        { page: 1, cid: 12345, title: "P1", duration: 120 },
        { page: 2, cid: 77777, title: "P2", duration: 180 },
      ],
    });

    await getVideoTranscriptData("BV1T6PQzQErF", undefined, false, 2);

    expect(mockGetVideoSubtitle).toHaveBeenCalledWith("BV1T6PQzQErF", 77777);
  });
});
