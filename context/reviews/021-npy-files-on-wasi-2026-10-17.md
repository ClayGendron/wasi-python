# Review of 021 — `.npy` files on WASI: the first carried patch (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change. I did not write the
  specification's pre-build review or its confirmation. I read `AGENTS.md`, the constitution
  (§4.1 as amended, §4.9, §4.10, §5.5, §5.6, §7), the 020 build review (for the format),
  specification 021 with its landing notes, its pre-build review with the confirmation,
  specification 020's rules, `context/upstream/3-numpy-npy-wasi/` (`fix.patch`, `pr.md`,
  `notes.md`), numpy 2.5.2's `numpy/lib/_format_impl.py` and `doc/source/dev/ai_policy.rst`
  (from the pinned tarball), `recipes/reactor_main.c`, and the diff. I did not rely on the
  landing notes. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** the scratch clone's `git diff 380f70d 43f2a98` (one commit, nine files): the
  patch `recipes/patches/numpy-2.5.2/0001-npy-files-without-dup.patch` (new), its draft
  `context/upstream/patches/numpy-2.5.2/0001-npy-files-without-dup.md` (new),
  `tests/checks/test_v1_3_data_stack.py` (`test_npy_files_round_trip`), `README.md`,
  `CHANGELOG.md`, `context/upstream/README.md`, `recipes/patches/README.md`, the research memo's
  status, and the specification.
