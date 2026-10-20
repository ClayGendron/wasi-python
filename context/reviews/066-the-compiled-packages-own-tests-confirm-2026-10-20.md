# Review of 066 — the compiled packages' own tests in the release (confirming the build review's answers)

- **Date:** 2026-10-20
- **Reviewer:** a fresh Claude agent (Opus 5.5). It wrote none of spec 066, did not do its build
  review, and reviewed none of its drafts.
- **Reviewed:** `spec/066-the-compiled-packages-own-tests` at `b3174f5`, against the build review's
  commit `493bb0a` (base `21dff9d`). The delta is the one commit `c6f419e..b3174f5`. Read in the
  worktree `/Users/claygendron/Git/Repos/wasi_python-066`, read only.
- **Rebase noise, separated:** `git range-diff 21dff9d..493bb0a 2516875..c6f419e` (EXECUTED): seven
  of eight commits `=`; the eighth (`41bed05`, the build) differs only in the context lines of
  its `known_gaps.toml` hunk, which now sits after main's Windows entry instead of 037's scipy
  entries. `git diff 2516875 b3174f5 -- tests/known_gaps.toml` adds 140 lines and removes none, and
  no `test_v1_3_scipy` gap is left on either side (EXECUTED). So the builder's one conflict
  hunk is resolved as described, and everything else in `c6f419e..b3174f5` is the fixes.
- **Time box:** 45 minutes of reading (build-class), plus the fast tier.
- **Run:** `39451333969` (run 124), the builder's, read under the owner's rule of 2026-10-20
  (constitution §5.6 amended in main `30e9b41`); no run dispatched. `gh run view 39451333969 --json
  jobs,headSha` (EXECUTED): `headSha` `b3174f5b9fe725fd27b08e85f4c0ad1c5ddf335d`, completed,
  success; 43 jobs: 40 `success`, 3 publish jobs `skipped`; `gather` success. Its
  `release-record-1` (downloaded to my scratch folder; byte-equal to the builder's
  `build/066/rec124/record.json`): 739/832 pass, 86 gap, 7 blocked, 0 fail. The 14
  `upstream-plot-*` shards' judge steps took 100 to 228 s.
- **Re-ran:**
  - `uv run pytest -m "not slow" -n 3` in the worktree, `build/lane.lock` absent at the start,
    `build/progress/latest.json` backed up first and restored after → exit 0; 2,469 passed,
    38 skipped in 7 min 23 s; scoreboard 603/832 pass, 0 fail (equal to the builder's
    `build/066/fast2.txt`); ratchet vs `e9a76ce`: lost 0, absent 0, grew 0, judge changed.
    Output: `fast.txt` in my scratch folder. The worktree is clean at `b3174f5` afterwards.
  - In-memory probes and mutants of `harness.packages` (imported from the worktree with
    `-B`, nothing written there): M2 and M3 below. Scripts and outputs are in my scratch folder
    (`scripts/probes.py`, `scripts/m2.py`, `scripts/cmp.py`, `scripts/cover.py`).
  - The repo's oracle venv (`build/oracle/venv/bin/python -I`, native Pillow 13.0.0, matplotlib
    3.11.2 with FreeType 2.14.3, contourpy 1.4.0), called directly so nothing syncs: the two
    new classes' native behaviour, below.
  - Reader scripts over the pinned `pillow-13.0.0.tar.gz` and `contourpy-1.4.0.tar.gz`
    (unpacked only into my scratch folder) and over the builder's kept streams
    (`build/harness/streams/`).

## Acceptance criteria against evidence (the build review's findings)

1. **M1, contourpy** — met. EXECUTED (stream `contourpy-contourpy-rest.txt`):
   `test_codebase.py::test_version` passes; `test_cppcheck` and `test_mypy` fail with
   `[Errno 58] wasi does not support processes` and are exactly `no-processes.txt`;
   `test_bokeh_renderer.py` is one counted `R skipped` (no `bokeh`). EXECUTED: every
   `tests/test_*.py` of the tarball (19) is in a group; the only other `*_test.py` is
   `tests/util_test.py`, a helper.
2. **M1, Pillow** — met in substance; two reasons are not true as written (L1). EXECUTED: all 182
   `Tests/test_*.py`, `checks/check_*.py` and `checks/*_check.py` files are under the group's
   paths; seven are named in `not_selected`. The stream ran `selftest.py`'s docstrings
   (`::docstrings:selftest.testimage` passed) and 22 items from `checks/`: 6 pass (with the
   selftest), 7 skip, 10 fail, each failure in exactly one class list. Read against the files:
   - `check_release_notes.py` reads `docs/releasenotes/*.rst` for a `TODO` (the Makefile's
     `release-test` runs it). True: a documentation check, not a product test.
   - `32bit_segfault_check.py` runs `Image.new("L", (999999, 999999))` at import when
     `sys.maxsize < 2**32`. True: in the guest that is a `MemoryError` at import, a collection
     error. The builder's `build/066/run4.txt` shows it.
   - `check_icns_dos.py` and `check_j2k_dos.py` call `Image.open` at module level and pass if it
     does not hang. True.
   - `check_fli_oob.py` and `check_jp2_overflow.py` — not true as written (L1).
