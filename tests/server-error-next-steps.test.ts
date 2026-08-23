import { describe, expect, it, vi } from "vitest";

import { getMcpHandler } from "./helpers/mcp.js";

const mockGetVideoInfoWithSubtitle = vi.fn();
const mockGetVideoTranscriptData = vi.fn();
const mockGetVideoCommentsData = vi.fn();
const mockSearchBilibiliVideos = vi.fn();
const mockSearchBilibiliCreators = vi.fn();
const mockListBilibiliFavoriteVideos = vi.fn();
const mockGetBilibiliCreatorContent = vi.fn();

vi.mock("../src/bilibili/subtitle.js", () => ({
  getVideoInfoWithSubtitle: (...args: unknown[]) =>
    mockGetVideoInfoWithSubtitle(...args),
  getVideoTranscriptData: (...args: unknown[]) =>
    mockGetVideoTranscriptData(...args),
}));

vi.mock("../src/bilibili/metadata.js", () => ({
  getVideoMetadataData: vi.fn(),
}));

vi.mock("../src/bilibili/comments.js", () => ({
  getVideoCommentsData: (...args: unknown[]) =>
    mockGetVideoCommentsData(...args),
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

vi.mock("../src/bilibili/creator-content.js", () => ({
  getBilibiliCreatorContent: (...args: unknown[]) =>
    mockGetBilibiliCreatorContent(...args),
}));

const httpMock = vi.hoisted(() => ({
  checkLoginStatus: vi.fn(async () => ({ isLogin: false })),
}));

vi.mock("../src/bilibili/http.js", () => ({
  checkLoginStatus: httpMock.checkLoginStatus,
}));

const {
  AsrError,
  BilibiliAPIError,
  CommentsDisabledError,
  NetworkError,
  NoSubtitleError,
  PaidVideoError,
  TimeoutError,
  UpstreamResponseError,
} = await import("../src/utils/errors.js");

const { credentialManager } = await import("../src/utils/credentials.js");

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

function expectStructuredError(
  payload: Record<string, unknown>,
  code: string,
  options: { retryable: boolean; userActionRequired: boolean },
) {
  expect(payload.error).toBe(true);
  expect(payload.code).toBe(code);
  expect(typeof payload.category).toBe("string");
  expect(typeof payload.message).toBe("string");
  expect(typeof payload.message_en).toBe("string");
  expect(typeof payload.message_zh).toBe("string");
  expect(Array.isArray(payload.next_steps)).toBe(true);
  expect(Array.isArray(payload.next_steps_en)).toBe(true);
  expect(Array.isArray(payload.next_steps_zh)).toBe(true);
  expect(payload.next_steps_en).toEqual(payload.next_steps);
  expect(payload.retryable).toBe(options.retryable);
  expect(payload.user_action_required).toBe(options.userActionRequired);
}

describe("generic MCP error credential next_steps", () => {
  it("adds code and next_steps when a content tool throws COOKIE_EXPIRED", async () => {
    mockGetVideoInfoWithSubtitle.mockRejectedValueOnce(
      new BilibiliAPIError("Cookie expired", "COOKIE_EXPIRED"),
    );

    const handler = getCallToolHandler();
    const response = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 1,
      params: {
        name: "get_video_info",
        arguments: { bvid_or_url: "BV1T6PQzQErF" },
      },
    });
    const payload = JSON.parse(response.content[0].text);

    expect(response.isError).toBe(true);
    expectStructuredError(payload, "COOKIE_EXPIRED", {
      retryable: false,
      userActionRequired: true,
    });
    expect(payload.next_steps).toContain(
      "Run: npx -y @xzxzzx/bilibili-mcp@latest config",
    );
    expect(payload.next_steps_en).toEqual(payload.next_steps);
    expect(payload.next_steps_zh.join(" ")).toContain(
      "npx -y @xzxzzx/bilibili-mcp@latest config",
    );
  });

  it("returns safe credential recovery guidance for authenticated search", async () => {
    mockSearchBilibiliVideos.mockRejectedValueOnce(
      new BilibiliAPIError("Cookie expired", "COOKIE_EXPIRED"),
    );

    const handler = getCallToolHandler();
    const response = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 2,
      params: {
        name: "search_bilibili_videos",
        arguments: { query: "MCP" },
      },
    });
    const payload = JSON.parse(response.content[0].text);

    expect(response.isError).toBe(true);
    expect(response).not.toHaveProperty("structuredContent");
    expectStructuredError(payload, "COOKIE_EXPIRED", {
      retryable: false,
      userActionRequired: true,
    });
    expect(payload.next_steps_en.join(" ")).toContain(
      "npx -y @xzxzzx/bilibili-mcp@latest config",
    );
    expect(JSON.stringify(payload)).not.toContain("configured");
  });

  it("returns safe credential recovery guidance for authenticated creator search", async () => {
    mockSearchBilibiliCreators.mockRejectedValueOnce(
      new BilibiliAPIError("Cookie expired", "COOKIE_EXPIRED"),
    );

    const handler = getCallToolHandler();
    const response = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 5,
      params: {
        name: "search_bilibili_creators",
        arguments: { query: "UP主" },
      },
    });
    const payload = JSON.parse(response.content[0].text);

    expect(response.isError).toBe(true);
    expect(response).not.toHaveProperty("structuredContent");
    expectStructuredError(payload, "COOKIE_EXPIRED", {
      retryable: false,
      userActionRequired: true,
    });
    expect(payload.next_steps_en.join(" ")).toContain(
      "npx -y @xzxzzx/bilibili-mcp@latest config",
    );
    expect(JSON.stringify(payload)).not.toContain("configured");
  });

  it("maps malformed search responses to a text-only upstream error", async () => {
    mockSearchBilibiliVideos.mockRejectedValueOnce(
      new UpstreamResponseError("Invalid search response"),
    );

    const handler = getCallToolHandler();
    const response = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 3,
      params: {
        name: "search_bilibili_videos",
        arguments: { query: "MCP" },
      },
    });
    const payload = JSON.parse(response.content[0].text);

    expect(response.isError).toBe(true);
    expect(response).not.toHaveProperty("structuredContent");
    expectStructuredError(payload, "UPSTREAM_RESPONSE_INVALID", {
      retryable: false,
      userActionRequired: false,
    });
  });

  it("returns safe credential recovery guidance for authenticated favorites discovery", async () => {
    mockListBilibiliFavoriteVideos.mockRejectedValueOnce(
      new BilibiliAPIError("Cookie expired", "COOKIE_EXPIRED"),
    );

    const handler = getCallToolHandler();
    const response = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 4,
      params: {
        name: "list_bilibili_favorite_videos",
        arguments: {},
      },
    });
    const payload = JSON.parse(response.content[0].text);

    expect(response.isError).toBe(true);
    expect(response).not.toHaveProperty("structuredContent");
    expectStructuredError(payload, "COOKIE_EXPIRED", {
      retryable: false,
      userActionRequired: true,
    });
    expect(payload.next_steps_en.join(" ")).toContain(
      "npx -y @xzxzzx/bilibili-mcp@latest config",
    );
    expect(JSON.stringify(payload)).not.toMatch(/SESSDATA|bili_jct|DedeUserID/i);
  });

  it("returns safe credential recovery guidance for authenticated creator content", async () => {
    mockGetBilibiliCreatorContent.mockRejectedValueOnce(
      new BilibiliAPIError("Cookie expired", "COOKIE_EXPIRED"),
    );

    const handler = getCallToolHandler();
    const response = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 6,
      params: {
        name: "get_bilibili_creator_content",
        arguments: { mid: 2_088_259_175, section: "videos" },
      },
    });
    const payload = JSON.parse(response.content[0].text);

    expect(response.isError).toBe(true);
    expect(response).not.toHaveProperty("structuredContent");
    expectStructuredError(payload, "COOKIE_EXPIRED", {
      retryable: false,
      userActionRequired: true,
    });
    expect(payload.next_steps_en.join(" ")).toContain(
      "npx -y @xzxzzx/bilibili-mcp@latest config",
    );
    expect(JSON.stringify(payload)).not.toMatch(/SESSDATA|bili_jct|DedeUserID/i);
  });

  it("returns resource-generic access guidance for Favorites access denial", async () => {
    mockListBilibiliFavoriteVideos.mockRejectedValueOnce(
      new BilibiliAPIError("Access denied", "ACCESS_DENIED"),
    );

    const handler = getCallToolHandler();
    const response = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 5,
      params: {
        name: "list_bilibili_favorite_videos",
        arguments: {},
      },
    });
    const payload = JSON.parse(response.content[0].text);

    expect(response.isError).toBe(true);
    expectStructuredError(payload, "ACCESS_DENIED", {
      retryable: false,
      userActionRequired: true,
    });
    expect(payload.next_steps_en.join(" ")).toContain("resource");
    expect(payload.next_steps_zh.join(" ")).toContain("资源");
  });

  it("adds bilingual next_steps when transcript subtitles are unavailable", async () => {
    mockGetVideoTranscriptData.mockRejectedValueOnce(
      new NoSubtitleError("No subtitles"),
    );

    const handler = getCallToolHandler();
    const response = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 1,
      params: {
        name: "get_video_transcript",
        arguments: { bvid_or_url: "BV1T6PQzQErF" },
      },
    });
    const payload = JSON.parse(response.content[0].text);

    expect(response.isError).toBe(true);
    expectStructuredError(payload, "SUBTITLE_UNAVAILABLE", {
      retryable: false,
      userActionRequired: true,
    });
    expect(payload.next_steps_en.join(" ")).toContain(
      "fallback_to_description: true",
    );
    expect(payload.next_steps_zh.join(" ")).toContain(
      "fallback_to_description: true",
    );
  });
});

