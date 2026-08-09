import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SUPPORTED_LANGUAGES } from "../src/bilibili/types.js";
import {
  DEFAULT_CONFIG,
  getPreferredLanguage,
} from "../src/config.js";

describe("language configuration", () => {
  it("uses the canonical supported-language list at runtime", () => {
    expect(DEFAULT_CONFIG.supportedLanguages).toEqual(SUPPORTED_LANGUAGES);
  });

  it("preserves ai-zh as the requested language", () => {
    expect(getPreferredLanguage("ai-zh")).toBe("ai-zh");
  });

  it("does not silently replace an unsupported language", () => {
    expect(() => getPreferredLanguage("fr")).toThrow(
      "Unsupported language. Supported values: zh-Hans, zh-CN, zh-Hant, en, ja, ko, ai-zh",
    );
  });
});

const NUMERIC_ENV_NAMES = [
  "BILIBILI_RATE_LIMIT_MS",
  "BILIBILI_REQUEST_TIMEOUT_MS",
  "BILIBILI_CACHE_SIZE",
] as const;

const originalNumericEnv = new Map(
  NUMERIC_ENV_NAMES.map((name) => [name, process.env[name]]),
);

async function importConfigWithEnv(name: string, value: string) {
  process.env[name] = value;
  vi.resetModules();
  return import("../src/config.js");
}

describe("numeric environment configuration", () => {
  beforeEach(() => {
    for (const name of NUMERIC_ENV_NAMES) {
      delete process.env[name];
    }
    vi.resetModules();
  });

  afterEach(() => {
    for (const name of NUMERIC_ENV_NAMES) {
      const original = originalNumericEnv.get(name);
      if (original === undefined) {
        delete process.env[name];
      } else {
        process.env[name] = original;
      }
    }
    vi.resetModules();
  });

  it.each([
    ["BILIBILI_RATE_LIMIT_MS", "17", "rateLimitMs", 17],
    ["BILIBILI_RATE_LIMIT_MS", "2147483647", "rateLimitMs", 2147483647],
    ["BILIBILI_REQUEST_TIMEOUT_MS", "2500", "requestTimeoutMs", 2500],
    [
      "BILIBILI_REQUEST_TIMEOUT_MS",
      "2147483647",
      "requestTimeoutMs",
      2147483647,
    ],
    ["BILIBILI_CACHE_SIZE", "25", "maxCacheSize", 25],
    [
      "BILIBILI_CACHE_SIZE",
      "9007199254740991",
      "maxCacheSize",
      Number.MAX_SAFE_INTEGER,
    ],
  ] as const)(
    "loads %s only when it is a complete positive safe integer",
    async (name, value, property, expected) => {
      const { config: loadedConfig } = await importConfigWithEnv(name, value);
      expect(loadedConfig[property]).toBe(expected);
    },
  );

  const invalidNumericValues = [
    "",
    "NaN",
    "12ms",
    "1.5",
    "0",
    "-1",
    "9007199254740992",
  ];

  it.each(
    NUMERIC_ENV_NAMES.flatMap((name) =>
      invalidNumericValues.map((value) => [name, value] as const),
    ),
  )(
    "rejects invalid %s value %j with an actionable error",
    async (name, value) => {
      await expect(importConfigWithEnv(name, value)).rejects.toThrow(
        `${name} must be a positive safe integer written in base-10 digits`,
      );
    },
  );

  it.each([
    "BILIBILI_RATE_LIMIT_MS",
    "BILIBILI_REQUEST_TIMEOUT_MS",
  ] as const)("rejects %s above Node's timer range", async (name) => {
    await expect(importConfigWithEnv(name, "2147483648")).rejects.toThrow(
      `${name} must not exceed 2147483647 milliseconds`,
    );
  });
});
