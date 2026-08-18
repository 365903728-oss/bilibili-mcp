# PR #39 automated-review round 5 — Codex Direct execution report

## Scope and authority

- Source: two Codex review threads on PR #39 at pushed base `f15171d`.
- Frozen mode: `codex-direct`; one Codex writer in the isolated worktree.
- Scope: shared bounded-lock transaction anchoring and MCP unknown-tool error
  handling. Product source, package metadata, credentials, SSH, release, and
  publishing remain excluded. This round has no new remote-write authority.

## Implementation

1. `bounded_file_lock` retains a POSIX parent descriptor, tracks nested lock
   parents as a context-local stack, and makes bounded reads, writes, ledger
   appends, and no-follow deletion verify or reuse the active parent. Same-parent
   nested locks cannot reopen a replacement path or create through a replaced
   ancestor. Windows verifies the active parent inside the existing no-reparse
   HANDLE chain for each bounded I/O without holding ancestor handles across Git
   subprocess work.
2. Direct-controller rollback deletion reuses the shared no-follow unlink.
3. An unknown MCP `tools/call` name returns JSON-RPC `-32602 Invalid params`;
   the stdio session continues and processes the following request.

## TDD and verification

- Red: a renamed/replaced POSIX lock parent accepted a second lock inode and
  wrote replacement state; an ancestor symlink allowed nested lock setup to
  create an external directory. An unknown tool call emitted a Harness error,
  exited with status 2, and skipped the following ping.
- Green: same-parent and ancestor-symlink nested-lock regressions reject with no
  replacement write or external directory creation. The MCP serve-loop returns
  `-32602` and then answers ping.
- Final Windows state/event/MCP/migration group: 60 tests passed, 9 skipped.
  Final WSL state/event/MCP group: 59 tests passed, 2 skipped. Direct start,
  concurrent-writer, rollback, Paseo bootstrap/dispatch, Python compilation,
  strict diff, and the LF-normalized three-level receipt chain passed.
- Independent risk review: PASS with no remaining reproducible P0–P3 after the
  nested-lock and pre-bind directory-creation findings were repaired.
