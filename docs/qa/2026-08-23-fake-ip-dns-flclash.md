# Issue #59 Fake-IP DNS and FlClash acceptance

## QA Session

- Title: Cross-Node Fake-IP contracts and real FlClash recovery
- Date: 2026-08-23
- Version or commit: `1.13.0`; base `03ccb8bf2e1172a7591b893d79f2af699c2532c3`
- Owner: Codex with user-controlled FlClash state changes
- Related ticket: GitHub Issue #59; parent #56; dependencies #57 and #58
- QA type: regression / MCP tool change

## Scope

In scope:

- Node 20, 22, and 25 focused Fake-IP contract tests.
- Real Windows FlClash Rule + TUN + Fake-IP behavior before and after the two
  Bilibili media-domain filters.
- A public `force_asr` MCP path using the already-ready CPU model.

Out of scope:

- GPU readiness, model installation, proxy-node selection, public DNS bypass,
  release, and publication.

## Preconditions

- [x] Work is isolated on `codex/issue-59-fake-ip-qa` from the recorded base.
- [x] Package version is `1.13.0`.
- [x] Credentials are loadable from the approved global configuration; no value
  was printed or copied into this record.
- [x] The test BVID is public and already used by repository fixtures.
- [x] Local MCP stdio, Windows, FlClash Rule mode, TUN, and Fake-IP DNS are active.
- [x] `doctor --json` reports the existing `small` model ready on CPU.

## Automated Evidence

| Runtime | Focused files | Result |
|---------|---------------|--------|
| Node 20.20.2 | pinned HTTPS, ASR candidate aggregation, MCP error structure | 92/92 pass |
| Node 22.23.2 | pinned HTTPS, ASR candidate aggregation, MCP error structure | 92/92 pass |
| Node 25.9.0 | pinned HTTPS, ASR candidate aggregation, MCP error structure | 92/92 pass |

- [x] The new matrix configuration regression failed 2/2 before the package
  script and workflow job existed, then passed 2/2.
- [x] `npm run test:fake-ip` passes 92/92 on the local default Node runtime.
- [x] Final `npm run build` and complete `npm test`: 44 files / 1,076 tests
  pass.
- [x] Exact real-pilot conformance passed 1/1; Harness contracts, events,
  adapters, and memory passed 102 tests with 15 skipped.
- [ ] Hosted Node matrix; requires a later authorized push/PR.

## Real FlClash Evidence

Environment:

- Windows with FlClash Rule mode, TUN enabled, DNS enhanced mode `fake-ip`.
- No proxy node, private profile content, Cookie, signed media URL, or complete
  DNS answer is recorded.

Without the two media-domain filters:

- [x] Active profile temporarily omits `+.bilivideo.com` and
  `+.bilivideo.cn` while Rule mode and TUN remain enabled.
- [x] The same `force_asr` request returns `ASR_FAKE_IP_DNS` in 2,223 ms,
  before model work, with category `network`, `retryable: false`, and
  `user_action_required: true`.

With the two media-domain filters:

- [x] The active generated configuration contains exactly
  `+.bilivideo.com` and `+.bilivideo.cn` from the user-approved override script.
- [x] The sampled Bilibili media hostname resolves outside the standard
  Fake-IP range; individual DNS answers are intentionally omitted.
- [x] The same public `force_asr` request completes with `data_source: asr`
  and a non-empty 1,744-character transcript; transcript text is omitted.
- [x] Rule mode and TUN remained enabled.
- [x] The original override script was restored, the configuration was
  reloaded, both filters returned, and DNS again resolved outside the standard
  Fake-IP range.

One harness-only first attempt used the MCP SDK's default 60-second client
timeout and was cancelled cleanly. Repeating with the product's 30-minute
ceiling completed successfully; no product timeout was changed.

## Security And Privacy

- [x] No Cookie, credential value, proxy node, private profile, signed media
  URL, complete DNS answer, or transcript text is retained.
- [x] The live result records only status, source, and bounded aggregate size.
- [x] Existing pinned HTTPS, Host/SNI, redirect, and candidate fallback behavior
  is unchanged.

## Result

- Overall result: `pass`
- Blocking issue: none.
- Non-blocking caveat: hosted Node matrix evidence requires later push/PR
  authority.
- Follow-up ticket: none.
- Codemap update status: complete.
- Research note: `docs/research/2026-08-23-fake-ip-node-matrix.md`
