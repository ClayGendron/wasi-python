# 040 — x86_64 rebuilds the same bytes

- **Status:** drafted 2026-10-17; revised the same day against its pre-build review
  (`../reviews/040-x86-64-rebuilds-the-same-bytes-spec-2026-10-17.md`). All eight findings are
  written in, and its Disposition says where. **Confirmed for build with conditions, written
  in.**
  - Condition A, the loader probe, is in Decision 5.
  - Condition B: the builder starts from `d98249b`, where 028 has landed, and takes main's
    `release.yml` `verify` job as it is. 028 changed only that job, so 040's `rebuild` and
    `same-bytes` edits do not overlap it.
  - **Built 2026-10-18** from main at `64663de` (Landing notes): three hosts wrote one
    `SHA256SUMS`. Its build review (`../reviews/040-x86-64-rebuilds-the-same-bytes-2026-10-18.md`)
    says land after four text answers; they are written in (Decisions 5, 9 and 11, the upstream
    draft), and the review's Disposition says where.

  It changes the build recipe and the release workflow, so it was reviewed before it is built
  (constitution §5.6). It is build-class: it touches `scripts/`, `downloads/SHA256SUMS` and the
  release workflow (§5.7). It builds next after 033 lands (Decision 12).
- **Owner:** Clay Gendron
- **Kind:** the build recipe (`scripts/line.conf`, `line.sh`, `00_download.sh`,
  `steps/common.sh`, `steps/10_tools.sh`, `steps/60_link.sh`, and a new compiler launcher,
  `scripts/clang-emulated`), the pins (`downloads/SHA256SUMS`), the release workflow's `rebuild`
  and `same-bytes` jobs, judge additions in `tests/`, an upstream issue draft under
  `context/upstream/`, an addendum to the x86_64 memo, `README.md`, `CHANGELOG.md`.
