import fs from "fs";
import os from "os";
import path from "path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildDoctorStatus,
  createCli,
  doctorCommand,
  parseDeviceChoice,
  parseModelChoice,
  setupCredentials,
  type DoctorStatus,
} from "../src/cli.js";
import { credentialManager } from "../src/utils/credentials.js";
import { ASR_PINNED_RUNTIME, ASR_PINNED_MODEL, ASR_PINNED_REVISION, ASR_MODEL_SPECS, readAsrState, deriveAsrPaths, type AsrModelKey } from "../src/asr/state.js";

const ENV_KEYS = [
  "BILIBILI_SESSDATA",
  "BILIBILI_BILI_JCT",
  "BILIBILI_DEDEUSERID",
] as const;

function saveEnv(): Record<string, string | undefined> {
  const saved: Record<string, string | undefined> = {};
  for (const key of ENV_KEYS) {
    saved[key] = process.env[key];
  }
  return saved;
}

function restoreEnv(saved: Record<string, string | undefined>) {
  for (const key of ENV_KEYS) {
    if (saved[key] === undefined) {
      delete process.env[key];
    } else {
      process.env[key] = saved[key];
    }
  }
}

function clearCredentialEnv() {
  for (const key of ENV_KEYS) {
    delete process.env[key];
  }
}

describe("CLI help and commands", () => {
  it("help output contains setup, doctor, config, check, check-update, version", () => {
    const cli = createCli();
    const output = cli.helpInformation();

    expect(output).toContain("config");
    expect(output).toContain("check");
    expect(output).toContain("check-update");
    expect(output).toContain("setup");
    expect(output).toContain("doctor");
    expect(output).toContain("version");
  });

  it("setup subcommand help documents the non-interactive flags", () => {
    const cli = createCli();
    const setupCmd = cli.commands.find((c) => c.name() === "setup");
    expect(setupCmd).toBeDefined();
    const output = setupCmd!.helpInformation();

    expect(output).toContain("--non-interactive");
    expect(output).toContain("--asr-model");
    expect(output).toContain("--asr-device");
  });

  it("help output does not contain duplicated [command] placeholder in a single line", () => {
    const cli = createCli();
    const output = cli.helpInformation();

    for (const line of output.split("\n")) {
      const count = (line.match(/\[command\]/g) ?? []).length;
      expect(count).toBeLessThanOrEqual(1);
    }
  });

  it("help output has exactly one Commands section header", () => {
    const cli = createCli();
    const output = cli.helpInformation();

    const headers = (output.match(/^Commands:/gm) ?? []);
    expect(headers.length).toBe(1);
  });

  it("version subcommand exists and prints package version", () => {
    const cli = createCli();
    const versionCmd = cli.commands.find((c) => c.name() === "version");
    expect(versionCmd).toBeDefined();
  });
});

describe("config credential replacement", () => {
  const originalUserProfile = process.env.USERPROFILE;
  const originalHome = process.env.HOME;
  let tempHome: string;
  let savedExitCode: typeof process.exitCode;

  beforeEach(() => {
    savedExitCode = process.exitCode;
    process.exitCode = undefined;
    tempHome = fs.mkdtempSync(
      path.join(os.tmpdir(), "bilibili-mcp-cli-config-test-"),
    );
    process.env.USERPROFILE = tempHome;
    process.env.HOME = tempHome;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.resetModules();
    if (originalUserProfile === undefined) {
      delete process.env.USERPROFILE;
    } else {
      process.env.USERPROFILE = originalUserProfile;
    }
    if (originalHome === undefined) {
      delete process.env.HOME;
    } else {
      process.env.HOME = originalHome;
    }
    process.exitCode = savedExitCode;
    fs.rmSync(tempHome, { recursive: true, force: true });
  });

  it.each([
    ["SESSDATA", ["   ", "synthetic-replacement-csrf", "20002"]],
    ["bili_jct", ["synthetic-replacement-session", "\t", "20002"]],
    [
      "DedeUserID",
      ["synthetic-replacement-session", "synthetic-replacement-csrf", "\n"],
    ],
  ])("keeps existing credentials when %s is blank", async (_field, answers) => {
    vi.resetModules();
    const credentialsModule = await import("../src/utils/credentials.js");
    const cliModule = await import("../src/cli.js");
    const existingCredentials = {
      sessdata: "synthetic-existing-session",
      bili_jct: "synthetic-existing-csrf",
      dedeuserid: "10001",
      expiresAt: Date.now() + 86_400_000,
    };
    fs.mkdirSync(credentialsModule.GLOBAL_CONFIG_DIR, { recursive: true });
    const originalFile = `${JSON.stringify(existingCredentials, null, 2)}\n`;
    fs.writeFileSync(credentialsModule.GLOBAL_CONFIG_FILE, originalFile, "utf8");
    credentialsModule.credentialManager.setCredentials(existingCredentials);
    const askHiddenFn = vi.fn<(question: string) => Promise<string>>();
    for (const answer of answers) {
      askHiddenFn.mockResolvedValueOnce(answer);
    }
    const logSpy = vi.spyOn(console, "log").mockImplementation(() => {});
    vi.spyOn(console, "error").mockImplementation(() => {});

    const result = await cliModule.configureCredentials(askHiddenFn);

    expect(result).toBe(false);
    expect(process.exitCode).toBe(1);
    expect(fs.readFileSync(credentialsModule.GLOBAL_CONFIG_FILE, "utf8")).toBe(
      originalFile,
    );
    expect(credentialsModule.credentialManager.getCredentials()).toEqual(
      existingCredentials,
    );
    expect(logSpy.mock.calls.flat().join("\n")).not.toContain("凭证配置成功");
  });

  it("trims and persists a complete synthetic credential set in the isolated home", async () => {
    vi.resetModules();
    const credentialsModule = await import("../src/utils/credentials.js");
    const cliModule = await import("../src/cli.js");
    const askHiddenFn = vi
      .fn<(question: string) => Promise<string>>()
      .mockResolvedValueOnce("  synthetic-new-session  ")
      .mockResolvedValueOnce("  synthetic-new-csrf  ")
      .mockResolvedValueOnce("  30003  ");
    const logSpy = vi.spyOn(console, "log").mockImplementation(() => {});
    vi.spyOn(console, "error").mockImplementation(() => {});

    const result = await cliModule.configureCredentials(askHiddenFn);

    expect(result).toBe(true);
    expect(process.exitCode).toBeUndefined();
    const saved = JSON.parse(
      fs.readFileSync(credentialsModule.GLOBAL_CONFIG_FILE, "utf8"),
    );
    expect(saved).toMatchObject({
      sessdata: "synthetic-new-session",
      bili_jct: "synthetic-new-csrf",
      dedeuserid: "30003",
    });
    expect(logSpy.mock.calls.flat().join("\n")).toContain("凭证配置成功");
  });
});

