# Research Topic

- Topic: CUDA readiness and the pinned CTranslate2 runtime for Issue #66
- Date: 2026-08-24
- Owner: Codex
- Related task: GitHub Issue #66 under #55
- Refresh before: changing either Python runtime pin or claiming a new GPU-supported release

## Question

Which exact CTranslate2 version should accompany `faster-whisper==1.2.1`,
what does a real readiness check need to execute, and what CUDA support can the
project truthfully claim today?

## Context

Why this matters for `@xzxzzx/bilibili-mcp`:

- `faster-whisper==1.2.1` allows a moving CTranslate2 range, so two installs of
  the same package version can otherwise receive different GPU runtimes.
- Detecting an NVIDIA device or constructing a model object does not prove that
  the selected model can complete CUDA inference.

What decision or implementation this may affect:

- The exact managed Python dependency pins, the `auto | cpu | cuda` setup
  contract, sanitized failure categories, and release claims.

## Sources

| Source | Type | Date checked | Notes |
|--------|------|--------------|-------|
| [faster-whisper v1.2.1 requirements](https://raw.githubusercontent.com/SYSTRAN/faster-whisper/v1.2.1/requirements.txt) | official source | 2026-08-24 | Allows `ctranslate2>=4.0,<5`; it does not provide an exact pin. |
| [faster-whisper GPU requirements and usage](https://github.com/SYSTRAN/faster-whisper#gpu) | official source | 2026-08-24 | Documents CUDA/FP16 and CPU/INT8 profiles, required NVIDIA libraries, and that transcription starts only when the segment generator is consumed. |
| [CTranslate2 installation](https://opennmt.net/CTranslate2/installation.html) | official docs | 2026-08-24 | Windows/Linux wheels support GPU execution; system CUDA libraries remain an external prerequisite. |
| [CTranslate2 hardware support](https://opennmt.net/CTranslate2/hardware_support.html) | official docs | 2026-08-24 | Prebuilt GPU support is NVIDIA-only and remains driver/CUDA dependent. |
| [CTranslate2 v4.8.0](https://github.com/OpenNMT/CTranslate2/releases/tag/v4.8.0) and [PyPI 4.8.0](https://pypi.org/project/ctranslate2/4.8.0/) | official release and registry | 2026-08-24 | Confirms the immutable release and published Windows wheel. |
| [NVIDIA cuDNN Windows installation](https://docs.nvidia.com/deeplearning/cudnn/installation/latest/windows.html) | official docs | 2026-08-24 | Documents Windows CUDA 12 cuDNN 9 wheels and the requirement to expose runtime DLL directories to the host process. |
| Sanitized project GPU smoke | local acceptance evidence | 2026-07-27 | CTranslate2 4.8.0 loaded the selected model on a Windows RTX 5060 with `cuda/float16`, transcribed a 15-second WAV, fully consumed the generator, and produced non-empty segments; a later six-video run also completed. |
| Isolated Issue #66 smoke | local acceptance evidence | 2026-08-24 | Exact runtime pins were exercised without modifying the user's managed ASR directory. |

## Findings

- The upstream `faster-whisper==1.2.1` dependency range is insufficient for a
  reproducible GPU setup because it can float across CTranslate2 releases.
- CTranslate2 4.8.0 is the only exact version for which this project has a
  recorded real Windows CUDA model-load and inference result. That evidence
  includes generator consumption, not only object construction or device
  enumeration.
- The 2026-07-27 command directly recorded CTranslate2 4.8.0, but did not print
  the faster-whisper version in the same command. It therefore supports the
  CTranslate2 pin but is not sufficient by itself to claim that the complete
  current pair has passed a fresh release smoke.
- The 2026-08-24 isolated environment installed exactly
  `faster-whisper==1.2.1` and `ctranslate2==4.8.0`. On an RTX 5060 Laptop GPU
  with driver 592.19, the real CUDA probe returned the sanitized
  `cuda_runtime_missing` category. The subsequent CPU/INT8 probe and actual
  transcript runner completed successfully.
- An explicit CPU setup performed no GPU stage. An explicit CUDA retry failed
  with the same sanitized category and left the previous state byte-for-byte
  unchanged.
- A post-review isolated staging smoke rebuilt the exact pinned runtime from a
  legacy state, published `cpu/int8`, and completed an actual runner transcript
  from the newly activated managed venv. A subsequent explicit CUDA attempt
  preserved both the prior state and a runtime marker, left zero staging
  directories, and returned only `cuda_runtime_missing`.
- A final Windows GPU acceptance run supplied external CUDA 12 libraries only
  through an isolated disposable Python environment and the current process
  `PATH`: `nvidia-cublas-cu12==12.9.2.10`,
  `nvidia-cudnn-cu12==9.24.0.43`, and
  `nvidia-cuda-runtime-cu12==12.9.79`. With those prerequisites visible, a new
  exact `faster-whisper==1.2.1` + `ctranslate2==4.8.0` staged setup published
  `cuda/float16`. The actual managed runner transcribed a locally synthesized
  speech WAV into one non-empty segment (46 characters, detected English).
- The final GPU run left no staging, backup, or generated-probe WAV residue.
  The existing user ASR state remained v1 with its prior CTranslate2 4.8.1
  environment, and neither persistent `PATH` nor `CUDA_PATH` was changed.
- Upstream pages are not fully consistent about the cuDNN generation for all
  CTranslate2 versions. The project should not encode an automatic CUDA library
  installer or a filesystem-specific recipe; the real inference probe remains
  the readiness authority.

## Applicability To This Project

Applies:

- Install both exact pins in the managed venv on every setup rerun.
- Treat `cuda/float16` as ready only after the selected local model completes a
  generated-WAV transcription and the segment generator is exhausted.
- Preserve ambient `CUDA_PATH` and `LD_LIBRARY_PATH` for the child without
  setting or modifying either variable; continue dropping `LD_PRELOAD`,
  credentials, proxies, and unrelated environment values.
- Return only the fixed categories `no_nvidia_gpu`, `cuda_runtime_missing`,
  `runtime_version_mismatch`, and `model_probe_failed`.

Does not apply:

- The historical smoke does not authorize a current GPU-ready release claim.
- The project does not install NVIDIA drivers, CUDA, cuBLAS, cuDNN, mutate
  system loader paths, or manage global Python.

## Decision Impact

Recommended project action:

- Pin `ctranslate2==4.8.0` beside `faster-whisper==1.2.1`.
- Keep `auto` as the default, but save CUDA only after full inference; otherwise
  explain the sanitized reason and save CPU only after its own inference passes.
- Treat the fresh Windows exact-pair GPU setup and non-empty runner transcript
  as satisfying the Issue #66 Windows GPU gate. Keep Linux GPU explicitly
  unverified.

Rules or files that may need updates:

- `src/asr/state.ts`, `src/asr/installer.ts`, `src/asr/transcription.ts`,
  `src/cli.ts`, ASR documentation, and the Issue #66 QA record.

## Risks And Unknowns

- The exact cuBLAS/cuDNN provenance of the 2026-07-27 successful machine was
  not recorded.
- GPU compatibility can change with drivers and system libraries even while
  Python package versions stay fixed.
- Windows is the only platform with historical real GPU evidence; no Linux GPU
  machine has been exercised for this ticket.

## Staleness Notes

Refresh this research when:

- either Python pin changes
- CUDA/cuDNN upstream requirements change
- a new Windows or Linux GPU smoke is used for a release claim

## Follow-Up

- [x] Expose compatible NVIDIA CUDA runtime libraries outside the project and
  pass new setup, readiness, and an actual GPU transcript.
- [x] Record the complete ASR pair, driver summary, sanitized result, and
  platform without recording raw stderr or private data.
- [ ] Obtain a separate real Linux GPU smoke before making a Linux GPU
  verification claim.
