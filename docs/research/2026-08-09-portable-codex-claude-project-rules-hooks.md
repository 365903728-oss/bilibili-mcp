# Portable Codex And Claude Project Rules And Hooks

## Research Topic

- Topic: Portable project-rule and Hook discovery for Harness v2
- Date: 2026-08-09
- Refreshed: 2026-08-11
- Owner: Codex
- Related task: GitHub Issue #29
- Refresh before: changing the adapter bootstrap or Hook config schema

## Question

How can one shared project-rule core and one shared Hook CLI be discovered from
clean Codex and Claude Code sessions without machine-specific checkout paths?

## Context

Issue #29 replaces duplicated, path-bound Harness rules and Hook registrations
with one shared core and thin host adapters. The project needs current primary
source evidence for host discovery/import behavior and portable Hook variables.

## Sources

| Source | Type | Date checked | Notes |
| --- | --- | --- | --- |
| https://learn.chatgpt.com/docs/agent-configuration/agents-md | OpenAI official docs | 2026-08-09 | Repository-root-to-CWD discovery, one instruction file per directory, combined size limit |
| https://learn.chatgpt.com/docs/hooks | OpenAI official docs | 2026-08-09 | Project-local Hook discovery and trust, lifecycle events, Git-root resolution, and JSON stdin fields |
| https://docs.anthropic.com/en/docs/claude-code/memory | Anthropic official docs | 2026-08-09 | `CLAUDE.md` project memory and `@path` imports |
| https://code.claude.com/docs/en/hooks | Anthropic official docs | 2026-08-09 | Project settings, command/args form, stdin JSON, `${CLAUDE_PROJECT_DIR}`, Hook security, and distinct success/failure tool events |
| https://github.com/openai/codex/issues/18607 | OpenAI repository issue | 2026-08-09 | Reported non-interactive `codex exec` Hook lifecycle gap |

## Findings

- Codex discovers `AGENTS.md` along the repository-root-to-working-directory
  path. The current official page does not document a native file-import
  directive; treating the thin Codex adapter as a bootstrap that explicitly
  requires reading `RULES.md` is therefore a project inference, not a claimed
  Codex import feature.
- Claude Code supports importing project instructions from `CLAUDE.md` with
  `@path`, so `@RULES.md` can load the shared core without duplicating it.
- Claude project Hook configuration can be shared in `.claude/settings.json`;
  `.claude/settings.local.json` is appropriate for ignored machine-local
  preferences.
- Claude Hook commands receive JSON on stdin and support
  `${CLAUDE_PROJECT_DIR}`, permitting a worktree-local CLI path.
- Claude `PostToolUse` runs only after successful execution, while failures that
  begin executing use `PostToolUseFailure` with a top-level `error`. Both must be
  registered and translated; a normal successful tool response can contain a
  `message` field and must not be inferred to be a failure from that field.
- Hook commands must validate and sanitize input, quote variables, avoid
  secrets, and use portable project-root resolution. These requirements support
  a thin adapter plus one bounded shared normalizer.
- OpenAI's current Hook documentation says project-local Hooks are discovered
  from `<repo>/.codex/hooks.json` only after trust, commands run with the session
  working directory, repository Hooks should resolve from the Git root, and
  every command receives one JSON object on stdin.
- An untrusted/non-bypass `codex exec` run on 2026-08-09 discovered project rules
  without dispatching the project Hook lifecycle, matching the historical gap
  reported in openai/codex issue #18607. A trusted normal-config run on
  2026-08-11 dispatched `SessionStart`, `PostToolUse`, and `Stop`; it also ran
  the primary worktree's legacy Hooks from the linked worktree, proving that
  multiple trusted configuration layers can overlap. A separate
  `--ignore-user-config` run proved clean rule discovery, and all four tracked
  Hook commands remain covered by real process-boundary stdin tests.

## Applicability To This Project

Applies:

- `AGENTS.md` is a small Codex bootstrap/delta that points to `RULES.md`.
- `CLAUDE.md` imports `RULES.md` and adds only Claude-specific behavior.
- `.claude/settings.json` uses `${CLAUDE_PROJECT_DIR}`.
- `.codex/hooks.json` resolves `git rev-parse --show-toplevel` at runtime because
  no equivalent documented project-dir variable was established for this
  configuration.

Does not apply:

- This research does not authorize a model/provider choice, permission change,
  product MCP/CLI change, or remote operation.
- It does not prove end-to-end behavior for every future Codex/Claude release;
  conformance fixtures and live smokes remain required.

## Decision Impact

Adopt one `RULES.md`, two thin adapter documents, tracked portable Hook
translators, and `harness/cli.py` as the normalization seam. Keep Hook runtime
state ignored and scoped by dynamically discovered worktree identity.

## Risks And Unknowns

- Project Hook trust and external configuration layers vary by host and
  checkout. `doctor` diagnoses event overlap with primary/user Codex Hooks and
  coexistence with machine-local Claude Hooks without rewriting those files.
- A normal Codex run may wait for unrelated user-configured MCP shutdown after
  producing its requested result; the clean rule-discovery smoke therefore uses
  `--ignore-user-config`, while Hook commands have independent process tests.

## Follow-Up

- [x] Issue #29 proved clean Codex and Claude rule discovery, every configured
  Codex translator command at a real process boundary with stdin forwarding, a
  trusted live Codex lifecycle, and real Claude success/failure lifecycle
  events. The primary-worktree Codex Hook overlap is detected and reported as
  `action-required`, not silently accepted.
- [ ] Re-run the complete three-adapter pilot matrix and release-level
  conformance suite in final ticket #36.
