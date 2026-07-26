import { spawn } from "node:child_process";
import { execSync } from "node:child_process";
import fs from "node:fs";
import { beforeAll, describe, expect, it } from "vitest";

import { getMcpHandler } from "./helpers/mcp.js";
import { server } from "../src/server.js";

type ListToolsRequest = {
  method: "tools/list";
  jsonrpc: "2.0";
  id: number;
};

type ListToolsResponse = {
  tools: Array<{ name: string }>;
};

describe("MCP stdio entrypoint", () => {
  beforeAll(() => {
    execSync("npm run build", { stdio: "pipe" });
  });

  it("starts the built stdio server and logs startup to stderr", async () => {
    const child = spawn(process.execPath, ["dist/index.js"], {
      stdio: ["pipe", "pipe", "pipe"],
    });

    const stderrChunks: Buffer[] = [];
    const stdoutChunks: Buffer[] = [];
    const READY_SIGNAL = "Bilibili MCP server running on stdio";
    const TIMEOUT_MS = 3_000;

    child.stdout.on("data", (chunk) => {
      stdoutChunks.push(Buffer.from(chunk));
    });

    const ready = new Promise<void>((resolve, reject) => {
      const onData = (chunk: Buffer) => {
        stderrChunks.push(Buffer.from(chunk));
        const text = Buffer.concat(stderrChunks).toString("utf8");
        if (text.includes(READY_SIGNAL)) {
          cleanup();
          resolve();
        }
      };
      const onError = (err: Error) => {
        cleanup();
        reject(err);
      };
      const onExit = (code: number | null) => {
        cleanup();
        reject(new Error(`Server exited with code ${code} before ready signal`));
      };
      const timer = setTimeout(() => {
        cleanup();
        reject(new Error(`Server did not emit ready signal within ${TIMEOUT_MS}ms`));
      }, TIMEOUT_MS);

      const cleanup = () => {
        clearTimeout(timer);
        child.stderr.removeListener("data", onData);
        child.removeListener("error", onError);
        child.removeListener("exit", onExit);
      };

      child.stderr.on("data", onData);
      child.on("error", onError);
      child.on("exit", onExit);
    });

    try {
      await ready;
    } finally {
      const closed = new Promise<void>((resolve) => child.on("close", () => resolve()));
      child.kill();
      await closed;
    }

    const stderr = Buffer.concat(stderrChunks).toString("utf8");
    const stdout = Buffer.concat(stdoutChunks).toString("utf8");

    expect(stderr).toContain(READY_SIGNAL);
    expect(stdout).toBe("");
  });

  it("lists all public tools through the registered MCP handler", async () => {
    const handler = getMcpHandler<ListToolsRequest, ListToolsResponse>(
      "tools/list",
    );

    const result = await handler({
      method: "tools/list",
      jsonrpc: "2.0",
      id: 1,
    });

    expect(result.tools.map((tool) => tool.name)).toEqual([
      "get_credential_setup_instructions",
      "check_bilibili_credentials",
      "check_mcp_update",
      "get_video_info",
      "get_video_comments",
      "get_video_transcript",
      "get_video_metadata",
      "get_video_chapters",
      "search_bilibili_videos",
    ]);
  });

  it("server metadata version matches package.json version", () => {
    const pkg = JSON.parse(
      fs.readFileSync(new URL("../package.json", import.meta.url), "utf8"),
    );

    type ServerWithInfo = { _serverInfo?: { name: string; version: string } };
    const info = (server as unknown as ServerWithInfo)._serverInfo;

    expect(info).toBeDefined();
    expect(info!.version).toBe(pkg.version);
  });
});
