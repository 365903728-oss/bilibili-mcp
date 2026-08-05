import { beforeEach, describe, expect, it, vi } from "vitest";

const mockGetPlayerData = vi.fn();

vi.mock("../src/bilibili/video-api.js", () => ({
  getPlayerData: (...args: unknown[]) => mockGetPlayerData(...args),
}));

vi.mock("../src/bilibili/navigation.js", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/bilibili/navigation.js")>();
  return {
    ...actual,
    resolvePartCid: vi.fn(),
  };
});

import { getVideoChaptersData } from "../src/bilibili/chapters.js";
import { resolvePartCid } from "../src/bilibili/navigation.js";

const mockResolvePartCid = resolvePartCid as unknown as ReturnType<typeof vi.fn>;

function defaultVideoData() {
  return {
    title: "Test Video",
    desc: "Description",
    cid: 999,
    pages: [{ cid: 999, page: 1, part: "Part 1", duration: 300 }],
  };
}

function defaultPages() {
  return [{ page: 1, cid: 999, title: "Part 1", duration: 300 }];
}

beforeEach(() => {
  vi.clearAllMocks();
  mockResolvePartCid.mockResolvedValue({
    cid: 999,
    videoData: defaultVideoData(),
    pages: defaultPages(),
  });
});

describe("getVideoChaptersData", () => {
  it("returns empty chapters when player has no view_points", async () => {
    mockGetPlayerData.mockResolvedValue({});

    const result = await getVideoChaptersData("BV1T6PQzQErF");

    expect(result.bvid).toBe("BV1T6PQzQErF");
    expect(result.chapters).toEqual([]);
  });

  it("returns empty chapters when view_points is empty array", async () => {
    mockGetPlayerData.mockResolvedValue({ view_points: [] });

    const result = await getVideoChaptersData("BV1T6PQzQErF");

    expect(result.chapters).toEqual([]);
  });

  it("maps view_points content field to chapter title", async () => {
    mockGetPlayerData.mockResolvedValue({
      view_points: [
        { content: "Intro", title: "Fallback", from: 0, to: 60 },
        { content: "Main Topic", from: 60, to: 180 },
      ],
    });

    const result = await getVideoChaptersData("BV1T6PQzQErF");

    expect(result.chapters).toEqual([
      { title: "Intro", start_seconds: 0, end_seconds: 60 },
      { title: "Main Topic", start_seconds: 60, end_seconds: 180 },
    ]);
  });

  it("falls back to title field when content is absent", async () => {
    mockGetPlayerData.mockResolvedValue({
      view_points: [
        { title: "OnlyTitle", from: 0, to: 30 },
      ],
    });

    const result = await getVideoChaptersData("BV1T6PQzQErF");

    expect(result.chapters).toEqual([
      { title: "OnlyTitle", start_seconds: 0, end_seconds: 30 },
    ]);
  });

  it("propagates player fetch errors", async () => {
    mockGetPlayerData.mockRejectedValue(new Error("Network error"));

    await expect(
      getVideoChaptersData("BV1T6PQzQErF"),
    ).rejects.toThrow("Network error");
  });

  it("passes page through to resolvePartCid", async () => {
    mockGetPlayerData.mockResolvedValue({});
    mockResolvePartCid.mockResolvedValue({
      cid: 200,
      videoData: defaultVideoData(),
      pages: [
        { page: 1, cid: 100, title: "P1", duration: 120 },
        { page: 2, cid: 200, title: "P2", duration: 180 },
      ],
    });

    await getVideoChaptersData("BV1T6PQzQErF", 2);

    expect(mockResolvePartCid).toHaveBeenCalledWith("BV1T6PQzQErF", 2);
  });

  it("returns Part identity from CID-matched Part, not pages[0]", async () => {
    mockResolvePartCid.mockResolvedValue({
      cid: 200,
      videoData: {
        title: "Root Title",
        desc: "",
        cid: 100,
        pages: [
          { cid: 100, page: 1, part: "P1", duration: 60 },
          { cid: 200, page: 2, part: "P2 Title", duration: 60 },
        ],
      },
      pages: [
        { page: 1, cid: 100, title: "P1", duration: 60 },
        { page: 2, cid: 200, title: "P2 Title", duration: 60 },
      ],
    });
    mockGetPlayerData.mockResolvedValue({});

    const result = await getVideoChaptersData("BV1T6PQzQErF");

    // Page should come from the Part matching CID 200, not pages[0]
    expect(result.page).toBe(2);
    expect(result.title).toBe("P2 Title");
  });

  it("bounds chapter title to MAX_CHAPTER_TITLE_LENGTH", async () => {
    mockGetPlayerData.mockResolvedValue({
      view_points: [{ content: "x".repeat(600), from: 0, to: 10 }],
    });

    const result = await getVideoChaptersData("BV1T6PQzQErF");

    expect(Buffer.byteLength(result.chapters[0].title, "utf8")).toBe(500);
    expect(result.chapters[0].title.endsWith("…")).toBe(true);
  });
});
