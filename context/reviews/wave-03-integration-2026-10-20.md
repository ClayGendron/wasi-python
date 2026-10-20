# Review of wave 03: integration of 094 and 092

- **Date:** 2026-10-20 (UTC; 2026-10-19 local)
- **Reviewer:** a fresh agent. I wrote and reviewed neither entry.
- **Reviewed:** `wave/03` at `c0d2e7e`, on main `e00d394`. First 094 (tip `fd6db0f`, based
  directly on `e00d394`), then 092 (rebased from `35e66b4` onto `fd6db0f`, with one new commit
  `c0d2e7e`).
- **Time box:** 20 minutes. Both entries change only the judge.
- **Run:** `tests/unit/test_gather.py` and `tests/unit/test_sameness.py`, in a
  `git archive c0d2e7e` export in my scratchpad with its own `build/`: **126 passed, 4.52 s**
  (EXECUTED). The ratchet line names the judge as changed in six files ("test_v1_4_embedding.py,
  gather.py, needs.py and 3 more"). That matches `git diff --name-only e00d394 c0d2e7e -- tests/`
  exactly (EXECUTED). **One fault in my procedure:** `build/lane.lock` did not exist when I first
  checked (23:29 local). It appeared within seconds, and the same shell command that started
  pytest also printed it. So that one run of 126 unit rows took 4.5 s in a scratchpad copy while
  the lock was held. It wrote nothing outside the scratchpad, and it ran no guest, no artifacts
  and no judge. Nothing ran after that.

Each item is labelled EXECUTED, READ or INFERRED.

## Acceptance criteria against evidence

### 1. 092's `git range-diff` against its reviewed tip (EXECUTED)

`git range-diff 880be64..35e66b4 fd6db0f..c0d2e7e` (saved beside this file as `rd.txt`):

```
1:  8184d86 = 1:  2eeee00 Spec 092, rebased onto main e8ba20a (wave 01) ...
2:  a10bc92 = 2:  7c572f2 Spec 092: landing notes for the rebased tip ...
3:  69c3b25 = 3:  62acec8 Spec 092 against its build review (lands once F1 and F2) ...
4:  35e66b4 = 4:  2dea0a8 Spec 092: the build review's confirmation on 69c3b25 ...
-:  ------- > 5:  c0d2e7e Spec 092, rebased onto wave/03 ...
```

All four reviewed commits are patch-identical. The only new commit is `c0d2e7e`, which changes two
files. It adds one row to `tests/unit/test_sameness.py`, and it changes 092's specification (its
units go from 45 to 46, and a rebase note is added). 094 is unchanged at `fd6db0f`, the tip its
reviewer confirmed. The confirmation's CI run, 39361856604, was on `1d70261`, before 094's rebase
onto `e00d394`. That rebase added only wave 02's code beneath an unchanged judge diff, as the
confirmation says (READ).

### 2. The merge's meaning in `gather.py` and the unit rows (READ; the rows EXECUTED)

There was no textual conflict. 094 adds a line to `CI_NEEDS` and a comment at the top of
`gather.py`. 092 rewrites `merge()` further down. Together they mean this:

- 094's `CI_NEEDS["read-only files"] = frozenset({"windows"})` sits beside `descriptor limit`, the
  only other need that is missing on Windows alone. `allowed()` reads `CI_NEEDS`, so the gather
  (G4) accepts the block only on Windows, and only for a check whose body calls the need. 094's
  row in `test_gather.py` shows `{"windows"}` for both cases.
- 092's `did_run()` counts a record blocked by any `CI_NEEDS` need as "not run". On Windows the
  two removal rows are `blocked` (`read-only files`), so their `source` is the darwin `pass` and
  their metrics come from darwin. This is the same path the `descriptor limit` rows already take.
- `worst` is `blocked` (it comes before `pass` in `ORDER`), and `worst_platform` is the Windows
  record's `win32-…`. In `sameness._ci_block`, `win32` maps to `{"windows"}`, and that set
  overlaps `CI_NEEDS["read-only files"]`. So F1's exception applies, and the rows are no
  difference. `sameness` imports `CI_NEEDS` from `gather`, so 094's entry reaches it with no
  second list to keep in step.
- The exception cannot hide a worse status. A `fail` or `unrun` anywhere comes before `blocked`
  in `ORDER`, so it becomes `worst` and is named. The same block on Linux or darwin is no
  exception, because `SYSTEMS` maps those to `linux`, `macos` and `build`. The new row's second
  assertion shows this.
