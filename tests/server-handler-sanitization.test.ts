import { beforeEach, describe, expect, it, vi } from "vitest";

import { getMcpHandler } from "./helpers/mcp.js";

const mockGetVideoMetadataData = vi.fn();
const mockGetVideoChaptersData = vi.fn();
const mockGetVideoTranscriptData = vi.fn();
const mockSearchBilibiliVideos = vi.fn();
const mockListBilibiliFavoriteVideos = vi.fn();

vi.mock("../src/bilibili/subtitle.js", () => ({
  getVideoInfoWithSubtitle: vi.fn(),
  getVideoTranscriptData: (...args: unknown[]) =>
    mockGetVideoTranscriptData(...args),
}));

vi.mock("../src/bilibili/metadata.js", () => ({
  getVideoMetadataData: (...args: unknown[]) => mockGetVideoMetadataData(...args),
}));

vi.mock("../src/bilibili/chapters.js", () => ({
  getVideoChaptersData: (...args: unknown[]) => mockGetVideoChaptersData(...args),
}));

vi.mock("../src/bilibili/search.js", () => ({
  searchBilibiliVideos: (...args: unknown[]) =>
    mockSearchBilibiliVideos(...args),
}));

vi.mock("../src/bilibili/favorites.js", () => ({
  listBilibiliFavoriteVideos: (...args: unknown[]) =>
    mockListBilibiliFavoriteVideos(...args),
}));

vi.mock("../src/bilibili/comments.js", () => ({
  getVideoCommentsData: vi.fn(),
}));

vi.mock("../src/bilibili/http.js", () => ({
  checkLoginStatus: vi.fn(async () => ({ isLogin: false })),
}));

const { NoSubtitleError } = await import("../src/utils/errors.js");

function getCallToolHandler() {
  return getMcpHandler<
    {
      method: "tools/call";
      jsonrpc: "2.0";
      id: number;
      params: { name: string; arguments?: Record<string, unknown> };
    },
    {
      content: Array<{ type: string; text: string }>;
      isError?: boolean;
      structuredContent?: Record<string, unknown>;
    }
  >("tools/call");
}

describe("server handler input sanitization", () => {
  it("passes sanitized input to metadata handler", async () => {
    mockGetVideoMetadataData.mockResolvedValueOnce({ bvid: "BV1T6PQzQErF" });

    const handler = getCallToolHandler();
    await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 1,
      params: {
        name: "get_video_metadata",
        arguments: {
          bvid_or_url: "  https://www.bilibili.com/video/BV1T6PQzQErF/?spm_id_from=333.999.0.0  ",
        },
      },
    });

    expect(mockGetVideoMetadataData).toHaveBeenCalledWith(
      "https://www.bilibili.com/video/BV1T6PQzQErF/?spm_id_from=333.999.0.0",
    );
  });
});

