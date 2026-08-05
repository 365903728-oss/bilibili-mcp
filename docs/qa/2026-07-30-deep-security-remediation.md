# Deep Security Remediation QA

## QA Session

- Date: 2026-07-30
- Version: uncommitted post-v1.10.1 working tree at base
  `ab4dd02854f0483fc7668c713523b4be77de6cc7`
- Owner: Codex
- Original scan: `6949ea8e-a129-43d6-9104-6edf7413a1ff`
- Related ticket:
  `docs/agent-memory/handoffs/2026-07-30-deep-security-remediation-task-ticket.md`
- QA type: security regression

## Scope

In scope:

- all 38 validated findings from the original Codex Security scan;
- the ten-tool MCP stdio boundary, Bilibili HTTP/WBI/bootstrap calls, output,
  cache and log budgets, ASR download/runtime/installer containment, hook
  trust and retention, and npm publish Action integrity;
- deterministic local tests, build, package inspection, production audit,
  secret classification, and an independent official Codex Security deep
  re-scan.

Out of scope:

- dependency, package version, MCP protocol, or public tool-count changes;
- real Cookie-backed Bilibili calls;
- ASR model installation, switching, or live transcription;
- commit, push, pull request, tag, release, or publication.

## Automated Baseline

- `npm run build`: pass.
- Focused security regression: 22 files / 407 tests pass.
- Full `npm test`: 38 files / 721 tests pass.
- Hook compile and safety suites: 6/6 hook-safety and 8/8 stop-summary tests
  pass.
- `npm pack --dry-run --json --ignore-scripts`: 180 files, 190,267 bytes
  packed, 776,730 bytes unpacked; structural forbidden paths and
  high-confidence package-content secret matches are zero.
- Built CLI help and the public JSON-RPC stdio initialization, tool discovery,
  representative call, and stdout-cleanliness smoke pass.
- `npm audit --omit=dev --json`: two moderate nodes remain for the installed
  Hono static-file advisory; the vulnerable SDK module is not imported by this
  stdio-only server. This is a documented residual, not a clean audit.

## Finding Closure Matrix

Every row below has an implemented control and deterministic evidence. The
“Original finding” column records the original `extensions.reportId` finding
slug, not the canonical `csf_*` finding ID. “Local status” means the original
source-to-sink path is closed in this working tree; the independent post-fix
scan is recorded separately when it completes.

