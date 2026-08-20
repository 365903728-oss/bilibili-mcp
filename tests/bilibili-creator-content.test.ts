import { beforeEach, describe, expect, it, vi } from "vitest";

const httpMocks = vi.hoisted(() => ({
  checkLoginStatus: vi.fn(),
  fetchWithoutWBI: vi.fn(),
  fetchWithWBI: vi.fn(),
}));

const credentialMocks = vi.hoisted(() => ({
  getAuthHeaders: vi.fn(),
}));

vi.mock("../src/bilibili/http.js", () => ({
  checkLoginStatus: httpMocks.checkLoginStatus,
  fetchWithoutWBI: httpMocks.fetchWithoutWBI,
  fetchWithWBI: httpMocks.fetchWithWBI,
}));

vi.mock("../src/utils/credentials.js", () => ({
  credentialManager: {
    getAuthHeaders: credentialMocks.getAuthHeaders,
  },
}));

const {
  BilibiliAPIError,
  ResourceLimitError,
  UpstreamResponseError,
  ValidationError,
} = await import("../src/utils/errors.js");
const {
  decodeCreatorContentCursor,
  encodeCreatorContentCursor,
  getBilibiliCreatorContent,
} = await import("../src/bilibili/creator-content.js");
const { handleToolCall } = await import("../src/server/tool-handlers.js");

const MID = 2_088_259_175;

function validCursor(
  mid = MID,
  section: "overview" | "videos" | "collections" | "series" = "videos",
  page = 1,
  containerId?: number,
): string {
  return encodeCreatorContentCursor(mid, section, page, containerId);
}

describe("creator content cursor encode/decode", () => {
  it("round-trips a videos cursor and stays canonical", () => {
    const cursor = validCursor(MID, "videos", 3);
    expect(cursor.length).toBeGreaterThan(0);
    expect(cursor.length).toBeLessThanOrEqual(256);
    expect(decodeCreatorContentCursor(cursor)).toEqual({
      mid: MID,
      section: "videos",
      page: 3,
    });
    expect(encodeCreatorContentCursor(MID, "videos", 3)).toBe(cursor);
  });

  it("binds a Collection member cursor to its container identity", () => {
    const cursor = encodeCreatorContentCursor(MID, "collections", 2, 1903592);

    expect(decodeCreatorContentCursor(cursor)).toEqual({
      mid: MID,
      section: "collections",
      page: 2,
      container_id: 1903592,
    });
  });

  it("rejects invalid mid/section/page at encode time", () => {
    expect(() => encodeCreatorContentCursor(0, "videos", 1)).toThrow(
      ValidationError,
    );
    expect(() =>
      encodeCreatorContentCursor(1.5, "videos", 1),
    ).toThrow(ValidationError);
    expect(() =>
      encodeCreatorContentCursor(MID, "archive", 1),
    ).toThrow(ValidationError);
    expect(() => encodeCreatorContentCursor(MID, "videos", 0)).toThrow(
      ValidationError,
    );
    expect(() =>
      encodeCreatorContentCursor(MID, "videos", 1.5),
    ).toThrow(ValidationError);
  });
});

describe("getBilibiliCreatorContent pre-network validation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    credentialMocks.getAuthHeaders.mockReturnValue({ Cookie: "configured" });
    httpMocks.checkLoginStatus.mockResolvedValue({ isLogin: true });
  });

  it.each([
    ["zero", 0],
    ["negative", -5],
    ["float", 1.5],
    ["string", "123"],
    ["NaN", Number.NaN],
    ["Infinity", Number.POSITIVE_INFINITY],
  ])("rejects invalid mid (%s) before credentials or network", async (_, mid) => {
    await expect(
      getBilibiliCreatorContent(mid as number, "overview"),
    ).rejects.toThrow(ValidationError);
    expect(credentialMocks.getAuthHeaders).not.toHaveBeenCalled();
    expect(httpMocks.checkLoginStatus).not.toHaveBeenCalled();
    expect(httpMocks.fetchWithWBI).not.toHaveBeenCalled();
  });

  it.each([
    ["empty", ""],
    ["unknown", "archive"],
    ["upper case", "VIDEOS"],
    ["number", 42],
  ])("rejects invalid section (%s) before credentials or network", async (_, section) => {
    await expect(
      getBilibiliCreatorContent(MID, section as "overview" | "videos"),
    ).rejects.toThrow(ValidationError);
    expect(credentialMocks.getAuthHeaders).not.toHaveBeenCalled();
    expect(httpMocks.fetchWithWBI).not.toHaveBeenCalled();
  });

  it("rejects a cursor on the overview section before credentials or network", async () => {
    await expect(
      getBilibiliCreatorContent(MID, "overview", validCursor(MID, "videos")),
    ).rejects.toThrow(ValidationError);
    expect(credentialMocks.getAuthHeaders).not.toHaveBeenCalled();
    expect(httpMocks.fetchWithWBI).not.toHaveBeenCalled();
  });

  it("rejects a container identity outside Collection/Series before credentials or network", async () => {
    await expect(
      getBilibiliCreatorContent(MID, "videos", undefined, 1903592),
    ).rejects.toThrow(ValidationError);
    expect(credentialMocks.getAuthHeaders).not.toHaveBeenCalled();
    expect(httpMocks.checkLoginStatus).not.toHaveBeenCalled();
    expect(httpMocks.fetchWithWBI).not.toHaveBeenCalled();
    expect(httpMocks.fetchWithoutWBI).not.toHaveBeenCalled();
  });

  it.each([0, -1, 1.5, Number.MAX_SAFE_INTEGER + 1])(
    "rejects invalid container identity %s before credentials or network",
    async (containerId) => {
      await expect(
        getBilibiliCreatorContent(
          MID,
          "collections",
          undefined,
          containerId,
        ),
      ).rejects.toThrow(ValidationError);
      expect(credentialMocks.getAuthHeaders).not.toHaveBeenCalled();
      expect(httpMocks.fetchWithoutWBI).not.toHaveBeenCalled();
    },
  );

  it("rejects cross-container cursor reuse before credentials or network", async () => {
    await expect(
      getBilibiliCreatorContent(
        MID,
        "collections",
        validCursor(MID, "collections", 2, 1_903_592),
        1_903_593,
      ),
    ).rejects.toThrow(ValidationError);
    expect(credentialMocks.getAuthHeaders).not.toHaveBeenCalled();
    expect(httpMocks.fetchWithoutWBI).not.toHaveBeenCalled();
  });

  it.each([
    ["non-string", 42],
    ["empty", ""],
    ["overlong", "A".repeat(257)],
    ["non-base64url", "abc=="],
    ["non-base64url padding", validCursor() + "="],
    ["non-canonical base64url", "AB"],
    ["invalid JSON payload", "Zm9v"],
    ["non-object payload", "MTIz"],
    ["unsupported version", "eyJ2ZXJzaW9uIjoyLCJtaWQiOjEsInNlY3Rpb24iOiJ2aWRlb3MiLCJwYWdlIjoxfQ"],
    ["missing page", "eyJ2ZXJzaW9uIjoxLCJtaWQiOjEsInNlY3Rpb24iOiJ2aWRlb3MifQ"],
    ["non-positive page", "eyJ2ZXJzaW9uIjoxLCJtaWQiOjEsInNlY3Rpb24iOiJ2aWRlb3MiLCJwYWdlIjowfQ"],
    ["unsafe page", "eyJ2ZXJzaW9uIjoxLCJtaWQiOjEsInNlY3Rpb24iOiJ2aWRlb3MiLCJwYWdlIjo5MDA3MTk5MjU0NzQwOTkxfQ"],
  ])("rejects malformed videos cursor (%s) before credentials or network", async (_, cursor) => {
    await expect(
      getBilibiliCreatorContent(MID, "videos", cursor as string),
    ).rejects.toThrow(ValidationError);
    expect(credentialMocks.getAuthHeaders).not.toHaveBeenCalled();
    expect(httpMocks.checkLoginStatus).not.toHaveBeenCalled();
    expect(httpMocks.fetchWithWBI).not.toHaveBeenCalled();
  });

  it("rejects a cross-creator cursor before credentials or network", async () => {
    const otherMid = MID + 1;
    await expect(
      getBilibiliCreatorContent(MID, "videos", validCursor(otherMid)),
    ).rejects.toThrow(ValidationError);
    expect(credentialMocks.getAuthHeaders).not.toHaveBeenCalled();
    expect(httpMocks.fetchWithWBI).not.toHaveBeenCalled();
  });

  it("rejects a cross-section cursor before credentials or network", async () => {
    await expect(
      getBilibiliCreatorContent(
        MID,
        "videos",
        validCursor(MID, "overview"),
      ),
    ).rejects.toThrow(ValidationError);
    expect(credentialMocks.getAuthHeaders).not.toHaveBeenCalled();
    expect(httpMocks.fetchWithWBI).not.toHaveBeenCalled();
  });
});

