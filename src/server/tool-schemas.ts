import type { Tool } from "@modelcontextprotocol/sdk/types.js";

export const toolSchemas: Tool[] = [
  {
    name: "get_credential_setup_instructions",
    description:
      "Return safe Bilibili Cookie setup instructions for users or installing agents. Call this after installing the MCP server if credentials are not configured. Never returns Cookie values.",
    inputSchema: {
      type: "object",
      properties: {},
      required: [],
    },
  },
  {
    name: "check_bilibili_credentials",
    description:
      "Check whether Bilibili credentials are configured and logged in without exposing Cookie values. If missing or invalid, returns next_steps for setup.",
    inputSchema: {
      type: "object",
      properties: {},
      required: [],
    },
  },
  {
    name: "check_mcp_update",
    description:
      "Check the installed package version against the npm latest version and return safe MCP update guidance. Does not expose credentials.",
    inputSchema: {
      type: "object",
      properties: {},
      required: [],
    },
  },
  {
    name: "get_video_info",
    description:
      "获取 Bilibili 视频信息，优先返回字幕内容，如无字幕则返回视频简介和标签。支持指定偏好语言和多P分集选择。For credential help, call get_credential_setup_instructions.",
    inputSchema: {
      type: "object",
      properties: {
        bvid_or_url: {
          type: "string",
          description: "Bilibili 视频 BV 号或完整 URL",
        },
        preferred_lang: {
          type: "string",
          description:
            "可选参数，指定偏好字幕语言代码，如 'zh-Hans', 'zh-Hant', 'en' 等。默认按 zh-Hans -> zh-Hant -> en 顺序选择。",
        },
        page: {
          type: "integer",
          minimum: 1,
          description:
            "可选，多P视频的分集编号（从1开始的正整数）。不指定时使用默认CID。",
        },
      },
      required: ["bvid_or_url"],
    },
  },
  {
    name: "get_video_comments",
    description:
      "获取 Bilibili 视频热门评论。过滤表情占位符，优先保留包含时间戳的评论（如 '05:20'）。支持 brief（10条）和 detailed（20条+回复）两种模式。For credential help, call get_credential_setup_instructions.",
    inputSchema: {
      type: "object",
      properties: {
        bvid_or_url: {
          type: "string",
          description: "Bilibili 视频 BV 号或完整 URL",
        },
        detail_level: {
          type: "string",
          description:
            "评论详细程度：'brief' 获取前10条热门评论；'detailed' 获取前20条热门评论及其高赞回复",
          enum: ["brief", "detailed"],
        },
        limit: {
          type: "number",
          description:
            "可选评论数量限制，整数 1-50。覆盖 detail_level 的默认数量。",
        },
        sort: {
          type: "string",
          enum: ["hot", "time"],
          description:
            "评论排序方式：'hot' 按热度，'time' 按时间。默认 'hot'。",
        },
        include_replies: {
          type: "boolean",
          description:
            "是否在 detailed 模式下包含高赞回复。默认 true。",
        },
      },
      required: ["bvid_or_url"],
    },
  },
  {
    name: "get_video_transcript",
    description:
      "获取 Bilibili 视频纯字幕文本（按行合并）。支持分集选择、时间戳输出、时间区间过滤和可选关键词搜索。不自动降级到描述；仅在 fallback_to_description 为 true 且字幕不可用时返回视频描述。关键词搜索与描述降级不兼容。Requires Bilibili Cookie for reliable subtitle access. If unavailable, call get_credential_setup_instructions.",
    inputSchema: {
      type: "object",
      properties: {
        bvid_or_url: {
          type: "string",
          description: "Bilibili 视频 BV 号或完整 URL",
        },
        preferred_lang: {
          type: "string",
          description:
            "可选，指定偏好字幕语言代码，如 'zh-Hans', 'en' 等。",
        },
        fallback_to_description: {
          type: "boolean",
          description:
            "字幕不可用时是否降级为视频描述文本。默认 false。与时间戳/区间过滤器不兼容。",
        },
        page: {
          type: "integer",
          minimum: 1,
          description:
            "可选，多P视频的分集编号（从1开始的正整数）。不指定时使用默认Part。",
        },
        include_timestamps: {
          type: "boolean",
          description:
            "可选，为每行字幕添加 [HH:MM:SS --> HH:MM:SS] 时间戳前缀。默认 false。",
        },
        start_seconds: {
          type: "number",
          description:
            "可选，字幕区间起始秒数（非负整数或小数）。只返回 to >= start_seconds 的字幕段。",
        },
        end_seconds: {
          type: "number",
          description:
            "可选，字幕区间结束秒数（非负整数或小数）。只返回 from <= end_seconds 的字幕段。当同时提供 start_seconds 和 end_seconds 时需 end_seconds >= start_seconds。",
        },
        query: {
          type: "string",
          maxLength: 100,
          description:
            "可选，关键词搜索。大小写不敏感的字面匹配。非空且最多100字符。与 description 降级不兼容。",
        },
        max_matches: {
          type: "integer",
          minimum: 1,
          maximum: 20,
          description:
            "可选，最大返回匹配数（1-20，默认10）。仅在 query 存在时生效。",
        },
        context_segments: {
          type: "integer",
          minimum: 0,
          maximum: 5,
          description:
            "可选，每个匹配前后的字幕段上下文数量（0-5，默认1）。仅在 query 存在时生效。",
        },
      },
      required: ["bvid_or_url"],
    },
    outputSchema: {
      type: "object",
      properties: {
        bvid: { type: "string" },
        data_source: {
          type: "string",
          enum: ["subtitle", "description"],
        },
        language: { type: "string" },
        transcript: { type: "string" },
        title: { type: "string" },
        page: { type: "integer" },
        source_url: { type: "string" },
        query: { type: "string" },
        total_matches: { type: "integer" },
        returned_matches: { type: "integer" },
        truncated: { type: "boolean" },
        matches: {
          type: "array",
          items: {
            type: "object",
            properties: {
              start_seconds: { type: "number" },
              end_seconds: { type: "number" },
              content: { type: "string" },
              context: { type: "string" },
              timestamp_url: { type: "string" },
            },
            required: [
              "start_seconds",
              "end_seconds",
              "content",
              "context",
              "timestamp_url",
            ],
          },
        },
      },
      required: ["bvid", "data_source", "transcript", "title", "source_url"],
    },
  },
  {
    name: "get_video_metadata",
    description:
      "获取 Bilibili 视频元数据（标题、作者、时长、发布日期、标签、统计信息、多P分集列表等）。不获取字幕或评论。",
    inputSchema: {
      type: "object",
      properties: {
        bvid_or_url: {
          type: "string",
          description: "Bilibili 视频 BV 号或完整 URL",
        },
      },
      required: ["bvid_or_url"],
    },
  },
  {
    name: "get_video_chapters",
    description:
      "获取 Bilibili 视频的创作者/平台定义的章节（进度条分段），包含章节标题和起止时间。无章节时返回空列表，不推断章节。支持多P分集选择。",
    inputSchema: {
      type: "object",
      properties: {
        bvid_or_url: {
          type: "string",
          description: "Bilibili 视频 BV 号或完整 URL",
        },
        page: {
          type: "integer",
          minimum: 1,
          description:
            "可选，多P视频的分集编号（从1开始的正整数）。不指定时使用默认Part。",
        },
      },
      required: ["bvid_or_url"],
    },
  },
  {
    name: "search_bilibili_videos",
    description:
      "按关键词搜索 Bilibili 视频，返回最多 10 个平台综合排序的候选元数据。不自动获取字幕、评论或重新排序。必须先配置并登录 Bilibili Cookie；如需帮助，请调用 get_credential_setup_instructions。",
    inputSchema: {
      type: "object",
      properties: {
        query: {
          type: "string",
          minLength: 1,
          maxLength: 100,
          description:
            "Bilibili 视频搜索关键词。trim 后必须非空，最多 100 字符。",
        },
        limit: {
          type: "integer",
          minimum: 1,
          maximum: 10,
          description: "可选，候选视频数量。默认 5，最大 10。",
        },
      },
      required: ["query"],
    },
    outputSchema: {
      type: "object",
      properties: {
        query: { type: "string" },
        results: {
          type: "array",
          items: {
            type: "object",
            properties: {
              bvid: { type: "string" },
              title: { type: "string" },
              author: { type: "string" },
              duration_seconds: { type: "integer" },
              published_at: { type: "string" },
              view_count: { type: "integer" },
              description: { type: "string" },
              source_url: { type: "string" },
            },
            required: [
              "bvid",
              "title",
              "author",
              "duration_seconds",
              "published_at",
              "view_count",
              "description",
              "source_url",
            ],
          },
        },
      },
      required: ["query", "results"],
    },
  },
  {
    name: "list_bilibili_favorite_videos",
    description:
      "Discover every created Favorite Folder of the currently authenticated Bilibili account and return one bounded page of its Video memberships. Follow the returned next_cursor until it is absent to traverse every Folder; do not assume one response contains the full account. Requires configured, logged-in Bilibili Cookie; call get_credential_setup_instructions for help.",
    inputSchema: {
      type: "object",
      properties: {
        cursor: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9_-]+$",
          description:
            "Opaque continuation token returned by a previous successful call. Omit on the first call. The token encodes only a versioned Folder ID and page number; it never contains credentials, account IDs, Folder titles, or Video data.",
        },
      },
      required: [],
    },
    outputSchema: {
      type: "object",
      properties: {
        folders_total: { type: "integer" },
        folder: {
          type: "object",
          properties: {
            id: { type: "integer" },
            title: { type: "string" },
            media_count: { type: "integer" },
          },
          required: ["id", "title", "media_count"],
        },
        page: { type: "integer" },
        videos: {
          type: "array",
          items: {
            type: "object",
            properties: {
              bvid: { type: "string" },
              title: { type: "string" },
              author: { type: "string" },
              duration_seconds: { type: "integer" },
              published_at: { type: "string" },
              favorited_at: { type: "string" },
              source_url: { type: "string" },
            },
            required: [
              "bvid",
              "title",
              "author",
              "duration_seconds",
              "published_at",
              "favorited_at",
              "source_url",
            ],
          },
        },
        skipped_count: { type: "integer" },
        next_cursor: { type: "string" },
      },
      required: ["folders_total", "videos", "skipped_count"],
    },
  },
];
