# Review of 111 — the filesystem along the WASI seams (the build)

- **Date:** 2026-10-21
- **Reviewer:** a fresh agent (Claude). It wrote none of 111, did not review it before the build,
  and wrote and reviewed none of the chain 103 to 109.
- **Reviewed:** `spec/111-the-filesystem-along-the-wasi-seams` at `5f9a7c1` (code commit
  `46ddf0b`), based on `5af0a42`; the diff `git diff 5af0a42..5f9a7c1`. Main is now `58f108f`.
  `5af0a42` is its ancestor, and `git merge-tree 58f108f 5f9a7c1` merges with no conflict
  (EXECUTED). The rebase is the lane's.
- **Box:** 75 minutes (the lane's). Runner code with a judge change, read as build-class. Done
  inside the box.
- **Run:** the builder's run **39551619591** on `f763178`. `git diff --stat f763178 5f9a7c1` is
  the specification file alone (EXECUTED), so the run's tree is the reviewed code. The reviewer
  dispatched no run of its own, as the lane asked. Read back with `gh run view --attempt 1|2
  --json jobs` (EXECUTED):
  - Attempt 1: every job green but `judge (ubuntu-24.04, upstream-plot-a)`. That job failed on
    the network before any test.
  - Attempt 2 re-ran that job and the gather. Every judge job is green on the three systems,
    including the four Windows legs (own-runner, own-guest, own-embedding, upstream-windows).
  - `release-record-2`, `scoreboard.txt`: `774/866 pass · 85 gap · 7 blocked · 0 fail (unit suite
    4644/4674, 30 skipped)`; rules 60/61 (1 blocked). The one red line is
    `RED: G7 the newest acceptance is not on the release's set`. No GREW line.
  - `record-windows-own-runner` (`win32-amd64`): `tests/unit/test_runner_mounts.py` was
    collected, and the suite passed 587 of 599 (12 skipped). The five changed or new rules rows
    are deselected in that shard, as every rules row is, and run in another.
  - Run 39541506877 on `91f66da` (the pre-rebase build), also read: everything green but the
    gather, whose red line is G7 alone.
- **Re-ran (EXECUTED, in the worktree):**
  - `uv run pytest tests/unit/test_runner_mounts.py tests/unit/test_runner_package.py
    tests/checks/test_rules.py -q -p no:cacheprovider` → 136 passed, 1 skipped, exit 0
    (`build/111-review/units.log`). **A process note:** `build/lane.lock` existed in the main
    tree at the time. The lane allowed the unit files, but `test_rules.py` is a checks file, so
    its whole file ran where only node ids were allowed. It took 35 s, in the worktree only, and
    touched no main-tree record.
  - `uv run ruff check src tests` and `uv run ruff format --check src tests` → clean (155 files).
  - `uv run mypy` → `Success: no issues found in 22 source files`.
  - `uv run python tests/harness/api.py --check` → exit 0. `tests/public_api.txt` is not in the
    diff.
  - No fast tier: `build/lane.lock` existed.
  - A mechanical move check (scratchpad `cmp.py`): every function and method of the base's
    `mounts.py` was compared, by normalised AST, with its twin in the five modules (criterion
    2, below).
  - Three probes: the import rule's `_sibling_imports` over a stand-in file (Low 1); the
    table-write scanner over a stand-in file (Low 2); the aliased-write read that the pre-build
    review asked for.

## The builder's self-check

Every item is present.

- **Base:** `5af0a42`, not main's tip. The lane's `58f108f` came after, and it merges cleanly
  (above).
- **Fast tier:** it ran on the `727bd4c` base "less the namespace comment", not on the reviewed
  tip. The CI run on the reviewed code's tree covers this.

Neither item is a finding.

## Acceptance criteria against evidence

1. **Modules and sizes** — met (EXECUTED, `wc -l`): `mounts.py` 361, `_fs_memory.py` 317,
   `_fs_table.py` 681, `_fs_descriptors.py` 513, `_fs_paths.py` 644. `ALLOWED = {"tools.py": 2449}`.
2. **The split is a move** — met (EXECUTED). Every one of the base's functions and methods was
   compared with its twin by normalised AST. The normalisation:
   - `self` is read as `files`;
   - `self._x(...)` becomes `_x(files, ...)` for a helper that is now free, and `_x(...)` for the
     six that lost the table;
   - annotations are dropped, and docstrings are de-indented.

   Every base function exists in the new modules, and all but eleven are identical. The eleven
   are exactly the landing notes' list:
   - `__call__`: `HANDLERS[name](files, …)` in place of `cast(int, getattr(…))`;
   - `_filestat` and its two callers: the caller computes `ino_of(path)` and passes
     `entry.mount.dev`. `ino_of` is a pure hash, so moving it earlier changes nothing;
   - `_fd_close`: `_unhold`, and `_owe` in place of the `del`/store pair;
   - `_fd_readdir`: `_relist`;
   - `_fd_renumber`: `_renumbered`;
   - `_path_open`: `_hold`;
   - the four `_Memory` methods differ only by the reviewer's own `self` rename.

   Each of the five new methods is the replaced statements verbatim, in the same order. For
   example, `_relist` computes `held - entry.held` before it assigns `entry.held`, as before.

   Every module-level statement of the base appears verbatim in one of the five modules. The
   statements that are new are the three `HANDLERS` tables and the two `TYPE_CHECKING` imports.
   No name is defined in two modules but `HANDLERS`, so every global a moved body reads is the
   same object it was.
3. **No by-hand table writes** — met:
   - `test_the_handlers_change_the_table_only_through_its_methods` is green (EXECUTED).
   - It was seen failing with the ten hits of Decision 1 (READ,
     `build/111/red-handlers-verbatim-hits.txt`).
   - The widened grep on the tip exits 1 (EXECUTED).
   - The aliased-write read that the pre-build review asked for: the only aliases are
     `forwards = files.forwards` in `_zeroed` (`_fs_descriptors.py:425`) and `_source_type`
     (`_fs_paths.py:589`). Both read or write the guard's wasm page, never the table's Python
     state (EXECUTED, grep).
   - No handler writes a row's `held` (EXECUTED, grep).
4. **The dispatch equals the signatures** — met (EXECUTED, the unit row green). The row checks
   that `_Files` has no `_<call>` attribute, so the old `getattr` path cannot be reached. The
   row also holds that `HANDLERS` is the union.
5. **Allowances and the import rule** — met (EXECUTED): `ALLOWED` without `mounts.py`;
   `FILESYSTEM_IMPORTS` as Decision 5 writes it. The `mounts.py` row is now empty: the old rule
   let `mounts.py` import the engine seam, and the new one does not. The grep for `from \.` or
   `import wasi_python` in `mounts.py` finds nothing. Seen failing: READ
   (`build/111/red-rules-on-base.txt`). Low 1 is about this check.
6. **The five new rows** — met: green (EXECUTED), and seen failing (READ:
   `red-unit-on-base.txt`, `red-api-lists.txt`, `red-handlers-verbatim-hits.txt`).
7. **No function over 80 lines** — met (EXECUTED). The ast one-liner gives the same counts on the
   base and the tip. `_path_open` is 78 lines, the longest in the five modules. `LONG_FUNCTIONS`
   is not in the diff.
8. **The test seams** — met (EXECUTED, `git diff --stat`):
   - The hostile-guest, grants, sweep, embedding and sessions files are not in the diff.
   - `SEAM_ALLOWED` is not in the diff.
   - `files.py` changes its two import lines only.
   - `test_runner_mounts.py` changes its imports, the moved names' use sites, the
     `_source_type` row's injection and the three new rows.
   - **The injection is equivalent (READ).** The old patch swapped the folder after
     `_source_type` returned 0. The new `forward` patch swaps it after the source's `stat=True`
     `path_filestat_get` at `STAT_PATH` answers 0. That is before `_source_type` reads byte 16
     of the page, but the page already holds wasmtime's answer, so the read still sees a folder.
     The rename that follows meets the same swapped link. If the swap never fired,
     `os.readlink` would raise, so the row cannot pass with no race.
9. **No verdict moved** — met as far as this worktree can show:
   - Fast tier: 2,605 passed, 0 failed, lost 0, grew 0 (READ, `build/111/fast.log`).
   - CI: 0 fail and no GREW line (EXECUTED, read back).
   - The `sameness.py --claims` line against the wave's record is the lane's to print.
   - The claim list's shape fits `sameness.py`: changed unit rows are tallied by `units = 3`
     (READ, `tests/harness/sameness.py:373`).
10. **Public API unchanged** — met (EXECUTED).
11. **ruff and mypy clean; `Any` and `type: ignore`** — met in substance:
    - ruff and mypy are clean (EXECUTED).
    - `type: ignore` is 2, as before; `cast` is 1, against 2 before.
    - `Any` is 73 lines against 69, which is over the criterion's letter (see Note 1).
12. **The dispatch** — met (EXECUTED, read back above). Every red line is G7.

## Findings, most severe first

No High finding and no Medium.

1. **Low: the import rule counts the `else:` of `if TYPE_CHECKING:` as typing-only**
   (`tests/checks/test_rules.py`, `_sibling_imports`).
   - **The defect:** the walk passes `typing_only=True` to every child of the `If`, so the
     `orelse` branch inherits it, and so does the test itself. A runtime import placed in the
     `else:` is reported as typing-only. The typing column then admits it, as `_fs_table` is for
     both handler modules. Decision 5 says the flag means "sits under `if TYPE_CHECKING:`", and
     the `else` branch does not.
   - **Failure (EXECUTED probe):** a file containing `if TYPE_CHECKING: from ._fs_table import
     _Files` / `else: from ._fs_table import _Files as F` gives `[(3, '_fs_table', True), (5,
     '_fs_table', True)]`. Line 5 is a runtime import, yet the check passes it.
   - **What else would catch it:** `test_runner_package.py`'s order rule, as changed here, lets
     any filesystem module import any other, so it would not. At module level the cycle would
     fail at import time anyway. Inside a function it would go unseen: an upward runtime edge
     in a chain the rule promises is acyclic.
   - **Fix (code, the builder's):** in the walk, when `node` is an `ast.If` whose test is the
     name `TYPE_CHECKING`, push `node.body`'s children with `True`, and push `node.test` and
     `node.orelse` with the inherited flag. Add the probe's two lines as a case the check
     reports, seen failing first.
   - **No case today:** neither handler module has an `else:` there (READ).
2. **Low: the accept-judge flag says "for every form of a write"; the row holds the five forms
   the specification names** (the landing notes' "For the lane, as built", and
   `scan.table_write_hits`).
   - **Failure (EXECUTED probe):** the scanner reports `files.held.add(n)` and
     `files.table[n].held += 1`. It reports nothing for any of these:
     - `held = files.held; held.add(n)`;
     - `heapq.heappush(files.free, n)`;
     - `files.owed.popitem()`;
     - `files.held.difference_update(...)`;
     - `setattr(files, "staged", 0)`.
   - **No case today:** the handlers use none of these (EXECUTED grep). The flag's sentence
     still says more than the check holds.
   - **Fix (context only):** in the flag, read "for the five forms of a write the
     specification names" for "for every form of a write".
   - **Optional (code, the builder's):** widen `TABLE_MUTATORS` with `popitem`, `insert`,
     `difference_update`, `intersection_update`, `symmetric_difference_update`, `sort` and
     `reverse`; also report a call with `files.<field>` as its first argument to `heapq.*`, and
     `setattr(files, …)`.

**Note 1, criterion 11's `Any` letter.** The five modules have 73 `Any` lines against the
criterion's 69. Lines outside the `from typing import` lines are 68 on the base and 68 on the
tip (EXECUTED). The extra lines are the four new modules' import lines. The landing notes answer
this in writing (Differences 4), and the answer is right. Nothing to fix.

**Note 2, the judge changes beyond the specification's list.** Each was read, and neither
weakens the judge:
- **`test_runner_package.py`'s order rule:**
  - `mounts` leaves `BESIDE` for `FILESYSTEM`, which may import only filesystem modules at
    module level. The rules row's per-module table is the stricter hold on that.
  - The four runner modules that could import `mounts` may now import any of the five.
  - The six `LATE` rows name the module each late import now reads (READ, the `_call.py` and
    `_sessions.py` diffs).
- **`test_the_rename_and_readdir_guard_match_the_floor`:** it reads the five modules' text where
  it read `mounts.py`'s. That is the same code, spread over five files. The "guard may go"
  direction is now stricter.
- **The retired row:** `test_mounts_imports_only_the_engine_seam` is succeeded by a check that
  holds more modules and denies `mounts.py` the engine seam it allowed. Low 1 is the one gap
  in it.

**Note 3, `__call__` on an unknown name.** The new dispatch raises `KeyError` where the old one
raised `AttributeError`. Both are inside the same `try`, and neither can be reached: the shared
function passes only the names in `SIGNATURES`, and the unit row of criterion 4 holds the two
tables equal to it.

**Note 4, the platforms.** The base's `mounts.py` had no platform branch. The five modules have
none either: `sys.platform`, `os.name` and `platform.system` appear only in `_platform.py`, 3
lines on both commits (EXECUTED). Junctions, read-only grants and case folding are judged in
`_places.py`, `_platform.py` and wasmtime's own forwards. Those are untouched but for one import
line, and every moved body is AST-identical. So no Windows-only or macOS-only branch moved, and
there is none that nobody ran. The Windows own-runner, own-guest and own-embedding legs ran the
mounts, hostile-guest and embedding rows green (EXECUTED, read back). `_HOST_ERRNO`, the one
host-dependent table, stays in `mounts.py` unchanged.

## Constitution checks

- **§4 constraints:**
  - No artifact byte, no pin, no recipe and no guest import or export changes.
  - Tests count operations.
  - The code names no specification: the citation measurement is 0 and 0, and 109's check is
    green.
  - Everything is under uv.
- **§5.6:** the builder's run on the reviewed code's tree, read back; criteria against evidence;
  ranked findings.
- **§7 never-do list:** nothing tripped.
  - No check was weakened to pass. The retired check's successor is stricter, and the two
    changed checks follow moved text, each with a reason in the flag.
  - No golden output, gap or progress file changed.

## Structure (the rubric)

Kind: parallel-safe, not structural. Checklist 4a: the diff adds no module-level mutable (the
three `HANDLERS` are upper-case displays that are only read, which 105's check admits), no
private-API use, no platform branch, no test seam and no function past 80. It splits a concern;
it adds none. The Kind line is right.

### Measurements (EXECUTED; `5af0a42` → `5f9a7c1`, the README's commands)

| what (row) | then (`5af0a42`) | now (`5f9a7c1`) |
|---|---|---|
| module sizes (R7) | `tools.py` 2,449; `mounts.py` 2,206; 12,873 in all | `tools.py` 2,449; `mounts.py` 361, `_fs_table.py` 681, `_fs_paths.py` 644, `_fs_descriptors.py` 513, `_fs_memory.py` 317; 13,185 in all |
| functions over 80 (R7) | `runner.py` 4, `tools.py` 2, `_call.py` 1, `_process.py` 1, `_sessions.py` 1 | the same; the filesystem's longest is `_path_open` at 78 |
| module-level mutables and locks (R4) | 0 lines | 0 lines |
| private-API uses (R3) | `_wasmtime_ffi.py` 84, `_places.py` 1, `tools.py` 1 | the same; the engine seam is imported only by `_fs_table.py`, at the base's three sites |
| platform branches (R5) | `_platform.py` 3 | `_platform.py` 3 |
| private names the judge patches (R6) | 30 distinct (`mounts_module._Files` `_source_type` and `__call__`) | 29 (`_fs_table._Files.__call__` alone) |
| `Any` / `type: ignore` (R7) | 338 / 25 | 342 / 25 (+4 import lines; uses 68 → 68 in the filesystem) |
| type checker (R7) | mypy clean | mypy clean, 22 files |
| citations (R7) | 0 / 0 | 0 / 0 |

### The eight rows

| row | then | now | reason |
|---|---|---|---|
| R1 Contract | Strong | Strong | `public_api.txt` is byte-identical, `__all__` and the eight public types are unchanged, and `api.py --check` exits 0 |
| R2 Safety | Strong | Strong | every errno and limit is the same, by AST identity; the table's invariants are kept by its own methods, held by a rules row |
| R3 Layering | Adequate | Adequate, firmer | the five modules form a chain with `mounts.py` at the bottom; the runtime graph is acyclic; the engine seam is reached from one module; Low 1 is a gap in the rule that holds this, not in the code |
| R4 Process state | Adequate | Adequate | no new mutable; `HANDLERS` are read-only; the table's back-reference-free shape keeps the GC row's zero |
| R5 Portability | Strong | Strong | no platform branch in the five (Note 4) |
| R6 Testability | Adequate | Adequate, firmer | one class-attribute patch of a private name is gone; three rows drive the memory, the table and the dispatch without wasmtime |
| R7 Evolvability | Adequate | Adequate, firmer | the 2,206-line module becomes five files, none over 681 lines; no function over 80; `ALLOWED` has one entry; `Any` uses are unchanged |
| R8 Operability | Strong | Strong | `record()`, `FileRecord`, the trap strings and the fuel rule are unchanged in body |

The rows R3, R6 and R7 move as the specification said. None moves toward Weak.

**Structural verdict:** the structure holds.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Low 1 —
2. Low 2 —

## Verdict

Lands: the move is exact by AST comparison, the judge is not weakened and the ceilings only
shrink. The two Lows are answered in writing or fixed per their text, and the lane reads any
code fix against the finding.

One line: `_Files` moved into four modules without changing a single behaviour, and the build
lands with two Low findings on how tightly its new checks are worded.
