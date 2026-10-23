# Review of 083 — The judge's driver answers a file's times and inode number (the specification, before build)

- **Date:** 2026-10-19
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I wrote none of the spec, the evidence, the prototype or the code. I read `AGENTS.md`; the constitution (§5.6, §5.7, and rules 4 and 5 of `AGENTS.md`); spec 002 (the stepped clock, Decision 9) as it stands; spec 081's two reviews (`build/reviews-evidence/081-spec/`, `081-buildreview/` in the main tree, F1); spec 068's pre-build review for the format; spec 065 at `6744f0e` (its `guest.py` hunk, its `stepped-clock` class in `tests/upstream/python.toml` and `tests/known_gaps.toml`, and `tests/harness/regrtest.py`, which runs CPython's tests through `harness.guest.run`); the driver (`tests/harness/guest.py`) and its units; `tests/checks/test_v1_4_embedding.py`'s real-metadata check; the release workflow's `verify` job; and wasmtime 49's `crates/wasi/src/filesystem.rs`, `filesystem/unix.rs`, `filesystem/windows.rs` and `p1.rs` (`fd_readdir`). Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `spec/083-the-driver-answers-file-timestamps` at `6abccea`, on main `59b90b6`: the spec and `research/2026-10-19-what-the-guest-learns-about-a-file/` (probes, `fuels.tsv`, `prototype.diff`). The diff touches only `context/` (READ). Main has since moved to `08de0c8` (spec 077 and spec 063 landed; READ, `git log 59b90b6..main`).
- **Ran (EXECUTED, darwin-arm64, APFS, CPython 3.14.2, wasmtime-py 49, the frozen set `build/sets/s-c50ca51fae5eb55b-c9dcb5b8`, read only).** Nothing was written in any git tree. Two scratch copies of `6abccea` (`main/`, and `tree/` with `prototype.diff` applied), and two of spec 065's tip `6744f0e` (`065base/`, and `065proto/` with the same diff applied by `patch`; both with 065's worktree's uncommitted `known_gaps.toml` and `python.toml`, since the committed `known_gaps.toml` at `6744f0e` does not parse, and with `Python-3.15.0` linked read-only from 065's worktree). The machine's load average was about 75 on 10 cores (other agents' judges), so I ran nothing wider than one process per copy. Scripts are in `probes/`, outputs in `out/`, beside this file:
  - `host_atime.py`, `host_atime2.py` → `out/host_atime*.out`: when a read moves a file's atime on this host.
  - `atime_grant.py` → `out/atime_grant.out`; `atime_seen.py` → `out/atime_seen.out`; `atime_zip.py` → `out/atime_zip.out`: whether the prototype's answers follow the host's atime history.
  - `semantics.py` → `out/semantics.out`: stdio, hard links, rename, an unlinked open file, scandir against stat, `.`, utime, a 300-entry listing (cut buffers), on main and prototype.
  - `utime_now.py`, `utime_trace.py` → `out/utime_now.out`, `out/utime_trace.out`: set-times "now", traced through the shadows.
  - `edges.py` → `out/edges.out`: errno and traps through the forward, and the fuel budget's edge, on hand-written commands, main against prototype.
  - `cut_listing.py` → `out/cut_listing.out`: `FileFacts.listing` on a listing cut at every byte of an entry.
  - `decompose.py` → `out/decompose.out`: the 21 rising rows split by the author's own driver variants (`fuels.tsv`).
  - `out/065base-fs.log`, `out/065proto-fs.log`, `out/065base-archives.log`, `out/065proto-archives.log` (and their `*-latest.json`): spec 065's `cpython-fs` group with its classes, and its `cpython-archives` group, on 065's driver and on 065's driver plus the prototype.
  - `out/variants_equal.out`: the author's 2**63 and separate-clock variants against times-only and the prototype, on every row of `fuels.tsv`.

## What holds

