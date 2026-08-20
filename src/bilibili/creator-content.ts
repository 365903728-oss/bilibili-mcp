import { credentialManager } from "../utils/credentials.js";
import {
  BilibiliAPIError,
  ResourceLimitError,
  UpstreamResponseError,
  ValidationError,
} from "../utils/errors.js";
import { isValidBVId } from "../utils/bvid.js";
import type {
  CreatorCollectionContainer,
  CreatorCollectionListPage,
  CreatorCollectionMemberPage,
  CreatorContainerVideoRow,
  CreatorContentOverview,
  CreatorContentSection,
  CreatorSeriesContainer,
  CreatorSeriesListPage,
  CreatorSeriesMemberPage,
  CreatorVideoPage,
  CreatorVideoRow,
} from "./types.js";
import { checkLoginStatus, fetchWithoutWBI, fetchWithWBI } from "./http.js";
import { boundedRemoteText } from "../utils/bounded-text.js";

const PROFILE_PATH = "/x/space/wbi/acc/info";
const CATALOG_PATH = "/x/space/wbi/arc/search";
const CONTAINER_LIST_PATH = "/x/polymer/web-space/seasons_series_list";
const COLLECTION_MEMBERS_PATH = "/x/polymer/web-space/seasons_archives_list";
const SERIES_METADATA_PATH = "/x/series/series";
const SERIES_MEMBERS_PATH = "/x/series/archives";
const PAGE_SIZE = 20;
const CURSOR_VERSION = 1;
const BASE64URL_RE = /^[A-Za-z0-9_-]+$/;
export const MAX_CREATOR_NAME_BYTES = 128;
export const MAX_CREATOR_BIO_BYTES = 512;
export const MAX_CREATOR_AVATAR_BYTES = 512;
export const MAX_CATALOG_TITLE_BYTES = 512;
export const MAX_CATALOG_DESCRIPTION_BYTES = 512;
export const MAX_CATALOG_COVER_BYTES = 512;
export const MAX_CATALOG_CATEGORY_BYTES = 64;
export const MAX_CATALOG_AUTHOR_BYTES = 128;
export const MAX_CONTAINER_NAME_BYTES = 128;
export const MAX_CONTAINER_DESCRIPTION_BYTES = 512;

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

function isCreatorContentSection(value: unknown): value is CreatorContentSection {
  return (
    value === "overview" ||
    value === "videos" ||
    value === "collections" ||
    value === "series"
  );
}

function toNonNegativeSafeInteger(value: unknown): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0) {
    return 0;
  }
  return value;
}

function toOptionalNonNegativeCount(value: unknown): number | undefined {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0) {
    return undefined;
  }
  return value;
}

function toOptionalPositiveInteger(value: unknown): number | undefined {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value <= 0) {
    return undefined;
  }
  return value;
}

function toIsoFromUnixSeconds(value: unknown): string {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
    return "";
  }
  const date = new Date(value * 1_000);
  return Number.isNaN(date.getTime()) ? "" : date.toISOString();
}

// 上游 length 为有界人类可读时长（"M:SS" 或 "H:MM:SS"，分钟可大于 59）。
// 畸形或超界时返回 undefined，由调用方回退到保守值。
function parseDurationSeconds(value: unknown): number | undefined {
  if (typeof value !== "string") return undefined;
  const parts = value.split(":");
  if (parts.length < 2 || parts.length > 3) return undefined;
  const nums: number[] = [];
  for (const part of parts) {
    if (!/^\d+$/.test(part)) return undefined;
    const n = Number(part);
    if (!Number.isSafeInteger(n)) return undefined;
    nums.push(n);
  }
  const total =
    nums.length === 2 ? nums[0] * 60 + nums[1] : nums[0] * 3600 + nums[1] * 60 + nums[2];
  return Number.isSafeInteger(total) && total >= 0 ? total : undefined;
}

// 发布时间以 created 为准，create 仅作兼容回退。
function toIsoFromCreated(value: unknown, fallback: unknown): string {
  if (typeof value === "number" && Number.isFinite(value) && value > 0) {
    return toIsoFromUnixSeconds(value);
  }
  return toIsoFromUnixSeconds(fallback);
}

