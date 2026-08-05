import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const savedRateLimit = process.env.BILIBILI_RATE_LIMIT_MS;
const savedRequestTimeout = process.env.BILIBILI_REQUEST_TIMEOUT_MS;

beforeEach(async () => {
  vi.useFakeTimers();
  vi.resetModules();
  process.env.BILIBILI_RATE_LIMIT_MS = "500";
});

afterEach(() => {
  vi.useRealTimers();
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

describe("throttledFetch", () => {
  it("serializes concurrent request admissions", async () => {
    const { throttledFetch } = await import("../src/bilibili/http.js");
    const starts: number[] = [];
    let resolveFirst!: (v: number) => void;
    const firstDone = new Promise<number>((resolve) => {
      resolveFirst = resolve;
    });

    const p1 = throttledFetch(async () => {
      starts.push(Date.now());
      return await firstDone;
    });
    const p2 = throttledFetch(async () => {
      starts.push(Date.now());
      return 2;
    });
    const p3 = throttledFetch(async () => {
      starts.push(Date.now());
      return 3;
    });

    await vi.advanceTimersByTimeAsync(500);
    await vi.advanceTimersByTimeAsync(500);
    await vi.advanceTimersByTimeAsync(500);

    // p2 and p3 admitted and resolved while p1 is still in-flight
    resolveFirst(1);
    const results = await Promise.all([p1, p2, p3]);
    expect(results).toEqual([1, 2, 3]);

    expect(starts).toHaveLength(3);
    expect(starts[1] - starts[0]).toBeGreaterThanOrEqual(500);
    expect(starts[2] - starts[1]).toBeGreaterThanOrEqual(500);
  });

  it("does not block subsequent admissions after a request failure", async () => {
    const { throttledFetch } = await import("../src/bilibili/http.js");
    const starts: number[] = [];

    const p1 = throttledFetch(async () => {
      starts.push(Date.now());
      throw new Error("boom");
    });
    p1.catch(() => {}); // suppress unhandled rejection until explicit expect below
    const p2 = throttledFetch(async () => {
      starts.push(Date.now());
      return "ok";
    });

    await vi.advanceTimersByTimeAsync(500);
    await vi.advanceTimersByTimeAsync(500);

    await expect(p1).rejects.toThrow("boom");
    const result = await p2;

    expect(result).toBe("ok");
    expect(starts).toHaveLength(2);
    expect(starts[1] - starts[0]).toBeGreaterThanOrEqual(500);
  });

  it("rejects excess queued requests before retaining an unbounded backlog", async () => {
    process.env.BILIBILI_RATE_LIMIT_MS = "1";
    process.env.BILIBILI_REQUEST_TIMEOUT_MS = "100000";
    vi.resetModules();
    const { throttledFetch } = await import("../src/bilibili/http.js");

    const calls = Array.from({ length: 33 }, () =>
      throttledFetch(async () => "ok"),
    );
    const settledPromise = Promise.allSettled(calls);
    await vi.runAllTimersAsync();
    const settled = await settledPromise;

    expect(settled.slice(0, 32).every((item) => item.status === "fulfilled")).toBe(
      true,
    );
    expect(settled[32]).toMatchObject({
      status: "rejected",
      reason: {
        name: "ResourceLimitError",
        resource: "http_operation_capacity",
        limit: 32,
      },
    });
  });

  it("releases capacity when a queued caller cancels before dispatch", async () => {
    process.env.BILIBILI_RATE_LIMIT_MS = "500";
    process.env.BILIBILI_REQUEST_TIMEOUT_MS = "100000";
    vi.resetModules();
    const { throttledFetch } = await import("../src/bilibili/http.js");
    let releaseFirst!: () => void;
    const firstGate = new Promise<void>((resolve) => {
      releaseFirst = resolve;
    });
    const secondController = new AbortController();
    const secondCallback = vi.fn(async () => "second");
    const thirdCallback = vi.fn(async () => "third");

    const first = throttledFetch(async () => {
      await firstGate;
      return "first";
    });
    const second = throttledFetch(secondCallback, {
      signal: secondController.signal,
    });
    secondController.abort();

    await expect(second).rejects.toMatchObject({ name: "AbortError" });
    expect(secondCallback).not.toHaveBeenCalled();
    const third = throttledFetch(thirdCallback);
    await vi.advanceTimersByTimeAsync(1_000);
    await expect(third).resolves.toBe("third");
    expect(thirdCallback).toHaveBeenCalledOnce();

    releaseFirst();
    await expect(first).resolves.toBe("first");
  });

  it("rejects admission past the caller deadline before invoking the callback", async () => {
    process.env.BILIBILI_RATE_LIMIT_MS = "500";
    process.env.BILIBILI_REQUEST_TIMEOUT_MS = "100000";
    vi.resetModules();
    const { throttledFetch } = await import("../src/bilibili/http.js");
    let releaseFirst!: () => void;
    const firstGate = new Promise<void>((resolve) => {
      releaseFirst = resolve;
    });
    const callback = vi.fn(async () => "late");

    const first = throttledFetch(async () => {
      await firstGate;
      return "first";
    });
    const late = throttledFetch(callback, {
      deadlineAt: Date.now() + 100,
    });

    await expect(late).rejects.toMatchObject({
      name: "ResourceLimitError",
      resource: "http_admission_wait_ms",
    });
    expect(callback).not.toHaveBeenCalled();
    releaseFirst();
    await expect(first).resolves.toBe("first");
  });
});

describe("checkLoginStatus", () => {
  it("returns false for a successful logged-out nav response", async () => {
    const { checkLoginStatus } = await import("../src/bilibili/http.js");
    const originalFetch = globalThis.fetch;
    try {
      globalThis.fetch = vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ code: 0, data: { isLogin: false } }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ) as typeof globalThis.fetch;

      const outcome = checkLoginStatus();
      await vi.advanceTimersByTimeAsync(500);
      await expect(outcome).resolves.toEqual({ isLogin: false });
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("rejects with NetworkError for non-2xx login-status response", async () => {
    const { NetworkError } = await import("../src/utils/errors.js");
    const { checkLoginStatus } = await import("../src/bilibili/http.js");
    const originalFetch = globalThis.fetch;
    try {
      globalThis.fetch = vi.fn().mockResolvedValue(
        new Response("Forbidden", { status: 403 }),
      ) as typeof globalThis.fetch;

      const outcome = checkLoginStatus().catch((error: unknown) => error);
      await vi.runAllTimersAsync();
      const error = await outcome;
      expect(error).toBeInstanceOf(NetworkError);
      expect(error).toMatchObject({ statusCode: 403 });
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});

describe("Bilibili redirect policy", () => {
  it("uses manual redirect mode and rejects a plain API redirect without a second request", async () => {
    const { fetchWithoutWBI } = await import("../src/bilibili/http.js");
    const fetchMock = vi.fn(async () =>
      new Response(null, {
        status: 302,
        headers: { Location: "http://127.0.0.1/private" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const outcome = fetchWithoutWBI("/x/web-interface/nav").catch(
      (error: unknown) => error,
    );
    await vi.runAllTimersAsync();

    await expect(outcome).resolves.toMatchObject({
      name: "NetworkError",
      statusCode: 302,
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({ redirect: "manual" });
  });
});

describe("throttledFetch TypeError normalization", () => {
  it("normalizes native fetch TypeError to NetworkError", async () => {
    const { NetworkError } = await import("../src/utils/errors.js");
    const { throttledFetch } = await import("../src/bilibili/http.js");
    const err = new TypeError("Failed to fetch");

    const outcome = throttledFetch(async () => { throw err; }).catch(
      (error: unknown) => error,
    );
    await vi.advanceTimersByTimeAsync(500);
    const error = await outcome;
    expect(error).toBeInstanceOf(NetworkError);
    expect(error).toMatchObject({ originalError: err });
  });
});
