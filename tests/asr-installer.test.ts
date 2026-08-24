import fs from "fs";
import os from "os";
import path from "path";
import { afterAll, afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildAsrChildEnv,
  discoverPython,
  runAsrInstallation,
  verifyModel,
  downloadModel,
  createVenv,
  installRuntime,
  validateModelInstallTree,
  verifyInstalledDeviceReadiness,
  type PythonCommand,
} from "../src/asr/installer.js";
import {
  ASR_MODEL_SPECS,
  ASR_PINNED_CTRANSLATE2,
  ASR_PINNED_MODEL,
  ASR_PINNED_REVISION,
  ASR_PINNED_RUNTIME,
  ASR_STATE_VERSION,
  deriveAsrPaths,
  isAllowlistedModel,
  modelKeyForRepo,
  readAsrState,
  resolveExecutionProfile,
  resolveModelSpec,
  writeAsrState,
  type AsrModelKey,
  type AsrState,
} from "../src/asr/state.js";

const CPU_PROFILE = { device: "cpu", computeType: "int8" } as const;
const CUDA_PROFILE = { device: "cuda", computeType: "float16" } as const;

function materializeMockVenv(args: string[]): void {
  const moduleIndex = args.findIndex(
    (arg, index) => arg === "venv" && args[index - 1] === "-m",
  );
  if (moduleIndex < 0) return;
  const venvPath = args[args.length - 1];
  const binDir = path.join(venvPath, process.platform === "win32" ? "Scripts" : "bin");
  fs.mkdirSync(binDir, { recursive: true });
  fs.writeFileSync(
    path.join(binDir, process.platform === "win32" ? "python.exe" : "python"),
    "fake",
  );
}

// ---------- state.ts ----------

describe("deriveAsrPaths", () => {
  it("returns paths under ~/.bilibili-mcp/asr/ by default", () => {
    const paths = deriveAsrPaths();
    expect(paths.root).toContain(".bilibili-mcp");
    expect(paths.root).toContain("asr");
    expect(paths.venv).toBe(path.join(paths.root, "venv"));
    expect(paths.model).toBe(path.join(paths.root, "models"));
    expect(paths.stateFile).toBe(path.join(paths.root, "state.json"));
  });

  it("respects a custom base", () => {
    const base = os.platform() === "win32" ? "C:\\tmp\\test-asr" : "/tmp/test-asr";
    const paths = deriveAsrPaths(base);
    expect(paths.root).toBe(base);
    expect(paths.venv).toBe(path.join(base, "venv"));
  });
});

describe("readAsrState", () => {
  const validLstatSync = () => vi.fn(() => ({
    isSymbolicLink: () => false,
    isDirectory: () => true,
    isFile: () => true,
  }));

  it("returns not_installed when state file and all artifacts are absent", () => {
    const existsSync = vi.fn(() => false);
    const state = readAsrState("/tmp/asr/state.json", fs.readFileSync, existsSync);
    expect(state.kind).toBe("not_installed");
  });

  it("returns incomplete when state file absent but venv artifact exists", () => {
    const stateFile = "/tmp/asr/state.json";
    const venvDir = path.join(path.dirname(stateFile), "venv");
    const existsSync = vi.fn((p: string) => p === stateFile ? false : p === venvDir ? true : p === path.dirname(stateFile));
    const state = readAsrState(stateFile, fs.readFileSync, existsSync);
    expect(state.kind).toBe("incomplete");
  });

  it("returns incomplete when state file absent but models artifact exists", () => {
    const stateFile = "/tmp/asr/state.json";
    const modelsDir = path.join(path.dirname(stateFile), "models");
    const existsSync = vi.fn((p: string) => p === modelsDir);
    const state = readAsrState(stateFile, fs.readFileSync, existsSync);
    expect(state.kind).toBe("incomplete");
  });

  it("returns incomplete for malformed JSON", () => {
    const existsSync = vi.fn(() => true);
    const readFileSync = vi.fn(() => "not json");
    const state = readAsrState("/tmp/asr/state.json", readFileSync, existsSync);
    expect(state.kind).toBe("incomplete");
  });

  it("returns incomplete when version does not match", () => {
    const existsSync = vi.fn((p: string) => p.endsWith("state.json"));
    const readFileSync = vi.fn(() =>
      JSON.stringify({ kind: "ready", version: 999, runtime: ASR_PINNED_RUNTIME, model: ASR_PINNED_MODEL, revision: ASR_PINNED_REVISION }),
    );
    const state = readAsrState("/tmp/asr/state.json", readFileSync, existsSync);
    expect(state.kind).toBe("incomplete");
  });

  it("returns incomplete when kind field is missing", () => {
    const existsSync = vi.fn(() => true);
    const readFileSync = vi.fn(() =>
      JSON.stringify({ version: ASR_STATE_VERSION, runtime: ASR_PINNED_RUNTIME, model: ASR_PINNED_MODEL, revision: ASR_PINNED_REVISION }),
    );
    const state = readAsrState("/tmp/asr/state.json", readFileSync, existsSync);
    expect(state.kind).toBe("incomplete");
  });

  it("returns incomplete when runtime does not match", () => {
    const existsSync = vi.fn((p: string) => p.endsWith("state.json"));
    const readFileSync = vi.fn(() =>
      JSON.stringify({ kind: "ready", version: ASR_STATE_VERSION, runtime: "wrong==1.0.0", model: ASR_PINNED_MODEL, revision: ASR_PINNED_REVISION }),
    );
    const state = readAsrState("/tmp/asr/state.json", readFileSync, existsSync);
    expect(state.kind).toBe("incomplete");
  });

  it("returns incomplete when model does not match", () => {
    const existsSync = vi.fn((p: string) => p.endsWith("state.json"));
    const readFileSync = vi.fn(() =>
      JSON.stringify({ kind: "ready", version: ASR_STATE_VERSION, runtime: ASR_PINNED_RUNTIME, model: "other/model", revision: ASR_PINNED_REVISION }),
    );
    const state = readAsrState("/tmp/asr/state.json", readFileSync, existsSync);
    expect(state.kind).toBe("incomplete");
  });

  it("returns ready when all fields match AND artifacts exist", () => {
    const existsSync = vi.fn(() => true); // everything exists
    const readFileSync = vi.fn(() =>
      JSON.stringify({
        kind: "ready",
        version: ASR_STATE_VERSION,
        runtime: ASR_PINNED_RUNTIME,
        model: ASR_PINNED_MODEL,
        revision: ASR_PINNED_REVISION,
        device: "cpu",
        compute_type: "int8",
        device_readiness: "ready",
        migration_status: "completed",
      }),
    );
    const lstatSync = vi.fn(() => ({
      isSymbolicLink: () => false,
      isDirectory: () => true,
      isFile: () => true,
    }));
    const state = readAsrState("/tmp/asr/state.json", readFileSync, existsSync, lstatSync);
    expect(state.kind).toBe("ready");
    expect(state.version).toBe(ASR_STATE_VERSION);
    expect(state.runtime).toBe(ASR_PINNED_RUNTIME);
  });

  it("returns incomplete when venv Python executable is missing", () => {
    const stateFile = "/tmp/asr/state.json";
    const venvPython = path.join(
      path.dirname(stateFile), "venv",
      os.platform() === "win32" ? "Scripts" : "bin",
      os.platform() === "win32" ? "python.exe" : "python",
    );
    const existsSync = vi.fn((p: string) => p !== venvPython);
    const readFileSync = vi.fn(() =>
      JSON.stringify({ kind: "ready", version: ASR_STATE_VERSION, runtime: ASR_PINNED_RUNTIME, model: ASR_PINNED_MODEL, revision: ASR_PINNED_REVISION, device: "cpu", compute_type: "int8", device_readiness: "ready", migration_status: "completed" }),
    );
    const state = readAsrState(stateFile, readFileSync, existsSync, validLstatSync());
    expect(state.kind).toBe("incomplete");
    expect(existsSync).toHaveBeenCalledWith(venvPython);
  });

  it("returns incomplete when model.bin is missing", () => {
    const modelBin = path.join(path.dirname("/tmp/asr/state.json"), "models", "model.bin");
    const existsSync = vi.fn((p: string) => p !== modelBin);
    const readFileSync = vi.fn(() =>
      JSON.stringify({ kind: "ready", version: ASR_STATE_VERSION, runtime: ASR_PINNED_RUNTIME, model: ASR_PINNED_MODEL, revision: ASR_PINNED_REVISION, device: "cpu", compute_type: "int8", device_readiness: "ready", migration_status: "completed" }),
    );
    const state = readAsrState("/tmp/asr/state.json", readFileSync, existsSync, validLstatSync());
    expect(state.kind).toBe("incomplete");
    expect(existsSync).toHaveBeenCalledWith(modelBin);
  });

  it("returns incomplete when config.json is missing", () => {
    const configJson = path.join(path.dirname("/tmp/asr/state.json"), "models", "config.json");
    const existsSync = vi.fn((p: string) => p !== configJson);
    const readFileSync = vi.fn(() =>
      JSON.stringify({ kind: "ready", version: ASR_STATE_VERSION, runtime: ASR_PINNED_RUNTIME, model: ASR_PINNED_MODEL, revision: ASR_PINNED_REVISION, device: "cpu", compute_type: "int8", device_readiness: "ready", migration_status: "completed" }),
    );
    const state = readAsrState("/tmp/asr/state.json", readFileSync, existsSync, validLstatSync());
    expect(state.kind).toBe("incomplete");
    expect(existsSync).toHaveBeenCalledWith(configJson);
  });

  it("returns incomplete when tokenizer.json is missing", () => {
    const tok = path.join(path.dirname("/tmp/asr/state.json"), "models", "tokenizer.json");
    const existsSync = vi.fn((p: string) => p !== tok);
    const readFileSync = vi.fn(() =>
      JSON.stringify({ kind: "ready", version: ASR_STATE_VERSION, runtime: ASR_PINNED_RUNTIME, model: ASR_PINNED_MODEL, revision: ASR_PINNED_REVISION, device: "cpu", compute_type: "int8", device_readiness: "ready", migration_status: "completed" }),
    );
    const state = readAsrState("/tmp/asr/state.json", readFileSync, existsSync, validLstatSync());
    expect(state.kind).toBe("incomplete");
    expect(existsSync).toHaveBeenCalledWith(tok);
  });

  it("returns incomplete when vocabulary.txt is missing", () => {
    const vocab = path.join(path.dirname("/tmp/asr/state.json"), "models", "vocabulary.txt");
    const existsSync = vi.fn((p: string) => p !== vocab);
    const readFileSync = vi.fn(() =>
      JSON.stringify({ kind: "ready", version: ASR_STATE_VERSION, runtime: ASR_PINNED_RUNTIME, model: ASR_PINNED_MODEL, revision: ASR_PINNED_REVISION, device: "cpu", compute_type: "int8", device_readiness: "ready", migration_status: "completed" }),
    );
    const state = readAsrState("/tmp/asr/state.json", readFileSync, existsSync, validLstatSync());
    expect(state.kind).toBe("incomplete");
    expect(existsSync).toHaveBeenCalledWith(vocab);
  });
});

describe("writeAsrState", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "bilibili-mcp-asr-test-"));
  const stateFile = path.join(tmpDir, "state.json");

  afterAll(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  afterEach(() => {
    try { fs.unlinkSync(stateFile); } catch { /* ok */ }
    try { fs.unlinkSync(stateFile + ".tmp"); } catch { /* ok */ }
  });

  it("writes a valid state file atomically", () => {
    fs.mkdirSync(tmpDir, { recursive: true });
    writeAsrState(stateFile);
    expect(fs.existsSync(stateFile)).toBe(true);
    expect(fs.existsSync(stateFile + ".tmp")).toBe(false);

    const raw = fs.readFileSync(stateFile, "utf8");
    const parsed = JSON.parse(raw);
    expect(parsed.version).toBe(ASR_STATE_VERSION);
    expect(parsed.runtime).toBe(ASR_PINNED_RUNTIME);
    expect(parsed.model).toBe(ASR_PINNED_MODEL);
    expect(parsed.revision).toBe(ASR_PINNED_REVISION);
  });

  it("cleans tmp file on rename failure", () => {
    const write = vi.fn();
    const rename = vi.fn(() => { throw new Error("rename failed"); });
    const unlink = vi.fn();
    const mkdir = vi.fn();

    expect(() => writeAsrState("/tmp/asr/state.json", "small", {}, write, rename, unlink, mkdir)).toThrow("atomically");
    expect(unlink).toHaveBeenCalledWith(expect.stringMatching(/\.state-[0-9a-f-]{36}\.tmp$/));
  });

  it("cleans tmp file when writeFileSync throws", () => {
    const write = vi.fn(() => { throw new Error("disk full"); });
    const rename = vi.fn();
    const unlink = vi.fn();
    const mkdir = vi.fn();

    expect(() => writeAsrState("/tmp/asr/state.json", "small", {}, write, rename, unlink, mkdir)).toThrow("write ASR state file");
    expect(rename).not.toHaveBeenCalled();
    expect(unlink).toHaveBeenCalledWith(expect.stringMatching(/\.state-[0-9a-f-]{36}\.tmp$/));
  });

  it("preserves the previous valid state bytes when atomic rename fails", () => {
    const previous = JSON.stringify({
      kind: "ready",
      version: 1,
      runtime: ASR_PINNED_RUNTIME,
      model: ASR_PINNED_MODEL,
      revision: ASR_PINNED_REVISION,
    });
    fs.writeFileSync(stateFile, previous);
    const randomId = () => "rename-failure";

    expect(() => writeAsrState(
      stateFile,
      "small",
      {},
      fs.writeFileSync,
      (() => { throw new Error("interrupted"); }) as typeof fs.renameSync,
      fs.unlinkSync,
      fs.mkdirSync,
      randomId,
    )).toThrow("atomically");

    expect(fs.readFileSync(stateFile, "utf8")).toBe(previous);
    expect(fs.existsSync(path.join(tmpDir, ".state-rename-failure.tmp"))).toBe(false);
  });
});

describe("readAsrState symlink safety", () => {
  const readyStateJson = JSON.stringify({
    kind: "ready",
    version: ASR_STATE_VERSION,
    runtime: ASR_PINNED_RUNTIME,
    model: ASR_PINNED_MODEL,
    revision: ASR_PINNED_REVISION,
    device: "cpu",
    compute_type: "int8",
    device_readiness: "ready",
    migration_status: "completed",
  });

  const managedPaths = (): Array<[string, "dir" | "file"]> => {
    const stateFile = "/tmp/asr/state.json";
    const root = path.dirname(stateFile);
    const venvDir = path.join(root, "venv");
    const binDir = path.join(venvDir, os.platform() === "win32" ? "Scripts" : "bin");
    const pythonExe = path.join(binDir, os.platform() === "win32" ? "python.exe" : "python");
    const modelDir = path.join(root, "models");
    return [
      [stateFile, "file"],
      [venvDir, "dir"],
      [binDir, "dir"],
      [pythonExe, "file"],
      [modelDir, "dir"],
      [path.join(modelDir, "model.bin"), "file"],
      [path.join(modelDir, "config.json"), "file"],
      [path.join(modelDir, "tokenizer.json"), "file"],
      [path.join(modelDir, "vocabulary.txt"), "file"],
    ];
  };

  it.each(managedPaths())(
    "rejects a symlinked managed path before returning ready: %s",
    (managed, kind) => {
      const existsSync = vi.fn(() => true);
      const readFileSync = vi.fn(() => readyStateJson);
      const lstatSync = vi.fn((candidate: string) => {
        const entry = managedPaths().find(([p]) => p === candidate);
        return {
          isSymbolicLink: () => candidate === managed,
          isDirectory: () =>
            candidate === path.dirname("/tmp/asr/state.json") ||
            entry?.[1] === "dir",
          isFile: () => entry?.[1] === "file",
        };
      });
      const state = readAsrState(
        "/tmp/asr/state.json",
        readFileSync,
        existsSync,
        lstatSync,
      );
      expect(state.kind).toBe("incomplete");
      expect(lstatSync).toHaveBeenCalledWith(managed);
    },
  );

  it("fails closed when a managed path cannot be inspected", () => {
    const existsSync = vi.fn(() => true);
    const readFileSync = vi.fn(() => readyStateJson);
    const lstatSync = vi.fn(() => {
      throw new Error("permission denied");
    });
    const state = readAsrState(
      "/tmp/asr/state.json",
      readFileSync,
      existsSync,
      lstatSync,
    );
    expect(state.kind).toBe("incomplete");
  });

  it("rejects a symlinked ASR root before reading the state file", () => {
    const readFileSync = vi.fn(() => readyStateJson);
    const existsSync = vi.fn(() => true);
    const lstatSync = vi.fn((candidate: string) => ({
      isSymbolicLink: () => candidate === "/tmp/asr",
    }));
    const state = readAsrState(
      "/tmp/asr/state.json",
      readFileSync,
      existsSync,
      lstatSync,
    );
    expect(state.kind).toBe("incomplete");
    expect(readFileSync).not.toHaveBeenCalled();
  });

  it("rejects a symlinked state file before the read mock runs", () => {
    const readFileSync = vi.fn(() => readyStateJson);
    const existsSync = vi.fn(() => true);
    const lstatSync = vi.fn((candidate: string) => ({
      // The root itself is a real directory; only the state file is a symlink.
      isSymbolicLink: () => candidate === "/tmp/asr/state.json",
      isDirectory: () => candidate === path.dirname("/tmp/asr/state.json"),
      isFile: () => false,
    }));
    const state = readAsrState(
      "/tmp/asr/state.json",
      readFileSync,
      existsSync,
      lstatSync,
    );
    expect(state.kind).toBe("incomplete");
    expect(readFileSync).not.toHaveBeenCalled();
  });
});