// 显式真值证据：布尔 true 或正整数（Bilibili 的 0/1 与枚举型标记）。
// 字符串或负值不算显式证据，避免把非事实值当作付费标记。
function isExplicitTruthy(value: unknown): boolean {
  return (
    value === true ||
    (typeof value === "number" && Number.isSafeInteger(value) && value > 0)
  );
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

export interface ResolvedCreatorContentCursor {
  mid: number;
  section: CreatorContentSection;
  page: number;
  container_id?: number;
}

export function encodeCreatorContentCursor(
  mid: number,
  section: CreatorContentSection,
  page: number,
  containerId?: number,
): string {
  if (!isPositiveSafeInteger(mid)) {
    throw new ValidationError("cursor mid must be a positive safe integer");
  }
  if (!isCreatorContentSection(section)) {
    throw new ValidationError("cursor section is not supported");
  }
  if (!isPositiveSafeInteger(page)) {
    throw new ValidationError("cursor page must be a positive safe integer");
  }
  if (containerId !== undefined) {
    if (!isPositiveSafeInteger(containerId)) {
      throw new ValidationError(
        "cursor container_id must be a positive safe integer",
      );
    }
    if (section !== "collections" && section !== "series") {
      throw new ValidationError(
        "cursor container_id is only supported for collections or series",
      );
    }
  }
  const payload = {
    version: CURSOR_VERSION,
    mid,
    section,
    page,
    ...(containerId === undefined ? {} : { container_id: containerId }),
  };
  return base64urlEncode(JSON.stringify(payload));
}

export function decodeCreatorContentCursor(
  cursor: string,
): ResolvedCreatorContentCursor {
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
  if (!isPositiveSafeInteger(parsed.mid)) {
    throw new ValidationError(
      "cursor mid must be a positive safe integer",
    );
  }
  if (!isCreatorContentSection(parsed.section)) {
    throw new ValidationError("cursor section is not supported");
  }
  if (!isPositiveSafeInteger(parsed.page)) {
    throw new ValidationError("cursor page must be a positive safe integer");
  }
  if (!Number.isSafeInteger(parsed.page * PAGE_SIZE)) {
    throw new ValidationError("cursor page is unsafe");
  }

  let containerId: number | undefined;
  if (parsed.container_id !== undefined) {
    if (!isPositiveSafeInteger(parsed.container_id)) {
      throw new ValidationError(
        "cursor container_id must be a positive safe integer",
      );
    }
    if (parsed.section !== "collections" && parsed.section !== "series") {
      throw new ValidationError(
        "cursor container_id is only supported for collections or series",
      );
    }
    containerId = parsed.container_id;
  }

  return {
    mid: parsed.mid,
    section: parsed.section,
    page: parsed.page,
    ...(containerId === undefined ? {} : { container_id: containerId }),
  };
}

export async function getBilibiliCreatorContent(
  mid: number,
  section: CreatorContentSection,
  cursor?: string,
  containerId?: number,
): Promise<
  | CreatorContentOverview
  | CreatorVideoPage
  | CreatorCollectionListPage
  | CreatorCollectionMemberPage
  | CreatorSeriesListPage
  | CreatorSeriesMemberPage
> {
  if (!isPositiveSafeInteger(mid)) {
    throw new ValidationError("mid must be a positive safe integer");
  }
  if (!isCreatorContentSection(section)) {
    throw new ValidationError("section is not supported");
  }
  if (containerId !== undefined) {
    if (!isPositiveSafeInteger(containerId)) {
      throw new ValidationError(
        "container_id must be a positive safe integer",
      );
    }
    if (section !== "collections" && section !== "series") {
      throw new ValidationError(
        "container_id is only supported for collections or series",
      );
    }
  }
  let page = 1;
  if (section === "overview") {
    if (cursor !== undefined) {
      throw new ValidationError(
        "cursor is not supported for the overview section",
      );
    }
  } else if (cursor !== undefined) {
    const resolved = decodeCreatorContentCursor(cursor);
    if (resolved.mid !== mid) {
      throw new ValidationError("cursor belongs to a different creator mid");
    }
    if (resolved.section !== section) {
      throw new ValidationError("cursor belongs to a different section");
    }
    if (resolved.container_id !== containerId) {
      throw new ValidationError("cursor belongs to a different container");
    }
    page = resolved.page;
  }

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

  if (section === "overview") {
    return fetchCreatorOverview(mid, authHeaders);
  }
  if (
    (section === "collections" || section === "series") &&
    containerId === undefined
  ) {
    return fetchCreatorContainerListPage(mid, section, page, authHeaders);
  }
  if (section === "collections" && containerId !== undefined) {
    return fetchCreatorCollectionMemberPage(
      mid,
      containerId,
      page,
      authHeaders,
    );
  }
  if (section === "series" && containerId !== undefined) {
    return fetchCreatorSeriesMemberPage(mid, containerId, page, authHeaders);
  }
  return fetchCreatorVideoPage(mid, page, authHeaders);
}

function normalizeContainerVideoRow(
  value: unknown,
): CreatorContainerVideoRow | undefined {
  if (!isRecord(value)) return undefined;
  const bvid =
    typeof value.bvid === "string" && isValidBVId(value.bvid)
      ? value.bvid
      : undefined;
  if (!bvid || typeof value.title !== "string") return undefined;
  if (Buffer.byteLength(value.title, "utf8") > MAX_CATALOG_TITLE_BYTES) {
    throw new ResourceLimitError(
      "Creator container Video title exceeded its byte limit",
      "creator_container_video_title",
      MAX_CATALOG_TITLE_BYTES,
    );
  }
  const title = boundedRemoteText(value.title, MAX_CATALOG_TITLE_BYTES);
  if (!title) return undefined;
  const result: CreatorContainerVideoRow = {
    bvid,
    title,
    description: boundedRemoteText(
      value.desc ?? value.description,
      MAX_CATALOG_DESCRIPTION_BYTES,
    ),
    cover_url: boundedRemoteText(value.pic, MAX_CATALOG_COVER_BYTES),
    duration_seconds: toNonNegativeSafeInteger(value.duration),
    published_at: toIsoFromCreated(value.pubdate, value.ctime),
    access: "unknown",
    source_url: `https://www.bilibili.com/video/${bvid}/`,
  };
  if (isRecord(value.stat)) {
    const viewCount = toOptionalNonNegativeCount(value.stat.view);
    if (viewCount !== undefined) result.view_count = viewCount;
    const danmakuCount = toOptionalNonNegativeCount(value.stat.danmaku);
    if (danmakuCount !== undefined) result.danmaku_count = danmakuCount;
  }
  if (
    isExplicitTruthy(value.ugc_pay) ||
    isExplicitTruthy(value.is_charge_video)
  ) {
    result.is_charge_video = true;
  }
  return result;
}

async function fetchCreatorCollectionMemberPage(
  mid: number,
  collectionId: number,
  page: number,
  authHeaders: Record<string, string>,
): Promise<CreatorCollectionMemberPage> {
  const data = await fetchWithoutWBI(
    COLLECTION_MEMBERS_PATH,
    {
      mid,
      season_id: collectionId,
      sort_reverse: "false",
      page_num: page,
      page_size: PAGE_SIZE,
    },
    authHeaders,
  );
  if (
    !isRecord(data) ||
    !isRecord(data.meta) ||
    !isRecord(data.page) ||
    !Array.isArray(data.archives)
  ) {
    throw new UpstreamResponseError(
      "Bilibili returned an invalid Creator Collection member response",
    );
  }
  const selectedCollection = normalizeCollectionContainer(
    { meta: data.meta },
    mid,
  );
  if (
    selectedCollection === undefined ||
    selectedCollection.collection_id !== collectionId
  ) {
    throw new UpstreamResponseError(
      "Bilibili returned a different Creator Collection",
    );
  }
  const pageNumber = toOptionalPositiveInteger(data.page.page_num);
  const pageSize = toOptionalPositiveInteger(data.page.page_size);
  const total = toOptionalNonNegativeCount(data.page.total);
  if (pageNumber !== page || pageSize !== PAGE_SIZE || total === undefined) {
    throw new UpstreamResponseError(
      "Bilibili returned invalid Creator Collection page facts",
    );
  }
  if (data.archives.length > PAGE_SIZE) {
    throw new ResourceLimitError(
      "Creator Collection member page exceeded its item limit",
      "creator_collection_member_items",
      PAGE_SIZE,
    );
  }

  const members: CreatorContainerVideoRow[] = [];
  let skippedCount = 0;
  for (const value of data.archives) {
    const video = normalizeContainerVideoRow(value);
    if (video) members.push(video);
    else skippedCount += 1;
  }
  const result: CreatorCollectionMemberPage = {
    mid,
    section: "collections",
    mode: "members",
    page,
    selected_collection: selectedCollection,
    members,
    skipped_count: skippedCount,
    live_state: "live",
  };
  const nextPage = page + 1;
  if (
    page * PAGE_SIZE < total &&
    Number.isSafeInteger(nextPage) &&
    Number.isSafeInteger(nextPage * PAGE_SIZE)
  ) {
    result.next_cursor = encodeCreatorContentCursor(
      mid,
      "collections",
      nextPage,
      collectionId,
    );
  }
  return result;
}

async function fetchCreatorSeriesMemberPage(
  mid: number,
  seriesId: number,
  page: number,
  authHeaders: Record<string, string>,
): Promise<CreatorSeriesMemberPage> {
  const metadata = await fetchWithoutWBI(
    SERIES_METADATA_PATH,
    { series_id: seriesId },
    authHeaders,
  );
  const selectedSeries = normalizeSeriesContainer(metadata, mid);
  if (selectedSeries === undefined || selectedSeries.series_id !== seriesId) {
    throw new UpstreamResponseError(
      "Bilibili returned a different Creator Series",
    );
  }

  const data = await fetchWithoutWBI(
    SERIES_MEMBERS_PATH,
    {
      mid,
      series_id: seriesId,
      only_normal: "true",
      sort: "desc",
      pn: page,
      ps: PAGE_SIZE,
    },
    authHeaders,
  );
  if (!isRecord(data) || !isRecord(data.page) || !Array.isArray(data.archives)) {
    throw new UpstreamResponseError(
      "Bilibili returned an invalid Creator Series member response",
    );
  }
  const pageNumber = toOptionalPositiveInteger(data.page.num);
  const pageSize = toOptionalPositiveInteger(data.page.size);
  const total = toOptionalNonNegativeCount(data.page.total);
  if (pageNumber !== page || pageSize !== PAGE_SIZE || total === undefined) {
    throw new UpstreamResponseError(
      "Bilibili returned invalid Creator Series page facts",
    );
  }
  if (data.archives.length > PAGE_SIZE) {
    throw new ResourceLimitError(
      "Creator Series member page exceeded its item limit",
      "creator_series_member_items",
      PAGE_SIZE,
    );
  }

  const members: CreatorContainerVideoRow[] = [];
  let skippedCount = 0;
  for (const value of data.archives) {
    const video = normalizeContainerVideoRow(value);
    if (video) members.push(video);
    else skippedCount += 1;
  }
  const result: CreatorSeriesMemberPage = {
    mid,
    section: "series",
    mode: "members",
    page,
    selected_series: selectedSeries,
    members,
    skipped_count: skippedCount,
    live_state: "live",
  };
  const nextPage = page + 1;
  if (
    page * PAGE_SIZE < total &&
    Number.isSafeInteger(nextPage) &&
    Number.isSafeInteger(nextPage * PAGE_SIZE)
  ) {
    result.next_cursor = encodeCreatorContentCursor(
      mid,
      "series",
      nextPage,
      seriesId,
    );
  }
  return result;
}

function normalizeCollectionContainer(
  value: unknown,
  mid: number,
): CreatorCollectionContainer | undefined {
  if (!isRecord(value) || !isRecord(value.meta)) return undefined;
  const meta = value.meta;
  if (meta.mid !== mid || !isPositiveSafeInteger(meta.season_id)) {
    return undefined;
  }
  const name = normalizeContainerName(meta.name, "Collection");
  if (!name) return undefined;
  if (
    typeof meta.description === "string" &&
    Buffer.byteLength(meta.description, "utf8") > MAX_CONTAINER_DESCRIPTION_BYTES
  ) {
    throw new ResourceLimitError(
      "Creator Collection description exceeded its byte limit",
      "creator_collection_description",
      MAX_CONTAINER_DESCRIPTION_BYTES,
    );
  }
  const memberCount = toOptionalNonNegativeCount(meta.total);
  if (memberCount === undefined) return undefined;
  return {
    collection_id: meta.season_id,
    name,
    description: boundedRemoteText(
      meta.description,
      MAX_CONTAINER_DESCRIPTION_BYTES,
    ),
    member_count: memberCount,
  };
}

function normalizeSeriesContainer(
  value: unknown,
  mid: number,
): CreatorSeriesContainer | undefined {
  if (!isRecord(value) || !isRecord(value.meta)) return undefined;
  const meta = value.meta;
  if (meta.mid !== mid || !isPositiveSafeInteger(meta.series_id)) {
    return undefined;
  }
  const name = normalizeContainerName(meta.name, "Series");
  if (!name) return undefined;
  if (
    typeof meta.description === "string" &&
    Buffer.byteLength(meta.description, "utf8") > MAX_CONTAINER_DESCRIPTION_BYTES
  ) {
    throw new ResourceLimitError(
      "Creator Series description exceeded its byte limit",
      "creator_series_description",
      MAX_CONTAINER_DESCRIPTION_BYTES,
    );
  }
  const memberCount = toOptionalNonNegativeCount(meta.total);
  if (memberCount === undefined) return undefined;
  return {
    series_id: meta.series_id,
    name,
    description: boundedRemoteText(
      meta.description,
      MAX_CONTAINER_DESCRIPTION_BYTES,
    ),
    member_count: memberCount,
  };
}

function normalizeContainerName(
  value: unknown,
  kind: "Collection" | "Series",
): string | undefined {
  if (typeof value !== "string" || value.trim().length === 0) return undefined;
  if (Buffer.byteLength(value, "utf8") > MAX_CONTAINER_NAME_BYTES) {
    throw new ResourceLimitError(
      `Creator ${kind} name exceeded its byte limit`,
      `creator_${kind.toLowerCase()}_name`,
      MAX_CONTAINER_NAME_BYTES,
    );
  }
  return boundedRemoteText(value, MAX_CONTAINER_NAME_BYTES) || undefined;
}

async function fetchCreatorContainerListPage(
  mid: number,
  section: "collections" | "series",
  page: number,
  authHeaders: Record<string, string>,
): Promise<CreatorCollectionListPage | CreatorSeriesListPage> {
  const data = await fetchWithoutWBI(
    CONTAINER_LIST_PATH,
    { mid, page_num: page, page_size: PAGE_SIZE },
    authHeaders,
  );
  if (
    !isRecord(data) ||
    !isRecord(data.items_lists) ||
    !isRecord(data.items_lists.page) ||
    !Array.isArray(data.items_lists.seasons_list) ||
    !Array.isArray(data.items_lists.series_list)
  ) {
    throw new UpstreamResponseError(
      "Bilibili returned an invalid Creator container list response",
    );
  }
  const pageFacts = data.items_lists.page;
  const pageNumber = toOptionalPositiveInteger(pageFacts.page_num);
  const pageSize = toOptionalPositiveInteger(pageFacts.page_size);
  const total = toOptionalNonNegativeCount(pageFacts.total);
  const rawPageLength =
    data.items_lists.seasons_list.length + data.items_lists.series_list.length;
  if (pageNumber !== page || pageSize !== PAGE_SIZE || total === undefined) {
    throw new UpstreamResponseError(
      "Bilibili returned invalid Creator container page facts",
    );
  }
  if (rawPageLength > PAGE_SIZE) {
    throw new ResourceLimitError(
      "Creator container page exceeded its item limit",
      "creator_container_page_items",
      PAGE_SIZE,
    );
  }

  const collections: CreatorCollectionContainer[] = [];
  const series: CreatorSeriesContainer[] = [];
  let skippedCount = 0;
  const targetItems =
    section === "collections"
      ? data.items_lists.seasons_list
      : data.items_lists.series_list;
  for (const item of targetItems) {
    if (section === "collections") {
      const collection = normalizeCollectionContainer(item, mid);
      if (collection) collections.push(collection);
      else skippedCount += 1;
    } else {
      const seriesContainer = normalizeSeriesContainer(item, mid);
      if (seriesContainer) series.push(seriesContainer);
      else skippedCount += 1;
    }
  }
  const result: CreatorCollectionListPage | CreatorSeriesListPage =
    section === "collections"
      ? {
          mid,
          section,
          mode: "containers",
          page,
          collections,
          skipped_count: skippedCount,
          live_state: "live",
        }
      : {
          mid,
          section,
          mode: "containers",
          page,
          series,
          skipped_count: skippedCount,
          live_state: "live",
        };
  const nextPage = page + 1;
  if (
    page * PAGE_SIZE < total &&
    Number.isSafeInteger(nextPage) &&
    Number.isSafeInteger(nextPage * PAGE_SIZE)
  ) {
    result.next_cursor = encodeCreatorContentCursor(mid, section, nextPage);
  }
  return result;
}

interface NormalizedProfile {
  mid: number;
  name: string;
  bio: string;
  avatar_url: string;
  followerCount: number | undefined;
  level: number;
  videoCount: number | undefined;
}

function normalizeProfile(data: unknown, mid: number): NormalizedProfile {
  if (!isRecord(data)) {
    throw new UpstreamResponseError(
      "Bilibili returned an invalid creator profile response",
    );
  }
  if (!isPositiveSafeInteger(data.mid) || data.mid !== mid) {
    throw new UpstreamResponseError(
      "Bilibili returned a creator profile for a different mid",
    );
  }
  if (typeof data.name !== "string" || data.name.trim().length === 0) {
    throw new UpstreamResponseError(
      "Bilibili returned an invalid creator profile response",
    );
  }
  if (Buffer.byteLength(data.name, "utf8") > MAX_CREATOR_NAME_BYTES) {
    throw new ResourceLimitError(
      "Creator profile name exceeded its byte limit",
      "creator_profile_name",
      MAX_CREATOR_NAME_BYTES,
    );
  }
  return {
    mid,
    name: boundedRemoteText(data.name, MAX_CREATOR_NAME_BYTES),
    bio: boundedRemoteText(data.sign, MAX_CREATOR_BIO_BYTES),
    avatar_url: boundedRemoteText(data.face, MAX_CREATOR_AVATAR_BYTES),
    // acc/info 当前不提供 fans；仅在存在有效上游事实时才暴露粉丝数，绝不编造为 0。
    followerCount: toOptionalNonNegativeCount(data.fans),
    level: toNonNegativeSafeInteger(data.level),
    videoCount: toOptionalNonNegativeCount(data.videos),
  };
}

function normalizeCatalogCount(data: unknown): number {
  if (!isRecord(data) || !isRecord(data.page)) {
    throw new UpstreamResponseError(
      "Bilibili returned an invalid creator catalog count response",
    );
  }
  const count = toOptionalNonNegativeCount(data.page.count);
  if (count === undefined) {
    throw new UpstreamResponseError(
      "Bilibili returned an invalid creator catalog count response",
    );
  }
  return count;
}

async function fetchCreatorOverview(
  mid: number,
  authHeaders: Record<string, string>,
): Promise<CreatorContentOverview> {
  const profileData = await fetchWithWBI(
    PROFILE_PATH,
    { mid },
    authHeaders,
  );
  const profile = normalizeProfile(profileData, mid);

  let videoCount = profile.videoCount;
  if (videoCount === undefined) {
    // 有界计数探测：pn=1, ps=1, order=pubdate，非目录爬取。
    const countData = await fetchWithWBI(
      CATALOG_PATH,
      { mid, pn: 1, ps: 1, order: "pubdate", tid: 0, keyword: "" },
      authHeaders,
    );
    videoCount = normalizeCatalogCount(countData);
  }

  const result: CreatorContentOverview = {
    mid: profile.mid,
    section: "overview",
    name: profile.name,
    bio: profile.bio,
    avatar_url: profile.avatar_url,
    level: profile.level,
    video_count: videoCount,
    live_state: "live",
  };
  if (profile.followerCount !== undefined) {
    result.follower_count = profile.followerCount;
  }
  return result;
}

// 页面级 tlist 映射：list.tlist 以 typeid 为键、条目含 name（真实 arc/search 形状）。
// 每页只解析一次；条目畸形或类别名超界时单独跳过，绝不追加请求。
function buildCategoryNameMap(tlist: unknown): Map<number, string> {
  const names = new Map<number, string>();
  if (!isRecord(tlist)) return names;
  for (const [key, entry] of Object.entries(tlist)) {
    if (!isRecord(entry)) continue;
    if (typeof entry.name !== "string") continue;
    if (Buffer.byteLength(entry.name, "utf8") > MAX_CATALOG_CATEGORY_BYTES) {
      continue;
    }
    const name = boundedRemoteText(entry.name, MAX_CATALOG_CATEGORY_BYTES);
    if (!name) continue;
    // 真实 tlist 键是字符串化 typeid；键回退仅作兼容，非数字键经 Number() 得
    // NaN 后自然被 toOptionalPositiveInteger 拒绝。
    const tid =
      toOptionalPositiveInteger(entry.tid) ??
      toOptionalPositiveInteger(Number(key));
    if (tid === undefined) continue;
    names.set(tid, name);
  }
  return names;
}

function normalizeCatalogRow(
  row: unknown,
  categoryNames: ReadonlyMap<number, string>,
): CreatorVideoRow | undefined {
  if (!isRecord(row)) return undefined;

  const bvid =
    typeof row.bvid === "string" && isValidBVId(row.bvid)
      ? row.bvid
      : undefined;
  if (!bvid) return undefined;

  // 联合投稿行的行内 mid 可能与所选创作者不同；它们是当前可列表的创作者视频，
  // 必须保留并使用行内 author，不做行身份拒绝。

  if (typeof row.title !== "string") return undefined;
  if (Buffer.byteLength(row.title, "utf8") > MAX_CATALOG_TITLE_BYTES) {
    throw new ResourceLimitError(
      "Creator video title exceeded its byte limit",
      "creator_video_title",
      MAX_CATALOG_TITLE_BYTES,
    );
  }
  const title = boundedRemoteText(row.title, MAX_CATALOG_TITLE_BYTES);
  if (!title) return undefined;

  if (
    typeof row.author === "string" &&
    Buffer.byteLength(row.author, "utf8") > MAX_CATALOG_AUTHOR_BYTES
  ) {
    throw new ResourceLimitError(
      "Creator video author exceeded its byte limit",
      "creator_video_author",
      MAX_CATALOG_AUTHOR_BYTES,
    );
  }

  const result: CreatorVideoRow = {
    bvid,
    title,
    description: boundedRemoteText(row.description, MAX_CATALOG_DESCRIPTION_BYTES),
    cover_url: boundedRemoteText(row.pic, MAX_CATALOG_COVER_BYTES),
    // 时长以人类可读 length 为准（分钟可大于 59），数值 duration 仅作兼容回退；
    // 两者都畸形时回退到保守的 0。
    duration_seconds:
      parseDurationSeconds(row.length) ?? toNonNegativeSafeInteger(row.duration),
    published_at: toIsoFromCreated(row.created, row.create),
    author: boundedRemoteText(row.author, MAX_CATALOG_AUTHOR_BYTES),
    access: "unknown",
    source_url: `https://www.bilibili.com/video/${bvid}/`,
  };

  // 目录类别标识符以 typeid 为准，type_id 仅作兼容回退；类别名只取页面级
  // tlist 映射（行级 tag 不是类别来源），无有效有界映射时省略 category。
  const categoryId =
    toOptionalPositiveInteger(row.typeid) ?? toOptionalPositiveInteger(row.type_id);
  if (categoryId !== undefined) {
    result.category_id = categoryId;
    const category = categoryNames.get(categoryId);
    if (category !== undefined) result.category = category;
  }

  // 仅暴露上游提供的有效参与度事实；缺失或畸形时省略而非编造。
  // arc/search 语义：comment 是评论数（reply_count），video_review 是弹幕数（danmaku_count）。
  const viewCount = toOptionalNonNegativeCount(row.play);
  if (viewCount !== undefined) result.view_count = viewCount;
  const replyCount = toOptionalNonNegativeCount(row.comment);
  if (replyCount !== undefined) result.reply_count = replyCount;
  const danmakuCount = toOptionalNonNegativeCount(row.video_review);
  if (danmakuCount !== undefined) result.danmaku_count = danmakuCount;
  // 付费标记仅在显式真值证据（is_pay / is_charging_arc / elec_arc_type，
  // 或兼容字段 is_charge_video）存在时暴露；列表可见性本身不证明权益。
  if (
    isExplicitTruthy(row.is_pay) ||
    isExplicitTruthy(row.is_charging_arc) ||
    isExplicitTruthy(row.elec_arc_type) ||
    isExplicitTruthy(row.is_charge_video)
  ) {
    result.is_charge_video = true;
  }

  return result;
}

interface NormalizedCatalogPage {
  rows: CreatorVideoRow[];
  videosTotal: number | undefined;
  skippedCount: number;
  rawPageLength: number;
}

function normalizeCatalogPage(
  data: unknown,
  mid: number,
): NormalizedCatalogPage {
  if (
    !isRecord(data) ||
    !isRecord(data.list) ||
    !Array.isArray(data.list.vlist)
  ) {
    throw new UpstreamResponseError(
      "Bilibili returned an invalid creator video catalog response",
    );
  }
  const vlist = data.list.vlist;
  if (vlist.length > PAGE_SIZE) {
    throw new ResourceLimitError(
      "Creator video catalog page exceeded its item limit",
      "creator_video_page_items",
      PAGE_SIZE,
    );
  }
  const videosTotal = toOptionalNonNegativeCount(
    isRecord(data.page) ? data.page.count : undefined,
  );

  // 类别名映射每页只解析一次，所有行共用。
  const categoryNames = buildCategoryNameMap(data.list.tlist);

  const rows: CreatorVideoRow[] = [];
  let skippedCount = 0;
  for (const row of vlist) {
    const video = normalizeCatalogRow(row, categoryNames);
    if (video) {
      rows.push(video);
    } else {
      skippedCount += 1;
    }
  }
  return { rows, videosTotal, skippedCount, rawPageLength: vlist.length };
}

async function fetchCreatorVideoPage(
  mid: number,
  page: number,
  authHeaders: Record<string, string>,
): Promise<CreatorVideoPage> {
  const data = await fetchWithWBI(
    CATALOG_PATH,
    { mid, pn: page, ps: PAGE_SIZE, order: "pubdate", tid: 0, keyword: "" },
    authHeaders,
  );
  const { rows, videosTotal, skippedCount, rawPageLength } =
    normalizeCatalogPage(data, mid);

  // 无上游总数时，续读证明基于原始上游 vlist 长度而非过滤后的行数，
  // 避免一页 20 行中单条畸形行截断遍历。
  const continuationProven =
    (videosTotal !== undefined && page * PAGE_SIZE < videosTotal) ||
    (videosTotal === undefined && rawPageLength === PAGE_SIZE);

  const result: CreatorVideoPage = {
    mid,
    section: "videos",
    page,
    videos: rows,
    skipped_count: skippedCount,
    live_state: "live",
  };
  if (videosTotal !== undefined) {
    result.videos_total = videosTotal;
  }
  // 发出 page + 1 前证明下一页及其 page * 20 算术仍为安全整数。
  const nextPage = page + 1;
  if (
    continuationProven &&
    Number.isSafeInteger(nextPage) &&
    Number.isSafeInteger(nextPage * PAGE_SIZE)
  ) {
    result.next_cursor = encodeCreatorContentCursor(mid, "videos", nextPage);
  }
  return result;
}