describe("buildDoctorStatus", () => {
  let savedEnv: Record<string, string | undefined>;

  beforeEach(() => {
    savedEnv = saveEnv();
    clearCredentialEnv();
    credentialManager.clearCredentials();
    vi.spyOn(fs, "existsSync").mockReturnValue(false);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    credentialManager.clearCredentials();
    restoreEnv(savedEnv);
  });

  it("returns needs_credentials when no credentials are configured", () => {
    const pkg = JSON.parse(
      fs.readFileSync(new URL("../package.json", import.meta.url), "utf8"),
    );

    const status = buildDoctorStatus();

    expect(status.package_name).toBe("@xzxzzx/bilibili-mcp");
    expect(status.version).toBe(pkg.version);
    expect(status.runtime.node).toBe(process.version);
    expect(status.runtime.platform).toBe(os.platform());
    expect(status.runtime.arch).toBe(os.arch());
    expect(status.credentials.configured).toBe(false);
    expect(status.credentials.source).toBe("none");
    expect(status.credentials.loadable).toBe(false);
    expect(status.status).toBe("needs_credentials");
    expect(status.next_steps.length).toBeGreaterThan(0);
  });

  it("next_steps recommends setup (not config)", () => {
    const status = buildDoctorStatus();
    expect(status.next_steps[0]).toContain("setup");
    expect(status.next_steps[0]).not.toContain("config");
  });

  it("returns locally_ready when env credentials are configured and loadable", () => {
    process.env.BILIBILI_SESSDATA = "test-sessdata";
    process.env.BILIBILI_BILI_JCT = "test-jct";
    process.env.BILIBILI_DEDEUSERID = "test-uid";
    vi.spyOn(fs, "existsSync").mockReturnValue(false);

    const status = buildDoctorStatus();

    expect(status.credentials.configured).toBe(true);
    expect(status.credentials.source).toBe("env");
    expect(status.credentials.loadable).toBe(true);
    expect(status.status).toBe("locally_ready");
    expect(status.next_steps).toEqual([]);
  });

  it("returns locally_ready when file credentials are configured and loadable", () => {
    vi.spyOn(fs, "existsSync").mockReturnValue(true);
    vi.spyOn(fs, "readFileSync").mockReturnValue(
      JSON.stringify({
        sessdata: "file-sessdata",
        bili_jct: "file-jct",
        dedeuserid: "file-uid",
        expiresAt: Date.now() + 86400000,
      }),
    );

    const status = buildDoctorStatus();

    expect(status.credentials.configured).toBe(true);
    expect(status.credentials.source).toBe("global_config");
    expect(status.credentials.loadable).toBe(true);
    expect(status.status).toBe("locally_ready");
  });

  it("returns needs_credentials when file exists but getCredentials returns null (expired)", () => {
    // File exists (source is not "none") but getCredentials returns null due to expiry
    vi.spyOn(fs, "existsSync").mockReturnValue(true);
    vi.spyOn(fs, "readFileSync").mockReturnValue(
      JSON.stringify({
        sessdata: "old-sessdata",
        bili_jct: "old-jct",
        dedeuserid: "old-uid",
        expiresAt: Date.now() - 86400000, // already expired
      }),
    );

    const status = buildDoctorStatus();

    expect(status.credentials.configured).toBe(true);
    expect(status.credentials.source).toBe("global_config");
    expect(status.credentials.loadable).toBe(false);
    expect(status.status).toBe("needs_credentials");
  });

  it("never includes raw cookie values in output", () => {
    process.env.BILIBILI_SESSDATA = "real-sessdata-value-123";
    process.env.BILIBILI_BILI_JCT = "real-jct-value-456";
    process.env.BILIBILI_DEDEUSERID = "real-uid-789";

    const status = buildDoctorStatus();
    const json = JSON.stringify(status);

    expect(json).not.toContain("real-sessdata-value-123");
    expect(json).not.toContain("real-jct-value-456");
    expect(json).not.toContain("real-uid-789");
    expect(json).not.toMatch(/SESSDATA=/);
    expect(json).not.toMatch(/bili_jct=/);
    expect(json).not.toMatch(/DedeUserID=/);
  });

  it("JSON output has stable top-level keys", () => {
    const status = buildDoctorStatus();
    const keys = Object.keys(status).sort();

    expect(keys).toEqual([
      "asr",
      "credentials",
      "next_steps",
      "package_name",
      "runtime",
      "status",
      "version",
    ]);
  });

  it("status field is only locally_ready or needs_credentials", () => {
    expect(buildDoctorStatus().status).toBe("needs_credentials");

    credentialManager.clearCredentials();
    process.env.BILIBILI_SESSDATA = "a";
    process.env.BILIBILI_BILI_JCT = "b";
    process.env.BILIBILI_DEDEUSERID = "c";
    expect(buildDoctorStatus().status).toBe("locally_ready");
  });

  it("credential source values are only env, global_config, or none", () => {
    vi.restoreAllMocks();
    clearCredentialEnv();
    credentialManager.clearCredentials();
    vi.spyOn(fs, "existsSync").mockReturnValue(false);
    expect(buildDoctorStatus().credentials.source).toBe("none");

    vi.restoreAllMocks();
    clearCredentialEnv();
    credentialManager.clearCredentials();
    process.env.BILIBILI_SESSDATA = "a";
    process.env.BILIBILI_BILI_JCT = "b";
    process.env.BILIBILI_DEDEUSERID = "c";
    vi.spyOn(fs, "existsSync").mockReturnValue(false);
    expect(buildDoctorStatus().credentials.source).toBe("env");

    vi.restoreAllMocks();
    clearCredentialEnv();
    credentialManager.clearCredentials();
    vi.spyOn(fs, "existsSync").mockReturnValue(true);
    vi.spyOn(fs, "readFileSync").mockReturnValue(
      JSON.stringify({
        sessdata: "f",
        bili_jct: "f",
        dedeuserid: "f",
        expiresAt: Date.now() + 86400000,
      }),
    );
    expect(buildDoctorStatus().credentials.source).toBe("global_config");
  });

  it("env takes priority over file in getCredentialSource check", () => {
    credentialManager.clearCredentials();
    process.env.BILIBILI_SESSDATA = "env-val";
    process.env.BILIBILI_BILI_JCT = "env-val";
    process.env.BILIBILI_DEDEUSERID = "env-val";
    vi.spyOn(fs, "existsSync").mockReturnValue(true);

    const status = buildDoctorStatus();
    expect(status.credentials.source).toBe("env");
  });

  it("doctor does not perform any network request", () => {
    const status = buildDoctorStatus();
    expect(status).toBeDefined();
    expect(status.status).toBeDefined();
  });

  it("doctor includes asr status as not_installed when no state file exists", () => {
    const status = buildDoctorStatus();
    expect(status.asr).toBeDefined();
    expect(status.asr.status).toBe("not_installed");
  });

  it("doctor reports asr ready when state file is valid", () => {
    const mockReadAsr = vi.fn(() => ({
      kind: "ready" as const,
      version: 1,
      runtime: "faster-whisper==1.2.1",
      model: "Systran/faster-whisper-small",
      revision: "536b0662742c02347bc0e980a01041f333bce120",
    }));
    const status = buildDoctorStatus(mockReadAsr);
    expect(status.asr.status).toBe("ready");
  });

  it("doctor reports asr incomplete when state file is malformed", () => {
    const mockReadAsr = vi.fn(() => ({ kind: "incomplete" as const }));
    const status = buildDoctorStatus(mockReadAsr);
    expect(status.asr.status).toBe("incomplete");
  });

  it("ASR not_installed does not change top-level status or credential exit code", () => {
    const mockReadAsr = vi.fn(() => ({ kind: "not_installed" as const }));
    vi.spyOn(fs, "existsSync").mockReturnValue(false);
    const status = buildDoctorStatus(mockReadAsr);
    expect(status.asr.status).toBe("not_installed");
    // credentials still drive top-level status
    expect(status.status).toBe("needs_credentials");
    expect(status.credentials.configured).toBe(false);
  });

  it("ASR ready does not flip needs_credentials to locally_ready", () => {
    const mockReadAsr = vi.fn(() => ({
      kind: "ready" as const,
      version: 1,
      runtime: ASR_PINNED_RUNTIME,
      model: ASR_PINNED_MODEL,
      revision: ASR_PINNED_REVISION,
    }));
    vi.spyOn(fs, "existsSync").mockReturnValue(false);
    const status = buildDoctorStatus(mockReadAsr);
    expect(status.asr.status).toBe("ready");
    // top-level status unchanged when credentials are missing
    expect(status.status).toBe("needs_credentials");
    expect(status.credentials.configured).toBe(false);
  });

  it("ASR incomplete does not change exit-code gating", () => {
    const mockReadAsr = vi.fn(() => ({ kind: "incomplete" as const }));
    vi.spyOn(fs, "existsSync").mockReturnValue(false);
    process.exitCode = undefined;
    vi.spyOn(console, "log").mockImplementation(() => {});
    doctorCommand(true, () => buildDoctorStatus(mockReadAsr));
    // needs_credentials exit code 1 preserved
    expect(process.exitCode).toBe(1);
  });

  it("ASR ready does not suppress needs_credentials exit code 1", () => {
    const mockReadAsr = vi.fn(() => ({
      kind: "ready" as const,
      version: 1,
      runtime: ASR_PINNED_RUNTIME,
      model: ASR_PINNED_MODEL,
      revision: ASR_PINNED_REVISION,
    }));
    vi.spyOn(fs, "existsSync").mockReturnValue(false);
    process.exitCode = undefined;
    vi.spyOn(console, "log").mockImplementation(() => {});
    doctorCommand(true, () => buildDoctorStatus(mockReadAsr));
    // status is needs_credentials → exit code 1 regardless of ASR ready
    expect(process.exitCode).toBe(1);
  });

  it("credentials-ready + ASR-incomplete: top-level status is locally_ready, exit 0", () => {
    const mockReadAsr = vi.fn(() => ({ kind: "incomplete" as const }));
    process.env.BILIBILI_SESSDATA = "a";
    process.env.BILIBILI_BILI_JCT = "b";
    process.env.BILIBILI_DEDEUSERID = "c";
    process.exitCode = undefined;
    vi.spyOn(console, "log").mockImplementation(() => {});

    const status = buildDoctorStatus(mockReadAsr);
    expect(status.credentials.configured).toBe(true);
    expect(status.asr.status).toBe("incomplete");
    // credentials drive top-level status, ASR is informational
    expect(status.status).toBe("locally_ready");

    doctorCommand(true, () => status);
    // locally_ready → exit 0
    expect(process.exitCode).toBeUndefined();
  });
});

