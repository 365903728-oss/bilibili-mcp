import { credentialManager } from "../utils/credentials.js";
import {
  BilibiliAPIError,
  ResourceLimitError,
  UpstreamResponseError,
} from "../utils/errors.js";
import {
  abortableDelay,
  getOperationSignal,
  throwIfAborted,
} from "../security/operation-context.js";
import { isValidBVId } from "../utils/bvid.js";
import type {
  CreatorSearchCandidate,
  CreatorSearchData,
  VideoSearchCandidate,
  VideoSearchData,
} from "./types.js";
import { checkLoginStatus, fetchWithoutWBI } from "./http.js";
import {
  boundedRemoteText,
  truncateUtf8,
} from "../utils/bounded-text.js";

const VIDEO_SEARCH_PATH = "/x/web-interface/wbi/search/type";
const VIDEO_SEARCH_TYPE = "video";
const CREATOR_SEARCH_TYPE = "bili_user";
const MAX_SEARCH_ROWS = 100;
const MAX_SEARCH_TITLE_BYTES = 512;
const MAX_SEARCH_AUTHOR_BYTES = 128;
const MAX_SEARCH_DESCRIPTION_BYTES = 512;
const MAX_CREATOR_NAME_BYTES = 128;
const MAX_CREATOR_BIO_BYTES = 512;
const MAX_CREATOR_AVATAR_BYTES = 512;
const SEARCH_SHAPE_RETRY_DELAY_MS = 500;

type UnknownRecord = Record<string, unknown>;

function createCredentialError(): BilibiliAPIError {
  return new BilibiliAPIError(
    'Current Bilibili credentials are expired or not logged in. Run "npx -y @xzxzzx/bilibili-mcp@latest config", then "npx -y @xzxzzx/bilibili-mcp@latest check", or update environment variables.',
    "COOKIE_EXPIRED",
  );
}

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null;
}

function cleanSearchText(value: unknown, maxBytes: number): string {
  if (typeof value !== "string") return "";
  const prebounded = truncateUtf8(value, Math.max(maxBytes * 4, 2_048), "");
  return boundedRemoteText(
    prebounded.replace(/<\/?em\b[^>]*>/gi, ""),
    maxBytes,
  );
}

function parseDurationSeconds(value: unknown): number {
  if (typeof value !== "string") return 0;

  const parts = value.trim().split(":");
  if (
    (parts.length !== 2 && parts.length !== 3) ||
    parts.some((part) => !/^\d+$/.test(part))
  ) {
    return 0;
  }

  const values = parts.map(Number);
  if (values.some((part) => !Number.isSafeInteger(part))) return 0;

  if (parts.length === 2) {
    const [minutes, seconds] = values;
    if (seconds >= 60) return 0;
    const total = minutes * 60 + seconds;
    return Number.isSafeInteger(total) ? total : 0;
  }

  const [hours, minutes, seconds] = values;
  if (minutes >= 60 || seconds >= 60) return 0;
  const total = hours * 3_600 + minutes * 60 + seconds;
  return Number.isSafeInteger(total) ? total : 0;
}

function toPublishedAt(value: unknown): string {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
    return "";
  }

  const date = new Date(value * 1_000);
  return Number.isNaN(date.getTime()) ? "" : date.toISOString();
}

function toViewCount(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
    return 0;
  }
  return Math.trunc(value);
}

// Creator profile facts are identity-adjacent and must never truncate or
// widen: only non-negative safe integers are accepted, everything else is 0.
function toNonNegativeSafeInteger(value: unknown): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0) {
    return 0;
  }
  return value;
}

function truncateDescription(value: unknown): string {
  return cleanSearchText(value, MAX_SEARCH_DESCRIPTION_BYTES);
}

function normalizeCandidate(value: unknown): VideoSearchCandidate | undefined {
  if (!isRecord(value) || value.type !== "video") return undefined;
  if (typeof value.bvid !== "string" || !isValidBVId(value.bvid)) {
    return undefined;
  }

  const title = cleanSearchText(value.title, MAX_SEARCH_TITLE_BYTES);
  if (!title) return undefined;

  return {
    bvid: value.bvid,
    title,
    author: cleanSearchText(value.author, MAX_SEARCH_AUTHOR_BYTES),
    duration_seconds: parseDurationSeconds(value.duration),
    published_at: toPublishedAt(value.pubdate),
    view_count: toViewCount(value.play),
    description: truncateDescription(value.description),
    source_url: `https://www.bilibili.com/video/${value.bvid}/`,
  };
}

