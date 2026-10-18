# Review of 040 — x86_64 rebuilds the same bytes (the build)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change, the specification,
  its pre-build review or its confirmation. I read `AGENTS.md`, the constitution, specification
  040 with its landing notes, the pre-build review with its confirmation and the author's note,
  and the diff (`git log -p main..HEAD`; the change itself is `git diff main...HEAD`, since main
  has moved 38 commits past the base `64663de`). Each claim is labelled EXECUTED, READ or
  INFERRED.
- **Reviewed:** `spec/040-x86-64-rebuilds-the-same-bytes` in the worktree `../wasi_python-040`:
  `09d90e8` (the change), and `3e9a746`, `f5b521a`, `fc4b2f8` (evidence and notes; READ: `git
  diff --stat 09d90e8 HEAD -- scripts downloads recipes .github src tests` is empty, so the
  built commit's recipe is HEAD's). The files: `scripts/clang-emulated` (new), `scripts/line.conf`,
  `line.sh`, `00_download.sh`, `steps/common.sh`, `steps/10_tools.sh`, `steps/60_link.sh`,
  `downloads/SHA256SUMS`, `.github/workflows/release.yml`, `tests/harness/scan.py`,
  `tests/checks/test_rules.py`, `tests/checks/test_v1_5_rebuild_from_pins.py`,
  `tests/unit/test_scan.py`, `tests/unit/test_clang_emulated.py` (new), the upstream draft
  `context/upstream/4-llvm-wasm-isel-slot-order/`, the research folder and memo addendum,
  `README.md`, `CHANGELOG.md`.
- **Edited nothing in any repository tree.** My work is under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/040-buildreview/`
  (below, `$R`). `git -C ../wasi_python-040 status --short` is empty after every step (EXECUTED).

## What I ran (EXECUTED unless labelled)

- **The judge**, `uv run pytest`, no flags, in the worktree on its own `build/artifacts/`
  (`SHA256SUMS` `ce0002861e0ee241…`), at `fc4b2f8` (`$R/judge.txt`). `uv run ruff check src
  tests` and `uv run ruff format --check src tests`.
- **The launcher's unit test and the scan's new mutations**: `uv run pytest
  tests/unit/test_clang_emulated.py tests/unit/test_scan.py -k "clang_emulated or compiler or
  rebuild"`, with `--progress-latest` in `$R`: 66 passed.
- **Twelve launcher mutants** (`$R/scripts/mutants.sh`, `$R/mutants/run.txt`). Each one applies
  one `sed` program to a copy of `scripts/clang-emulated`, puts it in place, runs the launcher's
  unit test and the rule check (`test_rules.py -k x86_64_compiles`), and copies the original
  back. At the end the file's SHA-256 is the original's (`bedb48c7…`) and `git status` is empty.
- **The new rules against main's files.** `scan.compiler_table_errors` and
  `scan.rebuild_gate_errors` from the branch, run on `64663de`'s `line.conf`, `00_download.sh`,
  `10_tools.sh`, `SHA256SUMS` and `release.yml` (`$R/scripts/failfirst.py`, `$R/failfirst.txt`).
- **actionlint 1.7.7** (`actionlint-py==1.7.7.23` through `uv tool run`, with its cache and
  tool folders under `$R`, shellcheck off) on the branch's and main's `release.yml`. Then on a
  copy with `matrix.timeoutx`, and on a copy with `timeout: "six hours"`, to see that it types
  the matrix (`$R/actionlint-*.txt`).