3. **M1, the new classes** — honest. Each closer names a real place, but two of those places
   hold nothing for their class yet (L2).
   - `no-processes` (contourpy, 2): true, as above.
   - `no-resource-module` (2): true. `R failed ... ModuleNotFoundError: Unsupported platform for
     standard library module 'resource'`; the README gains the fact.
   - `not-pillows-wheel` (3): true. `check_wheel.py` asserts the PyPI wheel's sets (`{'zlib'}
     == {'jpg', ...}`); closer spec 023, as `pillow-zlib-only`.
   - `fli-overflow-native` (1): true. EXECUTED: the oracle's native Pillow 13.0.0 opens
     `Tests/images/fli_overflow.fli` and `load()` raises `OSError: unrecognized data stream
     contents when reading image file`, the guest's exact message. The sdist's test commands
     (`tox.ini`, the Makefile, `ios.test-command`) never name it.
   - `text-rendering` (17): true, and the build is not the cause. EXECUTED: native matplotlib
     3.11.2 with FreeType 2.14.3 (the oracle) draws contourpy's `ConfigFilled` and `ConfigLines`
     with `show_text=True` at max 255, mean 4.77 to 6.46. That is past contourpy's thresholds,
     as in the guest. The `_no_text` images pass natively (max 0 to 52, mean at most 0.0005).
     So contourpy's text baselines fail at our FreeType pin on native too.
4. **M2** — met. EXECUTED (stream `lxml-lxml.txt`): 34 `D …::test_suite` lines, no `test_suite`
   item passed, 2,024 passes, equal to the record. Probes on `keep_findings`, with proper `S`/`R`
   lines: a builder that ran, a test of an unlisted class (passed or skipped), and a module-level
   function each give `ran a test lxml's test_suite() does not add`; a deselected builder gives
   none. Mutant: deleting the third-direction loop makes
   `test_lxml_selection_is_checked_both_ways` fail (killed). One edge is lenient (Note 2).
5. **M3** — met, under the rule as the owner wrote it ("rounded up to two figures"). EXECUTED:
   - A cap of 1.51 times `measured` is refused for `contourpy-filled-7` (664.05 G over its
     660 G) and `pillow` (653.75 G over 650 G).
   - It is accepted for `contourpy-1` (36.70 G under 37 G) and `contourpy-lines-3` (206.5 G under
     210 G). The two-figure round-up allows that: up to about 1.65 times just past a power of
     ten (`rule_cap(66_700_000_000)` is 1.649 times). That is the rule, not a defect (Note 1).
   - `path_packages = []`, `support = []` and a group without `measured` each give their own
     line.
   - Mutants: removing the cap comparison, or the refusal, fails its unit case (killed, three
     of three).
   - Every one of the 40 caps equals `rule_cap(measured)`. Each family's `budget` equals the sum
     of its caps.
6. **L1 (split counts compared)** — met for groups judged in one process; not across shards (L3).
7. **L2 (`--runslow`, `--runtext`, the `test_config.py` split)** — met. EXECUTED:
   - `args = ["--runslow", "--runtext"]` reach pytest unchanged
     (`group_args` for `contourpy-config-1`: `['--runslow', '--runtext', '/upstream-contourpy/tree/tests/test_config.py', '-k(True)']`).
   - contourpy's `conftest.py` has no other opt-in that selects tests; `--driver-path` serves the
     Bokeh export, which is not in the product.
   - The record's split counts are 36 for both config groups (config-1: 17 failed, 1 skipped;
     config-2: 17 passed). Three new `compare_slow` groups pass, 10 cases in all.
   - The 52 `cwd_files` are exactly the tarball's `tests/baseline_images/`.
8. **L5** — met. `_abs()` is gone. The driver passes `spec["args"]` as given. `group_args` makes
   only the group's paths and `--ignore` values absolute (EXECUTED for regex, contourpy-rest,
   pillow, matplotlib-rest-a), so a marker or an option's value is never a path. `--deselect`
   stays relative to the rootdir. regex's `test_main` does not appear in its stream.
9. **L8** — met (READ): `test_the_upstream_stage_never_takes_a_package_family` and
   `test_a_shard_fetches_only_its_families_trees` exist and pass in the fast tier.
10. **L3, L4, L6, L7** — met (READ): `test_bokeh_renderer.py` selected; the README's
    4 GiB and `resource` bullets; 099's order both ways in "For the lane"; the self-check wording.
