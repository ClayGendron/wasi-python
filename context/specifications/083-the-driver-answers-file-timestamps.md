# 083 — the judge's driver answers a file's times and inode number itself

- **Status:** **landed 2026-10-19** in a batch with 089 (constitution §5.7; rebased onto 089 by the lane, its `_release` removing the sealed stdlib copy through `litter.remove` as 089 specified; accepted on `69004e2` as `45b917c`, history line 80, `-n 3`; sameness clean against both reviewers, every CPython row equal to 083's reviewer's; dry run 39346796670 green on all three systems, `cpython-fs` included; reviews: `../reviews/083-the-driver-answers-file-timestamps-spec-2026-10-19.md`, `../reviews/083-the-driver-answers-file-timestamps-build-2026-10-19.md`, `../reviews/089-083-batch-delta-2026-10-19.md`). Before landing: **built 2026-10-19** on `spec/083-the-driver-answers-file-timestamps`, rebased onto main `9d89535` (spec 065 landed; the Landing notes). **Amended 2026-10-19** (the stdlib zip's link count: the section "Amendment of 2026-10-19"; confirmed with A1 and A2). **Drafted 2026-10-19** on `spec/083-the-driver-answers-file-timestamps` from main `59b90b6`; rebased onto main `08de0c8` (specs 063 and 077 landed) and **revised against its pre-build review** the same day ("ready once F1 to F5 are written in": the section "Disposition of the pre-build review"). It changes neither the guest's imports nor its exports, the artifact set nor the build recipe, so §5.6 asks no review before build; it was sent for one at the lane's request. **It is built after spec 065 lands**, rebased onto that main (Decision 8). A different agent reviews the build.
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** a judge change; **parallel-safe**, not build-class (§5.7). It edits the judge's guest driver (`tests/harness/guest.py`), its WAT modules (`tests/harness/wat.py`), its unit tests (`tests/unit/test_guest.py`) and one check file (`tests/checks/test_v1_4_embedding.py`: two new checks, one docstring), and it narrows one of spec 065's classes: one list file (`tests/upstream/expected/cpython-fs/stepped-clock.txt`), one `match` and reason (`tests/upstream/python.toml`) and one gap (`tests/known_gaps.toml`) (Decision 8). Nothing else: no `src/`, `scripts/`, `recipes/`, `downloads/SHA256SUMS`, workflow or README; one CHANGELOG entry under 0.1.0a8, at the lane's request at build time. The product runner keeps the host's real times and inode numbers. It restates the accepted fuel of most rows, and some rise past the tolerance (21 in the draft's measurement): **the lane accepts it with `--accept-judge` and `--accept-growth`** (Decision 7).
- **Depends on:** spec 065 (built, in the lane), which lands first: its CPython groups run through this driver, and its class `stepped-clock` shrinks from three tests to one (Decision 8). It also meets:
  - 081 (built, in review) edits the same file, `run()`'s signature and its first lines; the merge is textual (Decision 9).
  - 081 reserves this number in `context/roadmap.md`; this branch, from main, does not carry that line, and adds none.
- **Research it stands on:** spec 081's pre-build review, F1 (`build/reviews-evidence/081-spec/` in the main tree, its probes `r1_seventeen.py` and `r2_timestamps.py`); and this spec's measurement (EXECUTED, `../research/2026-10-19-what-the-guest-learns-about-a-file/`, the section below).

## The problem

The ratchet holds every fuel metric to one part in ten thousand of its accepted value. So fuel must depend only on the artifact and the check, never on when or where the check runs.

The judge's driver (`harness.guest.run`) already answers two host inputs itself: `random_get`, from a seeded stream, and `clock_time_get`, from a stepped clock that starts at 2026-01-01. Two more reach the guest unchanged, through wasmtime's `fd_filestat_get`, `path_filestat_get` and `fd_readdir`:

- **A file's three times** (`atim`, `mtim`, `ctim`): the host's real times. A file the check or the guest just wrote has a new time on every run.
- **A file's inode number** (`ino`, and readdir's `d_ino`): wasmtime's SipHash of the host's own (`st_dev`, `st_ino`) (READ and EXECUTED in `../research/2026-10-17-typed-grants.md`, 7b). A fresh file has a fresh host inode, so its hash is a new 64-bit number on every run.

Each changes the instructions a program runs. Spec 081's review found the times (F1). This measurement finds the inode numbers too, and on today's rows they are the larger part. Today the largest spread over five runs is 102 instructions, and the smallest accepted row allows 121. So a small check that stats files, or one that reads many, could flake.

The times also disagree with the clock. A file the guest writes is stamped with the host's date, 2026-10; the guest's clock says 2026-01-01. So every file the guest makes is about 291 days in its future (EXECUTED, `probe_times.out`). CPython's own `test_utime_current` pair fails on that alone, which is why spec 065 carries the class `stepped-clock` (Decision 8).

## The measurement (EXECUTED)

Evidence: `../research/2026-10-19-what-the-guest-learns-about-a-file/`. Against `build/sets/s-c50ca51fae5eb55b-c9dcb5b8` in the main tree, read only; `-n 3`.

**The rows.** `accepted.json` records fuel for 159 rows (darwin-arm64), from 69 check functions (`funcs.txt`). 148 run in a worktree; 11 are the upstream groups, whose source trees exist only after a build.

**Five runs of each, three drivers** (`measure.sh`, `spread.py`, `fuels.tsv`):

| driver | rows with a spread | largest spread |
|---|---|---|
| main's (`spread_before.out`) | 35 | 102 (matplotlib's plot rows and `savefig`) |
| times answered, inode numbers not (`spread_times_only.out`) | 33 | 28,725 (`test_lxml_is_builtin_at_manifest_versions[snapshot]` flips between two values) |
| times and inode numbers answered: the prototype (`spread_prototype.out`) | **2**: the lxml grant check's rows, by 16 to 80 | 80 |

The two rows left are spec 081's: their argument holds a host path under pytest's base temp, whose length changes between sessions. 081 removes it. Every other row gives one value five times.

**The inode number, alone** (`probe_corr.py`, `probe_corr.out`). Times answered by the driver, 120 runs of `open`, `write`, `os.stat`: the 12 runs whose inode hash was below 2**60 cost 17 instructions less than the 108 above it. CPython stores an int in 30-bit digits; a hash below 2**60 takes two, above it three. One in sixteen hashes is below. `str(st_ino)` spreads up to 241 a run (`probe_var.out`).

**The times, alone** (`probe_times.out`). On main, a program that takes a file's `st_mtime_ns` modulo 7 spreads 682 over eight runs. With the prototype every one of twelve programs gives one fuel value over eight runs.

**The forward costs the guest nothing** (`probe_var.out`). The prototype with its rewrite switched off gives main's fuel to the instruction (16,255,056 both). With the trampoline's own instructions let through, 11 more.

