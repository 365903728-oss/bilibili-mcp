# Claude Report: Strix + DeepSeek Security Remediation (SEC-2026-08-05-STRIX)

- Date: 2026-08-05
- Worktree: `C:\Users\ZX\.codex\worktrees\0a1b\bilibili-mcp` (HEAD `ab4dd02`)
- Handoff: `docs/agent-memory/handoffs/2026-08-05-strix-deepseek-security-remediation-codex-to-claude.md`
- QA record: `docs/qa/2026-08-05-strix-deepseek-security-remediation.md`

## Summary

Implemented all six validated Strix verdicts (V-01, V-02, V-03, V-04, V-05,
dependency) from ticket SEC-2026-08-05-STRIX in the exact inherited worktree,
then executed three same-scope repair rounds per the user's direct directives:
round 1 (pre-read root/state symlink checks in `readAsrState`,
`crypto.randomUUID` temp naming in `writeAsrState`, plus deterministic tests),
round 2 (root guards in `runAsrInstallation`/`writeAsrState` before any
mutation, and a path-type-aware ready gate) from an independent review, and
round 3 (final minimal repair: ENOTDIR fails closed in `runAsrInstallation`,
and `writeAsrState` chmod fails closed except for explicitly unsupported
platform cases), and a final dependency/spec closure round (round 4): with
the npm registry reachable again, the remaining `fast-uri@3.1.4` production
advisory was closed by a normal compatible lockfile refresh to
`fast-uri@3.1.5` (the latest 3.x inside ajv's `^3.0.1` range; no override),
`npm audit --omit=dev --json` now reports zero vulnerabilities, and the BVID
tool x input validation matrix was expanded to 15 deterministic cases. The
pre-existing dirty baseline (~127 modified/untracked entries) was preserved
untouched; no Git mutations, no `dist/` edits, no release operations, no live
Bilibili/Cookie usage, and no model/Python downloads were performed.

## Files Changed

Implementation:

- `src/utils/bounded-text.ts` — `isUnsafeCodePoint` extended (C1 controls
  0x80–0x9F, zero-width 0x200B–0x200F, bidi 0x202A–0x202E, isolates
  0x2066–0x2069, BOM 0xFEFF, unpaired surrogates; tab/newline/CJK/emoji
  preserved); exported `sanitizeRemoteText` (removal-only, no truncation).
- `src/bilibili/video-api.ts` — `parseSubtitleContent` sanitizes every subtitle
  line via `sanitizeRemoteText`; `getSubtitleContent` rejects custom-port and
  userinfo subtitle URLs before fetch ("Unsupported subtitle URL port or
  userinfo") after the existing exact-host allowlist check.
- `src/asr/transcription.ts` — `parseAsrNdjson` sanitizes each ASR segment text.
- `src/asr/state.ts` — `readAsrState` gained an injectable 4th `lstatSync`
  parameter (default `fs.lstatSync`) with a fail-closed `isRealPath` helper
  (rejects symlinks AND type mismatches: root/venv/bin/model must be real
  directories; state/python exe/model artifacts must be real files).
  lstat/fail-closed checks run on the ASR root and `stateFile` *before* any
  read (symlinked root/state → `incomplete`, never read), plus the 9 managed
  paths (state file, venv dir, bin dir, venv python exe, model dir,
  model.bin, config.json, tokenizer.json, vocabulary.txt); `writeAsrState`
  writes through a `.state-<randomUUID()>.tmp` temp file (`wx`, mode 0600,
  stdlib `crypto.randomUUID`, injectable `randomId` for tests), creates the
  root 0700, renames atomically, and now (round 2) rejects a symlinked or
  non-directory root *before* any write/rename/mkdir and enforces
  owner-only 0700 on an existing real root via `chmodSync` (injectable
  `lstatSync`/`chmodSync` parameters; absent root → ENOENT → skip chmod,
  create owner-only). Round 3: chmod failures fail closed (EPERM/EACCES/...
  rethrown before mkdir/write/rename); only explicitly unsupported cases are
  skipped — ENOSYS/EOPNOTSUPP, and EINVAL on Windows (mode bits a filesystem
  does not support).
- `src/asr/installer.ts` — `createVenv`/`assertInstallFreeSpace` create
  directories 0700; `runAsrInstallation` (round 2) gained an injectable
  `fsLstatSync` option and fails with `success: false` *before* any
  unlink/mkdir/spawn/download/mutation when an existing ASR root is a
  symlink or not a real directory ("Refusing ASR install: root is a symlink
  or not a directory"), fails closed on uninspectable roots, and allows an
  absent root through; still calls `writeAsrState` with the unchanged
  6-argument signature. Round 3: only ENOENT means absent — ENOTDIR (an
  invalid/non-directory path component) now also fails closed before any
  spawn or mutation.
- `src/utils/validation.ts` — `validateBVInput` throws a typed
  `ValidationError("bvid_or_url must be a string")` for non-string input.
- `src/server/error-response.ts` — `buildValidationErrorPayload` genericizes
  unexpected (non-`ValidationError`) exceptions to
  `new ValidationError("Invalid input")` so engine wording never leaks.
- `src/server/tool-handlers.ts` — inline validation throws converted to typed
  `ValidationError`.
- `src/server/tool-schemas.ts` — untrusted-data warnings appended to the 7
  Bilibili text tools (`get_video_info`, `get_video_comments`,
  `get_video_transcript`, `get_video_metadata`, `get_video_chapters`,
  `search_bilibili_videos`, `list_bilibili_favorite_videos`); schemas/shapes
  otherwise unchanged.
- `package.json`, `package-lock.json` — `@modelcontextprotocol/sdk` raised to
  `^1.30.0`; compatible lockfile refresh only (no overrides, no forced
  upgrades). Round 4: `fast-uri` refreshed 3.1.4 → 3.1.5 via `npm update
  fast-uri` (normal, within ajv@8.20.0's `^3.0.1` range; the lock diff is
  fast-uri-only; `package.json` unchanged by this step), closing the last
  production advisory — `npm audit --omit=dev --json` reports 0
  vulnerabilities.

Tests:

- `tests/bounded-text.test.ts` (new) — C1/bidi/zero-width/BOM/surrogate
  removal, whitespace/CJK/emoji preservation, no-truncation sanitize, byte
  budget after removal.
- `tests/validation.test.ts` — non-string `bvid_or_url` (number/boolean/
  object/null/array) throws typed `ValidationError`.
- `tests/bilibili-video-api.test.ts` — subtitle-line sanitization (strips
  unsafe code points, preserves CJK/emoji/tab/newline), long-line
  no-truncation, `it.each` custom-port/userinfo rejection with
  `fetchMock` not called.
- `tests/server-handler-sanitization.test.ts` — BVID tool x input matrix
  (round 4): all 5 BVID tools × {number, boolean, object} `bvid_or_url`
  (15 cases) return typed `VALIDATION_ERROR` ("bvid_or_url must be a
  string") with stable wording (no engine text, `includes` never reflected)
  and the corresponding business mock asserted never called (mocks for
  `getVideoInfoWithSubtitle` and `getVideoCommentsData` were named to
  support this); `buildValidationErrorPayload` genericization unit tests
  (typed error keeps message; generic `Error` becomes "Invalid input").
- `tests/asr-transcription.test.ts` — ASR NDJSON segment sanitization.
- `tests/asr-installer.test.ts` — `lstatSync` mock injection into the 4
  mock-based ready tests; unique-temp-name assertions on the two tmp-cleanup
  tests; describes: symlink rejection over all 9 managed paths, fail-closed
  on uninspectable path, secure temp write (unique `wx`/0600, 0700 root,
  atomic rename, no residue), real-fs model.bin symlink rejection (guarded for
  platforms without symlink privileges); repair round 1 added: injected
  random-source temp names (name from source, fresh per write), root-symlink
  and state-symlink rejection with `readFileSync` asserted never called, and
  real-fs root-symlink rejection; temp-name regexes now match the UUID
  pattern. Repair round 2 added (+18 tests): path-type verification
  (directory in a file slot and file in a directory slot never returns
  `ready` across all 9 managed paths; state-as-directory and root-as-file
  never read), `writeAsrState` root guard no-side-effect tests (symlinked and
  non-directory root throw before write/rename/unlink/mkdir/chmod; existing
  real root chmod'ed 0700; absent root skipped chmod and created
  `{recursive: true, mode: 0o700}`), and `runAsrInstallation` root-guard
  tests (symlinked and non-directory root → `success: false` with
  spawnFn/fsMkdirSync/fsUnlinkSync never called; absent root passes the guard
  and reaches spawn). Round 3 added (+5 tests): `writeAsrState` chmod
  fail-closed (`EPERM`/`EACCES` rethrow before write/rename/unlink/mkdir)
  and skip-only-when-unsupported (`ENOSYS`/`EOPNOTSUPP` continue), plus an
  ENOTDIR no-side-effect regression test for `runAsrInstallation` (invalid
  path component → `success: false`, "Cannot inspect ASR root",
  spawnFn/fsMkdirSync/fsUnlinkSync never called).
- `tests/server-tools.test.ts` — untrusted-data warning asserted on the 7
  affected tool descriptions.

Docs:

- `docs/qa/2026-08-05-strix-deepseek-security-remediation.md` — this task's QA
  checklist.
- `docs/research/2026-08-05-strix-deepseek-security-remediation-dependencies.md`
  — dependency advisory classification (created earlier in the session).

## Commands Run And Results

| Command | Result |
|---|---|
| `npx vitest run <7 touched test files>` | 7 files / 347 tests passed (round 1) |
| `npm run build` | pass (tsc exit 0) |
| `npm test` | 39 files / 765 tests passed (round 1) |
| `npx vitest run tests/asr-installer.test.ts tests/asr-transcription.test.ts` | 2 files / 152 tests passed (repair round 1) |
| `npm run build` | pass (tsc exit 0, repair round 1) |
| `npm test` | 39 files / 770 tests passed (repair round 1, +5 new tests) |
| `npx vitest run tests/asr-installer.test.ts tests/asr-transcription.test.ts` | 2 files / 170 tests passed (repair round 2, +18 new tests) |
| `npm run build` | pass (tsc exit 0, repair round 2) |
| `npm test` | 39 files / 788 tests passed (repair round 2) |
| `npx vitest run tests/asr-installer.test.ts tests/asr-transcription.test.ts` | 2 files / 175 tests passed (repair round 3, +5 new tests) |
| `npm run build` | pass (tsc exit 0, repair round 3) |
| `npm test` | 39 files / 793 tests passed (repair round 3) |
| `npx vitest run tests/validation.test.ts tests/server-handler-sanitization.test.ts` | 2 files / 150 tests passed (round 4, +10 matrix cases) |
| `npm run build` | pass (tsc exit 0, round 4) |
| `npm test` | 39 files / 803 tests passed (round 4) |
| `npm audit --omit=dev --json` | **0 vulnerabilities** (total 0; 97 prod / 665 total deps) — registry reachable again |
| `npm pack --dry-run --json --ignore-scripts` | 180 files, 788,704 bytes; dist + docs + assets + LICENSE only |
| `npm pack --dry-run --json --ignore-scripts` | 180 files, 783,133 bytes; dist + docs + assets + LICENSE only |
| `git diff --check` | exit 0 (only pre-existing CRLF warnings) |
| `npm ls --omit=dev --depth=1` / `npm ls fast-uri ip-address` | SDK 1.30.0, hono 4.13.0, @hono/node-server 2.1.0, express-rate-limit 8.6.2, ip-address 10.4.0, fast-uri 3.1.4 |
| `npm audit --omit=dev --json` | **skipped** — registry unreachable (connect ETIMEDOUT twice, 2026-08-05) |
| ASR residue check | no `.state-*.tmp` or other temp files under `~/.bilibili-mcp/asr/` or the repo |
| Value-free secret classification | full diff scan for `SESSDATA=`/`bili_jct=`/`DedeUserID=`/`Cookie:` found only redaction/placeholder/test patterns; no real values |

## Diff Notes

- The working tree diff against HEAD includes the entire pre-existing user
  baseline (74 files / ~5,315 insertions before my changes were measured
  against it); this report's file list above isolates the Strix-scope edits.
- `git diff --check` reports only repo-wide LF→CRLF conversion warnings, which
  predate this task and are expected on Windows.

## Skills And Capabilities Used

- `vitest` skill — applied for the deterministic test additions.
- `secret-scanning` skill — applied for the value-free secret classification
  before reporting (no commit/publish in this task).
- One bounded `risk-reviewer` subagent — launched after the first
  implementation round per the handoff's one-subagent cap; cancelled by the
  user before completion (see Risk-Reviewer Result). Not relaunched.
- `codex-security` — **not installed for Claude Code**; reported per handoff,
  with `risk-reviewer` as the closest local fallback.
- Round 2 was driven by an independent review issued directly by the user
  (P1 root guards + P2 path-type ready gate); no new subagent was launched
  (the one-subagent cap and the user's cancellation stand).

## Risk-Reviewer Result

The `risk-reviewer` subagent (a697cadd27d5bd994) was launched after the first
implementation round, then **stopped by the user before producing a result**;
its run is cancelled and will not be resumed, and no new agent was launched.
Its verdict is therefore unavailable. Instead, the user issued this
same-scope repair round directly with three concrete findings, which were
implemented (see "Same-Scope Repair Round" below) and are covered by new
deterministic tests.

## Same-Scope Repair Rounds (2026-08-05)

### Round 1

Per the user's direct repair directive, three concrete ASR issues were fixed:

1. **`readAsrState` rejects symlinked root/state before any read** —
   `src/asr/state.ts` now lstat/fail-closes on the ASR root directory (when
   it exists) and on `stateFile` *before* `readFileSync`: a symlinked root or
   state file is never followed or read and never produces `ready`
   (returns `incomplete`). The `not_installed` semantics for a fully absent
   root are preserved. The existing venv/bin/executable/model-dir/model-file
   checks are retained unchanged.
2. **`writeAsrState` temp names are cryptographically unpredictable** —
   PID+counter naming removed; temp names now come from Node's stdlib
   `crypto.randomUUID()` (no new dependency) via an injectable 7th
   `randomId` parameter, still `wx`/0600 with atomic rename.
3. **Deterministic tests added** — injected random-source tests (temp name
   taken from the source; fresh name per write), mock-based root-symlink and
   state-symlink rejection with `readFileSync` asserted never called, and a
   real-fs root-symlink rejection test (complete tree behind a symlinked
   root returns `incomplete`, proving the pre-read guard fires).

Round-1 files: `src/asr/state.ts`, `tests/asr-installer.test.ts`
(+5 tests, temp-name regexes updated to the UUID pattern).

### Round 2 (independent review)

Per the user's second direct repair directive from an independent review, two
concrete issues were fixed:

1. **P1 — root guards before any mutation** —
   `runAsrInstallation` (`src/asr/installer.ts`, injectable `fsLstatSync`
   option) now fails with `success: false` *before* any
   unlink/mkdir/spawn/download/mutation when an existing ASR root is a
   symlink or not a real directory ("Refusing ASR install: root is a symlink
   or not a directory"), fails closed on uninspectable roots ("Cannot inspect
   ASR root: ..."), and allows an absent root through (ENOENT/ENOTDIR).
   `writeAsrState` (`src/asr/state.ts`, injectable 8th/9th `lstatSync`/
   `chmodSync` parameters) independently rejects a symlinked or non-directory
   root before writing/renaming, never follows a symlink, enforces
   owner-only 0700 on an existing real root via best-effort `chmodSync`
   where supported, and creates an absent root owner-only (no chmod attempt).
2. **P2 — path-type-aware ready gate** — `readAsrState`'s `isNotSymlink`
   helper was replaced by `isRealPath(lstatSync, candidate, kind)` which
   verifies the expected path type, not merely non-symlink: root/venv/bin/
   model must be real directories; state/python executable/required model
   artifacts must be real files. A directory in a file slot or a file in a
   directory slot never returns `ready`. Fail-closed semantics (uninspectable
   → `incomplete`) and Windows portability (lstat detects junctions) are
   preserved; round 3 narrowed chmod best-effort to explicitly unsupported
   codes only (see round 3 below).
3. **Deterministic no-side-effect tests added (+18)** — path-type
   verification across all 9 managed slots (including state-as-directory and
   root-as-file with `readFileSync` asserted never called), `writeAsrState`
   root-guard tests (symlink/non-directory root throws with
   write/rename/unlink/mkdir/chmod never called; existing real root chmod'ed
   0700; absent root: no chmod, owner-only mkdir), and `runAsrInstallation`
   root-guard tests (symlink/non-directory root → `success: false` with
   spawnFn/fsMkdirSync/fsUnlinkSync never called; absent root passes the
   guard and reaches spawn).

Round-2 files: `src/asr/installer.ts`, `src/asr/state.ts`,
`tests/asr-installer.test.ts` (+18 tests).

### Round 3 (final minimal repair)

Per the user's third direct repair directive, two concrete issues were fixed:

1. **ENOTDIR fails closed in `runAsrInstallation`** — the root-guard catch
   now continues only on `ENOENT` (absent root). `ENOTDIR` (an
   invalid/non-directory path component) returns `success: false`
   ("Cannot inspect ASR root: ...") before any spawn or mutation.
2. **`writeAsrState` chmod fails closed except for unsupported platforms** —
   the chmod catch no longer swallows every failure: `EPERM`/`EACCES`/other
   permission or I/O errors rethrow before mkdir/write/rename; only
   `ENOSYS`/`EOPNOTSUPP` (and `EINVAL` on Windows, where chmod can reject
   unsupported mode bits) are skipped as explicitly unsupported.
3. **Deterministic no-side-effect regression tests (+5)** — `EPERM`/`EACCES`
   chmod fail-closed (write/rename/unlink/mkdir never called), `ENOSYS`/
   `EOPNOTSUPP` chmod skip (write/rename still proceed), and an ENOTDIR
   `runAsrInstallation` no-side-effect test (spawnFn/fsMkdirSync/
   fsUnlinkSync never called).

Round-3 files: `src/asr/installer.ts`, `src/asr/state.ts`,
`tests/asr-installer.test.ts` (+5 tests).

### Round 4 (final dependency/spec closure)

Per the user's fourth direct directive, with the npm registry reachable
again:

1. **Last production advisory closed compatibly** — `fast-uri` refreshed
   3.1.4 → 3.1.5 via a normal `npm update fast-uri` (no override). Verified
   live: `npm view fast-uri@3.1.5 version` → 3.1.5 exists and is the latest
   3.x; the `latest` dist-tag (4.1.2) is a new major outside ajv@8.20.0's
   `^3.0.1` range, so 3.1.5 is the compatible maximum. The lock diff is
   fast-uri-only; `package.json` unchanged by this step.
   `npm audit --omit=dev --json` now succeeds and reports **zero
   vulnerabilities**. The obsolete "4.1.2 / unreachable residual" claim in
   the research note, report, and QA is corrected.
2. **BVID tool x input validation matrix expanded** — all 5 BVID tools are
   each exercised with number, boolean, and object `bvid_or_url` (15
   deterministic cases) asserting stable `VALIDATION_ERROR` / "bvid_or_url
   must be a string" / no engine wording, and the corresponding business
   mock is asserted never called (the previously anonymous
   `getVideoInfoWithSubtitle` / `getVideoCommentsData` mocks were named for
   this).

Round-4 files: `package-lock.json`, `tests/server-handler-sanitization.test.ts`
(+10 matrix cases), `docs/research/2026-08-05-strix-deepseek-security-remediation-dependencies.md`.

## Harness Artifacts

- Task ticket: **used** — SEC-2026-08-05-STRIX is the execution boundary;
  handoff `2026-08-05-strix-deepseek-security-remediation-codex-to-claude.md`
  is the file-backed authority.
- Research note: **used** — `docs/research/2026-08-05-strix-deepseek-security-remediation-dependencies.md`
  records the dependency advisory classification and its Resolution:
  fast-uri closed via the compatible 3.1.5 refresh (no override), audit at
  zero vulnerabilities; ip-address already fixed.
- QA checklist: **created** — `docs/qa/2026-08-05-strix-deepseek-security-remediation.md`
  (per `docs/templates/qa-checklist.md`); QA type: MCP tool change / credential
  flow / regression.
- Codemap: **checked, left unchanged** — `docs/agent-memory/codemap.md` already
  covers every touched module (`bounded-text.ts`, `asr/state.ts`,
  `asr/installer.ts`, `error-response.ts`, `tool-schemas.ts`,
  `tool-handlers.ts`, `validation.ts`, and the touched test files); this task
  made no structural code change (no new modules, no moved boundaries, no new
  tools).
- Harness security: **reviewed** — `docs/agent-memory/harness-security.md`
  trust-boundary and no-secret rules honored; no credential material entered
  any file, test, log, or this report; the one-subagent cap was respected.
- Harness eval: **deferred** — no roadmap phase or release completed in this
  task; no harness-eval update warranted now.

## Residual Risks / Skips

- No live Bilibili/Cookie acceptance was run (handoff constraint); all
  workflow behavior is verified through the 803-test deterministic baseline.
- No ready-model/live-ASR E2E was run; the symlink-rejection real-fs tests
  are guarded and skipped on platforms without symlink creation privileges.
- `npm audit --omit=dev --json` **passes with 0 vulnerabilities** (registry
  reachable as of 2026-08-05); `fast-uri` refreshed 3.1.4 → 3.1.5 inside
  ajv@8.20.0's `^3.0.1` range with no override, and `ip-address@10.4.0` is
  already the fixed version. The earlier "4.1.2 / unreachable residual"
  classification is superseded (see research note Resolution section).
- The round-1 risk-reviewer subagent's verdict is unavailable (cancelled by
  the user); the repair rounds were instead issued directly by the user
  (rounds 2–4, round 2 from an independent review) and are fully implemented
  and tested.
- `writeAsrState` chmod skips 0700 enforcement only for explicitly
  unsupported codes (`ENOSYS`/`EOPNOTSUPP`, and `EINVAL` on Windows);
  permission/I/O failures (e.g. `EPERM`/`EACCES`) fail closed before
  mkdir/write/rename. Windows POSIX-permission semantics apply where
  supported.

## Decision Points

- None escalated. The only ambiguity (byte- vs char-budget truncation in the
  new `bounded-text.test.ts` row) was resolved in favor of the existing
  implementation contract (byte budget, verified against `truncateUtf8`).

## Suggested Codex Review Focus

1. `src/asr/state.ts` ready-gate ordering and fail-closed behavior — confirm
   the pre-read root/stateFile checks (symlinked root or state file →
   `incomplete`, never read, `not_installed` semantics preserved), the 9
   managed paths, and `isRealPath` type semantics (root/venv/bin/model are
   real directories; state/python exe/model artifacts are real files; a
   directory in a file slot or a file in a directory slot never returns
   `ready`) match the verdict's threat model (symlink to
   root/state/runtime/model files), that `crypto.randomUUID` temp naming
   (injectable `randomId`) meets the unpredictability requirement, and that
   the `writeAsrState` root guard (symlink/non-directory rejected before any
   write, 0700 enforced on existing real roots, ENOENT root created
   owner-only) holds.
2. `src/bilibili/video-api.ts` subtitle URL checks — confirm host allowlist +
   port/userinfo ordering rejects every bypass (encoded ports, userinfo in
   query, protocol-relative URLs) before any fetch.
3. The appended untrusted-data warnings on tool descriptions — confirm the
   bilingual wording is acceptable public-facing text.
4. Dependency resolution state — confirm the compatible-only lockfile refresh
   (SDK `^1.30.0`; `fast-uri` 3.1.4 → 3.1.5 within `^3.0.1`, no override) and
   the zero-vulnerability `npm audit --omit=dev --json` result.
5. Test density vs verdict coverage — every verdict has at least one
   deterministic regression test; spot-check the real-fs symlink test guard.
