# Pre-build review of 086 — the toolchain moves to wasi-sdk 34, 2026-10-19

- **Reviewer:** a fresh agent. I wrote none of 086 and none of the research it stands on.
- **Under review:** `context/specifications/086-the-toolchain-moves-to-wasi-sdk-34.md` on
  `spec/086-wasi-sdk-34`, commits `ff3cd37` and `9ed4610` over main `3866f56`. The drafter's
  evidence is in the worktree's git-ignored `build/086-evidence/`.
- **Read:**
  - the spec in full;
  - `AGENTS.md`; constitution §4 and §5 (§4.1, §4.9, §5.6, §5.7);
  - `decisions.md`, the entries for 105 and 104;
  - `research/2026-10-19-the-try-table-order-in-llvm.md`;
  - 081's pre-build review, for the house style.
- **Read in the code:** `scripts/line.conf`, `scripts/00_download.sh` (the pins and the count
  line), `downloads/SHA256SUMS`, `scripts/steps/10_tools.sh:14-15`, `scripts/steps/60_link.sh:106-141`,
  `recipes/iconv_refusals.c`, `scripts/assemble_artifacts.py:71,82`, `tests/harness/needs.py`
  (the fixed vocabulary), `tests/harness/paths.py` (`JUDGE_PATHS`), `tests/harness/scoreboard.py`
  (tolerances), `tests/release_shards.toml`, `.github/workflows/release.yml` (the `same-bytes` job),
  and `tests/upstream/python.toml:86-147`.
- **Read in upstream sources:**
  - CPython 3.15.0, from spec 043's 33 tree, read only: `Python/fileutils.c` (`_Py_dup`);
    `Modules/posixmodule.c` (`os.dup2`, `os.pipe2`, `os.login_tty`); `Modules/timemodule.c`;
    `Modules/selectmodule.c`; `Modules/fcntlmodule.c`; `Objects/fileobject.c`;
    `Include/internal/pycore_semaphore.h`; `configure.ac:5882`; `Platforms/WASI/_build.py`;
    `config.site-wasm32-wasi`; and `Lib/`.
  - wasi-libc at `2e6fb9d8`, fetched from GitHub into a fresh folder: `cloudlibc/.../fcntl.c`,
    `sources/dup.c`, `sources/pipe.c`, `sources/ppoll.c`, `cloudlibc/.../poll.c`, and musl's
    `pthread_getcpuclockid.c`.
- **How I ran things:** everything sat in my scratch folder. No git tree was touched, and nothing
  was pushed. I used neither the main tree nor its `build/`. The wasi-sdk 34 macOS tarball went
  into its own new folder. I hashed it before unpacking it. Its `clang`, `llvm-nm` and sysroot
  were used only as build tools. I did not run the judge: this branch changes only `context/`,
  and the worktree holds no artifact set.

Labels: **EXECUTED** (I ran it), **READ**, **INFERRED** (reasoned, not run).

## Short version

The move is the right one, and the drafter's trial makes most of it solid.

- The pins are right (EXECUTED, below).
- The cause is fixed in clang 23. I reproduced the drafter's numbers: wasi-sdk 33's clang gives
  two objects in 64 runs, and wasi-sdk 34's clang gives one (EXECUTED).
- The `fcntl` refusal is a recipe, not a patch. It is inside §4.1. ENOTSUP is the right answer,
  and the refusal hides no real behaviour.
- Accepting the three new functions, rather than pinning configure back, is the right call.

Five things must be written in before building:

- **F1.** The rule for numpy-core's growth contradicts itself.
- **F2.** "Nothing a program sees moves but three attributes" is not true. `select.PIPE_BUF`
  is new, and nothing in the spec compares the whole surface.
- **F3.** The same-bytes proof covers only today's compiled code. It has no clear trigger for
  re-running when 043's, 087's or 073's code is first compiled with clang 23.
- **F4.** The spec never says where 086 lands. Its re-measure rule also misses parallel-safe
  landings that move fuel.
- **F5.** The x86-64 recursion floors and the Linux trap entries are left to a dry run *after*
  landing. The containers can run them before.

Five low findings follow (F6 to F10). Fix each, or answer it in writing.

## 1. The pins (claims 1 and 3)

