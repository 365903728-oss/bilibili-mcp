# Official MCP Registry Publishing Research

## Research Topic

- Topic: Publish `@xzxzzx/bilibili-mcp` to the Official MCP Registry
- Date: 2026-08-06
- Owner: Codex
- Related task: `REGISTRY-001`
- Refresh before: Any later Registry release or metadata update

## Question

What does the current Official MCP Registry require for this public npm MCP server?

## Context

The project is already publicly published as npm version `1.11.1`, but that package does not declare the Registry ownership field.

## Sources

| Source | Type | Date checked | Notes |
|--------|------|--------------|-------|
| https://modelcontextprotocol.io/registry/quickstart | official docs | 2026-08-06 | npm package must contain `mcpName`; publish metadata with `mcp-publisher`. |
| https://modelcontextprotocol.io/registry/package-types | official docs | 2026-08-06 | npm public registry is supported and `mcpName` must match `server.json.name`. |
| https://modelcontextprotocol.io/registry/authentication | official docs | 2026-08-06 | GitHub authentication requires an `io.github.<owner>/...` namespace. |
| https://modelcontextprotocol.io/registry/moderation-policy | official docs | 2026-08-06 | Registry is permissive but removes malware, spam, illegal content, and non-functioning servers. |

## Findings

- The Registry stores metadata; the installable npm artifact must already be public.
- GitHub authentication permits the name `io.github.xzxzzx-ai/bilibili-mcp` when authenticated as the repository owner.
- `package.json.mcpName` and `server.json.name` must match exactly.
- Because npm version `1.11.1` is immutable and lacks `mcpName`, a new package version is required.

## Applicability To This Project

Applies:

- Add `mcpName`, create `server.json`, publish npm `1.11.2`, then publish Registry metadata.

Does not apply:

- No MCP tool behavior, transport, credential behavior, or dependency change is required.

## Decision Impact

- Use the existing tag-triggered trusted-publishing workflow for npm.
- Publish to the Official MCP Registry only after npm `1.11.2` is live.

## Risks And Unknowns

- Registry is still preview and its publishing CLI or schema may change.
- GitHub device authentication may require the user to approve a browser prompt.

## Follow-Up

- [ ] Verify npm `1.11.2`, Registry status, and public metadata after publication.
