# 081 — guest fuel does not depend on where the repository is checked out

- **Status:** **built 2026-10-19** on `spec/081-guest-fuel-does-not-depend-on-the-checkout`,
  rebased onto main `08de0c8` (spec 063 landed) with Decision 5's merge made (the Landing notes);
  drafted the same day from main `8f8de73`, first built on `3f69654`. It changes neither the guest's imports nor its exports, the artifact
  set nor the build recipe, so §5.6 asks no review before build. It was sent for one anyway, at
  the lane's request, and revised against it the same day ("ready once F1 to F3 are written
  in": `../reviews/081-guest-fuel-does-not-depend-on-the-checkout-spec-2026-10-19.md`, and the
  section "Revised against the pre-build review"). A different agent reviews the build.
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** a judge change; **parallel-safe**, not build-class (§5.7). It edits the judge's guest
  driver (`tests/harness/guest.py`), the `guest` fixture (`tests/checks/conftest.py`), one check
  (`tests/checks/test_v1_3_lxml.py`), the driver's unit tests (`tests/unit/test_guest.py`) and
  one roadmap line (spec 083 reserved, Decision 4), and nothing else: no `src/`, `scripts/`,
  `recipes/`, `downloads/SHA256SUMS`, workflow, README or CHANGELOG. No golden output, gap or
  allowance is edited. It restates the accepted fuel of two rows, and both fall: **the lane
  accepts it with `--accept-judge` alone** (Decision 3).
- **Depends on:** spec 063, which lands first and edits the same assertion of the lxml check.
  The build rebases onto main after 063 lands and merges that check by hand, as Decision 5 says.
- **Research it stands on:** spec 075's build review, N2
  (`../reviews/075-tools-small-fixes-build-2026-10-19.md`: the lxml snapshot row +113.8 k in a
  clone 88 characters longer than the main tree); and this spec's measurement (EXECUTED,
  `../research/2026-10-19-guest-fuel-and-the-checkout-path/`, the section below).

## The problem

A check's fuel is the number of wasm instructions its guest ran. The ratchet holds it to one
part in ten thousand of the accepted value (`FUEL_TOLERANCE`, `tests/harness/scoreboard.py`).
So fuel must depend only on the artifact and the check, never on the machine.

One check breaks that. `test_stylesheets_and_entities_reach_only_grants` (both binaries) gives
its guest a host path as an argument: `str(ro / "secret.txt")`, the real location of a granted
file. The check uses it to show that an entity naming a host path outside every grant reads
nothing. But that path lives under the checkout (`build/harness/guest-…/ro-…/`), so its length
is the checkout's length plus a constant. And the guest's work moves with that length.

The lane judges in the main tree (40 characters). The release's macOS legs check out at
`/Users/runner/work/wasi_python/wasi_python` (41 characters; GitHub's default workspace,
INFERRED from its runner layout, since `release.yml` passes no `path:` to `actions/checkout`)
and compare with `accepted.json`. A path-length-dependent metric there is a latent false
"grew". It has passed so far by luck.

## The measurement (EXECUTED)

Evidence: `../research/2026-10-19-guest-fuel-and-the-checkout-path/`. Against
`build/sets/s-c50ca51fae5eb55b` in the main tree, read only.

**Which rows record fuel.** `accepted.json` holds fuel for 159 rows (darwin-arm64), from 69
check functions (`funcs.txt`). Every fuel metric is recorded in one of three places (READ:
`grep 'metric("fuel"' tests/checks`): the `guest` fixture, and the upstream suite checks
twice. All three take their fuel from the judge's driver, `harness.guest.run`.

**Two checkouts, twice each.** All 69 functions run from this worktree (a 44-character path)
and from a clone at a 205-character path, twice each (`measure.sh`, `compare.py`,
`compare.out`, `runs.out`). 148 rows ran in each; 11 were skipped (the upstream suite groups:
their source trees exist only after a build).

