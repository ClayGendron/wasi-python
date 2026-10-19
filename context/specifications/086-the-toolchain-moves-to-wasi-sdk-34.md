# 086 — The toolchain moves to wasi-sdk 34

- **Status:** drafted 2026-10-19 on `spec/086-wasi-sdk-34` from main `932bc00`, rebased onto main
  `3866f56` (the owner's answer to question 105). Not yet reviewed. It changes the build recipe and
  every byte of the artifact set, so it is reviewed once before it is built (constitution §5.6).
  It changes neither the guest's imports nor its exports (EXECUTED, the trial below). The drafter
  ran the whole move once in a throwaway copy, so most facts here are EXECUTED; the section "The
  trial" says how.
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** **build-class** (§5.7): it changes `scripts/`, `recipes/` and `downloads/SHA256SUMS`.
  - **Changed:**
    - `scripts/line.conf`: `WASI_SDK_VERSION=34`, the six SDK folder names, `WASI_LIBC_COMMIT=2e6fb9d8`,
      `LLVM_COMMIT=895aa2c8`;
    - `scripts/00_download.sh`: the five wasi-sdk URLs and names, the ten licence-notice URLs and
      names, and the comment that names the versions;
    - `downloads/SHA256SUMS`: 15 lines out, 15 in (Decision 1);
    - `scripts/steps/10_tools.sh` and `scripts/steps/60_link.sh`: the sysroot and builtins tarball
      names lose `+m` (Decision 2);
    - `scripts/steps/60_link.sh`: one more `--wrap` flag and one more file in the guard compile
      (Decision 5);
    - comments that name wasi-sdk 33: `recipes/wasi-numpy.cross:30`, `recipes/wasi-pandas.cross:30`,
      `recipes/iconv_refusals.c:3`, and the libxml2 patch's facts sheet, whose reason changes
      (Decision 4);
    - `README.md`, `CHANGELOG.md`, `context/roadmap.md`.
  - **New:**
    - `recipes/fcntl_dup_refusal.c`: wasi-libc's `fcntl` answers the two dup commands as its `dup`
      does (Decision 5);
    - `tests/cpython_configure.txt`: the guest CPython's configure results, recorded (Decision 6);
    - three checks (Decision 7);
    - `context/upstream/25-wasi-libc-fcntl-dupfd/`: a facts sheet for wasi-libc (Decision 5; 23 and 24
      are taken by 037's and 087's branches).
  - **Judge changes:** the three new checks and the recorded list. No golden, allowance, class,
    trap entry or gap changes (Decision 8). So the lane accepts with `--accept-judge` (the new
    checks) and `--accept-growth` (Decision 9).
  - **Not changed:** `tests/public_api.txt` (no public name moves), `src/`, the release
    workflow, every carried patch.
- **Depends on:** 012 (the host-neutral sysroot and builtins), 040 and 059 (each host compiles with
  its own clang; `-ffp-contract=off` in `clang.cfg`), 063 and 065 (the shards and CPython's own
  tests); all landed. The owner's answers to questions 104 and 105 (`../decisions.md`, "105, and
  the open points of 078, 084 and 085, answered", 2026-10-19): **(b), the toolchain moves first**:
  086 is built now, takes 037's build slot, lands before 037, and 037's same-bytes exception is
  withdrawn at 037's rebase and never landed. The roadmap says the same (`../roadmap.md`, "In
  flight").
- **Research it stands on:** `../research/2026-10-19-the-try-table-order-in-llvm.md` and its folder
  (the cause, the upstream fix, the reproducer); spec 037's branch memo
  `2026-10-19-ducc0-is-not-reproducible-with-the-pinned-clang.md` (the symptom); and this
  specification's trial (EXECUTED, below).

**A correction to the brief.** The brief that started this draft said the pin is wasi-sdk 32. It is
wasi-sdk 33: `scripts/line.conf:7` says `WASI_SDK_VERSION=33`, and `downloads/SHA256SUMS` pins
`wasi-sdk-33.0-*` with LLVM `4434dabb` (22.1.0) (READ). Everything below moves from 33 to 34.

## The problem

wasi-sdk 33's clang (LLVM 22.1.0) does not always compile the same source to the same object. Its
WebAssembly backend nests `try_table` blocks in the order of a `DenseMap` keyed by block pointers
(`WebAssemblyCFGStackify.cpp:1829`, iterated at 1972). Heap addresses decide that order, and
address-space randomization moves them on every run. Today's set never hits it: every compile in
it is reproducible. Spec 037's scipy does hit it: ducc0's FFT (`pyduccfft.cxx`) compiles to
different bytes on every run. So 037 built a narrow same-bytes exception (its Decision 17).

The owner chose to remove the cause instead (question 105, (b)). LLVM fixed the map upstream in
`fd76c9bd` (PR #205184, issue #204883), which is in LLVM 23.1.0 and in no 22.x release. wasi-sdk
34 ships LLVM 23.1.0. This specification moves the pin there, proves the move keeps every byte
the same from every host, and leaves 037 to drop its exception at its rebase.

In one line: same source, same bytes, on every host, with no exception.

## The trial (EXECUTED)

The drafter ran the move once, before writing a decision, so that each decision rests on a run.

- **Where.** A plain copy of main `932bc00`, then a throwaway `git clone` of the worktree under
  its git-ignored `build/086-trial/`, with five files changed: `line.conf`, `00_download.sh`,
  `SHA256SUMS`, `10_tools.sh` and `60_link.sh` (the pins and the `+m` names, Decisions 1 and 2;
  not Decision 5's wrap). No branch file was edited. The containers are the research images of
  specs 040 and 059 (`wp040-arm64`, `wp040-amd64`), each cloning the clone and laying the five
  files over it.
- **Downloads.** Each tarball was fetched into its own new folder and hashed before use.
- **Runs.** `scripts/build.sh --plain` (macOS builds and container builds, below), then
  `uv run pytest -n 3` and the upstream suites on the clone's set.
- **Baseline.** Main's accepted set is 0.1.0a7's: `python.wasm` `ab78e893…`, the snapshot
  `c50ca51f…` (`context/progress/accepted.json`; the release tarball `fc59b977…`, downloaded and
  hashed, holds the same two files).

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
| Decision 5's refusal, trialled (appended to the guard's unit in the clone, `-Wl,--wrap=fcntl`, relinked from step 60) | `os.dup(1)` raises errno 58 again; numpy-core passes, its classes matching; the fast tier: 0 fail, lost 0; `python.wasm` +117 bytes over the trial set | EXECUTED |
| numpy's and pandas' fuel | **numpy-core +2.645%** (203.36 G → 208.73 G, on the set with the refusal); the other ten groups from −0.194% (pandas-io-parser) to +0.053% (pandas-groupby) | EXECUTED |
| numpy-core's rise, probed (time box 15 min) | the same workloads on 0.1.0a7's set and the trial set move under 0.6% each: libm calls −0.27%, sorts +0.18%, float formatting −0.08%, copies −0.17%, `np.char` +0.38%, `long double` arithmetic −0.12% and formatting −0.52%; the rise is **not traced** (Decision 9) | EXECUTED |
| fuel, every row the full judge compared (numpy's and pandas' groups not among them) | 153 rows: 57 up and 96 down by more than 0.01%; from −0.444% to +1.428%; the sum 1,421.60 G → 1,422.73 G (+0.08%) | EXECUTED |
| new warnings | 4,216 `-Wunused-template`, about 4,190 of them HarfBuzz's (step 37); no other class moved; no step builds with `-Werror` | EXECUTED |

The fuel rows that moved most: the compress job +1.428% (3.919 G → 3.975 G), `cpython-archives`
+0.537%, the door round trip on the snapshot +0.621% (16.1 M), `cpython-fs` +0.434%; and down,
lxml's encodings workaround −0.444%, `np.frompyfunc` recursion −0.393%, `test_nothing_is_a_shared_library`
−0.365%. Every recursion floor of `test_v1_2_hostile_guest.py` held on darwin-arm64, and so did
`test_the_c_stack_window_is_128_kib` ("used 112 kB").

## Decisions

1. **The pins.** wasi-sdk 34 (`wasi-sdk-34`, published 2026-08-25). Each tarball's SHA-256 was
   computed here from the downloaded file and equals the release page's digest (EXECUTED):

   | File | SHA-256 | Bytes |
   |---|---|---|
   | `wasi-sdk-34.0-arm64-macos.tar.gz` | `9c59398106b417f8f14913380fdf0097a8cc0ff4af9eb3ce0065a859e88d49e9` | 180,322,002 |
   | `wasi-sdk-34.0-arm64-linux.tar.gz` | `f7e243dff54d60bcc576e94d6166b69f410f2500ae4a9ceef34315be10e77971` | 192,255,247 |
   | `wasi-sdk-34.0-x86_64-linux.tar.gz` | `b761e3a0721dbae9c09a0059e5fdb2bf917d1b4a8a7b430fb3b5aafb0984b2c4` | 192,383,077 |
   | `wasi-sysroot-34.0.tar.gz` | `9d813544eeebe38b7b8f2244ed591de46b6db812c6dd1a257ff9f0d2a905a2be` | 119,283,116 |
   | `libclang_rt-34.0.tar.gz` | `eee3e634dcf71aa22b1333391623cf5c9965a637dc428a27b1a858c026c587f1` | 774,215 |

   The URLs are `https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-34/<file>`. The
   arm64 Linux tarball is also the x86_64 host's fallback compiler (spec 040), still switched off;
   its `get` line inside the fallback branch moves with the others.

   The licence notices move to the commits the SDK's `VERSION` names: wasi-libc
   `2e6fb9d8ee0cdf9e431fbcabe8af3115de000a13` and LLVM `895aa2c896ada719451be2e3673c83da8ddf1141`
   (full hashes READ from GitHub's commits API). Each was fetched and hashed (EXECUTED):

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

   Nine are the same bytes as 33's. musl's `COPYRIGHT` changed: one contributor's name (EXECUTED,
   `diff`). The set's `LICENSES/wasi-libc.txt` and `LICENSES/llvm-runtimes.txt` change with them
   (EXECUTED: the trial set's lines differ from a 33 set's).

   **Why 34 and not a patched 33.** The memo's route 2 (build LLVM ourselves with `fd76c9bd`)
   would pin a toolchain we built for three hosts and open ground §4.1 does not cover (patches are
   to sources). Route 1 costs one pin move and fixes the cause. There is no newer release: 34 is
   the newest wasi-sdk (READ, the releases list).

2. **The two neutral tarballs lose `+m`.** 33 named them `wasi-sysroot-33.0+m.tar.gz` and
   `libclang_rt-33.0+m.tar.gz`; 34 names them `wasi-sysroot-34.0.tar.gz` and `libclang_rt-34.0.tar.gz`
   (READ, the release assets). `10_tools.sh:14-15` and `60_link.sh:141` build the name from
   `$WASI_SDK_VERSION`; the `+m` is dropped there, and the names stay derived from the line, as
   now. The trial made exactly this change and step 60's neutral-runtime check passed (EXECUTED).

3. **What else moves with the compiler, and what does not.**
   - **The sysroot.** wasi-libc moves 67 commits, `161b3195` → `2e6fb9d8` (READ, GitHub compare).
     It takes musl 1.2.6 and a set of WASIp3 and cooperative-threads work. For `wasm32-wasip1` the
     file list is the same but for one header (`__errno.h` is gone) and the `llvm-lto/22.1.0-wasi-sdk`
     folder renamed `23.1.0-wasi-sdk`; 34 drops the `wasm32-wasi` and `wasm32-wasi-threads` folders
     and adds `wasm32-wasip3` and `experimental-coop-threads` (EXECUTED, the two sysroots' lists
     compared). Nineteen `wasm32-wasip1` headers changed. The ones that reach our build: `unistd.h`
     now declares `pipe`, `dup`, `dup2` and `dup3`; `__header_fcntl.h` defines `F_DUPFD`,
     `F_DUPFD_CLOEXEC`, `F_GETLK`, `F_SETLK`, `F_SETLKW` and the lock types; `limits.h` defines
     `PIPE_BUF`; `bits/stdint.h` makes `int_fast16_t` 32 bits wide (it was 16) (EXECUTED, `diff -r`).
     And `libc.a` defines 48 more symbols, among them `dup`, `dup2`, `dup3`, `pipe`, `pipe2`,
     `ppoll`, `pthread_getcpuclockid` and the `sem_*` family (EXECUTED, `llvm-nm --defined-only`).
     Decisions 5 and 6 take what this does to CPython.
   - **libc++, libc++abi, libunwind** move to 23.1.0, with wasi-sdk's three carried LLVM patches,
     which touch only `libunwind/src/config.h`, libc++abi's thread-atexit and one libc++ locale
     header (READ, `src/llvm-pr-*.patch` at the `wasi-sdk-34` tag). The libc++ ABI tag in mangled
     names follows the version (the memo, READ). No recipe, script or check names a mangled C++
     symbol (READ, the inventory below), so nothing here breaks on it. Spec 037's exception files do
     (`std::__2::make_shared[abi:nqe220100]`), and they are deleted at its rebase.
   - **compiler-rt's builtins**: the same layout (`wasm32-unknown-wasip1/libclang_rt.builtins.a`),
     new bytes (EXECUTED, the tarball's list).
   - **Target features.** The predefined `__wasm_*` macros are the same (the memo, EXECUTED), and
     the trial's `target_features` section is the same size; step 60's whole-list check
     (`tests/harness/constructors.py`, `FEATURES`) passed (EXECUTED). wasmtime 49 needs nothing new.
   - **The reviewed constructor list** (`constructors.py:32-46`, compared whole, in order) passed
     unchanged on today's set (EXECUTED). A package that brings new C++ (043's contourpy, 037's
     scipy) is re-checked at its own rebase (Decision 10).
   - **Warnings.** Clang 23 adds `-Wunused-template`: 4,216 warnings in the trial, about 4,190 of
     them HarfBuzz's in step 37 (14 there with 33, 4,204 with 34), and +14 in numpy, +12 in
     matplotlib. No other warning class moved; step 53 (regex) prints 0 warnings, as spec 087
     cites (EXECUTED, the step logs against spec 043's 33 logs). No build uses `-Werror`: HarfBuzz's
     error pragma is off by `-DHB_NO_PRAGMA_GCC_DIAGNOSTIC_ERROR`, 043's contourpy builds with
     `-Dwerror=false`, and 037's scipy has no `-Werror` (READ). The warnings change no byte. They
     are not silenced: a `-Wno-` flag is a recipe line with no product effect.
   - **GB18030 is still wrong in musl 1.2.6.** wasi-libc 34's `src/locale/iconv.c` is byte for byte
     musl 1.2.6's (`84bdddca…`), not the fixed one (`67219f0`, `7038e7f5…`) (EXECUTED, fetched and
     hashed). So `recipes/iconv_refusals.c` and its three wraps stay; only its comment's "wasi-sdk
     33" becomes "34".
   - **The other wraps still resolve.** The `__wasi_*` calls `reactor_main.c` wraps and
     `__wasilibc_reset_preopens` are referenced and defined as in 33 (READ, the inventory), and the
     reactor linked and passed the judge (EXECUTED).
   - **CPython's driver** reads `Platforms/WASI/config.toml`'s `wasi-sdk = 33` and only logs a
     warning on 34 (READ, `_build.py:262-273`); the build does not stop.

   **Every recipe and patch, against the move** (READ, then EXECUTED by the trial build):

   | File | What could move | Outcome |
   |---|---|---|
   | `line.conf`, `00_download.sh`, `SHA256SUMS` | the pins | Decision 1 |
   | `10_tools.sh`, `60_link.sh` | `+m` names; one `lib/clang/*`; `clang.cfg`; builtins path | Decision 2; the rest holds |
   | `60_link.sh` link flags (`-lc++ -lc++abi -lunwind -lsetjmp`), neutral-runtime check | libc++ 23 | holds |
   | `assemble_artifacts.py` | notice names from the line | follows Decision 1 |
   | `iconv_refusals.c` and its wraps | musl's decoder | stays (above) |
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

4. **The libxml2 patch keeps its code and changes its reason.** Its facts sheet
   (`context/upstream/patches/libxml2-2.15.4/0001-*.md:6`) says clang stops on
   `xmlIO.c` because wasi-libc declares no `dup`. With 34 it declares one, so that is no longer why.
   The patch is still needed: `dup` on preview1 returns `ENOTSUP` (READ, `libc-bottom-half/sources/dup.c`
   at `2e6fb9d8`), so xmlIO's duplicate-then-close path would fail at run time instead of at
   compile time. The patch file does not change, so its `MANIFEST` hash does not either; only the
   sheet's reason ("`dup` always fails on WASI preview1") changes.

5. **`os.dup` keeps its error: a link-time refusal of fcntl's two dup commands.**
   - **What moved** (EXECUTED, the trial guest): `os.dup(1)` raises `OSError: [Errno 28] Invalid
     argument`; with 33 it raised `[Errno 58] Not supported`. numpy-core's eight `tofile`/`fromfile`
     tests therefore fail with a message its `no-dup` class does not match, and the group turns red
     (its pass count and digest unchanged: 9,519 passed, `df21e78e7032`).
   - **Why** (READ): CPython's `_Py_dup` (`Python/fileutils.c`) uses `fcntl(fd, F_DUPFD_CLOEXEC, 0)`
     whenever `<fcntl.h>` defines `F_DUPFD_CLOEXEC`, before it looks at `HAVE_DUP`. 34's header
     defines it. But wasi-libc's `fcntl` compiles its `F_DUPFD` and `F_DUPFD_CLOEXEC` cases out on
     `__wasip1__`, so they fall to `default: errno = EINVAL`
     (`libc-bottom-half/cloudlibc/src/libc/fcntl/fcntl.c:92-110` at `2e6fb9d8`), while its own `dup`
     returns `ENOTSUP` on preview1. The header and the function disagree. No configure variable
     reaches it: it is a header macro.
   - **The decision**, trialled (EXECUTED, above). A recipe, as `iconv_refusals.c` is (spec 046, Decision 9):
     `recipes/fcntl_dup_refusal.c`, compiled into the reactor's link by step 60 beside that file,
     with `-Wl,--wrap=fcntl`. `__wrap_fcntl(fd, cmd, ...)` answers `F_DUPFD` and `F_DUPFD_CLOEXEC`
     with `errno = ENOTSUP` and −1, as wasi-libc's `dup` does, and passes every other command and
     its one argument to `__real_fcntl` unchanged (read with `va_arg` as an `int`, which is what
     wasi-libc's own `fcntl` reads for every command it takes an argument for). It changes no
     upstream source. Its header comment names the facts sheet and says to remove it, with its
     wrap flag, when a wasi-sdk release's `fcntl` returns `ENOTSUP` for these commands on
     preview1; Decision 7's check (b) turns red that day.
   - **Why not accept `EINVAL`.** It would be a judge change (numpy's `no-dup` class and its gap,
     which match `Errno 58`) that makes the guest's answer worse: "Invalid argument" tells a
     program its call was wrong, when the platform cannot do it. A toolchain move should change
     bytes, not what a program sees. The refusal is one small file, the pattern this project
     already carries, and it goes when upstream fixes the mismatch.
   - **Upstream.** A facts sheet, `context/upstream/25-wasi-libc-fcntl-dupfd/` (facts and a
     one-line fix: return `ENOTSUP` for `F_DUPFD`/`F_DUPFD_CLOEXEC` on `__wasip1__`, as for
     `F_GETLK`), drafted for the owner to send, as spec 046 did for GB18030.

6. **The guest's other configure results: accepted, recorded and documented.** wasi-libc 34 flips
   ten of CPython's configure results (EXECUTED, the trial's `pyconfig.h` against spec 043's 33
   one): `HAVE_DUP`, `HAVE_DUP2`, `HAVE_DUP3`, `HAVE_GETC_UNLOCKED`, `HAVE_PIPE2`, `HAVE_PPOLL`,
   `HAVE_PTHREAD_GETCPUCLOCKID`, `HAVE_SEM_GETVALUE`, `HAVE_SEM_OPEN`, `HAVE_SEM_TIMEDWAIT`. CPython's
   own `config.site` forces only `pipe` off (READ). What a program sees (EXECUTED, the trial guest):
   - `os.dup2`, `os.pipe2` and `time.pthread_getcpuclockid` now exist, and each raises
     `OSError: [Errno 58] Not supported`. `os.pipe` stays absent.
   - `select.poll` works as before, now through `ppoll` (a registered stdout polls writable).
   - `getc_unlocked` and `flockfile` are real functions in a single-threaded libc; `fileobject.c`
     uses them.
   - The semaphore results change nothing: `_multiprocessing` is not built, and CPython uses
     semaphores only when `_POSIX_SEMAPHORES` is defined, which 34's `unistd.h` does only for
     cooperative threads (READ, `pycore_semaphore.h:25-29`, `unistd.h`).

   **Why accept rather than pin them back.** Pinning needs cache variables on the host configure
   only (never the build-Python's), which means splitting step 20's one driver call into four, and
   it still cannot hold `os.dup2` out: CPython defines it when `F_DUPFD` is defined (READ,
   `posixmodule.c`), and keeping it out would take `#undef`s forced into every CPython compile.
   And with `HAVE_DUP2` forced off, `configure` compiles CPython's own `Python/dup2.c`, whose `dup2`
   clashes with wasi-libc's whenever its `dup.o` is linked. Every new function fails with
   `ENOTSUP`, so none is silently wrong and none opens a channel (constitution §4.15 holds); all
   five CPython groups and pandas' eight pass with their allowances unchanged (EXECUTED). So the
   smallest true thing is to accept them, say so in the README's platform facts, and record them.

   **Recorded.** `tests/cpython_configure.txt` lists every `HAVE_*` macro the guest's `pyconfig.h`
   defines, one per line, sorted. Decision 7's check (c) reads the build's `pyconfig.h` and names
   each macro that differs. A later toolchain move that flips a result then fails a check, and its
   specification states why, instead of the flip passing unseen.

7. **The checks, written first.** Each is seen failing on today's tree (wasi-sdk 33) or against a
   planted input before the recipe changes, and the landing notes quote the failure.
   - **(a) `test_the_backend_orders_try_tables_alike`** (`tests/checks/test_v1_5_rebuild_from_pins.py`,
     need: the toolchain unpacked under `build/tools/`). It compiles the memo's reproducer,
     `context/research/2026-10-19-the-try-table-order-in-llvm/try-table-order.ll`, 64 times with
     each `build/tools/wasi-sdk-*/bin/clang` (`--target=wasm32-wasip1 -O3 -fwasm-exceptions -mllvm
     -wasm-use-legacy-eh=false -c -Xclang -disable-llvm-passes`), and asserts one object. It counts
     distinct hashes, never time. **Seen failing:** on 33 the trial's 64 runs gave two objects (19
     and 45); a false pass on 33 needs all 64 runs to agree, about (45/64)^64 + (19/64)^64, under
     10^-9. On 34, 64 runs gave one (EXECUTED). This is the memo's ducc0 case reduced to 30 lines,
     in the repository, so it guards 086 before scipy exists on main.
   - **(b) `test_dup_is_refused_as_not_supported`** (`tests/checks/test_v1_2_hostile_guest.py`, both
     binaries): `os.dup(1)`, `os.dup2(1, 5)` and `os.pipe2(0)` each raise `OSError` with
     `errno.ENOTSUP`, and `os.pipe` is absent. **Seen failing:** on the 34 set without Decision 5
     (the trial's set), `os.dup` raises errno 28. On 33's set `os.dup2` is absent, so the check
     is written for 34; its first run is against the trial set.
   - **(c) `test_the_guests_configure_results_are_recorded`** (`tests/checks/test_v1_5_rebuild_from_pins.py`,
     need: compile records): the set of `#define HAVE_*` lines in
     `build/Python-3.15.0/cross-build/wasm32-wasip1/pyconfig.h` equals `tests/cpython_configure.txt`;
     a difference names each macro. **Seen failing:** the list written from 34's `pyconfig.h`,
     run against a 33 build tree, names the ten.
   - The release shards: (a) and (c) go to the `build` shard, (b) with its file's shard
     (`tests/release_shards.toml`); `test_release_shards_cover_the_judge` holds that.

8. **The judge's other parts: what moves, and who re-measures it.**
   - **Goldens.** The `tests/jobs/*.expected` outputs are native, and the guest's matched them
     all on the trial set, `plot_line`'s RGBA hash and `PNG_SHA256` included (EXECUTED: the full
     judge, 0 fail). With `-ffp-contract=off` run-time arithmetic does not change; musl 1.2.6's
     libm could. If a golden or an upstream group moves on another host, spec 059's Decision 6
     rule applies: trace it to the expression first; a traced libm or fold change is a judge change
     with its before and after values; anything untraced stops the build.
   - **Spec 065's nine trap entries** (`tests/upstream/python.toml:86-147`) depend on wasmtime's
     512 KiB stack, spent by Cranelift's frames for each host. A new compiler changes the wasm, so
     Cranelift's frames move. An open entry accepts "the named trap or no trap", so a trap that
     goes away is not red, and a new trap in a group is. On darwin-arm64 the trial matched every
     entry; `c-stack-itertools-tee` did not trap there, as before (it traps on Linux x86-64 only)
     (EXECUTED). The Linux hosts are checked by the release dry run (criterion 6).
   - **Spec 071's window and its floors.** `C_STACK_WINDOW` (128 KiB, `reactor_main.c:154`) does not
     change. The depths under it are clang's frame layout. Each `RECURSIONS` floor is "measured
     depth less a tenth", so a depth that falls more than a tenth turns a check red. On darwin-arm64
     every floor held and the window check still reads "used 112 kB" (EXECUTED). The x86-64 floors
     run in the dry run. A floor that fails there is re-measured with spec 071's own script and
     reported, not lowered quietly: lowering one is a judge change with the measured depth.
   - **Spec 078** (parallel-safe, not landed) records depths and edges at 8 MiB that Cranelift's
     frames set (its Decision 11; it says "086 … re-measures Decision 11's edges", line 396).
     Whichever of 078 and 086 lands second re-runs 078's measurement script on its own set and
     updates 078's numbers in the landing notes. 078's wider C-stack window is a follow-up
     **after** 086 (the owner, question 105's entry, "078"; 078's lines 891-895), because its
     x86-64 numbers depend on these frames.
   - **README numbers.** The sizes (41.1 / 44.6 / 22.2 MB) become 41.2 / 44.7 / 22.2. The depth
     rows (`README.md:240-253`: "40 to 250 levels", expat ~95, freeing a list 2,000, `json.loads`
     1,100, `repr` 1,800, a traceback ~2,700 frames, XPath 375, XSLT 480/470/670, C14N 1,500,
     RelaxNG 430, and the rest) are re-measured with the scripts that produced them on darwin-arm64;
     a row is changed only where the new value rounds differently. The fuel figures in the README
     (`:91`, `:863-864`) likewise.
   - **No allowance moves.** With Decision 5, numpy's `no-dup` classes match again, so no class,
     gap, trap entry, golden or `tests/upstream/*` allowance is edited. If the build finds one
     must move, it is a judge change, traced as above, and named in the landing notes.

9. **Fuel and bytes: measured, bounded, accepted with their causes.** Every fuel and byte metric
   moves. The ratchet's tolerance is 0.01% for fuel and zero for bytes (`scoreboard.py:31`,
   `:162-163`), so the run is red on growth until accepted.
   - **The measurement.** The builder runs the full judge (`uv run pytest -n 6`) on its set and
     writes a table of every fuel and byte metric against `accepted.json`: rows up, rows down,
     median, minimum, maximum, and the sum, per tier (the trial's figures are in "The trial"). For
     the bytes it writes the section sizes of `python.wasm` against the accepted one (the trial:
     code +45,304, name +17,763, data +4,256), and names the largest functions that grew, from the
     name section. Causes are labelled: the new libc functions and libc++ 23 (EXECUTED, the
     function count +69), the backend's choices (INFERRED).
   - **The bound.** A fuel row that rises more than 1% is traced to a measured cause before it is
     accepted; the trial has two, numpy-core (+2.645%, not yet traced) and the compress job
     (+1.428%). The build stops, before any acceptance, if any one of these holds: a fuel row rises
     more than 3%; the sum of the
     judge's fuel rises more than 1% (the trial: +0.08%); `python.wasm` or the snapshot grows more
     than 1% (the trial: +0.164% and +0.138%); the zip changes beyond `_sysconfigdata`. After the
     trace, a cause that is the toolchain's own (a libm routine, a libc path, a backend choice) is
     accepted with its numbers; a cause in a recipe is fixed.
   - **How numpy-core's rise is traced.** Run numpy-core's test files one at a time, with the
     group's own driver and stage, on 0.1.0a7's set and on the new one, and compare fuel per file;
     then, inside the file that carries the rise, per test. Spec 073 saw this group move +2.21% on
     its own set from which module the suite imported first (073's Landing notes), so the trace
     also runs the new set twice to confirm the number is stable. The cause, or "not found after two
     attempts" (AGENTS.md rule 7), goes in the landing notes and in the growth reason.
   - **What is never accepted.** A lost pass, a group whose pass count falls, a golden that moves
     untraced, a new import or export, a host whose `SHA256SUMS` differs. Each stops the build;
     after two failed attempts on one hypothesis the builder writes it down (AGENTS.md rule 7).
   - **The landing's flags** (the lane's): `--accept "<spec 086: wasi-sdk 34 (clang 23.1.0,
     wasi-libc 2e6fb9d8): every artifact's bytes move once>"`, `--accept-judge "<the three checks
     of Decision 7 and tests/cpython_configure.txt>"`, `--accept-growth "<the toolchain move, with
     the measured table: N fuel rows up, M down, the range, the sum; python.wasm +X bytes, code +C,
     name +N, data +D>"`.

10. **The order with the specifications in flight.** The roadmap's landing order is 083, 039, 073,
    085, 084, 043 (built or confirmed), with 086 built now in 037's slot (`../roadmap.md`, "In
    flight"). 086 is one build slot of four.
    - **Every build-class specification that lands before 086** changes main under 086. At each,
      086 rebases, rebuilds from empty `downloads/` and `build/` on macOS, re-runs criterion 3's
      same-bytes builds if the rebase touched a recipe hunk, and re-measures Decision 9's table.
      A rebase that changes 086's own recipe hunks gets a delta review (§5.7).
    - **039** (tier A; build-class, pure Python, being landed): its pins sit beside 086's in
      `SHA256SUMS` and `00_download.sh` (text neighbours only). Its fuel bounds per zip member
      (`20_000_000 + 6_000*(members-1_758)`) are relative and are re-run, not restated.
    - **043** (matplotlib M2; build-class; adds contourpy's C++ with `-Dwerror=false` and a qhull
      patch): whichever lands second rebuilds with both. Its contourpy objects then compile with
      clang 23: the builder checks step 60's constructor list (043 adds `_GLOBAL__sub_I_*` names;
      clang can renumber `__cxx_global_var_init.N`) and the warnings (no `-Werror`, READ). Its
      recorded fuel and sizes are re-measured by the later one.
    - **073** (`run` keeps an unclosed file's bytes; build-class, `reactor_main.c` and
      `reactor_bootstrap.py`): no shared hunk. The later one rebuilds and re-measures 073's fuel
      table (the snapshot's start, about +28 M; check (b)'s ratio).
    - **085** (gather checks what it trusts; build-class only for `release.yml`): no shared file.
      It already writes question 105's answer in. G7 and its set hash stay exact, which 086 makes
      true for scipy too.
    - **083** (parallel-safe, lands next): judge only. Its checks compare two runs, so they hold;
      its absolute fuel figures are re-measured by the later one.
    - **084** (parallel-safe): directory depth, not stack depth; unaffected.
    - **078** (parallel-safe): Decision 8 above.
    - **087** (build-class; carries `recipes/patches/regex-2026.9.29/0002-timeout-ticks.patch` and a
      `MODIFIED` line in `assemble_artifacts.py`): no shared hunk. The later one rebuilds; 087's
      `python.wasm` bytes (+202), its fuel figures and its Decision 6 depth table (XPath and XSLT
      depths; 087 says 086 re-measures them, its lines 319 and 393) are re-measured on the later
      set. Its patch applies on clang 23 unchanged (it is C source; step 53 prints 0 warnings on 34,
      EXECUTED).
    - **037** (scipy; built, waiting): **rebases onto 086 after 086 lands.** At that rebase it:
      deletes `recipes/same_bytes_exceptions.toml`, `scripts/same_bytes.py`, `scripts/compare_sets.py`,
      `tests/unit/test_same_bytes.py` and `tests/unit/fixtures/same_bytes_ducc0.json`; removes the
      `SAME_BYTES_RECIPE` reading and the `x-same-bytes-exception` line from
      `scripts/assemble_artifacts.py` (step 90 would crash on the missing file otherwise); restores
      main's `same-bytes` job in `release.yml` (`permissions: {}`, the `cmp` of every rebuild's
      `SHA256SUMS` and the wheel comparison) and main's rules in `tests/harness/scan.py`
      (`rebuild_gate_errors`, `JOB_PERMISSIONS["same-bytes"]`) and `tests/unit/test_scan.py`;
      removes the exception's README (four places) and CHANGELOG lines and its row in
      `context/upstream/README.md`; and turns `test_the_same_bytes_exception_is_still_needed` into
      its opposite: `pyduccfft.cxx`'s compile command run three times gives **one** hash. Its
      criterion 3 then holds as first written (one `SHA256SUMS` from every host, no exception);
      its OpenBLAS (3,782 compiles) and scipy (910) objects compile with clang 23 for the first time
      there, so 037 runs its own compile-twice comparison over all of them on macOS and in the
      linux/arm64 container, and the release dry run. Spec 037's Decision 17 amendment
      (its lines 735-748) already lists these removals.
    - **038, 044, 045** arrive after 037, built on 34 from the start.

