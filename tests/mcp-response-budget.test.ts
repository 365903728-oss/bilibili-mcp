import { describe, expect, it } from "vitest";

import { SECURITY_LIMITS } from "../src/security/limits.js";
import {
  toStructuredContent,
  toTextContent,
} from "../src/server/error-response.js";

describe("MCP success response budgets", () => {
  it("accepts an exact payload boundary and rejects one additional byte", () => {
    const overhead = Buffer.byteLength(
      JSON.stringify({ value: "" }, null, 2),
      "utf8",
    );
    const exact = {
      value: "x".repeat(SECURITY_LIMITS.mcpPayloadBytes - overhead),
    };
    const over = { value: `${exact.value}x` };

    const accepted = toTextContent(exact);
    expect(
      Buffer.byteLength(accepted.content[0].text, "utf8"),
    ).toBe(SECURITY_LIMITS.mcpPayloadBytes);
    expect(() => toTextContent(over)).toThrowError(
      expect.objectContaining({
        name: "ResourceLimitError",
        resource: "mcp_payload_bytes",
      }),
    );
  });

  it("keeps text and structured representations semantically identical", () => {
    const payload = {
      query: "quotes \" slash \\ newline \n control \u0001 emoji 🙂",
      rows: Array.from({ length: 50 }, (_, index) => ({
        index,
        value: "x".repeat(4_000),
      })),
    };

    const result = toStructuredContent(payload);
    expect(JSON.parse(result.content[0].text)).toEqual(
      result.structuredContent,
    );
    expect(
      Buffer.byteLength(JSON.stringify(result), "utf8"),
    ).toBeLessThanOrEqual(SECURITY_LIMITS.mcpResponseBytes);
  });

  it("accepts the complete structured envelope below 4 MiB and rejects the next two-byte step", () => {
    const payloadOverhead = Buffer.byteLength(
      JSON.stringify({ value: "" }, null, 2),
      "utf8",
    );
    const under = {
      value: "x".repeat(
        SECURITY_LIMITS.mcpPayloadBytes - payloadOverhead - 31,
      ),
    };
    const over = { value: `${under.value}x` };

    const accepted = toStructuredContent(under);
    expect(Buffer.byteLength(JSON.stringify(accepted), "utf8")).toBe(
      SECURITY_LIMITS.mcpResponseBytes - 1,
    );
    expect(() => toStructuredContent(over)).toThrowError(
      expect.objectContaining({
        name: "ResourceLimitError",
        resource: "mcp_response_bytes",
      }),
    );
  });
});