- **The problem is real, and the cause is split right (EXECUTED, the author's data).** Five runs on main's driver give a spread on 35 rows (`spread_before.out`); the prototype leaves 2, both spec 081's path rows. In `fuels.tsv`, numbering inodes from 2**63 gives exactly the times-only fuel on 135 of 147 rows (`out/variants_equal.out`). So on most rows it is the inode's size in 30-bit digits that moves fuel, not its value. The separate-clock variant equals the prototype on 144 of 147 rows: the clock steps the stamps take cost nothing measurable.
- **The forward adds no guest instruction while fuel is plentiful (EXECUTED).** A command that calls `fd_filestat_get` 50 times spends 455 on main's driver and 455 on the prototype (`out/edges.out`). The author's `probe_var.out` shows the same for CPython (16,255,056 both, rewrite off). Is "costs nothing" a restored lie? No. In the product, wasmtime's WASI calls are host calls and spend no fuel. The trampoline's 11 instructions exist only in the judge, and setting them back models the product exactly, except at the budget's edge (F2).
- **errno values and traps come back as wasmtime gives them (EXECUTED, `out/edges.out`).** A result pointer out of bounds, a path out of bounds, and a stat result out of bounds each trap on both drivers, with the same first line and no cause. A bad descriptor answers 8 (EBADF) on both.
- **Inode identity holds (EXECUTED, `out/semantics.out`).**
  - Two names of one file (a hard link) give one number, and `os.path.samefile` holds.
  - A rename keeps the number.
  - An unlinked file that is still open keeps its number, and a new file gets another.
  - Every `DirEntry.inode()` equals its `os.stat().st_ino`, on 8 entries and on 300 (the 300 take several `fd_readdir` calls, so cut buffers occur): 300 distinct numbers.
  - `stat('/d')` equals `stat('/d/.')`.
  - READ: wasmtime 49 gives readdir's `..` the directory's own hash (`p1.rs` near line 1974, "incorrect, but legacy"). So `..` gets `.`'s count, as it gets `.`'s hash on main.
  - READ: on Windows the identity is the volume serial plus the file index, read by handle (`filesystem/windows.rs:85-104`). So distinct files stay distinct there too.
- **Set-times semantics hold (EXECUTED, `out/utime_now.out`, `out/utime_trace.out`).** An exact time comes back as set. After "now", atim and mtim are one clock value, never after a later `time.time_ns()`. A write after an exact set moves mtim. ctim follows the host: on APFS a `utime` "now" left the host's ctime unchanged, so the driver keeps its first answer. One clock step is spent and never shown (the re-stat stamps the moved host times before the chosen value replaces them). That is harmless.
- **The real-metadata check keeps its power against the pin (READ).** `recipes/reactor_main.c` `pin_filestat` writes `ino` 0 and all three times as exactly 1767225600 s while pinned. The driver never answers either: the count starts at 1, and the first clock value is 1,000 ns past the start, which a float still tells apart. The author's +1 ns variant failed this check for exactly that reason (`variants.out`). The check's directory size and link count pass through unchanged (Decision 4). Criterion 4's two mutants test the right thing.
- **No other check in the judge reads a file's real times or inode numbers (READ).** Every other `st_ino`, `st_mtime` or `utime` in `tests/checks/` runs on the product runner (`wasi_python.run`) or on the host side: for example `test_the_zip_is_read_only_and_shared`, `test_the_import_path_writes_nothing` and `test_links_and_times_in_a_writable_mount`. The product is untouched, so those checks see what they saw before. The padding-guard units (`test_a_mount_writes_zero_dirent_padding`, `test_a_grant_readdir_writes_zero_dirent_padding`) test the runner's code, not the driver's. So on rule 4: shadowing hides no product behaviour a check is meant to see.
- **Decision 8 holds for spec 065's `cpython-fs` group (EXECUTED, `out/065base-fs.log`, `out/065proto-fs.log`).** That group is 41 CPython test modules (`test_os`, `test_shutil`, `test_pathlib`, `test_importlib`, `test_compileall`, `test_py_compile`, `test_filecmp`, `test_linecache`, `test_mailbox`, `test_logging`, and more). It runs through `harness.guest.run` (`regrtest.py:768`). On 065's driver it gives 3,710 passes and every class as its gap. With the prototype added it gives 3,712 passes: exactly the two `test_utime_current` tests changed. `cpython-fs-stepped-clock` fails with "3 finding(s), digest e3d81bfc44e3", listing `test_rollover` and the two tests as expected but not seen, as Decision 8 predicts. The group's fuel falls from 59,830,266,786 to 59,779,131,177 (−0.085%). The `cpython-archives` group (`test_tarfile`, `test_zipfile`, `test_zipimport`, `test_gzip` and more; `out/065*-archives.log`) passes on both drivers with 1,313 passes each. Its fuel falls from 164,610,406,675 to 164,596,106,765 (−0.009%).

## Findings, most severe first

### F1. A host atime move alone gives a new answer, so the answers follow the host's read history. Medium; fix the design (EXECUTED)

The spec's intent says fuel "depends on no file time of the host". Decision 2 gives a field a new clock value whenever its host value moved, and that includes atim. A host's atime moves when a file is *read*, depending on the file's past:

- EXECUTED (`out/host_atime*.out`): on this APFS volume, a read moves atime when atime is before mtime (a file just written), and not after (a file read once before, or one whose atime equals its mtime). Linux's `relatime` moves it when atime ≤ mtime, or once a day (INFERRED, the kernel's documented rule).
- EXECUTED (`out/atime_grant.out`): a granted host file the host never read. The program stats it, reads it, stats it again, and prints both atimes and `time.time_ns()`. First run: `…001000 …002000 …003000`. Second run, same program, same file: `…001000 …001000 …002000`. The answers and every later clock value differ. Only the host's history changed.
- EXECUTED (`out/atime_seen.out`): a matplotlib plot. The first run after `mpl_data_dir` extracts the data makes 3 atime-only re-stamps. Later runs on the same extraction make 0. `_mpl_data` is a cache per process, so under xdist each worker extracts its own copy. So the first plotting check in each worker gets other answers than later ones, and which check comes first depends on scheduling. That is the serial-against-`-n 6` difference spec 052's `sameness.py` stops a landing for.
- Fuel happened to be equal in both probes (16,613,343; 8,803,496,402). So no accepted row moves today. But any work that follows the values moves: the author's own "fstat times" program spreads 682 on `% 7` of these same fields (`probe_times.out`).