11. **Fuel and caps** — met. EXECUTED, `build/066/final.json` against the TOMLs and run 124's
    record:
    - 40 groups; 17,972 passes in both; fuel 9,984.7 G (final.json) and 9,985.5 G (Linux);
      caps 1.5166×10¹³.
    - Every group's `measured` equals final.json's fuel. Every group's Linux fuel is within
      0.16% of it (the largest is `contourpy-config-2`, +0.16%). Every group's passes are equal.
      Every group's status is `pass`.
    - `matplotlib-mathtext`'s `measured` is wave 06's (two host-litter voids on darwin). Linux
      measured it on `dc6ba3a5` at 296.57 G, 0.05% under, and its `no-processes` class is `gap`
      in the record.
    - The 14 Linux plot shards' judge steps took at most 228 s.
12. **"For the lane"** — met. EXECUTED:
    - Both flags begin "066" and contain no `"`, `$`, backtick, `!` or backslash.
    - The claim list matches the record: 63 new rows (40 suites `pass`, 23 classes `gap`); gaps
      matplotlib 10 (`README.md` 6, spec 023 2, roadmap 2), Pillow 9 (6, 2,
      `context/upstream/README.md` 1), lxml 2, contourpy 2.
    - The record's 65 rows not in `accepted.json` are those 63 plus
      `test_wheel_carries_the_artifact_set` and `test_same_bytes_passed_on_three_systems`. Those
      two are CI-side rows, not 066's (INFERRED: they need `dist/` and three records).
    - The six accepted passes that are not `pass` in the record are CI's standing `blocked` rows
      (descriptor limit, read-only files, oracle, prior-art clones), as on every CI record.
    - Two phrases in the accept-judge text are looser than the code (L3, Note 1).

## Findings, most severe first

No High and no Medium. The three Mediums of the build review are closed.

1. **L1 — Two of Pillow's six `not_selected` reasons state things that are not true**
   (`tests/upstream/pillow.toml`, the `check_fli_oob.py`/`check_jp2_overflow.py` entry; the same
   words in the spec's Disposition item 1 and its class table's lead-in).
   - "the second's inputs not in the sdist" is false. `tar -tzvf` of the pinned tarball
     (EXECUTED) lists `Tests/images/00r0_gray_l.jp2` (614 bytes) and
     `Tests/images/00r1_graya_la.jp2` (335 bytes).
   - The builder's `run4.txt` shows the real cause: `FileNotFoundError: [Errno 44] ...
     '00r0_gray_l.jp2'`. The script opens the bare name, so it is meant to be run from
     `Tests/images/`, and the group's working folder is the tree root.
   - "whose files `Tests/test_file_fli.py`'s own tests open and run" names the wrong file. No
     test in `Tests/test_file_fli.py`, or anywhere in `Tests/`, names `fli_oob` (grep, EXECUTED).
   - What is true is better: `Tests/oss-fuzz/test_fuzzers.py::test_fuzz_images` loads every file
     under `Tests/images/`. In the builder's stream it passed for all 51 `fli_oob/` files and
     for both `.jp2` samples (EXECUTED).
   - So no test is left out: the two scripts have no test functions, and every sample they load
     is loaded by a selected test that passes. Only the reason is wrong. Hence Low.
   - Failure: the owner's rule asks that each test not run be named with its true reason. A
     reader who trusts "not in the sdist" never learns the samples are there. Nor would a reader
     learn they are already exercised. A later spec that wants these samples run would start
     from a false fact.
   - Fix text (the builder's; it changes the judge's text, never an outcome or a fuel):
     `reason = "valgrind reproductions run by hand, not tests: each opens its crash samples by a
     path relative to the folder it is run from (images/fli_oob/... from Tests/, 00r0_gray_l.jp2
     and 00r1_graya_la.jp2 from Tests/images/) and prints each exception, so at the tree root its
     first open raises FileNotFoundError at import, a collection error (EXECUTED, the build);
     every one of those samples is loaded by Tests/oss-fuzz/test_fuzzers.py::test_fuzz_images,
     which runs and passes"`. Correct the Disposition's item 1 to match.

