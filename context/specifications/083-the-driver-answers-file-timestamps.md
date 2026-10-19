# 083 — the judge's driver answers a file's times and inode number itself

- **Status:** **drafted 2026-10-19** on `spec/083-the-driver-answers-file-timestamps` from main
  `59b90b6`. It changes neither the guest's imports nor its exports, the artifact set nor the
  build recipe, so §5.6 asks no review before build. It is sent for one anyway, at the lane's
  request. A different agent reviews the build.
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** a judge change; **parallel-safe**, not build-class (§5.7). It edits the judge's guest
  driver (`tests/harness/guest.py`), its WAT modules (`tests/harness/wat.py`), its unit tests
  (`tests/unit/test_guest.py`) and one check file (`tests/checks/test_v1_4_embedding.py`: one new
  check, one docstring). After spec 065 lands, it also narrows one of 065's classes (Decision 8).
  Nothing else: no `src/`, `scripts/`, `recipes/`, `downloads/SHA256SUMS`, workflow, README or
  CHANGELOG. The product runner keeps the host's real times and inode numbers. It restates the
  accepted fuel of most rows, and 21 rise past the tolerance: **the lane accepts it with
  `--accept-judge` and `--accept-growth`** (Decision 7).
- **Depends on:** nothing. It meets three specifications in flight:
  - 081 (built, in review) edits the same file, `run()`'s signature and its first lines; the
    merge is textual (Decision 9).
  - 065 (confirmed) carries a class `stepped-clock` that this spec shrinks from three tests to one
    (Decision 8).
  - 081 reserves this number in `context/roadmap.md`; this branch, from main, does not carry that
    line, and adds none.
- **Research it stands on:** spec 081's pre-build review, F1
  (`build/reviews-evidence/081-spec/` in the main tree, its probes `r1_seventeen.py` and
  `r2_timestamps.py`); and this spec's measurement (EXECUTED,
  `../research/2026-10-19-what-the-guest-learns-about-a-file/`, the section below).

## The problem

The ratchet holds every fuel metric to one part in ten thousand of its accepted value. So fuel must
depend only on the artifact and the check, never on when or where the check runs.

The judge's driver (`harness.guest.run`) already answers two host inputs itself: `random_get`, from
a seeded stream, and `clock_time_get`, from a stepped clock that starts at 2026-01-01. Two more
reach the guest unchanged, through wasmtime's `fd_filestat_get`, `path_filestat_get` and
`fd_readdir`:

- **A file's three times** (`atim`, `mtim`, `ctim`): the host's real times. A file the check or the
  guest just wrote has a new time on every run.
- **A file's inode number** (`ino`, and readdir's `d_ino`): wasmtime's SipHash of the host's own
  (`st_dev`, `st_ino`) (READ and EXECUTED in `../research/2026-10-17-typed-grants.md`, 7b). A fresh
  file has a fresh host inode, so its hash is a new 64-bit number on every run.

Each changes the instructions a program runs. Spec 081's review found the times (F1). This
measurement finds the inode numbers too, and on today's rows they are the larger part. Today the
largest spread over five runs is 102 instructions, and the smallest accepted row allows 121. So a
small check that stats files, or one that reads many, could flake.

The times also disagree with the clock. A file the guest writes is stamped with the host's date,
2026-10; the guest's clock says 2026-01-01. So every file the guest makes is about 291 days in its
future (EXECUTED, `probe_times.out`). CPython's own `test_utime_current` pair fails on that alone,
which is why spec 065 carries the class `stepped-clock` (Decision 8).

## The measurement (EXECUTED)

Evidence: `../research/2026-10-19-what-the-guest-learns-about-a-file/`. Against
`build/sets/s-c50ca51fae5eb55b-c9dcb5b8` in the main tree, read only; `-n 3`.

**The rows.** `accepted.json` records fuel for 159 rows (darwin-arm64), from 69 check functions
(`funcs.txt`). 148 run in a worktree; 11 are the upstream groups, whose source trees exist only
after a build.