function profileData(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    mid: MID,
    name: "Test Creator",
    face: "https://i0.hdslb.com/bfs/face/avatar.jpg",
    sign: "Creator bio",
    fans: 987_654,
    level: 6,
    videos: 42,
    ...overrides,
  };
}

function catalogPage(
  rows: unknown[],
  page = 1,
  count?: number,
  tlist?: Record<string, unknown>,
): Record<string, unknown> {
  const list: Record<string, unknown> = { vlist: rows };
  if (tlist !== undefined) {
    list.tlist = tlist;
  }
  const data: Record<string, unknown> = { list };
  if (count !== undefined) {
    data.page = { pn: page, ps: 20, count };
  }
  return data;
}

function catalogRow(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    bvid: "BV1T6PQzQErF",
    title: "Creator video one",
    description: "First description",
    pic: "https://i0.hdslb.com/bfs/archive/cover-1.jpg",
    typeid: 138,
    length: "1:02:03",
    created: 1_700_000_000,
    author: "Test Creator",
    mid: MID,
    play: 12_345,
    comment: 67,
    video_review: 89,
    is_charging_arc: 1,
    ...overrides,
  };
}

function containerListPage(
  seasons: unknown[],
  series: unknown[],
  page = 1,
  total = seasons.length + series.length,
): Record<string, unknown> {
  return {
    items_lists: {
      page: { page_num: page, page_size: 20, total },
      seasons_list: seasons,
      series_list: series,
    },
  };
}

function collectionItem(
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    meta: {
      mid: MID,
      season_id: 1_903_592,
      name: "合集·多人实况",
      description: "一起玩的实况",
      total: 20,
      ...overrides,
    },
  };
}

function seriesItem(
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    meta: {
      mid: MID,
      series_id: 4_684_427,
      name: "青春旅行团",
      description: "旅行系列",
      total: 13,
      ...overrides,
    },
  };
}

function memberRow(
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    bvid: "BV1T6PQzQErF",
    title: "Container video",
    desc: "Member description",
    pic: "https://i0.hdslb.com/bfs/archive/member.jpg",
    duration: 125,
    pubdate: 1_700_000_000,
    stat: { view: 1234, danmaku: 56 },
    ugc_pay: 1,
    ...overrides,
  };
}

function collectionMemberPage(
  archives: unknown[],
  page = 1,
  total = archives.length,
  metaOverrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    archives,
    meta: {
      mid: MID,
      season_id: 1_903_592,
      name: "合集·多人实况",
      description: "一起玩的实况",
      total,
      ...metaOverrides,
    },
    page: { page_num: page, page_size: 20, total },
  };
}

function seriesMetadata(
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    meta: {
      mid: MID,
      series_id: 4_684_427,
      name: "青春旅行团",
      description: "旅行系列",
      total: 13,
      ...overrides,
    },
  };
}

function seriesMemberPage(
  archives: unknown[],
  page = 1,
  total = archives.length,
): Record<string, unknown> {
  return {
    archives,
    page: { num: page, size: 20, total },
  };
}