| row | short to long | short to short, long to long |
|---|---|---|
| `test_stylesheets_and_entities_reach_only_grants[snapshot]` | **+113,522 and +113,529** (+0.053%) | +57, +64 |
| `test_stylesheets_and_entities_reach_only_grants[plain]` | **+50,981, both times** (+0.010%) | 0, 0 |
| the other 146 rows | at most 119 instructions, each a multiple of 17 | the same kind, as often |

So **the two lxml rows are the only path-dependent rows**, by an argument the guest is READ and
EXECUTED to receive. The long clone's run is red on its own: `GREW …[snapshot]: fuel 216000964
-> 216086430`. The other differences are not the path's: they appear as often between two runs
at one path, and they come from the host's file timestamps (Decision 4).

**The upstream groups (READ).** Their argv is `["-u", "/upstream/judge/drive.py", package,
group]`, their environment `{"TMPDIR": "/tmp", "HOME": "/tmp"}`, their one grant `/upstream`
(`tests/harness/upstream.py`, `guest_argv`, `ENV`, `preopens`). No host path reaches them.

**The cause, alone (`argv_length.py`, `argv_length.out`).** The same program, the same grants,
the same driver; only the length of the path argument changes:

| argument length | snapshot fuel | step |
|---|---|---|
| 40 | 215,915,897 | |
| 41 | 215,916,301 | +404 |
| 44 | 215,918,722 | |
| 45 | 215,949,977 | **+31,255 for one character** |
| 80 | 216,004,139 | |
| 100 | 215,977,914 | lower than at 80 |
| 180 | 216,154,938 | +239,041 over 40 |

The same lengths in another letter give the same fuel, to the instruction. So the fuel is a
deterministic function of the length alone, and not a smooth one: about 700 instructions a
character, with jumps (INFERRED: an allocation or a collection crossing a threshold). The
tolerance on this row is 21,600 instructions. **One character more in a checkout's path can turn
the row red**; a different one can turn it green by chance. The plain row moves the same way
(40 to 205 characters: +195,252).

## Decisions

1. **The host path goes to a run of its own that records no fuel.** The check makes two runs:
   - first, a small program (`OUTSIDE`) given the real host path, with `record=False`: the
     entity naming it must still give `<r/>`;
   - then the measured program (`SAFETY`, less that one case), given guest paths only.
   The check asserts both, as one dict of answers, exactly as before.
   - **Why the real path stays.** The probe's point is the real host location of a file the
     guest can read through a grant. A made-up path would not show that wasmtime refuses it.
   - **Why not a fixed-length staging folder.** No folder has the same path on every system
     (`/tmp` is not Windows'), and a shared fixed folder breaks parallel workers. Padding the
     argument to a fixed length would work only up to a chosen maximum, and the content of a path
     a check builds still has to be checked by someone.
   - **The cost.** One more guest run per row, of a few lines after `import lxml`.
2. **The driver refuses a measured run that gives the guest a host path.**
   - `harness.guest.run` gains `measured: bool = True` and `host_roots: Sequence[Path] = ()`.
     A measured run whose inputs name a path under the checkout (`paths.REPO`) or under a
     `host_roots` entry raises `ValueError` before anything runs, naming each input. The inputs
     are what the guest sees: each argument, each environment variable, each file's guest path
     and contents (`files=`), and each grant's guest path.
   - **The forms looked for.** Each root as written and resolved; each of those in forward
     slashes; as a `file:` URI (`as_uri()`, percent-encoded, for an absolute root), so a root
     with a space or a non-ASCII letter is still caught in a URI; and, for a form that holds a
     backslash, the same with every backslash doubled, as `repr()` and JSON write a Windows path
     inside code. On Windows the match ignores case (`fold_case`, default `sys.platform ==
     "win32"`), so `c:\` matches `C:\`. The escaped form is made from the string, so a unit row
     can give a Windows-shaped root on any system.
   - **The roots.** The checkout (`paths.REPO`), always; the system's temp folder
     (`tempfile.gettempdir()`) whenever it is not literally `/tmp` (macOS' `/var/folders/…`,
     Windows' `%TEMP%`, a runner's own temp), so no guest path collides with it; and the
     `host_roots` the caller gives. The `guest` fixture passes `measured=record` and, as a root,
     pytest's base temp folder (`tmp_path_factory.getbasetemp()`), where every `tmp_path` lives,
     wherever `--basetemp` puts it. The upstream checks keep the default: measured, with the
     checkout and the system temp folder as roots. The build re-runs every fuel function with
     these roots: a root that names a current check's input is a finding, not a reason to drop
     the root.
   - **Not checked:** a run on the caller's own engine (`own=`, which counts no fuel), and
     `Turns` (which records no fuel).
   - **Why a guard, not a self-test from two checkouts.** A two-checkout run needs a clone, its
     own environment and minutes of guest runs, and it covers only the sample it runs. The guard
     costs nothing, runs on every measured run in every judge run, and names the input. It is
     what this measurement found: a host path in a guest's inputs.
   - **What it does not catch.**
     - A host path in a `host=` door's answer: the driver hands it to the guest after the run has
       begun, and the guard looks only at what the run is given.
     - A host path a check writes into a file in a grant, not through `files=`.
     - A host path outside every root: `$HOME`, the uv cache, and the system temp folder when it
       is `/tmp` (on Linux, where the upstream groups pass `/tmp` as a guest path).
     - Another encoding of a path than the forms above (say, base64 of it).
     Today the measurement shows no row moves by any of these.
3. **The two rows' accepted fuel is restated, and both fall.** Measured with the prototype
   (`prototype.diff`, `fixed.out`) from both checkouts, twice each, one value every time:

   | row | accepted (main tree) | restated | change |
   |---|---|---|---|
   | `test_stylesheets_and_entities_reach_only_grants[plain]` | 507,157,737 | 506,200,859 | −956,878 (−0.189%) |
   | `test_stylesheets_and_entities_reach_only_grants[snapshot]` | 216,000,964 | 215,014,922 | −986,042 (−0.456%) |

   They fall because the measured program no longer runs the outside-grants entity. No row
   rises, so the lane needs no `--accept-growth`. The build re-measures them; if they differ
   from these, the landing notes say by how much and why.
4. **Out of scope: the 17-instruction steps, which are the host's file timestamps.** Between two
   runs at one path, about fifteen of the 148 rows differ by a multiple of 17 instructions, at
   most 119 (`compare.out`). They are not the path's: they appear as often at one path as
   between two.
   - **Their source** (the pre-build review, EXECUTED, its `probes/r1_seventeen.py` and
     `r2_timestamps.py`): the real modification times that wasmtime's `fd_filestat_get` and
     `path_filestat_get` hand the guest. Eight small programs, twelve runs each: only those that
     use a file's `st_mtime` give two values, 17 apart; the same programs give one value once
     `os.utime` fixes the time. The driver answers `random_get` and `clock_time_get` itself,
     but not the times inside a `filestat`. So the steps depend on when a check runs, not on
     chance and not on the checkout.
   - **Their bound.** The largest step seen is 119 instructions. The smallest accepted row,
     `test_unbuffered_output_survives_a_hard_exit[snapshot]` at 1,213,059, allows 121, and it
     reads no timestamps (it did not vary). So no row is at risk today; a future small check
     that stats files, or one that reads many timestamps, could be.
   - **Their owner.** Spec 083, reserved in `context/roadmap.md` by this spec: the driver
     answers the `filestat` times from its fixed clock, as it answers `clock_time_get`. Nothing
     here waits on it. The driver's docstring ("repeats to a few parts in ten million") is left
     to 083.
5. **The merge with spec 063.** 063 lands first and changes the same assertion: on Windows a host
   path is refused by name, so "entity outside grants" is `XMLSyntaxError` there. At the rebase
   the build merges the lxml check by hand, and the merged check:
   1. runs `OUTSIDE` with the real host path and `record=False`, and asserts its exit code is 0;
   2. runs `SAFETY` (measured) with guest paths only, and asserts its exit code is 0;
   3. merges the two answers with **disjoint keys**: `OUTSIDE` answers exactly "entity outside
      grants" and its control, "entity by guest path, outside run" (N1, below); `SAFETY`
      answers neither; the check asserts both, so a later edit cannot leave a case in both runs
      with one silently overriding the other;
   4. for "entity outside grants": on `win32`, `XMLSyntaxError` with "failed to load" and
      "Operation not permitted" (063); elsewhere `ok` with `<r/>` (046); and **on every
      platform, no `SECRET` in its value**, whatever its kind (063 had that line on `win32`
      only; it is the property itself);
   5. keeps the other twelve `expect` lines and the closing assertion on `ro/out.xml` and
      `rw/out.xml`;
   6. keeps both docstring sentences (063's, Windows' refusal by name; 081's, the unrecorded run)
      and 063's `import sys` at the module's top.
   On Windows the measured run no longer holds the case that refuses differently; Windows' fuel
   is not compared with `accepted.json` anyway (its values are darwin-arm64's).
6. **A positive control inside `OUTSIDE`** (the review's N1). The unrecorded run also resolves
   `file:///ro/secret.txt`, the same file by its guest path, and expects `ok <r>SECRET\n</r>`.
   So the run shows on its own that the file is there and readable by its guest path, and that
   the parser resolves entities, while its host path reads nothing. And before the run, the check
   asserts on the host that the path it hands `OUTSIDE` is the granted file (it reads `SECRET`
   there and is the same file as `ro / "secret.txt"`), so a made-up path cannot pass vacuously.

