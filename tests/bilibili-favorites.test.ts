import { beforeEach, describe, expect, it, vi } from "vitest";

const httpMocks = vi.hoisted(() => ({
  fetchWithoutWBI: vi.fn(),
}));

const credentialMocks = vi.hoisted(() => ({
  getAuthHeaders: vi.fn(),
}));

vi.mock("../src/bilibili/http.js", () => ({
  fetchWithoutWBI: httpMocks.fetchWithoutWBI,
}));

vi.mock("../src/utils/credentials.js", () => ({
  credentialManager: {
    getAuthHeaders: credentialMocks.getAuthHeaders,
  },
}));

const { BilibiliAPIError, ValidationError } = await import(
  "../src/utils/errors.js"
);
const {
  decodeFavoritesCursor,
  encodeFavoritesCursor,
  listBilibiliFavoriteVideos,
} = await import("../src/bilibili/favorites.js");

const AUTHENTICATED_MID = 1_234_567_890;

function folderRow(id: number, mediaCount: number, mid?: number) {
  return {
    id,
    fid: id,
    title: `folder-${id}`,
    media_count: mediaCount,
    attr: 0,
    fav_state: 0,
    mid: mid ?? AUTHENTICATED_MID,
  };
}

function videoRow(
  bvid: string,
  title: string,
  overrides: Record<string, unknown> = {},
) {
  return {
    bvid,
    bv_id: bvid,
    title,
    upper: { name: "uploader", mid: 99, face: "u", jump_link: "" },
    duration: 120,
    pubtime: 1_700_000_000,
    fav_time: 1_704_000_000,
    attr: 0,
    cnt_info: {},
    cover: "",
    ctime: 1_700_000_000,
    id: 1,
    intro: "",
    link: "",
    media_list_link: "",
    ogv: null,
    page: null,
    season: null,
    type: 2,
    ugc: null,
    ...overrides,
  };
}

function navResponse(mid: number = AUTHENTICATED_MID) {
  return { isLogin: true, mid };
}

describe("encodeFavoritesCursor / decodeFavoritesCursor round-trip", () => {
  it("encodes and decodes a valid folder/page pair without credentials", () => {
    const token = encodeFavoritesCursor(42, 3);
    expect(decodeFavoritesCursor(token)).toEqual({ folderId: 42, page: 3 });
  });

  it("uses base64url characters only", () => {
    expect(encodeFavoritesCursor(1, 1)).toMatch(/^[A-Za-z0-9_-]+$/);
  });

  it("encodes the expected payload shape", () => {
    const token = encodeFavoritesCursor(7, 2);
    const decoded = Buffer.from(token, "base64").toString("utf-8");
    expect(JSON.parse(decoded)).toEqual({
      version: 1,
      folder_id: 7,
      page: 2,
    });
  });
});

