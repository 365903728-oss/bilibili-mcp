# Security Remediation External Evidence

## Research Topic

- Topic: Codex Security CLI availability, immutable publish Action refs, and the
  remaining Hono production advisory
- Date: 2026-07-30
- Owner: Codex
- Related task:
  `docs/agent-memory/handoffs/2026-07-30-deep-security-remediation-task-ticket.md`
- Refresh before: changing the publish workflow, MCP SDK, HTTP transport, or
  security-scan tooling

## Question

Which current external facts affect remediation of the 38 validated Codex
Security findings without expanding the task into a dependency migration or
release?

## Context

The remediation pins third-party publish Actions, needs an independent
post-fix scan, and must classify the nonzero production audit accurately.
External state is authoritative for Action refs, the public Codex Security
package, and dependency/advisory metadata; the current worktree remains
authoritative for reachability.

## Sources

| Source | Type | Date checked | Notes |
|--------|------|--------------|-------|
| [openai/codex-security](https://github.com/openai/codex-security) | official source | 2026-07-30 | Apache-2.0 CLI and TypeScript SDK; official README documents `scan .` and `--mode deep`. |
| npm metadata and installed `dist/api.js` for `@openai/codex-security` | official package / live registry CLI output | 2026-07-31 | Latest moved from the locally resolved CLI 0.1.3 to 0.1.4. Version 0.1.4 prepares completion, collects/validates artifacts, and then completes the workbench scan; 0.1.3 completed before collection. |
| GitHub API for `actions/checkout` ref `v4` | official source API | 2026-07-30 | Ref resolved to verified commit `11d5960a326750d5838078e36cf38b85af677262`. |
| GitHub API for `actions/setup-node` ref `v4` | official source API | 2026-07-30 | Ref resolved to verified commit `49933ea5288caeca8642d1e84afbd3f7d6820020`. |
| [GHSA-frvp-7c67-39w9](https://github.com/advisories/GHSA-frvp-7c67-39w9) | official advisory | 2026-07-30 | `@hono/node-server` versions below 2.0.5 are affected in the static-file serving surface. |
| npm metadata for `@modelcontextprotocol/sdk` and `@hono/node-server` | live registry CLI output | 2026-07-30 | SDK latest 1.30.0 permits `^1.19.9 || ^2.0.5`; Hono latest 2.0.12 requires Node 20. |

## Findings

- The official open-source Codex Security package provides a non-UI CLI. A
  dry run resolved the correct `0a1b` worktree, repository target, deep mode,
  output directory, and stored Codex credentials before the remediation scan
  was started.
- The first full retry used CLI 0.1.3 and failed after workbench completion
  because canonical-file collection ran afterward and found no regular
  `scan-manifest.json` in the output directory. The directory remained empty,
  so that run is not accepted as a scan artifact.
- The official 0.1.4 package changes this exact order to prepare completion,
  collect and validate canonical artifacts, and only then complete the
  workbench scan. The next retry must be a new 0.1.4 scan, not a rerun of the
  failed 0.1.3 record.
- The publish workflow can retain its current Action majors while replacing
  mutable `@v4` refs with the verified full commit SHAs above.
- `npm audit --omit=dev --json` is not clean: it reports two moderate nodes,
  the transitive `@hono/node-server@1.19.14` advisory and the direct MCP SDK
  parent through which it is installed.
- Worktree reachability is narrower than the installed graph. The only SDK
  module importing `@hono/node-server` is
  `server/streamableHttp.js` (plus SDK examples). This project imports the
  low-level server, MCP types, shared transport, and shared stdio helpers only;
  it has no Streamable HTTP, Hono, `serveStatic`, SSE, listener, or static-file
  import.
- Therefore the advisory remains an installed dependency risk and a nonzero
  audit result, but the reviewed stdio-only product has no source-to-sink path
  to the vulnerable static-file behavior.

## Applicability To This Project

Applies:

- Pin both third-party Actions to immutable commits and regression-test that
  every `uses:` value is a full SHA.
- Use the official Codex Security CLI for an additional full-worktree deep
  post-fix scan when the Desktop setup confirmation cannot be automated.
- Report the Hono advisory as installed-but-unreachable residual risk, not as a
  clean audit and not as a confirmed application vulnerability.

Does not apply:

- Do not add an HTTP transport, import Hono, or add static-file serving.
- Do not update the MCP SDK, Hono, package version, or lockfile inside this
  remediation. Those changes require their own compatibility and release
  review.
- Do not claim the CLI scan replaces or completes an existing Desktop scan ID;
  it is an independent official scan.

## Decision Impact

Recommended project action:

- Keep the immutable Action pins already applied.
- Keep the current dependency graph unchanged for this task.
- Preserve the production-audit caveat and re-evaluate it in a separate MCP
  SDK dependency ticket or immediately if an HTTP/static-file surface is
  introduced.
- Record the exact CLI version and generated report path used by the final
  post-fix scan.

Rules or files updated:

- `.github/workflows/publish.yml`
- `tests/publish-workflow-pins.test.ts`
- remediation QA/report and project memory

## Risks And Unknowns

- The failed 0.1.3 scan has no canonical artifacts and cannot be repaired or
  represented as completed by editing its empty output directory. A fresh
  0.1.4 scan is required.
- Real ASR end-to-end behavior remains unverified because no ready model exists
  locally and this task forbids downloading or switching one.
- A future SDK import change could make the Hono path reachable even if the
  package versions are unchanged.

## Staleness Notes

Refresh this research when:

- `@openai/codex-security`, `@modelcontextprotocol/sdk`, or
  `@hono/node-server` changes;
- the project introduces an HTTP or static-file surface;
- either publish Action major ref moves; or
- the release workflow is edited.

## Follow-Up

- [ ] Track the MCP SDK/Hono dependency refresh as a separate compatibility
  task; do not bundle it into the 38-finding remediation.