describe("readAsrState path type verification", () => {
  const readyStateJson = JSON.stringify({
    kind: "ready",
    version: ASR_STATE_VERSION,
    runtime: ASR_PINNED_RUNTIME,
    model: ASR_PINNED_MODEL,
    revision: ASR_PINNED_REVISION,
    device: "cpu",
    compute_type: "int8",
    device_readiness: "ready",
    migration_status: "completed",
  });
  const stateFile = "/tmp/asr/state.json";
  const root = path.dirname(stateFile);
  const venvDir = path.join(root, "venv");
  const binDir = path.join(venvDir, os.platform() === "win32" ? "Scripts" : "bin");
  const pythonExe = path.join(binDir, os.platform() === "win32" ? "python.exe" : "python");
  const modelDir = path.join(root, "models");

  const fileSlots = [
    stateFile,
    pythonExe,
    path.join(modelDir, "model.bin"),
    path.join(modelDir, "config.json"),
    path.join(modelDir, "tokenizer.json"),
    path.join(modelDir, "vocabulary.txt"),
  ];
  const dirSlots = [venvDir, binDir, modelDir];

  it.each(fileSlots)("a directory in a file slot never returns ready: %s", (slot) => {
    const existsSync = vi.fn(() => true);
    const readFileSync = vi.fn(() => readyStateJson);
    const lstatSync = vi.fn((candidate: string) => {
      const isTarget = candidate === slot;
      const isDirSlot = candidate === root || dirSlots.includes(candidate);
      const isFileSlot = fileSlots.includes(candidate);
      return {
        isSymbolicLink: () => false,
        isDirectory: () => isDirSlot || isTarget,
        isFile: () => isFileSlot && !isTarget,
      };
    });
    const state = readAsrState(stateFile, readFileSync, existsSync, lstatSync);
    expect(state.kind).toBe("incomplete");
    expect(lstatSync).toHaveBeenCalledWith(slot);
  });

  it.each(dirSlots)("a file in a directory slot never returns ready: %s", (slot) => {
    const existsSync = vi.fn(() => true);
    const readFileSync = vi.fn(() => readyStateJson);
    const lstatSync = vi.fn((candidate: string) => {
      const isTarget = candidate === slot;
      const isDirSlot = candidate === root || dirSlots.includes(candidate);
      const isFileSlot = fileSlots.includes(candidate);
      return {
        isSymbolicLink: () => false,
        isDirectory: () => !isTarget && isDirSlot,
        isFile: () => isTarget || isFileSlot,
      };
    });
    const state = readAsrState(stateFile, readFileSync, existsSync, lstatSync);
    expect(state.kind).toBe("incomplete");
    expect(lstatSync).toHaveBeenCalledWith(slot);
  });

  it("never reads a state file that is a directory", () => {
    const existsSync = vi.fn(() => true);
    const readFileSync = vi.fn(() => readyStateJson);
    const lstatSync = vi.fn((candidate: string) => ({
      isSymbolicLink: () => false,
      isDirectory: () => candidate === root || candidate === stateFile,
      isFile: () => false,
    }));
    const state = readAsrState(stateFile, readFileSync, existsSync, lstatSync);
    expect(state.kind).toBe("incomplete");
    expect(readFileSync).not.toHaveBeenCalled();
  });

  it("never reads when the ASR root is a regular file", () => {
    const existsSync = vi.fn(() => true);
    const readFileSync = vi.fn(() => readyStateJson);
    const lstatSync = vi.fn(() => ({
      isSymbolicLink: () => false,
      isDirectory: () => false,
      isFile: () => true,
    }));
    const state = readAsrState(stateFile, readFileSync, existsSync, lstatSync);
    expect(state.kind).toBe("incomplete");
    expect(readFileSync).not.toHaveBeenCalled();
  });
});

describe("writeAsrState secure temp file", () => {
  it("writes a unique wx 0600 temp file, renames it atomically, and creates the root 0700", () => {
    const written: Array<{ path: string; options: unknown }> = [];
    const write = vi.fn((p: string, _data: unknown, options: unknown) => {
      written.push({ path: p, options });
    });
    const rename = vi.fn();
    const unlink = vi.fn();
    const mkdir = vi.fn();

    writeAsrState("/tmp/asr/state.json", "small", {}, write, rename, unlink, mkdir);

    expect(mkdir).toHaveBeenCalledWith(path.dirname("/tmp/asr/state.json"), {
      recursive: true,
      mode: 0o700,
    });
    expect(written).toHaveLength(1);
    expect(written[0].path).not.toBe("/tmp/asr/state.json");
    expect(written[0].path).toMatch(/\.state-[0-9a-f-]{36}\.tmp$/);
    expect(written[0].options).toMatchObject({
      encoding: "utf8",
      flag: "wx",
      mode: 0o600,
    });
    expect(rename).toHaveBeenCalledWith(written[0].path, "/tmp/asr/state.json");
    expect(unlink).not.toHaveBeenCalled();
  });

  it("uses the injected random source for the temp name", () => {
    const written: Array<{ path: string }> = [];
    const write = vi.fn((p: string) => {
      written.push({ path: p });
    });
    const rename = vi.fn();
    const unlink = vi.fn();
    const mkdir = vi.fn();
    const randomId = vi.fn(() => "abc-123");

    writeAsrState("/tmp/asr/state.json", "small", {}, write, rename, unlink, mkdir, randomId);

    expect(written[0].path).toBe(path.join("/tmp/asr", ".state-abc-123.tmp"));
    expect(rename).toHaveBeenCalledWith(
      path.join("/tmp/asr", ".state-abc-123.tmp"),
      "/tmp/asr/state.json",
    );
  });

  it("produces a fresh unpredictable temp name per write", () => {
    const write = vi.fn();
    const rename = vi.fn();
    const unlink = vi.fn();
    const mkdir = vi.fn();
    const randomId = vi
      .fn()
      .mockReturnValueOnce("first")
      .mockReturnValueOnce("second");

    writeAsrState("/tmp/asr/state.json", "small", {}, write, rename, unlink, mkdir, randomId);
    writeAsrState("/tmp/asr/state.json", "small", {}, write, rename, unlink, mkdir, randomId);

    const tmpPaths = write.mock.calls.map(([p]) => p);
    expect(tmpPaths).toEqual([
      path.join("/tmp/asr", ".state-first.tmp"),
      path.join("/tmp/asr", ".state-second.tmp"),
    ]);
    expect(rename).toHaveBeenNthCalledWith(
      1,
      path.join("/tmp/asr", ".state-first.tmp"),
      "/tmp/asr/state.json",
    );
    expect(rename).toHaveBeenNthCalledWith(
      2,
      path.join("/tmp/asr", ".state-second.tmp"),
      "/tmp/asr/state.json",
    );
  });

  it("rejects a symlinked root before any write or rename", () => {
    const write = vi.fn();
    const rename = vi.fn();
    const unlink = vi.fn();
    const mkdir = vi.fn();
    const chmodSync = vi.fn();
    const lstatSync = vi.fn(() => ({
      isSymbolicLink: () => true,
      isDirectory: () => false,
      isFile: () => false,
    }));

    expect(() =>
      writeAsrState(
        "/tmp/asr/state.json",
        "small",
        {},
        write,
        rename,
        unlink,
        mkdir,
        undefined,
        lstatSync,
        chmodSync,
      ),
    ).toThrow(/symlink/);
    expect(write).not.toHaveBeenCalled();
    expect(rename).not.toHaveBeenCalled();
    expect(unlink).not.toHaveBeenCalled();
    expect(mkdir).not.toHaveBeenCalled();
    expect(chmodSync).not.toHaveBeenCalled();
  });

  it("rejects a non-directory root before any write or rename", () => {
    const write = vi.fn();
    const rename = vi.fn();
    const unlink = vi.fn();
    const mkdir = vi.fn();
    const chmodSync = vi.fn();
    const lstatSync = vi.fn(() => ({
      isSymbolicLink: () => false,
      isDirectory: () => false,
      isFile: () => true,
    }));

    expect(() =>
      writeAsrState(
        "/tmp/asr/state.json",
        "small",
        {},
        write,
        rename,
        unlink,
        mkdir,
        undefined,
        lstatSync,
        chmodSync,
      ),
    ).toThrow(/not a directory/);
    expect(write).not.toHaveBeenCalled();
    expect(rename).not.toHaveBeenCalled();
    expect(unlink).not.toHaveBeenCalled();
    expect(mkdir).not.toHaveBeenCalled();
    expect(chmodSync).not.toHaveBeenCalled();
  });

  it("enforces owner-only permissions on an existing real root", () => {
    const write = vi.fn();
    const rename = vi.fn();
    const unlink = vi.fn();
    const mkdir = vi.fn();
    const chmodSync = vi.fn();
    const lstatSync = vi.fn(() => ({
      isSymbolicLink: () => false,
      isDirectory: () => true,
      isFile: () => false,
    }));

    writeAsrState(
      "/tmp/asr/state.json",
      "small",
      {},
      write,
      rename,
      unlink,
      mkdir,
      undefined,
      lstatSync,
      chmodSync,
    );

    expect(chmodSync).toHaveBeenCalledWith(path.dirname("/tmp/asr/state.json"), 0o700);
  });

  it("creates an absent root owner-only without a chmod attempt", () => {
    const write = vi.fn();
    const rename = vi.fn();
    const unlink = vi.fn();
    const mkdir = vi.fn();
    const chmodSync = vi.fn();
    const lstatSync = vi.fn(() => {
      const error = new Error("no such file") as NodeJS.ErrnoException;
      error.code = "ENOENT";
      throw error;
    });

    writeAsrState(
      "/tmp/asr/state.json",
      "small",
      {},
      write,
      rename,
      unlink,
      mkdir,
      undefined,
      lstatSync,
      chmodSync,
    );

    expect(chmodSync).not.toHaveBeenCalled();
    expect(mkdir).toHaveBeenCalledWith(path.dirname("/tmp/asr/state.json"), {
      recursive: true,
      mode: 0o700,
    });
  });

  it.each(["EPERM", "EACCES"])(
    "fails closed when chmod on an existing root is denied: %s",
    (code) => {
      const write = vi.fn();
      const rename = vi.fn();
      const unlink = vi.fn();
      const mkdir = vi.fn();
      const lstatSync = vi.fn(() => ({
        isSymbolicLink: () => false,
        isDirectory: () => true,
        isFile: () => false,
      }));
      const chmodSync = vi.fn(() => {
        const error = new Error(`chmod ${code}`) as NodeJS.ErrnoException;
        error.code = code;
        throw error;
      });

      expect(() =>
        writeAsrState(
          "/tmp/asr/state.json",
          "small",
          {},
          write,
          rename,
          unlink,
          mkdir,
          undefined,
          lstatSync,
          chmodSync,
        ),
      ).toThrow(`chmod ${code}`);
      expect(write).not.toHaveBeenCalled();
      expect(rename).not.toHaveBeenCalled();
      expect(unlink).not.toHaveBeenCalled();
      expect(mkdir).not.toHaveBeenCalled();
    },
  );

  it.each(["ENOSYS", "EOPNOTSUPP"])(
    "skips chmod only when explicitly unsupported: %s",
    (code) => {
      const write = vi.fn();
      const rename = vi.fn();
      const unlink = vi.fn();
      const mkdir = vi.fn();
      const lstatSync = vi.fn(() => ({
        isSymbolicLink: () => false,
        isDirectory: () => true,
        isFile: () => false,
      }));
      const chmodSync = vi.fn(() => {
        const error = new Error(`chmod ${code}`) as NodeJS.ErrnoException;
        error.code = code;
        throw error;
      });

      writeAsrState(
        "/tmp/asr/state.json",
        "small",
        {},
        write,
        rename,
        unlink,
        mkdir,
        undefined,
        lstatSync,
        chmodSync,
      );

      expect(chmodSync).toHaveBeenCalledWith(path.dirname("/tmp/asr/state.json"), 0o700);
      expect(write).toHaveBeenCalledTimes(1);
      expect(rename).toHaveBeenCalledTimes(1);
    },
  );
});

describe("readAsrState real-fs symlink rejection", () => {
  it("returns incomplete when model.bin is a symlink", () => {
    const base = fs.mkdtempSync(path.join(os.tmpdir(), "bilibili-mcp-asr-sym-"));
    const stateFile = path.join(base, "state.json");
    const binDir = path.join(base, "venv", os.platform() === "win32" ? "Scripts" : "bin");
    const pythonExe = path.join(binDir, os.platform() === "win32" ? "python.exe" : "python");
    const modelDir = path.join(base, "models");
    const outside = path.join(os.tmpdir(), `bilibili-mcp-asr-outside-${process.pid}.bin`);

    try {
      fs.mkdirSync(binDir, { recursive: true });
      fs.mkdirSync(modelDir, { recursive: true });
      fs.writeFileSync(pythonExe, "");
      for (const name of ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"]) {
        fs.writeFileSync(path.join(modelDir, name), "");
      }
      fs.writeFileSync(
        stateFile,
        JSON.stringify({
          kind: "ready",
          version: ASR_STATE_VERSION,
          runtime: ASR_PINNED_RUNTIME,
          model: ASR_PINNED_MODEL,
          revision: ASR_PINNED_REVISION,
          device: "cpu",
          compute_type: "int8",
          device_readiness: "ready",
          migration_status: "completed",
        }),
      );
      expect(readAsrState(stateFile).kind).toBe("ready");

      fs.writeFileSync(outside, "outside");
      fs.unlinkSync(path.join(modelDir, "model.bin"));
      try {
        fs.symlinkSync(outside, path.join(modelDir, "model.bin"), "file");
      } catch {
        return; // symlink creation unavailable on this platform
      }
      expect(readAsrState(stateFile).kind).toBe("incomplete");
    } finally {
      fs.rmSync(base, { recursive: true, force: true });
      fs.rmSync(outside, { force: true });
    }
  });

  it("returns incomplete when the ASR root directory is a symlink", () => {
    const base = fs.mkdtempSync(path.join(os.tmpdir(), "bilibili-mcp-asr-symroot-"));
    const outside = path.join(base, "outside");
    const linkRoot = path.join(base, "linkRoot");

    try {
      const binDir = path.join(outside, "venv", os.platform() === "win32" ? "Scripts" : "bin");
      const pythonExe = path.join(binDir, os.platform() === "win32" ? "python.exe" : "python");
      const modelDir = path.join(outside, "models");
      fs.mkdirSync(binDir, { recursive: true });
      fs.mkdirSync(modelDir, { recursive: true });
      fs.writeFileSync(pythonExe, "");
      for (const name of ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"]) {
        fs.writeFileSync(path.join(modelDir, name), "");
      }
      fs.writeFileSync(
        path.join(outside, "state.json"),
        JSON.stringify({
          kind: "ready",
          version: ASR_STATE_VERSION,
          runtime: ASR_PINNED_RUNTIME,
          model: ASR_PINNED_MODEL,
          revision: ASR_PINNED_REVISION,
        }),
      );

      try {
        fs.symlinkSync(outside, linkRoot, "dir");
      } catch {
        return; // symlink creation unavailable on this platform
      }
      // The tree behind the symlink is complete, so `incomplete` proves the
      // symlinked root was rejected before the state file was read.
      expect(readAsrState(path.join(linkRoot, "state.json")).kind).toBe("incomplete");
    } finally {
      fs.rmSync(base, { recursive: true, force: true });
    }
  });
});