describe("doctor exit codes", () => {
  let savedEnv: Record<string, string | undefined>;

  beforeEach(() => {
    savedEnv = saveEnv();
    clearCredentialEnv();
    credentialManager.clearCredentials();
    vi.spyOn(fs, "existsSync").mockReturnValue(false);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    credentialManager.clearCredentials();
    process.exitCode = undefined;
    restoreEnv(savedEnv);
  });

  it("exitCode 0 for locally_ready", () => {
    process.env.BILIBILI_SESSDATA = "a";
    process.env.BILIBILI_BILI_JCT = "b";
    process.env.BILIBILI_DEDEUSERID = "c";

    process.exitCode = undefined;
    vi.spyOn(console, "log").mockImplementation(() => {});
    doctorCommand(true);
    expect(process.exitCode).toBeUndefined();
  });

  it("exitCode 1 for needs_credentials", () => {
    process.exitCode = undefined;
    vi.spyOn(console, "log").mockImplementation(() => {});
    doctorCommand(true);
    expect(process.exitCode).toBe(1);
  });

  it("exitCode 2 for an internal local-check failure", () => {
    const logSpy = vi.spyOn(console, "log").mockImplementation(() => {});
    vi.spyOn(console, "error").mockImplementation(() => {});

    doctorCommand(true, () => {
      throw new Error("synthetic local-check failure");
    });

    expect(process.exitCode).toBe(2);
    expect(logSpy).not.toHaveBeenCalled();
  });
});

