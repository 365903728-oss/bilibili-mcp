import { afterEach, expect, it, vi } from "vitest";

import { SECURITY_LIMITS } from "../src/security/limits.js";
import { getWBI } from "../src/bilibili/wbi.js";

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

it("performs one WBI bootstrap attempt so the outer request owns retries", async () => {
  vi.useFakeTimers();
  const fetchMock = vi.fn(async () =>
    new Response(null, { status: 503, statusText: "Service Unavailable" }),
  );
  vi.stubGlobal("fetch", fetchMock);

  const result = getWBI().catch((error: unknown) => error);

  await vi.runAllTimersAsync();
  await expect(result).resolves.toMatchObject({ statusCode: 503 });
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it("normalizes a WBI AbortError without nesting retries", async () => {
  vi.useFakeTimers();
  const abortError = new DOMException("The operation was aborted.", "AbortError");
  const fetchMock = vi.fn(async () => {
    throw abortError;
  });
  vi.stubGlobal("fetch", fetchMock);

  const result = getWBI().catch((error: unknown) => error);

  await vi.runAllTimersAsync();
  await expect(result).resolves.toMatchObject({ name: "TimeoutError" });
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it("does not retry a non-retryable WBI HTTP status", async () => {
  vi.useFakeTimers();
  const fetchMock = vi.fn(async () =>
    new Response(null, { status: 403, statusText: "Forbidden" }),
  );
  vi.stubGlobal("fetch", fetchMock);

  const result = getWBI().catch((error: unknown) => error);

  await vi.runAllTimersAsync();
  await expect(result).resolves.toMatchObject({ statusCode: 403 });
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it("normalizes a WBI transport failure and clears its request timeout", async () => {
  vi.useFakeTimers();
  const clearTimeoutSpy = vi.spyOn(globalThis, "clearTimeout");
  const fetchMock = vi.fn(async () => {
    throw new TypeError("fetch failed");
  });
  vi.stubGlobal("fetch", fetchMock);

  const result = getWBI().catch((error: unknown) => error);

  await vi.runAllTimersAsync();
  await expect(result).resolves.toMatchObject({
    name: "NetworkError",
    statusCode: undefined,
  });
  expect(clearTimeoutSpy).toHaveBeenCalledTimes(1);
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it("rejects a WBI bootstrap redirect without following its Location", async () => {
  const fetchMock = vi.fn(async () =>
    new Response(null, {
      status: 302,
      headers: { Location: "http://127.0.0.1/private" },
    }),
  );
  vi.stubGlobal("fetch", fetchMock);

  await expect(getWBI()).rejects.toMatchObject({
    name: "NetworkError",
    statusCode: 302,
  });
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({ redirect: "manual" });
});

it("rejects a WBI bootstrap body above 256 KiB before parsing it", async () => {
  const fetchMock = vi.fn(async () =>
    new Response("{}", {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Content-Length": String(SECURITY_LIMITS.wbiBootstrapBytes + 1),
      },
    }),
  );
  vi.stubGlobal("fetch", fetchMock);

  await expect(getWBI()).rejects.toMatchObject({
    name: "ResourceLimitError",
    resource: "wbi_bootstrap_json",
    limit: SECURITY_LIMITS.wbiBootstrapBytes,
  });
  expect(fetchMock).toHaveBeenCalledTimes(1);
});
