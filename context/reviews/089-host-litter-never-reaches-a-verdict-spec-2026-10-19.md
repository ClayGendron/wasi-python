# Review of 089 — Host litter never reaches a verdict (the specification, before build)

- **Date:** 2026-10-19
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I wrote none of the spec, the
  memo, the prototype or the code. I read `AGENTS.md`, the constitution (§5.6, §5.7), spec 002 (the
  ratchet), spec 052 (Decision 11, `sameness.py`), spec 083's pre-build review for the format, and,
  at main `3866f56`: `tests/harness/guest.py` (`run`, `_place`, `mpl_data_dir`),
  `tests/harness/regrtest.py` and `tests/harness/upstream.py` (each `Session`, `_run`,
  `preopens`), `tests/checks/conftest.py`, `tests/unit/conftest.py`, `tests/harness/paths.py`,
  `tests/release_shards.toml`, the release workflow's `runs-on` lines, and every `preopens=` and
  `mpl_data=` caller in `tests/`. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `spec/089-host-litter-never-reaches-a-verdict` at **`0ae5253`**, on main `3866f56`:
  - `e115d00`: specs 089 and 090, the memo `research/2026-10-19-ds-store-in-the-judges-stages.md`
    and its evidence folder (`prototype.diff`, `trials/`, `tools/`, probes), and the roadmap lines.
  - `0ae5253`: Intent, Design and Landing notes sections added to 089 and 090; 089's "What the
    first attempt taught" moves under Design. See "The second commit" below.
  - Both commits touch only `context/` (READ, `git show --stat`).
  - 090 was read only to see where 089 ends.
- **Ran (EXECUTED, darwin-arm64, APFS, wasmtime-py 49).** Nothing was written in any git tree or in
  the main tree's `build/`. Everything is beside this file:
  - `base/`: `git archive 3866f56 tests src pyproject.toml`.
  - `set/`: a private `cp -c -Rp` copy of `build/sets/s-c50ca51fae5eb55b-c9dcb5b8`. Every file has
    nlink 1.
  - `probes/seal_on_base.py` → `out/seal_on_base.out`: main's own driver (no spec 083) runs one
    program that lists a granted stage. The stage is plain, sealed, sealed with drops tried, or
    unsealed with drops landed.
  - `out/rm_sealed.out`: `rm -rf` on a sealed tree.
  - A scan of the pinned tarballs the stages are built from (`Python-3.15.0.tar.xz`,
    `numpy-2.5.2.tar.gz`, `pandas-3.0.6.tar.gz`) and of every wheel in `downloads/`, for members
    with litter names.
  - Spec 083's build-review watch log (`083-buildreview/lane/watch.out`), read to see where the
    real writer wrote.
  - I did not run the fast tier. The prototype is written against `d84bb7e` (it carries 083's
    `FileFacts` and `_release`), so it does not apply as is to `3866f56`. The builder's full judge
    is the measurement.

## What holds

