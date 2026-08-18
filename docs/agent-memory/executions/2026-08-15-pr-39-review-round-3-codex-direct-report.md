# PR #39 automated-review round 3 — Codex Direct execution report

## Scope and authority

- Source: the two P2 Codex review threads on PR #39 commit
  `80e893b1d0e0a8078cb3c7a0dd8f91f2e11e9fb6`.
- Frozen mode: `codex-direct`; Codex holds the only implementation writer
  lease. The canonical worktree was clean and the primary checkout's 58 dirty
  status rows remained isolated.
- Scope: verified-descriptor JSONL reads and a recoverable two-artifact typed-
  memory projection transaction. Product `src/`, dependencies, package output,
  remotes, credentials, SSH, tags, releases, and publishing are excluded.

## Implementation

1. JSONL reads open one descriptor with no-follow where supported, verify its
   regular-file identity against lstat, and apply the configured byte bound to
   the actual descriptor read. Replacement and growth races fail closed.
2. Typed memory writes a bounded metadata-only prepared marker before either
   tracked artifact changes. It binds the target task and accepted envelope.
   Ordinary failures restore the exact in-process prior pair. Interrupted
   recovery accepts only a prior pair matching the internally consistent bytes
   committed at Git `HEAD`, restores it, then runs the same accepted envelope
   normally. Unanchored state stops for explicit recovery.

## TDD and verification

- Red: JSONL growth, second-file failure, and interrupted transaction marker
  tests failed 3/4; Windows skipped the symlink case for missing privilege.
- Focused green: the four regressions pass with that one Windows skip; WSL runs
  both descriptor races 2/2; full events and typed-memory modules pass 47 tests
  in 42.156s with one Windows symlink skip.
- Independent review found that self-reported after digests, then a fully
  self-consistent forged marker, could admit an unrelated record; reverse replay
  also failed for valid duplicate candidates. The repair removes forward trust
  from the marker and anchors recovery to Git `HEAD`; all three transaction
  regressions pass.
- Final risk-weighted matrix passes 49 tests in 47.689s with one Windows-only
  symlink-permission skip. Re-review then exposed a short-append descriptor
  race: tail discard and payload reads each had a byte budget. One descriptor
  read now uses the single budget and is revalidated afterward; the red
  regression and the complete 12-test event module pass, and WSL passes both
  descriptor races 2/2. Static/JSON/UTF-8/diff/secret/debug gates pass.
  Independent final review is PASS with no reproducible P0-P3; the scoped local
  commit follows Harness acceptance.
