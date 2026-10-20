# Review of 038 — scipy, the second milestone: the build review's fixes (the delta)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude Opus 5.5). I wrote none of spec 038, its build, its fixes or
  its build review. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `spec/038-scipy-second-milestone` at `ecc2423` (worktree `wasi_python-038`),
  restacked on main `958a22b`: `git diff 1073d68..ecc2423` (12 files, +425 −71; four commits,
  `60e0d41`, `442493b`, `2f52e0b`, `ecc2423`). The build review's tip was `1ef614c` on 037's
  `28bd08a`; `git range-diff 28bd08a..1ef614c 958a22b..1073d68` shows commits 1, 3 and 4
  unchanged and commit 2 changed only in `README.md`'s carried-patch row, prose and list
  (main's nineteen with kiwisolver's `tp_clear` and lxml's `fake_cython`, plus 038's two:
  twenty-one), exactly the hunks the phase-3 note names (EXECUTED).
- **Time box:** 45 minutes of reading (build-class), plus waiting for CI.
- **Run:** my own release-workflow run `39416337718` on `ecc2423` (dispatched first; it queued behind
  the builder's `39415728849` on the same commit, by the workflow's per-branch concurrency group),
  watched to the end and read (`gh run view --json jobs`, each failed job's log, and the shard
  records; there is no `release-record-1`, because the gather job is skipped when a judge job
  is red, the same as the builder's run). 22 jobs passed, 3 failed, 4 publishing jobs skipped.
  Every red line is GREW: macOS own-guest `RED: 103 metric(s) grew` (lost 0, gained 13),
  own-embedding `RED: 15 metric(s) grew` (lost 0), upstream-macos `RED: 1 metric(s) grew`
  (`test_upstream_suite[cpython-fs]`, lost 0). No G7 line, no LOST, no FAIL. Both Linux
  rebuilds and "the same bytes from every host" passed; every Windows job passed. The builder's
  `39415728849` ended the same (3 failed, the same three GREW counts), and the three macOS
  records of the two runs agree row for row: 757 rows each, 0 differing in status or fuel
  (EXECUTED).
- **Re-ran (EXECUTED, darwin-arm64, the 038 worktree's `build/artifacts`, set `SHA256SUMS`
  `c3a849c0`; `build/lane.lock` absent each time; single node ids only, no build):**
  - The six stand-in unit checks by node id (`values_have_no_memory`,
    `values_are_true_and_typed_as_cpythons`, `names_and_refuses`,
    `holds_numeric_values_as_wasm32_stores_them`, `holds_void_pointers_and_casts_them`,
    `types_import_only_what_a_start_has_loaded`): 6 passed, exit 0.
  - `tests/checks/test_v1_3_scipy.py::test_the_sobol_options_need_nothing_writable` and
    `::test_ndarray_ctypes_gives_the_arrays_address`, both binaries: 4 passed in 40 s, exit 0.
  - 27 probes of the stand-in (loaded at wasm32's sizes) against host CPython 3.14.2's `ctypes`:
    truth of `c_float(±1e-46)`, `c_longdouble(-0.0)`, `c_bool(2)`, `c_ubyte(256)`, `c_double(inf)`;
    `c_double` of `Decimal`, `Fraction`, `True`, `10**400`, `None`, `1j`, `array('d')`;
    `c_void_p` of `1.0`, `False`, `c_int(1)`; `hash`, a `set`, `==`; both `cast`s; `.value`
    assignment of an int, a float and a str. 24 agree exactly; the three that differ are
    `bytes()`, `bytearray()` and `memoryview()` of a value, which now raise `OSError` by design
    (High 1's fix; CPython returns the bytes).
  - The hard-exit row on 037's set (`build/038/set-037`, `40281c40`) and on 038's, through the
    judge's own driver, five argument variants (Finding 3).
  - main's set (`build/artifacts` in the main tree, `f12cd25c`) against 038's zip by member:
    exactly two members differ, `ctypes/_types.pyc` and
    `scipy/io/_fast_matrix_market/__init__.pyc`.

## Acceptance criteria against evidence (the build review's verdict)

1. **High 1, an instance's buffer refuses with `OSError`** — met. `_SimpleCData.__buffer__`
   raises `OSError(_MSG)` (READ, `recipes/ctypes_stand_in/_types.py`); the unit row was seen
   failing first with `TypeError: cannot convert 'c_double' object to bytes` (READ,
   `build/038/logs/review-rows-seen-failing.log`) and passes (EXECUTED). On the rebuilt set,
   `cpython-b`'s `no-ctypes` class still holds as a gap, its entry unchanged (READ,
   `upstream-classes-after.log`: 3 passed, 1 xfailed), and `cpython-b` keeps 9,536 passes
   (READ, `build/038/latest-upstream-ctypes.json` against main's `accepted.json`). CI (my run): the four Linux shards that carry these groups (upstream-numpy-a for `cpython-a`,
   upstream-frame for `cpython-b`, upstream-pandas-small for `cpython-c`, upstream-numpy-b for
   `numpy-others`) passed with "lost 0 · grew 0" (gained 1, 0, 1 and 1: the classes now empty), no "remove the gap" in any log, and record
   5,865, 9,536, 7,877 and 7,277 passes; `cpython-b-no-ctypes` is among upstream-frame's 7
   xfailed (gaps matched).
2. **The three emptied classes are a named judge change** — met. `--accept-judge` names them:
   "the no-ctypes classes of cpython-a, cpython-c and numpy-others emptied (their expected lists
   empty, their classes kept with a closed-by-038 reason) and their three [[gap]] entries
   removed … cpython-a +1, cpython-c +5 and numpy-others +8 passes" (READ). **The same shape as
   spec 086's `no-missing-stdlib-info`** — yes (READ): an empty
   `tests/upstream/expected/<group>/<id>.txt` kept, the `[[expected]]` entry kept with its
   `outcome` and `match` unchanged, `reason = "closed by spec NNN: …"`, `closes_with` the
   specification, and no `[[gap]]` entry (086's class has none in `known_gaps.toml`). The pass
   counts the claim list gives match the builder's record against main `d066695`: `cpython-a`
   5,864 → 5,865, `cpython-c` 7,872 → 7,877, `numpy-others` 7,269 → 7,277, fuel +0.044%,
   +0.038%, −0.038%, and `cpython-b` +0.067% at the same 9,536 (READ). This is the build
   review's own fix text, not a weakening: the classes are empty because no test meets the
   stand-in's `OSError` in those groups any more, and the judge's "remove the gap" demanded it.
3. **Medium 2, CPython's truth** — met. `__bool__` packs a float as `<d` and compares with
   eight zero bytes, else `bool(value)`; `c_void_p`'s NULL is `None`, so false (READ). EXECUTED
   against host CPython: `-0.0`, NaN, `inf` and `c_float(-1e-46)` are true; `c_float(1e-46)`
   (single precision rounds it to 0) and `c_ubyte(256)` are false; all as CPython. Seen failing
   first (`bool(c_int(0))` was `True`, READ). The README now says it.
4. **Low 3, argument types and hashing** — met. `_address` requires `isinstance(value, int)`
   (`PyLong_Check`; a `bool` is one); `_double` takes `__float__`, then `__index__`, else
   `TypeError`; `__hash__ = None` (READ). EXECUTED: `c_void_p(1.0)`, `c_void_p(c_int(1))`,
   `c_double(array('d'))`, `c_double(None)`, `c_double(1j)`, `hash()` and a `set` all raise
   `TypeError` as CPython's do; `Decimal`, `Fraction` and `True` convert as CPython's; `cast`
   of a `c_void_p` still works (READ: `cast` makes `c_void_p(obj.value)`, so the instance never reaches `_address`), and the
   guest address check passes on both binaries.
5. **Low 7, the Sobol options check** — met, not weakened. Seen failing on 037's set with
   shgo's `QH6421` (READ, `sobol-options-on-037-set-2.log`). Its first version failed on 038's
   set twice for the check's own reasons: a numpy `bool_` in the JSON (now `bool(...)`), then
   `maxiter=50`, under which differential_evolution stops before `success`. `maxiter=1000` is
   scipy's default and `popsize=16` is next to its default 15, so the check now runs the
   options as a README reader would; the assertion is unchanged in strength (`success` and
   `fun < 1e-8` for both). Its differential_evolution half also passes on 037's set (the spec
   says so in item 11), so shgo is the half that discriminates; Sobol's own points are guarded
   by 037's `test_sobol_needs_nothing_writable`. Note 6.
6. **Low 6, the local full judge** — answered in the phase-3 notes: the release workflow's run
   stands for it, as AGENTS.md rule 3a now says (READ).
7. **A new dry run red only on growth** — met (EXECUTED, run `39416337718`): red only on GREW lines (103, 15 and 1), no G7, no lost
   pass; the build review's five non-growth red lines are gone.

## Findings, most severe first

1. **The claim list predicts the fast tier and four upstream groups only** (`context/specifications/038-scipy-second-milestone.md`,
   "Rows that grow" and `--accept-growth`) — Medium: rows the lane's full judge will see grow
   are not claimed (the checklist: a row changed and not claimed is Medium). "180 rows move
   against main" is `build/038/growth-vs-main-3.txt`, which is the fast tier: the slow rows and
   all sixteen upstream groups are `deselected` in it, and the builder measured four groups by
   node id (`latest-upstream-ctypes.json`). The release records of run
   `39415728849` on `ecc2423` (READ: `record-macos-own-guest-failed-1`,
   `record-macos-upstream-macos-failed-1`, compared with main's `accepted.json` row by row)
   show 28 grown darwin-arm64 rows that no line of the claim list names:
   `test_upstream_suite[cpython-fs]` +0.046% (+29.2 M fuel; the job's one GREW line), and 27
   slow job rows, all at most +0.096% (`test_scipy_lapack_job_matches_native[snapshot]`;
   `test_symbolic_job_matches_native` +0.082%, the rest below +0.07%): the data-stack,
   default-profile, matplotlib, regex, lxml-workaround and scipy job goldens. They are the same
   causes the flags already name (the stand-in's first type lookup, import scipy) and all are
   small, which is why this is not High. Not measured on darwin-arm64 at all on this set:
   `numpy-core`, `cpython-archives` and the eight pandas groups (the Linux shards record their
   own fuel, which the ratchet does not compare with darwin's), so the lane meets them unpredicted.
   **Closes with** (the builder's, `context/` only, no rebuild): in "Rows that grow", "From run
   39415728849's records against main: `test_upstream_suite[cpython-fs]` +0.046% (test_io's
   no-ctypes tests make the stand-in's first type lookup) and 27 slow job rows +0.001% to
   +0.096% (scipy's three jobs, `test_symbolic_job_matches_native` +0.082%, the rest below
   +0.07%); `numpy-lib` −0.074%. Not measured on darwin-arm64 on this set: numpy-core,
   cpython-archives and the eight pandas groups, expected within ±0.1% for the same causes, or
   measured by node id: <numbers>"; and the same in `--accept-growth`, replacing "180 rows move
   against main" with "180 fast-tier rows, 27 slow rows and cpython-fs move against main".
2. **The flags' byte rows are 037's, not main's** (`context/specifications/038-scipy-second-milestone.md`,
   "Rows that grow" and `--accept-growth`) — Low, with its fix text (no round needed). The specification is now
   stacked on main `d066695`'s accepted set (`f12cd25c`, which has 096's lxml line in the zip),
   and `build/038/growth-vs-main-3.txt` gives the zip +3,192 bytes (44,445,945 → 44,449,137),
   `python.wasm` −2,786 (84,794,273 → 84,791,487) and the snapshot −5,638 (89,468,144 →
   89,462,506). The text says +3,221 "against 037's set `40281c40`", −2,778 and −5,611.
   **Fix text:** in "Rows that grow", "the zip's bytes, +3,192 against main's set `f12cd25c`
   (two members: `ctypes/_types.pyc` and `scipy/io/_fast_matrix_market/__init__.pyc`).
   `python.wasm` (−2,786) and the snapshot (−5,638) shrink."; in `--accept-growth`, "the zip
   +3,192 bytes in two members".
3. **The hard-exit row's growth names no cause** (`test_v1_4_embedding.py::test_unbuffered_output_survives_a_hard_exit[snapshot]`,
   +0.39%, 1,265,275 → 1,270,242) — Low, not Medium: the growth is real, deterministic and
   small, and it can be stated. EXECUTED through the judge's driver on 037's set and 038's
   (identical to the recorded numbers, so it is not noise):

   | program on the snapshot | 037's set | 038's set | move |
   |---|---|---|---|
   | `-c "import os; os._exit(0)"` | 1,017,809 | 1,018,549 | +740 |
   | `-Xutf8 -c` the same | 1,023,635 | 1,024,375 | +740 |
   | `-u -c` the same | 1,150,053 | 1,154,542 | +4,489 |
   | `-c "print('kept'); …"` | 1,124,047 | 1,125,205 | +1,158 |
   | the check: `-u -Xutf8 -c "print('kept'); …"` | 1,265,275 | 1,270,242 | +4,967 |

   So +740 fuel is in the snapshot's start and about +3,750 in rebuilding stdio unbuffered
   under `-u`; `sorted(sys.modules)` and the stdio objects are identical on both sets with and
   without `-u` (EXECUTED), so nothing is imported differently. INFERRED: a layout effect of the
   rebuilt snapshot heap (its bytes shrink 5,638), not 038's code. The row is large in percent
   only because `os._exit` skips finalization: the base is 1.27 M where every other snapshot
   row is about 50 M, and those rows move by −17,101 to +19,228 fuel against main; the plain
   twin moves +0.014%. **Fix text** for "Rows that grow" and `--accept-growth`, replacing
   "cause not identified": "+4,967 fuel, measured on 037's set and 038's: +740 in the
   snapshot's start and about +3,750 in `-u`'s unbuffered stdio, the same modules loaded; a
   heap-layout move of the rebuilt snapshot, large in percent only because `os._exit` skips
   finalization (a 1.27 M base where other snapshot rows are about 50 M and move up to ±19 k)".
4. **The CHANGELOG does not name the rules the fixes added** (`CHANGELOG.md`, 038's entry) —
   Low, with its fix text (the builder's: not under `context/`). The README's stand-in paragraph says an instance is false at zero
   and has no memory; the CHANGELOG's **Changed** sentence, the release note a user reads,
   does not. **Fix text,** after "give the array's address.": "An instance is false when its
   value is zero and unhashable, as in CPython; `c_void_p` takes only an `int`; its bytes
   cannot be read (`bytes()` and `memoryview()` of it raise `OSError`)."
5. **Note.** `build/progress/latest.json` in the 038 worktree was rewritten at 07:42 by my
   first unit node run (I did not save it first). The builder's own records under
   `build/038/` (`latest-fast-3.json`, `latest-upstream-ctypes.json` and the logs) are
   untouched; nothing in the claim list reads the overwritten file.
6. **Note.** Low 7's check guards the README's sentence; only its shgo half fails without 038's
   patch 0004. That is acceptable: a check of Sobol's points already exists (037's
   `test_sobol_needs_nothing_writable`, a gap closed by 038).
7. **Note.** The builder's self-check list was not in my brief. Its items are evidenced in the
   phase-3 notes: rebased on main `958a22b` today, the run on `ecc2423`, numbers from this
   build labelled, the claim list and flags with each reason beginning "038:", checks seen
   failing first, CHANGELOG under the one unreleased section.

## Constitution checks

- **§4.1:** no new patch; the two carried patches are unchanged by the delta (READ: no
  `recipes/patches/` or `downloads/SHA256SUMS` line in `git diff 1073d68..ecc2423`). The
  stand-in is a recipe file.
- **§4.4, §4.15:** nothing new reaches the host; the delta narrows what the stand-in accepts
  and makes reading a value's bytes raise.
- **Tests count operations:** yes; the new rows record fuel only.
- **AGENTS.md rule 4:** the only judge edits are the three emptied classes, their gap entries
  and the new rows, each named in `--accept-judge`; no golden, allowance or other gap moved
  (READ).
- **§7:** nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Medium 1 — the builder's (a claim-list and flags edit in `context/`; no rebuild, no rerun:
   the numbers are in run `39415728849`'s and `39416337718`'s records, identical).
   *Answered by the builder:* "Rows that grow" and `--accept-growth` take the fix text:
   `cpython-fs` +0.046%, `numpy-lib` −0.074%, the 27 slow job rows +0.001% to +0.096%, and the
   ten groups not measured on darwin-arm64 on this set named one by one (`numpy-core`,
   `cpython-archives`, the eight pandas groups), expected within ±0.1% for the same causes;
   `--accept-growth` says "180 fast-tier rows, 27 slow rows and cpython-fs move against main".
2. Low 2 — the builder's, or written in by the reviewer once the branch is handed over (text above).
   *Answered by the builder:* the byte rows are main's, as the fix text gives them: the zip
   +3,192 against `f12cd25c`, `python.wasm` −2,786, the snapshot −5,638, in "Rows that grow" and
   `--accept-growth`.
3. Low 3 — the same (text above).
   *Answered by the builder:* "cause not identified" is replaced by the reviewer's measured
   cause, in the phase-3 fuel line and `--accept-growth`.
4. Low 4 — `CHANGELOG.md` is not under `context/`, so the builder's (text above).
   *Answered by the builder:* the CHANGELOG's Changed sentence takes the fix text after "give the
   array's address."; the heading stays "0.1.0a8 — unreleased".
   The run ids `39415728849` and `39416337718` and their result are in the phase-3 note.

## Verdict

Lands once Medium 1 is answered: the claim list and `--accept-growth` name the rows the full
judge will see grow beyond the fast tier (`test_upstream_suite[cpython-fs]` +0.046% and the 27
slow job rows up to +0.096%, from run `39415728849`'s records) and say how the upstream groups
nobody measured on darwin-arm64 are predicted; High 1, Medium 2, Low 3 and Low 7 are fixed as
the build review asked, and my run is red only on growth.

## One line

The fixes are right (a value's bytes refuse with `OSError`, CPython's truth and argument rules
agree with CPython on 24 of 27 probes and differ only where memory is refused, the Sobol check is
meaningful, the three empty classes follow spec 086's shape under `--accept-judge`) and my run is
red only on growth; the claim list just has to name the slow and upstream rows that grow.