describe("handler validation and transcript output", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it.each([
    ["empty query", { query: "   " }],
    ["max_matches out of range", { query: "hello", max_matches: 999 }],
    ["context_segments out of range", { query: "hello", context_segments: 99 }],
  ])("get_video_transcript with %s returns VALIDATION_ERROR", async (_case, args) => {
    const handler = getCallToolHandler();
    const result = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 3,
      params: {
        name: "get_video_transcript",
        arguments: {
          bvid_or_url: "BV1T6PQzQErF",
          ...args,
        },
      },
    });

    expect(result.isError).toBe(true);
    expect(result).not.toHaveProperty("structuredContent");
    const text = JSON.parse(result.content[0].text);
    expect(text.code).toBe("VALIDATION_ERROR");
  });

  it("returns the same full search result as text and structured content", async () => {
    const fixture = {
      bvid: "BV1T6PQzQErF",
      data_source: "subtitle" as const,
      language: "zh-Hans",
      transcript: "命中片段",
      title: "Structured transcript fixture",
      page: 2,
      source_url: "https://www.bilibili.com/video/BV1T6PQzQErF/?p=2",
      query: "片段",
      total_matches: 2,
      returned_matches: 1,
      truncated: true,
      matches: [
        {
          start_seconds: 12.5,
          end_seconds: 15,
          content: "命中片段",
          context: "前文 命中片段 后文",
          timestamp_url: "https://www.bilibili.com/video/BV1T6PQzQErF/?p=2&t=12.5",
        },
      ],
    };
    mockGetVideoTranscriptData.mockResolvedValueOnce(fixture);

    const handler = getCallToolHandler();
    const result = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 4,
      params: {
        name: "get_video_transcript",
        arguments: {
          bvid_or_url: "BV1T6PQzQErF",
          preferred_lang: "zh-Hans",
          page: 2,
          query: "片段",
          max_matches: 1,
          context_segments: 1,
        },
      },
    });

    expect(result.structuredContent).toEqual(fixture);
    expect(result.content[0].text).toBe(JSON.stringify(fixture, null, 2));
  });

  it("keeps transcript errors text-only", async () => {
    mockGetVideoTranscriptData.mockRejectedValueOnce(
      new NoSubtitleError("No subtitles"),
    );

    const handler = getCallToolHandler();
    const result = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 5,
      params: {
        name: "get_video_transcript",
        arguments: {
          bvid_or_url: "BV1T6PQzQErF",
        },
      },
    });

    expect(result.isError).toBe(true);
    expect(result).not.toHaveProperty("structuredContent");
    expect(JSON.parse(result.content[0].text).code).toBe(
      "SUBTITLE_UNAVAILABLE",
    );
  });

  it("keeps generic transcript failures text-only", async () => {
    mockGetVideoTranscriptData.mockRejectedValueOnce(
      new Error("Unexpected transcript failure"),
    );

    const handler = getCallToolHandler();
    const result = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 6,
      params: {
        name: "get_video_transcript",
        arguments: {
          bvid_or_url: "BV1T6PQzQErF",
        },
      },
    });

    expect(result.isError).toBe(true);
    expect(result).not.toHaveProperty("structuredContent");
    expect(JSON.parse(result.content[0].text).code).toBe("UNKNOWN_ERROR");
  });

  it("get_video_chapters with out-of-range page returns VALIDATION_ERROR via generic error handler", async () => {
    const { ValidationError } = await import("../src/utils/errors.js");
    mockGetVideoChaptersData.mockRejectedValue(new ValidationError("Page 99 not found"));

    const handler = getCallToolHandler();
    const result = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 1,
      params: {
        name: "get_video_chapters",
        arguments: {
          bvid_or_url: "BV1T6PQzQErF",
          page: 99,
        },
      },
    });

    expect(result.isError).toBe(true);
    const text = JSON.parse(result.content[0].text);
    expect(text.code).toBe("VALIDATION_ERROR");
  });

  it("get_video_chapters with non-integer page returns validation error before business call", async () => {
    const handler = getCallToolHandler();
    const result = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 2,
      params: {
        name: "get_video_chapters",
        arguments: {
          bvid_or_url: "BV1T6PQzQErF",
          page: 1.5,
        },
      },
    });

    expect(result.isError).toBe(true);
    const text = JSON.parse(result.content[0].text);
    expect(text.code).toBe("VALIDATION_ERROR");
    expect(mockGetVideoChaptersData).not.toHaveBeenCalled();
  });
});

describe("search handler validation and output", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it.each([
    ["missing query", {}],
    ["empty query", { query: "   " }],
    ["long query", { query: "a".repeat(101) }],
    ["limit below range", { query: "MCP", limit: 0 }],
    ["limit above range", { query: "MCP", limit: 11 }],
    ["fractional limit", { query: "MCP", limit: 1.5 }],
    ["string limit", { query: "MCP", limit: "5" }],
  ])("search_bilibili_videos with %s returns VALIDATION_ERROR", async (_case, args) => {
    const handler = getCallToolHandler();
    const result = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 7,
      params: {
        name: "search_bilibili_videos",
        arguments: args,
      },
    });

    expect(result.isError).toBe(true);
    expect(result).not.toHaveProperty("structuredContent");
    expect(JSON.parse(result.content[0].text).code).toBe("VALIDATION_ERROR");
    expect(mockSearchBilibiliVideos).not.toHaveBeenCalled();
  });

  it("trims the query, applies the default limit, and returns identical dual output", async () => {
    const fixture = {
      query: "MCP",
      results: [
        {
          bvid: "BV1T6PQzQErF",
          title: "MCP introduction",
          author: "Creator",
          duration_seconds: 120,
          published_at: "2026-07-26T00:00:00.000Z",
          view_count: 100,
          description: "Candidate only",
          source_url: "https://www.bilibili.com/video/BV1T6PQzQErF/",
        },
      ],
    };
    mockSearchBilibiliVideos.mockResolvedValueOnce(fixture);

    const handler = getCallToolHandler();
    const result = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 8,
      params: {
        name: "search_bilibili_videos",
        arguments: { query: "  MCP  " },
      },
    });

    expect(mockSearchBilibiliVideos).toHaveBeenCalledWith("MCP", 5);
    expect(result.structuredContent).toEqual(fixture);
    expect(result.content[0].text).toBe(JSON.stringify(fixture, null, 2));
  });

  it("keeps search failures text-only", async () => {
    mockSearchBilibiliVideos.mockRejectedValueOnce(
      new Error("Unexpected search failure"),
    );

    const handler = getCallToolHandler();
    const result = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 9,
      params: {
        name: "search_bilibili_videos",
        arguments: { query: "MCP", limit: 3 },
      },
    });

    expect(result.isError).toBe(true);
    expect(result).not.toHaveProperty("structuredContent");
    expect(JSON.parse(result.content[0].text).code).toBe("UNKNOWN_ERROR");
  });
});

