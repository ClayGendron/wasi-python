# 005 — The CPython 3.15 + wasi-sdk 33 line

- **Status:** landed, 2026-10-17. Reviewed before build
  (`../reviews/005-the-3-15-line-spec-2026-10-16.md`) and after
  (`../reviews/005-the-3-15-line-2026-10-17.md`); accepted as `context/progress/history.jsonl`
  line 7.
- **Owner:** Clay Gendron
- **Kind:** build recipe (`downloads/SHA256SUMS`, `scripts/`, `recipes/`), `src/wasi_python/`
  (a docstring), judge edits in `tests/`, `CHANGELOG.md`, `README.md`,
  `.github/workflows/release.yml` (a comment).
- **Depends on:** 003 (the build), 004 (the release that ships it as the next alpha).
- **Research it stands on:** `../research/2026-10-16-the-cpython-3-15-and-wasi-sdk-33-line.md`
  (the experiment this specification turns into the build),
  `../research/2026-10-16-what-matplotlib-needs.md` (why: C++ exceptions, `<thread>` in
  pybind11, setjmp), `../research/2026-10-16-cpp-exceptions-and-wasi-hosts.md` (whether C++
  can be done without the exception-handling proposal, and which hosts have it).
- **The owner's decision** (2026-10-16): require the WebAssembly exception-handling proposal,
  after confirming that C++ cannot be done on WASI without it ("I want to make sure we are as
  supportive of WASI as possible"). That confirmation is the third memo above; this
  specification is built only once it is executed and confirms it.

## Decisions

1. **The line, and its pins.** CPython 3.15.0 with wasi-sdk 33, the SDK 3.15's own driver
   pins (`Platforms/WASI/config.toml`). Every new pin, with its `get` line's URL and its
   SHA-256 (EXECUTED: downloaded and hashed):
   - `Python-3.15.0.tar.xz`, `https://www.python.org/ftp/python/3.15.0/Python-3.15.0.tar.xz`,
     `ba4bed1ba346b916890b76d9e320451420aa69f6408997d33c66482eeae3d575`;
   - `cpython-3.15.0+20261009-aarch64-apple-darwin-install_only.tar.gz`,
     `https://github.com/astral-sh/python-build-standalone/releases/download/20261009/cpython-3.15.0%2B20261009-aarch64-apple-darwin-install_only.tar.gz`,
     `3fb079450ee57075a790b94634206759501166e0a99de459cdad095f6c158d39`;
   - `cython-3.3.0-cp315-cp315-macosx_11_0_arm64.whl`,
     `https://files.pythonhosted.org/packages/ea/45/7f6988070013e16918e39b1b3dab9c5f2c8e404253a7fd10ee685bbd6902/cython-3.3.0-cp315-cp315-macosx_11_0_arm64.whl`,
     `596e8df019372a2cd417805015022d42cb8ee4e1803ccdc11ed00e451625fb66` (PyPI's hash, and the
     downloaded file's);
   - `wasi-sdk-33.0-arm64-macos.tar.gz`, already pinned
     (`85c997a2665ead91673b5bb88b7d0df3fc8900df3bfa244f720d478187bbdc78`), becomes a build pin;
   - the licence notices of SDK 33's own sources (its `VERSION`: wasi-libc
     `161b3195fc2558d2b1ba3eb9ffae3b2b47407623`, LLVM `4434dabb69916856b824f68a64b029c67175e532`,
     22.1.0), each `https://raw.githubusercontent.com/<repo>/<commit>/<path>` saved as
     `wasi-libc-161b3195-<name>` or `llvm-4434dabb-<component>-LICENSE.TXT`:
     wasi-libc `LICENSE` `2711a8b5a5cdfef0e639f96c1aca12ae23d7d64a02d0507f1bdf14d2b27bbc3a`,
     `LICENSE-APACHE` `a60eea817514531668d7e00765731449fe14d059d3249e0bc93b36de45f759f2`,
     `LICENSE-APACHE-LLVM` `268872b9816f90fd8e85db5a28d33f8150ebb8dd016653fb39ef1f94f2686bc5`,
     `LICENSE-MIT` `23f18e03dc49df91622fe2a76176497404e46ced8a715d9d2b67a7446571cca3`,
     `libc-top-half/musl/COPYRIGHT` `f9bc4423732350eb0b3f7ed7e91d530298476f8fec0c6c427a1c04ade22655af`,
     `libc-bottom-half/cloudlibc/LICENSE` `c8b789cf5a746611e6300a0cc7750dbf92b61912a709d04e639245f7290656d0`;
     LLVM `libcxx/LICENSE.TXT` `539dd7aed86e8a4f12cbdd0e6c50c189c7d74847e4fecc64ce2c6ee3a01da38b`,
     `libcxxabi/LICENSE.TXT` `e2b35be49f7284a45b7baca8fc7b3ab7440e7902392b2528a457816b5bb2a15c`,
     `compiler-rt/LICENSE.TXT` `1a8f1058753f1ba890de984e48f0242a3a5c29a6a8f2ed9fd813f36985387e8d`,
     and, new because `-lunwind` links libunwind into both binaries, `libunwind/LICENSE.TXT`
     `b5efebcaca80879234098e52d1725e6d9eb8fb96a19fce625d39184b705f7b6d`.

   numpy 2.5.2, pandas 3.0.6, zlib 1.3.1, meson, ninja, the pure-Python wheels and wasmtime 49
   are unchanged.
2. **The line's versions live in one file, `scripts/line.conf`.** Its grammar: one
   `NAME=value` per line, no spaces, no quotes, `#` starting a comment line; nothing else.
   The names: `PYTHON_VERSION` (`3.15.0`), `WASI_SDK_VERSION` (`33`), `WASI_SDK_DIR`
   (`wasi-sdk-33.0-arm64-macos`), `HOST_PYTHON_ARCHIVE`, `CYTHON_WHEEL`, `WASMTIME_DIR`
   (`wasmtime-v49.0.3-aarch64-macos`), `WASI_LIBC_COMMIT` (the 8-character prefix of the
   pinned licence names) and `LLVM_COMMIT`. `steps/common.sh` sources it and derives
   `PYTHON_MM` (`3.15`) and `PYTHON_TAG` (`315`), so they cannot disagree with
   `PYTHON_VERSION`; `scripts/line.py` parses the same grammar for the Python scripts and
   derives the same two. Everything that named the line reads it there: every step, both cross
   files (a new `@SDK@` token, replaced by the same `sed` as `@ROOT@`), `python-wasi-cross`,
   `gen_inittab.py` and step 60 (the extension suffix), `make_stdlib_zip.py` and
   `freeze_bootstrap.py` (the target version), step 80 and the zip's guest name
   (`python{PYTHON_TAG}.zip`), the host-Python check of step 10, and `assemble_artifacts.py`
   (the Python version, and the licence names from the two commits). `line.conf` and
   `line.py` are tracked under `scripts/`, so they become `recipe` lines of `MANIFEST`.
3. **C++ exceptions are on**, as wasi-sdk 33 documents them: `-fwasm-exceptions -mllvm
   -wasm-use-legacy-eh=false` in both cross files' `cpp_args`; `-lunwind` beside `-lc++
   -lc++abi` in `Setup.local`; `LDFLAGS_NODIST="-fwasm-exceptions"` on step 60's `make` and
   `make -n` (CPython's stack and memory link flags sit in a separate variable and are kept:
   the review READ the Makefile). `recipes/cxa_stubs.c` is deleted.
4. **What hosts must support.** The binaries use the exception-handling proposal (its standard
   form, `exnref`), and a host without it cannot load them (EXECUTED by the review:
   `wasmtime compile -W exceptions=n` refuses them). The imports do not change: 42 WASI
   preview1 functions and `host::call`; the exception tag is defined inside the module
   (EXECUTED by the review). The third research memo confirms that C++ has no route on WASI
   without the proposal under our rules, and that the legacy form would lose wasmtime, wazero
   and WasmEdge (its findings 1, 4 and the recommendation). The README's host list is that
   memo's, and says only wasmtime 49 was run, the rest read:
   - runs by default: wasmtime ≥ 47 (CLI, Rust, wasmtime-py; 37 to 46 with `-W
     exceptions=y`) and WasmEdge ≥ 0.16 (AOT ≥ 0.18);
   - runs with a switch: wasmer ≥ 6 on LLVM, V8 or Cranelift ≥ 7 (not Singlepass); wazero
     ≥ 1.12 with its experimental opt-in; Node ≥ 24.15 or 25;
   - does not run: WAMR, wasmi, wasmer-python, wasmer-go, wasmtime's Winch, and wasmtime built
     without its `gc` feature.

   The README names the 0.1.0a1 set (3.14 + SDK 24) as the set for hosts without the
   proposal, with its limits (a C++ throw ends the guest; no matplotlib) and where to get it:
   the `v0.1.0a1` release's assets, or `wasi-python==0.1.0a1` once that version is on PyPI. An EH-free 3.15
   set is not built; it would be a build-time profile if an embedder needs one. `CHANGELOG.md`
   states the requirement. The `-V` sentence does not, since a host without the proposal
   cannot run `-V` at all. Neither 3.15 binary needs extended-const, which wazero gates
   behind a further opt-in: both compile with `-W extended-const=n` (EXECUTED by the review's
   confirmation). They need multi-value and reference-types, both Wasm 2.0. The README's
   opening sentence stops naming wazero and wasmer as plain WASI hosts and points to the host
   list, and its embedder step 1 names `python315.zip`.
5. **The snapshot is made by `wasmtime wizer`**, the pinned wasmtime 49 CLI's own: `wasmtime
   wizer -W exceptions=y,unknown-imports-trap=y -S
   cli=y,inherit-stdin=n,inherit-stdout=n,inherit-stderr=n -C cache=n --init-func
   wizer.initialize --dir <root>::/ -o python-snapshot.wasm python.wasm`. The standalone Wizer 11
   cannot read exception-handling code, and its pin is removed. `-C cache=n` keeps its
   compile cache out of the builder's home (the same snapshot bytes: EXECUTED by the review).
   `MANIFEST`'s `x-wizer` line is that literal command, with the root named generically.
6. **The snapshot pre-imports `_colorize` too.** In 3.14 another pre-import loaded it; in 3.15
   it is loaded lazily, so the first traceback, `pdb` or `argparse` help in a run imported it:
   an uncaught error cost 328.6M instructions on the 3.15 snapshot against 118.9M on 3.14
   (EXECUTED). `PREIMPORT` becomes `encodings, io, os, sys, json, csv, re, _colorize, numpy,
   pandas` (in `recipes/reactor_main.c` and `assemble_artifacts.py`'s `x-preimport`).
7. **The 3.14 line's pins leave** `downloads/SHA256SUMS` and `00_download.sh`: the 3.14.8
   tarball, its host Python, the cp314 Cython wheel, wasi-sdk 24, Wizer 11 and the six
   wasi-libc and three LLVM licence files at the SDK-24 commits. Brett Cannon's 3.14.7 build
   stays a research pin; `assemble_artifacts.py`'s `RESEARCH_PINS` is then that one file
   (wasi-sdk 33 leaves it, so `MANIFEST` keeps its SDK pin).
8. **CPython's driver moved**: step 20 runs `Platforms/WASI build` with the same arguments
   (the review READ that it fetches nothing).
9. **Judge edits** (accepted with `--accept-judge`):
   - `tests/harness/wasm.py` reads value type `0x69` (`exnref`); a unit test covers it;
   - `paths.manifest_pin_errors` requires pins for `wasi-sdk` and `wasmtime`, not `wizer`;
     `scan.toolchain_errors` drops `wizer`; the known gap of
     `test_toolchain_is_pinned_for_linux_and_macos` gets the match the run then prints (the
     review computed `2 finding(s), digest 518b39136d6f`); the unit tests that name the
     Wizer pin follow;
   - the runner checks name the stdlib zip from `MANIFEST`'s `python` line;
   - the oracle (the native run that writes the goldens) unpacks its own copy of the pinned
     host-Python archive under `build/oracle/python/`, after checking its SHA-256 against
     `downloads/SHA256SUMS`, and runs on it (`UV_PYTHON`, `UV_PYTHON_PREFERENCE=only-system`),
     because the pinned uv 0.9.22 cannot install 3.15.0. It shares no directory with the
     build. Its `requires-python` is `==3.15.0`, its `uv.lock` is regenerated, and it runs on
     arm64 macOS only, as the build does (the lock has no manylinux wheels for cp315 numpy and
     pandas). The goldens are regenerated; only their version line changes (the research
     memo, finding 6);
   - a new v1.1 check, `test_exceptions_are_the_standard_form`, on `python.wasm` and the
     snapshot: each has a tag section (`tests/harness/wasm.py` records section 13, beside
     reading `0x69`), passes `wasmtime.Module.validate` on an engine with exceptions on, and
     fails it with exceptions off. It proves the binaries are standard-form EH. It does not
     prove every object was compiled with the flags: a C++ file compiled without
     `-fwasm-exceptions` but linked with it still passes, and its `throw` is never caught
     (EXECUTED by the review's confirmation). A dropped `-wasm-use-legacy-eh=false` already
     fails the build at step 80, and a dropped link flag fails the link;
   - so a new v1.5 check, `test_cpp_is_compiled_with_exceptions`, scans the build recipe:
     both cross files' `cpp_args` carry `-fwasm-exceptions` and `-wasm-use-legacy-eh=false`,
     and step 60 links with `-lunwind` and passes `LDFLAGS_NODIST="-fwasm-exceptions"`;
   - a new v1.3 check, `test_a_cpp_exception_reaches_python`, on the snapshot through the
     runner: `np.fft.fft` of 12,000,001 zeros under a 560 MiB memory cap must raise a bare
     `MemoryError()` (no arguments: numpy's own array-allocation error carries a shape and a
     dtype, and comes before any C++), and a small FFT must then still work in the same
     program. Its fuel is recorded (the review measured 440,742,195 on the snapshot).
10. **Growth.** Every metric that grows is listed in the landing notes with its measured cause.
    The causes known now: 3.15's own stdlib costs more to import (EXECUTED, the plain reactor:
    `import socket` 293M to 334M, `import pdb` 1,090M to 1,281M, `import traceback` 577M to
    440M, which shrank), and 3.15's zip is larger (+6%). Growth without a measured cause is a
    regression (constitution §3) and is investigated before landing.
11. **The release** is the next alpha, `0.1.0a2`. Its `CHANGELOG.md` section names the line
    change, the exception fix, the requirement on hosts, and that the stdlib zip's guest name
    is now `/usr/local/lib/python315.zip` (an embedder laying out the root by hand must
    follow it).

## Intent

The project's line becomes the one matplotlib can be built on, and a C++ error inside numpy
becomes a Python exception instead of the end of the program.

## Design

```
scripts/line.conf      PYTHON_VERSION=3.15.0  WASI_SDK_VERSION=33 …   (the one place)
scripts/line.py        line.conf for the Python scripts
scripts/steps/*.sh     . common.sh, which sources line.conf and derives PYTHON_MM, PYTHON_TAG
recipes/*.cross        @SDK@ and the exception flags
recipes/cxa_stubs.c    deleted
recipes/reactor_main.c PREIMPORT gains _colorize
tests/harness/wasm.py  exnref
tests/harness/jobs.py  the oracle on its own verified copy of the pinned host 3.15.0
tests/jobs/            goldens regenerated
```

## Scope

In: the above. Out: matplotlib and its libraries (their own specifications); the lean exit
(its research memo awaits the owner); Linux pins.

## Acceptance criteria

1. The third research memo is executed and confirms that C++ exceptions need the proposal on
   WASI; otherwise this specification goes back to the owner. (Met, 2026-10-16: executed, and
   it confirms.)
2. From an empty `build/` (oracle kept), `scripts/build.sh` passes; steps 60 to 90 again give
   the same reactor, snapshot and zip.
3. `uv run pytest` is green against the 3.15 set, with the new check passing and every grown
   metric's cause in the landing notes.
4. `git grep -n -E "3\.14\.8|cp314|wasi-sdk-24|wizer-v11|python314\.zip"` finds nothing in
   `scripts/`, `recipes/`, `src/`, `.github/` or `tests/checks/`, nor in `downloads/` except
   Brett Cannon's research pin (`python-3.14.7-wasi_sdk-24.zip`); `tests/unit/` keeps 3.14
   names only as fixtures of parsing tests.
5. A dry run of the release workflow passes every job.

## Landing notes

Built 2026-10-17 by the author agent (commit `34952cf`). Reviewed after build in
`../reviews/005-the-3-15-line-2026-10-17.md` (its findings are answered there); the dry run is
below.

**The build** (EXECUTED: `scripts/build.sh` from a `build/` holding only the oracle and Brett's
reference unpack; the 3.14 tree was moved aside):

```
ok 10_tools: tools: python 3.15.0, meson 1.12.1, ninja 1.13.2…, cython 3.3.0
ok 20_cpython: cpython: 29582988 bytes, 21b8f3fe46aa6f87
ok 30_zlib: zlib: 102842 bytes
ok 40_numpy: numpy: 19 extension archives
ok 50_pandas: pandas: 45 extension archives
ok 60_link: reactor: 29801866 bytes, 856e08eb832d08f9
ok 70_zip: python-stdlib.zip: 1098 pyc, 653 data files, 11140659 bytes
ok 80_snapshot: snapshot: 63484356 bytes, 7d9836116aaecc1f
ok 90_artifacts: artifacts: 14 files in build/artifacts
```

Steps 60 to 90 run again gave the same three files (EXECUTED): reactor `856e08eb832d08f9…`,
snapshot `7d9836116aaecc1f…`, zip `e95b35dea78981e8…`. They differ from the experiment's
(`1522cd81…`, `9b10b259…`, `b10243c4…`) because the reactor now pre-imports `_colorize`, no
longer links `cxa_stubs.c`, and the recipe files the zip's bootstrap is frozen from changed.

**The goldens** (EXECUTED: `uv run python tests/jobs/regen.py --online` on the oracle's own
hash-checked 3.15.0): only each file's version line changed, `python=3.14` to `python=3.15`.

**The judge** (EXECUTED: `uv run pytest`): every check passes but the known gap, whose match is
now `2 finding(s), digest 518b39136d6f`, as the review computed. The three new checks pass;
`test_exceptions_are_the_standard_form` fails on the 0.1.0a1 binaries as it should (no tag
section; they validate with exceptions off). `test_a_cpp_exception_reaches_python` spends
440,862,415 instructions (the review measured 440,742,195 on its scratch build).

**Growth, with its measured causes** (EXECUTED: the judge's metrics against the 0.1.0a1 accepted
state; the probes are wasi_python.run with fuel on both artifact sets):

| metric | 3.14 | 3.15 | cause |
|---|---|---|---|
| snapshot `-c pass` and the 16 other snapshot runs | 117.6M to 118.5M | 124.2M to 125.6M (+5.5%) | 5.0M is finalization (`-c pass` minus the hard-exit path: 73.9M on 3.14, 78.9M on 3.15, for 581 and 583 modules), 1.5M comes before exit (hard exit 43.6M to 45.1M): CPython 3.15's own start and shutdown |
| plain uncaught error | 578.4M | 676.0M (+16.9%) | 3.15's traceback printing imports `pathlib`, `pathlib._os`, `ntpath`, `importlib.util` and `importlib._abc`, which 3.14's did not (EXECUTED: `sys.modules` before and after `sys.excepthook`) |
| plain `import socket` (`test_guest_has_no_network`) | 293.7M | 335.1M (+14.1%) | 3.15's `socket` module (Decision 10) |
| plain debugging tools (`pdb` and friends) | 552.4M | 577.4M (+4.5%) | 3.15's stdlib (Decision 10) |
| plain `import pandas` and the golden jobs | | +0.8% to +1.2% | 3.15's stdlib imports under pandas |
| plain `-c pass` and the nine other plain runs that do little else | 246.6M to 247.6M | +0.06% to +0.08% | 3.15's own start-up (plain `-c pass` 246.7M to 246.9M in the judge) |
| snapshot bytes | 62,317,581 | 63,484,356 (+1.9%) | 3.15's larger heap after the same pre-imports, plus `_colorize` (INFERRED: not measured by part) |
| stdlib zip bytes | 10,474,585 | 11,140,659 (+6.4%) | 3.15's stdlib is larger (Decision 10) |

Shrank: the reactor (29,829,406 to 29,801,866 bytes), plain `import traceback` (577M to 440M),
gzip (−2.7%).

**Criterion 4** (EXECUTED: the `git grep`): nothing in `scripts/`, `recipes/`, `src/`,
`.github/`, `tests/checks/` or `downloads/`; `tests/unit/` keeps 3.14 names only as fixtures of
parsing tests.

**`test_a_cpp_exception_reaches_python` and the cache** (the build review's finding 1,
EXECUTED by the author too): a module loaded from the runner's `.cwasm` cache counts a constant
fewer instructions than one compiled in the process (snapshot `-c pass` 81.8M against 124.1M;
plain 5M fewer), with the same output. The check passes `cache_dir=False`, so its figure does
not depend on the cache. The cause is open:
`../research/2026-10-17-fuel-depends-on-how-the-module-was-made.md`.

**The push before review** (the build review's finding 9): `34952cf` went to `origin/main` as a
draft before review, under the owner's instruction of 2026-10-16 ("You have full control to
push to git"); landing is the accepted state and the review, as for spec 004's drafts.

**Deviations from the design, both small:** the shell side reads `line.conf` through a third
file, `scripts/line.sh` (sourced by `steps/common.sh` and `python-wasi-cross`, which does not
source `common.sh`), so the grammar check lives in one place for the shell; and the `wheel` and
`three systems` needs now name spec 004 as their provider, since the README's Next list no
longer has the release workflow as an item.
