# Claude To Codex Report: Roadmap Subtitle Integrity + Scriptable Setup (Blocker Resolution)

## Summary

Resolved all 12 Codex blockers for the uncommitted Roadmap implementation in
the isolated worktree `C:/Users/ZX/.paseo/worktrees/28eefzkq/issue-40-ai-subtitle-integrity`
(branch `codex/issue-40-ai-subtitle-integrity`, base `44ac1e7`). No commit,
push, PR, Issue mutation, release, model download, or primary-worktree edit
occurred. The 12 blockers were resolved with the minimum safe diff, using
focused red-before-green tests where behavior changed. A follow-up Codex
acceptance pass found four same-scope misses, all repaired in the same
worktree: (1) `canonicalSubtitleBody` now serializes the exact tuple
`JSON.stringify([seg.from, seg.to, seg.content ?? ""])` — segment `location`
and object key order no longer destabilize a stable body (new red→green
regression); (2) `AiSubtitleIntegrityVerdict` is now an internal type;
(3) the unusable-ai video-info branch now uses `descriptionFallback()` — all
five description blocks share the helper; (4) `fallback_to_description` /
`fallback_to_asr` validation now goes through `validateBoolean` on the raw
args (the derived `|| false` variables had made the earlier helper calls
no-ops), and the manual typeof blocks are deleted — falsy invalid raw inputs
remain rejected by the shared helper. The 12 blockers were resolved with the
minimum safe diff, using focused red-before-green tests where behavior
changed:

- **B1 (title-topic gate removed):** `assessAiSubtitleIntegrity` now returns
  `{ usable: true }` for any stable same-language body; title lexical overlap
  is no longer a rejection signal. Stable same-language semantic mismatch is
  documented as an accepted limitation controlled by `force_asr` /
  `exclude_ai_subtitles`. Red test (topic-rejection replaced by acceptance)
  → green. Docs/QA/memory/PRD updated.
- **B2 (canonicalization):** `canonicalSubtitleBody` serializes each
  `[from,to,content]` tuple with `JSON.stringify` and joins with `\n` —
  collision-free for the reported case (single segment content `a\n1|2|b` vs
  two segments `a`/`b` at `[1,2]`). New regression test added (red → green).
  Helpers/types stay internal (nothing external uses them).
- **B3 (validateBoolean):** the three duplicate `typeof` checks in
  `src/server/tool-handlers.ts` now call `validateBoolean` from
  `src/utils/validation.ts`.
- **B4 (non-interactive credential gate):** non-interactive setup now requires
  `getCredentialSource()` ∈ {env, global_config} AND `getCredentials() !==
  null`; in-memory `source === "none"` is rejected with exit 1 and value-free
  field-name guidance. Tests added with `stdin.isTTY = false` and a
  source-none case (red → green).
- **B5 (description fallback dedup):** five duplicate video-info description
  object literals collapsed into one local `descriptionFallback()` helper in
  `getVideoInfoWithSubtitle`, preserving each branch's `logger.debug` + return.
- **B6 (README truthfulness):** README/README_EN integrity + ASR boundary
  bullets now state that every selected `ai-zh` is always double-read and may
  become unavailable (description or `SUBTITLE_UNAVAILABLE`) even on a default
  call, and that ASR runs only on confirmed absence when `fallback_to_asr` /
  `force_asr` authorizes it.
- **B7 (argv wording):** every "never reads stdin/argv" / "不读 stdin/argv"
  claim across README x2, CHANGELOG x2, client-setup x2, tool-reference x2,
  QA, and project facts now reads "never reads **credential values** from
  stdin/argv / 绝不从 stdin/argv 读取凭据值".
- **B8 (QA live facts):** QA checklist corrected to state that a valid
  logged-in global credential existed on this machine (live calls
  authenticated); no "no Cookie" claim remains; unsupported per-file test
  decomposition removed (focused suite recorded as 319/319). Post-build live
  evidence later verified real-body classification/exclusion/double-read on
  `BV15kyBB5Eg8`; corrupt-body rejection and ASR fallback remain unverified
  (`BV1ybuQ62EfK` exposes no target subtitle; no real ASR/model run
  authorized).
- **B9 (active-work):** `docs/agent-memory/active-work.md` rewritten from the
  stale 885/185/conditional/future state to the current unconditional
  double-read, accepted-limitation, non-interactive-setup, 902/189 state.