## Intent

Every fuel metric the judge records is the same whatever the checkout's path, so the release's
legs and the lane compare the same numbers; and a check that would hand a measured guest a host
path is refused at once, by name, before it runs.

## Design

- **`tests/harness/guest.py`.** A pure function, `host_paths_in(roots, argv, env, files,
  preopens, fold_case=sys.platform == "win32") -> list[str]`, names each input that holds one of
  a root's forms (Decision 2: as written, resolved, forward slashes, `as_uri()`, backslashes
  doubled), as `argv[3]`, `env DATA`, `file /a.py`, `the contents of /a.py` or `grant /ro`.
  `run()` calls it first when `measured` and not `own`, with `(paths.REPO, *system_temp,
  *host_roots)`, where `system_temp` is `(Path(tempfile.gettempdir()),)` unless that is `/tmp`,
  and raises `ValueError("a measured run gives the guest a host path in argv[3]: its fuel would
  depend on where the checkout is; give it guest paths, or record no fuel for this run (spec
  081)")`.
- **`tests/checks/conftest.py`.** The `guest` fixture takes `tmp_path_factory` and passes
  `measured=record, host_roots=(tmp_path_factory.getbasetemp(),)`; its docstring says so.
- **`tests/checks/test_v1_3_lxml.py`.** `SAFETY` loses `host_secret` and the case
  `entity outside grants`. A new `OUTSIDE` program reads `sys.argv[1]` and, with the same
  `entity()` document and `resolve_entities=True`, answers two cases: "entity by guest path,
  outside run" (`file:///ro/secret.txt`) and "entity outside grants" (`file://` and the host
  path). The check runs `OUTSIDE` with the host path and `record=False`, then `SAFETY` with no
  host path, asserts on the host that the path is the granted file (Decision 6), asserts the
  keys disjoint, merges the answers, and checks them as Decision 5 says:
  the control `ok <r>SECRET\n</r>`, 063's platform branch, no `SECRET` outside on any platform,
  and the twelve other `expect` lines.