- **Re-ran (EXECUTED, darwin-arm64; the clone's own `build/`; the main tree's `build/artifacts`
  copied read only).** Probes and outputs are under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev021b/`
  (`scripts/`, `out/`):
  - `p1_apply.sh`: the pinned tarball's hash, a fresh extraction, the clone's applier on it, the
    added lines against `fix.patch`, and `diff -r` of the result against `build/numpy-2.5.2`
    (`out/p1.txt`). `p1_rules.py`: `scan.patch_errors`, `patch_shape_errors` and `tree_drift`
    for numpy, pandas and CPython (`out/p1-rules.txt`). `p1_neg.py`: `tree_drift` on an
    unpatched extraction (`out/p1-neg.txt`).
  - `p2_zip.py`, `p2_pyc.py`: the two stdlib zips member by member, and the changed `.pyc`
    (`out/p2-*.txt`); `cmp`/`shasum` of both sets (`out/p2-sets.txt`).
  - `uv run pytest -p no:cacheprovider tests/checks/test_v1_3_data_stack.py -k npy` with
    `WASI_PYTHON_ARTIFACTS` at a copy of each set (`out/p3-check.txt`, `out/p3-mutants.txt`).
  - `mkset.sh`: steps 70 and 80's exact commands, into scratch, from a copy of
    `build/numpy-install`'s site tree. A control run, and three mutants made by `mutate.py`
    (`out/mut-*.txt`).
  - `probe_guest.py`: the check's program and a README probe through the judge's own driver, on
    both binaries of five sets (`out/guest/`). `fuel.py`, `jobfuel.py`: fuel of short programs
    and of the grown jobs on four sets, each short program run twice (`out/fuel.txt`,
    `out/jobfuel.txt`).
  - `uv run pytest -p no:cacheprovider` in the clone (`out/pytest-full.txt`), and `grew.py`
    listing every metric that moved against `context/progress/accepted.json` (`out/grew.txt`).
  - `uv run ruff check src tests` and `uv run ruff format --check src tests` (`out/ruff.txt`).
  - A scratch clone of the main tree (`merge/`), the build commit cherry-picked onto it with
    `--no-commit`, and `patch_errors` there.
  - I did not pass `--accept`. I committed and pushed nothing, and added no remote. I rebuilt no
    step in the clone: the mutants were built in scratch. The full judge run overwrote the clone's
    `build/progress/latest.json`; I restored it from a copy (sha256 `96aee216…`, as found). A
    probe left `build/harness/rev021b/` in the clone for one run; I removed it. The clone's
    `git status` is empty, at `43f2a98`, as I found it. In the main tree I wrote nothing.
  - One slip: `mutate.py` was run once with a bare `python3 -I` on scratch files, not through
    `uv run`. It only edits a scratch copy of one file; the diffs are in `out/mut-build.txt`.

## The patch

- **It applies cleanly, with no offset (EXECUTED, `out/p1.txt`).** The tarball's sha256 equals
  its pin (`d482d171…`). On a fresh extraction, the clone's applier prints "Applied patch
  numpy/lib/_format_impl.py cleanly", the same for `test_format.py`, then `applied
  0001-npy-files-without-dup.patch`; exit 0; no offset line. Both files keep their tarball mtime
  (1786234431 before and after).
- **Its added lines are `fix.patch`'s (EXECUTED).** 21 added lines in each; the files are equal
  by `cmp`, and per file by sha256 (`b91071c6…` for `_format_impl.py`, `d28b7317…` for
  `test_format.py`). It removes no line. The `index` lines name the real 2.5.2 blobs: `git
  hash-object` gives `51b16ce` and `13429e9` for the tarball's files, `d6686ea` and `c4e3690`
  for the patched ones.
- **It passes every spec 020 rule (EXECUTED).** `scan.patch_errors` on the clone gives `[]`;
  `patch_shape_errors` gives `[]` with the touched set `{numpy/lib/_format_impl.py,
  numpy/lib/tests/test_format.py}`. The file is mode 100644, `-text`, `eol: lf` (`git
  check-attr`). The same `[]` on the main tree with the commit cherry-picked onto it.
- **The built tree is the tarball plus the patch (EXECUTED).** `diff -r` of the fresh patched
  extraction against `build/numpy-2.5.2`: no output, exit 0. `tree_drift` on the built tree:
  `[]` (numpy, pandas and CPython). On an unpatched extraction it gives
  `['numpy/lib/_format_impl.py: modified', 'numpy/lib/tests/test_format.py: modified']`, so the
  v1.5 check sees a missing patch. Step 40's log begins with the applier's five lines (READ).
- **`import sys` is new in 2.5.2's file (READ).** The module imports `io`, `os`, `pickle`,
  `warnings` before it; the added `import sys` is not a duplicate.
- **`isfileobj` gates four call sites (READ).** `write_array` (lines 764 and 771),
  `read_array` (847) and `open_memmap` (948). The fourth is the side effect `pr.md` already names:
  `open_memmap(file_object)` now raises `TypeError`, not `ValueError` (EXECUTED, below).

## The artifact set

EXECUTED (`out/p2-*.txt`), the clone's `build/artifacts` against the main tree's (fcf1715):

- `python.wasm`: byte for byte the same (31,760,992 bytes, `4befe9de…`). The twelve
  `LICENSES/*.txt` are the same.
- `python-stdlib.zip`: 11,140,578 → 11,140,635 bytes (+57). The same 1,751 names in the same
  order, the same per-member metadata and the same comment. One member's bytes differ:
  `numpy/lib/_format_impl.pyc`, 36,040 → 36,140 bytes, compressed 15,440 → 15,497. Both `.pyc`
  files are hash-based (flags 1); the clone's holds the constant `wasi`, the main tree's does not.
- `python-snapshot.wasm`: 65,506,914 → 65,506,824 bytes (−90), `a7a0a4a8…` → `c7302cfd…`.
- `MANIFEST`: three lines differ. `recipes/patches/README.md`'s hash, a new `recipe` line for the
  patch, and `x-snapshot-zip`. Each recipe hash equals the file at `43f2a98` (`shasum`).
  `SHA256SUMS` differs in `MANIFEST`, the snapshot and the zip only.
- Steps 70 and 80 re-run in scratch from a copy of the clone's numpy site tree give the clone's
  zip and snapshot byte for byte (`1add57e4…`, `c7302cfd…`; `out/mut-control.txt`). So the set is
  reproducible from the tree, and the mutants below differ only in the file I changed.
- The build ran after the patch was written: the patch file is 13:36:43; logs 00 to 90 run from
  13:37:31 to 13:43:27 (READ, `ls -lT`).

## The check `test_npy_files_round_trip`

- **Fails on the main tree's set, passes on the clone's (EXECUTED, `out/p3-check.txt`).** Main
  set: both cases fail, `AssertionError: plain OSError 58`. Clone set: both pass. The full output
  of the program on the main set (`out/guest/main-snapshot-npy.txt`): `OSError 58` for plain,
  record, 0-d, Fortran, large, empty and two; `True` for object and npz. That is criterion 1's
  seven of nine.
- **It fails on three mutants (EXECUTED, `out/p3-mutants.txt`).** Each was built into a set in
  scratch by steps 70 and 80:
  - A: the `sys.platform` block removed (`import sys` kept). Both cases fail.
  - B: the block skipped for `io.BufferedReader` (saving works, loading fails). Both fail; the
    program prints `OSError 58` because the save and the load share one `try`.
  - C: the block skipped for `io.BufferedWriter` (saving fails). Both fail.
  - The control set (no change) passes both.
- **The equality is sound for these cases (READ, EXECUTED).** `same()` compares `dtype` (which
  includes byte order, field names and offsets), `shape`, `tolist()` (values) and
  `flags.f_contiguous` (so a C array read back as Fortran is caught). No case holds a NaN, so
  `tolist()` equality is exact. It does not compare the file's bytes with an in-memory save; my
  probe did, for 20 MB through an unbuffered file, and they are equal (below).
- **The large case runs the read loop twice (READ).** `BUFFER_SIZE` is `2**18`;
  `max_read_count` for `float64` is 32,768 items; the case has 40,000.
- **It counts, never times (READ).** It asserts the exit code and the exact text, and records
  fuel through the `guest` fixture. No clock. `scan.clock_hits` runs in the rules goal, which
  passes.
- **The new paths the patch opens work (EXECUTED, `out/guest/clone-*-readme.txt`, both
  binaries).** `np.save` to a `pathlib.Path`; a 20 MB array (more than `write_array`'s 16 MiB
  buffer) through `open(…, "wb", buffering=0)`, a raw `io.FileIO`, whose `write` the chunked path
  calls without a loop: the file is 20,000,128 bytes, loads back equal, and its bytes equal an
  in-memory save's; `np.load` of an `r+b` handle. INFERRED: wasmtime writes a regular file's
  `fd_write` whole, so no short write was seen; nothing guarantees that in WASI.

## The draft and the docs

- **The draft's link resolves (EXECUTED).** `../../3-numpy-npy-wasi/pr.md` from
  `context/upstream/patches/numpy-2.5.2/` is `context/upstream/3-numpy-npy-wasi/pr.md`, present.
  The six header lines pass the rules (above). Its three clauses are in the 2.5.2
  `ai_policy.rst`, under "Disclosure", "Code Quality" and "Copyright" (READ; finding 6 on two
  words).
- **The README's words are true (EXECUTED, both binaries, the clone's set).** `ndarray.tofile`
  and `np.fromfile` on a real file still fail, by path and by open handle: `OSError 58`.
  `np.load(…, mmap_mode="r")` and `np.memmap`: `OSError: mmap is unavailable on wasm32-wasi`.
  `tobytes()`/`np.frombuffer` and `io.BytesIO` work. `np.save`/`np.load` of paths and open files
  work. `open_memmap` of a handle: `TypeError` (the main set: `ValueError`), as `pr.md` says.
- **The CHANGELOG names the patch's path (READ, EXECUTED).** Its 0.1.0a3 entry has
  `recipes/patches/numpy-2.5.2/0001-npy-files-without-dup.patch`, which the rule requires.
- **README count and lead-in (READ).** `upstream patches carried: 1`; the lead-in has "(with one
  carried patch, below)"; the platform paragraph is where Decision 6 says. Finding 5 on one word
  of the row.
- **The memo (READ).** Its status line changed; its body did not (finding 2).
- **The commit lands on today's main (EXECUTED).** Main is now at `7968e79` (022 accepted, 023
  drafted). The build commit cherry-picks onto it with no conflict (`CHANGELOG.md` and
  `README.md` auto-merge); `patch_errors` is `[]` there.

## The fuel growth

The judge in the clone (EXECUTED, `out/pytest-full.txt`): `181/185 pass · 0 gap · 4 blocked · 0
fail (unit suite 445/452, 7 skipped)`; `626 passed, 11 skipped`; ratchet vs `408f3c0aa4`: `lost 0
· absent 0 · unrun 0 · unrun locally 2 · gained 2 · grew 18 · judge changed:
tests/checks/test_v1_3_data_stack.py`; `RED: 18 metric(s) grew`; exit 1. `gained 2` is the new
check, both binaries. ruff check and format: clean (`out/ruff.txt`).

The 18, from `out/grew.txt` (43 metrics moved; the rest stayed inside the tolerance or fell):

| what grew | how many | change |
|---|---|---|
| the zip's bytes | 1 | +57 bytes |
| snapshot checks, short programs | 13 | +23,242 to +50,374 fuel (+0.028% to +0.061%) |
| `test_extra_preopens_work_on_the_snapshot[*]` (snapshot) | 2 | +673,567 each (+0.080%) |
| `test_numpy_csv_job_matches_native` (plain) | 1 | +751,975 (+0.015%) |
| `test_random_matches_native` (plain) | 1 | +1,275,391 (+0.026%) |

So five of the 18 are not "about 34,000 per snapshot run" (finding 1). Are they the one changed
module? Yes, as far as I can test, and not through what the patch does:

- **None of these programs calls `isfileobj` (READ).** The golden jobs use `loadtxt`/`savetxt`;
  the preopen probe opens text files and walks `gc.get_objects()`.
- **A functionally stock module moves them as much (EXECUTED, `out/fuel.txt`,
  `out/jobfuel.txt`).** Mutant A has the patch's logic removed (only `import sys` differs from
  the tarball's file). Against the main set: snapshot `-c pass` +58,250 (the clone: +24,185);
  the preopen probe +722,867 (clone +673,567); `numpy_csv` +187,407 (clone +751,975);
  `numpy_random` +264,997 (clone +1,275,357). Mutant C: +106,343, +74,848, +993,279, +483,014.
  The moves are not monotone in the change. They come from where the module's objects land, not
  from what its code does.
- **The fuel is repeatable (EXECUTED).** Each short program ran twice per set with the same fuel.
  My `numpy_csv` on the main set is 17 fuel from the accepted number.
- **The plain binary's start is unchanged (EXECUTED).** Plain `-c pass` is +810 fuel on every
  run that does not import numpy; `import numpy` is +61,982 (the bigger `.pyc` unmarshalled and
  run).

**Where the snapshot's constant cost is (EXECUTED, then INFERRED).** On the snapshot, `-c pass`
costs 81,938,099 (main) against 81,962,284 (clone): +24,185. `-c "import os; os._exit(0)"`, which
leaves before `Py_FinalizeEx`, costs 2,658,123 against 2,657,382: −741. So the extra cost is
inside the interpreter's finalization at the end of `run()` (`recipes/reactor_main.c`), not in
start-up or in the program. INFERRED: finalization tears down the whole pre-imported heap (numpy
and pandas), and its cost depends on the heap's layout. One module's objects of a different size
shift that layout, so every snapshot run moves by a constant. A fact for a later memo, not for
this spec: finalization is about 79.3M of the 81.9M fuel of a snapshot `-c pass`, 97% (EXECUTED,
the same two numbers).

## Acceptance criteria against evidence

1. *The check exists and was seen failing with `OSError` 58 for seven of nine.* **Met**
   (EXECUTED, above).
2. *A full build from pins applies the patch at step 40; `python.wasm` equal; the zip differs only
   in the `.pyc`.* **Met** (EXECUTED: the set, the logs, the control rebuild). The build was in
   spec 020's reused clone with a full `scripts/build.sh` run, not a fresh clone (READ, the
   landing notes and log times); `diff -r` and `tree_drift` show its numpy tree is exactly the
   tarball plus the patch.
3. *Green with `--accept`, `--accept-judge`, `--accept-growth`.* **Not yet.** Exit 1 with 18
   grown, as expected. The growth reason the criterion and the notes give does not describe the
   18 (finding 1). It must be re-run on the rebased tree.
4. *A release dry run passes every job, with the arm64 Linux same-bytes rebuild.* **Not shown**
   (finding 3).

## Findings, most severe first

1. **Medium. The growth is described wrongly, and that text is about to go into the append-only
   history.** (Landing notes, "The judge"; criterion 3's `--accept-growth` reason; Decision 4)
   - The defect. The notes say the 18 are "the zip's bytes (+57) and the fuel of the snapshot
     checks, by about 34,000 instructions each (+0.04%)". Criterion 3's reason says "snapshot
     fuel about +24k per run". Decision 4 says "the plain binary moves less".
   - Failure. EXECUTED (`out/grew.txt`): 13 snapshot checks grew by +23,242 to +50,374. Two more
     snapshot checks grew by +673,567 each. Two plain-binary golden jobs grew past the tolerance:
     +751,975 and +1,275,391. Accepted with the planned reason, the history would say "+24k per
     snapshot run" next to growths 28 to 53 times that, two of them on the plain binary. A later
     reviewer who sees a golden job grow by a million could not tell this cause from a real
     regression, and rule 5's "accept growth with a stated reason" loses its point.
   - Fix. On the rebased tree, re-run the judge and write the reason from what it lists: "one
     carried `.pyc` (+100 bytes): zip +57 bytes; snapshot runs +23k to +50k fuel, in
     finalization; the snapshot preopen probe +0.67M and two plain golden jobs +0.75M and +1.3M,
     from heap layout (a mutant with the patch's logic removed moves them as much)". Put the same
     numbers in the landing notes, with the cause traced (finalization, EXECUTED above), and
     correct Decision 4's last sentence. The judge itself needs no change.

2. **Low. The research memo's body now says the opposite of what was built.**
   (`context/research/2026-10-17-numpy-npy-files-need-dup.md`)
   - The defect. Only the status line changed. "Why it is not fixed here" says patching numpy
     "would break a hard rule … (zero patches)". "Feeds" and "What it decides" say the judge
     records a known gap closed by this memo, and that the README names the workaround. "One
     line" says the fix is numpy's and the judge names the gap. The pre-build review's finding 4
     named this section too.
   - Failure. READ: `tests/known_gaps.toml` has no `.npy` entry; the check is a guard; §4.1 now
     allows the patch. A reader who opens the memo from the CHANGELOG learns the opposite.
   - Fix. One dated line under the status: "Superseded in part, 2026-10-17: §4.1 as amended
     allows a carried patch; spec 021 carries the fix, and `test_npy_files_round_trip` guards it
     (no known gap). 'Why it is not fixed here', 'What it decides' and 'One line' describe the
     state before." The memo stays a record.

3. **Low. Criterion 4, the release dry run, is not reported.** (Landing notes)
   - The defect. This is the first build whose zip holds a file that `git apply` changed. The
     arm64 Linux same-bytes rebuild is the one place a host difference in the applier would
     show.
   - Failure. None seen. INFERRED low risk: the 020 review ran the applier on Debian dash with
     git 2.47 and got the same tree hash; the `.pyc` is hash-based and compiled with
     `PYTHONHASHSEED=0`.
   - Fix. Run the dry run before landing and cite it, or say in the landing notes that it is
     pending and which run will show it.

4. **Low. The commit is built on `380f70d`; main is at `7968e79`.**
   - EXECUTED: it cherry-picks cleanly and the rules pass there. But `accepted.json` on main
     carries spec 022's numbers, and AGENTS.md rule 9 asks that a commit on main be green on its
     own.
   - Fix. Land it on main's head, re-run `uv run pytest` there, and accept from that run
     (finding 1's numbers come from it).

5. **Low. The README row says "each with an upstream pull request" while the one pull request
   is only drafted.** (`README.md` line 41; spec 020's wording)
   - With a count of 1 this now reads as "a pull request exists". READ: the rule's regex reads
     only the count.
   - Fix. "each with an upstream pull request drafted or sent". Or leave it and answer in
     writing that "pull request" means the draft.

6. **Low. Two points for the owner's facts, outside the diff.** (`pr.md`; the draft's body)
   - `numpy.lib.format` re-exports `isfileobj` (READ, `numpy/lib/format.py:14`). On WASI the
     public helper now answers `False` for a real file (EXECUTED: `True` → `False`). `pr.md`
     names the `open_memmap` side effect but not this. Its "move the check to the three data call
     sites" alternative would avoid both.
   - The draft gives the Copyright clause as "the submitter must own the code's copyright". The
     policy also allows including the code's BSD-compatible licence. And it leaves out
     "Responsibility" ("You must understand and be able to explain the code you submit"), which
     `pr.md` covers in one clause. Fix: one sentence each in `pr.md` or the draft; no rule
     changes.

## Constitution checks

- §4.1: the patch is recorded in `MANIFEST` by hash, named in the CHANGELOG, paired with a
  draft, applied after the hash check, and the tree is exactly the tarball plus it (EXECUTED). It
  meets "a recipe file first" by Decision 2's reasoning (READ). Deleted once numpy releases it:
  the draft says so.
- §4.2: the tarball's hash equals its pin (EXECUTED).
- §4.3: `sys.platform == "wasi"` is numpy's own target test, not a host branch in the build.
- §4.4: `python.wasm` is byte for byte unchanged (EXECUTED), so its imports are too.
- §4.5: `patch_errors` and the rules goal pass, including the drafts' embedder scan (EXECUTED).
- §4.6: the set keeps its members; the zip, the snapshot, `MANIFEST` and `SHA256SUMS` change.
- §4.9: the check asserts outputs and records fuel; no clock (READ).
- §4.10: the landing notes label their claims, but the growth claim is wrong (finding 1).
- §4.15: `allow_pickle` stays `False` by default; the check passes it for the object array only
  (READ).
- §5.6: the CHANGELOG says the next security review reads the patch (READ).
- §7: nothing tripped. No source tree changed by hand; nothing sent upstream; no commit, push or
  tag by me.

## Disposition (filled in by the author, then confirmed by the reviewer)

All six findings are fixed or answered, on main's head (`1299ae2` amended, on `7968e79`).

1. **Fixed.** The judge was re-run on main with main's set rebuilt from step 40; it lists the
   same 18 as this review (`numpy_csv` +751,958 there). The landing notes' *The judge* gives the
   table, the cause (finalization; a mutant without the patch's logic moves them as much) and
   the plain binary's two jobs. Decision 4's last sentences now say the build found more, and
   criterion 3's reason points at that account. The `--accept-growth` reason is written from it.
2. **Fixed.** The memo has a dated "Superseded in part" line naming the three sections.
3. **Answered.** The dry run needs the push; the landing notes say it is pending, and its run is
   cited in the acceptance's record when it finishes.
4. **Fixed.** The commit sits on main's head; the judge above ran there, against `3843181`'s
   accepted state (spec 022's numbers).
5. **Fixed.** The README row reads "each with an upstream pull request drafted for the owner to
   send".
6. **Fixed.** The draft names `numpy.lib.format.isfileobj`'s new answer on WASI, the policy's
   "Responsibility" clause, and words "Copyright" as the policy does.

## Verdict

Lands once finding 1 is fixed: the patch is exactly `fix.patch`'s added lines, applies cleanly,
the tree is the tarball plus it, `python.wasm` is unchanged, the zip changes in one `.pyc`, and the
check fails on the old set and on three mutants and passes on the new one. Finding 1 is a written
fix: correct the growth account and the `--accept-growth` reason, from a judge run on main's
head (finding 4). Findings 2, 3, 5 and 6 are small and can go in the same pass.

One line: the code is right and well guarded; the account of what it costs the judge is not yet,
and it must be right before it goes into the history.

## Confirmation

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5); not the author, and not the reviewer above.
- **Reviewed:** the Disposition above; the commit `1299ae2` (parent `7968e79`, main's head before
  it); the uncommitted edits to the specification (`git diff`); the memo, the README row and the
  draft as they stand in `1299ae2`; numpy 2.5.2's `doc/source/dev/ai_policy.rst`, from the
  pinned tarball.
- **Ran (EXECUTED, darwin-arm64, main tree).** Outputs are under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/conf021/`:
  `grew.py` on `context/progress/accepted.json` against `build/progress/latest.json` →
  `grew.txt`; `uv run ruff check src tests` and `ruff format --check src tests` → `ruff.txt`;
  `uv run pytest -p no:cacheprovider -m "not slow" -q` → `pytest.txt`, and `grew.py` on its
  scoreboard → `grew-mine.txt`. I did not pass `--accept`. I copied `build/progress/latest.json`
  before the run and restored it after (sha256 `75962cc2…`, as found). `git status` is as I found
  it. I wrote nothing in the repo but this section.

### Each disposition against its finding

1. **The growth account: closed.** EXECUTED. `grew.py` on main's scoreboard (commit `1299ae2`,
   ratchet vs `3843181e63`, the accepted state) lists 43 moved, 18 grown. They match the
   specification's table row for row: the zip +57 bytes; 13 snapshot short programs, +23,242
   (`test_run_returns_the_exit_code`) to +50,374 (`test_door_round_trips_bytes_through_a_host`),
   +0.0283% to +0.0611%; the two preopen probes +673,567 each (+0.0795%); `numpy_csv` +751,958
   (+0.0150%); `random` +1,275,391 (+0.0255%). The judge line in the landing notes (184/186, 2
   blocked, 649 passed, 4 skipped, lost 0, gained 2, grew 18) matches `build/judge021.txt`.
   My own `not slow` run grew the same 16 non-golden metrics by the same numbers, to the
   instruction, and passed `test_npy_files_round_trip` on both binaries. READ: step 40's log
   (14:07, after the commit at 14:06) begins with `applied 0001-npy-files-without-dup.patch`.
   Criterion 3 now points at the landing notes' account. Decision 4 no longer says "the plain
   binary moves less". It keeps the pre-build "about 24,000 more" sentence, then says at once that
   the build found 18, two on the plain binary, with the cost in finalization. That reads as the
   measured prediction and its correction, which is fair.
2. **The memo: closed.** READ. It has a dated "Superseded in part (2026-10-17)" line naming "Why
   it is not fixed here", "What it decides" and "One line". Nit (A, below): its "Feeds" line still
   says "a known gap in the judge (`test_npy_files_round_trip`)", which finding 2 also named.
3. **The dry run: closed as answered.** READ. The landing notes' *Release dry run* says it is
   pending, which run will show it (the one after this push, arm64 Linux same-bytes included),
   and where its result will be recorded.
4. **On main's head: closed.** EXECUTED. `1299ae2`'s parent is `7968e79`; the judge ran there,
   against `3843181`'s accepted state, with the set rebuilt from step 40 on this tree (v1.5 18/18,
   so `MANIFEST` matches the tree).
5. **The README row: closed.** READ. Line 41: "upstream patches carried: 1, each with an upstream
   pull request drafted for the owner to send".
6. **The draft: closed.** READ. It says the public `numpy.lib.format.isfileobj` now returns False
   on WASI for real files. It names "Responsibility". It words "Copyright" as holding the right to
   submit under numpy's licence, which covers the policy's two ways (own the copyright, or include
   a BSD-3-compatible licence). Nit (B, below) on "Responsibility".

### The judge

- `uv run ruff check src tests`: all checks passed. `ruff format --check`: 53 files already
  formatted.
- `uv run pytest -p no:cacheprovider -m "not slow" -q`: exit 1, as expected before acceptance.
  178/186 with 6 deselected, 0 fail; 643 passed, 4 skipped; ratchet lost 0, gained 2, grew 16
  (the 18 less the two golden jobs, which are `slow`), judge changed:
  `tests/checks/test_v1_3_data_stack.py`. The red line is the growth that criterion 3 accepts
  with `--accept-growth`, nothing else.

### New gaps (nits; none blocks landing)

- **A. The memo's "Feeds" line** still says the judge records a known gap closed by this memo.
  `tests/known_gaps.toml` has none; the check is a guard. Add "Feeds" to the superseded line, or
  "(no known gap; the check guards the fix)".
- **B. The draft's "Responsibility"** is given as "answers for the change as their own". The
  policy's operative words are "You must understand and be able to explain the code you submit".
  Worth quoting, since an agent wrote all of it.
- **C. Decision 3** still says the draft names "the policy's three clauses"; it now names four.

### Verdict

**Lands.** All six findings are closed, five fixed and one (the dry run) answered in writing. The
growth table equals the scoreboard exactly, and the account behind `--accept-growth` is now true.

One line: the account of the cost now matches the judge to the instruction; accept with it.

### The confirmation's notes, answered by the author

All three fixed before landing: the memo's "Feeds" line names the carried patch and its guard;
Decision 3 names the four clauses; the draft quotes "must understand and be able to explain".