| # | Original finding | Severity | Closing control | Primary regression evidence | Local status |
|---:|------------------|----------|-----------------|-----------------------------|--------------|
| 1 | `d0002-s2-http-admission-queue` | Medium | `src/bilibili/http.ts` caps active-plus-queued operations, admission queue length, wait time, and one shared deadline. | `tests/bilibili-http.test.ts` | Remediated |
| 2 | `fingerprint-cache-stampede` | Medium | `src/bilibili/fingerprint.ts` uses one process-owned refresh, at most 64 waiters, caller-independent cancellation, bounded parsing, and shared admission. | `tests/bootstrap-single-flight.test.ts`, `tests/bilibili-fingerprint.test.ts` | Remediated |
| 3 | `mcp-stdio-unbounded-frame` | Medium | `src/server/bounded-stdio-transport.ts` enforces 1 MiB inbound and 4 MiB outbound byte ceilings with fixed buffering and fail-closed framing. | `tests/bounded-stdio-transport.test.ts`, `tests/mcp-server-smoke.test.ts` | Remediated |
| 4 | `transcript-search-output-amplification` | Medium | `src/bilibili/subtitle.ts` computes exact serialized UTF-8 size and caps transcript-search results at 512 KiB after overlap processing. | `tests/bilibili-transcript.test.ts`, `tests/bounded-response.test.ts` | Remediated |
| 5 | `asr-audio-timeout-budget-reset` | Low | All candidates share one 120-second deadline and one aggregate 128 MiB download budget. | `tests/asr-transcription.test.ts` | Remediated |
| 6 | `asr-decoded-media-resource-exhaustion` | Low | Managed Python applies Windows Job or POSIX `RLIMIT` memory/CPU/process limits, thread caps, process grouping, and tree kill. | `tests/asr-transcription.test.ts` | Remediated |
| 7 | `asr-duration-metadata-fail-open` | Low | ASR rejects absent, invalid, non-positive, or over-limit selected-Part duration before state, network, temp, or child work. | `tests/asr-transcription.test.ts`, `tests/bilibili-playback.test.ts` | Remediated |
| 8 | `asr-malformed-subtitle-fallback` | Low | Malformed subtitle list/body data is a typed failure; only verified absence or verified empty content is eligible for ASR. | `tests/subtitle-fallback-security.test.ts` | Remediated |
| 9 | `mcp-asr-cancellation-ignored` | Low | SDK request cancellation is propagated through `AsyncLocalStorage`; downloads abort and the managed runtime tree is killed before cleanup and slot release. | `tests/server-handler-sanitization.test.ts`, `tests/bilibili-transcript.test.ts`, `tests/asr-transcription.test.ts` | Remediated |
| 10 | `d0002-s3-001` | Low | `.codex/agents/stabilization-reviewer.toml` explicitly treats issues, handoffs, reports, and quoted content as bounded untrusted data. | Static policy review and `.codex/scripts/test_hook_safety.py` | Remediated |
| 11 | `harness-hook-unbounded-input-state` | Low | `hook_safety.py` caps stdin, JSON depth/nodes, JSONL rows/bytes, uses tail reads, locks, atomic replacement, and refuses symlinks. | `.codex/scripts/test_hook_safety.py` | Remediated |
| 12 | `harness-learning-prompt-injection` | Low | Hooks persist fixed metadata only; SessionStart no longer previews candidate text or stored observations into model context. | `.codex/scripts/test_hook_safety.py`, `.codex/scripts/test_stop_summary.py` | Remediated |
| 13 | `hook-env-secret-redaction-bypass` | Low | Post-tool capture no longer persists raw command, stdout, stderr, exception, environment, or path text; proposal generation validates fixed enums and IDs. | `.codex/scripts/test_hook_safety.py` | Remediated |
| 14 | `asr-installer-unbounded-resources` | Low | Installer stages into a managed directory, enforces subprocess deadlines, 64 KiB output, free-space/model-byte/file-count budgets, no symlinks, atomic activation, and cleanup on failure. | `tests/asr-installer.test.ts`, `tests/asr-installer-process.test.ts` | Remediated |
| 15 | `d0002-s1-installer-env-forwarding` | Low | Installer children receive an allowlisted environment plus fixed noninteractive pip, isolated user-site, UTF-8, no-bytecode, and disabled Hugging Face telemetry settings; proxy, cloud, npm, Hugging Face, and Bilibili secrets are omitted. | `tests/asr-installer.test.ts` | Remediated |
| 16 | `d0002-s3-008` | Low | Unknown tool names are length-bounded, checked against the fixed tool set, logged as a fixed event, and returned as a fixed public error. | `tests/server-handler-sanitization.test.ts`, `tests/logger-redaction.test.ts` | Remediated |
| 17 | `cache-unbounded-value-retention` | Low | `src/utils/cache.ts` enforces per-entry and aggregate serialized-byte budgets with weighted eviction for Video and comment caches. | `tests/cache.test.ts` | Remediated |
| 18 | `update-check-unbounded-request` | Low | Update checks use a five-second total deadline, 64 KiB bounded JSON, one shared refresh, 64 waiters, cancellation isolation, and a five-minute cache. | `tests/update-check.test.ts`, `tests/bootstrap-single-flight.test.ts` | Remediated |
| 19 | `release-actions-mutable-tags` | Low | Every third-party `uses:` ref in the OIDC publish workflow is pinned to a verified full commit SHA. | `tests/publish-workflow-pins.test.ts` | Remediated |
| 20 | `subtitle-failures-masked-as-success` | Low | Subtitle transport, schema, and parsing failures remain errors; description fallback is limited to a verified no-subtitle state. | `tests/subtitle-fallback-security.test.ts`, `tests/bilibili-video-api.test.ts` | Remediated |
| 21 | `bilibili-plain-redirect-ssrf` | Low | Shared Bilibili JSON fetches use manual redirect mode and reject every redirect before a second destination can be contacted. | `tests/bilibili-http.test.ts` | Remediated |
| 22 | `bilibili-wbi-redirect-ssrf` | Low | Signed WBI requests reject redirects and retain one bounded operation context. | `tests/bilibili-wbi-http-security.test.ts` | Remediated |
| 23 | `d0002-s1-playback-dns-ssrf` | Low | `src/security/pinned-https.ts` resolves every media-host answer, rejects empty/mixed/private/special ranges, pins an approved address, preserves TLS hostname validation, and strips credentials. | `tests/pinned-https.test.ts` | Remediated |
| 24 | `fingerprint-redirect-ssrf` | Low | Fingerprint bootstrap uses manual redirect mode and rejects redirects away from the fixed Bilibili HTTPS request. | `tests/bilibili-fingerprint.test.ts` | Remediated |
| 25 | `update-check-redirect-ssrf` | Low | Registry update checks reject redirects instead of following attacker-selected destinations. | `tests/update-check.test.ts` | Remediated |
| 26 | `wbi-nav-redirect-ssrf` | Low | WBI nav bootstrap uses manual redirect mode and rejects redirects from the fixed first-party HTTPS request. | `tests/bilibili-wbi.test.ts` | Remediated |
| 27 | `api-error-secret-reflection` | Low | MCP errors expose fixed public messages and bounded recovery fields; raw upstream/native exception text cannot cross the response boundary. | `tests/server-error-next-steps.test.ts`, `tests/server-credential-tools.test.ts` | Remediated |
| 28 | `logger-unbounded-upstream-strings` | Low | Structured stderr logging bounds keys, strings, collection depth/items, and whole JSON records before serialization while redacting secrets, paths, and query values. | `tests/logger-redaction.test.ts` | Remediated |
| 29 | `bilibili-plain-unbounded-json` | Low | Plain first-party JSON responses are streamed into a bounded parser with a 4 MiB decoded ceiling. | `tests/bounded-response.test.ts`, `tests/bilibili-http.test.ts` | Remediated |
| 30 | `bilibili-wbi-unbounded-json` | Low | Signed WBI response JSON is bounded to the shared 4 MiB ceiling before parsing. | `tests/bilibili-wbi-http-security.test.ts`, `tests/bounded-response.test.ts` | Remediated |
| 31 | `comments-overreturned-response` | Low | Main comments, three replies per comment, author/message bytes, and the exact 1 MiB serialized result are enforced locally before caching/return. | `tests/bilibili-comments-tool.test.ts` | Remediated |
| 32 | `d0002-s1-playback-unbounded-json` | Low | Playback JSON is capped at 1 MiB and normalization limits representations to 256, backups to eight, and candidates to three with strict fields. | `tests/bilibili-playback.test.ts` | Remediated |
| 33 | `favorites-folder-list-unbounded` | Low | Folder lists are capped at 100 and folder/title/author fields have explicit UTF-8 byte limits before normalization. | `tests/bilibili-favorites.test.ts` | Remediated |
| 34 | `favorites-page-overreturned-response` | Low | Any Favorites media page above the fixed 20-row contract is rejected before normalization or response construction. | `tests/bilibili-favorites.test.ts` | Remediated |
| 35 | `fingerprint-unbounded-json` | Low | Fingerprint bootstrap parses at most 64 KiB and accepts only bounded, valid fingerprint fields before caching. | `tests/bilibili-fingerprint.test.ts`, `tests/bounded-response.test.ts` | Remediated |
| 36 | `mcp-unbounded-success-serialization` | Low | Shared response construction caps structured payloads at 2 MiB and complete text-plus-structured envelopes at 4 MiB while preserving semantic equality. | `tests/mcp-response-budget.test.ts`, `tests/server-handler-sanitization.test.ts` | Remediated |
| 37 | `nested-wbi-retry-amplification` | Low | WBI bootstrap is process-owned single-flight, outside the outer request slot, has one attempt and bounded waiters; each caller's wait is deadline-bounded without cancelling or multiplying the shared refresh. | `tests/bootstrap-single-flight.test.ts`, `tests/bilibili-http.test.ts` | Remediated |
| 38 | `wbi-bootstrap-unbounded-body` | Low | WBI nav bootstrap keeps its deadline through body consumption and parses no more than 256 KiB. | `tests/bilibili-wbi.test.ts`, `tests/bounded-response.test.ts` | Remediated |

