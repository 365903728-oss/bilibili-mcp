// MCP 服务器入口
import "./load-env.js";
import { fileURLToPath } from "url";
import { server } from "./server.js";
import { redactSecrets } from "./utils/logger.js";
import { BoundedStdioServerTransport } from "./server/bounded-stdio-transport.js";

// Reusable default server export for programmatic use
export default server;

// 启动服务器的入口点
async function main() {
  const transport = new BoundedStdioServerTransport();
  await server.connect(transport);
  console.error("Bilibili MCP server running on stdio");
}

// 检查是否作为主模块运行
if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main().catch((error) => {
    console.error("Fatal error:", redactSecrets(error));
    process.exit(1);
  });
}