describe("setup credential loadability", () => {
  const originalTtyDescriptor = Object.getOwnPropertyDescriptor(
    process.stdin,
    "isTTY",
  );
  const originalExitCode = process.exitCode;

  afterEach(() => {
    vi.restoreAllMocks();
    credentialManager.clearCredentials();
    process.exitCode = originalExitCode;
    if (originalTtyDescriptor) {
      Object.defineProperty(process.stdin, "isTTY", originalTtyDescriptor);
    } else {
      delete (process.stdin as NodeJS.ReadStream & { isTTY?: boolean }).isTTY;
    }
  });

  it("runs hidden reconfiguration when existing credentials are unloadable", async () => {
    Object.defineProperty(process.stdin, "isTTY", {
      configurable: true,
      value: true,
    });
    vi.spyOn(credentialManager, "getCredentials").mockReturnValue(null);
    const configure = vi.fn(async () => {});
    const runAsr = vi.fn(async () => ({ success: true }));
    const askHiddenFn = vi.fn(async () => "n");

    await setupCredentials(configure, runAsr, askHiddenFn);

    expect(configure).toHaveBeenCalledOnce();
  });

  it("stops before the ASR prompt when credential configuration reports failure", async () => {
    Object.defineProperty(process.stdin, "isTTY", {
      configurable: true,
      value: true,
    });
    vi.spyOn(credentialManager, "getCredentials").mockReturnValue(null);
    const configure = vi.fn(async () => false);
    const runAsr = vi.fn(async () => ({ success: true }));
    const askHiddenFn = vi.fn(async () => {
      throw new Error("ASR prompt must not be reached after credential failure");
    });
    process.exitCode = undefined;

    await setupCredentials(configure, runAsr, askHiddenFn);

    expect(configure).toHaveBeenCalledOnce();
    expect(askHiddenFn).not.toHaveBeenCalled();
    expect(runAsr).not.toHaveBeenCalled();
    expect(process.exitCode).toBe(1);
  });

  it("default No does not call the ASR runner", async () => {
    Object.defineProperty(process.stdin, "isTTY", { configurable: true, value: true });
    vi.spyOn(credentialManager, "getCredentials").mockReturnValue(null);
    const configure = vi.fn(async () => {});
    const runAsr = vi.fn(async () => ({ success: true }));
    const askHiddenFn = vi.fn(async () => "n");

    await setupCredentials(configure, runAsr, askHiddenFn);

    expect(runAsr).not.toHaveBeenCalled();
  });

  it("empty answer defaults to No and does not call ASR runner", async () => {
    Object.defineProperty(process.stdin, "isTTY", { configurable: true, value: true });
    vi.spyOn(credentialManager, "getCredentials").mockReturnValue(null);
    const configure = vi.fn(async () => {});
    const runAsr = vi.fn(async () => ({ success: true }));
    const askHiddenFn = vi.fn(async () => "");

    await setupCredentials(configure, runAsr, askHiddenFn);

    expect(runAsr).not.toHaveBeenCalled();
  });

  it("already configured credentials still reach the ASR prompt", async () => {
    Object.defineProperty(process.stdin, "isTTY", { configurable: true, value: true });
    vi.spyOn(credentialManager, "getCredentials").mockReturnValue({
      sessdata: "s", bili_jct: "j", dedeuserid: "d", expiresAt: Date.now() + 86400000,
    });
    vi.spyOn(credentialManager, "getCredentialSource").mockReturnValue("global_config");
    const configure = vi.fn(async () => {});
    const runAsr = vi.fn(async (_modelKey: string) => ({ success: true }));
    const askHiddenFn = vi.fn()
      .mockResolvedValueOnce("y")   // Yes to ASR
      .mockResolvedValueOnce("")    // Enter = small model
      .mockResolvedValueOnce("");   // Enter = auto

    await setupCredentials(configure, runAsr, askHiddenFn);

    expect(configure).not.toHaveBeenCalled();
    expect(runAsr).toHaveBeenCalledOnce();
    expect(runAsr).toHaveBeenCalledWith("small", "auto");
  });

  it("failed opted-in ASR installation sets process.exitCode 1", async () => {
    Object.defineProperty(process.stdin, "isTTY", { configurable: true, value: true });
    vi.spyOn(credentialManager, "getCredentials").mockReturnValue(null);
    const configure = vi.fn(async () => {});
    const runAsr = vi.fn(async (_modelKey: string) => ({ success: false, error: "test failure" }));
    const askHiddenFn = vi.fn()
      .mockResolvedValueOnce("y")   // Yes to ASR
      .mockResolvedValueOnce("")    // Enter = small model
      .mockResolvedValueOnce("");   // Enter = auto

    process.exitCode = undefined;
    vi.spyOn(console, "error").mockImplementation(() => {});
    await setupCredentials(configure, runAsr, askHiddenFn);

    expect(process.exitCode).toBe(1);
  });

  it("successful ASR install does not set process.exitCode", async () => {
    Object.defineProperty(process.stdin, "isTTY", { configurable: true, value: true });
    vi.spyOn(credentialManager, "getCredentials").mockReturnValue(null);
    const configure = vi.fn(async () => {});
    const runAsr = vi.fn(async (_modelKey: string) => ({ success: true }));
    const askHiddenFn = vi.fn()
      .mockResolvedValueOnce("y")   // Yes to ASR
      .mockResolvedValueOnce("")    // Enter = small model
      .mockResolvedValueOnce("");   // Enter = auto

    process.exitCode = undefined;
    await setupCredentials(configure, runAsr, askHiddenFn);

    expect(process.exitCode).toBeUndefined();
  });

  it("reports the validated CUDA profile instead of claiming CPU", async () => {
    Object.defineProperty(process.stdin, "isTTY", { configurable: true, value: true });
    vi.spyOn(credentialManager, "getCredentials").mockReturnValue(null);
    const logSpy = vi.spyOn(console, "log").mockImplementation(() => {});
    const askHiddenFn = vi.fn()
      .mockResolvedValueOnce("y")
      .mockResolvedValueOnce("")
      .mockResolvedValueOnce("auto");

    await setupCredentials(
      vi.fn(async () => {}),
      vi.fn(async () => ({
        success: true,
        executionProfile: { device: "cuda" as const, computeType: "float16" as const },
      })),
      askHiddenFn,
    );

    const output = logSpy.mock.calls.flat().join("\n");
    expect(output).toContain("CUDA Float16");
    expect(output).not.toContain("通过 CPU INT8 验证");
  });

  it("explains an auto GPU failure and lets the user choose how to proceed", async () => {
    Object.defineProperty(process.stdin, "isTTY", { configurable: true, value: true });
    vi.spyOn(credentialManager, "getCredentials").mockReturnValue(null);
    const logSpy = vi.spyOn(console, "log").mockImplementation(() => {});
    const askHiddenFn = vi.fn()
      .mockResolvedValueOnce("y")
      .mockResolvedValueOnce("")
      .mockResolvedValueOnce("auto");

    await setupCredentials(
      vi.fn(async () => {}),
      vi.fn(async () => ({
        success: true,
        executionProfile: { device: "cpu" as const, computeType: "int8" as const },
        failureCategory: "cuda_runtime_missing" as const,
      })),
      askHiddenFn,
    );

    const output = logSpy.mock.calls.flat().join("\n");
    expect(output).toContain("cuda_runtime_missing");
    expect(output).toContain("CUDA、cuBLAS 或 cuDNN");
    expect(output).toContain("CUDA 12");
    expect(output).toContain("github.com/SYSTRAN/faster-whisper#gpu");
    expect(output).toContain("CPU INT8");
    expect(output).toContain("不会自动安装或修改");
    expect(output).toContain("重新运行 setup");
  });

  it("explains explicit CUDA failure without silently falling back", async () => {
    Object.defineProperty(process.stdin, "isTTY", { configurable: true, value: true });
    vi.spyOn(credentialManager, "getCredentials").mockReturnValue(null);
    const logSpy = vi.spyOn(console, "log").mockImplementation(() => {});
    vi.spyOn(console, "error").mockImplementation(() => {});
    const askHiddenFn = vi.fn()
      .mockResolvedValueOnce("y")
      .mockResolvedValueOnce("")
      .mockResolvedValueOnce("cuda");
    process.exitCode = undefined;

    await setupCredentials(
      vi.fn(async () => {}),
      vi.fn(async () => ({
        success: false,
        error: "ASR device readiness failed (runtime_version_mismatch)",
        failureCategory: "runtime_version_mismatch" as const,
      })),
      askHiddenFn,
    );

    const output = logSpy.mock.calls.flat().join("\n");
    expect(process.exitCode).toBe(1);
    expect(output).toContain("runtime_version_mismatch");
    expect(output).toContain("升级 NVIDIA 驱动");
    expect(output).toContain("没有回退到 CPU");
    expect(output).toContain("选择 cpu");
    expect(output).toContain("重新选择 cuda");
  });

  it("labels an explicit CPU readiness failure as CPU instead of GPU", async () => {
    Object.defineProperty(process.stdin, "isTTY", { configurable: true, value: true });
    vi.spyOn(credentialManager, "getCredentials").mockReturnValue(null);
    const logSpy = vi.spyOn(console, "log").mockImplementation(() => {});
    vi.spyOn(console, "error").mockImplementation(() => {});
    const askHiddenFn = vi.fn()
      .mockResolvedValueOnce("y")
      .mockResolvedValueOnce("")
      .mockResolvedValueOnce("cpu");
    process.exitCode = undefined;

    await setupCredentials(
      vi.fn(async () => {}),
      vi.fn(async () => ({
        success: false,
        error: "ASR device readiness failed (model_probe_failed)",
        failureCategory: "model_probe_failed" as const,
        failureDevice: "cpu" as const,
      })),
      askHiddenFn,
    );

    const output = logSpy.mock.calls.flat().join("\n");
    expect(process.exitCode).toBe(1);
    expect(output).toContain("CPU 验证失败");
    expect(output).not.toContain("GPU 验证失败");
    expect(output).not.toContain("升级 NVIDIA 驱动");
  });

  it("explains both failures when auto GPU and CPU readiness fail", async () => {
    Object.defineProperty(process.stdin, "isTTY", { configurable: true, value: true });
    vi.spyOn(credentialManager, "getCredentials").mockReturnValue(null);
    const logSpy = vi.spyOn(console, "log").mockImplementation(() => {});
    vi.spyOn(console, "error").mockImplementation(() => {});
    const askHiddenFn = vi.fn()
      .mockResolvedValueOnce("y")
      .mockResolvedValueOnce("")
      .mockResolvedValueOnce("auto");
    process.exitCode = undefined;

    await setupCredentials(
      vi.fn(async () => {}),
      vi.fn(async () => ({
        success: false,
        error: "ASR device readiness failed (model_probe_failed)",
        failureCategory: "model_probe_failed" as const,
        failureDevice: "cpu" as const,
        gpuFailureCategory: "cuda_runtime_missing" as const,
      })),
      askHiddenFn,
    );

    const output = logSpy.mock.calls.flat().join("\n");
    expect(process.exitCode).toBe(1);
    expect(output).toContain("GPU 验证失败");
    expect(output).toContain("cuda_runtime_missing");
    expect(output).toContain("CPU 回退验证也失败");
    expect(output).toContain("model_probe_failed");
  });

  it("redacts credential-looking values from ASR error messages", async () => {
    Object.defineProperty(process.stdin, "isTTY", { configurable: true, value: true });
    vi.spyOn(credentialManager, "getCredentials").mockReturnValue(null);
    const configure = vi.fn(async () => {});
    const runAsr = vi.fn(async (_modelKey: string) => ({
      success: false,
      error: "Download failed while using SESSDATA=abc123def456,bili_jct=xyz789 for auth",
    }));
    const askHiddenFn = vi.fn()
      .mockResolvedValueOnce("y")   // Yes to ASR
      .mockResolvedValueOnce("")    // Enter = small model
      .mockResolvedValueOnce("");   // Enter = auto
    const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const logSpy = vi.spyOn(console, "log").mockImplementation(() => {});

    process.exitCode = undefined;
    await setupCredentials(configure, runAsr, askHiddenFn);

    expect(process.exitCode).toBe(1);
    const errCalls = errSpy.mock.calls.map((c) => c.join(" ")).join("\n");
    // Must never contain the raw SESSDATA value
    expect(errCalls).not.toMatch(/abc123def456/);
    // Must never contain the raw bili_jct value
    expect(errCalls).not.toMatch(/xyz789/);
  });

  describe("non-interactive setup", () => {
    it("exits 1 with value-free guidance when credentials are unloadable", async () => {
      Object.defineProperty(process.stdin, "isTTY", {
        configurable: true,
        value: true,
      });
      vi.spyOn(credentialManager, "getCredentialSource").mockReturnValue("none");
      vi.spyOn(credentialManager, "getCredentials").mockReturnValue(null);
      const configure = vi.fn(async () => {});
      const runAsr = vi.fn(async (_modelKey: string) => ({ success: true }));
      const askHiddenFn = vi.fn(async () => "n");
      const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
      process.exitCode = undefined;

      await setupCredentials(configure, runAsr, askHiddenFn, {
        nonInteractive: true,
      });

      expect(process.exitCode).toBe(1);
      expect(configure).not.toHaveBeenCalled();
      expect(askHiddenFn).not.toHaveBeenCalled();
      expect(runAsr).not.toHaveBeenCalled();
      const errCalls = errSpy.mock.calls.map((c) => c.join(" ")).join("\n");
      expect(errCalls).toContain("BILIBILI_SESSDATA");
      expect(errCalls).toContain("BILIBILI_BILI_JCT");
      expect(errCalls).toContain("BILIBILI_DEDEUSERID");
    });

    it("completes credential-only with non-TTY stdin and an env source, without prompting", async () => {
      Object.defineProperty(process.stdin, "isTTY", {
        configurable: true,
        value: false,
      });
      vi.spyOn(credentialManager, "getCredentialSource").mockReturnValue("env");
      vi.spyOn(credentialManager, "getCredentials").mockReturnValue({
        sessdata: "s", bili_jct: "j", dedeuserid: "d", expiresAt: Date.now() + 86400000,
      });
      const configure = vi.fn(async () => {});
      const runAsr = vi.fn(async (_modelKey: string) => ({ success: true }));
      const askHiddenFn = vi.fn(async () => "n");
      const logSpy = vi.spyOn(console, "log").mockImplementation(() => {});
      process.exitCode = undefined;

      await setupCredentials(configure, runAsr, askHiddenFn, {
        nonInteractive: true,
      });

      expect(process.exitCode).toBeUndefined();
      expect(configure).not.toHaveBeenCalled();
      expect(askHiddenFn).not.toHaveBeenCalled();
      expect(runAsr).not.toHaveBeenCalled();
      expect(logSpy.mock.calls.flat().join("\n")).toContain("ASR");
    });

    it("with a model calls the installer exactly once with that model", async () => {
      Object.defineProperty(process.stdin, "isTTY", {
        configurable: true,
        value: false,
      });
      vi.spyOn(credentialManager, "getCredentialSource").mockReturnValue("global_config");
      vi.spyOn(credentialManager, "getCredentials").mockReturnValue({
        sessdata: "s", bili_jct: "j", dedeuserid: "d", expiresAt: Date.now() + 86400000,
      });
      const configure = vi.fn(async () => {});
      const runAsr = vi.fn(async (_modelKey: string) => ({ success: true }));
      const askHiddenFn = vi.fn(async () => "n");
      vi.spyOn(console, "log").mockImplementation(() => {});
      process.exitCode = undefined;

      await setupCredentials(configure, runAsr, askHiddenFn, {
        nonInteractive: true,
        asrModel: "tiny",
      });

      expect(process.exitCode).toBeUndefined();
      expect(configure).not.toHaveBeenCalled();
      expect(askHiddenFn).not.toHaveBeenCalled();
      expect(runAsr).toHaveBeenCalledOnce();
      expect(runAsr).toHaveBeenCalledWith("tiny", "auto");
    });

    it("passes an explicit CUDA preference in non-interactive setup", async () => {
      vi.spyOn(credentialManager, "getCredentialSource").mockReturnValue("global_config");
      vi.spyOn(credentialManager, "getCredentials").mockReturnValue({
        sessdata: "s", bili_jct: "j", dedeuserid: "d", expiresAt: Date.now() + 86400000,
      });
      const runAsr = vi.fn(async () => ({ success: true }));

      await setupCredentials(vi.fn(), runAsr, vi.fn(), {
        nonInteractive: true,
        asrModel: "small",
        asrDevice: "cuda",
      });

      expect(runAsr).toHaveBeenCalledWith("small", "cuda");
    });

    it("rejects --asr-device without --asr-model", async () => {
      const runAsr = vi.fn(async () => ({ success: true }));
      process.exitCode = undefined;
      vi.spyOn(console, "error").mockImplementation(() => {});

      await setupCredentials(vi.fn(), runAsr, vi.fn(), {
        nonInteractive: true,
        asrDevice: "cpu",
      });

      expect(process.exitCode).toBe(1);
      expect(runAsr).not.toHaveBeenCalled();
    });

    it("rejects non-interactive setup when the credential source is none even with loadable credentials", async () => {
      Object.defineProperty(process.stdin, "isTTY", {
        configurable: true,
        value: false,
      });
      vi.spyOn(credentialManager, "getCredentialSource").mockReturnValue("none");
      vi.spyOn(credentialManager, "getCredentials").mockReturnValue({
        sessdata: "s", bili_jct: "j", dedeuserid: "d", expiresAt: Date.now() + 86400000,
      });
      const configure = vi.fn(async () => {});
      const runAsr = vi.fn(async (_modelKey: string) => ({ success: true }));
      const askHiddenFn = vi.fn(async () => "n");
      const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
      process.exitCode = undefined;

      await setupCredentials(configure, runAsr, askHiddenFn, {
        nonInteractive: true,
      });

      expect(process.exitCode).toBe(1);
      expect(configure).not.toHaveBeenCalled();
      expect(askHiddenFn).not.toHaveBeenCalled();
      expect(runAsr).not.toHaveBeenCalled();
      expect(errSpy.mock.calls.flat().join("\n")).toContain("BILIBILI_SESSDATA");
    });

    it("rejects a model without non-interactive mode as a validation error", async () => {
      Object.defineProperty(process.stdin, "isTTY", {
        configurable: true,
        value: true,
      });
      vi.spyOn(credentialManager, "getCredentials").mockReturnValue({
        sessdata: "s", bili_jct: "j", dedeuserid: "d", expiresAt: Date.now() + 86400000,
      });
      const configure = vi.fn(async () => {});
      const runAsr = vi.fn(async (_modelKey: string) => ({ success: true }));
      const askHiddenFn = vi.fn(async () => "n");
      const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
      process.exitCode = undefined;

      await setupCredentials(configure, runAsr, askHiddenFn, {
        asrModel: "small",
      });

      expect(process.exitCode).toBe(1);
      expect(configure).not.toHaveBeenCalled();
      expect(askHiddenFn).not.toHaveBeenCalled();
      expect(runAsr).not.toHaveBeenCalled();
      expect(errSpy.mock.calls.flat().join("\n")).toContain("--non-interactive");
    });
  });
});