describe("getBilibiliCreatorContent Collection containers", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    credentialMocks.getAuthHeaders.mockReturnValue({ Cookie: "configured" });
    httpMocks.checkLoginStatus.mockResolvedValue({ isLogin: true });
  });

  it("lists one bounded Collection container page without fetching members", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce(
      containerListPage([collectionItem()], [], 1, 1),
    );

    const result = await getBilibiliCreatorContent(MID, "collections");

    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(1);
    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledWith(
      "/x/polymer/web-space/seasons_series_list",
      { mid: MID, page_num: 1, page_size: 20 },
      { Cookie: "configured" },
    );
    expect(httpMocks.fetchWithWBI).not.toHaveBeenCalled();
    expect(result).toEqual({
      mid: MID,
      section: "collections",
      mode: "containers",
      page: 1,
      collections: [
        {
          collection_id: 1_903_592,
          name: "合集·多人实况",
          description: "一起玩的实况",
          member_count: 20,
        },
      ],
      skipped_count: 0,
      live_state: "live",
    });
  });

  it("returns equivalent structured and JSON text output through the MCP handler", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce(
      containerListPage([collectionItem()], [], 1, 1),
    );

    const result = await handleToolCall("get_bilibili_creator_content", {
      mid: MID,
      section: "collections",
    });

    expect(result.structuredContent).toMatchObject({
      mid: MID,
      section: "collections",
      mode: "containers",
      collections: [{ collection_id: 1_903_592 }],
    });
    const text = result.content[0] as { type: "text"; text: string };
    expect(JSON.parse(text.text)).toEqual(result.structuredContent);
  });

  it("continues a combined upstream page even when it contains only Series", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce(
      containerListPage([], Array.from({ length: 20 }, () => seriesItem()), 1, 21),
    );

    const result = await getBilibiliCreatorContent(MID, "collections");

    expect(result).toMatchObject({
      collections: [],
      skipped_count: 0,
      next_cursor: validCursor(MID, "collections", 2),
    });
  });

  it("rejects a container page whose upstream page size changed", async () => {
    const data = containerListPage([collectionItem()], []);
    (data.items_lists as { page: { page_size: number } }).page.page_size = 50;
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce(data);

    await expect(
      getBilibiliCreatorContent(MID, "collections"),
    ).rejects.toThrow(UpstreamResponseError);
  });

  it.each([
    ["malformed payload", {}, UpstreamResponseError],
    [
      "oversized combined page",
      containerListPage(
        Array.from({ length: 21 }, () => collectionItem()),
        [],
        1,
        21,
      ),
      ResourceLimitError,
    ],
  ])("fails explicitly for %s", async (_, payload, expectedError) => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce(payload);

    await expect(
      getBilibiliCreatorContent(MID, "collections"),
    ).rejects.toThrow(expectedError);
  });

  it("skips a Collection whose sanitized name is empty", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce(
      containerListPage([collectionItem({ name: "\u0000\u202e" })], []),
    );

    await expect(
      getBilibiliCreatorContent(MID, "collections"),
    ).resolves.toMatchObject({ collections: [], skipped_count: 1 });
  });

  it("returns one selected Collection's Video memberships with context", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce(
      collectionMemberPage([memberRow()]),
    );

    const result = await getBilibiliCreatorContent(
      MID,
      "collections",
      undefined,
      1_903_592,
    );

    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(1);
    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledWith(
      "/x/polymer/web-space/seasons_archives_list",
      {
        mid: MID,
        season_id: 1_903_592,
        sort_reverse: "false",
        page_num: 1,
        page_size: 20,
      },
      { Cookie: "configured" },
    );
    expect(result).toEqual({
      mid: MID,
      section: "collections",
      mode: "members",
      page: 1,
      selected_collection: {
        collection_id: 1_903_592,
        name: "合集·多人实况",
        description: "一起玩的实况",
        member_count: 1,
      },
      members: [
        {
          bvid: "BV1T6PQzQErF",
          title: "Container video",
          description: "Member description",
          cover_url: "https://i0.hdslb.com/bfs/archive/member.jpg",
          duration_seconds: 125,
          published_at: "2023-11-14T22:13:20.000Z",
          view_count: 1234,
          danmaku_count: 56,
          is_charge_video: true,
          access: "unknown",
          source_url: "https://www.bilibili.com/video/BV1T6PQzQErF/",
        },
      ],
      skipped_count: 0,
      live_state: "live",
    });
  });

  it("counts malformed members without suppressing a bound next cursor", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce(
      collectionMemberPage([memberRow(), memberRow({ bvid: "invalid" })], 1, 21),
    );

    const result = await getBilibiliCreatorContent(
      MID,
      "collections",
      undefined,
      1_903_592,
    );

    expect(result).toMatchObject({
      skipped_count: 1,
      next_cursor: validCursor(MID, "collections", 2, 1_903_592),
    });
    expect(result.mode === "members" && result.members).toHaveLength(1);
  });

  it.each([
    ["malformed payload", {}, UpstreamResponseError],
    [
      "oversized member page",
      collectionMemberPage(Array.from({ length: 21 }, () => memberRow())),
      ResourceLimitError,
    ],
    [
      "mismatched Collection ownership",
      collectionMemberPage([], 1, 0, { mid: MID + 1 }),
      UpstreamResponseError,
    ],
  ])("fails explicitly for %s", async (_, payload, expectedError) => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce(payload);

    await expect(
      getBilibiliCreatorContent(
        MID,
        "collections",
        undefined,
        1_903_592,
      ),
    ).rejects.toThrow(expectedError);
  });

  it("propagates upstream Collection API failures", async () => {
    const upstream = new BilibiliAPIError("risk control", "-352");
    httpMocks.fetchWithoutWBI.mockRejectedValueOnce(upstream);

    await expect(
      getBilibiliCreatorContent(MID, "collections"),
    ).rejects.toBe(upstream);
  });
});

