# 089 — host litter never reaches a verdict: the judge seals its stages and watches its grants

- **Status:** **landed 2026-10-19** in a batch with 083 (constitution §5.7; accepted on `69004e2` as `45b917c`, history line 80, `-n 3`; sameness clean against both reviewers; dry run 39346796670 green on all three systems; reviews: `../reviews/089-host-litter-never-reaches-a-verdict-spec-2026-10-19.md`, `../reviews/089-host-litter-never-reaches-a-verdict-build-2026-10-19.md`, `../reviews/089-083-batch-delta-2026-10-19.md`; follow-up from the delta review, L1: one `try`/`finally` from `litter.seal(lib)` to `run()`'s return, so a before-run `HostLitter` or an error before the `try` still releases; N1: on Windows an unremovable `lib` now prints a line after five tries). Before landing: **built 2026-10-19** on `spec/089-host-litter-never-reaches-a-verdict`, from main
  `3866f56` (the Landing notes). **Revised 2026-10-19 against its pre-build review** ("build once
  F1", `../reviews/089-host-litter-never-reaches-a-verdict-spec-2026-10-19.md`; the section
  "Disposition of the pre-build review"). **Drafted 2026-10-19** from main `3866f56`. It changes
  neither the guest's imports nor its exports, the artifact set nor the build recipe, so §5.6 asks
  no review before build. A different agent reviews the build.
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** a judge change; **parallel-safe**, not build-class (§5.7). New
  `tests/harness/litter.py`, `tests/unit/test_host_litter.py`; edits to `tests/harness/guest.py`
  (`run`, `mpl_data_dir`), `tests/harness/regrtest.py` and `tests/harness/upstream.py` (each
  `Session`, its `_run` and its stage writer; `upstream.safe_unzip`), `tests/checks/conftest.py`
  (the `guest_workdir` fixture), `tests/unit/conftest.py` (the `work` fixture),
  `tests/harness/plugin.py` (one session-start line), and one new check in
  `tests/checks/test_v1_4_embedding.py`. No `src/`, `scripts/`, `recipes/`, `downloads/`, workflow
  or README. It moves no accepted fuel (criterion 4): the lane accepts it with `--accept-judge`.
- **Depends on:** nothing unlanded. **It lands before spec 083** (the lane's order, with the
  owner's agreement, 2026-10-19): main's serial judge cannot run cleanly while a desktop process
  writes into the stages, and 083's landing waits on exactly that. **083 then rebases onto it**;
  their only shared file is `tests/harness/guest.py`, where 089 adds a few lines around the
  preopens and before `run()` returns, and 083 adds its call shadows. The merge (build review F2,
  EXECUTED there with `git merge-tree`): **one textual conflict**, in `guest.py`'s tail, 089's
  `try: watch.after() finally: litter.unseal(lib)` and `return Result(` against 083's
  `result = Result(` and `_release(store, lib)`; and **one semantic conflict**: 083's `_release`
  does `shutil.rmtree(lib, ignore_errors=True)`, which on a folder 089 sealed removes nothing and
  says nothing. The resolved shape is in "For the lane"; the lane checks it in 083's delta review.
- **Research it stands on:** `../research/2026-10-19-ds-store-in-the-judges-stages.md` (EXECUTED:
  the writer, the probe, the six trials, `prototype.diff`). Spec 083's build review, last addendum
  (the `.DS_Store` files in `build/harness/cpython/run-*` mid-run).

## The problem

The ratchet holds fuel to one part in ten thousand, and the lane's sameness check stops a landing
on any difference between a builder's `-n 3` record and its own serial one. So fuel must depend
only on the artifact and the check.

macOS writes `.DS_Store` files, as the user, into folders that something sizes: on the owner's
Mac, System Settings' storage scan and Finder (the memo, §1). They land in the judge's live
stages. Spec 083's build review caught `build/harness/cpython/run-*/.DS_Store` and
`…/lib/.DS_Store` appearing mid-run; `cpython-a`, `-c` and `-archives` moved by up to 1.6e-3 from
run to run, in the main tree only. That stopped 083's landing.

The judge did not notice. A simulated writer on a scratch clone's stage moves `cpython-archives`
from 164,648,434,127 to 164,609,014,815 (−2.4e-4), and the check **passes** (the memo, trial r3).

## Principle

A file a host process drops into a folder the guest sees is either **refused** (it cannot land) or
**named** (the check fails, saying which file). It is never measured, and never hidden: nothing is
filtered from what the guest sees.

## Decisions

1. **Litter, by name.** `litter.is_litter(name)`: `paths.OS_LITTER` (spec 011's three:
   `.DS_Store`, `Thumbs.db`, `desktop.ini`), `ehthumbs.db`, AppleDouble files (`._` prefix), `Icon\r`, and the
   volume-root names `.Spotlight-V100`, `.fseventsd`, `.Trashes`, `.TemporaryItems`,
   `.DocumentRevisions-V100`, `.apdisk`. `paths.OS_LITTER` itself is not changed here (the build
   shares it through a unit check; spec 090 widens both).
2. **Seal every read-only stage.** Once a stage is written, every folder in it loses its write
   bits (`litter.seal`). No process of the user's can add, remove or rename an entry (EXECUTED: the
   real writer and the simulated one are both refused by a 0555 folder). Folder modes do not reach
   a WASI guest: a filestat carries no mode, and wasmtime opens a read-only grant read-only either
   way. Sealed:
   - the CPython stage (`regrtest.Session`, at the end of `_prepare`, after `judge/`);
   - the upstream stage (`upstream.Session`, once its first `prepare` has staged every package);
   - matplotlib's data (`guest.mpl_data_dir`, after extraction; shared by a session's runs);
   - each run's stdlib folder (`guest.run`, after `_place`, before the watch; F4).

   **Writable roots are detection-only.** The guest writes there, so they cannot be sealed;
   Decision 4 names any litter in one. That is acceptable: the 083 review's watch log (554 lines,
   four main-tree runs) saw the writer only in `build/harness/`, `cpython/` and the stage, never in
   a `guest-*` folder, and the full judge here saw it only in the stages' parents. On Windows a
   folder's mode does not stop a write, so nothing is chmodded there and Decision 4 alone holds; no
   desktop writer is known there. `seal` still removes staging litter on Windows (only the chmod is
   skipped). Files are never chmodded (a run's `lib/python315.zip` is a hard link to the set's).
   - **A stage's writer refuses a litter-named member** (F6): `regrtest.stage`, `upstream.stage`
     and `upstream.safe_unzip` call `litter.refuse` on every member they write, an
     `AssertionError` naming it. So `seal`'s cleanup can only ever meet a file the stage did not
     write. No pinned tarball or kit wheel holds such a member today (the review's scan).
   - **Litter that lands while a stage is written** (EXECUTED: 172 files in the 2 s of staging)
     is removed by `seal` after every folder is closed: each file's folder is opened for its
     unlink alone, and the scan repeats until clean (ten rounds at most, then `HostLitter`). It
     was never staged and no guest has run, so this hides nothing from a guest.
   - **No symlink anywhere.** `seal` changes modes in place, on the real folders `mkdtemp` made
     under `paths.HARNESS_TMP`. It never moves a stage or links to one (the first attempt's
     lesson 1, below).
3. **Unseal, then remove, and retry.** `litter.remove(root)` gives every folder its owner's write
   bit back (carrying on past a folder it cannot change), removes the tree, and tries again (five
   times at most) if a writer refilled a folder between rmtree's unlinks (EXECUTED: today's
   `shutil.rmtree(…, ignore_errors=True)`, racing the writer, left a stage behind, silently). If
   anything is left after the last try, it is left unsealed and named on stderr, never in silence.
   `regrtest.Session.close` and `_run`, `upstream.Session.close` and `_run`, the `guest_workdir`
   fixture and the unit `work` fixture call it.
   - **A killed judge** (SIGKILL, SIGTERM, a worker crash: no teardown runs) leaves sealed: its
     stages, its mpl-data folders, and the stdlib folder of each run still live at the kill (at
     most one per worker). Every other run's stdlib folder is unsealed when its run ends
     (`guest.run`'s `finally`, build review F1: before that fix, a kill 75 s into two check files
     left 27). `rm -rf` cannot empty a sealed folder, so `rm -rf build` and `git worktree remove`
     fail on what is left (the reviews' `rm_sealed.out`, `kill-n2.out`). It is never read again:
     every stage and run folder has a fresh name. The recovery, `chmod -R u+w build/harness` then
     `rm -rf`, is named in `litter.py`'s docstring, in every `HostLitter` message, and in one line
     the controller writes at session start when any sealed folder is left under
     `build/harness` (`litter.sealed_leftovers`; named, never unsealed).
   - **No sweep of stale stages.** A stage's owner may be a live judge in another process of the
     same worktree (an xdist worker, a second pytest); telling a dead owner from a live one needs a
     pid marker, and pid reuse makes that unsafe. Leftovers are inert, so a named recovery is
     safer than a sweep that could seal or delete a live run's grant.
4. **Watch every guest run.** `guest.run` builds a `litter.Watch` over the grants it preopens,
   just before it preopens them, and checks it just before it returns:
   - no grant holds a litter entry, before the run or after it;
   - a read-only grant lists exactly the same entries after the run as before (any file, litter or
     not).

   A failure raises `litter.HostLitter`, an `AssertionError` naming each file by its guest path and
   where such files come from. The check fails and records no fuel. Nothing is retried. The cost is
   one `os.walk` per grant before and after a run; the CPython stage has 178 folders. `Turns`
   (multi-call instances) is not watched here: its grants are a root, the stdlib folder and a
   check's own, and none is a stage.
5. **The check that proves it.** `test_a_file_dropped_into_a_stage_changes_nothing`
   (`test_v1_4_embedding.py`, both binaries): it stages a folder of a few files under the guest
   workdir as the harness stages one (`litter.seal`), tries to drop a `.DS_Store` into every folder
   of it as a desktop writer would, then runs a program that
   lists each of the stage's folders at `/stage` by name (`os.listdir`, which reads no inode
   number or time, so the comparison holds before 083 too) and prints the listings, and compares
   with the same program on a twin stage no writer touched: the same exit, the same output, the
   same fuel, and no `.DS_Store` in the stage. **Where a folder's mode binds** (POSIX, not root)
   each drop must be refused and the twins must match. **Where it does not** (Windows, where
   nothing is chmodded; root, F1) the drops land and the dropped stage's run must fail with
   `HostLitter` naming `/stage/.DS_Store (before the run)`. On both, the twin's run passes and is
   the last, measured run, so the fuel row is the same program on every host (the `own-embedding`
   shard runs on macOS, Linux and Windows). On main it fails with an `ImportError` (no `litter`
   module); two mutants of the build show its power (criterion 1).