// ---------- installer.ts: Python discovery ----------

describe("discoverPython", () => {
  it("returns the override when BILIBILI_ASR_PYTHON is set and valid", async () => {
    const spawnFn = vi.fn(() => Promise.resolve({ code: 0, stdout: "Python 3.11.5\n", stderr: "" }));
    const result = await discoverPython(spawnFn, "/usr/bin/python3.11");
    expect(result.executable).toBe("/usr/bin/python3.11");
    expect(result.prefixArgs).toEqual([]);
    expect(spawnFn).toHaveBeenCalledWith("/usr/bin/python3.11", ["-I", "--version"]);
  });

  it("throws when override exits non-zero", async () => {
    const spawnFn = vi.fn(() => Promise.resolve({ code: 1, stdout: "", stderr: "not found" }));
    await expect(discoverPython(spawnFn, "/fake/python")).rejects.toThrow("failed to start");
  });

  it("throws when BILIBILI_ASR_PYTHON is too old", async () => {
    const spawnFn = vi.fn(() => Promise.resolve({ code: 0, stdout: "Python 3.8.10\n", stderr: "" }));
    await expect(discoverPython(spawnFn, "/usr/bin/python3.8")).rejects.toThrow("3.9+ required");
  });

  it("returns python3 from default non-Windows candidate order", async () => {
    const spawnFn = vi.fn(() => Promise.resolve({ code: 0, stdout: "Python 3.12.0\n", stderr: "" }));
    const result = await discoverPython(spawnFn, undefined, [
      { executable: "python3", prefixArgs: [] },
      { executable: "python", prefixArgs: [] },
    ]);
    expect(result.executable).toBe("python3");
    expect(result.prefixArgs).toEqual([]);
  });

  it("returns py -3 when it is the first candidate (Windows-order injection)", async () => {
    const spawnFn = vi.fn((file: string) => {
      if (file === "py") return Promise.resolve({ code: 0, stdout: "Python 3.12.0\n", stderr: "" });
      return Promise.reject(new Error("ENOENT"));
    });
    const result = await discoverPython(spawnFn, undefined, [
      { executable: "py", prefixArgs: ["-3"] },
      { executable: "python3", prefixArgs: [] },
      { executable: "python", prefixArgs: [] },
    ]);
    expect(result.executable).toBe("py");
    expect(result.prefixArgs).toEqual(["-3"]);
  });

  it("falls back to python when python3 not found", async () => {
    let callCount = 0;
    const spawnFn = vi.fn((file: string) => {
      callCount++;
      if (file === "python3" || file === "py") return Promise.reject(new Error("ENOENT"));
      return Promise.resolve({ code: 0, stdout: "Python 3.10.0\n", stderr: "" });
    });
    const result = await discoverPython(spawnFn);
    expect(result.executable).toBe("python");
    expect(callCount).toBeGreaterThanOrEqual(2);
  });

  it("throws when no Python found", async () => {
    const spawnFn = vi.fn(() => Promise.reject(new Error("ENOENT")));
    await expect(discoverPython(spawnFn)).rejects.toThrow("not found");
  });

  it("rejects old Python from discovery", async () => {
    const spawnFn = vi.fn(() => Promise.resolve({ code: 0, stdout: "Python 3.8.10\n", stderr: "" }));
    await expect(discoverPython(spawnFn)).rejects.toThrow("not found");
  });
});

// ---------- installer.ts: subprocess actions ----------

function spawnOk(stdout = "") {
  return vi.fn(() => Promise.resolve({ code: 0, stdout, stderr: "" }));
}

describe("createVenv", () => {
  it("creates a venv with a copied interpreter and returns its Python command", async () => {
    const spawnFn = spawnOk();
    const mkdirSyncFn = vi.fn();
    const python: PythonCommand = { executable: "python3", prefixArgs: [] };
    const venvPath = path.join(os.tmpdir(), "test-venv");
    const result = await createVenv(python, venvPath, spawnFn, mkdirSyncFn);

    expect(spawnFn).toHaveBeenCalledWith("python3", ["-I", "-m", "venv", "--copies", venvPath]);
    expect(result.executable).toContain("python");
    expect(result.prefixArgs).toEqual([]);
  });

  it("throws when venv creation fails", async () => {
    const spawnFn = vi.fn(() => Promise.resolve({ code: 1, stdout: "", stderr: "error" }));
    const python: PythonCommand = { executable: "python3", prefixArgs: [] };
    await expect(createVenv(python, "/tmp/v", spawnFn, vi.fn())).rejects.toThrow("venv creation failed");
  });
});

describe("installRuntime", () => {
  it("calls venv python -m pip install with pinned runtime", async () => {
    const spawnFn = spawnOk();
    const venvPython: PythonCommand = { executable: "/tmp/venv/bin/python", prefixArgs: [] };
    await installRuntime(venvPython, spawnFn);

    expect(spawnFn).toHaveBeenCalledWith(
      "/tmp/venv/bin/python",
      [
        "-I",
        "-m",
        "pip",
        "install",
        "--quiet",
        ASR_PINNED_RUNTIME,
        "ctranslate2==4.8.0",
      ],
    );
  });

  it("throws on pip failure", async () => {
    const spawnFn = vi.fn(() => Promise.resolve({
      code: 1,
      stdout: "",
      stderr: "pip error at C:\\private\\venv TOKEN=secret",
    }));
    let caught: unknown;
    try {
      await installRuntime({ executable: "python3", prefixArgs: [] }, spawnFn);
    } catch (error) {
      caught = error;
    }
    expect(String(caught)).toContain("pip install");
    expect(String(caught)).not.toContain("private");
    expect(String(caught)).not.toContain("TOKEN");
  });
});

describe("downloadModel", () => {
  it("passes model_id, revision, local_dir via argv", async () => {
    const spawnFn = vi.fn(() => Promise.resolve({ code: 0, stdout: "DOWNLOADED\n", stderr: "" }));
    const mkdirSyncFn = vi.fn();

    await downloadModel(
      { executable: "python3", prefixArgs: [] },
      "/tmp/models",
      ASR_PINNED_MODEL,
      ASR_PINNED_REVISION,
      spawnFn,
      mkdirSyncFn,
    );

    const args = spawnFn.mock.calls[0][1];
    expect(args).toContain(ASR_PINNED_MODEL);
    expect(args).toContain(ASR_PINNED_REVISION);
    expect(args).toContain("/tmp/models");
  });

  it("throws when stdout is not exactly DOWNLOADED", async () => {
    const spawnFn = vi.fn(() => Promise.resolve({ code: 0, stdout: "DOWNLOADED with extra text\n", stderr: "" }));
    await expect(
      downloadModel({ executable: "python3", prefixArgs: [] }, "/tmp/models", ASR_PINNED_MODEL, ASR_PINNED_REVISION, spawnFn, vi.fn()),
    ).rejects.toThrow("did not confirm completion");
  });

  it("throws on non-zero exit", async () => {
    const spawnFn = vi.fn(() => Promise.resolve({ code: 1, stdout: "", stderr: "network error" }));
    await expect(
      downloadModel({ executable: "python3", prefixArgs: [] }, "/tmp/models", ASR_PINNED_MODEL, ASR_PINNED_REVISION, spawnFn, vi.fn()),
    ).rejects.toThrow("Model download failed");
  });
});

describe("verifyModel", () => {
  it("passes the allowlisted CUDA profile through argv and consumes the generator", async () => {
    const spawnFn = vi.fn((_file: string, args: string[]) => {
      expect(args[2]).toContain("for _ in segments");
      expect(args.slice(-2)).toEqual(["cuda", "float16"]);
      return Promise.resolve({ code: 0, stdout: "VERIFIED\n", stderr: "" });
    });

    await verifyModel(
      { executable: "python3", prefixArgs: [] },
      "/tmp/models",
      CUDA_PROFILE,
      spawnFn,
    );
  });

  it("does not apply CUDA loader diagnostics to CPU probe failures", async () => {
    const spawnFn = vi.fn((_file: string, args: string[]) => {
      const exceptionBlock = args[2].slice(args[2].indexOf("except Exception as error:"));
      expect(exceptionBlock).toContain("    if device == 'cuda':");
      return Promise.resolve({ code: 0, stdout: "VERIFIED\n", stderr: "" });
    });

    await verifyModel(
      { executable: "python3", prefixArgs: [] },
      "/tmp/models",
      CPU_PROFILE,
      spawnFn,
    );
  });

  it.each([
    ["no_nvidia_gpu", 20],
    ["cuda_runtime_missing", 21],
    ["runtime_version_mismatch", 22],
    ["model_probe_failed", 23],
  ] as const)("returns only the sanitized %s readiness category", async (category, code) => {
    const spawnFn = vi.fn(() => Promise.resolve({
      code,
      stdout: `FAILED:${category}\n`,
      stderr: "raw stderr at C:\\private\\cuda.dll TOKEN=secret",
    }));

    let caught: unknown;
    try {
      await verifyModel(
        { executable: "python3", prefixArgs: [] },
        "/tmp/models",
        CUDA_PROFILE,
        spawnFn,
      );
    } catch (error) {
      caught = error;
    }

    expect(caught).toMatchObject({ category });
    expect(String(caught)).not.toContain("private");
    expect(String(caught)).not.toContain("TOKEN");
  });

  it("rejects a readiness category paired with the wrong exit code", async () => {
    const spawnFn = vi.fn(() => Promise.resolve({
      code: 23,
      stdout: "FAILED:cuda_runtime_missing\n",
      stderr: "raw C:\\private\\cuda.dll TOKEN=secret",
    }));

    await expect(verifyModel(
      { executable: "python3", prefixArgs: [] },
      "/tmp/models",
      CUDA_PROFILE,
      spawnFn,
    )).rejects.toMatchObject({ category: "model_probe_failed" });
  });

  it("runs a minimal inference against a generated WAV and cleans it", async () => {
    let probePath = "";
    const spawnFn = vi.fn((_file: string, args: string[]) => {
      const script = args[2];
      probePath = args[4];
      expect(script).toContain("model.transcribe");
      expect(script).toContain("for _ in segments");
      expect(fs.readFileSync(probePath).subarray(0, 4).toString("ascii")).toBe("RIFF");
      return Promise.resolve({ code: 0, stdout: "VERIFIED\n", stderr: "" });
    });

    await verifyModel({ executable: "python3", prefixArgs: [] }, "/tmp/models", CPU_PROFILE, spawnFn);

    expect(probePath).not.toBe("");
    expect(fs.existsSync(probePath)).toBe(false);
  });

  it("cleans the generated WAV when inference fails", async () => {
    let probePath = "";
    const spawnFn = vi.fn((_file: string, args: string[]) => {
      probePath = args[4];
      expect(fs.existsSync(probePath)).toBe(true);
      return Promise.resolve({ code: 1, stdout: "", stderr: "probe failed" });
    });

    await expect(
      verifyModel({ executable: "python3", prefixArgs: [] }, "/tmp/models", CPU_PROFILE, spawnFn),
    ).rejects.toMatchObject({ category: "model_probe_failed" });
    expect(fs.existsSync(probePath)).toBe(false);
  });

  it("does not verify ready when the generated WAV cannot be removed", async () => {
    let probePath = "";
    const realUnlinkSync = fs.unlinkSync;
    const spawnFn = vi.fn((_file: string, args: string[]) => {
      probePath = args[4];
      return Promise.resolve({ code: 0, stdout: "VERIFIED\n", stderr: "" });
    });
    const unlinkSpy = vi.spyOn(fs, "unlinkSync").mockImplementation((candidate) => {
      if (candidate === probePath) throw new Error("cleanup denied");
      return realUnlinkSync(candidate);
    });

    try {
      await expect(
        verifyModel({ executable: "python3", prefixArgs: [] }, "/tmp/models", CPU_PROFILE, spawnFn),
      ).rejects.toMatchObject({ category: "model_probe_failed" });
    } finally {
      unlinkSpy.mockRestore();
      if (probePath) realUnlinkSync(probePath);
    }
  });

  it("passes model path via argv", async () => {
    const spawnFn = vi.fn(() => Promise.resolve({ code: 0, stdout: "VERIFIED\n", stderr: "" }));
    await verifyModel({ executable: "python3", prefixArgs: [] }, "/tmp/models", CPU_PROFILE, spawnFn);

    const args = spawnFn.mock.calls[0][1];
    expect(args).toContain("/tmp/models");
  });

  it("throws when stdout is not exactly VERIFIED", async () => {
    const spawnFn = vi.fn(() => Promise.resolve({ code: 0, stdout: "VERIFIED and more\n", stderr: "" }));
    await expect(verifyModel({ executable: "python3", prefixArgs: [] }, "/tmp/models", CPU_PROFILE, spawnFn)).rejects.toMatchObject({ category: "model_probe_failed" });
  });

  it("throws on non-zero exit", async () => {
    const spawnFn = vi.fn(() => Promise.resolve({ code: 1, stdout: "", stderr: "import error" }));
    await expect(verifyModel({ executable: "python3", prefixArgs: [] }, "/tmp/models", CPU_PROFILE, spawnFn)).rejects.toMatchObject({ category: "model_probe_failed" });
  });

  it("propagates cancellation through the installed-readiness subprocess seam", async () => {
    const controller = new AbortController();
    const spawnFn = vi.fn((
      _file: string,
      _args: string[],
      signal?: AbortSignal,
    ) => new Promise<never>((_resolve, reject) => {
      expect(signal).toBe(controller.signal);
      signal?.addEventListener("abort", () => reject(new DOMException(
        "The operation was aborted.",
        "AbortError",
      )), { once: true });
    }));
    const pending = verifyInstalledDeviceReadiness(
      { venv: "/tmp/venv", model: "/tmp/models" },
      "auto",
      controller.signal,
      spawnFn,
    );

    controller.abort();
    await expect(pending).rejects.toMatchObject({ name: "AbortError" });
    expect(spawnFn).toHaveBeenCalledOnce();
  });
});

// ---------- installer.ts: full orchestration ----------

