# 086 — The toolchain moves to wasi-sdk 34

- **Status:** **landed 2026-10-20 as wave 04, alone**, on main `085dba5`: accepted on `a75e5d4`, history line 85, 638/708 pass, 0 fail; the dry run 39369492451 dispatched as main moved (see "Landed in wave 04" below). Before: **rebased onto main `f7511b7` (wave 03 landed) and ready to land as wave 04, alone**, 2026-10-20. Rebuilt on `b0c7a74` (one `SHA256SUMS`, `4e0dc0cf…`, from macOS and linux/arm64; wave 03 changed no build input, and step 90 on `f7511b7` gives the same). The delta review (`../reviews/086-the-toolchain-moves-to-wasi-sdk-34-delta-2026-10-20.md`, in the lane's scratchpad) said "lands once M1": M1 and L2 are done ("Rebased onto b0c7a74"). Branch dry run 39364304770 read: every red line is GREW or 084's two Windows rows that 094 fixed. Before that: rebased onto `e8ba20a` with the 0.1.0 security review's S5 and the zip's `_missing_stdlib_info` folded in, the A/B on 078's base (`97be88a`). Before: **built 2026-10-19** on main `3866f56` (the Landing notes); **build review** (`../reviews/086-the-toolchain-moves-to-wasi-sdk-34-build-2026-10-19.md`, in the lane's scratchpad): "lands once the A/B is done on 083's base and B1 is run and written in"; B1 to B3 and N1 are done ("Disposition of the build review"): every criterion but Decision 9's A/B, which is measured once 083 has landed (the lane's instruction), and the dry run, which follows the landing. **Confirmed for build** at `663bc15` (the review's addendum, "ready to build"). Before that: drafted 2026-10-19 on `spec/086-wasi-sdk-34` from main `932bc00`, rebased onto main `3866f56` (the owner's answer to question 105). **Revised 2026-10-19 against its pre-build review** (`../reviews/086-the-toolchain-moves-to-wasi-sdk-34-spec-2026-10-19.md`, written in the lane's scratchpad with its probes, copied by the lane; verdict "ready once F1 to F5 are written in"): F1 to F5 are written in as the lane ruled, F6 to F10 are fixed, and "Disposition of the pre-build review" at the end says where. It changes the build recipe and every byte of the artifact set, so it is reviewed once before it is built (constitution §5.6). It changes neither the guest's imports nor its exports (EXECUTED, the trial below). The drafter ran the whole move once in a throwaway copy, so most facts here are EXECUTED; the section "The trial" says how.
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** **build-class** (§5.7): it changes `scripts/`, `recipes/` and `downloads/SHA256SUMS`.
  - **Changed:**
    - `scripts/line.conf`: `WASI_SDK_VERSION=34`, the six SDK folder names, `WASI_LIBC_COMMIT=2e6fb9d8`, `LLVM_COMMIT=895aa2c8`;
    - `scripts/00_download.sh`: the five wasi-sdk URLs and names, the ten licence-notice URLs and names, and the comment that names the versions;
    - `downloads/SHA256SUMS`: 15 lines out, 15 in (Decision 1);
    - `scripts/steps/10_tools.sh` and `scripts/steps/60_link.sh`: the sysroot and builtins tarball names lose `+m` (Decision 2);
    - `scripts/steps/60_link.sh`: one more `--wrap` flag and one more file in the guard compile (Decision 5);
    - comments that name wasi-sdk 33: `recipes/wasi-numpy.cross:30`, `recipes/wasi-pandas.cross:30`, `recipes/iconv_refusals.c:3`, and the libxml2 patch's facts sheet, whose reason changes (Decision 4);
    - `README.md`, `CHANGELOG.md`, `context/roadmap.md`;
    - at the rebase (the owner's word, `../decisions.md`, 2026-10-19): `scripts/steps/20_cpython.sh` passes `--with-hash-algorithm=siphash13` (S5), `scripts/steps/70_zip.sh` copies `_missing_stdlib_info.py` (spec 078's build review, F2), `tests/cpython_configure.txt` gains `Py_HASH_ALGORITHM 3`, 078's class `no-missing-stdlib-info` is closed (`tests/upstream/python.toml`, its expected file, `tests/known_gaps.toml`, `tests/unit/test_regrtest.py`'s count).
  - **New:**
    - `recipes/fcntl_dup_refusal.c`: wasi-libc's `fcntl` answers the two dup commands as its `dup` does (Decision 5);
    - `tests/cpython_configure.txt`: every `#define` of the guest CPython's `pyconfig.h`, recorded (Decisions 6 and 7);
    - `tests/fixtures/try-table-order.ll`: the memo's reproducer, copied under the judge's paths (Decision 7, check (a));
    - three checks (Decision 7);
    - an evidence folder, `context/research/2026-10-19-the-toolchain-move-evidence/`, with a short memo: the surface probe (`surface_probe.py`) and its diff, the five `SHA256SUMS`, Decision 9's table, the other libraries' configure diffs, and the container runs (Decisions 6, 9 and 10, criteria 3 to 5), as spec 059 moved its evidence in (its Decision 10);
    - `context/upstream/25-wasi-libc-fcntl-dupfd/`: a facts sheet for wasi-libc (Decision 5; 23 and 24 are taken by 037's and 087's branches).
  - **Judge changes:** the three new checks, the recorded list and the fixture. No golden, allowance, class, trap entry or gap changes (Decision 8). So the lane accepts with `--accept-judge` (the new checks) and `--accept-growth` (Decision 9).
  - **Not changed:** `tests/public_api.txt` (no public name moves), `src/`, the release workflow, every carried patch.
