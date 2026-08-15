# PR #39 automated-review round 4 — Codex Direct execution report

## Scope and authority

- Source: three current Codex review threads on PR #39 at pushed base
  `1f638b5085568e1c87e46057df915f2ba53c348a`.
- Frozen mode: `codex-direct`; one Codex writer in the isolated worktree. The
  primary checkout's 58 dirty status rows remained isolated.
- Scope: V2 zero-result Search evidence, cross-platform Paseo test resolution,
  and a portable forged-receipt fixture. Product source, package manifests,
  remotes, credentials, SSH, releases, and publishing are excluded.

## Implementation

1. V2 zero-candidate Build reuses the shared four-channel verifier. Its source
   records share one Git identity; official/live URLs bind repository, revision,
   and artifact; Registry and exact unversioned npm paths bind the original
   query digest. Recorded bytes/results are derived again before acceptance.
2. Paseo tests emit `.cmd` on Windows and an executable `paseo` shell launcher
   on POSIX. Production resolution accepts only the native launcher, including
   under WSL with an inherited Windows PATH.
3. The forged receipt fixture preserves valid terminal-task fields, corrupts
   only receipt authority, and writes canonical bytes so Windows and POSIX reach
   the same accepted-current-gap rejection.

## TDD, recovery, and verification

- Red: forged zero-result digests, four allowed-host but unrelated coordinates,
  and a version-scoped npm 404 each reached `build-ready`; POSIX lacked a native
  runnable stub; the receipt fixture failed at different boundaries by OS.
- The first contract omitted the shared Paseo resolver. It stopped in Recovery
  Bundle fingerprint
  `cedc3edc5b54bf15ad3eb3b04133fc11186487dfe3ec255c52ebe5beb24b7f83`.
  A reversible stash transferred the unchanged diff to a same-base, same-mode
  continuation with the resolver explicitly owned.
- Green: the final V2 rejection and legal Search→Build→Evaluate→Accept test
  passed 1/1 in 57.435s; the final zero/candidate channel group passed 3/3 in
  97.449s. WSL native resolution passed with the ordinary inherited PATH.
  Earlier risk-weighted Evolution coverage passed 6/6 in 323.104s and POSIX
  Paseo coverage passed 4/4 in 3.224s.
- Migration/conformance/package exclusion passes 1/1 after every final digest
  refresh. Python compile, strict diff, product-path, credential-pattern, and
  remote-effect boundaries pass.
- Independent final review: PASS with no reproducible P0-P3 after closing its
  three P1 findings for unrelated coordinates, WSL launcher ordering, and
  version-scoped npm 404 evidence.
