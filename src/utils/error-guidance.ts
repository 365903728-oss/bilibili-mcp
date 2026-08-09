import {
  AsrError,
  BilibiliAPIError,
  CommentsDisabledError,
  NetworkError,
  NoSubtitleError,
  PaidVideoError,
  ResourceLimitError,
  TimeoutError,
  UpstreamResponseError,
  ValidationError,
} from "./errors.js";
import {
  buildCredentialNextSteps,
  buildCredentialNextStepsEn,
  buildCredentialNextStepsZh,
} from "./credential-guidance.js";
import { boundedRemoteText } from "./bounded-text.js";
import { redactSecrets } from "./logger.js";

export type StructuredErrorCode =
  | "VALIDATION_ERROR"
  | "COOKIE_EXPIRED"
  | "SUBTITLE_UNAVAILABLE"
  | "NETWORK_ERROR"
  | "NETWORK_TIMEOUT"
  | "API_RATE_LIMITED"
  | "ACCESS_DENIED"
  | "PAID_VIDEO"
  | "COMMENTS_DISABLED"
  | "BILIBILI_API_ERROR"
  | "RESOURCE_LIMIT_EXCEEDED"
  | "UNKNOWN_ERROR";

export type StructuredErrorCategory =
  | "validation"
  | "credentials"
  | "content"
  | "network"
  | "access"
  | "rate_limit"
  | "api"
  | "resource"
  | "runtime"
  | "unknown";

export interface StructuredErrorPayload {
  error: true;
  message: string;
  message_en: string;
  message_zh: string;
  code: StructuredErrorCode | string;
  category: StructuredErrorCategory;
  retryable: boolean;
  user_action_required: boolean;
  next_steps: string[];
  next_steps_en: string[];
  next_steps_zh: string[];
  details?: {
    status_code?: number;
    timeout_ms?: number;
    api_code?: string | number;
  };
}

export interface StructuredErrorContext {
  fallbackToDescriptionAvailable?: boolean;
}

function withCompatibilityNextSteps(
  payload: Omit<StructuredErrorPayload, "next_steps">,
): StructuredErrorPayload {
  return {
    ...payload,
    next_steps: payload.next_steps_en,
  };
}

function safeValidationMessage(error: unknown): string {
  if (!(error instanceof Error) || !error.message) return "Invalid input";
  const redacted = redactSecrets(error.message);
  return boundedRemoteText(redacted, 512) || "Invalid input";
}

