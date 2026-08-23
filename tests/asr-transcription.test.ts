import { EventEmitter } from "node:events";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { PassThrough } from "node:stream";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ASR_TEMP_PREFIX,
  buildAsrRuntimeEnv,
  cleanupAsrTempDir,
  createAsrTempDir,
  downloadPlaybackAudio,
  MAX_ASR_AUDIO_BYTES,
  MAX_ASR_STDOUT_BYTES,
  parseAsrNdjson,
  runManagedAsrRuntime,
  transcribeVideoPart,
} from "../src/asr/transcription.js";
import type { PlaybackAudioCandidate } from "../src/bilibili/playback.js";
import { FakeIpDnsError } from "../src/security/pinned-https.js";
import { AsrError } from "../src/utils/errors.js";

const CPU_PROFILE = { device: "cpu", computeType: "int8" } as const;

const tempDirs: string[] = [];
const candidate: PlaybackAudioCandidate = {
  url: "https://upos-sz-mirrorcoso1.bilivideo.com/audio.m4s?token=signed",
  mimeType: "audio/mp4",
  bandwidth: 64_000,
  representationId: 30216,
};

function readyDependencies() {
  return {
    getPaths: () => ({
      root: "managed-root",
      venv: path.join("managed-root", "venv"),
      model: path.join("managed-root", "models"),
      stateFile: path.join("managed-root", "state.json"),
    }),
    getState: () => ({
      kind: "ready" as const,
      executionProfile: CPU_PROFILE,
      deviceReadiness: "ready" as const,
      migrationStatus: "completed" as const,
    }),
  };
}

function fakeNdjson() {
  return [
    JSON.stringify({ type: "meta", language: "zh" }),
    JSON.stringify({ type: "segment", start: 0, end: 1.25, text: "你好" }),
    JSON.stringify({ type: "segment", start: 1.25, end: 2.5, text: "世界" }),
    JSON.stringify({ type: "done", count: 2 }),
    "",
  ].join("\n");
}

afterEach(async () => {
  for (const dir of tempDirs.splice(0)) {
    try {
      await cleanupAsrTempDir(dir);
    } catch {
      await fs.promises.rm(dir, { recursive: true, force: true });
    }
  }
});

describe("managed ASR output protocol", () => {
  it("accepts ordered bounded NDJSON", () => {
    expect(parseAsrNdjson(fakeNdjson())).toEqual({
      language: "zh",
      segments: [
        { from: 0, to: 1.25, content: "你好" },
        { from: 1.25, to: 2.5, content: "世界" },
      ],
    });
  });

  it("sanitizes remote ASR segment text", () => {
    const output = [
      JSON.stringify({ type: "meta", language: "zh" }),
      JSON.stringify({
        type: "segment",
        start: 0,
        end: 1.25,
        text: "你好" + String.fromCharCode(0x202e, 0x200b) + "世界",
      }),
      JSON.stringify({ type: "done", count: 1 }),
      "",
    ].join("\n");
    expect(parseAsrNdjson(output).segments[0].content).toBe("你好世界");
  });

  it.each([
    "not-json\n",
    `${JSON.stringify({ type: "meta", language: "zh" })}\n\n${JSON.stringify({ type: "done", count: 0 })}\n`,
    `${JSON.stringify({ type: "segment", start: 0, end: 1, text: "x" })}\n${JSON.stringify({ type: "done", count: 1 })}\n`,
    `${JSON.stringify({ type: "meta", language: "zh", extra: true })}\n${JSON.stringify({ type: "done", count: 0 })}\n`,
    `${JSON.stringify({ type: "meta", language: "zh" })}\n${JSON.stringify({ type: "segment", start: 2, end: 1, text: "x" })}\n${JSON.stringify({ type: "done", count: 1 })}\n`,
    `${JSON.stringify({ type: "meta", language: "zh" })}\n${JSON.stringify({ type: "done", count: 1 })}\n`,
  ])("rejects malformed or inconsistent output", (output) => {
    expect(() => parseAsrNdjson(output)).toThrowError(AsrError);
  });

  it("rejects output larger than two MiB", () => {
    expect(() => parseAsrNdjson("x".repeat(MAX_ASR_STDOUT_BYTES + 1))).toThrow("exceeded");
  });
});

