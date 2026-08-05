import type {
  JSONRPCMessage,
} from "@modelcontextprotocol/sdk/types.js";
import { JSONRPCMessageSchema } from "@modelcontextprotocol/sdk/types.js";
import type {
  Transport,
} from "@modelcontextprotocol/sdk/shared/transport.js";
import { serializeMessage } from "@modelcontextprotocol/sdk/shared/stdio.js";

import { SECURITY_LIMITS } from "../security/limits.js";

type ReadableStdio = NodeJS.ReadableStream & {
  pause(): unknown;
  listenerCount(eventName: string | symbol): number;
};

/**
 * Newline-delimited MCP stdio transport with strict byte ceilings.
 *
 * The upstream SDK ReadBuffer concatenates until a newline without a maximum.
 * This transport terminates the session as soon as either an unterminated
 * frame or a completed frame exceeds the configured byte limit.
 */
export class BoundedStdioServerTransport implements Transport {
  private readonly buffer: Buffer;
  private bufferedBytes = 0;
  private started = false;
  private closed = false;

  onclose?: () => void;
  onerror?: (error: Error) => void;
  onmessage?: (message: JSONRPCMessage) => void;

  constructor(
    private readonly stdin: ReadableStdio = process.stdin,
    private readonly stdout: NodeJS.WritableStream = process.stdout,
    private readonly maxInboundFrameBytes = SECURITY_LIMITS.stdioFrameBytes,
    private readonly maxOutboundFrameBytes =
      SECURITY_LIMITS.stdioOutboundFrameBytes,
  ) {
    if (!Number.isSafeInteger(maxInboundFrameBytes) || maxInboundFrameBytes < 1) {
      throw new TypeError("maxInboundFrameBytes must be a positive safe integer");
    }
    if (!Number.isSafeInteger(maxOutboundFrameBytes) || maxOutboundFrameBytes < 1) {
      throw new TypeError("maxOutboundFrameBytes must be a positive safe integer");
    }
    this.buffer = Buffer.allocUnsafe(maxInboundFrameBytes);
  }

  private readonly handleData = (chunk: Buffer | string): void => {
    if (this.closed) return;
    const incoming = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    let offset = 0;

    while (offset < incoming.length && !this.closed) {
      const newline = incoming.indexOf(0x0a, offset);
      const end = newline === -1 ? incoming.length : newline;
      const part = incoming.subarray(offset, end);

      if (this.bufferedBytes + part.length > this.maxInboundFrameBytes) {
        this.failClosed(
          new Error(
            `MCP stdio frame exceeds ${this.maxInboundFrameBytes} bytes`,
          ),
        );
        return;
      }

      if (part.length > 0) {
        part.copy(this.buffer, this.bufferedBytes);
        this.bufferedBytes += part.length;
      }

      if (newline === -1) return;

      const line = this.buffer
        .toString("utf8", 0, this.bufferedBytes)
        .replace(/\r$/, "");
      this.buffer.fill(0, 0, this.bufferedBytes);
      this.bufferedBytes = 0;
      offset = newline + 1;

      try {
        if (line.length === 0) continue;
        const message = JSONRPCMessageSchema.parse(JSON.parse(line));
        this.onmessage?.(message);
      } catch (error) {
        this.onerror?.(
          error instanceof Error ? error : new Error("Invalid MCP stdio frame"),
        );
      }
    }
  };

  private readonly handleError = (error: Error): void => {
    this.onerror?.(error);
  };

  private failClosed(error: Error): void {
    this.buffer.fill(0, 0, this.bufferedBytes);
    this.bufferedBytes = 0;
    this.onerror?.(error);
    void this.close();
  }

  async start(): Promise<void> {
    if (this.started) {
      throw new Error("BoundedStdioServerTransport already started");
    }
    this.started = true;
    this.stdin.on("data", this.handleData);
    this.stdin.on("error", this.handleError);
  }

  async close(): Promise<void> {
    if (this.closed) return;
    this.closed = true;
    this.stdin.off("data", this.handleData);
    this.stdin.off("error", this.handleError);
    if (this.stdin.listenerCount("data") === 0) {
      this.stdin.pause();
    }
    this.buffer.fill(0, 0, this.bufferedBytes);
    this.bufferedBytes = 0;
    this.onclose?.();
  }

  async send(message: JSONRPCMessage): Promise<void> {
    if (this.closed) {
      throw new Error("MCP stdio transport is closed");
    }
    const serialized = serializeMessage(message);
    const size = Buffer.byteLength(serialized, "utf8");
    if (size > this.maxOutboundFrameBytes) {
      const error = new Error(
        `MCP stdio response exceeds ${this.maxOutboundFrameBytes} bytes`,
      );
      this.failClosed(error);
      throw error;
    }

    await new Promise<void>((resolve, reject) => {
      const onError = (error: Error) => {
        this.stdout.off("error", onError);
        reject(error);
      };
      this.stdout.once("error", onError);
      this.stdout.write(serialized, () => {
        this.stdout.off("error", onError);
        resolve();
      });
    });
  }
}
