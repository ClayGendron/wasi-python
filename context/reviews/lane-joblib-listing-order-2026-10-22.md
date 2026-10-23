# Review of the lane's judge change: joblib's cross-version mmap test in either listing order

- **Date:** 2026-10-22
- **Reviewer:** a fresh agent (Claude Opus 5.5); not the author (the lane)
- **Reviewed:** 42798898 on local `main` (parent cb5f4707): `tests/upstream/joblib.toml` (+6 -1), `tests/unit/test_upstream.py` (+11)
- **Run:** none dispatched. The caller limited this review to local single node ids. The run that found the failure is dry run 39764234616 (on deb18923), job "judge the release tier (ubuntu-24.04, upstream-pure-r-112)", its log read at `build/wave-12/dryrun2/r112.log`.
- **Time box:** 25 minutes (a judge-only change)
- **Re-ran (on HEAD 42798898, no `build/lane.lock`):**
  - `uv run pytest -q -p no:cacheprovider tests/unit/test_upstream.py` → 85 passed, exit 0
  - the new row run from a scratchpad script against the parent's `joblib.toml` (cb5f4707) → fails on `AssertionError: assert False` with the finding "unexpected failed …test_joblib_pickle_across_python_versions_with_mmap — AssertionError: assert False"; the same script against HEAD's `joblib.toml` → passes
  - `uv run pytest --tier=release "…::test_upstream_suite[joblib-r]" "…::test_upstream_class[joblib-r-no-mmap]"` → 1 passed, 1 xfailed, exit 0, 21.9 s (darwin-arm64)
  - `ruff check` and `ruff format --check` on `tests/unit/test_upstream.py` → clean