describe("ASR child isolation and lifecycle", () => {
  it("passes model/audio only through argv with shell disabled and a filtered environment", async () => {
    const child = new EventEmitter() as EventEmitter & {
      stdout: PassThrough;
      stderr: PassThrough;
      kill: ReturnType<typeof vi.fn>;
    };
    child.stdout = new PassThrough();
    child.stderr = new PassThrough();
    child.kill = vi.fn();
    const spawnFn = vi.fn(() => child as never);

    const promise = runManagedAsrRuntime(
      "managed-python",
      "managed-model",
      "temporary-audio",
      { executionProfile: CPU_PROFILE, spawnFn: spawnFn as never },
    );
    child.stdout.write(fakeNdjson());
    child.emit("close", 0);

    await expect(promise).resolves.toMatchObject({ language: "zh" });
    expect(spawnFn).toHaveBeenCalledOnce();
    const [executable, argv, options] = spawnFn.mock.calls[0];
    expect(executable).toBe("managed-python");
    expect(argv[0]).toBe("-I");
    expect(argv.slice(-4)).toEqual(["managed-model", "temporary-audio", "cpu", "int8"]);
    expect(argv[2]).toContain("device=sys.argv[3]");
    expect(argv[2]).toContain("compute_type=sys.argv[4]");
    expect(argv[2]).toContain("CreateJobObjectW");
    expect(argv[2]).toContain("AssignProcessToJobObject");
    expect(argv[2]).toContain("RLIMIT_AS");
    expect(argv[2]).toContain("RLIMIT_CPU");
    expect(argv[2]).toContain("RLIMIT_NPROC");
    expect(options.shell).toBe(false);
    expect(options.stdio).toEqual(["ignore", "pipe", "pipe"]);
    expect(options.detached).toBe(process.platform !== "win32");
    expect(options.env).not.toHaveProperty("BILIBILI_SESSDATA");
    expect(options.env).not.toHaveProperty("API_TOKEN");
    expect(options.env.HF_HUB_OFFLINE).toBe("1");
  });

  it("kills the child on cancellation and waits for close before rejecting", async () => {
    const controller = new AbortController();
    const child = new EventEmitter() as EventEmitter & {
      stdout: PassThrough;
      stderr: PassThrough;
      kill: ReturnType<typeof vi.fn>;
    };
    child.stdout = new PassThrough();
    child.stderr = new PassThrough();
    child.kill = vi.fn(() => true);
    const spawnFn = vi.fn(() => child as never);
    const promise = runManagedAsrRuntime("python", "model", "audio", {
      executionProfile: CPU_PROFILE,
      spawnFn: spawnFn as never,
      signal: controller.signal,
    });
    let settled = false;
    void promise.then(
      () => {
        settled = true;
      },
      () => {
        settled = true;
      },
    );

    controller.abort();
    await Promise.resolve();

    expect(child.kill).toHaveBeenCalledWith("SIGKILL");
    expect(settled).toBe(false);

    child.emit("close", null);
    await expect(promise).rejects.toMatchObject({ name: "AbortError" });
  });

  it("kills the child and returns a bounded timeout error", async () => {
    const child = new EventEmitter() as EventEmitter & {
      stdout: PassThrough;
      stderr: PassThrough;
      kill: ReturnType<typeof vi.fn>;
    };
    child.stdout = new PassThrough();
    child.stderr = new PassThrough();
    child.kill = vi.fn(() => {
      queueMicrotask(() => child.emit("close", null));
      return true;
    });
    const spawnFn = vi.fn(() => child as never);

    const promise = runManagedAsrRuntime("python", "model", "audio", {
      executionProfile: CPU_PROFILE,
      spawnFn: spawnFn as never,
      timeoutMs: 5,
    });

    await expect(promise).rejects.toMatchObject({ code: "ASR_TRANSCRIPTION_TIMEOUT" });
    expect(child.kill).toHaveBeenCalledWith("SIGKILL");
  });

  it("kills the child when stdout exceeds its bound", async () => {
    const child = new EventEmitter() as EventEmitter & {
      stdout: PassThrough;
      stderr: PassThrough;
      kill: ReturnType<typeof vi.fn>;
    };
    child.stdout = new PassThrough();
    child.stderr = new PassThrough();
    child.kill = vi.fn(() => {
      queueMicrotask(() => child.emit("close", null));
      return true;
    });
    const spawnFn = vi.fn(() => child as never);
    const promise = runManagedAsrRuntime("python", "model", "audio", {
      executionProfile: CPU_PROFILE,
      spawnFn: spawnFn as never,
      timeoutMs: 1_000,
    });
    child.stdout.write(Buffer.alloc(MAX_ASR_STDOUT_BYTES + 1));

    await expect(promise).rejects.toMatchObject({ code: "ASR_OUTPUT_INVALID" });
    expect(child.kill).toHaveBeenCalledWith("SIGKILL");
  });

  it("filters credentials, tokens, Python injection, and proxy values from child env", () => {
    const env = buildAsrRuntimeEnv({
      PATH: "safe-path",
      SYSTEMROOT: "safe-root",
      BILIBILI_SESSDATA: "secret",
      BILIBILI_BILI_JCT: "secret",
      BILIBILI_DEDEUSERID: "secret",
      PYTHONPATH: "injected",
      PYTHONHOME: "injected",
      API_TOKEN: "secret",
      HTTPS_PROXY: "http://secret-proxy",
    });

    expect(env).toMatchObject({ PATH: "safe-path", SYSTEMROOT: "safe-root" });
    expect(JSON.stringify(env)).not.toContain("secret");
    expect(env).not.toHaveProperty("PYTHONPATH");
    expect(env).not.toHaveProperty("PYTHONHOME");
    expect(env).not.toHaveProperty("HTTPS_PROXY");
  });
});