- **Depends on:** 012 (the same bytes from any host: the host keys, the host-neutral wasm
  runtime, the `rebuild` and `same-bytes` jobs), 016 (the rebuilt wheel's comparison), 020
  (`MANIFEST` and the recipe hashes). All landed.
- **Research it stands on:**
  `../research/2026-10-17-x86-64-rebuilds-differ-in-one-function.md` and its folder
  `../research/2026-10-17-the-x86-64-rebuild/`. x86_64 Linux builds the same zip, `MANIFEST` and
  licences, and its Wizer step is host-independent. Its `python.wasm` differs by 21 bytes, all in
  numpy's `npy_cpowl`. One object differs, from equal source and equal flags, and each host's
  clang is deterministic. The memo did not trace the cause past the compiler binary and
  recommended no fix. It named three routes: a compiler that gives the same output on every
  host, an x86_64 build that runs aarch64's compiler under emulation, or an upstream LLVM fix.
  Also `../research/2026-10-17-the-linux-build-experiment/` (the containers and the pinned
  Debian image), and four experiments run while drafting this specification. They ran in a
  scratch folder, outside the repository; their commands and results are in Decision 1, and the
  builder reproduces them into the research folder first (Decision 10).

## The problem

The release gate proves that arm64 macOS and arm64 Linux build the same artifact set. It says
nothing for x86_64 Linux, which is most of the world's servers and CI. A person who wants to
check our bytes on the machine they have, most likely x86_64, cannot today. Spec 012 took its
fallback for x86_64: it stays a pinned build host outside the `same-bytes` gate, and the README
says its rebuilds are not yet byte-identical. The roadmap's hardening milestone asks for "x86_64
Linux rebuilds byte-identical" (`../roadmap.md`, milestone 6).

The difference is not in our recipe. It is in wasi-sdk's x86_64 compiler binary, which, given the
same input and the same flags, lays out one function's stack differently from the aarch64
compilers. No source tree we build differs, so no recipe file and no carried patch can reach it.

## Decisions

1. **The cause, as far as it is traced.** Each fact was run while drafting (EXECUTED), in a
   scratch folder, against the pinned SDKs, each checked against `downloads/SHA256SUMS` first.
   - **One file reproduces it.** numpy's `npy_math_complex.c` was preprocessed with the build's
     own command from `build/numpy-build/compile_commands.json` (`-E -P`, 324,353 bytes). That file
     compiled with the build's code-generation flags (`--target=wasm32-wasip1 -std=c11 -O3
     -fno-strict-aliasing -ftrapping-math -fvisibility=hidden
     -Wno-unsupported-floating-point-opt -w`) gives `20ef33440bb2e944…` with the arm64 macOS SDK,
     the build's own aarch64 object. In a `linux/amd64` container of the experiment's pinned
     Debian image, the x86_64 Linux SDK (`0ba8b5bf…`) gives `d36897438056e356…`, the x86_64
     build's object. So the whole difference reproduces from one self-contained file. The
     build's warning flags (`-Wall`, `-Wno-unsupported-floating-point-opt`) change no object:
     the review got the same object with and without them (EXECUTED there).
   - **The IR is equal; instruction selection differs.** With `-mllvm -print-after-all -mllvm
     -filter-print-funcs=npy_cpowl`, each host prints 65,227 lines with `-w` (65,236 without it:
     nine warning lines, as the review counted). Every IR pass prints the same
     function on both hosts. Three header lines differ only in how each compiler build spells a
     template name (`RequireAnalysisPass<…, llvm::AnalysisManager<Module>>` against
     `RequireAnalysisPass<…>`). The first difference in content is the output of "WebAssembly
     Instruction Selection (wasm-isel)": two `__multf3` calls (128-bit `long double`
     multiplies) receive their 16-byte result slots in swapped order (`%stack.25` and
     `%stack.28`). Every later pass carries the swap to the memo's offsets 112 and 160.
   - **The scheduler is not a lever.** Each of the seven `-mllvm -pre-RA-sched` choices
     (default, `source`, `list-burr`, `list-hybrid`, `list-ilp`, `linearize`, `fast`) gives
     different objects on the two hosts. So the slots are ordered before scheduling, inside
     instruction selection.
   - So the memo's explanation through register allocation's spill weights (INFERRED there) is
     ruled out: the choice is made before register allocation. Why instruction selection orders
     the two slots differently on the two hosts is not traced. The SDK's compilers are release
     builds, without `-debug-only`. That each host is deterministic and gets equal IR points to
     the compiler's own build, such as floating-point contraction in the aarch64 build of LLVM
     (INFERRED; not shown).
   - **The aarch64 compiler, emulated on x86_64, gives the aarch64 bytes.** The pinned arm64
     Linux SDK (`4f98ee73…`) was run in the `linux/amd64` container under Debian's
     `qemu-aarch64` 10.0.13, on the same file. It wrote `20ef33440bb2e944…`. It was run with
     five Debian packages unpacked into a folder (`dpkg-deb -x`; nothing installed), and with
     the launcher design of Decision 5. `clang -v` reported the aarch64 tree as its
     `InstalledDir`. Compile-only, compile-and-link in one call, link alone and `clang++` mode
     all worked. The first attempt failed compile-and-link: the driver re-ran itself for `cc1`
     by its canonical path, the aarch64 ELF, which an x86_64 kernel cannot run. The second
     attempt passed `-no-canonical-prefixes`, with the launcher as `argv[0]`. Then the re-run
     came back through the launcher. With that flag the object was still `20ef3344…`.
   - Benchmark fact, not representative: that one compile took 22 s emulated against 1 s
     native. This was qemu inside Rosetta, two emulators nested.

2. **The fix: the x86_64 host compiles with the aarch64 compiler, under a pinned emulator.**
   On `LINUX_X86_64`, every C and C++ compile runs the pinned arm64 Linux wasi-sdk's own clang
   under `qemu-aarch64`. Every other tool stays native x86_64.
   - **Why this route.** It fixes the whole class by construction, not one tie. Every host then
     compiles with an aarch64 build of the pinned clang: the Mach-O build on macOS, and the same
     ELF build on both Linux hosts, which qemu runs on x86_64 with aarch64's arithmetic exactly.
     The two aarch64 builds already agree (spec 012). It is a recipe item, a compiler wrapper, which §4.1 lists first. It
     changes no byte of any artifact on any host (Decision 8). It is EXECUTED on the one object
     that differs (Decision 1).
   - **Why not a flag.** A flag needs the exact cause, which is untraced, and the scheduler, the
     one lever found, does not work. A flag that only moved this one tie would prove nothing
     about the next numpy or scipy release (the memo's own objection). A per-file workaround is
     refused for the same reason.
   - **Why not a carried patch.** §4.1 allows one only where a source change is unavoidable,
     and it applies to source trees we build. The tree that differs is a downloaded binary
     compiler, which we do not build. A patch to LLVM would need us to build LLVM on every host:
     a new toolchain, hours per build, and every byte changed. That is not the smallest thing
     (§6.4).
   - **Why not wait.** No upstream issue exists yet, so there is no date. The upstream issue is
     drafted (Decision 9), and the emulation is temporary in the same way a carried patch is.
   - **Why only the compiler is emulated.** The memo's x86_64 build, all native, made the same
     zip, `MANIFEST`, licences and snapshot step. Its reactor differed only in the one function
     whose object differed (EXECUTED, memo findings 1 to 3 and 6). So `wasm-ld`, `llvm-ar`,
     `llvm-ranlib`, wasmtime, the host Python, Cython, meson and ninja already agree natively.
     Emulating them would cost time and prove nothing more. The `same-bytes` gate would catch
     any of them that stopped agreeing.

3. **The pins: five Debian packages, for the x86_64 host only.** Each is a
   `snapshot.debian.org` URL, which does not change when Debian moves on, plus a SHA-256. Each
   SHA-256 is the one Debian's signed `Packages` index gives (EXECUTED: `apt-cache show` in the
   pinned `debian:trixie-slim` image). `apt-get download` wrote matching bytes for the two it
   printed. The URLs are READ from snapshot.debian.org's API (`first_seen`), and the builder
   checks that each URL serves those bytes.

   | file | bytes | SHA-256 | snapshot path |
   |---|---|---|---|
   | `qemu-user_10.0.13+ds-0+deb13u1_amd64.deb` | 71,089,852 | `ca6ede739327a20ae5a3498230c8a3a9a072c586e131bc6bcc1201eb1725e336` | `20260905T205002Z/pool/main/q/qemu/` |
   | `libc6_2.41-12+deb13u4_arm64.deb` | 2,483,572 | `8784eda966b189c777a384dac5ce009e8fc9b52d006926c5a013e7fa8aa688cc` | `20260711T202405Z/pool/main/g/glibc/` |
   | `libstdc++6_14.2.0-19_arm64.deb` | 637,536 | `6669b0c52a2e7c6af9adfdabce3ff6e286065cdfbc7b85280862b5f799daebee` | `20250317T031857Z/pool/main/g/gcc-14/` |
   | `libgcc-s1_14.2.0-19_arm64.deb` | 54,104 | `1108bc87879833d6d9a145f22a4a15cddb34e065b4b5f4b97bee586adbac2851` | `20250317T031857Z/pool/main/g/gcc-14/` |
   | `libtinfo6_6.5+20250216-2_arm64.deb` | 341,360 | `2a747f7fff3c2347c357387a7133df997410f07ba1b1df1a1461a97bd7fbc2fc` | `20250306T211336Z/pool/main/n/ncurses/` |

   Each URL is `https://snapshot.debian.org/archive/debian/<path><file>`, with `+` written as
   `%2B`, as the existing `cpython-…%2B…` pin writes it. The review fetched all five from these
   URLs and each matched its size and SHA-256 (EXECUTED there). If snapshot.debian.org is slow
   or throttles, `get`'s `curl --retry 3` is the only defence. A fetch that still fails stops
   the build with one line, before anything runs, which is acceptable.
   - **Why these packages.** `qemu-aarch64` in Debian's `qemu-user` is a static-pie binary
     (EXECUTED, `file`), so it needs nothing. The SDK's clang is dynamic. It needs `libc6`,
     `libstdc++6` and `libgcc-s1`, and its `libLLVM` needs `libtinfo.so.6` (EXECUTED: `NEEDED`
     lines, and the first emulated run's error). Its `libedit.so.0` ships in the SDK.
   - **The arm64 Linux SDK is already pinned** (`wasi-sdk-33.0-arm64-linux.tar.gz`,
     `4f98ee73…`) for the aarch64 host. The x86_64 branch of `00_download.sh` fetches it too.
   - **Downloads stay untrusted** (§4.8). The packages unpack under `build/tools/`, never into
     the system. Nothing is registered with the kernel (no `binfmt_misc`). qemu runs only as a
     build tool, and so do the libraries, inside the emulated compiler.
   - **Licences.** qemu (GPL-2.0), glibc (LGPL-2.1), libstdc++ and libgcc (GPL-3.0 with the
     GCC runtime exception) and ncurses (X11) are build tools here, like the runner's `cc`.
     Nothing of them is linked into, or shipped with, an artifact. So §4.12 is not engaged. The
     README names them among the x86_64 host's inputs.

4. **The line names the compiler per host.** `scripts/line.conf` gains a sixth host name,
   `COMPILER_SDK_DIR`, for every host key. It is the SDK whose clang compiles on that host.
   - `MACOS_ARM64_COMPILER_SDK_DIR=wasi-sdk-33.0-arm64-macos` and
     `LINUX_AARCH64_COMPILER_SDK_DIR=wasi-sdk-33.0-arm64-linux`: each host's own SDK.
   - `LINUX_X86_64_COMPILER_SDK_DIR=wasi-sdk-33.0-arm64-linux`: the aarch64 host's SDK.
   - `LINUX_X86_64` alone gains the five emulation names: `EMULATOR_DEB`,
     `AARCH64_LIBC_DEB`, `AARCH64_LIBSTDCXX_DEB`, `AARCH64_LIBGCC_DEB` and
     `AARCH64_LIBTINFO_DEB`, each set to the file name above. The line's grammar takes them.
   - `line.sh` sets `COMPILER_SDK_DIR` for the running host. It sets the emulation names where
     the key has them. `common.sh` derives `CSDK="$T/$COMPILER_SDK_DIR"`, which is `$SDK` on the
     two arm64 hosts. `line.py`, the judge's reader, needs none of these and is unchanged.
   - So the claim is in one file: every host compiles with an arm64 build of the pinned clang.
     Two hosts run it natively. One runs it under the pinned emulator.

5. **Step 10's x86_64 branch, and the launcher.** Where `CSDK` differs from `SDK`, step 10
   also does the following, after spec 012's runtime replacement.
   - It unpacks the arm64 Linux SDK to `$CSDK`. It gives that tree the same host-neutral
     sysroot and builtins (spec 012, Decision 2; the replacement becomes one function, run on
     each tree). The emulated driver passes this tree's sysroot and builtins to the link.
   - It extracts the member `./usr/bin/qemu-aarch64` alone from the `qemu-user` package into
     `$T/emulator/`. The member is stored with its `./`, and GNU tar matches the stored name.
     It extracts the four runtime packages into `$T/aarch64-root/`, and adds the
     `lib -> usr/lib` link that a merged-`/usr` system gives (the loader's path is
     `/lib/ld-linux-aarch64.so.1`). Each package is an `ar` archive, read with the native SDK's
     `llvm-ar` and the host's `tar`. `dpkg-deb` is not assumed.
   - It writes an empty `$T/aarch64-root/etc/ld.so.cache`. Without it, qemu's `-L` falls
     through to the host's `/etc/ld.so.cache`, and the guest's loader reads that. The review
     showed both cases under `qemu -strace` (EXECUTED in its confirmation). Without the file,
     the loader opens `/etc/ld.so.cache` and maps 4,095 bytes, the host file's size. With the
     empty file in the root, it opens it, maps nothing, and goes straight to
     `/lib/aarch64-linux-gnu`. Gate probe 5 holds this on every x86_64 build. The host's cache
     is never read.
   - It copies `scripts/clang-emulated` (our recipe file) into `$CSDK/bin/`. It replaces the
     real clang binary of the native tree (the file `$SDK/bin/clang` resolves to) with a
     symbolic link to that copy. So every caller is unchanged: CPython's `Platforms/WASI`
     driver, `scripts/wasi-cc` and `wasi-cxx`, and steps 30 and 35, which all run
     `$SDK/bin/clang` or `clang++`. The native compiler is gone from the tree, so no step can
     reach it by accident.
   - It replaces `$CSDK/bin/wasm-ld` with a two-line script that runs the native
     `$SDK/bin/wasm-ld` with the same arguments. The emulated driver runs `wasm-ld` from its own
     tree; that one is aarch64, and without `binfmt_misc` the x86_64 kernel cannot run it
     (EXECUTED, Decision 1).
   - **A gate.** Step 10 stops with one line unless each of these holds:
     - the file `$SDK/bin/clang` resolves to is a link to `$CSDK/bin/clang-emulated`;
     - `$SDK/bin/clang -v` names `$CSDK/bin` as its `InstalledDir`;
     - `$SDK/bin/clang-cpp`, given a two-line file holding `__clang__` and
       `__cplusplus`, prints the first expanded and the second not (cpp mode, C);
     - `$SDK/bin/clang++ -v` names `clang++.cfg` as its configuration file (g++ mode);
     - **The host's loader cache is not read** (condition A of the review's confirmation).
       Step 10 runs `$T/emulator/qemu-aarch64 -strace -L $T/aarch64-root
       $CSDK/bin/<clang> --version` directly, not through the launcher. It requires the trace
       to show the `ld.so.cache` open followed by no `mmap` of it before the next `openat`, and
       `--version` to exit 0.
       - **Why this probe, not `LD_DEBUG=libs`.** The trace records the system calls with
         qemu's `-L` redirection already applied. So it tells the empty root file (nothing
         mapped) from the host's file (4,095 bytes mapped), which is the fact that matters.
         `LD_DEBUG=libs` prints only the paths the guest sees, so `search
         cache=/etc/ld.so.cache` prints either way (EXECUTED by the review, nine lines in both
         cases). It also makes the launcher's native `sh`, `readlink` and `dirname` print, so
         its lines must be picked out by pid. A test that the root's file exists and is empty
         checks the setup, not the effect. The trace checks the effect.
       - The probe needs no environment of its own. It runs the pinned emulator on the pinned
         clang, which is what every compile does.
       - **As built** (the build review, finding 4): the probe passes the launcher's three `-U`
         flags to qemu too, so a host `LD_PRELOAD` cannot change what the guest's loader does
         during the probe, as it cannot during a compile. It is still not run through the
         launcher, so it checks the root, not the launcher, and it does not clear `QEMU_`
         variables. No `QEMU_` variable makes it pass falsely (INFERRED by the review):
         `QEMU_STRACE` is already on, `-L` overrides `QEMU_LD_PREFIX`, the later `-U` flags undo a
         `QEMU_SET_ENV` of the loader's variables, and a `QEMU_LOG_FILENAME` hides the trace, so no
         cache open is seen and the gate fails closed.
     Each tree's other tools (`llvm-ar`, `llvm-ranlib`, `llvm-nm`) are run from `$SDK` as
     today.
   - **The launcher's contract** (`scripts/clang-emulated`, a POSIX `sh` script).
     - **Where it lives.** It is copied into `$CSDK/bin/`, the directory of the real aarch64
       clang. That matters twice: the driver takes its `InstalledDir` from `argv[0]`, and the
       guest's loader finds `libLLVM` and `libclang-cpp` through the clang's RPATH,
       `$ORIGIN/../lib` (EXECUTED by the review).
     - It finds its own directory `A` with `readlink -f "$0"`. It takes `T` as two levels above
       it, and the real clang as what `$A/clang` links to.
     - **The name sets the mode, exactly.** The name it was called by (`basename "$0"`) maps to
       a driver mode: `clang` to none, `clang++` to `--driver-mode=g++`, `clang-cpp` to
       `--driver-mode=cpp`. Any other name stops it with one line naming the name. The SDK's
       other links to the replaced file (`clang-cl`, the target-prefixed `wasm32-…-clang`
       names) are used by no step, and a refusal is better than a silently lost mode. The
       driver itself always sees `argv[0]` as `…/clang-emulated`, so without this map it would
       run every name in gcc mode (EXECUTED by the review: `clang-cpp` failed CPython's
       preprocessor probe).
     - **The environment is cleared of what only the emulator reads.** Before it runs qemu it
       unsets every variable whose name starts with `QEMU_` (a loop over `env`'s names, POSIX
       `unset`). It passes `-U LD_PRELOAD -U LD_LIBRARY_PATH -U LD_AUDIT`, so the guest's
       loader never sees the host's. EXECUTED by the review: `QEMU_SET_ENV` changed the
       object, and a host `LD_PRELOAD` made the emulated preprocessor print to stderr, which
       autoconf counts as failure.
     - An argument list that starts with `-cc1` or `-cc1as` is the driver re-running itself.
       It runs `$T/emulator/qemu-aarch64 -L $T/aarch64-root -U LD_PRELOAD -U LD_LIBRARY_PATH
       -U LD_AUDIT -0 $A/clang-emulated <clang> "$@"` and inserts nothing after the clang path.
     - Any other call is a driver call. It runs the same command with `-no-canonical-prefixes`
       and the name's mode, if any, ahead of the caller's arguments.
     - Arguments pass through untouched, spaces included.
     - A missing emulator, root or clang stops it with one line naming the path.
     - **The closure.** The emulated driver may run only two programs: the launcher (for
       `-cc1` and `-cc1as`) and `$CSDK/bin/wasm-ld` (the redirect to the native linker).
       Anything else it tried to run would be an aarch64 ELF, which fails on a host without
       `binfmt_misc`. That is why the CI rebuild job lists `binfmt_misc`'s entries
       (Decision 6): a runner with an aarch64 entry would run such a program through its own,
       unpinned qemu, and hide the gap.
   - Step 60's link-map check (spec 012, Decision 2) reads the replaced directories under
     `$CSDK`, which is where the emulated driver's link paths point. On the arm64 hosts
     `$CSDK` is `$SDK`, so nothing changes there.
   - **The zip names no host** (spec 012, Decision 5). The aarch64 tree's name holds `arm64`,
     which the v1.5 zip check refuses on every host. If the name reaches `_sysconfigdata` or
     numpy's `__config__`, the check fails. Step 70 then gains that name as a computed rewrite,
     ahead of the SDK's own name, in the style of spec 012's Decision 5. If it reaches neither member, no
     rewrite is added.

