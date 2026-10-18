# 059 — The x86_64 rebuild runs natively

- **Status:** confirmed for build 2026-10-18 (N1 and N2 written in and checked by the lane:
  `build/reviews-evidence/059-spec/059-the-x86-64-rebuild-runs-natively-spec-2026-10-18-confirmation.md`
  in the main tree); building on this branch, rebased onto main `dfa820c` (023 landed). Drafted 2026-10-18 on `spec/059-the-x86-64-rebuild-runs-natively` from main
  `d68a594`, where the owner's decision is recorded (`../decisions.md`, "The x86_64 rebuild
  without emulation (2026-10-18)"). The pre-build review
  (`build/reviews-evidence/059-spec/059-the-x86-64-rebuild-runs-natively-spec-2026-10-18.md` in
  the main tree, git-ignored; copied to `../reviews/` by the lane) said "ready once F1 to F3 are
  written in"; its confirmation (`…-confirmation.md` beside it) confirmed F1 to F10 and raised N1
  and N2, two sentences each, which the lane checks without another round. All are written in, and
  the Disposition below says where. Build-class: it builds after spec 023 lands and before spec
  057 (which edits the same workflow and rebases onto this).
- **Owner:** Clay Gendron
- **Kind:** build-class: compile flags (one flag, `-ffp-contract=off`, on every compile in the
  recipe), the release workflow's x86_64 job; a judge change (one rule check replaced, one added,
  one workflow constant, one need); the hashes of `python.wasm`, `python-snapshot.wasm`,
  `MANIFEST` and so `SHA256SUMS` change once (the zip is expected to stay; Decision 6). It
  changes `scripts/line.conf`, `scripts/00_download.sh`, `scripts/steps/10_tools.sh`,
  `.github/workflows/release.yml`, `tests/`, the upstream draft
  `context/upstream/4-llvm-wasm-isel-slot-order/`, `README.md`, `CHANGELOG.md`, and adds
  amendment lines to spec 040 (Decisions 2, 4 and 11). It changes no pin, no source tree, no
  carried patch, no `src/` file.
- **Depends on:** 023 (matplotlib M1, in the build-class slot now: its steps 37 and 55 add C and
  C++ compiles that this specification's flag must reach; Decision 7). Also 012 (the host keys,
  the host-neutral runtime, `rebuild` and `same-bytes`), 040 (the emulated compiler this
  specification switches off and keeps as the fallback), 050 (the upstream suites in the guest,
  whose `passes` are this specification's numerics check) and 020 (`MANIFEST`'s recipe hashes).
  All but 023 are landed.
- **Research it stands on:** `../research/2026-10-18-byte-identical-wasm-builds-prior-art.md`
  (EXECUTED there: `-ffp-contract=off` makes the pinned x86_64 and aarch64 clangs emit the same
  object, `2914eb833ad62c93`, for the build's own preprocessed `npy_math_complex.c`, and
  `bca38dcd95e249c3` for the nine-line reproducer; every other flag tried still differs; the IR
  holds 78 `llvm.fmuladd` calls that the flag removes; the object's call set is unchanged; READ
  there: no project studied emulates a compiler to make a second architecture agree, and none
  normalizes compiler output), with its text evidence in
  `../research/2026-10-18-byte-identical-wasm-builds-prior-art/`. Spec 040's research
  (`../research/2026-10-17-x86-64-rebuilds-differ-in-one-function.md` and its folder): the
  difference is one function's two `fp128` libcall result slots, first visible after `wasm-isel`,
  deterministic per compiler build. Four more facts were run while drafting this specification,
  in the memo's scratch folder, on the two pinned SDKs (hashes checked), labelled EXECUTED in
  Decision 1; the pre-build review re-ran them and added its own (the override family, the
  constant-fold case, the pragmas; its `probe/` and `x86/` folders), cited where used. The
  builder reproduces all of them into the research folder first (Decision 10).

## The problem