describe("temporary audio download", () => {
  it("refuses to remove or write outside its unique ASR temp directory", async () => {
    const unsafe = path.join(os.tmpdir(), "not-an-asr-request", "audio.m4a");
    await expect(downloadPlaybackAudio([candidate], unsafe, vi.fn())).rejects.toMatchObject({
      code: "ASR_TRANSCRIPTION_FAILED",
    });

    const prefixOnly = path.join(os.tmpdir(), `${ASR_TEMP_PREFIX}models`, "audio.m4a");
    await expect(downloadPlaybackAudio([candidate], prefixOnly, vi.fn())).rejects.toMatchObject({
      code: "ASR_TRANSCRIPTION_FAILED",
    });
  });

  it("streams audio without sending Cookie headers", async () => {
    const dir = await createAsrTempDir(ASR_TEMP_PREFIX);
    tempDirs.push(dir);
    const destination = path.join(dir, "audio.m4a");
    const fetchFn = vi.fn(async (_url: string | URL | Request, init?: RequestInit) => {
      const headers = new Headers(init?.headers);
      expect(headers.has("cookie")).toBe(false);
      return new Response(new Uint8Array([1, 2, 3]), {
        status: 200,
        headers: { "content-type": "audio/mp4", "content-length": "3" },
      });
    });

    await downloadPlaybackAudio([candidate], destination, fetchFn);

    expect(await fs.promises.readFile(destination)).toEqual(Buffer.from([1, 2, 3]));
  });

  it("returns ASR_FAKE_IP_DNS only when every attempted candidate resolves to Fake-IP", async () => {
    const dir = await createAsrTempDir(ASR_TEMP_PREFIX);
    tempDirs.push(dir);
    const destination = path.join(dir, "audio.m4a");
    const candidates = [
      candidate,
      { ...candidate, url: "https://upos-sz-mirrorcoso2.bilivideo.com/audio.m4s" },
    ];
    const fetchFn = vi.fn(async () => {
      throw new FakeIpDnsError();
    });

    await expect(
      downloadPlaybackAudio(candidates, destination, fetchFn),
    ).rejects.toMatchObject({
      code: "ASR_FAKE_IP_DNS",
      retryable: false,
    });
    expect(fetchFn).toHaveBeenCalledTimes(2);
  });

  it("continues to a usable candidate after a Fake-IP DNS failure", async () => {
    const dir = await createAsrTempDir(ASR_TEMP_PREFIX);
    tempDirs.push(dir);
    const destination = path.join(dir, "audio.m4a");
    const candidates = [
      candidate,
      { ...candidate, url: "https://upos-sz-mirrorcoso2.bilivideo.com/audio.m4s" },
    ];
    const fetchFn = vi
      .fn()
      .mockRejectedValueOnce(new FakeIpDnsError())
      .mockResolvedValueOnce(
        new Response(new Uint8Array([1, 2, 3]), {
          status: 200,
          headers: { "content-type": "audio/mp4", "content-length": "3" },
        }),
      );

    await downloadPlaybackAudio(candidates, destination, fetchFn);

    expect(await fs.promises.readFile(destination)).toEqual(Buffer.from([1, 2, 3]));
    expect(fetchFn).toHaveBeenCalledTimes(2);
  });

  it.each([
    [new FakeIpDnsError(), new Error("synthetic resolution failure")],
    [new Error("synthetic resolution failure"), new FakeIpDnsError()],
    [
      new FakeIpDnsError(),
      new AsrError("ASR_AUDIO_UNAVAILABLE", "synthetic media failure", true),
    ],
    [
      new AsrError("ASR_AUDIO_UNAVAILABLE", "synthetic media failure", true),
      new FakeIpDnsError(),
    ],
  ])("keeps mixed candidate failures generic", async (firstError, secondError) => {
    const dir = await createAsrTempDir(ASR_TEMP_PREFIX);
    tempDirs.push(dir);
    const destination = path.join(dir, "audio.m4a");
    const candidates = [
      candidate,
      { ...candidate, url: "https://upos-sz-mirrorcoso2.bilivideo.com/audio.m4s" },
    ];
    const fetchFn = vi
      .fn()
      .mockRejectedValueOnce(firstError)
      .mockRejectedValueOnce(secondError);

    await expect(
      downloadPlaybackAudio(candidates, destination, fetchFn),
    ).rejects.toMatchObject({ code: "ASR_AUDIO_UNAVAILABLE" });
  });

  it("keeps a public redirect followed by Fake-IP generic", async () => {
    const dir = await createAsrTempDir(ASR_TEMP_PREFIX);
    tempDirs.push(dir);
    const destination = path.join(dir, "audio.m4a");
    const fetchFn = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(null, {
          status: 302,
          headers: { location: "https://upos-sz-mirrorcoso2.bilivideo.com/audio.m4s" },
        }),
      )
      .mockRejectedValueOnce(new FakeIpDnsError());

    await expect(
      downloadPlaybackAudio([candidate], destination, fetchFn),
    ).rejects.toMatchObject({ code: "ASR_AUDIO_UNAVAILABLE" });
  });

  it("revalidates every redirect and never exposes the signed location", async () => {
    const dir = await createAsrTempDir(ASR_TEMP_PREFIX);
    tempDirs.push(dir);
    const destination = path.join(dir, "audio.m4a");
    const secretLocation = "https://evil.test/audio?token=DO_NOT_LEAK";
    const fetchFn = vi.fn(async () => new Response(null, {
      status: 302,
      headers: { location: secretLocation },
    }));

    try {
      await downloadPlaybackAudio([candidate], destination, fetchFn);
      throw new Error("expected rejection");
    } catch (error) {
      expect((error as AsrError).code).toBe("ASR_AUDIO_UNAVAILABLE");
      expect((error as Error).message).not.toContain("DO_NOT_LEAK");
      expect((error as Error).message).not.toContain(secretLocation);
    }
    await expect(fs.promises.stat(destination)).rejects.toMatchObject({ code: "ENOENT" });
  });

  it("rejects an oversized Content-Length before creating a file", async () => {
    const dir = await createAsrTempDir(ASR_TEMP_PREFIX);
    tempDirs.push(dir);
    const destination = path.join(dir, "audio.m4a");
    const fetchFn = vi.fn(async () => new Response("x", {
      status: 200,
      headers: {
        "content-type": "audio/mp4",
        "content-length": String(MAX_ASR_AUDIO_BYTES + 1),
      },
    }));

    await expect(downloadPlaybackAudio([candidate], destination, fetchFn)).rejects.toMatchObject({
      code: "ASR_LIMIT_EXCEEDED",
    });
    await expect(fs.promises.stat(destination)).rejects.toMatchObject({ code: "ENOENT" });
  });

  it("rejects a response without supported media content type", async () => {
    const dir = await createAsrTempDir(ASR_TEMP_PREFIX);
    tempDirs.push(dir);
    const destination = path.join(dir, "audio.m4a");
    const fetchFn = vi.fn(async () => new Response("not-media", { status: 200 }));

    await expect(downloadPlaybackAudio([candidate], destination, fetchFn)).rejects.toMatchObject({
      code: "ASR_AUDIO_UNAVAILABLE",
    });
    await expect(fs.promises.stat(destination)).rejects.toMatchObject({ code: "ENOENT" });
  });

  it("aborts a timed-out candidate and returns no URL", async () => {
    const dir = await createAsrTempDir(ASR_TEMP_PREFIX);
    tempDirs.push(dir);
    const destination = path.join(dir, "audio.m4a");
    const fetchFn = vi.fn((_url: string | URL | Request, init?: RequestInit) => {
      return new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => {
          reject(new DOMException("aborted", "AbortError"));
        });
      });
    });

    await expect(downloadPlaybackAudio([candidate], destination, fetchFn, 5)).rejects.toMatchObject({
      code: "ASR_AUDIO_UNAVAILABLE",
      retryable: true,
    });
  });

  it("shares one timeout deadline across all fallback candidates", async () => {
    const dir = await createAsrTempDir(ASR_TEMP_PREFIX);
    tempDirs.push(dir);
    const destination = path.join(dir, "audio.m4a");
    const secondCandidate = {
      ...candidate,
      url: "https://upos-sz-mirrorcoso2.bilivideo.com/audio.m4s",
    };
    vi.useFakeTimers();
    try {
      let call = 0;
      const fetchFn = vi.fn(
        (_url: string | URL | Request, init?: RequestInit) => {
          call += 1;
          if (call === 1) {
            return new Promise<Response>((resolve) => {
              setTimeout(
                () => resolve(new Response(null, { status: 503 })),
                8,
              );
            });
          }
          return new Promise<Response>((_resolve, reject) => {
            init?.signal?.addEventListener(
              "abort",
              () => reject(new DOMException("aborted", "AbortError")),
              { once: true },
            );
          });
        },
      );

      const outcome = downloadPlaybackAudio(
        [candidate, secondCandidate],
        destination,
        fetchFn,
        10,
      ).catch((error: unknown) => error);
      for (let attempt = 0; attempt < 10 && fetchFn.mock.calls.length < 1; attempt += 1) {
        await fs.promises.stat(dir);
        await Promise.resolve();
      }
      expect(fetchFn).toHaveBeenCalledTimes(1);
      await vi.advanceTimersByTimeAsync(8);
      for (let attempt = 0; attempt < 10 && fetchFn.mock.calls.length < 2; attempt += 1) {
        await fs.promises.stat(dir);
        await Promise.resolve();
      }
      expect(fetchFn).toHaveBeenCalledTimes(2);
      await vi.advanceTimersByTimeAsync(2);
      await expect(outcome).resolves.toMatchObject({
        code: "ASR_AUDIO_UNAVAILABLE",
      });
    } finally {
      vi.useRealTimers();
    }
  });

  it("shares one decoded-byte budget across failed fallback candidates", async () => {
    const dir = await createAsrTempDir(ASR_TEMP_PREFIX);
    tempDirs.push(dir);
    const destination = path.join(dir, "audio.m4a");
    const secondCandidate = {
      ...candidate,
      url: "https://upos-sz-mirrorcoso2.bilivideo.com/audio.m4s",
    };
    let firstPull = true;
    const fetchFn = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          new ReadableStream<Uint8Array>({
            pull(controller) {
              if (firstPull) {
                firstPull = false;
                controller.enqueue(new Uint8Array(6));
                return;
              }
              controller.error(new Error("synthetic stream failure"));
            },
          }),
          {
            status: 200,
            headers: { "content-type": "audio/mp4" },
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(new Uint8Array([1]), {
          status: 200,
          headers: {
            "content-type": "audio/mp4",
            "content-length": "5",
          },
        }),
      );

    await expect(
      downloadPlaybackAudio(
        [candidate, secondCandidate],
        destination,
        fetchFn,
        1_000,
        undefined,
        10,
      ),
    ).rejects.toMatchObject({
      code: "ASR_LIMIT_EXCEEDED",
    });
    expect(fetchFn).toHaveBeenCalledTimes(2);
    await expect(fs.promises.stat(destination)).rejects.toMatchObject({
      code: "ENOENT",
    });
  });
});

