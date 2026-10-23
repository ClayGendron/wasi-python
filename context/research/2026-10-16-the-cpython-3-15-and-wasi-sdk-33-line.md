# The CPython 3.15 + wasi-sdk 33 line

- **Status:** executed, 2026-10-16 (written as a placeholder the same day, completed in place)
- **Owner:** Clay Gendron
- **Researcher:** the author agent (Claude Opus 5.5); box: an afternoon, at the owner's order of post-v1 work (matplotlib first, which needs this line: `2026-10-16-what-matplotlib-needs.md`).
- **Blocks:** the matplotlib build; the second release line.
- **Evidence:** `2026-10-16-the-3-15-line-experiment/`: `setup.sh` and `edit.py` (they clone this repository into a scratch directory and move the clone to the new line; nothing in the repository itself changed), the build's output, and the judge-side changes the experiment needed.
- **Machine (benchmark facts only):** Apple arm64, macOS 26.5, wasmtime 49.

## The question

The first release line is CPython 3.14.8 with wasi-sdk 24, where a C++ `throw` aborts the guest and matplotlib cannot be built. CPython 3.15.0 (2026-10-09) builds with wasi-sdk 33, whose sysroot links C++ exceptions. Does the whole recipe reproduce on 3.15 + SDK 33, and what changes?

## Findings

1. **3.15.0's own driver pins wasi-sdk 33** (READ: `Platforms/WASI/config.toml`, `wasi-sdk = 33`). The driver moved from `Tools/wasm/wasi` to `Platforms/WASI` and kept its interface (`build`, `--quiet`, `--logdir`, extra `configure` arguments after `--`) (READ: `Platforms/WASI/__main__.py`).
2. **Every input exists and is pinnable** (EXECUTED): `Python-3.15.0.tar.xz` (`ba4bed1ba346b916890b76d9e320451420aa69f6408997d33c66482eeae3d575`), python-build-standalone `cpython-3.15.0+20261009-aarch64-apple-darwin-install_only.tar.gz` as the host Python, `cython-3.3.0-cp315-cp315-macosx_11_0_arm64.whl` (`596e8df019372a2cd417805015022d42cb8ee4e1803ccdc11ed00e451625fb66`, from PyPI), and wasi-sdk 33 (already pinned as a research input). meson, ninja, numpy 2.5.2 and pandas 3.0.6 are unchanged.
3. **The recipe needed only build-side edits, no upstream patch** (EXECUTED: `edit.py`):
   - the versions and paths of the line, which today sit in 14 files: SDK and source paths, `cpython-314-wasm32-wasi`, `lib.wasi-wasm32-3.14`, `python314.zip`, the host-Python version check, `TARGET = (3, 14)` in the zip builder and the bootstrap freezer;
   - C++ exceptions, as wasi-sdk 33 documents them (READ: its `CppExceptions.md`): `-fwasm-exceptions -mllvm -wasm-use-legacy-eh=false` in both cross files' `cpp_args`; `-lunwind` beside `-lc++ -lc++abi`; `LDFLAGS_NODIST="-fwasm-exceptions"` on step 60's two `make` calls, so the link picks the exception-enabled libc++; `recipes/cxa_stubs.c` is no longer linked;
   - the snapshot: the standalone Wizer 11 has no switch for the exception-handling proposal, so step 80 runs the wasmtime 49 CLI's own `wasmtime wizer`, with `-W exceptions=y,unknown-imports-trap=y -S cli=y,inherit-stdin=n,inherit-stdout=n,inherit-stderr=n` and `--dir <root>::/`. The door import must be given a stub (`unknown-imports-trap`: the snapshot never calls it, and if it did it would trap), WASI must be switched on (`-S cli=y`), and stdio is not inherited, as the standalone Wizer did by default. One pin fewer: Wizer is part of the pinned wasmtime.
4. **The whole build passes from an empty `build/`** (EXECUTED: 4 min 11 s): the reactor is 29,801,866 bytes (3.14 line: 29,829,406), the snapshot 63,266,905 (62,317,581), the zip 11,140,661 (10,474,585: 3.15's stdlib is larger).
5. **It rebuilds to the same bytes** (EXECUTED: steps 60 to 90 twice): reactor `1522cd8136fc40e5…`, snapshot `9b10b25925df8097…`, zip `b10243c4165170e5…` both times. The link-time pins of the WASI calls work under `wasmtime wizer`, whose preview1 runs on the preview2 implementation.
6. **The guest's results match native 3.15** (EXECUTED). The goldens record the Python version, so the experiment regenerated them with a native 3.15.0 oracle (the same package pins; uv 0.9.22 cannot install 3.15.0, so the oracle used the unpacked host 3.15.0). Native 3.15's outputs equal native 3.14's except the version line, and the guest's equal native 3.15's: v1.3 is 11/11.
7. **C++ exceptions now reach Python** (EXECUTED: `np.fft.fft(np.zeros(12_000_001))` under `memory_bytes` caps of 560 and 700 MiB, where pocketfft's own allocation fails in C++):
   - 3.14 + SDK 24: the guest traps, `fatal: C++ exception thrown in python.wasm (no unwinder on wasm32-wasip1)`;
   - 3.15 + SDK 33: the program gets `MemoryError` and exits 0.

   wasmtime-py 49 runs exception-handling modules with its default configuration: every guest check ran.
8. **The judge needs four edits for the line** (EXECUTED: 11 failures on the first full run, all of these):
   - its own wasm parser (`tests/harness/wasm.py`) does not know value type `0x69` (`exnref`), so four import/export checks could not read the binaries;
   - three runner checks name `python314.zip`;
   - the goldens and the oracle are 3.14 (finding 6);
   - the 3.14 pins have to leave `downloads/SHA256SUMS` with their `get` lines, or stay as research pins.
9. **Cost** (EXECUTED: the judge's driver, fuel exact; wall time a benchmark fact, median of five):

   | run | 3.14 + SDK 24 | 3.15 + SDK 33 |
   |---|---|---|
   | snapshot `-c pass` | 117.6M instructions, 18.7 ms | 124.1M (+5.5%), 19.7 ms |
   | plain `-c pass` | 246.7M, 31.0 ms | 246.8M, 29.8 ms |
   | plain `-c "import pandas"` | 4,953.9M, 698.6 ms | 4,995.3M (+0.8%), 724.9 ms |

## What it decides

The next release line is CPython 3.15.0 + wasi-sdk 33: it reproduces, matches native, and turns C++ exceptions from an abort into a Python exception, which numpy needs today (finding 7) and matplotlib needs to exist at all. `0.1.0a1` ships on 3.14.8 + SDK 24, already built, judged and verified on three systems, with the abort listed as a known limit. A specification moves the line: it gathers the line's versions into one place first (so the next line is a small diff), then makes the edits of findings 3 and 8, drops the standalone Wizer pin, and moves the oracle to 3.15 (a newer pinned uv, or the host Python as in the experiment).

## One line

CPython 3.15 with wasi-sdk 33 builds, rebuilds to the same bytes and matches native with only build-side edits, and it makes a C++ exception a Python exception instead of a crash.
