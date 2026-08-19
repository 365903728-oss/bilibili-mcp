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
const { runWithOperationSignal } = await import(
  "../src/security/operation-context.js"
);
const { searchBilibiliCreators, searchBilibiliVideos } = await import(
  "../src/bilibili/search.js"
);

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
          description: `${"🙂".repeat(127)}…`,
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
    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(1);
  });

  it("does not add an endpoint retry for a raw system-coded failure", async () => {
    const error = Object.assign(new Error("Socket reset"), {
      code: "ECONNRESET",
    });
    httpMocks.fetchWithoutWBI.mockRejectedValue(error);

    await expect(searchBilibiliVideos("MCP", 5)).rejects.toBe(error);
    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(1);
  });

  it("does not add an endpoint retry for an HTTP status failure", async () => {
    const error = new NetworkError(
      "Service unavailable",
      undefined,
      undefined,
      503,
    );
    httpMocks.fetchWithoutWBI.mockRejectedValue(error);

    await expect(searchBilibiliVideos("MCP", 5)).rejects.toBe(error);
    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(1);
  });

  it("aborts during shape-retry backoff without a second request", async () => {
    const controller = new AbortController();
    httpMocks.fetchWithoutWBI.mockResolvedValue({});

    const searchPromise = runWithOperationSignal(controller.signal, () =>
      searchBilibiliVideos("MCP", 5),
    );
    await vi.waitFor(() => {
      expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(1);
    });
    controller.abort();

    await expect(searchPromise).rejects.toMatchObject({ name: "AbortError" });
    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(1);
  });

  it("returns an explicit empty result without an extra request", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValue({ result: [] });

    await expect(searchBilibiliVideos("nothing", 5)).resolves.toEqual({
      query: "nothing",
      results: [],
    });
    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(1);
  });

  it("retries a missing result once before failing closed", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValue({});

    await expect(searchBilibiliVideos("nothing", 5)).rejects.toMatchObject({
      name: "UpstreamResponseError",
    });
    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(2);
  });

  it("retries a non-array result once before failing closed", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValue({ result: "unexpected" });

    await expect(searchBilibiliVideos("nothing", 5)).rejects.toMatchObject({
      name: "UpstreamResponseError",
    });
    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(2);
  });

  it("recovers when the retry returns an explicit empty result", async () => {
    httpMocks.fetchWithoutWBI
      .mockResolvedValueOnce({})
      .mockResolvedValueOnce({ result: [] });

    await expect(searchBilibiliVideos("nothing", 5)).resolves.toEqual({
      query: "nothing",
      results: [],
    });
    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(2);
  });
});

