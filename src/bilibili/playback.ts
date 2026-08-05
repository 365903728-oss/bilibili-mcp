import { config } from "../config.js";
import { SECURITY_LIMITS } from "../security/limits.js";
import { credentialManager } from "../utils/credentials.js";
import { AsrError } from "../utils/errors.js";
import { fetchWithoutWBI } from "./http.js";

export const MAX_ASR_DURATION_SECONDS = 7_200;
export const MAX_AUDIO_URL_CANDIDATES = 3;
export const MAX_AUDIO_REPRESENTATIONS = 256;
export const MAX_BACKUP_AUDIO_URLS = 8;

const ALLOWED_MEDIA_HOST_SUFFIXES = [
  ".bilivideo.com",
  ".bilivideo.cn",
] as const;

export interface PlaybackAudioCandidate {
  url: string;
  mimeType: string;
  bandwidth: number;
  representationId: number;
}

export interface PlaybackAudioSet {
  candidates: PlaybackAudioCandidate[];
  durationSeconds?: number;
}

type FetchPlayurl = (
  path: string,
  params: Record<string, string | number>,
  headers?: Record<string, string>,
  signal?: AbortSignal,
  maxResponseBytes?: number,
) => Promise<unknown>;

interface DashAudioRepresentation {
  id?: unknown;
  bandwidth?: unknown;
  mimeType?: unknown;
  mime_type?: unknown;
  codecs?: unknown;
  baseUrl?: unknown;
  base_url?: unknown;
  backupUrl?: unknown;
  backup_url?: unknown;
}

function isAllowedMediaHost(hostname: string): boolean {
  const normalized = hostname.toLowerCase();
  return ALLOWED_MEDIA_HOST_SUFFIXES.some(
    (suffix) => normalized === suffix.slice(1) || normalized.endsWith(suffix),
  );
}

export function validatePlaybackMediaUrl(value: unknown): string {
  if (typeof value !== "string" || value.length === 0 || value.length > 8_192) {
    throw new AsrError(
      "ASR_AUDIO_UNAVAILABLE",
      "Bilibili returned an invalid temporary audio location.",
      true,
    );
  }

  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    throw new AsrError(
      "ASR_AUDIO_UNAVAILABLE",
      "Bilibili returned an invalid temporary audio location.",
      true,
    );
  }

  if (
    parsed.protocol !== "https:" ||
    parsed.port !== "" ||
    parsed.username !== "" ||
    parsed.password !== "" ||
    !isAllowedMediaHost(parsed.hostname)
  ) {
    throw new AsrError(
      "ASR_AUDIO_UNAVAILABLE",
      "Bilibili returned an unsupported temporary audio location.",
      true,
    );
  }

  return parsed.toString();
}

function parseDurationSeconds(value: unknown): number | undefined {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
    return undefined;
  }
  const durationSeconds = value / 1_000;
  if (durationSeconds > MAX_ASR_DURATION_SECONDS) {
    throw new AsrError(
      "ASR_LIMIT_EXCEEDED",
      `The selected Part exceeds the ${MAX_ASR_DURATION_SECONDS}-second ASR limit.`,
    );
  }
  return durationSeconds;
}

function isSupportedAudioRepresentation(
  representation: DashAudioRepresentation,
): boolean {
  const mimeType =
    typeof representation.mimeType === "string"
      ? representation.mimeType
      : representation.mime_type;
  const codecs = representation.codecs;
  return (
    (mimeType === "audio/mp4" || mimeType === "audio/m4a") &&
    mimeType.length <= 64 &&
    typeof codecs === "string" &&
    codecs.length <= 128 &&
    codecs.toLowerCase().startsWith("mp4a")
  );
}