describe("runAsrInstallation root guard", () => {
  it("refuses to install when the ASR root is a symlink, before any mutation", async () => {
    const spawnFn = vi.fn();
    const fsMkdirSync = vi.fn();
    const fsUnlinkSync = vi.fn();
    const fsLstatSync = vi.fn(() => ({
      isSymbolicLink: () => true,
      isDirectory: () => false,
      isFile: () => false,
    }));

    const result = await runAsrInstallation({
      spawnFn,
      fsMkdirSync,
      fsUnlinkSync,
      fsLstatSync,
      asrBase: "/tmp/asr",
    });

    expect(result.success).toBe(false);
    expect(result.error).toContain("symlink");
    expect(spawnFn).not.toHaveBeenCalled();
    expect(fsMkdirSync).not.toHaveBeenCalled();
    expect(fsUnlinkSync).not.toHaveBeenCalled();
  });

  it("refuses to install when the ASR root is not a directory, before any mutation", async () => {
    const spawnFn = vi.fn();
    const fsMkdirSync = vi.fn();
    const fsUnlinkSync = vi.fn();
    const fsLstatSync = vi.fn(() => ({
      isSymbolicLink: () => false,
      isDirectory: () => false,
      isFile: () => true,
    }));

    const result = await runAsrInstallation({
      spawnFn,
      fsMkdirSync,
      fsUnlinkSync,
      fsLstatSync,
      asrBase: "/tmp/asr",
    });

    expect(result.success).toBe(false);
    expect(result.error).toContain("not a directory");
    expect(spawnFn).not.toHaveBeenCalled();
    expect(fsMkdirSync).not.toHaveBeenCalled();
    expect(fsUnlinkSync).not.toHaveBeenCalled();
  });

  it("proceeds when the ASR root does not exist yet", async () => {
    const spawnFn = vi
      .fn()
      .mockResolvedValueOnce({ code: 0, stdout: "Python 3.12.0\n", stderr: "" })
      .mockResolvedValue({ code: 1, stdout: "", stderr: "boom" });
    const fsMkdirSync = vi.fn();
    const fsUnlinkSync = vi.fn();
    const fsLstatSync = vi.fn(() => {
      const error = new Error("no such file") as NodeJS.ErrnoException;
      error.code = "ENOENT";
      throw error;
    });

    const result = await runAsrInstallation({
      spawnFn,
      fsMkdirSync,
      fsUnlinkSync,
      fsLstatSync,
      asrBase: "/tmp/asr",
    });

    // The guard passed (absent root is allowed); the pipeline ran and failed
    // later at venv creation, proving spawn happened after the guard.
    expect(spawnFn).toHaveBeenCalled();
    expect(result.success).toBe(false);
  });

  it("fails before any mutation when the root path has an invalid component (ENOTDIR)", async () => {
    const spawnFn = vi.fn();
    const fsMkdirSync = vi.fn();
    const fsUnlinkSync = vi.fn();
    const fsLstatSync = vi.fn(() => {
      const error = new Error("not a directory") as NodeJS.ErrnoException;
      error.code = "ENOTDIR";
      throw error;
    });

    const result = await runAsrInstallation({
      spawnFn,
      fsMkdirSync,
      fsUnlinkSync,
      fsLstatSync,
      asrBase: "/tmp/asr",
    });

    // ENOTDIR means an invalid/non-directory path component, not an absent
    // root: it must fail before any spawn or mutation.
    expect(result.success).toBe(false);
    expect(result.error).toContain("Cannot inspect ASR root");
    expect(spawnFn).not.toHaveBeenCalled();
    expect(fsMkdirSync).not.toHaveBeenCalled();
    expect(fsUnlinkSync).not.toHaveBeenCalled();
  });
});

describe("runAsrInstallation", () => {
  it("succeeds when all steps pass and writes ready marker", async () => {
    let step = 0;
    const outputs = [
      "Python 3.12.0\n", "", "", "DOWNLOADED\n", "VERIFIED\n",
    ];
    const spawnFn = vi.fn(() => Promise.resolve({ code: 0, stdout: outputs[step++] ?? "", stderr: "" }));
    const tmpBase = path.join(os.tmpdir(), "bilibili-mcp-asr-int-" + Date.now());
    fs.mkdirSync(tmpBase, { recursive: true });
    // Create expected artifact directories so readAsrState finds them
    const binDir = path.join(tmpBase, "venv", os.platform() === "win32" ? "Scripts" : "bin");
    fs.mkdirSync(binDir, { recursive: true });
    fs.writeFileSync(path.join(binDir, os.platform() === "win32" ? "python.exe" : "python"), "fake");
    const modelsDir = path.join(tmpBase, "models");
    fs.mkdirSync(modelsDir, { recursive: true });
    for (const f of ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"]) {
      fs.writeFileSync(path.join(modelsDir, f), "placeholder");
    }

    const result = await runAsrInstallation({ spawnFn, fsMkdirSync: fs.mkdirSync, asrBase: tmpBase });
    expect(result.success).toBe(true);

    // pip, download, verify all use the derived venv Python
    const calls = spawnFn.mock.calls.map((c) => c[0]);
    const venvPythonExe = process.platform === "win32" ? "python.exe" : "python";
    // skip: discovery (0), venv creation (1)
    const postVenv = calls.slice(2);
    expect(postVenv.length).toBeGreaterThanOrEqual(3);
    expect(postVenv.every((exe) => path.basename(exe) === venvPythonExe)).toBe(true);
    // Ready marker was written
    expect(fs.existsSync(path.join(tmpBase, "state.json"))).toBe(true);
    expect(readAsrState(path.join(tmpBase, "state.json")).kind).toBe("ready");

    try { fs.rmSync(tmpBase, { recursive: true, force: true }); } catch { /* ok */ }
  });

  it("verify failure leaves no ready marker", async () => {
    let step = 0;
    const outputs = [
      "Python 3.12.0\n", "", "",
      "DOWNLOADED\n",
      { code: 1, stdout: "", stderr: "model load failed" },
    ];
    let verifyReached = false;
    const spawnFn = vi.fn((_file: string, args: string[]) => {
      const out = outputs[step++];
      if (typeof out !== "string" && args.some((a) => a.includes("WhisperModel"))) {
        verifyReached = true;
      }
      if (typeof out === "string") return Promise.resolve({ code: 0, stdout: out, stderr: "" });
      return Promise.resolve(out);
    });
    const tmpBase = path.join(os.tmpdir(), "bilibili-mcp-asr-vfy-" + Date.now());
    fs.mkdirSync(tmpBase, { recursive: true });

    const result = await runAsrInstallation({ spawnFn, fsMkdirSync: fs.mkdirSync, asrBase: tmpBase });
    expect(result.success).toBe(false);
    expect(verifyReached).toBe(true);
    // No ready marker
    expect(fs.existsSync(path.join(tmpBase, "state.json"))).toBe(false);

    try { fs.rmSync(tmpBase, { recursive: true, force: true }); } catch { /* ok */ }
  });

  it("returns success false when discovery fails", async () => {
    const spawnFn = vi.fn(() => Promise.reject(new Error("ENOENT")));
    const tmpBase = path.join(os.tmpdir(), "bilibili-mcp-asr-disc-" + Date.now());
    const result = await runAsrInstallation({ spawnFn, asrBase: tmpBase });
    expect(result.success).toBe(false);
    expect(result.error).toContain("not found");
    try { fs.rmSync(tmpBase, { recursive: true, force: true }); } catch { /* ok */ }
  });

  it("returns success false mid-install", async () => {
    let step = 0;
    const outputs = [
      { code: 0, stdout: "Python 3.12.0\n" },
      { code: 1, stdout: "", stderr: "disk full" },
    ];
    const spawnFn = vi.fn(() => Promise.resolve(outputs[step++] ?? { code: 1, stdout: "", stderr: "unknown" }));
    const tmpBase = path.join(os.tmpdir(), "bilibili-mcp-asr-mid-" + Date.now());
    const result = await runAsrInstallation({ spawnFn, asrBase: tmpBase });
    expect(result.success).toBe(false);
    expect(result.error).toBeDefined();
    try { fs.rmSync(tmpBase, { recursive: true, force: true }); } catch { /* ok */ }
  });

  it("re-pins the runtime and reruns explicit CPU readiness when already ready", async () => {
    const tmpBase = path.join(os.tmpdir(), "bilibili-mcp-asr-idem-" + Date.now());
    fs.mkdirSync(tmpBase, { recursive: true });
    const stateFile = path.join(tmpBase, "state.json");
    const binDir = path.join(tmpBase, "venv", os.platform() === "win32" ? "Scripts" : "bin");
    fs.mkdirSync(binDir, { recursive: true });
    fs.writeFileSync(path.join(binDir, os.platform() === "win32" ? "python.exe" : "python"), "fake");
    const modelsDir = path.join(tmpBase, "models");
    fs.mkdirSync(modelsDir, { recursive: true });
    for (const f of ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"]) {
      fs.writeFileSync(path.join(modelsDir, f), "placeholder");
    }
    writeAsrState(stateFile);

    const spawnFn = vi.fn((_file: string, args: string[]) => {
      materializeMockVenv(args);
      return Promise.resolve({
        code: 0,
        stdout: args.includes("pip") || args.includes("venv") ? "" : "VERIFIED\n",
        stderr: "",
      });
    });
    const result = await runAsrInstallation({
      spawnFn,
      asrBase: tmpBase,
      devicePreference: "cpu",
    });

    expect(result.success).toBe(true);
    expect(spawnFn).toHaveBeenCalledTimes(3);
    expect(spawnFn.mock.calls[1][1]).toContain(ASR_PINNED_CTRANSLATE2);
    expect(spawnFn.mock.calls[2][1].slice(-2)).toEqual(["cpu", "int8"]);

    // cleanup
    try { fs.rmSync(tmpBase, { recursive: true, force: true }); } catch { /* ok */ }
  });

  it("old marker + missing file + download restores files + verify fails => incomplete", async () => {
    const tmpBase = path.join(os.tmpdir(), "bilibili-mcp-asr-regr-" + Date.now());
    fs.mkdirSync(tmpBase, { recursive: true });
    const stateFile = path.join(tmpBase, "state.json");
    const modelsDir = path.join(tmpBase, "models");
    fs.mkdirSync(modelsDir, { recursive: true });
    const binDir = path.join(tmpBase, "venv", os.platform() === "win32" ? "Scripts" : "bin");
    fs.mkdirSync(binDir, { recursive: true });
    fs.writeFileSync(path.join(binDir, os.platform() === "win32" ? "python.exe" : "python"), "fake");

    // Write old valid marker
    writeAsrState(stateFile);
    // All model files present – state is ready
    for (const f of ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"]) {
      fs.writeFileSync(path.join(modelsDir, f), "placeholder");
    }
    expect(readAsrState(stateFile).kind).toBe("ready");

    // Delete model.bin to simulate corrupt artifact
    fs.unlinkSync(path.join(modelsDir, "model.bin"));
    expect(readAsrState(stateFile).kind).toBe("incomplete");

    // Retry: discover → venv → pip → download (restores model.bin) → verify fails
    let step = 0;
    const outputs = [
      "Python 3.12.0\n",   // 0: discoverPython ok
      "",                    // 1: createVenv ok
      "",                    // 2: installRuntime (pip) ok
      "DOWNLOADED\n",        // 3: downloadModel — actually write model.bin
      { code: 1, stdout: "", stderr: "verify error" }, // 4: verifyModel FAILS
    ];
    let verifyReached = false;
    const spawnFn = vi.fn((_file: string, args: string[]) => {
      const out = outputs[step++];
      // Download call restores model.bin in the managed staging directory.
      if (typeof out === "string" && out.trim() === "DOWNLOADED") {
        const staging = args.find(
          (arg) => arg.includes(".models-staging-"),
        );
        if (!staging) throw new Error("missing staging path");
        fs.writeFileSync(path.join(staging, "model.bin"), "restored");
      }
      // Track that verifyModel was called (script contains WhisperModel)
      if (typeof out !== "string" && args.some((a) => a.includes("WhisperModel"))) {
        verifyReached = true;
      }
      if (typeof out === "string") return Promise.resolve({ code: 0, stdout: out, stderr: "" });
      return Promise.resolve(out);
    });

    const result = await runAsrInstallation({ spawnFn, asrBase: tmpBase });
    expect(result.success).toBe(false);
    expect(verifyReached).toBe(true);
    // Verification failure removes staging and never publishes a model tree.
    expect(fs.existsSync(path.join(modelsDir, "model.bin"))).toBe(false);
    // Old marker was invalidated; remaining artifacts are incomplete.
    expect(readAsrState(stateFile).kind).toBe("incomplete");

    try { fs.rmSync(tmpBase, { recursive: true, force: true }); } catch { /* ok */ }
  });

  it("buildAsrChildEnv uses an allowlist and fixed safe flags", () => {
    const source = {
      BILIBILI_SESSDATA: "x",
      bilibili_sessdata: "x",
      BILIBILI_DEDEUSERID: "x",
      BILIBILI_BILI_JCT: "x",
      PYTHONPATH: "/some/path",
      PYTHONHOME: "/some/home",
      OTHER_VAR: "x",
      PATH: "/usr/bin",
      CUDA_PATH: "C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v12.8",
      LD_LIBRARY_PATH: "/opt/cuda/lib64",
      LD_PRELOAD: "/tmp/injected.so",
      CUDA_PATH_EVIL: "C:\\private",
    };
    const result = buildAsrChildEnv(source);
    expect(result.BILIBILI_SESSDATA).toBeUndefined();
    expect(result.bilibili_sessdata).toBeUndefined();
    expect(result.BILIBILI_DEDEUSERID).toBeUndefined();
    expect(result.BILIBILI_BILI_JCT).toBeUndefined();
    expect(result.PYTHONPATH).toBeUndefined();
    expect(result.PYTHONHOME).toBeUndefined();
    expect(result.OTHER_VAR).toBeUndefined();
    expect(result.PATH).toBe("/usr/bin");
    expect(result.CUDA_PATH).toContain("NVIDIA GPU Computing Toolkit");
    expect(result.LD_LIBRARY_PATH).toBe("/opt/cuda/lib64");
    expect(result.LD_PRELOAD).toBeUndefined();
    expect(result.CUDA_PATH_EVIL).toBeUndefined();
    expect(result.PIP_NO_INPUT).toBe("1");
    expect(result.PYTHONNOUSERSITE).toBe("1");
  });

  it("does not clear an invalid stale marker before installation succeeds", async () => {
    const tmpBase = path.join(os.tmpdir(), "bilibili-mcp-asr-perm-" + Date.now());
    fs.mkdirSync(tmpBase, { recursive: true });
    const stateFile = path.join(tmpBase, "state.json");
    // Write an incomplete marker
    fs.writeFileSync(stateFile, JSON.stringify({ kind: "ready", version: 999 }), "utf8");

    const previous = fs.readFileSync(stateFile, "utf8");
    const unlockFn = vi.fn();
    const spawnFn = vi.fn();

    const result = await runAsrInstallation({
      spawnFn,
      asrBase: tmpBase,
      fsUnlinkSync: unlockFn,
    });

    expect(result.success).toBe(false);
    expect(result.error).toContain("Python 3.9+ not found");
    expect(unlockFn).not.toHaveBeenCalled();
    expect(fs.readFileSync(stateFile, "utf8")).toBe(previous);

    try { fs.rmSync(tmpBase, { recursive: true, force: true }); } catch { /* ok */ }
  });

  it("atomically replaces an invalid stale marker after setup succeeds", async () => {
    const tmpBase = path.join(os.tmpdir(), "bilibili-mcp-asr-enoent-" + Date.now());
    fs.mkdirSync(tmpBase, { recursive: true });
    const stateFile = path.join(tmpBase, "state.json");
    fs.writeFileSync(stateFile, JSON.stringify({ kind: "ready", version: 999 }), "utf8");

    const modelsDir = path.join(tmpBase, "models");
    fs.mkdirSync(modelsDir, { recursive: true });
    for (const file of ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"]) {
      fs.writeFileSync(path.join(modelsDir, file), "placeholder");
    }
    const binDir = path.join(tmpBase, "venv", process.platform === "win32" ? "Scripts" : "bin");
    fs.mkdirSync(binDir, { recursive: true });
    fs.writeFileSync(path.join(binDir, process.platform === "win32" ? "python.exe" : "python"), "fake");
    const unlockFn = vi.fn();
    let step = 0;
    const outputs = ["Python 3.12.0\n", "", "", "DOWNLOADED\n", "VERIFIED\n"];
    const spawnFn = vi.fn(() => Promise.resolve({
      code: 0,
      stdout: outputs[step++] ?? "",
      stderr: "",
    }));

    const result = await runAsrInstallation({
      spawnFn,
      asrBase: tmpBase,
      fsUnlinkSync: unlockFn,
      devicePreference: "cpu",
    });

    expect(result.success).toBe(true);
    expect(unlockFn).not.toHaveBeenCalled();
    expect(readAsrState(stateFile)).toMatchObject({
      kind: "ready",
      executionProfile: CPU_PROFILE,
    });

    try { fs.rmSync(tmpBase, { recursive: true, force: true }); } catch { /* ok */ }
  });

  it("buildAsrChildEnv drops ambient non-allowlisted variables", () => {
    const source = { BILIBILI_SESSDATA: "a", OTHER_KEEP: "b" };
    const result = buildAsrChildEnv(source);
    expect(result.BILIBILI_SESSDATA).toBeUndefined();
    expect(result.OTHER_KEEP).toBeUndefined();
  });

  it("uses env BILIBILI_ASR_PYTHON when pythonOverride not passed", async () => {
    const saved = process.env.BILIBILI_ASR_PYTHON;
    try {
      process.env.BILIBILI_ASR_PYTHON = "/custom/python";

      let step = 0;
      const outputs = [
        "Python 3.11.0\n", "", "", "DOWNLOADED\n", "VERIFIED\n",
      ];
      const spawnFn = vi.fn(() => Promise.resolve({ code: 0, stdout: outputs[step++] ?? "", stderr: "" }));

      const tmpBase = path.join(os.tmpdir(), "bilibili-mcp-asr-env-" + Date.now());
      fs.mkdirSync(tmpBase, { recursive: true });
      const result = await runAsrInstallation({ spawnFn, asrBase: tmpBase });

      expect(spawnFn).toHaveBeenCalledWith("/custom/python", ["-I", "--version"]);
      expect(result.pythonPath).toBe("/custom/python");

      try { fs.rmSync(tmpBase, { recursive: true, force: true }); } catch { /* ok */ }
    } finally {
      if (saved === undefined) delete process.env.BILIBILI_ASR_PYTHON;
      else process.env.BILIBILI_ASR_PYTHON = saved;
    }
  });

  it("explicit pythonOverride takes precedence over env", async () => {
    const saved = process.env.BILIBILI_ASR_PYTHON;
    try {
      process.env.BILIBILI_ASR_PYTHON = "/env/python";

      let step = 0;
      const outputs = [
        "Python 3.11.0\n", "", "", "DOWNLOADED\n", "VERIFIED\n",
      ];
      const spawnFn = vi.fn(() => Promise.resolve({ code: 0, stdout: outputs[step++] ?? "", stderr: "" }));

      const tmpBase = path.join(os.tmpdir(), "bilibili-mcp-asr-expl-" + Date.now());
      fs.mkdirSync(tmpBase, { recursive: true });
      const result = await runAsrInstallation({ spawnFn, pythonOverride: "/explicit/python", asrBase: tmpBase });

      expect(spawnFn).toHaveBeenCalledWith("/explicit/python", ["-I", "--version"]);
      expect(result.pythonPath).toBe("/explicit/python");

      try { fs.rmSync(tmpBase, { recursive: true, force: true }); } catch { /* ok */ }
    } finally {
      if (saved === undefined) delete process.env.BILIBILI_ASR_PYTHON;
      else process.env.BILIBILI_ASR_PYTHON = saved;
    }
  });

  it("all Python operations include -I (isolated mode)", async () => {
    // Override probe
    const ovr = vi.fn(() => Promise.resolve({ code: 0, stdout: "Python 3.11.0\n", stderr: "" }));
    await discoverPython(ovr, "/bin/python");
    expect(ovr.mock.calls[0][1]).toEqual(["-I", "--version"]);

    // Candidate probe
    const cand = vi.fn(() => Promise.resolve({ code: 0, stdout: "Python 3.12.0\n", stderr: "" }));
    await discoverPython(cand, undefined, [{ executable: "python3", prefixArgs: [] }]);
    expect(cand.mock.calls[0][1]).toEqual(["-I", "--version"]);

    // py -3 probe
    const py3 = vi.fn(() => Promise.resolve({ code: 0, stdout: "Python 3.12.0\n", stderr: "" }));
    await discoverPython(py3, undefined, [{ executable: "py", prefixArgs: ["-3"] }]);
    expect(py3.mock.calls[0][1]).toEqual(["-3", "-I", "--version"]);

    // venv
    const vv = vi.fn(() => Promise.resolve({ code: 0, stdout: "", stderr: "" }));
    await createVenv({ executable: "python3", prefixArgs: [] }, "/tmp/venv", vv, vi.fn());
    expect(vv.mock.calls[0][1]).toEqual(["-I", "-m", "venv", "--copies", "/tmp/venv"]);

    // pip
    const pip = vi.fn(() => Promise.resolve({ code: 0, stdout: "", stderr: "" }));
    await installRuntime({ executable: "/tmp/venv/bin/python", prefixArgs: [] }, pip);
    expect(pip.mock.calls[0][1][0]).toBe("-I");
    expect(pip.mock.calls[0][1][1]).toBe("-m");

    // download
    const dl = vi.fn(() => Promise.resolve({ code: 0, stdout: "DOWNLOADED\n", stderr: "" }));
    await downloadModel({ executable: "python3", prefixArgs: [] }, "/tmp/models", ASR_PINNED_MODEL, ASR_PINNED_REVISION, dl, vi.fn());
    expect(dl.mock.calls[0][1][0]).toBe("-I");
    expect(dl.mock.calls[0][1][1]).toBe("-c");

    // verify
    const vrfy = vi.fn(() => Promise.resolve({ code: 0, stdout: "VERIFIED\n", stderr: "" }));
    await verifyModel({ executable: "python3", prefixArgs: [] }, "/tmp/models", CPU_PROFILE, vrfy);
    expect(vrfy.mock.calls[0][1][0]).toBe("-I");
    expect(vrfy.mock.calls[0][1][1]).toBe("-c");
  });

  it("all exported functions are defined", async () => {
    const mod = await import("../src/asr/installer.js");
    expect(mod.discoverPython).toBeDefined();
    expect(mod.runAsrInstallation).toBeDefined();
    expect(mod.verifyModel).toBeDefined();
    expect(mod.downloadModel).toBeDefined();
    expect(mod.createVenv).toBeDefined();
    expect(mod.installRuntime).toBeDefined();
  });
});

