import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  vi.resetModules();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("subtitle fallback eligibility", () => {
  it.each([
    ["missing subtitle", {}],
    ["null subtitle", { subtitle: null }],
    ["missing subtitle list", { subtitle: {} }],
    ["non-array subtitle list", { subtitle: { subtitles: "invalid" } }],
  ])(
    "does not reinterpret malformed WBI metadata as a verified empty result: %s",
    async (_label, malformedData) => {
      const fetchMock = vi.fn(async (input: string | URL | Request) => {
        const url = String(input);
        if (url.includes("/x/frontend/finger/spi")) {
          return jsonResponse({
            code: 0,
            data: {
              b_3: "synthetic-buvid-3",
              b_4: "synthetic-buvid-4",
            },
          });
        }
        if (url.includes("/x/web-interface/nav")) {
          return jsonResponse({
            code: 0,
            data: {
              wbi_img: {
                img_url:
                  "https://i0.hdslb.com/bfs/wbi/abcdefghijklmnopqrstuvwxyz123456.png",
                sub_url:
                  "https://i0.hdslb.com/bfs/wbi/123456abcdefghijklmnopqrstuvwxyz.png",
              },
            },
          });
        }
        if (url.includes("/x/player/wbi/v2")) {
          return jsonResponse({ code: 0, data: malformedData });
        }
        if (url.includes("/x/player/v2")) {
          throw new Error("plain fallback must not run for malformed data");
        }
        throw new Error("unexpected synthetic URL");
      });
      vi.stubGlobal("fetch", fetchMock);
      const { credentialManager } = await import(
        "../src/utils/credentials.js"
      );
      const { getVideoSubtitle } = await import(
        "../src/bilibili/client.js"
      );
      credentialManager.setCredentials({
        sessdata: "synthetic",
        expiresAt: Date.now() + 60_000,
      });

      try {
        await expect(
          getVideoSubtitle("BV1T6PQzQErF", 123),
        ).rejects.toMatchObject({
          name: "NetworkError",
        });
      } finally {
        credentialManager.clearCredentials();
      }

      const urls = fetchMock.mock.calls.map(([input]) => String(input));
      expect(
        urls.some(
          (url) =>
            url.includes("/x/player/v2") &&
            !url.includes("/x/player/wbi/v2"),
        ),
      ).toBe(false);
    },
  );
});