async function fetchSearchRows(
  query: string,
  limit: number,
  authHeaders: Record<string, string>,
  searchType: string,
  invalidResponseMessage: string,
): Promise<unknown[]> {
  const signal = getOperationSignal();
  const params = {
    search_type: searchType,
    keyword: query,
    page: 1,
    page_size: limit,
  };

  for (let attempt = 0; attempt < 2; attempt++) {
    throwIfAborted(signal);
    const data = await fetchWithoutWBI(
      VIDEO_SEARCH_PATH,
      params,
      authHeaders,
    );
    if (isRecord(data) && Array.isArray(data.result)) {
      return data.result;
    }
    if (attempt === 0) {
      await abortableDelay(SEARCH_SHAPE_RETRY_DELAY_MS, signal);
    }
  }

  throw new UpstreamResponseError(invalidResponseMessage);
}

export async function searchBilibiliVideos(
  query: string,
  limit = 5,
): Promise<VideoSearchData> {
  const normalizedQuery = query.trim();
  const authHeaders = credentialManager.getAuthHeaders();

  if (
    typeof authHeaders.Cookie !== "string" ||
    authHeaders.Cookie.trim().length === 0
  ) {
    throw createCredentialError();
  }

  const loginStatus = await checkLoginStatus();
  if (!loginStatus.isLogin) {
    throw createCredentialError();
  }

  const rows = await fetchSearchRows(
    normalizedQuery,
    limit,
    authHeaders,
    VIDEO_SEARCH_TYPE,
    "Bilibili returned an invalid video search response",
  );

  if (rows.length > MAX_SEARCH_ROWS) {
    throw new ResourceLimitError(
      "Video search response exceeded its item limit",
      "video_search_items",
      MAX_SEARCH_ROWS,
    );
  }
  const results: VideoSearchCandidate[] = [];

  for (const row of rows) {
    const candidate = normalizeCandidate(row);
    if (candidate) results.push(candidate);
    if (results.length === limit) break;
  }

  return {
    query: normalizedQuery,
    results,
  };
}

function toPositiveMid(value: unknown): number | undefined {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value <= 0) {
    return undefined;
  }
  return value;
}

function normalizeCreatorCandidate(
  value: unknown,
): CreatorSearchCandidate | undefined {
  if (!isRecord(value)) return undefined;
  const mid = toPositiveMid(value.mid);
  const name = cleanSearchText(value.uname, MAX_CREATOR_NAME_BYTES);
  if (mid === undefined || !name) return undefined;

  return {
    mid,
    name,
    bio: cleanSearchText(value.usign, MAX_CREATOR_BIO_BYTES),
    avatar_url: cleanSearchText(value.upic, MAX_CREATOR_AVATAR_BYTES),
    follower_count: toNonNegativeSafeInteger(value.fans),
    video_count: toNonNegativeSafeInteger(value.videos),
    level: toNonNegativeSafeInteger(value.level),
    source_url: `https://space.bilibili.com/${mid}/`,
  };
}

export async function searchBilibiliCreators(
  query: string,
  limit = 5,
): Promise<CreatorSearchData> {
  const normalizedQuery = query.trim();
  const authHeaders = credentialManager.getAuthHeaders();

  if (
    typeof authHeaders.Cookie !== "string" ||
    authHeaders.Cookie.trim().length === 0
  ) {
    throw createCredentialError();
  }

  const loginStatus = await checkLoginStatus();
  if (!loginStatus.isLogin) {
    throw createCredentialError();
  }

  const rows = await fetchSearchRows(
    normalizedQuery,
    limit,
    authHeaders,
    CREATOR_SEARCH_TYPE,
    "Bilibili returned an invalid creator search response",
  );

  if (rows.length > MAX_SEARCH_ROWS) {
    throw new ResourceLimitError(
      "Creator search response exceeded its item limit",
      "creator_search_items",
      MAX_SEARCH_ROWS,
    );
  }
  const results: CreatorSearchCandidate[] = [];

  for (const row of rows) {
    const candidate = normalizeCreatorCandidate(row);
    if (candidate) results.push(candidate);
    if (results.length === limit) break;
  }

  return {
    query: normalizedQuery,
    results,
  };
}