- **B10 (report + handoff-log link):** this report created; the
  `handoff-log.md` Roadmap entry already carries the report path and was
  updated with final numbers.
- **B11 (truthful docs/memory only):** decisions.md, project-facts.md,
  codemap.md, task ticket (amendment note), CHANGELOG x2, PRD updated; dated
  historical records (old verification-log/QA/report entries) left untouched.
- **B12 (verification matrix):** see Results below.

## AI Classification Repair (ai-zh → ai-*)

A follow-up acceptance pass in the same approved Issue #40 scope found a
current-upstream root-cause gap. Live authenticated read-only evidence: public
video `BV15kyBB5Eg8` exposes subtitle languages `[ai-zh, ai-en, ai-ja, ai-es,
ai-ar, ai-pt]`. The ai-zh-only classifier filtered only `ai-zh` under
`exclude_ai_subtitles`, silently selected `ai-en` (priority matching
`s.lan.includes(lang)`), and returned `data_source: "subtitle"` — violating the
AI-vs-human distinction and the general `exclude_ai_subtitles` name. No
subtitle text or credential values were recorded.

Repair (TDD red → green, four new public-seam regressions):

- `isAiSubtitle` — the single shared classification driving `data_source`,
  `exclude_ai_subtitles` filtering, and the double-read gate — now matches
  every `ai-*` language (`lan.startsWith("ai-")`).
- `assessAiSubtitleIntegrity` gains a `trackLanguage` argument: the
  collision-free double-read stability check applies to every selected `ai-*`;
  the conservative Han-ratio language rejection applies to `ai-zh` only —
  valid `ai-en`/`ai-ja` bodies are not rejected for being non-Chinese.
- Schema descriptions, bilingual docs, changelogs, PRD v1.2, QA, codemap, and
  memory updated from ai-zh-only to ai-* classification (ai-zh-specific
  language validation retained).

## Files Changed

Source (5):

- `src/bilibili/subtitle-integrity.ts` — topic gate removed; exact-tuple
  canonicalization `JSON.stringify([from,to,content ?? ""])` (location/key
  order invariant); language check unchanged; `AiSubtitleIntegrityVerdict`
  internal.
- `src/bilibili/subtitle.ts` — both `assessAiSubtitleIntegrity` call sites
  drop the title argument; local `descriptionFallback()` helper — all five
  description blocks (empty list, exclude-filtered, no best subtitle, empty
  body, unusable ai-zh) share it.
- `src/cli.ts` — non-interactive branch requires source env/global_config +
  loadable credentials; docstring clarifies no credential values from
  stdin/argv.
- `src/server/tool-handlers.ts` — `validateBoolean` reuse on raw args for
  `fallback_to_description` / `fallback_to_asr` (plus `exclude_ai_subtitles` /
  `force_asr`); both manual typeof blocks deleted.
- `src/bilibili/types.ts` — unchanged this pass (previously ai_subtitle
  classification).
- `src/bilibili/subtitle.ts`, `src/bilibili/subtitle-integrity.ts`,
  `src/server/tool-schemas.ts` — repair pass (see AI Classification Repair
  section): `isAiSubtitle` widened to every `ai-*`; integrity assessment
  takes `trackLanguage` with the language check gated to `ai-zh`;
  `exclude_ai_subtitles` schema descriptions updated.

Tests (4):

- `tests/bilibili-transcript.test.ts` — topic-rejection test replaced with
  stable same-language acceptance; canonical-collision regression added.
- `tests/cli.test.ts` — non-interactive tests mock `getCredentialSource` /
  `getCredentials` (machine-independent), add `stdin.isTTY=false`, add
  source-none rejection.
- `tests/server-tools.test.ts`, `tests/server-handler-sanitization.test.ts` —
  updated for `validateBoolean` / integrity call shapes (already green this
  pass).
- `tests/bilibili-transcript.test.ts` — repair pass added four regressions:
  stable `ai-en` returns `ai_subtitle` after two reads (mock call count proves
  the double read); stable human subtitle stays single-read (lock); transcript
  `exclude_ai_subtitles` filters an AI-only `ai-zh`+`ai-en` set to
  deterministic absence; video-info returns description for the same set.

