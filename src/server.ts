// MCP 服务器定义
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import fs from "fs";
import { logger } from "./utils/logger.js";
import { toolSchemas } from "./server/tool-schemas.js";
import { handleToolCall } from "./server/tool-handlers.js";
import {
  buildGenericErrorPayload,
  toErrorTextContent,
} from "./server/error-response.js";
import { runWithOperationSignal } from "./security/operation-context.js";

const packageJson = JSON.parse(
  fs.readFileSync(new URL("../package.json", import.meta.url), "utf8")
);

// 创建 MCP 服务器实例
export const server = new Server(
  {
    name: "bilibili-mcp-server",
    version: packageJson.version,
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// 注册工具列表处理器
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: toolSchemas,
}));

// 注册工具调用处理器
server.setRequestHandler(CallToolRequestSchema, async (request, extra) => {
  const { name, arguments: args } = request.params;

  try {
    return await runWithOperationSignal(
      extra?.signal,
      async () => await handleToolCall(
        name,
        args as Record<string, unknown> | undefined,
        extra?.signal,
      ),
    );
  } catch (error) {
    logger.error(
      "Error processing MCP tool",
      { error },
      { type: "mcp-tool-error" },
    );
    return toErrorTextContent(buildGenericErrorPayload(error));
  }
});