**Fix.** Do not let a host atime move alone produce a new answer. atim takes a new clock value only when the guest sets it, or when mtim or ctim takes a new value in the same answer. This is `noatime` semantics, which many hosts mount with anyway. Say so in Decision 2. Add a unit row: the host reads the file (through the door) between two stats, and the second stat answers the same three times.

### F2. At the budget's edge the forward is not neutral: the trampoline can run the guest out of fuel early. Medium; fix (EXECUTED)

`_FileCalls.call` reads the guest's fuel, runs the trampoline on that same fuel, and sets it back afterwards. When fewer than about 11 units are left, the trampoline itself runs out.

- EXECUTED (`out/edges.out`): a command looping 50 `fd_filestat_get` calls costs 455. On main's driver it still exits 0 with a budget of 455 − 10. On the prototype it traps "out of fuel" at 455 − 7, 455 − 8, 455 − 9 and 455 − 10.
- At 455 − 7 the prototype reports 447 spent of a 448 budget. The `finally` restored one unit that nothing then spent. So the driver's own invariant, an out-of-fuel run spends exactly its cap (`tests/unit/test_guest.py:62-64` and `:126`), breaks for any run that ends inside a shadowed call.
- So, to the question "can it mask a fuel cost the product would have?": no. But it can invent an exhaustion the product would not have, and it can under-report the spend by up to 11.

**Fix.** Lift the fuel before the forward (for example `set_fuel(before + 2**20)`, or `UNMETERED`) and set `before` back in the `finally`. Add a unit row: the same loop at budgets from full − 1 down to full − 15 ends, and reports fuel, exactly as main's driver does (or as the same loop over an unshadowed call of the same shape, such as `fd_fdstat_get`). Criterion 5 should name this row.

