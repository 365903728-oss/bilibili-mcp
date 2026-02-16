# Bilibili MCP Tool
用claude code(glm4.7模型)做的提取B站视频的MCP

Bilibili MCP (Model Context Protocol) 工具，用于总结 Bilibili 视频和视频评论。(安装方式在下方)

MCP工具包括两个tools,视频总结和评论获取

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

## 安装与使用

### 我该选择哪种安装方式？

如果您**不了解 MCP 工具**，请根据您的使用场景选择：

#### 🎯 场景一：普通使用（最常见）
**推荐：方式 A 或方式 B**

**首次使用**（最推荐，最简单）：
```bash
# 无需安装，直接运行
npx @xzxzzx/bilibili-mcp
```

**经常使用**（推荐）：
```bash
# 全局安装，以后直接运行
npm install -g @xzxzzx/bilibili-mcp
bilibili-mcp  # 安装后直接运行
```

#### 🔧 场景二：作为开发工具使用（本地项目）
**选择：方式 C**

```bash
npm install @xzxzzx/bilibili-mcp

# 运行方式：
npx bilibili-mcp  # 通过 npx 运行
# 或
./node_modules/.bin/bilibili-mcp  # 直接运行本地二进制文件
```

#### 📦 场景三：从源码修改或贡献
**选择：方式二（从源码安装）**

```bash
# 克隆仓库
git clone https://github.com/365903728-oss/bilibili-mcp.git
cd bilibili-mcp

# 安装依赖
npm install

# 构建
npm run build
```

## 什么是 Bilibili MCP 工具？

如果您是第一次听说 MCP（Model Context Protocol），简单来说：

**MCP 是一种让 AI 模型能够与外部工具通信的协议**。这个工具可以让 AI 模型直接访问 Bilibili 的视频信息和评论，无需您手动复制粘贴。

### 谁需要这个工具？
- 需要总结 Bilibili 视频内容的用户
- 需要获取视频热门评论的用户
- 希望提高工作效率的内容创作者或研究者

## 快速上手

### 第一步：确保已安装 Node.js
**这是使用本工具的前提条件**：
1. 访问 [Node.js 官网](https://nodejs.org/) 下载并安装
2. 验证安装成功：
   ```bash
   node -v
   # 应该显示 v18.0.0 或更高版本
   npm -v
   ```

### 第二步：安装工具
根据您的使用场景选择合适的安装方式（参考前文）。

### 第三步：运行工具
- 使用 npx 直接运行：`npx @xzxzzx/bilibili-mcp`
- 全局安装后运行：`bilibili-mcp`

### 第四步：配置环境变量（可选）
如果您需要获取视频字幕内容，需要配置 B 站登录凭证（参考前文）。

## 验证配置成功

直接运行工具，检查是否能够正常启动。如果看到以下信息，说明工具已正常运行：
```
本工具仅供技术研究使用，请确保您的访问行为符合平台规范
Bilibili MCP server running on stdio
```

### ⚠️ 重要：环境变量配置（可选但推荐）

**为了使用本工具的全部功能（特别是获取视频字幕内容），您需要配置 B 站的登录凭证。**

如果不配置，您仍可使用基本功能（获取视频信息和评论），但**无法获取字幕内容**。

#### 1. 获取 B 站 Cookie
1. 打开浏览器，登录 [Bilibili](https://www.bilibili.com)
2. 按 `F12` 打开开发者工具
3. 切换到 `Network`（网络）标签
4. 刷新页面，点击任意请求
5. 在 `Headers`（请求头）中找到 `Cookie` 字段
6. 复制以下三个值：
   - `SESSDATA=...`
   - `bili_jct=...`
   - `DedeUserID=...`

#### 2. 创建环境变量文件
在项目根目录下创建 `.env` 文件：
```bash
# 复制示例文件
cp .env.example .env
```

#### 3. 填入您的凭证
编辑 `.env` 文件，填入您刚才复制的值：
```env
# B站SESSDATA（从浏览器Cookie中获取）
BILIBILI_SESSDATA=你的_sessdata_值

# B站bili_jct（从浏览器Cookie中获取）
BILIBILI_BILI_JCT=你的_bili_jct_值

# B站DedeUserID（从浏览器Cookie中获取）
BILIBILI_DEDEUSERID=你的_dedeuserid_值
```

#### 4. 验证配置
```bash
# 检查环境变量是否正确加载
npm run test:env
```

#### 🔒 安全提示
- **.env 文件不会被提交到 Git** - 已添加到 `.gitignore`
- **请勿分享您的 .env 文件或 Cookie 值**
- Cookie 定期会过期，需要重新获取
- 建议使用小号或测试账号的 Cookie

### 不配置环境变量的影响

- ✅ **仍可使用**：获取视频基本信息、评论
- ❌ **无法使用**：获取视频字幕内容、部分需要登录的 API

## 常见问题解答

### Q: 我需要安装什么软件才能使用？
A: 只需要安装 Node.js（v18.0.0 或更高版本）即可。

### Q: 为什么我无法运行命令？
A:
1. 检查 Node.js 是否已正确安装：`node -v`
2. 检查 npm 是否正常：`npm -v`
3. 尝试以管理员身份运行命令提示符

### Q: 获取字幕失败怎么办？
A:
1. 检查是否已配置环境变量
2. 确认 Cookie 值是否过期
3. 检查视频是否有字幕

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