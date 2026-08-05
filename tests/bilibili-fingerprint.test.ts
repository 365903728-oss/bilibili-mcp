import { afterEach, beforeEach, expect, it, vi } from "vitest";

beforeEach(() => {
  vi.resetModules();
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

it("clears the fingerprint request timeout when fetch rejects", async () => {
  vi.useFakeTimers();
  const clearTimeoutSpy = vi.spyOn(globalThis, "clearTimeout");
  const mockFetch = vi.fn(async () => {
    throw new TypeError("fetch failed");
  });
  vi.stubGlobal("fetch", mockFetch);
  const { getBuvid } = await import("../src/bilibili/fingerprint.js");

  await expect(getBuvid()).resolves.toBeNull();
  expect(clearTimeoutSpy).toHaveBeenCalledTimes(1);
  expect(mockFetch).toHaveBeenCalledTimes(1);
});

it("coalesces concurrent cold-cache callers onto one fetch", async () => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  const mockFetch = vi.fn(async () => {
    await gate;
    return new Response(
      JSON.stringify({
        code: 0,
        data: { b_3: "synthetic-buvid-3", b_4: "synthetic-buvid-4" },
      }),
      { status: 200 },
    );
  });
  vi.stubGlobal("fetch", mockFetch);
  const { getBuvid } = await import("../src/bilibili/fingerprint.js");

  const callers = Array.from({ length: 32 }, () => getBuvid());
  await vi.waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));
  release();

  await expect(Promise.all(callers)).resolves.toEqual(
    Array.from({ length: 32 }, () => ({
      buvid3: "synthetic-buvid-3",
      buvid4: "synthetic-buvid-4",
    })),
  );
  expect(mockFetch).toHaveBeenCalledTimes(1);
  await expect(getBuvid()).resolves.toEqual({
    buvid3: "synthetic-buvid-3",
    buvid4: "synthetic-buvid-4",
  });
  expect(mockFetch).toHaveBeenCalledTimes(1);
});

it("clears a failed single-flight slot so one later retry can succeed", async () => {
  const mockFetch = vi
    .fn()
    .mockRejectedValueOnce(new TypeError("synthetic failure"))
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          code: 0,
          data: { b_3: "retry-buvid-3", b_4: "retry-buvid-4" },
        }),
        { status: 200 },
      ),
    );
  vi.stubGlobal("fetch", mockFetch);
  const { getBuvid } = await import("../src/bilibili/fingerprint.js");

  await expect(Promise.all([getBuvid(), getBuvid()])).resolves.toEqual([
    null,
    null,
  ]);
  await expect(getBuvid()).resolves.toEqual({
    buvid3: "retry-buvid-3",
    buvid4: "retry-buvid-4",
  });
  expect(mockFetch).toHaveBeenCalledTimes(2);
});

it("rejects a fingerprint redirect without following its Location", async () => {
  const mockFetch = vi.fn(async () =>
    new Response(null, {
      status: 302,
      headers: { Location: "http://127.0.0.1/private" },
    }),
  );
  vi.stubGlobal("fetch", mockFetch);
  const { getBuvid } = await import("../src/bilibili/fingerprint.js");

  await expect(getBuvid()).resolves.toBeNull();
  expect(mockFetch).toHaveBeenCalledTimes(1);
  expect(mockFetch.mock.calls[0]?.[1]).toMatchObject({ redirect: "manual" });
});

it("does not parse or cache an oversized fingerprint response", async () => {
  const mockFetch = vi.fn(async () =>
    new Response(
      JSON.stringify({
        code: 0,
        data: { b_3: "synthetic-buvid-3", b_4: "synthetic-buvid-4" },
      }),
      {
        status: 200,
        headers: { "Content-Length": String(64 * 1024 + 1) },
      },
    ),
  );
  vi.stubGlobal("fetch", mockFetch);
  const { getBuvid } = await import("../src/bilibili/fingerprint.js");

  await expect(getBuvid()).resolves.toBeNull();
  await expect(getBuvid()).resolves.toBeNull();
  expect(mockFetch).toHaveBeenCalledTimes(2);
});