### F3. The new check compares two runs on Linux and Windows too, where file times are coarse. Medium; scope or redesign (READ and INFERRED)

- READ: the release workflow's `verify` job runs `tests/checks/test_v1_4_embedding.py` on `ubuntu-24.04`, `windows-2025` and `macos-15` (`release.yml`, the matrix near line 371 and the step near line 432). Each build job's full `pytest` also runs it on two Linux hosts. So `test_file_facts_cost_the_same_on_every_run` runs on all three systems.
- EXECUTED (`out/utime_trace.out`): CPython's `open()` stats a new file (`fstat`) before the program writes it. So the file is first seen before its write, and the later `scandir` stat gets a new value only if the write moved the host's mtime.
- INFERRED: ext4 stamps from a coarse clock (Decision 6 says so), and NTFS from the system time. Whether a create and a write that follow each other land in one tick depends on timing. So the number of clock steps, the printed times and the fuel can differ between the check's two runs. F1's atime rule makes it worse on Linux, where `relatime` moves a tar-extracted file's atime (atime equal to mtime) on its first read.
- Decision 6 says fuel is compared only on darwin, but this check makes its own comparison on every host.

**Fix.** Either make the "same output, same fuel" assertion darwin-only (with a sentence in its docstring on why), keeping the host-independent assertions everywhere: eight distinct small numbers, the set time back as set, no file after the clock. Or write the program so no file is seen before its last change, for example by setting each file's times exactly before anything stats it. The driver's docstring should then say fuel repeats "on a host with fine file times", not "exactly".

### F4. A zero answer (stdio) is given an invented inode and time, and steps the clock. Low-medium; pass zeros through (EXECUTED)

- EXECUTED (`out/semantics.out`): `os.fstat` of fds 0, 1 and 2 on main's driver gives `ino` 0 and `mtime` 0 for each, as wasmtime answers for its stdio streams. The prototype gives `ino` 1 and `mtime` 1767225600000001000 for all three, and spends a clock step.
- A zero varies with no host, so rewriting it gains nothing. It also makes the judge show what the product never shows: a stream with an inode and a date.

**Fix.** Pass `ino` 0 through as 0, and a time of 0 through as 0, without a stamp or a step. Add it to the unit rows.

### F5. Spec 065 lands first in practice, and criterion 6 does not cover its CPython groups. Medium for the plan; write in (READ and EXECUTED)

- READ: 065 is built and in the lane. Its worktree carries uncommitted edits to the very files Decision 8 edits (`tests/known_gaps.toml`, `tests/upstream/python.toml`; `git status` in `wasi_python-065`). Its CPython groups (a, b, c, fs, archives) run through `harness.guest.run` and record fuel. Once 065 lands, they are accepted rows that this driver moves.
- EXECUTED: `cpython-fs` moves by −0.085% and its class takes a new digest ("What holds"). `cpython-archives` keeps its outcomes and falls by −0.009%. Groups a, b and c were not run here (a load average of about 75).
- Criterion 6 names only the 11 numpy and pandas rows, and Decision 7's table has no CPython group.

**Write in.** Build 083 after 065 lands, rebased on that main, so Decision 8 is unconditional. Criterion 6 then runs every CPython group too, five runs each: the same outcomes as accepted except the two `test_utime_current` ids, and the class's new match ("3 finding(s), digest e3d81bfc44e3" on this set; the build's own digest is the one written in). The groups' fuel moves belong in the landing notes' growth list. If 083 must land first instead, 065's lane carries Decision 8's three edits, and 065's landing notes say so.

### F6. The base is stale and the growth list is the draft's. Low; write in (READ)

Main has moved from `59b90b6` to `08de0c8` (specs 077 and 063; 063 changed `plugin.py`, `scan.py`, `shards.py` and `gather.py`). Spec 081 is still to merge, and so is 065. Decision 7's table and its 21 rows were measured on the old base. The spec already says the build re-measures. Make it explicit that the build rebases onto main first, and that the landing notes' `--accept-growth` list, measured there, replaces Decision 7's table. Decision 7's table is evidence of the draft, not the list the lane accepts.

