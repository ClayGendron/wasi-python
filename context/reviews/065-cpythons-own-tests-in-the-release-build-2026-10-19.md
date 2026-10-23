# Review of 065 — CPython's own tests in the release (the build)

- **Date:** 2026-10-19
- **Reviewer:** a fresh agent (Claude Opus 5.5). I reviewed this specification before it was built, and confirmed its revision twice; I wrote none of its code. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `spec/065-cpythons-own-tests-in-the-release` at `41b02eb`, built on spec 063's unlanded head `1488377`: `git diff 1488377..41b02eb` (77 files, +6,818 −61). I read:
  - the new harness (`tests/harness/regrtest.py`) and the guest-side driver (`tests/upstream/regrtest_drive.py`);
  - every changed harness file (`guest.py`, `plugin.py`, `shards.py`, `scoreboard.py`, `gather.py`, `upstream.py`), `fetch.py`, `test_v1_3_upstream_suites.py`, the helper change in `test_v1_2_hostile_guest.py`, and the unit tests' names and coverage;
  - `python.toml`, the relevant parts of `known_gaps.toml`, facts sheets 20 and 21, and the README and CHANGELOG diffs;
  - the landing notes.
- **Ran (EXECUTED, darwin-arm64, in the 065 worktree, against main's frozen set `s-ff5246a2c2f1a52b`, read only; every record written to my scratchpad with `--progress-latest`, so the builder's `build/progress/latest.json` is untouched; nothing committed, pushed or dispatched).** Probes and outputs are in `probes/` beside this file:
  - `full_judge.txt`: `uv run pytest -n 3`.
  - `fast_tier.txt`: `uv run pytest -m "not slow" -n 3`.
  - `ruff.txt`: `ruff check` and `ruff format --check`.
  - `shard-upstream-macos.*` and `shard-upstream-frame.*`: `uv run pytest --shard=upstream-macos` and `--shard=upstream-frame`, serial.
  - `clock_res.py`: the guest's `time.get_clock_info` through main's harness and through 065's. `runner_clock.txt`: the same through the product's `wasi_python.run`.
  - `dryrun_cpython.py` over `dryrun-records/`: the six upstream shard records of the branch's last dry run 39196429702, downloaded with `gh run download` (read only), compared with my full judge's record.

## What holds

- **The full judge reproduces the builder's numbers (EXECUTED, `full_judge.txt`).** 417/515 pass, 77 gap, 21 blocked, 0 fail; ratchet lost 0, absent 0, unrun 0, gained 9, grew 0. The same summary line as the landing notes, in 698 s at load 55 to 70.
  - The CPython checks: 5 groups pass, 28,107 passes, 1.137 T of fuel (under the 1.45×10¹² review rule).
  - The gaps: 24 classes, 10 trap entries, 1 deselection, 2 environment entries and 26 host entries are gaps; the emptied `trailing-slash-einval` class passes.
  - The environment entries hold: `env_altered` is exactly `test_doctest` in `cpython-b` and `test_bdb` in `cpython-c`.
  - The open-entry line prints: "trap entries with no trap here: c-stack-ordered-dict-subclass".
