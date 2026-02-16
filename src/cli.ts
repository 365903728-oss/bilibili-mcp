#!/usr/bin/env node

// CLI 入口点
import { program } from 'commander';
import { server } from "./server.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { credentialManager } from './utils/credentials.js';

// 版本信息
import fs from 'fs';
const packageJson = JSON.parse(fs.readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

// 启动 MCP 服务器
async function startServer() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Bilibili MCP server running on stdio");
}

// 配置环境变量
async function configureCredentials() {
  const readline = await import('readline');

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  console.log('请输入您的 Bilibili 凭证信息（可从浏览器开发者工具中获取）：');

  const sessdata = await new Promise<string>((resolve) => {
    rl.question('SESSDATA: ', resolve);
  });

  const bili_jct = await new Promise<string>((resolve) => {
    rl.question('bili_jct: ', resolve);
  });

  const dedeuserid = await new Promise<string>((resolve) => {
    rl.question('DedeUserID: ', resolve);
  });

  rl.close();

  try {
    credentialManager.setCredentials({
      sessdata,
      bili_jct,
      dedeuserid,
      expiresAt: Date.now() + 30 * 24 * 60 * 60 * 1000 // 30天过期
    });

    console.log('凭证信息配置成功！');
    console.log('');
    console.log('注意：');
    console.log('1. 凭证信息将存储在内存中，重启工具后需要重新配置');
    console.log('2. 您也可以通过设置环境变量来永久配置：');
    console.log('   - BILIBILI_SESSDATA');
    console.log('   - BILIBILI_BILI_JCT');
    console.log('   - BILIBILI_DEDEUSERID');
    console.log('3. 或创建 .env 文件（复制 .env.example 并填写）');

  } catch (error) {
    console.error('配置失败：', error);
    process.exit(1);
  }
}

// 检查配置状态
function checkConfig() {
  const creds = credentialManager.getCredentials();
  if (creds) {
    console.log('配置状态：已配置');
    console.log('');
    console.log('DedeUserID:', creds.dedeuserid);
    console.log('');
    if (credentialManager.isExpiringSoon()) {
      console.warn('警告：凭证将在7天内过期');
    }
  } else {
    console.log('配置状态：未配置');
    console.log('');
    console.log('请使用以下方法之一配置凭证：');
    console.log('1. bilibili-mcp config');
    console.log('2. 设置环境变量');
    console.log('3. 创建 .env 文件');
  }
}

// 显示帮助信息
function showHelp() {
  console.log(`bilibili-mcp ${packageJson.version}`);
  console.log('');
  console.log('Bilibili MCP 工具 - 视频和评论总结');
  console.log('');
  console.log('用法：');
  console.log('  bilibili-mcp             启动 MCP 服务器');
  console.log('  bilibili-mcp config      配置 Bilibili 凭证');
  console.log('  bilibili-mcp check       检查配置状态');
  console.log('  bilibili-mcp help        显示此帮助信息');
  console.log('');
  console.log('选项：');
  console.log('  --version, -v            显示版本号');
  console.log('  --help, -h               显示帮助信息');
}

// 主函数
async function main() {
  // 设置命令行参数
  program
    .name('bilibili-mcp')
    .version(packageJson.version)
    .description('Bilibili MCP 工具 - 视频和评论总结');

  // 启动命令（默认）
  program
    .arguments('[command]')
    .action(async (command) => {
      switch (command) {
        case 'config':
          await configureCredentials();
          break;
        case 'check':
          checkConfig();
          break;
        case 'help':
        case '--help':
        case '-h':
          showHelp();
          break;
        case 'version':
        case '--version':
        case '-v':
          console.log(packageJson.version);
          break;
        case undefined:
          await startServer();
          break;
        default:
          console.error(`未知命令：${command}`);
          console.error('');
          showHelp();
          process.exit(1);
      }
    });

  // 配置命令
  program
    .command('config')
    .description('配置 Bilibili 凭证信息')
    .action(configureCredentials);

  // 检查配置命令
  program
    .command('check')
    .description('检查配置状态')
    .action(checkConfig);

  // 帮助命令
  program
    .command('help')
    .description('显示帮助信息')
    .action(showHelp);

  await program.parseAsync(process.argv);
}

main().catch((error) => {
  console.error("Fatal error in main():", error);
  process.exit(1);
});