### F7. The growth reason is a stated cause; give each row its two parts. Low; write in (EXECUTED, from `fuels.tsv`)

"Reshuffle" alone would not meet rule 5. But the spec does state the cause: the guest sees other values (small counted inodes, clock times), and the forward costs nothing. The author's own data lets each row be split into those two parts (`out/decompose.out`), in parts per ten thousand against accepted:

- `test_sqlite_job_matches_native`: times only +4.19; with inodes +7.76.
- `test_encodings_are_wasi_libcs_as_documented`: times only −1.46; with inodes +7.72.
- `test_the_guest_package_round_trips_through_the_door[snapshot]`: −0.23; +6.69.
- `test_fuel_is_exact_across_async_tool_calls`: +2.52; +5.60.

So the largest rises come from the inode's size: one 30-bit digit where the hashes took three. The 2**63 numbering equals times-only on 135 of 147 rows, and it moves 24 rows past the tolerance, against 21. So no numbering choice avoids an acceptance. Ask the landing notes to give, for each row in the growth list, the times-only value and the full value from the build's own runs. That makes the reason a cause per row. It needs no new runs beyond a times-only switch kept for the measurement.

### F8. The cut-entry rewrite does more than the spec says. Low; align (EXECUTED)

`FileFacts.listing` zeroes every byte of a cut header from offset 8: `d_ino`, and also `d_namlen` and `d_type` (`out/cut_listing.out`: cut 17 to 23 bytes into an entry changes `d_namlen` and `d_type`). Decision 3 and the unit row say only `d_ino` and the padding. Neither field varies with the host, and wasi-libc does not read a header it cannot read whole. Zero only the `d_ino` bytes and padding bytes that are present, as written, or say the larger rewrite. Similarly, `FILESTAT.pack` writes zeros into the 7 padding bytes after `filetype`, which wasmtime leaves as the guest's own bytes. That is harmless, but "only a successful answer is rewritten" should say it includes that padding.

### F9. Small design points. Low; write in (READ)

- **The trampoline cache by `id(engine)`.** An id can be reused after an engine is collected, and a module from a dead engine would then be handed to a new one. The spec says the build adds the own-engine rule. Compile per run for `own=`, or key by the engine object (a `WeakKeyDictionary`), not by its id.
- **A shadow called before `bind`.** It would raise `KeyError`, which becomes a trap. No guest here has a wasm start section, so nothing calls one that early today. One sentence and an assertion in `bind`'s caller would cover it.
- **Second granularity.** Every answered time lies in the second 1767225600 until a run has made a million clock calls. Anything that keeps whole seconds (a `.pyc`'s source mtime, a tar or zip member time, logging's rollover) sees every file in one second. The `cpython-fs` run shows no outcome change from it beyond Decision 8's. One sentence in Decision 2 would record it, so a later reader does not take it for a bug.
- **The real-metadata check.** It now proves "not the pin", which is its purpose. A stronger form under this driver would assert the driver's own answer (an `ino` below 2**30, a time after the clock's start and before `time.time()`). That proves the value came from a live call, not from a stale heap. Optional.

## Interplay

- **081.** A textual merge in `run()`'s signature and first lines, as Decision 9 says (READ: 081's `guest.py` diff is 75 lines, the guard and two parameters). 081's two lxml grant rows are the only ones left with a spread; after 081 they repeat. The new check passes host folders only as grants, never in argv or env, so 081's guard (which refuses host paths in a measured run's inputs) does not refuse it (INFERRED from 081's Decision 2 as its review describes it).
- **063** (landed). It changed the harness the judge runs in (shards, gather). Rebase first (F6).
- **065.** See F5. Its `clock_res_get` hunk and this spec's shadows touch different lines, and `patch` applied the prototype on 065's tip with one offset hunk (EXECUTED).

## Verdict

**Ready once F1 to F5 are written in.**

