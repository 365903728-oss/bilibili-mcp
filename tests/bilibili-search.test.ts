import { beforeEach, describe, expect, it, vi } from "vitest";

const httpMocks = vi.hoisted(() => ({
  checkLoginStatus: vi.fn(),
  fetchWithoutWBI: vi.fn(),
}));

const credentialMocks = vi.hoisted(() => ({
  getAuthHeaders: vi.fn(),
}));

vi.mock("../src/bilibili/http.js", () => ({
  checkLoginStatus: httpMocks.checkLoginStatus,
  fetchWithoutWBI: httpMocks.fetchWithoutWBI,
}));

vi.mock("../src/utils/credentials.js", () => ({
  credentialManager: {
    getAuthHeaders: credentialMocks.getAuthHeaders,
  },
}));

const { BilibiliAPIError, NetworkError } = await import(
  "../src/utils/errors.js"
);
const { searchBilibiliVideos } = await import("../src/bilibili/search.js");

describe("searchBilibiliVideos", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    credentialMocks.getAuthHeaders.mockReturnValue({ Cookie: "configured" });
    httpMocks.checkLoginStatus.mockResolvedValue({ isLogin: true });
  });

  it("checks authentication, performs one bounded search, and normalizes candidates", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValue({
      result: [
        {
          type: "video",
          bvid: "BV1T6PQzQErF",
          title: 'Learn <em class="keyword">MCP</em>',
          author: "Creator",
          duration: "123:28",
          pubdate: 1_700_000_000,
          play: 12_345.9,
          description: "🙂".repeat(201),
        },
        {
          type: "ketang",
          bvid: "BV1xx411c7mD",
          title: "Paid course",
        },
        {
          type: "video",
          bvid: "not-a-bvid",
          title: "Invalid BVID",
        },
        {
          type: "video",
          bvid: "BV1xx411c7mD",
          title: '<em class="keyword">   </em>',
        },
        {
          type: "video",
          bvid: "BV1xx411c7mD",
          title: "Second result",
          author: 42,
          duration: "1:02:03",
          pubdate: "invalid",
          play: -1,
          description: '<em class="keyword">Second</em> description',
        },
        {
          type: "video",
          bvid: "BV1Q541167Qg",
          title: "Beyond limit",
          duration: "27:6",
        },
      ],
    });

    const result = await searchBilibiliVideos("  MCP  ", 2);

    expect(credentialMocks.getAuthHeaders).toHaveBeenCalledTimes(1);
    expect(httpMocks.checkLoginStatus).toHaveBeenCalledTimes(1);
    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(1);
    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledWith(
      "/x/web-interface/wbi/search/type",
      {
        search_type: "video",
        keyword: "MCP",
        page: 1,
        page_size: 2,
      },
      { Cookie: "configured" },
    );
    expect(result).toEqual({
      query: "MCP",
      results: [
        {
          bvid: "BV1T6PQzQErF",
          title: "Learn MCP",
          author: "Creator",
          duration_seconds: 7_408,
          published_at: "2023-11-14T22:13:20.000Z",
          view_count: 12_345,
          description: `${"🙂".repeat(200)}…`,
          source_url: "https://www.bilibili.com/video/BV1T6PQzQErF/",
        },
        {
          bvid: "BV1xx411c7mD",
          title: "Second result",
          author: "",
          duration_seconds: 3_723,
          published_at: "",
          view_count: 0,
          description: "Second description",
          source_url: "https://www.bilibili.com/video/BV1xx411c7mD/",
        },
      ],
    });
  });

  it("parses variable-width minutes and falls back safely for malformed metadata", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValue({
      result: [
        {
          type: "video",
          bvid: "BV1Q541167Qg",
          title: "Short seconds",
          duration: "27:6",
          pubdate: 0,
          play: "unknown",
        },
        {
          type: "video",
          bvid: "BV1xx411c7mD",
          title: "Malformed duration",
          duration: "1:99:03",
          pubdate: -1,
          play: Number.NaN,
        },
      ],
    });

    const result = await searchBilibiliVideos("duration", 5);

    expect(result.results.map((candidate) => candidate.duration_seconds)).toEqual([
      1_626,
      0,
    ]);
    expect(result.results.map((candidate) => candidate.published_at)).toEqual([
      "",
      "",
    ]);
    expect(result.results.map((candidate) => candidate.view_count)).toEqual([
      0,
      0,
    ]);
    expect(result.results.map((candidate) => candidate.description)).toEqual([
      "",
      "",
    ]);
  });

  it("fails before login or search when no usable Cookie is configured", async () => {
    credentialMocks.getAuthHeaders.mockReturnValue({ Cookie: "   " });

    await expect(searchBilibiliVideos("MCP", 5)).rejects.toMatchObject({
      name: "BilibiliAPIError",
      code: "COOKIE_EXPIRED",
    });
    expect(httpMocks.checkLoginStatus).not.toHaveBeenCalled();
    expect(httpMocks.fetchWithoutWBI).not.toHaveBeenCalled();
  });

  it("fails before search when the configured Cookie is not logged in", async () => {
    httpMocks.checkLoginStatus.mockResolvedValue({ isLogin: false });

    const error = await searchBilibiliVideos("MCP", 5).catch(
      (caught: unknown) => caught,
    );

    expect(error).toBeInstanceOf(BilibiliAPIError);
    expect(error).toMatchObject({ code: "COOKIE_EXPIRED" });
    expect(httpMocks.checkLoginStatus).toHaveBeenCalledTimes(1);
    expect(httpMocks.fetchWithoutWBI).not.toHaveBeenCalled();
  });

  it("preserves login-check network failures", async () => {
    const error = new NetworkError("Network request failed");
    httpMocks.checkLoginStatus.mockRejectedValue(error);

    await expect(searchBilibiliVideos("MCP", 5)).rejects.toBe(error);
    expect(httpMocks.fetchWithoutWBI).not.toHaveBeenCalled();
  });

  it("does not convert search request failures into empty success", async () => {
    const error = new NetworkError("Search request failed");
    httpMocks.fetchWithoutWBI.mockRejectedValue(error);

    await expect(searchBilibiliVideos("MCP", 5)).rejects.toBe(error);
  });

  it.each([
    ["missing result", {}],
    ["non-array result", { result: "unexpected" }],
    ["empty result", { result: [] }],
  ])("returns a successful empty result for %s", async (_case, payload) => {
    httpMocks.fetchWithoutWBI.mockResolvedValue(payload);

    await expect(searchBilibiliVideos("nothing", 5)).resolves.toEqual({
      query: "nothing",
      results: [],
    });
  });
});