- **The fast tier and ruff are green (EXECUTED).** 1,824 passed, 28 skipped, lost 0; `All checks passed!`, 101 files formatted.
- **The shards are the judge (EXECUTED).** `--shard=upstream-macos` (numpy-lib, `cpython-fs`) and `--shard=upstream-frame` (pandas-frame, `cpython-b`) are green. Each group's `passes` and `passed_digest` equal the full judge's, and their fuel agrees within 5×10⁻⁷.
- **Every host gives the same verdict, as G5 would check (EXECUTED, from the dry run's records).** The gather never ran, so I compared by hand. Across the six upstream shard records of 39196429702 (Linux, the CI macOS runner, Windows), every group's `passes` and `passed_digest` equal my darwin record's: all 19 groups, the five CPython groups and `cpython-fs` on all three systems included. `cpython-fs` on the CI macOS runner is −1.4×10⁻⁵ from my fuel (tolerance 1e-4). Fuel elsewhere differs by host by up to 0.8% (`cpython-b` on Linux), which is expected, since fuel is ratcheted on darwin only.
- **The pre-build review's F5 came true, and the any-host rule handled it (EXECUTED, the records).** On Linux x86-64 the guest traps in `test_ordered_dict.CPythonOrderedDictSubclassTests.test_highly_nested`, where darwin does not. It is now a tenth trap entry, deselected on every host. Its check records "trap at or after …" on Linux and "no trap on this host" on darwin, and is the same gap on both. All nine other entries trapped at their named test on Linux.
- **The 26 host entries cannot hide a regression (READ, `regrtest.judge_group`; unit tests `test_a_test_host_entry_is_checked_exactly_per_system_and_out_of_the_count` and the module variants).**
  - A host entry's test is checked against that system's recorded outcome exactly, in the group check and in its own check. For example, the 22 `test_tempfile` tests must pass on darwin and Linux and error on Windows.
  - It is left out of `passes` on every host. Each entry's gap digests its constant finding, so a second finding on any host turns it red.
- **The mechanisms the confirmation asked for are in and tested (READ).**
  - Environment kinds match `<change> was modified by` exactly (`Environment.admits`), so `sys.path` cannot admit `sys.path_hooks`.
  - An `altered` module with no warning line is a finding.
  - The `print_warning` wrapper carries `orig_stderr`, and a unit check runs it.
  - A1 wraps `single.clear_caches` and never imports `ctypes`.
  - Deselected and trap ids are resolved against the tarball's source with `ast`.
  - The stage is read from the verified tarball, with a stand-in test.
  - The whole-module trap verdict records counts and does not judge failures.
  - 37 unit tests cover these in `tests/unit/test_regrtest.py`.
- **Not build-class, as claimed (READ).** The diff touches nothing under `scripts/` or `recipes/`, no line of `downloads/SHA256SUMS`, and not `release.yml`. The conflict-marker repair is in `context/` and test files only.
- **No conflict marker remains at the head (EXECUTED, `git grep` at `41b02eb`: none).**

## The departures, judged

1. **`guest.py` answers `clock_res_get` itself: right, but needs a check (F1).**
   - **READ.** The judge already replaces `clock_time_get` with its stepped clock, 1 µs per read, for every clock id. Before this change it let wasmtime answer `clock_res_get` from the host. So the guest saw a clock that steps by 1 µs while claiming 1 ns on Linux. `support.Stopwatch` then measures two reads, 1 µs, and `test_int`'s four timing tests compare that with twice the resolution (`test_int.py:599, 638`): they skip at 1 µs and run, then fail, at 1 ns. The failures are an artifact of the judge's own clock, not a host difference of the product's.
   - **EXECUTED (`clock_res.py`).** Through main's harness and through 065's, the guest reports the same values on darwin: realtime, monotonic and perf_counter 1.0e-06, process_time 1e-09 (`thread_time` is not available in the guest). So no darwin result moves; the full judge's grew 0 agrees.
   - **The product is not hidden.** The product's runner on darwin reports 1 µs too (`runner_clock.txt`, EXECUTED). On Linux it would report the host's 1 ns (INFERRED from the dry run), which is a true answer about a real clock. The judge makes no claim about the runner's clock resolution, and the judge's clock is the judge's. Host entries would be wrong here: they would record an artifact of the judge as a host's semantics, under a closer that can never close it. Rule 4 is not weakened: the change removes a host difference of the judge's own making, in the open, with its reason, and the judge hash moves.
   - **What is missing** is in F1.
2. **Ten trap entries: accepted.** This is Decision 1's any-host rule applied as written, with the evidence in the records (above).
3. **26 host entries: accepted as a mechanism.** The per-system results and the equal digests are checked above. Their closers and the README are F2 and F3.
4. **The findings of a failing group as facts: accepted.** They are recorded only when the group is already red (`test_upstream_suite`), so they change no verdict. They let a release record show every finding instead of the message's first five. They do not enter `passed_digest` or the ratchet.
5. **28,107 passes, not 28,134: accepted (EXECUTED).**
   - The arithmetic: 28,134 − 1 (`test_doctest`'s `test_CLI`, a skipped doctest) − 1 (the OrderedDict test, deselected) − 25 (the Windows host entries' tests, which pass on darwin and Linux and are left out of `passes` everywhere) = 28,107.
   - My judge's groups: 3,710 + 1,313 + 5,681 + 9,534 + 7,869.
6. **The `sys.monitoring` stand-in shows half of criterion 2: accepted.** Its purpose, that a `sys.monitoring` regression is now red, is shown: 76 `unexpected failed` with `LINE` dropped. The other half, that the draft's class would have hidden a body-only regression, cannot be shown by a stand-in that breaks `setUp` too. The base runs already show it: under the draft all 45 tests failed in `setUp` before their bodies ran. The landing notes say exactly this.
7. **Facts sheet 20 clashes with spec 076: F5.**

## Findings, most severe first

### F1 (medium): the stated clock resolution has no check and no home outside the landing notes

- **Rule 3.** No check guards it: `grep` of `tests/` finds `CLOCK_RESOLUTION_NS` and `clock_res_get` only in `guest.py` (EXECUTED). If the shadowing were lost (a wasmtime-py change, a refactor), Linux would silently go back to the host's 1 ns. Linux runs only in the release, so the release would find it, not the lane.
- **The stated values are partly not the served clock's.** The CPU-time clocks (ids 2 and 3) are stated at 1 ns but step by 1 µs like the others (`clock_time_get` steps every id). They were kept at 1 ns so no darwin result moves, and that is a fair choice, but say so where the clock is specified.
- **The four `test_int` tests now skip on every host.** The judge therefore never exercises CPython's integer-to-string DoS limit. The skip is upstream's own outcome, so nothing is admitted, but it is a consequence of the stepped clock worth one sentence.
- **Fix.**
  - A unit check: `guest.run` of a snapshot program printing `time.get_clock_info(n).resolution` for the four clocks gives exactly `CLOCK_RESOLUTION_NS`. A stand-in that deletes the `define_func` lets the host answer.
  - One dated line in spec 002 (the stepped clock's specification), naming the stated resolutions and why.
  - The spec's Design list gains `tests/harness/guest.py`.

### F2 (medium-low): the README's trailing-slash sentence is now wrong on two of three hosts

- **READ.** The README's new platform facts say opening a missing path with a trailing slash "raises `OSError` (`EINVAL`), not `FileNotFoundError` (wasmtime's answers…)". The dry runs showed, and facts sheet 21 now says, `EINVAL` on darwin, `ENOENT` (`FileNotFoundError`) on Linux and `ENOTDIR` on Windows. That is why `trailing-slash` became a host entry and its class was emptied.
- **Fix.** Restate it per host ("on a macOS host … `EINVAL`; on Linux `FileNotFoundError`, as natively; on Windows `ENOTDIR`").

### F3 (low-medium): the Windows host entries name the wrong closer, and two of their facts are not in the README

- **READ.**
  - Decision 21 says a host entry closes with `README.md` when the difference is the host's genuine semantics, and with the wasmtime facts sheet when it is wasmtime's choice.
  - The README already states the open-file rule as the Windows grant's behaviour ("a Windows grant cannot remove or rename a file the guest holds open, so `tempfile.TemporaryFile` … fail there", under *On Windows*). Yet the 22 `test_tempfile` entries close with facts sheet 21, which calls it "wasmtime on Windows".
  - The other two Windows facts are in neither the README's *On Windows* list nor anywhere else users read: a name with a colon cannot be made, and opening a folder for reading gives `EINVAL`.
- **Effect (EXECUTED, `full_judge.txt`).** The scoreboard's `next:` line now names `context/upstream/21-wasmtime-read-only-errnos/notes.md` ("closes 31"). That points the progress signal at a sheet only the owner can act on, by posting it.
- **Fix.** Close the 25 Windows entries with `README.md`, and add the colon-name and folder-open facts to its *On Windows* list. Keep sheet 21 for `read-only-eperm`, the two environment entries and `trailing-slash`. This is a judge change (the closers are judged); its reason is Decision 21.

### F4 (low; procedure): six commits carry conflict markers, so the squash is required

- **EXECUTED (`git grep` per commit).**
  - `7bcec1e`, `dbf888a`, `bd2202f`, `8449627` and `0ca493d` each carry markers in 2 files.
  - The build commit `8c7c8a1` carries them in 5.
  - `1776879` repairs them; the head is clean.
- AGENTS rule 9 asks that a commit on main be green on its own, so the landing notes' "the lane may squash" should read "the lane squashes" (or the history is rewritten before landing).

### F5 (low): the facts-sheet numbers collide with spec 076

- **READ.** Spec 076's branch (`d0d1dd7`) adds `context/upstream/20-wasmtime-preview1-write-on-a-read-descriptor/`; 065 adds `20-cpython-tests-in-one-wasi-process` and `21-wasmtime-read-only-errnos`. Sixty-three lines under `tests/` name 065's sheets as closers (EXECUTED, `grep`), so renumbering is a judge change to `known_gaps.toml` and `python.toml`.
- **Fix.** 076 is the likelier to land first, since the gather waits on it. So renumber 065's sheets to 21 and 22 before landing, rather than at the lane, and the review sees the judge-hash line.

## Notes

- **N1.** Main has moved to `b413192` (spec 055 landed, set `s-9d43bf645dfcaa71`), and 063 is not yet on main. The lane rebases 065 after 063, re-judges on the new set, and confirms the CPython passes and gaps. The build is otherwise independent of 055 (INFERRED).
- **N2.** Trap checks record no `fuel` metric while they are gaps (EXECUTED, my record: `metrics` absent). So the 1.45×10¹² review rule sums the groups only, which is fine: a trap run costs a few G.
- **N3.** The 11 `left_out` files are the tree's `__pycache__`, as the memo said (EXECUTED).

## Verdict

**Lands once F1 to F3 are fixed:**
- F1: a check of the stated clock resolution, and its line in spec 002.
- F2: the trailing-slash sentence, per host.
- F3: the Windows entries closed with the README, which gains the two missing facts.

F4 and F5 are the lane's and the builder's at landing: squash, and renumber the sheets after 076. Everything else stands, measured three ways:
- my full judge, fast tier and two shards equal the builder's;
- the dry run's records give one verdict on three hosts;
- the departures are each right in substance.

**One line:** the build reproduces exactly and gives one verdict on every host; add a check for the judge's stated clock resolution and fix the two README facts and the Windows closers, then it lands.

---

# Confirmation of the fixes (d7916c9, on 41b02eb)

- **Reviewed:** `git diff 41b02eb..d7916c9`, 10 files:
  - the README;
  - spec 002's dated line and the 065 spec;
  - the facts sheets, renamed, and `context/upstream/README.md`;
  - `tests/checks/test_v1_2_portable_and_sealed.py` and `tests/unit/test_regrtest.py`;
  - the closers in `tests/known_gaps.toml` and `tests/upstream/python.toml`.
- **Ran (EXECUTED, the 065 worktree, `s-ff5246a2c2f1a52b`, records to my scratchpad; no git tree touched).**
  - `probes/fix_checks.txt` ran the new v1.2 check, `tests/unit/test_regrtest.py`, `test_upstream_files_are_well_formed`, `tests/checks/test_rules.py` and `tests/unit/test_hostile_helper_blocks.py`: 112 passed, 1 skipped; lost 0, grew 0. Ruff check and format are clean.
  - `probes/standin/`: the v1.2 check's stand-in, run on a scratch copy of `tests/harness` with the `clock_res_get` binding deleted.

| item | confirmed | evidence |
|---|---|---|
| F1, the clock check | **Yes.** `test_the_guest_clocks_resolution_is_the_judges` patches the stated table to distinct values (7 µs, 11 µs, 13 ns, 17 ns) and asserts the guest reports them for `time`, `monotonic` and `perf_counter`, so only the judge's answer can pass it. A unit check pins the real table to {step, step, 1, 1}. Spec 002 gains the dated line, with the 1 ns CPU clocks and the four `test_int` skips stated. | EXECUTED: the check passes as built (`['7000', '11000', '11000']`); with the binding deleted the guest reports `['1000', '1000', '1000']`, the host's, and the check fails. Leaving out `process_time` is right: it reads 1 ns without asking `clock_res_get` (both runs agree) |
| F2, the trailing slash | **Yes.** It is stated per host: `EINVAL` on macOS, `FileNotFoundError` on Linux as natively, `NotADirectoryError` (`ENOTDIR`) on Windows. The read-only `EPERM` keeps its citation of sheet 22. | READ; matches the dry run's facts in sheet 22 |
| F3, the Windows closers | **Yes.** All 25 `win-*` host entries close with `README.md`, in `python.toml` and in their gaps; `trailing-slash` keeps sheet 22. The README's *On Windows* list gains the colon-name and folder-open (`EINVAL`) facts beside the open-file rule. | EXECUTED (counted by `tomllib`): 25 `README.md`, 1 sheet 22; the rules check passes, so every closer exists |
| F5, the renumbering | **Yes.** The sheets are now `21-cpython-tests-in-one-wasi-process` and `22-wasmtime-read-only-errnos`; 065 adds no sheet 20, so 076's 20 is free. | EXECUTED: `git grep` at `d7916c9` finds no path to the old `20-cpython…` or `21-wasmtime…` anywhere |
| F4 | The lane squashes at landing; the landing notes now say so. | READ |

Nothing new is wrong as far as I can see. The new goal check adds one gained check at the lane (v1.2). The rest of the judge is unchanged by this commit, apart from the closers and the README.

## Verdict

**Confirmed, it lands**, after spec 063, by the lane's rebase onto main as it stands, with the squash (F4) and the lane's own serial judge on the new frozen set.

**One line:** F1, F2, F3 and F5 are fixed and proven; the clock check fails without the judge's binding, so 065 lands after 063 with the squash.

---

# Delta look: the rebase onto 08de0c8 and the re-judge (19c4acb)

- **Reviewed:** tip `19c4acb` on base `08de0c8`, against my confirmed tip `d7916c9` on base `1488377`. I compared the branch's whole patch on each base, normalized (`index` and `@@` lines dropped): `git diff 1488377 d7916c9`, `git diff 08de0c8 6744f0e` (the rebase commit) and `git diff 08de0c8 19c4acb`. I also read `git diff 6744f0e 19c4acb` in full, and the landing notes' section "Rebased onto main `08de0c8`". Files are in `delta/` beside this review.
- **Ran (EXECUTED, darwin-arm64, the 065 worktree's harness: the runner's 512 KiB engine).** I made a fresh `cp -Rp` copy of `s-c50ca51fae5eb55b-c9dcb5b8` (`delta/set/`). The zip's link count is 1 there, against 554 on the shared set.
  - `delta/trap_probe.py`: each closed and added trap test run alone in its own session, through the drafting stage of `Lib/test`.
  - `delta/run1.*`, `delta/run2.*`: `test_upstream_suite[cpython-a]`, `[cpython-c]` and the three `OrderedDict` trap checks, twice, as separate pytest runs on the copy.
  - Nothing was written in any git tree; every record went to the scratchpad.

## 1. Did the rebase change only what it required? Yes, with one unlisted change (G1)

- **The rebase commit `6744f0e` changed only context (EXECUTED).** The normalized patches of `d7916c9` and `6744f0e` differ in 43 lines. All of them are context lines that main changed under the branch's hunks (the CHANGELOG's neighbours, the README's "seven carried patches", other gaps, the shard unit tests). There is one exception: 063's Linux faulthandler gap came back in the three-way merge, and `19c4acb` drops it again, as the notes say.
- **`19c4acb` changes what is listed**, with one exception (G1). It removes four trap entries and their gaps, adds two, restates one reason, moves the eight trap closers, raises two caps, and updates the numbers in the CHANGELOG, README and a unit test. One unit test has a whitespace fix.

## 2. Is each changed entry measured? Yes (EXECUTED, the fresh copy)

| test, run alone (`-m <id>`) | result | the entry |
|---|---|---|
| `TestPartialC.test_recursive_pickle` | passes, 2.51 G, no trap | removed: right |
| `TestPartialCSubclass…` | passes, no trap | removed: right |
| `TestPartialPy…` | passes, no trap | removed: right |
| `TestPartialPySubclass…` | passes, no trap | removed: right |
| `PurePythonOrderedDictTests.test_highly_nested` | **traps**, call stack exhausted, 1.86 G | added: right |
| `PurePythonOrderedDictSubclassTests.test_highly_nested` | **traps**, 1.86 G | added: right |
| `CPythonOrderedDictSubclassTests.test_highly_nested` | **traps on darwin now**, 1.83 G | reason restated: right |
| `CPythonOrderedDictTests.test_highly_nested` (no entry) | passes | no entry needed: right |

The harness's own trap checks on the copy agree: all three `OrderedDict` entries give "trap at or after <their id>", twice. My probe used the drafting stage, built from the same pinned `Lib/test`, not the judge's stage. The trap checks used the judge's own.

## 3. Are the caps and the budget honest? Yes (EXECUTED, READ)

- My fuel on the copy matches the builder's: `cpython-a` 268.63 G (cap 4.1×10¹¹: 1.53×) and `cpython-c` 372.47 to 372.49 G (cap 5.6×10¹¹: 1.50×).
- The other caps, from the builder's numbers (READ): `cpython-b` 4.9×10¹¹ on 294.4 G (1.66×), `cpython-fs` 1.0×10¹¹ on 59.8 G (1.67×), `cpython-archives` 2.5×10¹¹ on 164.6 G (1.52×).
- The `/cpython` family: 1.0 + 2.5 + 4.1 + 4.9 + 5.6 = 18.1×10¹¹, plus 8 × 5×10¹⁰, = 2.21×10¹² against 2.5×10¹². The rules check passes. `cpython-c` sits exactly at 1.5×. That meets the rule, but it has no headroom, so the lane's first run should be read against it.
- **Passes:** `cpython-a` 5,685 and `cpython-c` 7,867 on the copy (EXECUTED); 28,109 in all, as reported.

## 4. The run-to-run variation: will the lane go red? Probably, until 083

- **Measured (EXECUTED).** On the private copy, where the zip's link count is fixed at 1, `cpython-a` repeats within 5×10⁻⁹. `cpython-c` moved **8.2×10⁻⁵** between two runs, under the ratchet's 1e-4 but close. The builder saw 3.3×10⁻⁴ (`cpython-b`) on the shared set.
- **The cause (READ).** The judge hard-links the set's zip into every run root (`guest._place`, `os.link`). The guest therefore sees a link count that moves with every other run on the machine (554 now), and it also sees real file times and inode numbers. Spec 083, confirmed and amended for exactly these, fixes all three in the driver.
- **So** a value the lane accepts serially can be "grown" past by the next landing's run. The lane's set is shared and busy, so that is likely for the CPython groups and for main's own checks alike; main already showed 26 such rows.
- **What the lane should do, without weakening the judge** (the tolerance stays 1e-4, no check is edited):
  - (a) Land **083 immediately after 065**, with no landing between them. 083 already plans to restate the accepted fuel with `--accept-judge` and `--accept-growth`, so 065's possibly noisy accepted values live for one landing only.
  - (b) For 065's own accept, judge on a **private copy (or APFS clone) of the frozen set** with no leftover run folders, so the link count is not a variable. This is measured above to cut the variation from 3.3×10⁻⁴ to ≤ 8.2×10⁻⁵ on these groups.
  - (c) If a CPython group still "grows" at the lane, re-run the same commit to show it is run-to-run variation, and accept with `--accept-growth` naming spec 083, as rule 5 allows. Do not widen the tolerance and do not drop the metric.
- The landing notes still say the lane needs `--accept-growth` for 26 of main's rows. The coordinator reports the final full judge gave grew 0. The notes should record that final run, so the lane knows which record it compares with.

## 5. The closer: change it before landing, to the roadmap's reservation of 078

- **READ.** Main has moved past `08de0c8`: `3561e55` answers questions 100 to 103 and moves them out of `context/questions-for-the-owner.md` into `decisions.md`, and the roadmap reserves **078** ("the runner runs each guest on a stack of its own", question 102 answered (a)). After the lane's next rebase, eight trap closers named `context/questions-for-the-owner.md`, "(question 102)", would point at a file that no longer holds question 102.
- The same is true of the six question-101 closers (the class `no-test-modules`, the deselection, three not-selected modules). Question 101 is answered, and its binary is reserved as **088**.
- **Recommendation.** Before landing, at the rebase the lane must do anyway, close the eight trap entries with `context/roadmap.md`, with the reason naming spec 078. Main has precedent: its faulthandler gap closes with "`context/roadmap.md` (spec 071, widened to own it)". Close the question-101 entries with the roadmap naming 088. 078 then moves its eight to its own file when it lands, as 071 did. Waiting for 078 to be confirmed would land 065 with closers that are stale on day one.

## New findings

- **G1 (low-medium; an unlisted change).** `19c4acb` also moved the `closes_with` of three spec-074 classes in `tests/upstream/python.toml`, from the memo to `context/questions-for-the-owner.md`: `mmap-stand-in-surface`, `no-executable-file` and `ctypes-stand-in-surface`, each of whose reasons says "(spec 074)".
  - Their gaps in `tests/known_gaps.toml` still close with the memo (lines 131, 197, 239). The two files now disagree, and the TOML side names a closer unrelated to 074.
  - The not-selected entries for spec 074 kept the memo.
  - It looks like a replace-all that went past the trap entries. Restore the memo for the three (or, with 5, the roadmap's 074 line), so the TOML and the gaps agree. A rules line that requires an entry's `closes_with` to equal its gap's would catch this kind of drift; that is the lane's call.
- **G2 (low; for the lane).** Main is at `2737b29`. Spec 081 has landed and edits `tests/harness/guest.py`'s `run()`, the same function where 065 adds `clock_res_get`. 0.1.0a7 is released. So the lane's rebase is not trivial: it needs a textual merge in `guest.py`, and 081's fuel changes may move the CPython groups again. If the CPython numbers move beyond what is recorded here, they need a short delta note at landing.

## Verdict

**Lands once G1 is reverted and the closers are moved per 5** (both small text changes at the lane's rebase onto current main). Then the lane accepts on a private copy of the set, and 083 lands next (4).

**One line:** the rebase is clean and every changed trap entry is measured; fix three wrongly moved closers, point the trap closers at 078's reservation, and land 083 right after.

---

# Addendum: 5294520, the ninth trap entry (READ; the dry run's result read with `gh`)

`c-stack-itertools-tee` is Decision 1's any-host rule applied as written. It is a full id, unique and not inherited (`test_itertools.py:1633, 1842`). It is deselected on every host; it is a trap entry, not a host entry (Decision 21). Its gap holds the constant finding, and its closer is the roadmap's 078 line, per this review's item 5. The budget becomes 2.21×10¹² + 5×10¹⁰ = 2.26×10¹², under 2.5×10¹². The count goes 8 → 9 and 28,108 passes. The new dry run, 39265738300 on `5294520`, is green, gather included.

This is a second Linux-x86-64-only trap (F5 of the pre-build review, again), so spec 078 must prove its 8 MiB stack on x86-64 and Windows, not only darwin. **Lands.**
