# Task Ticket: Deep Security Remediation

Status: direct Codex implementation and local verification complete; the first
official post-fix deep scan failed before artifact collection due to the CLI
0.1.3 completion order, and a fresh CLI 0.1.4 scan remains required. No Paseo
or external implementation agent was used.

## Objective

Close all 38 validated findings from Codex Security scan
`6949ea8e-a129-43d6-9104-6edf7413a1ff` in the current uncommitted working tree,
without changing the ten-tool product boundary, exposing credentials, or
performing any Git or release operation.

## Scope

- Four Medium findings: bounded stdio framing, bounded HTTP admission,
  single-flight fingerprint bootstrap, and bounded transcript-search output.
- Thirty-four Low findings across shared outbound HTTP policy, response and
  cache budgets, output/error/log boundaries, subtitle integrity, ASR runtime
  and installer containment, development hooks/agent trust, and publish-action
  integrity.
- Deterministic offline regression tests and repository verification.
- Codex Security remediation validation against the completed scan artifacts.

## Patch Contract

- Prefer shared enforcement points over per-call-site guards:
  - bounded stdio transport and bounded successful MCP serialization;
  - bounded outbound HTTP reader, redirect/destination policy, aggregate retry
    and admission budgets;
  - bounded cache values and normalized upstream collections/strings;
  - aggregate ASR deadlines, cancellation, child environment and cleanup;
  - bounded, escaped and review-only harness observations.
- Preserve fixed tool names/order and existing successful result shapes where
  data remains within limits.
- Fail closed with small, stable, secret-free errors when a security limit is
  crossed.
- Never include a Cookie, signed media URL, token, `.env` value, child private
  path, or raw untrusted diagnostic in MCP output, logs, tests, or reports.
- Do not download or switch an ASR model and do not use live credentials or
  Bilibili network calls.

## Files

Primary runtime surfaces are under `src/server/`, `src/bilibili/`, `src/asr/`,
and `src/utils/`. Harness and release surfaces are under `.codex/agents/`,
`.codex/scripts/`, `.codex/hooks.json`, and `.github/workflows/publish.yml`.
Regression coverage belongs under `tests/` plus focused Python hook tests when
needed.

## Acceptance Criteria

- Every scan finding has a concrete closing control and a passing focused
  regression, or a documented platform containment boundary with the strongest
  portable control implemented and validated.
- `npm run build` passes.
- `npm test` passes.
- `npm pack --dry-run` contains only expected package files and no secrets.
- Scoped credential/secret scans pass with synthetic fixtures only.
- Stdio stdout remains JSON-RPC clean and oversized frames/results fail closed.
- No product source, test, documentation, or user-owned change is reverted.
- No stage, commit, push, pull request, tag, version bump, publish, release,
  model download, or persistent Codex configuration change occurs.

## Verification

```powershell
npm run build
npm test
npm pack --dry-run
git status --short --untracked-files=all
```

Focused tests must also cover queue saturation, cold-cache concurrency,
over-limit frames/bodies/results, redirect rejection, error/log redaction,
subtitle failure typing, ASR cancellation/deadlines/environment, hook input and
retention budgets, and immutable action references.

## Stop And Report Conditions

Stop only for a material scope expansion, unavoidable destructive action, or a
required real credential/model/network validation. Ordinary implementation
failures remain in scope and must be diagnosed and repaired without requesting
additional permission.

## Local Completion Evidence

- All 38 original `extensions.reportId` finding slugs have one closing control
  and regression entry in `docs/qa/2026-07-30-deep-security-remediation.md`;
  canonical IDs remain the separate `csf_*` values.
- Focused security suites pass 22 files / 407 tests.
- Full Vitest passes 38 files / 721 tests.
- TypeScript build, built CLI/public stdio smoke, 6 hook-safety tests, and 8
  stop-summary tests pass.
- The 180-file npm dry run has zero forbidden structural paths and zero
  high-confidence private-key/GitHub/npm/AWS-token content matches.
- Production audit remains explicitly nonzero for the installed Hono
  static-file advisory; current stdio-only imports do not reach that module.
- No model, real Cookie, Git operation, version, publication, or persistent
  Codex configuration change was used.

The ticket is not final until the independent official Codex Security re-scan
has generated and sealed its report/artifacts.
