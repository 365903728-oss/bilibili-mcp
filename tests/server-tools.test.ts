import { beforeAll, describe, expect, it } from "vitest";

import { getMcpHandler } from "./helpers/mcp.js";

function getListToolsResult() {
  const fakeRequest = {
    method: "tools/list",
    jsonrpc: "2.0" as const,
    id: 1,
  };
  const handler = getMcpHandler<
    typeof fakeRequest,
    {
      tools: Array<{
        name: string;
        inputSchema: Record<string, unknown>;
        outputSchema?: Record<string, unknown>;
      }>;
    }
  >("tools/list");

  return handler(fakeRequest);
}

let toolsResult: Awaited<ReturnType<typeof getListToolsResult>>;

describe("MCP tool list baseline", () => {
  beforeAll(async () => {
    toolsResult = await getListToolsResult();
  });
  it("exposes all 12 tools", () => {
    const names = toolsResult.tools.map((t) => t.name);
    expect(names).toHaveLength(12);
    expect(names).toContain("get_credential_setup_instructions");
    expect(names).toContain("check_bilibili_credentials");
    expect(names).toContain("check_mcp_update");
    expect(names).toContain("get_video_info");
    expect(names).toContain("get_video_comments");
    expect(names).toContain("get_video_transcript");
    expect(names).toContain("get_video_metadata");
    expect(names).toContain("get_video_chapters");
    expect(names).toContain("search_bilibili_videos");
    expect(names).toContain("search_bilibili_creators");
    expect(names).toContain("list_bilibili_favorite_videos");
    expect(names).toContain("get_bilibili_creator_content");
  });

  it("keeps the public tool order stable", () => {
    expect(toolsResult.tools.map((tool) => tool.name)).toEqual([
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
  });

  it("keeps all public tool required fields stable", () => {
    const requiredByTool = Object.fromEntries(
      toolsResult.tools.map((tool) => [
        tool.name,
        tool.inputSchema.required ?? [],
      ]),
    );

    expect(requiredByTool).toEqual({
      get_credential_setup_instructions: [],
      check_bilibili_credentials: [],
      check_mcp_update: [],
      get_video_info: ["bvid_or_url"],
      get_video_comments: ["bvid_or_url"],
      get_video_transcript: ["bvid_or_url"],
      get_video_metadata: ["bvid_or_url"],
      get_video_chapters: ["bvid_or_url"],
      search_bilibili_videos: ["query"],
      search_bilibili_creators: ["query"],
      list_bilibili_favorite_videos: [],
      get_bilibili_creator_content: ["mid", "section"],
    });
  });

  describe("get_video_info schema", () => {
    let schema: { name: string; inputSchema: Record<string, unknown> };

    it("is registered", () => {
      schema = toolsResult.tools.find((t) => t.name === "get_video_info")!;
      expect(schema).toBeDefined();
    });

    it("requires bvid_or_url", () => {
      schema = toolsResult.tools.find((t) => t.name === "get_video_info")!;
      expect(schema.inputSchema.required).toContain("bvid_or_url");
    });

    it("publishes the supported preferred_lang values including ai-zh", () => {
      schema = toolsResult.tools.find((t) => t.name === "get_video_info")!;
      const prop = schema.inputSchema.properties.preferred_lang as {
        type?: string;
        enum?: string[];
        description?: string;
      };

      expect(prop).toMatchObject({
        type: "string",
        enum: ["zh-Hans", "zh-CN", "zh-Hant", "en", "ja", "ko", "ai-zh"],
      });
      expect(prop.description).toContain("ai-zh");
      expect(prop.description).toContain("未知值会被拒绝");
      expect(prop.description).toContain("unsupported values are rejected");
    });

    it("accepts optional page with integer type and minimum 1", () => {
      schema = toolsResult.tools.find((t) => t.name === "get_video_info")!;
      const prop = schema.inputSchema.properties.page as { type?: string; minimum?: number };
      expect(prop).toBeDefined();
      expect(prop.type).toBe("integer");
      expect(prop.minimum).toBe(1);
    });

    it("accepts optional exclude_ai_subtitles (boolean, default-off)", () => {
      schema = toolsResult.tools.find((t) => t.name === "get_video_info")!;
      const prop = schema.inputSchema.properties
        .exclude_ai_subtitles as { type?: string; description?: string };
      expect(prop).toBeDefined();
      expect(prop.type).toBe("boolean");
      expect(prop.description).toContain("ai");
    });
  });

  describe("get_video_comments schema", () => {
    let schema: { name: string; inputSchema: Record<string, unknown> };

    it("is registered", () => {
      schema = toolsResult.tools.find(
        (t) => t.name === "get_video_comments",
      )!;
      expect(schema).toBeDefined();
    });

    it("requires bvid_or_url", () => {
      schema = toolsResult.tools.find(
        (t) => t.name === "get_video_comments",
      )!;
      expect(schema.inputSchema.required).toContain("bvid_or_url");
    });

    it("accepts optional detail_level", () => {
      schema = toolsResult.tools.find(
        (t) => t.name === "get_video_comments",
      )!;
      expect(schema.inputSchema.properties).toHaveProperty("detail_level");
    });

    it("restricts detail_level to brief and detailed", () => {
      schema = toolsResult.tools.find(
        (t) => t.name === "get_video_comments",
      )!;
      const prop = schema.inputSchema.properties
        .detail_level as { enum?: string[] };
      expect(prop.enum).toEqual(["brief", "detailed"]);
    });

    it("defines limit as a 1-50 main-comment count and documents reply expansion", () => {
      schema = toolsResult.tools.find(
        (t) => t.name === "get_video_comments",
      )!;
      const prop = schema.inputSchema.properties.limit as {
        type?: string;
        minimum?: number;
        maximum?: number;
        description?: string;
      };

      expect(prop).toMatchObject({
        type: "integer",
        minimum: 1,
        maximum: 50,
      });
      expect(prop.description).toContain("主评论");
      expect(prop.description).toContain("main-comment");
      expect(prop.description).toContain("comments[]");
      expect(prop.description).toContain("超过 limit");
    });

    it("accepts optional sort with enum hot/time", () => {
      schema = toolsResult.tools.find(
        (t) => t.name === "get_video_comments",
      )!;
      const prop = schema.inputSchema.properties.sort as { enum?: string[] };
      expect(prop).toBeDefined();
      expect(prop.enum).toEqual(["hot", "time"]);
    });

    it("accepts optional include_replies (boolean)", () => {
      schema = toolsResult.tools.find(
        (t) => t.name === "get_video_comments",
      )!;
      const prop = schema.inputSchema.properties
        .include_replies as { type?: string };
      expect(prop).toBeDefined();
      expect(prop.type).toBe("boolean");
    });
  });

  describe("get_video_transcript schema", () => {
    let schema: {
      name: string;
      inputSchema: Record<string, unknown>;
      outputSchema?: Record<string, unknown>;
    };

    it("is registered", () => {
      schema = toolsResult.tools.find(
        (t) => t.name === "get_video_transcript",
      )!;
      expect(schema).toBeDefined();
    });

    it("requires bvid_or_url", () => {
      schema = toolsResult.tools.find(
        (t) => t.name === "get_video_transcript",
      )!;
      expect(schema.inputSchema.required).toContain("bvid_or_url");
    });

    it("publishes the supported preferred_lang values including ai-zh", () => {
      schema = toolsResult.tools.find(
        (t) => t.name === "get_video_transcript",
      )!;
      const prop = schema.inputSchema.properties.preferred_lang as {
        type?: string;
        enum?: string[];
        description?: string;
      };

      expect(prop).toMatchObject({
        type: "string",
        enum: ["zh-Hans", "zh-CN", "zh-Hant", "en", "ja", "ko", "ai-zh"],
      });
      expect(prop.description).toContain("ai-zh");
      expect(prop.description).toContain("未知值会被拒绝");
      expect(prop.description).toContain("unsupported values are rejected");
    });

    it("accepts optional fallback_to_description (boolean)", () => {
      schema = toolsResult.tools.find(
        (t) => t.name === "get_video_transcript",
      )!;
      const prop = schema.inputSchema.properties
        .fallback_to_description as { type?: string };
      expect(prop).toBeDefined();
      expect(prop.type).toBe("boolean");
    });

    it("accepts optional fallback_to_asr (boolean, default-off contract)", () => {
      schema = toolsResult.tools.find(
        (t) => t.name === "get_video_transcript",
      )!;
      const prop = schema.inputSchema.properties
        .fallback_to_asr as { type?: string };
      expect(prop).toBeDefined();
      expect(prop.type).toBe("boolean");
    });

    it("accepts optional exclude_ai_subtitles (boolean, default-off)", () => {
      schema = toolsResult.tools.find(
        (t) => t.name === "get_video_transcript",
      )!;
      const prop = schema.inputSchema.properties
        .exclude_ai_subtitles as { type?: string; description?: string };
      expect(prop).toBeDefined();
      expect(prop.type).toBe("boolean");
      expect(prop.description).toContain("ai");
    });

    it("accepts optional force_asr (boolean, default-off)", () => {
      schema = toolsResult.tools.find(
        (t) => t.name === "get_video_transcript",
      )!;
      const prop = schema.inputSchema.properties
        .force_asr as { type?: string; description?: string };
      expect(prop).toBeDefined();
      expect(prop.type).toBe("boolean");
      expect(prop.description).toContain("ASR");
    });

    it("accepts optional page (integer, min 1), include_timestamps, start_seconds, end_seconds", () => {
      schema = toolsResult.tools.find(
        (t) => t.name === "get_video_transcript",
      )!;
      const pageProp = schema.inputSchema.properties.page as { type?: string; minimum?: number };
      expect(pageProp).toBeDefined();
      expect(pageProp.type).toBe("integer");
      expect(pageProp.minimum).toBe(1);
      expect(schema.inputSchema.properties).toHaveProperty("include_timestamps");
      expect(schema.inputSchema.properties).toHaveProperty("start_seconds");
      expect(schema.inputSchema.properties).toHaveProperty("end_seconds");
    });

    it("accepts optional query (string), max_matches (integer 1-20), context_segments (integer 0-5)", () => {
      schema = toolsResult.tools.find(
        (t) => t.name === "get_video_transcript",
      )!;
      const queryProp = schema.inputSchema.properties.query as {
        type?: string;
        maxLength?: number;
      };
      expect(queryProp).toBeDefined();
      expect(queryProp.type).toBe("string");
      expect(queryProp.maxLength).toBe(100);

      const mmProp = schema.inputSchema.properties.max_matches as {
        type?: string;
        minimum?: number;
        maximum?: number;
      };
      expect(mmProp).toBeDefined();
      expect(mmProp.type).toBe("integer");
      expect(mmProp.minimum).toBe(1);
      expect(mmProp.maximum).toBe(20);

      const csProp = schema.inputSchema.properties.context_segments as {
        type?: string;
        minimum?: number;
        maximum?: number;
      };
      expect(csProp).toBeDefined();
      expect(csProp.type).toBe("integer");
      expect(csProp.minimum).toBe(0);
      expect(csProp.maximum).toBe(5);
    });

    it("declares the complete structured transcript output", () => {
      schema = toolsResult.tools.find(
        (t) => t.name === "get_video_transcript",
      )!;

      expect(schema.outputSchema).toEqual({
        type: "object",
        properties: {
          bvid: { type: "string" },
          data_source: {
            type: "string",
            enum: ["subtitle", "ai_subtitle", "description", "asr"],
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
      });
    });
  });

  describe("credential helper tools", () => {
    it("registers get_credential_setup_instructions with no required input", () => {
      const schema = toolsResult.tools.find(
        (t) => t.name === "get_credential_setup_instructions",
      )!;

      expect(schema).toBeDefined();
      expect(schema.inputSchema.required ?? []).toEqual([]);
    });

    it("registers check_bilibili_credentials with no required input", () => {
      const schema = toolsResult.tools.find(
        (t) => t.name === "check_bilibili_credentials",
      )!;

      expect(schema).toBeDefined();
      expect(schema.inputSchema.required ?? []).toEqual([]);
    });

    it("registers check_mcp_update with no required input", () => {
      const schema = toolsResult.tools.find(
        (t) => t.name === "check_mcp_update",
      )!;

      expect(schema).toBeDefined();
      expect(schema.description).toContain("npm latest");
      expect(schema.inputSchema.required ?? []).toEqual([]);
    });

    it("points transcript users to credential setup instructions", () => {
      const schema = toolsResult.tools.find(
        (t) => t.name === "get_video_transcript",
      ) as { description?: string };

      expect(schema.description).toContain(
        "get_credential_setup_instructions",
      );
    });

    it("warns on every Bilibili text tool that returned text is untrusted", () => {
      const textTools = [
        "get_video_info",
        "get_video_comments",
        "get_video_transcript",
        "get_video_metadata",
        "get_video_chapters",
        "search_bilibili_videos",
        "search_bilibili_creators",
        "list_bilibili_favorite_videos",
        "get_bilibili_creator_content",
      ];
      for (const name of textTools) {
        const schema = toolsResult.tools.find(
          (t) => t.name === name,
        ) as { description?: string };
        expect(schema.description, name).toContain("untrusted data");
      }
    });
  });

  describe("get_video_metadata schema", () => {
    let schema: { name: string; inputSchema: Record<string, unknown> };

    it("is registered", () => {
      schema = toolsResult.tools.find(
        (t) => t.name === "get_video_metadata",
      )!;
      expect(schema).toBeDefined();
    });

    it("requires bvid_or_url", () => {
      schema = toolsResult.tools.find(
        (t) => t.name === "get_video_metadata",
      )!;
      expect(schema.inputSchema.required).toContain("bvid_or_url");
    });
  });

  describe("get_video_chapters schema", () => {
    let schema: { name: string; inputSchema: Record<string, unknown> };

    it("is registered as the 8th tool", () => {
      const names = toolsResult.tools.map((t) => t.name);
      expect(names).toContain("get_video_chapters");
      expect(names[7]).toBe("get_video_chapters");
    });

    it("requires bvid_or_url", () => {
      schema = toolsResult.tools.find(
        (t) => t.name === "get_video_chapters",
      )!;
      expect(schema).toBeDefined();
      expect(schema.inputSchema.required).toContain("bvid_or_url");
    });

    it("accepts optional page with integer type and minimum 1", () => {
      schema = toolsResult.tools.find(
        (t) => t.name === "get_video_chapters",
      )!;
      const prop = schema.inputSchema.properties.page as { type?: string; minimum?: number };
      expect(prop).toBeDefined();
      expect(prop.type).toBe("integer");
      expect(prop.minimum).toBe(1);
    });
  });

  describe("search_bilibili_videos schema", () => {
    it("declares the exact bounded input and structured candidate output", () => {
      const schema = toolsResult.tools.find(
        (tool) => tool.name === "search_bilibili_videos",
      )!;

      expect(schema).toBeDefined();
      expect(schema.inputSchema).toEqual({
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
      });
      expect(schema.outputSchema).toEqual({
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
      });
    });
  });

  describe("search_bilibili_creators schema", () => {
    it("declares the exact bounded input and structured creator candidate output", () => {
      const schema = toolsResult.tools.find(
        (tool) => tool.name === "search_bilibili_creators",
      )!;

      expect(schema).toBeDefined();
      expect(schema.inputSchema).toEqual({
        type: "object",
        properties: {
          query: {
            type: "string",
            minLength: 1,
            maxLength: 100,
            description:
              "Bilibili 创作者搜索关键词。trim 后必须非空，最多 100 字符。",
          },
          limit: {
            type: "integer",
            minimum: 1,
            maximum: 10,
            description: "可选，候选 Creator 数量。默认 5，最大 10。",
          },
        },
        required: ["query"],
      });
      expect(schema.outputSchema).toEqual({
        type: "object",
        properties: {
          query: { type: "string", maxLength: 100 },
          results: {
            type: "array",
            maxItems: 10,
            items: {
              type: "object",
              properties: {
                mid: {
                  type: "integer",
                  minimum: 1,
                  maximum: Number.MAX_SAFE_INTEGER,
                },
                name: { type: "string", minLength: 1, maxLength: 128 },
                bio: { type: "string", maxLength: 512 },
                avatar_url: { type: "string", maxLength: 512 },
                follower_count: {
                  type: "integer",
                  minimum: 0,
                  maximum: Number.MAX_SAFE_INTEGER,
                },
                video_count: {
                  type: "integer",
                  minimum: 0,
                  maximum: Number.MAX_SAFE_INTEGER,
                },
                level: {
                  type: "integer",
                  minimum: 0,
                  maximum: Number.MAX_SAFE_INTEGER,
                },
                source_url: { type: "string", maxLength: 64 },
              },
              required: [
                "mid",
                "name",
                "bio",
                "avatar_url",
                "follower_count",
                "video_count",
                "level",
                "source_url",
              ],
            },
          },
        },
        required: ["query", "results"],
      });
    });

    it("is registered as the 10th tool", () => {
      const names = toolsResult.tools.map((t) => t.name);
      expect(names[9]).toBe("search_bilibili_creators");
    });
  });

  describe("list_bilibili_favorite_videos schema", () => {
    it("declares the bounded cursor input and structured favorites output", () => {
      const schema = toolsResult.tools.find(
        (tool) => tool.name === "list_bilibili_favorite_videos",
      )!;

      expect(schema).toBeDefined();
      expect(schema.inputSchema).toEqual({
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
      });
      expect(schema.outputSchema).toEqual({
        type: "object",
        properties: {
          folders_total: { type: "integer", minimum: 0, maximum: 100 },
          folder: {
            type: "object",
            properties: {
              id: { type: "integer" },
              title: { type: "string", maxLength: 256 },
              media_count: { type: "integer" },
            },
            required: ["id", "title", "media_count"],
          },
          page: { type: "integer" },
          videos: {
            type: "array",
            maxItems: 20,
            items: {
              type: "object",
              properties: {
                bvid: { type: "string", maxLength: 12 },
                title: { type: "string", maxLength: 512 },
                author: { type: "string", maxLength: 128 },
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
          next_cursor: { type: "string", maxLength: 256 },
        },
        required: ["folders_total", "videos", "skipped_count"],
      });
    });

    it("is registered as the 11th tool", () => {
      const names = toolsResult.tools.map((t) => t.name);
      expect(names[10]).toBe("list_bilibili_favorite_videos");
    });
  });

  describe("get_bilibili_creator_content schema", () => {
    it("declares the exact bounded mid/section/cursor input", () => {
      const schema = toolsResult.tools.find(
        (tool) => tool.name === "get_bilibili_creator_content",
      )!;

      expect(schema).toBeDefined();
      expect(schema.inputSchema).toEqual({
        type: "object",
        properties: {
          mid: {
            type: "integer",
            minimum: 1,
            maximum: Number.MAX_SAFE_INTEGER,
            description:
              "Bilibili Creator 数字 mid（正整数安全整数），如 2088259175。",
          },
          section: {
            type: "string",
            enum: ["overview", "videos"],
            description:
              "要读取的内容段：overview 返回有界档案与可用计数事实；videos 返回至多一页 20 条当前可列表 BVID 元数据。",
          },
          cursor: {
            type: "string",
            minLength: 1,
            maxLength: 256,
            pattern: "^[A-Za-z0-9_-]+$",
            description:
              "Opaque continuation token returned by a previous successful videos call. Omit on the first call; never pass a cursor for overview. The token encodes only a versioned Creator mid, section, and page number; it never contains credentials or Video data.",
          },
        },
        required: ["mid", "section"],
      });
    });

    it("declares the section-specific structured output contract", () => {
      const schema = toolsResult.tools.find(
        (tool) => tool.name === "get_bilibili_creator_content",
      )!;

      expect(schema.outputSchema).toEqual({
        type: "object",
        properties: {
          mid: {
            type: "integer",
            minimum: 1,
            maximum: Number.MAX_SAFE_INTEGER,
          },
          section: { type: "string", enum: ["overview", "videos"] },
          name: { type: "string", minLength: 1, maxLength: 128 },
          bio: { type: "string", maxLength: 512 },
          avatar_url: { type: "string", maxLength: 512 },
          follower_count: {
            type: "integer",
            minimum: 0,
            maximum: Number.MAX_SAFE_INTEGER,
          },
          level: {
            type: "integer",
            minimum: 0,
            maximum: Number.MAX_SAFE_INTEGER,
          },
          video_count: {
            type: "integer",
            minimum: 0,
            maximum: Number.MAX_SAFE_INTEGER,
          },
          page: {
            type: "integer",
            minimum: 1,
            maximum: Math.floor(Number.MAX_SAFE_INTEGER / 20),
          },
          videos_total: {
            type: "integer",
            minimum: 0,
            maximum: Number.MAX_SAFE_INTEGER,
          },
          videos: {
            type: "array",
            maxItems: 20,
            items: {
              type: "object",
              properties: {
                bvid: { type: "string", minLength: 1, maxLength: 12 },
                title: { type: "string", minLength: 1, maxLength: 512 },
                description: { type: "string", maxLength: 512 },
                cover_url: { type: "string", maxLength: 512 },
                category_id: {
                  type: "integer",
                  minimum: 1,
                  maximum: Number.MAX_SAFE_INTEGER,
                },
                category: { type: "string", maxLength: 64 },
                duration_seconds: {
                  type: "integer",
                  minimum: 0,
                  maximum: Number.MAX_SAFE_INTEGER,
                },
                published_at: { type: "string" },
                author: { type: "string", maxLength: 128 },
                view_count: {
                  type: "integer",
                  minimum: 0,
                  maximum: Number.MAX_SAFE_INTEGER,
                },
                danmaku_count: {
                  type: "integer",
                  minimum: 0,
                  maximum: Number.MAX_SAFE_INTEGER,
                },
                reply_count: {
                  type: "integer",
                  minimum: 0,
                  maximum: Number.MAX_SAFE_INTEGER,
                },
                is_charge_video: { type: "boolean" },
                access: { type: "string", enum: ["unknown"] },
                source_url: { type: "string" },
              },
              required: [
                "bvid",
                "title",
                "description",
                "cover_url",
                "duration_seconds",
                "published_at",
                "author",
                "access",
                "source_url",
              ],
            },
          },
          skipped_count: { type: "integer", minimum: 0, maximum: 20 },
          next_cursor: {
            type: "string",
            minLength: 1,
            maxLength: 256,
            pattern: "^[A-Za-z0-9_-]+$",
          },
          live_state: { type: "string", enum: ["live"] },
        },
        required: ["mid", "section", "live_state"],
      });
    });

    it("is registered as the 12th tool", () => {
      const names = toolsResult.tools.map((t) => t.name);
      expect(names[11]).toBe("get_bilibili_creator_content");
    });
  });
});
