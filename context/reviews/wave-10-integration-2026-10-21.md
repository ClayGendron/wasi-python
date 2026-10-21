# Review of wave 10's integration (045, 110, 111)

- **Date:** 2026-10-21
- **Reviewer:** a fresh agent (Claude Opus 5.5). It wrote none of 045, 110 or 111 and reviewed
  none of them before (their pre-build and build reviews were other agents'). It is the wave's
  integration reviewer (AGENTS.md rule 8; constitution §5.7).
- **Reviewed:** the wave's tip **`a001b5c5`**, linear on main `d8fc73ff` (wave 09 and the owner's
  answers to questions 108 to 111): 045 (`d8fc73ff..ed731606`, 11 commits, the last H1's fix),
  then 110 (`..a426de8d`, 8), then 111 (`..e64508e4`, 7), then the lane's fix, the oracle lock
  check (`2db86e00`, `a001b5c5`); no merge commit. The review began on the first tip `00aa7b3d`
  (045 at `ba38a6a9`, 110 at `448b24d0`); sections 1 to 2 were done there, section 2a reads the
  restack and 2b the lane's fix. The lane's
  restack of the entries' own branches (045 `3b7f6abf`, 110 `842e32e4`, 111 `329fd29f`, all on
  `265607bd`) over the one context-only main commit: `git range-diff 265607bd..329fd29f
  d8fc73ff..00aa7b3d` maps all 25 commits `=`, and `git diff 329fd29f 00aa7b3d` is
  `git diff 265607bd d8fc73ff` (four `context/` files) but for one index line (EXECUTED).
- **Run:** the dry run of record **39588461408** on `a001b5c5`, read in section 4. The first,
  39584711213 on `00aa7b3d`, was cancelled by the lane after H1 before any judge job ran. Base for the deltas: main's step-7 dry run **39572424790** on `111d56f4` (40 jobs green).
- **Ran:** reads; in a `git clone --shared` of the repository in this agent's scratchpad at
  `00aa7b3d` (no worktree, no branch switch in the main tree): `ruff check src tests` → "All
  checks passed!"; `ruff format --check src tests` → "159 files already formatted"; `mypy
  --strict src/wasi_python` → "no issues found in 24 source files"; `tests/harness/api.py
  --check` → exit 0; seventeen rules checks by node id (the ceiling, the 80-line rule, 111's three
  new rows, the seam rule, the engine-seam rule, mypy, the patches rule, both citation rules, the
  guard floor, once-bound names, the specification-shape and landed-review rules, the
  own-suite rule, the tracked-artifact rule) → 17 passed; the touched unit files
  (`test_runner_package.py`, `test_scan.py`, `test_tools.py`, `test_statsmodels_build.py`,
  `test_runner_mounts.py`, `test_runner_tools.py`, `test_async_tools.py`, `test_guest_tools.py`,
  `test_artifact_rules.py`, `test_build_progress.py`) → 781 passed, 7 skipped; `--collect-only` of
  `tests/unit` and `tests/checks` at `d8fc73ff`, `ba38a6a9`, `448b24d0` and `00aa7b3d`; `uv tree
  --frozen --offline` of the oracle project at seven commits, `uv lock --check` and `uv export
  --frozen` on a repaired copy; the oracle synced online into the scratchpad from the repaired
  lock and every golden job run natively under hash seeds 0 and 1 (section 2). At `a001b5c5` in the same
  clone: the lock check's rules row and `test_scan.py` (260 passed), ruff on `tests`, both
  `--collect-only` counts, and probes of `scan.lock_errors` (section 2b). The lane's judge record
  `build/wave-10/lane/judge-1.json` was read with `predict.py` and `sameness.py`. No judge tier ran;
  no build ran; nothing was dispatched. `build/lane.lock` was absent when I started.
- **Box:** 45 minutes for the reading, plus the wait for the dry run.

## 1. Each entry's rebase against its reviewed diff (EXECUTED)

Method, as wave 09's: per file, `git diff <old base> <old tip>` against `git diff <new base> <new
tip>`, `index`, `@@` and `diff --git` lines dropped, compared line by line; then again with
comment lines (`#`) dropped; and `git range-diff` beside it.

### 045 (`dbecd2d..3aa663a`, its build review's range) against `d8fc73ff..ba38a6a9`

`git range-diff`: seven reviewed commits map one to one; four `=`, three changed
(`9d8baad`→`751357c7`, `7be1837`→`01e08050`, `3aa663a`→`943cf861`: the rebase hunks), then three
commits no build review read: `2e5503a0` (the build review, copied), `092a5613` (its
Disposition: README and `context/` only, EXECUTED `git show --stat`) and `ba38a6a9` (the Rebase
bullet, README and `context/`).

