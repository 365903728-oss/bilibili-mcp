import { afterEach, describe, expect, it, vi } from "vitest";

import { buildPackageUpdateInfo } from "../src/utils/update-check.js";

function mockRegistryVersion(version: string) {
  return vi.fn(async () =>
    new Response(JSON.stringify({ version }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

describe("package update guidance", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("returns @latest MCP config and manual update commands", async () => {
    const result = await buildPackageUpdateInfo(mockRegistryVersion("9.9.9"));

    expect(result.package_name).toBe("@xzxzzx/bilibili-mcp");
    expect(result.latest_version).toBe("9.9.9");
    expect(result.update_available).toBe(true);
    expect(result.recommended_mcp_config).toEqual({
      command: "npx",
      args: ["-y", "@xzxzzx/bilibili-mcp@latest"],
    });
    expect(result.update_commands.global_update).toBe(
      "npm install -g @xzxzzx/bilibili-mcp@latest",
    );
    expect(result.update_commands.npx_config).toBe(
      "npx -y @xzxzzx/bilibili-mcp@latest config",
    );
    expect(result.notes_en.join(" ")).toContain("Use the @latest MCP config");
    expect(result.notes_zh.join(" ")).toContain("建议在 MCP 配置中使用 @latest");
  });

  it("reports unknown registry state without throwing", async () => {
    const result = await buildPackageUpdateInfo(
      vi.fn(async () => {
        throw new Error("offline");
      }),
    );

    expect(result.latest_version).toBeNull();
    expect(result.update_available).toBeNull();
    expect(result.notes.join(" ")).toContain("Could not reach the npm registry");
    expect(result.notes_en.join(" ")).toContain("Could not reach the npm registry");
    expect(result.notes_zh.join(" ")).toContain("无法连接 npm registry");
  });

  it("rejects redirects locally and never dispatches to Location", async () => {
    const fetchMock = vi.fn(async () =>
      new Response(null, {
        status: 302,
        headers: { Location: "http://127.0.0.1/private" },
      }),
    );

    const result = await buildPackageUpdateInfo(fetchMock);

    expect(result.latest_version).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({
      redirect: "manual",
      signal: expect.any(AbortSignal),
    });
  });

  it("returns bounded unknown state for an oversized registry body", async () => {
    const result = await buildPackageUpdateInfo(
      vi.fn(async () =>
        new Response(JSON.stringify({ version: "9.9.9" }), {
          status: 200,
          headers: { "Content-Length": String(64 * 1024 + 1) },
        }),
      ),
    );

    expect(result.latest_version).toBeNull();
    expect(result.update_available).toBeNull();
  });

  it("aborts a registry request at the five-second update deadline", async () => {
    vi.useFakeTimers();
    let requestSignal: AbortSignal | undefined;
    const fetchMock = vi.fn(
      (_input: string | URL | Request, init?: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          requestSignal = init?.signal ?? undefined;
          requestSignal?.addEventListener(
            "abort",
            () => reject(new DOMException("aborted", "AbortError")),
            { once: true },
          );
        }),
    );

    const resultPromise = buildPackageUpdateInfo(
      fetchMock as unknown as typeof fetch,
    );
    await vi.advanceTimersByTimeAsync(4_999);
    expect(requestSignal?.aborted).toBe(false);

    await vi.advanceTimersByTimeAsync(1);
    expect(requestSignal?.aborted).toBe(true);
    await expect(resultPromise).resolves.toMatchObject({
      latest_version: null,
      update_available: null,
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
