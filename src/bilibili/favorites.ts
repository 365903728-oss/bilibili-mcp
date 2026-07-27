import { credentialManager } from "../utils/credentials.js";
import { BilibiliAPIError, ValidationError } from "../utils/errors.js";
import { isValidBVId } from "../utils/bvid.js";
import type {
  FavoriteFolder,
  FavoriteVideo,
  FavoriteVideoPage,
} from "./types.js";
import { fetchWithoutWBI } from "./http.js";

const NAV_PATH = "/x/web-interface/nav";
const FOLDERS_PATH = "/x/v3/fav/folder/created/list-all";
const RESOURCES_PATH = "/x/v3/fav/resource/list";
const PAGE_SIZE = 20;
const CURSOR_VERSION = 1;
const BASE64URL_RE = /^[A-Za-z0-9_-]+$/;

type UnknownRecord = Record<string, unknown>;

function createCredentialError(): BilibiliAPIError {
  return new BilibiliAPIError(
    'Current Bilibili credentials are expired or not logged in. Run "npx -y @xzxzzx/bilibili-mcp@latest config", then "npx -y @xzxzzx/bilibili-mcp@latest check", or update environment variables.',
    "COOKIE_EXPIRED",
  );
}

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isPositiveSafeInteger(value: unknown): value is number {
  return (
    typeof value === "number" &&
    Number.isSafeInteger(value) &&
    value > 0
  );
}

function toNonNegativeInteger(value: unknown): number | undefined {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
    return undefined;
  }
  return Math.trunc(value);
}

function toIsoFromUnixSeconds(value: unknown): string {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
    return "";
  }
  const date = new Date(value * 1_000);
  return Number.isNaN(date.getTime()) ? "" : date.toISOString();
}