// ---------- Phase 2: model allowlist ----------

describe("resolveModelSpec", () => {
  it("returns tiny spec for 'tiny'", () => {
    const spec = resolveModelSpec("tiny");
    expect(spec.key).toBe("tiny");
    expect(spec.repository).toBe("Systran/faster-whisper-tiny");
    expect(spec.approximateMB).toBe(78.2);
  });

  it("returns base spec for 'base'", () => {
    const spec = resolveModelSpec("base");
    expect(spec.key).toBe("base");
    expect(spec.repository).toBe("Systran/faster-whisper-base");
    expect(spec.approximateMB).toBe(148);
  });

  it("returns small spec for 'small'", () => {
    const spec = resolveModelSpec("small");
    expect(spec.key).toBe("small");
    expect(spec.repository).toBe("Systran/faster-whisper-small");
    expect(spec.approximateMB).toBe(486);
  });

  it("is case-insensitive", () => {
    expect(resolveModelSpec("TINY").key).toBe("tiny");
    expect(resolveModelSpec("Small").key).toBe("small");
  });

  it("throws for unknown model key", () => {
    expect(() => resolveModelSpec("large")).toThrow("Unknown ASR model key");
  });

  it("throws for empty string", () => {
    expect(() => resolveModelSpec("")).toThrow("Unknown ASR model key");
  });
});

describe("isAllowlistedModel", () => {
  it("returns true for Phase 1 small repository/revision", () => {
    expect(isAllowlistedModel(ASR_PINNED_MODEL, ASR_PINNED_REVISION)).toBe(true);
  });

  it("returns true for tiny repository/revision", () => {
    expect(isAllowlistedModel("Systran/faster-whisper-tiny", "d90ca5fe260221311c53c58e660288d3deb8d356")).toBe(true);
  });

  it("returns true for base repository/revision", () => {
    expect(isAllowlistedModel("Systran/faster-whisper-base", "ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66")).toBe(true);
  });

  it("returns false for unknown repository", () => {
    expect(isAllowlistedModel("unknown/model", ASR_PINNED_REVISION)).toBe(false);
  });

  it("returns false for known repository with wrong revision", () => {
    expect(isAllowlistedModel(ASR_PINNED_MODEL, "0000000000000000000000000000000000000000")).toBe(false);
  });
});

describe("readAsrState Phase 2 compatibility", () => {
  it("returns ready for tiny model state with matching artifacts", () => {
    const existsSync = vi.fn(() => true);
    const readFileSync = vi.fn(() =>
      JSON.stringify({
        kind: "ready",
        version: 1,
        runtime: ASR_PINNED_RUNTIME,
        model: "Systran/faster-whisper-tiny",
        revision: "d90ca5fe260221311c53c58e660288d3deb8d356",
      }),
    );
    const lstatSync = vi.fn(() => ({
      isSymbolicLink: () => false,
      isDirectory: () => true,
      isFile: () => true,
    }));
    const state = readAsrState("/tmp/asr/state.json", readFileSync, existsSync, lstatSync);
    expect(state.kind).toBe("ready");
    expect(state.model).toBe("Systran/faster-whisper-tiny");
  });

  it("returns ready for base model state with matching artifacts", () => {
    const existsSync = vi.fn(() => true);
    const readFileSync = vi.fn(() =>
      JSON.stringify({
        kind: "ready",
        version: 1,
        runtime: ASR_PINNED_RUNTIME,
        model: "Systran/faster-whisper-base",
        revision: "ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66",
      }),
    );
    const lstatSync = vi.fn(() => ({
      isSymbolicLink: () => false,
      isDirectory: () => true,
      isFile: () => true,
    }));
    const state = readAsrState("/tmp/asr/state.json", readFileSync, existsSync, lstatSync);
    expect(state.kind).toBe("ready");
  });

  it("Phase 1 small state is still read as ready", () => {
    const existsSync = vi.fn(() => true);
    const readFileSync = vi.fn(() =>
      JSON.stringify({
        kind: "ready",
        version: 1,
        runtime: ASR_PINNED_RUNTIME,
        model: ASR_PINNED_MODEL,
        revision: ASR_PINNED_REVISION,
      }),
    );
    const lstatSync = vi.fn(() => ({
      isSymbolicLink: () => false,
      isDirectory: () => true,
      isFile: () => true,
    }));
    const state = readAsrState("/tmp/asr/state.json", readFileSync, existsSync, lstatSync);
    expect(state.kind).toBe("ready");
  });

  it("returns incomplete for un-allowlisted model even with valid version", () => {
    const existsSync = vi.fn(() => true);
    const readFileSync = vi.fn(() =>
      JSON.stringify({
        kind: "ready",
        version: 1,
        runtime: ASR_PINNED_RUNTIME,
        model: "evil/model",
        revision: "deadbeef",
      }),
    );
    const state = readAsrState("/tmp/asr/state.json", readFileSync, existsSync);
    expect(state.kind).toBe("incomplete");
  });
});

describe("readAsrState Execution Profile schema", () => {
  const existsSync = vi.fn(() => true);
  const lstatSync = vi.fn(() => ({
    isSymbolicLink: () => false,
    isDirectory: () => true,
    isFile: () => true,
  }));
  const base = {
    kind: "ready",
    version: 2,
    runtime: ASR_PINNED_RUNTIME,
    model: ASR_PINNED_MODEL,
    revision: ASR_PINNED_REVISION,
    device: "cpu",
    compute_type: "int8",
    device_readiness: "ready",
    migration_status: "completed",
  };
  const read = (value: Record<string, unknown>) => readAsrState(
    "/tmp/asr/state.json",
    vi.fn(() => JSON.stringify(value)),
    existsSync,
    lstatSync,
  );

  it("reads v1 as model-ready with device migration pending", () => {
    const state = read({
      kind: "ready",
      version: 1,
      runtime: ASR_PINNED_RUNTIME,
      model: ASR_PINNED_MODEL,
      revision: ASR_PINNED_REVISION,
    });

    expect(state.kind).toBe("ready");
    expect(state.modelKey).toBe("small");
    expect(state.executionProfile).toBeUndefined();
    expect(state.deviceReadiness).toBe("migration_pending");
    expect(state.migrationStatus).toBe("pending");
  });

  it("reads a verified v2 CPU profile", () => {
    const state = read(base);

    expect(state.kind).toBe("ready");
    expect(state.executionProfile).toEqual({ device: "cpu", computeType: "int8" });
    expect(state.deviceReadiness).toBe("ready");
    expect(state.migrationStatus).toBe("completed");
    expect(state.failureCategory).toBeUndefined();
  });

  it("reads a verified v2 CUDA profile", () => {
    expect(resolveExecutionProfile("cuda", "float16")).toEqual({
      device: "cuda",
      computeType: "float16",
    });

    const state = read({
      ...base,
      device: "cuda",
      compute_type: "float16",
    });

    expect(state.kind).toBe("ready");
    expect(state.executionProfile).toEqual({ device: "cuda", computeType: "float16" });
    expect(state.deviceReadiness).toBe("ready");
    expect(state.migrationStatus).toBe("completed");
    expect(state.failureCategory).toBeUndefined();
  });

  it("accepts a sanitized GPU failure category on the CPU fallback profile", () => {
    const state = read({
      ...base,
      failure_category: "no_nvidia_gpu",
    });

    expect(state.executionProfile).toEqual({ device: "cpu", computeType: "int8" });
    expect(state.failureCategory).toBe("no_nvidia_gpu");
  });

  it.each([
    ["device", { device: "../../gpu" }],
    ["compute type", { compute_type: "__import__('os')" }],
    ["cross-paired profile", { device: "cpu", compute_type: "float16" }],
    ["readiness", { device_readiness: "maybe" }],
    ["migration status", { migration_status: "running" }],
    ["failure category", { failure_category: "raw stderr: C:\\secret" }],
    ["CUDA ready with a GPU failure category", { device: "cuda", compute_type: "float16", failure_category: "no_nvidia_gpu" }],
    ["unexpected sensitive field", { stderr: "C:\\secret" }],
  ])("fails closed for invalid %s", (_label, overrides) => {
    expect(read({ ...base, ...overrides }).kind).toBe("incomplete");
  });
});

describe("writeAsrState Phase 2", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "bilibili-mcp-asr-p2-"));
  const stateFile = path.join(tmpDir, "state.json");

  afterAll(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  afterEach(() => {
    try { fs.unlinkSync(stateFile); } catch { /* ok */ }
    try { fs.unlinkSync(stateFile + ".tmp"); } catch { /* ok */ }
  });

  it("writes tiny model state", () => {
    fs.mkdirSync(tmpDir, { recursive: true });
    writeAsrState(stateFile, "tiny");
    const parsed = JSON.parse(fs.readFileSync(stateFile, "utf8"));
    expect(parsed.model).toBe("Systran/faster-whisper-tiny");
    expect(parsed.revision).toBe("d90ca5fe260221311c53c58e660288d3deb8d356");
    expect(parsed).toMatchObject({
      version: 2,
      device: "cpu",
      compute_type: "int8",
      device_readiness: "ready",
      migration_status: "completed",
    });
  });

  it("writes base model state", () => {
    fs.mkdirSync(tmpDir, { recursive: true });
    writeAsrState(stateFile, "base");
    const parsed = JSON.parse(fs.readFileSync(stateFile, "utf8"));
    expect(parsed.model).toBe("Systran/faster-whisper-base");
  });

  it("writes a verified CUDA profile", () => {
    fs.mkdirSync(tmpDir, { recursive: true });
    writeAsrState(stateFile, "small", {
      executionProfile: { device: "cuda", computeType: "float16" },
    });

    expect(JSON.parse(fs.readFileSync(stateFile, "utf8"))).toMatchObject({
      device: "cuda",
      compute_type: "float16",
      device_readiness: "ready",
      migration_status: "completed",
    });
  });

  it("writes only a sanitized GPU failure category on a CPU fallback", () => {
    fs.mkdirSync(tmpDir, { recursive: true });
    writeAsrState(stateFile, "small", {
      executionProfile: { device: "cpu", computeType: "int8" },
      failureCategory: "cuda_runtime_missing",
    });

    expect(JSON.parse(fs.readFileSync(stateFile, "utf8"))).toMatchObject({
      device: "cpu",
      compute_type: "int8",
      failure_category: "cuda_runtime_missing",
    });
  });

  it("rejects a CUDA profile paired with a failure category", () => {
    fs.mkdirSync(tmpDir, { recursive: true });
    expect(() => writeAsrState(stateFile, "small", {
      executionProfile: { device: "cuda", computeType: "float16" },
      failureCategory: "no_nvidia_gpu",
    })).toThrow("failure category");
  });

  it("throws for invalid model key", () => {
    fs.mkdirSync(tmpDir, { recursive: true });
    expect(() => writeAsrState(stateFile, "large")).toThrow("Unknown ASR model key");
  });
});