- **Step 10 re-run in the `linux/amd64` container** (`wp040-amd64`, the builder's image), on a
  fresh clone of the branch at `fc4b2f8` (`$R/src`, mounted read-only). The builder's downloads
  folder was mounted read-only, and `00_download.sh` verified each file again
  (`$R/scripts/gate-rerun.sh`, `$R/out-gate/`). It ran three cases.
  - As committed, plus a real compile through the launcher, a compile with a separate `-cc1`
    process, a compile in a hostile environment, a compile-and-link, and a `clang-cl` call.
  - Two reviewer mutants of the launcher (`no-gxx-mode`, `no-argv0`).
  - Then a second run (`$R/scripts/env-probe.sh`): where stderr comes from under a host
    `LD_PRELOAD`, and what the emulated driver runs for a link (`-###`).
- **The aarch64 runtime packages' links**: every symbolic link in the four `.deb`s, listed in
  the container (`$R/scripts/deb-links.sh`, `$R/out-gate/deb-links.txt`).
- **CI time facts** from GitHub, read only: `gh run view` of the two release dry runs that ran
  the arm64 `rebuild` (39022271049 and 39109451358).
- **Rebase check**: `git merge-tree --write-tree main HEAD`, and `git diff --stat 64663de main`
  over `scripts recipes downloads .github`.
- I did not redo the three-hour x86_64 build. I compared the builder's outputs instead
  (`040-build/out-040-amd64/`, `out-040-arm64/`).

## The judge

```
wasi_python v1: 224/228 pass · 0 gap · 4 blocked · 0 fail   (unit suite 861/868, 7 skipped)
  v1.5  rebuild from pins   18/18
  rules constitution rules  22/23  blocked 1
blocked by: oracle 1 · prior-art clones 1 · three systems 1 · wheel 1
ratchet vs c42410a127: lost 0 · absent 1 · unrun 0 · unrun locally 2 · gained 2 · grew 0 · judge changed: tests/checks/test_rules.py, tests/checks/test_v1_5_rebuild_from_pins.py, tests/harness/scan.py and 2 more
ABSENT tests/checks/test_v1_5_rebuild_from_pins.py::test_release_workflow_rebuilds_on_a_second_host
RED: 1 accepted check(s) absent (retire them with --retire)
1085 passed, 11 skipped in 190.97s
```

EXECUTED. This is the landing notes' scoreboard, line for line. The one red line is the renamed
check, as Decision 8 expects. The two gained checks are `test_x86_64_compiles_with_an_aarch64_compiler`
and `test_release_workflow_rebuilds_on_two_more_hosts`. Grew 0 and lost 0. Ruff is clean on
`src/` and `tests/` (63 files formatted).

## Findings, most severe first

Nothing blocks the landing. All the findings are about text: one about the upstream draft, which
the owner posts later, and three small points.

### 1. Low for the landing, must-do before the LLVM issue is posted: the native x86_64 difference has never been seen on an x86_64 CPU

- The reproducer's x86_64 object (`7daeec07…`) and the numpy object (`d3689743…`) come from the
  x86_64 Linux SDK in a `linux/amd64` container on Apple silicon, that is, under Rosetta (READ:
  `issue.md`'s table says so; `notes.md`, "Not done", says so too). So does spec 012's original
  x86_64 build (READ: the memo's machine).
- No step of this change, and no step of dry run 2, runs the **native** x86_64 clang on a real
  x86_64 CPU. On CI, step 10 replaces that clang before any compile (READ, `10_tools.sh`).
- Rosetta's translation is a second host build in the loop. The difference is plausibly in
  wasi-sdk's x86_64 binary, as the issue says. But "not an artefact of Rosetta" is INFERRED, not
  shown. If it were Rosetta's, the issue would send LLVM's maintainers after a bug that is not
  theirs. LLVM's policy names exactly that kind of report as extractive (READ:
  https://llvm.org/docs/AIToolPolicy.html, fetched 2026-10-18).
- **The fix does not depend on it.** qemu runs the aarch64 clang with softfloat, so its bytes do
  not depend on the x86_64 CPU (INFERRED). Dry run 2's `same-bytes` checks that on a real
  x86_64 runner. If the difference were Rosetta's, the emulation would be unneeded but harmless.
- **Asked.**
  - (a) In `issue.md`'s preamble, add one step before posting: run `compare-two-hosts.sh` with
    the x86_64 SDK on a real x86_64 Linux machine, and put that row in the table.
  - (b) Decision 9's exit test ("one native x86_64 rebuild in the research container") should run
    on real x86_64. The CI runner is one. The research container is Rosetta. One sentence, in the
    specification and in `notes.md`.

### 2. Low: two statements in `issue.md` say more than the evidence shows

- **The template-name lines.** The issue says the "two builds spell a template name
  differently". It compares the macOS aarch64 dump with the Linux x86_64 dump. The builder's own
  evidence shows that spelling follows the OS, not the CPU. The arm64 Linux build, run emulated,
  spells it as x86_64 Linux does (READ:
  `outputs/decision1/passes-macos-vs-emulated.diff` and the landing notes' "New fact").
  - A reader will take those three lines as part of the x86_64-against-aarch64 difference.
  - Better: diff the **arm64 Linux** dump against the x86_64 Linux dump. Both are Linux builds,
    so the first difference would be `wasm-isel`'s, with no header noise. That is INFERRED from
    the emulated run, which printed the same as macOS but for those headers. Or say plainly that
    the header lines differ between the macOS and Linux builds.
- **"The same `__multf3` result slots trade numbers."** The quoted lines show a renumbering, not
  a swap. The aarch64 build has `%stack.5`, `%stack.6` and `%stack.8`. The x86_64 build has
  `%stack.6`, `%stack.7` and `%stack.5` (READ:
  `evidence/slot-order-passes-first-differences.diff`). Say "are numbered in a different
  order", as the body's first paragraph already does.
- The rest is right.
  - The policy summary in the preamble matches the policy as fetched. It requires human review
    and a label for substantial tool output, and it bans agents that act without approval. It
    does not require people to write issues by hand. It strongly recommends hand-written PR
    descriptions; this is an issue, not a PR.
  - The disclosure line says the poster "ran the reproducer". That becomes true only once the
    owner does (a) of finding 1, so (a) and the line go together.

### 3. Low: Decision 11's same-day fallback does not tell an outage from a defect

- **The trigger is too broad.** The fallback fires if the `ubuntu-24.04` rebuild "fails, times
  out, or `same-bytes` finds a difference". This change puts a new origin on the release's
  critical path, `snapshot.debian.org`, which is known to throttle. The guard against it is
  `curl --retry 3` (READ, `00_download.sh`). A fetch failure or a lost runner would take x86_64
  out of the gate for a reason that has nothing to do with the bytes.
- **Asked.** In Decision 11, add one sentence: a failure before step 10, or one with no recipe
  line in its log (a fetch, or the runner), is re-run once first. The fallback is for a failure
  that repeats, or for a difference. Text only.

### 4. Low: say the gate probe's deviation in Decision 5, and what it leaves out

- **What the build does.** Probe 5 passes the launcher's three `-U` flags to qemu, though
  Decision 5 runs it "directly" (landing notes, "For the reviewer"). I accept the deviation. The
  probe then runs the emulator as every compile does. It is still not run through the launcher,
  so it checks the root, not the launcher.
- **What it leaves out.** The probe does not clear `QEMU_` variables, as the launcher does.
- **I found no variable that makes it pass falsely** (INFERRED, from qemu's argument order and
  the `awk`).
  - `QEMU_STRACE` is already on.
  - `QEMU_LD_PREFIX` is overridden by `-L`.
  - `QEMU_SET_ENV` is undone by the later `-U` for the loader's variables.
  - `QEMU_LOG_FILENAME` sends the trace to a file. Then no `ld.so.cache` open is seen, and the
    `awk` requires `seen > 0`, so the gate fails closed.
- **Asked.** One sentence in Decision 5, through the Disposition, recording the `-U` flags and
  why. No code change.

### 5. Informational: no change needed

- **The `awk`, on a real trace.** Debian's `awk` is `mawk` (EXECUTED, the container). The
  committed probe passed. The trace reads `openat(AT_FDCWD,"/etc/ld.so.cache",O_RDONLY|O_CLOEXEC)
  = 12`, then `fstat(12,…)`, `close(12)`, and the next `openat` for
  `/lib/aarch64-linux-gnu/libpthread.so.0` (`$R/out-gate/as-is.loader-trace-excerpt.txt`).
  - `$NF` is the fd. The `index(…, "," fd ",0)")` match cannot confuse fd 2 with fd 12, because
    the comma must come right before the digits.
  - When the open fails, `$NF` is not a number, so nothing is counted as mapped. The probe passes,
    which is right: then no cache was read.
  - The builder's `host-cache` case shows a mapped host cache failing it (READ,
    `outputs/gate-fails-first/host-cache.txt`).
  - The container's own `/etc/ld.so.cache` is 7,855 bytes (EXECUTED), so the host file exists
    there.
- **The closure holds** (EXECUTED, `-###` of a compile-and-link). The emulated driver runs
  `…/wasi-sdk-33.0-arm64-linux/bin/clang-emulated -cc1 …` and
  `…/wasi-sdk-33.0-arm64-linux/bin/wasm-ld …` (the redirect). `InstalledDir` and
  `Configuration file` are the arm64 tree's.
  - With `-fno-integrated-cc1`, the separate `-cc1` comes back through the launcher.
  - A plain compile, the separate-`cc1` compile, and a compile with `QEMU_SET_ENV=FOO=1
    QEMU_STRACE=1 QEMU_CPU=cortex-a53 LD_PRELOAD=/nonexistent.so LD_LIBRARY_PATH=/nonexistent`
    all wrote the same object (`d48345c199a6704d`). Compile-and-link exits 0.
  - `clang-cl` stops with `ERROR clang-emulated: no driver mode for the name clang-cl`.
- **A host `LD_PRELOAD`.** If the library cannot be loaded, the 8 stderr lines through
  `clang-cpp` are the host loader's, printed by the launcher's own native helpers. `cat` alone
  prints the same line. The guest prints nothing. If the library can be loaded (`libm.so.6`),
  stderr is 0 bytes (EXECUTED, `$R/out-gate/env-probe.txt`). So the `-U` flags do their part.
  A preload that cannot be loaded would break every native tool of the build anyway.
- **Loader fall-through.** qemu's `-L` sends a path that is missing from the root on to the host.
  A library missing from the root would load from a host with aarch64 multiarch libraries, and
  the gate would not see it (INFERRED). Today the root holds every `NEEDED` library: the builder
  ran Decision 1 without `libtinfo` first, and it failed (READ). GitHub's x86_64 image has no
  aarch64 libraries (INFERRED). No package link has an absolute target or `..`, so nothing in
  the root resolves to the host (EXECUTED, `$R/out-gate/deb-links.txt`: six relative links).
- **The scan reads text, and the unit test backs it.**
  - The `QEMU_` rule is satisfied by `unset` and `QEMU_` appearing anywhere in the code.
  - `_maps` reads the first line of the form `<name>)`.
  - Both are coarse by design. The behaviour is the unit test's to check, and it does. All twelve
    of my launcher mutants are killed by the unit test (table below). Four are killed by the rule
    check too.
- **The `test_scan.py` fixture rewrite is sound.**
  - The rebuild fixture now carries both runners, the timeouts, the tools step, all four
    downloads and both loops.
  - The `cmp ` → `diff ` mutation became `cmp "$sums"` → `diff "$sums"`. The old string would
    now also change the wheel loop's `cmp -s`, so the mutant would not name one breach.
  - The old mutation "the SHA256SUMS loop names only `ubuntu-24.04`" is replaced by the four
    loop mutations.
  - The older "run text names the runner" sub-rule now has no mutation of its own. It is
    subsumed by the loop rule, which is stricter.
  - No assertion was loosened. Each case still asserts its first finding.
- **The rebase is mechanical** (EXECUTED).
  - `git merge-tree --write-tree main HEAD` reports two conflicts, `CHANGELOG.md` and
    `tests/checks/test_rules.py`. Both are appends at the same place (048's guard check and its
    CHANGELOG entry). Keep both sides.
  - Main has not touched `scripts/`, `recipes/`, `downloads/` or `.github/` since `64663de`, so
    `MANIFEST` and the set do not move. Main's `src/` changes reach the wheel. Both sides of the
    wheel comparison are built in the same run.
- **The evidence was kept side by side.** Criterion 3's step 20 and step 60 evidence is a live
  capture and a separate link script, because `run-build.sh` copies only `build/logs/`. Both are
  sound (READ). Next time, copying `build/link/runtime-check.log` and `build/compiler-gate/`
  would make this direct.

## Launcher mutants (EXECUTED, `$R/mutants/run.txt`)

| mutant | unit test | rule check |
|---|---|---|
| any other name runs in gcc mode | 1 failed (refused-name) | passes |
| `clang` without `-no-canonical-prefixes` | 1 failed | passes |
| `clang++` without `--driver-mode=g++` | 1 failed | **failed** |
| `clang-cpp` gets `--driver-mode=gcc` | 1 failed | **failed** |
| no `QEMU_` clearing | 1 failed | **failed** |
| no `-U LD_AUDIT` | 6 failed | **failed** |
| `$@` unquoted | 5 failed | passes |
| `-cc1as` not a re-run | 1 failed | passes |
| `-cc1` gets `-no-canonical-prefixes` | 2 failed | passes |
| no missing-piece check | 2 failed (root, real clang) | passes |
| `-0` names the real clang | 6 failed | passes |
| no `-L` | 6 failed | passes |

- Restored byte for byte: SHA-256 `bedb48c7781c5c77…` before and after. `git status --short` is
  empty.
- **The gate catches some launcher mutants and not others** (EXECUTED, the container).
  - `no-gxx-mode` stops step 10 at probe 4, in one line: `ERROR: compiler gate: clang++ -v does
    not name …/clang++.cfg`.
  - `no-argv0` passes all five probes. None of them makes the driver re-run itself.
  - That is acceptable. The unit test kills `no-argv0` (6 failed), and the closure is shown
    above. It does mean the gate does not check the re-run path, and the unit test does.

## Each Decision against the code

| Decision | Evidence |
|---|---|
| 1, the cause | READ: `outputs/decision1/`. The objects are `20ef3344` (macOS), `d3689743` (x86_64 native) and `20ef3344` (emulated), each with 65,227 pass lines. The seven scheduler objects are equal between macOS and emulated (EXECUTED: `cmp` of the two `sched.txt`). The first content difference is `wasm-isel`'s. |
| 2, the aarch64 clang under qemu, other tools native | READ: `10_tools.sh`. Only `clang` is replaced. `llvm-ar` and the rest are `$SDK`'s. `wasm-ld` is redirected to native. EXECUTED: the `-###` above. |
| 3, five pins | READ: `downloads/SHA256SUMS` has the five hashes of the table. `00_download.sh` has the five `snapshot.debian.org` URLs with `%2B`. `pinned()` re-checks the hash at use. EXECUTED: `00_download.sh` verified them again in my container runs. |
| 4, `COMPILER_SDK_DIR` | READ: `line.conf` and `line.sh` (required, like the five), and the emulation names (empty elsewhere). `common.sh` has `CSDK`. `line.py` is unchanged. |
| 5, step 10 and the launcher | READ and EXECUTED. One `neutral_runtime`, run on both trees. Only `./usr/bin/qemu-aarch64` is taken from `qemu-user`. The four packages go into `aarch64-root`, with `lib -> usr/lib` and an empty `etc/ld.so.cache`. The launcher is copied beside the real clang, and `clang-22` links to it (EXECUTED: `ls -l`). The `wasm-ld` redirect is in place. The five probes each print one line (EXECUTED, `$R/out-gate/as-is.txt`). The launcher matches the contract: names to modes exactly, `QEMU_` cleared, three `-U` flags, `-cc1`/`-cc1as` passed through, arguments intact, missing pieces named. One deviation (finding 4). |
| 5, step 60 and step 70 | READ: step 60 reads `$CSDK`'s directories. Step 70 is unchanged, and the zip names no host (EXECUTED: v1.5 18/18; the x86_64 zip is `ee1acace…`, main's). |
| 6, the workflow | READ and EXECUTED (actionlint clean, typing `matrix` as `{os: string; timeout: number}`). The matrix is `[ubuntu-24.04-arm, ubuntu-24.04]`. `include` adds `timeout` to the two existing combinations and creates none. `timeout-minutes: ${{ matrix.timeout }}` is allowed: actionlint checks context availability and passes it, and flags `matrix.timeoutx` and a string timeout. The tools step prints `nproc` and `binfmt_misc`. Same-bytes downloads four artifacts by exact name (`rebuild-ubuntu-24.04` cannot match `-arm`). Both loops cover both runners. The comments are updated. The `verify` job is untouched (condition B). |
| 7, the judge | EXECUTED: both rules give the landing notes' ten findings each on main's files (`$R/failfirst.txt`). The 22 compiler and 31 rebuild mutations pass on the change. The launcher test has 10 cases and is skipped without `sh`. The Windows `verify` job runs a named list that does not include it (READ), so it cannot fail there. |
| 8, the bytes do not change | EXECUTED: the worktree's `SHA256SUMS` equals both containers' (`cmp`). Against main's frozen set `s-0cdc7b2bd78db6f5`, only the `MANIFEST` line differs. `python.wasm` is `4befe9de…`, the snapshot `0cdc7b2b…`, the zip `ee1acace…`. |
| 9, temporary, upstream draft | READ: `issue.md`, `notes.md`, `evidence/` and the README row. The reproducer has nine lines (`reduction.txt`: 17 cuts). The AI policy was checked (EXECUTED: fetched). Findings 1 and 2. |
| 10, the evidence in the repository | READ: the `decision1-*.sh` scripts and their outputs. The memo has the addendum, finding 7 is marked superseded, and the Status line names it. The preprocessed file is not committed. |
| 11, time | READ: the landing notes record 3h14m as a correctness run, not a CI figure. The trip-wire and fallback are text for after landing (finding 3). |
| 12, the order | READ: 033 landed before; 040 rebased on `64663de`, which carries `d98249b` (EXECUTED: `merge-base --is-ancestor`). |
| 13, documentation | READ: the README's paragraph, the five packages with their licences, the workflow paragraph ("up to six hours"), and the list item removed. The CHANGELOG has one entry. |

## Acceptance criteria against evidence

| # | Criterion | Evidence | Met |
|---|---|---|---|
| 1 | Seen failing first | **EXECUTED by me:** both rules on main's files give the ten findings each that the landing notes list. Both of Decision 7's lines are there. **READ:** the launcher test with no launcher, then each rule missing (landing notes). My twelve mutants agree, each killed. **READ:** the gate stops the build in one line when there is no link and when there is no cpp mode (`outputs/gate-fails-first/`). **EXECUTED by me:** a third case, no `g++` mode, stops it at probe 4. **READ:** main rebuilt on `linux/amd64` differs from macOS in exactly `python.wasm` and the snapshot. Dry run 1 is replaced by the container run, as the criterion allows without a push. | yes |
| 2 | Decision 1 reproduced | READ, with `cmp` EXECUTED on the scheduler files: the hashes, line counts, first difference and sweep are as the Decision says. | yes |
| 3 | Three hosts, one set | EXECUTED by me: the three `SHA256SUMS` hash to `ce0002861e0ee241…`. The worktree's file equals both containers' (`cmp`). The x86_64 run is at `09d90e8` (READ: `host-tools.txt`), whose recipe equals HEAD's. The three artifacts keep main's hashes. EXECUTED by me: the gate's five lines on `linux/amd64`. READ: step 20's triplet (a live capture) and step 60's runtime archives under `$CSDK` (a side script, finding 5). | yes |
| 4 | The judge | EXECUTED: green but for the one absent check, which `--retire` clears. Lost 0, grew 0, gained 2. The renamed check passes. Acceptance is the lane's. | yes, at the lane |
| 5 | Dry run 2 | Not run: no push was instructed (§4.14). It runs after landing, as the criterion allows, with Decision 11's trip-wire and fallback. | after landing |
| 6 | Draft, README, CHANGELOG, addendum | READ: all exist as written. Findings 1 and 2 ask for text changes to the draft before posting. | yes |

## The implementer's flags

- **The launcher and step 10 against Decision 5.** They match, apart from the one deviation in
  finding 4 (EXECUTED and READ, the table above).
- **The `awk`.** It is correct on mawk and on a real trace, and it fails closed (finding 5).
- **The deviation.** Accepted. It is to be recorded in Decision 5 (finding 4).
- **`_maps`.** It is coarse, and the unit test backs it (finding 5).
- **The workflow's `include` and `timeout-minutes`.**
  - Valid by actionlint 1.7.7, which types and context-checks them (EXECUTED).
  - The `include` semantics, which add a key to an existing combination without creating a new
    one, are READ from GitHub's matrix rules as actionlint models them. They are not run on
    GitHub. Dry run 2 is the first real run.
- **The rebuild fixture.** It is sound, and nothing was loosened (finding 5).
- **The LLVM issue against LLVM's AI policy.** It complies, once the owner reviews it, runs the
  reproducer and posts it himself. Two text points remain (finding 2), and one check is due on
  real x86_64 hardware before posting (finding 1).
- **Untrusted downloads.**
  - The `.deb`s are hash-checked at fetch and again at use (`pinned()`).
  - They are read with the native `llvm-ar` and `tar` under `build/`, and only one member is
    taken from `qemu-user`.
  - No link in them points outside the root.
  - Nothing is installed, and nothing is registered with `binfmt_misc` (READ and EXECUTED).
- **Host tools stay native** (EXECUTED, `-###`).
- **Determinism.** The x86_64 object of `npy_cpowl` is the aarch64 one. All three sets are equal.
  A hostile environment does not change an object (EXECUTED).
- **The ABSENT check and the lane's flags.** See the Verdict.
- **CI time.**
  - GitHub's arm64 `rebuild` took 6m09s in run 39022271049 and 7m03s in run 39109451358
    (EXECUTED, `gh run view`; benchmark facts).
  - Under Rosetta, the emulated compiler cost 8.3 times the native x86_64 wall time (READ,
    landing notes). If a similar factor holds on a real 4-core `ubuntu-24.04` runner, the x86_64
    rebuild is about one to two hours (INFERRED). That is well under the 240-minute trip-wire
    and the 360-minute limit.
  - Decision 11 covers the rest. Finding 3 sharpens its trigger.

## Constitution checks

- **§4.1, patches few and temporary.** No source tree is patched. The launcher is a recipe file,
  a compiler wrapper, which §4.1 names first. It is temporary in the same way a patch is
  (Decision 9), with an upstream draft. Pass.
- **§4.2, every input pinned.** The five `.deb`s and the arm64 Linux SDK for the x86_64 branch
  are pinned by URL and SHA-256 and verified before use. Pass.
- **§4.3, one target.** The x86_64 branch is a build-host branch, not a guest code path. The
  artifact is byte-identical across hosts. Pass.
- **§4.6, the artifact set.** No `.cwasm` and nothing large in git. The preprocessed numpy file
  is regenerated, not committed (READ). Pass.
- **§4.7, prior art.** The launcher and step 10 are original. Debian's packages are used as
  binary build tools, not copied. Pass.
- **§4.8, downloads untrusted.** The packages unpack under `build/tools/`. qemu and the libraries
  run only as the compiler's runtime, and nothing touches the system or the kernel. Pass.
- **§4.9, tests count.** No test measures time. Times are in the landing notes as benchmark
  facts. The launcher test counts arguments. Pass.
- **§4.10, claims carry evidence.** The landing notes label their claims, and the numbers I
  checked match. Finding 1 asks the upstream draft to make one claim run on real hardware
  before it goes out. Pass.
- **§4.12, licences.** qemu (GPL-2.0), glibc, libstdc++, libgcc and ncurses are build tools.
  Nothing of them is linked or shipped (EXECUTED: the set is unchanged). The README names them.
  Pass.
- **§4.13, tooling.** uv only, ruff green, pytest green but for the retire. No dependency added.
  Pass.
- **§4.14, git.** Own worktree and local branch, nothing pushed. Dry runs wait for the owner or
  the landing. Pass.
- **§5.6 and §5.7.** It was reviewed before build, and confirmed with conditions A and B, both
  met. It is build-class and goes through the lane alone. Pass.
- **§6.4, smallest thing.** One launcher, five pins, one branch. It changes no artifact byte.
  Pass.

## Disposition (filled in by the author, then confirmed by the reviewer)

The author is the builder of 040 (Claude Opus 5.5). Every answer is text; no code, recipe, pin,
check or byte changed. The answers are commit `c9f57ef` on the branch, after the rebase onto main
(`ae42c89`); before the rebase it was `d682fb6`.

1. **Fixed, both parts.**
   - (a) `issue.md`'s preamble gains "Before posting: run it on a real x86_64 CPU". It says every
     x86_64 object came from Rosetta, that the difference being the x86_64 clang's is INFERRED,
     that the owner runs `evidence/compare-two-hosts.sh slot-order.c` on a real x86_64 Linux
     machine and puts that row in the table, and that the issue is not posted if the hash is not
     `7daeec0794b49c01`. The table's x86_64 row now says "under Rosetta; the real-x86_64 row goes
     here". `notes.md`'s "Not done" says the same.
   - (b) Decision 9's exit test now compiles the reproducer with the x86_64 SDK on a real x86_64
     CPU, and runs the native x86_64 rebuild on the `ubuntu-24.04` runner (a dry run with the
     emulation off), not the Rosetta research container. `notes.md`'s "When it leaves" matches.
   - The landing notes' criterion 2 records that every x86_64 object here ran under Rosetta.
2. **Fixed, and the evidence gained a Linux-only diff** (EXECUTED).
   - I ran the reproducer's `-print-after-all` with the arm64 Linux SDK in a `linux/arm64`
     container and diffed it against the x86_64 Linux dump: 18,374 lines each, 1,296 changed,
     **no header line differs**, and the first difference is the dump after `wasm-isel`
     (`evidence/slot-order-passes-linux-first-differences.diff`, new). As you inferred.
   - `issue.md`'s "Where it starts" now quotes the two Linux builds, with no header noise, and
     says the slots "are numbered in a different order". It adds the `__addtf3` line that shows
     the renumbering. The macOS header spelling is one parenthesis: it follows the system clang
     was built on, not the CPU, and changes no object. The macOS diff file gains a four-line
     comment saying the same.
   - The disclosure line stays as written; the preamble now says it is true only after the
     owner's run of (a).
3. **Fixed.** Decision 11's fallback gains "First, once, a re-run": a failure before step 10, or
   one whose log has no recipe line (a fetch from `snapshot.debian.org` or another origin, or a
   lost or cancelled runner), is re-run once first. The fallback is for a failure that repeats, a
   timeout of the build itself, or any byte difference. The landing notes' criterion 5 says so.
4. **Fixed.** Decision 5's gate gains an "As built" bullet under the loader-cache probe: it
   passes the launcher's three `-U` flags, why, that it checks the root and not the launcher,
   that it does not clear `QEMU_` variables, and your four reasons why no `QEMU_` variable makes
   it pass falsely (labelled INFERRED by the review).
5. **Noted.** Next time a container run copies `build/link/runtime-check.log` and
   `build/compiler-gate/`.

**The rebase** (`git rebase main`, main at `ae42c89`). `CHANGELOG.md` and
`tests/checks/test_rules.py` conflicted as you said; I kept both sides. In the CHANGELOG, main's
two entries (048's security fix, 036's tools) come first, then 040's. Main had removed the
"Known issue: `fd_readdir`" bullet, which was only context on my side, so it stays removed. In
`test_rules.py`, 048's guard check comes first, then 040's rule check. Main changed nothing under
`scripts/`, `recipes/`, `downloads/` or `.github/` since `64663de` (EXECUTED: `git diff --stat`,
empty).

**After the rebase** (EXECUTED, in the worktree):
- `scripts/build.sh 70 80 90` re-ran on the build tree from `09d90e8`: `python.wasm`
  `4befe9de64edc783`, `python-snapshot.wasm` `0cdc7b2bd78db6f5`, `python-stdlib.zip`
  `ee1acace2fc1fb26`, `MANIFEST` `70731f51…`. `build/artifacts/SHA256SUMS` is byte-identical
  (`cmp`) to the three-host set (`ce0002861e0ee241…`); against main's frozen set only the
  `MANIFEST` line differs.
- `uv run ruff check src tests` and `ruff format --check`: clean.
- `uv run pytest` (no `--accept`): `wasi_python v1: 244/248 pass · 0 gap · 4 blocked · 0 fail
  (unit suite 903/910, 7 skipped)`; v1.5 18/18; rules 23/24 (blocked 1); `ratchet vs
  361775dd62: lost 0 · absent 1 · unrun 0 · unrun locally 2 · gained 2 · grew 0`; the one red
  line is `ABSENT …::test_release_workflow_rebuilds_on_a_second_host`, which the lane retires;
  1147 passed, 11 skipped.

## Verdict

**Land, after the four text answers.** Findings 1 to 4 change no code and no byte. They can be
answered in the Disposition and in a context-only follow-up commit on the branch, before the
lane. Finding 1's step (a) and finding 2 bind the draft before the owner posts it, not the
landing.

The build does what the specification asks.
- The launcher keeps each name's mode and clears the emulator's and the loader's environment.
- Step 10's gate stops the build in one line when the compiler is not in place.
- The three hosts write one `SHA256SUMS`, and only `MANIFEST` moves against main.
- Every new check fails first and has teeth.

**The lane's flags,** in the main tree after the rebase (keep both sides of the
`CHANGELOG.md` and `test_rules.py` appends):

```
uv run pytest --accept "<spec 040: x86_64 compiles with the aarch64 clang under the pinned qemu; three hosts, one SHA256SUMS; MANIFEST gains five pins and the launcher>" \
  --accept-judge "<spec 040: the compiler rule check, the workflow check renamed with x86_64, timeouts, nproc/binfmt_misc and both same-bytes loops; the launcher's unit test; scan mutations>" \
  --retire tests/checks/test_v1_5_rebuild_from_pins.py::test_release_workflow_rebuilds_on_a_second_host
```

- No `--accept-growth`: grew 0. No `--partial` on a machine with the artifact set.
- The lane judges against main's frozen set plus this `MANIFEST`. The artifacts' hashes must stay
  `4befe9de…`, `0cdc7b2b…` and `ee1acace…`. Any other moved hash is a defect (Decision 8).
- After landing, dry run 2 runs. Its x86_64 wall time and `nproc` go into the landing notes.
  Decision 11's trip-wire applies, and so does its fallback, re-run once first (finding 3).

## One line

The emulated aarch64 clang makes x86_64 write the same bytes, the gate and the launcher test
both have teeth, and the workflow lints clean. Land it after four text answers, and before
posting the LLVM issue, see the x86_64 difference once on a real x86_64 CPU.

## Confirmation (2026-10-18)

- **Reviewer:** the same fresh agent that wrote the review above (Claude Opus 5.5), not the
  author. I read the Disposition and the rebased branch. I edited nothing in any repository tree
  (`git status --short` empty before and after).
- **Reviewed:** `spec/040-x86-64-rebuilds-the-same-bytes` at `c9f57ef`, on main `ae42c89`.
  - It carries `eb2d2d7`, `31c500d`, `48b80e9` and `8a51082` (the reviewed four, rebased), and
    `c9f57ef` (the answers).
  - `git merge-base --is-ancestor main HEAD` holds, and `git merge-tree --write-tree main HEAD`
    exits 0.

### The rebase (EXECUTED)

- **`git range-diff 64663de..fc4b2f8 main..HEAD`.** Commits 2 to 4 are `=`, unchanged. Commit 1
  differs only where the two append conflicts were resolved.
  - In the CHANGELOG, 040's entry sits after main's 048 and 036 entries. The context bullet main
    had removed stays removed.
  - In `tests/checks/test_rules.py`, 040's rule check sits after 048's guard check, with its
    text unchanged.
- **The recipe and the judge did not move.** `git diff --stat fc4b2f8 HEAD` over `scripts`,
  `downloads`, `.github`, `tests/unit/test_clang_emulated.py`, `tests/unit/test_scan.py` and
  `tests/checks/test_v1_5_rebuild_from_pins.py` is empty. `tests/harness/scan.py` is unchanged
  too. The only harness file that differs is `files.py`, and that is main's change, not 040's.
- **The artifacts did not move.** `build/artifacts/SHA256SUMS` in the worktree is byte-identical
  (`cmp`) to the x86_64 container's (`ce0002861e0ee241…`). So the three artifacts keep main's
  hashes, and only `MANIFEST` differs from main's set.

### Each finding

1. **Confirmed (READ).**
   - (a) `issue.md` gains "Before posting: run it on a real x86_64 CPU".
     - It names Rosetta and labels the attribution INFERRED.
     - It has the owner run `compare-two-hosts.sh` on real x86_64, put that row in the table,
       and not post if the hash differs.
     - It ties the disclosure line to that run.
     - The table's x86_64 row says "under Rosetta". `notes.md`'s "Not done" says the same, and
       notes that dry run 2 runs only the emulated clang.
   - (b) Decision 9's exit test now compiles on a real x86_64 CPU. It runs the native rebuild on
     the `ubuntu-24.04` runner with the emulation off, not in the research container.
     `notes.md`'s "When it leaves" matches.
   - Criterion 2's notes record that every x86_64 object here ran under Rosetta.
   - One point remains for later: a dry-run branch with the emulation off is a pushed ref. It
     will need the owner's instruction when that change comes (§4.14). The text implies it
     rather than saying it, which is fine.
2. **Confirmed (EXECUTED).**
   - From the builder's raw dumps (`040-build/reduce/r16-*.passes`, 18,374 lines each):
     - `diff r16-a64linux.passes r16-x86.passes` has 1,296 changed lines. The first is at line
       6956, in the `wasm-isel` dump, and no `IR Dump After` header line differs.
     - `diff r16-mac.passes r16-a64linux.passes` differs in exactly the three
       `RequireAnalysisPass` headers.
     - So the new `slot-order-passes-linux-first-differences.diff` says what the dumps show.
   - `issue.md`'s "Where it starts" now quotes the two Linux builds. It shows the `__addtf3`
     renumbering and says "numbered in a different order".
   - The macOS spelling is put in one accurate parenthesis, and the macOS diff file carries the
     same note.
3. **Confirmed (READ).** Decision 11 gains "First, once, a re-run". A failure before step 10, or
   one with no recipe line in its log (a fetch, or a lost or cancelled runner), is re-run once.
   The fallback is kept for a failure that repeats, a timeout of the build, or any byte
   difference. Criterion 5's notes match.
4. **Confirmed (READ).** Decision 5's loader probe gains an "As built" bullet. It names the
   three `-U` flags and why. It says the probe checks the root, not the launcher, and does not
   clear `QEMU_` variables. It gives the four reasons none makes the probe pass falsely,
   labelled INFERRED.
5. **Noted.** Nothing was asked.

### The judge (EXECUTED, in the worktree at `c9f57ef`, no `--accept`)

```
wasi_python v1: 244/248 pass · 0 gap · 4 blocked · 0 fail   (unit suite 903/910, 7 skipped)
  v1.5  rebuild from pins   18/18
  rules constitution rules  23/24  blocked 1
ratchet vs 361775dd62: lost 0 · absent 1 · unrun 0 · unrun locally 2 · gained 2 · grew 0 · judge changed: …
ABSENT tests/checks/test_v1_5_rebuild_from_pins.py::test_release_workflow_rebuilds_on_a_second_host
RED: 1 accepted check(s) absent (retire them with --retire)
1147 passed, 11 skipped
```

- This matches the Disposition's account. The one red line is the renamed check, which the lane
  retires.
- `uv run ruff check src tests` and `ruff format --check`: clean (64 files).

### Lands?

**Yes. 040 lands.** All four findings are answered in text, and each answer says what the
evidence shows. The rebase changed no recipe, pin, check or byte.

The lane judges `c9f57ef` in the main tree with:

```
uv run pytest --accept "<reason>" --accept-judge "<reason>" \
  --retire tests/checks/test_v1_5_rebuild_from_pins.py::test_release_workflow_rebuilds_on_a_second_host
```

- No `--accept-growth` and no `--partial`.
- `python.wasm` must stay `4befe9de…`, the snapshot `0cdc7b2b…` and the zip `ee1acace…`. Only
  `MANIFEST` moves, to `70731f51…`.
- This review is copied into `context/reviews/` with the landing, as the Status line cites it.
- Dry run 2 follows the landing, with Decision 11 as amended.
- The LLVM issue waits for the owner's run on real x86_64.

One line: the four answers hold and the rebase moved no recipe, check or byte, so 040 lands with
`--accept-judge` and the one `--retire`.