**Five runs of each, three drivers** (`measure.sh`, `spread.py`, `fuels.tsv`):

| driver | rows with a spread | largest spread |
|---|---|---|
| main's (`spread_before.out`) | 35 | 102 (matplotlib's plot rows and `savefig`) |
| times answered, inode numbers not (`spread_times_only.out`) | 33 | 28,725 (`test_lxml_is_builtin_at_manifest_versions[snapshot]` flips between two values) |
| times and inode numbers answered: the prototype (`spread_prototype.out`) | **2**: the lxml grant check's rows, by 16 to 80 | 80 |

The two rows left are spec 081's: their argument holds a host path under pytest's base temp, whose
length changes between sessions. 081 removes it. Every other row gives one value five times.

**The inode number, alone** (`probe_corr.py`, `probe_corr.out`). Times answered by the driver, 120
runs of `open`, `write`, `os.stat`: the 12 runs whose inode hash was below 2**60 cost 17
instructions less than the 108 above it. CPython stores an int in 30-bit digits; a hash below 2**60
takes two, above it three. One in sixteen hashes is below. `str(st_ino)` spreads up to 241 a run
(`probe_var.out`).

**The times, alone** (`probe_times.out`). On main, a program that takes a file's `st_mtime_ns`
modulo 7 spreads 682 over eight runs. With the prototype every one of twelve programs gives one fuel
value over eight runs.

**The forward costs the guest nothing** (`probe_var.out`). The prototype with its rewrite switched
off gives main's fuel to the instruction (16,255,056 both). With the trampoline's own instructions
let through, 11 more.

## Decisions

1. **The driver shadows five calls and forwards each to wasmtime.** The calls are
   `fd_filestat_get`, `path_filestat_get`, `fd_filestat_set_times`, `path_filestat_set_times` and
   `fd_readdir`.
   - **How.** As the runner's mounts do (spec 032, Decision 1; spec 048), studied and written
     again in the driver, which never imports the runner. A small module (the *trampoline*)
     imports wasmtime's own five calls from a plain linker and exports one function each. It is
     instantiated on the guest's memory, after the guest and before it runs. The shadow calls it,
     and wasmtime does everything it does today: the descriptor table, rights, path resolution,
     every errno and every trap. Only a successful answer is rewritten, in the guest's memory,
     where wasmtime wrote it.
   - **Fuel-neutral.** The shadow reads the store's fuel before the forward and sets it back after
     it, in a `finally`. So the guest pays for its own instructions only, as with any host call.
   - **A second trampoline, on a page of its own,** imports `fd_filestat_get` and
     `path_filestat_get` for the driver's own stats after a set-times call (item 2), so they never
     touch a byte of the guest's memory.
   - **Why forward rather than answer.** Answering a stat means knowing wasmtime's descriptor
     table and its path rules; forwarding keeps them wasmtime's.
   - **Why not a fixed `utime` before each run.** Files the guest makes, and every inode number,
     come after it.
   - **The product is untouched.** `wasi_python.run` keeps the host's real times and inode
     numbers. Only the judge's measurement changes.