describe("favorites handler validation and output", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it.each([
    ["non-string cursor", { cursor: 42 }],
    ["empty cursor", { cursor: "" }],
    ["overlong cursor", { cursor: `${"A".repeat(257)}` }],
    ["non-base64url cursor", { cursor: "A+B" }],
  ])("list_bilibili_favorite_videos with %s returns VALIDATION_ERROR", async (_case, args) => {
    const handler = getCallToolHandler();
    const result = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 10,
      params: {
        name: "list_bilibili_favorite_videos",
        arguments: args,
      },
    });

    expect(result.isError).toBe(true);
    expect(result).not.toHaveProperty("structuredContent");
    expect(JSON.parse(result.content[0].text).code).toBe("VALIDATION_ERROR");
    expect(mockListBilibiliFavoriteVideos).not.toHaveBeenCalled();
  });

  it("returns identical structured and text favorites output on success", async () => {
    const fixture = {
      folders_total: 2,
      folder: { id: 7, title: "学习", media_count: 12 },
      page: 1,
      videos: [
        {
          bvid: "BV1T6PQzQERF",
          title: "First favorite",
          author: "Uploader",
          duration_seconds: 90,
          published_at: "2026-01-01T00:00:00.000Z",
          favorited_at: "2026-07-01T00:00:00.000Z",
          source_url: "https://www.bilibili.com/video/BV1T6PQzQERF/",
        },
      ],
      skipped_count: 0,
      next_cursor: "eyJ2ZXJzaW9uIjoxLCJmb2xkZXJfaWQiOjcsInBhZ2UiOjJ9",
    };
    mockListBilibiliFavoriteVideos.mockResolvedValueOnce(fixture);

    const handler = getCallToolHandler();
    const result = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 11,
      params: {
        name: "list_bilibili_favorite_videos",
        arguments: {},
      },
    });

    expect(mockListBilibiliFavoriteVideos).toHaveBeenCalledWith(undefined);
    expect(result.structuredContent).toEqual(fixture);
    expect(result.content[0].text).toBe(JSON.stringify(fixture, null, 2));
  });

  it("passes a valid cursor through to the favorites module", async () => {
    mockListBilibiliFavoriteVideos.mockResolvedValueOnce({
      folders_total: 1,
      videos: [],
      skipped_count: 0,
    });

    const handler = getCallToolHandler();
    await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 12,
      params: {
        name: "list_bilibili_favorite_videos",
        arguments: { cursor: "eyJ2ZXJzaW9uIjoxLCJmb2xkZXJfaWQiOjEsInBhZ2UiOjF9" },
      },
    });

    expect(mockListBilibiliFavoriteVideos).toHaveBeenCalledWith(
      "eyJ2ZXJzaW9uIjoxLCJmb2xkZXJfaWQiOjEsInBhZ2UiOjF9",
    );
  });

  it("keeps favorites failures text-only", async () => {
    mockListBilibiliFavoriteVideos.mockRejectedValueOnce(
      new Error("Unexpected favorites failure"),
    );

    const handler = getCallToolHandler();
    const result = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 13,
      params: {
        name: "list_bilibili_favorite_videos",
        arguments: {},
      },
    });

    expect(result.isError).toBe(true);
    expect(result).not.toHaveProperty("structuredContent");
    expect(JSON.parse(result.content[0].text).code).toBe("UNKNOWN_ERROR");
  });

  it("routes a stale-cursor ValidationError from the favorites module as VALIDATION_ERROR", async () => {
    const { ValidationError } = await import("../src/utils/errors.js");
    mockListBilibiliFavoriteVideos.mockRejectedValueOnce(
      new ValidationError(
        "cursor folder no longer belongs to the current account; restart without a cursor",
      ),
    );

    const handler = getCallToolHandler();
    const result = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 14,
      params: {
        name: "list_bilibili_favorite_videos",
        arguments: { cursor: "eyJ2ZXJzaW9uIjoxLCJmb2xkZXJfaWQiOjk5OSwicGFnZSI6MX0" },
      },
    });

    expect(result.isError).toBe(true);
    expect(result).not.toHaveProperty("structuredContent");
    const payload = JSON.parse(result.content[0].text);
    expect(payload.code).toBe("VALIDATION_ERROR");
    expect(payload.message).toContain("restart without a cursor");
  });
});