6. **The release workflow: x86_64 joins the gate.**
   - `rebuild`'s matrix becomes `[ubuntu-24.04-arm, ubuntu-24.04]`.
   - `same-bytes` downloads both runners' `SHA256SUMS` and rebuilt wheels. Both of its loops
     (the set's `SHA256SUMS`, and spec 016's wheel) run over both runners.
   - **Each runner keeps its own time limit.** The matrix's `include` gives each runner a
     `timeout`: `ubuntu-24.04-arm` keeps 120 minutes, and `ubuntu-24.04` gets 360, GitHub's
     limit for a hosted job. `rebuild` sets `timeout-minutes: ${{ matrix.timeout }}`. So a hung
     arm64 job still frees the gate after two hours. An emulated compile is slower (Decision
     1), and the time is a benchmark fact the dry run records. It is never a check.
   - **"The runner's own tools" step prints two more facts:** `nproc`, so every time figure
     carries its core count, and the entries under `/proc/sys/fs/binfmt_misc/` (or that there
     are none), so a runner that could run aarch64 ELFs by itself is visible (Decision 5's
     closure).
   - The comments on `rebuild` and `same-bytes` stop saying x86_64 is outside the gate. Instead
     they say how its compiler runs.
   - Nothing else changes. `attest` and `publish` already need `same-bytes`. So a tag is never
     signed or published unless the x86_64 runner rebuilt the same set.

