import { describe, expect, it, vi } from "vitest";

import { logger, redactSecrets } from "../src/utils/logger.js";
import { withRetry } from "../src/utils/retry.js";

function restoreDebugEnv(previous: string | undefined) {
  if (previous === undefined) {
    delete process.env.BILIBILI_MCP_DEBUG;
  } else {
    process.env.BILIBILI_MCP_DEBUG = previous;
  }
}

describe("logger secret redaction", () => {
  it("redacts Cookie fields by key and value pattern", () => {
    const redacted = redactSecrets({
      Cookie: "SESSDATA=real-sess; bili_jct=real-jct; DedeUserID=123456",
      nested: {
        message: "BILIBILI_SESSDATA=real-env",
      },
    });

    const serialized = JSON.stringify(redacted);

    expect(serialized).toContain('"Cookie":"***"');
    expect(serialized).not.toContain("real-sess");
    expect(serialized).not.toContain("real-jct");
    expect(serialized).not.toContain("123456");
    expect(serialized).not.toContain("real-env");
    expect(serialized).toContain("BILIBILI_SESSDATA=***");
  });

  it("redacts account and Favorite Folder identifiers from params and URLs", () => {
    const redacted = redactSecrets({
      params: {
        up_mid: 1_234_567_890,
        media_id: 9_876_543_210,
      },
      url: "https://api.bilibili.com/x/v3/fav/resource/list?up_mid=1234567890&media_id=9876543210&pn=1",
    });

    const serialized = JSON.stringify(redacted);

    expect(serialized).toContain('"up_mid":"***"');
    expect(serialized).toContain('"media_id":"***"');
    expect(serialized).toContain("up_mid=***");
    expect(serialized).toContain("media_id=***");
    expect(serialized).not.toContain("1234567890");
    expect(serialized).not.toContain("9876543210");
  });

  it("redacts logger output before writing to stderr", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    logger.error("failed with SESSDATA=real-sess", {
      headers: {
        Cookie: "SESSDATA=real-sess; bili_jct=real-jct; DedeUserID=123456",
      },
    });

    const output = spy.mock.calls.map((call) => call.join(" ")).join("\n");
    spy.mockRestore();

    expect(output).not.toContain("real-sess");
    expect(output).not.toContain("real-jct");
    expect(output).not.toContain("123456");
    expect(output).toContain("SESSDATA=***");
    expect(output).toContain('"Cookie":"***"');
  });

  it("does not emit debug logs unless debug logging is enabled", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    const previous = process.env.BILIBILI_MCP_DEBUG;

    try {
      delete process.env.BILIBILI_MCP_DEBUG;

      logger.debug("debug message", { Cookie: "SESSDATA=real-sess" });

      expect(spy).not.toHaveBeenCalled();
    } finally {
      restoreDebugEnv(previous);
      spy.mockRestore();
    }
  });

  it("emits redacted debug logs when debug logging is enabled", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    const previous = process.env.BILIBILI_MCP_DEBUG;

    try {
      process.env.BILIBILI_MCP_DEBUG = "1";

      logger.debug("debug message SESSDATA=real-sess", {
        Cookie: "SESSDATA=real-sess; bili_jct=real-jct; DedeUserID=123456",
        nested: {
          message: "BILIBILI_SESSDATA=real-env",
        },
      });

      const output = spy.mock.calls.map((call) => call.join(" ")).join("\n");

      expect(output).toContain('"level":"debug"');
      expect(output).toContain("SESSDATA=***");
      expect(output).toContain('"Cookie":"***"');
      expect(output).not.toContain("real-sess");
      expect(output).not.toContain("real-jct");
      expect(output).not.toContain("123456");
      expect(output).not.toContain("real-env");
    } finally {
      restoreDebugEnv(previous);
      spy.mockRestore();
    }
  });

  it("redacts retryable error messages before writing to stderr", async () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    const error = new Error(
      "boom SESSDATA=real-sess; bili_jct=real-jct; DedeUserID=123456",
    );
    error.name = "NetworkError";

    try {
      await withRetry(
        async () => {
          throw error;
        },
        { maxRetries: 1, baseDelay: 1, maxDelay: 1 },
      ).catch(() => {});

      const output = spy.mock.calls.map((call) => call.join(" ")).join("\n");

      expect(output).toContain("SESSDATA=***");
      expect(output).toContain("bili_jct=***");
      expect(output).toContain("DedeUserID=***");
      expect(output).not.toContain("real-sess");
      expect(output).not.toContain("real-jct");
      expect(output).not.toContain("123456");
    } finally {
      spy.mockRestore();
    }
  });
});