## Security And Privacy Checks

- High-confidence private-key, GitHub-token, npm-token, and AWS-key patterns:
  zero matches in the current tree and package surface.
- Bilibili credential-shaped assignments were reviewed without printing
  values. Matches are synthetic tests, scanner patterns, or explicitly
  redacted historical plan examples; suspicious unclassified matches are
  zero.
- Root `.env`, `.npmrc`, `.yarnrc`, and `npm-debug.log`: absent.
- Package contents exclude source, tests, QA, research, agent memory, hooks,
  local state, model data, audio, credential files, and private keys.
- Full Cookies, signing query strings, token values, local private paths, and
  raw child/upstream diagnostics are absent from this record.

## Residual And Untested Boundaries

- A ready ASR model is not installed. Real audio download, native decoder
  behavior, and end-to-end transcription are not tested; deterministic injected
  tests and static data-flow evidence cover the implemented boundary.
- Managed-Python tests verify the embedded Windows Job/POSIX `RLIMIT` setup,
  platform process-group option, abort/tree-kill behavior, and bounded protocol,
  but do not prove kernel enforcement against a real decoder on this
  model-free machine.
- Installer staging and polling enforce application-level storage limits, but
  they are not an operating-system disk quota and may overshoot by one polling
  interval before the child tree is stopped.
