# Fake-IP Node compatibility matrix

## Research Topic

- Topic: GitHub Actions matrix for the Issue #59 focused Fake-IP suite
- Date: 2026-08-23
- Owner: Codex
- Related task: GitHub Issue #59
- Refresh before: changing the Verify workflow or its pinned setup-node action

## Question

How should the repository run one focused Vitest command on Node 20, 22, and
25 without duplicating the test definition or weakening the existing Required
gate?

## Context

Issue #59 requires durable cross-Node evidence for DNS lookup, pinned HTTPS,
audio-candidate aggregation, and the public MCP Fake-IP error structure.

## Sources

| Source | Type | Date checked | Notes |
|--------|------|--------------|-------|
| [GitHub workflow syntax — strategy matrix](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idstrategymatrix) | official docs | 2026-08-23 | Matrix values are exposed through the `matrix` context and create one job per value. |
| [actions/setup-node usage](https://github.com/actions/setup-node/blob/main/README.md) | official source | 2026-08-23 | `node-version` accepts a matrix value; the repository already pins setup-node v7 to an immutable SHA. |

## Findings

- One `strategy.matrix.node-version` list creates independent Node 20, 22, and
  25 jobs while keeping one focused command.
- `fail-fast: false` preserves evidence from the other Node versions if one
  version fails.
- The existing immutable checkout and setup-node pins can be reused; no new
  action or dependency is required.
- The aggregate `Required` job must depend on the matrix job so a failed or
  cancelled Node version cannot be hidden by the main product job.

## Applicability To This Project

Applies:

- Add one `test:fake-ip` package script as the single focused command.
- Add one three-version job to `.github/workflows/verify.yml`.
- Include that job result in `Required`.

Does not apply:

- This matrix does not run live Bilibili, Cookie, ASR model, or FlClash tests in
  GitHub-hosted runners.

## Decision Impact

Use the existing workflow actions and npm cache, and run the deterministic
Fake-IP contract suite on Node 20, 22, and 25. Keep real FlClash evidence in a
separate redacted QA record.

## Risks And Unknowns

- Major-only Node selectors intentionally follow the newest available patch in
  each tested major; exact local patch versions are recorded in QA evidence.
- Hosted matrix evidence is available only after the branch is pushed and a PR
  or master workflow run starts.

## Staleness Notes

Refresh this note when the supported Node floor, Verify workflow, or setup-node
pin changes.

## Follow-Up

- [ ] Confirm the hosted Node matrix before release.