Docs (user-facing, 10): README.md, README_EN.md, CHANGELOG.md,
CHANGELOG_EN.md, docs/tool-reference.md, docs/tool-reference.en.md,
docs/client-setup.md, docs/client-setup.en.md,
docs/subtitle-integrity-and-scriptable-setup-prd.md (v1.0 → v1.1 → v1.2),
docs/qa/2026-08-18-roadmap-subtitle-integrity-setup.md.

Memory/harness (8): docs/agent-memory/active-work.md, decisions.md,
project-facts.md, codemap.md, handoff-log.md, handoffs/…-task-ticket.md
(amendment note), handoffs/…-claude-report.md (this file),
docs/agent-memory/lessons-learned.md (earlier slice entry, unchanged this
pass).

## Commands Run

```bash
npm run build
npx vitest run tests/bilibili-transcript.test.ts tests/cli.test.ts \
  tests/server-tools.test.ts tests/server-handler-sanitization.test.ts \
  tests/server-error-next-steps.test.ts \
  tests/asr-transcription.test.ts tests/bilibili-playback.test.ts
npm test
npm pack --dry-run --json --ignore-scripts
git diff --check
python <UTF-8 scan over the 34 changed files>
python <secret-pattern scan over the 34 changed files, counts only>
```

## Results

- **Red-before-green evidence (blocker pass):** three focused tests failed
  before the fixes and passed after: (1) source-none non-interactive setup
  expected exit 1 (observed `undefined` before the guard existed); (2) stable
  same-language ai-zh body was rejected by the old topic gate — test flipped
  to acceptance; (3) canonical-collision regression: single segment content
  `a\n1|2|b` must not canonicalize equal to two segments at `[1,2]` (observed
  `NoSubtitleError` after `JSON.stringify` normalization).
- **Red-before-green evidence (acceptance repairs):** one focused test failed
  before the repair and passed after: a stable ai-zh body whose two reads
  differ only in non-canonical fields (segment `location` present vs absent,
  and differing object key order) was wrongly rejected by
  `JSON.stringify(seg)` serialization; the exact-tuple canonicalization
  accepts it (observed `data_source: "ai_subtitle"` after the fix).
- **Focused suite:** 7 files / 319 tests passed.
- **Full suite:** 41 files / 902 tests passed.
- **Build:** `npm run build` passed (tsc clean).
- **Pack:** `npm pack --dry-run --json --ignore-scripts` → 189 entries,
  `dist/bilibili/subtitle-integrity.js` included, no forbidden paths.
- **Diff check:** `git diff --check` clean (only informational LF/CRLF
  warning on CONTEXT.md).
- **Secret scan (counts only, no values):** 34 files scanned. Zero real
  credential values. Classification: `BILIBILI_SESSDATA` assignments in
  `tests/cli.test.ts` are synthetic test fixtures (established prior
  classification); one token-shaped match in verification-log.md is prose
  stating no token was found; `.env` matches are field-name references in
  docs/CLI guidance.
- **UTF-8 scan:** all 34 changed files valid UTF-8 with no replacement
  characters in the working-tree changes. One pre-existing `U+FFFD` exists in
  `docs/agent-memory/verification-log.md:288` in HEAD (old mojibake caveat
  line, not introduced by this worktree); left untouched as historical record.
- **Red-before-green evidence (ai-* classification repair):** four focused
  tests failed before the repair and passed after: (1) stable `ai-en` track
  must return `data_source: "ai_subtitle"` with two reads (observed
  `data_source: "subtitle"` with a single read before the fix); (2) transcript
  `exclude_ai_subtitles` must filter an AI-only `ai-zh`+`ai-en` set to
  deterministic absence (observed the subtitle returned before the fix);
  (3) video-info must return description for the same set (observed
  `data_source: "subtitle"` before the fix); (4) the human-subtitle
  single-read test stayed green throughout (lock).
- **Focused suite (repair pass):** 7 files / 323 tests passed.
- **Full suite (repair pass):** 41 files / 906 tests passed.
- **Live evidence (repair pass):** `BV15kyBB5Eg8` → `[ai-zh, ai-en, ai-ja,
  ai-es, ai-ar, ai-pt]`; pre-fix candidate reproduced the `ai-en` silent
  selection under `exclude_ai_subtitles`. A post-build live run then verified
  classification/exclusion/double-read success (see Risks). No subtitle text
  or credential values recorded.