// ---------- Phase 2: installer model selection ----------

describe("runAsrInstallation with modelKey", () => {
  it("installs tiny model when modelKey is 'tiny'", async () => {
    let step = 0;
    const outputs = ["Python 3.12.0\n", "", "", "DOWNLOADED\n", "VERIFIED\n"];
    const spawnFn = vi.fn(() => Promise.resolve({ code: 0, stdout: outputs[step++] ?? "", stderr: "" }));
    const tmpBase = path.join(os.tmpdir(), "bilibili-mcp-asr-p2-tiny-" + Date.now());
    fs.mkdirSync(tmpBase, { recursive: true });
    const binDir = path.join(tmpBase, "venv", os.platform() === "win32" ? "Scripts" : "bin");
    fs.mkdirSync(binDir, { recursive: true });
    fs.writeFileSync(path.join(binDir, os.platform() === "win32" ? "python.exe" : "python"), "fake");
    const modelsDir = path.join(tmpBase, "models");
    fs.mkdirSync(modelsDir, { recursive: true });
    for (const f of ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"]) {
      fs.writeFileSync(path.join(modelsDir, f), "placeholder");
    }

    const result = await runAsrInstallation({ spawnFn, fsMkdirSync: fs.mkdirSync, asrBase: tmpBase, modelKey: "tiny" });
    expect(result.success).toBe(true);

    const state = readAsrState(path.join(tmpBase, "state.json"));
    expect(state.kind).toBe("ready");
    expect(state.model).toBe("Systran/faster-whisper-tiny");
    expect(state.revision).toBe("d90ca5fe260221311c53c58e660288d3deb8d356");

    try { fs.rmSync(tmpBase, { recursive: true, force: true }); } catch { /* ok */ }
  });

  it("defaults to small when no modelKey is provided", async () => {
    let step = 0;
    const outputs = ["Python 3.12.0\n", "", "", "DOWNLOADED\n", "VERIFIED\n"];
    const spawnFn = vi.fn(() => Promise.resolve({ code: 0, stdout: outputs[step++] ?? "", stderr: "" }));
    const tmpBase = path.join(os.tmpdir(), "bilibili-mcp-asr-p2-def-" + Date.now());
    fs.mkdirSync(tmpBase, { recursive: true });
    const binDir = path.join(tmpBase, "venv", os.platform() === "win32" ? "Scripts" : "bin");
    fs.mkdirSync(binDir, { recursive: true });
    fs.writeFileSync(path.join(binDir, os.platform() === "win32" ? "python.exe" : "python"), "fake");
    const modelsDir = path.join(tmpBase, "models");
    fs.mkdirSync(modelsDir, { recursive: true });
    for (const f of ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"]) {
      fs.writeFileSync(path.join(modelsDir, f), "placeholder");
    }

    const result = await runAsrInstallation({ spawnFn, fsMkdirSync: fs.mkdirSync, asrBase: tmpBase });
    expect(result.success).toBe(true);
    const state = readAsrState(path.join(tmpBase, "state.json"));
    expect(state.model).toBe("Systran/faster-whisper-small");

    try { fs.rmSync(tmpBase, { recursive: true, force: true }); } catch { /* ok */ }
  });

  it("throws before any mutation when modelKey is invalid", async () => {
    const spawnFn = vi.fn();
    const tmpBase = path.join(os.tmpdir(), "bilibili-mcp-asr-p2-bad-" + Date.now());
    fs.mkdirSync(tmpBase, { recursive: true });

    const result = await runAsrInstallation({ spawnFn, asrBase: tmpBase, modelKey: "large" });
    expect(result.success).toBe(false);
    expect(result.error).toContain("Unknown ASR model key");
    expect(spawnFn).not.toHaveBeenCalled();

    try { fs.rmSync(tmpBase, { recursive: true, force: true }); } catch { /* ok */ }
  });

  it("reinstalls when existing state has different model (model switch)", async () => {
    const tmpBase = path.join(os.tmpdir(), "bilibili-mcp-asr-p2-switch-" + Date.now());
    fs.mkdirSync(tmpBase, { recursive: true });
    const stateFile = path.join(tmpBase, "state.json");

    // Pre-create ready state for tiny
    const binDir = path.join(tmpBase, "venv", os.platform() === "win32" ? "Scripts" : "bin");
    fs.mkdirSync(binDir, { recursive: true });
    fs.writeFileSync(path.join(binDir, os.platform() === "win32" ? "python.exe" : "python"), "fake");
    const modelsDir = path.join(tmpBase, "models");
    fs.mkdirSync(modelsDir, { recursive: true });
    for (const f of ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"]) {
      fs.writeFileSync(path.join(modelsDir, f), "placeholder");
    }
    writeAsrState(stateFile, "tiny");
    expect(readAsrState(stateFile).kind).toBe("ready");

    // Now install small. The downloaded staging tree is published only after verification.
    let step = 0;
    const outputs = ["", "", "DOWNLOADED\n", "VERIFIED\n"];
    const spawnFn = vi.fn((_file: string, args: string[]) => {
      materializeMockVenv(args);
      const stdout = outputs[step++] ?? "";
      if (stdout.trim() === "DOWNLOADED") {
        const staging = args.find((arg) => arg.includes(".models-staging-"));
        if (!staging) throw new Error("missing staging path");
        for (const file of ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"]) {
          fs.writeFileSync(path.join(staging, file), `new-${file}`);
        }
      }
      return Promise.resolve({ code: 0, stdout, stderr: "" });
    });

    const result = await runAsrInstallation({ spawnFn, fsMkdirSync: fs.mkdirSync, asrBase: tmpBase, modelKey: "small" });
    expect(result.success).toBe(true);

    // State should now be small
    const finalState = readAsrState(stateFile);
    expect(finalState.kind).toBe("ready");
    expect(finalState.model).toBe("Systran/faster-whisper-small");

    // Spawn was called (reinstalled)
    expect(spawnFn).toHaveBeenCalled();

    try { fs.rmSync(tmpBase, { recursive: true, force: true }); } catch { /* ok */ }
  });

  it("same-model ready state reruns the selected readiness probe", async () => {
    const tmpBase = path.join(os.tmpdir(), "bilibili-mcp-asr-p2-same-" + Date.now());
    fs.mkdirSync(tmpBase, { recursive: true });
    const stateFile = path.join(tmpBase, "state.json");
    const binDir = path.join(tmpBase, "venv", os.platform() === "win32" ? "Scripts" : "bin");
    fs.mkdirSync(binDir, { recursive: true });
    fs.writeFileSync(path.join(binDir, os.platform() === "win32" ? "python.exe" : "python"), "fake");
    const modelsDir = path.join(tmpBase, "models");
    fs.mkdirSync(modelsDir, { recursive: true });
    for (const f of ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"]) {
      fs.writeFileSync(path.join(modelsDir, f), "placeholder");
    }
    writeAsrState(stateFile, "small");

    const spawnFn = vi.fn((_file: string, args: string[]) => {
      materializeMockVenv(args);
      return Promise.resolve({
        code: 0,
        stdout: args.includes("pip") || args.includes("venv") ? "" : "VERIFIED\n",
        stderr: "",
      });
    });
    const result = await runAsrInstallation({
      spawnFn,
      asrBase: tmpBase,
      modelKey: "small",
      devicePreference: "cpu",
    });
    expect(result.success).toBe(true);
    expect(spawnFn).toHaveBeenCalledTimes(3);
    expect(spawnFn.mock.calls[2][1].slice(-2)).toEqual(["cpu", "int8"]);

    try { fs.rmSync(tmpBase, { recursive: true, force: true }); } catch { /* ok */ }
  });

  it("promotes a same-model v1 state with a staged runtime and one CPU probe", async () => {
    const tmpBase = fs.mkdtempSync(path.join(os.tmpdir(), "bilibili-mcp-asr-v1-promote-"));
    const stateFile = path.join(tmpBase, "state.json");
    const binDir = path.join(tmpBase, "venv", os.platform() === "win32" ? "Scripts" : "bin");
    fs.mkdirSync(binDir, { recursive: true });
    fs.writeFileSync(path.join(binDir, os.platform() === "win32" ? "python.exe" : "python"), "fake");
    fs.mkdirSync(path.join(tmpBase, "models"));
    for (const file of ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"]) {
      fs.writeFileSync(path.join(tmpBase, "models", file), "placeholder");
    }
    fs.writeFileSync(stateFile, JSON.stringify({
      kind: "ready",
      version: 1,
      runtime: ASR_PINNED_RUNTIME,
      model: ASR_PINNED_MODEL,
      revision: ASR_PINNED_REVISION,
    }));
    const spawnFn = vi.fn((_file: string, args: string[]) => {
      materializeMockVenv(args);
      return Promise.resolve({
        code: 0,
        stdout: args.includes("pip") || args.includes("venv") ? "" : "VERIFIED\n",
        stderr: "",
      });
    });

    const result = await runAsrInstallation({
      spawnFn,
      asrBase: tmpBase,
      modelKey: "small",
      devicePreference: "cpu",
    });

    expect(result.success).toBe(true);
    expect(spawnFn).toHaveBeenCalledTimes(3);
    expect(spawnFn.mock.calls[2][1]).toContain(path.join(tmpBase, "models"));
    const state = readAsrState(stateFile);
    expect(state.executionProfile).toEqual({ device: "cpu", computeType: "int8" });
    expect(state.migrationStatus).toBe("completed");
    fs.rmSync(tmpBase, { recursive: true, force: true });
  });

  it("keeps a same-model v1 state unchanged when the CPU probe fails", async () => {
    const tmpBase = fs.mkdtempSync(path.join(os.tmpdir(), "bilibili-mcp-asr-v1-fail-"));
    const stateFile = path.join(tmpBase, "state.json");
    const binDir = path.join(tmpBase, "venv", os.platform() === "win32" ? "Scripts" : "bin");
    fs.mkdirSync(binDir, { recursive: true });
    fs.writeFileSync(path.join(binDir, os.platform() === "win32" ? "python.exe" : "python"), "fake");
    fs.mkdirSync(path.join(tmpBase, "models"));
    for (const file of ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"]) {
      fs.writeFileSync(path.join(tmpBase, "models", file), "placeholder");
    }
    const previous = JSON.stringify({
      kind: "ready",
      version: 1,
      runtime: ASR_PINNED_RUNTIME,
      model: ASR_PINNED_MODEL,
      revision: ASR_PINNED_REVISION,
    });
    fs.writeFileSync(stateFile, previous);
    const spawnFn = vi.fn((_file: string, args: string[]) => {
      materializeMockVenv(args);
      if (args.includes("venv") || args.includes("pip")) {
        return Promise.resolve({ code: 0, stdout: "", stderr: "" });
      }
      return Promise.resolve({ code: 23, stdout: "FAILED:model_probe_failed\n", stderr: "probe failed" });
    });

    const result = await runAsrInstallation({
      spawnFn,
      asrBase: tmpBase,
      modelKey: "small",
      devicePreference: "cpu",
    });

    expect(result.success).toBe(false);
    expect(spawnFn).toHaveBeenCalledTimes(3);
    expect(fs.readFileSync(stateFile, "utf8")).toBe(previous);
    expect(readAsrState(stateFile).migrationStatus).toBe("pending");
    fs.rmSync(tmpBase, { recursive: true, force: true });
  });

  it("already-installed tiny reruns readiness with explicit modelKey", async () => {
    const tmpBase = path.join(os.tmpdir(), "bilibili-mcp-asr-p2-tidem-" + Date.now());
    fs.mkdirSync(tmpBase, { recursive: true });
    const stateFile = path.join(tmpBase, "state.json");
    const binDir = path.join(tmpBase, "venv", os.platform() === "win32" ? "Scripts" : "bin");
    fs.mkdirSync(binDir, { recursive: true });
    fs.writeFileSync(path.join(binDir, os.platform() === "win32" ? "python.exe" : "python"), "fake");
    const modelsDir = path.join(tmpBase, "models");
    fs.mkdirSync(modelsDir, { recursive: true });
    for (const f of ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"]) {
      fs.writeFileSync(path.join(modelsDir, f), "placeholder");
    }
    writeAsrState(stateFile, "tiny");

    const spawnFn = vi.fn((_file: string, args: string[]) => {
      materializeMockVenv(args);
      return Promise.resolve({
        code: 0,
        stdout: args.includes("pip") || args.includes("venv") ? "" : "VERIFIED\n",
        stderr: "",
      });
    });
    const result = await runAsrInstallation({
      spawnFn,
      asrBase: tmpBase,
      modelKey: "tiny",
      devicePreference: "cpu",
    });
    expect(result.success).toBe(true);
    expect(spawnFn).toHaveBeenCalledTimes(3);

    try { fs.rmSync(tmpBase, { recursive: true, force: true }); } catch { /* ok */ }
  });

  it("shows correct model size in progress message", async () => {
    const stages: string[] = [];
    let step = 0;
    const outputs = ["Python 3.12.0\n", "", "", "DOWNLOADED\n", "VERIFIED\n"];
    const spawnFn = vi.fn(() => Promise.resolve({ code: 0, stdout: outputs[step++] ?? "", stderr: "" }));
    const tmpBase = path.join(os.tmpdir(), "bilibili-mcp-asr-p2-size-" + Date.now());
    fs.mkdirSync(tmpBase, { recursive: true });
    const binDir = path.join(tmpBase, "venv", os.platform() === "win32" ? "Scripts" : "bin");
    fs.mkdirSync(binDir, { recursive: true });
    fs.writeFileSync(path.join(binDir, os.platform() === "win32" ? "python.exe" : "python"), "fake");
    const modelsDir = path.join(tmpBase, "models");
    fs.mkdirSync(modelsDir, { recursive: true });
    for (const f of ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"]) {
      fs.writeFileSync(path.join(modelsDir, f), "placeholder");
    }

    await runAsrInstallation({
      spawnFn, fsMkdirSync: fs.mkdirSync, asrBase: tmpBase, modelKey: "tiny",
      onStage: (s) => stages.push(s),
    });

    const downloadStage = stages.find((s) => s.includes("下载"));
    expect(downloadStage).toContain("78.2");
    expect(downloadStage).not.toContain("486");

    try { fs.rmSync(tmpBase, { recursive: true, force: true }); } catch { /* ok */ }
  });

  it("model-switch failure preserves the ready tiny state and model", async () => {
    const tmpBase = path.join(os.tmpdir(), "bilibili-mcp-asr-p2-swfail-" + Date.now());
    fs.mkdirSync(tmpBase, { recursive: true });
    const stateFile = path.join(tmpBase, "state.json");

    // Pre-create ready state for tiny
    const binDir = path.join(tmpBase, "venv", os.platform() === "win32" ? "Scripts" : "bin");
    fs.mkdirSync(binDir, { recursive: true });
    fs.writeFileSync(path.join(binDir, os.platform() === "win32" ? "python.exe" : "python"), "fake");
    const modelsDir = path.join(tmpBase, "models");
    fs.mkdirSync(modelsDir, { recursive: true });
    for (const f of ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"]) {
      fs.writeFileSync(path.join(modelsDir, f), "placeholder");
    }
    writeAsrState(stateFile, "tiny");
    expect(readAsrState(stateFile).kind).toBe("ready");
    const previousState = fs.readFileSync(stateFile, "utf8");
    const previousModel = fs.readFileSync(path.join(modelsDir, "model.bin"), "utf8");

    // Switch to small — pass discovery/venv/pip/download, fail verify
    let step = 0;
    const outputs = [
      "Python 3.12.0\n",
      "",                    // venv OK
      "",                    // pip OK
      "DOWNLOADED\n",        // download OK
      { code: 1, stdout: "", stderr: "model load failed" }, // verify FAILS
    ];
    const spawnFn = vi.fn((_file: string, args: string[]) => {
      const out = outputs[step++];
      if (typeof out === "string") return Promise.resolve({ code: 0, stdout: out, stderr: "" });
      return Promise.resolve(out);
    });

    const result = await runAsrInstallation({
      spawnFn, fsMkdirSync: fs.mkdirSync, asrBase: tmpBase, modelKey: "small",
      devicePreference: "cpu",
    });
    expect(result.success).toBe(false);
    expect(fs.readFileSync(stateFile, "utf8")).toBe(previousState);
    expect(fs.readFileSync(path.join(modelsDir, "model.bin"), "utf8")).toBe(previousModel);
    expect(readAsrState(stateFile)).toMatchObject({ kind: "ready", modelKey: "tiny" });

    try { fs.rmSync(tmpBase, { recursive: true, force: true }); } catch { /* ok */ }
  });

  it("invalid modelKey leaves all mutation functions untouched", async () => {
    const tmpBase = path.join(os.tmpdir(), "bilibili-mcp-asr-p2-untouch-" + Date.now());
    const unlockFn = vi.fn();
    const mkdirFn = vi.fn();
    const spawnFn = vi.fn();

    // At runtime, an invalid key passes through the catch block in runAsrInstallation
    const result = await runAsrInstallation({
      spawnFn, fsMkdirSync: mkdirFn, fsUnlinkSync: unlockFn, asrBase: tmpBase,
      modelKey: "large" as AsrModelKey,
    });

    expect(result.success).toBe(false);
    expect(result.error).toContain("Unknown ASR model key");
    // No mutation functions called before validation
    expect(unlockFn).not.toHaveBeenCalled();
    expect(mkdirFn).not.toHaveBeenCalled();
    expect(spawnFn).not.toHaveBeenCalled();

    try { fs.rmSync(tmpBase, { recursive: true, force: true }); } catch { /* ok */ }
  });
});

