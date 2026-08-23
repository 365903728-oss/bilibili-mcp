import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { config } from "../config.js";
import {
  getPlaybackAudioSet,
  MAX_ASR_DURATION_SECONDS,
  validatePlaybackMediaUrl,
  type PlaybackAudioCandidate,
  type PlaybackAudioSet,
} from "../bilibili/playback.js";
import type { SubtitleBodyItem } from "../bilibili/types.js";
import {
  createAbortError,
  getOperationSignal,
  linkAbortSignal,
  throwIfAborted,
} from "../security/operation-context.js";
import {
  FakeIpDnsError,
  pinnedHttpsFetch,
} from "../security/pinned-https.js";
import { sanitizeRemoteText } from "../utils/bounded-text.js";
import { AsrError } from "../utils/errors.js";
import { buildAsrChildEnv } from "./installer.js";
import {
  deriveAsrPaths,
  readAsrState,
  type AsrPaths,
  type AsrState,
} from "./state.js";

export const MAX_ASR_AUDIO_BYTES = 128 * 1024 * 1024;
export const MAX_ASR_REDIRECTS = 3;
export const ASR_DOWNLOAD_TIMEOUT_MS = 120_000;
export const ASR_TRANSCRIPTION_TIMEOUT_MS = 30 * 60 * 1_000;
export const MAX_ASR_STDOUT_BYTES = 2 * 1024 * 1024;
export const MAX_ASR_STDERR_BYTES = 2 * 1024;
export const MAX_ASR_SEGMENTS = 10_000;
export const MAX_ASR_TRANSCRIPT_CHARS = 500_000;
export const ASR_TEMP_PREFIX = "bilibili-mcp-asr-";
const createdAsrTempDirs = new Set<string>();

function isAsrRequestTempDir(tempDir: string): boolean {
  const name = path.basename(tempDir);
  const suffix = name.slice(ASR_TEMP_PREFIX.length);
  return name.startsWith(ASR_TEMP_PREFIX) && /^[A-Za-z0-9_-]{6}$/.test(suffix);
}

const ALLOWED_AUDIO_CONTENT_TYPES = new Set([
  "audio/mp4",
  "audio/m4a",
  "video/mp4",
  "application/octet-stream",
]);

