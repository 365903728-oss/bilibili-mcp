# Research Note: npm Trusted Publishing For v1.10.0

## Research Topic

- Topic: Current GitHub Actions OIDC and npm trusted-publishing requirements
- Date: 2026-07-27
- Owner: Codex
- Related task: GitHub Issue #22 / `v1.10.0` release
- Refresh before: any publish-workflow edit

## Sources

| Source | Type | Date checked | Notes |
|--------|------|--------------|-------|
| https://docs.npmjs.com/trusted-publishers/ | official npm docs | 2026-07-27 | GitHub trusted publishing requires OIDC, npm 11.5.1+, Node 22.14.0+, and a GitHub-hosted runner. |
| https://docs.github.com/en/actions/reference/security/oidc | official GitHub docs | 2026-07-27 | `id-token: write` permits OIDC token requests; checkout also needs `contents: read`. |
| https://docs.github.com/en/actions/tutorials/publish-packages/publish-nodejs-packages | official GitHub docs | 2026-07-27 | Current Node-package examples use registry setup plus `npm publish`. |

## Findings And Decision

- `.github/workflows/publish.yml` already uses Ubuntu, Node `22.14.0`, npm `11.18.0`, `id-token: write`, `contents: read`, `npm ci`, tests, build, and direct public publication with provenance.
- The workflow satisfies the current documented minimums and has already published `v1.9.1` successfully.
- No workflow, token, dependency, action-version, or provenance change is needed for `v1.10.0`.

## Staleness Notes

Refresh when the workflow, Node/npm versions, npm trusted publisher, or GitHub OIDC requirements change.
