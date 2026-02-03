# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly.

### How to Report

**Do not** open a public issue. Instead, send an email or private message to:

- **Repository Owner**: 365903728-oss
- **GitHub Security Advisories**: Use [GitHub's Private Vulnerability Reporting](https://github.com/365903728-oss/bilibili-mcp/security/advisories/new)

### What to Include

Please include:

1. A description of the vulnerability
2. Steps to reproduce the issue
3. Potential impact of the vulnerability
4. Any suggested fixes or mitigations

### Response Timeline

- **Acknowledge**: Within 48 hours
- **Initial Assessment**: Within 1 week
- **Fix and Release**: As soon as possible, typically within 2 weeks

### Supported Versions

| Version | Support Status |
|---------|----------------|
| 1.x.x   | ✅ Supported   |
| < 1.0   | ❌ Unsupported |

## Security Best Practices

- This tool does not store any user data
- Only uses public Bilibili API endpoints
- Does not require authentication or personal information
- All errors are logged to stderr, not stdout

### For Users

- Always install from trusted sources (npm or this GitHub repository)
- Review the code before using in sensitive environments
- Be cautious when processing video content from unknown sources