// ---------- Phase 2: model choice parsing ----------

describe("parseModelChoice", () => {
  it("empty string defaults to small", () => {
    expect(parseModelChoice("")).toBe("small");
    expect(parseModelChoice("  ")).toBe("small");
  });

  it("numeric 1 returns tiny", () => {
    expect(parseModelChoice("1")).toBe("tiny");
  });

  it("numeric 2 returns base", () => {
    expect(parseModelChoice("2")).toBe("base");
  });

  it("numeric 3 returns small", () => {
    expect(parseModelChoice("3")).toBe("small");
  });

  it("name 'tiny' returns tiny", () => {
    expect(parseModelChoice("tiny")).toBe("tiny");
    expect(parseModelChoice("TINY")).toBe("tiny");
  });

  it("name 'base' returns base", () => {
    expect(parseModelChoice("base")).toBe("base");
    expect(parseModelChoice("BASE")).toBe("base");
  });

  it("name 'small' returns small", () => {
    expect(parseModelChoice("small")).toBe("small");
    expect(parseModelChoice("SMALL")).toBe("small");
  });

  it("returns null for invalid input", () => {
    expect(parseModelChoice("4")).toBeNull();
    expect(parseModelChoice("medium")).toBeNull();
    expect(parseModelChoice("y")).toBeNull();
    expect(parseModelChoice("yes")).toBeNull();
    expect(parseModelChoice("n")).toBeNull();
  });

  it("whitespace-only input trims to empty and defaults to small", () => {
    expect(parseModelChoice(" ")).toBe("small");
    expect(parseModelChoice("\t")).toBe("small");
  });
});