export function parsePlaybackAudioSet(raw: unknown): PlaybackAudioSet {
  if (typeof raw !== "object" || raw === null) {
    throw new AsrError(
      "ASR_AUDIO_UNAVAILABLE",
      "Bilibili returned an invalid playback response.",
      true,
    );
  }

  const response = raw as {
    timelength?: unknown;
    dash?: { audio?: unknown };
  };
  const durationSeconds = parseDurationSeconds(response.timelength);

  if (typeof response.dash !== "object" || response.dash === null) {
    throw new AsrError(
      "ASR_AUDIO_UNAVAILABLE",
      "Bilibili returned a playback response without DASH audio metadata.",
      true,
    );
  }
  if (!Array.isArray(response.dash.audio)) {
    throw new AsrError(
      "ASR_AUDIO_UNAVAILABLE",
      "Bilibili returned an invalid audio representation list.",
      true,
    );
  }
  if (response.dash.audio.length > MAX_AUDIO_REPRESENTATIONS) {
    throw new AsrError(
      "ASR_LIMIT_EXCEEDED",
      "Bilibili returned too many audio representations.",
      true,
    );
  }
  if (response.dash.audio.length === 0) {
    return { candidates: [], durationSeconds };
  }

  const supported = (response.dash.audio as unknown[])
    .filter((entry): entry is DashAudioRepresentation => {
      if (typeof entry !== "object" || entry === null) return false;
      const representation = entry as DashAudioRepresentation;
      return (
        typeof representation.id === "number" &&
        Number.isInteger(representation.id) &&
        typeof representation.bandwidth === "number" &&
        Number.isFinite(representation.bandwidth) &&
        representation.bandwidth > 0 &&
        isSupportedAudioRepresentation(representation)
      );
    })
    .sort((left, right) => {
      return (
        (left.bandwidth as number) - (right.bandwidth as number) ||
        (left.id as number) - (right.id as number)
      );
    });

  if (supported.length === 0) {
    throw new AsrError(
      "ASR_AUDIO_UNAVAILABLE",
      "Bilibili did not return a supported MP4/AAC audio representation.",
    );
  }

  const selected = supported[0];
  const mimeType = (selected.mimeType ?? selected.mime_type) as string;
  const backupUrls = Array.isArray(selected.backupUrl)
    ? selected.backupUrl
    : Array.isArray(selected.backup_url)
      ? selected.backup_url
      : [];
  const rawUrls: unknown[] = [
    selected.baseUrl ?? selected.base_url,
    ...backupUrls.slice(0, MAX_BACKUP_AUDIO_URLS),
  ];

  const candidates: PlaybackAudioCandidate[] = [];
  const seen = new Set<string>();
  for (const rawUrl of rawUrls.slice(0, MAX_AUDIO_URL_CANDIDATES)) {
    let url: string;
    try {
      url = validatePlaybackMediaUrl(rawUrl);
    } catch (error) {
      if (error instanceof AsrError) continue;
      throw error;
    }
    if (seen.has(url)) continue;
    seen.add(url);
    candidates.push({
      url,
      mimeType,
      bandwidth: selected.bandwidth as number,
      representationId: selected.id as number,
    });
  }

  if (candidates.length === 0) {
    throw new AsrError(
      "ASR_AUDIO_UNAVAILABLE",
      "Bilibili did not return a usable temporary audio location.",
      true,
    );
  }

  return { candidates, durationSeconds };
}

export async function getPlaybackAudioSet(
  bvid: string,
  cid: number,
  fetchPlayurl: FetchPlayurl = fetchWithoutWBI,
  signal?: AbortSignal,
): Promise<PlaybackAudioSet> {
  const response = await fetchPlayurl(
    "/x/player/playurl",
    {
      bvid,
      cid,
      fnval: 16,
      fnver: 0,
      fourk: 1,
    },
    {
      ...credentialManager.getAuthHeaders(),
      "User-Agent": config.userAgent,
      Referer: config.referer,
    },
    signal,
    SECURITY_LIMITS.playbackJsonBytes,
  );

  return parsePlaybackAudioSet(response);
}
