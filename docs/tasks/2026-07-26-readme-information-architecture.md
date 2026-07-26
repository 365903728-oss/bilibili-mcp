# README Information Architecture

- ID: `DOCS-README-2026-07-26`
- Status: `done`
- Owner: `Codex`
- Source: User-requested README optimization after the v1.7–v1.9 audit

## Objective

Turn the Chinese and English READMEs back into concise project homepages while preserving the complete client setup and MCP tool reference in dedicated documentation.

## Scope

In scope:

- Add accessible text titles and accurate first-use paths.
- Move exhaustive client setup and tool examples into bilingual reference documents.
- Keep current credential, error, tool, and release claims accurate.
- Package the local README hero asset.

Out of scope:

- MCP runtime, schemas, tests, credentials, release workflow, commits, pushes, tags, and publication.

## Files To Inspect Or Edit

- `README.md`, `README_EN.md`
- `assets/readme/hero.svg`, `assets/readme/hero-en.svg`
- `docs/client-setup.md`, `docs/client-setup.en.md`
- `docs/tool-reference.md`, `docs/tool-reference.en.md`
- `package.json`
- `docs/agent-memory/codemap.md`, `docs/agent-memory/verification-log.md`

Do not touch source code, tests, credentials, generated `dist/`, or the existing review-gated learning proposal.

## Acceptance Criteria

- [x] Both READMEs provide a concise value → proof → first-use → detail path.
- [x] The complete Agent-guided installation prompt is prominent in both bilingual client setup guides and covers client identification, client-specific syntax, local credential entry, reconnection, login validation, and optional update checking.
- [x] Both READMEs link prominently to the matching client setup guide without duplicating end-user installation or configuration methods.
- [x] Every existing client configuration and tool example remains reachable.
- [x] Client-specific configuration is not presented as universal.
- [x] README hero assets are included by `npm pack --dry-run`.
- [x] No Cookie or secret value is added.

## Verification

```bash
python C:\Users\ZX\.agents\skills\beautify-github-readme\scripts\audit_readme.py README.md
python C:\Users\ZX\.agents\skills\beautify-github-readme\scripts\audit_readme.py README_EN.md
npm test -- tests/credential-guidance.test.ts tests/server-credential-tools.test.ts
npm pack --dry-run --json --ignore-scripts
git diff --check
```

Manual checks:

- Verify internal links and bilingual navigation.
- Inspect the hero at desktop and narrow widths.
- Confirm MCP tool names and public behavior remain unchanged.

## Stop And Report Conditions

Stop if content cannot be moved without dropping an existing client, tool example, security boundary, or if package verification exposes unrelated failures.