const PYTHON_SCRIPT = [
  "import json, os, sys",
  "MEMORY_LIMIT = 4 * 1024 * 1024 * 1024",
  "CPU_LIMIT_SECONDS = 30 * 60",
  "if sys.platform == 'win32':",
  "    import ctypes",
  "    from ctypes import wintypes",
  "    class LARGE_INTEGER(ctypes.Structure):",
  "        _fields_ = [('QuadPart', ctypes.c_longlong)]",
  "    class BASIC_LIMITS(ctypes.Structure):",
  "        _fields_ = [('PerProcessUserTimeLimit', LARGE_INTEGER), ('PerJobUserTimeLimit', LARGE_INTEGER), ('LimitFlags', wintypes.DWORD), ('MinimumWorkingSetSize', ctypes.c_size_t), ('MaximumWorkingSetSize', ctypes.c_size_t), ('ActiveProcessLimit', wintypes.DWORD), ('Affinity', ctypes.c_size_t), ('PriorityClass', wintypes.DWORD), ('SchedulingClass', wintypes.DWORD)]",
  "    class IO_COUNTERS(ctypes.Structure):",
  "        _fields_ = [('ReadOperationCount', ctypes.c_ulonglong), ('WriteOperationCount', ctypes.c_ulonglong), ('OtherOperationCount', ctypes.c_ulonglong), ('ReadTransferCount', ctypes.c_ulonglong), ('WriteTransferCount', ctypes.c_ulonglong), ('OtherTransferCount', ctypes.c_ulonglong)]",
  "    class EXTENDED_LIMITS(ctypes.Structure):",
  "        _fields_ = [('BasicLimitInformation', BASIC_LIMITS), ('IoInfo', IO_COUNTERS), ('ProcessMemoryLimit', ctypes.c_size_t), ('JobMemoryLimit', ctypes.c_size_t), ('PeakProcessMemoryUsed', ctypes.c_size_t), ('PeakJobMemoryUsed', ctypes.c_size_t)]",
  "    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)",
  "    kernel32.CreateJobObjectW.restype = wintypes.HANDLE",
  "    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]",
  "    kernel32.GetCurrentProcess.restype = wintypes.HANDLE",
  "    kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]",
  "    kernel32.SetInformationJobObject.restype = wintypes.BOOL",
  "    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]",
  "    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL",
  "    job = kernel32.CreateJobObjectW(None, None)",
  "    if not job:",
  "        raise RuntimeError('job containment unavailable')",
  "    limits = EXTENDED_LIMITS()",
  "    limits.BasicLimitInformation.PerProcessUserTimeLimit.QuadPart = CPU_LIMIT_SECONDS * 10_000_000",
  "    limits.BasicLimitInformation.ActiveProcessLimit = 1",
  "    limits.BasicLimitInformation.LimitFlags = 0x00000002 | 0x00000008 | 0x00000100 | 0x00000200 | 0x00002000",
  "    limits.ProcessMemoryLimit = MEMORY_LIMIT",
  "    limits.JobMemoryLimit = MEMORY_LIMIT",
  "    if not kernel32.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):",
  "        raise RuntimeError('job limits unavailable')",
  "    if not kernel32.AssignProcessToJobObject(job, kernel32.GetCurrentProcess()):",
  "        raise RuntimeError('job assignment unavailable')",
  "else:",
  "    import resource",
  "    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT, MEMORY_LIMIT))",
  "    resource.setrlimit(resource.RLIMIT_CPU, (CPU_LIMIT_SECONDS, CPU_LIMIT_SECONDS))",
  "    if hasattr(resource, 'RLIMIT_NPROC'):",
  "        soft, hard = resource.getrlimit(resource.RLIMIT_NPROC)",
  "        cap = 64 if hard < 0 else min(64, hard)",
  "        resource.setrlimit(resource.RLIMIT_NPROC, (cap, cap))",
  "from faster_whisper import WhisperModel",
  "model = WhisperModel(sys.argv[1], device='cpu', compute_type='int8')",
  "segments, info = model.transcribe(sys.argv[2], beam_size=5)",
  "language = info.language if isinstance(info.language, str) else None",
  "print(json.dumps({'type': 'meta', 'language': language}, ensure_ascii=True), flush=True)",
  "count = 0",
  "for segment in segments:",
  "    text = segment.text.strip()",
  "    if not text:",
  "        continue",
  "    print(json.dumps({'type': 'segment', 'start': segment.start, 'end': segment.end, 'text': text}, ensure_ascii=True), flush=True)",
  "    count += 1",
  "print(json.dumps({'type': 'done', 'count': count}, ensure_ascii=True), flush=True)",
].join("\n");

export interface AsrTranscriptionResult {
  language?: string;
  segments: SubtitleBodyItem[];
}

export interface AsrTranscriptionRequest {
  bvid: string;
  cid: number;
  durationSeconds: number;
}

type FetchFn = (
  input: string | URL | Request,
  init?: RequestInit,
) => Promise<Response>;

export interface AsrTranscriptionDependencies {
  getPlayback?: (
    bvid: string,
    cid: number,
    signal?: AbortSignal,
  ) => Promise<PlaybackAudioSet>;
  getPaths?: () => AsrPaths;
  getState?: (stateFile: string) => AsrState;
  createTempDir?: (prefix: string) => Promise<string>;
  removeTempDir?: (tempDir: string) => Promise<void>;
  downloadAudio?: (
    candidates: PlaybackAudioCandidate[],
    destination: string,
    signal?: AbortSignal,
  ) => Promise<void>;
  runRuntime?: (
    pythonExecutable: string,
    modelPath: string,
    audioPath: string,
    signal?: AbortSignal,
  ) => Promise<AsrTranscriptionResult>;
}

let activeTranscriptions = 0;

function managedPythonExecutable(venvPath: string): string {
  return path.join(
    venvPath,
    process.platform === "win32" ? "Scripts" : "bin",
    process.platform === "win32" ? "python.exe" : "python",
  );
}

