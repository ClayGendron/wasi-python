# Review of 040 — x86_64 rebuilds the same bytes (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the specification, the x86_64
  memo or question 63. I read `AGENTS.md` and the constitution (§2, §4.1 to §4.15, §5.2, §5.6,
  §5.7), and the 037 pre-build review for the format. Each claim is labelled EXECUTED, READ or
  INFERRED.
- **Reviewed:** `context/specifications/040-x86-64-rebuilds-the-same-bytes.md` as drafted
  (`b5db853`; unchanged at `fe71eb0`).
- **Read:** the memo `research/2026-10-17-x86-64-rebuilds-differ-in-one-function.md` and its
  folder (`Dockerfile`, `run-build.sh`, `recompile.sh`, `outputs/`); the Linux build
  experiment's folder; specs 012, 003, 037 (as revised at `fe71eb0`), 023, 028, 031, 033, 035,
  039 (headers and x86_64 text); question 63; `scripts/line.conf`, `line.sh`, `line.py`,
  `00_download.sh`, `wasi-cc`, `wasi-cxx`, `python-wasi-cross`, `steps/{common,10_tools,
  20_cpython,30_zlib,35_stdlib_libs,40_numpy,50_pandas,60_link,70_zip}.sh`,
  `assemble_artifacts.py` (MANIFEST); `recipes/wasi-{numpy,pandas}.cross`;
  `downloads/SHA256SUMS`; `.github/workflows/release.yml`; `tests/harness/scan.py` (the host
  table, the fetch rules, the rebuild gate), `tests/checks/test_rules.py`,
  `tests/checks/test_v1_5_rebuild_from_pins.py`, `tests/checks/test_v1_1_artifact_set.py`;
  `context/progress/README.md`. From CPython 3.15.0 (`build/Python-3.15.0`):
  `Platforms/WASI/_build.py` and `configure`. The macOS SDK's `bin/` layout and `clang.cfg`.