- **The five tarballs match the release (EXECUTED).** GitHub's release API for tag `wasi-sdk-34`
  (published 2026-08-25T00:13:18Z) gives the same digest and byte size for all five as Decision
  1's table. `wasi-sdk-34` is the newest release. The two before it are release candidates.
- **One download, hashed by me (EXECUTED).** `wasi-sdk-34.0-arm64-macos.tar.gz`, fetched into a
  new empty folder, gives `9c593981…49e9`, 180,322,002 bytes. Its `VERSION` says `34.0`,
  wasi-libc `2e6fb9d8ee0c`, llvm `895aa2c896ad`, llvm-version `23.1.0`.
- **The fix is in the SDK's LLVM (EXECUTED).** GitHub's compare of `fd76c9bdf103...895aa2c8`
  says `ahead`, 2,545 ahead and 0 behind. So `fd76c9bd` is an ancestor.
- **Three licence notices, hashed by me (EXECUTED).** musl `COPYRIGHT` gives `b870108e…`,
  cloudlibc's `LICENSE` gives `c8b789cf…`, and libcxx's `LICENSE.TXT` gives `539dd7ae…`. Each
  equals Decision 1's table. musl's file differs from 33's only by one contributor's name:
  "Valentin Ochs" becomes "Lynn Ochs", in two places, plus one added line.
- **Layout and verification are fully specified (READ).**
  - `SHA256SUMS` has 67 lines. Fifteen move: five tarballs and ten notices. The fallback's
    `get` line reuses the arm64-linux pin.
  - `00_download.sh` verifies with `shasum --ignore-missing -c`.
  - It refuses any fetched name with no pin (lines 183-197).
  - It counts this host's pins. So criterion 2's "N pins, N fetched, N verified" is right per
    host from an empty `downloads/`. The Linux tarballs are verified in the containers and in
    the release's rebuild jobs.
  - `assemble_artifacts.py:71,82` derives the notice names from `WASI_LIBC_COMMIT` and
    `LLVM_COMMIT`, so the two `line.conf` values carry the rename.
  - `line.conf` holds seven `wasi-sdk-33` strings: the six folder names, and one inside the
    fallback's comment (line 34). Criterion 2's "no `33.0` outside history comments" catches the
    comment, since it is an instruction, not history.
- **The five `SHA256SUMS` (EXECUTED).** `run2/`, both `linux-arm64/` files and `linux-amd64/`
  all hash to `0083fcef…`. `run1/SHA256SUMS` differs only in its `MANIFEST` line: it is the
  plain-copy build, whose `MANIFEST` lacks the recipe lines.
  - Only one macOS clone build's `SHA256SUMS` is kept. The second shows up only in
    `build2.log`/`build3.log`, which print the same `python.wasm` (`2e627c87…`) and zip.
  - That is enough for a draft. Criterion 3 repeats it anyway.

## 2. The reproducer and check (a) (claim 4)

- **Reproduced (EXECUTED).** I compiled the memo's `try-table-order.ll` (`63a709ec…`) 64 times
  with check (a)'s flags.
  - wasi-sdk 33's clang (from 043's worktree) gave **two** objects: 15 × `4e0dd4cb…` and
    49 × `601494f7…`.
  - wasi-sdk 34's clang gave **one** object: 64 × `4e0dd4cb…`.
  - Both agree with the trial and the memo.
- **The flags match the build (READ).** Every C++ cross file, and steps 37 and 55, pass
  `-fwasm-exceptions -mllvm -wasm-use-legacy-eh=false`. So the reproducer runs in the
  exception mode the set uses.
- **It counts, never times.** It counts distinct hashes. Its false-pass odds on 33 are below
  10⁻⁶ even at the memo's 14/50 split. F7 covers where its input lives and which need it names.

## 3. The `fcntl` refusal (claim 5)

- **Within §4.1 (READ).** §4.1 names "a linker flag" as a recipe. The refusal is a new file under
  `recipes/` plus one `--wrap`, with no upstream source changed. That is exactly
  `iconv_refusals.c`'s pattern.