7. **The judge's checks.** Each is written, and seen failing, before the code it guards (AGENTS.md
   rule 3).
   - **`test_x86_64_compiles_with_an_aarch64_compiler`** (rules, `test_rules.py`;
     `scan.compiler_table_errors`). It requires:
     - every host key has `COMPILER_SDK_DIR`, naming a pinned SDK whose name says `arm64`;
     - a key whose `COMPILER_SDK_DIR` equals its `WASI_SDK_DIR` has no emulation name;
     - a key whose `COMPILER_SDK_DIR` differs has all five emulation names, and that SDK is
       another key's own `WASI_SDK_DIR`, so the emulated compiler is one a host runs natively;
     - each of those six files is pinned and fetched in that key's own branch of
       `00_download.sh`;
     - `10_tools.sh`, read without its comments (the scan's `_code_lines`), names
       `clang-emulated`, `aarch64-root`, `ld.so.cache` and the gate's `InstalledDir` and
       `clang-cpp` probes and its `-strace` loader-cache probe, so a comment cannot satisfy it;
     - `scripts/clang-emulated`, read without its comments, holds the three `-U` loader
       flags, the `QEMU_` clearing, and the three names `clang`, `clang++` and `clang-cpp`
       with their modes.
     On today's tree it fails: no key has `COMPILER_SDK_DIR`, and there is no launcher.
     `tests/unit/test_scan.py` gains one mutation per rule, each naming its breach.
   - **`test_release_workflow_rebuilds_on_two_more_hosts`** (v1.5). This is spec 012's name
     again; it is now `…_on_a_second_host`, which the landing retires (Decision 8).
     `scan.REBUILD_RUNNERS` gains `ubuntu-24.04`. The scan also requires each gated runner in
     `same-bytes`' wheel loop, which it does not check today. It requires `timeout-minutes` to
     come from the matrix, with 120 for `ubuntu-24.04-arm` and 360 for `ubuntu-24.04`. And it
     requires the runner's tools step to print `nproc` and `binfmt_misc`. On today's workflow it fails with `rebuild's matrix lacks ubuntu-24.04` and
     `same-bytes does not name ubuntu-24.04`. `tests/unit/test_scan.py` gains the matching
     mutations: each runner dropped from each place.
   - **`tests/unit/test_clang_emulated.py`.** The launcher's contract runs against a stand-in
     emulator, a script that writes its arguments one per line, in a temporary tree with
     Decision 5's layout. It checks, by counting and comparing arguments:
     - a driver call through `clang` gets `-L`, `-0` and `-no-canonical-prefixes` once each,
       and no driver mode, with every argument intact, one holding a space;
     - a call through `clang++` gets `--driver-mode=g++` once, and one through `clang-cpp`
       gets `--driver-mode=cpp` once;
     - a call through any other name (`clang-cl`) stops with a non-zero exit, one line, and no
       emulator run;
     - a `-cc1` call gets nothing inserted after the clang path, and `-cc1` stays first;
     - every call passes `-U LD_PRELOAD`, `-U LD_LIBRARY_PATH` and `-U LD_AUDIT` once each;
     - with `QEMU_SET_ENV` and `QEMU_CPU` set in the caller's environment, the stand-in
       emulator, which also writes its environment's `QEMU_` names, receives none;
     - a missing emulator stops it with a non-zero exit and one line.
     It is skipped where `sh` is absent (the Windows `verify` job). It fails today: there is no
     launcher.
   - **Unchanged and still passing:** `test_every_build_host_has_its_whole_table` (its five
     names stay; `COMPILER_SDK_DIR` belongs to the new check),
     `test_toolchain_is_pinned_for_linux_and_macos`, and the v1.5 zip check.
   - The scoreboard's not-machine-checked list does not change. The x86_64 rebuild is
     machine-checked by the workflow, as arm64's is.

8. **The bytes do not change.** The fix runs only on x86_64. On the arm64 hosts nothing
   compiles differently, so `python.wasm`, the snapshot, the zip and the licences keep their
   accepted hashes. Fuel does not move. `MANIFEST` changes on every host, and so does
   `SHA256SUMS` with it. It lists every host's pins, which gain five, and every tracked file
   under `scripts/`, which gains one and changes several.
   - **The landing's flags.** `--accept-judge` with its reason (the new checks, the workflow
     check's new rules), and `--retire
     tests/checks/test_v1_5_rebuild_from_pins.py::test_release_workflow_rebuilds_on_a_second_host`,
     because the ratchet turns a vanished check red (`context/progress/README.md`). The
     renamed check passes under its new name in the same run.
   - **No `--accept-growth`.** The judge records `bytes` only for `python.wasm` and the zip
     (READ by the review: `test_v1_1_artifact_set.py`), not for `MANIFEST`, and neither of those
     moves. If any metric grows, that is a defect in this change, not growth to accept.
   - A binary hash that moves on any host is a defect too.

9. **Temporary, with an upstream issue drafted.** The emulation is a workaround for an
   upstream behaviour, held to §4.1's rules for a patch.
   - **The draft.** `context/upstream/4-llvm-wasm-isel-slot-order/` holds `issue.md`, the text
     of an LLVM issue for the owner to send (wasi-sdk is named in it, as the builder of the
     per-host binaries). It holds `notes.md`, how it was found, and `evidence/` (Decision 1's
     commands and outputs).
   - **The reproducer.** The builder reduces Decision 1's file by hand to a small C function
     that keeps the two-host difference, within a one-hour box. If the box runs out, the issue
     cites numpy 2.5.2's `npy_math_complex.c` and the build command.
   - **AI policy.** The builder checks LLVM's policy on AI-assisted contributions. If it
     requires a person to write the text, `issue.md` holds the facts for the owner, as the
     numpy draft does.
   - The upstream README's table gains the row.
   - **When the emulation leaves.** When the line moves to a new wasi-sdk, that change compiles
     the reproducer with the new SDK's x86_64 and aarch64 compilers, natively, the x86_64 one on
     a real x86_64 CPU. If the objects are equal, it runs one native x86_64 rebuild on real
     x86_64: the release workflow's `ubuntu-24.04` runner, in a dry run with the emulation off,
     not the research container, which runs under Rosetta (the build review, finding 1). If
     that set equals the others, the same change removes the launcher, the five pins, the emulation
     names and the x86_64 branch of step 10. `COMPILER_SDK_DIR` stays, each host naming its own
     SDK. The CHANGELOG records it.

10. **The evidence moves into the repository first.** Decision 1 ran in a scratch folder. The
    builder starts by re-running it from the research folder,
    `../research/2026-10-17-the-x86-64-rebuild/`. The scripts go there (the preprocessing, the
    pass print and its diff, the scheduler sweep, the emulated compile), and so do the outputs.
    The memo gains a dated addendum, "Traced further (spec 040)", with Decision 1's findings.
    Its finding 7 is marked as superseded where the new facts rule it out. The preprocessed
    file itself is numpy's and wasi-libc's text; it is regenerated, not committed.

11. **Time is recorded, never tested, and acted on before the limit.**
    - **Recorded.** The x86_64 rebuild's wall time, emulated, on the `ubuntu-24.04` runner, with
      `nproc` beside it, goes into the landing notes as a benchmark fact (§4.9). So does every
      later build-class specification's x86_64 rebuild time. None of it is ever a check.
    - **A trip-wire at 240 minutes.** When an x86_64 rebuild's wall time passes 240 minutes,
      the landing notes of the change that measured it say so. The agent then writes it in
      `../questions-for-the-owner.md` and asks the owner before the next build-class
      specification lands. The choices are a larger runner, or x86_64 out of the gate as below.
      This leaves two hours of margin under the 360-minute limit for the next specification's
      growth.
    - **At the limit.** If a rebuild ever needs more than 360 minutes, the release cannot pass
      the gate. The agent then stops and asks the owner, as at the trip-wire. It does not lower
      the gate on its own.
    - **A same-day fallback if the first real run fails after landing.** Dry run 2 may first
      run after landing (criterion 5). If its `ubuntu-24.04` rebuild fails, times out, or
      `same-bytes` finds a difference there, then x86_64 leaves the gate on the same day, by
      one change through the lane.
      - **First, once, a re-run** (the build review, finding 3). A failure before step 10, or
        one whose log has no recipe line (a fetch from `snapshot.debian.org` or another origin,
        or a lost or cancelled runner), is re-run once first. The fallback is for a failure that
        repeats, for a timeout of the build itself, or for any byte difference in `same-bytes`.
      - That change removes `ubuntu-24.04` from `rebuild`'s matrix and `include`, from both of
        `same-bytes`' loops and its two downloads, and from `scan.REBUILD_RUNNERS`. The
        workflow check's x86_64 timeout rule goes with it.
      - It restores spec 012's README sentence ("x86_64 Linux is a pinned build host too, but
        its rebuilds are not yet byte-identical") with the run's link.
      - It keeps everything else: the launcher, the pins, `COMPILER_SDK_DIR` and its rule check.
        x86_64 still builds with the emulated compiler, outside the gate.
      - It is recorded in 040's landing notes ("fallback taken", the run, the job that failed,
        and its first failing line), in the CHANGELOG, and in the memo's addendum.
      - It is reviewed by a fresh agent like any change, accepted with `--accept-judge` and its
        reason, and lands before anything else does.
      - So no release waits on an undecided problem. The cause is then worked on in the memo,
        and x86_64 rejoins the gate by its own change.

12. **The order of work.** §5.7 and AGENTS.md rule 2 allow one build-class specification in
    flight.
    - **The queue as it stands:** 028 (landed, `d98249b`), then 033 (in build), then
      **040**, then 035, 023, 037 and 039.
    - **Why 033 went before 040.** 040 was not confirmed when 028 landed, so 033 took the slot,
      as the fallback below provides. 040 builds next, after 033 lands, and rebases onto main
      as it then stands. 033 changes only the zip, so the rebase touches no file 040 edits but
      `MANIFEST`'s recipe list, which is computed.
    - **040 next.** It is small: one launcher, five pins, one step's branch, a
      matrix entry, three checks. It changes no artifact byte, so it moves no number that a
      later specification measures. Every specification after it then has its new compiles
      gated on x86_64 from their first build, rather than in a later change of their own.
      That matters most where the most compiles are new.
    - **033 and 035 against 040.** They are cheap to gate and move no compile volume worth
      waiting for, so their order against 040 matters little.
      - 033 changes only the zip (`make_stdlib_zip.py`, step 70, a Python stand-in). It
        compiles nothing, so 040 gates nothing new in it. Its numbers do not move with 040, nor
        040's with it.
      - 035 compiles one changed file, `recipes/reactor_main.c`. Gated after 040, its one new
        object is checked on x86_64 at once.
      - **If 040 is not confirmed when 028 lands,** 033 takes the slot, and 040 takes the next
        slot after its confirmation. This is what happened: 040 is confirmed, so it goes after
        033 and before 035. Neither waits on 040.
    - **023 after 040, 033 and 035.** 023 adds the most C and C++ before scipy: FreeType,
      HarfBuzz, SheenBidi, libraqm, Qhull, Agg, kiwisolver, and matplotlib's own extensions.
      It is the first place a new tie is likely to show. Gated from its first build, 023's
      builder finds it within the two-attempt rule. Bringing x86_64 in after 023 would mean
      someone else finding 023's ties later. 023's text says nothing of x86_64 today. Once
      040 has landed, the rule below binds it, as it binds 037. 023's landing notes record
      the x86_64 rebuild's wall time with matplotlib.
    - **037 after 023,** as it already depends (023, 033, 035).
    - **039 last.** It depends on 033, 035 and 023. Its 31 pins are pure-Python packages, so it
      compiles nothing, and its order with 037 does not matter to 040. The roadmap puts scipy
      (milestone 3) before the rest of the profile (milestone 4), so 037 goes first.
    - **031** is build-class too (it adds `recipes/guest/` and changes step 70). It compiles
      nothing, so its place in the queue does not matter to 040.
    - **What 037 does after 040 lands is already written** in its revision (`fe71eb0`):
      - its x86_64 text is conditional on 040 landing first;
      - every `getarch` value that reaches a compile flag is fixed on the make line;
      - its landing notes record the x86_64 rebuild's wall time with scipy, emulated, with
        Decision 11 applying if that time nears the limit.
      Its new compiles need no change. OpenBLAS compiles through `scripts/wasi-cc`. scipy,
      f2py's C and the C++ subprojects compile through meson's cross file. All of them reach
      `$SDK/bin/clang` or `clang++`, which is the launcher on x86_64. OpenBLAS's
      `HOSTCC=cc` for `getarch` stays native (READ by the review).
    - **The same rule binds every later build-class specification.** From 040's landing,
      the three hosts' sets are equal, with no host excepted. A specification that cannot keep
      them equal stops after two attempts and writes a memo (AGENTS.md rule 7). It does not
      land with an exception. Its landing notes record its x86_64 rebuild time (Decision 11).
    - **If 023 or 037 lands before 040 after all,** 040's builder gates their objects too. Its
      landing notes then record the x86_64 wall time with them. The design is the same.

13. **Documentation.**
    - **README.** "The same bytes from any build host" says all three hosts give the same
      set. It says the x86_64 host compiles with the pinned aarch64 compiler under qemu, and
      why, linking the memo and the upstream draft. It names the five packages among the x86_64
      host's inputs. The "x86_64 Linux rebuilds byte-identical" item leaves the README's list.
    - **CHANGELOG.** One entry: x86_64 Linux joins the same-bytes gate, how, and the upstream
      draft.
    - The workflow's comments, as in Decision 6.
    - Spec 012 is landed and its text stays as it landed. Its landing notes already point to
      the memo, and the memo's addendum points here.

## Intent

Anyone can rebuild the published sandbox from its pins on arm64 macOS, arm64 Linux or x86_64
Linux, and get the same artifact set, byte for byte. CI proves all three on every release, before
anything is signed. On x86_64, the compiler is the pinned aarch64 build of clang, run under a
pinned emulator. That is because wasi-sdk's x86_64 clang orders two stack slots differently in
one numpy function, and that difference is reported upstream.

## Design

```
scripts/line.conf                COMPILER_SDK_DIR per host; five emulation names for LINUX_X86_64
scripts/line.sh                  sets COMPILER_SDK_DIR and the emulation names for the running host
scripts/00_download.sh           LINUX_X86_64: the arm64 Linux SDK and the five .deb pins
scripts/steps/common.sh          CSDK
scripts/steps/10_tools.sh        the runtime replacement as one function, run on each tree;
                                 x86_64: the emulator, the aarch64 root, the launcher, the
                                 wasm-ld redirect, an empty ld.so.cache, the gate (five probes)
scripts/clang-emulated           new: the launcher (names to modes, QEMU_ and LD_ cleared)
scripts/steps/60_link.sh         the link-map check reads $CSDK
scripts/steps/70_zip.sh          a computed rewrite of the aarch64 tree's name, only if it leaks
downloads/SHA256SUMS             five pins
.github/workflows/release.yml    rebuild: ubuntu-24.04 added, per-runner timeouts (120, 360),
                                 nproc and binfmt_misc printed; same-bytes: both loops
tests/harness/scan.py            compiler_table_errors; REBUILD_RUNNERS; the wheel loop rule
tests/checks/test_rules.py       test_x86_64_compiles_with_an_aarch64_compiler
tests/checks/test_v1_5_rebuild_from_pins.py   the workflow check, renamed
tests/unit/test_scan.py          the new mutations
tests/unit/test_clang_emulated.py   the launcher's contract
context/upstream/4-llvm-wasm-isel-slot-order/   issue.md, notes.md, evidence/; README row
context/research/2026-10-17-the-x86-64-rebuild/  Decision 1's scripts and outputs
context/research/2026-10-17-x86-64-rebuilds-differ-in-one-function.md   the addendum
README.md, CHANGELOG.md
```

## Scope

In: the above.

Out:
- tracing the tie inside LLVM's instruction selection past Decision 1, which is the upstream
  issue's business;
- building LLVM or wasi-sdk from source;
- emulating any tool other than clang;
- x86_64 macOS, Windows or any other build host;
- pinning the runner images' own packages (spec 012, Decision 10);
- a published container recipe for local x86_64 rebuilds (the research folder's `Dockerfile`
  serves);
- a larger or paid runner.

## Acceptance criteria

1. **Seen failing first, before any recipe change**, each recorded in the landing notes with its
   output.
   - `test_x86_64_compiles_with_an_aarch64_compiler` fails on today's tree. So does
     `test_release_workflow_rebuilds_on_two_more_hosts` on today's workflow, with the two lines
     Decision 7 names. The new `test_scan.py` mutations each name their breach.
   - `tests/unit/test_clang_emulated.py` fails: there is no launcher. Then each case is seen
     failing against a launcher missing its rule. The `clang-cpp` case fails on the draft
     contract's launcher, which has no cpp mode. The refused-name case fails on one that
     accepts any name. The environment cases fail on one without the `QEMU_` clearing and the
     `-U` flags.
   - **The gate fails first.** Today's `main` is rebuilt in the research container on
     `linux/amd64`, from empty `downloads/` and `build/`. Its `SHA256SUMS` differs from
     macOS's in exactly two lines, `python.wasm` and `python-snapshot.wasm`, as spec 012
     found.
   - **Dry run 1, before the fix.** A dry run runs on a ref that carries main plus only
     Decision 6's workflow change. Its `same-bytes` job fails on `ubuntu-24.04`, and `cmp`
     names those two lines. This is the first build on a real x86_64 machine, which the memo
     could only infer. It needs a pushed ref, which needs the owner's instruction (§4.14).
     Without that instruction, the container run above stands for it, and the landing notes
     say so.
   - **Step 10's gate stops the build**, with one line, in two cases. The first is when the
     launcher is not installed. The second is when an installed launcher has no `clang-cpp`
     mode: the cpp probe then fails.
2. **Decision 1 reproduced** into the research folder (Decision 10). Both hosts' objects are
   equal to the hashes above, and so are the first difference in the pass print and the
   scheduler sweep.
3. **Three hosts, one set.**
   - macOS, the `linux/arm64` container and the `linux/amd64` container each build from empty
     `downloads/` and `build/`, with this change. All three write a byte-identical `SHA256SUMS`.
   - The `linux/amd64` container runs qemu inside Rosetta, so its build takes hours. It is a
     correctness run, not a time estimate. It runs in the background, and its time is not
     reported as a CI figure.
   - `python.wasm`, the snapshot, the zip and the licences keep today's accepted hashes on
     every host.
   - The x86_64 build's log shows every probe of step 10's gate passing (Decision 5): the link,
     `InstalledDir`, `clang-cpp`, `clang++` and the loader-cache trace.
   - Its step 20 log shows CPython's configure passing its preprocessor checks, with
     `PLATFORM_TRIPLET` set to `wasm32-wasi`, as on the arm64 hosts.
   - Its step 60 log shows the three runtime archives under `$CSDK`'s replaced directories,
     with the neutral hashes.
4. **The judge.** `uv run pytest` is green, accepted with `--accept-judge` and its reason and
   with `--retire
   tests/checks/test_v1_5_rebuild_from_pins.py::test_release_workflow_rebuilds_on_a_second_host`
   (Decision 8). The ratchet shows lost 0 and grew 0, with no `--accept-growth`. The renamed
   check passes under its new name.
5. **Dry run 2**, on the reviewed change, passes every job.
   - Both rebuild runners build. Each runner's tools step prints `nproc` and `binfmt_misc`'s
     entries.
   - `same-bytes` reports `ubuntu-24.04-arm: the same SHA256SUMS`, `ubuntu-24.04: the same
     SHA256SUMS`, and the same wheel for each.
   - The x86_64 rebuild's wall time and core count are recorded (Decision 11). If the time
     passes 240 minutes, the trip-wire applies.
   - It runs on the pushed ref if the owner instructs one, and otherwise after landing, as
     spec 012's did. If it first runs after landing and fails on `ubuntu-24.04`, Decision 11's
     same-day fallback is taken and recorded.
6. The upstream draft, the README, the CHANGELOG and the memo's addendum exist as Decisions 9,
   10 and 13 say.

## The owner's choices

None open here. One is recorded in `../questions-for-the-owner.md` as **63**, decided here as
written so nothing waits. It asks whether "x86_64 Linux rebuilds byte-identical" may mean an
x86_64 host that compiles with the pinned aarch64 compiler under a pinned qemu, while the
upstream issue waits. Decided: yes (Decision 2).

## Landing notes

Built 2026-10-18 by a builder agent (Claude Opus 5.5) in the worktree `wasi_python-040`, branch
`spec/040-x86-64-rebuilds-the-same-bytes`, from main at `64663de` (033 and 031 landed; the
`verify` job taken as main has it, condition B). The machine: Apple arm64, macOS 26.5, Docker
29.7.2 (10 CPUs, 7.7 GiB); `linux/amd64` containers run under Rosetta. Every claim below is
EXECUTED unless labelled. The container image is the research folder's `Dockerfile` (pinned
`debian:trixie-slim`, uv 0.9.22 checked by hash). Scratch logs stay in the worktree's `build/` and
the session's scratch folder; the numbers are written here. Not yet reviewed: the build review
(`../reviews/`) is next, then the lane's acceptance.

### What changed

- `scripts/clang-emulated` (new, mode 755): the launcher, as Decision 5's contract.
- `scripts/line.conf`: `COMPILER_SDK_DIR` for the three keys; the five emulation names for
  `LINUX_X86_64`. `scripts/line.sh` sets `COMPILER_SDK_DIR` (required, like the other five) and the
  emulation names (empty where a key has none). `line.py` is unchanged.
- `scripts/00_download.sh`: the x86_64 branch fetches the arm64 Linux SDK and the five `.deb`s from
  their `snapshot.debian.org` URLs. `downloads/SHA256SUMS`: the five pins.
- `scripts/steps/common.sh`: `CSDK`. `scripts/steps/10_tools.sh`: the runtime replacement is one
  function, `neutral_runtime`, run on `$SDK` and, on x86_64, on `$CSDK`; the x86_64 branch (the
  emulator, the aarch64 root with `lib -> usr/lib` and an empty `etc/ld.so.cache`, the launcher,
  the `wasm-ld` redirect) and the gate's five probes, each printing one `compiler gate:` line.
  `scripts/steps/60_link.sh`: the link-map check reads `$CSDK`.
- `.github/workflows/release.yml`: `rebuild` on `[ubuntu-24.04-arm, ubuntu-24.04]`, each with its
  `timeout` from the matrix's `include` (120, 360); the tools step prints `nproc` and
  `binfmt_misc`'s entries; `same-bytes` downloads both runners' sums and wheels and both loops run
  over both; comments as Decision 6 says.
- The judge: `scan.compiler_table_errors` and `code_text`, `test_rules.py::
  test_x86_64_compiles_with_an_aarch64_compiler`; `scan.REBUILD_RUNNERS` gains `ubuntu-24.04`,
  `REBUILD_TIMEOUTS`, and `rebuild_gate_errors` gains the timeout, `nproc`/`binfmt_misc`, wheel
  download and both-loops rules; the v1.5 check is renamed
  `test_release_workflow_rebuilds_on_two_more_hosts`; `tests/unit/test_scan.py` (the rebuild
  fixture now has both runners; 22 compiler mutations, 31 rebuild mutations);
  `tests/unit/test_clang_emulated.py` (new, 10 cases).
- `context/upstream/4-llvm-wasm-isel-slot-order/` (issue, notes, a nine-line reproducer, evidence)
  and the upstream README's row; the research folder's `decision1-*.sh`, `gate-fails-first.sh` and
  `outputs/`; the memo's addendum "Traced further (spec 040)"; `README.md`; `CHANGELOG.md`.
- **Not changed: step 70.** Decision 5's conditional rewrite is not added: the aarch64 tree's name
  reaches neither `_sysconfigdata` nor numpy's `__config__` (the v1.5 zip check, and the x86_64
  zip's hash, below).

### Criterion 1: seen failing first

- **The rule check**, on `64663de` with only the check written (`uv run pytest
  tests/checks/test_rules.py -k x86_64_compiles`): 1 failed, ten findings:
  `line.conf: no LINUX_AARCH64_COMPILER_SDK_DIR`, the same for `LINUX_X86_64` and `MACOS_ARM64`,
  `10_tools.sh does not name` each of `clang-emulated`, `aarch64-root`, `ld.so.cache`,
  `InstalledDir`, `clang-cpp`, `10_tools.sh does not trace the guest's loader (qemu-aarch64
  -strace)`, `scripts/clang-emulated is missing`.
- **The workflow check**, renamed, on today's workflow: 1 failed, ten findings, among them the two
  Decision 7 names: `rebuild's matrix lacks ubuntu-24.04`; `rebuild's timeout-minutes does not come
  from its matrix`; `rebuild's matrix does not give ubuntu-24.04-arm 120 minutes`; `... ubuntu-24.04
  360 minutes`; `rebuild's tools step does not print nproc`; `... binfmt_misc`; `same-bytes does
  not name ubuntu-24.04's SHA256SUMS`; `... ubuntu-24.04's rebuilt wheel`; `same-bytes' SHA256SUMS
  loop does not run over ubuntu-24.04`; `same-bytes' wheel loop does not run over ubuntu-24.04`.