## Diff Notes

- No public MCP tool names or response shapes changed. The repair pass updated
  the `exclude_ai_subtitles` description text in both schemas (ai-zh → every
  `ai-*` language); tool names, input schema shapes, and response shapes are
  unchanged. Integrity assessment stays a pure internal function;
  helpers/types remain unexported.
- Behavior change per Codex blocker 1: stable same-language bodies are always
  accepted regardless of title topic. This is deliberate and documented as an
  accepted limitation, not a regression.
- `docs/agent-memory/verification-log.md` historical entries still record the
  pre-blocker counts (41/885, 185-file pack) for that point in time; the
  Roadmap handoff-log entry carries the final numbers.

## Risks Or Skipped Checks

- **Accepted limitation:** stable same-language off-topic AI text is returned
  (no local rule can prove semantic mismatch). Controls: `force_asr` /
  `exclude_ai_subtitles`. Documented in PRD v1.2, README x2, tool-reference x2,
  CHANGELOG x2, decisions, project-facts, QA.
- **Live classification verified; corrupt-body/ASR E2E unverified:** a
  post-build authenticated read-only run on `BV15kyBB5Eg8` verified live
  classification, exclusion, and double-read success (default transcript →
  `ai_subtitle`/`ai-zh` with a non-empty body; `exclude_ai_subtitles=true` →
  `NoSubtitleError`; default video-info → `ai_subtitle` with `subtitle_text`;
  exclude=true → description without `subtitle_text`). Live corrupt-body
  rejection and ASR fallback remain unverified: `BV1ybuQ62EfK` currently
  exposes no target subtitle, and no real ASR/model run was authorized.
  Mock-matrix + post-build child smoke cover those paths.
- **Child smoke environment nuance:** post-build child smoke mocks
  `getCredentialSource`/`getCredentials` so results do not depend on this
  machine's real global config file.
- **Pre-existing finding:** `verification-log.md:288` contains a `U+FFFD`
  that exists in HEAD; not introduced here, offered as a separate cleanup.
- Skipped: real model install/transcription, live ASR E2E, npm publish
  checks (nothing published), GitHub Actions (no remote state touched).

## Harness Artifacts

- Task ticket: used — `ROADMAP-2026-08-18-INTEGRITY-SETUP`; an amendment note
  records the title-topic scope change (PRD v1.1).
- Research note: not required — no external research affected this
  implementation; all facts came from the worktree, tests, and build.
- QA checklist: created — `docs/qa/2026-08-18-roadmap-subtitle-integrity-setup.md`,
  updated to final truth (323/323 focused, 906/906 full, live-facts wording
  incl. `BV15kyBB5Eg8` ai-* evidence, credential-values wording, PRD v1.2
  reference).
- Codemap: updated — `src/bilibili/subtitle-integrity.ts` entry rewritten
  (topic gate removed, canonical normalization described).
- Harness security: reviewed — credential-claim wording in docs/harness-facing
  files corrected to "credential values from stdin/argv"; no secret values
  added anywhere; trust-boundary rules respected (no harness surface changed).
- Harness eval: deferred — no roadmap phase, release, or significant harness
  update completed in this pass that would warrant an eval entry.

## Decision Points

None blocking. The one judgment call (title-topic removal) was already made by
Codex in the blocker list; implementation followed it.

## Suggested Codex Review Focus

1. Diff of `src/bilibili/subtitle-integrity.ts` + `src/bilibili/subtitle.ts`:
   confirm the canonical normalization and the removed topic gate match PRD
   v1.1, and that `descriptionFallback()` preserves per-branch debug/return
   behavior.
2. `src/cli.ts` non-interactive gate: source ∈ {env, global_config} AND
   loadable credentials; error output value-free.
3. `tests/cli.test.ts` determinism: all four non-interactive tests mock the
   credential source so they pass on machines with or without a real global
   config.
4. Wording sweep: any remaining "reads argv"/"不读 stdin" claim outside dated
   historical records would be a miss (scan pattern: `stdin`, `argv`).
5. Live follow-up: `BV15kyBB5Eg8` already verified classification/exclusion/
   double-read live. Remaining live gap: corrupt-body rejection and ASR
   fallback (`BV1ybuQ62EfK` currently exposes no target subtitle; no real
   ASR/model run authorized).