describe("searchBilibiliCreators", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    credentialMocks.getAuthHeaders.mockReturnValue({ Cookie: "configured" });
    httpMocks.checkLoginStatus.mockResolvedValue({ isLogin: true });
  });

  it("checks authentication, performs one bounded creator search, and normalizes candidates", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValue({
      result: [
        {
          mid: 2_468_136,
          uname: '<em class="keyword">UP</em>主一号',
          usign: "分享<em class=\"keyword\">生活</em>",
          upic: "https://i0.hdslb.com/bfs/face/a.jpg",
          fans: 1_234_567,
          videos: 42,
          level: 6,
        },
        {
          mid: -1,
          uname: "Invalid mid",
        },
        {
          mid: 1.5,
          uname: "Fractional mid",
        },
        {
          mid: Number.MAX_SAFE_INTEGER + 1,
          uname: "Unsafe mid",
        },
        {
          mid: 0,
          uname: "Zero mid",
        },
        {
          mid: 7,
          uname: '<em class="keyword">   </em>',
        },
        {
          mid: 123,
          uname: "UP主一号",
          usign: 42,
          upic: "https://i0.hdslb.com/bfs/face/b.jpg",
          fans: -5,
          videos: "many",
          level: "six",
        },
        {
          mid: 456,
          uname: "Beyond limit",
        },
      ],
    });

    const result = await searchBilibiliCreators("  UP主  ", 2);

    expect(credentialMocks.getAuthHeaders).toHaveBeenCalledTimes(1);
    expect(httpMocks.checkLoginStatus).toHaveBeenCalledTimes(1);
    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(1);
    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledWith(
      "/x/web-interface/wbi/search/type",
      {
        search_type: "bili_user",
        keyword: "UP主",
        page: 1,
        page_size: 2,
      },
      { Cookie: "configured" },
    );
    expect(result).toEqual({
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
        {
          mid: 123,
          name: "UP主一号",
          bio: "",
          avatar_url: "https://i0.hdslb.com/bfs/face/b.jpg",
          follower_count: 0,
          video_count: 0,
          level: 0,
          source_url: "https://space.bilibili.com/123/",
        },
      ],
    });
  });

  it("normalizes malformed profile counts and level to zero while preserving valid non-negative safe integers", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValue({
      result: [
        {
          mid: 1,
          uname: "Fractional facts",
          fans: 99.5,
          videos: 3.1,
          level: 5.9,
        },
        {
          mid: 2,
          uname: "Unsafe facts",
          fans: Number.MAX_SAFE_INTEGER + 1,
          videos: Number.MAX_SAFE_INTEGER + 2,
          level: Number.MAX_SAFE_INTEGER + 3,
        },
        {
          mid: 3,
          uname: "Non-finite facts",
          fans: Number.POSITIVE_INFINITY,
          videos: Number.NaN,
          level: Number.NEGATIVE_INFINITY,
        },
        {
          mid: 4,
          uname: "Valid facts",
          fans: 0,
          videos: Number.MAX_SAFE_INTEGER,
          level: 6,
        },
      ],
    });

    const result = await searchBilibiliCreators("facts", 4);

    expect(result.results).toEqual([
      {
        mid: 1,
        name: "Fractional facts",
        bio: "",
        avatar_url: "",
        follower_count: 0,
        video_count: 0,
        level: 0,
        source_url: "https://space.bilibili.com/1/",
      },
      {
        mid: 2,
        name: "Unsafe facts",
        bio: "",
        avatar_url: "",
        follower_count: 0,
        video_count: 0,
        level: 0,
        source_url: "https://space.bilibili.com/2/",
      },
      {
        mid: 3,
        name: "Non-finite facts",
        bio: "",
        avatar_url: "",
        follower_count: 0,
        video_count: 0,
        level: 0,
        source_url: "https://space.bilibili.com/3/",
      },
      {
        mid: 4,
        name: "Valid facts",
        bio: "",
        avatar_url: "",
        follower_count: 0,
        video_count: Number.MAX_SAFE_INTEGER,
        level: 6,
        source_url: "https://space.bilibili.com/4/",
      },
    ]);
  });

  it("fails before login or search when no usable Cookie is configured", async () => {
    credentialMocks.getAuthHeaders.mockReturnValue({ Cookie: "   " });

    await expect(searchBilibiliCreators("UP主", 5)).rejects.toMatchObject({
      name: "BilibiliAPIError",
      code: "COOKIE_EXPIRED",
    });
    expect(httpMocks.checkLoginStatus).not.toHaveBeenCalled();
    expect(httpMocks.fetchWithoutWBI).not.toHaveBeenCalled();
  });

  it("fails before search when the configured Cookie is not logged in", async () => {
    httpMocks.checkLoginStatus.mockResolvedValue({ isLogin: false });

    await expect(searchBilibiliCreators("UP主", 5)).rejects.toMatchObject({
      code: "COOKIE_EXPIRED",
    });
    expect(httpMocks.checkLoginStatus).toHaveBeenCalledTimes(1);
    expect(httpMocks.fetchWithoutWBI).not.toHaveBeenCalled();
  });

  it("returns an explicit empty result without an extra request", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValue({ result: [] });

    await expect(searchBilibiliCreators("nobody", 5)).resolves.toEqual({
      query: "nobody",
      results: [],
    });
    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(1);
  });

  it("retries a missing or non-array result once before failing closed", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValue({});
    await expect(searchBilibiliCreators("nobody", 5)).rejects.toMatchObject({
      name: "UpstreamResponseError",
    });
    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(2);
  });

  it("does not convert raw request failures into empty success", async () => {
    const error = new NetworkError("Search request failed");
    httpMocks.fetchWithoutWBI.mockRejectedValue(error);

    await expect(searchBilibiliCreators("UP主", 5)).rejects.toBe(error);
    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(1);
  });

  it("fails closed when the response exceeds the item limit", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValue({
      result: Array.from({ length: 101 }, (_, index) => ({
        mid: index + 1,
        uname: `Creator ${index}`,
      })),
    });

    await expect(searchBilibiliCreators("UP主", 5)).rejects.toMatchObject({
      name: "ResourceLimitError",
      resource: "creator_search_items",
      limit: 100,
    });
    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(1);
  });
});
