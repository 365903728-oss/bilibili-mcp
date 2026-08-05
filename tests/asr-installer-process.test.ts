import { EventEmitter } from "node:events";
import { PassThrough } from "node:stream";
import { afterEach, describe, expect, it, vi } from "vitest";

const { spawnMock } = vi.hoisted(() => ({
  spawnMock: vi.fn(),
}));

vi.mock("child_process", () => ({
  spawn: spawnMock,
}));

import { discoverPython } from "../src/asr/installer.js";

function createChild() {
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
  return child;
}

afterEach(() => {
  vi.useRealTimers();
  vi.clearAllMocks();
});

describe("ASR installer subprocess containment", () => {
  it("kills default Python discovery after 64 KiB of output", async () => {
    const child = createChild();
    spawnMock.mockReturnValue(child);
    const discovery = discoverPython(undefined, "synthetic-python");

    child.stdout.write(Buffer.alloc(64 * 1024 + 1));

    await expect(discovery).rejects.toThrow(
      "ASR installer subprocess output exceeded its limit",
    );
    expect(child.kill).toHaveBeenCalledWith("SIGKILL");
    expect(spawnMock).toHaveBeenCalledWith(
      "synthetic-python",
      ["-I", "--version"],
      expect.objectContaining({
        shell: false,
        stdio: ["ignore", "pipe", "pipe"],
        detached: process.platform !== "win32",
      }),
    );
  });

  it("kills default Python discovery after its 15-second deadline", async () => {
    vi.useFakeTimers();
    const child = createChild();
    spawnMock.mockReturnValue(child);
    const discovery = discoverPython(undefined, "synthetic-python");
    const rejection = expect(discovery).rejects.toThrow(
      "ASR installer subprocess exceeded its time limit",
    );

    await vi.advanceTimersByTimeAsync(15_001);

    await rejection;
    expect(child.kill).toHaveBeenCalledWith("SIGKILL");
    expect(spawnMock).toHaveBeenCalledWith(
      "synthetic-python",
      ["-I", "--version"],
      expect.objectContaining({
        shell: false,
        stdio: ["ignore", "pipe", "pipe"],
        detached: process.platform !== "win32",
      }),
    );
  });
});
