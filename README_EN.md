# Bilibili MCP Tool
Bilibili MCP (Model Context Protocol) tool for video and comment summarization. Supports use with Claude Code, Cursor, Trae and other MCP compatible platforms.

---

## Features

### 1. Video Summarization (`get_video_info`)
- Preferentially retrieves CC or AI subtitles
- Falls back to video title, description and tags if no subtitles are available
- Supports multi-language subtitle selection (default priority: Simplified Chinese)
- Manual language specification supported

### 2. Comment Summarization (`get_video_comments`)
- Retrieves popular video comments
- Automatically filters emoji placeholders (e.g., `[doge]`)
- Prioritizes comments with timestamps (e.g., `05:20`)
- Supports two detail levels:
  - `brief`: 10 popular comments
  - `detailed`: 50 popular comments + high-quality replies

## Installation

### Claude Code

#### Method 1: Direct npm Installation (Recommended)

The simplest way is to install globally via npm:

```bash
npm install -g @xzxzzx/bilibili-mcp
```

After installation:

1. Check if installation is successful:
   ```bash
   bilibili-mcp --help
   ```

2. Configure Bilibili credentials (first use):
   ```bash
   bilibili-mcp config
   ```

3. Check configuration status:
   ```bash
   bilibili-mcp check
   ```

4. Use directly in Claude Code without additional configuration

#### Method 2: Configuration File Installation (for development or custom paths)

1. Open Claude Code configuration file (typically at `~/.claude.json`)
2. Add the following configuration to the `mcpServers` section:

**Using npx (Recommended):**
```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "command": "npx",
      "args": ["-y", "@xzxzzx/bilibili-mcp"]
    }
  }
}
```

**For local development:**
```json
{
  "mcpServers": {
    "bilibili-mcp": {
      "command": "node",
      "args": ["/path/to/bilibili-mcp/dist/index.js"]
    }
  }
}
```

3. Save the configuration file
4. Restart Claude Code for changes to take effect

#### Method 3: CLI Command Installation (Simplest)

Simply run the following command:

```bash
claude mcp add bilibili-mcp npx -y @xzxzzx/bilibili-mcp
```

Then restart Claude Code.

### OpenCode

OpenCode is an open-source AI code editor that also supports MCP protocol.

#### Method 1: Configuration File Installation

1. Create or edit the OpenCode configuration file (located at `~/.config/opencode/opencode.json`)
2. Add the following configuration to the `mcp` section:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "bilibili-mcp": {
      "type": "local",
      "command": ["npx", "-y", "@xzxzzx/bilibili-mcp"],
      "enabled": true
    }
  }
}
```

3. Save the configuration file
4. Restart OpenCode for changes to take effect

#### Method 2: Local Development Mode

For local development usage:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "bilibili-mcp": {
      "type": "local",
      "command": ["node", "/path/to/bilibili-mcp/dist/index.js"],
      "enabled": true
    }
  }
}
```

### Environment Variables Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and configure as needed:
   - `BILIBILI_SESSDATA`: Bilibili session data
   - `BILIBILI_BILI_JCT`: Bilibili login credential
   - `BILIBILI_DEDEUSERID`: Bilibili user ID

**Note**: These variables can be obtained from browser developer tools (Cookie storage).

#### 🔒 Security Notice

- **.env files are not committed to Git** - included in `.gitignore`
- **Do not share your .env file or Cookie values**
- Cookies expire regularly and need to be re-acquired
- It is recommended to use a secondary or test account's cookies

## Usage Examples

### Get Video Information (with subtitles)

```json
{
  "name": "get_video_info",
  "arguments": {
    "bvid_or_url": "BV1xx4x1x7xx"
  }
}
```

### Get Video Information (specify language)

```json
{
  "name": "get_video_info",
  "arguments": {
    "bvid_or_url": "BV1xx4x1x7xx",
    "preferred_lang": "en"
  }
}
```

### Get Comments (brief mode)

```json
{
  "name": "get_video_comments",
  "arguments": {
    "bvid_or_url": "BV1xx4x1x7xx",
    "detail_level": "brief"
  }
}
```

### Get Comments (detailed mode)

```json
{
  "name": "get_video_comments",
  "arguments": {
    "bvid_or_url": "BV1xx4x1x7xx",
    "detail_level": "detailed"
  }
}
```

## Return Data Formats

### Video Information Return Format

