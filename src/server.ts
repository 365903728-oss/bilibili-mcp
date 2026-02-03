// MCP 服务器定义
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { getVideoInfoWithSubtitle } from "./bilibili/subtitle.js";
import { getVideoCommentsData } from "./bilibili/comments.js";

// 创建 MCP 服务器实例
export const server = new Server(
  {
    name: "bilibili-mcp-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// 注册工具列表处理器
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "get_video_info",
        description:
          "获取 Bilibili 视频信息，优先返回字幕内容，如无字幕则返回视频简介和标签。支持指定偏好语言。",
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
          },
          required: ["bvid_or_url"],
        },
      },
      {
        name: "get_video_comments",
        description:
          "获取 Bilibili 视频热门评论。过滤表情占位符，优先保留包含时间戳的评论（如 '05:20'）。支持 brief（10条）和 detailed（50条+回复）两种模式。",
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
                "评论详细程度：'brief' 获取前10条热门评论；'detailed' 获取前50条热门评论及其高赞回复",
              enum: ["brief", "detailed"],
            },
          },
          required: ["bvid_or_url"],
        },
      },
    ],
  };
});

// 注册工具调用处理器
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "get_video_info": {
        const bvidOrUrl = args?.bvid_or_url as string;
        const preferredLang = args?.preferred_lang as string | undefined;

        if (!bvidOrUrl) {
          throw new Error("Missing required parameter: bvid_or_url");
        }

        const result = await getVideoInfoWithSubtitle(bvidOrUrl, preferredLang);

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case "get_video_comments": {
        const bvidOrUrl = args?.bvid_or_url as string;
        const detailLevel = (args?.detail_level as "brief" | "detailed") || "brief";

        if (!bvidOrUrl) {
          throw new Error("Missing required parameter: bvid_or_url");
        }

        const result = await getVideoCommentsData(bvidOrUrl, detailLevel);

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    console.error(`Error executing tool ${name}:`, error);
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              error: true,
              message: error instanceof Error ? error.message : "Unknown error",
            },
            null,
            2
          ),
        },
      ],
      isError: true,
    };
  }
});