export function buildAsrRuntimeEnv(
  source: Record<string, string | undefined>,
): Record<string, string> {
  const sanitized = buildAsrChildEnv(source);
  const allowed = new Set([
    "PATH",
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "PATHEXT",
    "TEMP",
    "TMP",
    "TMPDIR",
    "LANG",
    "LC_ALL",
    "NO_COLOR",
  ]);
  const env: Record<string, string> = {
    HF_HUB_OFFLINE: "1",
    TRANSFORMERS_OFFLINE: "1",
    OMP_NUM_THREADS: "4",
    MKL_NUM_THREADS: "4",
    OPENBLAS_NUM_THREADS: "4",
    NUMEXPR_NUM_THREADS: "4",
    TOKENIZERS_PARALLELISM: "false",
  };
  for (const [key, value] of Object.entries(sanitized)) {
    if (value !== undefined && allowed.has(key.toUpperCase())) {
      env[key] = value;
    }
  }
  return env;
}

function assertDuration(durationSeconds: number | undefined): void {
  if (durationSeconds === undefined) {
    throw new AsrError(
      "ASR_AUDIO_UNAVAILABLE",
      "The selected Part has no trustworthy duration metadata.",
    );
  }
  if (!Number.isFinite(durationSeconds) || durationSeconds <= 0) {
    throw new AsrError(
      "ASR_AUDIO_UNAVAILABLE",
      "The selected Part has invalid duration metadata.",
    );
  }
  if (durationSeconds > MAX_ASR_DURATION_SECONDS) {
    throw new AsrError(
      "ASR_LIMIT_EXCEEDED",
      `The selected Part exceeds the ${MAX_ASR_DURATION_SECONDS}-second ASR limit.`,
    );
  }
}

async function readBoundedBody(
  response: Response,
  destination: string,
  aggregateBudget: { remainingBytes: number },
): Promise<void> {
  const contentLength = response.headers.get("content-length");
  if (contentLength !== null) {
    const expected = Number(contentLength);
    if (!Number.isFinite(expected) || expected < 0) {
      throw new AsrError(
        "ASR_AUDIO_UNAVAILABLE",
        "The temporary audio response has an invalid length.",
        true,
      );
    }
    if (expected > aggregateBudget.remainingBytes) {
      throw new AsrError(
        "ASR_LIMIT_EXCEEDED",
        "The temporary audio exceeds the 128 MiB ASR limit.",
      );
    }
  }

  const rawContentType = response.headers.get("content-type") ?? "";
  const contentType = rawContentType.split(";", 1)[0].trim().toLowerCase();
  if (!ALLOWED_AUDIO_CONTENT_TYPES.has(contentType)) {
    throw new AsrError(
      "ASR_AUDIO_UNAVAILABLE",
      "The temporary media response is not a supported audio type.",
      true,
    );
  }
  if (!response.body) {
    throw new AsrError(
      "ASR_AUDIO_UNAVAILABLE",
      "The temporary audio response has no body.",
      true,
    );
  }

  const handle = await fs.promises.open(destination, "wx", 0o600);
  const reader = response.body.getReader();
  let received = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      received += value.byteLength;
      aggregateBudget.remainingBytes -= value.byteLength;
      if (aggregateBudget.remainingBytes < 0) {
        await reader.cancel();
        throw new AsrError(
          "ASR_LIMIT_EXCEEDED",
          "The temporary audio exceeds the 128 MiB ASR limit.",
        );
      }
      await handle.writeFile(value);
    }
  } finally {
    await handle.close();
  }

  if (received === 0) {
    throw new AsrError(
      "ASR_AUDIO_UNAVAILABLE",
      "The temporary audio response is empty.",
      true,
    );
  }
}