- **`tests/unit/test_guest.py`.** Rows: every input kind is found, in both forms of the root;
  a root with a space is found in its `file:` URI; a Windows-shaped root (`C:\Users\runner\work`)
  is found inside `json.dumps` and `repr` text, and, with `fold_case`, in another case; guest
  paths and paths under another folder are not; the system temp folder is a root unless it is
  `/tmp` (with `tempfile.gettempdir` patched each way); a measured `run` with a host path in an
  argument or a grant is refused before it runs, and the same run with `measured=False` runs.

The prototype is `prototype.diff` in the evidence folder: 129 lines added, 10 removed. It
predates the review: it has neither the added forms, the system temp root, the control nor the
merge with 063.

## Scope

In: the driver's guard, the fixture's wiring, the lxml check's split and its merge with 063, the
unit rows, the two restated values, and the roadmap line reserving 083. Out: the file
timestamps (Decision 4, spec 083); checks that call `wasi_python.run` (they record no fuel);
spec 082 (inline sessions and wasmtime's handlers).

## Acceptance criteria

1. **The checks fail first.** On main's code the three unit rows fail (`host_paths_in` and
   `measured` do not exist). With the guard alone, of the 148 fuel rows that run without a
   build, exactly the two lxml rows fail, each with the guard's message naming `argv[3]`
   (seen in the draft: `guard_only.out`).
