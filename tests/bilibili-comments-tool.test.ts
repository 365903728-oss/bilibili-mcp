import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock the client module before it's imported
const mockGetVideoComments = vi.fn();
const mockGetVideoInfo = vi.fn();

vi.mock("../src/bilibili/client.js", () => ({
  getVideoInfo: (...args: unknown[]) => mockGetVideoInfo(...args),
  getVideoComments: (...args: unknown[]) => mockGetVideoComments(...args),
}));

import { getVideoCommentsData } from "../src/bilibili/comments.js";
import { SECURITY_LIMITS } from "../src/security/limits.js";
import { cacheManager } from "../src/utils/cache.js";

function makeFakeReplies(overrides: Record<string, unknown> = {}) {
  return [
    {
      rpid: 1,
      member: { uname: "UserA", avatar: "" },
      content: { message: "First comment 05:20 nice" },
      like: 10,
      replies: [
        {
          rpid: 100,
          member: { uname: "Replier", avatar: "" },
          content: { message: "reply one" },
          like: 5,
        },
        {
          rpid: 101,
          member: { uname: "Replier2", avatar: "" },
          content: { message: "reply two" },
          like: 3,
        },
        {
          rpid: 102,
          member: { uname: "Replier3", avatar: "" },
          content: { message: "reply three" },
          like: 1,
        },
        {
          rpid: 103,
          member: { uname: "Replier4", avatar: "" },
          content: { message: "reply four" },
          like: 0,
        },
      ],
      ...overrides,
    },
  ];
}

