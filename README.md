# Bilibili MCP Tool

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

```bash
# 安装依赖
npm install

# 构建
npm run build
```

## 使用

### 方式一：作为 MCP 服务器

在 Claude Desktop 的配置文件中添加：

**macOS/Linux**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

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

## 开发

```bash
# 监听模式编译
npm run watch
```

## 许可证

MIT