2. **Two paths, one fuel.** Each of the two lxml rows, run twice from the worktree and twice
   from a clone at a path at least 150 characters longer (`lxml.sh`), gives one fuel value
   (seen in the draft: `fixed.out`).
3. **The probe still bites.** A mutant that grants the read-only folder at its own host path, in
   the `OUTSIDE` run only, fails the check on `entity outside grants` with `<r>SECRET\n</r>`
   (seen in the draft: `mutant_outside.out`). Three more mutants each fail: the control naming a
   file that is not there (`file:///ro/elsewhere.txt`) fails on the control; a made-up host path
   (`/nonexistent/secret.txt`) fails the host-side assertion; "entity outside grants" answered in
   `SAFETY` too fails on the disjoint keys. The other twelve
   answers are asserted as before; on Windows the expectation is 063's.
4. **No other row depends on the path.** With the build, all 69 functions (`measure.sh`) from
   both checkouts: no row differs between the two paths by more than the largest difference
   between two runs at one path (with Decision 4's timestamps, up to about 119 instructions);
   and no measured run is refused by the added roots or forms.
4a. **The guard's new forms.** The unit rows for the `file:` URI, the doubled backslashes, the
   folded case and the system temp root each fail against the draft's prototype guard and pass
   with the build's.
5. **The judge.** `ruff check` and `ruff format --check` green; the fast tier and one full run
   (`-n 3`) against `build/sets/s-c50ca51fae5eb55b`: no failure, no lost pass; the ratchet's
   only moves are the two restated rows (both fall) and `judge changed`. The prototype's fast
   tier (`fast_tier_prototype.out`): `474/550 pass · 1 gap · 24 blocked · 0 fail` (the blocked
   are source trees, a wheel, the wasmtime CLI and the like, absent from a worktree), unit suite
   1270/1278, `1744 passed, 32 skipped, 1 xfailed`, `lost 0 · grew 0`.

## Revised against the pre-build review (2026-10-19)

The review (`scratchpad/081-review/081-guest-fuel-does-not-depend-on-the-checkout-spec-2026-10-19.md`,
probes beside it; copied to `../reviews/` by the lane): "ready once F1, F2 and F3 are written in".
It reproduced the restated values at a third path length (128 characters) and the mutant's
failure.
- **F1.** Decision 4 names the steps' source (the host's file timestamps through `filestat`),
  their bound (119 against 121 on the smallest row) and their owner (spec 083, reserved in the
  roadmap).
- **F2.** Decision 2 adds the `file:` URI and doubled-backslash forms, case folding on Windows,
  and the system temp folder as a root unless it is `/tmp`; the holes list names the `host=`
  door's answer. The unit rows grow to match (Design; criterion 4a).
- **F3.** Decision 5 writes out the merged lxml check; Depends on names 063.
- **N1.** Decision 6: a positive control inside `OUTSIDE`; criterion 3 gains its mutant.

## Landing notes

### What was built

On `spec/081-guest-fuel-does-not-depend-on-the-checkout`, rebased onto main `3f69654` (075's
landing) with no conflict: the draft and its revision, then `b760a6e` (the checks, written first),
`fa5321e` (the guard), `767404d` (the lxml check), then these notes. Evidence:
`../research/2026-10-19-guest-fuel-and-the-checkout-path/build/`. All runs against
`build/sets/s-c50ca51fae5eb55b` in the main tree, read only; `-n 3`.