async function fetchAudioResponse(
  initialUrl: string,
  signal: AbortSignal,
  fetchFn: FetchFn,
): Promise<Response> {
  let currentUrl = validatePlaybackMediaUrl(initialUrl);
  for (let redirects = 0; redirects <= MAX_ASR_REDIRECTS; redirects += 1) {
    let response: Response;
    try {
      response = await fetchFn(currentUrl, {
        method: "GET",
        headers: {
          "User-Agent": config.userAgent,
          Referer: config.referer,
          Accept: "audio/mp4,audio/*;q=0.9,application/octet-stream;q=0.5",
        },
        redirect: "manual",
        signal,
      });
    } catch (error) {
      if (redirects > 0 && error instanceof FakeIpDnsError) {
        throw new Error("Media redirect resolution failed");
      }
      throw error;
    }

    if (response.status >= 300 && response.status < 400) {
      if (redirects === MAX_ASR_REDIRECTS) {
        throw new AsrError(
          "ASR_AUDIO_UNAVAILABLE",
          "The temporary audio exceeded the redirect limit.",
          true,
        );
      }
      const location = response.headers.get("location");
      if (!location) {
        throw new AsrError(
          "ASR_AUDIO_UNAVAILABLE",
          "The temporary audio redirect was invalid.",
          true,
        );
      }
      await response.body?.cancel();
      currentUrl = validatePlaybackMediaUrl(new URL(location, currentUrl).toString());
      continue;
    }

    if (!response.ok) {
      throw new AsrError(
        "ASR_AUDIO_UNAVAILABLE",
        `The temporary audio request failed with HTTP ${response.status}.`,
        response.status >= 500 || response.status === 408 || response.status === 429,
      );
    }
    return response;
  }

  throw new AsrError(
    "ASR_AUDIO_UNAVAILABLE",
    "The temporary audio could not be retrieved.",
    true,
  );
}

export async function downloadPlaybackAudio(
  candidates: PlaybackAudioCandidate[],
  destination: string,
  fetchFn: FetchFn = pinnedHttpsFetch,
  timeoutMs: number = ASR_DOWNLOAD_TIMEOUT_MS,
  callerSignal?: AbortSignal,
  maxBytes: number = MAX_ASR_AUDIO_BYTES,
): Promise<void> {
  const signal = getOperationSignal(callerSignal);
  throwIfAborted(signal);
  const target = path.resolve(destination);
  const requestDir = path.dirname(target);
  if (
    path.dirname(requestDir) !== path.resolve(os.tmpdir()) ||
    !isAsrRequestTempDir(requestDir) ||
    !createdAsrTempDirs.has(requestDir) ||
    path.basename(target) !== "audio.m4a"
  ) {
    throw new AsrError(
      "ASR_TRANSCRIPTION_FAILED",
      "Refused an unsafe ASR temporary audio path.",
    );
  }

  if (
    !Number.isSafeInteger(maxBytes) ||
    maxBytes <= 0 ||
    maxBytes > MAX_ASR_AUDIO_BYTES
  ) {
    throw new AsrError(
      "ASR_TRANSCRIPTION_FAILED",
      "Refused an invalid ASR audio byte budget.",
    );
  }

  let lastError: unknown;
  let attemptedCandidates = 0;
  let fakeIpDnsFailures = 0;
  const aggregateBudget = { remainingBytes: maxBytes };
  const controller = new AbortController();
  const unlinkAbort = linkAbortSignal(signal, controller);
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  try {
    for (const candidate of candidates.slice(0, 3)) {
      throwIfAborted(signal);
      attemptedCandidates += 1;
      try {
        await fs.promises.rm(destination, { force: true });
        const response = await fetchAudioResponse(candidate.url, controller.signal, fetchFn);
        await readBoundedBody(response, destination, aggregateBudget);
        return;
      } catch (error) {
        await fs.promises.rm(destination, { force: true });
        if (signal?.aborted) {
          throw createAbortError();
        }
        if (error instanceof AsrError && error.code === "ASR_LIMIT_EXCEEDED") {
          throw error;
        }
        if (error instanceof FakeIpDnsError) {
          fakeIpDnsFailures += 1;
        }
        if (
          timedOut &&
          error instanceof Error &&
          error.name === "AbortError"
        ) {
          lastError = new AsrError(
            "ASR_AUDIO_UNAVAILABLE",
            "The temporary audio download timed out.",
            true,
          );
        } else {
          lastError = error;
        }
      }
    }
  } finally {
    clearTimeout(timer);
    unlinkAbort();
    controller.abort();
  }

  if (attemptedCandidates > 0 && fakeIpDnsFailures === attemptedCandidates) {
    throw new AsrError(
      "ASR_FAKE_IP_DNS",
      "All temporary audio candidates resolved only to the standard Fake-IP range.",
    );
  }
  if (lastError instanceof AsrError) throw lastError;
  throw new AsrError(
    "ASR_AUDIO_UNAVAILABLE",
    "The temporary audio could not be retrieved.",
    true,
  );
}

