# npm Trusted Publisher 配置指南

## 项目配置检查

我已经检查了你的项目配置，看到：

1. **GitHub Actions workflow** (`publish.yml`) 已经正确配置：
   - ✅ 包含了必要的权限设置 `id-token: write`
   - ✅ 使用了最新的 Node.js 和 npm
   - ✅ 执行 `npm publish --provenance --access public`

2. **package.json** 配置正确：
   - ✅ 包名：`@365903728-oss/bilibili-mcp`
   - ✅ 仓库地址：`https://github.com/365903728-oss/bilibili-mcp.git`
   - ✅ 发布配置：`"access": "public"`

## 关键步骤：在 npmjs.com 上配置 Trusted Publisher

现在你需要在 npmjs.com 上为你的包添加 Trusted Publisher 配置：

### 步骤 1：登录 npmjs.com
1. 打开 [npmjs.com](https://www.npmjs.com/)
2. 登录你的 npm 账号

### 步骤 2：找到你的包
1. 在顶部导航栏点击你的头像
2. 选择 "Packages"
3. 找到并点击 `@365903728-oss/bilibili-mcp` 包

### 步骤 3：进入包设置
1. 在包页面的右侧，点击 "Settings"
2. 找到 "Publishers" 部分

### 步骤 4：添加 Trusted Publisher
1. 点击 "Add Publisher"
2. 选择 "GitHub Actions"
3. 填写以下信息：
   - **Owner**: `365903728-oss`
   - **Repository**: `bilibili-mcp`
   - **Workflow name**: `publish.yml`
4. 点击 "Add Publisher" 保存配置

### 步骤 5：验证配置
1. 返回 GitHub 仓库
2. 创建一个新的标签（例如 `v1.1.6`）
3. 推送标签到 GitHub
4. 观察 GitHub Actions 运行状态
5. 检查 npmjs.com 上的包是否成功更新

## 技术说明

### Trusted Publisher 的优势
- **更安全**：不需要存储敏感的 NPM_TOKEN
- **更可靠**：使用 OIDC 认证，避免 token 过期问题
- **更易于管理**：直接与 GitHub 仓库和工作流绑定

### 必要条件
- npm 版本 ≥ 11.5.1（你的配置已经满足）
- GitHub Actions workflow 中设置了 `id-token: write` 权限（你的配置已经满足）
- 包所有者权限（你需要在 npmjs.com 上拥有包的管理权限）

## 故障排除

如果遇到问题：

1. **检查 npm 版本**：确保工作流中使用的 npm 版本 ≥ 11.5.1
2. **检查权限**：确认 workflow 文件中有正确的权限设置
3. **检查包名**：确保 npmjs.com 上的包名与 package.json 中的一致
4. **检查仓库配置**：确保 npmjs.com 上的仓库配置与 GitHub 仓库匹配

## 下一步

完成 npmjs.com 上的 Trusted Publisher 配置后，你就可以通过创建新标签来自动触发发布流程了。