- **The scan mutations** each name their breach: `test_scan.py -k "compiler or rebuild"`, every
  case asserting its first finding (all pass on the change).
- **The launcher test**, with no launcher: 10 errors (`FileNotFoundError: …/scripts/clang-emulated`).
  Then against launchers missing one rule each (the real launcher with one part cut, put in place
  and restored):
  - the draft contract (`*++` in g++ mode, every other name in none): 2 failed, the `clang-cpp`
    case and the refused-name case;
  - one that runs any name: 1 failed, the refused-name case;
  - one without the `QEMU_` clearing: 1 failed, `test_the_emulators_variables_never_reach_it`;
  - one without the three `-U` flags: 6 failed (every case that reaches the emulator);
  - one without both: 6 failed.
- **The gate fails first.** Today's main (`64663de`) rebuilt in the `linux/amd64` container from
  empty `downloads/` and `build/` (`run-build.sh`): exit 0 in 1,406 s, and its `SHA256SUMS`
  differs from macOS's in exactly two lines, `python.wasm` (`b71c2a18e0343e4c…` against
  `4befe9de64edc783…`) and `python-snapshot.wasm` (`3dbbb5b2034cb60f…` against
  `0cdc7b2bd78db6f5…`) (`../research/2026-10-17-the-x86-64-rebuild/outputs/seen-failing-main-*`).