- F1, F2 and F4 are small changes to `FileFacts` and `_FileCalls.call`, each with a unit row.
- F3 decides how the new check behaves off darwin.
- F5 orders the build after 065 and widens criterion 6 to the CPython groups.
- F6 to F9 are wording and small code points the build can absorb.

The design is sound: forwarding keeps wasmtime's rules, errno values and traps; the measured spread falls from 35 rows to 2; and no check loses a product behaviour it was meant to see.

In one line: the shadows are right and hide nothing from the checks, but atime must stop following the host's reads, the forward must not run out of fuel at the edge, the new check must not compare runs on hosts with coarse times, and 065's groups belong in the criteria.

## Confirmation of the revision (2026-10-19)

- **Reviewed:** `spec/083-the-driver-answers-file-timestamps` at `3d03434`, rebased onto main `08de0c8`. I read the whole revised spec, its "Disposition of the pre-build review" section, and `revised/` (`prototype_revised.diff`, `times_only.diff` and the author's outputs). `guest.py` at `3d03434` is main's (EXECUTED: `diff` against `git show 08de0c8:tests/harness/guest.py`).
- **Ran (EXECUTED, same machine and the same frozen set, read only):**
  - Scratch copies of `3d03434`: `revmain/`, and `rev/` with `prototype.diff` and then `revised/prototype_revised.diff` applied. The revised diff is written against the first prototype, so it needs both. The revised shadow code is in `out/rev/revised_shadow_code.txt`.
  - My own F1, F2, F4 and F8 probes, unchanged, re-run on these copies. Outputs are in `out/rev/`.
  - One new probe, `probes/stat_padding.py`, for the filestat half of F8.
  - Nothing was written in any git tree.

### Each finding against the revision

- **F1, confirmed (EXECUTED, `out/rev/atime_grant.out`).**
  - The same granted file gives `…001000 …001000 …002000` on its first and second runs, read-only and writable. That holds even though the host's atime moved only in the first run. The fuel is 16,613,343 in every run.
  - In the code, atim is new only when mtim or ctim is new, or the guest set it.
  - The side effect Decision 2 records is real (`out/rev/semantics.out`). After `utime(ns=(5, 6))` and an append, the prototype answers atim with the write's clock value; main's driver answers 5.
  - I considered the alternative: atim is new only when the host's atim *also* moved. It would keep the 5. But it would let the host's read history back in whenever a read and a write fall between two stats. So the author's rule is the right trade, and it is written down.
  - The unit row `test_a_read_alone_moves_no_answered_time` and criterion 1 cover it.
- **F2, confirmed (EXECUTED, `out/rev/edges.out`).**
  - The 50-stat loop gives the same exit, trap and fuel on main's driver and on the revised prototype at every budget from full down to full − 15.
  - Both still exit 0 at full − 10, and both run out of fuel from full − 11, each spending exactly its budget.
  - errno values and traps are unchanged.
  - The fuel is raised to `min(before + 2**20, UNMETERED)` and set back in a `finally`.
  - The unit row `test_the_forward_never_runs_a_guest_out_of_fuel_early` and criteria 1 and 5 hold it.
- **F3, confirmed (READ).** Decision 6 limits "same output, same fuel" to darwin. It keeps the assertions that hold on any host everywhere, and says why a program no coarse host can perturb is not possible: CPython's `open()` stats a file before writing it, and a host `utime` moves ctime by the host's clock. The driver's docstring promise is narrowed to match (Decisions 6 and 9).
- **F4, confirmed (EXECUTED, `out/rev/semantics.out`).** `fstat` of fds 0 to 2 answers inode 0 and time 0 on the revised prototype, as on main's driver. In the code, a zero inode and all-zero times pass through with no clock step. The `FILE_FACTS` row stats fd 1.
- **F5, confirmed (READ).**
  - Status and "Depends on" now say the spec is built after 065 lands.
  - Decision 8 is unconditional, with the fallback stated.
  - Criterion 0 rebases after 065.
  - Criterion 6 runs every upstream group, 065's five CPython groups included, five times each, with the class's new digest and each group's fuel move in the landing notes.
- **F6, confirmed (READ).** The branch is rebased. Decision 7's table is marked as the draft's evidence, and the landing notes' list replaces it.
- **F7, confirmed (READ).** Decision 7 names the two measured causes and the decomposition. The landing notes give each growth row its accepted, times-only and full values, using `revised/times_only.diff` on a scratch copy, so the judge carries no switch. Decision 3's corrected reasoning is sound: the times alone push 21 to 24 rows past the tolerance, so an acceptance is needed whatever the numbering.
- **F8, confirmed for the listing; the filestat half is the build's (EXECUTED).**
  - Listing: `out/rev/cut_listing.out` shows a cut entry now changes only `d_ino` and the padding bytes that are present. Cuts 17 to 23 bytes into an entry no longer touch `d_namlen` or `d_type`.
  - Filestat: `out/rev/stat_padding.out` shows the revised prototype still writes all 7 padding bytes after `filetype`; main's driver writes none. It still packs the whole 64-byte struct.
  - The spec is consistent about this. Decision 1 says "never its padding", and the Design says "the build adds … field-only filestat writes (F8)". Only the Disposition's sentence "the code writes what the text says … (`revised/prototype_revised.diff`)" claims more than that diff does.
  - No named row checks the filestat padding. See the note below.
- **F9, confirmed (READ).**
  - The `id(engine)` cache is gone: the driver's own engine is cached, and `own=` compiles per run.
  - A shadow called before `bind` raises a named `RuntimeError`, and `run()` asserts the bind.
  - The one-second fact is in Decision 2.
  - Decision 5 declines the driver-values assertion with a sound reason: an artifact check should not depend on one judge's numbering.

### Notes for the build (not conditions)

- **N1, the filestat padding.** Write only `ino` (bytes 8 to 16) and the three times (bytes 40 to 64), as Decision 1 says. Let `FILE_FACTS` or a unit row show that a result buffer pre-filled with a marker keeps its 7 padding bytes. `probes/stat_padding.py` is that probe: it should give "0 of 7" on the build. Correct the Disposition's F8 sentence when the build lands.
- **N2, the set in criterion 7.** Criterion 7 names `s-c50ca51fae5eb55b-c9dcb5b8`, but criterion 0 rebases onto main after 065. If 065's landing freezes another set, judge against that one, and say which set in the landing notes.

### Verdict

**Confirmed for build.** F1, F2, F4 and the listing half of F8 are fixed in the revised prototype (EXECUTED). F3 and F5 to F9 are written into the text (READ). The filestat-padding half of F8 is assigned to the build in the Design; N1 asks for a row that proves it.

In one line: every finding is fixed or written in; the build must still write only the filestat's fields (N1) and judge against the set that is current after 065 (N2).

## The amendment of 2026-10-19 (the stdlib zip's link count), commit 17698ac

- **Read:** the spec's section "Amendment of 2026-10-19" (Decision 10, the new check, criteria 8 and 9, the note on Decision 4), and `amendment/` (`nlink_fuel`, `link_during_run`, `copy_cost`, `runner_links`, with their outputs). I also read the driver's `_place`, `run()`, `Turns.close`, and the `guest_workdir` fixture (`tests/checks/conftest.py:61-65`). I grepped `tests/` for every use of the run's `lib` folder, of `st_nlink`, and of the set's zip by its host path.
- **Ran (EXECUTED, `out/amend/nlink_fuel.out`):** the author's `nlink_fuel.py`, unchanged, on my scratch copies.
  - Main's driver at 3d03434: the guest sees `nlink` 2 against 1,104, and fuel moves +300 and +521.
  - The revised prototype with the zip still linked: the same.
  - With `_place` copying: `nlink` 1 at both counts, and +0 on both programs.
  - This matches the author's `amendment/nlink_fuel.out` to the instruction. The probe removed its folder and its 1,100 links at exit.

**1. Does copying hide anything a check is meant to see? No (READ).**
- No check reads the run's `lib` folder. The only uses of it are in the driver itself (`guest.py` lines 192 and 363). `upstream.py:731` removes `r.root.parent` whole, which suits the change.
- The read-only and shared properties of the zip are checked on the product runner (`test_the_zip_is_read_only_and_shared`, the `wasi_python.run` child), which this spec does not touch.
- The guest sees the same path (`/usr/local/lib/python315.zip`), the same bytes and the same read-only grant. Its inode number was already the driver's count (Decision 3).
- So spec 041's reads by path, and the zip-directory checks, see what they saw before.
- The only `st_nlink` a check asserts is a directory's (`/w`, in the real-metadata check), which is compared with the host's own answer. That is unaffected.
- `mpl_data_dir` keys and extracts from the set's own zip, not from the run's copy, so it is unaffected.
- One gain: a guest that broke the read-only grant could, until now, write the set's own zip through the hard link. A copy keeps the set's bytes safe from every judge run.

**2. Removal on a failed or killed run, and on Windows.**
- A failed run: Decision 10 removes the copy in a `finally`, and `guest_workdir`'s teardown removes the rest. A killed run (SIGKILL, or a timeout that kills the process) leaves its copy behind. That costs disk only. A leftover copy is a file no other run links or reads, so it cannot move anyone's fuel. The leftover *links* of the old design were the hazard, and this removes them. (INFERRED.)
- **A1, Windows.** `run()` would remove `lib` while the run's `wt.Store` still holds wasmtime's open handles (the read-only preopen of `lib`, and any zip handle the guest kept). Rust opens files and directories on Windows with delete sharing (READ: wasmtime's `filesystem/windows.rs`, the reopen comment near line 52). That makes the unlink likely to succeed, but whether the directory itself can be removed while its handle is open depends on the Windows version and the file system. The spec should say:
  - close the store first (`store.close()`, as `Turns.close` already does), then remove;
  - remove with errors ignored (`shutil.rmtree(lib, ignore_errors=True)`);
  - so a removal can never fail or change a run. The release's `verify` job on `windows-2025` is where this would show. (INFERRED; not run here.)

**3. The new check.**
- It fails on main (EXECUTED above). Main's driver prints `nlink` 2 against 1,104 and spends +521. It passes with the copy: `nlink` 1 both times, +0.
- It never links the set's own zip, and it removes its links in a `finally`, so it perturbs no other run. 1,101 crosses the 1,017-to-1,023 point that 081's bisection found. It is sound.
- **A2, Windows.** NTFS allows at most 1,024 hard links to one file. `os.link` fails beyond that with `ERROR_TOO_MANY_LINKS` (READ: the documented NTFS limit). The check is in `tests/checks/test_v1_4_embedding.py`, which the `verify` job runs on `windows-2025`. As written, it would error there at about the 1,023rd link.
  - Fix: use fewer links on Windows (for example 1,000, still asserting `nlink` 1 and the same output), or skip the extra links there with the reason given.
  - Keep 1,101 on darwin and Linux (ext4 allows 65,000). By Decision 6, fuel equality is asserted on darwin only anyway.

**4. The cost.**
- About 2,000 runs at 10 to 16 ms is roughly 30 s serial, and about 5 s at `-n 6`. That is under 6% of a 9-minute judge. It is worth paying for a hidden input removed from every row.
- It does not need to be an operation count. It is not a check's metric, and "tests count operations, never wall-clock" is kept by recording it only in the memo as a benchmark fact, as the amendment does.
- Optional, not a condition: on APFS a clone (`clonefile`, as `cp -c` does) gives the same thing, its own inode with `nlink` 1, at about the cost of a link. A plain copy as the fallback keeps every host correct.

**Verdict on the amendment: confirmed once A1 and A2 are written in.** A1: close the store before removing `lib`, and ignore removal errors. A2: the new check stays under NTFS's limit of 1,024 links on Windows. Both are wording plus a line of code each. The design itself is right: copying removes the link-count input at its source, and keeps a guest's own hard links true.