describe("decodeFavoritesCursor strict validation", () => {
  it.each([
    ["undefined", undefined],
    ["number", 42],
    ["object", {}],
    ["null", null],
  ])("rejects non-string cursor (%s)", (_case, value) => {
    expect(() =>
      decodeFavoritesCursor(value as unknown as string),
    ).toThrow("cursor must be a string");
  });

  it("rejects empty string", () => {
    expect(() => decodeFavoritesCursor("")).toThrow(
      "cursor length must be between 1 and 256",
    );
  });

  it("rejects overlong cursor (>256 chars)", () => {
    expect(() => decodeFavoritesCursor(`${"A".repeat(256)}A`)).toThrow(
      "cursor length must be between 1 and 256",
    );
  });

  it.each([
    ["plus sign", "AB+C"],
    ["slash", "AB/C"],
    ["equals padding", "AB=C"],
    ["space", "AB C"],
    ["unicode", "ABé"],
  ])("rejects non-base64url characters (%s)", (_case, value) => {
    expect(() => decodeFavoritesCursor(value)).toThrow(
      "cursor must contain only base64url characters",
    );
  });

  it("rejects payload that is not valid JSON", () => {
    const bad = Buffer.from("not-json", "utf-8").toString("base64url");
    expect(() => decodeFavoritesCursor(bad)).toThrow(
      "cursor is not valid JSON",
    );
  });

  it("rejects a non-canonical base64url token with an ignored trailing sextet", () => {
    const bad = `${encodeFavoritesCursor(1, 1)}A`;
    expect(() => decodeFavoritesCursor(bad)).toThrow(
      "cursor is not valid base64url",
    );
  });

  it("rejects payload that is not a JSON object", () => {
    const bad = Buffer.from("[1,2,3]", "utf-8").toString("base64url");
    expect(() => decodeFavoritesCursor(bad)).toThrow(
      "cursor payload must be a JSON object",
    );
  });

  it("rejects unsupported version", () => {
    const bad = Buffer.from(
      JSON.stringify({ version: 99, folder_id: 1, page: 1 }),
      "utf-8",
    ).toString("base64url");
    expect(() => decodeFavoritesCursor(bad)).toThrow(
      "cursor version 99 is not supported",
    );
  });

  it.each([
    ["missing folder_id", { version: 1, page: 1 }],
    ["zero folder_id", { version: 1, folder_id: 0, page: 1 }],
    ["fractional folder_id", { version: 1, folder_id: 1.5, page: 1 }],
    ["string folder_id", { version: 1, folder_id: "1", page: 1 }],
  ])("rejects invalid folder_id (%s)", (_case, payload) => {
    const bad = Buffer.from(JSON.stringify(payload), "utf-8").toString(
      "base64url",
    );
    expect(() => decodeFavoritesCursor(bad)).toThrow(
      "cursor folder_id must be a positive safe integer",
    );
  });

  it.each([
    ["missing page", { version: 1, folder_id: 1 }],
    ["zero page", { version: 1, folder_id: 1, page: 0 }],
    ["negative page", { version: 1, folder_id: 1, page: -1 }],
    ["string page", { version: 1, folder_id: 1, page: "1" }],
  ])("rejects invalid page (%s)", (_case, payload) => {
    const bad = Buffer.from(JSON.stringify(payload), "utf-8").toString(
      "base64url",
    );
    expect(() => decodeFavoritesCursor(bad)).toThrow(
      "cursor page must be a positive safe integer",
    );
  });
});

describe("listBilibiliFavoriteVideos credential and identity gates", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    credentialMocks.getAuthHeaders.mockReturnValue({
      Cookie: "configured=1",
    });
  });

  it("fails before any network request when cursor is malformed", async () => {
    await expect(
      listBilibiliFavoriteVideos("not base64url!!"),
    ).rejects.toThrow("cursor must contain only base64url characters");

    expect(credentialMocks.getAuthHeaders).not.toHaveBeenCalled();
    expect(httpMocks.fetchWithoutWBI).not.toHaveBeenCalled();
  });

  it("fails before credentials or network when cursor base64url is non-canonical", async () => {
    const cursor = `${encodeFavoritesCursor(1, 1)}A`;

    await expect(listBilibiliFavoriteVideos(cursor)).rejects.toThrow(
      "cursor is not valid base64url",
    );

    expect(credentialMocks.getAuthHeaders).not.toHaveBeenCalled();
    expect(httpMocks.fetchWithoutWBI).not.toHaveBeenCalled();
  });

  it("fails before any network request when no usable Cookie is configured", async () => {
    credentialMocks.getAuthHeaders.mockReturnValue({ Cookie: "   " });

    await expect(listBilibiliFavoriteVideos()).rejects.toMatchObject({
      name: "BilibiliAPIError",
      code: "COOKIE_EXPIRED",
    });

    expect(httpMocks.fetchWithoutWBI).not.toHaveBeenCalled();
  });

  it("fails with COOKIE_EXPIRED when nav is not logged in", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({ isLogin: false });

    await expect(listBilibiliFavoriteVideos()).rejects.toMatchObject({
      name: "BilibiliAPIError",
      code: "COOKIE_EXPIRED",
    });

    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(1);
    expect(httpMocks.fetchWithoutWBI).toHaveBeenNthCalledWith(
      1,
      "/x/web-interface/nav",
      undefined,
      { Cookie: "configured=1" },
    );
  });

  it("fails with COOKIE_EXPIRED when nav isLogin but mid is missing", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({ isLogin: true });

    await expect(listBilibiliFavoriteVideos()).rejects.toMatchObject({
      code: "COOKIE_EXPIRED",
    });
  });
});