describe("getBilibiliCreatorContent Series containers", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    credentialMocks.getAuthHeaders.mockReturnValue({ Cookie: "configured" });
    httpMocks.checkLoginStatus.mockResolvedValue({ isLogin: true });
  });

  it("keeps Series containers separate from Collections", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce(
      containerListPage([collectionItem()], [seriesItem()], 1, 2),
    );

    const result = await getBilibiliCreatorContent(MID, "series");

    expect(result).toEqual({
      mid: MID,
      section: "series",
      mode: "containers",
      page: 1,
      series: [
        {
          series_id: 4_684_427,
          name: "青春旅行团",
          description: "旅行系列",
          member_count: 13,
        },
      ],
      skipped_count: 0,
      live_state: "live",
    });
  });

  it("revalidates Series ownership before returning one member page", async () => {
    httpMocks.fetchWithoutWBI
      .mockResolvedValueOnce(seriesMetadata({ total: 1 }))
      .mockResolvedValueOnce(seriesMemberPage([memberRow()], 1, 1));

    const result = await getBilibiliCreatorContent(
      MID,
      "series",
      undefined,
      4_684_427,
    );

    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(2);
    expect(httpMocks.fetchWithoutWBI).toHaveBeenNthCalledWith(
      1,
      "/x/series/series",
      { series_id: 4_684_427 },
      { Cookie: "configured" },
    );
    expect(httpMocks.fetchWithoutWBI).toHaveBeenNthCalledWith(
      2,
      "/x/series/archives",
      {
        mid: MID,
        series_id: 4_684_427,
        only_normal: "true",
        sort: "desc",
        pn: 1,
        ps: 20,
      },
      { Cookie: "configured" },
    );
    expect(result).toEqual({
      mid: MID,
      section: "series",
      mode: "members",
      page: 1,
      selected_series: {
        series_id: 4_684_427,
        name: "青春旅行团",
        description: "旅行系列",
        member_count: 1,
      },
      members: [
        {
          bvid: "BV1T6PQzQErF",
          title: "Container video",
          description: "Member description",
          cover_url: "https://i0.hdslb.com/bfs/archive/member.jpg",
          duration_seconds: 125,
          published_at: "2023-11-14T22:13:20.000Z",
          view_count: 1234,
          danmaku_count: 56,
          is_charge_video: true,
          access: "unknown",
          source_url: "https://www.bilibili.com/video/BV1T6PQzQErF/",
        },
      ],
      skipped_count: 0,
      live_state: "live",
    });
  });

  it("stops before member lookup when Series ownership does not match", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce(
      seriesMetadata({ mid: MID + 1 }),
    );

    await expect(
      getBilibiliCreatorContent(
        MID,
        "series",
        undefined,
        4_684_427,
      ),
    ).rejects.toThrow(UpstreamResponseError);
    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(1);
  });

  it("skips a Series whose sanitized name is empty", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce(
      containerListPage([], [seriesItem({ name: "\u0000\u202e" })]),
    );

    await expect(
      getBilibiliCreatorContent(MID, "series"),
    ).resolves.toMatchObject({ series: [], skipped_count: 1 });
  });

  it.each([
    ["malformed", {}, UpstreamResponseError],
    [
      "oversized",
      seriesMemberPage(Array.from({ length: 21 }, () => memberRow())),
      ResourceLimitError,
    ],
  ])("fails explicitly for a %s Series member page", async (_, payload, expectedError) => {
    httpMocks.fetchWithoutWBI
      .mockResolvedValueOnce(seriesMetadata())
      .mockResolvedValueOnce(payload);

    await expect(
      getBilibiliCreatorContent(
        MID,
        "series",
        undefined,
        4_684_427,
      ),
    ).rejects.toThrow(expectedError);
  });

  it("preserves the same BVID in separate Collection and Series memberships", async () => {
    httpMocks.fetchWithoutWBI
      .mockResolvedValueOnce(collectionMemberPage([memberRow()]))
      .mockResolvedValueOnce(seriesMetadata({ total: 1 }))
      .mockResolvedValueOnce(seriesMemberPage([memberRow()]));

    const collection = await getBilibiliCreatorContent(
      MID,
      "collections",
      undefined,
      1_903_592,
    );
    const series = await getBilibiliCreatorContent(
      MID,
      "series",
      undefined,
      4_684_427,
    );

    expect(collection.mode === "members" && collection.members[0]?.bvid).toBe(
      "BV1T6PQzQErF",
    );
    expect(series.mode === "members" && series.members[0]?.bvid).toBe(
      "BV1T6PQzQErF",
    );
  });
});

