# 059 — The x86_64 rebuild runs natively

- **Status:** drafted 2026-10-18; awaiting its pre-build review (required: build-class). Drafted
  on `spec/059-the-x86-64-rebuild-runs-natively` from main `d68a594`, where the owner's decision
  is recorded (`../decisions.md`, "The x86_64 rebuild without emulation (2026-10-18)"). It builds
  after spec 023 lands and before spec 057 (which edits the same workflow and rebases onto this).
- **Owner:** Clay Gendron
- **Kind:** build-class: compile flags (one flag, `-ffp-contract=off`, on every compile in the
  recipe), the release workflow's x86_64 job; a judge change (one rule check replaced, one added,
  one workflow constant); every artifact hash changes (`python.wasm`, the snapshot, the zip,
  `MANIFEST`, so `SHA256SUMS`). It changes `scripts/line.conf`, `scripts/00_download.sh`,
  `scripts/steps/10_tools.sh`, `.github/workflows/release.yml`, `tests/`, the upstream draft
  `context/upstream/4-llvm-wasm-isel-slot-order/`, `README.md`, `CHANGELOG.md`, and adds a
  one-line amendment note to spec 040 (Decision 2). It changes no pin, no source tree, no carried
  patch, no `src/` file.
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
  Decision 1; the builder reproduces them into the research folder first (Decision 10).

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
and `fadd`, the construct is gone, and both compilers write the same object. The arithmetic is the
same either way on this target. The bytes are not: the optimizer can share a multiply between two
plain expressions where it could not inside the intrinsic, so every artifact hash moves once.

So: one flag, in one place every compile passes through, and the x86_64 host compiles with its own
clang in about the time the arm64 host takes. The emulation stays in the tree, switched off, for
one release, as the parachute spec 040's Decision 11 already describes.

## Decisions