- **The diagnosis is right (READ).**
  - `_Py_dup` takes its `F_DUPFD_CLOEXEC` branch before `HAVE_DUP`
    (`fileutils.c:2689-2700`).
  - wasi-libc's `fcntl` wraps `case F_DUPFD:`/`case F_DUPFD_CLOEXEC:` in `#ifndef __wasip1__`,
    so on preview1 they fall to `default: errno = EINVAL`.
  - The header still defines both macros (`__header_fcntl.h:50-51`, EXECUTED on the sysroot).
  - `dup`, `dup2` and `__dup3` (aliased as `dup3`) each return ENOTSUP on preview1
    (`sources/dup.c`).
  - The same `fcntl` already answers `F_GETLK`, `F_SETLK` and `F_SETLKW` with ENOTSUP.
- **ENOTSUP is the right answer.** It matches libc's own `dup` and its lock commands. It is also
  what 0.1.0a7's guest says today, through `_Py_dup`'s `#else`.
- **It hides nothing.** The two cases are compiled out on preview1, so there is no real duplicate
  behind them.
- **The rest of the family (READ):**
  - `_Py_dup`'s callers:
    - `os.dup`.
    - `socket.socket.dup`. Its answer stays ENOTSUP.
    - `os.listdir(fd)` and `os.scandir(fd)`. These call it only under `HAVE_FDOPENDIR`, which
      `config.site` forces off.
    - `mmap`. This is a Python stand-in here.
  - `os.dup2` calls `dup2`, or `dup3` when `inheritable=False`. Both give ENOTSUP, and `dup3`'s
    ENOTSUP is not ENOSYS, so `posix_error()` raises.
  - The `fcntl` module is `n/a` on WASI (`py_cv_module_fcntl=n/a` in 043's `config.log`), so the
    new `F_*` constants reach no Python code.
  - `os.login_tty` stays absent: `HAVE_SETSID` is undefined.
  - Other C callers of `fcntl` (SQLite's lock commands, and `F_GETFD`/`F_SETFD`/`F_GETFL`/
    `F_SETFL`) pass through.
  - No C source in the set calls `fcntl(…F_DUPFD…)` apart from CPython's `fileutils.c` and
    `Python/dup2.c`. `dup2.c` is not compiled while `HAVE_DUP2` holds (grep over 043's trees).
- **One wrinkle in the wrapper:** see F8.

## 4. The three new functions: accept, or pin configure back?

**Recommendation: accept, as the spec decides.** The spec's reasons hold, and I checked each:

- **`os.dup2` cannot be held out by configure (READ).** `posixmodule.c:11833` defines it under
  `HAVE_DUP3 || F_DUPFD`, and `F_DUPFD` is a header macro.
- **Forcing `HAVE_DUP2` off clashes (READ, then EXECUTED).** `configure.ac:5882` is
  `AC_REPLACE_FUNCS([dup2])`, so that would compile `Python/dup2.c`. That file defines `dup2`,
  and `libc.a`'s `dup.c.obj` defines `dup`, `dup2` and `__dup3` together (EXECUTED,
  `llvm-nm -A`). Any reference to `dup` or `dup3` pulls that member in, and the two `dup2`
  definitions collide.
- **The driver passes extra configure arguments to both configures (READ).** `_build.py:197`
  (the build Python) and `:377` (the host) both receive them. So host-only cache variables do
  need the split the spec describes.
- **No code path outside the tests branches on the new names (READ, grep).**
  - **Stdlib:** no non-test module tests for `os.dup2`, `os.pipe2` or
    `time.pthread_getcpuclockid`. The `os.dup` callers (`subprocess`, `multiprocessing`,
    `_pyrepl`) sit behind `os.pipe` or fork, which are absent, or they already failed with
    ENOTSUP. `selectors` already chose `PollSelector` on 33.
  - **The set's packages:** numpy, pandas, matplotlib, lxml, Pillow, regex, kiwisolver,
    contourpy, SQLite, xz, zlib, libxml2 and libxslt have no use outside their tests, apart from
    libxml2's patched `xmlIO.c` and its unbuilt Python bindings.
- **CPython's own groups do not hide newly-run tests (READ).**
  - `test_os`'s `TestInvalidFD.test_dup2*` are skipped on WASI (`skipIf(support.is_wasi)`).
  - `FDInheritanceTests.test_dup2` needs a subprocess.
  - `test_time` (the getcpuclockid test) is not in the plan.
  - So "allowances unchanged" is not newly failing tests absorbed by a class.
- **`select.poll` through `ppoll` is the same call (READ).** In 34, `poll()` is itself a wrapper
  of `ppoll` (`cloudlibc/.../poll.c`). CPython's ppoll path only carries the timeout in
  nanoseconds instead of rounding it up to milliseconds.
- **The semaphores change nothing (READ).** `_POSIX_SEMAPHORES` is defined only under
  `__wasi_cooperative_threads__` (`unistd.h:358-363`), so `_Py_USE_SEMAPHORES` stays off.

Pinning only `pipe2` and `pthread_getcpuclockid` (two plain `ac_cv_func_*`) would still need that
split, and `os.dup2` would remain. It is not worth it.

## 5. Determinism and the release gate

- **The release gate needs no exception (READ).**
  - `release.yml` builds on `macos-15` and rebuilds on `ubuntu-24.04-arm` and `ubuntu-24.04`,
    both native.
  - `same-bytes` runs `cmp` on each rebuild's `SHA256SUMS` against the set's, and compares the
    wheel.
  - Main carries no exception, so the dry run (criterion 6) is the same gate with no change.
- **In the release, check (a) runs only on macOS's clang.** It sits in the `build` shard,
  `systems = ["build"]`. The two Linux clangs are covered by criterion 3's manual run and by
  `same-bytes`.
- **Five builds are enough for today's code (INFERRED).**
  - Each compile is its own process, so each build is one independent address-layout sample per
    file. Five builds give five samples per file.
  - That would miss a file that flips only rarely: the memo's `-O2` case flipped 1 in 31.
  - But the known cause is removed, and every earlier release held the same two-build standard
    on 33. `same-bytes` keeps checking every release.
  - So the proof is sufficient **for the code on main at the trial**. F3 is about the code that
    arrives later.

## 6. numpy-core (claim 6)

- **The number is real, but its comparison is loose (EXECUTED, the evidence).**
  `upstream4.log` compares the trial set's numpy-core run (208.73 G) with the value accepted at
  `b91e0ea` (203.36 G). It is not an A/B run of 0.1.0a7's set on the same machine and checkout.
- **The drafter's probes moved under 0.6%.** They cover libm, sorts, formatting, copies, `np.char`
  and `long double`.
- **A sibling growth points to a layout effect (READ).** Spec 073's landing notes have the same
  untraced kind of growth in the same group: numpy-core +2.21% (+4.48 G) from which module the
  suite imported first, with counts unchanged. 073 lands before 086.
- **An inference, not a measurement.** Two unrelated changes, a bootstrap change and a toolchain
  change, each move this one group by over 2%, and no workload probe explains either. The likely
  shared cause is that numpy-core's fuel is sensitive to heap or code layout: id-keyed hashing,
  or garbage-collection timing as addresses shift. The toolchain is not the likely cause.
- See F1 for what the spec should say.

## 7. Coordination

- **039:** pins sit next to 086's (text only). Covered.
- **073:** re-measured by the later one. Covered, but it interacts with numpy-core (F1).
- **085:** no shared file; G7 stays exact. Covered.
- **084:** unaffected. Covered.
- **083:** "its absolute figures are re-measured by the later one", but 083 lands *first*. F4.
- **078:** "whichever lands second re-runs 078's script". Covered. 078's own floors fall under
  Decision 8's rule (a re-measured depth, as a judge change).
- **087:** its Decision 6 table names "the builder's linux/amd64 run, or 086's re-measure" as the
  trigger for its 4,800 edge. So 086's re-measure needs an x86-64 run (F5).
- **043:** "whichever lands second" covers the constructor list and the warnings. It does not
  cover cross-host same-bytes for contourpy and qhull (F3), or the landing order (F4).
- **037:** its removal list matches 037's own Decision 17 amendment (its lines 735-748, READ),
  including `assemble_artifacts.py`'s `SAME_BYTES_RECIPE` and `scan.py`'s rules. Covered.
- **038, 044, 045:** arrive after 037, built on 34. Covered.

## 8. Size and licences

- **Size is recorded.** `python.wasm` grows 67,390 bytes (+0.164%), the snapshot 61,717
  (+0.138%) and the zip shrinks 18. The spec gives the section breakdown and the function
  count, and Decision 9's table repeats it at build.
- **Licences are recorded.** Nine notices keep their bytes, musl's `COPYRIGHT` changes (verified
  above), and `LICENSES/wasi-libc.txt` and `llvm-runtimes.txt` change with it.