11. **Documentation.** The README's reproducibility paragraph names wasi-sdk 34 and clang 23.1.0
    and says every build host gives the same bytes with no exception. Its platform facts gain
    Decision 6's three attributes ("exist and raise `ENOTSUP`, as `os.dup` does"). `README.md:16`
    and the CHANGELOG's history keep their 33 sentences (history). The CHANGELOG's next alpha
    section says: the toolchain is wasi-sdk 34 (clang 23.1.0, wasi-libc `2e6fb9d8`, musl 1.2.6);
    every artifact's bytes changed; the new `fcntl` refusal and its upstream sheet; the three new
    attributes. The roadmap's reservation for 086 points here.

## Intent

Move the pinned toolchain from wasi-sdk 33 to wasi-sdk 34 so that the compiler gives the same
bytes for the same source on every run and every host, scipy's ducc0 included, and so spec 037
needs no exception. Keep what a guest program sees the same, except three new functions that fail
as `os.dup` already does, which are recorded and documented. Measure every number that moves and
accept it with its cause.

## Design

1. Change the pins (Decision 1) and the two `+m` names (Decision 2). Fix the comments that name 33
   (Decision 3, Decision 4).
2. Write Decision 7's checks and the recorded list; see each fail as it says.
3. Add `recipes/fcntl_dup_refusal.c` and its wrap flag to step 60's guard compile (Decision 5);
   draft the facts sheet.