- **Order of records (INFERRED; already a Low residual in 092's confirmation).** When two records
  are both `blocked`, `min()` keeps the first one in record order. The new row passes because the
  fixture lists `("linux", "own")` before `("windows", "own")`. If Windows came first, a Linux
  block by `read-only files` would get `worst_platform = win32` and would be masked in
  `sameness`. G4 is the backstop: `allowed()` refuses that block on Linux, and the gather goes
  red. `_read_only_files` is also met wherever `os.name != "nt"`. 094 adds a second need to the
  class 092's reviewer already named (it was `descriptor limit` alone). It adds no new kind of
  risk, so I do not count it as a new finding.

### 3. No build input changed (EXECUTED)

`git diff --stat e00d394 c0d2e7e -- scripts recipes downloads src .github` is empty. The wave
touches 13 files: `CHANGELOG.md`, `README.md`, `context/progress/README.md`, the two
specifications, the two build reviews, and six judge files under `tests/`. The README change is
094's M1 prose, in the Windows removal bullet and in "Not protected". No artifact, recipe, pin or
workflow moves, so the lane needs no rebuild. The frozen set judges the tip.

### 4. The two claim lists (READ; the unit counts EXECUTED/READ)

- **094:** no row grows, no pass moves, and no node is gained, lost or retired. On macOS and
  Linux both removal rows stay `pass` with no metrics. On Windows they go from FAIL (wave 01's
  dry run) to `blocked` (`read-only files`). Windows is not part of the lane's darwin record, so
  the accept sees no status change. One unit row. Accept with `--accept-judge "094: …"`, with no
  `--accept-growth`, no `--accept-fewer-passes` and no `--retire`.
- **092:** `new = ["tests/unit/test_sameness.py"]`, `units = 46`, no `grows`, `retired` or
  `changed`. Accept with `--accept-judge "092: …"`.
- **Unit counts on the tip.** `test_sameness.py` has 22 functions: 18 plain, plus parametrized
  rows of 8 + 6 + 8 + 3, which makes **43** (READ). `test_gather.py` goes from 13 functions at
  `e00d394`, to 14 at `fd6db0f` (094), to 17 at `c0d2e7e` (092's three), with no new
  parametrize (EXECUTED). So the wave's unit suite should grow by **47 = 46 + 1**. My run's 126
  rows equal 43 plus the gather file's 83, which fits the 79 rows that file had before
  (INFERRED).
- **Overlap.** The two lists name no row in common. Neither list grows, retires or moves a pass.
  Both are judge changes only.

### 5. Reviews on record (READ)

- `context/reviews/094-the-removal-rows-name-their-windows-need-build-2026-10-20.md`: "Confirmed:
  lands" (M1 and L1 closed, L2 stands). Its run, 39361856604, shows the Windows own-embedding job
  as `blocked by: read-only files 2`, `0 fail`, and the gather had no G line.
- `context/reviews/092-the-judge-reads-a-release-record-build-2026-10-20.md`: "Confirmed … the
  verdict is now 'lands'" (F1 to F4 fixed with rows, F5 and F6 answered, one Low residual).
  092 has no CI run of its own after the rebase. It is judge-only, so the wave's dry run before a
  tag (rule 6b) covers it.

## Findings, most severe first

There are no Critical, High or Medium findings.

### L1 (Low, cosmetic): a blank line inside the CHANGELOG's bullet list

092's CHANGELOG entry ends with an extra blank line before the spec 065 bullet. In Markdown that
makes the 0.1.0a8 list "loose", which changes the spacing of every item when rendered. The fix
deletes one line of CHANGELOG prose. It needs no further round, and the lane may fix it in
the landing notes commit or leave it.

### N1 (note, lane): the wave's claim file needs a 094 block

092's TOML shape is how the lane runs `sameness.py --claims`. 094's claim list is prose: it was
written before 092 existed. For the `suite` line to be explained, the wave's file must carry both
blocks, so that the units add to 47:

```toml
[[claim]]
spec = "094"
units = 1

[[claim]]
spec = "092"
new = ["tests/unit/test_sameness.py"]
units = 46   # 43 rows in test_sameness.py, 3 in test_gather.py
```

### N2 (note): record order decides `worst_platform` between two blocks

This is item 2's last bullet. It is already 092's Low residual, and G4 is its backstop. A later
change could have `merge` keep each system's status, or keep the worst status apart from an
allowed CI block.

## Constitution checks

- §4.1 (patches) and §4.2 (pins): no file under `recipes/`, `downloads/` or `scripts/` changed.
- The judge is not weakened (rule 4). No check, golden output, `known_gaps.toml`, upstream
  allowance or `context/progress/` file is edited to make a run green. 094 replaces a bare
  Windows `pytest.skip` with a named need, which the gather polices system by system. That is
  stricter than before, not weaker. The judge hash changes in six files, and both accept texts
  name the change.
- Tests count operations, not wall-clock (rule): no new timing assertion.
- Nothing lands unreviewed (rule 8): both build reviews and their confirmations are on the
  branch. This file is the integration review.

## Accept log: pending

The lane sends its accept summary. I check it for: lost 0, gained 0, grew 0, no node retired,
`judge changed` in exactly the six files of item 1, and the unit suite up by 47.

## Verdict

**Lands as merged at `c0d2e7e`.** 092's four reviewed commits are patch-identical after the
rebase. The one new commit adds a row that shows F1's exception now covers 094's need on Windows
and on no other system. No build input changed. The two claim lists overlap nowhere, and neither
grows, moves a pass or retires a node. L1 is cosmetic, and N1 is how the lane should write the
wave's claim file.

One line: two judge-only entries, merged cleanly; their meanings fit together; no build input
moved; lands at `c0d2e7e`.