| file | interdiff lines (all / code) | what they are | verdict |
|---|---|---|---|
| every file under `scripts/`, `recipes/`, `src/`, `tests/`, `downloads/`, `.github/`, `CHANGELOG.md` but one | 0 / 0 | — | identical |
| `scripts/steps/60_link.sh` | 10 / 0 | the header's list (named: wave 09's "scipy and numpy with one OpenBLAS" with 045's "statsmodels") and the staged-input checks (named: wave 09's `libnumpy_lapack_shims.a` check, then 045's step-59 check, its comment without the citation) | clean: (a), comments and context only; at the tip both `die` lines stand (lines 42 and 44), and `weak_archives` and the link line carry wave 09's numpy shims unchanged |
| `README.md` | 8 | the artifact row and the sizes row (both named), with this build's 99.4 / 104.5 / 53.9 MB and "the wheel 98.3 MB" | clean; the `@W@ / @S@ / @Z@` placeholders of `943cf861` are gone at the tip (EXECUTED, `grep -c` 0) |
| `context/` | — | the specification's notes and the build review | context |

So the reviewed code reached the tip unchanged. **But the interdiff cannot see H1**: 045's hunk to
`tests/jobs/oracle/uv.lock` is the same text it was on `dbecd2d`, and on wave 09's base that text
is wrong (section 2).

### 110 (`5af0a42..54fe623`) against `ba38a6a9..448b24d0`

`git range-diff`: the five reviewed commits map one to one, four `=`; `e6728fa`→`1e14c0fb`
differs by its `CHANGELOG.md` context (the named hunk: 100's entry above 110's, both kept); then
`24e13ddb` (the build review), `1bc485f7` (its two Lows) and `448b24d0` (the Rebase bullet).
Per file outside `context/`: every interdiff 0 but `tests/unit/test_tools.py`, 19 lines, which
is L2's fix: `test_a_refused_call_records_its_operation_and_tool`, the build review's fix text
(a non-string tool, a tool not offered, arguments that are not an object; `(op, tool, outcome)`
`== [("call", None, "protocol"), ("call", "nope", "unknown_tool"), ("call", "f",
"invalid_arguments")]`). It adds a unit row and touches no `src/` line; it passes at the tip (the
781). Clean.

### 111 (`5af0a42..5f9a7c1`) against `448b24d0..00aa7b3d`

`git range-diff`: `46ddf0b`→`411c234f` changed (every conflict hunk is in this commit), the two
note commits `=`, then `de0209bb` (the build review), `7247534a` (its two Lows), `c6b99280` and
`00aa7b3d` (notes only; EXECUTED `git show --stat`). Per file outside `context/`:

| file | interdiff (all / code) | what | verdict |
|---|---|---|---|
| `src/wasi_python/_call.py` | 2 / 2 | the `TYPE_CHECKING` block: 110's `._tool_host` and `.tools` lines kept with 111's `from ._fs_table import _Files` (named) | clean: the same three names imported, typing only |
| `src/wasi_python/_sessions.py` | 2 / 2 | the same, with 110's `from ._tool_host import _Bounded, _ToolHost, _ToolLoop` (named) | clean |
| `tests/checks/test_rules.py` | 63 / 57 | `ALLOWED: dict[str, int] = {}` and the ceiling's comment and docstring (named); L1's fix, the walk moved to `scan.sibling_imports` (the check now calls it) | clean: the named hunk and the Disposition's fix |
| `tests/harness/scan.py`, `tests/unit/test_scan.py` | 38, 30 | L1's fix: `sibling_imports`, where only the body of `if TYPE_CHECKING:` is typing-only and `orelse` inherits; the unit row `test_only_the_body_of_type_checking_is_typing_only` (the build review's probe plus three cases), appended after 110's rows (named) | clean: the fix text, read against the finding; the row passes |
| `tests/harness/api.py` | 9 / 9 | `INTERNAL_FILES` and `INTERNAL_MODULES` name both 110's `TOOL_FILES` and 111's `FILESYSTEM_FILES` (named) | clean |
| `tests/unit/test_runner_package.py` | 20 / 20 | `TOOLS`, `BY_NAME_MODULES` with `FILESYSTEM`; `BESIDE` gone with its branch in `_order_errors`; the `LATE` rows of both; the order check's docstring (all named) | clean: read whole at the tip below |

`BESIDE`'s removal, read whole (READ, `test_runner_package.py:109-161` at the tip): a module-level
import is routed to the tool order whenever either side is in `TOOLS` (so `tools` keeps 110's
rule); else a filesystem module may import only filesystem modules, and a filesystem module may
be imported only by `MAY_IMPORT_MOUNTS`. `BESIDE` held "no package module at module level" for
`mounts` and `tools`; both are now held by a stricter rule of their own, so nothing it caught
goes unseen. The `LATE` rows name, for each late import, the module the tip's code reads (READ,
the `_call.py` and `_sessions.py` diffs against main: every `.mounts`/`.tools` late import moved
to `_fs_table`, `_fs_memory` or `_tool_host`). Clean.

**No code change outside the named hunks and the two Dispositions' fixes reached the tip.**

## 2. Generated files merged as text (EXECUTED)

The wave touches one lock, `tests/jobs/oracle/uv.lock` (045: +82 lines), and one generated
golden, `tests/jobs/statistical_models.expected`; no other `uv.lock`, `public_api.txt` or
generated recipe moves (`git diff --stat d8fc73ff 00aa7b3d`).