describe("getBilibiliCreatorContent overview", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    credentialMocks.getAuthHeaders.mockReturnValue({ Cookie: "configured" });
    httpMocks.checkLoginStatus.mockResolvedValue({ isLogin: true });
  });

  it("normalizes the upstream profile and count facts without a catalog probe", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce(profileData());

    const result = await getBilibiliCreatorContent(MID, "overview");

    expect(httpMocks.fetchWithWBI).toHaveBeenCalledTimes(1);
    expect(httpMocks.fetchWithWBI).toHaveBeenCalledWith(
      "/x/space/wbi/acc/info",
      { mid: MID },
      { Cookie: "configured" },
    );
    expect(result).toEqual({
      mid: MID,
      section: "overview",
      name: "Test Creator",
      bio: "Creator bio",
      avatar_url: "https://i0.hdslb.com/bfs/face/avatar.jpg",
      follower_count: 987_654,
      level: 6,
      video_count: 42,
      live_state: "live",
    });
  });

  it("runs exactly one bounded arc/search count probe when acc/info lacks a count", async () => {
    httpMocks.fetchWithWBI
      .mockResolvedValueOnce(profileData({ videos: undefined }))
      .mockResolvedValueOnce(catalogPage([], 1, 137));

    const result = await getBilibiliCreatorContent(MID, "overview");

    expect(httpMocks.fetchWithWBI).toHaveBeenCalledTimes(2);
    expect(httpMocks.fetchWithWBI).toHaveBeenNthCalledWith(
      2,
      "/x/space/wbi/arc/search",
      { mid: MID, pn: 1, ps: 1, order: "pubdate", tid: 0, keyword: "" },
      { Cookie: "configured" },
    );
    expect(result).toMatchObject({ video_count: 137, live_state: "live" });
  });

  it("defensively normalizes missing profile facts without inventing counts", async () => {
    httpMocks.fetchWithWBI
      .mockResolvedValueOnce(profileData({ sign: "", face: 42, fans: -1, level: "x", videos: "nope" }))
      .mockResolvedValueOnce(catalogPage([], 1, 7));

    const result = await getBilibiliCreatorContent(MID, "overview");

    expect(result).toEqual({
      mid: MID,
      section: "overview",
      name: "Test Creator",
      bio: "",
      avatar_url: "",
      level: 0,
      video_count: 7,
      live_state: "live",
    });
  });

  it("omits follower_count unless a valid upstream fans fact exists", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      profileData({ fans: undefined, videos: 42 }),
    );

    const result = await getBilibiliCreatorContent(MID, "overview");

    expect(result).toMatchObject({ video_count: 42, live_state: "live" });
    expect(
      (result as Record<string, unknown>).follower_count,
    ).toBeUndefined();
  });

  it("omits follower_count and probes the count when acc/info provides neither fans nor videos", async () => {
    httpMocks.fetchWithWBI
      .mockResolvedValueOnce(profileData({ fans: undefined, videos: undefined }))
      .mockResolvedValueOnce(catalogPage([], 1, 9));

    const result = await getBilibiliCreatorContent(MID, "overview");

    expect(httpMocks.fetchWithWBI).toHaveBeenCalledTimes(2);
    expect(result).toMatchObject({ video_count: 9 });
    expect(
      (result as Record<string, unknown>).follower_count,
    ).toBeUndefined();
  });

  it("fails explicitly when the profile mid does not match the requested creator", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce(profileData({ mid: MID + 1 }));

    await expect(
      getBilibiliCreatorContent(MID, "overview"),
    ).rejects.toThrow(UpstreamResponseError);
  });

  it("fails explicitly on a malformed profile payload", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce({});

    await expect(
      getBilibiliCreatorContent(MID, "overview"),
    ).rejects.toThrow(UpstreamResponseError);
  });

  it("fails explicitly when the count probe response is malformed", async () => {
    httpMocks.fetchWithWBI
      .mockResolvedValueOnce(profileData({ videos: undefined }))
      .mockResolvedValueOnce({ data: { list: { vlist: [] } } });

    await expect(
      getBilibiliCreatorContent(MID, "overview"),
    ).rejects.toThrow(UpstreamResponseError);
  });
});