function hasExactKeys(
  value: Record<string, unknown>,
  expected: string[],
): boolean {
  const actual = Object.keys(value).sort();
  return actual.length === expected.length &&
    actual.every((key, index) => key === [...expected].sort()[index]);
}

export function parseAsrNdjson(output: string): AsrTranscriptionResult {
  if (Buffer.byteLength(output, "utf8") > MAX_ASR_STDOUT_BYTES) {
    throw new AsrError("ASR_OUTPUT_INVALID", "Managed ASR output exceeded its limit.");
  }
  const lines = output.split("\n");
  if (lines.at(-1) === "") lines.pop();
  for (let index = 0; index < lines.length; index += 1) {
    lines[index] = lines[index].replace(/\r$/, "");
  }
  if (lines.some((line) => line.length === 0)) {
    throw new AsrError("ASR_OUTPUT_INVALID", "Managed ASR output contained an empty record.");
  }
  if (lines.length < 2 || lines.length > MAX_ASR_SEGMENTS + 2) {
    throw new AsrError("ASR_OUTPUT_INVALID", "Managed ASR output had an invalid record count.");
  }

  let records: Array<Record<string, unknown>>;
  try {
    records = lines.map((line) => {
      const parsed = JSON.parse(line) as unknown;
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
        throw new Error("record");
      }
      return parsed as Record<string, unknown>;
    });
  } catch {
    throw new AsrError("ASR_OUTPUT_INVALID", "Managed ASR output was not valid NDJSON.");
  }

  const meta = records[0];
  if (
    !hasExactKeys(meta, ["type", "language"]) ||
    meta.type !== "meta" ||
    !(
      meta.language === null ||
      (typeof meta.language === "string" &&
        meta.language.length > 0 &&
        meta.language.length <= 64)
    )
  ) {
    throw new AsrError("ASR_OUTPUT_INVALID", "Managed ASR metadata was invalid.");
  }

  const done = records.at(-1)!;
  if (
    !hasExactKeys(done, ["type", "count"]) ||
    done.type !== "done" ||
    typeof done.count !== "number" ||
    !Number.isInteger(done.count) ||
    done.count < 0
  ) {
    throw new AsrError("ASR_OUTPUT_INVALID", "Managed ASR completion record was invalid.");
  }

  const segmentRecords = records.slice(1, -1);
  if (segmentRecords.length !== done.count || segmentRecords.length > MAX_ASR_SEGMENTS) {
    throw new AsrError("ASR_OUTPUT_INVALID", "Managed ASR segment count was invalid.");
  }

  const segments: SubtitleBodyItem[] = [];
  let previousStart = -1;
  let totalChars = 0;
  for (const record of segmentRecords) {
    if (
      !hasExactKeys(record, ["type", "start", "end", "text"]) ||
      record.type !== "segment" ||
      typeof record.start !== "number" ||
      !Number.isFinite(record.start) ||
      record.start < 0 ||
      typeof record.end !== "number" ||
      !Number.isFinite(record.end) ||
      record.end < record.start ||
      record.start < previousStart ||
      typeof record.text !== "string" ||
      record.text.length === 0 ||
      record.text.length > 10_000
    ) {
      throw new AsrError("ASR_OUTPUT_INVALID", "Managed ASR segment data was invalid.");
    }
    previousStart = record.start;
    totalChars += record.text.length;
    if (totalChars > MAX_ASR_TRANSCRIPT_CHARS) {
      throw new AsrError("ASR_OUTPUT_INVALID", "Managed ASR transcript exceeded its text limit.");
    }
    segments.push({
      from: record.start,
      to: record.end,
      content: sanitizeRemoteText(record.text),
    });
  }

  return {
    language: typeof meta.language === "string" ? meta.language : undefined,
    segments,
  };
}

function killManagedRuntimeTree(child: ReturnType<typeof spawn>): void {
  if (process.platform !== "win32" && child.pid !== undefined) {
    try {
      process.kill(-child.pid, "SIGKILL");
      return;
    } catch {
      // Fall through to the direct child.
    }
  }
  child.kill("SIGKILL");
}