- No new component and no new licence enters the set. libc++ 23 keeps the same licence.
- The wheel's size is not stated. That is trivial, and Decision 9's bytes table can carry it.

## Findings

**F1 (medium, must be written in). numpy-core's rule contradicts itself, and the trace lacks a
layout control.**

- **The contradiction.** Decision 9 says a fuel row that rises more than 1% "is traced to a
  measured cause before it is accepted". It then allows "the cause, or 'not found after two
  attempts'" in the growth reason. Both cannot hold for numpy-core (+2.645%, untraced).
- **Why it must be fixed now.** §5.2 allows no open question. Left open, it can stall the build
  at its last step.
- **Decide one rule:**
  - an untraced rise of 1 to 3% stops the build and goes to the owner; or
  - (my recommendation) it may be accepted if all three hold:
    - it is localised to the test files that carry it;
    - a layout control shows the group's fuel moves by a comparable amount with no code change;
    - the landing notes and "For the owner" name it.
- **The trace method:**
  - Run as an A/B on one machine and one checkout: 0.1.0a7's set (or main's set rebuilt on
    086's base) against 086's set. Never compare with `accepted.json`'s figure alone.
  - Add a layout control first. On the *same* set, change only the heap's starting layout:
    an extra environment variable of a few KiB, or the first import, as 073 found. Then see
    whether numpy-core moves by a percent or more.
  - Cross-reference 073's open point. One trace can serve both specs.