- **Depends on:** 012 (the host-neutral sysroot and builtins), 040 and 059 (each host compiles with its own clang; `-ffp-contract=off` in `clang.cfg`), 063 and 065 (the shards and CPython's own tests); all landed. The owner's answers to questions 104 and 105 (`../decisions.md`, "105, and the open points of 078, 084 and 085, answered", 2026-10-19): **(b), the toolchain moves first**: 086 is built now, takes 037's build slot, lands before 037, and 037's same-bytes exception is withdrawn at 037's rebase and never landed. The roadmap says the same (`../roadmap.md`, "In flight").
- **Research it stands on:** `../research/2026-10-19-the-try-table-order-in-llvm.md` and its folder (the cause, the upstream fix, the reproducer); spec 037's branch memo `2026-10-19-ducc0-is-not-reproducible-with-the-pinned-clang.md` (the symptom); and this specification's trial (EXECUTED, below).

**A correction to the brief.** The brief that started this draft said the pin is wasi-sdk 32. It is wasi-sdk 33: `scripts/line.conf:7` says `WASI_SDK_VERSION=33`, and `downloads/SHA256SUMS` pins `wasi-sdk-33.0-*` with LLVM `4434dabb` (22.1.0) (READ). Everything below moves from 33 to 34.

## The problem

wasi-sdk 33's clang (LLVM 22.1.0) does not always compile the same source to the same object. Its WebAssembly backend nests `try_table` blocks in the order of a `DenseMap` keyed by block pointers (`WebAssemblyCFGStackify.cpp:1829`, iterated at 1972). Heap addresses decide that order, and address-space randomization moves them on every run. Today's set never hits it: every compile in it is reproducible. Spec 037's scipy does hit it: ducc0's FFT (`pyduccfft.cxx`) compiles to different bytes on every run. So 037 built a narrow same-bytes exception (its Decision 17).

The owner chose to remove the cause instead (question 105, (b)). LLVM fixed the map upstream in `fd76c9bd` (PR #205184, issue #204883), which is in LLVM 23.1.0 and in no 22.x release. wasi-sdk 34 ships LLVM 23.1.0. This specification moves the pin there, proves the move keeps every byte the same from every host, and leaves 037 to drop its exception at its rebase.

In one line: same source, same bytes, on every host, with no exception.

## The trial (EXECUTED)

The drafter ran the move once, before writing a decision, so that each decision rests on a run.

- **Where.** A plain copy of main `932bc00`, then a throwaway `git clone` of the worktree under its git-ignored `build/086-trial/`, with five files changed: `line.conf`, `00_download.sh`, `SHA256SUMS`, `10_tools.sh` and `60_link.sh` (the pins and the `+m` names, Decisions 1 and 2; not Decision 5's wrap). No branch file was edited. The containers are the research images of specs 040 and 059 (`wp040-arm64`, `wp040-amd64`), each cloning the clone and laying the five files over it. The large trees are deleted; the logs, the five `SHA256SUMS`, the judge records, both `pyconfig.h` files, the probes and the drafter's scripts are kept in the worktree's git-ignored `build/086-evidence/` (1.7 MB) for the reviewer.
- **Downloads.** Each tarball was fetched into its own new folder and hashed before use.
- **Runs.** `scripts/build.sh --plain` (macOS builds and container builds, below), then `uv run pytest -n 3` and the upstream suites on the clone's set.
- **Baseline.** Main's accepted set is 0.1.0a7's: `python.wasm` `ab78e893…`, the snapshot `c50ca51f…` (`context/progress/accepted.json`; the release tarball `fc59b977…`, downloaded and hashed, holds the same two files).

| Fact | Result | Label |
|---|---|---|
| The five wasi-sdk 34 tarballs | each SHA-256 equals the release page's digest (Decision 1) | EXECUTED |
| `VERSION` inside the SDKs and the sysroot | `34.0`, wasi-libc `2e6fb9d8ee0c`, llvm `895aa2c896ad`, llvm-version `23.1.0` | EXECUTED |
| clang | `clang version 23.1.0-wasi-sdk (… 895aa2c896ada719451be2e3673c83da8ddf1141)` | EXECUTED |
| `fd76c9bd` in the SDK's LLVM | an ancestor of `895aa2c8` (GitHub compare: `ahead`, behind 0); `895aa2c8` is 28 commits before the `llvmorg-23.1.0` tag | READ |
| Step 10 on the 34 SDK | passes: one `lib/clang/23`, `bin/clang.cfg` and `clang++.cfg` present, the `-ffp-contract=off` gate holds for both drivers | EXECUTED |
| Every step, 00 to 90 | passes with no recipe change but the pins and the `+m` names | EXECUTED |
| Carried patches | all seven apply (the steps that carry them ran `apply_patches.sh`) | EXECUTED |
| `python.wasm` | 41,099,661 → 41,167,051 bytes (+67,390; +0.164%); `2e627c87…` | EXECUTED |
| the snapshot | 44,633,983 → 44,695,700 (+61,717; +0.138%); `259c11dd…` | EXECUTED |
| the zip | 22,197,173 → 22,197,155 (−18; `_sysconfigdata` records new configure results) | EXECUTED |
| sections of `python.wasm` | code +45,304, name +17,763, data +4,256, function +74, element −7; 69 more function bodies (40,577 → 40,646); `type`, `import`, `export`, `target_features` and `producers` the same size | EXECUTED |
| imports | the same 43, from `host` and `wasi_snapshot_preview1` only | EXECUTED |
| the reduced reproducer, wasi-sdk 33 clang | 64 runs, two objects (19 and 45) | EXECUTED |
| the reduced reproducer, wasi-sdk 34 clang | 64 runs, one object (`4e0dd4cb…`, one of 33's two) | EXECUTED |
| macOS, two builds in the clone | the same `SHA256SUMS`, byte for byte (`0083fcef…`); a third build, in the plain copy, gave the same three artifacts (its `MANIFEST` lacked the recipe lines a copy without git cannot list) | EXECUTED |
| linux/arm64 container, two builds | `SHA256SUMS` byte for byte the macOS clone build's (`0083fcef…`), both times | EXECUTED |
| linux/amd64 container (Rosetta), one build, its own x86_64 clang | the same `SHA256SUMS` (`0083fcef…`): wasi-sdk 34's x86_64 and aarch64 Linux clangs agree under `-ffp-contract=off`, as 33's did (spec 059) | EXECUTED |
| the full judge, `-n 3` | 0 fail, lost 0, grew 59, with numpy's and pandas' groups blocked (no upstream kit yet); the five CPython groups pass with their allowances unchanged | EXECUTED |
| the upstream suites, kit fetched (`tests/upstream/fetch.py`), run alone | pandas' eight groups and numpy's other two pass; **numpy-core fails**: eight tests that fail with `Errno 58` now fail with `Errno 28` (Decision 5); its counts and digest are unchanged (9,519 passed, `df21e78e7032`) | EXECUTED |
| Decision 5's refusal, trialled (appended to the guard's unit in the clone, `-Wl,--wrap=fcntl`, relinked from step 60) | `os.dup(1)` raises errno 58 again; numpy-core passes, its classes matching; the fast tier: 0 fail, lost 0; `python.wasm` +117 bytes over the trial set. The trialled wrapper read its argument for every command; the design reads it only where one is passed (Decision 5, the review's F8) | EXECUTED |
| numpy's and pandas' fuel | **numpy-core +2.645%** (203.36 G → 208.73 G, on the set with the refusal); the other ten groups from −0.194% (pandas-io-parser) to +0.053% (pandas-groupby) | EXECUTED |
| numpy-core's rise, probed (time box 15 min) | the same workloads on 0.1.0a7's set and the trial set move under 0.6% each: libm calls −0.27%, sorts +0.18%, float formatting −0.08%, copies −0.17%, `np.char` +0.38%, `long double` arithmetic −0.12% and formatting −0.52%; the rise is **not traced** (Decision 9) | EXECUTED |
| fuel, every row the full judge compared (numpy's and pandas' groups not among them) | 153 rows: 57 up and 96 down by more than 0.01%; from −0.444% to +1.428%; the sum 1,421.60 G → 1,422.73 G (+0.08%) | EXECUTED |
| new warnings | 4,216 `-Wunused-template`, about 4,190 of them HarfBuzz's (step 37); no other class moved; no step builds with `-Werror` | EXECUTED |

The fuel rows that moved most: the compress job +1.428% (3.919 G → 3.975 G), `cpython-archives` +0.537%, the door round trip on the snapshot +0.621% (16.1 M), `cpython-fs` +0.434%; and down, lxml's encodings workaround −0.444%, `np.frompyfunc` recursion −0.393%, `test_nothing_is_a_shared_library` −0.365%. Every recursion floor of `test_v1_2_hostile_guest.py` held on darwin-arm64, and so did `test_the_c_stack_window_is_128_kib` ("used 112 kB").

## Decisions

1. **The pins.** wasi-sdk 34 (`wasi-sdk-34`, published 2026-08-25). Each tarball's SHA-256 was computed here from the downloaded file and equals the release page's digest (EXECUTED):

   | File | SHA-256 | Bytes |
   |---|---|---|
   | `wasi-sdk-34.0-arm64-macos.tar.gz` | `9c59398106b417f8f14913380fdf0097a8cc0ff4af9eb3ce0065a859e88d49e9` | 180,322,002 |
   | `wasi-sdk-34.0-arm64-linux.tar.gz` | `f7e243dff54d60bcc576e94d6166b69f410f2500ae4a9ceef34315be10e77971` | 192,255,247 |
   | `wasi-sdk-34.0-x86_64-linux.tar.gz` | `b761e3a0721dbae9c09a0059e5fdb2bf917d1b4a8a7b430fb3b5aafb0984b2c4` | 192,383,077 |
   | `wasi-sysroot-34.0.tar.gz` | `9d813544eeebe38b7b8f2244ed591de46b6db812c6dd1a257ff9f0d2a905a2be` | 119,283,116 |
   | `libclang_rt-34.0.tar.gz` | `eee3e634dcf71aa22b1333391623cf5c9965a637dc428a27b1a858c026c587f1` | 774,215 |

   The URLs are `https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-34/<file>`. The arm64 Linux tarball is also the x86_64 host's fallback compiler (spec 040), still switched off; its `get` line inside the fallback branch moves with the others.

   The licence notices move to the commits the SDK's `VERSION` names: wasi-libc `2e6fb9d8ee0cdf9e431fbcabe8af3115de000a13` and LLVM `895aa2c896ada719451be2e3673c83da8ddf1141` (full hashes READ from GitHub's commits API). Each was fetched and hashed (EXECUTED):

   | File | SHA-256 |
   |---|---|
   | `wasi-libc-2e6fb9d8-LICENSE` | `2711a8b5a5cdfef0e639f96c1aca12ae23d7d64a02d0507f1bdf14d2b27bbc3a` |
   | `wasi-libc-2e6fb9d8-LICENSE-APACHE` | `a60eea817514531668d7e00765731449fe14d059d3249e0bc93b36de45f759f2` |
   | `wasi-libc-2e6fb9d8-LICENSE-APACHE-LLVM` | `268872b9816f90fd8e85db5a28d33f8150ebb8dd016653fb39ef1f94f2686bc5` |
   | `wasi-libc-2e6fb9d8-LICENSE-MIT` | `23f18e03dc49df91622fe2a76176497404e46ced8a715d9d2b67a7446571cca3` |
   | `wasi-libc-2e6fb9d8-musl-COPYRIGHT` | `b870108ec5e7790e9f9919064f1b9421d62d5f9b0e6c230c6adf7ea2da62e97b` |
   | `wasi-libc-2e6fb9d8-cloudlibc-LICENSE` | `c8b789cf5a746611e6300a0cc7750dbf92b61912a709d04e639245f7290656d0` |
   | `llvm-895aa2c8-libcxx-LICENSE.TXT` | `539dd7aed86e8a4f12cbdd0e6c50c189c7d74847e4fecc64ce2c6ee3a01da38b` |
   | `llvm-895aa2c8-libcxxabi-LICENSE.TXT` | `e2b35be49f7284a45b7baca8fc7b3ab7440e7902392b2528a457816b5bb2a15c` |
   | `llvm-895aa2c8-libunwind-LICENSE.TXT` | `b5efebcaca80879234098e52d1725e6d9eb8fb96a19fce625d39184b705f7b6d` |
   | `llvm-895aa2c8-compiler-rt-LICENSE.TXT` | `1a8f1058753f1ba890de984e48f0242a3a5c29a6a8f2ed9fd813f36985387e8d` |

   Nine are the same bytes as 33's. musl's `COPYRIGHT` changed: one contributor's name (EXECUTED, `diff`). The set's `LICENSES/wasi-libc.txt` and `LICENSES/llvm-runtimes.txt` change with them (EXECUTED: the trial set's lines differ from a 33 set's).

   **Why 34 and not a patched 33.** The memo's route 2 (build LLVM ourselves with `fd76c9bd`) would pin a toolchain we built for three hosts and open ground §4.1 does not cover (patches are to sources). Route 1 costs one pin move and fixes the cause. There is no newer release: 34 is the newest wasi-sdk (READ, the releases list).

2. **The two neutral tarballs lose `+m`.** 33 named them `wasi-sysroot-33.0+m.tar.gz` and `libclang_rt-33.0+m.tar.gz`; 34 names them `wasi-sysroot-34.0.tar.gz` and `libclang_rt-34.0.tar.gz` (READ, the release assets). `10_tools.sh:14-15` and `60_link.sh:141` build the name from `$WASI_SDK_VERSION`; the `+m` is dropped there, and the names stay derived from the line, as now. The trial made exactly this change and step 60's neutral-runtime check passed (EXECUTED).

3. **What else moves with the compiler, and what does not.**
   - **The sysroot.** wasi-libc moves 67 commits, `161b3195` → `2e6fb9d8` (READ, GitHub compare). It takes musl 1.2.6 and a set of WASIp3 and cooperative-threads work. For `wasm32-wasip1` the file list is the same but for one header (`__errno.h` is gone) and the `llvm-lto/22.1.0-wasi-sdk` folder renamed `23.1.0-wasi-sdk`; 34 drops the `wasm32-wasi` and `wasm32-wasi-threads` folders and adds `wasm32-wasip3` and `experimental-coop-threads` (EXECUTED, the two sysroots' lists compared). Nineteen `wasm32-wasip1` headers changed. The ones that reach our build: `unistd.h` now declares `pipe`, `dup`, `dup2` and `dup3`; `__header_fcntl.h` defines `F_DUPFD`, `F_DUPFD_CLOEXEC`, `F_GETLK`, `F_SETLK`, `F_SETLKW` and the lock types; `limits.h` defines `PIPE_BUF`; `bits/stdint.h` makes `int_fast16_t` 32 bits wide (it was 16) (EXECUTED, `diff -r`). And `libc.a` defines 48 more symbols, among them `dup`, `dup2`, `dup3`, `pipe`, `pipe2`, `ppoll`, `pthread_getcpuclockid` and the `sem_*` family (EXECUTED, `llvm-nm --defined-only`). Decisions 5 and 6 take what this does to CPython.
   - **libc++, libc++abi, libunwind** move to 23.1.0, with wasi-sdk's three carried LLVM patches, which touch only `libunwind/src/config.h`, libc++abi's thread-atexit and one libc++ locale header (READ, `src/llvm-pr-*.patch` at the `wasi-sdk-34` tag). The libc++ ABI tag in mangled names follows the version (the memo, READ). No recipe, script or check names a mangled C++ symbol (READ, the inventory below), so nothing here breaks on it. Spec 037's exception files do (`std::__2::make_shared[abi:nqe220100]`), and they are deleted at its rebase.
   - **compiler-rt's builtins**: the same layout (`wasm32-unknown-wasip1/libclang_rt.builtins.a`), new bytes (EXECUTED, the tarball's list).
   - **Target features.** The predefined `__wasm_*` macros are the same (the memo, EXECUTED), and the trial's `target_features` section is the same size; step 60's whole-list check (`tests/harness/constructors.py`, `FEATURES`) passed (EXECUTED). wasmtime 49 needs nothing new.
   - **The reviewed constructor list** (`constructors.py:32-46`, compared whole, in order) passed unchanged on today's set (EXECUTED). A package that brings new C++ (043's contourpy, 037's scipy) is re-checked at its own rebase (Decision 10).
   - **Warnings.** Clang 23 adds `-Wunused-template`: 4,216 warnings in the trial, about 4,190 of them HarfBuzz's in step 37 (14 there with 33, 4,204 with 34), and +14 in numpy, +12 in matplotlib. No other warning class moved; step 53 (regex) prints 0 warnings, as spec 087 cites (EXECUTED, the step logs against spec 043's 33 logs). No build uses `-Werror`: HarfBuzz's error pragma is off by `-DHB_NO_PRAGMA_GCC_DIAGNOSTIC_ERROR`, 043's contourpy builds with `-Dwerror=false`, and 037's scipy has no `-Werror` (READ). The warnings change no byte. They are not silenced: a `-Wno-` flag is a recipe line with no product effect.
   - **GB18030 is still wrong in musl 1.2.6.** wasi-libc 34's `src/locale/iconv.c` is byte for byte musl 1.2.6's (`84bdddca…`), not the fixed one (`67219f0`, `7038e7f5…`) (EXECUTED, fetched and hashed). So `recipes/iconv_refusals.c` and its three wraps stay; only its comment's "wasi-sdk 33" becomes "34".
   - **The other wraps still resolve.** The `__wasi_*` calls `reactor_main.c` wraps and `__wasilibc_reset_preopens` are referenced and defined as in 33 (READ, the inventory), and the reactor linked and passed the judge (EXECUTED).
   - **CPython's driver** reads `Platforms/WASI/config.toml`'s `wasi-sdk = 33` and only logs a warning on 34 (READ, `_build.py:262-273`); the build does not stop.

   **Every recipe and patch, against the move** (READ, then EXECUTED by the trial build):

   | File | What could move | Outcome |
   |---|---|---|
   | `line.conf`, `00_download.sh`, `SHA256SUMS` | the pins | Decision 1 |
   | `10_tools.sh`, `60_link.sh` | `+m` names; one `lib/clang/*`; `clang.cfg`; builtins path | Decision 2; the rest holds |
   | `60_link.sh` link flags (`-lc++ -lc++abi -lunwind -lsetjmp`), neutral-runtime check | libc++ 23 | holds |
   | `assemble_artifacts.py` | notice names from the line | follows Decision 1 |
   | `iconv_refusals.c` and its wraps | musl's decoder | stays (above) |
   | `fcntl_dup_refusal.c` and its wrap (new here) | wasi-libc's `fcntl` on preview1 | added (Decision 5); the next toolchain move checks it here |
   | `reactor_main.c` (`__wasi_*` wraps, `<wasi/libc.h>`) | wasi-libc | holds |
   | `hostmodule.c` | none | holds |
   | `npy_rename.h`, `pandas_rename.h`, `npy_random_legacy_rename.h` | wasm32 `long`, wasm-ld warnings | holds |
   | `wasi-numpy.cross`, `wasi-pandas.cross`, `wasi-plot-libs.cross`, `wasi-matplotlib.cross` | `@SDK@` tools, EH flags | hold; two comments name 33 |
   | `ctypes_stand_in/` | type sizes (`int_fast16_t` is not among them) | holds |
   | `clang-emulated` (fallback, off) | driver behaviour | unchanged; its gate runs only when switched on |
   | `patches/libxml2-2.15.4/0001-xmlio-without-dup-on-wasi.patch` | `dup` now declared | applies and is still needed (`dup` is an `ENOTSUP` stub); its stated reason changes (Decision 4) |
   | `patches/numpy-2.5.2/0001-npy-files-without-dup.patch` | `os.dup`'s errno | holds with Decision 5 |
   | `patches/numpy-2.5.2/0002`, `kiwisolver/0001`, `pillow/0001`, `regex/0001` (signatures) | none | apply; spec 051's scan reruns |
   | `patches/matplotlib-3.11.2/0001-ft2font-enums-without-python.patch` | the constructor list | applies; the list holds |
   | Python-only recipes (`mmap_stub.py`, stand-ins, `zip_*.py`, `reactor_bootstrap.py`, `guest/`) | none | hold |

4. **The libxml2 patch keeps its code and changes its reason.** Its facts sheet (`context/upstream/patches/libxml2-2.15.4/0001-*.md:6`) says clang stops on `xmlIO.c` because wasi-libc declares no `dup`. With 34 it declares one, so that is no longer why. The patch is still needed: `dup` on preview1 returns `ENOTSUP` (READ, `libc-bottom-half/sources/dup.c` at `2e6fb9d8`), so xmlIO's duplicate-then-close path would fail at run time instead of at compile time. The patch file does not change, so its `MANIFEST` hash does not either; only the sheet's reason ("`dup` always fails on WASI preview1") changes.

5. **`os.dup` keeps its error: a link-time refusal of fcntl's two dup commands.**
   - **What moved** (EXECUTED, the trial guest): `os.dup(1)` raises `OSError: [Errno 28] Invalid argument`; with 33 it raised `[Errno 58] Not supported`. numpy-core's eight `tofile`/`fromfile` tests therefore fail with a message its `no-dup` class does not match, and the group turns red (its pass count and digest unchanged: 9,519 passed, `df21e78e7032`).
   - **Why** (READ): CPython's `_Py_dup` (`Python/fileutils.c`) uses `fcntl(fd, F_DUPFD_CLOEXEC, 0)` whenever `<fcntl.h>` defines `F_DUPFD_CLOEXEC`, before it looks at `HAVE_DUP`. 34's header defines it. But wasi-libc's `fcntl` compiles its `F_DUPFD` and `F_DUPFD_CLOEXEC` cases out on `__wasip1__`, so they fall to `default: errno = EINVAL` (`libc-bottom-half/cloudlibc/src/libc/fcntl/fcntl.c:92-110` at `2e6fb9d8`), while its own `dup` returns `ENOTSUP` on preview1. The header and the function disagree. No configure variable reaches it: it is a header macro.
   - **The decision**, trialled (EXECUTED, above). A recipe, as `iconv_refusals.c` is (spec 046, Decision 9): `recipes/fcntl_dup_refusal.c`, compiled into the reactor's link by step 60 beside that file, with `-Wl,--wrap=fcntl`. `__wrap_fcntl(fd, cmd, ...)` is one `switch`:
     - `F_DUPFD` and `F_DUPFD_CLOEXEC`: `errno = ENOTSUP`, return −1, as wasi-libc's `dup` does;
     - the commands that take no argument (`F_GETFD`, `F_GETFL`, and any other without one): `__real_fcntl(fd, cmd)`, with no `va_arg`. wasm32 clang passes a null vararg buffer for a call with no variadic arguments, so reading one would read linear memory at 0 (the review's F8, EXECUTED there);
     - the commands that take one: `F_SETFD` and `F_SETFL` read an `int`, `F_GETLK`, `F_SETLK` and `F_SETLKW` a pointer, each with `va_arg` and passed on unchanged; an unknown command is passed on with no argument, and wasi-libc answers it `EINVAL` as before. It changes no upstream source.
   - **Step 60's guard compile becomes two.** Today one `sed` turns the reactor's compile command into `iconv_refusals.o` (`60_link.sh:114`). It becomes a loop over the two recipe files, each to its own object, both added to the link, and a failed compile names its file (`recipes/fcntl_dup_refusal.c did not compile`).
   - **What removes it.** Its header comment names the facts sheet and says to remove it, with its wrap flag, when a wasi-sdk release's `fcntl` returns `ENOTSUP` for these commands on preview1. No check turns red that day: with upstream fixed, check (b) passes with or without the refusal (the review's F6). The signals are the facts sheet's answer and the next toolchain move's recipe table, which names this file as Decision 3's table does.
   - **Why not accept `EINVAL`.** It would be a judge change (numpy's `no-dup` class and its gap, which match `Errno 58`) that makes the guest's answer worse: "Invalid argument" tells a program its call was wrong, when the platform cannot do it. A toolchain move should change bytes, not what a program sees. The refusal is one small file, the pattern this project already carries, and it goes when upstream fixes the mismatch.
   - **Upstream.** A facts sheet, `context/upstream/25-wasi-libc-fcntl-dupfd/` (facts and a one-line fix: return `ENOTSUP` for `F_DUPFD`/`F_DUPFD_CLOEXEC` on `__wasip1__`, as for `F_GETLK`), drafted for the owner to send, as spec 046 did for GB18030.

6. **The guest's other configure results: accepted, recorded and documented.** wasi-libc 34 flips ten of CPython's configure results (EXECUTED, the trial's `pyconfig.h` against spec 043's 33 one): `HAVE_DUP`, `HAVE_DUP2`, `HAVE_DUP3`, `HAVE_GETC_UNLOCKED`, `HAVE_PIPE2`, `HAVE_PPOLL`, `HAVE_PTHREAD_GETCPUCLOCKID`, `HAVE_SEM_GETVALUE`, `HAVE_SEM_OPEN`, `HAVE_SEM_TIMEDWAIT`. CPython's own `config.site` forces only `pipe` off (READ). What a program sees (EXECUTED, the trial guest):
   - `os.dup2`, `os.pipe2` and `time.pthread_getcpuclockid` now exist, and each raises `OSError: [Errno 58] Not supported`. `os.pipe` stays absent.
   - `select.PIPE_BUF` (4096) now exists: `limits.h` defines `PIPE_BUF`, and `selectmodule.c` exports it under `#ifdef PIPE_BUF` (the review's F2, READ and EXECUTED on the sysroot). A constant; nothing reads it without a pipe, and `os.pipe` is absent.
   - `sysconfig.get_config_vars()` shows the ten flipped `HAVE_*` (the zip's −18 bytes).
   - `select.poll` works as before, now through `ppoll` (a registered stdout polls writable).
   - `getc_unlocked` and `flockfile` are real functions in a single-threaded libc; `fileobject.c` uses them.
   - The semaphore results change nothing: `_multiprocessing` is not built, and CPython uses semaphores only when `_POSIX_SEMAPHORES` is defined, which 34's `unistd.h` does only for cooperative threads (READ, `pycore_semaphore.h:25-29`, `unistd.h`).

   **Why accept rather than pin them back.** Pinning needs cache variables on the host configure only (never the build-Python's), which means splitting step 20's one driver call into four, and it still cannot hold `os.dup2` out: CPython defines it when `F_DUPFD` is defined (READ, `posixmodule.c`), and keeping it out would take `#undef`s forced into every CPython compile. And with `HAVE_DUP2` forced off, `configure` compiles CPython's own `Python/dup2.c`, whose `dup2` clashes with wasi-libc's whenever its `dup.o` is linked. Every new function fails with `ENOTSUP`, so none is silently wrong and none opens a channel (constitution §4.15 holds); all five CPython groups and pandas' eight pass with their allowances unchanged (EXECUTED). So the smallest true thing is to accept them, say so in the README's platform facts, and record them.

   **The whole surface is compared, not assumed.** `surface_probe.py` (the evidence folder) runs in both binaries of main's set and of 086's set, on one machine. It writes `sorted(dir(m))` for every module in `sys.builtin_module_names` and every compiled extension module in the zip, and `sysconfig.get_config_vars()`. The diff is the accepted list: the three functions, `select.PIPE_BUF`, and the ten `HAVE_*` config variables. Any other difference stops the build until it is traced and either accepted here, with the README's platform facts, or fixed (criterion 4).

   **The other libraries probe libc too** (the review's F9). libxml2, libxslt and xz configure with autoconf; numpy, pandas, FreeType, HarfBuzz and matplotlib with meson. The builder diffs each generated config header between a 33 tree (spec 043's worktree, read only) and the 34 tree: `libxml2-build/config.h`, `libxslt-build/config.h`, the xz and other autoconf `config.h` files, numpy's `_numpyconfig.h` and meson `config.h` files, pandas', FreeType's and HarfBuzz's. Each flip is recorded in the evidence folder and treated as this decision treats CPython's: traced to what a program sees, then accepted and documented, or held back by a recipe if it is wrong.

   **Recorded.** `tests/cpython_configure.txt` lists every `#define` line of the guest's `pyconfig.h`, name and value, sorted (the review's F10: the non-`HAVE_*` lines are the same on 33 and 34 today, EXECUTED there, and recording them too catches a later `SIZEOF_*` or `ALIGNOF_*` move at no cost). Decision 7's check (c) reads the build's `pyconfig.h` and names each line that differs. A later toolchain move that flips a result then fails a check, and its specification states why, instead of the flip passing unseen.

7. **The checks, written first.** Each is seen failing on today's tree (wasi-sdk 33) or against a planted input before the recipe changes, and the landing notes quote the failure.
   - **(a) `test_the_backend_orders_try_tables_alike`** (`tests/checks/test_v1_5_rebuild_from_pins.py`, need: `compile records`, from the fixed vocabulary, as `test_every_compile_contracts_nothing` uses). Its input is `tests/fixtures/try-table-order.ll`, a copy of the memo's reproducer under the judge's paths, whose SHA-256 the check names (`63a709ecfd611ccbe7d2beb4d5c5c2b85e450fa2217296d117957b398ee138a3`, EXECUTED), so an edit to it changes the judge hash. It compiles it 64 times with each `build/tools/wasi-sdk-*/bin/clang` (`--target=wasm32-wasip1 -O3 -fwasm-exceptions -mllvm -wasm-use-legacy-eh=false -c -Xclang -disable-llvm-passes`), and asserts one object. It **fails** if it finds no such clang, so it cannot pass with nothing compiled. It counts distinct hashes, never time. **Seen failing:** on 33 the trial's 64 runs gave two objects (19 and 45); a false pass on 33 needs all 64 runs to agree, about (45/64)^64 + (19/64)^64, under 10^-9. On 34, 64 runs gave one (EXECUTED). This is the memo's ducc0 case reduced to 30 lines, in the repository, so it guards 086 before scipy exists on main.
   - **(b) `test_dup_is_refused_as_not_supported`** (`tests/checks/test_v1_2_hostile_guest.py`, both binaries): `os.dup(1)`, `os.dup2(1, 5)`, `os.dup2(1, 5, inheritable=False)` (the `dup3` path), `os.pipe2(0)` and `time.pthread_getcpuclockid(threading.get_ident())` each raise `OSError` with `errno.ENOTSUP`, and `os.pipe` is absent (the review's F6). **Seen failing:** on the 34 set without Decision 5 (the trial's set), `os.dup` raises errno 28. On 33's set `os.dup2` is absent, so the check is written for 34; its first run is against the trial set.
   - **(c) `test_the_guests_configure_results_are_recorded`** (`tests/checks/test_v1_5_rebuild_from_pins.py`, need: compile records): the sorted `#define` lines of `build/Python-3.15.0/cross-build/wasm32-wasip1/pyconfig.h` equal `tests/cpython_configure.txt`; a difference names each line. **Seen failing:** the list written from 34's `pyconfig.h`, run against a 33 build tree, names the ten `HAVE_*` lines and no other.
   - The release shards: (a) and (c) go to the `build` shard, (b) with its file's shard (`tests/release_shards.toml`); `test_release_shards_cover_the_judge` holds that.

8. **The judge's other parts: what moves, and who re-measures it.**
   - **Goldens.** The `tests/jobs/*.expected` outputs are native, and the guest's matched them all on the trial set, `plot_line`'s RGBA hash and `PNG_SHA256` included (EXECUTED: the full judge, 0 fail). With `-ffp-contract=off` run-time arithmetic does not change; musl 1.2.6's libm could. If a golden or an upstream group moves on another host, spec 059's Decision 6 rule applies: trace it to the expression first; a traced libm or fold change is a judge change with its before and after values; anything untraced stops the build.
   - **Spec 065's nine trap entries** (`tests/upstream/python.toml:86-147`) depend on wasmtime's 512 KiB stack, spent by Cranelift's frames for each host. A new compiler changes the wasm, so Cranelift's frames move. An open entry accepts "the named trap or no trap", so a trap that goes away is not red, and a new trap in a group is. On darwin-arm64 the trial matched every entry; `c-stack-itertools-tee` did not trap there, as before (it traps on Linux x86-64 only) (EXECUTED). The Linux hosts are checked in the containers before landing (criterion 5), and again by the release dry run (criterion 7).
   - **Spec 071's window and its floors.** `C_STACK_WINDOW` (128 KiB, `reactor_main.c:154`) does not change. The depths under it are clang's frame layout. Each `RECURSIONS` floor is "measured depth less a tenth", so a depth that falls more than a tenth turns a check red. On darwin-arm64 every floor held and the window check still reads "used 112 kB" (EXECUTED). The x86-64 and Linux arm64 floors run in the containers before landing (criterion 5). A floor that fails is re-measured with spec 071's own script and reported, not lowered quietly: lowering one is a judge change with the measured depth.
   - **Spec 078** (parallel-safe, not landed) records depths and edges at 8 MiB that Cranelift's frames set (its Decision 11; it says "086 … re-measures Decision 11's edges", line 396). Whichever of 078 and 086 lands second re-runs 078's measurement script on its own set and updates 078's numbers in the landing notes. 078's wider C-stack window is a follow-up **after** 086 (the owner, question 105's entry, "078"; 078's lines 891-895), because its x86-64 numbers depend on these frames.
   - **README numbers.** The sizes (41.1 / 44.6 / 22.2 MB) become 41.2 / 44.7 / 22.2. The depth rows (`README.md:240-253`: "40 to 250 levels", expat ~95, freeing a list 2,000, `json.loads` 1,100, `repr` 1,800, a traceback ~2,700 frames, XPath 375, XSLT 480/470/670, C14N 1,500, RelaxNG 430, and the rest) are re-measured with the scripts that produced them on darwin-arm64; a row is changed only where the new value rounds differently. The fuel figures in the README (`:91`, `:863-864`) likewise.
   - **No allowance moves.** With Decision 5, numpy's `no-dup` classes match again, so no class, gap, trap entry, golden or `tests/upstream/*` allowance is edited. If the build finds one must move, it is a judge change, traced as above, and named in the landing notes.

9. **Fuel and bytes: measured, bounded, accepted with their causes.** Every fuel and byte metric moves. The ratchet's tolerance is 0.01% for fuel and zero for bytes (`scoreboard.py:31`, `:162-163`), so the run is red on growth until accepted.
   - **The measurement.** The builder runs the full judge (`uv run pytest -n 6`) on its set and writes a table of every fuel and byte metric against `accepted.json`: rows up, rows down, median, minimum, maximum, and the sum, per tier (the trial's figures are in "The trial"). For the bytes it writes the section sizes of `python.wasm` against the accepted one (the trial: code +45,304, name +17,763, data +4,256), and names the largest functions that grew, from the name section. Causes are labelled: the new libc functions and libc++ 23 (EXECUTED, the function count +69), the backend's choices (INFERRED).
   - **The A/B, on one machine.** A row's growth is 086's own only when it is measured as an A/B: main's set, rebuilt on the exact base 086 lands on, against 086's set, both judged by the same commit of the judge on the same machine. The table above is made against `accepted.json`; the bound below applies to the A/B delta, never to `accepted.json`'s figure alone, so a rebase onto 073 (or anything else that moves a group) cannot push a row over the bound for that specification's reasons (the review's F1).
   - **A layout control first.** Spec 073's build review (its delta-look addendum) MEASURED that numpy-core's fuel moves with memory layout: `test_strings.py::test_string_comparisons` converts lists of 32,768 bools, and numpy's `_global_pytype_to_type_dict` lookup is keyed by `bool`'s address, so +4.29 G of 073's +4.48 G came from `bool` moving 0x780 when the data segment changed size (073's first build gave −73.6 M). 086's data section grows 4,256 bytes (the trial), so the same mechanism is the first suspect for numpy-core's +2.645%. Before tracing any row the builder: prints `id(bool)` (and `id(True)`) in both sets; runs that test alone on both sets and compares its fuel; and, on one set, changes only the layout (an extra environment variable of a few KiB) and sees how far the group moves.
   - **The rule** (one rule, the lane's ruling on F1):
     - a row whose A/B rise is over 3% **stops the build**;
     - a row whose A/B rise is between 1% and 3% is **traced file by file**: the group's test files one at a time, with its own driver and stage, on both sets; then per test inside the file that carries it; numpy-core's `test_strings.py` first, by the control above;
     - if two attempts do not find the cause, AGENTS.md rule 7 applies: the builder records where it stood and why in the evidence memo and the landing notes, and the row is accepted with that record in its growth reason. The build moves on.
   - **The other bounds.** The build also stops if the sum of the judge's fuel rises more than 1% (the trial: +0.08%), if `python.wasm` or the snapshot grows more than 1% (the trial: +0.164% and +0.138%), or if the zip changes beyond `_sysconfigdata`. A traced cause that is the toolchain's own (a libm routine, a libc path, a backend choice, a layout shift) is accepted with its numbers; a cause in a recipe is fixed.
   - **What is never accepted.** A lost pass, a group whose pass count falls, a golden that moves untraced, a new import or export, a host whose `SHA256SUMS` differs. Each stops the build; after two failed attempts on one hypothesis the builder writes it down (AGENTS.md rule 7).
   - **The landing's flags** (the lane's): `--accept "<spec 086: wasi-sdk 34 (clang 23.1.0, wasi-libc 2e6fb9d8): every artifact's bytes move once>"`, `--accept-judge "<the three checks of Decision 7, tests/cpython_configure.txt and tests/fixtures/try-table-order.ll>"`, `--accept-growth "<the toolchain move, with the A/B table: N fuel rows up, M down, the range, the sum, the layout control, each 1 to 3% row's cause or rule 7's record; python.wasm +X bytes, code +C, name +N, data +D>"`.

10. **The order with the specifications in flight.** 086 takes 037's build slot once confirmed (question 105's entry); it is one build slot of four.
    - **Where 086 lands** (the lane's ruling on F4). When it is built and reviewed, after whatever is ahead of it in the lane: 083, 039, 073, 085 and 084 (`../roadmap.md`, "In flight"), and 043 too if 043 is ready first, since the packages come first. 037 rebases onto 086. Whichever of 086 and 043 lands second rebuilds with clang 23 for contourpy and qhull (the trigger below).
    - **The base Decision 9 is measured on** is the exact commit 086 lands on, after every landing that moved accepted fuel or bytes: build-class or parallel-safe. In particular 083 lands first and its driver change moves fuel, so 086's table and A/B are made after 083.
    - **At every rebase** 086 rebuilds from empty `downloads/` and `build/` on macOS and re-measures Decision 9's table. A rebase that changes 086's own recipe hunks gets a delta review (§5.7).
    - **The same-bytes trigger** (the lane's ruling on F3). Whenever code first compiled by clang 23 arrives at a rebase (043's contourpy and qhull, 087's patched regex, 073's `reactor_main.c`, anything build-class that brings new or changed compiled sources), the linux/arm64 container comparison is re-run alongside the macOS build: one container build from empty `downloads/` and `build/`, its `SHA256SUMS` equal to macOS's. At 086's rebase it is 086's duty; for a specification that lands after 086, it is that specification's, at its rebase onto 086. ducc0 showed that one file is enough to break the bytes.
    - **039** (tier A; build-class, pure Python, being landed): its pins sit beside 086's in `SHA256SUMS` and `00_download.sh` (text neighbours only). Its fuel bounds per zip member (`20_000_000 + 6_000*(members-1_758)`) are relative and are re-run, not restated.
    - **043** (matplotlib M2; build-class; adds contourpy's C++ with `-Dwerror=false` and a qhull patch): whichever lands second rebuilds with both. Its contourpy objects then compile with clang 23: the builder checks step 60's constructor list (043 adds `_GLOBAL__sub_I_*` names; clang can renumber `__cxx_global_var_init.N`) and the warnings (no `-Werror`, READ), and runs the same-bytes trigger's container comparison. Its recorded fuel and sizes are re-measured by the later one.
    - **073** (`run` keeps an unclosed file's bytes; build-class, `reactor_main.c` and `reactor_bootstrap.py`): no shared hunk. The later one rebuilds and re-measures 073's fuel table (the snapshot's start, about +28 M; check (b)'s ratio).
    - **085** (gather checks what it trusts; build-class only for `release.yml`): no shared file. It already writes question 105's answer in. G7 and its set hash stay exact, which 086 makes true for scipy too.
    - **083** (parallel-safe, lands next): judge only. Its checks compare two runs, so they hold. It lands before 086, so 086 is the later one: its fuel moves are in the base 086 measures on.
    - **084** (parallel-safe): directory depth, not stack depth; unaffected.
    - **078** (parallel-safe): Decision 8 above.
    - **087** (build-class; carries `recipes/patches/regex-2026.9.29/0002-timeout-ticks.patch` and a `MODIFIED` line in `assemble_artifacts.py`): no shared hunk. The later one rebuilds; 087's `python.wasm` bytes (+202), its fuel figures and its Decision 6 depth table (XPath and XSLT depths; 087 says 086 re-measures them, its lines 319 and 393) are re-measured on the later set, the x86-64 edge (its 4,800) in the linux/amd64 container (criterion 5). Its patch applies on clang 23 unchanged (it is C source; step 53 prints 0 warnings on 34, EXECUTED). The same-bytes trigger applies to its patched `_regex.c`.
    - **037** (scipy; built, waiting): **rebases onto 086 after 086 lands.** At that rebase it: deletes `recipes/same_bytes_exceptions.toml`, `scripts/same_bytes.py`, `scripts/compare_sets.py`, `tests/unit/test_same_bytes.py` and `tests/unit/fixtures/same_bytes_ducc0.json`; removes the `SAME_BYTES_RECIPE` reading and the `x-same-bytes-exception` line from `scripts/assemble_artifacts.py` (step 90 would crash on the missing file otherwise); restores main's `same-bytes` job in `release.yml` (`permissions: {}`, the `cmp` of every rebuild's `SHA256SUMS` and the wheel comparison) and main's rules in `tests/harness/scan.py` (`rebuild_gate_errors`, `JOB_PERMISSIONS["same-bytes"]`) and `tests/unit/test_scan.py`; removes the exception's README (four places) and CHANGELOG lines and its row in `context/upstream/README.md`; and turns `test_the_same_bytes_exception_is_still_needed` into its opposite: `pyduccfft.cxx`'s compile command run three times gives **one** hash. Its criterion 3 then holds as first written (one `SHA256SUMS` from every host, no exception); its OpenBLAS (3,782 compiles) and scipy (910) objects compile with clang 23 for the first time there, so 037 runs its own compile-twice comparison over all of them on macOS and in the linux/arm64 container, and the release dry run. Spec 037's Decision 17 amendment (its lines 735-748) already lists these removals.
    - **038, 044, 045** arrive after 037, built on 34 from the start.

11. **Documentation.** The README's reproducibility paragraph names wasi-sdk 34 and clang 23.1.0 and says every build host gives the same bytes with no exception. Its platform facts gain Decision 6's three attributes ("exist and raise `ENOTSUP`, as `os.dup` does") and `select.PIPE_BUF`, and whatever else the surface comparison lists. One line says the set is built with wasi-sdk 34 while CPython 3.15.0's WASI driver names 33, which it only warns about (the review's N2). `README.md:16` and the CHANGELOG's history keep their 33 sentences (history). The CHANGELOG's next alpha section says: the toolchain is wasi-sdk 34 (clang 23.1.0, wasi-libc `2e6fb9d8`, musl 1.2.6); every artifact's bytes changed; the new `fcntl` refusal and its upstream sheet; the three new functions and `select.PIPE_BUF`. The roadmap's reservation for 086 points here.

## Intent

Move the pinned toolchain from wasi-sdk 33 to wasi-sdk 34 so that the compiler gives the same bytes for the same source on every run and every host, scipy's ducc0 included, and so spec 037 needs no exception. Keep what a guest program sees the same, except three new functions that fail as `os.dup` already does and one new constant (`select.PIPE_BUF`), which are compared by script, recorded and documented. Measure every number that moves and accept it with its cause.

## Design

1. Change the pins (Decision 1) and the two `+m` names (Decision 2). Fix the comments that name 33 (Decision 3, Decision 4).
2. Write Decision 7's checks and the recorded list; see each fail as it says.
3. Add `recipes/fcntl_dup_refusal.c` and its wrap flag to step 60's guard compile (Decision 5); draft the facts sheet.
4. Build on macOS from empty `downloads/` and `build/`. Run the full judge. Write Decision 9's table and its A/B, after the layout control. Stop on its bound.
5. Compare the surface and the other libraries' configure headers (Decision 6).
6. Prove the bytes (criterion 3) and run the Linux floors and trap entries (criterion 5), then the README, the CHANGELOG, the evidence memo and the roadmap line.

## Scope

- **In:** the pins, the two names, the `fcntl` refusal, the recorded configure results, three checks and their fixture, the surface comparison, the Linux container runs before landing, the evidence memo, the README and CHANGELOG lines, re-measured numbers.
- **Out:**
  - **Removing spec 037's exception.** It is not on main; 037 does it at its rebase (Decision 10).
  - **The x86-64 fallback's removal.** `clang-emulated` stays switched off for one release, as spec 059 decided. Whether wasi-sdk 34's two clang builds agree without `-ffp-contract=off` is not asked here: the flag stays.
  - **Silencing `-Wunused-template`.**
  - **078's wider window**, after 086.
  - **GB18030.** Still musl 1.2.6's decoder.
  - **Wall-clock.** No check reads a clock (§4.9). The trial's build times (10 min 58 s, then 7 min 46 s on macOS; 6 min 23 s and 6 min 9 s in the arm64 container; 24 min 37 s in the amd64 container under Rosetta) are benchmark facts.

## Acceptance criteria

1. **Seen failing first**, each quoted in the landing notes: check (a) on today's tree gives two objects; check (a) with no clang under `build/tools/` fails, naming that; check (b) on the trial-like set (no refusal) names errno 28; check (c) against a 33 build tree names the ten `HAVE_*` lines. Then the recipe changes.
2. **The pins.** `downloads/SHA256SUMS` holds exactly Decision 1's fifteen lines in place of 33's fifteen; `scripts/00_download.sh` fetches each from a literal URL; a build from empty `downloads/` verifies all of them (`downloads: N pins, N fetched, N verified`). No `33.0`, `161b3195` or `4434dabb` remains in `scripts/`, `recipes/` (outside history comments) or `downloads/SHA256SUMS`.
3. **The same bytes, with no exception.**
   - macOS: two builds from empty `build/` write the same `SHA256SUMS`, byte for byte.
   - The linux/arm64 research container: two builds from empty `downloads/` and `build/` write that same `SHA256SUMS`.
   - The linux/amd64 research container (Rosetta, a correctness run): one build writes it too.
   - Check (a) passes on each host's SDK (macOS, and in both containers: the x86_64 and aarch64 Linux clangs).
   - The landing notes list the five `SHA256SUMS` hashes. One file, or the build stops.
   - At every later rebase that brings code first compiled by clang 23, the linux/arm64 container comparison again (Decision 10's trigger).
4. **Nothing a program sees moves but the accepted list.** `surface_probe.py`, run on both binaries of main's set and of 086's set on one machine, compares every builtin and compiled extension module's `dir()` and `sysconfig.get_config_vars()`. Its diff is exactly Decision 6's accepted list (`os.dup2`, `os.pipe2`, `time.pthread_getcpuclockid`, `select.PIPE_BUF`, the ten `HAVE_*`), or each further line is traced and added to that list and the README, or fixed. The other libraries' configure diffs are recorded (Decision 6). The full judge's goldens, classes, trap entries and allowances are unchanged and pass; numpy-core's `no-dup` classes match `Errno 58` again; `python.wasm`'s imports are the same 43 and its exports the same.
5. **The Linux floors and trap entries, before landing** (the lane's ruling on F5, as 065 did). In the linux/amd64 container (Cranelift's x86-64 code, under Rosetta) and in the linux/arm64 container, on 086's set: `test_v1_2_hostile_guest.py`'s recursion checks, `test_the_c_stack_window_is_128_kib`, and the CPython groups that carry spec 065's trap entries. Each passes, with each open trap entry trapping as named or not at all; a floor that fails is re-measured with spec 071's script and changed only as a judge change with the measured depth (Decision 8). 087's x86-64 edge is re-measured in the same run if 087 has landed. Windows stays with the dry run (criterion 7); a Windows floor that fails there is handled the same way.
6. **Decision 9's table and its A/B** are in the landing notes, with the layout control's numbers, inside the bound, with causes labelled (or rule 7's record for a 1 to 3% row), and with the README numbers re-measured where they moved.
7. **The dry run.** One `workflow_dispatch` run of `release.yml` on main's exact commit after the landing passes every job on the three systems, `same-bytes` included, with no exception. No tag before it passes (AGENTS.md rule 6b).
8. **The judge.** `uv run pytest` is green and accepted by the lane with Decision 9's three flags; lost 0. `ruff check` and `ruff format --check` are clean.
9. **The record.** The facts sheet, the evidence memo and folder (naming only 086's files: the review's N1), the README, the CHANGELOG, the libxml2 sheet's reason and the roadmap line exist as Decisions 4, 5, 6 and 11 say.

## Landing notes

**Built 2026-10-19** on `spec/086-wasi-sdk-34`, on main `3866f56`, by a build agent. The recipe is at `810c032`; the evidence is `../research/2026-10-19-the-toolchain-move-evidence.md` and its folder. **Decision 9's A/B and growth accounting wait for 083**: the lane rebases 086 onto main once 083 has landed, and the builder re-measures there (Decision 10, "The base"). Everything else is done.

### What was built

- **The pins** (Decision 1): `line.conf`, `00_download.sh` (the five SDK URLs, the ten notices, the comment) and `downloads/SHA256SUMS`, fifteen lines replaced in place. The neutral tarballs lose `+m` in steps 10 and 60 (Decision 2).
- **The refusal** (Decision 5): `recipes/fcntl_dup_refusal.c`, a `switch` that reads its argument only for `F_SETFD`/`F_SETFL` (an `int`) and `F_GETLK`/`F_SETLK`/`F_SETLKW` (a pointer); step 60's guard compile is a loop over the two refusals, each to its own object, a failure naming its file, and `-Wl,--wrap=fcntl` joins the wraps. It compiles with no warning.
- **The checks** (Decision 7): (a) `test_the_backend_orders_try_tables_alike` and (c) `test_the_guests_configure_results_are_recorded` in `test_v1_5_rebuild_from_pins.py`, (b) `test_dup_is_refused_as_not_supported` in `test_v1_2_hostile_guest.py`; the fixture `tests/fixtures/try-table-order.ll` and the record `tests/cpython_configure.txt`. All three files sit in shards that already exist, so `tests/release_shards.toml` does not change (`test_release_shards_cover_the_judge` passes).
- **An amendment at build: the record keeps one line out.** `HAVE_SYS_STATVFS_H` holds the word part `vfs`, which `context/embedders.txt` reserves, so `test_no_embedder_name_in_code` refused the first record (EXECUTED). The record now leaves out any line holding a reserved word part and carries a `digest` line, the SHA-256 of every line sorted and joined by newlines; check (c) compares the visible lines and, when they agree, the digest, naming "a line holding a reserved word moved" if only that differs. Coverage is whole and the rule is unchanged.
- **Comments and records**: `wasi-numpy.cross`, `wasi-pandas.cross`, `iconv_refusals.c`; the libxml2 patch sheet's reason (Decision 4); the wasi-libc facts sheet and its README row; the README (sizes, platform facts, reproducibility, recipe list, CPython's driver line) and the CHANGELOG.

### Criteria, with their evidence (EXECUTED unless marked)

1. **Seen failing first.** (a) on a wasi-sdk 33 build of today's tree: 2 objects in 64 runs (13 and 51); with no clang under `build/tools`: "no build/tools/wasi-sdk-*/bin/clang: nothing was compiled". (b) on the 34 set without the refusal: `os.dup(1) EINVAL`, both binaries. (c) on the 33 tree: the ten `HAVE_*` lines, nothing else. Then each passes on 34 (`seen-failing.txt`). (c)'s digest half, the amendment at build, was seen failing by the build review (its section 3, EXECUTED there): `HAVE_SYS_STATVFS_H 0` planted in a copy's `pyconfig.h` gave "a line holding a reserved word moved: digest a4d4a837…, not d8eefd30…", and the restored header passed (the build review's B3).
2. **The pins.** `downloads: 49 pins, 49 fetched, 49 verified` from empty `downloads/` on macOS; the containers verify the Linux pins (6 fetched, 49 verified each). No `33.0`, `161b3195` or `4434dabb` remains in `scripts/`, `recipes/` or `SHA256SUMS`; one sentence of history in the refusal's comment names "wasi-sdk 33's guest".
3. **The same bytes.** macOS A and B, the linux/arm64 container twice and the linux/amd64 container once: one `SHA256SUMS`, `aac927dc…`, all five (memo, section 2). Check (a) passes on the macOS, aarch64 Linux and x86_64 Linux clangs.
4. **The surface.** The probe's diff is the accepted list plus `sysconfig` `LIBOBJS` (`Python/dup2$U.o` → empty), traced to `HAVE_DUP2` (`AC_REPLACE_FUNCS([dup2])`): a build variable, accepted here, not a README fact. Two values move too, found by the build review's value probe (its B2) and confirmed here (EXECUTED, both binaries): `sys.version` and `platform.python_compiler()` name `Clang 23.1.0-wasi-sdk (… 895aa2c8…)` where they named Clang 22.1.0, as a toolchain move must, accepted; and `time.CLOCK_MONOTONIC` and `time.CLOCK_REALTIME` are 22668564 and 22668568 (22664664 and 22664668 on main's set, the review's figures): wasi-libc's clock ids are the addresses of static objects, so they move with the data segment (0xF00 here), accepted, and the README question is for the owner. The other libraries' configure headers and probes are unchanged (memo, section 5). The full judge's goldens, classes, trap entries and allowances pass unchanged; numpy-core's `no-dup` classes match `Errno 58`; the imports are the same 43.
5. **Before landing, in the containers.** linux/arm64: 49 hostile checks pass; `cpython-a`, `-b` and `-c` pass with their 16 gaps; checks (a) and (c) pass. linux/amd64: the same 49 hostile checks pass on Cranelift's x86-64 code (every recursion floor, the 128 KiB window, the deep-data limits); `cpython-a`, `-b` and `-c` pass with their 16 gaps; checks (a) and (c) pass on the x86_64 Linux clang. Spec 065's nine trap-entry checks (`-k test_upstream_trap`) were not in that first run, which selected only the groups and their classes, so it showed nothing about them (the build review's B1). They were run afterwards in both containers, on the same set (`SHA256SUMS` `aac927dc…`, copied in; `run-086-traps.sh`, `traps-linux-*.txt`): on linux/amd64 all nine trap as named, `c-stack-itertools-tee` included ("trap at or after test.test_itertools.TestPurePythonRoughEquivalents.test_tee_recipe"); on linux/arm64 eight trap as named and `c-stack-itertools-tee` reports "no trap on this host", as on darwin, which an open entry accepts (it traps on Linux x86-64 only). Each stays a gap closed by 078. 087 has not landed, so its x86-64 edge is not re-measured here. The darwin depths of all fifteen README rows are the same on both sets (memo, section 6), so the README's depth rows stand.
6. **Decision 9's table and A/B**: preliminary only, against `accepted.json` (memo, section 7): 164 fuel rows, 62 up and 98 down, −0.444% to +2.645%, sum +0.22%; `python.wasm` +67,598 bytes (code +45,497, name +17,779, data +4,256). The layout control (memo, section 8): `bool` moves 0xFF0 bytes and a bool conversion costs +31.5% fuel, 073's mechanism. **The A/B on the landing base, after 083, follows.**
7. **The dry run** follows the landing (rule 6b).
8. **The judge.** `uv run pytest -n 3` on set B: 546/627 pass, 77 gap, 4 blocked, 0 fail; the ratchet lost 0, gained 4 (the new checks), grew 64; the judge changed (the three checks, the record, the fixture). Record: the worktree's `build/086-evidence/latest-full-1.json`. `ruff check` and `ruff format --check` are clean on `src/` and `tests/`.
9. **The record.** The memo and its folder (086's files only), the facts sheet, the README, the CHANGELOG, the libxml2 sheet and the roadmap line.

### The rebase, S5 and the zip fix (2026-10-20)

Evidence: `../research/2026-10-19-the-toolchain-move-evidence.md`, section 10, and its folder `rebase/`. Everything below is EXECUTED unless marked.

- **The rebases.** 086 was rebased three times, each with `git rebase`:
  - onto `45b917c` (083 and 089): clean;
  - onto `97be88a` (078): two conflicts, in `tests/checks/test_v1_2_hostile_guest.py` (both sides appended at the file's end; I kept 078's runner-stack checks, then 086's dup check) and `CHANGELOG.md` (I kept 078's entry, then 086's);
  - onto `e8ba20a` (wave 01): the same two files, each resolved by keeping both sides, wave 01's first.
- **What was folded in.**
  - **S5:** step 20 passes `--with-hash-algorithm=siphash13`. It is a configure flag, not a patch. The build-Python gets it too, and it is that host's default already.
  - **The zip fix:** step 70 copies the generated `_missing_stdlib_info.py` beside `_sysconfigdata`.
  - **Two new checks,** each seen failing first on the `aac927dc` set:
    - `test_the_string_hash_is_siphash13[plain]` and `[snapshot]`: "fnv 32 32 64";
    - `test_a_missing_stdlib_module_says_why`: "Standard library module '_tkinter' was not found".
  - **Check (c)** named `+Py_HASH_ALGORITHM 3 (built, not recorded)` (macOS and both containers), and then the record took the line and its new digest.
  - **README:** the snapshot facts state the hash (SipHash-1-3, 32 bits wide, the plain reactor's key fresh per call, the snapshot's fixed and public). *Not protected* gains keys built to collide under the snapshot's key. The sentence about the zip lacking `_missing_stdlib_info` is restated. **CHANGELOG:** two lines.
- **078's class closes** (superseded by M1 below: the class now stays, empty). After 078 landed, the full judge said `cpython-a-no-missing-stdlib-info` "passes, but tests/known_gaps.toml still lists it". So I removed its class, its expected file and its gap. `test_regrtest`'s class count went 26 → 25, as the lane asked. `cpython-a` passes 5,863 → 5,864 (`MiscTest.test_windows_only_module_error`).
- **The same bytes.**
  - On `45b917c` (at `45efcc3`): macOS A (empty `downloads/` and `build/`), macOS B, linux/arm64 and linux/amd64 all wrote `SHA256SUMS` `4586ce2a…`.
  - On `e8ba20a` (at `77d2a81`): macOS (empty `build/`) and linux/arm64 wrote `6d362277…`. 087's carried regex patch applied cleanly under clang 23: python.wasm +200 bytes.
  - Criterion 5 ran in the containers. All nine trap entries trap as named on linux/amd64 before
    078. After 078, 52 hostile checks pass on linux/arm64.
- **The A/B** (Decision 9), on 078's base: four full judges, `-n 3`, one judge commit, darwin-arm64. M is main's set; T, TZ and F are the steps (memo section 10).

  | Step | Fuel: up / down | Median | Range | Sum |
  |---|---|---|---|---|
  | M→T, the toolchain | 66 / 100 | −0.097% | −0.365% to +2.706% | +0.230% |
  | T→TZ, the zip file | 102 / 22 | +0.015% | −0.230% to +1.094% | −0.004% |
  | TZ→F, the hash flag | 159 / 12 | +0.737% | −2.475% to +1.836% | +0.230% |
  | M→F | 164 / 3 | +0.582% | −2.519% to +2.700% | +0.460% |

  - **numpy-core** is +2.706%, which falls in Decision 9's band for tracing file by file. It is the layout control's mechanism: `bool` moves 0xFF0 under the toolchain and stays put under the flag; a bool conversion costs +31.5% on T and F alike. Spec 091, landed in wave 01, makes `test_string_comparisons`' fuel a fact. **Not done:** the file-by-file trace of numpy-core's remainder on 091's base. The lane lock held during wave 02, so the 200 G group was not run. It is the first thing to measure at the rebase after wave 02, where the A/B is re-run; rule 7 has not been invoked.
  - **The compress job** is +1.430% (the toolchain's; INFERRED, the backend's choices).
  - **The zip file:** the uncaught-error traceback is +1.094%, traced (traceback now loads `_missing_stdlib_info`).
  - **The hash flag:** SipHash-1-3 costs 142.7 more instructions per fresh 8-character string than FNV (`rebase/hashcost.txt`); plain starts are +1.43%; snapshot programs that import regex or pickle are up to +1.84%.
  - **The bounds hold.** The fuel sum is +0.460%; python.wasm is +0.164% and the snapshot +0.186%; the zip moved only by the folded-in file.
  - **078's 8 MiB edges** on darwin are unchanged, M against F, for every row that still traps. x86-64 was not re-measured.
- **The fast tier** on `77d2a81` (`build/086/fast-e8ba20a.log`): 561/675 pass, 1 gap, 3 blocked, 0 fail; unit suite 1727/1734. Ratchet: lost 0, absent 1, gained 7, grew 141. Against `e8ba20a`'s accepted record: 143 fuel rows, 138 up and 3 down, from −2.519% to +1.795%, median +0.592%. python.wasm 41,099,863 → 41,167,079, the snapshot 44,634,185 → 44,717,041, the zip 22,197,173 → 22,198,669. `ruff check` and `ruff format --check` are clean.
- **The full judge**, `uv run pytest -n 3`, local, on 078's base, set F, on the commit before the class count fix (`build/086/records-97be88a/`): 590/662 pass, 68 gap, 4 blocked, 0 fail in the goals. One unit row failed, `test_regrtest`'s class count, since fixed. Ratchet: lost 0, absent 1, gained 7, grew 168, more 1. Under the waves rule, the full judges now run on CI.
- **The branch dry run, 39360800335** (`77d2a81`), read with `gh run view`:
  - The build shard ran 39/39, grew 0, gained 2. Its one red line is `ABSENT tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[cpython-a-no-missing-stdlib-info]`.
  - Both rebuilds from the pins (ubuntu-24.04 and -arm) are green.
  - Every judge shard, gather and the same-bytes job were skipped, because each needs the build job. A branch run before acceptance cannot pass the absent check: the workflow takes no `--retire`, and its record still holds the class's gap.
  - The lane ruled (a) (2026-10-20; superseded, see "Rebased onto b0c7a74"): the wave's dry run after acceptance with `--retire` is the shards' confirmation, as it was for 078.

### Rebased onto b0c7a74 (wave 02), then f7511b7 (wave 03), 2026-10-20

Evidence: `../research/2026-10-19-the-toolchain-move-evidence/rebase/`. Everything is EXECUTED unless marked.

- **The conflict hunks, for the delta review.** Each was resolved by hand:
  1. Onto `b0c7a74`, in the build commit, `README.md`'s sizes row: I took wave 02's row (039's tier A sizes), then restated it after the rebuild (41.2 / 45.4 / 38.7 MB, wasi-sdk 34).
  2. Onto `b0c7a74`, in the build commit, `CHANGELOG.md`: I kept 093's entry, then 086's toolchain entry.
  3. Onto `f7511b7`, in the build commit, `CHANGELOG.md`: I kept 092's entry, then 086's.

  `release.yml`, `tests/known_gaps.toml` and step 70 merged without conflict. Step 70 keeps 039's tier A lines and 086's `_missing_stdlib_info` copy.
- **M1 (the delta review), done.** 078's class `cpython-a-no-missing-stdlib-info` stays, with an empty list file, as a passing check (`context/progress/README.md`'s rule for a fixed class). Its reason now says spec 086 closed it, its gap is removed, and `test_regrtest`'s count stays
  26. No check is absent, so the lane needs no `--retire`. **The lane's ruling (a) of 2026-10-20 is superseded:** the branch dry run below ran every shard before acceptance.
- **L2, done.** The README says the key is fresh in every plain call and every plain session, and that a `Session` is on the snapshot unless `snapshot=False`.
- **The rebuild on `b0c7a74`.** macOS (from an empty `build/`) and linux/arm64 wrote one `SHA256SUMS`, `4e0dc0cf…`.
  - python.wasm 41,169,347 bytes, the snapshot 45,444,036, the zip 38,723,140.
  - Against main's set (`2b0480af…`, the set_sums of history line 83): +67,216, +69,925 and +1,496.
  - On `f7511b7`, step 90 gives the same `SHA256SUMS`, since wave 03 changed no build input.
  - In linux/arm64, at `76474f6`: 52 hostile checks pass; `cpython-a`, `-b` and `-c` pass; checks (a), (c) and the zip check pass.
- **numpy-core alone**, darwin, on 091's base (`numpy-core-alone-b0c7a74.txt`):
  - main's set 156.190 G (equal to the accepted value) → 086's 156.506 G: **+0.20%**, under Decision 9's 1% tracing band, so no trace is needed;
  - its `string-comparisons` fact goes 63.54 G → 58.28 G, the layout term 091 holds out of the ratchet.
- **The branch dry run, 39364304770** (`47a853b`, on `b0c7a74`):
  - **Green:** the build shard, both rebuilds from the pins, the same-bytes job (every host's `SHA256SUMS` and wheel equal), all three `verify` jobs, and every Ubuntu shard. On Windows, every shard but own-embedding.
  - **Red lines:**
    - macOS upstream-macos: GREW 2 (`cpython-fs`, `numpy-lib`);
    - macOS own-guest: GREW 132;
    - macOS own-embedding: GREW 21;
    - Windows own-embedding: LOST on 084's two rows, `test_the_removal_never_deletes_what_the_guest_may_not[home]` and `[private]`, which 094 fixed on main (wave 03).
  - Gather was skipped because shards failed, so G7 did not run. No other red line.
- **The A/B against main's accepted values**, same shard against same shard: main's wave 02 dry run 39363060501 against 086's run 39364304770 (`ci-same-shard-39363060501-vs-39364304770.txt`).
  - Fuel: 193 rows, 164 up and 26 down, median +0.573%, from −2.530% to +1.854%, sum +0.284%.
  - Bytes: python.wasm +0.164%, the snapshot +0.154%, the zip +0.004%.
  - The rows over 1% are those the A/B on 078's base attributed:
    - plain starts, about +1.58%: the hash flag;
    - `test_unbuffered_output_survives_a_hard_exit[plain]`, +1.854%: the hash flag;
    - `test_pickling_a_deep_list_raises`, −2.53%: the hash flag.
- **`cpython-b` on Linux x86-64 is bimodal; it is not 086's** (`cpython-b-linux.txt`).
  - 086's run gave 302.99 G against wave 02's 292.76 G (+3.495%).
  - The same Linux shard swings 3.25% on a fixed set. On one set (097be88a's inputs), run 39351481374 gave 301.98 G, while 39354482605 and 39357023086 gave 292.48 G. On main's set, 39363060501 and 39365394797 both gave 292.76 G.
  - In the linux/arm64 container, cpython-b on main's set against 086's is exact and repeatable: 294.774 G → 295.457 G (+0.231%), twice, in both orders.
  - Darwin, on 078's base: +0.18%.
  - So 302.99 G is the high mode of a Linux x86-64 row that varies run to run, and 086's own move is about +0.2%. `cpython-archives` swings the same way (163.08 G and 165.80 G on one set). That variance is a follow-up for its own specification. It does not bear on 086.

### For the lane

- **Wave 04 is 086 alone**, on `f7511b7`. Tip: the branch's head (pushed with lease). The lane rebuilds in the main tree; its `SHA256SUMS` should be `4e0dc0cf…`.
- **The claim list: the rows 086 changes.**
  - **New checks (7):**
    - `tests/checks/test_v1_5_rebuild_from_pins.py::test_the_backend_orders_try_tables_alike` and `::test_the_guests_configure_results_are_recorded` (no fuel);
    - `tests/checks/test_v1_2_hostile_guest.py::test_dup_is_refused_as_not_supported[plain]`, `[snapshot]`, and `::test_the_string_hash_is_siphash13[plain]`, `[snapshot]` (fuel recorded);
    - `tests/checks/test_v1_1_artifact_set.py::test_a_missing_stdlib_module_says_why` (fuel recorded).
  - **A gap that now passes (1):** `tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[cpython-a-no-missing-stdlib-info]` (an empty class; its gap removed).
  - **Retired:** none. **Passes moved:** `cpython-a` +1 (5,863 → 5,864, `MiscTest.test_windows_only_module_error`). No group's passes fall.
  - **Rows that grow:** every fuel and byte row may move. The toolchain and the hash flag touch every guest run, and the three byte rows grow. The A/Bs above give the causes.
  - **Not 086's:** a Linux x86-64 swing of `cpython-b` or `cpython-archives` between runs (above).
- **The exact flags:**

  ```
  --accept "086: wasi-sdk 34 (clang 23.1.0, wasi-libc 2e6fb9d8, musl 1.2.6): every artifact's bytes move once, one SHA256SUMS from every host; fcntl's two dup commands refused as ENOTSUP by a link-time recipe; CPython configured with --with-hash-algorithm=siphash13 (the 0.1.0 security review's S5); the stdlib zip carries CPython's generated _missing_stdlib_info"
  --accept-judge "086: seven new checks (the try_table reproducer compiled 64 times with each pinned clang, the guest pyconfig.h defines recorded in tests/cpython_configure.txt with Py_HASH_ALGORITHM 3, dup refused as ENOTSUP and sys.hash_info siphash13 on both binaries, a missing stdlib module named as natively) and the fixture tests/fixtures/try-table-order.ll; 078's class cpython-a no-missing-stdlib-info emptied, its gap removed, its reason naming 086, because the zip now carries the file"
  --accept-growth "086: the A/B on 078's base (four full judges, one judge commit, darwin-arm64; research 2026-10-19-the-toolchain-move-evidence, section 10) splits the move: the toolchain 66 fuel rows up and 100 down, -0.365% to +2.706%, sum +0.230% (numpy-core's bool-address layout, now 091's fact, and the compress job +1.430%); the zip file median +0.015%, max +1.094% (a traceback now loads _missing_stdlib_info), sum -0.004%; the hash flag 159 up and 12 down, -2.475% to +1.836%, median +0.737%, sum +0.230% (SipHash-1-3 costs about 143 more instructions per 8-character string than FNV; plain starts +1.43%). On b0c7a74, main's dry run 39363060501 against 086's 39364304770, shard by shard: 193 fuel rows, 164 up and 26 down, median +0.573%, -2.530% to +1.854%, sum +0.284%; numpy-core alone +0.20% (156.190 G to 156.506 G); python.wasm +67,216 bytes (41,102,131 to 41,169,347), the snapshot +69,925 (45,374,111 to 45,444,036), the zip +1,496 (38,721,644 to 38,723,140)"
  ```

  No `--retire`. No `--accept-fewer-passes`: no group's passes fall. No `--partial`.
- **Dry-run needs:** the dry run on main after acceptance. Run 39364304770 has already run every shard, the same-bytes job and Windows on 086's set. The one Windows red there is gone on main since 094.

## For the owner

1. **Nothing blocks the build.** Every choice above is decided. Three are worth knowing:
   - **Accepting the new attributes.** Guest programs gain `os.dup2`, `os.pipe2` and `time.pthread_getcpuclockid`, each raising `ENOTSUP`, and the constant `select.PIPE_BUF` (4096) (Decision 6). This is what wasi-libc 34 provides. Holding them out would take forced `#undef`s in CPython's compile and a `dup2` symbol clash. The reviewer concurs. **Recommendation: accept** (as decided), and the README lists them.
   - **Sending the wasi-libc sheet after landing.** A second link-time refusal joins `iconv_refusals.c`, so `os.dup` keeps `ENOTSUP` (Decision 5). It goes when wasi-libc's `fcntl` answers `ENOTSUP` for its two dup commands on preview1, as its `dup` does. The facts sheet, `upstream/25-wasi-libc-fcntl-dupfd/`, is yours to send. **Recommendation: send it once 086 lands**; the fix is one line, and it lets the refusal go.
   - **Clock ids are not stable across releases.** `time.CLOCK_MONOTONIC` and `time.CLOCK_REALTIME` are wasi-libc data addresses, so their numbers change whenever the data segment moves (by 0xF00 in this move); a program that stored a number instead of using the name would pass the wrong id to a later release. **Recommendation: add one README platform fact** ("the `time.CLOCK_*` ids are addresses that change between releases; use the names"), in 086's README edit if you agree, since it costs one sentence and the platform facts exist to say such things (constitution §4.11).
   - **numpy-core's fuel moves with memory layout.** 073 measured it; 086's control (Decision 9) will say how much of its +2.645% is the same. If it is, a later judge-side look at that one group's fuel, outside 086, may be worth a question. Nothing to decide now.
2. **The brief's "wasi-sdk 32" was 33.** No decision; recorded above.

## Disposition of the pre-build review (2026-10-19)

The review (`../reviews/086-the-toolchain-moves-to-wasi-sdk-34-spec-2026-10-19.md`, in the lane's scratchpad with its probes, copied by the lane) said "ready once F1 to F5 are written in"; F6 to F10 to be fixed or answered. The lane ruled on each; all are written in.

- **F1 (medium), numpy-core's rule contradicted itself.** One rule now (Decision 9, "The rule"): measured as an A/B on one machine (main's set against 086's, the same judge commit) after a layout control, never against `accepted.json` alone; over 3% stops the build; 1 to 3% is traced file by file; two failed attempts invoke AGENTS.md rule 7 (recorded, then accepted with the record). The control starts from 073's measured mechanism: `bool`'s address and `test_strings.py::test_string_comparisons`.
- **F2 (medium), the surface moves by more than three attributes.** `select.PIPE_BUF` is added to the accepted list (Decision 6, Decision 11, For the owner), and criterion 4 now compares every module's `dir()` and `sysconfig` across both sets by `surface_probe.py`.
- **F3 (medium), no trigger for code first compiled by clang 23.** Decision 10's same-bytes trigger: the linux/arm64 container comparison is re-run, beside the macOS build, at every rebase that brings such code (043's contourpy and qhull, 087's patch, 073, anything build-class), by whichever specification rebases; criterion 3's last bullet.
- **F4 (medium), where 086 lands and on what base.** Decision 10: after 083, 039, 073, 085 and 084, and after 043 if 043 is ready first; 037 rebases onto 086; whichever of 086 and 043 lands second rebuilds contourpy and qhull with clang 23. Decision 9 is measured on the exact base 086 lands on, after 083's driver change.
- **F5 (medium), x86-64 floors and Linux trap entries only after landing.** Criterion 5: run in the linux/amd64 and linux/arm64 containers before landing, as 065 did; Windows stays with the dry run, under the same re-measure rule.
- **F6 (low), check (b) never turns red on an upstream fix.** The false sentence is gone; the removal signals are the facts sheet and the next toolchain move's recipe table, which now names `fcntl_dup_refusal.c` (Decisions 3 and 5). Check (b) also covers `pthread_getcpuclockid` and the `dup3` path.
- **F7 (low), check (a)'s input and need.** The reproducer is copied to `tests/fixtures/try-table-order.ll` with its SHA-256 named; the need is `compile records`; the check fails when it finds no clang (Decision 7, criterion 1).
- **F8 (low), the wrapper read an argument that may not exist.** The wrapper reads `va_arg` only for commands that take one; the justification is corrected; step 60's guard compile becomes a loop whose failure names its file (Decision 5). The trial's table says the trialled wrapper read unconditionally.
- **F9 (low), other components probe libc.** Decision 6: the builder diffs every generated config header, 33 against 34, and treats each flip as CPython's.
- **F10 (nit), record every `#define`.** Done (Decisions 6 and 7).
- **N1.** The evidence moves into the repository with only 086's files named (criterion 9); the worktree's `build/086-evidence/` also holds older scripts from the shared scratch folder, which are not 086's.
- **N2.** One README line (Decision 11).
- **N3, N4.** No action.

## Disposition of the build review (2026-10-19)

The review (`../reviews/086-the-toolchain-moves-to-wasi-sdk-34-build-2026-10-19.md`, in the lane's scratchpad, copied by the lane) confirmed the bytes, the refusal, the checks and the record, and said "lands once the A/B is done on 083's base and B1 is run and written in".

- **B1 (medium), the trap entries were not run in the containers.** Run in both, on the same set (EXECUTED, `../research/2026-10-19-the-toolchain-move-evidence/traps-linux-*.txt`): all nine trap as named on linux/amd64, `c-stack-itertools-tee` included; eight on linux/arm64, with `c-stack-itertools-tee` "no trap on this host", as on darwin. The landing notes' and the memo's unsupported sentence is replaced by these facts. No entry failed to trap where it should.
- **B2 (low), two more values.** `sys.version` naming Clang 23.1.0 is on the accepted list, and the clock ids' move (wasi-libc data addresses, 0xF00 with the data segment) is in the memo and the criterion 4 notes; the README line is put to the owner with a recommendation.
- **B3 (low), check (c)'s digest half.** Its seen-failing is the review's planted run, cited in criterion 1.
- **N1.** The facts sheet's last line now says the row is in the table.
- **N2.** Noted: a copy of a built tree cannot pass `test_every_build_python_is_pinned`.
- **Still to come:** the A/B on the landing base, with a delta review if its numbers move beyond the preliminary table's.

### Landed in wave 04

- The lane rebuilt the set in the main tree at `c4af3c4` from the pins (13 downloads fetched for the new toolchain): SHA256SUMS `4e0dc0cf`, the same file the builder's macOS and linux/arm64 builds wrote.
- Against main `f7511b7`'s acceptance, 195 fuel rows moved, 167 up and 28 down, median +0.577%, -2.530% to +1.854%, as the shard-by-shard A/B claimed; every row over 1% is the SipHash-1-3 flag's per-string cost. python.wasm +0.164%, the snapshot +0.154%, the zip +0.004%. Seven new checks pass; `test_upstream_class[cpython-a-no-missing-stdlib-info]` passes as an empty class (the delta review's M1), and cpython-a gains one pass.
- Reviews: `../reviews/086-*` (the specification, the build, and the delta with its confirmation at `c4af3c4`). The delta review's N3: the growth text's 193 rows leave out Linux's two bimodal rows (cpython-b, cpython-archives), which 092 keeps out of the lane's comparison; the Linux swing on a fixed set is a follow-up for its own specification (this dry run's cpython-b near 293.4 G or 303 G confirms the reading).
- **The dry run 39369492451 on `085dba5` passed every job on all three systems**, the gather and G7 included: the toolchain move holds on Windows and Linux x86-64. Linux x86-64's cpython-b read 293.447 G, the low mode plus 086's +0.23%, which confirms the delta review's reading of the 302.99 G branch value as runner variance.