## Acceptance criteria against evidence
1. The diagnosis holds. Met (READ/INFERRED). `test_joblib_pickle_across_python_versions_with_mmap` builds its list from `os.listdir(test_data_dir)`, keeps the `.pkl` files and calls `_check_pickle(fname, expected_list, mmap_mode="r")` on each, unsorted (test source lines 577-597). `_check_pickle` catches any exception. For a file named `py2x` it runs `assert isinstance(exc, ValueError)`; for a `py3x` file that is not `.lz4` it re-raises (lines 523-535). So the first file listed decides the message: `OSError: mmap is unavailable on wasm32-wasi` for a Python 3 pickle, `AssertionError: assert False` for a Python 2 pickle. The data folder holds 10 `.pkl` files, 3 of them `py27`. That fits the evidence. Today's darwin stream (`build/harness/streams/joblib-joblib-r.txt`) shows the OSError reason. The Linux log shows the assertion. Dry run 1 passed joblib-r on Linux. The folder holds 67 entries, so on ext4 it is most likely a hashed (htree) directory. Its order then follows the file system's hash seed, which is set per file system, not by the file names alone. The lane's guest probe (all ten files raise the mmap OSError) is cited, not re-run here. Its result matches the reading of the source: `numpy_pickle.load` reaches mmap before it can tell a Python 2 pickle by its `ValueError`. I see no other account that fits both dry runs on the same artifact set. An `.lz4` or protocol branch cannot apply, because only `.pkl` files are listed and every writing protocol is at most 3.
2. The wider pattern cannot hide a new failing test. Met (READ/EXECUTED). `judge_group` takes the first class whose outcome matches and whose pattern `re.search`es the one-line reason (`tests/harness/upstream.py:763-774`; the reason is the first line of pytest's crash message, `tests/upstream/package_drive.py:245-254`). The new alternative is anchored at both ends, so it takes only a reason that is exactly `AssertionError: assert False`. Here is what each other class can do with it:
   - The classes before no-mmap in joblib-r (`joblib-cache-clock`, `no-asyncio-loop-error`, `no-asyncio-loop`) still take their members first. Nothing of theirs can move.
   - `joblib-cache-clock` has `^assert False$`, which does not match the prefixed reason (checked). Its member `test_memory_expires_after` reports a bare `assert False` today, so it stays put.
   - The one class after no-mmap, `no-processes`, matches process strings that the exact reason does not contain. So none of its members can move.
   - A test that passes today and later fails with that reason joins no-mmap. That is no longer a finding of `test_upstream_suite[joblib-r]`. It is still red: `class_findings` adds `+<id>`, the count and the digest move, and the gap's `match` ("14 finding(s), digest c86ab2e9c452") no longer holds, so `plugin.py:514` fails the check as "fails differently from its gap".

   On darwin the class has the same 14 members as `expected/joblib-r/no-mmap.txt`, and the gap xfails with its digest unchanged (EXECUTED). Neither the list nor `known_gaps.toml` changed in the diff (READ).
3. The unit row fails on the parent and passes now. Met (EXECUTED; see Re-ran). It follows the file's idiom: `_group(_stream(...), classes=...)` with an assertion on `findings` and `members`, like `test_failures_sort_into_the_first_class_that_fits_and_the_rest_are_findings`. It reads the real joblib classes from `CONFIGS`, so it pins the shipped configuration and not a fixture. Its docstring gives the reason in words.
4. Rule compliance. Met (READ).
   - **Rule 4.** This is a judge change with its reason stated in the commit and in the TOML comment. No member, list or gap is edited.
   - **Code speaks for itself.** Neither the TOML comment nor the docstring names a spec, run id, review or `context/` path. The run id is in the commit message only, which the rule allows.
   - **ruff.** Clean.
   - **Precedent.** `tests/upstream/matplotlib.toml:244` uses the same `^AssertionError: assert False$` alternative.

## Findings, most severe first
1. **Low: the class's `reason` (and the gap's) does not mention this case.** The reason still reads "…xlrd opens a workbook with mmap, so a test that checks the error a bad workbook raises sees mmap's". That text came over from the shared no-mmap wording, and xlrd has nothing to do with joblib. The new member's message is now explained only by the TOML comment, which the scoreboard does not show. Optional fix text for both `joblib.toml`'s joblib-r no-mmap `reason` and its gap in `known_gaps.toml`: "no mmap: the stand-in raises OSError (README); joblib's cross-version test reads a Python 2 pickle's error as a failed ValueError assertion when that pickle is listed first". Editing a reason is itself a judge change. Leaving it as it is is also fine.
2. **Note: the listing order is not a product defect.** WASI's `fd_readdir` promises no order. wasmtime passes the host's order through, and native CPython on the same host lists in the same order. joblib's test, not the guest, makes the outcome depend on order. No portability follow-up is needed for the product. For the judge, the general lesson is this: any upstream test whose failure reason depends on listing order can flip classes between hosts. When one appears, the fix is the same as this one: one class that takes both messages, with members pinned by node id.
3. **Note: pytest's "AssertionError: " prefix varies by test.** In today's darwin stream, `test_memory_expires_after` reports a bare `assert False`, while the Linux log shows this test's assertion with the prefix (raised inside an `except` block). First-fit keeps the two apart only because one pattern has the prefix and the other does not. If a pytest upgrade changed the prefix rule, members would move between `joblib-cache-clock` and `no-mmap`. That would show as `+`/`-` lines, so the judge would be red, not silent.
4. **Note: what the lane still owes before a tag.** The judge's hash moves. The release acceptance at history line 95 predates this change, so the lane accepts again with `--accept-judge`, and G7 needs that newest acceptance to judge the release tier. The unit suite also grows by one test. A sameness comparison against `build/releases/0.1.0/record.json` explains that only through a claim with `units = 1`, or through a fresh release acceptance that takes the place of that record. This review file is untracked under `context/reviews/`, which refuses `--accept` until it is committed.
5. **Note: structure.** No `src/` change, no harness code change, no new mutable or platform branch. Not structural.

## Constitution checks
- §4 constraints: none touched beyond the judge.
- Rule 3 (check first): the row fails on the parent's configuration; this review confirmed it.
- Rule 4 (never weaken the judge): holds. The class's members and the gap's digest are unchanged, and a new member would still be red.
- Rule 8 (the implementer never reviews): this reviewer wrote none of it.
- §7 never-do list: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)
1. Low 1: answered in writing, no change. The class's `reason` and its gap's stay as they are for 0.1.0: both still say what the class is (mmap's absence), and rewording them is a judge change of its own after the dry run. The TOML comment above the class gives this test's case. The reword is on the roadmap's follow-ups with the listing-order note.

## Verdict
Lands. The diagnosis fits the test source and both dry runs. The wider pattern is exact and comes after every class it could take from, and the class's pinned members keep any new test red. Low 1 is an optional rewording of the class's reason.