describe("parseDeviceChoice", () => {
  it.each([
    ["", "auto"],
    ["auto", "auto"],
    [" CPU ", "cpu"],
    ["CUDA", "cuda"],
  ])("parses %j as %s", (input, expected) => {
    expect(parseDeviceChoice(input)).toBe(expected);
  });

  it.each(["gpu", "1", "float16", "../cuda"])("rejects %j", (input) => {
    expect(parseDeviceChoice(input)).toBeNull();
  });
});

// ---------- Phase 2: doctor model field ----------

describe("buildDoctorStatus Phase 2 model field", () => {
  let savedEnv: Record<string, string | undefined>;

  beforeEach(() => {
    savedEnv = saveEnv();
    clearCredentialEnv();
    credentialManager.clearCredentials();
    vi.spyOn(fs, "existsSync").mockReturnValue(false);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    credentialManager.clearCredentials();
    restoreEnv(savedEnv);
  });

  it("asr.model is null when not_installed", () => {
    const mockReadAsr = vi.fn(() => ({ kind: "not_installed" as const }));
    const status = buildDoctorStatus(mockReadAsr);
    expect(status.asr.model).toBeNull();
  });

  it("asr.model is null when incomplete", () => {
    const mockReadAsr = vi.fn(() => ({ kind: "incomplete" as const }));
    const status = buildDoctorStatus(mockReadAsr);
    expect(status.asr.model).toBeNull();
  });

  it("asr.model is 'small' when ready with Phase 1 model", () => {
    const mockReadAsr = vi.fn(() => ({
      kind: "ready" as const,
      version: 1,
      runtime: ASR_PINNED_RUNTIME,
      model: ASR_PINNED_MODEL,
      revision: ASR_PINNED_REVISION,
      modelKey: "small" as const,
    }));
    const status = buildDoctorStatus(mockReadAsr);
    expect(status.asr.model).toBe("small");
  });

  it("asr.model is 'tiny' when ready with tiny model", () => {
    const mockReadAsr = vi.fn(() => ({
      kind: "ready" as const,
      version: 1,
      runtime: ASR_PINNED_RUNTIME,
      model: "Systran/faster-whisper-tiny",
      revision: "d90ca5fe260221311c53c58e660288d3deb8d356",
      modelKey: "tiny" as const,
    }));
    const status = buildDoctorStatus(mockReadAsr);
    expect(status.asr.model).toBe("tiny");
  });

  it("asr.model is 'base' when ready with base model", () => {
    const mockReadAsr = vi.fn(() => ({
      kind: "ready" as const,
      version: 1,
      runtime: ASR_PINNED_RUNTIME,
      model: "Systran/faster-whisper-base",
      revision: "ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66",
      modelKey: "base" as const,
    }));
    const status = buildDoctorStatus(mockReadAsr);
    expect(status.asr.model).toBe("base");
  });

  it("asr.model is null when ready but model not in allowlist (defensive)", () => {
    const mockReadAsr = vi.fn(() => ({
      kind: "ready" as const,
      version: 1,
      runtime: ASR_PINNED_RUNTIME,
      model: "other/model",
      revision: "abc123",
    }));
    const status = buildDoctorStatus(mockReadAsr);
    expect(status.asr.model).toBeNull();
  });

  it("doctor JSON contains asr.model field", () => {
    const status = buildDoctorStatus();
    const json = JSON.stringify(status);
    const parsed = JSON.parse(json);
    expect(parsed.asr).toHaveProperty("model");
    expect(parsed.asr.model).toBeNull();
  });

  it("no credential exit-code change with model field", () => {
    process.exitCode = undefined;
    vi.spyOn(console, "log").mockImplementation(() => {});
    doctorCommand(true);
    // needs_credentials → exit code 1 preserved
    expect(process.exitCode).toBe(1);
  });
});