- **Dry run 1** needs a pushed ref, which needs the owner's instruction (§4.14). None was given, so
  the container run above stands for it.
- **Step 10's gate stops the build** in one line (`gate-fails-first.sh`; outputs in
  `outputs/gate-fails-first/`), each case in its own clone at `09d90e8`:
  - the native clang never replaced by the link: exit 1, `ERROR: compiler gate: …/wasi-sdk-33.0-
    x86_64-linux/bin/clang does not lead to …/wasi-sdk-33.0-arm64-linux/bin/clang-emulated`;
  - the draft contract's launcher (no `clang-cpp` mode): exit 1 after the first two probes pass,
    `ERROR: compiler gate: clang-cpp failed (build/compiler-gate/clang-cpp.txt)`;
  - also, not required: no empty cache in the root: exit 1 after four probes pass, `ERROR: compiler
    gate: the guest's loader read an ld.so.cache`. So probe 5 tells the two cases apart.

### Criterion 2: Decision 1 reproduced

Into `../research/2026-10-17-the-x86-64-rebuild/` (`decision1-host.sh` on macOS,
`decision1-x86_64.sh` in the `linux/amd64` container at `09d90e8`; `outputs/decision1/`):

| | object | `-print-after-all` lines | `-pre-RA-sched` objects (default, source, list-burr, list-hybrid, list-ilp, linearize, fast) |
|---|---|---|---|
| arm64 macOS SDK | `20ef33440bb2e944` | 65,227 | `20ef3344`, `c3b001c3`, `20ef3344`, `522f924a`, `98f1fbf6`, `13f0e786`, `d8c6f8d5` |
| x86_64 Linux SDK, native | `d36897438056e356` | 65,227 | `d3689743`, `d5f10409`, `d3689743`, `d79a51b8`, `80029e2b`, `4dfe54d1`, `1e6427b9` |
| arm64 Linux SDK under qemu, through step 10's `$SDK/bin/clang` | `20ef33440bb2e944` | 65,227 | as macOS, all seven |

