import { getVideoChaptersData } from "../bilibili/chapters.js";
import { getVideoCommentsData } from "../bilibili/comments.js";
import { checkLoginStatus } from "../bilibili/http.js";
import { getVideoMetadataData } from "../bilibili/metadata.js";
import { searchBilibiliVideos } from "../bilibili/search.js";
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
import { NoSubtitleError } from "../utils/errors.js";
import { sanitizeBVInput } from "../utils/sanitization.js";
import { buildPackageUpdateInfo } from "../utils/update-check.js";
import {
  validateBoolean,
  validateBVInput,
  validateCommentLimit,
  validateCommentSort,
  validateContextSegments,
  validateDetailLevel,
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
  toTextContent,
} from "./error-response.js";

type ToolArgs = Record<string, unknown> | undefined;

export async function handleToolCall(name: string, args: ToolArgs) {
  switch (name) {
    case "get_credential_setup_instructions": {
      return toTextContent(buildCredentialSetupInstructions());
    }

    case "check_bilibili_credentials": {
      const result = await buildCredentialStatus(checkLoginStatus);
      return toTextContent(result);
    }

    case "check_mcp_update": {
      const result = await buildPackageUpdateInfo();
      return toTextContent(result);
    }

    case "get_video_info": {
      const bvidOrUrl = args?.bvid_or_url as string;
      const preferredLang = args?.preferred_lang as string | undefined;
      const page = args?.page as number | undefined;

      let sanitizedBvidOrUrl: string;
      try {
        validateBVInput(bvidOrUrl);
        validateLanguage(preferredLang);
        validatePage(page);
        sanitizedBvidOrUrl = sanitizeBVInput(bvidOrUrl);
      } catch (error) {
        return toErrorTextContent(buildValidationErrorPayload(error));
      }

      const normalizedLang = getPreferredLanguage(preferredLang);
      const result = await getVideoInfoWithSubtitle(sanitizedBvidOrUrl, normalizedLang, page);

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
          throw new Error("include_replies must be a boolean");
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
        validateBoolean(fallbackToDescription, "fallback_to_description");
        validatePage(page);
        validateBoolean(includeTimestamps, "include_timestamps");
        validateTimestampRange(startSeconds, endSeconds);
        if (args?.fallback_to_description !== undefined && typeof args.fallback_to_description !== "boolean") {
          throw new Error("fallback_to_description must be a boolean");
        }
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
        const result = await getVideoTranscriptData(
          sanitizedBvidOrUrl,
          normalizedLang,
          fallbackToDescription,
          page,
          includeTimestamps,
          startSeconds,
          endSeconds,
          searchOptions,
        );
        return {
          ...toTextContent(result),
          structuredContent: result as unknown as Record<string, unknown>,
        };
      } catch (error) {
        if (error instanceof NoSubtitleError) {
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
          throw new Error("query is required");
        }
        validateQuery(rawQuery);
        validateSearchLimit(rawLimit);
      } catch (error) {
        return toErrorTextContent(buildValidationErrorPayload(error));
      }

      const query = (rawQuery as string).trim();
      const limit = rawLimit === undefined ? 5 : (rawLimit as number);
      const result = await searchBilibiliVideos(query, limit);

      return {
        ...toTextContent(result),
        structuredContent: result as unknown as Record<string, unknown>,
      };
    }

    default:
      throw new Error(`Unknown tool: ${name}`);
  }
}
