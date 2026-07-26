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
  it("exposes all 9 tools", () => {
    const names = toolsResult.tools.map((t) => t.name);
    expect(names).toHaveLength(9);
    expect(names).toContain("get_credential_setup_instructions");
    expect(names).toContain("check_bilibili_credentials");
    expect(names).toContain("check_mcp_update");
    expect(names).toContain("get_video_info");
    expect(names).toContain("get_video_comments");
    expect(names).toContain("get_video_transcript");
    expect(names).toContain("get_video_metadata");
    expect(names).toContain("get_video_chapters");
    expect(names).toContain("search_bilibili_videos");
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

    it("accepts optional preferred_lang", () => {
      schema = toolsResult.tools.find((t) => t.name === "get_video_info")!;
      expect(schema.inputSchema.properties).toHaveProperty("preferred_lang");
    });

    it("accepts optional page with integer type and minimum 1", () => {
      schema = toolsResult.tools.find((t) => t.name === "get_video_info")!;
      const prop = schema.inputSchema.properties.page as { type?: string; minimum?: number };
      expect(prop).toBeDefined();
      expect(prop.type).toBe("integer");
      expect(prop.minimum).toBe(1);
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

    it("accepts optional limit", () => {
      schema = toolsResult.tools.find(
        (t) => t.name === "get_video_comments",
      )!;
      expect(schema.inputSchema.properties).toHaveProperty("limit");
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

    it("accepts optional preferred_lang", () => {
      schema = toolsResult.tools.find(
        (t) => t.name === "get_video_transcript",
      )!;
      expect(schema.inputSchema.properties).toHaveProperty("preferred_lang");
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
});