describe("getBilibiliCreatorContent videos", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    credentialMocks.getAuthHeaders.mockReturnValue({ Cookie: "configured" });
    httpMocks.checkLoginStatus.mockResolvedValue({ isLogin: true });
  });

  it("requests exactly one newest-first catalog page and normalizes rows", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      catalogPage([catalogRow(), catalogRow({ bvid: "BV1Q541167Qg", title: "Second" })], 1, 2, {
        "138": { tid: 138, name: "科技" },
      }),
    );

    const result = await getBilibiliCreatorContent(MID, "videos");

    expect(httpMocks.fetchWithWBI).toHaveBeenCalledTimes(1);
    expect(httpMocks.fetchWithWBI).toHaveBeenCalledWith(
      "/x/space/wbi/arc/search",
      { mid: MID, pn: 1, ps: 20, order: "pubdate", tid: 0, keyword: "" },
      { Cookie: "configured" },
    );
    expect(result).toEqual({
      mid: MID,
      section: "videos",
      page: 1,
      videos_total: 2,
      videos: [
        {
          bvid: "BV1T6PQzQErF",
          title: "Creator video one",
          description: "First description",
          cover_url: "https://i0.hdslb.com/bfs/archive/cover-1.jpg",
          category_id: 138,
          category: "科技",
          duration_seconds: 3_723,
          published_at: "2023-11-14T22:13:20.000Z",
          author: "Test Creator",
          view_count: 12_345,
          danmaku_count: 89,
          reply_count: 67,
          is_charge_video: true,
          access: "unknown",
          source_url: "https://www.bilibili.com/video/BV1T6PQzQErF/",
        },
        {
          bvid: "BV1Q541167Qg",
          title: "Second",
          description: "First description",
          cover_url: "https://i0.hdslb.com/bfs/archive/cover-1.jpg",
          category_id: 138,
          category: "科技",
          duration_seconds: 3_723,
          published_at: "2023-11-14T22:13:20.000Z",
          author: "Test Creator",
          view_count: 12_345,
          danmaku_count: 89,
          reply_count: 67,
          is_charge_video: true,
          access: "unknown",
          source_url: "https://www.bilibili.com/video/BV1Q541167Qg/",
        },
      ],
      skipped_count: 0,
      live_state: "live",
    });
  });

  it("preserves upstream row order and skips invalid rows with an explicit count", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      catalogPage(
        [
          catalogRow(),
          catalogRow({ bvid: "not-a-bvid", title: "Bad BVID" }),
          catalogRow({ bvid: "BV1xx411c7mD", title: 42 }),
          catalogRow({ bvid: "BV1xx411c7mD", title: "   " }),
          catalogRow({ bvid: "BV1f84y1k7S3", title: "Second valid" }),
        ],
        1,
        5,
      ),
    );

    const result = await getBilibiliCreatorContent(MID, "videos");

    expect(result).toMatchObject({
      videos_total: 5,
      videos: [
        { bvid: "BV1T6PQzQErF" },
        { bvid: "BV1f84y1k7S3" },
      ],
      skipped_count: 3,
    });
  });

  it("omits engagement and charge fields when upstream does not provide valid values", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      catalogPage(
        [catalogRow({ play: -1, comment: "many", video_review: undefined, is_pay: 0, is_charging_arc: 0, elec_arc_type: 0 })],
        1,
        1,
      ),
    );

    const result = await getBilibiliCreatorContent(MID, "videos");

    expect(result).toMatchObject({
      videos: [
        {
          bvid: "BV1T6PQzQErF",
          access: "unknown",
        },
      ],
    });
    const row = (result as { videos: Record<string, unknown>[] }).videos[0];
    expect(row.view_count).toBeUndefined();
    expect(row.danmaku_count).toBeUndefined();
    expect(row.reply_count).toBeUndefined();
    expect(row.is_charge_video).toBeUndefined();
  });

  it("parses the bounded human duration length string, including minutes greater than 59", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      catalogPage(
        [
          catalogRow({ bvid: "BV1Q541167Qg", title: "H:MM:SS", length: "1:02:33" }),
          catalogRow({ bvid: "BV1xx411c7mD", title: "MM:SS over an hour", length: "75:30" }),
          catalogRow({ bvid: "BV1f84y1k7S3", title: "Minutes only", length: "3:45" }),
        ],
        1,
        3,
      ),
    );

    const result = await getBilibiliCreatorContent(MID, "videos");

    expect(result).toMatchObject({
      videos: [
        { bvid: "BV1Q541167Qg", duration_seconds: 3_753 },
        { bvid: "BV1xx411c7mD", duration_seconds: 4_530 },
        { bvid: "BV1f84y1k7S3", duration_seconds: 225 },
      ],
    });
  });

  it("falls back to numeric duration only when length is malformed, and to 0 when both are unsafe", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      catalogPage(
        [
          catalogRow({ bvid: "BV1Q541167Qg", title: "Malformed length", length: "abc" }),
          catalogRow({ bvid: "BV1xx411c7mD", title: "Four parts", length: "1:2:3:4" }),
          catalogRow({ bvid: "BV1f84y1k7S3", title: "Non-string length", length: 42 }),
          catalogRow({ bvid: "BV1T6PQzQE44", title: "Oversized parts", length: "99999999999999999999:00" }),
        ],
        1,
        4,
      ),
    );

    const result = await getBilibiliCreatorContent(MID, "videos");

    expect(result).toMatchObject({
      videos: [
        { bvid: "BV1Q541167Qg", duration_seconds: 0 },
        { bvid: "BV1xx411c7mD", duration_seconds: 0 },
        { bvid: "BV1f84y1k7S3", duration_seconds: 0 },
        { bvid: "BV1T6PQzQE44", duration_seconds: 0 },
      ],
    });
  });

  it("prefers length but accepts numeric duration as a compatibility fallback", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      catalogPage(
        [
          catalogRow({ bvid: "BV1Q541167Qg", title: "Length wins", length: "0:05", duration: 999 }),
          catalogRow({ bvid: "BV1xx411c7mD", title: "Duration fallback", length: "", duration: 3_723 }),
        ],
        1,
        2,
      ),
    );

    const result = await getBilibiliCreatorContent(MID, "videos");

    expect(result).toMatchObject({
      videos: [
        { bvid: "BV1Q541167Qg", duration_seconds: 5 },
        { bvid: "BV1xx411c7mD", duration_seconds: 3_723 },
      ],
    });
  });

  it("accepts typeid as the category identifier with type_id only as a fallback", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      catalogPage(
        [
          catalogRow({ bvid: "BV1Q541167Qg", title: "typeid only", typeid: 138, type_id: undefined }),
          catalogRow({ bvid: "BV1xx411c7mD", title: "typeid wins", typeid: 1, type_id: 999 }),
          catalogRow({ bvid: "BV1f84y1k7S3", title: "type_id fallback", typeid: undefined, type_id: 138 }),
          catalogRow({ bvid: "BV1T6PQzQE44", title: "No category", typeid: undefined, type_id: undefined }),
        ],
        1,
        4,
      ),
    );

    const result = await getBilibiliCreatorContent(MID, "videos");

    expect(result).toMatchObject({
      videos: [
        { bvid: "BV1Q541167Qg", category_id: 138 },
        { bvid: "BV1xx411c7mD", category_id: 1 },
        { bvid: "BV1f84y1k7S3", category_id: 138 },
        { bvid: "BV1T6PQzQE44" },
      ],
    });
    expect(
      (result as { videos: Record<string, unknown>[] }).videos[3].category_id,
    ).toBeUndefined();
  });

  it("resolves category names from the page-level tlist mapping once per page, omitting invalid mappings", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      catalogPage(
        [
          catalogRow({ bvid: "BV1Q541167Qg", title: "Mapped" }),
          catalogRow({ bvid: "BV1xx411c7mD", title: "Missing mapping", typeid: 119 }),
          catalogRow({ bvid: "BV1f84y1k7S3", title: "Malformed name", typeid: 99 }),
          catalogRow({ bvid: "BV1T6PQzQE44", title: "Oversized name", typeid: 77 }),
          catalogRow({ bvid: "BV1i4a411s7p", title: "Blank name", typeid: 66 }),
          catalogRow({ bvid: "BV1J3x411w7F", title: "Row tag ignored", tag: "旧字段" }),
          catalogRow({ bvid: "BV1bK4y1t7bG", title: "No typeid", typeid: undefined, type_id: undefined }),
        ],
        1,
        6,
        {
          "138": { tid: 138, name: "科技" },
          "99": { tid: 99, name: 42 },
          // 65 字节超过 64 字节的类别名上限，映射条目必须被跳过。
          "77": { tid: 77, name: "x".repeat(65) },
          "66": { tid: 66, name: "   " },
          "55": "not a record",
        },
      ),
    );

    const result = await getBilibiliCreatorContent(MID, "videos");

    expect(httpMocks.fetchWithWBI).toHaveBeenCalledTimes(1);
    expect(result).toMatchObject({
      videos: [
        { bvid: "BV1Q541167Qg", category_id: 138, category: "科技" },
        { bvid: "BV1xx411c7mD", category_id: 119 },
        { bvid: "BV1f84y1k7S3", category_id: 99 },
        { bvid: "BV1T6PQzQE44", category_id: 77 },
        { bvid: "BV1i4a411s7p", category_id: 66 },
        // 行级 tag 不再作为类别来源；类别名只来自页面级 tlist 映射。
        { bvid: "BV1J3x411w7F", category_id: 138, category: "科技" },
        { bvid: "BV1bK4y1t7bG" },
      ],
      skipped_count: 0,
    });
    const videos = (result as { videos: Record<string, unknown>[] }).videos;
    expect(videos[1].category).toBeUndefined();
    expect(videos[2].category).toBeUndefined();
    expect(videos[3].category).toBeUndefined();
    expect(videos[4].category).toBeUndefined();
    expect(videos[6].category).toBeUndefined();
    expect(videos[6].category_id).toBeUndefined();
  });

  it("omits category names when tlist is absent or malformed without throwing or probing", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      catalogPage([catalogRow({ bvid: "BV1Q541167Qg", title: "No tlist" })], 1, 1, 42),
    );

    const result = await getBilibiliCreatorContent(MID, "videos");

    expect(httpMocks.fetchWithWBI).toHaveBeenCalledTimes(1);
    expect(result).toMatchObject({
      videos: [{ bvid: "BV1Q541167Qg", category_id: 138 }],
      skipped_count: 0,
    });
    expect(
      (result as { videos: Record<string, unknown>[] }).videos[0].category,
    ).toBeUndefined();
  });

  it("uses created as the publish timestamp with create only as a fallback", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      catalogPage(
        [
          catalogRow({ bvid: "BV1Q541167Qg", title: "created only", created: 1_700_000_000, create: undefined }),
          catalogRow({ bvid: "BV1xx411c7mD", title: "created wins", created: 1_700_000_001, create: 1 }),
          catalogRow({ bvid: "BV1f84y1k7S3", title: "create fallback", created: undefined, create: 1_700_000_000 }),
          catalogRow({ bvid: "BV1T6PQzQE44", title: "invalid created", created: 0, create: 1_700_000_000 }),
        ],
        1,
        4,
      ),
    );

    const result = await getBilibiliCreatorContent(MID, "videos");

    expect(result).toMatchObject({
      videos: [
        { bvid: "BV1Q541167Qg", published_at: "2023-11-14T22:13:20.000Z" },
        { bvid: "BV1xx411c7mD", published_at: "2023-11-14T22:13:21.000Z" },
        { bvid: "BV1f84y1k7S3", published_at: "2023-11-14T22:13:20.000Z" },
        { bvid: "BV1T6PQzQE44", published_at: "2023-11-14T22:13:20.000Z" },
      ],
    });
  });

  it.each([
    ["is_pay boolean", { is_pay: true }],
    ["is_pay numeric", { is_pay: 1 }],
    ["is_charging_arc numeric", { is_charging_arc: 1 }],
    ["elec_arc_type", { elec_arc_type: 2 }],
    ["elec_arc_type 1", { elec_arc_type: 1 }],
    ["compatibility is_charge_video", { is_charge_video: true }],
  ])("marks is_charge_video from explicit upstream evidence (%s) while keeping access unknown", async (_, evidence) => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      catalogPage(
        [catalogRow({ bvid: "BV1Q541167Qg", title: "Charged", ...evidence })],
        1,
        1,
      ),
    );

    const result = await getBilibiliCreatorContent(MID, "videos");

    expect(result).toMatchObject({
      videos: [{ bvid: "BV1Q541167Qg", is_charge_video: true, access: "unknown" }],
    });
  });

  it("never sets is_charge_video from falsy or absent evidence, and never infers access", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      catalogPage(
        [
          catalogRow({ bvid: "BV1Q541167Qg", title: "All falsy", is_pay: 0, is_charging_arc: 0, elec_arc_type: 0, is_charge_video: false }),
          catalogRow({ bvid: "BV1xx411c7mD", title: "No evidence", is_pay: undefined, is_charging_arc: undefined, elec_arc_type: undefined, is_charge_video: undefined }),
        ],
        1,
        2,
      ),
    );

    const result = await getBilibiliCreatorContent(MID, "videos");

    expect(result).toMatchObject({
      videos: [
        { bvid: "BV1Q541167Qg", access: "unknown" },
        { bvid: "BV1xx411c7mD", access: "unknown" },
      ],
    });
    expect(
      (result as { videos: Record<string, unknown>[] }).videos[0].is_charge_video,
    ).toBeUndefined();
    expect(
      (result as { videos: Record<string, unknown>[] }).videos[1].is_charge_video,
    ).toBeUndefined();
  });

  it("keeps collaboration rows whose row mid differs, with the row author", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      catalogPage(
        [
          catalogRow({ bvid: "BV1Q541167Qg", title: "Collaboration", mid: MID + 1, author: "Co-Author" }),
          catalogRow({ bvid: "BV1xx411c7mD", title: "No mid field", mid: undefined, author: "Ghost Author" }),
        ],
        1,
        2,
      ),
    );

    const result = await getBilibiliCreatorContent(MID, "videos");

    expect(result).toMatchObject({
      videos: [
        { bvid: "BV1Q541167Qg", author: "Co-Author", access: "unknown" },
        { bvid: "BV1xx411c7mD", author: "Ghost Author", access: "unknown" },
      ],
      skipped_count: 0,
    });
  });

  it("emits a next cursor when the upstream count proves continuation", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      catalogPage(Array.from({ length: 20 }, (_, i) => catalogRow({ bvid: `BV1T6PQzQE${String(i).padStart(2, "0")}`, title: `Row ${i}` })), 1, 45),
    );

    const result = await getBilibiliCreatorContent(MID, "videos", validCursor());

    expect(result).toMatchObject({ next_cursor: validCursor(MID, "videos", 2) });
  });

  it("does not emit a next cursor when the count proves the page is final", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      catalogPage(Array.from({ length: 20 }, (_, i) => catalogRow({ bvid: `BV1T6PQzQE${String(i).padStart(2, "0")}`, title: `Row ${i}` })), 1, 20),
    );

    const result = await getBilibiliCreatorContent(MID, "videos");

    expect(result.next_cursor).toBeUndefined();
  });

  it("falls back to a full-page row count only when the upstream count is absent", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      catalogPage(
        Array.from({ length: 20 }, (_, i) => catalogRow({ bvid: `BV1T6PQzQE${String(i).padStart(2, "0")}`, title: `Row ${i}` })),
        1,
      ),
    );
    const full = await getBilibiliCreatorContent(MID, "videos");
    expect(full.next_cursor).toBe(validCursor(MID, "videos", 2));

    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      catalogPage([catalogRow()], 1),
    );
    const partial = await getBilibiliCreatorContent(MID, "videos");
    expect(partial.next_cursor).toBeUndefined();
    expect((partial as { videos_total?: number }).videos_total).toBeUndefined();
  });

  it("bases continuation on the raw upstream page length when the count is absent", async () => {
    const rawFull = Array.from(
      { length: 20 },
      (_, i) => catalogRow({
        bvid: `BV1T6PQzQE${String(i).padStart(2, "0")}`,
        title: `Row ${i}`,
      }),
    );
    rawFull[0] = catalogRow({ bvid: "not-a-bvid", title: "Malformed row" });
    httpMocks.fetchWithWBI.mockResolvedValueOnce(catalogPage(rawFull, 1));

    const full = await getBilibiliCreatorContent(MID, "videos");

    expect(full).toMatchObject({ skipped_count: 1 });
    expect((full as { videos_total?: number }).videos_total).toBeUndefined();
    expect(full.next_cursor).toBe(validCursor(MID, "videos", 2));

    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      catalogPage(
        Array.from({ length: 19 }, (_, i) =>
          catalogRow({ bvid: `BV1T6PQzQE${String(i).padStart(2, "0")}`, title: `Row ${i}` }),
        ),
        1,
      ),
    );
    const partial = await getBilibiliCreatorContent(MID, "videos");
    expect(partial.next_cursor).toBeUndefined();
  });

  it("proves next-page arithmetic safe at the largest accepted current page", async () => {
    const MAX_PAGE = Math.floor(Number.MAX_SAFE_INTEGER / 20);
    const cursor = validCursor(MID, "videos", MAX_PAGE);
    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      catalogPage([catalogRow()], MAX_PAGE, MAX_PAGE * 20 + 5),
    );

    const result = await getBilibiliCreatorContent(MID, "videos", cursor);

    expect(result).toMatchObject({ page: MAX_PAGE });
    expect(result.next_cursor).toBeUndefined();
  });

  it("continues from the cursor page", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      catalogPage([catalogRow()], 2, 45),
    );

    const result = await getBilibiliCreatorContent(MID, "videos", validCursor(MID, "videos", 2));

    expect(httpMocks.fetchWithWBI).toHaveBeenCalledWith(
      "/x/space/wbi/arc/search",
      { mid: MID, pn: 2, ps: 20, order: "pubdate", tid: 0, keyword: "" },
      { Cookie: "configured" },
    );
    expect(result).toMatchObject({ page: 2, next_cursor: validCursor(MID, "videos", 3) });
  });

  it("fails explicitly on a malformed catalog payload instead of empty success", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce({ data: { list: {} } });

    await expect(
      getBilibiliCreatorContent(MID, "videos"),
    ).rejects.toThrow(UpstreamResponseError);
  });

  it("fails with ResourceLimitError when the catalog page exceeds 20 rows", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      catalogPage(
        Array.from({ length: 21 }, (_, i) => catalogRow({ bvid: `BV1T6PQzQE${String(i).padStart(2, "0")}`, title: `Row ${i}` })),
        1,
        21,
      ),
    );

    await expect(
      getBilibiliCreatorContent(MID, "videos"),
    ).rejects.toThrow(ResourceLimitError);
  });

  it("fails with ResourceLimitError when a row title exceeds its byte limit", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      catalogPage([catalogRow({ title: "🙂".repeat(300) })], 1, 1),
    );

    await expect(
      getBilibiliCreatorContent(MID, "videos"),
    ).rejects.toThrow(ResourceLimitError);
  });

  it("propagates network and API failures without turning them into empty success", async () => {
    httpMocks.fetchWithWBI.mockRejectedValueOnce(
      new Error("network down"),
    );
    await expect(
      getBilibiliCreatorContent(MID, "videos"),
    ).rejects.toThrow("network down");

    httpMocks.fetchWithWBI.mockRejectedValueOnce(
      new BilibiliAPIError("risk control", "API_ERROR"),
    );
    await expect(
      getBilibiliCreatorContent(MID, "overview"),
    ).rejects.toThrow(BilibiliAPIError);
  });

  it("makes no per-row requests and no additional catalog requests for a valid videos call", async () => {
    httpMocks.fetchWithWBI.mockResolvedValueOnce(
      catalogPage([catalogRow()], 1, 1),
    );

    await getBilibiliCreatorContent(MID, "videos", validCursor());

    expect(httpMocks.fetchWithWBI).toHaveBeenCalledTimes(1);
  });
});

describe("getBilibiliCreatorContent credential and login gates", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    httpMocks.checkLoginStatus.mockResolvedValue({ isLogin: true });
  });

  it("fails with COOKIE_EXPIRED when no Cookie is configured, without network", async () => {
    credentialMocks.getAuthHeaders.mockReturnValue({});
    await expect(
      getBilibiliCreatorContent(MID, "overview"),
    ).rejects.toThrow(BilibiliAPIError);
    await expect(
      getBilibiliCreatorContent(MID, "videos"),
    ).rejects.toThrow(BilibiliAPIError);
    expect(httpMocks.checkLoginStatus).not.toHaveBeenCalled();
    expect(httpMocks.fetchWithWBI).not.toHaveBeenCalled();
  });

  it("fails with COOKIE_EXPIRED when the login status is not logged in, without catalog requests", async () => {
    credentialMocks.getAuthHeaders.mockReturnValue({ Cookie: "configured" });
    httpMocks.checkLoginStatus.mockResolvedValue({ isLogin: false });
    await expect(
      getBilibiliCreatorContent(MID, "videos", validCursor()),
    ).rejects.toThrow(BilibiliAPIError);
    expect(httpMocks.fetchWithWBI).not.toHaveBeenCalled();
  });
});
