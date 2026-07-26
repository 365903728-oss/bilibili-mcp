# QA: Transcript Evidence Links

## QA Session

- Title: `get_video_transcript` citation-ready Bilibili links
- Date: 2026-07-26
- Version or commit: package `1.7.2`, base commit `d4b06e5d8f8c9dfd7b217286bd2705a95164bfe2`, uncommitted Issue #17 worktree
- Owner: Codex
- Related ticket and PRD: GitHub Issue #17 and `docs/transcript-evidence-links-prd.md`
- QA type: `MCP tool change`

## Scope

In scope:

- Required `source_url` on every successful `get_video_transcript` result.
- Required `timestamp_url` on every returned transcript search match.
- Ordinary and multi-Part URL semantics, exact BVID casing, structured/text equality, package contents, and live browser behavior.

Out of scope:

- Other MCP tools, Bilibili search, danmaku, cursors, ASR, mobile deep links, release, commit, push, and publication.

## Preconditions

- [x] Branch `master` and base commit recorded.
- [x] Package version `1.7.2` recorded.
- [x] Credentials were read only through the approved global credential source.
- [x] No Cookie value was printed or stored in this file.
- [x] Public test BVIDs are safe to share.
- [x] Official MCP SDK 1.27.1 and Playwright browser environments were identified.

## Automated Baseline

- Focused Vitest: pass, 3 files / 87 tests.
- Build: pass.
- Full Vitest: pass, 23 files / 299 tests.
- Package dry run: pass, 124 entries; `dist/index.js` present; `src/`, `.env`, and internal Issue #17 docs absent.
- `git diff --check`: pass; Windows line-ending warnings only.
- Independent reviews: two read-only Codex reviewers reported no actionable findings.

## MCP Stdio And Tool Discovery

- [x] Official `Client` + `StdioClientTransport` connected to local `dist/index.js`.
- [x] `tools/list` returned the existing eight tools in unchanged order.
- [x] `get_video_transcript.outputSchema` requires root `source_url`.
- [x] Each `matches[]` schema requires `timestamp_url`.
- [x] No `$schema`, URI format constraint, `oneOf`, new input, or new tool was added.
- [x] Successful formatted JSON text exactly equaled `JSON.stringify(structuredContent, null, 2)`.
- [x] Existing full-suite validation and error regressions remained green and errors stayed text-only.

## Credential And Live Tool Checks

- Credential status: `configured: true`, `source: global_config`, `logged_in: true`.
- Ordinary Video `BV1vL411G7N7`: subtitle call passed and returned
  `https://www.bilibili.com/video/BV1vL411G7N7/`.
- Multi-Part Video `BV1Eb411u7Fw`, Part 4, query `函数`: one bounded match returned
  `source_url` `https://www.bilibili.com/video/BV1Eb411u7Fw/?p=4` and
  `timestamp_url` `https://www.bilibili.com/video/BV1Eb411u7Fw/?p=4&t=1.12`.

## Browser Link Checks

- [x] Ordinary mixed-case BVID link remained unchanged and selected the expected Video.
- [x] Ordinary `t=42.5` loaded the player at exactly 42.5 seconds when inspected.
- [x] Multi-Part `p=4&t=1.12` selected Part 4 with title `1.1 函数`.
- [x] The multi-Part player was observed after the requested time while playback advanced.

## Client Compatibility

| Client | Version | Method | Result | Notes |
|---|---|---|---|---|
| Official TypeScript SDK | 1.27.1 | Local stdio | pass | Discovery and two credentialed calls passed with exact text/structured equality. |
| Playwright | current installed connector | Live Bilibili browser pages | pass | Ordinary and multi-Part navigation passed. |
| Claude Desktop | not recorded | not tested | not tested | Non-blocking and outside this ticket. |
| Cursor | not recorded | not tested | not tested | Non-blocking and outside this ticket. |
| Codex CLI | not recorded | not tested | not tested | SDK stdio acceptance is the ticket's client gate. |

## Documentation And Security

- [x] README and README_EN describe both fields concisely.
- [x] Package metadata, lockfile, version, changelog, and release workflow are unchanged.
- [x] Generated links contain only the fixed Bilibili HTTPS origin, validated BVID, resolved Part, and subtitle start time.
- [x] No caller tracking parameters, Cookie values, `.env` content, npm tokens, GitHub tokens, or private credentials were added.
- [x] Playwright's temporary snapshot and console files were removed after QA.

## Result

- Overall result: `pass`
- Blocking issues: none
- Non-blocking caveats: Bilibili browser query behavior is external and should be refreshed under the research note's staleness conditions.
- Tracker state: Issue #17 remains open with `ready-for-human`, pending explicit Git authorization.
- Codemap update status: checked; no module ownership or navigation change, so no update required.
- Research note: `docs/research/2026-07-26-bilibili-timestamp-link-contract.md`