- **Ran (EXECUTED, darwin-arm64; Docker 29.7.2, `linux/amd64` containers under Rosetta).**
  Nothing in `src/`, `tests/`, `scripts/`, `recipes/`, `downloads/`, the workflow or the spec was
  edited. I did not run `scripts/build.sh` or the full judge. Scripts and outputs are under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/040-review/`
  (`stage/` holds the container scripts and my stand-in launcher, `out/` the outputs):
  - The two Linux SDK tarballs checked against `downloads/SHA256SUMS` (both OK).
  - **The five `.deb` pins fetched from Decision 3's snapshot URLs**, `+` written `%2B`. Each
    has the spec's size and SHA-256 (`shasum -a 256 -c`: five OK). Each is an `ar` archive of
    `debian-binary`, `control.tar.xz`, `data.tar.xz`, read with the macOS SDK's `llvm-ar`.
    `qemu-aarch64` is `static-pie linked` (`file`). The four runtime packages hold one symlink
    between them that matters (`usr/lib/ld-linux-aarch64.so.1`, relative).
  - The aarch64 clang's `NEEDED` lines (`llvm-objdump -p`): `libc`, `libm`, `libpthread`,
    `libdl`, `librt`, `libstdc++`, `libgcc_s`, and through the SDK's `libedit`, `libtinfo`. The
    four packages cover them, as Decision 3 says.
  - **Decision 1's one-file reproduction.** `npy_math_complex.c` preprocessed with the build's
    own command (`-E -P`, 324,353 bytes) and compiled with the spec's flags: macOS arm64 SDK
    `20ef33440bb2e944`, the same as the build's object; x86_64 Linux SDK, native, in the pinned
    `debian:trixie-slim` on `linux/amd64`: `d36897438056e356`.
  - **The pass print and the scheduler sweep** (`stage/sweep.sh`). Both hosts print 65,236
    lines (the spec's 65,227 plus nine warning lines I left in). The first difference in content
    is after "WebAssembly Instruction Selection (wasm-isel)": the two `__multf3` calls take
    `%stack.28` and `%stack.25` in swapped order. Before it, only the three
    `RequireAnalysisPass<…>` header spellings differ. All seven `-pre-RA-sched` choices give
    different objects on the two hosts (`out/sweep-*/sched.txt`).
  - **Decision 5's layout, built by hand in the `linux/amd64` container** (`stage/setup.sh`,
    `stage/run.sh`): both SDKs unpacked, the emulator and the root as Decision 5 places them
    (`lib -> usr/lib`), my launcher written from Decision 5's contract only
    (`stage/clang-emulated`), the native `clang-22` replaced by a link to it, and `wasm-ld` in
    the aarch64 tree replaced by a script. Results (`out/container-run.txt`):
    `$SDK/bin/clang -v` names the aarch64 tree's `bin` as `InstalledDir` and its `clang.cfg`;
    the file compiles to `20ef33440bb2e944` twice (22 s each, qemu inside Rosetta); compile and
    link of a `hello.c` works through the `wasm-ld` script; `clang++ -c` of a `<string>` user
    works; **`clang-cpp` does not preprocess** (finding 1).
  - With the fix of finding 1 (`stage/clang-emulated-cpp`): `clang-cpp` prints the
    preprocessed text, loads the aarch64 tree's `clang.cfg`, and CPython's
    `Misc/platform_triplet.c` gives `PLATFORM_TRIPLET=wasm32-wasi`, as natively
    (`out/container-run2.txt`).
  - The environment the emulated compiler sees (finding 2): `QEMU_SET_ENV`, `LD_PRELOAD` and
    the guest loader's library search (`LD_DEBUG=libs` passed in with `QEMU_SET_ENV`)
    (`out/container-run2.txt`, `out/container-run4.txt`).
  - `uv run pytest tests/checks/test_rules.py -k specifications_have`: 2 passed (the header and
    open-question rules hold on the draft).

## What holds

- **The cause is reproduced, and it is where the spec says.** EXECUTED above: equal IR on both
  hosts, the first content difference in wasm-isel's output, and no scheduler choice that makes
  the hosts agree. The memo's register-allocation explanation is ruled out, as Decision 1 says.
  So no flag in the recipe is a sound fix, and Decision 2's reasons against a flag, a per-file
  workaround and a carried patch stand.
- **The aarch64 compiler under qemu gives the aarch64 bytes.** EXECUTED: `20ef33440bb2e944`
  twice, through a launcher written from the spec's contract by someone who did not write the
  spec. `-no-canonical-prefixes` changes nothing in the object.
- **The pins are right, and they are the whole closure.** EXECUTED: the five snapshot URLs
  serve the pinned bytes; qemu is static; the four libraries are what the aarch64 clang and its
  `libLLVM` load. The arm64 Linux SDK is already pinned for the aarch64 host.
- **The design keeps host tools native.** READ: CPython's build-Python is configured by
  `Platforms/WASI` with the caller's `PATH`, which holds no SDK directory, so it uses the
  runner's `cc`. Only the WASI configure puts `$SDK/bin` first. numpy and pandas reach clang
  only through `scripts/wasi-cc` and `wasi-cxx`; zlib and step 35 through
  `$SDK/bin/clang --target=…`; ar, ranlib, nm and strip are `$SDK`'s, native. Cython, meson and
  ninja are the host Python's. So replacing the one file `$SDK/bin/clang-22` reaches every
  wasm compile and no host compile. 037's `HOSTCC=cc` for `getarch` stays native too.
- **Paths do not leak into the artifacts.** READ: `_sysconfigdata` records only `$SDK` paths
  (`bin/clang` five times, `clang-cpp`, `clang++` twice, `llvm-ar`, the sysroot's pkgconfig
  dirs), all rewritten by step 70's `$WASI_SDK_DIR` rule. The aarch64 tree's own paths reach
  only debug info, depfiles and the link map. INFERRED from the existing gate: the macOS and
  arm64 Linux SDK trees already have different names and paths, and their sets are equal, so
  the SDK path does not reach `python.wasm` (step 60 strips debug info). Decision 5's
  conditional rewrite will most likely not be needed; keeping it conditional is fine.
- **Untrusted downloads stay contained (§4.8).** READ and EXECUTED: the `.deb`s are verified by
  `pinned` before use, unpacked under `build/tools/`, nothing is installed or registered with
  the kernel, and their code runs only inside the build as the compiler's runtime.
- **Licences (§4.12).** READ: nothing of qemu, glibc, libstdc++, libgcc or ncurses is linked
  into or shipped with an artifact or the wheel. The workflow uploads only `SHA256SUMS`, the
  wheel and `build/logs/`. GPL-2.0 obligations attach to distribution, and the project
  distributes none of it. Naming them in the README is the right amount.
- **The release gate's scan already tells the two runners apart.** READ: `rebuild_gate_errors`
  matches `rebuild-<runner>` followed by a newline and the runner as a whole word, so
  `ubuntu-24.04` is not satisfied by `ubuntu-24.04-arm`. The `runs-on: ubuntu-24.04` of
  `same-bytes` itself is stripped before the search.
- **The new rule check is well shaped.** Requiring that an emulated compiler SDK is another
  host's own `WASI_SDK_DIR` ties the claim to a host that runs that binary natively. The value
  grammar (`[A-Za-z0-9._+-]`) takes the `.deb` names, and `CONF_HOST_LINE` does not mistake
  `…_COMPILER_SDK_DIR` for `…_WASI_SDK_DIR` (READ).

## Acceptance criteria against evidence

1. Sound, with one addition: the seen-failing list should include the launcher test's
   `clang-cpp` case and the step-10 gate's cpp probe (finding 1).
2. Sound. Already reproduced here (EXECUTED); the builder moves the scripts into the folder.
3. Sound, but the `linux/amd64` container build will take hours on the owner's Mac (finding 3).
   Its log should also show the cpp probe passing (finding 1).
4. Needs `--retire` for the renamed check, and the `MANIFEST` growth branch is moot
   (finding 5).
5. Sound. It is the first emulated run on a real x86_64 machine; finding 3 asks what happens
   if it fails after landing.
6. Sound.

## Findings, most severe first

1. **The launcher drops `clang-cpp`'s mode, so CPython's configure fails on x86_64.** High: the
   build stops at step 20 as specified.
   - READ: CPython's `Platforms/WASI/_build.py:291-297` sets `CPP` to `$SDK/bin/clang-cpp`.
     The macOS build's `Makefile` records `CPP=…/wasi-sdk-33.0-arm64-macos/bin/clang-cpp`.
     `configure` runs `$CPP` directly: the preprocessor sanity check (`configure:6091-6141`,
     fatal on failure), the compiler-name probe (`:6404`) and the platform-triplet probe
     (`:7220`), which decides `MULTIARCH` and the `_sysconfigdata` name step 70 needs.
   - READ: in the SDK, `clang-cpp` is a link to `clang`. Natively the driver takes cpp mode
     from its own name. Under Decision 5 the driver's `argv[0]` is always
     `…/clang-emulated`, which the driver reads as plain `clang` (gcc mode). The contract adds
     `--driver-mode=g++` for `++` names and nothing else.
   - EXECUTED (`out/container-run.txt`): through the launcher, `clang-cpp cc_name.c` exits 1
     with `error: unknown type name 'clang'`; `clang-cpp Misc/platform_triplet.c` exits 1. So
     autoconf's sanity check, which needs `#include <limits.h>` plus "Syntax error" to pass the
     preprocessor, fails, and configure stops with "C preprocessor … fails sanity check".
   - Decision 1 tried compile-only, compile-and-link, link alone and `clang++` mode. It did not
     try `clang-cpp`, and Decision 5's "every caller is unchanged" names CPython's driver.
   - **Fix.** The launcher maps the name it was called by to a mode, exactly:
     `clang` → none, `clang++` → `--driver-mode=g++`, `clang-cpp` → `--driver-mode=cpp`. Any
     other name (`clang-cl`, `wasm32-wasip2-clang`, …, all links to the replaced file) stops
     it with one line, so no target prefix or mode is silently lost. EXECUTED with that fix:
     `clang-cpp` prints `clang` and `PLATFORM_TRIPLET=wasm32-wasi`, with the aarch64 tree's
     `clang.cfg` (`out/container-run2.txt`). `test_clang_emulated.py` gains the cpp case and a
     refused name. Step 10's gate runs all three names, not only `clang -v` (finding 6).