- **The 3% stop bound.** Keep it. But state that it applies to 086's own A/B delta, so a rebase
  onto 073 cannot push numpy-core past 3% for 073's reasons.

**F2 (medium). The guest surface moves by more than three attributes, and the spec does not
check the whole surface.**

- **The counterexample (READ, then EXECUTED on the 34 sysroot).** wasi-libc 34's `limits.h`
  defines `PIPE_BUF 4096`, and `selectmodule.c:2689-2694` exports it under `#ifdef PIPE_BUF`. So
  `select.PIPE_BUF` is new.
- **Why it matters.** It is harmless, but it contradicts criterion 4 and Decision 6's "three
  attributes".
- **What else moves.** `sysconfig.get_config_vars()` shows the ten flipped `HAVE_*` (that is
  what the zip's −18 bytes is).
- **Write in a mechanical comparison under criterion 4.** On both binaries of 0.1.0a7's set and
  of 086's set, take `sorted(dir(m))` for every module in `sys.builtin_module_names` and every
  compiled extension module in the zip. Take `sysconfig.get_config_vars()` too. List every
  difference in the landing notes, and add the guest-visible ones to the README's platform
  facts. This is one probe script.
- **Restate the claim.** "Three new functions that fail with ENOTSUP, one new constant
  (`select.PIPE_BUF`), and whatever the comparison lists."

**F3 (medium). The same-bytes proof needs a trigger for code compiled with clang 23 for the
first time.**

- **The problem.** The five-build proof covers the objects on main at `932bc00`. Decision 10
  re-runs criterion 3's container builds only "if the rebase touched a recipe hunk", and it is
  unclear whose hunk.
- **What arrives later.** Whichever order the lane takes:
  - 043 adds contourpy's C++ and qhull;
  - 087 adds a regex C patch;
  - 073 changes `reactor_main.c`.
  Each is first compiled by clang 23 either at 086's rebase or at its own rebase onto 086.
  ducc0 showed that one file is enough.
- **Write in:**
  - 086 rebuilds in the linux/arm64 container and compares `SHA256SUMS` with macOS whenever a
    rebase brings new or changed compiled sources;
  - for a specification that lands after 086, the same duty falls to that specification's
    rebase;
  - Decision 10's 043 and 087 bullets say so;
  - 037's bullet already does this for scipy.

**F4 (medium). Say where 086 lands, and re-measure against the base it lands on.**

- **Where 086 lands.** Decision 10 lists the roadmap's order "083, 039, 073, 085, 084, 043" and
  "086 built now in 037's slot". It never says where 086 lands. The lane's rule that "a built
  package lands before any other built specification" would put 043 ahead of 086. The brief
  that sent me this review says 043 and 037 rebase onto 086. Name the position (for example,
  "after 084 and before 043", or "after 043") and the reason. Then the 043 bullet can say which
  side does the work.
- **The re-measure base.** Decision 10's re-measure duty covers only "every build-class
  specification that lands before 086". But 083 (parallel-safe) restates fuel on most rows,
  and 078 may too. Write it as: Decision 9's table is made against `accepted.json` at the exact
  base 086 lands on, after every landing that moved accepted fuel or bytes. The 083 bullet's
  "re-measured by the later one" then reads correctly: 086 is the later one.

**F5 (medium). Run the x86-64 floors and the Linux trap entries before landing, not after.**

- **The risk.** Criterion 6 leaves the x86-64 recursion floors and spec 065's Linux trap entries
  to the dry run on main *after* landing. A failure there leaves main untaggable (rule 6b) until
  a follow-up lands.
- **Why it is likely.** One trap entry exists on Linux x86-64 only (`c-stack-itertools-tee`),
  and 071 measured x86-64 frames 0 to 29% larger.
- **It can be run now.** The drafter already has the linux/amd64 container, which runs
  Cranelift's x86-64 code under Rosetta. Spec 065 reproduced its x86-64-only trap in such a
  container (commit `5294520`).
- **Write in a pre-landing run, in the linux/amd64 container and in linux/arm64:**
  - `test_v1_2_hostile_guest.py`'s recursion checks;
  - `test_the_c_stack_window_is_128_kib`;
  - the CPython groups that carry trap entries.
- Then 087's 4,800 edge can be re-measured on x86-64 in the same run.
- Windows stays with the dry run. Say what follows if a Windows floor fails there: re-measure
  with 071's script, then a judge change with the measured depth, as Decision 8 already says
  for Linux.

**F6 (low). Check (b) never turns red when upstream fixes `fcntl`.**

- **The false claim.** Decision 5 says check (b) "turns red that day". But if wasi-libc's `fcntl`
  answers ENOTSUP, check (b) passes with or without the refusal. So nothing signals its removal.
- **The fix.** Correct the sentence. The real removal trigger is the facts sheet plus the next
  toolchain move's recipe table. That table, "Every recipe and patch, against the move", is a
  good precedent; name `fcntl_dup_refusal.c` in it.
- **Also add to check (b), cheaply:**
  - `time.pthread_getcpuclockid(threading.get_ident())` raises ENOTSUP, since Decision 6's third
    attribute has no check;
  - `os.dup2(1, 5, inheritable=False)` raises ENOTSUP, which is the `dup3` path.

**F7 (low). Check (a)'s input and need.**

- **The input.** The reproducer lives in `context/research/…/try-table-order.ll`. That is outside
  the judge hash: `JUDGE_PATHS` is `tests`, `pyproject.toml` and the rest. So an edit to it
  would change a check silently.
- **The fix.** Copy it under `tests/` (for example `tests/fixtures/try-table-order.ll`) and name
  its SHA-256 (`63a709ec…`) in the check.
- **The need.** The need vocabulary is fixed (`needs.VOCABULARY`), and it has no "toolchain
  unpacked". Use `"compile records"`, as `test_every_compile_contracts_nothing` does (lines
  195-203). Also make the check **fail** if no `build/tools/wasi-sdk-*/bin/clang` is found, so it
  cannot pass vacuously.