**The oracle's lock does not parse at the tip (H1).** `uv tree --frozen --offline --project
<copy>` with the judge's oracle interpreter (`UV_PYTHON` the main tree's pinned 3.15.0,
`UV_PYTHON_PREFERENCE=only-system`), on the lock and `pyproject.toml` of each commit:

| commit | what | result |
|---|---|---|
| `d8fc73ff` (main), `265607bd` (wave 09's tip) | before 045 | parses |
| `dbecd2d`, `3aa663a` (045 as its build review read it) | 045 on the chain's base | parses |
| `3b7f6abf` (045 rebased onto `265607bd`), `ba38a6a9`, `00aa7b3d` (the tip) | 045 on wave 09 | **"Failed to parse `uv.lock` / Dependency `numpy` has missing `source` field but has more than one matching package"** |

`uv lock --check` and `uv export --frozen` fail the same way. The broken lines are 045's own:
formulaic's and statsmodels' `{ name = "numpy" },` (lines 156 and 792 at the tip). On `dbecd2d`
numpy had one source; wave 09's spec 100 split it into the registry entry and the
`macosx_11_0_arm64` URL entry, and rewrote every dependent of its day into two marker lines. 045's
rebase applied its new `[[package]]` blocks cleanly, so git raised no conflict, the Rebase bullet
names no hunk in the lock, and no one parsed it. 045's notes show the step was done on an
earlier rebase ("`uv lock` on the merged oracle project changed nothing", the `faa9c93` rebase)
but not on this one; wave 09's review (H1) asked for it after every rebase. CI cannot see it:
the oracle is blocked there by design (`gather.CI_NEEDS`).

**The repair, tried on a copy (EXECUTED).** Each of the two bare lines replaced by the two
marker lines the other dependents carry, byte for byte:

```
    { name = "numpy", version = "2.5.2", source = { registry = "https://pypi.org/simple" }, marker = "platform_machine != 'arm64' or sys_platform != 'darwin'" },
    { name = "numpy", version = "2.5.2", source = { url = "https://files.pythonhosted.org/packages/dd/d1/973ca116000d244897e468ea1aff30b589e5022e3c8744b71706fe33bd57/numpy-2.5.2-cp315-cp315-macosx_11_0_arm64.whl" }, marker = "platform_machine == 'arm64' and sys_platform == 'darwin'" },