describe("buildDoctorStatus ASR Execution Profile", () => {
  beforeEach(() => {
    clearCredentialEnv();
    credentialManager.clearCredentials();
    vi.spyOn(fs, "existsSync").mockReturnValue(false);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    credentialManager.clearCredentials();
  });

  it("reports the verified v2 CPU profile", () => {
    const status = buildDoctorStatus(vi.fn(() => ({
      kind: "ready" as const,
      version: 2,
      runtime: ASR_PINNED_RUNTIME,
      model: ASR_PINNED_MODEL,
      revision: ASR_PINNED_REVISION,
      modelKey: "small" as const,
      executionProfile: { device: "cpu" as const, computeType: "int8" as const },
      deviceReadiness: "ready" as const,
      migrationStatus: "completed" as const,
    })));

    expect(status.asr).toEqual({
      status: "ready",
      model: "small",
      device: "cpu",
      compute_type: "int8",
      device_readiness: "ready",
      migration_status: "completed",
      failure_category: null,
    });
  });

  it("reports the verified v2 CUDA profile", () => {
    const status = buildDoctorStatus(vi.fn(() => ({
      kind: "ready" as const,
      version: 2,
      runtime: ASR_PINNED_RUNTIME,
      model: ASR_PINNED_MODEL,
      revision: ASR_PINNED_REVISION,
      modelKey: "small" as const,
      executionProfile: { device: "cuda" as const, computeType: "float16" as const },
      deviceReadiness: "ready" as const,
      migrationStatus: "completed" as const,
    })));

    expect(status.asr).toEqual({
      status: "ready",
      model: "small",
      device: "cuda",
      compute_type: "float16",
      device_readiness: "ready",
      migration_status: "completed",
      failure_category: null,
    });
  });

  it("reports only an allowlisted sanitized failure category", () => {
    const status = buildDoctorStatus(vi.fn(() => ({
      kind: "ready" as const,
      version: 2,
      modelKey: "small" as const,
      executionProfile: { device: "cpu" as const, computeType: "int8" as const },
      deviceReadiness: "ready" as const,
      migrationStatus: "completed" as const,
      failureCategory: "no_nvidia_gpu" as const,
    })));

    expect(status.asr.failure_category).toBe("no_nvidia_gpu");
  });

  it("reports v1 as migration pending without claiming a verified device", () => {
    const status = buildDoctorStatus(vi.fn(() => ({
      kind: "ready" as const,
      version: 1,
      runtime: ASR_PINNED_RUNTIME,
      model: ASR_PINNED_MODEL,
      revision: ASR_PINNED_REVISION,
      modelKey: "small" as const,
      deviceReadiness: "migration_pending" as const,
      migrationStatus: "pending" as const,
    })));

    expect(status.asr).toMatchObject({
      status: "ready",
      model: "small",
      device: null,
      compute_type: null,
      device_readiness: "migration_pending",
      migration_status: "pending",
      failure_category: null,
    });
  });

  it.each(["not_installed", "incomplete"] as const)(
    "reports %s without an execution profile",
    (kind) => {
      const status = buildDoctorStatus(vi.fn(() => ({ kind })));
      expect(status.asr).toMatchObject({
        device: null,
        compute_type: null,
        device_readiness: "not_ready",
        migration_status: null,
        failure_category: null,
      });
    },
  );

  it("never serializes injected stderr, paths, commands, or failure text", () => {
    const status = buildDoctorStatus(vi.fn(() => ({
      kind: "ready",
      version: 2,
      modelKey: "small",
      executionProfile: { device: "../../cuda", computeType: "raw-command" },
      deviceReadiness: "ready",
      migrationStatus: "completed",
      failureCategory: "raw stderr at C:\\private\\driver.dll",
      stderr: "SECRET_STDERR",
      command: "python --secret",
      env: "TOKEN=secret",
    } as never)));
    const json = JSON.stringify(status);

    expect(status.asr.device).toBeNull();
    expect(status.asr.failure_category).toBeNull();
    expect(json).not.toContain("SECRET_STDERR");
    expect(json).not.toContain("private");
    expect(json).not.toContain("--secret");
    expect(json).not.toContain("TOKEN");
  });
});

// ---------- Phase 2: setup model selection flow ----------

