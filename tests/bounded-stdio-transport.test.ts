import { PassThrough } from "node:stream";

import { serializeMessage } from "@modelcontextprotocol/sdk/shared/stdio.js";
import { describe, expect, it, vi } from "vitest";

import { BoundedStdioServerTransport } from "../src/server/bounded-stdio-transport.js";

describe("BoundedStdioServerTransport", () => {
  it("accepts a complete frame below the byte limit", async () => {
    const input = new PassThrough();
    const output = new PassThrough();
    const transport = new BoundedStdioServerTransport(input, output, 256, 256);
    const onMessage = vi.fn();
    transport.onmessage = onMessage;
    await transport.start();

    input.write(
      `${JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "ping",
      })}\n`,
    );

    await vi.waitFor(() => expect(onMessage).toHaveBeenCalledTimes(1));
    await transport.close();
  });

  it("fails closed on an oversized unterminated frame", async () => {
    const input = new PassThrough();
    const output = new PassThrough();
    const transport = new BoundedStdioServerTransport(input, output, 32, 256);
    const onError = vi.fn();
    const onClose = vi.fn();
    transport.onerror = onError;
    transport.onclose = onClose;
    await transport.start();

    input.write(Buffer.alloc(33, 0x61));

    await vi.waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({
        message: "MCP stdio frame exceeds 32 bytes",
      }),
    );
  });

  it("fails closed before parsing an oversized newline-terminated frame", async () => {
    const input = new PassThrough();
    const output = new PassThrough();
    const transport = new BoundedStdioServerTransport(input, output, 32, 256);
    const onMessage = vi.fn();
    const onError = vi.fn();
    transport.onmessage = onMessage;
    transport.onerror = onError;
    await transport.start();

    input.write(`${"a".repeat(33)}\n`);

    await vi.waitFor(() => expect(onError).toHaveBeenCalledTimes(1));
    expect(onMessage).not.toHaveBeenCalled();
  });

  it("accepts a valid frame exactly at the byte boundary across small chunks", async () => {
    const input = new PassThrough();
    const output = new PassThrough();
    const line = JSON.stringify({
      jsonrpc: "2.0",
      id: 7,
      method: "ping",
      params: { value: "分块" },
    });
    const bytes = Buffer.from(line, "utf8");
    const transport = new BoundedStdioServerTransport(
      input,
      output,
      bytes.byteLength,
      512,
    );
    const onMessage = vi.fn();
    transport.onmessage = onMessage;
    await transport.start();

    for (const byte of bytes) input.write(Buffer.from([byte]));
    input.write("\n");

    await vi.waitFor(() => expect(onMessage).toHaveBeenCalledTimes(1));
    await transport.close();
  });

  it("counts UTF-8 bytes rather than JavaScript characters", async () => {
    const input = new PassThrough();
    const output = new PassThrough();
    const line = JSON.stringify({
      jsonrpc: "2.0",
      id: 8,
      method: "ping",
      params: { value: "你" },
    });
    const transport = new BoundedStdioServerTransport(
      input,
      output,
      Buffer.byteLength(line, "utf8") - 1,
      512,
    );
    const onError = vi.fn();
    transport.onerror = onError;
    await transport.start();

    input.write(`${line}\n`);

    await vi.waitFor(() => expect(onError).toHaveBeenCalledTimes(1));
  });

  it("parses multiple bounded frames delivered in one chunk", async () => {
    const input = new PassThrough();
    const output = new PassThrough();
    const transport = new BoundedStdioServerTransport(input, output, 256, 512);
    const onMessage = vi.fn();
    transport.onmessage = onMessage;
    await transport.start();

    input.write(
      `${JSON.stringify({ jsonrpc: "2.0", id: 1, method: "ping" })}\n` +
        `${JSON.stringify({ jsonrpc: "2.0", id: 2, method: "ping" })}\n`,
    );

    await vi.waitFor(() => expect(onMessage).toHaveBeenCalledTimes(2));
    await transport.close();
  });

  it("writes an exact outbound frame boundary and fails closed one byte below it", async () => {
    const message = {
      jsonrpc: "2.0" as const,
      id: 9,
      result: { value: "bounded output" },
    };
    const serialized = serializeMessage(message);
    const serializedBytes = Buffer.byteLength(serialized, "utf8");

    const exactInput = new PassThrough();
    const exactOutput = new PassThrough();
    let exactWritten = "";
    exactOutput.on("data", (chunk) => {
      exactWritten += chunk.toString();
    });
    const exactTransport = new BoundedStdioServerTransport(
      exactInput,
      exactOutput,
      256,
      serializedBytes,
    );
    await exactTransport.start();
    await exactTransport.send(message);
    expect(exactWritten).toBe(serialized);
    await exactTransport.close();

    const overInput = new PassThrough();
    const overOutput = new PassThrough();
    let overWritten = "";
    overOutput.on("data", (chunk) => {
      overWritten += chunk.toString();
    });
    const overTransport = new BoundedStdioServerTransport(
      overInput,
      overOutput,
      256,
      serializedBytes - 1,
    );
    const onError = vi.fn();
    const onClose = vi.fn();
    overTransport.onerror = onError;
    overTransport.onclose = onClose;
    await overTransport.start();

    await expect(overTransport.send(message)).rejects.toThrow(
      `MCP stdio response exceeds ${serializedBytes - 1} bytes`,
    );
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(overWritten).toBe("");
  });
});