**F8 (low). The wrapper reads an argument that may not exist.**

- **What happens (EXECUTED).** wasm32 clang lowers a call with no variadic arguments,
  `fcntl(fd, 1)`, by passing `i32.const 0` as the vararg buffer. So `va_arg(ap, int)` for
  `F_GETFD`/`F_GETFL` reads linear memory at address 0. It does not trap, but it is undefined
  behaviour.
- **The justification is wrong.** "What wasi-libc's own fcntl reads" is not true: that `fcntl`
  calls `va_arg` only inside the cases that take an argument.
- **The fix.** Read the argument only for the commands that take one, or call
  `__real_fcntl(fd, cmd)` for `F_GETFD`/`F_GETFL`. The wrapper is one `switch`.
- **Also.** Step 60's guard is one `sed` of the reactor's compile command into one object
  (`60_link.sh:114`). Say that it becomes two compiles, or a loop, and that the failure message
  names the file that failed.

**F9 (low). Other components probe libc too.**

- **What is recorded.** Decision 6 and check (c) record CPython's configure only.
- **What 34 adds (EXECUTED).** An `llvm-nm` diff of 33's and 34's `libc.a` gives `dup`, `dup2`,
  `dup3`, `pipe`, `pipe2`, `ppoll`, `flockfile`/`ftrylockfile`/`funlockfile`, `mtx_*`, `thrd_join`,
  `thrd_yield`, `sem_*` and `pthread_*sched*`.