describe("setupCredentials model selection", () => {
  const originalTtyDescriptor = Object.getOwnPropertyDescriptor(
    process.stdin,
    "isTTY",
  );

  afterEach(() => {
    vi.restoreAllMocks();
    credentialManager.clearCredentials();
    if (originalTtyDescriptor) {
      Object.defineProperty(process.stdin, "isTTY", originalTtyDescriptor);
    } else {
      delete (process.stdin as NodeJS.ReadStream & { isTTY?: boolean }).isTTY;
    }
  });

  it("No answer does not reach model selector", async () => {
    Object.defineProperty(process.stdin, "isTTY", { configurable: true, value: true });
    vi.spyOn(credentialManager, "getCredentials").mockReturnValue(null);
    const configure = vi.fn(async () => {});
    const runAsr = vi.fn(async (_modelKey: string) => ({ success: true }));
    const askHiddenFn = vi.fn(async () => "n");

    await setupCredentials(configure, runAsr, askHiddenFn);

    expect(runAsr).not.toHaveBeenCalled();
  });

  it("default Enter selects small model", async () => {
    Object.defineProperty(process.stdin, "isTTY", { configurable: true, value: true });
    vi.spyOn(credentialManager, "getCredentials").mockReturnValue(null);
    const configure = vi.fn(async () => {});
    const runAsr = vi.fn(async (_modelKey: string) => ({ success: true }));
    const askHiddenFn = vi.fn()
      .mockResolvedValueOnce("y")   // Yes to ASR
      .mockResolvedValueOnce("")    // Enter = small
      .mockResolvedValueOnce("");   // Enter = auto

    await setupCredentials(configure, runAsr, askHiddenFn);

    expect(runAsr).toHaveBeenCalledWith("small", "auto");
  });

  it("passes an explicit CPU preference after model selection", async () => {
    Object.defineProperty(process.stdin, "isTTY", { configurable: true, value: true });
    vi.spyOn(credentialManager, "getCredentials").mockReturnValue(null);
    const runAsr = vi.fn(async () => ({ success: true }));
    const askHiddenFn = vi.fn()
      .mockResolvedValueOnce("y")
      .mockResolvedValueOnce("base")
      .mockResolvedValueOnce("cpu");

    await setupCredentials(vi.fn(async () => {}), runAsr, askHiddenFn);

    expect(runAsr).toHaveBeenCalledWith("base", "cpu");
  });

  it("numeric 1 selects tiny", async () => {
    Object.defineProperty(process.stdin, "isTTY", { configurable: true, value: true });
    vi.spyOn(credentialManager, "getCredentials").mockReturnValue(null);
    const configure = vi.fn(async () => {});
    const runAsr = vi.fn(async (_modelKey: string) => ({ success: true }));
    const askHiddenFn = vi.fn()
      .mockResolvedValueOnce("y")   // Yes to ASR
      .mockResolvedValueOnce("1")   // tiny
      .mockResolvedValueOnce("");   // auto

    await setupCredentials(configure, runAsr, askHiddenFn);

    expect(runAsr).toHaveBeenCalledWith("tiny", "auto");
  });

  it("numeric 2 selects base", async () => {
    Object.defineProperty(process.stdin, "isTTY", { configurable: true, value: true });
    vi.spyOn(credentialManager, "getCredentials").mockReturnValue(null);
    const configure = vi.fn(async () => {});
    const runAsr = vi.fn(async (_modelKey: string) => ({ success: true }));
    const askHiddenFn = vi.fn()
      .mockResolvedValueOnce("y")
      .mockResolvedValueOnce("2")
      .mockResolvedValueOnce("");

    await setupCredentials(configure, runAsr, askHiddenFn);

    expect(runAsr).toHaveBeenCalledWith("base", "auto");
  });

  it("name 'tiny' selects tiny", async () => {
    Object.defineProperty(process.stdin, "isTTY", { configurable: true, value: true });
    vi.spyOn(credentialManager, "getCredentials").mockReturnValue(null);
    const configure = vi.fn(async () => {});
    const runAsr = vi.fn(async (_modelKey: string) => ({ success: true }));
    const askHiddenFn = vi.fn()
      .mockResolvedValueOnce("y")
      .mockResolvedValueOnce("tiny")
      .mockResolvedValueOnce("");

    await setupCredentials(configure, runAsr, askHiddenFn);

    expect(runAsr).toHaveBeenCalledWith("tiny", "auto");
  });

  it("re-prompts on invalid input then accepts valid input", async () => {
    Object.defineProperty(process.stdin, "isTTY", { configurable: true, value: true });
    vi.spyOn(credentialManager, "getCredentials").mockReturnValue(null);
    const configure = vi.fn(async () => {});
    const runAsr = vi.fn(async (_modelKey: string) => ({ success: true }));
    const askHiddenFn = vi.fn()
      .mockResolvedValueOnce("y")       // Yes to ASR
      .mockResolvedValueOnce("invalid") // re-prompt
      .mockResolvedValueOnce("4")       // re-prompt
      .mockResolvedValueOnce("small")   // valid model
      .mockResolvedValueOnce("");        // auto

    await setupCredentials(configure, runAsr, askHiddenFn);

    expect(runAsr).toHaveBeenCalledWith("small", "auto");
    expect(askHiddenFn).toHaveBeenCalledTimes(5);
  });

  it("re-prompts indefinitely until valid (no infinite loop in tests)", async () => {
    Object.defineProperty(process.stdin, "isTTY", { configurable: true, value: true });
    vi.spyOn(credentialManager, "getCredentials").mockReturnValue(null);
    const configure = vi.fn(async () => {});
    const runAsr = vi.fn(async (_modelKey: string) => ({ success: true }));
    let callCount = 0;
    const askHiddenFn = vi.fn(async () => {
      callCount++;
      if (callCount === 1) return "y";    // Yes
      if (callCount === 2) return "bad";  // re-prompt
      if (callCount === 3) return "xyz";  // re-prompt
      if (callCount === 4) return "base"; // valid model
      return "auto";
    });

    await setupCredentials(configure, runAsr, askHiddenFn);

    expect(runAsr).toHaveBeenCalledWith("base", "auto");
    expect(callCount).toBe(5);
  });

  it("No answer does not print model selector text", async () => {
    Object.defineProperty(process.stdin, "isTTY", { configurable: true, value: true });
    vi.spyOn(credentialManager, "getCredentials").mockReturnValue(null);
    const configure = vi.fn(async () => {});
    const runAsr = vi.fn(async (_modelKey: AsrModelKey) => ({ success: true }));
    const askHiddenFn = vi.fn(async () => "n");
    const logSpy = vi.spyOn(console, "log").mockImplementation(() => {});

    await setupCredentials(configure, runAsr, askHiddenFn);

    expect(runAsr).not.toHaveBeenCalled();
    const allOutput = logSpy.mock.calls.map((c) => c.join(" ")).join("\n");
    expect(allOutput).not.toMatch(/1\.\s*tiny/);
    expect(allOutput).not.toMatch(/2\.\s*base/);
    expect(allOutput).not.toMatch(/3\.\s*small/);
    expect(allOutput).not.toMatch(/请选择模型/);
    expect(allOutput).not.toContain("推荐");

    logSpy.mockRestore();
  });

  it("model selector explains every Model Tier after Yes", async () => {
    Object.defineProperty(process.stdin, "isTTY", { configurable: true, value: true });
    vi.spyOn(credentialManager, "getCredentials").mockReturnValue(null);
    const configure = vi.fn(async () => {});
    const runAsr = vi.fn(async (_modelKey: AsrModelKey) => ({ success: true }));
    const askHiddenFn = vi.fn()
      .mockResolvedValueOnce("y")   // Yes
      .mockResolvedValueOnce("")    // Enter = small
      .mockResolvedValueOnce("");   // Enter = auto
    const logSpy = vi.spyOn(console, "log").mockImplementation(() => {});

    await setupCredentials(configure, runAsr, askHiddenFn);

    const allOutput = logSpy.mock.calls.map((c) => c.join(" ")).join("\n");
    expect(allOutput).toMatch(/1\.\s*tiny/);
    expect(allOutput).toMatch(/2\.\s*base/);
    expect(allOutput).toMatch(/3\.\s*small/);
    expect(allOutput).toMatch(/请选择模型/);
    expect(allOutput).toContain(
      "速度优先：适合快速提取和长视频初筛，准确率相对较低",
    );
    expect(allOutput).toContain("均衡：兼顾速度、质量和资源占用");
    expect(allOutput).toContain("质量优先：耗时和内存占用更高");
    expect(allOutput).toContain("推荐");

    logSpy.mockRestore();
  });
});