2. **L2 — `fli-overflow-native` and `text-rendering` close with a file that does not mention them**
   (`tests/known_gaps.toml`, `pillow.toml`, `contourpy.toml`: `closes_with =
   "context/upstream/README.md"`).
   - That file is the table of upstream drafts waiting for the owner. It has no row, folder or
     text for either class (grep, EXECUTED).
   - Both classes are honest. Both fail on native too at our pins (criterion 3 above, EXECUTED).
     But the gap's closer should point at something that will close it.
   - The scoreboard groups these two as "README 2" beside "README 61", which hides the
     difference.
   - Failure: the gap lists say these close "upstream". Nobody has drafted anything, so the two
     gaps never close and nobody is asked.
   - Fix text (context only, so the reviewer or the lane may write it in once the branch is
     handed over): two rows in `context/upstream/README.md`:
     - `30-pillow-check-fli-overflow/` — Pillow — `checks/check_fli_overflow.py` expects
       `Tests/images/fli_overflow.fli` to load, and native Pillow 13.0.0 raises `OSError:
       unrecognized data stream contents`; no test command in the sdist runs it — facts only
       (spec 066); the owner decides whether to report.
     - `31-contourpy-text-baselines-freetype/` — contourpy — the `--runtext` baselines of
       `test_config.py` fail at FreeType 2.14.3 on native matplotlib 3.11.2 as in the guest (max
       255, mean 4.8 to 6.5; without text, max at most 52, mean at most 0.0005) — facts only
       (spec 066); the owner decides whether to report.
   - Or change both closers to `README.md`, with one platform fact each.
   - Also add to `text-rendering`'s reason: "native matplotlib at the same pins fails the same
     way (the confirming review, EXECUTED)". That is a builder's change, since it moves a class's
     text.

3. **L3 — The split-count comparison runs only inside one judge process**
   (`tests/harness/packages.py` `Session._split_findings`).
   - It compares a group's `K` count with groups of the same split already judged in the same
     `Session`.
   - On CI the groups of a split are spread over shards. `contourpy-config-1` is in
     `upstream-plot-k` and `contourpy-config-2` in `upstream-plot-m`, so that pair is never
     compared. `test_filled.py`'s twelve groups are in ten shards. Under `-n 3` only the groups
     on one worker meet.
   - No unit case covers the call in `Session.group`. A mutant that drops it leaves the unit
     suite green. That is READ, not run: the suite's only `packages.Session` case calls
     `_split_findings` directly, and no unit case calls `Session.group`.
   - The `collected` fact is still recorded. Run 124's record has 518, 419 and 36 in every
     split group (EXECUTED), so the lane can still read it.
   - Failure: a pytest change that collects `test_config.py` differently on one shard is caught
     by the partition only if the counts meet in one process. The accept-judge text ("collected
     counts compared") promises more than that.
   - Fix text (context only): in "For the lane" and the accept-judge text, write "collected
     counts compared within one judge process; across shards the lane reads the `collected`
     facts (518, 419, 36 in run 124)". No code change is needed. The build review's L1 was
     optional.

**Notes, no finding:**
1. **The cap rule's round-up.** `rule_cap` rounds 1.5 times `measured` up to two significant
   figures, as Decision 14 and the owner's words say. So a cap can reach about 1.65 times just
   past a power of ten. Today the largest is 1.547 (`lxml`). The accept-judge text says "at most
   1.5 times its recorded measurement"; "1.5 times, rounded up to two figures" would be exact.
   `measured` is data the builder writes. Nothing ties it to a record, so raising `measured`
   with the cap passes. A fuel row's growth is still red in the ratchet. Spec 091 ("a fuel
   fact's fuel below its cap") is already listed as not machine-checked.
2. **`_added` reads class names, the driver reads `TestCase`.** For a module whose
   `test_suite()` loads everything (`"*"`), the host check treats any class as added, while
   `_keep` keeps only `TestCase` classes. Suppose such a module had a plain pytest class. The
   driver would deselect it, and the host would call that "deselected a test lxml's
   test_suite() runs". The run goes red, never silently green. lxml has no such class today
   (the run is green).
3. **`check_icns_dos.py` closes with spec 023.** ICNS is pure Python and has nothing to do with
   the zlib-only build. `README.md` would fit that file better. Cosmetic.

## Constitution checks

- §4 constraints:
  - No `src/`, `scripts/`, `recipes/` or `downloads/` line in the delta, and no artifact byte
    changes (the set is main's `dc6ba3a5`, run 124's `three systems` line).
  - Inputs are pinned tarballs, read only in my scratch folder.
  - Tests count fuel and passes. The shard times above are benchmark facts.
  - The judge is not weakened: new rule checks only (the cap rule, the refusals, the third lxml
    direction, the split comparison). The removed `SPLIT_MAX` total is replaced by a stricter
    per-cap rule. numpy's and pandas' configurations and stage are untouched in the delta.
  - "Never left out" holds (L1 is about wording).
- §7 never-do list: nothing tripped. No upstream patch, no prior-art copying, no accepted row
  edited, no progress file touched.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. L1 — 
2. L2 — 
3. L3 — 

## Verdict

Lands: M1, M2 and M3 are closed and evidenced at `b3174f5` by run `39451333969`; the three Lows
(two Pillow reasons corrected, the two closers given something to point at, the split
comparison's reach stated) are write-ins that need no further round.