beforeEach(() => {
  cacheManager.clear();

  mockGetVideoInfo.mockResolvedValue({
    cid: 12345,
    title: "Test Video",
    desc: "",
    owner: { name: "Author", face: "" },
    stat: { view: 0, danmaku: 0, reply: 0, favorite: 0, coin: 0, share: 0, like: 0 },
    aid: 678,
    duration: 0,
    pubdate: 0,
  });

  mockGetVideoComments.mockResolvedValue({
    replies: makeFakeReplies(),
  });
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("getVideoCommentsData - old positional API", () => {
  it("does not fetch video metadata before delegating to the comments API", async () => {
    await getVideoCommentsData("BV1T6PQzQErF");

    expect(mockGetVideoInfo).not.toHaveBeenCalled();
  });

  it("brief default: passes pageSize 10, sort 1, includeReplies true", async () => {
    await getVideoCommentsData("BV1T6PQzQErF");

    expect(mockGetVideoComments).toHaveBeenCalledWith(
      "BV1T6PQzQErF",
      1,    // page
      10,   // pageSize
      1,    // sort (hot)
      true, // includeReplies
    );
  });

  it('brief default: summary reflects processed count', async () => {
    const result = await getVideoCommentsData("BV1T6PQzQErF");

    expect(result.summary.total_comments).toBeGreaterThanOrEqual(1);
    expect(result.comments.length).toBe(result.summary.total_comments);
  });

  it('detailed default: passes pageSize 20, includes replies', async () => {
    await getVideoCommentsData("BV1T6PQzQErF", "detailed");

    expect(mockGetVideoComments).toHaveBeenCalledWith(
      "BV1T6PQzQErF",
      1,
      20,
      1,
      true,
    );
  });

  it("detailed default: includes top replies in processed result", async () => {
    const result = await getVideoCommentsData("BV1T6PQzQErF", "detailed");

    // 1 main comment + up to 3 replies = at least 4
    expect(result.comments.length).toBeGreaterThanOrEqual(4);
  });
});

describe("getVideoCommentsData - new options API", () => {
  it("explicit limit overrides detail-level-derived count", async () => {
    await getVideoCommentsData("BV1T6PQzQErF", { limit: 5 });

    expect(mockGetVideoComments).toHaveBeenCalledWith(
      "BV1T6PQzQErF",
      1,
      5,    // explicit limit
      1,    // default hot sort
      true, // default includeReplies
    );
  });

  it('explicit sort "time" passes sort 0', async () => {
    await getVideoCommentsData("BV1T6PQzQErF", { sort: "time" });

    expect(mockGetVideoComments).toHaveBeenCalledWith(
      "BV1T6PQzQErF",
      1,
      10,   // default brief pageSize
      0,    // time sort
      true,
    );
  });

  it('explicit sort "hot" passes sort 1', async () => {
    await getVideoCommentsData("BV1T6PQzQErF", { sort: "hot" });

    expect(mockGetVideoComments).toHaveBeenCalledWith(
      "BV1T6PQzQErF",
      1,
      10,
      1,    // hot sort
      true,
    );
  });

  it("explicit includeReplies false is passed through", async () => {
    mockGetVideoComments.mockResolvedValue({
      replies: makeFakeReplies(),
    });

    await getVideoCommentsData("BV1T6PQzQErF", { includeReplies: false });

    expect(mockGetVideoComments).toHaveBeenCalledWith(
      "BV1T6PQzQErF",
      1,
      10,
      1,
      false, // includeReplies false
    );
  });

  it("explicit includeReplies false: does not append child replies", async () => {
    mockGetVideoComments.mockResolvedValue({
      replies: makeFakeReplies(),
    });

    const result = await getVideoCommentsData("BV1T6PQzQErF", {
      detailLevel: "detailed",
      includeReplies: false,
    });

    // Only main comments, no extra replies
    expect(result.comments.length).toBe(1);
  });

  it("combined options: limit + sort + includeReplies all honored", async () => {
    await getVideoCommentsData("BV1T6PQzQErF", {
      detailLevel: "detailed",
      limit: 8,
      sort: "time",
      includeReplies: false,
    });

    expect(mockGetVideoComments).toHaveBeenCalledWith(
      "BV1T6PQzQErF",
      1,
      8,
      0,     // time
      false, // no replies
    );
  });
});

describe("getVideoCommentsData - cache key behavior", () => {
  it("does not share cached results between brief and detailed modes with the same limit", async () => {
    const brief = await getVideoCommentsData("BV1T6PQzQErF", {
      detailLevel: "brief",
      limit: 5,
      includeReplies: true,
    });
    const detailed = await getVideoCommentsData("BV1T6PQzQErF", {
      detailLevel: "detailed",
      limit: 5,
      includeReplies: true,
    });

    expect(brief.comments).toHaveLength(1);
    expect(detailed.comments).toHaveLength(4);
    expect(mockGetVideoComments).toHaveBeenCalledTimes(2);
  });

  it("different options produce different cache keys", async () => {
    // First call
    await getVideoCommentsData("BV1T6PQzQErF", { limit: 5, sort: "hot" });
    const callsBefore = mockGetVideoComments.mock.calls.length;

    // Different limit -> different cache key -> should call API again
    await getVideoCommentsData("BV1T6PQzQErF", { limit: 10, sort: "hot" });
    expect(mockGetVideoComments.mock.calls.length).toBe(callsBefore + 1);
  });

  it("same options reuse cache", async () => {
    await getVideoCommentsData("BV1T6PQzQErF", { limit: 3, sort: "time" });
    const callsBefore = mockGetVideoComments.mock.calls.length;

    // Same params -> same cache key -> should NOT call API again
    await getVideoCommentsData("BV1T6PQzQErF", { limit: 3, sort: "time" });
    expect(mockGetVideoComments.mock.calls.length).toBe(callsBefore);
  });
});

describe("getVideoCommentsData - pagination for limits above 20", () => {
  it("limit: 50 fetches pages 1, 2, 3 with page sizes 20, 20, 10", async () => {
    mockGetVideoComments.mockImplementation(
      async (_url: string, page: number, pageSize: number, _sort: number, _includeReplies: boolean) => {
        const start = (page - 1) * 20 + 1;
        return { replies: Array.from({ length: pageSize }, (_, i) => ({
          rpid: start + i,
          member: { uname: `User${start + i}`, avatar: "" },
          content: { message: `Comment ${start + i}` },
          like: start + i,
          replies: [],
        })) };
      },
    );

    await getVideoCommentsData("BV1T6PQzQErF", { limit: 50, includeReplies: false });

    const calls = mockGetVideoComments.mock.calls;
    expect(calls).toHaveLength(3);
    expect(calls[0][1]).toBe(1);
    expect(calls[0][2]).toBe(20);
    expect(calls[1][1]).toBe(2);
    expect(calls[1][2]).toBe(20);
    expect(calls[2][1]).toBe(3);
    expect(calls[2][2]).toBe(10);
  });

  it("limit: 50 returns exactly 50 top-level comments", async () => {
    mockGetVideoComments.mockImplementation(
      async (_url: string, page: number, pageSize: number, _sort: number, _includeReplies: boolean) => {
        const start = (page - 1) * 20 + 1;
        return { replies: Array.from({ length: pageSize }, (_, i) => ({
          rpid: start + i,
          member: { uname: `User${start + i}`, avatar: "" },
          content: { message: `Comment ${start + i}` },
          like: start + i,
          replies: [],
        })) };
      },
    );

    const result = await getVideoCommentsData("BV1T6PQzQErF", { limit: 50, includeReplies: false });

    expect(result.comments).toHaveLength(50);
    expect(result.summary.total_comments).toBe(50);
  });

  it("stops early when a page returns empty", async () => {
    mockGetVideoComments.mockImplementation(
      async (_url: string, page: number, pageSize: number, _sort: number, _includeReplies: boolean) => {
        if (page === 1) {
          return { replies: Array.from({ length: pageSize }, (_, i) => ({
            rpid: i + 1,
            member: { uname: `User${i + 1}`, avatar: "" },
            content: { message: `Comment ${i + 1}` },
            like: i + 1,
            replies: [],
          })) };
        }
        return { replies: [] };
      },
    );

    const result = await getVideoCommentsData("BV1T6PQzQErF", { limit: 50, includeReplies: false });

    expect(mockGetVideoComments).toHaveBeenCalledTimes(2);
    expect(result.comments).toHaveLength(20);
  });

  it("stops early when a page returns fewer than requested", async () => {
    mockGetVideoComments.mockImplementation(
      async (_url: string, page: number, _pageSize: number, _sort: number, _includeReplies: boolean) => {
        if (page === 1) {
          return { replies: Array.from({ length: 20 }, (_, i) => ({
            rpid: i + 1,
            member: { uname: `User${i + 1}`, avatar: "" },
            content: { message: `Comment ${i + 1}` },
            like: i + 1,
            replies: [],
          })) };
        }
        return { replies: Array.from({ length: 5 }, (_, i) => ({
          rpid: 21 + i,
          member: { uname: `User${21 + i}`, avatar: "" },
          content: { message: `Comment ${21 + i}` },
          like: 21 + i,
          replies: [],
        })) };
      },
    );

    const result = await getVideoCommentsData("BV1T6PQzQErF", { limit: 50, includeReplies: false });

    expect(mockGetVideoComments).toHaveBeenCalledTimes(2);
    expect(result.comments).toHaveLength(25);
  });

  it("limit at or below 20 still makes a single request", async () => {
    await getVideoCommentsData("BV1T6PQzQErF", { limit: 20, includeReplies: false });
    expect(mockGetVideoComments).toHaveBeenCalledTimes(1);
    expect(mockGetVideoComments).toHaveBeenCalledWith("BV1T6PQzQErF", 1, 20, 1, false);

    vi.clearAllMocks();

    await getVideoCommentsData("BV1T6PQzQErF", { limit: 5, includeReplies: false });
    expect(mockGetVideoComments).toHaveBeenCalledTimes(1);
    expect(mockGetVideoComments).toHaveBeenCalledWith("BV1T6PQzQErF", 1, 5, 1, false);
  });

  it("detailed mode with limit: 50 does not multiply reply expansion", async () => {
    const makeCommentWithReplies = (id: number) => ({
      rpid: id,
      member: { uname: `User${id}`, avatar: "" },
      content: { message: `Comment ${id}` },
      like: id,
      replies: [
        {
          rpid: id * 100,
          member: { uname: `Replier${id}`, avatar: "" },
          content: { message: `reply to ${id}` },
          like: 1,
        },
      ],
    });

    mockGetVideoComments.mockImplementation(
      async (_url: string, page: number, pageSize: number, _sort: number, _includeReplies: boolean) => {
        const start = (page - 1) * 20 + 1;
        return { replies: Array.from({ length: pageSize }, (_, i) => makeCommentWithReplies(start + i)) };
      },
    );

    const result = await getVideoCommentsData("BV1T6PQzQErF", { limit: 50, detailLevel: "detailed" });

    // 50 top-level + 50 expanded replies = 100
    expect(result.comments).toHaveLength(100);
    expect(result.summary.total_comments).toBe(100);
  });
});

describe("getVideoCommentsData - hostile upstream bounds", () => {
  it("slices an over-returned page to the caller-visible main-comment limit", async () => {
    mockGetVideoComments.mockResolvedValue({
      replies: Array.from({ length: 7 }, (_, index) => ({
        rpid: index + 1,
        member: { uname: `User${index + 1}` },
        content: { message: `Comment ${index + 1}` },
        like: index,
        replies: [],
      })),
    });

    const result = await getVideoCommentsData("BV1T6PQzQErF", {
      limit: 1,
      includeReplies: false,
    });

    expect(result.comments).toHaveLength(1);
    expect(result.summary.total_comments).toBe(1);
  });

  it("retains at most three replies per accepted main comment", async () => {
    mockGetVideoComments.mockResolvedValue({
      replies: [
        {
          rpid: 1,
          member: { uname: "Main" },
          content: { message: "Main comment" },
          like: 1,
          replies: Array.from({ length: 8 }, (_, index) => ({
            rpid: index + 10,
            member: { uname: `Reply${index}` },
            content: { message: `Reply ${index}` },
            like: index,
          })),
        },
      ],
    });

    const result = await getVideoCommentsData("BV1T6PQzQErF", {
      detailLevel: "detailed",
      limit: 1,
      includeReplies: true,
    });

    expect(result.comments).toHaveLength(4);
    expect(result.comments.map((item) => item.content)).not.toContain(
      "Reply 3",
    );
  });

  it.each([
    [
      "author",
      {
        rpid: 1,
        member: { uname: "界".repeat(43) },
        content: { message: "ok" },
        like: 0,
        replies: [],
      },
      "comment_author",
      128,
    ],
    [
      "content",
      {
        rpid: 1,
        member: { uname: "ok" },
        content: { message: "🙂".repeat(1_001) },
        like: 0,
        replies: [],
      },
      "comment_content",
      4_000,
    ],
  ])(
    "fails closed when a remote %s exceeds its UTF-8 budget",
    async (_label, row, resource, limit) => {
      mockGetVideoComments.mockResolvedValue({ replies: [row] });

      await expect(
        getVideoCommentsData("BV1T6PQzQErF", {
          limit: 1,
          includeReplies: false,
        }),
      ).rejects.toMatchObject({
        name: "ResourceLimitError",
        resource,
        limit,
      });
    },
  );

  it("rejects an aggregate comment result above one MiB before caching it", async () => {
    mockGetVideoComments.mockImplementation(
      async (_url: string, page: number, pageSize: number) => ({
        replies: Array.from({ length: pageSize }, (_, index) => ({
          rpid: (page - 1) * pageSize + index + 1,
          member: { uname: "Bounded author" },
          content: { message: "x".repeat(4_000) },
          like: 0,
          replies: [],
        })),
      }),
    );
    const cacheWrite = vi.spyOn(cacheManager, "setCommentInfo");

    try {
      await expect(
        getVideoCommentsData("BV1T6PQzQErF", {
          limit: 300,
          includeReplies: false,
        }),
      ).rejects.toMatchObject({
        name: "ResourceLimitError",
        resource: "comment_result",
        limit: SECURITY_LIMITS.commentResultBytes,
      });
      expect(cacheWrite).not.toHaveBeenCalled();
    } finally {
      cacheWrite.mockRestore();
    }
  });
});