**After the pre-build review** (`revised/`). The prototype with the review's F1, F2, F4 and F8 written in (`revised/prototype_revised.diff`), run through the review's own probes:
- at the budget's edge, a loop of 50 `fd_filestat_get` ends and reports fuel exactly as main's driver does, from the full budget down to full − 15 (`revised/edges.out`);
- a granted file read between two stats gives the same answers whatever the host's read history (`revised/atime_grant.out`: both runs `…001000 …001000 …002000`);
- stdio's `fstat` answers inode 0 and time 0, as on main (`revised/semantics.out`).

## Decisions

1. **The driver shadows five calls and forwards each to wasmtime.** The calls are `fd_filestat_get`, `path_filestat_get`, `fd_filestat_set_times`, `path_filestat_set_times` and `fd_readdir`.
   - **How.** As the runner's mounts do (spec 032, Decision 1; spec 048), studied and written again in the driver, which never imports the runner. A small module (the *trampoline*) imports wasmtime's own five calls from a plain linker and exports one function each. It is instantiated on the guest's memory, after the guest and before it runs. The shadow calls it, and wasmtime does everything it does today: the descriptor table, rights, path resolution, every errno and every trap. Only a successful answer is rewritten, in the guest's memory, where wasmtime wrote it, and only these fields: a filestat's `ino` (8 bytes at 8) and its three times (24 bytes at 40), never its padding; a listing's `d_ino` and padding (Decision 3).
   - **Fuel-neutral, at the budget's edge too.** The shadow reads the store's fuel, raises it by 2**20 for the forward, and sets the value it read back in a `finally`. So the guest pays for its own instructions only, as with any host call in the product, and the trampoline's own few instructions can never run a guest out of fuel early: an out-of-fuel run still spends exactly its cap (`test_guest.py`'s two fuel-cap rows; the review's F2).
   - **Bound before the guest runs.** `run()` binds the trampolines right after instantiation, and asserts they are bound, before the fuel cap and before any export is called. A shadow called earlier (only a wasm start section could; no guest of the judge has one) raises `RuntimeError("a file call before the driver's trampolines were bound")`, which ends the run as a trap that names it.
   - **A second trampoline, on a page of its own,** imports `fd_filestat_get` and `path_filestat_get` for the driver's own stats after a set-times call (item 2), so they never touch a byte of the guest's memory.
   - **Why forward rather than answer.** Answering a stat means knowing wasmtime's descriptor table and its path rules; forwarding keeps them wasmtime's.
   - **Why not a fixed `utime` before each run.** Files the guest makes, and every inode number, come after it.
   - **The product is untouched.** `wasi_python.run` keeps the host's real times and inode numbers. Only the judge's measurement changes.

