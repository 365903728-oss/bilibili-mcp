import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SECURITY_LIMITS } from "../src/security/limits.js";

const savedRateLimit = process.env.BILIBILI_RATE_LIMIT_MS;
const savedRequestTimeout = process.env.BILIBILI_REQUEST_TIMEOUT_MS;
const IMG_KEY = "a".repeat(32);
const SUB_KEY = "b".repeat(32);

function wbiNavResponse(): Response {
  return new Response(
    JSON.stringify({
      code: 0,
      data: {
        wbi_img: {
          img_url: `https://i0.hdslb.com/bfs/wbi/${IMG_KEY}.png`,
          sub_url: `https://i0.hdslb.com/bfs/wbi/${SUB_KEY}.png`,
        },
      },
    }),
    {
      status: 200,
      headers: { "Content-Type": "application/json" },
    },
  );
}

beforeEach(() => {
  vi.resetModules();
  process.env.BILIBILI_RATE_LIMIT_MS = "0";
  process.env.BILIBILI_REQUEST_TIMEOUT_MS = "1000";
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  if (savedRateLimit === undefined) {
    delete process.env.BILIBILI_RATE_LIMIT_MS;
  } else {
    process.env.BILIBILI_RATE_LIMIT_MS = savedRateLimit;
  }
  if (savedRequestTimeout === undefined) {
    delete process.env.BILIBILI_REQUEST_TIMEOUT_MS;
  } else {
    process.env.BILIBILI_REQUEST_TIMEOUT_MS = savedRequestTimeout;
  }
});

describe("signed WBI HTTP response containment", () => {
  it("rejects a signed-request redirect without following its Location", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(wbiNavResponse())
      .mockResolvedValueOnce(
        new Response(null, {
          status: 302,
          headers: { Location: "http://127.0.0.1/private" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);
    const { fetchWithWBI } = await import("../src/bilibili/http.js");

    await expect(
      fetchWithWBI("/x/v2/reply/wbi/main", { oid: 1, type: 1 }),
    ).rejects.toMatchObject({
      name: "NetworkError",
      statusCode: 302,
    });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[1]?.[1]).toMatchObject({
      redirect: "manual",
      signal: expect.any(AbortSignal),
    });
  });

  it("rejects a signed WBI JSON body above four MiB", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(wbiNavResponse())
      .mockResolvedValueOnce(
        new Response("{}", {
          status: 200,
          headers: {
            "Content-Type": "application/json",
            "Content-Length": String(SECURITY_LIMITS.httpJsonBytes + 1),
          },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);
    const { fetchWithWBI } = await import("../src/bilibili/http.js");

    await expect(
      fetchWithWBI("/x/v2/reply/wbi/main", { oid: 1, type: 1 }),
    ).rejects.toMatchObject({
      name: "ResourceLimitError",
      resource: "bilibili_wbi_json",
      limit: SECURITY_LIMITS.httpJsonBytes,
    });

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