export async function runManagedAsrRuntime(
  pythonExecutable: string,
  modelPath: string,
  audioPath: string,
  options: {
    spawnFn?: typeof spawn;
    timeoutMs?: number;
    signal?: AbortSignal;
  } = {},
): Promise<AsrTranscriptionResult> {
  return new Promise((resolve, reject) => {
    const signal = getOperationSignal(options.signal);
    try {
      throwIfAborted(signal);
    } catch (error) {
      reject(error);
      return;
    }
    const spawnFn = options.spawnFn ?? spawn;
    const child = spawnFn(
      pythonExecutable,
      ["-I", "-c", PYTHON_SCRIPT, modelPath, audioPath],
      {
        env: buildAsrRuntimeEnv(process.env),
        shell: false,
        stdio: ["ignore", "pipe", "pipe"],
        windowsHide: true,
        detached: process.platform !== "win32",
      },
    );
    const stdout: Buffer[] = [];
    let stdoutBytes = 0;
    let stderr = "";
    let timedOut = false;
    let overflowed = false;
    let aborted = false;
    let settled = false;

    const finishReject = (error: unknown) => {
      if (settled) return;
      settled = true;
      reject(error);
    };
    const finishResolve = (result: AsrTranscriptionResult) => {
      if (settled) return;
      settled = true;
      resolve(result);
    };

    const onAbort = () => {
      aborted = true;
      killManagedRuntimeTree(child);
    };
    signal?.addEventListener("abort", onAbort, { once: true });

    const timer = setTimeout(() => {
      timedOut = true;
      killManagedRuntimeTree(child);
    }, options.timeoutMs ?? ASR_TRANSCRIPTION_TIMEOUT_MS);

    child.stdout?.on("data", (chunk: Buffer) => {
      stdoutBytes += chunk.byteLength;
      if (stdoutBytes > MAX_ASR_STDOUT_BYTES) {
        overflowed = true;
        killManagedRuntimeTree(child);
        return;
      }
      stdout.push(Buffer.from(chunk));
    });
    child.stderr?.on("data", (chunk: Buffer) => {
      stderr = (stderr + chunk.toString("utf8")).slice(-MAX_ASR_STDERR_BYTES);
    });
    child.once("error", (error) => {
      clearTimeout(timer);
      signal?.removeEventListener("abort", onAbort);
      finishReject(new AsrError(
        "ASR_TRANSCRIPTION_FAILED",
        `The managed ASR process could not start (${error.name}).`,
        true,
      ));
    });
    child.once("close", (code) => {
      clearTimeout(timer);
      signal?.removeEventListener("abort", onAbort);
      if (aborted || signal?.aborted) {
        finishReject(createAbortError());
        return;
      }
      if (timedOut) {
        finishReject(new AsrError(
          "ASR_TRANSCRIPTION_TIMEOUT",
          "Managed ASR exceeded the 30-minute time limit.",
          true,
        ));
        return;
      }
      if (overflowed) {
        finishReject(new AsrError("ASR_OUTPUT_INVALID", "Managed ASR output exceeded its limit."));
        return;
      }
      if (code !== 0) {
        void stderr;
        finishReject(new AsrError(
          "ASR_TRANSCRIPTION_FAILED",
          `Managed ASR exited unsuccessfully (code ${code ?? "unknown"}).`,
          true,
        ));
        return;
      }
      try {
        finishResolve(parseAsrNdjson(Buffer.concat(stdout).toString("utf8")));
      } catch (error) {
        finishReject(error);
      }
    });
  });
}

export async function createAsrTempDir(prefix: string): Promise<string> {
  if (prefix !== ASR_TEMP_PREFIX) {
    throw new AsrError(
      "ASR_TRANSCRIPTION_FAILED",
      "Refused an unsafe ASR temporary-directory prefix.",
    );
  }
  const tempDir = path.resolve(await fs.promises.mkdtemp(path.join(os.tmpdir(), prefix)));
  if (!isAsrRequestTempDir(tempDir)) {
    throw new AsrError(
      "ASR_TRANSCRIPTION_FAILED",
      "Failed to create a safe ASR temporary directory.",
    );
  }
  createdAsrTempDirs.add(tempDir);
  return tempDir;
}

