import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

function wbiResponse(): Response {
  return new Response(
    JSON.stringify({
      data: {
        wbi_img: {
          img_url:
            "https://i0.hdslb.com/bfs/wbi/abcdefghijklmnopqrstuvwxyz123456.png",
          sub_url:
            "https://i0.hdslb.com/bfs/wbi/123456abcdefghijklmnopqrstuvwxyz.png",
        },
      },
    }),
    { status: 200 },
  );
}

beforeEach(() => {
  vi.resetModules();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("process-owned bootstrap single flights", () => {
  it("keeps the fingerprint refresh alive when one waiter cancels", async () => {
    const gate = deferred<Response>();
    let backendSignal: AbortSignal | undefined;
    const fetchMock = vi.fn(
      async (_url: string | URL | Request, init?: RequestInit) => {
        backendSignal = init?.signal ?? undefined;
        return await gate.promise;
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    const { getBuvid } = await import("../src/bilibili/fingerprint.js");
    const { runWithOperationSignal } = await import(
      "../src/security/operation-context.js"
    );
    const firstController = new AbortController();

    const first = runWithOperationSignal(
      firstController.signal,
      async () => await getBuvid(),
    );
    const second = getBuvid();
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    firstController.abort();

    await expect(first).rejects.toMatchObject({ name: "AbortError" });
    expect(backendSignal?.aborted).toBe(false);
    gate.resolve(
      new Response(
        JSON.stringify({
          code: 0,
          data: {
            b_3: "synthetic-buvid-3",
            b_4: "synthetic-buvid-4",
          },
        }),
        { status: 200 },
      ),
    );
    await expect(second).resolves.toEqual({
      buvid3: "synthetic-buvid-3",
      buvid4: "synthetic-buvid-4",
    });
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("bounds fingerprint waiters while retaining one backend request", async () => {
    const gate = deferred<Response>();
    const fetchMock = vi.fn(async () => await gate.promise);
    vi.stubGlobal("fetch", fetchMock);
    const { getBuvid } = await import("../src/bilibili/fingerprint.js");

    const waiters = Array.from({ length: 64 }, () => getBuvid());
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    await expect(getBuvid()).rejects.toMatchObject({
      name: "ResourceLimitError",
      resource: "fingerprint_waiters",
      limit: 64,
    });
    gate.resolve(
      new Response(
        JSON.stringify({
          code: 0,
          data: {
            b_3: "synthetic-buvid-3",
            b_4: "synthetic-buvid-4",
          },
        }),
        { status: 200 },
      ),
    );
    await expect(Promise.all(waiters)).resolves.toHaveLength(64);
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("keeps the WBI refresh alive when one waiter cancels", async () => {
    const gate = deferred<Response>();
    let backendSignal: AbortSignal | undefined;
    const fetchMock = vi.fn(
      async (_url: string | URL | Request, init?: RequestInit) => {
        backendSignal = init?.signal ?? undefined;
        return await gate.promise;
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    const { getWBI } = await import("../src/bilibili/wbi.js");
    const firstController = new AbortController();

    const first = getWBI({ signal: firstController.signal });
    const second = getWBI();
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    firstController.abort();

    await expect(first).rejects.toMatchObject({ name: "AbortError" });
    expect(backendSignal?.aborted).toBe(false);
    gate.resolve(wbiResponse());
    await expect(second).resolves.toMatchObject({
      imgKey: "abcdefghijklmnopqrstuvwxyz123456",
      subKey: "123456abcdefghijklmnopqrstuvwxyz",
    });
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("applies each caller's WBI deadline without aborting shared work", async () => {
    vi.useFakeTimers();
    const gate = deferred<Response>();
    const fetchMock = vi.fn(async () => await gate.promise);
    vi.stubGlobal("fetch", fetchMock);
    const { getWBI } = await import("../src/bilibili/wbi.js");

    const first = getWBI({ deadlineAt: Date.now() + 5 });
    const firstOutcome = expect(first).rejects.toMatchObject({
      name: "TimeoutError",
    });
    const second = getWBI();
    await vi.advanceTimersByTimeAsync(5);
    await firstOutcome;
    gate.resolve(wbiResponse());
    await expect(second).resolves.toMatchObject({
      imgKey: "abcdefghijklmnopqrstuvwxyz123456",
    });
    expect(fetchMock).toHaveBeenCalledOnce();
    vi.useRealTimers();
  });

  it("bounds update-check waiters while retaining one registry request", async () => {
    const gate = deferred<Response>();
    const fetchMock = vi.fn(async () => await gate.promise);
    vi.stubGlobal("fetch", fetchMock);
    const { buildPackageUpdateInfo } = await import(
      "../src/utils/update-check.js"
    );

    const waiters = Array.from(
      { length: 64 },
      () => buildPackageUpdateInfo(),
    );
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    await expect(buildPackageUpdateInfo()).rejects.toMatchObject({
      name: "ResourceLimitError",
      resource: "update_check_waiters",
      limit: 64,
    });
    gate.resolve(
      new Response(JSON.stringify({ version: "9.9.9" }), {
        status: 200,
      }),
    );
    await expect(Promise.all(waiters)).resolves.toHaveLength(64);
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("lets one update-check waiter cancel without aborting another", async () => {
    const gate = deferred<Response>();
    let backendSignal: AbortSignal | undefined;
    const fetchMock = vi.fn(
      async (_url: string | URL | Request, init?: RequestInit) => {
        backendSignal = init?.signal ?? undefined;
        return await gate.promise;
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    const { buildPackageUpdateInfo } = await import(
      "../src/utils/update-check.js"
    );
    const firstController = new AbortController();

    const first = buildPackageUpdateInfo(
      globalThis.fetch,
      firstController.signal,
    );
    const second = buildPackageUpdateInfo();
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    firstController.abort();

    await expect(first).rejects.toMatchObject({ name: "AbortError" });
    expect(backendSignal?.aborted).toBe(false);
    gate.resolve(
      new Response(JSON.stringify({ version: "9.9.9" }), {
        status: 200,
      }),
    );
    await expect(second).resolves.toMatchObject({
      latest_version: "9.9.9",
      update_available: true,
    });
    expect(fetchMock).toHaveBeenCalledOnce();
  });
});
