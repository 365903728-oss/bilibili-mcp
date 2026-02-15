// MCP 服务器入口
import { config } from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

// 获取当前文件的目录
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// 使用绝对路径加载.env文件
const envPath = resolve(__dirname, '../.env');
config({ path: envPath });

import { server } from "./server.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

// 启动服务器
async function main() {
  console.error("本工具仅供技术研究使用，请确保您的访问行为符合平台规范");
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Bilibili MCP server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error in main():", error);
  process.exit(1);
});