2. **A file's times come from the driver's clock.** The driver keeps, for each file (by
   wasmtime's inode number), each of its three host times and the answer it gave for it.
   - A time the guest has not seen for that file is answered with the clock's next value: one
     value for all the times that are new in one answer, and the clock steps once, as for a
     `clock_time_get`. So a file first seen at one moment has `atim = mtim = ctim`.
   - A time the host still holds is answered as before. An unchanged file keeps its times.
   - A time that moved on the host (a write, a rename into the folder, a `utime`) is answered with
     the clock's next value. So a write moves `mtim`, as it does on the host.
   - A time the guest set itself (`*_filestat_set_times` with an exact time) is answered exactly as
     set, while the host keeps it. A time set "now" (`ATIM_NOW`, `MTIM_NOW`) is the clock's next
     value. To know which file a set-times call reached, the shadow stats it again on its own page
     after the host accepts it.
   - **Why the clock, not a constant.** With one constant time a folder never changes, so CPython's
     import system never rescans it: a module written into a folder already on `sys.path` is not
     found (EXECUTED, `probe_const_out.out`: `ModuleNotFoundError: No module named 'b'`; with this
     design, `1 2`).
   - **Why the same clock.** A file's time is then never ahead of `time.time()`. CPython's
     `test_utime_current` pair passes (EXECUTED, `probe_cpython_tests.out`), where on main it fails
     by 25,180,957 seconds.
   - **Why a full clock step, not a nanosecond.** A variant that stamped files at the clock's last
     value plus one nanosecond, so stats never step the clock, failed
     `test_a_program_sees_real_entropy_and_file_metadata[snapshot]` (`variants.out`): a float holds
     1767225600.000000001 as 1767225600.0, the build's pinned time. A step is one microsecond,
     which a float holds.

3. **A file's inode number is a count.** The first file the guest sees is 1, the next 2, and so on,
   by wasmtime's inode number. The same file keeps its number: by any stat, and in readdir's
   `d_ino`, where wasmtime gives the same hash as its stat (EXECUTED, `probe_dino.out`). Two
   names of one file (a hard link) keep one number, since wasmtime's hash is one.
   - **readdir.** Each whole entry's `d_ino` is rewritten. An entry cut at the buffer's end keeps
     no partial number: its `d_ino` bytes present are zeroed (wasi-libc never reads a cut entry; it
     lists again from it). Each entry's three padding bytes are zeroed too: wasmtime 49.0.0 leaves
     host bytes there (spec 048's guard), and a forwarded listing should hold no host byte.
   - **A listing whose count lies over it** (a guest's `used` pointer inside its own buffer) is
     left as wasmtime wrote it. No check does this; the runner's guard handles it for embedders.
   - **Why a count from 1.** A number never repeats within a run, never collides, and costs one
     30-bit digit. A count from 2**63, the size of wasmtime's hashes, moves the restated rows as
     much in other directions (Decision 7), so size buys nothing.

4. **What the driver does not answer.**
   - `dev` (wasmtime's answer is always 1, READ in the typed-grants memo), `nlink`, `size` and the
     file type: the host's, the same on every run on one machine.
   - `clock_res_get`: spec 065 answers it.
   - `Turns`, the session driver: it records no fuel.
   - A run on the caller's own engine (`own=`): it is shadowed too, so every guest of the driver
     sees the same files; it counts no fuel, so nothing is set back.

5. **The real-metadata check keeps its power.** `test_a_program_sees_real_entropy_and_file_metadata`
   asks that a program never see the constants the build pins while it snapshots: `ino` 0 and a
   time of exactly 1767225600 s (`recipes/reactor_main.c`, `pin_filestat`). The driver's answers
   are never those: a count starts at 1, and the clock's first value is 1767225600.000001 s. So a
   pinned value that leaked from the snapshot's heap would still show. Its docstring says so.

6. **A file system with coarse times.** A host that stamps writes coarsely (ext4 uses a clock of a
   few milliseconds) can leave a time unchanged across a write, and then the guest sees no change,
   as it would on that host. Fuel is compared only on darwin-arm64 (`accepted.json` holds its
   metrics only), where APFS gave each of 5,000 writes its own time (EXECUTED,
   `granularity.out`: the smallest step 2,917 ns).

7. **The restated values.** Against `accepted.json` (`moved_prototype.out`; one value five times
   on every row but 081's two): 50 rows rise, 60 fall, 38 are unchanged. The sum over all rows
   moves +0.007%; the mean row +0.0002%, the median 0. The largest moves are +0.078%
   (`test_sqlite_job_matches_native`) and −0.055% (`test_nothing_is_a_shared_library`).
   - **Why they move.** The guest now sees other values: small counted inode numbers where it saw
     64-bit hashes, and clock times where it saw the host's. CPython's work depends on such values
     (INFERRED: an int's digits, a hash's slot, and the allocations that follow).
   - **Why this is not a cost.** The moves are symmetric. Numbering from 2**63 instead
     (`moved_inobase.out`) moves the same rows by as much, in other directions (46 rise, 57 fall,
     24 past the tolerance). And the forward itself costs the guest nothing (the measurement).
   - **The 21 that rise past the tolerance** need `--accept-growth`:

     | row | accepted | restated | change |
     |---|---|---|---|
     | `test_sqlite_job_matches_native` | 5,148,863,956 | 5,152,859,931 | +0.078% |
     | `test_encodings_are_wasi_libcs_as_documented` | 30,712,123,224 | 30,735,822,227 | +0.077% |
     | `test_the_guest_package_round_trips_through_the_door[snapshot]` | 4,613,261,669 | 4,616,348,719 | +0.067% |
     | `test_fuel_is_exact_across_async_tool_calls` | 93,262,499 | 93,314,713 | +0.056% |
     | `test_resources_read_as_zipfile_reads_them[snapshot]` | 6,017,825,150 | 6,019,576,353 | +0.029% |
     | `test_the_fast_reader_builds_zipimports_dict[prepended]` | 289,662,951 | 289,737,127 | +0.026% |
     | `test_fuel_is_exact_across_tool_calls` | 93,265,513 | 93,286,923 | +0.023% |
     | `test_the_fast_reader_builds_zipimports_dict[padded]` | 1,538,549,373 | 1,538,865,236 | +0.021% |
     | `test_recursion_through_python_raises[xslt-extension-snapshot]` | 226,779,285 | 226,818,676 | +0.017% |
     | `test_savefig_rejects_a_negative_dpi` | 7,938,882,658 | 7,940,233,564 | +0.017% |
     | `test_longdouble_parses` | 1,059,320,877 | 1,059,500,520 | +0.017% |
     | `test_metadata_answers_from_the_zips_directory[snapshot]` | 158,329,403 | 158,355,596 | +0.017% |
     | `test_regex_is_builtin_at_manifest_version[plain]` | 440,316,072 | 440,388,911 | +0.017% |
     | `test_kiwisolver_raises_unsatisfiable_constraint[snapshot]` | 20,996,483 | 20,999,805 | +0.016% |
     | `test_lxml_is_builtin_at_manifest_versions[snapshot]` | 208,776,178 | 208,807,522 | +0.015% |
     | `test_libxml2_has_no_zlib[plain]` | 475,324,597 | 475,395,592 | +0.015% |
     | `test_stylesheets_and_entities_reach_only_grants[snapshot]` | 216,000,932 | 216,026,882 to 216,026,962 | +0.012% (081's row) |
     | `test_plot_line_job_matches_native[snapshot]` | 8,783,536,060 | 8,784,517,438 | +0.011% |
     | `test_read_html_uses_lxml_by_default[plain]` | 5,006,283,082 | 5,006,826,239 | +0.011% |
     | `test_recursion_through_python_raises[lxml-target-snapshot]` | 229,963,362 | 229,987,947 | +0.011% |
     | `test_ctypes_stand_in_names_what_packages_import[plain]` | 5,363,488,416 | 5,364,034,792 | +0.010% |

   - The 11 upstream rows and the new check's rows are not in this table: the lane restates the
     first (their trees exist only in the main tree; criterion 6 measures them in the build if it
     can), and the second are new. The build re-measures every row; values that differ from these
     are named in the landing notes.

8. **Spec 065's class `stepped-clock` shrinks to one test.** 065 admits three CPython tests there,
   "file times are the host's, time.time() starts at 2026-01-01". With this driver, the two
   `test_utime_current` tests pass, and `test_logging`'s `test_rollover` still fails: it waits for a
   rotation a second away, and the clock steps a microsecond a call (EXECUTED,
   `probe_cpython_tests.out`). So, whichever of 065 and 083 lands second makes the change:
   - the two `test_os` ids leave `tests/upstream/expected/cpython-fs/stepped-clock.txt`;
   - the class's `match` in `tests/upstream/python.toml` keeps only `No rotated files found`;
   - its reason, there and in `tests/known_gaps.toml`, says the clock's step, not the file times;
     the gap's `match` names one finding and its new digest.
   - This narrows an allowance because the judge stopped causing two failures. It is a judge
     change with this reason, seen in the judge-hash line, never a widening.
   - **Every other CPython, numpy and pandas test** runs as before or the build stops. If 065 has
     landed, the build runs CPython's whole suite with this driver; any outcome that changes, other
     than these two, is a finding the build reports before it goes on.

9. **The merge with spec 081.** 081 adds `measured` and `host_roots` to `run()` and a guard on
   its first lines; this spec adds the shadows after the linker is made, and the trampolines after
   the guest is instantiated. Whichever lands second rebases and merges by hand; neither changes
   the other's behaviour. 081 left the driver's docstring line "repeats to a few parts in ten
   million" to this spec, which makes it "repeats exactly, on one machine and one checkout
   path".

## Intent

Every fuel metric the judge records depends on no file time and no inode number of the host: a
file's times are values of the driver's clock, and its inode number a count, so the same check
costs the same on every run; and a file the guest writes is never dated after the guest's clock.

## Design

- **`tests/harness/guest.py`.**
  - Constants: `FILE_CALLS` (the five calls and their wasm parameters), the filestat and dirent
    layouts as `struct.Struct`, the set-times flags.
  - `forwarders_wat(names, own_page)`: the trampoline's text; a cache of its compiled module for
    the driver's engine (a run on its own engine compiles its own, since a module of one engine
    cannot be used with another).
  - `FileFacts(now)`: one run's answers. `ino(real)`, `stamp(real_ino, real_times)`,
    `filestat(raw) -> bytes`, `set_times(raw, chosen)`, `listing(bytearray)`. Pure: no wasmtime.
  - `_FileCalls(counted, facts)`: `bind(store, engine, plain_linker, guest_instance)`; `call`, the
    fuel-neutral forward; the five shadows, each forwarding and then rewriting a successful answer.
  - `run()`: makes a plain linker with `define_wasi()`, a `FileFacts` on the shared clock
    (`REALTIME_START_NS + next(ticks) * CLOCK_STEP_NS`), defines the five shadows beside
    `random_get` and `clock_time_get`, and binds the trampolines right after instantiation, before
    the fuel cap.
  - The module docstring: the driver answers a file's times and inode number too (this spec), and
    fuel repeats exactly.
  - The prototype is `prototype.diff` in the evidence folder (194 lines added); the build adds the
    own-engine cache rule and the docstrings.
- **`tests/harness/wat.py`.** `FILE_FACTS`, a snapshot-shaped module that imports the five calls,
  `path_open` and the door. Its `run` stats a file in a grant twice with a door call between (the
  host changes the file there), lists the grant, sets the file's times by path and by descriptor
  (exact, then "now"), and sends each answer through the door; then it spins once for every set bit
  of the answers' inode and time words, so its fuel follows their values. And `STAT_COST(name)`, a
  module that calls one two-argument call a hundred times.
- **`tests/unit/test_guest.py`.**
  - `test_a_files_times_and_inode_are_the_drivers`: `FILE_FACTS`, twice, over a grant whose file is
    made again between the runs with other host times (a new host inode, `os.utime` to another
    year). Both runs send the same bytes through the door and spend the same fuel. In each: the
    first stat's inode is 1 and its three times are the clock's first value; after the host's
    `utime` and write, `atim` and `mtim` are the next value and the inode is still 1 (`ctim` is
    either, as hosts differ); the listing's entry for the file carries inode 1, every inode in it is
    below 2**30 and every padding byte is zero; the exact set-times come back as set, by path and by
    descriptor; the "now" set-times come back as one later clock value.
  - `test_a_shadowed_file_call_costs_the_guest_only_its_own_instructions`: `STAT_COST` with
    `fd_filestat_get` and with `fd_fdstat_get` (not shadowed), same shape: the same fuel.
  - `test_a_cut_listing_entry_keeps_no_host_byte`: `FileFacts.listing` on a listing cut inside an
    entry's header: whole entries renumbered, the cut entry's `d_ino` bytes and padding zero.
- **`tests/checks/test_v1_4_embedding.py`.**
  - `test_file_facts_cost_the_same_on_every_run[plain|snapshot]`: a program makes a folder with
    eight files, sets one file's times, lists the folder with `os.scandir`, and prints, for each
    file, `str(st_ino)`, `repr(st_mtime)`, `st_mtime_ns`, whether `DirEntry.inode()` equals
    `st_ino`, and whether `time.time()` is at least the file's `st_mtime`. It runs twice, the
    first unrecorded, with a granted host folder whose files are made again between the runs with
    other times. Same output, same fuel; eight distinct inode numbers; the set time back as set;
    no file after the clock.
  - The docstring of `test_a_program_sees_real_entropy_and_file_metadata` gains Decision 5's
    sentence.

## Scope

In: the five shadows, the two trampolines, `FileFacts`, the unit rows, the check, the docstrings,
the restated values, and Decision 8's class change once 065 has landed. Out: the product runner;
`clock_res_get` (065); `Turns`; `dev`, `nlink` and `size`; spec 081's path rows.

## Acceptance criteria

1. **The checks fail first.** On main's driver: `test_a_files_times_and_inode_are_the_drivers`
   fails (the two runs' bytes differ, and the inode is a hash); `test_file_facts_cost_the_same_on_every_run`
   fails on both binaries (fuel differs; a file is after the clock); `test_a_cut_listing_entry_keeps_no_host_byte`
   fails (`FileFacts` does not exist). `test_a_shadowed_file_call_costs_the_guest_only_its_own_instructions`
   passes on main and with the build: it guards the forward's neutrality.
2. **Zero spread.** With the build, five runs of the 69 fuel functions and the new check: every
   row gives one value five times, except 081's two lxml grant rows while 081 is not landed.
3. **The behaviours.** `probe_times.py` with the build, eight runs each: every program gives one
   fuel value and the outputs of the prototype's run (`probe_times.out`): an unchanged file keeps
   its time, a write moves it, both `utime` forms round-trip, `utime` "now" is within 0.05 s of
   `time.time()`, a module written after a scan imports. `probe_cpython_tests.py`: the two
   `test_utime_current` tests pass and `test_rollover` fails, as Decision 8 says.
4. **The real-metadata check still bites.** Two mutants of the build's driver each fail
   `test_a_program_sees_real_entropy_and_file_metadata` on both binaries: one that answers every
   inode as 0, one that answers every time as 1767225600 s.
5. **Neutral, and nothing else moved.** The prototype's rewrite switched off, on the build:
   main's fuel to the instruction for `probe_var.py`'s first program.
6. **The upstream rows.** The build copies the numpy and pandas tarballs, trees and test kit from
   the main tree into the worktree (read from main's `downloads/` and `build/`, never written) and
   runs the 11 upstream rows five times: one value each, the same outcomes and class members as
   `accepted.json` records. If a copy cannot stand in for the build's own (a check refuses it), the
   landing notes say so and the lane measures them.
7. **The judge.** `ruff check` and `ruff format --check` green; the fast tier and one full run
   (`-n 3`) against `build/sets/s-c50ca51fae5eb55b-c9dcb5b8`: no failure, no lost pass; the
   ratchet's moves are the restated rows (Decision 7), the new check's rows as gained, and
   `judge changed`. The landing notes give `--accept-growth` its list.

## Landing notes

Not built.