describe("listBilibiliFavoriteVideos request flow and normalization", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    credentialMocks.getAuthHeaders.mockReturnValue({
      Cookie: "configured=1",
    });
    httpMocks.fetchWithoutWBI.mockReset();
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce(navResponse());
  });

  it("returns the bounded empty state when the account has no created folders", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({ count: 0, list: [] });

    const result = await listBilibiliFavoriteVideos();

    expect(result).toEqual({
      folders_total: 0,
      videos: [],
      skipped_count: 0,
    });
    expect(result).not.toHaveProperty("folder");
    expect(result).not.toHaveProperty("page");
    expect(result).not.toHaveProperty("next_cursor");

    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(2);
    expect(httpMocks.fetchWithoutWBI).toHaveBeenNthCalledWith(
      2,
      "/x/v3/fav/folder/created/list-all",
      { up_mid: AUTHENTICATED_MID },
      { Cookie: "configured=1" },
    );
  });

  it("returns one page with next_cursor advancing within the same folder when has_more=true", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      count: 1,
      list: [folderRow(101, 30)],
    });
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      has_more: true,
      medias: [videoRow("BV1T6PQzQERF", "Hello"), videoRow("BV1xx411c7mD", "World")],
    });

    const result = await listBilibiliFavoriteVideos();

    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(3);
    expect(httpMocks.fetchWithoutWBI).toHaveBeenNthCalledWith(
      3,
      "/x/v3/fav/resource/list",
      {
        media_id: 101,
        pn: 1,
        ps: 20,
        keyword: "",
        order: "mtime",
        type: 0,
        tid: 0,
        platform: "web",
      },
      { Cookie: "configured=1" },
    );

    expect(result).toEqual({
      folders_total: 1,
      folder: { id: 101, title: "folder-101", media_count: 30 },
      page: 1,
      videos: [
        expect.objectContaining({
          bvid: "BV1T6PQzQERF",
          title: "Hello",
          author: "uploader",
          source_url: "https://www.bilibili.com/video/BV1T6PQzQERF/",
        }),
        expect.objectContaining({ bvid: "BV1xx411c7mD", title: "World" }),
      ],
      skipped_count: 0,
      next_cursor: expect.any(String),
    });

    expect(decodeFavoritesCursor(result.next_cursor!)).toEqual({
      folderId: 101,
      page: 2,
    });
  });

  it("advances to the next folder page 1 when has_more=false", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      count: 2,
      list: [folderRow(101, 1), folderRow(102, 5)],
    });
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      has_more: false,
      medias: [videoRow("BV1T6PQzQERF", "Only")],
    });

    const result = await listBilibiliFavoriteVideos();

    expect(decodeFavoritesCursor(result.next_cursor!)).toEqual({
      folderId: 102,
      page: 1,
    });
    expect(result.folder).toEqual({ id: 101, title: "folder-101", media_count: 1 });
  });

  it("omits next_cursor after the final folder final page", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      count: 1,
      list: [folderRow(101, 1)],
    });
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      has_more: false,
      medias: [videoRow("BV1T6PQzQERF", "Only")],
    });

    const result = await listBilibiliFavoriteVideos();

    expect(result).not.toHaveProperty("next_cursor");
  });

  it("treats empty medias as terminal for the current folder even when has_more=true", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      count: 2,
      list: [folderRow(101, 0), folderRow(102, 1)],
    });
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      has_more: true,
      medias: [],
    });

    const result = await listBilibiliFavoriteVideos();

    expect(result.videos).toEqual([]);
    expect(result.folder).toEqual({ id: 101, title: "folder-101", media_count: 0 });
    expect(decodeFavoritesCursor(result.next_cursor!)).toEqual({
      folderId: 102,
      page: 1,
    });
  });

  it("continues the same folder when a non-empty page has only rejected rows", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      count: 2,
      list: [folderRow(101, 40), folderRow(102, 1)],
    });
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      has_more: true,
      medias: [
        { bvid: "not-a-bvid", title: "Rejected" },
        { bvid: "BV1xx411c7mD", title: "   " },
      ],
    });

    const result = await listBilibiliFavoriteVideos();

    expect(result.videos).toEqual([]);
    expect(result.skipped_count).toBe(2);
    expect(decodeFavoritesCursor(result.next_cursor!)).toEqual({
      folderId: 101,
      page: 2,
    });
  });

  it("omits next_cursor when an empty page is on the final folder", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      count: 1,
      list: [folderRow(101, 0)],
    });
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      has_more: true,
      medias: [],
    });

    const result = await listBilibiliFavoriteVideos();

    expect(result.videos).toEqual([]);
    expect(result).not.toHaveProperty("next_cursor");
  });
});