describe("ASR orchestration", () => {
  it("creates unique request directories below the OS temp root", async () => {
    const first = await createAsrTempDir(ASR_TEMP_PREFIX);
    const second = await createAsrTempDir(ASR_TEMP_PREFIX);
    tempDirs.push(first, second);

    expect(first).not.toBe(second);
    expect(path.dirname(first)).toBe(path.resolve(os.tmpdir()));
    expect(path.basename(first)).toMatch(/^bilibili-mcp-asr-/);
  });

  it("requires ready state before playback, temp files, or subprocess work", async () => {
    const getPlayback = vi.fn();
    const createTempDir = vi.fn();
    await expect(transcribeVideoPart(
      { bvid: "BV1T6PQzQErF", cid: 12345, durationSeconds: 60 },
      {
        ...readyDependencies(),
        getState: () => ({ kind: "not_installed" }),
        getPlayback,
        createTempDir,
      },
    )).rejects.toMatchObject({ code: "ASR_NOT_READY" });
    expect(getPlayback).not.toHaveBeenCalled();
    expect(createTempDir).not.toHaveBeenCalled();
  });

  it("returns null for a valid empty audio set without creating temp files", async () => {
    const createTempDir = vi.fn();
    await expect(transcribeVideoPart(
      { bvid: "BV1T6PQzQErF", cid: 12345, durationSeconds: 60 },
      {
        ...readyDependencies(),
        getPlayback: async () => ({ candidates: [], durationSeconds: 60 }),
        createTempDir,
      },
    )).resolves.toBeNull();
    expect(createTempDir).not.toHaveBeenCalled();
  });

  it("cleans the unique request directory after success", async () => {
    const removeTempDir = vi.fn();
    const runRuntime = vi.fn(async () => ({
      language: "en",
      segments: [{ from: 0, to: 1, content: "hello" }],
    }));
    await expect(transcribeVideoPart(
      { bvid: "BV1T6PQzQErF", cid: 12345, durationSeconds: 60 },
      {
        ...readyDependencies(),
        getPlayback: async () => ({ candidates: [candidate], durationSeconds: 60 }),
        createTempDir: async () => path.join(os.tmpdir(), `${ASR_TEMP_PREFIX}success`),
        removeTempDir,
        downloadAudio: vi.fn(async () => undefined),
        runRuntime,
      },
    )).resolves.toMatchObject({ language: "en" });
    expect(removeTempDir).toHaveBeenCalledOnce();
    expect(runRuntime).toHaveBeenCalledOnce();
    expect(runRuntime.mock.calls[0][3]).toEqual(CPU_PROFILE);
  });

  it("uses the controlled legacy CPU fallback for a v1 migration-pending state", async () => {
    const runRuntime = vi.fn(async () => ({ language: "zh", segments: [] }));

    await transcribeVideoPart(
      { bvid: "BV1T6PQzQErF", cid: 12345, durationSeconds: 60 },
      {
        ...readyDependencies(),
        getState: () => ({
          kind: "ready",
          version: 1,
          deviceReadiness: "migration_pending",
          migrationStatus: "pending",
        }),
        getPlayback: async () => ({ candidates: [candidate], durationSeconds: 60 }),
        createTempDir: async () => path.join(os.tmpdir(), `${ASR_TEMP_PREFIX}legacy`),
        removeTempDir: vi.fn(async () => undefined),
        downloadAudio: vi.fn(async () => undefined),
        runRuntime,
      },
    );

    expect(runRuntime.mock.calls[0][3]).toEqual(CPU_PROFILE);
  });

  it("rejects an unallowlisted injected profile before playback or subprocess work", async () => {
    const getPlayback = vi.fn();
    const runRuntime = vi.fn();

    await expect(transcribeVideoPart(
      { bvid: "BV1T6PQzQErF", cid: 12345, durationSeconds: 60 },
      {
        ...readyDependencies(),
        getState: () => ({
          kind: "ready",
          executionProfile: { device: "cpu", computeType: "float16" },
          deviceReadiness: "ready",
          migrationStatus: "completed",
        } as never),
        getPlayback,
        runRuntime,
      },
    )).rejects.toMatchObject({ code: "ASR_NOT_READY" });
    expect(getPlayback).not.toHaveBeenCalled();
    expect(runRuntime).not.toHaveBeenCalled();
  });

  it("rejects a CPU profile that has not reached ready/completed", async () => {
    const getPlayback = vi.fn();

    await expect(transcribeVideoPart(
      { bvid: "BV1T6PQzQErF", cid: 12345, durationSeconds: 60 },
      {
        ...readyDependencies(),
        getState: () => ({
          kind: "ready",
          executionProfile: CPU_PROFILE,
          deviceReadiness: "migration_pending",
          migrationStatus: "pending",
        }),
        getPlayback,
      },
    )).rejects.toMatchObject({ code: "ASR_NOT_READY" });
    expect(getPlayback).not.toHaveBeenCalled();
  });

  it("does not execute a CUDA profile before the CUDA readiness ticket", async () => {
    const getPlayback = vi.fn();

    await expect(transcribeVideoPart(
      { bvid: "BV1T6PQzQErF", cid: 12345, durationSeconds: 60 },
      {
        ...readyDependencies(),
        getState: () => ({
          kind: "ready",
          executionProfile: { device: "cuda", computeType: "float16" },
          deviceReadiness: "ready",
          migrationStatus: "completed",
        }),
        getPlayback,
      },
    )).rejects.toMatchObject({ code: "ASR_NOT_READY" });
    expect(getPlayback).not.toHaveBeenCalled();
  });

  it("cleans the request directory after download or runtime failure", async () => {
    const removeTempDir = vi.fn();
    await expect(transcribeVideoPart(
      { bvid: "BV1T6PQzQErF", cid: 12345, durationSeconds: 60 },
      {
        ...readyDependencies(),
        getPlayback: async () => ({ candidates: [candidate], durationSeconds: 60 }),
        createTempDir: async () => path.join(os.tmpdir(), `${ASR_TEMP_PREFIX}failure`),
        removeTempDir,
        downloadAudio: vi.fn(async () => {
          throw new AsrError("ASR_AUDIO_UNAVAILABLE", "download failed", true);
        }),
      },
    )).rejects.toMatchObject({ code: "ASR_AUDIO_UNAVAILABLE" });
    expect(removeTempDir).toHaveBeenCalledOnce();
  });

  it("cleans the request directory after a transcription timeout", async () => {
    const removeTempDir = vi.fn();
    await expect(transcribeVideoPart(
      { bvid: "BV1T6PQzQErF", cid: 12345, durationSeconds: 60 },
      {
        ...readyDependencies(),
        getPlayback: async () => ({ candidates: [candidate], durationSeconds: 60 }),
        createTempDir: async () => path.join(os.tmpdir(), `${ASR_TEMP_PREFIX}timeout`),
        removeTempDir,
        downloadAudio: vi.fn(async () => undefined),
        runRuntime: vi.fn(async () => {
          throw new AsrError(
            "ASR_TRANSCRIPTION_TIMEOUT",
            "timeout",
            true,
          );
        }),
      },
    )).rejects.toMatchObject({ code: "ASR_TRANSCRIPTION_TIMEOUT" });
    expect(removeTempDir).toHaveBeenCalledOnce();
  });

  it("admits one active ASR job and rejects a second without queueing", async () => {
    let releasePlayback!: (value: { candidates: [] }) => void;
    const firstPlayback = new Promise<{ candidates: [] }>((resolve) => {
      releasePlayback = resolve;
    });
    const dependencies = {
      ...readyDependencies(),
      getPlayback: vi.fn(() => firstPlayback),
    };
    const first = transcribeVideoPart(
      { bvid: "BV1T6PQzQErF", cid: 1, durationSeconds: 60 },
      dependencies,
    );
    await Promise.resolve();

    await expect(transcribeVideoPart(
      { bvid: "BV1T6PQzQErF", cid: 2, durationSeconds: 60 },
      dependencies,
    )).rejects.toMatchObject({ code: "ASR_BUSY", retryable: true });
    expect(dependencies.getPlayback).toHaveBeenCalledOnce();

    releasePlayback({ candidates: [] });
    await expect(first).resolves.toBeNull();
  });

  it("rejects duration limits before reading state or playback", async () => {
    const getState = vi.fn();
    const getPlayback = vi.fn();
    await expect(transcribeVideoPart(
      { bvid: "BV1T6PQzQErF", cid: 1, durationSeconds: 7_201 },
      { ...readyDependencies(), getState, getPlayback },
    )).rejects.toMatchObject({ code: "ASR_LIMIT_EXCEEDED" });
    expect(getState).not.toHaveBeenCalled();
    expect(getPlayback).not.toHaveBeenCalled();
  });

  it("rejects missing duration before reading state or playback", async () => {
    const getPaths = vi.fn();
    const getState = vi.fn();
    const getPlayback = vi.fn();

    await expect(
      transcribeVideoPart(
        {
          bvid: "BV1T6PQzQErF",
          cid: 1,
        } as never,
        {
          ...readyDependencies(),
          getPaths,
          getState,
          getPlayback,
        },
      ),
    ).rejects.toMatchObject({
      code: "ASR_AUDIO_UNAVAILABLE",
    });
    expect(getPaths).not.toHaveBeenCalled();
    expect(getState).not.toHaveBeenCalled();
    expect(getPlayback).not.toHaveBeenCalled();
  });

  it("propagates cancellation through download, cleans up, and releases the ASR slot", async () => {
    const controller = new AbortController();
    const removeTempDir = vi.fn(async () => undefined);
    const downloadAudio = vi.fn(
      async (
        _candidates: PlaybackAudioCandidate[],
        _destination: string,
        signal?: AbortSignal,
      ) =>
        await new Promise<void>((_resolve, reject) => {
          signal?.addEventListener(
            "abort",
            () => reject(new DOMException("aborted", "AbortError")),
            { once: true },
          );
        }),
    );
    const first = transcribeVideoPart(
      { bvid: "BV1T6PQzQErF", cid: 1, durationSeconds: 60 },
      {
        ...readyDependencies(),
        getPlayback: async () => ({
          candidates: [candidate],
          durationSeconds: 60,
        }),
        createTempDir: async () =>
          path.join(os.tmpdir(), `${ASR_TEMP_PREFIX}cancel`),
        removeTempDir,
        downloadAudio,
      },
      controller.signal,
    );
    await vi.waitFor(() => expect(downloadAudio).toHaveBeenCalledOnce());
    controller.abort();

    await expect(first).rejects.toMatchObject({ name: "AbortError" });
    expect(removeTempDir).toHaveBeenCalledOnce();
    await expect(
      transcribeVideoPart(
        { bvid: "BV1T6PQzQErF", cid: 2, durationSeconds: 60 },
        {
          ...readyDependencies(),
          getPlayback: async () => ({
            candidates: [],
            durationSeconds: 60,
          }),
        },
      ),
    ).resolves.toBeNull();
  });

  it("refuses cleanup outside a direct prefixed child of the OS temp root", async () => {
    await expect(cleanupAsrTempDir(os.tmpdir())).rejects.toMatchObject({
      code: "ASR_TRANSCRIPTION_FAILED",
    });
    await expect(cleanupAsrTempDir(path.join(os.tmpdir(), `${ASR_TEMP_PREFIX}models`))).rejects.toMatchObject({
      code: "ASR_TRANSCRIPTION_FAILED",
    });
  });
});
