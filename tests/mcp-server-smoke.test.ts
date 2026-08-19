import { execFileSync, spawn } from "node:child_process";
import { execSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
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

type CallToolRequest = {
  method: "tools/call";
  jsonrpc: "2.0";
  id: number;
  params: {
    name: string;
    arguments: Record<string, unknown>;
  };
};

type CallToolResponse = {
  content: Array<{ type: "text"; text: string }>;
  isError?: boolean;
  structuredContent?: Record<string, unknown>;
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

  it("serves initialize, exact tools/list, and a representative tools/call over public stdio JSON-RPC", async () => {
    const child = spawn(process.execPath, ["dist/index.js"], {
      stdio: ["pipe", "pipe", "pipe"],
    });
    const stdoutChunks: Buffer[] = [];
    const stderrChunks: Buffer[] = [];
    let pendingText = "";
    const messages = new Map<number, Record<string, unknown>>();
    const waiters = new Map<number, (message: Record<string, unknown>) => void>();

    child.stderr.on("data", (chunk) => stderrChunks.push(Buffer.from(chunk)));
    child.stdout.on("data", (chunk) => {
      stdoutChunks.push(Buffer.from(chunk));
      pendingText += chunk.toString("utf8");
      while (pendingText.includes("\n")) {
        const newline = pendingText.indexOf("\n");
        const line = pendingText.slice(0, newline).replace(/\r$/, "");
        pendingText = pendingText.slice(newline + 1);
        if (!line) continue;
        const message = JSON.parse(line) as Record<string, unknown>;
        if (typeof message.id === "number") {
          messages.set(message.id, message);
          waiters.get(message.id)?.(message);
          waiters.delete(message.id);
        }
      }
    });

    const send = (message: Record<string, unknown>) => {
      child.stdin.write(`${JSON.stringify(message)}\n`);
    };
    const waitForId = (id: number) => new Promise<Record<string, unknown>>((resolve, reject) => {
      const existing = messages.get(id);
      if (existing) {
        resolve(existing);
        return;
      }
      const timer = setTimeout(() => {
        waiters.delete(id);
        reject(new Error(`No stdio response for id ${id}`));
      }, 5_000);
      waiters.set(id, (message) => {
        clearTimeout(timer);
        resolve(message);
      });
    });

    try {
      send({
        jsonrpc: "2.0",
        id: 1,
        method: "initialize",
        params: {
          protocolVersion: "2025-06-18",
          capabilities: {},
          clientInfo: { name: "wire-smoke", version: "1.0.0" },
        },
      });
      const initialized = await waitForId(1);
      expect(initialized).toHaveProperty("result");

      send({ jsonrpc: "2.0", method: "notifications/initialized" });
      send({ jsonrpc: "2.0", id: 2, method: "tools/list", params: {} });
      const listed = await waitForId(2);
      const tools = (listed.result as { tools: Array<{ name: string }> }).tools;
      expect(tools.map((tool) => tool.name)).toEqual([
        "get_credential_setup_instructions",
        "check_bilibili_credentials",
        "check_mcp_update",
        "get_video_info",
        "get_video_comments",
        "get_video_transcript",
        "get_video_metadata",
        "get_video_chapters",
        "search_bilibili_videos",
        "search_bilibili_creators",
        "list_bilibili_favorite_videos",
      ]);

      send({
        jsonrpc: "2.0",
        id: 3,
        method: "tools/call",
        params: { name: "get_credential_setup_instructions", arguments: {} },
      });
      const called = await waitForId(3);
      const callResult = called.result as CallToolResponse;
      expect(callResult.isError).not.toBe(true);
      expect(callResult.content[0].type).toBe("text");
      expect(JSON.parse(callResult.content[0].text)).not.toMatchObject({
        Cookie: expect.anything(),
      });

      send({
        jsonrpc: "2.0",
        id: 4,
        method: "tools/call",
        params: {
          name: "get_video_info",
          arguments: {
            bvid_or_url: "BV1T6PQzQErF",
            preferred_lang: "fr",
          },
        },
      });
      const rejectedLanguage = await waitForId(4);
      const rejectedLanguageResult = rejectedLanguage.result as CallToolResponse;
      expect(rejectedLanguageResult.isError).toBe(true);
      expect(JSON.parse(rejectedLanguageResult.content[0].text)).toMatchObject({
        code: "VALIDATION_ERROR",
      });

      send({
        jsonrpc: "2.0",
        id: 5,
        method: "tools/call",
        params: {
          name: "search_bilibili_creators",
          arguments: { limit: 11 },
        },
      });
      const creatorSearchValidation = await waitForId(5);
      const creatorSearchResult =
        creatorSearchValidation.result as CallToolResponse;
      expect(creatorSearchResult.isError).toBe(true);
      expect(JSON.parse(creatorSearchResult.content[0].text)).toMatchObject({
        code: "VALIDATION_ERROR",
      });
    } finally {
      child.stdin.end();
      const closed = new Promise<void>((resolve) => child.once("close", () => resolve()));
      child.kill();
      await closed;
    }

    const stdout = Buffer.concat(stdoutChunks).toString("utf8");
    const stderr = Buffer.concat(stderrChunks).toString("utf8");
    expect(() => stdout.trim().split(/\r?\n/).forEach((line) => JSON.parse(line))).not.toThrow();
    expect(stderr).toContain("Bilibili MCP server running on stdio");
    expect(stdout).not.toContain("Bilibili MCP server running on stdio");
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
      "search_bilibili_creators",
      "list_bilibili_favorite_videos",
    ]);
  });

  it("maps a base64url cursor with invalid JSON to VALIDATION_ERROR", async () => {
    const handler = getMcpHandler<CallToolRequest, CallToolResponse>(
      "tools/call",
    );

    const result = await handler({
      method: "tools/call",
      jsonrpc: "2.0",
      id: 2,
      params: {
        name: "list_bilibili_favorite_videos",
        arguments: {
          cursor: Buffer.from("not-json", "utf8").toString("base64url"),
        },
      },
    });

    expect(result.isError).toBe(true);
    expect(result).not.toHaveProperty("structuredContent");
    expect(JSON.parse(result.content[0].text).code).toBe("VALIDATION_ERROR");
  });

  it("dist/cli.js no-arg starts stdio server and logs to stderr", async () => {
    const child = spawn(process.execPath, ["dist/cli.js"], {
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

  it("dist/cli.js doctor --json with isolated HOME emits single JSON object and exits 1", async () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "bili-mcp-test-"));
    try {
      const childEnv = {
        ...process.env,
        HOME: tmpDir,
        USERPROFILE: tmpDir,
      };
      delete childEnv.BILIBILI_SESSDATA;
      delete childEnv.BILIBILI_BILI_JCT;
      delete childEnv.BILIBILI_DEDEUSERID;

      const child = spawn(
        process.execPath,
        ["dist/cli.js", "doctor", "--json"],
        {
          stdio: ["pipe", "pipe", "pipe"],
          env: childEnv,
        },
      );

      const stdoutChunks: Buffer[] = [];
      child.stdout.on("data", (chunk) => {
        stdoutChunks.push(Buffer.from(chunk));
      });

      const code = await new Promise<number | null>((resolve) => {
        child.on("close", resolve);
      });

      const stdout = Buffer.concat(stdoutChunks).toString("utf8").trim();
      const parsed = JSON.parse(stdout);

      expect(parsed).toHaveProperty("package_name");
      expect(parsed).toHaveProperty("status");
      expect(parsed.status).toBe("needs_credentials");
      expect(code).toBe(1);
    } finally {
      const resolvedTmpDir = path.resolve(tmpDir);
      if (path.dirname(resolvedTmpDir) !== path.resolve(os.tmpdir())) {
        throw new Error(`Unsafe temporary cleanup target: ${resolvedTmpDir}`);
      }
      fs.rmSync(resolvedTmpDir, { recursive: true, force: true });
    }
  });

  it("dist/cli.js setup with piped stdin (non-TTY) fast-fails with exit 1", async () => {
    const child = spawn(process.execPath, ["dist/cli.js", "setup"], {
      stdio: ["pipe", "pipe", "pipe"],
    });

    const stderrChunks: Buffer[] = [];
    child.stderr.on("data", (chunk) => {
      stderrChunks.push(Buffer.from(chunk));
    });

    // Close stdin immediately to simulate non-TTY
    child.stdin.end();

    const code = await new Promise<number | null>((resolve) => {
      child.on("close", resolve);
    });

    const stderr = Buffer.concat(stderrChunks).toString("utf8");
    expect(stderr).toContain("Error: setup requires an interactive terminal");
    expect(code).toBe(1);
  });

  it.each(["-V", "--version", "-v", "version"])(
    "dist/cli.js preserves the %s version entry",
    (entry) => {
      const stdout = execFileSync(
        process.execPath,
        ["dist/cli.js", entry],
        { encoding: "utf8" },
      ).trim();
      const pkg = JSON.parse(
        fs.readFileSync(new URL("../package.json", import.meta.url), "utf8"),
      );

      expect(stdout).toBe(pkg.version);
    },
  );

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