The confirmation's two points are taken. c1: `_forms` makes a `file:` URI only for an absolute
path, so the Windows-shaped unit row runs on POSIX. c2: the check binds `host = str(ro /
"secret.txt")` once, asserts on that string, and passes that string to `OUTSIDE`.

### The checks fail first (criteria 1 and 4a, EXECUTED)

- On main's driver, all six new unit rows fail (`unit_first.out`).
- Against the draft's prototype guard, three fail, as criterion 4a asks: the `file:` URI, the
  Windows root (escaped and in another case) and the system temp root (`unit_against_prototype.out`).
- With the guard alone (`fa5321e`), of the 69 fuel functions exactly the lxml grant check's two
  rows fail, each `ValueError: a measured run gives the guest a host path in argv[3]` (`build_guard_only.out`).
  No other measured run is refused by the added roots and forms, here or in the full judge.

### Two paths, one fuel (criteria 2 and 4, EXECUTED)

- **The two lxml rows**, from the worktree (44 characters) and the clone (205), three runs at
  each: plain **506,200,859** and snapshot **215,014,922** every time (`build_fixed.out`,
  `build_spread3.out`). These are Decision 3's restated values, to the instruction.
- **All 148 rows that run without a build**, three runs at each path (`spread.py`,
  `build_spread3.out`): no row is offset by the path. On 146 rows the spread between the paths is
  no wider than the spread at one path. On matplotlib's two plot rows it is wider by 34 (two
  steps of 17): `test_plot_line_job_matches_native[snapshot]` spreads 187 at one path and 221
  over both, `[plain]` 102 and 136. Their means differ by −62 and −34 instructions (under one part
  in 10^8), the long path the *lower*; before the fix the lxml snapshot row moved +113,522. These
  are Decision 4's timestamps, whose spread six samples can widen; the literal reading of
  criterion 4 misses on these two rows by two steps, and I say so rather than re-run.
- **Decision 4's bound moves.** The draft saw steps up to 119; the build sees 187 at one path on
  matplotlib's plot row (8.8 G instructions; 2 parts in 10^8). On that row it is harmless; it
  shows that a check reading many file times takes more steps. The roadmap line for 083 says so.

### The probe still bites (criterion 3, EXECUTED, `mutate.py`, `build_mutants.out`)

In the long clone, each mutant fails both rows:
- `m1`, `ro` granted at its own host path for `OUTSIDE`: `entity outside grants: ok
  '<r>SECRET\n</r>'` and `the host's secret was read`;
- `m2`, the control naming `file:///ro/elsewhere.txt`: the control gives `<r/>`;
- `m3`, a made-up host path: the host-side assertion (`FileNotFoundError`);
- `m4`, `SAFETY` answering "entity outside grants" too: the disjoint-keys assertion.

### The judge (criterion 5, EXECUTED, `build/fast-081.log` and `build/full-081.log` in the worktree)

- `ruff check` and `ruff format --check` on `src/` and `tests/`: clean.
- Fast tier (`uv run pytest -m "not slow" -n 3`): `474/550 pass · 1 gap · 24 blocked · 0 fail ·
  51 deselected (unit suite 1366/1374, 8 skipped)`; `1840 passed, 32 skipped, 1 xfailed`;
  `ratchet vs 35f76d3b3d: lost 0 · absent 0 · unrun 0 · unrun locally 22 · gained 0 · grew 0 ·
  upstream unrun 31 · not selected 37 · judge changed: tests/checks/conftest.py,
  tests/checks/test_v1_3_lxml.py, tests/harness/guest.py and 1 more`.
