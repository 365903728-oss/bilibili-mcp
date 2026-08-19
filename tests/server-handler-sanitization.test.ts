import { beforeEach, describe, expect, it, vi } from "vitest";

import { SECURITY_LIMITS } from "../src/security/limits.js";
import { getMcpHandler } from "./helpers/mcp.js";

const mockGetVideoInfoWithSubtitle = vi.fn();
const mockGetVideoMetadataData = vi.fn();
const mockGetVideoChaptersData = vi.fn();
const mockGetVideoTranscriptData = vi.fn();
const mockGetVideoCommentsData = vi.fn();
const mockSearchBilibiliVideos = vi.fn();
const mockSearchBilibiliCreators = vi.fn();
const mockListBilibiliFavoriteVideos = vi.fn();

vi.mock("../src/bilibili/subtitle.js", () => ({
  getVideoInfoWithSubtitle: (...args: unknown[]) =>
    mockGetVideoInfoWithSubtitle(...args),
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
  searchBilibiliCreators: (...args: unknown[]) =>
    mockSearchBilibiliCreators(...args),
}));

vi.mock("../src/bilibili/favorites.js", () => ({
  listBilibiliFavoriteVideos: (...args: unknown[]) =>
    mockListBilibiliFavoriteVideos(...args),
}));

vi.mock("../src/bilibili/comments.js", () => ({
  getVideoCommentsData: (...args: unknown[]) =>
    mockGetVideoCommentsData(...args),
}));

vi.mock("../src/bilibili/http.js", () => ({
  checkLoginStatus: vi.fn(async () => ({ isLogin: false })),
}));

