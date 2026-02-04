# Bilibili MCP Tool
用claude code(glm4,7模型)做的提取B站视频的MCP

Bilibili MCP (Model Context Protocol) 工具，用于总结 Bilibili 视频和视频评论。

## 功能特性

### 1. 视频总结 (`get_video_info`)
- 优先获取视频的 CC 或 AI 字幕
- 无字幕时自动降级为视频标题、简介和标签
- 支持多语言字幕选择（默认优先简体中文）
- 可手动指定偏好字幕语言

### 2. 评论总结 (`get_video_comments`)
- 获取视频热门评论
- 自动过滤表情占位符（如 `[doge]`）
- 优先保留包含时间戳的评论（如 `05:20`）
- 支持两种详细程度：
  - `brief`: 10 条热门评论
  - `detailed`: 50 条热门评论 + 高赞回复

## 安装

### 方式一：从 npm 安装（推荐）

```bash
# 方式 A：使用 npx 直接运行（无需安装）
npx @xzxzzx/bilibili-mcp

# 方式 B：全局安装
npm install -g @xzxzzx/bilibili-mcp
```

### 方式二：从源码安装

```bash
# 克隆仓库
git clone https://github.com/365903728-oss/bilibili-mcp.git
cd bilibili-mcp

# 安装依赖
npm install

# 构建
npm run build
```

## 使用

### Claude Desktop 配置

在 Claude Desktop 的配置文件中添加 MCP 服务器：

**macOS/Linux**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

#### 推荐配置（使用 npm）

```json
{
  "mcpServers": {
    "bilibili": {
      "command": "npx",
      "args": ["@xzxzzx/bilibili-mcp"]
    }
  }
}
```

#### 或使用全局安装版本

```json
{
  "mcpServers": {
    "bilibili": {
      "command": "bilibili-mcp"
    }
  }
}
```

#### 本地源码运行（仅开发）

```json
{
  "mcpServers": {
    "bilibili": {
      "command": "node",
      "args": ["C:\\Users\\ZX\\bilibili-mcp\\dist\\index.js"]
    }
  }
}
```

### 方式二：直接运行

```bash
npm start
```

## 工具使用示例

### 获取视频信息（含字幕）

```json
{
  "name": "get_video_info",
  "arguments": {
    "bvid_or_url": "BV1xx4x1x7xx"
  }
}
```

### 获取视频信息（指定语言）

```json
{
  "name": "get_video_info",
  "arguments": {
    "bvid_or_url": "BV1xx4x1x7xx",
    "preferred_lang": "en"
  }
}
```

### 获取评论（简略模式）

```json
{
  "name": "get_video_comments",
  "arguments": {
    "bvid_or_url": "BV1xx4x1x7xx",
    "detail_level": "brief"
  }
}
```

### 获取评论（详细模式）

```json
{
  "name": "get_video_comments",
  "arguments": {
    "bvid_or_url": "BV1xx4x1x7xx",
    "detail_level": "detailed"
  }
}
```

## 返回数据格式

### 视频信息返回格式

```json
{
  "data_source": "subtitle",
  "video_info": {
    "title": "视频标题",
    "description": "视频简介",
    "tags": ["标签1", "标签2"],
    "subtitle_text": "字幕内容..."
  }
}
```

当 `data_source` 为 `description` 时，表示没有字幕，只有基本信息。

### 评论返回格式

```json
{
  "comments": [
    {
      "author": "用户名",
      "content": "评论内容",
      "likes": 123,
      "has_timestamp": true,
      "timestamp": "05:20"
    }
  ],
  "summary": {
    "total_comments": 50,
    "comments_with_timestamp": 5
  }
}
```

## 安全性

- 仅使用 Bilibili 公开 API，无需登录
- 不存储任何用户数据
- 代码开源可审计
- 错误输出使用 `console.error` 避免干扰 Stdio 协议

## API 限流机制

为了遵守 Bilibili 的 API 使用规范并防止被限制，本工具实现了请求限流机制：

### 限流配置

| 配置项 | 值 |
|--------|-----|
| 请求间隔 | 500ms（0.5 秒） |
| 请求方式 | 队列顺序执行，不并发 |

### 为什么需要限流

1. **遵守 Bilibili API 规范** - 避免高频请求导致账号或 IP 被限制
2. **保证稳定性** - 降低 API 返回错误或被拒绝的风险
3. **尊重服务提供方** - 合理使用公共资源

### 对用户的影响

| 操作 | 预计额外延迟 |
|------|-------------|
| 获取视频信息 | 约 1-1.5 秒（2-3 个 API 调用） |
| 获取视频评论 | 约 1 秒（2 个 API 调用） |

对于视频总结的使用场景，这个延迟是**可接受**的，因为：
- 用户通常一次只总结一个视频
- 1-2 秒的等待时间在正常范围内
- 避免被限流后完全无法使用的风险

## 免责声明

本项目仅供学习和个人使用，请确保您遵守 Bilibili 的服务条款和相关法律法规。

**使用须知：**

1. **仅限非商业用途** - 本工具不应用于商业目的或商业分发
2. **尊重版权** - 视频字幕、总结等内容可能受版权保护，请勿擅自传播或用于商业用途
3. **遵守服务条款** - 使用本工具即表示您同意遵守 Bilibili 的用户协议和 API 使用规范
4. **数据隐私** - 本工具不存储、收集或传输任何用户的私密信息
5. **风险自负** - 作者不对因使用本工具导致的任何问题或损失负责
6. **API 变更** - Bilibili 可能随时修改或关闭其 API，本工具可能因此无法正常工作
7. **请求限制** - 请勿高频请求，以免被 Bilibili 限制或封禁

**注意：** 本项目与 Bilibili 官方无关，并非 Bilibili 官方产品。Bilibili 是哔哩哔哩弹幕网的商标。

## 开发

```bash
# 监听模式编译
npm run watch
```

## 许可证

MIT