// ---------- Phase 2: allowlist order and validation ----------

describe("ASR_MODEL_SPECS order", () => {
  it("first entry is tiny", () => {
    expect(ASR_MODEL_SPECS[0].key).toBe("tiny");
  });

  it("second entry is base", () => {
    expect(ASR_MODEL_SPECS[1].key).toBe("base");
  });

  it("third entry is small", () => {
    expect(ASR_MODEL_SPECS[2].key).toBe("small");
  });

  it("has exactly three entries", () => {
    expect(ASR_MODEL_SPECS.length).toBe(3);
  });
});

describe("isAllowlistedModel cross-paired rejection", () => {
  it("rejects tiny repository with small revision", () => {
    expect(isAllowlistedModel(
      "Systran/faster-whisper-tiny",
      "536b0662742c02347bc0e980a01041f333bce120", // small revision
    )).toBe(false);
  });

  it("rejects base repository with tiny revision", () => {
    expect(isAllowlistedModel(
      "Systran/faster-whisper-base",
      "d90ca5fe260221311c53c58e660288d3deb8d356", // tiny revision
    )).toBe(false);
  });

  it("rejects small repository with base revision", () => {
    expect(isAllowlistedModel(
      "Systran/faster-whisper-small",
      "ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66", // base revision
    )).toBe(false);
  });
});

describe("resolveModelSpec rejects malicious/invalid keys", () => {
  it("rejects 'medium'", () => {
    expect(() => resolveModelSpec("medium" as any)).toThrow("Unknown ASR model key");
  });

  it("rejects URL-like input", () => {
    expect(() => resolveModelSpec("https://evil.com/model" as any)).toThrow("Unknown ASR model key");
  });

  it("rejects '../tiny'", () => {
    expect(() => resolveModelSpec("../tiny" as any)).toThrow("Unknown ASR model key");
  });

  it("rejects 'constructor'", () => {
    expect(() => resolveModelSpec("constructor" as any)).toThrow("Unknown ASR model key");
  });

  it("rejects '__proto__'", () => {
    expect(() => resolveModelSpec("__proto__" as any)).toThrow("Unknown ASR model key");
  });

});

describe("modelKeyForRepo", () => {
  it("returns 'tiny' for tiny repository+revision pair", () => {
    expect(modelKeyForRepo("Systran/faster-whisper-tiny", "d90ca5fe260221311c53c58e660288d3deb8d356")).toBe("tiny");
  });

  it("returns 'base' for base repository+revision pair", () => {
    expect(modelKeyForRepo("Systran/faster-whisper-base", "ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66")).toBe("base");
  });

  it("returns 'small' for small repository+revision pair", () => {
    expect(modelKeyForRepo("Systran/faster-whisper-small", "536b0662742c02347bc0e980a01041f333bce120")).toBe("small");
  });

  it("returns null for cross-paired repo+revision", () => {
    expect(modelKeyForRepo("Systran/faster-whisper-tiny", "536b0662742c02347bc0e980a01041f333bce120")).toBeNull();
  });

  it("returns null for unknown repository", () => {
    expect(modelKeyForRepo("evil/model", "deadbeef")).toBeNull();
  });
});

describe("readAsrState derived modelKey", () => {
  it("ready state includes derived modelKey for small", () => {
    const existsSync = vi.fn(() => true);
    const readFileSync = vi.fn(() =>
      JSON.stringify({
        kind: "ready",
        version: 1,
        runtime: ASR_PINNED_RUNTIME,
        model: ASR_PINNED_MODEL,
        revision: ASR_PINNED_REVISION,
      }),
    );
    const lstatSync = vi.fn(() => ({
      isSymbolicLink: () => false,
      isDirectory: () => true,
      isFile: () => true,
    }));
    const state = readAsrState("/tmp/asr/state.json", readFileSync, existsSync, lstatSync);
    expect(state.modelKey).toBe("small");
  });

  it("ready state includes derived modelKey for tiny", () => {
    const existsSync = vi.fn(() => true);
    const readFileSync = vi.fn(() =>
      JSON.stringify({
        kind: "ready",
        version: 1,
        runtime: ASR_PINNED_RUNTIME,
        model: "Systran/faster-whisper-tiny",
        revision: "d90ca5fe260221311c53c58e660288d3deb8d356",
      }),
    );
    const lstatSync = vi.fn(() => ({
      isSymbolicLink: () => false,
      isDirectory: () => true,
      isFile: () => true,
    }));
    const state = readAsrState("/tmp/asr/state.json", readFileSync, existsSync, lstatSync);
    expect(state.modelKey).toBe("tiny");
  });

  it("incomplete state has no modelKey", () => {
    // state file absent, but venv directory exists → incomplete
    const stateFile = "/tmp/asr/state.json";
    const venvDir = path.join(path.dirname(stateFile), "venv");
    const existsSync = vi.fn((p: string) => p === venvDir);
    const state = readAsrState(stateFile, fs.readFileSync, existsSync);
    expect(state.kind).toBe("incomplete");
    expect(state.modelKey).toBeUndefined();
  });

  it("not_installed state has no modelKey", () => {
    const existsSync = vi.fn(() => false);
    const state = readAsrState("/tmp/asr/state.json", fs.readFileSync, existsSync);
    expect(state.modelKey).toBeUndefined();
    expect(state.kind).toBe("not_installed");
  });
});

describe("ASR installer staging containment", () => {
  it("enforces file-count and byte budgets on the staged model tree", () => {
    const root = fs.mkdtempSync(
      path.join(os.tmpdir(), "bilibili-mcp-asr-tree-"),
    );
    try {
      fs.writeFileSync(path.join(root, "one.bin"), Buffer.alloc(6));
      fs.writeFileSync(path.join(root, "two.bin"), Buffer.alloc(5));

      expect(validateModelInstallTree(root, 11, 2)).toEqual({
        bytes: 11,
        files: 2,
      });
      expect(() => validateModelInstallTree(root, 10, 2)).toThrow(
        "storage budget",
      );
      expect(() => validateModelInstallTree(root, 11, 1)).toThrow(
        "storage budget",
      );
    } finally {
      fs.rmSync(root, { recursive: true, force: true });
    }
  });

  it("rejects symbolic links in the staged model tree", () => {
    const root = fs.mkdtempSync(
      path.join(os.tmpdir(), "bilibili-mcp-asr-link-"),
    );
    const outside = path.join(
      os.tmpdir(),
      `bilibili-mcp-asr-outside-${Date.now()}.bin`,
    );
    try {
      fs.writeFileSync(outside, "outside");
      try {
        fs.symlinkSync(outside, path.join(root, "linked.bin"), "file");
      } catch {
        return;
      }
      expect(() => validateModelInstallTree(root, 1024)).toThrow(
        "symbolic link",
      );
    } finally {
      fs.rmSync(root, { recursive: true, force: true });
      fs.rmSync(outside, { force: true });
    }
  });

  it("does not forward proxy, cloud, package-token, or credential variables", () => {
    const environment = buildAsrChildEnv({
      PATH: "safe-path",
      SYSTEMROOT: "safe-root",
      HTTPS_PROXY: "http://synthetic-proxy",
      HTTP_PROXY: "http://synthetic-proxy",
      NO_PROXY: "127.0.0.1",
      AWS_SECRET_ACCESS_KEY: "synthetic-secret",
      AZURE_CLIENT_SECRET: "synthetic-secret",
      GOOGLE_APPLICATION_CREDENTIALS: "synthetic-private-path",
      NPM_TOKEN: "synthetic-secret",
      HF_TOKEN: "synthetic-secret",
      BILIBILI_SESSDATA: "synthetic-secret",
    });

    expect(environment).toMatchObject({
      PATH: "safe-path",
      SYSTEMROOT: "safe-root",
      PIP_NO_INPUT: "1",
      PYTHONNOUSERSITE: "1",
    });
    const serialized = JSON.stringify(environment);
    expect(serialized).not.toContain("synthetic-secret");
    expect(serialized).not.toContain("synthetic-proxy");
    expect(serialized).not.toContain("synthetic-private-path");
  });
});