4. Build on macOS from empty `downloads/` and `build/`. Run the full judge. Write Decision 9's
   table. Stop on its bound.
5. Prove the bytes (criterion 3), then the README, the CHANGELOG and the roadmap line.

## Scope

- **In:** the pins, the two names, the `fcntl` refusal, the recorded configure results, three
  checks, the README and CHANGELOG lines, re-measured numbers.
- **Out:**
  - **Removing spec 037's exception.** It is not on main; 037 does it at its rebase (Decision 10).
  - **The x86-64 fallback's removal.** `clang-emulated` stays switched off for one release, as spec
    059 decided. Whether wasi-sdk 34's two clang builds agree without `-ffp-contract=off` is not
    asked here: the flag stays.
  - **Silencing `-Wunused-template`.**
  - **078's wider window**, after 086.
  - **GB18030.** Still musl 1.2.6's decoder.
  - **Wall-clock.** No check reads a clock (§4.9). The trial's build times (10 min 58 s, then
    7 min 46 s on macOS; 6 min 23 s and 6 min 9 s in the arm64 container; 24 min 37 s in the amd64
    container under Rosetta) are benchmark facts.

## Acceptance criteria

1. **Seen failing first**, each quoted in the landing notes: check (a) on today's tree gives two
   objects; check (b) on the trial-like set (no refusal) names errno 28; check (c) against a 33
   build tree names the ten macros. Then the recipe changes.
