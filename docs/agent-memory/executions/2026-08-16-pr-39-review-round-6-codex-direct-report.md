# PR #39 automated-review round 6 — Codex Direct execution report

## Scope and authority

- Source: three Codex review threads on PR #39 at pushed base `6b9683c`.
- Frozen mode: `codex-direct`; one Codex writer in the isolated worktree.
- Scope: safe lock-directory creation, POSIX lock-inode serialization, and MCP
  invalid-params responses. The user separately authorized commit, push, and a
  new `@codex review`; PR merge, release, publish, credentials, and SSH remain
  excluded.

## Implementation

1. Missing runtime directories are created through verified no-follow directory
   chains. POSIX uses descriptor-relative `mkdir`; Windows holds no-reparse,
   no-share-delete directory handles while creating and opening each component.
2. POSIX outer transactions flock the verified parent directory, retain the
   descriptor, and bind the active lock name and inode. A replaced or unlinked
   lock fails closed, and another controller cannot acquire a replacement lock
   inode while the original transaction is active. Same-parent nested locks
   reuse the active parent transaction.
3. The MCP stdio boundary maps bounded validation failures for supported
   requests to JSON-RPC `-32602`, advances initialization only after a successful
   response, and continues processing later messages.

## TDD and verification

- Red: a missing lock parent followed a swapped ancestor and created an external
  directory; replacing `run.lock` admitted a second writer; invalid tool
  arguments emitted a Harness error and terminated the MCP session.
- Green: the three regressions reject external creation and the second writer,
  detect lock-file drift, and return `-32602` before answering the trailing ping.
- Windows: events plus CLI/MCP/migration passed 44 tests with 9 platform skips;
  focused Direct/Memory/Paseo lock transactions passed 7/7.
- WSL/POSIX: events, lock races, MCP invalid params, and concurrent reminder
  serialization passed 23 tests with 1 platform skip; focused
  Direct/Memory/Paseo lock transactions passed 7/7.
- Python compilation, strict diff, and the LF-normalized CLI/safe-I/O/migration
  receipt chain pass. WSL cannot run the Git-backed migration assertion because
  this linked worktree's `.git` file contains a native Windows path; the native
  Windows conformance result is authoritative for that check.