describe("listBilibiliFavoriteVideos continuation and ownership", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    credentialMocks.getAuthHeaders.mockReturnValue({
      Cookie: "configured=1",
    });
    httpMocks.fetchWithoutWBI.mockReset();
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce(navResponse());
  });

  it("continues the same folder at the requested page when the cursor matches", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      count: 1,
      list: [folderRow(101, 30)],
    });
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      has_more: true,
      medias: [videoRow("BV1Q541167Qg", "Page 2 row")],
    });

    const cursor = encodeFavoritesCursor(101, 2);
    const result = await listBilibiliFavoriteVideos(cursor);

    expect(httpMocks.fetchWithoutWBI).toHaveBeenNthCalledWith(
      3,
      "/x/v3/fav/resource/list",
      expect.objectContaining({ media_id: 101, pn: 2 }),
      { Cookie: "configured=1" },
    );
    expect(result.page).toBe(2);
    expect(decodeFavoritesCursor(result.next_cursor!)).toEqual({
      folderId: 101,
      page: 3,
    });
  });

  it("does not emit an unsafe cursor after the maximum safe page", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      count: 1,
      list: [folderRow(101, 1)],
    });
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      has_more: true,
      medias: [videoRow("BV1Q541167Qg", "Maximum page row")],
    });

    const cursor = encodeFavoritesCursor(101, Number.MAX_SAFE_INTEGER);

    await expect(listBilibiliFavoriteVideos(cursor)).rejects.toMatchObject({
      name: "ValidationError",
      message: "cursor page must be a positive safe integer",
    });
  });

  it("rejects a stale cursor whose folder no longer belongs to the account", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      count: 1,
      list: [folderRow(101, 1)],
    });

    const cursor = encodeFavoritesCursor(999, 1);
    const error = await listBilibiliFavoriteVideos(cursor).catch(
      (caught: unknown) => caught,
    );

    expect(error).toBeInstanceOf(ValidationError);
    expect(error).toMatchObject({
      name: "ValidationError",
      message:
        "cursor folder no longer belongs to the current account; restart without a cursor",
    });

    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(2);
    const lastCall =
      httpMocks.fetchWithoutWBI.mock.calls[
        httpMocks.fetchWithoutWBI.mock.calls.length - 1
      ];
    expect(lastCall[0]).toBe("/x/v3/fav/folder/created/list-all");
  });

  it("rejects a continuation cursor when the account now has no valid folders", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      count: 0,
      list: [],
    });

    const cursor = encodeFavoritesCursor(999, 1);

    await expect(listBilibiliFavoriteVideos(cursor)).rejects.toMatchObject({
      name: "ValidationError",
      message:
        "cursor folder no longer belongs to the current account; restart without a cursor",
    });
    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(2);
  });
});