export async function cleanupAsrTempDir(tempDir: string): Promise<void> {
  const tempRoot = path.resolve(os.tmpdir());
  const target = path.resolve(tempDir);
  if (
    path.dirname(target) !== tempRoot ||
    !isAsrRequestTempDir(target) ||
    !createdAsrTempDirs.has(target) ||
    target === tempRoot
  ) {
    throw new AsrError(
      "ASR_TRANSCRIPTION_FAILED",
      "Refused unsafe ASR temporary-directory cleanup.",
    );
  }
  try {
    const stat = await fs.promises.lstat(target);
    if (!stat.isDirectory() || stat.isSymbolicLink()) {
      throw new AsrError(
        "ASR_TRANSCRIPTION_FAILED",
        "Refused unsafe ASR temporary-directory cleanup.",
      );
    }
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      createdAsrTempDirs.delete(target);
      return;
    }
    throw error;
  }
  await fs.promises.rm(target, { recursive: true, force: true });
  createdAsrTempDirs.delete(target);
}

export async function transcribeVideoPart(
  request: AsrTranscriptionRequest,
  dependencies: AsrTranscriptionDependencies = {},
  callerSignal?: AbortSignal,
): Promise<AsrTranscriptionResult | null> {
  const signal = getOperationSignal(callerSignal);
  throwIfAborted(signal);
  if (activeTranscriptions >= 1) {
    throw new AsrError(
      "ASR_BUSY",
      "Another ASR transcription is already active. Retry after it finishes.",
      true,
    );
  }
  activeTranscriptions += 1;

  const getPaths = dependencies.getPaths ?? (() => deriveAsrPaths());
  const getState = dependencies.getState ?? ((stateFile: string) => readAsrState(stateFile));
  const getPlayback = dependencies.getPlayback ??
    (
      async (bvid: string, cid: number, operationSignal?: AbortSignal) =>
        await getPlaybackAudioSet(
          bvid,
          cid,
          undefined,
          operationSignal,
        )
    );
  const createTempDir = dependencies.createTempDir ?? createAsrTempDir;
  const removeTempDir = dependencies.removeTempDir ?? cleanupAsrTempDir;
  const downloadAudio = dependencies.downloadAudio ??
    (
      async (
        candidates: PlaybackAudioCandidate[],
        destination: string,
        operationSignal?: AbortSignal,
      ) => await downloadPlaybackAudio(
        candidates,
        destination,
        pinnedHttpsFetch,
        ASR_DOWNLOAD_TIMEOUT_MS,
        operationSignal,
      )
    );
  const runRuntime = dependencies.runRuntime ??
    (
      async (
        pythonExecutable: string,
        modelPath: string,
        audioPath: string,
        operationSignal?: AbortSignal,
      ) => await runManagedAsrRuntime(
        pythonExecutable,
        modelPath,
        audioPath,
        { signal: operationSignal },
      )
    );
  let tempDir: string | undefined;

  try {
    assertDuration(request.durationSeconds);
    throwIfAborted(signal);
    const paths = getPaths();
    const state = getState(paths.stateFile);
    if (state.kind !== "ready") {
      throw new AsrError(
        "ASR_NOT_READY",
        "Local ASR is not ready. Run `npx -y @xzxzzx/bilibili-mcp@latest setup`, then inspect `doctor --json`.",
      );
    }

    const playback = await getPlayback(request.bvid, request.cid, signal);
    throwIfAborted(signal);
    if (playback.durationSeconds !== undefined) {
      assertDuration(playback.durationSeconds);
    }
    if (playback.candidates.length === 0) {
      return null;
    }

    tempDir = await createTempDir(ASR_TEMP_PREFIX);
    throwIfAborted(signal);
    const audioPath = path.join(tempDir, "audio.m4a");
    await downloadAudio(playback.candidates, audioPath, signal);
    throwIfAborted(signal);
    return await runRuntime(
      managedPythonExecutable(paths.venv),
      paths.model,
      audioPath,
      signal,
    );
  } finally {
    try {
      if (tempDir !== undefined) {
        await removeTempDir(tempDir);
      }
    } finally {
      activeTranscriptions -= 1;
    }
  }
}