- Production audit remains nonzero because
  `@modelcontextprotocol/sdk@1.27.1` installs
  `@hono/node-server@1.19.14`. The static-file sink is unreachable from current
  imports, but a future HTTP transport must re-open this review.
- No live Bilibili or registry redirect target was contacted for exploit
  validation. Redirect/DNS/body-limit tests use local synthetic responses and
  resolvers.

## Post-Fix Codex Security Re-scan

- Official CLI repository target:
  `C:\Users\ZX\.codex\worktrees\0a1b\bilibili-mcp`
- Mode: `deep`
- Authentication: existing stored Codex credentials; no credential value is
  recorded.
- First retry: scan `c93dd212-6e9c-4ed0-a0c6-36bc93f9769b` used CLI 0.1.3
  and failed before artifact collection with
  `scan-manifest.json: expected a regular file inside the scan directory`;
  its output directory is empty and it is not accepted as a completed scan.
- Root cause: CLI 0.1.3 invoked workbench completion before collecting the
  canonical files. Official CLI 0.1.4 prepares completion, validates/collects
  the files, and only then completes the scan.
- Status: a fresh official CLI 0.1.4 deep scan remains required; its final scan
  ID, findings, canonical artifacts, and generated report will replace this
  pending status.

## Result

- Current result: `pass pending fresh independent scan`
- Blocking local regression: none.
- Non-blocking caveats: installed-but-unreachable Hono advisory and absent
  ready ASR model.
- Git/release state: no stage, commit, push, PR, tag, version, publish, or
  release action performed.
- Codemap: checked and updated for the new security modules, tests, and bounded
  hook helper.
- Research:
  `docs/research/2026-07-30-security-remediation-dependency-and-action-pins.md`
