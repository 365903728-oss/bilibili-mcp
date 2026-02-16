#!/usr/bin/env node

import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

function runCommand(command, options = {}) {
  try {
    const result = execSync(command, {
      encoding: 'utf8',
      ...options
    });
    return { success: true, output: result };
  } catch (error) {
    return { success: false, error: error.message, output: error.stdout };
  }
}

function checkFileExists(filePath) {
  return fs.existsSync(filePath);
}

function getFileContent(filePath) {
  try {
    return fs.readFileSync(filePath, 'utf8');
  } catch (error) {
    return null;
  }
}

console.log('🔍 检查 bilibili-mcp 项目配置...\n');

// 检查 package.json
const packageJsonPath = path.join(process.cwd(), 'package.json');
if (checkFileExists(packageJsonPath)) {
  console.log('✅ package.json 存在');
  const packageJson = JSON.parse(getFileContent(packageJsonPath));
  console.log(`   包名: ${packageJson.name}`);
  console.log(`   版本: ${packageJson.version}`);
  console.log(`   仓库: ${packageJson.repository?.url}`);
  console.log(`   发布配置: ${JSON.stringify(packageJson.publishConfig)}`);
} else {
  console.log('❌ package.json 不存在');
}

// 检查 workflow 文件
const workflowPath = path.join(process.cwd(), '.github', 'workflows', 'publish.yml');
if (checkFileExists(workflowPath)) {
  console.log('\n✅ workflow 文件存在');
  const workflowContent = getFileContent(workflowPath);
  const hasIdTokenPermission = workflowContent.includes('id-token: write');
  const hasContentsPermission = workflowContent.includes('contents: read');
  const hasProvenanceFlag = workflowContent.includes('--provenance');
  
  console.log(`   id-token: write 权限: ${hasIdTokenPermission ? '✅' : '❌'}`);
  console.log(`   contents: read 权限: ${hasContentsPermission ? '✅' : '❌'}`);
  console.log(`   --provenance 标志: ${hasProvenanceFlag ? '✅' : '❌'}`);
} else {
  console.log('\n❌ workflow 文件不存在');
}

// 检查 dist 目录
const distPath = path.join(process.cwd(), 'dist');
if (checkFileExists(distPath)) {
  console.log('\n✅ dist 目录存在');
  const distFiles = fs.readdirSync(distPath);
  console.log(`   包含文件: ${distFiles.length} 个`);
  if (distFiles.length > 0) {
    console.log(`   示例文件: ${distFiles.slice(0, 5).join(', ')}${distFiles.length > 5 ? '...' : ''}`);
  }
} else {
  console.log('\n❌ dist 目录不存在');
}

// 检查构建状态
console.log('\n🔧 检查构建状态...');
const buildResult = runCommand('npm run build');
if (buildResult.success) {
  console.log('✅ 构建成功');
} else {
  console.log('❌ 构建失败');
  console.log(`   错误: ${buildResult.error}`);
}

// 检查 npm 版本
console.log('\n📦 检查 npm 版本...');
const npmVersionResult = runCommand('npm --version');
if (npmVersionResult.success) {
  console.log(`✅ npm 版本: ${npmVersionResult.output.trim()}`);
  const versionParts = npmVersionResult.output.trim().split('.').map(Number);
  const isNewEnough = versionParts[0] >= 11 && versionParts[1] >= 5;
  console.log(`   版本足够新 (>= 11.5.1): ${isNewEnough ? '✅' : '❌'}`);
} else {
  console.log('❌ 无法获取 npm 版本');
}

// 检查 Git 配置
console.log('\n📡 检查 Git 配置...');
const gitRemoteResult = runCommand('git remote -v');
if (gitRemoteResult.success) {
  console.log('✅ Git 远程配置存在');
  console.log(`   远程地址: ${gitRemoteResult.output.trim()}`);
} else {
  console.log('❌ 无法获取 Git 远程配置');
}

// 检查最近的标签
console.log('\n🏷️ 检查最近的 Git 标签...');
const gitTagsResult = runCommand('git tag -l --sort=-v:refname | head -5');
if (gitTagsResult.success && gitTagsResult.output.trim()) {
  console.log('✅ Git 标签存在');
  console.log(`   最近标签: ${gitTagsResult.output.trim()}`);
} else {
  console.log('❌ 没有找到 Git 标签');
}

console.log('\n📋 故障排除建议:');
console.log('1. 确保在 npmjs.com 上正确配置了 Trusted Publisher');
console.log('   - Owner: 365903728-oss');
console.log('   - Repository: bilibili-mcp');
console.log('   - Workflow name: publish.yml');
console.log('2. 确保你是包的所有者或具有发布权限');
console.log('3. 检查 GitHub Actions 运行日志获取详细错误信息');
console.log('4. 确保 npm 版本 >= 11.5.1');
console.log('5. 尝试手动触发 workflow 测试');
console.log('6. 检查 package.json 中的仓库配置是否正确');
console.log('7. 确保工作流文件路径正确: .github/workflows/publish.yml');

console.log('\n🔗 参考链接:');
console.log('- npm Trusted Publisher 文档: https://docs.npmjs.com/using-private-packages-in-a-ci-cd-workflow#using-the-oidc-provider');
console.log('- GitHub Actions OIDC 文档: https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect');
