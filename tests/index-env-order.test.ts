import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const savedCacheSize = process.env.BILIBILI_CACHE_SIZE;

beforeEach(() => {
  vi.resetModules();
  delete process.env.BILIBILI_CACHE_SIZE;
});

afterEach(() => {
  vi.doUnmock("dotenv");
  if (savedCacheSize === undefined) {
    delete process.env.BILIBILI_CACHE_SIZE;
  } else {
    process.env.BILIBILI_CACHE_SIZE = savedCacheSize;
  }
});

describe("entrypoint environment loading order", () => {
  it("validates values loaded by dotenv before the server imports runtime config", async () => {
    vi.doMock("dotenv", () => ({
      config: vi.fn(() => {
        process.env.BILIBILI_CACHE_SIZE = "0";
        return { parsed: { BILIBILI_CACHE_SIZE: "0" } };
      }),
    }));

    await expect(import("../src/index.js")).rejects.toMatchObject({
      name: "ConfigurationError",
      message:
        "BILIBILI_CACHE_SIZE must be a positive safe integer written in base-10 digits",
    });
  });
});