2. **The pins.** `downloads/SHA256SUMS` holds exactly Decision 1's fifteen lines in place of 33's
   fifteen; `scripts/00_download.sh` fetches each from a literal URL; a build from empty
   `downloads/` verifies all of them (`downloads: N pins, N fetched, N verified`). No `33.0`,
   `161b3195` or `4434dabb` remains in `scripts/`, `recipes/` (outside history comments) or
   `downloads/SHA256SUMS`.
3. **The same bytes, with no exception.**
   - macOS: two builds from empty `build/` write the same `SHA256SUMS`, byte for byte.
   - The linux/arm64 research container: two builds from empty `downloads/` and `build/` write that
     same `SHA256SUMS`.
   - The linux/amd64 research container (Rosetta, a correctness run): one build writes it too.
   - Check (a) passes on each host's SDK (macOS, and in both containers: the x86_64 and aarch64
     Linux clangs).
   - The landing notes list the five `SHA256SUMS` hashes. One file, or the build stops.
4. **Nothing a program sees moves but Decision 6's three attributes.** The full judge's goldens,
   classes, trap entries and allowances are unchanged and pass; numpy-core's `no-dup` classes
   match `Errno 58` again; `python.wasm`'s imports are the same 43 and its exports the same.
5. **Decision 9's table** is in the landing notes, inside its bound, with causes labelled, and with
   the README numbers re-measured where they moved.