describe("runAsrInstallation device readiness", () => {
  function readyInstall(
    modelKey: AsrModelKey = "small",
    executionProfile = CPU_PROFILE,
  ): string {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "bilibili-mcp-asr-device-"));
    const binDir = path.join(root, "venv", process.platform === "win32" ? "Scripts" : "bin");
    fs.mkdirSync(binDir, { recursive: true });
    fs.writeFileSync(path.join(binDir, process.platform === "win32" ? "python.exe" : "python"), "fake");
    const modelDir = path.join(root, "models");
    fs.mkdirSync(modelDir, { recursive: true });
    for (const file of ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"]) {
      fs.writeFileSync(path.join(modelDir, file), `old-${modelKey}`);
    }
    writeAsrState(path.join(root, "state.json"), modelKey, { executionProfile });
    return root;
  }

  it("explicit CPU reruns only CPU readiness and saves cpu/int8", async () => {
    const root = readyInstall();
    const profiles: string[] = [];
    const spawnFn = vi.fn((_file: string, args: string[]) => {
      materializeMockVenv(args);
      if (args.includes("venv")) return Promise.resolve({ code: 0, stdout: "", stderr: "" });
      if (args.includes("pip")) return Promise.resolve({ code: 0, stdout: "", stderr: "" });
      profiles.push(args.slice(-2).join("/"));
      return Promise.resolve({ code: 0, stdout: "VERIFIED\n", stderr: "" });
    });

    try {
      const result = await runAsrInstallation({
        asrBase: root,
        devicePreference: "cpu",
        spawnFn,
      });

      expect(result).toMatchObject({
        success: true,
        executionProfile: CPU_PROFILE,
      });
      expect(profiles).toEqual(["cpu/int8"]);
      expect(readAsrState(path.join(root, "state.json")).executionProfile).toEqual(CPU_PROFILE);
    } finally {
      fs.rmSync(root, { recursive: true, force: true });
    }
  });

  it("uses an explicit Python override to rebuild a ready same-model runtime", async () => {
    const root = readyInstall();
    const override = "/synthetic/python";
    const spawnFn = vi.fn((file: string, args: string[]) => {
      materializeMockVenv(args);
      if (file === override && args.includes("--version")) {
        return Promise.resolve({ code: 0, stdout: "Python 3.12.0\n", stderr: "" });
      }
      if (args.includes("venv") || args.includes("pip")) {
        return Promise.resolve({ code: 0, stdout: "", stderr: "" });
      }
      return Promise.resolve({ code: 0, stdout: "VERIFIED\n", stderr: "" });
    });

    try {
      const result = await runAsrInstallation({
        asrBase: root,
        pythonOverride: override,
        devicePreference: "cpu",
        spawnFn,
      });

      expect(result.success).toBe(true);
      expect(spawnFn).toHaveBeenCalledWith(override, ["-I", "--version"]);
      expect(spawnFn.mock.calls.some(([file, args]) =>
        file === override && args.includes("venv"),
      )).toBe(true);
    } finally {
      fs.rmSync(root, { recursive: true, force: true });
    }
  });

  it("uses an explicit Python override while staging a ready model switch", async () => {
    const root = readyInstall("tiny");
    const override = "/synthetic/python";
    const spawnFn = vi.fn((file: string, args: string[]) => {
      materializeMockVenv(args);
      if (file === override && args.includes("--version")) {
        return Promise.resolve({ code: 0, stdout: "Python 3.12.0\n", stderr: "" });
      }
      if (args.includes("venv") || args.includes("pip")) {
        return Promise.resolve({ code: 0, stdout: "", stderr: "" });
      }
      if (args.some((arg) => arg.includes("snapshot_download"))) {
        const staging = args.find((arg) => arg.includes(".models-staging-"));
        if (!staging) throw new Error("missing staging path");
        for (const fileName of ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"]) {
          fs.writeFileSync(path.join(staging, fileName), `new-${fileName}`);
        }
        return Promise.resolve({ code: 0, stdout: "DOWNLOADED\n", stderr: "" });
      }
      return Promise.resolve({ code: 0, stdout: "VERIFIED\n", stderr: "" });
    });

    try {
      const result = await runAsrInstallation({
        asrBase: root,
        modelKey: "small",
        pythonOverride: override,
        devicePreference: "cpu",
        spawnFn,
      });

      expect(result.success).toBe(true);
      expect(spawnFn).toHaveBeenCalledWith(override, ["-I", "--version"]);
      expect(spawnFn.mock.calls.some(([file, args]) =>
        file === override && args.includes("venv"),
      )).toBe(true);
      expect(readAsrState(path.join(root, "state.json")).modelKey).toBe("small");
    } finally {
      fs.rmSync(root, { recursive: true, force: true });
    }
  });

  it("labels an explicit CPU probe failure as CPU readiness", async () => {
    const root = readyInstall();
    const spawnFn = vi.fn((_file: string, args: string[]) => {
      materializeMockVenv(args);
      if (args.includes("venv") || args.includes("pip")) {
        return Promise.resolve({ code: 0, stdout: "", stderr: "" });
      }
      return Promise.resolve({
        code: 23,
        stdout: "FAILED:model_probe_failed\n",
        stderr: "private CPU error",
      });
    });

    try {
      const result = await runAsrInstallation({
        asrBase: root,
        devicePreference: "cpu",
        spawnFn,
      });

      expect(result).toMatchObject({
        success: false,
        failureCategory: "model_probe_failed",
        failureDevice: "cpu",
      });
      expect(result.gpuFailureCategory).toBeUndefined();
      expect(JSON.stringify(result)).not.toContain("private CPU error");
    } finally {
      fs.rmSync(root, { recursive: true, force: true });
    }
  });

  it("auto saves CUDA when the real GPU probe succeeds", async () => {
    const root = readyInstall();
    const profiles: string[] = [];
    const spawnFn = vi.fn((_file: string, args: string[]) => {
      materializeMockVenv(args);
      if (args.includes("venv")) return Promise.resolve({ code: 0, stdout: "", stderr: "" });
      if (args.includes("pip")) return Promise.resolve({ code: 0, stdout: "", stderr: "" });
      profiles.push(args.slice(-2).join("/"));
      return Promise.resolve({ code: 0, stdout: "VERIFIED\n", stderr: "" });
    });

    try {
      const result = await runAsrInstallation({ asrBase: root, spawnFn });
      expect(result).toMatchObject({ success: true, executionProfile: CUDA_PROFILE });
      expect(profiles).toEqual(["cuda/float16"]);
      expect(readAsrState(path.join(root, "state.json")).executionProfile).toEqual(CUDA_PROFILE);
    } finally {
      fs.rmSync(root, { recursive: true, force: true });
    }
  });

  it("reports success when post-publication runtime backup cleanup fails", async () => {
    const root = readyInstall();
    const spawnFn = vi.fn((_file: string, args: string[]) => {
      materializeMockVenv(args);
      if (args.includes("venv") || args.includes("pip")) {
        return Promise.resolve({ code: 0, stdout: "", stderr: "" });
      }
      return Promise.resolve({ code: 0, stdout: "VERIFIED\n", stderr: "" });
    });
    const originalRmSync = fs.rmSync.bind(fs);
    const rmSpy = vi.spyOn(fs, "rmSync").mockImplementation((candidate, options) => {
      if (String(candidate).includes(".venv-backup-")) {
        throw new Error("cleanup denied");
      }
      return originalRmSync(candidate, options);
    });

    try {
      const result = await runAsrInstallation({
        asrBase: root,
        devicePreference: "cpu",
        spawnFn,
      });

      expect(result).toMatchObject({ success: true, executionProfile: CPU_PROFILE });
      expect(readAsrState(path.join(root, "state.json"))).toMatchObject({
        kind: "ready",
        executionProfile: CPU_PROFILE,
      });
    } finally {
      rmSpy.mockRestore();
      originalRmSync(root, { recursive: true, force: true });
    }
  });

  it("auto records a sanitized category only after CPU fallback also succeeds", async () => {
    const root = readyInstall();
    const profiles: string[] = [];
    const spawnFn = vi.fn((_file: string, args: string[]) => {
      materializeMockVenv(args);
      if (args.includes("venv")) return Promise.resolve({ code: 0, stdout: "", stderr: "" });
      if (args.includes("pip")) return Promise.resolve({ code: 0, stdout: "", stderr: "" });
      const profile = args.slice(-2).join("/");
      profiles.push(profile);
      return profile === "cuda/float16"
        ? Promise.resolve({
            code: 21,
            stdout: "FAILED:cuda_runtime_missing\n",
            stderr: "raw C:\\private\\cublas.dll TOKEN=secret",
          })
        : Promise.resolve({ code: 0, stdout: "VERIFIED\n", stderr: "" });
    });

    try {
      const result = await runAsrInstallation({ asrBase: root, spawnFn });
      expect(result).toMatchObject({
        success: true,
        executionProfile: CPU_PROFILE,
        failureCategory: "cuda_runtime_missing",
      });
      expect(profiles).toEqual(["cuda/float16", "cpu/int8"]);
      expect(readAsrState(path.join(root, "state.json"))).toMatchObject({
        executionProfile: CPU_PROFILE,
        failureCategory: "cuda_runtime_missing",
      });
      expect(JSON.stringify(result)).not.toContain("private");
      expect(JSON.stringify(result)).not.toContain("TOKEN");
    } finally {
      fs.rmSync(root, { recursive: true, force: true });
    }
  });

  it("keeps both sanitized categories when auto GPU and CPU probes fail", async () => {
    const root = readyInstall();
    const previous = fs.readFileSync(path.join(root, "state.json"), "utf8");
    const profiles: string[] = [];
    const spawnFn = vi.fn((_file: string, args: string[]) => {
      materializeMockVenv(args);
      if (args.includes("venv") || args.includes("pip")) {
        return Promise.resolve({ code: 0, stdout: "", stderr: "" });
      }
      const profile = args.slice(-2).join("/");
      profiles.push(profile);
      return profile === "cuda/float16"
        ? Promise.resolve({ code: 21, stdout: "FAILED:cuda_runtime_missing\n", stderr: "private GPU" })
        : Promise.resolve({ code: 23, stdout: "FAILED:model_probe_failed\n", stderr: "private CPU" });
    });

    try {
      const result = await runAsrInstallation({ asrBase: root, spawnFn });
      expect(result).toMatchObject({
        success: false,
        failureCategory: "model_probe_failed",
        failureDevice: "cpu",
        gpuFailureCategory: "cuda_runtime_missing",
      });
      expect(profiles).toEqual(["cuda/float16", "cpu/int8"]);
      expect(fs.readFileSync(path.join(root, "state.json"), "utf8")).toBe(previous);
      expect(JSON.stringify(result)).not.toContain("private GPU");
      expect(JSON.stringify(result)).not.toContain("private CPU");
    } finally {
      fs.rmSync(root, { recursive: true, force: true });
    }
  });

  it("explicit CUDA failure preserves the prior verified state without CPU fallback", async () => {
    const root = readyInstall();
    const previous = fs.readFileSync(path.join(root, "state.json"), "utf8");
    const runtimeMarker = path.join(root, "venv", "runtime-marker.txt");
    fs.writeFileSync(runtimeMarker, "previous-runtime");
    const profiles: string[] = [];
    const pipExecutables: string[] = [];
    const spawnFn = vi.fn((file: string, args: string[]) => {
      if (args.includes("venv")) return Promise.resolve({ code: 0, stdout: "", stderr: "" });
      if (args.includes("pip")) {
        pipExecutables.push(file);
        return Promise.resolve({ code: 0, stdout: "", stderr: "" });
      }
      profiles.push(args.slice(-2).join("/"));
      return Promise.resolve({
        code: 20,
        stdout: "FAILED:no_nvidia_gpu\n",
        stderr: "raw private details",
      });
    });

    try {
      const result = await runAsrInstallation({
        asrBase: root,
        devicePreference: "cuda",
        spawnFn,
      });
      expect(result).toMatchObject({ success: false, failureCategory: "no_nvidia_gpu" });
      expect(profiles).toEqual(["cuda/float16"]);
      expect(pipExecutables).toHaveLength(1);
      expect(pipExecutables[0]).toContain(".venv-staging-");
      expect(fs.readFileSync(runtimeMarker, "utf8")).toBe("previous-runtime");
      expect(fs.readFileSync(path.join(root, "state.json"), "utf8")).toBe(previous);
      expect(JSON.stringify(result)).not.toContain("private");
    } finally {
      fs.rmSync(root, { recursive: true, force: true });
    }
  });

  it("rejects an invalid device preference before subprocess or mutation", async () => {
    const root = readyInstall();
    const previous = fs.readFileSync(path.join(root, "state.json"), "utf8");
    const spawnFn = vi.fn();

    try {
      const result = await runAsrInstallation({
        asrBase: root,
        devicePreference: "gpu" as never,
        spawnFn,
      });
      expect(result.success).toBe(false);
      expect(spawnFn).not.toHaveBeenCalled();
      expect(fs.readFileSync(path.join(root, "state.json"), "utf8")).toBe(previous);
    } finally {
      fs.rmSync(root, { recursive: true, force: true });
    }
  });

  it("model-switch CUDA failure keeps the previous model and profile", async () => {
    const root = readyInstall("tiny");
    const stateFile = path.join(root, "state.json");
    const previousState = fs.readFileSync(stateFile, "utf8");
    const oldModel = fs.readFileSync(path.join(root, "models", "model.bin"), "utf8");
    const runtimeMarker = path.join(root, "venv", "runtime-marker.txt");
    fs.writeFileSync(runtimeMarker, "previous-runtime");
    const pipExecutables: string[] = [];
    const spawnFn = vi.fn((file: string, args: string[]) => {
      if (args.includes("--version")) return Promise.resolve({ code: 0, stdout: "Python 3.12.0\n", stderr: "" });
      if (args.includes("venv")) return Promise.resolve({ code: 0, stdout: "", stderr: "" });
      if (args.includes("pip")) {
        pipExecutables.push(file);
        return Promise.resolve({ code: 0, stdout: "", stderr: "" });
      }
      if (args.some((arg) => arg.includes("snapshot_download"))) {
        return Promise.resolve({ code: 0, stdout: "DOWNLOADED\n", stderr: "" });
      }
      if (args.slice(-2).join("/") === "cuda/float16") {
        return Promise.resolve({ code: 21, stdout: "FAILED:cuda_runtime_missing\n", stderr: "private" });
      }
      return Promise.resolve({ code: 0, stdout: "", stderr: "" });
    });

    try {
      const result = await runAsrInstallation({
        asrBase: root,
        modelKey: "small",
        devicePreference: "cuda",
        spawnFn,
      });
      expect(result).toMatchObject({ success: false, failureCategory: "cuda_runtime_missing" });
      expect(fs.readFileSync(stateFile, "utf8")).toBe(previousState);
      expect(fs.readFileSync(path.join(root, "models", "model.bin"), "utf8")).toBe(oldModel);
      expect(fs.readFileSync(runtimeMarker, "utf8")).toBe("previous-runtime");
      expect(pipExecutables).toHaveLength(1);
      expect(pipExecutables[0]).toContain(".venv-staging-");
      expect(readAsrState(stateFile).modelKey).toBe("tiny");
    } finally {
      fs.rmSync(root, { recursive: true, force: true });
    }
  });

  it("does not publish CPU fallback when the GPU probe WAV cannot be removed", async () => {
    const root = readyInstall();
    const stateFile = path.join(root, "state.json");
    const previousState = fs.readFileSync(stateFile, "utf8");
    const profiles: string[] = [];
    let orphanedProbe = "";
    const originalUnlinkSync = fs.unlinkSync.bind(fs);
    const unlinkSpy = vi.spyOn(fs, "unlinkSync").mockImplementation((candidate) => {
      const probe = String(candidate);
      if (
        orphanedProbe === "" &&
        path.basename(probe).startsWith(".bilibili-mcp-asr-probe-")
      ) {
        orphanedProbe = probe;
        throw new Error("cleanup denied");
      }
      return originalUnlinkSync(candidate);
    });
    const spawnFn = vi.fn((_file: string, args: string[]) => {
      materializeMockVenv(args);
      if (args.includes("venv") || args.includes("pip")) {
        return Promise.resolve({ code: 0, stdout: "", stderr: "" });
      }
      profiles.push(args.slice(-2).join("/"));
      return Promise.resolve({ code: 0, stdout: "VERIFIED\n", stderr: "" });
    });

    try {
      const result = await runAsrInstallation({ asrBase: root, spawnFn });

      expect(result).toMatchObject({
        success: false,
        failureCategory: "model_probe_failed",
        failureDevice: "cuda",
      });
      expect(profiles).toEqual(["cuda/float16"]);
      expect(fs.readFileSync(stateFile, "utf8")).toBe(previousState);
      expect(orphanedProbe).not.toBe("");
      expect(fs.existsSync(orphanedProbe)).toBe(true);
    } finally {
      unlinkSpy.mockRestore();
      if (orphanedProbe && fs.existsSync(orphanedProbe)) {
        originalUnlinkSync(orphanedProbe);
      }
      fs.rmSync(root, { recursive: true, force: true });
    }
  });

  it("fails closed when state publication and model rollback both fail", async () => {
    const root = readyInstall("tiny");
    const stateFile = path.join(root, "state.json");
    const modelDir = path.join(root, "models");
    let statePublicationFailed = false;
    const originalRenameSync = fs.renameSync.bind(fs);
    const originalRmSync = fs.rmSync.bind(fs);
    const renameSpy = vi.spyOn(fs, "renameSync").mockImplementation((source, destination) => {
      if (
        path.dirname(String(source)) === root &&
        path.basename(String(source)).startsWith(".state-") &&
        path.extname(String(source)) === ".tmp" &&
        String(destination) === stateFile
      ) {
        statePublicationFailed = true;
        throw new Error("state publication denied");
      }
      return originalRenameSync(source, destination);
    });
    const rmSpy = vi.spyOn(fs, "rmSync").mockImplementation((candidate, options) => {
      if (statePublicationFailed && String(candidate) === modelDir) {
        throw new Error("model rollback denied");
      }
      return originalRmSync(candidate, options);
    });
    const spawnFn = vi.fn((_file: string, args: string[]) => {
      materializeMockVenv(args);
      if (args.includes("venv") || args.includes("pip")) {
        return Promise.resolve({ code: 0, stdout: "", stderr: "" });
      }
      if (args.some((arg) => arg.includes("snapshot_download"))) {
        const staging = args.find((arg) => arg.includes(".models-staging-"));
        if (!staging) throw new Error("missing staging path");
        for (const file of ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"]) {
          fs.writeFileSync(path.join(staging, file), `new-small-${file}`);
        }
        return Promise.resolve({ code: 0, stdout: "DOWNLOADED\n", stderr: "" });
      }
      return Promise.resolve({ code: 0, stdout: "VERIFIED\n", stderr: "" });
    });

    try {
      const result = await runAsrInstallation({
        asrBase: root,
        modelKey: "small",
        devicePreference: "cuda",
        spawnFn,
      });

      expect(result).toMatchObject({
        success: false,
        error: "ASR setup failed and the previous installation could not be restored",
      });
      expect(fs.existsSync(stateFile)).toBe(false);
      expect(readAsrState(stateFile).kind).toBe("incomplete");
      expect(fs.readFileSync(path.join(modelDir, "model.bin"), "utf8")).toBe(
        "new-small-model.bin",
      );
      expect(
        fs.readdirSync(root).some((entry) => entry.startsWith(".state-backup-")),
      ).toBe(true);
    } finally {
      renameSpy.mockRestore();
      rmSpy.mockRestore();
      originalRmSync(root, { recursive: true, force: true });
    }
  });

  it("keeps the old runtime when its backup rename fails", async () => {
    const root = readyInstall();
    const stateFile = path.join(root, "state.json");
    const runtimeMarker = path.join(root, "venv", "runtime-marker.txt");
    const previousState = fs.readFileSync(stateFile, "utf8");
    fs.writeFileSync(runtimeMarker, "previous-runtime");
    const originalRenameSync = fs.renameSync.bind(fs);
    const renameSpy = vi.spyOn(fs, "renameSync").mockImplementation((source, destination) => {
      if (
        String(source) === path.join(root, "venv") &&
        path.basename(String(destination)).startsWith(".venv-backup-")
      ) {
        throw new Error("runtime backup denied");
      }
      return originalRenameSync(source, destination);
    });
    const spawnFn = vi.fn((_file: string, args: string[]) => {
      materializeMockVenv(args);
      if (args.includes("venv") || args.includes("pip")) {
        return Promise.resolve({ code: 0, stdout: "", stderr: "" });
      }
      return Promise.resolve({ code: 0, stdout: "VERIFIED\n", stderr: "" });
    });

    try {
      const result = await runAsrInstallation({
        asrBase: root,
        devicePreference: "cpu",
        spawnFn,
      });

      expect(result.success).toBe(false);
      expect(fs.readFileSync(runtimeMarker, "utf8")).toBe("previous-runtime");
      expect(fs.readFileSync(stateFile, "utf8")).toBe(previousState);
      expect(readAsrState(stateFile).kind).toBe("ready");
    } finally {
      renameSpy.mockRestore();
      fs.rmSync(root, { recursive: true, force: true });
    }
  });
});