2. **A file's times come from the driver's clock.** The driver keeps, for each file (by wasmtime's inode number), each of its three host times and the answer it gave for it.
   - A time the guest has not seen for that file is answered with the clock's next value: one value for all the times that are new in one answer, and the clock steps once, as for a `clock_time_get`. So a file first seen at one moment has `atim = mtim = ctim`.
   - A time the host still holds is answered as before. An unchanged file keeps its times.
   - A `mtim` or `ctim` that moved on the host (a write, a rename into the folder, a `utime`) is answered with the clock's next value. So a write moves `mtim`, as it does on the host.
   - **`atim` follows `noatime`.** A host moves a file's atime when it is *read*, depending on the file's past (EXECUTED by the review: on APFS a read moves it only while atime is before mtime; Linux's `relatime` has its own rule). So a host atime move alone never gives a new answer: `atim` takes a new value only when the guest sets it, or when `mtim` or `ctim` takes a new value in the same answer (then all the new ones share that value). Many hosts mount `noatime` anyway. One consequence, written down: a write after an exact `utime` replaces the set `atim` with the write's value, as a `relatime` host would at the next read.
   - A time the guest set itself (`*_filestat_set_times` with an exact time) is answered exactly as set, while the host keeps it. A time set "now" (`ATIM_NOW`, `MTIM_NOW`) is the clock's next value. To know which file a set-times call reached, the shadow stats it again on its own page after the host accepts it.
   - **Why the clock, not a constant.** With one constant time a folder never changes, so CPython's import system never rescans it: a module written into a folder already on `sys.path` is not found (EXECUTED, `probe_const_out.out`: `ModuleNotFoundError: No module named 'b'`; with this design, `1 2`).
   - **Why the same clock.** A file's time is then never ahead of `time.time()`. CPython's `test_utime_current` pair passes (EXECUTED, `probe_cpython_tests.out`), where on main it fails by 25,180,957 seconds.
   - **Why a full clock step, not a nanosecond.** A variant that stamped files at the clock's last value plus one nanosecond, so stats never step the clock, failed `test_a_program_sees_real_entropy_and_file_metadata[snapshot]` (`variants.out`): a float holds 1767225600.000000001 as 1767225600.0, the build's pinned time. A step is one microsecond, which a float holds.
   - **Every time lies in one second.** The clock steps a microsecond a call, so every answered time lies in the second 1767225600 until a run has made a million clock calls. Anything that keeps whole seconds (a `.pyc`'s source mtime, a tar or zip member's time, logging's rollover) sees every file in that one second. That is the stepped clock's nature (spec 002, Decision 9), not a defect of this spec: the review's run of 065's `cpython-fs` group shows no outcome change from it beyond Decision 8's.

3. **A file's inode number is a count.** The first file the guest sees is 1, the next 2, and so on, by wasmtime's inode number. The same file keeps its number: by any stat, and in readdir's `d_ino`, where wasmtime gives the same hash as its stat (EXECUTED, `probe_dino.out`). Two names of one file (a hard link) keep one number, since wasmtime's hash is one.
   - **Zeros pass through.** wasmtime answers its stdio streams with inode 0 and times 0 (EXECUTED by the review). A zero varies with no host, so the driver answers it unchanged: an inode 0 is 0, a time 0 is 0, with no stamp and no clock step. So the judge never shows a stream an inode or a date the product does not.
   - **readdir.** Each whole entry's `d_ino` is rewritten (a 0 stays 0). An entry cut at the buffer's end keeps no partial number: of its `d_ino` bytes (8 to 16) and its padding bytes (21 to 24), those present are zeroed, and nothing else of it is touched (wasi-libc never reads a cut header; it lists again from that entry). Each whole entry's three padding bytes are zeroed too: wasmtime 49.0.0 leaves host bytes there (spec 048's guard), and a forwarded listing should hold no host byte.
   - **A listing whose count lies over it** (a guest's `used` pointer inside its own buffer) is left as wasmtime wrote it. No check does this; the runner's guard handles it for embedders.
   - **Why a count from 1** (corrected at the build review, F1). A number never repeats within a run and never collides. The draft gave a second reason: that a count with three 30-bit digits, like wasmtime's hashes, would still need an acceptance because the times alone moved 21 to 24 rows past the tolerance. **On the build's base that reason is false.** The times alone move none of the 22 rows that grow (their times-only part is +0.00 to +0.01 parts in 10^4, `at-build/growth.out`), and the build review measured a count from 2**62 returning four of them to their accepted values, three to the instruction (its section 3). So a three-digit count would probably avoid most or all of the growth; that is untested on the other 18 rows.
     - **The count from 1 stays**, for these reasons: a small number reads as the driver's own and is never mistaken for a host hash, so a check can assert it (`< 2**30`) and a reader can see at once where it came from; a high base would fix no further host input, since the fuel is exact either way (one value over six runs); and every dry run is red until this lands, so re-measuring 168 rows for a different base would hold every landing back. A three-digit base can follow as its own specification if the owner wants fewer restated values.
     - **The cost of that choice is the growth**, accepted with its measured cause: the inode number's digit count (one where wasmtime's hashes took three), confirmed by the build review on four rows. **Why one digit costs more instructions, not fewer, is unexplained** (the review: two digits cost 17 to 238 fewer than three; one digit costs 15,186 more on kiwisolver and 103 million more on pandas-reshape). The words "an int's digits, hashing, the allocations after" are a label, not a mechanism: INFERRED at most.

4. **What the driver does not answer.**
   - `dev` (wasmtime's answer is always 1, READ in the typed-grants memo), `nlink`, `size` and the file type: the host's, the same on every run on one machine. `nlink` holds that only because the driver no longer shares the stdlib zip by hard link (the amendment of 2026-10-19, below).
   - `clock_res_get`: spec 065 answers it.
   - `Turns`, the session driver: it records no fuel.
   - A run on the caller's own engine (`own=`): it is shadowed too, so every guest of the driver sees the same files; it counts no fuel, so nothing is set back.

5. **The real-metadata check keeps its power.** `test_a_program_sees_real_entropy_and_file_metadata` asks that a program never see the constants the build pins while it snapshots: `ino` 0 and a time of exactly 1767225600 s (`recipes/reactor_main.c`, `pin_filestat`). The driver's answers are never those: a count starts at 1, and the clock's first value is 1767225600.000001 s. So a pinned value that leaked from the snapshot's heap would still show. Its docstring says so.
   - **Not added: an assertion of the driver's own values** (an inode below 2**30, a time between the clock's start and `time.time()`), which the review offered as optional. That check is about the artifact: what it must prove is that no pinned value reaches a program, and it proves it. The driver's own answers are the unit rows' and the new check's to assert, and they do. Tying an artifact check to one judge's numbering would make it fail for a reason that is not the artifact's.

6. **A file system with coarse times.** A host that stamps writes coarsely (ext4 uses a clock of a few milliseconds) can leave a time unchanged across a write, and then the guest sees no change, as it would on that host. Fuel is compared only on darwin-arm64 (`accepted.json` holds its metrics only), where APFS gave each of 5,000 writes its own time (EXECUTED, `granularity.out`: the smallest step 2,917 ns).
   - **So the new check asserts "same output, same fuel" on darwin only** (the review's F3; the release's `verify` job runs it on Linux and Windows too). Off darwin it asserts what holds on any host: eight distinct inode numbers below 2**30, every `DirEntry.inode()` equal to its stat's, the set time back as set, and no file after the clock. Its docstring says why.
   - **Why not a program that no coarse host can perturb.** One would have to see no file before its last change. But CPython's `open()` stats a new file before the program writes it (EXECUTED by the review), so the guest cannot make its own files that way; and files made by the host and set with `utime` still move the host's `ctim` by the host's own clock (on ext4 a `utime` sets ctime to "now", coarsely), and a moved `ctim` takes a clock step. The promise this spec makes is "the same fuel on a host with fine file times", and darwin is where the ratchet holds it; the check promises no more.
   - The driver's docstring says the same: fuel repeats on one machine whose file system stamps every change apart, at one checkout path.

7. **The restated values.** This table and its numbers are the draft's evidence, measured on main `59b90b6` before the review. The build measures again on its own base (after 065 and any spec that lands before it), and **the landing notes' `--accept-growth` list, measured there, replaces this table**. Against `accepted.json` (`moved_prototype.out`; one value five times on every row but 081's two): 50 rows rise, 60 fall, 38 are unchanged. The sum over all rows moves +0.007%; the mean row +0.0002%, the median 0. The largest moves are +0.078% (`test_sqlite_job_matches_native`) and −0.055% (`test_nothing_is_a_shared_library`).
   - **Why they move: two measured causes, per row.** The guest now sees other values, and each row's move splits into two parts (the review's `out/decompose.out`, from `fuels.tsv`):
     - **the times**: clock values where the host's were. The times-only driver alone moves each row by its first part (for `test_sqlite_job_matches_native`, +4.19 parts in 10^4);
     - **the inode number's size**: one 30-bit digit (a count) where wasmtime's hashes took three (or two, one time in sixteen). Adding the count moves each row to its full value (sqlite +7.76). Numbering from 2**63, three digits like the hashes, equals the times-only fuel on 135 of 147 rows (the review's `out/variants_equal.out`): on most rows it is the inode's size, not its value, that costs. How a value turns into instructions inside CPython (an int's digits, a hash's slot, the allocations that follow) is INFERRED; the split itself is measured.
   - **Why this is not a cost of the driver.** The moves are symmetric, and the forward itself costs the guest nothing (the measurement). On the draft's base, numbering from 2**63 (`moved_inobase.out`) still moved rows past the tolerance (46 rise, 57 fall, 24 past it); on the build's base that no longer holds (Decision 3, corrected: a three-digit count would probably avoid the growth, and the count from 1 is kept for the reasons given there).
   - **Per-row values in the landing notes.** For each row of the growth list, the landing notes give the accepted value, the times-only value and the full value, from the build's own runs: the times-only value is measured on a scratch copy of the build with the one-line `revised/times_only.diff` (wasmtime's inode number passed through). The judge carries no switch for it. So the growth reason names, per row, how much the times and how much the inode's size moved it.
   - **The 21 that rose past the tolerance in the draft's measurement** (evidence, not the list the lane accepts):

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

   - Not in this table: the upstream groups (numpy's and pandas' 11 rows, and 065's CPython groups, which record fuel once 065 lands) and the new check's rows (new). Criterion 6 measures the upstream groups in the build, and their rises join the growth list. The review measured two of 065's groups with the prototype: `cpython-fs` −0.085%, `cpython-archives` −0.009%.

8. **Spec 065's class `stepped-clock` shrinks to one test.** 065 admits three CPython tests there, "file times are the host's, time.time() starts at 2026-01-01". With this driver, the two `test_utime_current` tests pass, and `test_logging`'s `test_rollover` still fails: it waits for a rotation a second away, and the clock steps a microsecond a call (EXECUTED, `probe_cpython_tests.out`; and the review's run of the whole `cpython-fs` group: 3,710 passes on 065's driver, 3,712 with the prototype, exactly these two tests changed). **065 lands first**, and this spec is built on that main, so this spec makes the change:
   - the two `test_os` ids leave `tests/upstream/expected/cpython-fs/stepped-clock.txt`;
   - the class's `match` in `tests/upstream/python.toml` keeps only `No rotated files found`;
   - its reason, there and in `tests/known_gaps.toml`, says the clock's step, not the file times; the gap's `match` names one finding and its new digest.
   - This narrows an allowance because the judge stopped causing two failures. It is a judge change with this reason, seen in the judge-hash line, never a widening.
   - **Every other CPython, numpy and pandas test** runs as before or the build stops: the build runs every upstream group with this driver (criterion 6), and any outcome that changes, other than these two, is a finding the build reports before it goes on.
   - If the lane must land 083 before 065 after all, 065's lane carries these three edits and 065's landing notes say so.

9. **The merge with spec 081.** 081 adds `measured` and `host_roots` to `run()` and a guard on its first lines; this spec adds the shadows after the linker is made, and the trampolines after the guest is instantiated. Whichever lands second rebases and merges by hand; neither changes the other's behaviour. 081 left the driver's docstring line "repeats to a few parts in ten million" to this spec, which makes it "repeats exactly on one machine whose file system stamps every change apart, at one checkout path" (Decision 6).

## Intent

Every fuel metric the judge records depends on no file time and no inode number of the host: a file's times are values of the driver's clock, and its inode number a count, so the same check costs the same on every run; and a file the guest writes is never dated after the guest's clock.

## Design

- **`tests/harness/guest.py`.**
  - Constants: `FILE_CALLS` (the five calls and their wasm parameters), the filestat and dirent layouts as `struct.Struct`, the set-times flags.
  - `forwarders_wat(names, own_page)`: the trampoline's text. Its compiled module is cached for the driver's own engine only (`engine()`, made once per process); a run on its own engine (`own=`) compiles its own each time. No cache is keyed by `id(engine)`: an id can be reused once an engine is collected, and a module of a dead engine must never reach a new one.
  - `FileFacts(now)`: one run's answers. `ino(real)`, `stamp(real_ino, real_times)` (Decision 2's `noatime` rule, zeros through), `filestat_fields(raw) -> (ino, times)`, `set_times(raw, chosen)`, `listing(bytearray)`. Pure: no wasmtime.
  - `_FileCalls(counted, facts)`: `bind(store, engine, plain_linker, guest_instance)`; `call`, the forward, with the fuel raised by 2**20 and set back; the five shadows, each forwarding and then writing a successful answer's `ino` and times (or a listing's `d_ino` and padding) in place.
  - `run()`: makes a plain linker with `define_wasi()`, a `FileFacts` on the shared clock (`REALTIME_START_NS + next(ticks) * CLOCK_STEP_NS`), defines the five shadows beside `random_get` and `clock_time_get`, and binds the trampolines right after instantiation, with an assertion that they are bound, before the fuel cap.
  - The module docstring: the driver answers a file's times and inode number too (this spec), and fuel repeats on one machine whose file system stamps every change apart (Decision 6).
  - The prototype is `prototype.diff` (194 lines added) and `revised/prototype_revised.diff` (the review's F1, F2, F4, F8) in the evidence folder; the build adds the engine rule, the bind assertion, field-only filestat writes (F8) and the docstrings.
- **`tests/harness/wat.py`.** `FILE_FACTS`, a snapshot-shaped module that imports the five calls, `path_open` and the door. Its `run` stats a file in a grant twice with a door call between (the host changes the file there), reads it with a door call between two more stats (the host reads it there too), lists the grant, sets the file's times by path and by descriptor (exact, then "now"), stats fd 1, and sends each answer through the door; then it spins once for every set bit of the answers' inode, `atim` and `mtim` words (not `ctim`, which hosts move by their own rules), so its fuel follows those values. And `stat_loop(name, n)`, a command that calls one two-argument call `n` times.
- **`tests/unit/test_guest.py`.**
  - `test_a_files_times_and_inode_are_the_drivers`: `FILE_FACTS`, twice, over a grant whose file is made again between the runs with other host times (a new host inode, `os.utime` to another year; every host change is a year away, so it holds on a host with coarse times). Both runs send the same bytes through the door, but for `ctim`, and spend the same fuel. In each: the first stat's inode is 1 and its three times are the clock's first value; after the host's `utime` and write, `atim` and `mtim` are the next value and the inode is still 1 (`ctim` is either, as hosts differ); the listing's entry for the file carries inode 1, every inode in it is below 2**30 and every padding byte is zero; the exact set-times come back as set, by path and by descriptor; the "now" set-times come back as one later clock value; fd 1 answers inode 0 and times 0 (F4).
  - `test_a_read_alone_moves_no_answered_time`: in `FILE_FACTS`' read step, the host and the guest read the file between two stats, and the second stat answers the same three times as the first (F1). And on `FileFacts` itself: a host atime move alone gives the same answer; an mtim move gives a new value to `atim` and `mtim` together.
  - `test_a_shadowed_file_call_costs_the_guest_only_its_own_instructions`: `stat_loop` of 50 with `fd_filestat_get` and with `fd_fdstat_get` (not shadowed), same shape: the same fuel.
  - `test_the_forward_never_runs_a_guest_out_of_fuel_early`: the same two loops at every budget from the full cost − 1 down to − 15: each run's exit, trap and fuel are the same for both calls, and an out-of-fuel run spends exactly its budget (F2).
  - `test_a_cut_listing_entry_keeps_no_host_byte`: `FileFacts.listing` on a listing cut at every byte of an entry: whole entries renumbered and padded with zeros; of the cut entry, the `d_ino` and padding bytes present are zero and every other byte is as it was (F8).
- **`tests/checks/test_v1_4_embedding.py`.**
  - `test_file_facts_cost_the_same_on_every_run[plain|snapshot]`: a program makes a folder with eight files, sets one file's times, lists the folder with `os.scandir`, and prints, for each file, `str(st_ino)`, `repr(st_mtime)`, `st_mtime_ns`, whether `DirEntry.inode()` equals `st_ino`, and whether `time.time()` is at least the file's `st_mtime`. It runs twice, the first unrecorded, with a granted host folder whose files are made again between the runs with other times. On darwin: same output, same fuel. On every host: eight distinct inode numbers below 2**30, each `DirEntry.inode()` equal to its stat's, the set time back as set, no file after the clock (Decision 6).
  - The docstring of `test_a_program_sees_real_entropy_and_file_metadata` gains Decision 5's sentence.

## Scope

In: the five shadows, the two trampolines, `FileFacts`, the stdlib copied into each run (the amendment), the unit rows, the checks, the docstrings, the restated values, and Decision 8's class change. Out: the product runner; `clock_res_get` (065); `Turns`; `dev`, `nlink` and `size`; spec 081's path rows.

## Acceptance criteria

0. **The base.** The build starts by rebasing onto main after spec 065 has landed; every number below is measured there.
1. **The checks fail first.** On main's driver: `test_a_files_times_and_inode_are_the_drivers` fails (the two runs' bytes differ, and the inode is a hash); `test_file_facts_cost_the_same_on_every_run` fails on both binaries (fuel differs; a file is after the clock); `test_a_cut_listing_entry_keeps_no_host_byte` and `test_a_read_alone_moves_no_answered_time` fail (`FileFacts` does not exist). Against the draft's prototype, the read row, the cut-entry row, the zero answer and the fuel-edge row each fail (F1, F8, F4, F2). `test_a_shadowed_file_call_costs_the_guest_only_its_own_instructions` and `test_the_forward_never_runs_a_guest_out_of_fuel_early` pass on main and with the build: they guard the forward's neutrality.
2. **Zero spread.** With the build, five runs of the 69 fuel functions and the new check: every row gives one value five times, except 081's two lxml grant rows while 081 is not landed.
3. **The behaviours.** `probe_times.py` with the build, eight runs each: every program gives one fuel value and the outputs of the prototype's run (`probe_times.out`): an unchanged file keeps its time, a write moves it, both `utime` forms round-trip, `utime` "now" is within 0.05 s of `time.time()`, a module written after a scan imports. `probe_cpython_tests.py`: the two `test_utime_current` tests pass and `test_rollover` fails, as Decision 8 says.
4. **The real-metadata check still bites.** Two mutants of the build's driver each fail `test_a_program_sees_real_entropy_and_file_metadata` on both binaries: one that answers every inode as 0, one that answers every time as 1767225600 s.
5. **Neutral, and nothing else moved.** The build's rewrite switched off: main's fuel to the instruction for `probe_var.py`'s first program; and `test_the_forward_never_runs_a_guest_out_of_fuel_early` passes (the edge).
6. **Every upstream group.** The build copies the CPython, numpy and pandas tarballs, trees and test kit from the main tree into the worktree (read from main's `downloads/` and `build/`, never written) and runs every upstream group, 065's CPython groups (a, b, c, fs, archives) and numpy's and pandas' eight, five runs each: one fuel value each; the same outcomes and class members as `accepted.json` records, except Decision 8's two tests; and `cpython-fs-stepped-clock` as the one-finding gap Decision 8 writes in, with the digest the build sees. Each group's fuel move is listed in the landing notes, and its rises join the growth list. If a copy cannot stand in for the build's own (a check refuses it), the landing notes say so and the lane measures those groups.
7. **The judge.** `ruff check` and `ruff format --check` green; the fast tier and one full run (`-n 3`) against `build/sets/s-c50ca51fae5eb55b-c9dcb5b8`: no failure, no lost pass; the ratchet's moves are the restated rows, the new check's rows as gained, and `judge changed`. The landing notes give `--accept-growth` its list: each row with its accepted, times-only and full values (Decision 7).

## Amendment of 2026-10-19: the stdlib zip's link count

**Why.** Spec 081's delta look found a fourth host value that reaches a measured guest: a file's link count (`nlink`). The driver hard-links the set's stdlib zip into every run folder (`_place`, `os.link`), so the zip's count is the number of run folders that hold it, in every judge, probe and agent on the machine, alive or left behind. My own draft probes left over 2,000 links in the shared scratch folder (the count reached 2,576; they are deleted, and every probe now removes its run folders). 081's reviewer bisected the effect on a copy: up to 1,017 links gives one set of fuel values, 1,023 or more another, and about 21 rows change across that point, three of them rows that already grew. So a judge's fuel against one set depended on how many links other work had left on its zip.

**The measurement (EXECUTED, `../research/2026-10-19-what-the-guest-learns-about-a-file/amendment/`; every probe removes its work folder).**
- `nlink_fuel.py`, a private copy of the zip granted as the stdlib (the `guest` fixture's `stdlib=`), at 1 link and then with 1,100 more: on main's driver the guest sees `nlink` 2 and 1,104, and fuel moves +300 (a stat of the zip) and +521 (`import json` and a stat); the revised prototype moves the same. With the zip copied into each run, the guest sees 1 both times and the fuel does not move.
- `link_during_run.py`: another run links the shared zip while this guest runs (through the door). The guest's two stats of the zip see 531 and then 532: the count moves *during* a run, from outside it. wasmtime's `ctim` and `mtim` of the zip did not move.
- `runner_links.py`: a guest can make hard links, through the product runner too: in a writable grant `os.link` gives two names with `nlink` 2 each, `samefile` true, and the host agrees.
- `copy_cost.py` (a benchmark fact, not a test): a hard link costs 0.33 ms, a copy of the 22 MB zip 10 to 16 ms, on this machine's APFS.

**Decision 10. The driver copies the stdlib into each run, and removes the copy when the run ends.**
- `_place` gives a file its own inode where it hard-linked it: on darwin an APFS clone (`clonefile(2)` by `ctypes`, what `cp -c` makes), and wherever that fails, or elsewhere, a copy (`shutil.copyfile`); a stdlib folder is copied as before (`copytree`). So the run's zip has exactly one name, the guest sees `nlink` 1 for it, and no other run, probe or agent can change that, before the run or during it.
  - **The clone** (the review's optional point, adopted): 0.13 ms a run against 8 to 16 ms for a copy, with `nlink` 1 and an inode of its own (EXECUTED, `amendment/clone_cost.py` and `.out`). It is about ten lines with its fallback. It changes nothing the guest sees: a clone and a copy both give one name and the same bytes, so the fuel compared on darwin is the fuel of a copy.
- `run()` removes the run's `lib` folder once the guest has ended, in a `finally`, in this order (the review's A1): it reads the run's outputs and fuel, **closes the store** (`store.close()`, as `Turns.close` does), and only then removes the folder with `shutil.rmtree(lib, ignore_errors=True)`. On Windows wasmtime's open handles (the read-only preopen of `lib`, a zip the guest kept open) go with the store, so the removal can succeed; and since its errors are ignored, a removal can never fail or change a run. `Turns` removes its own `lib` the same way at `close()`, after its store. So the disk holds one copy per live run, never one per run of a session. A check reads `Result.root`, never `lib`. A killed run leaves its copy behind; that costs disk only, since no other run links or reads it.
- **Why a copy, not an answered `nlink`.**
  - The shared zip's count moves during a run (531 to 532 above), so no answer computed from the host's count of that file is stable; only a file no one else links is.
  - A guest makes hard links of its own (`runner_links.py`; the review's `semantics.out` through the driver), and their counts must stay true: 2 for two names. A fixed `nlink` would need three more shadows (`path_link`, `path_unlink_file`, `path_rename`) to keep each file's count by hand, inventing behaviour the copy gets from the host for nothing.
  - With the copy, every `nlink` the guest sees is the host's true count of a file only this run can link. The driver answers no `nlink`, and Decision 4 stands.
- **The cost.** 10 to 16 ms a run on APFS, and one live copy per running guest. Judged worth it: it removes a hidden input from every row, the price of determinism this spec pays everywhere.
- **What it does not cover.** A file a check itself shares by hard link with another process. None does (READ: the driver's `_place` is the only `os.link` of a guest-visible file in `tests/harness/` and `tests/checks/`; the build greps again).

**Its check, written first.** `test_fuel_does_not_follow_the_stdlib_zips_link_count`, in `tests/checks/test_v1_4_embedding.py`, both binaries (it needs the artifacts): a private copy of the set's zip, granted with `stdlib=`; one program (`import json`, a stat of the zip, its `st_nlink` printed) runs with the copy at 1 link and again with more links to it, made under the check's own temp folder and removed in a `finally`. Both runs print `nlink` 1 and the same output; on darwin they spend the same fuel too (Decision 6). On main's driver it fails (`nlink` 2 against 1,104; +521 fuel). It never links the set's own zip, so it perturbs no other run on the machine.
- **How many links (the review's A2).** NTFS allows at most 1,024 links to one file, and the release's `verify` job runs this file on `windows-2025`. So the check makes **1,101** extra links on darwin and Linux (ext4 allows 65,000) and **1,021** on Windows. Both stay past 081's bisected flip (one set of values up to 1,017 links, another from 1,023): a driver that regressed to linking would show its two runs `nlink` 2 and then 1,104, or on Windows 2 and then 1,024 (the copy, 1,021 extra links and the two runs' own), so each comparison crosses the flip, and Windows' total stays within 1,024 even then. With the build the copy holds 1 + 1,021 = 1,022 links on Windows, two below the limit.

**Criteria added.** 8. **The link count.** `test_fuel_does_not_follow_the_stdlib_zips_link_count` fails on main's driver and passes with the build. With the build, no file under the worktree shares the set zip's inode during or after the full judge (`find … -inum`; the driver no longer links it), and `nlink_fuel.py` gives `difference +0` on both programs. 9. **The probes clean up.** Every probe in the evidence folder removes its work folder at exit; after the build's measurements, no file under the scratch folder or the worktree shares the set zip's inode (`find … -inum`).

## Disposition of the pre-build review

The review (`scratchpad/083-review/083-the-driver-answers-file-timestamps-spec-2026-10-19.md`, probes and outputs beside it; copied to `../reviews/` by the lane): "ready once F1 to F5 are written in". Each finding, and where it went:

- **F1 (atime follows host reads): fixed in the design.** Decision 2's `noatime` rule; the unit row `test_a_read_alone_moves_no_answered_time`; criterion 1. On the revised prototype the review's `atime_grant.py` gives one answer whatever the host's read history (`revised/atime_grant.out`).
- **F2 (the forward at the budget's edge): fixed.** Decision 1 raises the fuel by 2**20 before the forward and sets it back after; the unit row `test_the_forward_never_runs_a_guest_out_of_fuel_early`; criteria 1 and 5. On the revised prototype the review's `edges.py` matches main's driver at every budget from full to full − 15 (`revised/edges.out`).
- **F3 (the new check off darwin): scoped.** Decision 6: "same output, same fuel" is asserted on darwin only; the host-independent assertions run everywhere. Chosen over a program no coarse host can perturb, because CPython stats a file before writing it and a host `utime` moves `ctim` by the host's clock; the driver's docstring promises repeats only on fine file times.
- **F4 (stdio's zeros): fixed.** Decision 3: an inode 0 and a time 0 pass through, with no stamp and no step; a row in `test_a_files_times_and_inode_are_the_drivers` (fd 1). `revised/semantics.out` shows main's answers.
- **F5 (065 first; its groups in the criteria): written in.** Status and Depends on: built after 065 lands; Decision 8 made unconditional, with the fallback if the lane orders it otherwise; criterion 6 runs every CPython group five times and lists their fuel moves in the growth list.
- **F6 (stale base): done.** The branch is rebased onto main `08de0c8`; criterion 0 rebases again onto main after 065; Decision 7's table is the draft's evidence, replaced by the landing notes' list.
- **F7 (the growth reason per row): written in.** Decision 7 names the two measured causes, the times and the inode's size, from the review's decomposition; the landing notes give each growth row its accepted, times-only and full values, the times-only ones from `revised/times_only.diff` on a scratch copy.
- **F8 (the cut entry and the filestat rewrite): aligned.** The listing half was fixed in the revised prototype: of a cut entry only the `d_ino` and padding bytes present are zeroed (Decision 3; `revised/prototype_revised.diff`), and the cut-entry row checks every other byte is unchanged. The filestat half was the build's (the confirmation's N1): the build writes only a stat's `ino` (8 bytes at 8) and its three times (24 bytes at 40), so the 7 padding bytes keep the guest's own; `test_a_files_times_and_inode_are_the_drivers` asserts they keep 0xAA, and the review's `stat_padding.py` gives "0 of 7" on main and on the build (corrected at landing; the revision's sentence had said the code already did).
- **F9 (design points): answered.**
  - The `id(engine)` key: dropped; the module is cached for the driver's own engine only and compiled per run for `own=` (Design).
  - A shadow called before `bind`: a named `RuntimeError` that ends the run, and an assertion after `bind` in `run()` (Decision 1).
  - The single second: written into Decision 2.
  - The driver-values assertion in the real-metadata check: not added, with the reason in Decision 5.

## Disposition of the build review

The review (`scratchpad/083-buildreview/083-the-driver-answers-file-timestamps-build-2026-10-19.md`, probes beside it; copied to `../reviews/` by the lane): "lands once F1 is answered in writing"; the code correct, cross-host sameness confirmed on darwin. Answered in `context/` only, with no code change and no new judge run, as the lane asked:

- **F1 (medium): answered in writing (option a).** Decision 3's reason is corrected: on this base a three-digit count would probably avoid the growth (measured on four rows); the count from 1 stays for the reasons now given there; the growth is accepted with its measured cause, the inode number's digit count; why one digit costs more is unexplained. Decision 7, the landing notes' cause and the `--accept-growth` text say the same.
- **F2 (low): fixed.** The landing notes name `build/083/latest-full.json` as the full record.
- **F3 (low): fixed.** Departure 5 (a guest with no memory export raises `KeyError`), and the sentence on criterion 1's prototype half.
- **F4 (low): taken as a follow-up**, written into the landing notes; no unit row added, so the judge is unchanged by this answer.
- N1 to N3: no action; N3's addition to the growth text is made.

## Landing notes

### What was built

On `spec/083-the-driver-answers-file-timestamps`, rebased onto main `9d89535` (065 landed; 081, 063 and 077 before it) with no conflict: the draft, its revision, the amendment and A1/A2, then `0bc21ea` (the checks, written first), `29e6794` (the driver), `cb67e4b` (the file-facts check reads the guest's clock by `clock_gettime_ns`), `e511da2` (Decision 8), `c682177` (the probes take a private set), `51f3402` (the CHANGELOG entry, the Kind line, F8's sentence), then these notes. **Not build-class:** nothing under `scripts/`, `recipes/`, `downloads/SHA256SUMS` or the release workflow. Evidence: `../research/2026-10-19-what-the-guest-learns-about-a-file/at-build/`. Every run against a private clone of main's set (`cp -c -Rp build/sets/s-c50ca51fae5eb55b-c9dcb5b8 build/set-083`, `SHA256SUMS` `c9dcb5b8`, every file checked against it after the owner's pause), never the shared set; `-n 3`. The upstream groups ran on clones of the main tree's CPython, numpy and pandas tarballs, trees and test kit, cloned into the worktree (read from main's `downloads/` and `build/`, never written).

### The checks fail first (criterion 1, EXECUTED)

- On main's driver (`unit_first.out`): `test_a_files_times_and_inode_are_the_drivers` (the two runs' answers differ; the inode is a hash), `test_a_read_alone_moves_no_answered_time` (the host's read moved atime) and `test_a_cut_listing_entry_keeps_no_host_byte` (`FileFacts` does not exist) fail; the cost and edge rows pass, as guards.
- `checks_first.out`: both new checks fail on both binaries on main's driver: `test_file_facts_cost_the_same_on_every_run` prints `8 False True True False 1 2` (hashes above 2**30; a written file after the clock), and `test_fuel_does_not_follow_the_stdlib_zips_link_count` sees `nlink` 2 and then 1,104.
- With the build all five unit rows and all four check rows pass.

### Zero spread (criterion 2, EXECUTED, `spread_build.out`, `fuels.tsv`, `runs.out`)

Five passes of every fuel-recording function (`funcs.txt`: the 69 of the draft, 065's groups, and the two new checks): **168 rows, every one gives one value five times, largest spread 0**. That includes all 16 upstream groups (CPython's five, numpy's three, pandas' eight) and spec 081's two lxml rows, which 081 has made path-independent. Before 083, 35 of 148 rows varied (the draft's measurement); the spec's "2 of 148" was before 081 landed; it is 0 now.

**`test_upstream_suite[cpython-fs]`** (the row 039's dry run 39291580648 saw grow on macos-15): **59,778,645,587** on the private set in each of the five passes and in the full judge, six runs, one value (`fuels.tsv`). Accepted at `9d89535`: 59,839,885,329.

### The behaviours (criteria 3 to 5, 8 and N1, EXECUTED)

- `probe_times.out`: twelve programs, eight runs each, one fuel value each; an unchanged file keeps its time, a write moves it, both `utime` forms round-trip, `utime` "now" is within 0.05 s of the guest's clock, a module written after a scan imports.
- `probe_cpython_tests.out`: on main the two `test_utime_current` tests fail by 25,198,318 s and `test_rollover` fails; with the build only `test_rollover` fails.
- `cpython_fs_class.out`: with the build, the `cpython-fs` group passes, and its class `stepped-clock` has one finding, digest `896f645c570d` (written into `tests/known_gaps.toml`).
- `mutants.out` (criterion 4): a driver answering every inode 0, and one answering every time 1767225600 s, each fail `test_a_program_sees_real_entropy_and_file_metadata` on both binaries.
- `neutral.out` (criterion 5): with the build's rewrite switched off, `probe_var.py`'s first program spends 16,255,056, main's value to the instruction; with it on, one value (16,254,698) over 20 runs where main gives two. The edge row passes.
- `nlink.out` (criterion 8): `nlink_fuel.py` on main's driver: +300 and +521 between 2 and 1,104 links; on the build: `nlink` 1 at both counts, +0. The private set's zip kept one link through every run (`stat`), and no file under the worktree shares its inode (`find -inum`).
- `stat_padding.out` (N1): "0 of 7" padding bytes changed, on main and on the build.
- Criterion 9: every probe removes its work folder at exit.

### The judge (criterion 7, EXECUTED, `full_judge.out`)

The log is `build/full-083.log` and **the full judge's record is `build/083/latest-full.json`** (627 checks, on `51f3402`), in the worktree: the lane's sameness step uses that file. The worktree's `build/progress/latest.json` is a later partial run (44 checks, dirty), not the record (the build review's F2; the draft of these notes named it wrongly).

- `ruff check` and `ruff format --check` on `src/` and `tests/`: clean.
- Fast tier (`-m "not slow" -n 3`, before the clock fix): one failure, `test_no_test_reads_a_clock` (the check's guest program wrote `time.time()`, which the rule's textual scan reads as a host clock); fixed by `cb67e4b`, the rule then passes.
- Full (`uv run pytest -n 3`, on `51f3402`): `wasi_python v1: 527/627 pass · 77 gap · 23 blocked · 0 fail (unit suite 1584/1592, 8 skipped)`; `2111 passed, 31 skipped, 77 xfailed in 548.34s`; `ratchet vs b91e0eaa4e: lost 0 · absent 0 · unrun 0 · unrun locally 21 · gained 4 · grew 22 · more 1 · judge changed: …`. The 4 gained are the two new checks' rows; `more 1` is `cpython-fs`'s passes, 3,710 to 3,712 (the two `test_utime_current` tests); the 22 grown are the list below. The blocked rows need source trees, compile records, the oracle, the wheel, the wasmtime CLI and prior-art clones, which a worktree without a build lacks.

### The restated values and the growth list (Decision 7, F7; `growth.out`)

Against `accepted.json` at `9d89535`, 164 rows: 48 rise, 78 fall, the rest unchanged; mean −0.0024%, median 0, sum −0.020% (most of it CPython's groups). **22 rise past the tolerance.** Each with its accepted value, its times-only value (one pass of a scratch copy with `times_only.diff`: wasmtime's inode numbers passed through, times answered) and the build's value (one value over five passes), with each in parts in ten thousand:

| row | accepted | times only | full | times only, per 10^4 | full, per 10^4 |
|---|---|---|---|---|---|
| `test_upstream_suite[pandas-reshape]` | 102,664,111,646 | 102,664,115,398 | 102,767,163,170 | +0.00 | +10.04 |
| `test_kiwisolver_raises_unsatisfiable_constraint[snapshot]` | 20,996,483 | 20,996,483 | 21,011,669 | +0.00 | +7.23 |
| `test_upstream_suite[pandas-io-parser]` | 93,556,158,855 | 93,556,167,361 | 93,593,511,781 | +0.00 | +3.99 |
| `test_numpy_and_pandas_are_builtin_at_manifest_versions[plain]` | 4,917,358,672 | 4,917,358,638 | 4,919,200,297 | -0.00 | +3.75 |
| `test_lxml_xml_job_matches_native` | 23,963,555,943 | 23,963,555,994 | 23,970,300,286 | +0.00 | +2.81 |
| `test_upstream_suite[cpython-archives]` | 164,602,698,738 | 164,591,681,819 | 164,648,434,127 | -0.67 | +2.78 |
| `test_recursion_through_python_raises[xslt-extension-snapshot]` | 226,779,285 | 226,779,285 | 226,836,367 | +0.00 | +2.52 |
| `test_upstream_suite[numpy-lib]` | 132,021,562,863 | 132,021,581,027 | 132,051,825,072 | +0.00 | +2.29 |
| `test_the_fast_reader_builds_zipimports_dict[truncated]` | 288,691,792 | 288,691,792 | 288,752,027 | +0.00 | +2.09 |
| `test_the_fast_reader_builds_zipimports_dict[padded]` | 1,538,549,373 | 1,538,549,373 | 1,538,865,236 | +0.00 | +2.05 |
| `test_lxml_is_builtin_at_manifest_versions[snapshot]` | 208,776,178 | 208,776,178 | 208,816,454 | +0.00 | +1.93 |
| `test_recursion_through_python_raises[lxml-target-snapshot]` | 229,963,362 | 229,963,362 | 230,006,596 | +0.00 | +1.88 |
| `test_the_fast_reader_builds_zipimports_dict[prepended]` | 289,662,951 | 289,662,934 | 289,714,976 | -0.00 | +1.80 |
| `test_sqlite_job_matches_native` | 5,148,863,956 | 5,148,863,990 | 5,149,743,772 | +0.00 | +1.71 |
| `test_libxml2_has_no_zlib[plain]` | 475,324,597 | 475,324,597 | 475,403,860 | +0.00 | +1.67 |
| `test_gb18030_is_never_silently_wrong[plain]` | 5,037,234,102 | 5,037,234,102 | 5,037,972,944 | +0.00 | +1.47 |
| `test_read_html_uses_lxml_by_default[plain]` | 5,006,283,082 | 5,006,283,116 | 5,007,007,755 | +0.00 | +1.45 |
| `test_files_by_path_in_grants[snapshot]` | 219,244,114 | 219,244,114 | 219,275,491 | +0.00 | +1.43 |
| `test_files_by_path_in_grants[plain]` | 493,206,148 | 493,206,148 | 493,266,086 | +0.00 | +1.22 |
| `test_the_fast_reader_builds_zipimports_dict[explicit_dirs]` | 291,391,341 | 291,391,341 | 291,421,317 | +0.00 | +1.03 |
| `test_lxml_is_builtin_at_manifest_versions[plain]` | 499,916,405 | 499,916,405 | 499,967,571 | +0.00 | +1.02 |
| `test_regex_is_builtin_at_manifest_version[plain]` | 440,316,072 | 440,316,072 | 440,360,134 | +0.00 | +1.00 |

- **The cause, per row.** On every row of the list the times-only part is 0.00 to 0.01 per 10^4 except `cpython-archives` (−0.67): the times alone barely move these rows on this base. The rise is the inode number's size: one 30-bit digit (the count) where wasmtime's hashes took three (two, one time in sixteen). The build review confirmed it on four rows: a count from 2**62 returned each to its accepted value. Why one digit costs more, not less, is unexplained (Decision 3). The times-only copy carries the amendment too (each run's own stdlib, `nlink` 1), so its column already holds the times' and the link count's share against accepted, and the step from it to the build's value is the inode count's alone.
- A times-only value is one draw: with wasmtime's hashes the times-only driver still varies by 17-instruction steps (and by more on the two new checks, which fail there by design: `runs.out`).
- The draft's list (21 rows, Decision 7's table) was on main `59b90b6`; this list replaces it.

### Departures from the specification

1. The file-facts check reads the guest's clock as `time.clock_gettime_ns(time.CLOCK_REALTIME)` (the driver's stepped clock), not `time.time()`: the rule `test_no_test_reads_a_clock` scans text and cannot tell a guest program's clock from the host's.
2. `bind(store, engine, guest)` makes its own plain linker; `FileFacts.fields(raw)` is the name of the spec's `filestat_fields`. There is no separate assertion after `bind`: a shadow called before it finds no forwarder and raises `RuntimeError("a file call before the driver's trampolines were bound")`, which ends the run, as Decision 1 says.
3. `run()` releases the run's stdlib (store closed, then `rmtree` with errors ignored) when it returns and on any exception out of the guest's calls; an exception before them (a preopen that fails) leaves the copy to the session's teardown, costing disk only.
4. A CHANGELOG entry under 0.1.0a8, at the lane's request; the Kind line says so.
5. **A guest that exports no memory** (the build review's F3). `bind` reads the guest's `memory` export to instantiate the trampoline on it, so `run()` now raises `KeyError: 'memory'` for a module without one, where main's driver ran it to its exit (EXECUTED by the review, `probes/nomemory.out`). No guest of the judge lacks the export, and the suite is green; it is a change in the driver's contract, declared here, and left as it is.

Criterion 1's other half, the read, cut-entry, zero and fuel-edge rows failing against the draft's prototype, is evidenced by the pre-build review's runs and `revised/` (`edges.out`, `atime_grant.out`, `semantics.out`), not re-run at build.

**A follow-up (the build review's F4).** Nothing in the unit rows checks that stdio's zeros step no clock: a mutant without the zero shortcut answers zeros all the same and passes every row, since fd 1 is `FILE_FACTS`' last stat. The judge has no hole there (a CPython guest stats its stdio at start, so the ratchet would see a stray step on every row), and this landing changes no code. A later judge change adds one more stat of `f` after fd 1 in `FILE_FACTS`, or a `FileFacts` row asserting that a zero answer leaves the clock where it was.

### For the lane

- 083 lands ahead of 039, 073, 085 and 084 (the lane's order). 078 and 073 edit `tests/harness/guest.py`'s `run()` and `tests/checks/test_v1_4_embedding.py`: textual merges.
- `--accept-judge "spec 083: the judge's driver answers a file's times (its stepped clock) and inode number (a count) itself and gives each run its own stdlib copy, so fuel no longer moves with host file times, inode numbers or link counts; two new checks; 065's stepped-clock class narrows to test_rollover"`.
- `--accept-growth "spec 083: the guest now sees the driver's inode numbers (one 30-bit digit, a count) where it saw wasmtime's 64-bit hashes, and clock times where it saw the host's; 22 rows rise (+1.00 to +10.04 parts in 10^4), each one value over five runs, the times-only part ~0 but for cpython-archives (growth.out); the cause is the inode number's digit count (a count from 2**62 returned four rows to accepted in the build review), kept for Decision 3's reasons"`.