## Intent

No file a host process drops into a grant of the judge's own driver (`guest.run`) changes a
verdict or a fuel value silently, whichever process writes it: a stage, an mpl-data folder or a
run's stdlib folder refuses it (sealed), and any of its grants that changes anyway, a check's own
read-only folder or a writable root included (watched, not sealed), fails its run, naming the
file. `Turns` and the product runner's runs are neither sealed nor watched (N2).

## Design

`tests/harness/litter.py` holds the litter names, `seal`, `unseal`, `remove` and `Watch`. The two
`Session`s seal their stages when staged and remove them through `litter.remove`; `mpl_data_dir`
seals the data it extracts; the `guest_workdir` fixture removes through `litter.remove`. `guest.run`
builds its `Watch` from the exact list it preopens, before the preopens, and calls `after()` once
the run has ended, before it returns its `Result`. The new check stages two small folders the same
way and compares them.

### What the first attempt taught

- **A mitigation is tried on the whole fast tier before it is called working.** The research
  proposed a symlinked `build/harness` outside the home folder for 083's rerun, from one CPython
  group. The lane tried it: 87 runner and session checks failed, because the product runner
  refuses a root that passes through a symlink in a user-writable folder. So this spec's seal uses
  no symlink anywhere in a stage's path (Decision 2), and its build runs the full judge.