const { AsrError, NoSubtitleError } = await import("../src/utils/errors.js");

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

  it("passes ai-zh unchanged to get_video_info subtitle selection", async () => {
    mockGetVideoInfoWithSubtitle.mockResolvedValueOnce({
      data_source: "subtitle",
      video_info: { title: "AI subtitle fixture" },
    });

    const handler = getCallToolHandler();
    await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 21,
      params: {
        name: "get_video_info",
        arguments: {
          bvid_or_url: "BV1T6PQzQErF",
          preferred_lang: "ai-zh",
        },
      },
    });

    expect(mockGetVideoInfoWithSubtitle).toHaveBeenCalledWith(
      "BV1T6PQzQErF",
      "ai-zh",
      undefined,
      false,
    );
  });

  it("passes ai-zh unchanged to get_video_transcript subtitle selection", async () => {
    mockGetVideoTranscriptData.mockResolvedValueOnce({
      bvid: "BV1T6PQzQErF",
      data_source: "subtitle",
      language: "ai-zh",
      transcript: "AI subtitle fixture",
      title: "AI subtitle fixture",
      source_url: "https://www.bilibili.com/video/BV1T6PQzQErF/",
    });

    const handler = getCallToolHandler();
    await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 22,
      params: {
        name: "get_video_transcript",
        arguments: {
          bvid_or_url: "BV1T6PQzQErF",
          preferred_lang: "ai-zh",
        },
      },
    });

    expect(mockGetVideoTranscriptData).toHaveBeenCalledWith(
      "BV1T6PQzQErF",
      "ai-zh",
      false,
      undefined,
      undefined,
      undefined,
      undefined,
      undefined,
      false,
      false,
      false,
    );
  });

  it.each([
    ["get_video_info", mockGetVideoInfoWithSubtitle],
    ["get_video_transcript", mockGetVideoTranscriptData],
  ])(
    "%s rejects a well-formed unsupported language before business work",
    async (name, businessMock) => {
      const handler = getCallToolHandler();
      const result = await handler({
        method: "tools/call",
        jsonrpc: "2.0",
        id: 23,
        params: {
          name,
          arguments: {
            bvid_or_url: "BV1T6PQzQErF",
            preferred_lang: "fr",
          },
        },
      });

      expect(result.isError).toBe(true);
      expect(result).not.toHaveProperty("structuredContent");
      expect(JSON.parse(result.content[0].text)).toMatchObject({
        code: "VALIDATION_ERROR",
        message:
          "Unsupported language. Supported values: zh-Hans, zh-CN, zh-Hant, en, ja, ko, ai-zh",
      });
      expect(businessMock).not.toHaveBeenCalled();
    },
  );

  it.each([
    ["empty query", { query: "   " }],
    ["max_matches out of range", { query: "hello", max_matches: 999 }],
    ["context_segments out of range", { query: "hello", context_segments: 99 }],
    ["non-boolean fallback_to_asr", { fallback_to_asr: "yes" }],
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

  it("forwards exclude_ai_subtitles to get_video_info subtitle selection", async () => {
    mockGetVideoInfoWithSubtitle.mockResolvedValueOnce({
      data_source: "subtitle",
      video_info: { title: "AI subtitle fixture" },
    });

    const handler = getCallToolHandler();
    await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 51,
      params: {
        name: "get_video_info",
        arguments: {
          bvid_or_url: "BV1T6PQzQErF",
          exclude_ai_subtitles: true,
        },
      },
    });

    expect(mockGetVideoInfoWithSubtitle).toHaveBeenCalledWith(
      "BV1T6PQzQErF",
      "zh-Hans",
      undefined,
      true,
    );
  });

  it("forwards exclude_ai_subtitles and force_asr to get_video_transcript", async () => {
    mockGetVideoTranscriptData.mockResolvedValueOnce({
      bvid: "BV1T6PQzQErF",
      data_source: "subtitle",
      language: "zh-Hans",
      transcript: "AI subtitle fixture",
      title: "AI subtitle fixture",
      source_url: "https://www.bilibili.com/video/BV1T6PQzQErF/",
    });

    const handler = getCallToolHandler();
    await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 52,
      params: {
        name: "get_video_transcript",
        arguments: {
          bvid_or_url: "BV1T6PQzQErF",
          exclude_ai_subtitles: true,
          force_asr: true,
        },
      },
    });

    expect(mockGetVideoTranscriptData).toHaveBeenCalledWith(
      "BV1T6PQzQErF",
      "zh-Hans",
      false,
      undefined,
      undefined,
      undefined,
      undefined,
      undefined,
      false,
      true,
      true,
    );
  });

  it.each([
    ["get_video_info", "exclude_ai_subtitles"],
    ["get_video_transcript", "exclude_ai_subtitles"],
    ["get_video_transcript", "force_asr"],
  ])("%s rejects a non-boolean %s before business work", async (name, argName) => {
    const handler = getCallToolHandler();
    const result = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 53,
      params: {
        name,
        arguments: {
          bvid_or_url: "BV1T6PQzQErF",
          [argName]: "yes",
        },
      },
    });

    expect(result.isError).toBe(true);
    expect(JSON.parse(result.content[0].text)).toMatchObject({
      code: "VALIDATION_ERROR",
    });
    expect(mockGetVideoInfoWithSubtitle).not.toHaveBeenCalled();
    expect(mockGetVideoTranscriptData).not.toHaveBeenCalled();
  });

  it("forwards explicit ASR opt-in and returns identical ASR text/structured output", async () => {
    const fixture = {
      bvid: "BV1T6PQzQErF",
      data_source: "asr" as const,
      language: "zh",
      transcript: "本地转录",
      title: "ASR fixture",
      page: 1,
      source_url: "https://www.bilibili.com/video/BV1T6PQzQErF/",
    };
    mockGetVideoTranscriptData.mockResolvedValueOnce(fixture);

    const handler = getCallToolHandler();
    const result = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 41,
      params: {
        name: "get_video_transcript",
        arguments: {
          bvid_or_url: "BV1T6PQzQErF",
          fallback_to_asr: true,
        },
      },
    });

    expect(mockGetVideoTranscriptData.mock.calls[0][8]).toBe(true);
    expect(result.structuredContent).toEqual(fixture);
    expect(JSON.parse(result.content[0].text)).toEqual(fixture);
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

  it("keeps ASR errors text-only with their bounded code", async () => {
    mockGetVideoTranscriptData.mockRejectedValueOnce(
      new AsrError("ASR_BUSY", "Another ASR transcription is active", true),
    );

    const handler = getCallToolHandler();
    const result = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 51,
      params: {
        name: "get_video_transcript",
        arguments: { bvid_or_url: "BV1T6PQzQErF", fallback_to_asr: true },
      },
    });

    expect(result.isError).toBe(true);
    expect(result).not.toHaveProperty("structuredContent");
    expect(JSON.parse(result.content[0].text).code).toBe("ASR_BUSY");
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

  it("bridges the MCP abort signal to transcript work and keeps the error text-only", async () => {
    const controller = new AbortController();
    mockGetVideoTranscriptData.mockImplementationOnce(
      (...args: unknown[]) =>
        new Promise((_resolve, reject) => {
          const signal = args.at(-1) as AbortSignal;
          signal.addEventListener(
            "abort",
            () => reject(new DOMException("aborted", "AbortError")),
            { once: true },
          );
        }),
    );

    const handler = getCallToolHandler();
    const pending = handler(
      {
        method: "tools/call",
        jsonrpc: "2.0",
        id: 61,
        params: {
          name: "get_video_transcript",
          arguments: { bvid_or_url: "BV1T6PQzQErF" },
        },
      },
      { signal: controller.signal },
    );
    controller.abort();
    const result = await pending;

    expect(mockGetVideoTranscriptData.mock.calls[0].at(-1)).toBe(
      controller.signal,
    );
    expect(result.isError).toBe(true);
    expect(result).not.toHaveProperty("structuredContent");
    expect(JSON.parse(result.content[0].text).code).toBe("UNKNOWN_ERROR");
  });

  it("does not reflect an oversized unknown tool name into the response or bounded log", async () => {
    const marker = `ATTACK_MARKER-${"x".repeat(1_024)}`;
    const logSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    try {
      const handler = getCallToolHandler();
      const result = await handler({
        method: "tools/call",
        jsonrpc: "2.0",
        id: 62,
        params: { name: marker, arguments: {} },
      });

      const response = JSON.stringify(result);
      expect(result.isError).toBe(true);
      expect(result).not.toHaveProperty("structuredContent");
      expect(JSON.parse(result.content[0].text).code).toBe("UNKNOWN_ERROR");
      expect(response).not.toContain("ATTACK_MARKER");
      expect(response).not.toContain(marker);

      expect(logSpy).toHaveBeenCalledTimes(1);
      const serializedLog = String(logSpy.mock.calls[0][0]);
      expect(Buffer.byteLength(serializedLog, "utf8")).toBeLessThanOrEqual(
        SECURITY_LIMITS.logEntryBytes,
      );
      expect(serializedLog).not.toContain("ATTACK_MARKER");
      expect(serializedLog).not.toContain(marker);
      expect(JSON.parse(serializedLog)).toMatchObject({
        message: "Error processing MCP tool",
        data: {
          error: {
            name: "Error",
            message: "Unknown MCP tool",
          },
        },
      });
    } finally {
      logSpy.mockRestore();
    }
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

describe("creator search handler validation and output", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it.each([
    ["missing query", {}],
    ["empty query", { query: "   " }],
    ["long query", { query: "a".repeat(101) }],
    ["limit below range", { query: "UP主", limit: 0 }],
    ["limit above range", { query: "UP主", limit: 11 }],
    ["fractional limit", { query: "UP主", limit: 1.5 }],
    ["string limit", { query: "UP主", limit: "5" }],
  ])("search_bilibili_creators with %s returns VALIDATION_ERROR", async (_case, args) => {
    const handler = getCallToolHandler();
    const result = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 15,
      params: {
        name: "search_bilibili_creators",
        arguments: args,
      },
    });

    expect(result.isError).toBe(true);
    expect(result).not.toHaveProperty("structuredContent");
    expect(JSON.parse(result.content[0].text).code).toBe("VALIDATION_ERROR");
    expect(mockSearchBilibiliCreators).not.toHaveBeenCalled();
  });

  it("trims the query, applies the default limit, and returns identical dual output", async () => {
    const fixture = {
      query: "UP主",
      results: [
        {
          mid: 2_468_136,
          name: "UP主一号",
          bio: "分享生活",
          avatar_url: "https://i0.hdslb.com/bfs/face/a.jpg",
          follower_count: 1_234_567,
          video_count: 42,
          level: 6,
          source_url: "https://space.bilibili.com/2468136/",
        },
      ],
    };
    mockSearchBilibiliCreators.mockResolvedValueOnce(fixture);

    const handler = getCallToolHandler();
    const result = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 16,
      params: {
        name: "search_bilibili_creators",
        arguments: { query: "  UP主  " },
      },
    });

    expect(mockSearchBilibiliCreators).toHaveBeenCalledWith("UP主", 5);
    expect(result.structuredContent).toEqual(fixture);
    expect(result.content[0].text).toBe(JSON.stringify(fixture, null, 2));
  });

  it("keeps creator search failures text-only", async () => {
    mockSearchBilibiliCreators.mockRejectedValueOnce(
      new Error("Unexpected creator search failure"),
    );

    const handler = getCallToolHandler();
    const result = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 17,
      params: {
        name: "search_bilibili_creators",
        arguments: { query: "UP主", limit: 3 },
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

describe("BVID tools reject non-string bvid_or_url", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const businessMocks: Record<string, ReturnType<typeof vi.fn>> = {
    get_video_info: mockGetVideoInfoWithSubtitle,
    get_video_comments: mockGetVideoCommentsData,
    get_video_transcript: mockGetVideoTranscriptData,
    get_video_metadata: mockGetVideoMetadataData,
    get_video_chapters: mockGetVideoChaptersData,
  };

  // Tool x input matrix: every BVID tool with number, boolean, and object
  // bvid_or_url must return the same stable typed error and never reach the
  // corresponding business mock.
  const matrix: Array<[string, string, unknown]> = [
    ["get_video_info", "number", 12345],
    ["get_video_info", "boolean", true],
    ["get_video_info", "object", { bvid: "BV1T6PQzQErF" }],
    ["get_video_comments", "number", 12345],
    ["get_video_comments", "boolean", true],
    ["get_video_comments", "object", { bvid: "BV1T6PQzQErF" }],
    ["get_video_transcript", "number", 12345],
    ["get_video_transcript", "boolean", true],
    ["get_video_transcript", "object", { bvid: "BV1T6PQzQErF" }],
    ["get_video_metadata", "number", 12345],
    ["get_video_metadata", "boolean", true],
    ["get_video_metadata", "object", { bvid: "BV1T6PQzQErF" }],
    ["get_video_chapters", "number", 12345],
    ["get_video_chapters", "boolean", true],
    ["get_video_chapters", "object", { bvid: "BV1T6PQzQErF" }],
  ];

  it.each(matrix)(
    "%s with %s bvid_or_url returns a typed VALIDATION_ERROR before any business call",
    async (toolName, _inputKind, bvidOrUrl) => {
      const handler = getCallToolHandler();
      const result = await handler({
        method: "tools/call",
        jsonrpc: "2.0",
        id: 71,
        params: {
          name: toolName,
          arguments: { bvid_or_url: bvidOrUrl },
        },
      });

      expect(result.isError).toBe(true);
      expect(result).not.toHaveProperty("structuredContent");
      const payload = JSON.parse(result.content[0].text);
      expect(payload.code).toBe("VALIDATION_ERROR");
      expect(payload.message).toBe("bvid_or_url must be a string");
      expect(JSON.stringify(result)).not.toContain("includes");
      expect(businessMocks[toolName]).not.toHaveBeenCalled();
    },
  );
});

describe("buildValidationErrorPayload genericization", () => {
  it("keeps the controlled message of a typed ValidationError", async () => {
    const { ValidationError } = await import("../src/utils/errors.js");
    const { buildValidationErrorPayload } = await import(
      "../src/server/error-response.js"
    );
    const payload = buildValidationErrorPayload(
      new ValidationError("bvid_or_url must be a string"),
    );
    expect(payload.code).toBe("VALIDATION_ERROR");
    expect(payload.message).toBe("bvid_or_url must be a string");
  });

  it("genericizes unexpected exceptions without leaking engine wording", async () => {
    const { buildValidationErrorPayload } = await import(
      "../src/server/error-response.js"
    );
    const payload = buildValidationErrorPayload(
      new Error("includes is not a function"),
    );
    expect(payload.code).toBe("VALIDATION_ERROR");
    expect(payload.message).toBe("Invalid input");
  });
});