- **The problem and its channel (EXECUTED, on main's driver).** A `.DS_Store` dropped into each
  folder of an unsealed read-only grant shows up in `os.listdir`. It also moves fuel: 16,611,224
  becomes 16,650,743 (+39,519, +2.4e-3). So the drift does not need 083's clock: main's own judge
  has it (`out/seal_on_base.out`).
- **The seal refuses a writer and costs no fuel on this base (EXECUTED).**
  - Drops into a 0555 stage: five of five folders refused.
  - Plain, sealed, and sealed with drops tried each spend **16,611,224**, with the same output.
    Repeat runs give the same value.
  - So "folder modes do not reach a WASI guest" holds on `3866f56`, not only on the prototype's
    base. READ: `preopen_dir(…, fs_mutable=False)` gives wasmtime read-only perms. A guest's write
    is refused by wasmtime's own check before the host's mode is consulted, so the errno does not
    change either.
- **No symlink anywhere (READ).** Decision 2 changes modes in place, on folders `mkdtemp` made. The
  prototype chmods only folders that `os.walk` yields, and never follows a link. Files are never
  chmodded. That matters: the per-run `lib/python315.zip` is a hard link to the set's zip
  (`guest._place`), so a file chmod would change the shared set.
- **It fails closed (READ, INFERRED).** If the seal does not hold (a root process, a filesystem
  that ignores modes, Windows), the watch still names any litter before or after the run, and any
  change in a read-only grant. If the staging cleanup does not converge in ten rounds, `seal`
  raises. `HostLitter` is an `AssertionError`. Nothing between `guest.run` and the check catches
  it: the guest fixture and both `Session._run` callers let it through. My grep found broad
  `except` clauses only around product-runner calls and inside guest programs.
- **Linux (READ).** The release's Linux jobs run on `ubuntu-24.04` and `ubuntu-24.04-arm` as the
  runner user, with no `container:`. Modes are honoured there.
- **Parallel and serial alike (READ).** Each stage, mpl-data folder and watch belongs to one
  process. `_mpl_data` is a cache per process, and `guest_workdir` is per worker. Nothing depends
  on the worker count.
- **Private copies (READ).** Criterion 4 names a `cp -c -Rp` copy with every file at nlink 1,
  checked before the run, and the worktree's own `HARNESS_TMP`. That answers the nlink-151 lesson.
- **The whole fast tier, then the full judge (READ).** Criterion 4 and Design's first-attempt
  section both say it. That answers the symlink lesson (87 checks failed).
- **Nothing is weakened (READ).**
  - Nothing is filtered from what the guest is shown.
  - Nothing is retried.
  - No check, golden, gap or allowance is edited.
  - The only removal is staging litter, before any guest runs. F6 adds a guard to it.
- **The 089/090 split is right (READ).** 083 is blocked by litter in the judge's stages. 089 holds
  exactly that: seal, watch, removal, one check. The build's walks, the release tarball and
  `OS_LITTER`'s widening are build-class, and none of them reaches 083's verdicts. 090 says it
  does not need 089. 089 depends on nothing unlanded.
- **Class (READ).** 089 touches only `tests/`. It is parallel-safe, not build-class. It changes no
  imports, exports, artifact set or recipe, so §5.6 asks for no review before build. This review
  is the courtesy the Status line offers.
- **Turns are left out correctly (READ).** `Turns` grants are a root, the stdlib folder and a
  check's own folders. None is a stage.
- **The other read-only grants in the fast tier are fresh (READ).** Every `preopens=` caller grants
  a fresh folder under `guest_workdir`: `test_extra_preopens_work_on_the_snapshot`'s `data-*`, and
  lxml's `_grants`. lxml's FILES check already asserts its read-only grant is unchanged. No guest
  program in `tests/` writes a litter name (grep). The test sources of CPython, numpy and pandas
  create no file whose name starts with `._` (grep; test_site's `._pth` is a suffix). So the watch
  should raise no false failure.

## Findings, most severe first

### F1. The drop check fails on Windows as written. Blocks build (READ)

- `tests/checks/test_v1_4_embedding.py` is the `own-embedding` shard, which runs on `macos`,
  `linux` **and `windows`** (`tests/release_shards.toml`; the release's `windows-2025` job).
- Decision 2 says nothing is sealed on Windows. So the drops land, and Decision 4's watch raises
  `HostLitter` "before the run" on the dropped stage.
- Decision 5 asks for "the same exit, the same output, the same fuel, and no `.DS_Store` in the
  stage" on both binaries. That fails on Windows.
- It would show only in the release dry run (AGENTS rule 6b), after the landing.

**Fix.** Give Decision 5 and criterion 3 a Windows branch that keeps the principle, "refused or
named", on every host:

- POSIX: assert each drop raises `PermissionError`. Then the dropped stage and its twin give the
  same exit, output and fuel, and the stage holds no litter.
- `win32`: assert the drops land, and the dropped stage's run raises `HostLitter` naming
  `/stage/.DS_Store (before the run)`.
- On both: the twin's run passes and is the measured (last) run, so the fuel row is the same
  program everywhere.

Also skip the POSIX refusal assertion when `os.geteuid() == 0`, where modes do not bind (a
container). Or take the Windows branch there.

### F2. "Fails on main" is an ImportError, which proves nothing about the behaviour. Fix before landing (READ, EXECUTED)

- Criterion 1 says the check fails on `3866f56` "because there is no `litter` module". That
  failure shows the module is missing. It does not show that the check catches a drop.
- If `from harness import litter` sits at module level, collecting the whole of
  `test_v1_4_embedding.py` fails on main, not one check on two binaries. The landing notes would
  then quote a collection error.

**Fix.** Keep the main-tree failure line, stated as what it is. Add two mutants on the built tree,
with their failure lines in the landing notes:

- (a) `litter.seal` made a no-op: the check fails with `HostLitter` naming
  `/stage/.DS_Store (before the run)`. The file is named.
- (b) seal and watch both made no-ops: the listing shows `.DS_Store` and the fuel differs. That is
  main's behaviour. My probe shows it on main's driver: +39,519 fuel, and
  `/stage ['.DS_Store', 'judge', 'lib', 'top.txt']` (`out/seal_on_base.out`).

Those two mutants are what show the check has power.

### F3. A killed run leaves sealed stages, and a sealed tree defeats `rm -rf`. Fix before landing (EXECUTED)

- `rm -rf` on a tree with 0555 folders fails with "Permission denied" and leaves the tree
  (`out/rm_sealed.out`).
- A judge killed without teardown leaves its `cpython/run-*` and `upstream/run-*` stages and its
  `guest-*/mpl-data-*` sealed. Ways that happen: SIGKILL, an xdist worker crash, a timeout kill,
  spec 039's killed run.
- Then `rm -rf build`, `git worktree remove` (the lane's last step for a worktree) and any cleanup
  fail, and the stages pile up on disk.
- The spec says nothing about this. Separately, the prototype's `remove` gives up silently after
  five tries. Its `unseal` also stops at the first `OSError`, so it can leave sealed folders
  behind. That is the silent leftover the memo faults `ignore_errors=True` for.

**Fix.**

- `unseal` carries on past an error on one folder.
- After its last try, `remove` never leaves a folder without its owner's write bit, and it reports
  what is left: a warning line naming the path, never silence.
- Name the recovery in `litter.py`'s docstring and in the `HostLitter` message:
  `chmod -R u+w build/harness`.
- Either sweep stale sealed stages at session start, or say in a sentence why not. A sweep could
  remove a `run-*` stage whose owning pid, written in a marker beside the stage, is dead. It must
  never touch a live worker's stage.
- Criterion 5 stays as written.

### F4. Writable roots and the per-run stdlib folder are named, not refused. Seal the one that can be sealed. Fix before landing (READ, INFERRED)

- Decision 2 leaves `guest-*/run-N/lib` (read-only, fresh) and `guest-*/run-N/root` (writable)
  unsealed.
- A CPython group runs for minutes, and the memo's `lsof` caught `StorageManagementService` holding
  `build/harness/guest-m0gndg21` open. So on the owner's Mac a 089 judge can still go red with
  `HostLitter` in `/usr/local/lib` or `/`. That is loud, not silent, but it can stall the serial
  run that 083's landing waits on.
- The evidence so far is reassuring. The 083 review's watch log has 554 lines over four main-tree
  runs and only four paths: `build/harness/`, `cpython/`, `cpython/run-r_uoe6lp/` and its `lib/`.
  None is under `guest-*` (READ). So the writer was seen only where the seal now reaches.

**Fix.**

- Seal the per-run `lib` folder after `_place` and before the `Watch`. It is read-only and fresh,
  and sealing it costs nothing.
- Remove each run folder through `litter.remove`. That means changing the
  `shutil.rmtree(r.root.parent, ignore_errors=True)` lines in `regrtest.Session._run` and
  `upstream.Session._run`. The `guest_workdir` fixture already covers the guest fixture's runs.
- Say plainly in Decision 2 that a writable root is detection-only, citing the watch log as the
  reason this is acceptable.
- Correct "the per-run stdlib folder (… Decision 3 watches it)" to Decision 4.

### F5. No "For the lane" text, and no rule for a run that `HostLitter` voids. Fix before landing (READ)

- 089 changes files under `tests/`, so the judge hash moves. The Kind line says only "the lane
  accepts it with `--accept-judge`".
- AGENTS rule 6a says a sameness difference stops the landing "until the check is fixed, never a
  re-run". A `HostLitter` failure is not a check to fix. It voids a run because the host changed
  it. Without a written rule, the lane cannot tell which applies.

**Fix.** Add a "For the lane" paragraph with:

- The acceptance text, for example: `--accept-judge "spec 089: the judge seals its read-only
  stages and watches every guest run's grants (tests/harness/litter.py; guest.py, regrtest.py,
  upstream.py, tests/checks/conftest.py); one new check,
  test_a_file_dropped_into_a_stage_changes_nothing (both binaries), and
  tests/unit/test_host_litter.py; no existing check, golden, gap or allowance edited"`. Adjust the
  file list to what the build touches.
- A rule: a run that fails with `HostLitter` is void, not a verdict on the change. The lane
  removes the cause (closes System Settings' Storage pane and Finder windows on the checkout),
  runs again, and records the void run and its named files in the landing notes. A sameness
  difference without `HostLitter` keeps rule 6a.
- The expected record: gained, the new check's rows; `judge changed`; lost 0; grew 0.

### F6. `seal` deletes any litter-named entry, including one the stage itself wrote. Fix before landing (EXECUTED, READ)

- Decision 2's cleanup removes every litter name it finds after staging. If a pinned tarball, a
  patch or a kit wheel ever ships a member named `._x`, `desktop.ini` or `Icon\r`, the judge would
  delete a real test input without a word. That is the hidden filtering the Principle rules out.
- Today nothing ships one. `Python-3.15.0.tar.xz`, `numpy-2.5.2.tar.gz`, `pandas-3.0.6.tar.gz` and
  every wheel in `downloads/` hold no such member (EXECUTED scan).
- But only 090's unit row would keep it that way, and 090 lands later.

**Fix.** Give 089 the guard. Either:

- the stage writers (`regrtest.stage`, `upstream.stage`, the kit unzip) refuse a member with a
  litter name, as an `AssertionError` naming it; or
- 090's "no pinned tarball holds such a member" row moves into 089's unit file, widened to the kit
  wheels and the patches' created files.

### F7. 083's rebase is not purely textual; give the `fd_readdir` watch to its own spec. Note (READ)

- The memo's trial r2 failed with "`/usr/local/lib/python315.zip` vanished during the run". The
  watch ran after 083's `_release(store, lib)`.
- The spec says the 083 merge "is textual". It should add one line: in 083's rebase,
  `watch.after(...)` runs before `_release`, as the prototype's `try/finally` does.
- Scope says 083's rebase "adds" the `fd_readdir` watch. That is new behaviour after 083's
  reviews, and it would need a delta review. Assign it to a later spec instead, so 083 lands as
  reviewed.

### F8. Criterion 4 is measured against main's own noise. Note (EXECUTED, READ)

- On `3866f56` real inode numbers and times reach the guest. 083's pre-build review saw a spread
  on 35 rows over five runs of main's driver.
- The seal itself is fuel-neutral (EXECUTED, above). So if a row moves past its tolerance in the
  build's run, first compare it with a run of main `3866f56` on the same private set. Only then
  call it 089's.
- The memo's trials ran on `d84bb7e`, with 083's shadows. My probe is the only evidence on this
  base. Say so in the landing notes.

### F9. Small points. Note (READ)

- **Unit rows.**
  - The "a sealed stage refuses a write" row needs a skip on Windows (the prototype has one) and
    when `geteuid() == 0`.
  - A row that seals under the `work` fixture must remove through `litter.remove` in a `finally`.
    That fixture's `rmtree(ignore_errors=True)` would leave a sealed tree, and criterion 5 would
    fail.
  - `tmp_path`, as the prototype uses, is cleaned by pytest's own `rm_rf`, which chmods.
- **The litter list.** Decision 1 omits `ehthumbs.db`. The prototype and 090's list have it.
  Align, so 090's replacement changes nothing.
- **Windows cleanup.** Say whether `seal` still removes staging litter on Windows. The prototype
  does: only the chmod is skipped.
- **Intent (added in `0ae5253`).** "No file … can change a verdict" overclaims. A `HostLitter`
  failure turns a pass into a fail. Say "never silently: it is refused, or its run fails naming
  the file", as the Principle does.

## The second commit, `0ae5253`

- It touches only 089 and 090 (+36, −1; READ, `git diff e115d00 0ae5253 --stat`).
- In 089 it adds Intent, a Design paragraph and "Landing notes: Not built yet", and makes "What
  the first attempt taught" a subsection of Design. No Decision, criterion, Scope, Kind or Status
  line changed (READ, the diff).
- The Design paragraph agrees with Decisions 2 to 5: the `Watch` is built from the exact preopen
  list before the preopens, and `after()` runs before the `Result` is returned.
- 090 gains Intent, Design and Landing notes, consistent with its Decisions. 090's Design does not
  say that 089's `tests/harness/litter.py` names are folded in. That is for 090's own review.
- The commit message's "no decision changed" holds. The only new claim is the Intent's wording
  (F9).

## Verdict

**Build once F1.** F2 to F6 before landing; F7 to F9 are notes.

- F1 is a sentence in Decision 5 and a branch in the check. Without it the release's Windows job
  fails.
- F2 gives criterion 1 two mutants that prove the check's power.
- F3 and F4 close the leaks: a sealed tree left after a kill, and the one read-only folder left
  unsealed.
- F5 gives the lane its acceptance text and a rule for a void run.
- F6 keeps the staging cleanup from ever deleting a real input.

The design is sound. On main's own driver the seal refuses the writer and costs no fuel, and an
unsealed drop moves fuel by 2.4e-3. The watch makes anything that gets past the seal loud. And
089 holds exactly what 083's landing needs.

In one line: seal and watch are the right defence and fuel-neutral on this base, but the drop
check needs a Windows branch before build, and the spec must still cover killed runs, the
unsealed stdlib folder, the lane's rule for a void run, and a guard so the cleanup never deletes
a real input.