6. **The dry run.** One `workflow_dispatch` run of `release.yml` on main's exact commit after the
   landing passes every job on the three systems, `same-bytes` included, with no exception. No
   tag before it passes (AGENTS.md rule 6b).
7. **The judge.** `uv run pytest` is green and accepted by the lane with Decision 9's three flags;
   lost 0. `ruff check` and `ruff format --check` are clean.
8. **The record.** The facts sheet, the README, the CHANGELOG, the libxml2 sheet's reason and the
   roadmap line exist as Decisions 4, 5 and 11 say.

## For the owner

1. **Nothing blocks the build.** Every choice above is decided. Two are worth knowing:
   - **Guest programs gain `os.dup2`, `os.pipe2` and `time.pthread_getcpuclockid`**, each raising
     `ENOTSUP` (Decision 6). This is what wasi-libc 34 provides. Holding them out would take
     forced `#undef`s in CPython's compile and a `dup2` symbol clash risk. **Recommendation:
     accept** (as decided).
   - **A second link-time refusal joins `iconv_refusals.c`**, so `os.dup` keeps `ENOTSUP` (Decision
     5). It goes when wasi-libc fixes the header-and-`fcntl` mismatch. A new facts sheet,
     `upstream/25-wasi-libc-fcntl-dupfd/`, is yours to send. **Recommendation: send it** once 086
     lands; the fix is one line.
2. **The brief's "wasi-sdk 32" was 33.** No decision; recorded above.