- **Who else probes.** libxml2, libxslt and xz use autoconf. numpy, pandas, FreeType, HarfBuzz
  and matplotlib use meson.
- **The fix.** The builder diffs each generated config header between a 33 tree and the 34 tree:
  `libxml2-build/config.h`, `libxslt-build/config.h`, `xz-build/config.h`, the meson
  `config.h`/`_numpyconfig.h` files, and HarfBuzz's `config.h`. 043's worktree holds the 33
  trees. Record any flip in the landing notes, and treat it as Decision 6 treats CPython's.

**F10 (nit). Check (c) could record every `#define`, not only `HAVE_*`.**

- Today the non-`HAVE_*` defines are identical between the two `pyconfig.h` files (EXECUTED).
  Recording the whole list costs nothing, and it would catch a `SIZEOF_*` or `ALIGNOF_*` move
  in a later toolchain.
- If only `HAVE_*` is kept, say why.

**Notes (no action needed):**

- **N1. The evidence folder holds unrelated scripts.** `q34.py`, `land034.py`, `move052.py` and
  others come from earlier work. The landing notes should name the files that are 086's.
- **N2. CPython 3.15.0's driver names wasi-sdk 33 as supported.** It only warns on 34
  (`_build.py:259-273`, READ). The set runs ahead of what upstream validated. The judge covers
  it. One README line, "built with wasi-sdk 34; CPython 3.15.0 names 33", would be honest.
- **N3. `int_fast16_t` widening from 16 to 32 bits** is ABI-neutral here, since everything is
  compiled against one sysroot. No recipe names the type (READ).
- **N4. The size of check (a).** It runs 64 compiles of a 30-line file per clang: small. It
  counts hashes, never time.

## For the owner

- **The new functions.** I concur with the spec: accept them. Add `select.PIPE_BUF` (F2) to what
  is documented.
- **The refusal.** The second link-time refusal is a recipe within §4.1. Sending the wasi-libc
  facts sheet is worthwhile: the fix is one line, and it would let the refusal go.
- **numpy-core.** Two specifications, 073 and 086, each carry an untraced numpy-core growth of
  2.2 to 2.6%. That suggests this one metric moves with memory layout, more than with the code.
  F1 asks 086 to settle its own case with a control. If the control confirms it, a later
  judge-side look at that group's fuel (outside 086) may be worth a question.

## Verdict

**Ready once F1 to F5 are written in.** F6 to F10 are fixed or answered in writing. None needs a
new trial. They are decisions and procedures to write into the spec, plus small changes to the
three checks and the wrapper.

In one line: the move and its design are right; write down the numpy-core rule, the whole
surface, when to re-prove same bytes, where 086 lands, and run x86-64 before landing.

## Addendum: confirmation of the revision (2026-10-19)

- **Under review:** `663bc15` on `spec/086-wasi-sdk-34`, the diff `9ed4610..663bc15`. One file
  changed: the specification (+242 −84). It has a new section, "Disposition of the pre-build
  review", and renumbered criteria (now 1 to 9).
- **How:** I read the whole diff against each finding. I spot-checked the claim it adds, and wrote
  nothing in any git tree.

**Each finding against the revision (READ):**