describe("listBilibiliFavoriteVideos defensive normalization", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    credentialMocks.getAuthHeaders.mockReturnValue({
      Cookie: "configured=1",
    });
    httpMocks.fetchWithoutWBI.mockReset();
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce(navResponse());
  });

  it("filters folder rows whose mid does not match the authenticated account", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      count: 2,
      list: [
        folderRow(101, 1, AUTHENTICATED_MID),
        folderRow(202, 9, 999_999_999),
      ],
    });
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      has_more: false,
      medias: [videoRow("BV1T6PQzQERF", "Owned")],
    });

    const result = await listBilibiliFavoriteVideos();

    expect(result.folders_total).toBe(1);
    expect(result.folder?.id).toBe(101);
  });

  it("filters malformed folder rows while preserving string titles", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      count: 6,
      list: [
        null,
        { ...folderRow(101, 1), id: 0 },
        { ...folderRow(102, 1), title: 42 },
        { ...folderRow(103, 1), media_count: -1 },
        { ...folderRow(104, 1), media_count: "1" },
        { ...folderRow(105, 1), title: "   " },
      ],
    });
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      has_more: false,
      medias: [videoRow("BV1T6PQzQERF", "Valid folder")],
    });

    const result = await listBilibiliFavoriteVideos();

    expect(result.folders_total).toBe(1);
    expect(result.folder).toMatchObject({
      id: 105,
      title: "   ",
      media_count: 1,
    });
  });

  it("counts malformed video rows in skipped_count and never fetches a replacement page", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      count: 1,
      list: [folderRow(101, 5)],
    });
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      has_more: false,
      medias: [
        videoRow("BV1T6PQzQERF", "Valid"),
        { bvid: "not-a-bvid", title: "Bad BVID" },
        { bvid: "BV1xx411c7mD", title: "   " },
        { bvid: "BV1Q541167Qg", title: 42 },
        { type: "not-a-video" },
      ],
    });

    const result = await listBilibiliFavoriteVideos();

    expect(result.videos.map((v) => v.bvid)).toEqual(["BV1T6PQzQERF"]);
    expect(result.folder?.media_count).toBe(5);
    expect(result.skipped_count).toBe(4);
    expect(httpMocks.fetchWithoutWBI).toHaveBeenCalledTimes(3);
  });

  it("preserves upstream folder order when continuing", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      count: 3,
      list: [
        folderRow(301, 1),
        folderRow(302, 1),
        folderRow(303, 1),
      ],
    });
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      has_more: false,
      medias: [videoRow("BV1T6PQzQERF", "On 302")],
    });

    const cursor = encodeFavoritesCursor(302, 1);
    const result = await listBilibiliFavoriteVideos(cursor);

    expect(result.folder?.id).toBe(302);
    expect(decodeFavoritesCursor(result.next_cursor!)).toEqual({
      folderId: 303,
      page: 1,
    });
  });

  it("keeps the same BVID visible in each folder context", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      count: 2,
      list: [folderRow(101, 1), folderRow(202, 1)],
    });
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      has_more: false,
      medias: [videoRow("BV1T6PQzQERF", "First folder")],
    });
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce(navResponse());
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      count: 2,
      list: [folderRow(101, 1), folderRow(202, 1)],
    });
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      has_more: false,
      medias: [videoRow("BV1T6PQzQERF", "Second folder")],
    });

    const first = await listBilibiliFavoriteVideos();
    const second = await listBilibiliFavoriteVideos(first.next_cursor);

    expect(first.folder?.id).toBe(101);
    expect(second.folder?.id).toBe(202);
    expect(first.videos[0].bvid).toBe("BV1T6PQzQERF");
    expect(second.videos[0].bvid).toBe("BV1T6PQzQERF");
    expect(first.videos[0].title).toBe("First folder");
    expect(second.videos[0].title).toBe("Second folder");
    expect(second.next_cursor).toBeUndefined();
  });

  it("normalizes invalid duration/timestamps to safe defaults", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      count: 1,
      list: [folderRow(101, 1)],
    });
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      has_more: false,
      medias: [
        videoRow("BV1T6PQzQERF", "Edge", {
          duration: -5,
          pubtime: "bad",
          fav_time: null,
          upper: { name: 123 },
        }),
      ],
    });

    const result = await listBilibiliFavoriteVideos();

    const video = result.videos[0];
    expect(video.duration_seconds).toBe(0);
    expect(video.published_at).toBe("");
    expect(video.favorited_at).toBe("");
    expect(video.author).toBe("");
  });

  it("does not convert favorites request failures into empty success", async () => {
    httpMocks.fetchWithoutWBI.mockResolvedValueOnce({
      count: 1,
      list: [folderRow(101, 1)],
    });
    const error = new BilibiliAPIError("Resource failed", "API_ERROR");
    httpMocks.fetchWithoutWBI.mockRejectedValueOnce(error);

    await expect(listBilibiliFavoriteVideos()).rejects.toBe(error);
  });
});
