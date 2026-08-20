import { getVideoChaptersData } from "../bilibili/chapters.js";
import { getVideoCommentsData } from "../bilibili/comments.js";
import { getBilibiliCreatorContent } from "../bilibili/creator-content.js";
import { listBilibiliFavoriteVideos } from "../bilibili/favorites.js";
import { checkLoginStatus } from "../bilibili/http.js";
import { getVideoMetadataData } from "../bilibili/metadata.js";
import {
  searchBilibiliCreators,
  searchBilibiliVideos,
} from "../bilibili/search.js";
import {
  getVideoInfoWithSubtitle,
  getVideoTranscriptData,
} from "../bilibili/subtitle.js";
import { getPreferredLanguage } from "../config.js";
import {
  buildCredentialSetupInstructions,
  buildCredentialStatus,
} from "../utils/credential-guidance.js";
import { buildStructuredErrorPayload } from "../utils/error-guidance.js";
import {
  AsrError,
  NoSubtitleError,
  ValidationError,
} from "../utils/errors.js";
import { sanitizeBVInput } from "../utils/sanitization.js";
import { buildPackageUpdateInfo } from "../utils/update-check.js";
import {
  validateBoolean,
  validateBVInput,
  validateCommentLimit,
  validateCommentSort,
  validateContextSegments,
  validateCreatorContentInput,
  validateDetailLevel,
  validateFavoritesCursor,
  validateLanguage,
  validateMaxMatches,
  validatePage,
  validateQuery,
  validateSearchLimit,
  validateTimestampRange,
} from "../utils/validation.js";
import {
  buildValidationErrorPayload,
  toErrorTextContent,
  toStructuredContent,
  toTextContent,
} from "./error-response.js";

type ToolArgs = Record<string, unknown> | undefined;
const KNOWN_TOOL_NAMES = new Set([
  "get_credential_setup_instructions",
  "check_bilibili_credentials",
  "check_mcp_update",
  "get_video_info",
  "get_video_comments",
  "get_video_transcript",
  "get_video_metadata",
  "get_video_chapters",
  "search_bilibili_videos",
  "search_bilibili_creators",
  "list_bilibili_favorite_videos",
  "get_bilibili_creator_content",
]);