function cleanText(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function base64urlEncode(value: string): string {
  const b64 = Buffer.from(value, "utf-8").toString("base64");
  return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function base64urlDecode(value: string): string {
  if (value.length % 4 === 1) {
    throw new Error("invalid base64url length");
  }
  const pad = value.length % 4 === 0 ? "" : "=".repeat(4 - (value.length % 4));
  const b64 = `${value}${pad}`.replace(/-/g, "+").replace(/_/g, "/");
  const decoded = Buffer.from(b64, "base64");
  const canonical = decoded
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
  if (canonical !== value) {
    throw new Error("non-canonical base64url");
  }
  return decoded.toString("utf-8");
}

export interface ResolvedCursor {
  folderId: number;
  page: number;
}

export function encodeFavoritesCursor(
  folderId: number,
  page: number,
): string {
  if (!isPositiveSafeInteger(folderId)) {
    throw new ValidationError(
      "cursor folder_id must be a positive safe integer",
    );
  }
  if (!isPositiveSafeInteger(page)) {
    throw new ValidationError("cursor page must be a positive safe integer");
  }
  const payload = {
    version: CURSOR_VERSION,
    folder_id: folderId,
    page,
  };
  return base64urlEncode(JSON.stringify(payload));
}

export function decodeFavoritesCursor(cursor: string): ResolvedCursor {
  if (typeof cursor !== "string") {
    throw new ValidationError("cursor must be a string");
  }
  if (cursor.length < 1 || cursor.length > 256) {
    throw new ValidationError("cursor length must be between 1 and 256");
  }
  if (!BASE64URL_RE.test(cursor)) {
    throw new ValidationError(
      "cursor must contain only base64url characters",
    );
  }

  let decoded: string;
  try {
    decoded = base64urlDecode(cursor);
  } catch {
    throw new ValidationError("cursor is not valid base64url");
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(decoded);
  } catch {
    throw new ValidationError("cursor is not valid JSON");
  }

  if (!isRecord(parsed)) {
    throw new ValidationError("cursor payload must be a JSON object");
  }
  if (parsed.version !== CURSOR_VERSION) {
    throw new ValidationError(
      `cursor version ${String(parsed.version)} is not supported`,
    );
  }
  if (!isPositiveSafeInteger(parsed.folder_id)) {
    throw new ValidationError(
      "cursor folder_id must be a positive safe integer",
    );
  }
  if (!isPositiveSafeInteger(parsed.page)) {
    throw new ValidationError("cursor page must be a positive safe integer");
  }

  return { folderId: parsed.folder_id, page: parsed.page };
}

function normalizeFolder(
  row: unknown,
  authenticatedMid: number,
): FavoriteFolder | undefined {
  if (!isRecord(row)) return undefined;
  if (!isPositiveSafeInteger(row.id)) return undefined;
  if (typeof row.title !== "string") return undefined;
  const mediaCount = toNonNegativeInteger(row.media_count);
  if (mediaCount === undefined) return undefined;
  if (row.mid !== undefined && row.mid !== authenticatedMid) {
    return undefined;
  }
  return {
    id: row.id,
    title: row.title,
    media_count: mediaCount,
  };
}

function normalizeFolderList(
  data: unknown,
  authenticatedMid: number,
): FavoriteFolder[] {
  if (!isRecord(data) || !Array.isArray(data.list)) return [];
  const folders: FavoriteFolder[] = [];
  for (const row of data.list) {
    const folder = normalizeFolder(row, authenticatedMid);
    if (folder) folders.push(folder);
  }
  return folders;
}

function normalizeVideo(row: unknown): FavoriteVideo | undefined {
  if (!isRecord(row)) return undefined;

  const bvid =
    typeof row.bvid === "string" && isValidBVId(row.bvid)
      ? row.bvid
      : typeof row.bv_id === "string" && isValidBVId(row.bv_id)
        ? row.bv_id
        : undefined;
  if (!bvid) return undefined;

  const title = cleanText(row.title);
  if (!title) return undefined;

  const upper = isRecord(row.upper) ? row.upper : undefined;
  const author = cleanText(upper?.name);
  const duration = toNonNegativeInteger(row.duration) ?? 0;

  return {
    bvid,
    title,
    author,
    duration_seconds: duration,
    published_at: toIsoFromUnixSeconds(row.pubtime),
    favorited_at: toIsoFromUnixSeconds(row.fav_time),
    source_url: `https://www.bilibili.com/video/${bvid}/`,
  };
}

interface NormalizedResourcePage {
  videos: FavoriteVideo[];
  hasMore: boolean;
  skippedCount: number;
  isEmptyPage: boolean;
}

function normalizeVideoPage(data: unknown): NormalizedResourcePage {
  if (!isRecord(data) || !Array.isArray(data.medias)) {
    return {
      videos: [],
      hasMore: false,
      skippedCount: 0,
      isEmptyPage: true,
    };
  }
  const videos: FavoriteVideo[] = [];
  let skippedCount = 0;
  for (const row of data.medias) {
    const video = normalizeVideo(row);
    if (video) {
      videos.push(video);
    } else {
      skippedCount += 1;
    }
  }
  return {
    videos,
    hasMore: data.has_more === true,
    skippedCount,
    isEmptyPage: data.medias.length === 0,
  };
}

function createStaleCursorError(): ValidationError {
  return new ValidationError(
    "cursor folder no longer belongs to the current account; restart without a cursor",
  );
}

async function fetchAuthenticatedMid(
  authHeaders: Record<string, string>,
): Promise<number> {
  const data = await fetchWithoutWBI(NAV_PATH, undefined, authHeaders);
  if (!isRecord(data) || data.isLogin !== true) {
    throw createCredentialError();
  }
  if (!isPositiveSafeInteger(data.mid)) {
    throw createCredentialError();
  }
  return data.mid;
}

export async function listBilibiliFavoriteVideos(
  cursor?: string,
): Promise<FavoriteVideoPage> {
  let startFolderId: number | undefined;
  let startPage: number | undefined;
  if (cursor !== undefined) {
    const resolved = decodeFavoritesCursor(cursor);
    startFolderId = resolved.folderId;
    startPage = resolved.page;
  }

  const authHeaders = credentialManager.getAuthHeaders();
  if (
    typeof authHeaders.Cookie !== "string" ||
    authHeaders.Cookie.trim().length === 0
  ) {
    throw createCredentialError();
  }

  const authenticatedMid = await fetchAuthenticatedMid(authHeaders);

  const folderListData = await fetchWithoutWBI(
    FOLDERS_PATH,
    { up_mid: authenticatedMid },
    authHeaders,
  );

  const folders = normalizeFolderList(folderListData, authenticatedMid);

  if (folders.length === 0) {
    if (startFolderId !== undefined) {
      throw createStaleCursorError();
    }
    return {
      folders_total: 0,
      videos: [],
      skipped_count: 0,
    };
  }

  let folderIndex = 0;
  let page = 1;
  if (startFolderId !== undefined && startPage !== undefined) {
    const idx = folders.findIndex((folder) => folder.id === startFolderId);
    if (idx < 0) {
      throw createStaleCursorError();
    }
    folderIndex = idx;
    page = startPage;
  }

  const currentFolder = folders[folderIndex];

  const resourceData = await fetchWithoutWBI(
    RESOURCES_PATH,
    {
      media_id: currentFolder.id,
      pn: page,
      ps: PAGE_SIZE,
      keyword: "",
      order: "mtime",
      type: 0,
      tid: 0,
      platform: "web",
    },
    authHeaders,
  );

  const {
    videos,
    hasMore,
    skippedCount,
    isEmptyPage,
  } = normalizeVideoPage(resourceData);

  let nextCursor: string | undefined;
  if (isEmptyPage) {
    if (folderIndex + 1 < folders.length) {
      nextCursor = encodeFavoritesCursor(folders[folderIndex + 1].id, 1);
    }
  } else if (hasMore) {
    nextCursor = encodeFavoritesCursor(currentFolder.id, page + 1);
  } else if (folderIndex + 1 < folders.length) {
    nextCursor = encodeFavoritesCursor(folders[folderIndex + 1].id, 1);
  }

  const result: FavoriteVideoPage = {
    folders_total: folders.length,
    folder: {
      id: currentFolder.id,
      title: currentFolder.title,
      media_count: currentFolder.media_count,
    },
    page,
    videos,
    skipped_count: skippedCount,
  };
  if (nextCursor) {
    result.next_cursor = nextCursor;
  }
  return result;
}
