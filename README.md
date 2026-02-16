# Bilibili MCP Tool
用claude code(glm4.7模型)做的总结B站视频的MCP

MCP工具包括两个tools,视频总结和评论获取

Bilibili MCP (Model Context Protocol) 工具，用于总结 Bilibili 视频和视频评论。支持在 Claude Code、Cursor、Trae 等多种 MCP 兼容平台上使用。


---

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







## 安装方式

### 在 Claude Code 中安装

#### 方法一：通过配置文件安装

1. 打开 Claude Code 配置文件（通常在 `~/.claude.json`）
2. 在 `mcpServers` 部分添加以下配置：

```json
{
  "command": "cd C:\\Users\\ZX\\bilibili-mcp ; npm run watch",
  "env": {},
  "name": "bilibili-mcp",
  "path": "C:\\Users\\ZX\\bilibili-mcp"
}
```

3. 保存配置文件
4. 重启 Claude Code 使配置生效

#### 方法二：通过命令行安装

1. 打开命令行工具（CMD 或 PowerShell）
2. 进入项目目录：
   ```bash
   cd C:\Users\ZX\bilibili-mcp
   ```
3. 安装依赖：
   ```bash
   npm install
   ```
4. 启动开发服务器：
   ```bash
   npm run watch
   ```
5. 在 Claude Code 中使用 `/mcp connect` 命令连接到该服务器

### 环境变量配置

1. 复制 `.env.example` 文件为 `.env`：
   ```bash
   cp .env.example .env
   ```
2. 打开 `.env` 文件，根据需要配置以下变量：
   - `BILI_JCT`：Bilibili 登录凭证（可选，用于获取评论）
   - `SESSDATA`：Bilibili 会话数据（可选，用于获取评论）
   - `BUVID3`：Bilibili 设备标识（可选）

**注意**：这些变量通常可以从浏览器的开发者工具中获取（Cookie 存储）。

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

- ✅ 使用 Bilibili 公开 API
- ✅ 敏感信息（Cookie）通过环境变量配置，不会提交到代码仓库
- ✅ 不存储任何用户数据
- ✅ 代码开源可审计
- ✅ 错误输出使用 `console.error` 避免干扰 Stdio 协议
- ⚠️ 用户需自行配置 B 站 Cookie（存储在本地 .env 文件中）

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

## 开发

```bash
# 监听模式编译
npm run watch
```

## 许可证

本项目采用 **GNU General Public License v3.0** 许可证。

此许可证意味着：
- 任何人都可以自由使用、修改和分发本软件
- 修改后的代码必须以相同的 GPL-3.0 许可证开源
- 禁止将代码用于闭源商业软件中（除非提供完整源代码）

完整的许可证文本请参见 [LICENSE](./LICENSE) 文件。

---

## 免责声明

> **重要法律声明：使用本工具前请仔细阅读以下条款**

### 商标声明

**Bilibili (哔哩哔哩) 是哔哩哔哩公司的注册商标**，本项目为第三方开源工具，与哔哩哔哩公司无任何关联或合作关系。

### 非商业用途限制

- 本项目**仅供个人学习和研究使用**
- 严禁用于任何形式的商业分发或商业用途
- 严禁用于大规模数据采集或爬虫行为
- 严禁将本工具集成到商业产品或服务中

### 合规义务

使用本工具时，您必须遵守：
- **《中华人民共和国反不正当竞争法》**
- Bilibili 的服务协议和用户协议
- Bilibili 的 API 使用规范

### 责任自负

- 开发者不对用户利用本工具进行的任何违规操作负责
- 开发者不对因使用本工具导致的账号风险（包括但不限于账号封禁、IP 限制等）负责
- 开发者不对因使用本工具可能产生的任何法律后果或经济损失负责
- 用户应独立承担使用本工具的一切风险

### 其他注意事项

1. **尊重版权** - 视频字幕、总结等内容可能受版权保护，请勿擅自传播
2. **数据隐私** - 本工具不存储、收集或传输任何用户的私密信息
3. **API 变更** - Bilibili 可能随时修改或关闭其 API，本工具可能因此无法正常工作
4. **请求限制** - 本工具已内置限流机制，但仍请合理使用，避免被限制