```json
{
  "data_source": "subtitle",
  "video_info": {
    "title": "Video Title",
    "description": "Video description",
    "tags": ["tag1", "tag2"],
    "subtitle_text": "Subtitle content..."
  }
}
```

When `data_source` is `description`, it means no subtitles are available, only basic information.

### Comments Return Format

```json
{
  "comments": [
    {
      "author": "Username",
      "content": "Comment content",
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

## Security

- ✅ Uses Bilibili public API
- ✅ Sensitive information (Cookie) configured via environment variables, not committed to code repository
- ✅ No user data stored
- ✅ Open source auditable code
- ✅ Error output uses `console.error` to avoid interfering with Stdio protocol
- ⚠️ Users need to configure Bilibili Cookie themselves (stored in local .env file)

## API Rate Limiting

To comply with Bilibili API specifications and prevent being blocked, this tool implements request rate limiting:

### Rate Limiting Configuration

| Configuration Item | Value |
|-------------------|-------|
| Request Interval  | 500ms (0.5 seconds) |
| Request Method    | Sequential queue processing, no concurrency |

### Why Rate Limiting is Needed

1. **Comply with Bilibili API specifications** - avoid high-frequency requests causing account or IP restrictions
2. **Ensure stability** - reduce risk of API errors or rejection
3. **Respect service provider** - use public resources responsibly

### Impact on Users

| Operation | Estimated Additional Delay |
|-----------|---------------------------|
| Get video information | Approximately 1-1.5 seconds (2-3 API calls) |
| Get video comments | Approximately 1 second (2 API calls) |

For video summarization use cases, this delay is **acceptable**:
- Users typically summarize one video at a time
- 1-2 second wait time is within normal range
- Avoids the risk of being restricted and completely unavailable

## Development

```bash
# Watch mode compilation
npm run watch
```

## License

This project uses **GNU General Public License v3.0**.

This license means:
- Anyone can freely use, modify and distribute this software
- Modified code must be open source under the same GPL-3.0 license
- Prohibited from being used in closed-source commercial software (unless complete source code is provided)

For the full license text, please see [LICENSE](./LICENSE) file.

## Contribution and Feedback

### Reporting Issues

If you find any bugs or have improvement suggestions, please report them through:

1. Check if a similar issue already exists
2. Click the "New issue" button on the [Issues](https://github.com/365903728-oss/bilibili-mcp/issues) page
3. Select an appropriate template (Bug report or Feature request)
4. Fill in the details including:
   - Description of the issue
   - Steps to reproduce
   - Operating system and tool version used
   - Any relevant error messages or screenshots

### Submitting Pull Requests

We welcome contributions from the community:

1. Fork the project
2. Create a new branch
3. Make your changes
4. Test your changes
5. Submit a Pull Request

### Development Environment Setup

```bash
# Clone the repository
git clone https://github.com/365903728-oss/bilibili-mcp.git

# Install dependencies
cd bilibili-mcp
npm install

# Start development server
npm run watch
```

---

## Disclaimer

> **Important Legal Notice: Please read these terms carefully before using this tool**

### Trademark Notice

**Bilibili is a registered trademark of Bilibili Inc.** This project is a third-party open source tool and has no affiliation or cooperation with Bilibili Inc.

### Non-Commercial Use Restrictions

- This project is **for personal learning and research purposes only**
- Commercial distribution or use in any form is strictly prohibited
- Large-scale data collection or crawling behaviors are strictly prohibited
- Integration of this tool into commercial products or services is strictly prohibited

### Compliance Obligations

When using this tool, you must comply with:
- **Anti-Unfair Competition Law of the People's Republic of China**
- Bilibili's service agreements and user agreements
- Bilibili's API usage specifications

### Responsibility

- The developer is not responsible for any illegal operations performed by users using this tool
- The developer is not responsible for account risks (including but not limited to account suspension, IP restrictions, etc.) caused by using this tool
- The developer is not responsible for any legal consequences or economic losses that may result from using this tool
- Users should bear all risks of using this tool independently

### Other Notes

1. **Respect Copyright** - Video subtitles, summaries and other content may be copyrighted, please do not spread them without authorization
2. **Data Privacy** - This tool does not store, collect or transmit any user's private information
3. **API Changes** - Bilibili may modify or close its API at any time, and this tool may not function properly as a result
4. **Request Limits** - This tool has built-in rate limiting mechanisms, but please use it responsibly to avoid being restricted