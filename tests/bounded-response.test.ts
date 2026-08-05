import { describe, expect, it } from "vitest";

import {
  parseBoundedJsonResponse,
  readBoundedResponseBytes,
} from "../src/utils/bounded-response.js";

describe("bounded remote response readers", () => {
  it("parses a JSON body within the actual byte limit", async () => {
    const response = new Response(JSON.stringify({ ok: true }), {
      headers: { "Content-Type": "application/json" },
    });

    await expect(
      parseBoundedJsonResponse(response, 64, "test_json"),
    ).resolves.toEqual({ ok: true });
  });

  it("rejects an oversized declared Content-Length before JSON parsing", async () => {
    const response = new Response("{}", {
      headers: { "Content-Length": "65" },
    });

    await expect(
      parseBoundedJsonResponse(response, 64, "test_json"),
    ).rejects.toMatchObject({
      name: "ResourceLimitError",
      resource: "test_json",
      limit: 64,
    });
  });

  it("rejects a streaming body that exceeds its declared-independent limit", async () => {
    const response = new Response(
      new ReadableStream<Uint8Array>({
        start(controller) {
          controller.enqueue(new Uint8Array(40));
          controller.enqueue(new Uint8Array(40));
          controller.close();
        },
      }),
    );

    await expect(
      readBoundedResponseBytes(response, 64, "test_stream"),
    ).rejects.toMatchObject({
      name: "ResourceLimitError",
      resource: "test_stream",
      limit: 64,
    });
  });

  it("rejects malformed Content-Length instead of trusting it", async () => {
    const response = new Response("{}", {
      headers: { "Content-Length": "not-a-number" },
    });

    await expect(
      readBoundedResponseBytes(response, 64, "test_stream"),
    ).rejects.toMatchObject({ name: "UpstreamResponseError" });
  });

  it("accepts the exact streaming byte boundary", async () => {
    const response = new Response(new Uint8Array(64));

    await expect(
      readBoundedResponseBytes(response, 64, "test_stream"),
    ).resolves.toHaveLength(64);
  });

  it("rejects empty, invalid UTF-8, and invalid JSON bodies", async () => {
    await expect(
      readBoundedResponseBytes(
        new Response(new Uint8Array()),
        64,
        "test_stream",
      ),
    ).rejects.toMatchObject({ name: "UpstreamResponseError" });
    await expect(
      parseBoundedJsonResponse(
        new Response(new Uint8Array([0xff])),
        64,
        "test_json",
      ),
    ).rejects.toMatchObject({ name: "UpstreamResponseError" });
    await expect(
      parseBoundedJsonResponse(
        new Response("{"),
        64,
        "test_json",
      ),
    ).rejects.toMatchObject({ name: "UpstreamResponseError" });
  });
});