- **F1, taken.** Decision 9 now has one rule:
  - the bound applies to a same-machine A/B (main's set rebuilt on 086's exact base, against
    086's set, judged by the same commit), never to `accepted.json` alone;
  - a layout control comes first;
  - a rise over 3% stops the build;
  - a rise of 1 to 3% is traced file by file, then per test;
  - after two failed attempts, rule 7's record goes into the growth reason, and the row is
    accepted.

  That is decided, so §5.2 is met. The control's starting point is real. Spec 073's build review,
  in the lane's scratchpad (`073-review/…-build-2026-10-19.md:261-318`), measured +4.29 G of 073's
  +4.48 G in `test_string_comparisons`. It traced that to numpy's `_global_pytype_to_type_dict`
  lookup, keyed by `bool`'s address, which moved 0x780 with the data segment. numpy 2.5.2's
  `array_coercion.c:91` holds that dict (READ). The spec calls it "073's delta review"; it is
  073's build review (n1).
- **F2, taken.**
  - `select.PIPE_BUF` and the ten `sysconfig` variables join the accepted list (Decisions 6 and
    11, Intent, For the owner).
  - `surface_probe.py` compares `dir()` of every builtin and compiled extension module, and
    `sysconfig.get_config_vars()`, on both binaries of both sets.
  - Any other difference stops the build until it is traced (criterion 4).
- **F3, taken.** Decision 10's trigger re-runs the linux/arm64 container comparison at every
  rebase that brings code first compiled by clang 23. Whichever specification rebases owns it.
  The 043 and 087 bullets and criterion 3's last bullet say so.
- **F4, taken.**
  - **Where 086 lands:** after 083, 039, 073, 085 and 084, and after 043 if 043 is ready first.
    037 rebases onto 086.
  - **The base:** the exact commit 086 lands on, after every landing that moved fuel or bytes,
    parallel-safe ones included. The 083 bullet is corrected.
- **F5, taken.** The new criterion 5 runs, before landing, in the linux/amd64 and linux/arm64
  containers:
  - the recursion checks;
  - the 128 KiB window check;
  - the CPython groups with trap entries;
  - 087's x86-64 edge, if 087 has landed.

  Windows stays with the dry run, under the same re-measure rule.
- **F6, taken.**
  - The false sentence is gone.
  - The recipe table names `fcntl_dup_refusal.c` for the next toolchain move.
  - Check (b) adds `time.pthread_getcpuclockid` and the `dup3` path.
- **F7, taken.**
  - The input is `tests/fixtures/try-table-order.ll`, with its SHA-256 named. It matches the hash
    I computed.
  - The need is `compile records`.
  - The check fails when it finds no clang, and criterion 1 sees that failure.
- **F8, taken.**
  - The wrapper is one `switch`. It calls `va_arg` only for `F_SETFD`/`F_SETFL` (an `int`) and
    `F_GETLK`/`F_SETLK`/`F_SETLKW` (a pointer).
  - The no-argument and unknown commands pass on with no argument.
  - The trial table says the trialled wrapper differed.
  - The guard compile becomes a loop whose failure names its file.
- **F9, taken.** Each library's generated config header is diffed, 33 against 34, and each flip
  is treated as Decision 6 treats CPython's.
- **F10, taken.** The recorded list holds every `#define`, with name and value. Check (c)'s
  seen-failing step expects "the ten `HAVE_*` lines and no other", which matches my comparison.
- **N1 and N2, taken.** The evidence moves into the repository, naming only 086's files
  (criterion 9). The README line on CPython's supported SDK is added (Decision 11).

**Two notes for the builder, not conditions:**

- **n1.** The citation "073's delta review" should read "073's build review", with its path once
  the lane copies it.
- **n2.** The extra-environment-variable control moves only the heap. `PyBool_Type` is static,
  so it moves only when the data segment changes size, and a padded environment will not move
  it. So `id(bool)` on both sets, plus `test_string_comparisons` alone, is the control that
  tests 073's mechanism. The environment control tests a different one. Do not read "the
  environment control moved nothing" as "not layout".

Nothing new is wrong. Nothing in the revision weakens a check, and no criterion lost its
evidence in the renumbering: the old 4 to 8 are now 4 and 6 to 9, around the new 5.

**Ready to build.**