```

Then `uv tree --frozen --offline` parses; `uv lock --check` → "Resolved 56 packages", exit 0
(the file is what uv writes; `uv lock` itself cannot regenerate from the broken file, it stops on
the same parse error); `uv export --frozen` gives numpy twice (the registry pin off arm64 macOS,
the URL wheel on it) and `formulaic==1.2.2`, `statsmodels==0.15.0`. Synced online into a scratch
oracle (`ORACLE_HOME` and `ORACLE_PROJECT` pointed into the scratchpad, the judge's own
`jobs.run_native`): numpy 2.5.2 names `scipy-openblas`, statsmodels 0.15.0; **all 28 golden jobs
reproduce their `.expected` byte for byte under hash seeds 0 and 1**, `statistical_models` and
`statistical_plots` among them. So the golden 045 recorded is what its pinned oracle prints, once
the lock can be read. The main tree's oracle venv (`build/oracle/venv`) holds numpy but not
statsmodels, formulaic, interface-meta or wrapt (EXECUTED, `ls site-packages`), so the lane's
judge needs an online sync after the fix (M2).

The golden: `tests/jobs/statistical_models.expected` (36 lines) is reproduced above; the other
27 `.expected` files are untouched by the wave.

### 2a. H1's fix and the restack, `e64508e4` (EXECUTED)

The lane restacked the wave on main `d8fc73ff`: 045 at `ed731606` (its ten commits and the fix),
110 at `a426de8d`, 111 at `e64508e4`, pushed as `wave/10`. `git range-diff d8fc73ff..00aa7b3d
d8fc73ff..e64508e4`: all 25 commits `=`, and one added, `ed731606` (045's fix). `git diff --stat
00aa7b3d e64508e4`: `tests/jobs/oracle/uv.lock` 4 added, 2 removed, and 045's specification (an
11-line bullet naming the missed merge). The tip's lock is **byte for byte the repaired copy of
section 2** (`cmp`), so everything section 2 executed on that copy holds for the tip: it parses,
`uv lock --check` asks no change, and all 28 goldens reproduce under it. READ, the builder's: `uv
lock` leaves the file unchanged under `jobs.oracle_env()`, and
`test_goldens_reproduce_under_the_pinned_oracle` passes by node id (`build/045/oracle-goldens.txt`).
The main tree's oracle venv now holds statsmodels 0.15.0, formulaic 1.2.2, interface-meta 2.0.1
and wrapt 2.5.1 (EXECUTED, `ls`; the lane's `build/wave-10/lane/sync.log`): M2 is met. No code
besides the two lock lines moved, and no recipe or script, so the set is `d0d91cef` still.

### 2b. The lane's fix, `2db86e00` and `a001b5c5` (EXECUTED; read as a judge change)

On `e64508e4` the lane put a rules check, `test_rules.py::test_the_oracles_lock_is_its_projects`,
with `scan.lock_errors` and nine unit rows in `test_scan.py`, and its own review
(`context/reviews/oracle-lock-check-2026-10-21.md`, a fresh agent's: one Medium and one Low, both
fixed in `a001b5c5` and confirmed against uv 0.9.22). `git diff --stat e64508e4 a001b5c5`: those
four files only, every hunk an addition at a file's end. At `a001b5c5` in the clone: the rules row
and `test_scan.py` → 260 passed; `ruff check` and `ruff format --check` on `tests` clean;
`tests/unit` collects 2,023 (+9) and `tests/checks` 889 (+1).

**Is it sound?** My probes of `scan.lock_errors` on real and hand-broken locks (scratchpad
`tools/lockprobe.py`):

| lock | result |
|---|---|
| main `d8fc73ff`; 045 on `dbecd2d` (`3aa663a`); the tip | `[]` |
| `00aa7b3d` (H1) | formulaic's and statsmodels' numpy entries "no source, and 2 packages are named numpy": the defect, named |
| interface-meta's `[[package]]` dropped | its two dependents' entries "match 0 packages" |
| `pyproject.toml` pins statsmodels 0.15.1 against the lock's 0.15.0; or adds a requirement | the project and the lock disagree, both sides named |
| a conflict marker left in | "the lock does not parse" |
| wrapt locked twice | its dependents' entries "no source" |

It reads the two files only (no uv, cache, network or interpreter), so it runs on all three
systems and is red, where the goldens check could only be blocked; both files are ASCII, so the
default `read_text()` decodes the same on Windows. It adds and weakens nothing. What it does not
hold, and does not claim to in its docstring: that the lock is the resolution uv would choose
today (a stale transitive pin passes; `uv lock --check` online stays the builder's step, and the
goldens check is the end-to-end test). The commit subject says "is what uv would write", which
says more than the check holds (Note 9).

**Does it belong in this wave?** Yes. It is judge-only and parallel-safe, so §5.7 has room for it
(045 the package, 110 and 111 parallel-safe, this the fourth entry). It closes the class the wave
reopened, and it was reviewed by an agent that wrote none of it. Its acceptance needs its own
`--accept-judge` reason and its claim block (section 3). Its review names `1d894241` and
`505fc8c7` on `lane/oracle-lock-check`, which this repository does not hold (`git log --all`).
The wave's commits `2db86e00` and `a001b5c5` are what lands, so the review cannot be read
against what lands. That is L2.

## 3. The judge: claims and the prediction for the lane's acceptance

### The claim file

110 and 111 give TOML blocks; 045 gives its claim list in prose and no `units`; the lane's fix
gives none. The wave's claim file, built from the three "For the lane" sections and the lane fix's
diff, parsed by `sameness.load_claims` (EXECUTED: `[('045', 5, 15), ('110', 2, 0), ('111', 4, 3),
('lane', 9, 1)]`, as (spec, units, new)), is at:

`/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/6c490d24-fe1d-441f-9d11-d529e2f0c242/scratchpad/claims/wave-10.toml`

- **045:** `new`, its 14 rows and `tests/unit/test_statsmodels_build.py`; `changed`, the three
  checks whose lists or facts it widens (`test_packages_carry_their_metadata[*`,
  `test_dotted_builtins_keep_their_import_names[*`, `test_stdlib_c_modules_are_builtin[*`);
  `grows`, the eleven check files its own growth list names (`build/045/grew-2.txt` in its
  worktree: 211 rows in exactly these files) and `test_upstream_suite[*` (M1); `units = 5`.
- **110:** `units = 2` (no check row moves).
- **111:** its block as written: three `new`, the one `retired`, two `changed`, `units = 4`.
- **lane** (the oracle lock check): `new = ["tests/checks/test_rules.py::test_the_oracles_lock_is_its_projects"]`,
  `units = 9`.

The counts, EXECUTED by `--collect-only`: `tests/checks` 872 → 886 (045's 14, exactly its list)
→ 886 → 888 (111: +3, −`test_mounts_imports_only_the_engine_seam`); `tests/unit` 2,003 → 2,008
(045's five rows of `test_statsmodels_build.py`) → 2,010 (110's two) → 2,014 (111's four); at
`a001b5c5` 2,023 and 889 (the lane fix's nine and one). The claims' `units` sum, 20, is the
move.

A dry use of the file: `sameness.py --claims wave-10.toml build/wave-09/lane/accepted-record.json
<045's fast-tier record, build/045/fast-2-latest.json>` → `explained by claims: 045 226`; every
line left is the fast tier's own (a slow check `deselected`, the prior-art clones blocked in a
worktree, 111's rows absent from 045's tip), and the suite line moved by exactly 045's 5.

### The prediction

Against the lane's record of wave 09's acceptance (`build/wave-09/lane/accepted-record.json`,
commit `a3bb5854`: 872 rows, 785 pass, 85 gap, 2 blocked; suite 2,010):

| | predicted |
|---|---|
| rows | **889** (+17) |
| pass | **802** (785 − 1 retired + 14 + 3 + 1) |
| gap / blocked / fail | 85 / 2 / **0** |
| unit suite | 2,030 (+20) |
| lost | **0**; **absent 1**, `tests/checks/test_rules.py::test_mounts_imports_only_the_engine_seam`, so the acceptance needs `--retire tests/checks/test_rules.py::test_mounts_imports_only_the_engine_seam` (111's claim; run 39579884932's red line) |
| gained | **18**: 045's 14, 111's 3 and the lane's lock check |
| unrun locally | 0 only if H1 is fixed and the oracle synced (M2); else 1, the goldens check, and `--accept` refuses it |
| grew | 045's rows only (110 and 111 grow nothing: their runs have no GREW line), in three parts: (1) the fast tier's 211 (3 byte rows; 208 fuel rows, all up: plain starts +15.1 M, snapshot starts +1.36 M, the zip-directory checks up to +10.1%, the metadata check +48.2 M, the largest import row +166.7 M); (2) the slow job and guest rows the fast tier deselects (the golden jobs, seaborn's `statistical_plots` +29.0 M; about 35 more, as the `dbecd2d` CI's 245 guest GREW lines against 211); (3) the darwin upstream groups, `cpython-fs` about +258 M (+0.41%) and the other groups the lane's local judge runs (M1); section 4 gives the CI rows |
| judge changed | 30 files (the clone's scoreboard line: `test_rules.py`, `test_v1_1_artifact_set.py`, `test_v1_3_data_stack.py` and 27 more): 045's harness lists, checks, golden, oracle project and unit file; 110's and 111's rules, scan, api, package and unit files; at `a001b5c5` no new file (the lock check is in `test_rules.py`, `scan.py` and `test_scan.py`), so 30 still |

**The bytes.** `python.wasm` 92,553,279 → 99,421,513 (+6,868,234), the snapshot 97,445,041 →
104,511,377 (+7,066,336), the zip 49,772,117 → 53,913,865 (+4,141,748): 045's `d0d91cef` set,
which the lane's rebuild in the main tree matches (the lane's word); 110 and 111 change no
artifact byte. **The wheel:** main's CI wheel 90,864,138 bytes (EXECUTED, run 39572424790's
`rebuild-wheel-ubuntu-24.04`); 045's local build of the tip's set 98,251,487 (READ, its notes),
1,748,513 under the owner's 100,000,000-byte line (question 64), so question 64 does not come back
with this wave; the dry run's wheel is read in section 4.

### 3a. The lane's first judge on `e64508e4`, against the prediction (EXECUTED)

The lane's record `build/wave-10/lane/judge-1.json` (`-n 3`, no `--accept`, on `e64508e4`, before
the lock check): `801/888 pass · 85 gap · 2 blocked · 0 fail (unit suite 2019/2021, 2 skipped)`;
`ratchet vs a3bb58541b: lost 0 · absent 1 · unrun 0 · gained 17 · grew 287`; red only on
`ABSENT tests/checks/test_rules.py::test_mounts_imports_only_the_engine_seam` and the growth.
Against the prediction for that commit (one row, one pass, one gain and nine units fewer than
`a001b5c5`'s, the lock check not yet in it): rows, pass, gap, blocked, fail, the suite's +11,
lost, absent and gained all as predicted. **unrun 0:** the goldens check ran on the fixed lock
with the synced oracle and passed (H1 and M2 closed in the judge).

- **grew 287**, by the ratchet's rule (EXECUTED, `predict.py` over the record against main's
  `accepted.json`): the three byte rows; 250 guest fuel rows in the eleven files of 045's claim
  (zip-directory checks up to +10.1%, the plain starts about +5.9%, median of all fuel rows
  +0.70%); and **34 darwin upstream groups**, from `contourpy-filled-4` +0.011% to `cpython-fs`
  +0.452% and `cpython-c` **+1.291%**, the largest (INFERRED: its pydoc class imports every
  package and walks the modules, now 26 builtins and 588 members more). 7 upstream groups fell,
  none past −0.06%. That is M1 measured: 33 of the 34 upstream rows are ones 045's prose claim
  does not name.
- **Sameness with the claims** (EXECUTED: `uv run python tests/harness/sameness.py --claims
  <the claim file> --except lane build/wave-09/lane/accepted-record.json
  build/wave-10/lane/judge-1.json`; `--except lane` because the record predates the lock check):
  **exit 0**, `note: explained by claims: 045 311 · 110 1 · 111 5`. No line is left: no pass
  count moved in any upstream group (a `passes` move is a kind no claim here explains), and the
  unit suite moved by exactly 045's 5, 110's 2 and 111's 4. The "claimed, not seen" notes are the
  `changed` entries whose checks moved only in source, which the record does not compare.

## 4. The dry run of record (EXECUTED)

**39588461408 on `a001b5c5`** (`gh run view --json jobs`, `--log` of the build job, every
artifact downloaded): **failure at its first job**, `build and judge (arm64 macOS)`. The two
rebuild jobs succeeded and the other nine jobs were skipped: verify, the three judge matrices,
the same-bytes job, the gather and the three publishing jobs. So there is no shard record, no
`release-record-1` and no gather.
- **The build job, step by step:** build from the pins green; the wheel built; the zero-patch
  step `28 passed, 24 deselected` (statsmodels' tree the twenty-eighth); the build shard `65
  passed, 2854 deselected`, scoreboard `55/889 pass · 0 fail`, `ratchet vs a3bb58541b: lost 0 ·
  absent 1 · gained 2 · grew 0`, and its one red line **`ABSENT
  tests/checks/test_rules.py::test_mounts_imports_only_the_engine_seam`** ("1 accepted check(s)
  absent (retire them with --retire)"). That is 111's claimed retirement and nothing else, as its
  own run 39579884932 showed on `dd711674`. No G1 to G7 line was reached.
- **The set:** both rebuild hosts' `SHA256SUMS` hash to **`d0d91cef7361…`** (`ubuntu-24.04` and
  `-arm`). That is 045's builder's set and the one the lane rebuilt in the main tree
  (`build/artifacts/SHA256SUMS` → `d0d91cef7361…`, EXECUTED). §5.7's comparison of sets holds.
- **The wheel:** `rebuild-wheel-ubuntu-24.04` and `-arm` are both **98,259,192 bytes**, against
  main's 90,864,138 (run 39572424790): +7,395,054, **1,740,808 under the 100,000,000-byte line**.
  Question 64 is not brought back by this wave. The next landing that adds about 1.7 MB is the one
  that brings it back (Note 10).
- **What this run cannot show (M3).** A release run of any commit with 111 stops at the build
  shard while main's accepted record holds the retired check. Only an acceptance with `--retire`
  removes it, and only the lane accepts. So this wave's code has had no Linux or Windows read on
  the integrated tip before its acceptance. The darwin read is the lane's local judge (section
  3a). The entries' own three-system runs read their code apart: 110 on `e6728fa` (39546608171,
  green on three systems), 111 on `f763178` (39551619591, green on three systems), and 045 on
  `7be1837` (39533679276, its two Windows failures not 045's).

## 5. Constitution checks

- **§4.1 (045's one patch):** `recipes/patches/statsmodels-0.15.0/0001-datasets-from-a-zip.patch`,
  moved whole from the facts sheet's `fix.patch` (`R100`, EXECUTED `git diff -M --name-status`),
  SHA-256 `751e7190…db58` at the tip (EXECUTED), as the build review recorded and `MANIFEST`
  hashes it (`scripts/assemble_artifacts.py` hashes every `recipes/patches/*/NNNN-*.patch` by glob;
  the build review READ the line); named in the CHANGELOG's 045 bullet; its pull request drafted at
  `context/upstream/patches/statsmodels-0.15.0/0001-datasets-from-a-zip.md` (moved whole from
  `pr.md`), the facts sheet row updated in `context/upstream/README.md`;
  `test_carried_patches_follow_the_rules` passes at the tip; the zero-patch job's count is 28
  (`release.yml`). Everything else is a recipe. Holds.
- **§4.2 (pins):** five new lines in `downloads/SHA256SUMS`; the three wheels' and the sdist's
  digests are the ones the oracle lock records (EXECUTED: formulaic `0f84ff49…`, interface-meta
  `f38016be…`, wrapt `c6e6c226…`, the sdist `5d257fe5…`).
- **§4.3 to §4.5:** `tests/public_api.txt` untouched; `api.py --check` exit 0; no guest import or
  export moves (045's link-map gate READ in its build review; 110 and 111 touch no guest code).
- **Rule 4:** `tests/known_gaps.toml`, `tests/upstream/` allowances and expectations,
  `context/progress/` untouched; the wave adds `statistical_models.expected` and four `later`
  entries to `packages.toml` (spec 063: statsmodels' suite with spec 095 its closer, the three
  wheels with 067) and edits no expectation (EXECUTED `git diff --stat`).
- **The structural rubric, 110 and 111 together** (EXECUTED, the README's commands; main
  `d8fc73ff`, whose `src/` is `5af0a42`'s, against the tip):

  | what (row) | main | tip |
  |---|---|---|
  | module sizes (R7) | 18 modules, 12,873 lines; `tools.py` 2,449 and `mounts.py` 2,206 over the 1,500 ceiling | 24 modules, 13,276 lines (+91 for 110, +312 for 111, as each build review measured); none over 1,500, the largest `_platform.py` 1,407, then `runner.py` 1,198; `tools.py` 727, `_tool_schema.py` 785, `_tool_host.py` 1,027; `mounts.py` 361, `_fs_table.py` 681, `_fs_paths.py` 644, `_fs_descriptors.py` 513, `_fs_memory.py` 317 |
  | `ALLOWED` (spec 108) | two entries | **empty**, `ALLOWED: dict[str, int] = {}` kept for its stale-entry rule; the ceiling check passes |
  | functions over 80 lines (R7) | 9 (`runner.py` 4, `tools.py` 2, `_call.py`, `_process.py`, `_sessions.py` 1 each) | 7 (`tools.py`'s two gone), exactly `LONG_FUNCTIONS`' seven entries, which lost two and gained none; the 80-line check passes |
  | module-level mutables and locks (R4) | 0 | 0 (111's three `HANDLERS` are read-only upper-case displays) |
  | private-API uses (R3) | 86: `_wasmtime_ffi.py` 84, `_places.py` 1, `tools.py` 1 | 86: the same with `_tool_host.py` 1 (the frame host's own `self._context()`); the engine seam imported at runtime by `_fs_table.py` alone among the filesystem modules (`FILESYSTEM_IMPORTS`; its rows pass) |
  | platform branches (R5) | 3, in `_platform.py` | 3, in `_platform.py` |
  | the seam allowance (R6) | `SEAM_ALLOWED` | untouched by the wave (EXECUTED: no `SEAM_ALLOWED` line in the diff); 29 distinct private names patched by the judge, as 111's review counted; the seam check passes |
  | `Any` / `type: ignore` (R7) | 338 / 25 | 344 / 25 (110's two and 111's four `from typing import` lines) |
  | type checker; citations (R7) | clean; 0 / 0 | `mypy --strict` clean, 24 files; 0 / 0 |

  Together the two specifications move R3, R6 and R7 the way each build review scored them and
  none toward Weak; their union adds no concern, no lifecycle flag, no mutable, no platform branch
  and no seam. The one place they meet, the package-order rule, holds both (section 1). The
  structure holds.
- **§7:** nothing tripped; no `--accept`, push or artifact in git by any entry.

## Findings, most severe first

1. **H1 (High, against 045's rebase; the lane found it at the same time): the oracle's lock does
   not parse at the tip** (`tests/jobs/oracle/uv.lock`, lines 156 and 792 at `00aa7b3d`,
   formulaic's and statsmodels' `{ name = "numpy" }`; section 2). Introduced at `3b7f6abf`, 045's
   rebase onto wave 09's tip; no Rebase bullet names it and no review read it. **Failure:** `uv
   run --frozen`, `uv tree`, `uv export` and `uv lock` all refuse the project, so
   `test_goldens_reproduce_under_the_pinned_oracle` is blocked on every system ("needs oracle",
   counted unrun locally; `--accept` refuses it without `--partial`), 045's own golden is never
   re-checked under the pins it adds, and 044's native script cannot export the oracle. **Fix
   (045's builder, a `tests/` file):** the two lines of section 2, each replaced by the two marker
   lines; then `uv lock --check --project tests/jobs/oracle` (with the judge's oracle Python) must
   print no change, and 045's Rebase bullet names the lock as the missed merge. Verified on a copy
   here: it parses, `--check` passes, and every golden reproduces under it. **Done:** `ed731606`
   is that copy byte for byte, with the bullet (section 2a). **And** the lane's lock check
   (section 2b) makes this class red in the fast tier, on every system, from now on.
2. **M1 (Medium): 045's claim list has no TOML block, no unit count, and names only one darwin
   upstream row** (045's *For the lane*, "Rows that grow"). It names `cpython-fs`, the row CI's
   macOS shard measures; the lane's local judge measures darwin fuel for every upstream group, and
   045 adds to each of them what it adds to every start: +15.1 M per plain start, about 8 k per
   import lookup and a longer zip directory per cache invalidation. **Failure:** sameness with the
   entries' claims prints those groups as unexplained, which rule 6a reads as an ejection of 045
   for its own mechanism (wave 09's M1, the same shape). **Fix (context only, done here):** the
   claim file above (045's block with `test_upstream_suite[*` and `units = 5`), and one clause in
   045's `--accept-growth`: `; on darwin every upstream group pays the same per start, per import
   lookup and per rebuilt zip directory, every pass count unchanged (the integration review's
   M1)`. Then read the acceptance's upstream rows against it: a group whose **passes** move is a
   finding against 045, not covered.
3. **M2 (Medium, the lane; met): the main tree's oracle lacked 045's four packages.** `build/oracle/venv`
   has numpy and no statsmodels, formulaic, interface-meta or wrapt (EXECUTED). After H1's fix,
   sync it online once before the judge (`UV_CACHE_DIR=build/oracle/cache`,
   `UV_PROJECT_ENVIRONMENT=build/oracle/venv`, the oracle's Python, `uv sync --frozen --project
   tests/jobs/oracle`; every wheel is hash-pinned), as wave 09's M2 did, and let the acceptance
   run the goldens check. It must pass (it does in the scratch oracle, section 2).
4. **M3 (Medium, the lane): the wave has no three-system read before its acceptance.** (Section
   4; 111's *Rebased for wave 10* bullet foresaw it.) The dry run of record stops at the build
   shard on 111's retired check, so no Linux or Windows judge ran the integrated tip: 045 on
   wave 09's numpy, and the merged package-order and rules code of 110 and 111. **Failure:** a
   check that fails only on Windows or Linux in the merged code (rule 6b's lesson, 0.1.0a4) is
   first seen after main has moved. **What closes it:** the step-7 dry run on the acceptance
   commit. The acceptance's `--retire` lets that run past the build shard, so it reads all three
   systems. Every red line it shows must be one 045 claims (G5 "grew" on the macOS shards) or G7.
   Any other line is fixed forward, before anything else in the next wave (progress README, step
   7). The acceptance's notes should say which run is the wave's three-system read. Nothing in
   the entries' own runs suggests such a line: each was green on Windows apart, and the merge's
   new lines are judge code that the darwin judge ran (section 3a). That is why this is Medium,
   not a reason to eject an entry.
5. **L1 (Low, a pre-existing twin of 111's L1): the package-order rule's own import walk still
   gives the `else:` of `if TYPE_CHECKING:` the typing-only flag** (`tests/unit/test_runner_package.py`,
   `_imports`, lines 88-89 at the tip; the same on main at lines 78-79). 111 fixed the walk in
   `scan.sibling_imports` for the filesystem rule; `_imports` walks `child` with `typing_only or
   guarded`, so its `orelse` inherits the flag and `_order_errors` skips a runtime import placed
   there. Not the wave's code, and no module has such an `else:` today. **Fix:** none in this
   wave; the lane's rules check for locks (H1) or the next judge change of the order rule makes
   `_imports` push the guard's `body` alone with the flag, or reads `scan.sibling_imports`; a
   roadmap line names it.
6. **L2 (Low): the lock check's review names commits this repository does not hold.**
   (`context/reviews/oracle-lock-check-2026-10-21.md`, its Reviewed line and Disposition.) It
   read `1d894241` on `lane/oracle-lock-check` (base `3b7f6abf`) and confirmed `505fc8c7`. Neither
   commit is in `git log --all`; what lands is `2db86e00` and `a001b5c5` on `e64508e4`, with
   test-file conflicts the lane resolved. **Failure:** a later reader cannot run `git range-diff`
   from the reviewed commit to the landed one, so the review is not tied to what lands. **Fix
   (context only):** one line under the review's Confirmation: "Landed in wave 10 as `2db86e00`
   and `a001b5c5` on `e64508e4`; the conflicts in `test_rules.py` and `test_scan.py` were
   append-only, and wave 10's integration review read the landed diff (`git diff e64508e4
   a001b5c5`: four files, every hunk an addition at the file's end) and probed `lock_errors` on
   it." The lane may also give the check a roadmap line or its spec number, since it carries
   none.
7. **Note: 111's dry-run needs line is stale.** *For the lane, as built* says "this build's
   dispatches (39541506877, and 39551619591 on the rebased tip)"; its later notes rightly say the
   three-system read of the rebased code is the wave's dry run. The lane reads the later.
8. **Note: 045's rebase did run `uv lock` once before.** Its notes for the `faa9c93` rebase say
   "`uv lock` on the merged oracle project changed nothing"; the `265607bd` rebase's bullet does
   not, which is how H1 came back after wave 09's review asked for it.
9. **Note: the lock check holds less than "what uv would write".** `2db86e00`'s subject says it;
   the check's docstring rightly says less: the lock parses as uv reads it, every entry names one
   package, and the root's pins match the project's. A stale transitive pin passes. `uv lock
   --check` online stays the builder's step after a rebase that touches the oracle, and the
   goldens check stays the end-to-end test.
10. **Note: the wheel and question 64.** 98,259,192 bytes on CI (section 4), 1.74 MB under the
   owner's line. Spec 095 (statsmodels', scipy's and scikit-learn's own suites) adds no artifact
   bytes. The next package that adds bytes, the three wheels of 067 or any build-class change that
   grows the set, is the landing for which the agent brings question 64 back first.

## Disposition (for the lane; the entries' builders where named)

1. H1: fixed by 045's builder in `ed731606`, byte for byte this review's repair, read in section
   2a. 110 and 111 were restacked with no hunk (range-diff `=`). Closed in the judge: the lane's
   record on `e64508e4` has unrun 0, and the goldens check passes there. The lane's lock check
   (section 2b) keeps the class red from now on.
2. M1: closed by this review's claim file and the clause in 045's `--accept-growth` (the
   finding's text). Sameness with it on the lane's record exits 0 (section 3a).
3. M2: met (the lane's online sync; section 2a).
4. M3: the lane names the step-7 dry run on the acceptance commit as the wave's three-system
   read. Any red line there that is not 045's growth or G7 is fixed forward.
5. L1: a roadmap line for the package-order rule's `else:` walk.
6. L2: the line in the finding, written into the lock check's review by the lane.
7. Notes 7 to 10: no action beyond what they say.

## Verdict

**Lands as merged at `a001b5c5` once** the lane's acceptance on that tip:
1. runs with `--retire tests/checks/test_rules.py::test_mounts_imports_only_the_engine_seam`, each
   entry's flags, the lock check's own `--accept-judge` reason, and M1's clause in 045's
   `--accept-growth`;
2. shows 802/889 pass, 0 fail, lost 0, gained 18, unrun 0 (the goldens check passing), and grows
   only 045's rows (about 287: the 253 guest and byte rows and the darwin upstream groups, no pass
   count moved);
3. prints, from `sameness.py --claims` with this review's claim file, nothing but the claims'
   note;
4. and the step-7 dry run then reads three systems with red lines only on 045's growth and G7
   (M3).

Every rebase is its reviewed diff plus named conflicts and the Dispositions' fixes. The one
unnamed rebase change, 045's broken oracle lock (H1), is fixed on the tip and now held by a
rules check. The structure of 110 and 111 together holds: `ALLOWED` is empty, there are seven
long functions, and there is no new seam. The dry run of record 39588461408 is red only on 111's
claimed retirement, before any judge job, with the set `d0d91cef` on every host and the wheel at
98,259,192 bytes. No entry is ejected.

One line: statsmodels, the tool facade and the filesystem seams merge cleanly once 045's lock is
repaired, which the tip carries and a new rules check now guards; the wave's Windows and Linux
read can only come after the acceptance retires 111's old check.
