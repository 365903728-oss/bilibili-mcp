# 创建 npm Granular Access Token 指南

由于 npm 只支持 Granular Access Tokens，请按照以下步骤创建：

## 步骤1：创建 Granular Access Token

1. 访问 https://www.npmjs.com/settings/365903728/tokens
2. 点击 **"Create New Token"**
3. 点击 **"Create Granular Access Token"**
4. 配置权限：
   - **Publish**: ✅ `bilibili-mcp` 包的发布权限
   - **Other**: 取消所有其他权限（最小权限原则）
5. 给 token 命名，比如 `github-actions-publish`
6. 点击 **"Create Token"**
7. **立即复制 token**（只显示一次！）

## 步骤2：更新 GitHub Secrets

1. 进入你的 GitHub 仓库
2. Settings → Secrets and variables → Actions
3. 点击 **"New repository secret"**
4. Name: `NPM_TOKEN`
5. Secret: 你刚复制的 token
6. 点击 **"Add secret"**

## 步骤3：测试发布

更新 secret 后，GitHub Actions 应该能正常发布了。

## 注意事项

- Granular Access Tokens 需要 2FA 验证
- GitHub Actions 可以处理 2FA，前提是 token 有正确的权限
- 确保只勾选了 `Publish` 权限