- Full (`uv run pytest -n 3`): `491/550 pass · 3 gap · 56 blocked · 0 fail (unit suite
  1366/1374, 8 skipped)`; `1857 passed, 64 skipped, 3 xfailed`; `ratchet vs 35f76d3b3d: lost 0
  · absent 0 · unrun 0 · unrun locally 42 · gained 0 · grew 0 · upstream unrun 31 · judge
  changed: …` (the same four files). The blocked checks need source trees, the oracle, the
  wheel, the wasmtime CLI and the like, which a worktree without a build lacks; the lane runs
  them. Its `build/progress/latest.json` is kept in the worktree.
- The two restated rows fall, so the ratchet prints no line for them.

### Rebased onto `08de0c8` and merged with 063 (Decision 5)

Spec 063 landed as `19427b5` (squashed) and `08de0c8`. The rebase conflicted only in
`test_stylesheets_and_entities_reach_only_grants`, in two hunks; the roadmap and everything else
merged cleanly. The merge, by hand (`build/merge_with_063.diff`, against the pre-rebase tip
`e194f46`):
- 063's `import sys` is kept at the module's top;
- the docstring keeps both sentences: 063's (on Windows the drive and backslashes are refused by
  name, so libxml2 reports the load failed, and still nothing is read) and 081's (the unrecorded
  run, with its guest-path read);
- the outside case takes 063's platform branch: on `win32`, `XMLSyntaxError` with "failed to
  load" and "Operation not permitted"; elsewhere `ok <r/>`;
- 063's "no `SECRET`" line moves out of the `win32` branch and runs on every platform;
- unchanged from the build: `OUTSIDE` unrecorded and `SAFETY` measured, each exit code
  asserted; the host-side assertion on the string passed; the two disjoint keys; the control;
  the twelve other `expect` lines; the `out.xml` assertion.
The measured program is unchanged, so the two rows' fuel is unchanged: plain 506,200,859 and
snapshot 215,014,922 in the merged full run.

**The judge after the merge** (`-n 3`, against `build/sets/s-c50ca51fae5eb55b`;
`build/fast-081-merged.log`, `build/full-081-merged.log`; `build/progress/latest.json` kept):
- fast tier: `476/554 pass · 1 gap · 25 blocked · 1 fail · 51 deselected (unit suite 1503/1511,
  8 skipped)`; `1 failed, 1979 passed, 33 skipped, 1 xfailed`; `ratchet vs 9a446e03f6: lost 1 ·
  absent 0 · unrun 0 · unrun locally 23 · gained 0 · grew 0 · upstream unrun 31 · not selected
  37 · judge changed: tests/checks/conftest.py, tests/checks/test_v1_3_lxml.py,
  tests/harness/guest.py and 1 more`;
- full: `493/554 pass · 3 gap · 57 blocked · 1 fail (unit suite 1503/1511, 8 skipped)`; `1
  failed, 1996 passed, 65 skipped, 3 xfailed`; `ratchet vs 9a446e03f6: lost 1 · absent 0 · unrun
  0 · unrun locally 43 · gained 0 · grew 0 · upstream unrun 31 · judge changed: …` (the same four
  files).
- **The one failure is not 081's.** `test_manifest_recipes_match_the_tree`: `stale artifact:
  scripts/refuse-python is not in MANIFEST; stale artifact: scripts/build.sh changed` (digest
  `0e68988ea311`). Spec 079 changed `scripts/` after `s-c50ca51fae5eb55b` was built, so that
  set's `MANIFEST` no longer matches main's recipes. Main `08de0c8` itself fails the same check
  against that set, with the same digest (EXECUTED in a clean clone, `build/main_manifest_check.out`).
  Against the lane's newer set `s-c50ca51fae5eb55b-c9dcb5b8`, whose two binaries are
  byte-identical to `s-c50ca51fae5eb55b`'s and whose `MANIFEST` differs only in the recipe lines,
  the check passes in this worktree. The lane judges against that set, so it should see no
  failure; the fuel rows cannot differ, since the binaries are the same.

### For the lane

- `--accept-judge "spec 081: a measured guest run may not be given a host path (the driver
  refuses it), so fuel does not depend on where the checkout is; the lxml grant check's
  host-path probe runs on its own, unrecorded, and its two rows' fuel is restated (both fall)"`.