1. **The flag lives in the compiler's own configuration files, so no compile can miss it.**
   wasi-sdk's `bin/clang.cfg` and `bin/clang++.cfg` hold one line each
   (`--sysroot=<CFGDIR>/../share/wasi-sysroot`), and clang reads the one for its driver name on
   every call. Step 10 appends `-ffp-contract=off` as a second line to both files of the tree
   whose clang compiles (`$CSDK`; on the arm64 hosts that is `$SDK`). Facts, each EXECUTED while
   drafting, with the pinned arm64 macOS SDK natively and the pinned x86_64 Linux SDK in the
   research container (`linux/amd64`, under Rosetta), the two files edited exactly so:
   - `clang -v`, with or without `--target`, and `clang++ -v` each print `Configuration file:
     …/bin/clang.cfg` or `clang++.cfg` (spec 040's gate already relies on the second).
   - `clang --target=wasm32-wasip1 -### -c x.c`, the same with `-E`, and `clang++ … -### -c -x
     c++ x.c` each show `-ffp-contract=off` on the `-cc1` line.
   - The build's preprocessed `npy_math_complex.c` (324,353 bytes, `2193b9bd4d40aadc`), compiled
     with the build's code-generation flags and **no flag on the command line**, gives
     `2914eb833ad62c93` from both SDKs: the object the memo got with the flag on the command line.
   - Compile, link, and compile-and-link of a hello-world through the edited `clang` with
     `-Werror` all succeed. A configuration-file option raises no unused-argument warning at link,
     so no autoconf probe (CPython's, xz's, FreeType's) changes its answer.
   - `clang-cpp` reads no configuration file (its `-v` prints none and its `-cc1` line carries
     the default `-ffp-contract=on`). It preprocesses only and generates no code, so it needs
     none. Nothing in the recipe compiles through it (CPython's configure uses it for `CPP`).
   - **A later command-line `-ffp-contract=on` overrides the file** (the reproducer then gives
     the old `9afcef294ca52dad`). So Decision 4's rule forbids `-ffp-contract=` on any command
     line the recipe writes or any build system emits; the file is the one place.
   - **Why the configuration file, not the flags of each build.** The alternative is eight places
     today (CPython's `CFLAGS` through the WASI driver, two cross files' `c_args` and `cpp_args`,
     steps 30 and 35's `CFLAGS` and direct compiles, step 60's reactor compile), plus one or more
     for each package 023 and 037 add, kept equal by audit. The configuration file is read by every
     caller that exists or will exist: CPython's `Platforms/WASI` driver (`$WASI_SDK_PATH/bin/clang`),
     `scripts/wasi-cc` and `wasi-cxx` (`$WASI_SDK_PATH/bin/clang` and `clang++`), steps 30, 35, 37,
     55 and 60 (`$SDK/bin/clang`, `clang++`, or `make -n`'s commands), meson, autoconf and
     CMake-less direct compiles alike. It is a recipe item of §4.1's first kind, like the launcher
     and the neutral runtime: a change to the downloaded toolchain tree under `build/tools/`, made
     by step 10, never to a source tree.
   - **Why `off`, not `fast`.** `fast` gave the same object (the memo), because it also emits
     plain `fmul` and `fadd` and leaves fusion to a backend that has none. `off` says what it does
     and cannot change if a future wasi-sdk enables relaxed SIMD by default; `fast` could then fuse.
   - **The arithmetic does not change** (INFERRED, made EXECUTED by criterion 4): without a fused
     instruction, `fmuladd(a, b, c)` is lowered to the same multiply and add that the plain IR
     writes; the one multiply the optimizer then shares is the same value computed once. The
     object's set of call targets is unchanged (no `fmal`, no new libcall; the memo). The upstream
     suites' `passes` (spec 050) must not fall, and no golden job may change its output.
   - **Idempotent.** Step 10 removes and re-unpacks `build/tools/` first, so the line is appended
     exactly once per build. The gate (Decision 2) also fails if the line is absent or doubled.

2. **Step 10's gate proves the flag is in force.** After the write (and after the emulation
   layout, when it is on), step 10 runs `$SDK/bin/clang --target=wasm32-wasip1 -### -c
   "$G/probe.c"` and `$SDK/bin/clang++ --target=wasm32-wasip1 -### -c -x c++ "$G/probe.c"`,
   writes each output under `build/compiler-gate/`, and stops with one line unless each `-cc1` line
   holds `-ffp-contract=off` exactly once and `-ffp-contract=on` not at all. It prints
   `compiler gate: clang contracts nothing (-ffp-contract=off)` and the same for `clang++`. It
   also requires each of the two configuration files to hold exactly one `-ffp-contract=off`
   line. On x86_64 with the emulation on, `$SDK/bin/clang` is the link to the launcher and the
   probe reaches `$CSDK`'s files through it, which is why the write goes to `$CSDK`.

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
   - **Switching the fallback on is one line**: `LINUX_X86_64_COMPILER_SDK_DIR=wasi-sdk-33.0-arm64-linux`.
     Then the download fetches, step 10 lays out and probes the emulated compiler, and the flag
     write lands in `$CSDK`'s files as Decision 1 says. Decision 9 says when that line is used.
   - **When the emulation leaves.** After the first release whose tag run passes `same-bytes` with
     this specification's native x86_64 rebuild, a small build-class change of its own removes:
     `scripts/clang-emulated`, the five emulation names and their comment from `line.conf`, the
     emulation loop from `line.sh`, the conditional block from `00_download.sh`, the six pins from
     `downloads/SHA256SUMS`, step 10's emulation branch and its probes, `tests/unit/test_clang_emulated.py`,
     the emulation half of Decision 4's rule check and its unit mutations, `scan.EMULATION_NAMES`,
     `STEP_10_WORDS`, `STEP_10_STRACE`, `LAUNCHER_FLAGS` and `LAUNCHER_MODES`, and the README's
     paragraph about the fallback. `COMPILER_SDK_DIR` stays, each host naming its own SDK, and so
     does the flag. The CHANGELOG records it. That change is drafted when the release lands, not
     here, so this specification stays small and its evidence stays one dry run.

4. **The judge.** Each check is written, and seen failing, before the code it guards (AGENTS.md
   rule 3). The judge changes, so the landing uses `--accept-judge` with its reason.
   - **`test_every_compile_contracts_nothing`** (v1.5, `test_v1_5_rebuild_from_pins.py`;
     `scan.fp_contract_errors`). Three parts.
     - *The recipe, always:* `scripts/steps/10_tools.sh`, read without its comments
       (`scan.code_text`), names both configuration files (`clang.cfg`, `clang++.cfg`), the flag
       `-ffp-contract=off`, and the probe (`-###` with `-cc1` matched), so a comment satisfies
       nothing; and no other tracked file under `scripts/` or `recipes/` holds `-ffp-contract=`
       (the string, in any form), so no recipe file can override the file's setting.
     - *The build's compile records, when present:* every `build/*-build/compile_commands.json`
       (numpy, pandas, and 023's matplotlib and every later meson build) holds no `-ffp-contract=`
       on any command, and CPython's `build/Python-<version>/cross-build/wasm32-wasip1/Makefile`
       holds none in its `CFLAGS`, `CONFIGURE_CFLAGS`, `CONFIGURE_CFLAGS_NODIST`, `OPT` or
       `BASECFLAGS` lines. Each record found is named in the check's output with its command count,
       so the review sees how many compiles it read. With no record present (a checkout without a
       build) this part is `blocked` by a new need, `compile records` (`tests/harness/needs.py`),
       named in the scoreboard's blocked list. The release workflow's `build` job has every record.
     - *The compiler itself, when present:* with `build/tools/<WASI_SDK_DIR>/bin/clang` present,
       the check runs Decision 2's two `-###` probes itself (through the judge's `subprocess`, on
       a one-line C file in a temporary folder) and asserts the `-cc1` lines as the gate does. It is
       blocked by the same need otherwise.
     On today's tree it fails: step 10 names neither file nor the flag.
   - **`test_every_host_compiles_natively_with_the_fallback_kept`** (rules, `test_rules.py`;
     `scan.compiler_table_errors`, rewritten) replaces `test_x86_64_compiles_with_an_aarch64_compiler`,
     which the landing retires with `--retire` (the ratchet turns a vanished check red,
     `../progress/README.md`). It requires:
     - every host key has `COMPILER_SDK_DIR`, **equal to its own `WASI_SDK_DIR`** (native; the
       old rule required an arm64 SDK, which is now wrong for x86_64);
     - exactly one key, `LINUX_X86_64`, carries the five emulation names (the fallback), each
       naming a pinned file fetched in that key's branch, and that key's branch fetches the arm64
       Linux SDK too; a key with some but not all five names, or a second key with any, is a breach;
     - `10_tools.sh`, without comments, still names `clang-emulated`, `aarch64-root`, `ld.so.cache`,
       `InstalledDir` and `clang-cpp` and the `-strace` probe (the fallback is runnable), and
       `scripts/clang-emulated` still holds its three `-U` flags, its `QEMU_` clearing and its
       three name-to-mode arms (spec 040, Decision 7, unchanged);
     - and, if any key's `COMPILER_SDK_DIR` differs from its own SDK (the switch thrown), that
       SDK is another key's own `WASI_SDK_DIR` and that key has the five names: spec 040's rule,
       kept so the one-line switch is still checked when it is used.
     On today's tree it fails: `LINUX_X86_64_COMPILER_SDK_DIR` is the arm64 SDK.
     `tests/unit/test_scan.py`'s compiler-table cases are rewritten to the new rules, one mutation
     per rule (the switch thrown without the names; a second key with the names; four names; a
     name not fetched; the launcher missing a flag), each naming its breach.
   - **`test_release_workflow_rebuilds_on_two_more_hosts`** keeps its name. `scan.REBUILD_TIMEOUTS`
     becomes `{"ubuntu-24.04-arm": 120, "ubuntu-24.04": 120}`. The workflow check otherwise stands
     (both runners in the matrix and in both `same-bytes` loops, `nproc` and `binfmt_misc` printed:
     the fallback can still be switched on, and the facts cost nothing). On today's workflow it
     fails with `rebuild's matrix does not give ubuntu-24.04 120 minutes`. The matching unit case
     in `test_scan.py` changes with it.
   - **Unchanged and still passing:** `test_every_build_host_has_its_whole_table`,
     `test_toolchain_is_pinned_for_linux_and_macos`, `test_cpp_is_compiled_with_exceptions`, the
     v1.5 zip check, `tests/unit/test_clang_emulated.py` (the launcher is unchanged).
   - The scoreboard's not-machine-checked list does not change.

5. **The release workflow: the x86_64 job becomes an ordinary rebuild.** In `rebuild`'s matrix
   `include`, `ubuntu-24.04` gets `timeout: 120`, the same as the arm64 runner: a native rebuild
   is expected near the arm64 one's 7 minutes, and 120 is already six times spec 012's own margin.
   The comments on `rebuild` and `same-bytes` stop describing an emulated compiler; they say every
   host compiles with its own pinned clang and `-ffp-contract=off`, and link this specification.
   The `nproc` and `binfmt_misc` lines stay. Nothing else changes; `attest` and `publish` still need
   `same-bytes`. **Spec 057** lands after this one and rebases onto it: its two rebuild jobs
   (`rebuild-linux-arm64`, `rebuild-linux-x86-64`) each take `timeout-minutes: 120`, and its
   sentence "the x86_64 job compiles with the arm64 Linux …" (057, Decision 4, "What two jobs
   cannot separate") is revised at that rebase to say the x86_64 job compiles natively. 057's
   `REBUILD_TIMEOUTS` rewrite takes this specification's values. Nothing here edits a line 057
   adds.

6. **Every artifact hash changes once, and the ratchet accepts it with its reason.** The flag
   reaches CPython, zlib, bzip2, xz, SQLite, numpy, pandas, the reactor and, after 023, the plot
   libraries and packages, so `python.wasm`, `python-snapshot.wasm` (it follows the reactor), the
   zip (numpy's and pandas's `.so` archives are not in it, but `_sysconfigdata` records `CFLAGS`;
   the builder states whether the zip moved and why) and `MANIFEST` (recipe hashes: `line.conf`,
   `00_download.sh`, `10_tools.sh`) all move, and `SHA256SUMS` with them.
   - **The landing's flags:** `--accept "<spec 059: -ffp-contract=off on every compile; every
     artifact hash moves once>"`, `--accept-judge "<the two rule and v1.5 checks, the timeout
     constant>"`, `--retire tests/checks/test_rules.py::test_x86_64_compiles_with_an_aarch64_compiler`.
   - **`--accept-growth` only if a metric grew, with the measured numbers in its reason.** The
     memo saw 392 fewer instructions in the one numpy object (10,484 to 10,092), so `python.wasm`'s
     `bytes` is expected to fall or stay, and `fuel` to move slightly either way. The landing notes
     record every metric before and after. Growth is accepted only as "the flag's effect", never
     as a quiet by-product.
   - **Never `--accept-fewer-passes`.** A fall in any upstream group's `passes` means the flag
     changed a result, which Decision 1 says it cannot; the build stops and the memo is wrong
     before this specification is (AGENTS.md rule 7: two attempts, then write it down).
   - The three hosts' `SHA256SUMS` must be one file, byte for byte, as before. A hash that moves on
     one host and not another is a defect.

7. **023 is covered when this specification rebases after it lands.** 023 adds step 37
   (FreeType, HarfBuzz, SheenBidi, libraqm, qhull: meson and direct compiles), step 55 (Pillow,
   kiwisolver from source lists; matplotlib with meson), a `pkgconf` install in step 10, cross
   files and stand-ins under `recipes/`, and drops `-pthread` from `scripts/wasi-cc`. Every one of
   its compiles runs `$SDK/bin/clang`, `$SDK/bin/clang++`, `scripts/wasi-cc` or `scripts/wasi-cxx`,
   so Decision 1's file reaches them without a line of this specification knowing their names. What
   the builder does at the rebase:
   - re-runs Decision 4's compile-records part over 023's `build/*-build/compile_commands.json`
     (matplotlib, and any 023 library built with meson) and over step 37's and 55's direct compile
     lines in the scripts, which the static part reads as tracked files under `scripts/`: none may
     carry `-ffp-contract=`;
   - merges step 10: 023's `pkgconf` install and this specification's configuration write and
     probe touch different lines of the same file;
   - confirms 023's `test_cpp_is_compiled_with_exceptions` extension (its cross files' C++ flags)
     is untouched: `-fwasm-exceptions` and `-ffp-contract=off` do not interact;
   - records 023's packages' upstream suites, if 023 adds any to spec 050's groups, under
     criterion 4 alongside numpy's and pandas's.
   If 023 has not landed when the lane reaches this specification, this specification builds first
   on main as it stands, and 023's builder gets Decision 1's property for free at its own rebase;
   Decision 4's compile-records check then covers 023's records from 023's first build.

8. **The upstream draft gains the finding.** `context/upstream/4-llvm-wasm-isel-slot-order/issue.md`
   gains a section "Narrowed: the difference needs `llvm.fmuladd` on `fp128`": the two tables from
   the memo (the reproducer and the numpy file, with and without `-ffp-contract=off`, both hosts),
   the sentence that `-ffp-contract=fast` gives the same object as `off`, and that an empty or a
   large environment moves nothing (so the cause is not address-dependent iteration). The guess
   in "What we would expect" is narrowed to the lowering of `FMA`/`fmuladd` into libcalls. The
   workaround paragraph says the project now compiles with `-ffp-contract=off` everywhere and runs
   x86_64 natively. `notes.md` gains "Narrowed (spec 059)" with the memo's commands. The upstream
   README's row for folder 4 says the same in its state column. The owner's "run it on real
   x86_64 first" condition stands; nothing is posted by an agent (LLVM's AI policy, as spec 040
   recorded).

9. **The fallback, and when it is used.** Spec 040's Decision 11 stands with one change: the
   same-day fallback is now the one-line switch of Decision 3, not a workflow edit.
   - If the dry run (criterion 5) fails on `ubuntu-24.04` with a byte difference in `same-bytes`,
     or a repeated build failure inside a compile, the builder throws the switch
     (`LINUX_X86_64_COMPILER_SDK_DIR=wasi-sdk-33.0-arm64-linux`) and the `ubuntu-24.04` timeout
     goes back to 360, through the lane, reviewed, with `--accept-judge` for the constant, and
     records it in the landing notes, the CHANGELOG and the memo's successor. The flag stays: it
     is right on every host and the emulated compiler then also compiles with it. The gate stays
     three hosts.
   - A fetch failure or a lost runner is re-run once first, as 040 says.
   - The 240-minute trip-wire and the 360-minute limit of 040's Decision 11 no longer apply to a
     native job; the 120-minute timeout is the limit, and a native rebuild that nears it is a
     defect to find, not a time to accept.

10. **The evidence moves into the repository first.** Decision 1's four facts ran in the memo's
    scratch folder. The builder re-runs them from the research folder
    `../research/2026-10-18-byte-identical-wasm-builds-prior-art/`: a script `cfg-route.sh` (the
    two SDKs, each checked against `downloads/SHA256SUMS`; the configuration files edited in a
    scratch copy of each SDK, never in `build/tools/`; the `-v`, `-###`, `-Werror` and `clang-cpp`
    probes; the numpy object through the edited files on both hosts) and its outputs as text
    (commands, hashes, the `-cc1` lines; no objects, as 847a954 set the folder's rule). The
    preprocessed file is numpy's and wasi-libc's text and is regenerated, not committed. The memo
    is not edited (`../README.md`: a memo is never edited after the fact); the folder's `README.md`
    gains a dated paragraph naming the script.

11. **Documentation.**
    - **README**, "The same bytes from any build host": every host compiles with its own pinned
      wasi-sdk clang, and every compile carries `-ffp-contract=off`, set in the toolchain's own
      configuration files by step 10, because the x86_64 and aarch64 builds of the same clang
      order two stack slots of one `long double` expression differently when the IR holds
      `llvm.fmuladd` (the memo, the upstream draft). The paragraph about the emulated compiler
      shrinks to one sentence: the launcher and its five pinned Debian packages stay in the tree,
      switched off, as the fallback for one release, and the five licences stay named while they do.
    - **CHANGELOG**, under the unreleased section: the x86_64 rebuild runs natively; the flag;
      every artifact hash changes; the fallback kept for one release; the upstream draft narrowed.
    - **Spec 040** gains one line under Decision 2: "Amended by spec 059 (2026-10-18): the
      emulation is switched off and kept one release as the fallback; every compile carries
      `-ffp-contract=off`, which makes the two compiler builds agree." Spec 012's text stands.
    - The workflow's comments, as Decision 5.

12. **The order of work.** This specification is build-class (§5.7). It builds after 023 lands,
    rebasing onto main then, and before 057, which rebases onto it (Decision 5). It changes every
    artifact hash, so every build-class specification after it measures against its numbers; 057
    changes no byte, so the order between them costs 057 nothing but the rebase.

## Intent

Anyone can rebuild the published sandbox from its pins on arm64 macOS, arm64 Linux or x86_64 Linux,
with that machine's own pinned compiler, and get the same artifact set, byte for byte. CI proves all
three on every release in the time the fastest host takes. Every compile carries `-ffp-contract=off`,
which removes the one construct on which wasi-sdk's two compiler builds disagree, and nothing in the
arithmetic changes. The emulated compiler stays one release as the parachute, then leaves.

## Design

```
scripts/line.conf                LINUX_X86_64_COMPILER_SDK_DIR = its own SDK (the switch); comment
scripts/00_download.sh           LINUX_X86_64: the arm64 SDK and five .deb get lines inside
                                 `if COMPILER_SDK_DIR != WASI_SDK_DIR`
scripts/steps/10_tools.sh        append -ffp-contract=off to $CSDK/bin/clang.cfg and clang++.cfg;
                                 the gate: two -### probes, one line each in the files
.github/workflows/release.yml    rebuild: ubuntu-24.04 timeout 120; comments
tests/harness/scan.py            fp_contract_errors; compiler_table_errors rewritten;
                                 REBUILD_TIMEOUTS
tests/harness/needs.py           the need `compile records`
tests/checks/test_v1_5_rebuild_from_pins.py   test_every_compile_contracts_nothing
tests/checks/test_rules.py       test_every_host_compiles_natively_with_the_fallback_kept
                                 (replaces test_x86_64_compiles_with_an_aarch64_compiler)
tests/unit/test_scan.py          the rewritten compiler-table mutations; the timeout case
context/upstream/4-llvm-wasm-isel-slot-order/   issue.md, notes.md narrowed; README row
context/research/2026-10-18-byte-identical-wasm-builds-prior-art/   cfg-route.sh and outputs
context/specifications/040-…md   one amendment line (Decision 2)
README.md, CHANGELOG.md
```

Unchanged: `scripts/clang-emulated`, `scripts/wasi-cc`, `wasi-cxx`, `python-wasi-cross`, the cross
files, steps 20 to 90, `downloads/SHA256SUMS`, `tests/unit/test_clang_emulated.py`.

## Scope

In: the above.

Out:
- deleting the emulation (its own change after the first release, Decision 3);
- tracing the tie inside LLVM past the `fmuladd` finding (the upstream issue's business);
- any change to the meaning of "the same bytes": `SHA256SUMS` byte equality, no exception list,
  no normalized comparison (the owner's decision);
- a per-package flag or a flag on the command lines of individual builds;
- relaxed SIMD, or any other codegen flag;
- spec 057's workflow restructuring, and anything 023 adds beyond what Decision 7 names;
- building or patching the compiler, or a compiler as a wasm program (the memo's options F and G,
  recorded and not taken).

## Acceptance criteria

1. **Seen failing first, before any recipe change**, each recorded in the landing notes with its
   output.
   - `test_every_compile_contracts_nothing` fails on today's tree with `10_tools.sh does not name
     clang.cfg` (and the flag and the probe); with a build tree present, its compile-records part
     passes today (no record holds `-ffp-contract=`), and the landing notes say so, because that part
     guards the future, not the present.
   - `test_every_host_compiles_natively_with_the_fallback_kept` fails on today's `line.conf` with
     `LINUX_X86_64_COMPILER_SDK_DIR: wasi-sdk-33.0-arm64-linux is not the host's own SDK`.
   - `test_release_workflow_rebuilds_on_two_more_hosts` fails on today's workflow with `rebuild's
     matrix does not give ubuntu-24.04 120 minutes`.
   - Each `test_scan.py` mutation names its breach.
   - **Step 10's gate stops the build**, with one line, in each of three cases, each in its own
     clone: the configuration write removed; `-ffp-contract=on` appended after the write; the line
     written twice.
   - **The bytes differ without the flag.** Today's main, rebuilt in the research container on
     `linux/amd64` with the switch off and no flag (that is, the native x86_64 clang alone), writes a
     `SHA256SUMS` that differs from macOS's in exactly `python.wasm` and `python-snapshot.wasm`, as
     spec 012 and 040 found. This is the fact the flag fixes, seen once more on the tree it fixes.
2. **Decision 1 reproduced** into the research folder (Decision 10): the `-cc1` lines of both
   drivers carry the flag; `clang-cpp` loads no file; the hello-world links under `-Werror`; the
   numpy object through the edited files is `2914eb833ad62c93` from both SDKs; a later
   `-ffp-contract=on` restores `9afcef294ca52dad` on the reproducer.
3. **Three hosts, one set, natively.** macOS, the `linux/arm64` container and the `linux/amd64`
   container each build from empty `downloads/` and `build/` with this change. All three write a
   byte-identical `SHA256SUMS`. The x86_64 build's log shows step 10's two new gate lines and none
   of the five emulation probes; its `00_download.log` shows no fetch from `snapshot.debian.org`
   and no arm64 Linux SDK; its `MANIFEST` still lists the six pins. The x86_64 build's
   `meson-generated_npy_math_complex.c.o` is `2914eb833ad62c93`, and so is macOS's.
4. **The arithmetic did not change.** `uv run pytest` is green on the new set with no
   `--accept-fewer-passes`: every upstream group's `passes` equals its accepted value (spec 050),
   and every golden job's output equals its `.expected`. The landing notes list each group's
   `passes` before and after, and each metric (`bytes` of `python.wasm` and the zip, every `fuel`)
   before and after, with `--accept-growth` only where a metric grew, and its reason.
5. **The judge.** `uv run pytest` is green, accepted by the lane with `--accept`, `--accept-judge`
   and `--retire tests/checks/test_rules.py::test_x86_64_compiles_with_an_aarch64_compiler`. The
   ratchet shows lost 0. The two new checks pass; `test_clang_emulated.py` still passes (the
   launcher is unchanged). `ruff check` and `ruff format --check` are clean.
6. **The dry run.** One `workflow_dispatch` run of `release.yml` on the landed commit passes every
   job: both rebuild runners build natively, `same-bytes` reports `ubuntu-24.04-arm: the same
   SHA256SUMS`, `ubuntu-24.04: the same SHA256SUMS`, and the same wheel for each. The x86_64 job's
   log shows the two new gate lines and none of the emulation's. Its wall time and `nproc` are
   recorded in the landing notes as benchmark facts, beside spec 040's 64.5 minutes; never a check.
   If the run first happens after landing and fails on `ubuntu-24.04`, Decision 9's fallback is
   taken and recorded.
7. The upstream draft, the README, the CHANGELOG, the research folder's script and the amendment
   line in spec 040 exist as Decisions 8, 10 and 11 say.

## The owner's choices

None open. The owner decided the four points this specification carries (`../decisions.md`,
2026-10-18): the flag on every compile, the native rebuild, the fallback kept one release then
deleted, and byte equality as the one meaning of "the same bytes". Where the flag lives (Decision
1), when the fallback leaves (Decision 3) and the timeout (Decision 5) are decided here with their
reasons, so nothing waits. No entry is added to `../questions-for-the-owner.md`.

## Landing notes