describe("structured MCP error categories", () => {
  it("explains standard Fake-IP DNS and lets the user choose a safe remedy", async () => {
    mockGetVideoTranscriptData.mockRejectedValueOnce(
      new AsrError(
        "ASR_FAKE_IP_DNS",
        "safe bounded Fake-IP diagnosis",
      ),
    );
    const handler = getCallToolHandler();
    const response = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 29,
      params: {
        name: "get_video_transcript",
        arguments: { bvid_or_url: "BV1T6PQzQErF", force_asr: true },
      },
    });
    const payload = JSON.parse(response.content[0].text);
    const rendered = JSON.stringify(payload);

    expect(response.isError).toBe(true);
    expectStructuredError(payload, "ASR_FAKE_IP_DNS", {
      retryable: false,
      userActionRequired: true,
    });
    expect(payload.category).toBe("network");
    expect(`${payload.message_en} ${payload.next_steps_en.join(" ")}`).toMatch(
      /198\.18\.0\.0\/15.*Fake-IP.*reject/is,
    );
    expect(`${payload.message_zh} ${payload.next_steps_zh.join(" ")}`).toMatch(
      /198\.18\.0\.0\/15.*Fake-IP.*拒绝/is,
    );
    expect(payload.next_steps_en.join(" ")).toMatch(
      /choose.*fake-ip-filter.*\*\.bilivideo\.com.*\*\.bilivideo\.cn.*reconnect/is,
    );
    expect(payload.next_steps_zh.join(" ")).toMatch(
      /选择.*fake-ip-filter.*\*\.bilivideo\.com.*\*\.bilivideo\.cn.*重连/is,
    );
    expect(rendered).toContain("Do not allowlist 198.18.0.0/15");
    expect(rendered).not.toMatch(/SESSDATA|bili_jct|DedeUserID|token=|audio\.m4s|Authorization/i);
  });

  it.each([
    ["ASR_NOT_READY", false, true],
    ["ASR_AUDIO_UNAVAILABLE", true, false],
    ["ASR_LIMIT_EXCEEDED", false, true],
    ["ASR_BUSY", true, false],
    ["ASR_TRANSCRIPTION_TIMEOUT", true, false],
    ["ASR_TRANSCRIPTION_FAILED", true, false],
    ["ASR_OUTPUT_INVALID", false, false],
  ] as const)("maps %s to bounded bilingual runtime guidance", async (code, retryable, userActionRequired) => {
    mockGetVideoTranscriptData.mockRejectedValueOnce(
      new AsrError(code, `safe ${code}`, retryable),
    );
    const handler = getCallToolHandler();
    const response = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 30,
      params: {
        name: "get_video_transcript",
        arguments: { bvid_or_url: "BV1T6PQzQErF", fallback_to_asr: true },
      },
    });
    const payload = JSON.parse(response.content[0].text);

    expect(response.isError).toBe(true);
    expect(response).not.toHaveProperty("structuredContent");
    expectStructuredError(payload, code, { retryable, userActionRequired });
    expect(JSON.stringify(payload)).not.toMatch(/SESSDATA|bili_jct|DedeUserID|token=|audio\.m4s/i);
  });

  it("maps handler validation errors to VALIDATION_ERROR", async () => {
    const handler = getCallToolHandler();
    const response = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 1,
      params: {
        name: "get_video_comments",
        arguments: { bvid_or_url: "BV1T6PQzQErF", limit: 51 },
      },
    });
    const payload = JSON.parse(response.content[0].text);

    expect(response.isError).toBe(true);
    expectStructuredError(payload, "VALIDATION_ERROR", {
      retryable: false,
      userActionRequired: true,
    });
    expect(payload.message).toBe("Comment limit must be between 1 and 50");
  });

  it.each([
    {
      name: "network failures",
      error: new NetworkError(
        "HTTP 503: Service Unavailable",
        undefined,
        "https://api.bilibili.com/x",
        503,
      ),
      code: "NETWORK_ERROR",
      retryable: true,
      userActionRequired: false,
      zhNeedle: "网络",
    },
    {
      name: "network timeouts",
      error: new TimeoutError("Request timeout: 30000ms", 30000),
      code: "NETWORK_TIMEOUT",
      retryable: true,
      userActionRequired: false,
      zhNeedle: "超时",
    },
    {
      name: "API rate limits",
      error: new NetworkError(
        "HTTP 429: Too Many Requests",
        undefined,
        "https://api.bilibili.com/x",
        429,
      ),
      code: "API_RATE_LIMITED",
      retryable: true,
      userActionRequired: true,
      zhNeedle: "频率",
    },
    {
      name: "access denied API errors",
      error: new BilibiliAPIError("Access denied", "ACCESS_DENIED"),
      code: "ACCESS_DENIED",
      retryable: false,
      userActionRequired: true,
      zhNeedle: "访问",
    },
    {
      name: "paid videos",
      error: new PaidVideoError("Paid video"),
      code: "PAID_VIDEO",
      retryable: false,
      userActionRequired: true,
      zhNeedle: "付费",
    },
    {
      name: "disabled comments",
      error: new CommentsDisabledError("Comments disabled"),
      code: "COMMENTS_DISABLED",
      retryable: false,
      userActionRequired: false,
      zhNeedle: "评论",
    },
  ])(
    "returns structured guidance for $name",
    async ({ error, code, retryable, userActionRequired, zhNeedle }) => {
      mockGetVideoInfoWithSubtitle.mockRejectedValueOnce(error);

      const handler = getCallToolHandler();
      const response = await handler({
        method: "tools/call",
        jsonrpc: "2.0",
        id: 1,
        params: {
          name: "get_video_info",
          arguments: { bvid_or_url: "BV1T6PQzQErF" },
        },
      });
      const payload = JSON.parse(response.content[0].text);

      expect(response.isError).toBe(true);
      expectStructuredError(payload, code, { retryable, userActionRequired });
      expect(payload.next_steps_zh.join(" ")).toContain(zhNeedle);
    },
  );

  it("maps comments-disabled errors from get_video_comments to COMMENTS_DISABLED", async () => {
    mockGetVideoCommentsData.mockRejectedValueOnce(
      new CommentsDisabledError("Comments disabled"),
    );

    const handler = getCallToolHandler();
    const response = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 1,
      params: {
        name: "get_video_comments",
        arguments: { bvid_or_url: "BV1T6PQzQErF" },
      },
    });
    const payload = JSON.parse(response.content[0].text);

    expect(response.isError).toBe(true);
    expectStructuredError(payload, "COMMENTS_DISABLED", {
      retryable: false,
      userActionRequired: false,
    });
    expect(payload.next_steps_zh.join(" ")).toContain("评论");
  });

  it("maps generic Bilibili API errors to BILIBILI_API_ERROR", async () => {
    mockGetVideoInfoWithSubtitle.mockRejectedValueOnce(
      new BilibiliAPIError("Bilibili returned an error", "API_ERROR"),
    );

    const handler = getCallToolHandler();
    const response = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 1,
      params: {
        name: "get_video_info",
        arguments: { bvid_or_url: "BV1T6PQzQErF" },
      },
    });
    const payload = JSON.parse(response.content[0].text);

    expect(response.isError).toBe(true);
    expectStructuredError(payload, "BILIBILI_API_ERROR", {
      retryable: false,
      userActionRequired: false,
    });
    expect(payload.details).toEqual({ api_code: "API_ERROR" });
  });
});

describe("check_bilibili_credentials network errors", () => {
  it("returns NETWORK_ERROR when checkLoginStatus rejects with NetworkError", async () => {
    const spy = vi.spyOn(credentialManager, "getCredentialSource").mockReturnValue("env");
    try {
      httpMock.checkLoginStatus.mockRejectedValueOnce(
        new NetworkError("Network request failed"),
      );

      const handler = getCallToolHandler();
      const response = await handler({
        method: "tools/call",
        jsonrpc: "2.0",
        id: 1,
        params: {
          name: "check_bilibili_credentials",
          arguments: {},
        },
      });
      const payload = JSON.parse(response.content[0].text);

      expect(response.isError).toBe(true);
      expectStructuredError(payload, "NETWORK_ERROR", {
        retryable: true,
        userActionRequired: false,
      });
      expect(JSON.stringify(payload)).not.toMatch(/SESSDATA|bili_jct|DedeUserID/i);
    } finally {
      spy.mockRestore();
    }
  });
});