- The preprocessed file: 324,353 bytes, `2193b9bd4d40aadc`, the same twice; regenerated, not
  committed. The build's own object is `20ef33440bb2e944`.
- macOS against native x86_64: the first three differences are the `RequireAnalysisPass<…>`
  spellings; the first content difference is in the dump after "WebAssembly Instruction Selection
  (wasm-isel)" (`passes-first-differences.diff`).
- macOS against emulated: only those three header lines differ (`passes-macos-vs-emulated.diff`).
  New fact: the spelling follows the system the clang was built on (both Linux builds spell it
  alike), not the CPU.
- **The reproducer** (Decision 9), reduced by hand in well under the hour: `slot-order.c`, nine
  lines. arm64 macOS and arm64 Linux `9afcef294ca52dad`; x86_64 Linux `7daeec0794b49c01`; the
  arm64 Linux SDK under the pinned qemu on x86_64 `9afcef294ca52dad`. Its first difference is
  again `wasm-isel`'s `__multf3` slots. Between the two Linux builds (arm64 in a `linux/arm64`
  container, x86_64 in the `linux/amd64` one) no header line differs at all: the first of 1,296
  changed lines is `wasm-isel`'s (`slot-order-passes-linux-first-differences.diff`, added for the
  build review's finding 2).
- **Every x86_64 object here ran under Rosetta**, never on an x86_64 CPU (the build review,
  finding 1). The fix does not rest on it: dry run 2 checks the emulated compiler on a real x86_64
  runner. The LLVM issue waits for the owner to run the reproducer on real x86_64 first
  (`issue.md`'s preamble), and Decision 9's exit test now runs on real x86_64.
- **LLVM's AI policy** (https://llvm.org/docs/AIToolPolicy.html, read 2026-10-18): a human reads and
  reviews all generated text, substantially generated content is labelled, and agents may not act in
  LLVM's spaces without approval. It does not require the person to write the text, so `issue.md`
  is the text, with a disclosure line, for the owner to check and post.

### Criterion 3: three hosts, one set

Each from empty `downloads/` and `build/`, at `09d90e8` (outputs in
`../research/2026-10-17-the-x86-64-rebuild/outputs/three-hosts/`):

| host | where | wall time (benchmark fact, §4.9) | `SHA256SUMS` |
|---|---|---|---|
| arm64 macOS | a fresh clone in a scratch folder, `scripts/build.sh --plain` | 9m45s, downloads included | `ce0002861e0ee241…` |
| arm64 Linux | the `linux/arm64` container, `run-build.sh` | 385 s | `ce0002861e0ee241…` |
| x86_64 Linux | the `linux/amd64` container, `run-build.sh` | 11,669 s (3h14m); steps 20 1h27m, 35 34m, 40 38m, 50 23m, 60 7m46s | `ce0002861e0ee241…` |

- **All three `SHA256SUMS` are byte-identical** (`cmp`). The x86_64 build's own lines:
  `python.wasm 31760992 bytes 4befe9de64edc783`, `python-snapshot.wasm 65509949 bytes
  0cdc7b2bd78db6f5`, `python-stdlib.zip 11175028 bytes ee1acace2fc1fb26`: main's accepted hashes.
  Its numpy object `meson-generated_npy_math_complex.c.o` is `20ef33440bb2e944`, the aarch64
  object.
- **Against main's frozen set** (`build/sets/s-0cdc7b2bd78db6f5/SHA256SUMS`): before the change,
  the worktree's arm64 build gave the same file, byte for byte. After it, exactly one line differs,
  `MANIFEST` (`fbb1b1e2…` to `70731f51…`). `MANIFEST` gains the five `pin` lines and one `recipe`
  line (`scripts/clang-emulated`), and six `recipe` hashes change (`00_download.sh`, `line.conf`,
  `line.sh`, `steps/10_tools.sh`, `steps/60_link.sh`, `steps/common.sh`)
  (`manifest-main-vs-040.diff`). The worktree's own rebuild at `09d90e8` wrote the same
  `SHA256SUMS` as the fresh clone.
- The x86_64 log's step 10 prints the five gate lines: the link to the launcher, `InstalledDir`
  `…/wasi-sdk-33.0-arm64-linux/bin`, `clang-cpp` in cpp mode, `clang++.cfg`, and "the guest's
  loader maps no ld.so.cache" (`step10-gate-linux-x86_64.txt`).
- Step 20: CPython's WASI configure, read live from its log during the build, chose
  `…/wasi-sdk-33.0-x86_64-linux/bin/clang-cpp` as its preprocessor and found the platform triplet
  `wasm32-wasi`, as on the arm64 hosts; the build Python's own configure used the runner's `gcc`
  (`x86_64-linux-gnu`). The container copies only `build/logs/*`, so this is recorded in
  `step20-triplet-linux-x86_64.txt`.
- Step 60: its runtime check passes only if each of `libc++.a`, `libc++abi.a` and
  `libclang_rt.builtins.a` the link map names lies under `$CSDK`'s replaced directories and equals
  the neutral tarball's member, and it passed (READ, the step's code; EXECUTED, exit 0). Its
  printed lines go to `build/link/runtime-check.log`, which the container does not keep, so
  `link-paths-x86_64.sh` shows the same fact apart from the build: a C++ program linked through
  `$SDK/bin/clang++` after step 10 takes all three from `…/wasi-sdk-33.0-arm64-linux/…`, each equal
  to the neutral member (`d4527e52…`, `53a077fc…`, `b1e23c03…`; `link-paths-linux-x86_64.txt`).