export function buildStructuredErrorPayload(
  error: unknown,
  context: StructuredErrorContext = {},
): StructuredErrorPayload {
  if (
    error instanceof ValidationError ||
    (error instanceof Error && error.name === "ValidationError")
  ) {
    return withCompatibilityNextSteps({
      error: true,
      message: safeValidationMessage(error),
      message_en: safeValidationMessage(error),
      message_zh: "输入参数无效，请检查 BV 号、链接、语言代码或评论参数。",
      code: "VALIDATION_ERROR",
      category: "validation",
      retryable: false,
      user_action_required: true,
      next_steps_en: ["Fix the input arguments and call the MCP tool again."],
      next_steps_zh: ["请修正输入参数后重新调用 MCP 工具。"],
    });
  }

  if (error instanceof BilibiliAPIError && error.code === "COOKIE_EXPIRED") {
    return withCompatibilityNextSteps({
      error: true,
      message: "Current Bilibili credentials are expired or not logged in.",
      message_en:
        "Current Bilibili credentials are expired or not logged in.",
      message_zh: "当前 Bilibili 凭据已过期或未登录。",
      code: "COOKIE_EXPIRED",
      category: "credentials",
      retryable: false,
      user_action_required: true,
      next_steps_en: buildCredentialNextStepsEn(),
      next_steps_zh: buildCredentialNextStepsZh(),
      details: { api_code: "COOKIE_EXPIRED" },
    });
  }

  if (error instanceof NoSubtitleError) {
    const fallbackStepEn = context.fallbackToDescriptionAvailable
      ? "Retry get_video_transcript with fallback_to_description: true if description fallback is acceptable."
      : "If description fallback is acceptable, use get_video_info or retry transcript with fallback_to_description: true.";
    const fallbackStepZh = context.fallbackToDescriptionAvailable
      ? "如果接受降级为视频简介，请用 fallback_to_description: true 重新调用 get_video_transcript。"
      : "如果接受降级为视频简介，请使用 get_video_info，或用 fallback_to_description: true 重试字幕工具。";
    return withCompatibilityNextSteps({
      error: true,
      message: "No subtitles are available for this video.",
      message_en: "No subtitles are available for this video.",
      message_zh: "该视频没有可用字幕。",
      code: "SUBTITLE_UNAVAILABLE",
      category: "content",
      retryable: false,
      user_action_required: true,
      next_steps_en: [
        "If you expected subtitles, configure Bilibili Cookies.",
        ...buildCredentialNextSteps(),
        fallbackStepEn,
      ],
      next_steps_zh: [
        "如果你预期该视频应该有字幕，请先配置 Bilibili Cookie。",
        ...buildCredentialNextStepsZh(),
        fallbackStepZh,
      ],
    });
  }

  if (error instanceof AsrError) {
    const guidance: Record<
      AsrError["code"],
      { en: string; zh: string; stepsEn: string[]; stepsZh: string[] }
    > = {
      ASR_NOT_READY: {
        en: "Local ASR is not ready.",
        zh: "本地 ASR 尚未就绪。",
        stepsEn: [
          "Run `npx -y @xzxzzx/bilibili-mcp@latest setup` outside the MCP call.",
          "Inspect `npx -y @xzxzzx/bilibili-mcp@latest doctor --json` before retrying.",
        ],
        stepsZh: [
          "请在 MCP 调用之外运行 `npx -y @xzxzzx/bilibili-mcp@latest setup`。",
          "重试前请检查 `npx -y @xzxzzx/bilibili-mcp@latest doctor --json`。",
        ],
      },
      ASR_AUDIO_UNAVAILABLE: {
        en: "A temporary audio-only source is unavailable.",
        zh: "无法获取临时纯音频源。",
        stepsEn: ["Retry later; Bilibili playback URLs are temporary."],
        stepsZh: ["请稍后重试；Bilibili 播放地址是临时的。"],
      },
      ASR_LIMIT_EXCEEDED: {
        en: "The selected Part exceeds a bounded ASR safety limit.",
        zh: "所选分集超出了 ASR 安全限制。",
        stepsEn: ["Choose a shorter Part or use native subtitles."],
        stepsZh: ["请选择更短的分集，或使用原生字幕。"],
      },
      ASR_BUSY: {
        en: "Another local ASR transcription is already active.",
        zh: "已有一个本地 ASR 转录正在运行。",
        stepsEn: ["Retry after the active transcription finishes."],
        stepsZh: ["请在当前转录完成后重试。"],
      },
      ASR_TRANSCRIPTION_TIMEOUT: {
        en: "Local ASR exceeded its time limit.",
        zh: "本地 ASR 超过了时间限制。",
        stepsEn: ["Retry later or choose a shorter Part."],
        stepsZh: ["请稍后重试，或选择更短的分集。"],
      },
      ASR_TRANSCRIPTION_FAILED: {
        en: "The managed local ASR process failed.",
        zh: "项目托管的本地 ASR 进程失败。",
        stepsEn: ["Inspect `doctor --json`, then retry without changing the model inside MCP."],
        stepsZh: ["请检查 `doctor --json`，不要在 MCP 调用中切换模型，然后重试。"],
      },
      ASR_OUTPUT_INVALID: {
        en: "The managed local ASR process returned invalid bounded output.",
        zh: "项目托管的本地 ASR 进程返回了无效的有界输出。",
        stepsEn: ["Run `doctor --json` and report the error if it repeats."],
        stepsZh: ["请运行 `doctor --json`；如反复出现，请反馈该错误。"],
      },
    };
    const selected = guidance[error.code];
    return withCompatibilityNextSteps({
      error: true,
      message: selected.en,
      message_en: selected.en,
      message_zh: selected.zh,
      code: error.code,
      category: "runtime",
      retryable: error.retryable,
      user_action_required: error.code === "ASR_NOT_READY" || error.code === "ASR_LIMIT_EXCEEDED",
      next_steps_en: selected.stepsEn,
      next_steps_zh: selected.stepsZh,
    });
  }

  if (error instanceof TimeoutError) {
    return withCompatibilityNextSteps({
      error: true,
      message: "The Bilibili request timed out.",
      message_en: "The Bilibili request timed out.",
      message_zh: "请求 Bilibili 超时。",
      code: "NETWORK_TIMEOUT",
      category: "network",
      retryable: true,
      user_action_required: false,
      next_steps_en: [
        "Retry later.",
        "Check local network, proxy, firewall, or VPN settings if the problem repeats.",
      ],
      next_steps_zh: [
        "请稍后重试。",
        "如果超时问题反复出现，请检查本机网络、代理、防火墙或 VPN 设置。",
      ],
      details: { timeout_ms: error.timeoutMs },
    });
  }

  if (error instanceof ResourceLimitError) {
    return withCompatibilityNextSteps({
      error: true,
      message: "The request exceeded a local safety limit.",
      message_en: "The request exceeded a local safety limit.",
      message_zh: "请求超出了本地安全限制。",
      code: "RESOURCE_LIMIT_EXCEEDED",
      category: "resource",
      retryable: true,
      user_action_required: false,
      next_steps_en: [
        "Reduce request concurrency or requested output size, then retry.",
      ],
      next_steps_zh: ["请降低请求并发量或请求的输出规模后重试。"],
    });
  }

  if (error instanceof UpstreamResponseError) {
    return withCompatibilityNextSteps({
      error: true,
      message: "The remote service returned an invalid bounded response.",
      message_en: "The remote service returned an invalid bounded response.",
      message_zh: "远程服务返回了无效或超出格式约束的响应。",
      code: "UPSTREAM_RESPONSE_INVALID",
      category: "api",
      retryable: false,
      user_action_required: false,
      next_steps_en: ["Retry later if the upstream response was temporary."],
      next_steps_zh: ["如果上游响应异常是临时问题，请稍后重试。"],
    });
  }

  if (error instanceof NetworkError) {
    const rateLimited = error.statusCode === 429;
    return withCompatibilityNextSteps({
      error: true,
      message: rateLimited
        ? "Bilibili API rate limit reached."
        : "Network request failed.",
      message_en: rateLimited
        ? "Bilibili API rate limit reached."
        : "Network request failed.",
      message_zh: rateLimited
        ? "Bilibili API 访问频率受限。"
        : "网络请求失败。",
      code: rateLimited ? "API_RATE_LIMITED" : "NETWORK_ERROR",
      category: rateLimited ? "rate_limit" : "network",
      retryable: true,
      user_action_required: rateLimited,
      next_steps_en: rateLimited
        ? [
            "Wait and retry later.",
            "Reduce request frequency or increase BILIBILI_RATE_LIMIT_MS if running many calls.",
          ]
        : [
            "Retry later.",
            "Check local network, proxy, firewall, or VPN settings if the problem repeats.",
          ],
      next_steps_zh: rateLimited
        ? [
            "请等待一段时间后重试。",
            "如果连续调用较多，请降低调用频率，或调大 BILIBILI_RATE_LIMIT_MS。",
          ]
        : [
            "稍后重试。",
            "如果问题反复出现，请检查本机网络、代理、防火墙或 VPN 设置。",
          ],
      details: { status_code: error.statusCode },
    });
  }

  if (error instanceof BilibiliAPIError && error.code === "ACCESS_DENIED") {
    return withCompatibilityNextSteps({
      error: true,
      message: "Bilibili denied access to this resource.",
      message_en: "Bilibili denied access to this resource.",
      message_zh: "Bilibili 拒绝访问该资源。",
      code: "ACCESS_DENIED",
      category: "access",
      retryable: false,
      user_action_required: true,
      next_steps_en: [
        "Check whether the requested Bilibili resource (such as a video or Favorite Folder) is private, restricted, removed, or requires a logged-in account.",
        "Run the credential check if you expected this account to have access.",
      ],
      next_steps_zh: [
        "请检查所请求的 Bilibili 资源（如视频或收藏夹）是否为私密、受限、已下架，或需要登录账号访问。",
        "如果你认为当前账号应有权限，请先运行凭据检查。",
      ],
      details: { api_code: error.code, status_code: error.statusCode },
    });
  }

  if (error instanceof PaidVideoError) {
    return withCompatibilityNextSteps({
      error: true,
      message: "This video appears to require paid access.",
      message_en: "This video appears to require paid access.",
      message_zh: "该视频可能需要付费、会员或额外权限。",
      code: "PAID_VIDEO",
      category: "access",
      retryable: false,
      user_action_required: true,
      next_steps_en: [
        "Open the video in Bilibili and confirm whether it requires purchase, membership, or account-specific permission.",
        "This MCP cannot bypass paid or restricted access.",
      ],
      next_steps_zh: [
        "请在 Bilibili 中打开视频，确认是否需要购买、会员或账号权限。",
        "本 MCP 不会绕过付费或受限访问。",
      ],
    });
  }

  if (error instanceof CommentsDisabledError) {
    return withCompatibilityNextSteps({
      error: true,
      message: "Comments are disabled or restricted for this video.",
      message_en: "Comments are disabled or restricted for this video.",
      message_zh: "该视频评论已关闭或访问受限。",
      code: "COMMENTS_DISABLED",
      category: "content",
      retryable: false,
      user_action_required: false,
      next_steps_en: [
        "Use transcript or metadata tools instead.",
        "Open the video in Bilibili to confirm whether comments are visible in the official UI.",
      ],
      next_steps_zh: [
        "可以改用字幕或元数据工具。",
        "也可以在 Bilibili 官方页面确认评论是否可见。",
      ],
    });
  }

  if (error instanceof BilibiliAPIError) {
    return withCompatibilityNextSteps({
      error: true,
      message: "Bilibili API returned an error.",
      message_en: "Bilibili API returned an error.",
      message_zh: "Bilibili API 返回错误。",
      code: "BILIBILI_API_ERROR",
      category: "api",
      retryable: false,
      user_action_required: false,
      next_steps_en: [
        "Retry later if this looks temporary.",
        "If the problem repeats, include the error code when reporting the issue.",
      ],
      next_steps_zh: [
        "如果看起来是临时问题，请稍后重试。",
        "如果问题反复出现，反馈时请带上错误代码。",
      ],
      details: { api_code: error.code, status_code: error.statusCode },
    });
  }

  return withCompatibilityNextSteps({
    error: true,
    message: "An internal error occurred.",
    message_en: "An internal error occurred.",
    message_zh: "发生未知错误。",
    code: "UNKNOWN_ERROR",
    category: "unknown",
    retryable: false,
    user_action_required: false,
    next_steps_en: [
      "Retry later.",
      "If the problem repeats, report the error message without including credentials.",
    ],
    next_steps_zh: [
      "请稍后重试。",
      "如果问题反复出现，请反馈错误信息，但不要包含 Cookie 或其他凭据。",
    ],
  });
}
