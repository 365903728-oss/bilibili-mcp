# Research Topic

- Topic: Phase 2 faster-whisper model allowlist
- Date: 2026-07-27
- Owner: Codex
- Related task: `docs/asr-model-selector-prd.md`
- Refresh before: changing the allowlist or publishing the next release

## Question

Which small multilingual CTranslate2 model repositories, immutable revisions,
and approximate download sizes should the selector expose?

## Context

The selector should offer meaningful storage choices without accepting custom
repositories or including hardware-heavy models.

## Sources

| Source | Type | Date checked | Notes |
|---|---|---|---|
| [Systran/faster-whisper-tiny](https://huggingface.co/Systran/faster-whisper-tiny/tree/d90ca5fe260221311c53c58e660288d3deb8d356) | official model repository | 2026-07-27 | Multilingual CTranslate2 model, MIT; tree reports 78.2 MB. |
| [Systran/faster-whisper-base](https://huggingface.co/Systran/faster-whisper-base/tree/ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66) | official model repository | 2026-07-27 | Multilingual CTranslate2 model, MIT; tree reports 148 MB. |
| [Systran/faster-whisper-small](https://huggingface.co/Systran/faster-whisper-small/tree/536b0662742c02347bc0e980a01041f333bce120) | official model repository | 2026-07-27 | Existing Phase 1 multilingual model; tree reports 486 MB. |
| `git ls-remote https://huggingface.co/<repo> HEAD` | live official repository metadata | 2026-07-27 | Confirmed the three full HEAD revisions above. |
| Hugging Face repository-details connector | live repository metadata | 2026-07-27 | Confirmed author, ASR task, CTranslate2 library, multilingual tags, and MIT license for all three repositories. |

## Findings

- The three repositories share the files required by the current readiness
  check: `model.bin`, `config.json`, `tokenizer.json`, and `vocabulary.txt`.
- Their displayed repository sizes are approximately 78.2 MB, 148 MB, and
  486 MB.
- All three are multilingual CTranslate2 ASR models and work with the existing
  `faster-whisper` loading interface.
- `small` is already the Phase 1 pinned model and remains the recommended
  default for backward compatibility.

## Applicability To This Project

Applies:

- Pin all three revisions in a local allowlist.
- Show approximate model size before download.
- Keep `small` as the Enter/default choice.

Does not apply:

- Downloads, likes, Spaces, benchmark claims, and English-only variants do not
  affect the selector.
- `medium` and `large` variants are intentionally excluded from the lightweight
  first selector.

## Decision Impact

- Add no dependency and no remote catalog lookup at setup time.
- Reject any model key outside `tiny`, `base`, and `small`.
- Reuse the existing managed model directory and state schema.

## Risks And Unknowns

- Displayed repository sizes are approximate and exclude Python runtime library
  overhead.
- Upstream HEAD can change; immutable revisions prevent silent installer drift.

## Follow-Up

- [ ] Refresh revisions and displayed sizes before publication.
