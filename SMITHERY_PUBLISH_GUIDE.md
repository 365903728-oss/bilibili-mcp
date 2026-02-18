# Smithery.ai 发布指南

本指南将帮助你在 Smithery.ai 上发布 Bilibili MCP 服务器。

## 前置准备

### 1. 确认项目状态

在发布前，请确认以下内容：

- ✅ `smithery.json` 配置文件已创建
- ✅ `package.json` 中的版本号正确
- ✅ README.md 和 README_EN.md 文档完整
- ✅ 项目已构建：`npm run build`
- ✅ 代码已推送到 GitHub 仓库
- ✅ 已发布到 npm：`npm publish`

### 2. 检查必要文件

```bash
# 确保这些文件存在
ls smithery.json      # Smithery 配置文件
ls package.json       # npm 包配置
ls README.md          # 中文文档
ls README_EN.md       # 英文文档
ls LICENSE            # 许可证文件
ls dist/index.js      # 构建产物
```

## 发布步骤

### 步骤 1: 访问 Smithery.ai

1. 访问 [Smithery.ai](https://smithery.ai)
2. 注册/登录账号
3. 进入 "Publish" 或 "Submit MCP" 页面

### 步骤 2: 填写基本信息

在 Smithery.ai 的表单中填写：

| 字段 | 值 |
|------|-----|
| **Name** | `bilibili-mcp` |
| **Display Name** | `Bilibili MCP - 视频总结与评论工具` |
| **Description** | `Bilibili (B站) MCP 工具，用于总结视频内容（含字幕）和获取热门评论。支持多语言字幕，智能过滤无意义评论，保留带时间戳的高质量评论。` |
| **Repository** | `https://github.com/365903728-oss/bilibili-mcp` |
| **NPM Package** | `@xzxzzx/bilibili-mcp` |
| **Version** | `1.1.8` |
| **License** | `GPL-3.0` |
| **Author** | `xzxzzx` |

### 步骤 3: 上传 smithery.json

在 Smithery.ai 上：

1. 找到 "Upload Configuration" 或 "Import from smithery.json" 选项
2. 上传项目根目录下的 `smithery.json` 文件
3. Smithery 会自动解析工具定义和环境变量要求

### 步骤 4: 配置工具信息

Smithery.ai 会自动解析以下工具：

#### 工具 1: get_video_info
- **名称**: `get_video_info`
- **功能**: 获取视频信息和字幕
- **参数**:
  - `bvid_or_url` (必填): BV 号或 URL
  - `preferred_lang` (可选): 语言偏好

#### 工具 2: get_video_comments
- **名称**: `get_video_comments`
- **功能**: 获取热门评论
- **参数**:
  - `bvid_or_url` (必填): BV 号或 URL
  - `detail_level` (可选): `brief` 或 `detailed`

### 步骤 5: 配置环境变量

Smithery.ai 会识别以下可选环境变量：

| 变量名 | 描述 | 必填 | 是否敏感 |
|--------|------|------|----------|
| `BILIBILI_SESSDATA` | Bilibili SESSDATA Cookie | ❌ | ✅ 是 |
| `BILIBILI_BILI_JCT` | Bilibili bili_jct Cookie | ❌ | ✅ 是 |
| `BILIBILI_DEDEUSERID` | Bilibili DedeUserID Cookie | ❌ | ✅ 是 |

**注意**:
- 这些环境变量都是**可选的**
- 不配置也能使用基本功能（获取视频信息）
- 配置后可以获取评论（需要登录凭证）

### 步骤 6: 添加分类和标签

建议选择以下分类：

- **主要分类**: Video, Social Media
- **标签**:
  - `chinese-content`
  - `video`
  - `subtitle`
  - `comments`
  - `entertainment`
  - `bilibili`

### 步骤 7: 添加图标和截图（可选）

为了提高 MCP 的吸引力，建议添加：

1. **图标** (Icon)
   - 尺寸: 512x512 像素
   - 格式: PNG 或 SVG
   - 建议使用 Bilibili 的粉色主题

2. **截图** (Screenshots)
   - 展示在 Claude Code 中的使用示例
   - 展示工具返回的数据格式
   - 展示配置过程

### 步骤 8: 填写安装说明

Smithery.ai 会自动生成安装说明，你可以手动调整：

```bash
# 使用 npx 直接运行（推荐）
npx @xzxzzx/bilibili-mcp

# 或全局安装后使用
npm install -g @xzxzzx/bilibili-mcp
bilibili-mcp
```

**Claude Desktop 配置示例**:

```json
{
  "mcpServers": {
    "bilibili": {
      "command": "bilibili-mcp"
    }
  }
}
```

**带环境变量的配置**:

```json
{
  "mcpServers": {
    "bilibili": {
      "command": "bilibili-mcp",
      "env": {
        "BILIBILI_SESSDATA": "your_sessdata_here",
        "BILIBILI_BILI_JCT": "your_bili_jct_here",
        "BILIBILI_DEDEUSERID": "your_dedeuserid_here"
      }
    }
  }
}
```

### 步骤 9: 提交审核

完成以上步骤后：

1. 检查所有填写的信息是否准确
2. 预览 MCP 页面（如果 Smithery 提供预览功能）
3. 点击 "Submit" 或 "Publish" 提交审核
4. 等待 Smithery.ai 团队审核（通常 1-3 个工作日）

### 步骤 10: 审核通过后

- 你的 MCP 将会在 Smithery.ai 市场上公开
- 用户可以通过 Smithery.ai 一键安装
- 记得分享链接到 README 和社区

## 发布检查清单

在提交前，请确认：

- [ ] `smithery.json` 文件存在且格式正确
- [ ] 项目已推送到 GitHub
- [ ] 已发布到 npm (`npm publish`)
- [ ] 版本号在 `package.json` 和 `smithery.json` 中一致
- [ ] README 文档包含安装说明
- [ ] LICENSE 文件存在且正确
- [ ] 所有示例代码可以正常运行
- [ ] 环境变量说明清晰

## 维护和更新

### 更新 MCP 版本

当你发布新版本时：

1. 更新 `package.json` 中的版本号
2. 更新 `smithery.json` 中的版本号
3. 运行 `npm run build` 重新构建
4. 运行 `npm publish` 发布到 npm
5. 在 Smithery.ai 上更新版本信息

### 监控用户反馈

定期检查：
- GitHub Issues
- Smithery.ai 上的评论和评分
- 社区反馈

## 常见问题

### Q: Smithery.ai 审核需要多长时间？

A: 通常 1-3 个工作日。如果遇到问题，他们会联系你。

### Q: 环境变量是必填的吗？

A: 不是。BILIBILI_SESSDATA 等变量都是可选的，不配置也能使用基本功能。

### Q: 如何获取 Bilibili Cookie？

A: 参考 README.md 中的"环境变量配置"章节。

### Q: 可以商业使用吗？

A: 请查看 LICENSE 文件和 README 中的"免责声明"章节。

### Q: MCP 被拒绝了怎么办？

A: 查看拒绝原因，修改后重新提交。常见问题包括：
- 文档不完整
- 缺少必要的配置文件
- 许可证问题
- 功能描述不清楚

## 联系方式

如有问题，请通过以下方式联系：

- GitHub Issues: https://github.com/365903728-oss/bilibili-mcp/issues
- 作者: xzxzzx

## 相关链接

- Smithery.ai: https://smithery.ai
- MCP 官方文档: https://modelcontextprotocol.io
- Bilibili MCP 仓库: https://github.com/365903728-oss/bilibili-mcp
- npm 包地址: https://www.npmjs.com/package/@xzxzzx/bilibili-mcp

---

**祝发布顺利！🎉**