- **Immunity, whoever writes.** The writer was identified only far enough to know it runs as the
  user and respects folder modes. The seal does not depend on which process it is, and the watch
  names whatever gets past the seal (a root process, a Windows host).
- **Link counts.** A shared artifact set reached nlink 151 after a killed run (spec 039), and link
  counts reach fuel. The build judges a private `cp -c -Rp` copy of the set with every file at
  nlink 1, and never touches the main tree's `build/`; `paths.HARNESS_TMP` is the worktree's own.
- **Parallel and serial alike.** The lane's sameness check compares the reviewer's `-n 3` record
  with its serial one; 083's difference came from this litter. Nothing in 089 depends on worker
  count: every stage, mpl-data folder and watch belongs to one process.

## Scope

In: Decisions 1 to 5. Out, to spec 090: the build's walks, the release tarball, the artifact-folder
checks, `OS_LITTER`'s widening, `.gitignore`. Out, to a later spec of its own: a third
watch, a litter name handed to the guest by `fd_readdir`, which needs a readdir shadow (083's
`FileFacts.listing` already walks every entry; F7). Out: which process writes
the files; the product runner's grants.

## Acceptance criteria

1. **The checks fail first, and have power.** On main `3866f56`:
   `test_a_file_dropped_into_a_stage_changes_nothing` fails on both binaries with an `ImportError`
   (the import is inside the check, so only its two rows fail, not the file's collection), and
   `tests/unit/test_host_litter.py` fails to collect (its import is at module level). That shows
   only that the module is missing (F2). The power is shown by two mutants of the build, each on
   both binaries, with their failure lines in the landing notes: (a) `litter.seal` a no-op: the
   check fails with `HostLitter` naming `/stage/.DS_Store (before the run)`; (b) seal and watch
   both no-ops (main's behaviour): the listing shows `.DS_Store` and the fuel differs.
2. **The unit rows.** With the build, `tests/unit/test_host_litter.py` passes: litter names (yes
   and no rows); a sealed stage refuses a write in every folder (skipped on Windows and as root);
   a stage writer refuses a litter-named member (`refuse`, the CPython stage, a kit wheel);
   `seal` removes what landed while
   staging and returns it; `remove` removes a sealed tree; the watch names litter before a run, any
   new entry in a read-only grant (a non-litter `stray.py` included), and litter in a writable root
   after a run, and passes a writable root the guest changed.
3. **The drop check passes,** on both binaries, and the stage holds no `.DS_Store` after it.
4. **Nothing moves.** `ruff check` and `ruff format --check` green. The fast tier `-n 3`, then the
   full judge once (`-n 3`), against a private copy of `build/sets/s-c50ca51fae5eb55b-c9dcb5b8`
   (every file nlink 1, checked before the run): no failure, no lost pass, **no accepted fuel row
   moved past its tolerance**; the ratchet shows the new check's rows as gained and
   `judge changed`. The landing notes give the record's path and the counts.
5. **Cleanup.** After the full judge, no `run-*` stage is left under the worktree's
   `build/harness/cpython` or `build/harness/upstream`, and no folder under `build/harness` lacks
   its owner's write bit.
6. **The upstream groups** (CPython a, b, c, fs, archives; numpy's and pandas'), when their trees
   are present in the worktree, pass at their accepted fuel. If the build cannot run them (no
   trees), the landing notes say so and the lane's serial judge is their measurement.

## For the lane

- **Accept with** `--accept-judge "spec 089: the judge seals its read-only stages (the CPython and
  upstream stages, matplotlib's data, each run's stdlib folder) and watches every guest run's
  grants (tests/harness/litter.py; guest.py, regrtest.py, upstream.py, plugin.py,
  tests/checks/conftest.py, tests/unit/conftest.py); one new check, test_a_file_dropped_into_a_stage_changes_nothing (both
  binaries), and tests/unit/test_host_litter.py; no existing check, golden, gap or allowance
  edited"`.
- **The expected record:** gained, the new check's two rows; `judge changed`; lost 0; grew 0,
  except the CPython groups on this base's own noise (below).
- **089 and 083 land as one batch** (constitution §5.7 as amended 2026-10-19; build review F3).
  On this base real inode numbers and times reach the guest, so `cpython-a`, `-b`, `-c`, `-fs` and
  `-archives` spread run to run: up to 8.5e-5 on main `3866f56` alone in three runs, and the build
  reviewer's full judge put `cpython-c` at +1.21e-4. 083 removes those host file facts; 089 removes
  the litter. Together they make the CPython rows exact.
  - **The batch's flags:** 089's `--accept-judge` text above, together with 083's own `--accept`,
    `--accept-judge` and `--accept-growth` texts (083's "For the lane").
  - **A sameness difference** between a reviewer's record and the lane's that is confined to rows
    083 changes is explained by 083 (`context/progress/README.md`, step 3a's batch rule); any other
    difference splits the batch.
  - **If they ever land apart,** 089 first: a CPython row past 1e-4 whose move is covered by main
    `3866f56`'s measured spread on the same private set is accepted with `--accept-growth
    "<row>: this base's own noise before 083 (spec 089, F8), main 3866f56 gave <values> on the same
    set"`, and the main runs are recorded in the landing notes. A row main's spread does not cover
    is 089's to explain.
- **083's rebase onto 089, resolved** (build review F2). `_release` removes `lib` through
  `litter.remove` after the store is closed, and the watch runs before it, in a `try`/`finally`
  that still releases; 089's `litter.unseal(lib)` folds into it:
  ```python
  def _release(store: wt.Store, lib: Path | None) -> None:
      """After a guest: its store closed first (on Windows, wasmtime's handles in `lib` go with it),
      then its own stdlib folder, which spec 089 sealed, unsealed and removed; `litter.remove`
      never raises, so it can never fail a run, and names on stderr anything it could not remove."""
      store.close()
      if lib is not None:
          litter.remove(lib)
  ```
  and the tail of `run()`:
  ```python
      except BaseException:
          _release(store, lib)
          raise
      spent = fuel - store.get_fuel() if metered else 0
      result = Result(
          exit_code=exit_code,
          stdout=(io / "stdout").read_bytes(),
          stderr=(io / "stderr").read_bytes(),
          trapped=trapped,
          fuel=spent,
          root=root,
          trap_cause=cause,
      )
      try:
          watch.after()  # before the release: the watch must see the run's own stdlib copy
      finally:
          _release(store, lib)
      return result
  ```
- **A run that fails with `HostLitter` is void,** not a verdict on the change. The lane removes the
  cause (closes System Settings' Storage pane and Finder windows on the checkout; for a stage a
  killed judge left, `chmod -R u+w build/harness`), runs again, and records the void run and the
  files it named in the landing notes. The re-run is a whole fresh judge, never the failed checks
  alone. This is not the re-run AGENTS rule 6a forbids, and needs no further agreement: rule 6a
  forbids re-running a *measured* run to make a sameness difference go away; the void-run rule
  re-runs nothing measured, it discards a run that measured nothing, since `HostLitter` records no
  fuel and says the host changed the judge's own inputs (N3). A sameness difference without
  `HostLitter` keeps rule 6a.
- **If a fuel row moves** past its tolerance in the lane's run, compare it with a run of main
  `3866f56` on the same private set before calling it 089's (F8): on this base real inode numbers
  and times still reach the guest until 083 lands.

## Disposition of the pre-build review

The review (`../reviews/089-host-litter-never-reaches-a-verdict-spec-2026-10-19.md`, on
`0ae5253`): "build once F1; F2 to F6 before landing; F7 to F9 are notes". Each is answered here,
and in the build.

- **F1 (the drop check on Windows): fixed.** Decision 5 and the check branch on whether a folder's
  mode binds (`sys.platform != "win32"` and `os.geteuid() != 0`): refused and equal where it binds;
  landed and `HostLitter` "before the run" where it does not. The twin's run is last everywhere.
- **F2 (fails on main only by ImportError): fixed.** Criterion 1 says what the main-tree failure is
  (per row for the check; collection for the unit file), and adds mutants (a) and (b); their lines
  are in the landing notes.
- **F3 (a killed run leaves sealed stages): fixed.** `unseal` carries on past a folder it cannot
  change; `remove` leaves nothing sealed and names on stderr what it could not remove; the recovery
  `chmod -R u+w build/harness` is in `litter.py`'s docstring and every `HostLitter` message. No
  sweep, with the reason in Decision 3.
- **F4 (the stdlib folder; writable roots): fixed.** Each run's stdlib folder is sealed after
  `_place`; `regrtest.Session._run` and `upstream.Session._run` remove run folders through
  `litter.remove`, as do both fixtures; Decision 2 says writable roots are detection-only, and why;
  "Decision 3 watches it" is gone.
- **F5 (for the lane): fixed.** The section above: the acceptance text, the expected record, the
  void-run rule and why it is not rule 6a's re-run.
- **F6 (the cleanup could delete a real input): fixed** by the first of the two ways offered: the
  stage writers refuse a litter-named member (`litter.refuse`), with unit rows.
- **F7 (083's rebase; the readdir watch): answered.** The Depends-on line says `watch.after()` goes
  before 083's `_release`, in a `try`/`finally`. The `fd_readdir` watch goes to a later spec of its
  own, not to 083's rebase, so 083 lands as reviewed (Scope).
- **F8 (main's own noise): answered.** "For the lane" says to compare a moved row with main
  `3866f56` on the same set first. The memo's trials ran on `d84bb7e` (with 083); on this base the
  evidence is the review's probe and this build's runs (the landing notes).
- **F9 (small points): fixed.** The refusal unit row skips on Windows and as root; every row that
  seals uses `tmp_path` (pytest's own removal chmods) or `litter.remove`; Decision 1 lists
  `ehthumbs.db`; Decision 2 says `seal` still removes staging litter on Windows; the Intent says
  "silently".

## Disposition of the build review

The review (`../reviews/089-host-litter-never-reaches-a-verdict-build-2026-10-19.md`, on
`6f525a0`): "lands once F1 to F3".

- **F1 (a kill leaves every run's stdlib folder sealed): fixed.** `guest.run` unseals `lib` in a
  `finally` after the run and `watch.after()` (not removed: on this base the zip's link count
  reaches fuel; 083's `_release` removes it). A unit row, `test_a_runs_stdlib_folder_is_unsealed_after_a_voided_run`,
  fails without the `finally` (EXECUTED: `['…/run-0/lib']` left sealed) and passes with it.
  Decision 3 names what a kill leaves. The controller writes one line at session start naming any
  sealed leftovers and the recovery (`litter.sealed_leftovers`, with a unit row); no sweep, as
  Decision 3 argues (a lock-keyed sweep, the review's alternative, is left for later if needed).
- **F2 (083's `_release` on a sealed lib): fixed in writing.** The Depends-on line states the merge
  exactly; "For the lane" gives the resolved `_release` and `run()` tail.
- **F3 (a CPython row past 1e-4 on main's own noise): fixed in writing.** "For the lane": 089 and
  083 land as one batch, with the batch's flags and the sameness rule; and the rule if they ever
  land apart.
- **N1 (two writers without `refuse`): applied.** `mpl_data_dir` refuses each inner member before
  `extractall`. `_place`'s `copytree` of a stdlib folder skips litter names instead of refusing
  them: its source is a host folder (the reference build) a desktop writes into, where a refusal
  would fail checks for a file that is no input; skipping is the collecting-walk rule spec 090
  states.
- **N2 (what is sealed, watched, neither): applied** in the Intent.
- **N3 (the void-run rule): applied.** "For the lane" says the re-run is a whole fresh judge, and
  why the rule needs no further agreement: it discards an unmeasured run, it re-runs no measured
  one.
- **N4 (a partial upstream stage stays unsealed): noted.** A refused member fails `_prepare`
  loudly; later checks fail on "no source tree"; nothing is measured on that stage.

## Landing notes

Built 2026-10-19 in `../wasi_python-089`, on main `3866f56`, by the agent that wrote the draft
(a fresh agent reviews the build). Evidence: `../research/2026-10-19-ds-store-in-the-judges-stages/at-build/`
(`first-fail.txt`, `mutants.txt`, `drop-repeats.txt`, `judge.txt`); the full record is
`build/089/latest-full.json` in the worktree. Every run used a private `cp -c -Rp` copy of
`build/sets/s-c50ca51fae5eb55b-c9dcb5b8` (`shasum -c` OK; no file with nlink above 1, checked
before each judge), and the CPython, numpy and pandas tarballs, trees and kit wheels APFS-cloned
from the main tree into the worktree (read only there; their `.DS_Store` files deleted from the
copies).

### What was built

- `tests/harness/litter.py`: `is_litter`, `refuse`, `seal`, `unseal`, `remove`, `Watch`,
  `HostLitter` (Decisions 1 to 4).
- `guest.run` seals the run's stdlib folder after `_place`, builds the `Watch` from its exact
  preopen list just before preopening, and calls `after()` before returning; `mpl_data_dir` seals
  what it extracts.
- `regrtest.Session` and `upstream.Session` seal their stages once staged, and remove stages and run
  folders through `litter.remove`; `regrtest.stage`, `upstream.stage` and `upstream.safe_unzip`
  refuse a litter-named member. Both fixtures remove through `litter.remove`.
- `tests/unit/test_host_litter.py` (18 rows) and `test_a_file_dropped_into_a_stage_changes_nothing`
  (both binaries).

### Criterion 1: the checks fail first, and have power (EXECUTED, `first-fail.txt`, `mutants.txt`)

- On main's code with the new checks: both rows of the drop check fail with `ImportError: cannot
  import name 'litter' from 'harness'` (per row: the import is inside the check); the unit file
  fails to collect (its import is at module level).
- Mutant (a), `seal` a no-op, both binaries: `HostLitter: … /stage/.DS_Store (before the run);
  /stage/judge/.DS_Store (before the run); /stage/lib/.DS_Store …`.
- Mutant (b), seal and watch no-ops (main's behaviour), both binaries: the listing differs,
  `/stage ['.DS_Store', 'judge', 'lib']`, `/stage/lib ['.DS_Store', 'c.py', 'test']`,
  `/stage/lib/test ['.DS_Store', 'a.py', 'b.txt']`. With the output assertion also removed
  (plain), the fuel assertion fails: **168,162,442 against the twin's 168,144,427** (+18,015).

### Criteria 2 and 3 (EXECUTED)

- The unit rows pass (with `test_upstream.py`, `test_regrtest.py`, `test_guest.py`: 173 passed,
  4 skipped).
- The drop check passes on both binaries, three runs each, one fuel value each: **plain
  168,144,427, snapshot 16,284,357** (`drop-repeats.txt`). No `.DS_Store` in the stage after it.

### Criterion 4: nothing moves (EXECUTED, `judge.txt`)

- `ruff check` and `ruff format --check`: green.
- The fast tier, `-n 3`: 483/625 pass, 0 fail; the ratchet: lost 0, gained 2, grew 0, judge
  changed.
- **The full judge, `-n 3`, once, 18:52 to 19:01: 525/625 pass · 77 gap · 23 blocked · 0 fail
  (unit suite 1597/1605, 8 skipped); ratchet vs `b91e0ea`: lost 0 · absent 0 · unrun 0 · unrun
  locally 21 · gained 2 · grew 0 · judge changed.** 2122 passed, 31 skipped, 77 xfailed.
- Against `accepted.json`, 164 fuel rows compare; **none moves past 1e-4**. The largest moves are
  main's own noise before 083 (F8): `cpython-fs` 5.3e-5, `cpython-c` 4.1e-5, `cpython-a` 3.7e-5,
  `cpython-archives` 3.4e-5.
- A full run before the review's fixes (same code but F1, F3, F4, F6) gave every check the same
  outcome and fuel: `sameness.py` between the two records differs only in the unit suite's count
  (1600 against 1605, the five new unit rows).
- **The real writer was active, and the seal held.** A watcher on the worktree's `build/harness`
  through both full runs saw `.DS_Store` written into `build/harness/`, `cpython/` and `upstream/`
  (the stages' parents; `build/harness/.DS_Store` grew from 6,148 to 8,196 bytes during the final
  run), and never inside a stage, a guest root or an mpl-data folder. No run failed with
  `HostLitter`.

### Criterion 5: cleanup (EXECUTED)

After the full judge no folder under `build/harness` lacks its owner's write bit, and no stage of
that run is left. Two older stages were there, from a run I stopped by hand (below), made while
mutant (a) had turned the seal off, so unsealed; `rm -rf` took them.

### Criterion 6: the upstream groups (EXECUTED)

All sixteen ran in the full judge and passed: CPython a, b, c, fs, archives; numpy core, lib,
others; pandas' eight. Their fuel is within the tolerance of `accepted.json` (above).

### After the build review (EXECUTED, `judge-after-build-review.txt`)

Rebased onto main `302df18` (context/ and AGENTS.md only; no conflict). F1 and N1 in `51a5ce8`,
the text in `2eed9ee`. On `2eed9ee`, clean, the same private set (no file above nlink 1):

- The unit rows with `test_guest.py`, `test_upstream.py`, `test_regrtest.py`: 175 passed, 4
  skipped. F1's row fails without the `finally` (`['…/run-0/lib']` left sealed).
- **The fast tier, `-n 3`:** 483/625 pass, 0 fail; lost 0, gained 2, grew 0.
- **The full judge, `-n 3`, once, 19:34 to 19:42:** `wasi_python v1: 525/625 pass · 77 gap · 23
  blocked · 0 fail (unit suite 1599/1607, 8 skipped)`; `ratchet vs b91e0eaa4e: lost 0 · absent 0 ·
  unrun 0 · unrun locally 21 · gained 2 · grew 0 · judge changed`; 2124 passed, 31 skipped, 77
  xfailed. The record: `build/089/latest-full.json` in the worktree.
- Against `accepted.json`, none of 164 fuel rows moves past 1e-4; the largest are the CPython
  groups (`cpython-a` −8.9e-5, `cpython-c` +5.1e-5, `cpython-archives` −3.3e-5, `cpython-fs`
  +1.7e-5), this base's own noise (F3). `sameness.py` against the previous full run (`6f525a0`):
  only the unit suite's count differs (1605 against 1607, the two new rows).
- **The real writer reached a stage, and the seal took it.** The watcher saw macOS write
  `build/harness/cpython/run-p087q_vy/lib/.DS_Store` at 19:34:50, three seconds into the run,
  while the CPython stage was being written. `seal` removed it when the stage was sealed (no group
  failed with `HostLitter`, and every group passed at its usual fuel): the staging-litter cleanup
  of Decision 2, met by the real writer. No sealed folder is left under `build/harness`.

### Departures and incidents

- **A stray full-suite run.** In zsh, `"$N[$w]"` subscripts `$N` (lesson 6 of the brief): one
  mutant command ran the whole suite serially instead of one node. I stopped it (TaskStop); its
  stages stayed, unsealed (mutant a), and were removed by hand. No record from it is used.
- The first full judge ran before the pre-build review's fixes; it is kept as
  `build/089/pre-review-latest-full.json` only for the sameness comparison above.
- Plain and snapshot fuel were swapped in my interim message to the lane; the values above are
  right (plain runs the whole startup).

One line: the judge seals every stage it grants read-only and fails any run whose grants change,
so a file a desktop process drops is refused or named, never measured.