export async function handleToolCall(
  name: string,
  args: ToolArgs,
  signal?: AbortSignal,
) {
  if (name.length > 128 || !KNOWN_TOOL_NAMES.has(name)) {
    throw new Error("Unknown MCP tool");
  }
  switch (name) {
    case "get_credential_setup_instructions": {
      return toTextContent(buildCredentialSetupInstructions());
    }

    case "check_bilibili_credentials": {
      const result = await buildCredentialStatus(checkLoginStatus);
      return toTextContent(result);
    }

    case "check_mcp_update": {
      const result = await buildPackageUpdateInfo(globalThis.fetch, signal);
      return toTextContent(result);
    }

    case "get_video_info": {
      const bvidOrUrl = args?.bvid_or_url as string;
      const preferredLang = args?.preferred_lang as string | undefined;
      const page = args?.page as number | undefined;
      const excludeAiSubtitles = (args?.exclude_ai_subtitles as boolean) || false;

      let sanitizedBvidOrUrl: string;
      try {
        validateBVInput(bvidOrUrl);
        validateLanguage(preferredLang);
        validatePage(page);
        validateBoolean(args?.exclude_ai_subtitles, "exclude_ai_subtitles");
        sanitizedBvidOrUrl = sanitizeBVInput(bvidOrUrl);
      } catch (error) {
        return toErrorTextContent(buildValidationErrorPayload(error));
      }

      const normalizedLang = getPreferredLanguage(preferredLang);
      const result = await getVideoInfoWithSubtitle(sanitizedBvidOrUrl, normalizedLang, page, excludeAiSubtitles);

      return toTextContent(result);
    }

    case "get_video_comments": {
      const bvidOrUrl = args?.bvid_or_url as string;
      const detailLevel = (args?.detail_level as "brief" | "detailed") || "brief";
      const limit = args?.limit as number | undefined;
      const sort = args?.sort as "hot" | "time" | undefined;
      const includeReplies = args?.include_replies as boolean | undefined;

      let sanitizedBvidOrUrl: string;
      try {
        validateBVInput(bvidOrUrl);
        validateDetailLevel(detailLevel);
        if (limit !== undefined) validateCommentLimit(limit);
        if (sort !== undefined) validateCommentSort(sort);
        if (includeReplies !== undefined && typeof includeReplies !== "boolean") {
          throw new ValidationError("include_replies must be a boolean");
        }
        sanitizedBvidOrUrl = sanitizeBVInput(bvidOrUrl);
      } catch (error) {
        return toErrorTextContent(buildValidationErrorPayload(error));
      }

      const result = await getVideoCommentsData(sanitizedBvidOrUrl, {
        detailLevel,
        limit,
        sort,
        includeReplies,
      });

      return toTextContent(result);
    }

    case "get_video_transcript": {
      const bvidOrUrl = args?.bvid_or_url as string;
      const preferredLang = args?.preferred_lang as string | undefined;
      const fallbackToDescription = (args?.fallback_to_description as boolean) || false;
      const fallbackToAsr = (args?.fallback_to_asr as boolean) || false;
      const excludeAiSubtitles = (args?.exclude_ai_subtitles as boolean) || false;
      const forceAsr = (args?.force_asr as boolean) || false;
      const page = args?.page as number | undefined;
      const includeTimestamps = args?.include_timestamps as boolean | undefined;
      const startSeconds = args?.start_seconds as number | undefined;
      const endSeconds = args?.end_seconds as number | undefined;
      const query = args?.query as string | undefined;
      const maxMatches = args?.max_matches as number | undefined;
      const contextSegments = args?.context_segments as number | undefined;

      let sanitizedBvidOrUrl: string;
      try {
        validateBVInput(bvidOrUrl);
        validateLanguage(preferredLang);
        validatePage(page);
        validateBoolean(args?.fallback_to_description, "fallback_to_description");
        validateBoolean(args?.fallback_to_asr, "fallback_to_asr");
        validateBoolean(includeTimestamps, "include_timestamps");
        validateTimestampRange(startSeconds, endSeconds);
        validateBoolean(args?.exclude_ai_subtitles, "exclude_ai_subtitles");
        validateBoolean(args?.force_asr, "force_asr");
        validateQuery(query);
        validateMaxMatches(maxMatches);
        validateContextSegments(contextSegments);
        sanitizedBvidOrUrl = sanitizeBVInput(bvidOrUrl);
      } catch (error) {
        return toErrorTextContent(buildValidationErrorPayload(error));
      }

      const normalizedLang = getPreferredLanguage(preferredLang);

      const searchOptions = query !== undefined
        ? {
            query: query.trim(),
            max_matches: maxMatches ?? 10,
            context_segments: contextSegments ?? 1,
          }
        : undefined;

      try {
        const transcriptArgs = [
          sanitizedBvidOrUrl,
          normalizedLang,
          fallbackToDescription,
          page,
          includeTimestamps,
          startSeconds,
          endSeconds,
          searchOptions,
          fallbackToAsr,
          excludeAiSubtitles,
          forceAsr,
        ] as const;
        const result = signal === undefined
          ? await getVideoTranscriptData(...transcriptArgs)
          : await getVideoTranscriptData(...transcriptArgs, signal);
        return toStructuredContent(
          result as unknown as Record<string, unknown>,
        );
      } catch (error) {
        if (error instanceof NoSubtitleError || error instanceof AsrError) {
          return toErrorTextContent(
            buildStructuredErrorPayload(error, {
              fallbackToDescriptionAvailable: !includeTimestamps && startSeconds === undefined && endSeconds === undefined && fallbackToDescription !== true,
            }),
          );
        }
        throw error;
      }
    }

    case "get_video_metadata": {
      const bvidOrUrl = args?.bvid_or_url as string;

      let sanitizedBvidOrUrl: string;
      try {
        validateBVInput(bvidOrUrl);
        sanitizedBvidOrUrl = sanitizeBVInput(bvidOrUrl);
      } catch (error) {
        return toErrorTextContent(buildValidationErrorPayload(error));
      }

      const result = await getVideoMetadataData(sanitizedBvidOrUrl);

      return toTextContent(result);
    }

    case "get_video_chapters": {
      const bvidOrUrl = args?.bvid_or_url as string;
      const page = args?.page as number | undefined;

      let sanitizedBvidOrUrl: string;
      try {
        validateBVInput(bvidOrUrl);
        validatePage(page);
        sanitizedBvidOrUrl = sanitizeBVInput(bvidOrUrl);
      } catch (error) {
        return toErrorTextContent(buildValidationErrorPayload(error));
      }

      const result = await getVideoChaptersData(sanitizedBvidOrUrl, page);

      return toTextContent(result);
    }

    case "search_bilibili_videos": {
      const rawQuery = args?.query;
      const rawLimit = args?.limit;

      try {
        if (rawQuery === undefined) {
          throw new ValidationError("query is required");
        }
        validateQuery(rawQuery);
        validateSearchLimit(rawLimit);
      } catch (error) {
        return toErrorTextContent(buildValidationErrorPayload(error));
      }

      const query = (rawQuery as string).trim();
      const limit = rawLimit === undefined ? 5 : (rawLimit as number);
      const result = await searchBilibiliVideos(query, limit);

      return toStructuredContent(result as unknown as Record<string, unknown>);
    }

    case "search_bilibili_creators": {
      const rawQuery = args?.query;
      const rawLimit = args?.limit;

      try {
        if (rawQuery === undefined) {
          throw new ValidationError("query is required");
        }
        validateQuery(rawQuery);
        validateSearchLimit(rawLimit);
      } catch (error) {
        return toErrorTextContent(buildValidationErrorPayload(error));
      }

      const query = (rawQuery as string).trim();
      const limit = rawLimit === undefined ? 5 : (rawLimit as number);
      const result = await searchBilibiliCreators(query, limit);

      return toStructuredContent(result as unknown as Record<string, unknown>);
    }

    case "list_bilibili_favorite_videos": {
      const rawCursor = args?.cursor;

      try {
        validateFavoritesCursor(rawCursor);
      } catch (error) {
        return toErrorTextContent(buildValidationErrorPayload(error));
      }

      const cursor = typeof rawCursor === "string" ? rawCursor : undefined;
      const result = await listBilibiliFavoriteVideos(cursor);

      return toStructuredContent(result as unknown as Record<string, unknown>);
    }

    case "get_bilibili_creator_content": {
      const rawMid = args?.mid;
      const rawSection = args?.section;
      const rawContainerId = args?.container_id;
      const rawCursor = args?.cursor;

      try {
        validateCreatorContentInput(
          rawMid,
          rawSection,
          rawCursor,
          rawContainerId,
        );
      } catch (error) {
        return toErrorTextContent(buildValidationErrorPayload(error));
      }

      const mid = rawMid as number;
      const section = rawSection as
        | "overview"
        | "videos"
        | "collections"
        | "series"
        | "dynamics";
      const cursor = typeof rawCursor === "string" ? rawCursor : undefined;
      const result =
        typeof rawContainerId === "number"
          ? await getBilibiliCreatorContent(
              mid,
              section,
              cursor,
              rawContainerId,
            )
          : await getBilibiliCreatorContent(mid, section, cursor);

      return toStructuredContent(result as unknown as Record<string, unknown>);
    }

    default:
      throw new Error("Unknown MCP tool");
  }
}