2. **The emulated compiler reads host state that the native one does not.** Medium: three new
   inputs, each able to change a configure result or an object on one host only.
   - **qemu's own variables.** READ (qemu-user's documentation): qemu reads `QEMU_*`
     variables (`QEMU_SET_ENV`, `QEMU_UNSET_ENV`, `QEMU_CPU`, `QEMU_STRACE`, `QEMU_LOG`,
     `QEMU_RAND_SEED`, `QEMU_GUEST_BASE`, …). EXECUTED: `QEMU_SET_ENV=CCC_OVERRIDE_OPTIONS=+-O0`
     changed the object from `20ef33440bb2e944` to `9e90c6fdc2a35265`. Step 35's `env -i`
     clears them there; no other step clears the environment.
   - **The host's loader variables reach the guest's loader.** EXECUTED: with
     `LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libc.so.6` set on the host, the emulated `clang-cpp`
     prints `ERROR: ld.so: object … cannot be preloaded … ignored.` on stderr. A native clang
     prints nothing. Autoconf's second preprocessor pass treats any stderr as failure
     (`ac_c_preproc_warn_flag=yes`). `LD_LIBRARY_PATH` likewise steers the guest's search.
   - **The host's `/etc/ld.so.cache`.** EXECUTED (`LD_DEBUG=libs`): the guest's loader reads
     `search cache=/etc/ld.so.cache`; the root has none, so qemu's `-L` falls through to the
     host's file. Today it lists only x86_64 libraries, which the aarch64 loader skips
     (INFERRED from the search then going to `/lib/aarch64-linux-gnu`). A runner with arm64
     multiarch packages would change that.
   - **Fix.** The launcher unsets every `QEMU_`-prefixed variable before it runs qemu (a loop
     over `env`'s names, POSIX `unset`), and passes `-U LD_PRELOAD -U LD_LIBRARY_PATH -U
     LD_AUDIT` so the guest never sees the host's. Step 10 writes an empty
     `$T/aarch64-root/etc/ld.so.cache` so the host's cache is never read (the builder confirms
     with `LD_DEBUG=libs` that the guest then searches only the root; INFERRED that an invalid
     cache is ignored). `test_clang_emulated.py`'s stand-in emulator prints its environment's
     `QEMU_` names, and the test asserts none arrive and the three `-U` flags do.

3. **The time risk is measured late, and the stop rule waits for a failure.** Medium.
   - READ: today's arm64 rebuild took 6 m 19 s (`build/dryrun-39033299933.txt`); the x86_64
     build, all native under Rosetta, took 1,155 s (memo, `outputs/build-x86_64.txt`).
     EXECUTED: one emulated compile took 22 s against about 1 s native, qemu inside Rosetta.
   - INFERRED: on a real x86_64 runner qemu-user alone is slower than native by a factor
     nearer 5 to 10 for a compiler, so today's set should rebuild in well under an hour. But 023
     (C and C++ for FreeType, HarfBuzz, matplotlib) and 037 (OpenBLAS, scipy's C and C++) multiply
     the compile volume, and nothing measures the emulated factor on x86_64 hardware before
     040 lands, unless the owner instructs a pushed ref.
   - Decision 11 acts only after a rebuild exceeds 360 minutes: a six-hour run, then a blocked
     release, then a question to the owner.
   - INFERRED: criterion 3's `linux/amd64` container build under Rosetta and qemu will take
     several hours (most of 1,155 s is compiles, each about 20 times slower). It is a
     correctness run, not a CI estimate.
   - **Fix.** (a) A trip-wire below the limit: when an x86_64 rebuild's wall time passes 240
     minutes, its landing notes say so and the owner is asked before the next build-class
     specification lands (still a benchmark fact, never a check). (b) A decided fallback if
     dry run 2 first runs after landing and fails or times out: one change takes `ubuntu-24.04`
     out of the matrix and `REBUILD_RUNNERS`, as spec 012 left it, and restores the README
     sentence, the same day. Then no release waits on an open problem. (c) Keep 120 minutes for
     `ubuntu-24.04-arm` (a per-runner `timeout-minutes` from the matrix), so a hung arm64 job
     does not hold the gate for six hours. (d) "The runner's own tools" step also prints
     `nproc`, so time facts carry the core count. (e) Say in criterion 3 that the container
     build takes hours, and run it in the background.

4. **The order of work leaves out the specifications in flight.** Medium.
   - READ: 028 is in build (`spec/028-pip-install-wasi-python`, its worktree exists) and is
     build-class: it changes `.github/workflows/release.yml`. §5.7 and AGENTS.md rule 2 allow
     one build-class specification in flight, so 040 cannot start until 028 lands.
   - READ: 037 now depends on 023, 033 and 035 landing first. Decision 12 says 040 lands before
     037 but not whether before 023. 023 adds the most new C and C++ before scipy, and its text
     says nothing about x86_64. 031 and 039 are build-class too and touch step 70 and the pins.
   - READ: 037's revision (`fe71eb0`) already writes 040's asks in, conditional on 040 landing
     first (its `getarch` values, and line 518's "before spec 040 lands"). Decision 12's "what
     037 then does" is therefore already done; it should say so.
   - **Fix.** Decision 12 names the queue: 040 is the next build-class specification after 028
     lands, ahead of 023 and 037, for the reason it gives for scipy (every new compile gated
     from its first build). If 023 lands first, 040's builder gates matplotlib's objects too and
     records the wall time with them, as the clause for 037 already says. 031, 033, 035 and 039
     change no compile; their order with 040 does not matter, and the decision says so.

5. **The acceptance flags are not the ones the judge needs.** Low.
   - READ: the ratchet turns a disappearing check red (`context/progress/README.md`); dropping
     one needs `--retire <node id>`. Decision 7 renames
     `test_release_workflow_rebuilds_on_a_second_host`; Decision 8 and criterion 4 name only
     `--accept-judge`.
   - READ: the judge records `bytes` only for `python.wasm` and the zip
     (`test_v1_1_artifact_set.py:41,112`), not for `MANIFEST`. So Decision 8's "if the judge
     tracks `MANIFEST`'s bytes" branch is decidable now: it does not, and `--accept-growth` is
     not needed. §5.2 asks for no undecided branches.
   - **Fix.** Keep the old name and change its docstring, which avoids a retire; or name
     `--retire tests/checks/test_v1_5_rebuild_from_pins.py::test_release_workflow_rebuilds_on_a_second_host`
     in Decision 8 and criterion 4. Drop the growth branch and say why.

6. **The gate and the rule check can pass while the design is broken.** Low.
   - The step-10 gate checks only `clang -v`'s `InstalledDir`. It would have passed with
     finding 1's bug. The rule check's "`10_tools.sh` names `scripts/clang-emulated`" passes on
     a comment.
   - **Fix.** The gate runs the three names: `clang -v` names `$CSDK/bin`; `clang-cpp` on a
     two-line `#ifdef __clang__` file prints the token; `clang++ -v` reports `clang++.cfg` or
     g++ mode. It also checks that the file `$SDK/bin/clang` resolves to is a link to
     `$CSDK/bin/clang-emulated`. The rule check reads `10_tools.sh` without comments (the
     scan's `_code_lines`).

7. **An unpinned runner can hide a regression.** Low.
   - INFERRED: a runner (or a developer's Docker host) with `binfmt_misc` registered for
     aarch64 runs any aarch64 ELF through its own, unpinned qemu. Then a tool the design did not
     redirect (a future driver sub-tool, or a step that calls `$CSDK/bin/llvm-ar` by mistake)
     works there and fails in the research container, or the reverse. EXECUTED: the research
     container has no entry (`/proc/sys/fs/binfmt_misc` lists nothing).
   - **Fix.** "The runner's own tools" step lists `/proc/sys/fs/binfmt_misc` beside `nproc`.
     The launcher contract states the closure: the emulated driver may run only the launcher
     (for `-cc1`/`-cc1as`) and `wasm-ld`. The launcher sits in the same directory as the real
     clang, which the guest loader's `$ORIGIN` search relies on (EXECUTED: the RPATH it uses is
     `…/arm64-linux/bin/../lib`).

8. **Smaller text points.** Low.
   - Decision 2's "every wasm instruction then comes from one compiler binary's semantics":
     macOS uses the Mach-O aarch64 build and the two Linux hosts the ELF one. The claim is
     "an aarch64 build of the pinned clang", which Decision 4's last bullet says correctly.
   - Decision 1's flag list omits `-Wno-unsupported-floating-point-opt` and `-Wall`; EXECUTED,
     the object is the same either way. Its "65,227 lines" excludes the warnings; say so, or the
     reproduction counts 65,236.
   - Decision 5: the qemu member is stored as `./usr/bin/qemu-aarch64`; GNU tar matches the
     stored name, so the extraction names it with the `./`.
   - Decision 3: the five URLs served the pinned bytes today (EXECUTED). `curl --retry 3`
     is the only defence against snapshot.debian.org being slow or throttled; a failed fetch
     fails the build cleanly, which is acceptable.

## Ordering

- 040 is build-class (§5.7). It waits for 028 to land, then goes next, ahead of 023 and 037
  (finding 4).
- It changes no artifact byte (Decision 8; nothing in this review contradicts it), so it moves
  no number 023, 033, 035 or 037 measures.
- 037's revision already carries 040's asks conditionally, so landing 040 first needs no
  further change to 037's design.

## Constitution checks

- **§4.1, patches few and temporary:** holds. A compiler wrapper is a recipe item. No source
  tree changes; the SDK is a downloaded binary, edited by step 10 as spec 012 already does.
  Decision 9 holds the emulation to a patch's rules: an upstream draft, and a stated exit.
- **§4.2, every input pinned:** holds. Five pins, each URL and SHA-256 EXECUTED here. The
  host's `/etc/ld.so.cache` and environment become unpinned inputs of the emulated compiler
  until finding 2 is fixed.
- **§4.3, one target:** holds. The target and the artifact set are unchanged.
- **§4.6, the artifact set is the product:** holds. Nothing per host is published.
- **§4.8, downloads untrusted:** holds. Verified, unpacked under `build/tools/`, never
  installed, nothing registered with the kernel, run only as build tools.
- **§4.9, tests count:** holds. The launcher test counts arguments; time is a benchmark fact
  in the landing notes (Decision 11).
- **§4.10, claims carry evidence:** holds. Decision 1's facts reproduce (EXECUTED here); the
  pins' sources are labelled; the 22 s is a labelled, unrepresentative benchmark. Finding 8's
  points are wording.
- **§4.12, licences:** holds. GPL-2.0 qemu and the GNU runtime libraries are build tools only;
  nothing of them is linked in or shipped.
- **§4.13, tooling:** holds. No dependency is added.
- **§4.14, git:** holds. Both dry runs that need a pushed ref wait for the owner's
  instruction.
- **§5.2, no open questions:** holds once finding 5's growth branch is decided. Question 63 is
  decided in the spec. The rules check passes (EXECUTED).
- **§5.6, review before build:** this review.
- **§5.7, one build-class specification in flight:** holds once Decision 12 names 028
  (finding 4).
- **AGENTS.md rules 3 and 7:** holds. Each check is seen failing first; the two-attempt stop
  binds every later build-class specification. Finding 3 asks for a trip-wire before the hard
  limit.

## Disposition (filled in by the author, then confirmed by the reviewer)

Each finding is fixed in the specification as revised on 2026-10-17. The author is Claude Opus
5.5, the drafter of 040.

1. **Fixed.**
   - **Decision 5, the launcher's contract.** The name the launcher was called by maps to a
     driver mode, exactly: `clang` to none, `clang++` to `--driver-mode=g++`, `clang-cpp` to
     `--driver-mode=cpp`. Any other name stops it with one line.
   - **Decision 5's gate** runs five probes: the link to the launcher, `clang -v`'s
     `InstalledDir`, a `clang-cpp` probe (`__clang__` expanded, `__cplusplus` not), `clang++ -v`
     naming `clang++.cfg`, and the loader's search.
   - **Decision 7's unit test** gains the `clang-cpp` case and a refused name (`clang-cl`).
   - **Criterion 1** sees both fail on the draft contract's launcher. **Criterion 3** requires
     the cpp probe in the x86_64 log and CPython's `PLATFORM_TRIPLET=wasm32-wasi` in step 20's
     log.
2. **Fixed.**
   - **Decision 5, the launcher.** It unsets every `QEMU_` variable before it runs qemu, and
     passes `-U LD_PRELOAD -U LD_LIBRARY_PATH -U LD_AUDIT`.
   - **Step 10** writes an empty `$T/aarch64-root/etc/ld.so.cache`. The builder confirms with
     `LD_DEBUG=libs` that the guest's loader then searches only the root. That probe is one of
     the gate's five. It is INFERRED, from reading glibc's cache loader, that a too-short file
     counts as no cache; a probe that shows otherwise is a failed attempt under rule 7.
   - **The unit test** asserts that no `QEMU_` name reaches the stand-in emulator and that the
     three `-U` flags do.
   - **The rule check** reads the launcher's code for both.
3. **Fixed** in Decisions 6 and 11, and criteria 3 and 5.
   - **(a) A trip-wire.** At 240 minutes of x86_64 rebuild time, the landing notes say so. The
     owner is then asked, in the questions file, before the next build-class specification
     lands. Question 63 now names it.
   - **(b) A same-day fallback.** It applies if dry run 2 first runs after landing and its
     x86_64 rebuild fails, times out, or differs. One change through the lane does all of
     this:
     - it removes `ubuntu-24.04` from the matrix and `include`, both `same-bytes` loops and its
       two downloads, and `REBUILD_RUNNERS`;
     - it restores spec 012's README sentence with the run's link;
     - it keeps the launcher, the pins and the rule check, so x86_64 still builds, outside the
       gate;
     - it is recorded in 040's landing notes (the run, the job and its first failing line),
       the CHANGELOG and the memo's addendum;
     - it is reviewed and accepted with `--accept-judge`, and it lands before anything else.
   - **(c) Per-runner limits.** The timeout comes from the matrix: 120 minutes for arm64, 360
     for x86_64. The workflow scan requires both.
   - **(d)** The runner's tools step prints `nproc` and `binfmt_misc`. The scan requires both.
   - **(e)** Criterion 3 says the container build takes hours, runs in the background, and is
     no CI figure.
4. **Fixed**, in Decision 12, which names the queue: 028 (in build), then 040, 033, 035, 023,
   037, 039.
   - 040 goes next after 028: it is small, moves no number, and gates every later compile from
     its first build.
   - **033 and 035 are confirmed but go after 040.** 033 compiles nothing. 035 compiles one
     changed file (`reactor_main.c`), which is gated at once. If 040 is not confirmed when 028
     lands, 033 and then 035 take the slots, and 040 the next one. Neither waits on 040.
   - 023 comes before 037. It adds the most C and C++ before scipy, so its ties are found by
     its own builder.
   - 037 follows its own dependencies. 039 is last: it compiles nothing, and the roadmap puts
     scipy first.
   - 031 compiles nothing, so its place does not matter to 040.
   - What 037 does after 040 is already written in its revision (`fe71eb0`). Decision 12 says
     so and lists it.
5. **Fixed.** The old check is retired, not renamed silently. Decision 8 and criterion 4 name
   `--retire tests/checks/test_v1_5_rebuild_from_pins.py::test_release_workflow_rebuilds_on_a_second_host`
   with `--accept-judge`. The growth branch is dropped: the judge tracks bytes only for
   `python.wasm` and the zip, which do not move. So there is no `--accept-growth`, and any
   growth is a defect.
6. **Fixed.**
   - **The gate** has five probes (finding 1). It includes the check that `$SDK/bin/clang`
     resolves to a link to `$CSDK/bin/clang-emulated`.
   - **The rule check** reads `10_tools.sh` and the launcher without comments (`_code_lines`).
     It requires `10_tools.sh` to name `clang-emulated`, `aarch64-root`, `ld.so.cache` and the
     gate's probes, and the launcher to carry the `-U` flags, the `QEMU_` clearing and the
     three names with their modes.
   - `test_scan.py` gains one mutation per rule.
7. **Fixed.**
   - **Decision 5's contract** states the closure: the emulated driver may run only the
     launcher, for `-cc1` and `-cc1as`, and `$CSDK/bin/wasm-ld`. It states why the launcher sits
     beside the real clang: `argv[0]` gives the `InstalledDir`, and the RPATH is
     `$ORIGIN/../lib`.
   - **Decision 6** prints `/proc/sys/fs/binfmt_misc/`'s entries on each runner, so a runner
     that would hide a gap is visible.
8. **Fixed.**
   - **Decision 2** now says "an aarch64 build of the pinned clang": Mach-O on macOS, one ELF
     build on both Linux hosts.
   - **Decision 1** lists `-Wno-unsupported-floating-point-opt -w`. It says the warning flags
     change no object (the review's run), and that the count is 65,227 with `-w` and 65,236
     without.
   - **Decision 5** names the member `./usr/bin/qemu-aarch64`.
   - **Decision 3** records the review's fetch of the five URLs and the `curl --retry 3` point.

The rules check passes on the revision: `uv run pytest -q tests/checks/test_rules.py`, 22
passed (EXECUTED).

## Verdict

- **Not ready to build as written, but the route is right and proven.** The cause, the fix and
  the pins all reproduce here, and the emulated compiler gives the aarch64 bytes through a
  launcher written from the spec's own contract.
- Before the build:
  - fix finding 1 in the launcher contract, its unit test and the step-10 gate (the build
    cannot pass step 20 without it);
  - fix finding 2 in the launcher contract and its test;
  - decide findings 3 and 4 in the text (a trip-wire, a same-day fallback, the queue);
  - answer 5 to 8.
- These are contract and text changes, not a new design. A confirmation of the dispositions is
  enough.

## One line

The aarch64 clang under the pinned qemu gives macOS's bytes on x86_64 (EXECUTED), but the
launcher as specified turns `clang-cpp` into a compiler, so CPython's configure stops; map each
name to its driver mode, clear qemu's and the loader's environment, and decide the time
trip-wire and the queue before building.

## Confirmation (2026-10-17)

The same reviewer checked the revision (`bf7baf1`) and the Disposition against each finding.
Main is now at `d98249b`, where 028 has landed. I re-ran the revised contract in the same
`linux/amd64` container. My stand-in launcher was rewritten from the revised Decision 5 alone
(`stage/clang-emulated-v2`; outputs `out/container-run5.txt` to `run7.txt` in the scratch
folder named above).

- **1, confirmed (EXECUTED).** Through the launcher, `clang-cpp` passes both halves of
  autoconf's sanity check. On `<limits.h>` plus "Syntax error" it exits 0 with no stderr; on
  `<ac_nonexistent.h>` it exits 1. `Misc/platform_triplet.c` gives
  `PLATFORM_TRIPLET=wasm32-wasi`. On the two-line probe, `__clang__` becomes `1` and
  `__cplusplus` stays as written. `clang++ -v` names the aarch64 tree's `clang++.cfg`. A
  `clang-cl` link stops with one line. Gate probes 1 to 4 behave as written.
- **2, confirmed, with one condition on gate probe 5 (EXECUTED).**
  - With `QEMU_SET_ENV=CCC_OVERRIDE_OPTIONS=+-O0` and `QEMU_STRACE=1` on the host, the object
    is still `20ef33440bb2e944`, so the variables are cleared.
  - With `LD_PRELOAD` set on the host, `clang-cpp` writes 0 bytes to stderr.
  - The empty `etc/ld.so.cache` works. Under `qemu -strace`, without it the guest's loader
    opens `/etc/ld.so.cache` and maps 4,095 bytes, which is the host file's size. With the
    empty file in the root, it opens it, finds it empty, maps nothing, and goes straight to
    `/lib/aarch64-linux-gnu`. So the host's cache is no longer read. The spec's INFERRED claim
    now has evidence.
  - **Condition A.** Gate probe 5, as written, cannot tell the two cases apart.
    `LD_DEBUG=libs` prints the paths the guest sees. qemu's `-L` redirection is invisible to
    it. `search cache=/etc/ld.so.cache` prints with or without the root's file (9 lines
    either way, EXECUTED). `LD_DEBUG` set on the host also makes the native `sh`, `readlink`
    and `dirname` print, so the guest's lines must be picked out by its pid. The builder
    instead writes the probe as either of these:
    - `qemu-aarch64 -strace -L $T/aarch64-root … clang-22 --version`, which shows no `mmap`
      after the `ld.so.cache` open;
    - or a test that the root's `etc/ld.so.cache` exists and is empty, plus `LD_DEBUG=libs`
      showing only `/lib/aarch64-linux-gnu` and the SDK's `lib/` as search paths.
    Either is a wording change in Decision 5; no attempt is spent.
- **3, confirmed (READ).** The changes are in place:
  - the 240-minute trip-wire, in Decision 11 and question 63;
  - the same-day fallback, which keeps the launcher and the pins and lands first;
  - per-runner timeouts (120 and 360) taken from the matrix, with a scan rule;
  - `nproc` and `binfmt_misc` printed by the runner's tools step, with a scan rule;
  - criterion 3's hours, stated.
- **4, confirmed (READ).** Decision 12 names the queue: 028, then 040, then 033, 035, 023,
  037 and 039. It says 040 waits for 028, and it gives a fallback if 040 is not confirmed in
  time. 028 has now landed. It changed only the `verify` job in `release.yml` (READ:
  `git diff bf7baf1 d98249b`), so 040's `rebuild` and `same-bytes` edits do not overlap it.
  The rebase is mechanical.
- **5, confirmed (READ).** Decision 8 and criterion 4 now name `--retire` for the old node id.
  The growth branch is dropped.
- **6, confirmed (READ).** The gate has five probes. The rule check reads `10_tools.sh` and the
  launcher without comments, and `test_scan.py` gains one mutation per rule.
- **7, confirmed (READ).** The closure and the reason for the launcher's place are stated.
  EXECUTED again: with `-fno-integrated-cc1`, the driver's `-cc1` run comes back through the
  launcher and still gives `20ef33440bb2e944`. Compile-and-link and `clang++ -c` work.
- **8, confirmed (READ).** The four text points are made.
- `uv run pytest -q tests/checks/test_rules.py`: 22 passed on the revision (EXECUTED).

**Verdict: 040 is confirmed for build**, with these conditions:
- **A.** Rewrite gate probe 5 as above.
- **B.** Rebase onto `d98249b` (028 landed), and take main's `release.yml` `verify` job as it
  is.

It is the next build-class specification, in its own worktree, as Decision 12 says.

### Author's note on the confirmation (2026-10-17)

- **Condition A is written into Decision 5.** Gate probe 5 is now the `qemu-aarch64 -strace`
  trace of `clang-22 --version`, run directly, not through the launcher. It requires the
  `ld.so.cache` open to be followed by no `mmap` of it, and `--version` to exit 0.
  - **Why this probe and not the other.** The trace sees the system calls after qemu's `-L`
    redirection, so it checks the effect: the host's 4,095 bytes are mapped, or nothing is. The
    alternative, an empty file plus `LD_DEBUG` search paths, checks the setup and the guest's
    view of paths, and the confirmation showed that `LD_DEBUG` cannot tell the cases apart.
  - The confirmation's `-strace` result is cited as the evidence that an empty cache is read as
    no cache, which the revision had marked INFERRED.
  - The rule check now also requires the probe's `-strace` in `10_tools.sh`'s code.
- **Condition B is in the Status line.** The builder starts from `d98249b` and takes main's
  `verify` job as it is.
- **Decision 12's queue** now reads 028 (landed), 033 (in build), 040, 035, 023, 037, 039. 033
  took the slot under the fallback Decision 12 already gave, and 040 builds next after 033
  lands.