- The `linux/amd64` time is qemu inside Rosetta, two emulators nested, on 10 CPUs. It is a
  correctness run, not a CI figure. For scale only: today's main, all native under the same
  Rosetta, took 1,406 s, so the emulated compiler cost about 8.3 times the wall time here.

### Criterion 4: the judge

`uv run pytest` in the worktree, on its own `build/artifacts/` (rebuilt at `09d90e8`), without
`--accept`:

```
wasi_python v1: 224/228 pass · 0 gap · 4 blocked · 0 fail   (unit suite 861/868, 7 skipped)
  v1.1  artifact set        24/25  blocked 1
  v1.2  portable, sealed    45/46  blocked 1
  v1.3  data stack          20/21  blocked 1
  v1.4  embedding           95/95
  v1.5  rebuild from pins   18/18
  rules constitution rules  22/23  blocked 1
blocked by: oracle 1 · prior-art clones 1 · three systems 1 · wheel 1
ratchet vs c42410a127: lost 0 · absent 1 · unrun 0 · unrun locally 2 · gained 2 · grew 0 · judge changed: …
ABSENT tests/checks/test_v1_5_rebuild_from_pins.py::test_release_workflow_rebuilds_on_a_second_host
RED: 1 accepted check(s) absent (retire them with --retire)
1085 passed, 11 skipped
```

- The one red line is the renamed check, as Decision 8 expects. The lane accepts with
  `--accept-judge "<reason>"` and `--retire
  tests/checks/test_v1_5_rebuild_from_pins.py::test_release_workflow_rebuilds_on_a_second_host`;
  the two gained checks are the new rule check and the renamed workflow check. Grew 0, lost 0: no
  `--accept-growth`.
- `ruff check` and `ruff format --check` are clean on `src/` and `tests/`.

### Criterion 5: dry run 2

Not run: it needs a pushed ref or the landing, and no push was instructed (§4.14). It runs after
landing, as spec 012's did. The `ubuntu-24.04` runner's wall time and `nproc` go into these notes
then (Decision 11); if it passes 240 minutes, the trip-wire applies, and if the x86_64 rebuild
fails, times out or differs, Decision 11's same-day fallback is taken, after one re-run for a
failure that is a fetch or a lost runner.

### Criterion 6

The upstream draft (`../upstream/4-llvm-wasm-isel-slot-order/`), the README, the CHANGELOG and the
memo's addendum exist as Decisions 9, 10 and 13 say.

### For the reviewer

- `scripts/clang-emulated` and step 10's x86_64 branch, against Decision 5's contract; the gate's
  `awk` reading of the loader trace (it matches the cache's file descriptor in `mmap(…,fd,0)`).
- `scan.compiler_table_errors`' `_maps`: it reads the launcher's `case` arms by text.
- The workflow's matrix `include` and `timeout-minutes: ${{ matrix.timeout }}`; nothing has run it
  on GitHub yet.
- Deviation: the gate's loader-trace probe passes the launcher's three `-U` flags to qemu as well,
  so a host `LD_PRELOAD` cannot change what it sees; Decision 5 runs it "directly". It is still not
  run through the launcher.
- Step 70 is unchanged (Decision 5's rewrite was not needed).

**Landed 2026-10-18** through the lane: rebased onto main (`ae42c89`); the main tree, detached at
`c9f57ef`, ran the full build (5m13s) and gave the worktree's `SHA256SUMS` byte for byte (only
`MANIFEST` moves); the build review (scratchpad, copied by the lane) committed on that HEAD;
accepted with `--accept-judge` and `--retire
tests/checks/test_v1_5_rebuild_from_pins.py::test_release_workflow_rebuilds_on_a_second_host` as
`fe67910`; the rules tier passed; main fast-forwarded. **Dry run 2**, release run 39118009462 on
`fe67910`: every job passed. The x86_64 rebuild ran on GitHub's `ubuntu-24.04` (a real x86_64
runner) under the emulated aarch64 compiler in 64.5 minutes (10:07:29 to 11:12:01 UTC), against
7m16s for the arm64 rebuild; "the same bytes from every host" passed with both Linux runners and
macOS. That is under Decision 11's 240-minute trip-wire, so nothing is asked of the owner.