Spec 040 put x86_64 Linux into the same-bytes gate by compiling there with the arm64 Linux
wasi-sdk's clang under a pinned `qemu-aarch64`. It works: three hosts write one `SHA256SUMS`. It
costs an hour: the x86_64 rebuild took 64.5 minutes on GitHub's `ubuntu-24.04` against 7m16s for
the arm64 rebuild (spec 040's landing notes, dry run 2; benchmark facts, §4.9). The owner asked
whether that hour buys anything, and the research found a cheaper way to the same bytes.

The x86_64 clang and the aarch64 clangs differ only where the IR holds `llvm.fmuladd` on `long
double`. Clang emits that intrinsic for `a*b+c` in one expression under its default
`-ffp-contract=on`, so the backend may fuse the two operations. wasm32 has nothing to fuse with
(no fused multiply-add outside relaxed SIMD, which this build does not enable), so the intrinsic
is lowered back into a multiply and an add, and that lowering is where the two compiler builds
order two 16-byte result slots differently. With `-ffp-contract=off` clang emits a plain `fmul`
and `fadd`, the construct is gone, and both compilers write the same object. Run-time arithmetic is
the same either way on this target; a value the compiler folds at compile time can move by one
rounding (Decision 1). The bytes move: the optimizer can share a multiply between two plain
expressions where it could not inside the intrinsic, so the reactor's hash moves once.

So: one flag, in one place every compile passes through, and the x86_64 host compiles with its own
clang in about the time the arm64 host takes. The emulation stays in the tree, switched off, for
one release, as the parachute spec 040's Decision 11 already describes.

## Decisions

1. **The flag lives in the compiler's own configuration files, so no compile can miss it.**
   wasi-sdk's `bin/clang.cfg` and `bin/clang++.cfg` hold one line each
   (`--sysroot=<CFGDIR>/../share/wasi-sysroot`), and clang reads the one for its driver name on
   every call. Step 10 appends `-ffp-contract=off` as a second line to both files of the tree
   whose clang compiles (`$CSDK`; on the arm64 hosts that is `$SDK`), and, when the two trees
   differ (the switch of Decision 3 thrown), to `$SDK`'s two files as well, so no tree under
   `build/tools/` holds an unedited pair (the review's F10). Facts, each EXECUTED while drafting,
   with the pinned arm64 macOS SDK natively and the pinned x86_64 Linux SDK in the research
   container (`linux/amd64`, under Rosetta), the two files edited exactly so; the review re-ran each
   and extended them (its "What was verified"):
   - `clang -v`, with or without `--target`, and `clang++ -v` each print `Configuration file:
     …/bin/clang.cfg` or `clang++.cfg` (spec 040's gate already relies on the second). The review
     adds: `clang-22`, `wasm32-wasip1-clang`, `wasm32-wasip1-clang++`, `wasm32-wasi-clang`,
     `clang -x c++` and `--driver-mode=g++` all read the file and carry the flag.
   - `clang --target=wasm32-wasip1 -### -c x.c`, the same with `-E`, and `clang++ … -### -c -x
     c++ x.c` each show `-ffp-contract=off` on the `-cc1` line.
   - The build's preprocessed `npy_math_complex.c` (324,353 bytes, `2193b9bd4d40aadc`), compiled
     with the build's code-generation flags and **no flag on the command line**, gives
     `2914eb833ad62c93` from both SDKs: the object the memo got with the flag on the command line.
   - Compile, link, and compile-and-link of a hello-world through the edited `clang` with
     `-Werror` all succeed; the review adds `-Wunused-command-line-argument`, `-E`, `-M`,
     `-fsyntax-only` and a stdin compile. A configuration-file option raises no unused-argument
     warning at link, so no autoconf probe (CPython's, xz's, FreeType's) changes its answer. The
     flag changes no predefined macro (`clang -dM -E` equal with and without it; the review).
   - `clang-cpp` reads no configuration file (its `-v` prints none and its `-cc1` line carries
     the default `-ffp-contract=on`). It preprocesses only and generates no code, so it needs
     none. Its predefined macros equal `clang -E`'s (the review), so CPython's `CPP=clang-cpp`
     sees nothing different.
   - **A later command-line option overrides the file.** `-ffp-contract=on` restores the old
     `9afcef294ca52dad` on the reproducer (EXECUTED). The review showed the whole family that
     does the same: `-ffp-model=precise` gives `-ffp-contract=on` (and the numpy file then
     compiles to the old pair, `20ef3344…` against `d3689743…`, EXECUTED there); `-ffast-math`,
     `-Ofast`, `-funsafe-math-optimizations` and `-ffp-model=fast` give `fast`;
     `--no-default-config` drops the file; `--config` names another. So Decision 4's rule forbids
     that whole family on any command line the recipe writes or any build system emits, and
     Decision 2's gate accepts no value but `off`; the file is the one place.
   - **Why the configuration file, not the flags of each build.** The alternative is eight places
     today (CPython's `CFLAGS` through the WASI driver, two cross files' `c_args` and `cpp_args`,
     steps 30 and 35's `CFLAGS` and direct compiles, step 60's reactor compile), plus one or more
     for each package 023 and 037 add, kept equal by audit. The configuration file is read by every
     caller that exists or will exist: CPython's `Platforms/WASI` driver (`$WASI_SDK_PATH/bin/clang`),
     `scripts/wasi-cc` and `wasi-cxx` (`$WASI_SDK_PATH/bin/clang` and `clang++`), steps 30, 35, 37,
     55 and 60 (`$SDK/bin/clang`, `clang++`, or `make -n`'s commands), meson, autoconf and
     CMake-less direct compiles alike. A triple-named file (`bin/wasm32-wasip1.cfg`) is not loaded
     while `clang.cfg` exists (the review), so the existing file is the one that must carry it. It is
     a recipe item of §4.1's first kind, like the launcher and the neutral runtime: a change to the
     downloaded toolchain tree under `build/tools/`, made by step 10 (a hashed recipe file in
     `MANIFEST`), never to a source tree; spec 020's tree check reads source trees only (the review).
   - **Why `off`, not `fast`.** `fast` gave the same object (the memo), because it also emits
     plain `fmul` and `fadd` and leaves fusion to a backend that has none. `off` says what it does
     and cannot change if a future wasi-sdk enables relaxed SIMD by default; `fast` could then fuse.
   - **What the flag changes in results, exactly** (the review's F2). *Run-time arithmetic does not
     change*: `double a*b+c` is `f64.mul`, `f64.add` both ways, and `long double a*b+c` is
     `__multf3`, `__addtf3` both ways, with no `fmal` (EXECUTED by the review; the memo's unchanged
     call set). *A value the compiler folds can change by one rounding*: LLVM folds
     `llvm.fmuladd` with constant operands as one fused operation (one rounding), while wasm32
     evaluates the same expression at run time as a multiply and an add (two roundings). EXECUTED
     by the review with the pinned clang at `-O2`: `g(0.1, 10.0, -1.0)` with `g(a,b,c) = a*b+c`,
     inlined and folded, returns `0x1p-54` under the default and `0x0p0` under `off`; at run time
     the expression gives `0` either way. So wherever inlining and constant propagation folded an
     `a*b+c`, the flag moves that constant from the fused value to the value the run time computes.
     That is the intended direction (the binary then agrees with itself), and it is rare: the
     goldens print floats to nine digits (`jobs.compare`) and the upstream suites use tolerances,
     so most such moves are invisible. Decision 6 says what happens when one is visible.
   - **Idempotent.** Step 10 removes and re-unpacks `build/tools/` first, so the line is appended
     exactly once per build. The gate (Decision 2) also fails if the line is absent or doubled.

2. **Step 10's gate proves the flag is in force, and that nothing else is.** After the write (and
   after the emulation layout, when it is on), step 10 runs `$SDK/bin/clang --target=wasm32-wasip1
   -### -c "$G/probe.c"` and `$SDK/bin/clang++ --target=wasm32-wasip1 -### -c -x c++
   "$G/probe.c"`, writes each output under `build/compiler-gate/`, and stops with one line unless
   each `-cc1` line holds `-ffp-contract=off` exactly once and **no other `-ffp-contract=` value
   at all** (not merely no `on`; the review's F1). It prints `compiler gate: clang contracts
   nothing (-ffp-contract=off)` and the same for `clang++`. It also requires each edited
   configuration file (both trees', when two exist) to hold exactly one `-ffp-contract=off` line.
   The gate runs in the build's own environment, so a `CCC_OVERRIDE_OPTIONS` that changed the
   driver's options would show on the `-cc1` line and stop the build (the review); step 35 also runs
   every tool under `env -i`. On x86_64 with the emulation on, `$SDK/bin/clang` is the link to the
   launcher and the probe reaches `$CSDK`'s files through it. The gate cannot see a flag one
   build system adds to one compile later; Decision 4's record scan is the guard for those.

3. **x86_64 compiles with its own clang; the emulation stays in the tree, switched off, for one
   release.**
   - `scripts/line.conf`: `LINUX_X86_64_COMPILER_SDK_DIR=wasi-sdk-33.0-x86_64-linux`. That line
     is the switch. With it, `CSDK` equals `SDK` on every host, and step 10's emulation branch
     (`if [ "$CSDK" != "$SDK" ]`) does not run. The comment above the compiler lines says what the
     switch does and names this specification.
   - **Kept, unchanged:** `scripts/clang-emulated`; the five `LINUX_X86_64_*_DEB` names in
     `line.conf`; their five pins and the arm64 Linux SDK's pin in `downloads/SHA256SUMS`; step 10's
     emulation branch and its five probes; `tests/unit/test_clang_emulated.py`; the `-strace`
     loader probe. `MANIFEST` keeps listing the pins (it lists every host's pins).
   - **The fetch becomes conditional.** In `00_download.sh`'s `LINUX_X86_64` branch, the six `get`
     lines for the arm64 Linux SDK and the five Debian packages move inside
     `if [ "$COMPILER_SDK_DIR" != "$WASI_SDK_DIR" ]; then … fi`. A native build never asks
     `snapshot.debian.org` for 75 MB it does not use, and a throttled mirror cannot fail a build
     that does not need it (spec 040, Decision 3's own worry). The lines stay literal, one pin per
     line, inside the key's `case` arm, so `scan.host_case_branches` still counts them as fetched in
     that branch (READ: it takes every `get` line between the arm's label and its `;;`).
   - **The fallback, exactly** (the review's F3). Throwing the switch is one line in the recipe
     and two in the judge, all named here so the day needs no design:
     1. `scripts/line.conf`: `LINUX_X86_64_COMPILER_SDK_DIR=wasi-sdk-33.0-arm64-linux`;
     2. `.github/workflows/release.yml`: `rebuild`'s `include` gives `ubuntu-24.04` `timeout: 360`
        again (Decision 5), with its comment;
     3. `tests/harness/scan.py`: `REBUILD_TIMEOUTS["ubuntu-24.04"] = 360`, and the matching case in
        `tests/unit/test_scan.py`;
     accepted by the lane with `--accept-judge "<the fallback's timeout>"`. Decision 4's rule check
     passes in both positions of the switch by construction (its first bullet). Nothing else moves:
     the flag stays (it is right on every host, and the emulated clang then compiles with it, through
     `$CSDK`'s edited files), the download fetches its six pins, step 10 lays out and probes the
     emulated compiler and then runs Decision 2's probes through it, and the gate stays three hosts.
     **Criterion 3b proves the fallback runnable before landing**, by executing step 10 with the
     switch thrown in the `linux/amd64` container.
   - **When the emulation leaves.** "The first release" is the first alpha published after this
     specification lands whose tag run's native x86_64 rebuild passed `same-bytes` (the review's
     F9). After it, a later build-class specification of its own may remove: `scripts/clang-emulated`,
     the five emulation names and their comment from `line.conf`, the emulation loop from `line.sh`,
     the conditional block from `00_download.sh`, the six pins from `downloads/SHA256SUMS`, step 10's
     emulation branch and its probes and the second tree's configuration write,
     `tests/unit/test_clang_emulated.py`, the emulation half of Decision 4's rule check and its unit
     mutations, `scan.EMULATION_NAMES`, `STEP_10_WORDS`, `STEP_10_STRACE`, `LAUNCHER_FLAGS` and
     `LAUNCHER_MODES`, and the README's sentence about the fallback. `COMPILER_SDK_DIR` stays, each
     host naming its own SDK, and so does the flag. The CHANGELOG records it. That change is drafted
     when that release has shipped, not here, so this specification stays small and its evidence
     stays one dry run.
   - **Between landing and the dry run** (the review's F9): no release tag. AGENTS.md rule 6b
     already says it ("Tag only what a dry run passed": dispatch the release workflow on main's exact
     commit and wait for every job to pass on all three systems); this specification repeats it
     because real `ubuntu-24.04` is first seen in that dry run (criterion 6), every x86_64 fact before
     it being Rosetta's. A tag run in that window would fail at `same-bytes` and publish nothing, but
     it would spend an alpha's security review.

4. **The judge.** Each check is written, and seen failing, before the code it guards (AGENTS.md
   rule 3). The judge changes, so the landing uses `--accept-judge` with its reason.
   - **`test_every_compile_contracts_nothing`** (v1.5, `test_v1_5_rebuild_from_pins.py`;
     `scan.fp_contract_errors`). **The forbidden family** is one constant,
     `scan.FP_CONTRACT_OVERRIDES`: any `-ffp-contract=` whose value is not `off`, `-ffp-model=`,
     `-ffast-math`, `-Ofast`, `-funsafe-math-optimizations`, `--no-default-config` and `--config`
     (the review's F1; each EXECUTED there as overriding or dropping the file). A hit names the file,
     the line or the command, and the option. **A member counts only as a whole token on a
     compiler's command line or in a compile-flag variable** (the confirmation's N1), never as a
     substring of an arbitrary line: a compiler command line is a `compile_commands.json` entry's
     `command` (split as a shell would), a line of `build/link/make-n.txt` or
     `reactor-commands.txt` whose first word ends in `clang` or `clang++`, or a Makefile recipe
     line that invokes `$(CC)`, `$(CXX)`, `$(CPP)` or a word ending in `clang` or `clang++`; a
     compile-flag variable is a Makefile assignment whose name is `CC`, `CXX` or `CPP`, or holds
     `CFLAGS`, `CXXFLAGS`, `CPPFLAGS`, `CCSHARED` or `OPT` (so `CFLAGS_NODIST`, `EXTRA_CFLAGS`,
     `PY_STDMODULE_CFLAGS`, `CONFIGURE_CFLAGS_NODIST` and every `MODULE_*_CFLAGS` are read). Why:
     `--config` is wasmtime's option too, and CPython's cross-build Makefile carries it on
     `HOSTRUNNER=` (line 425) and inside `PYTHON_FOR_BUILD=` (line 429), `wasmtime run … --config
     <path>/wasmtime.toml`, neither of which compiles anything (EXECUTED by the confirmation). The
     token rule skips them because of what they are, not by name: no line is exempted, and a
     compile-flag variable or compiler line that gained `--config` would still be a hit. Four parts.
     - *The recipe, always:* `scripts/steps/10_tools.sh`, read without its comments
       (`scan.code_text`), names both configuration files (`clang.cfg`, `clang++.cfg`), the flag
       `-ffp-contract=off`, and the probe (`-###` with `-cc1` matched), so a comment satisfies
       nothing; and no other tracked file under `scripts/` or `recipes/` holds any member of the
       family (nor `-ffp-contract=` in any form outside step 10), so no recipe file can override the
       file's setting. This part covers every compile the recipe writes by hand: steps 30 and 35's
       `CFLAGS` and direct compiles, 023's step 37 (qhull) and step 55 (Pillow, kiwisolver) source
       lists, and the cross files' `c_args` and `cpp_args`.
     - *The build's compile records, when present* (the review's F4; the confirmation's N2): the
       expected records are a judge constant, `scan.MESON_BUILDS`, the meson build folders under
       `build/` by name: today `("numpy-build", "pandas-build")`; 023 extends it with its five
       (`freetype-build`, `harfbuzz-build`, `sheenbidi-build`, `libraqm-build`, `matplotlib-build`),
       and every later specification that adds a meson build extends it in the same change. Why a
       constant and not the steps' text: the steps name their folders through variables and loops
       (`meson setup "$BUILD" …`; 023's `meson setup "$dir" …` runs four times from one cross file),
       so a text parse would read `$dir`; and the cross files stay unchanged and a comment satisfies
       nothing. The constant is code the judge reads and a mutation can break. Two rules keep it
       honest: **every listed folder's `compile_commands.json` must exist once any exists** (a
       record that vanished would otherwise only lower a count), and **every `compile_commands.json`
       under `build/*/` must be listed** (an unlisted meson build is a breach, so the constant cannot
       fall behind the tree). It also reads the Makefiles the autoconf builds generate
       (`build/zlib-build/Makefile`, `build/xz-build/Makefile` and
       `build/xz-build/src/liblzma/Makefile`), step 60's `build/link/make-n.txt` and
       `build/link/reactor-commands.txt`, and **the whole** of CPython's
       `build/Python-<version>/cross-build/wasm32-wasip1/Makefile` (every compile-flag variable and
       every compiler recipe line, by the token rule above: `CFLAGS_NODIST`, `EXTRA_CFLAGS`,
       `PY_STDMODULE_CFLAGS` and the per-module `MODULE_*_CFLAGS` lines included; the review's F1).
       No compiler command or compile-flag variable may hold a member of the family. Each record
       read is named in the check's output with its command or line count, so the review sees what
       it read. A later make-based build that leaves no record (037's OpenBLAS) saves its `make -n`
       output under `build/` and joins this list when it lands; this specification says so so that
       037's builder knows. With no record present (a checkout without a build) this part is
       `blocked` by a new need, `compile records` (`tests/harness/needs.py`), named in the
       scoreboard's blocked list. The release workflow's `build` job has every record.
     - *The source trees, when present* (the review's F5): a source pragma overrides the file per
       block: `#pragma STDC FP_CONTRACT ON` and `#pragma clang fp contract(on)` or `(fast)` bring
       `llvm.fmuladd` back under the edited file (EXECUTED by the review). None is in a compiled file
       today or in 023's trees (the review's grep; CPython's mpdecimal `float_control` is MSVC-only,
       OpenBLAS 0.3.34's are `contract(off)` in non-wasm kernels). The check greps every unpacked
       source tree under `build/` (the ones `needs.SOURCE_COMPONENTS` names, plus Cython's generated
       `.c` under the meson build folders) for `FP_CONTRACT ON` and `fp contract(on|fast)` and fails
       on any hit, naming the file. A hit in a file the build never compiles is answered by an
       allowance in `scan.py` naming the file and why, as a judge change with its reason; a hit in a
       compiled file is a tie waiting to happen and is fixed by a carried patch or an upstream
       release, never by an allowance. The pragmas are otherwise outside the gate's reach, and the
       three-host `same-bytes` comparison is the backstop for anything this grep misses.
     - *The compiler itself, when present:* with `build/tools/<WASI_SDK_DIR>/bin/clang` present,
       the check runs Decision 2's two `-###` probes itself (through the judge's `subprocess`, on
       a one-line C file in a temporary folder) and asserts the `-cc1` lines as the gate does: exactly
       one `-ffp-contract=off`, no other `-ffp-contract=` value. Blocked by the same need otherwise.
     On today's tree it fails: step 10 names neither file nor the flag.
   - **`test_every_host_compiles_natively_with_the_fallback_kept`** (rules, `test_rules.py`;
     `scan.compiler_table_errors`, rewritten) replaces `test_x86_64_compiles_with_an_aarch64_compiler`,
     which the landing retires with `--retire` (the ratchet turns a vanished check red,
     `../progress/README.md`). It requires:
     - every host key has `COMPILER_SDK_DIR`, **equal to its own `WASI_SDK_DIR`, or else equal to
       another key's own `WASI_SDK_DIR` while carrying all five emulation names** (the switch thrown;
       the review's F3: one rule, true in both positions). A `COMPILER_SDK_DIR` that is neither, or a
       foreign SDK without the five names, is a breach;
     - exactly one key, `LINUX_X86_64`, carries the five emulation names (the fallback), each
       naming a pinned file fetched in that key's branch, and that key's branch fetches the arm64
       Linux SDK too; a key with some but not all five names, or a second key with any, is a breach;
     - `10_tools.sh`, without comments, still names `clang-emulated`, `aarch64-root`, `ld.so.cache`,
       `InstalledDir` and `clang-cpp` and the `-strace` probe (the fallback is runnable), and
       `scripts/clang-emulated` still holds its three `-U` flags, its `QEMU_` clearing and its
       three name-to-mode arms (spec 040, Decision 7, unchanged).
     On today's `line.conf` the rewritten check **passes**: today's line is the switch thrown with
     the five names present, which the first bullet allows. So it is not seen red on today's tree;
     it is proven by its unit mutations, and the retired check is seen vanishing in the ratchet's
     `ABSENT` line. The landing notes say so. `tests/unit/test_scan.py`'s compiler-table cases are
     rewritten to the new rules, one mutation per rule (the switch thrown without the names; a
     foreign SDK that is no host's own; a second key with the names; four names; a name not fetched;
     the launcher missing a flag; step 10 missing a word), each naming its breach.
   - **`test_release_workflow_rebuilds_on_two_more_hosts`** keeps its name. `scan.REBUILD_TIMEOUTS`
     becomes `{"ubuntu-24.04-arm": 120, "ubuntu-24.04": 120}`. The workflow check otherwise stands
     (both runners in the matrix and in both `same-bytes` loops, `nproc` and `binfmt_misc` printed:
     the fallback can still be switched on, and the facts cost nothing). On today's workflow it
     fails with `rebuild's matrix does not give ubuntu-24.04 120 minutes`. The matching unit case
     in `test_scan.py` changes with it.
   - **Unchanged and still passing:** `test_every_build_host_has_its_whole_table`,
     `test_toolchain_is_pinned_for_linux_and_macos`, `test_cpp_is_compiled_with_exceptions`, the
     v1.5 zip check, `tests/unit/test_clang_emulated.py` (the launcher is unchanged).
   - The scoreboard's not-machine-checked list gains one line: "source pragmas and compiler
     options outside the scanned records; `same-bytes` is the backstop".

5. **The release workflow: the x86_64 job becomes an ordinary rebuild.** In `rebuild`'s matrix
   `include`, `ubuntu-24.04` gets `timeout: 120`, the same as the arm64 runner: a native rebuild
   is expected near the arm64 one's 7 minutes, and 120 is already six times spec 012's own margin.
   The comments on `rebuild` and `same-bytes` stop describing an emulated compiler; they say every
   host compiles with its own pinned clang and `-ffp-contract=off`, and link this specification.
   The `nproc` and `binfmt_misc` lines stay. Nothing else changes; `attest` and `publish` still need
   `same-bytes`. **Spec 057** lands after this one and rebases onto it (the review's F8); at that
   rebase 057's builder:
   - gives its two rebuild jobs (`rebuild-linux-arm64`, `rebuild-linux-x86-64`) `timeout-minutes:
     120` each, and takes this specification's `REBUILD_TIMEOUTS` values into its rewritten
     `rebuild_gate_errors`;
   - revises 057's Decision 4 sentence "the x86_64 job compiles with the arm64 Linux …" ("What
     two jobs cannot separate"), its Scope bullet "The arm64 Linux wasi-sdk shared by both rebuild
     jobs" and its F2 disposition's "the arm64 Linux wasi-sdk tarball runs on both legs", to say
     each leg compiles with its own host's pinned clang;
   - records the security gain in 057's text: no one tarball is an input to both rebuild votes
     any more. Each leg runs only its own host's compiler, so a tampered arm64 Linux SDK could
     change at most one vote, and `same-bytes` would see the two disagree.
   Nothing here edits a line 057 adds.

6. **The hashes change once, and the ratchet accepts it with its reason.** The flag reaches
   CPython, zlib, bzip2, xz, SQLite, numpy, pandas, the reactor and, after 023, the plot libraries
   and packages, so `python.wasm` and `python-snapshot.wasm` (it follows the reactor) move, and
   `MANIFEST` (recipe hashes: `line.conf`, `00_download.sh`, `10_tools.sh`) with them, and
   `SHA256SUMS` with all three. **The zip is expected to stay** (the review's F6): the flag lives in
   the toolchain's configuration files and never in `CFLAGS`, so `_sysconfigdata` records nothing
   new (INFERRED; the Makefile has no such line). The builder states which of the four moved and why,
   whichever way it falls.
   - **The landing's flags:** `--accept "<spec 059: -ffp-contract=off on every compile; the
     reactor's, the snapshot's and MANIFEST's hashes move once>"`, `--accept-judge "<the two rule
     and v1.5 checks, the need, the timeout constant>"`,
     `--retire tests/checks/test_rules.py::test_x86_64_compiles_with_an_aarch64_compiler`.
   - **`--accept-growth` only if a metric grew, with the measured numbers in its reason.** The
     memo saw 392 fewer instructions in the one numpy object (10,484 to 10,092), so `python.wasm`'s
     `bytes` is expected to fall or stay, and `fuel` to move slightly either way. The landing notes
     record every metric before and after. Growth is accepted only as "the flag's effect", never
     as a quiet by-product.
   - **A moved pass or golden is traced, then disposed of by its cause** (the review's F2). Decision
     1 says run-time arithmetic cannot move and a folded constant can move by one rounding. So:
     - a golden job whose output moves, or an upstream group whose `passes` falls, is first traced
       to the expression (the test's values, the IR of the function with and without the flag);
     - if the cause is a fold (a constant `a*b+c` the compiler evaluated), that is the flag's intended
       effect: the before and after values are recorded in the landing notes, the golden's
       `.expected` or the upstream allowance (`tests/upstream/*.toml`, `expected/`) is changed as a
       judge change with its reason (`--accept-judge "<the fold, the test, the two values>"`, and for a
       fallen `passes` also `--accept-fewer-passes` with the same reason), and the build goes on. A
       correct change does not stop the build;
     - anything else (a run-time difference, an object whose call set or arithmetic opcodes changed
       beyond the shared multiply) stops the build: Decision 1 is then wrong before this specification
       is, and the builder writes it down after two attempts (AGENTS.md rule 7).
     Never is a golden or an allowance edited to turn a run green without that trace in the notes
     (AGENTS.md rule 4).
   - The three hosts' `SHA256SUMS` must be one file, byte for byte, as before. A hash that moves on
     one host and not another is a defect.

7. **023 is covered when this specification rebases after it lands.** 023 adds step 37
   (FreeType, HarfBuzz, SheenBidi, libraqm with meson through `recipes/wasi-plot-libs.cross`;
   qhull by direct compiles), step 55 (Pillow, kiwisolver from source lists; matplotlib with meson
   through `recipes/wasi-matplotlib.cross`), a `pkgconf` install in step 10, stand-ins under
   `recipes/`, and drops `-pthread` from `scripts/wasi-cc`. Every one of its compiles runs
   `$SDK/bin/clang`, `$SDK/bin/clang++`, `scripts/wasi-cc` or `scripts/wasi-cxx`, so Decision 1's
   file reaches them without a line of this specification knowing their names. The review read
   023's seven `compile_commands.json` and its source trees: no member of the family and no pragma
   (EXECUTED there). What the builder does at the rebase:
   - extends `scan.MESON_BUILDS` with 023's five meson build folders (Decision 4) and re-runs the
     records, Makefile, source-tree and static parts over 023's tree (the confirmation read 023's
     nine `compile_commands.json`: no member of the family);
   - merges step 10: 023's `pkgconf` install and this specification's configuration write and
     probe touch different lines of the same file;
   - confirms 023's `test_cpp_is_compiled_with_exceptions` extension (its cross files' C++ flags)
     is untouched: `-fwasm-exceptions` and `-ffp-contract=off` do not interact;
   - records 023's packages' upstream suites, if 023 adds any to spec 050's groups, under
     criterion 4 alongside numpy's and pandas's, and 023's pixel goldens (RGBA buffers compared
     exactly) under Decision 6's trace rule: a pixel that moves is traced to a fold or stops the
     build.
   If 023 has not landed when the lane reaches this specification, this specification builds first
   on main as it stands, and 023's builder gets Decision 1's property for free at its own rebase;
   Decision 4's record check then covers 023's records from 023's first build.

8. **The upstream draft gains the finding.** `context/upstream/4-llvm-wasm-isel-slot-order/issue.md`
   gains a section "Narrowed: the difference needs `llvm.fmuladd` on `fp128`": the two tables from
   the memo (the reproducer and the numpy file, with and without `-ffp-contract=off`, both hosts),
   the sentence that `-ffp-contract=fast` gives the same object as `off`, that `-ffp-model=precise`
   brings the difference back (the review), and that an empty or a large environment moves nothing
   (so the cause is not address-dependent iteration). The guess in "What we would expect" is
   narrowed to the lowering of `FMA`/`fmuladd` into libcalls. The workaround paragraph says the
   project now compiles with `-ffp-contract=off` everywhere and runs x86_64 natively. `notes.md`
   gains "Narrowed (spec 059)" with the memo's commands. The upstream README's row for folder 4
   says the same in its state column. The owner's "run it on real x86_64 first" condition stands;
   nothing is posted by an agent (LLVM's AI policy, as spec 040 recorded).

9. **The fallbacks, in order** (spec 040's Decision 11, amended; the review's F3 and F7).
   - **First, once, a re-run**, for a fetch failure or a lost runner, as 040 says.
   - **Second, the switch** (Decision 3's three-line change set), when the dry run (criterion 6)
     fails on `ubuntu-24.04` with a byte difference in `same-bytes` or a compile failure that
     repeats. It is taken the same day, through the lane, reviewed, with `--accept-judge` for the
     timeout constant, and recorded in the landing notes, the CHANGELOG and the memo's successor. The
     flag stays. The gate stays three hosts. The native x86_64 bytes are then worked on in a memo and
     the switch is turned back by a change of its own.
   - **Third, 040's own last resort, kept:** if the emulated compiler with the flag also fails the
     gate, x86_64 leaves the gate by one reviewed change (`ubuntu-24.04` out of `rebuild`'s matrix
     and `include`, out of both `same-bytes` loops and its two downloads, out of
     `scan.REBUILD_RUNNERS`; the README sentence of spec 012's Decision 8 restored with the run's
     link), exactly as 040's Decision 11 wrote it. It is not dropped; it is third, because two
     cheaper steps now come before it. Spec 012's Decision 8 (x86_64 may be a pinned build host
     outside the gate) is that last resort's basis and is why 012 needs no amendment.
   - The 240-minute trip-wire and the 360-minute limit of 040's Decision 11 apply only while the
     switch is thrown. For the native job the 120-minute timeout is the limit, and a native rebuild
     that nears it is a defect to find, not a time to accept.

10. **The evidence moves into the repository first.** Decision 1's facts ran in the memo's scratch
    folder and the review's. The builder re-runs them from the research folder
    `../research/2026-10-18-byte-identical-wasm-builds-prior-art/`: a script `cfg-route.sh` (the
    two SDKs, each checked against `downloads/SHA256SUMS`; the configuration files edited in a
    scratch copy of each SDK, never in `build/tools/`; the `-v`, `-###`, `-Werror`, `-dM -E` and
    `clang-cpp` probes; the override family, each member shown on the `-cc1` line; the constant-fold
    case with its two values; the pragma case; the numpy object through the edited files on both
    hosts) and its outputs as text (commands, hashes, the `-cc1` lines; no objects, as 847a954 set
    the folder's rule). The preprocessed file is numpy's and wasi-libc's text and is regenerated,
    not committed. The memo is not edited (`../README.md`: a memo is never edited after the fact);
    the folder's `README.md` gains a dated paragraph naming the script and the review's additions.

11. **Documentation.**
    - **README**, "The same bytes from any build host": every host compiles with its own pinned
      wasi-sdk clang, and every compile carries `-ffp-contract=off`, set by step 10 in the
      toolchain's own configuration files (`bin/clang.cfg`, `bin/clang++.cfg`), **so it appears in
      no recorded flag: `sysconfig.get_config_var("CFLAGS")` inside the guest does not show it, and
      a rebuild must not add it to a command line** (the review's F6). Why: the x86_64 and aarch64
      builds of the same clang order two stack slots of one `long double` expression differently
      when the IR holds `llvm.fmuladd` (the memo, the upstream draft). What it changes: run-time
      arithmetic nothing; a compile-time-folded `a*b+c` by one rounding, to the value the run time
      gives. The paragraph about the emulated compiler shrinks to one sentence: the launcher and its
      five pinned Debian packages stay in the tree, switched off, as the fallback until the first
      alpha whose native x86_64 rebuild passed has shipped, and the five licences stay named while
      they do.
    - **CHANGELOG**, under the unreleased section: the x86_64 rebuild runs natively; the flag and
      where it lives; the reactor's, the snapshot's and `MANIFEST`'s hashes change; the fallback kept
      one release; the upstream draft narrowed.
    - **Spec 040** gains three amendment lines (the review's F7), each "Amended by spec 059
      (2026-10-18)": under **Decision 2**, the emulation is switched off and kept one release as the
      fallback, because every compile now carries `-ffp-contract=off`, which makes the two compiler
      builds agree; under **Decision 4**, `LINUX_X86_64_COMPILER_SDK_DIR` names the host's own SDK,
      and the arm64 SDK's name there is the switch that turns the emulation on; under **Decision
      11**, the same-day fallback is the switch, the trip-wire and the 360-minute limit apply only
      while it is thrown, and "x86_64 leaves the gate" is the step after a failed switch. Spec 012's
      text stands: its decisions (the host keys, the neutral runtime, the `rebuild` and
      `same-bytes` jobs, Decision 8's fallback) are untouched, and Decision 8 is the last resort
      above.
    - The workflow's comments, as Decision 5.

12. **The order of work.** This specification is build-class (§5.7). It builds after 023 lands,
    rebasing onto main then, and before 057, which rebases onto it (Decision 5). It changes the
    reactor's hash, so every build-class specification after it measures against its numbers; 057
    changes no byte, so the order between them costs 057 nothing but the rebase.

## Intent

Anyone can rebuild the published sandbox from its pins on arm64 macOS, arm64 Linux or x86_64 Linux,
with that machine's own pinned compiler, and get the same artifact set, byte for byte. CI proves all
three on every release in the time the fastest host takes. Every compile carries `-ffp-contract=off`,
which removes the one construct on which wasi-sdk's two compiler builds disagree; run-time arithmetic
does not change, and a folded constant moves only to the value the run time computes. The emulated
compiler stays one release as the parachute, then leaves.

## Design

```
scripts/line.conf                LINUX_X86_64_COMPILER_SDK_DIR = its own SDK (the switch); comment
scripts/00_download.sh           LINUX_X86_64: the arm64 SDK and five .deb get lines inside
                                 `if COMPILER_SDK_DIR != WASI_SDK_DIR`
scripts/steps/10_tools.sh        append -ffp-contract=off to clang.cfg and clang++.cfg of every
                                 SDK tree under build/tools/; the gate: two -### probes (off once,
                                 no other value), one line in each file
.github/workflows/release.yml    rebuild: ubuntu-24.04 timeout 120; comments
tests/harness/scan.py            FP_CONTRACT_OVERRIDES (whole tokens on compiler lines and
                                 compile-flag variables); MESON_BUILDS; fp_contract_errors
                                 (recipe, listed records, Makefiles, source-tree pragmas, the
                                 compiler); compiler_table_errors rewritten; REBUILD_TIMEOUTS
tests/harness/needs.py           the need `compile records`
tests/checks/test_v1_5_rebuild_from_pins.py   test_every_compile_contracts_nothing
tests/checks/test_rules.py       test_every_host_compiles_natively_with_the_fallback_kept
                                 (replaces test_x86_64_compiles_with_an_aarch64_compiler)
tests/unit/test_scan.py          the rewritten compiler-table mutations; the timeout case
context/upstream/4-llvm-wasm-isel-slot-order/   issue.md, notes.md narrowed; README row
context/research/2026-10-18-byte-identical-wasm-builds-prior-art/   cfg-route.sh and outputs
context/specifications/040-…md   three amendment lines (Decisions 2, 4, 11)
README.md, CHANGELOG.md
```

Unchanged: `scripts/clang-emulated`, `scripts/wasi-cc`, `wasi-cxx`, `python-wasi-cross`, the cross
files, steps 20 to 90, `downloads/SHA256SUMS`, `tests/unit/test_clang_emulated.py`.

## Scope

In: the above.

Out:
- deleting the emulation (a later specification after the first qualifying release, Decision 3);
- tracing the tie inside LLVM past the `fmuladd` finding (the upstream issue's business);
- any change to the meaning of "the same bytes": `SHA256SUMS` byte equality, no exception list,
  no normalized comparison (the owner's decision);
- a per-package flag or a flag on the command lines of individual builds;
- relaxed SIMD, or any other codegen flag;
- spec 057's workflow restructuring, and anything 023 adds beyond what Decision 7 names;
- 037's OpenBLAS record (Decision 4 says what 037 brings; nothing here builds it);
- building or patching the compiler, or a compiler as a wasm program (the memo's options F and G,
  recorded and not taken).

## Acceptance criteria

1. **Seen failing first, before any recipe change**, each recorded in the landing notes with its
   output.
   - `test_every_compile_contracts_nothing` fails on today's tree with `10_tools.sh does not name
     clang.cfg` (and the flag and the probe); with a build tree present, its record, Makefile and
     source-tree parts pass today (no compiler command or compile-flag variable holds a member of
     the family, and no tree holds a pragma; the confirmation's EXECUTED greps), and the landing
     notes say so, because those parts guard the future, not the present. **The case the token rule
     handles is named there:** CPython's cross-build Makefile lines 425 (`HOSTRUNNER=`) and 429
     (`PYTHON_FOR_BUILD=`) carry wasmtime's `--config`, and the check passes over them because
     neither is a compiler line or a compile-flag variable, with no line exempted by name; the
     landing notes quote the two lines and the check's output reading that Makefile. Then each part
     is seen failing against a planted input: a `compile_commands.json` copy with
     `-ffp-model=precise` on one command; a Makefile copy with `-ffast-math` in `CFLAGS_NODIST`,
     and another with `--config` on a `$(CC)` recipe line (a hit) beside the two wasmtime lines (not
     a hit); a `compile_commands.json` under an unlisted `build/<name>-build/` (a breach); a listed
     folder's record removed (a breach); a source file with `#pragma STDC FP_CONTRACT ON`; a
     configuration file with the line doubled; one with `-ffp-contract=fast` after `off`. Each names
     its hit.
   - `test_every_host_compiles_natively_with_the_fallback_kept` is proven by its unit mutations
     (Decision 4 says why today's `line.conf` passes it); the retired check is seen vanishing in the
     ratchet's `ABSENT` line and retired with `--retire`.
   - `test_release_workflow_rebuilds_on_two_more_hosts` fails on today's workflow with `rebuild's
     matrix does not give ubuntu-24.04 120 minutes`.
   - Each `test_scan.py` mutation names its breach.
   - **Step 10's gate stops the build**, with one line, in each of four cases, each in its own
     clone: the configuration write removed; `-ffp-contract=on` appended after the write;
     `-ffp-contract=fast` appended after the write; the line written twice.
   - **The bytes differ without the flag.** Today's main, rebuilt in the research container on
     `linux/amd64` with the switch off and no flag (that is, the native x86_64 clang alone), writes a
     `SHA256SUMS` that differs from macOS's in exactly `python.wasm` and `python-snapshot.wasm`, as
     spec 012 and 040 found. This is the fact the flag fixes, seen once more on the tree it fixes.
2. **Decision 1 reproduced** into the research folder (Decision 10): the `-cc1` lines of both
   drivers carry the flag; `clang-cpp` loads no file and its macros equal `clang -E`'s; the
   hello-world links under `-Werror -Wunused-command-line-argument`; the numpy object through the
   edited files is `2914eb833ad62c93` from both SDKs; `-ffp-contract=on` and `-ffp-model=precise` on
   the command line restore the old pair; the fold example gives `0x1p-54` and `0x0p0`; a
   `FP_CONTRACT ON` pragma brings `llvm.fmuladd` back.
3. **Three hosts, one set, natively.** macOS, the `linux/arm64` container and the `linux/amd64`
   container each build from empty `downloads/` and `build/` with this change. All three write a
   byte-identical `SHA256SUMS`. The x86_64 build's log shows step 10's two new gate lines and none
   of the five emulation probes; its `00_download.log` shows no fetch from `snapshot.debian.org`
   and no arm64 Linux SDK; its `MANIFEST` still lists the six pins. The x86_64 build's
   `meson-generated_npy_math_complex.c.o` is `2914eb833ad62c93`, and so is macOS's.
   - **3b. The fallback is runnable** (the review's F3). In the `linux/amd64` container, on a
     clone with the switch thrown (Decision 3's three lines), `scripts/00_download.sh` fetches the
     six pins and `scripts/build.sh 10` runs: its log shows the five emulation probes and then the
     two new gate lines, through the emulated clang; both trees' configuration files hold the one
     line; and the numpy file compiled through `$SDK/bin/clang` (the launcher) gives
     `2914eb833ad62c93`. Step 10 alone; no full emulated build (a correctness run of one step, not
     a time figure). The rule check and the workflow check pass on that clone with the three lines
     changed.
4. **The arithmetic did not change, or every change is a traced fold.** `uv run pytest` on the new
   set: every golden job's output equals its `.expected` and every upstream group's `passes`
   equals its accepted value (spec 050), **or** each exception is traced to a constant fold and
   disposed of as Decision 6 says, with the before and after values in the landing notes and the
   judge change accepted with its reason. Anything not traced to a fold stops the build. The
   landing notes list each group's `passes` before and after, and each metric (`bytes` of
   `python.wasm` and the zip, every `fuel`) before and after, with `--accept-growth` only where a
   metric grew, and its reason. They state which of the four hashes moved and why (Decision 6).
5. **The judge.** `uv run pytest` is green, accepted by the lane with `--accept`, `--accept-judge`
   and `--retire tests/checks/test_rules.py::test_x86_64_compiles_with_an_aarch64_compiler` (and
   `--accept-fewer-passes` only under criterion 4's fold rule). The ratchet shows lost 0. The two
   new checks pass; `test_clang_emulated.py` still passes (the launcher is unchanged). `ruff check`
   and `ruff format --check` are clean.
6. **The dry run.** One `workflow_dispatch` run of `release.yml` on main's exact commit after
   landing passes every job: both rebuild runners build natively, `same-bytes` reports
   `ubuntu-24.04-arm: the same SHA256SUMS`, `ubuntu-24.04: the same SHA256SUMS`, and the same wheel
   for each. The x86_64 job's log shows the two new gate lines and none of the emulation's. Its
   wall time and `nproc` are recorded in the landing notes as benchmark facts, beside spec 040's
   64.5 minutes; never a check. **No release tag is pushed between the landing and this run's
   pass** (AGENTS.md rule 6b; Decision 3). If the run fails on `ubuntu-24.04`, Decision 9's order
   applies and is recorded.
7. The upstream draft, the README, the CHANGELOG, the research folder's script and the three
   amendment lines in spec 040 exist as Decisions 8, 10 and 11 say.

## The owner's choices

None open. The owner decided the four points this specification carries (`../decisions.md`,
2026-10-18): the flag on every compile, the native rebuild, the fallback kept one release then
deleted, and byte equality as the one meaning of "the same bytes". Where the flag lives (Decision
1), the fallback's exact change set and when the emulation leaves (Decision 3), the timeout
(Decision 5) and the fold rule (Decision 6) are decided here with their reasons, so nothing waits.
No entry is added to `../questions-for-the-owner.md`.

## Disposition of the pre-build review (2026-10-18)

- **F1 (medium): written in.** Decision 1 (the override family, each member named with what it
  does); Decision 2 (the gate accepts `off` once and no other value); Decision 4
  (`scan.FP_CONTRACT_OVERRIDES`; the whole CPython Makefile; the planted-input cases in criterion 1).
- **F2 (medium): written in.** Decision 1's "What the flag changes in results, exactly" (run-time
  unchanged; a fold moves by one rounding, with the review's example); Decision 6's trace rule (a
  fold is recorded and the golden or allowance changed through `--accept-judge`, with
  `--accept-fewer-passes` for a fallen `passes`; anything else stops the build); criterion 4; the
  Intent and the README sentence.
- **F3 (medium): written in.** Decision 4's first bullet is one rule true in both positions of the
  switch; Decision 3 lists the fallback's three-line change set and its flag; criterion 3b runs step
  10 with the switch thrown in the `linux/amd64` container; Decision 9 orders the fallbacks.
- **F4 (low): written in.** Decision 4's record part derives the records from the cross files and
  requires every one; reads the autoconf Makefiles, step 60's two command files and the whole CPython
  Makefile; names what 037's OpenBLAS brings. Direct compiles stay covered by the static part, which
  reads the scripts that write them.
- **F5 (low): written in.** Decision 4's source-tree part greps the unpacked trees for the two
  pragmas (cheap), with the allowance rule for an uncompiled file; the pragmas are also named as
  outside the gate's reach with `same-bytes` as the backstop, in the scoreboard's not-machine-checked
  line.
- **F6 (low): written in.** The Kind line, Decision 6 and the CHANGELOG plan expect the zip to stay
  and the other three to move, the builder stating either way; the README says the flag appears in
  no recorded `CFLAGS`.
- **F7 (low): written in.** Decision 11: three amendment lines under 040's Decisions 2, 4 and 11.
  Decision 9: 040's last resort is kept as the third step, not dropped, and why 012 needs no
  amendment (its Decision 8 is that last resort's basis; its other decisions are untouched).
- **F8 (low): written in.** Decision 5: 057's rebase list gains its Scope bullet and its F2
  disposition sentence, and the security gain (each leg runs only its own host's compiler; one
  tampered tarball changes at most one vote).
- **F9 (low): written in.** Decision 3 and criterion 6: no release tag between the landing and a
  passing dry run on main's exact commit (AGENTS.md rule 6b, cited); "the first release" defined as
  the first alpha published after landing whose native x86_64 rebuild passed; a later build-class
  specification may then delete the emulation.
- **F10 (nit): written in.** Decision 1 and Decision 2: both trees' configuration files are written
  and gated when the switch is thrown; criterion 3b checks it.

The confirmation (2026-10-18) confirmed F1 to F10, F7's third fallback included, and raised two low
findings:

- **N1 (low): written in.** Decision 4: a member of the family counts only as a whole token on a
  compiler's command line or in a compile-flag variable, each defined there; CPython's Makefile
  lines 425 and 429 (wasmtime's `--config` on `HOSTRUNNER=` and `PYTHON_FOR_BUILD=`) are therefore
  not hits, by what they are and not by name, so criterion 1's "passes today" is true; criterion 1
  names them as the case the rule handles and plants a `--config` on a `$(CC)` recipe line as the hit
  beside them.
- **N2 (low): written in.** Decision 4: the expected records are a judge constant,
  `scan.MESON_BUILDS` (numpy and pandas today; 023 adds its five; every later meson build extends
  it), chosen over parsing the steps because the steps name folders through variables and loops and
  the cross files stay unchanged; every listed record must exist once any does, and every
  `compile_commands.json` under `build/` must be listed. Decision 7 names 023's five; criterion 1
  plants both breaches.

## Landing notes
