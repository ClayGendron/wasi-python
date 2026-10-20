# Build review of 084 — a private root never outlives its call, 2026-10-19

- **Reviewer:** a fresh agent. I wrote none of 084's code or checks. I reviewed its spec before
  the build (`084-a-private-root-never-outlives-its-call-spec-2026-10-19.md`, beside this file,
  confirmed at `b9763ec`).
- **Under review:** `spec/084-a-private-root-never-outlives-its-call` at `2fbeaca`, rebased onto
  main `9d89535`. `b9763ec..2fbeaca` also carries main's 065, so I read the branch's own diff,
  `9d89535..2fbeaca`.
  - Its spec text at `2a9708d` equals the confirmed `b9763ec` in everything 084's own.
  - The code and checks are `0cefbc0` and `e4d418f`: `runner.py` +447, `test_runner_sweep.py`
    +501, `test_v1_4_embedding.py` +156, plus README, CHANGELOG and the landing notes.
  - No `scripts/`, `recipes/`, pins or workflow change, so it is parallel-safe as declared.
- **Read:**
  - the whole runner diff: `_remove_tree`, `_Removal`, `_remove_at`, `_enter`, `_listing`,
    `_is_folder`, `_long_path`, `_remove_by_path`, `_Private.remove`, `_sweep_once`,
    `_sweep_entry`, `_remove_fresh_home`, `_warn_later`, `_flush_warnings`,
    `_run_checked_flushed`, and the flush calls in `Session.__init__`, `_end_session` and
    `_release`;
  - every caller of `_end_session` and `_end_with_ctrl_c`, to see whether a lock is held at the
    flush;
  - every new check, and the restated one;
  - the README and CHANGELOG diffs, and the landing notes;
  - the builder's logs: `build/084-checks-on-main.log`, `084-standins.log`,
    `084-standins-c10.log`, `084-py311.log`, `full-084-build2.log`, and `b_counts.out`.
- **Ran (EXECUTED, darwin arm64, CPython 3.14.2)**, in the 084 worktree, against my private
  `cp -Rp` copy of `s-c50ca51fae5eb55b-c9dcb5b8`. It is identical to the frozen set (`diff -r`,
  and `SHA256SUMS` checks OK). I never used the main tree's `build/artifacts`. Every record went
  to my scratch folder with `--progress-latest`, so the builder's `build/progress/latest.json`
  (`43a96ef`) is untouched. Outputs are in `build-review/` beside this file:
  - **the full judge:** `uv run pytest -n 3` (`latest.json`);
  - **sameness** between the builder's record and mine (`sameness_builder_vs_mine.txt`);
  - **ruff:** `ruff check` and `ruff format --check` on `src` and `tests` (`ruff.txt`);
  - **my pre-build probes, against the built code:** F1 (`r1b-home.log`, `r1b-private.log`)
    and F2's attacks (`r2b_built.log`, `probes/r2b_built_attacks.py`);
  - **four stand-ins of my own**, each from a scratch copy of `src/` put first on `PYTHONPATH`
    (confirmed by import), never by editing the worktree.

  I wrote nothing in any git tree (`git status` is clean). Every probe tree was deleted by name.

Labels: **EXECUTED** (I ran it), **READ**, **INFERRED** (reasoned, not run).

## Short version

The build does what the confirmed spec says, and it is correct where it matters.

- **The removal holds two descriptors at any depth.**
- **It changes no mode.** My F1 probe now keeps the host's read-only file in both cases.
- **The climb check holds.** My attacks keep the canary in every case.
- **The rest works as specified:** the retry, the bound, the order of the drop and the re-arm,
  the queued warning and the `HOME`'s budget.

My judge equals the builder's: **501/629 pass · 3 gap · 125 blocked · 0 fail**, unit suite
1595/1603 (8 skipped), and `sameness.py` finds no difference. All seven departures are sound.

One finding to fix before landing, and two notes:

- **B1 (medium). Criterion 7's check is dangerous when it bites** (EXECUTED, to my cost). With
  the identity check removed, the walk climbs out of the test's `tmp_path` and deletes what lies
  up to four levels above it. In my stand-in run that was my scratch review folder. In a default
  judge run it would be the session's whole pytest base temp, with every xdist worker's folders.
  The check is right and it bites, but a regression would turn the judge itself destructive.
  Nest the tree under enough throwaway levels that any escape stays inside `tmp_path`.
- **N1 (nit):** the warning's `stacklevel` points into `wasi_python`, not at the caller.
- **N2 (nit):** a Windows top that is any reparse point is unlinked, which is stricter than the
  test used for entries. It is safe; it can only leave a folder.

## 1. The judge (EXECUTED)

- **The command:**
  `WASI_PYTHON_ARTIFACTS=<my copy> uv run pytest -n 3 --progress-latest=build-review/latest.json`
  on `2fbeaca` (`meta.commit`, `dirty: false`).
- **The record:** 629 checks: **501 pass, 3 gap, 125 blocked, 0 fail**. The unit suite gives
  `{"passed": 1595, "skipped": 8, "total": 1603}`. These are the builder's numbers. The 125
  blocked are the upstream groups and rebuild checks, which have no source trees in a worktree
  without a build, as the landing notes say.
- **`uv run python tests/harness/sameness.py`** against the builder's `build/progress/latest.json`
  (`43a96ef`, whose code and checks are `2fbeaca`'s) and mine: no difference, exit 0. So the
  ratchet is the builder's: `lost 0 · grew 0 · gained 6` (the six new embedding nodes), and the
  judge changed in exactly the two check files. That ratchet line is the builder's
  (`full-084-build2.log`). **My run's console output was lost**: my own B1 stand-in deleted the
  log file's directory entry mid-run, while the record was written at the end
  (`full_judge.txt` says so).
- **ruff:** `All checks passed!`, and `105 files already formatted`.
- **For the lane's sameness step:** my record is
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/5c4a788f-6229-4fb4-8a87-05b4e7e5e695/scratchpad/084-review/build-review/latest.json`.

## 2. The pre-build probes against the built code (EXECUTED)

- **F1** (`r1b-*.log`, through the built runner, no routing). The guest's unlink is refused, and
  it moves `data/` into its `HOME` (or its private root). `secret` is **kept** in both cases:
  under `tmp/.home-…/data/ro/`, and in the left private root with its lock file. One
  `RuntimeWarning` names each folder, with the first error (`[Errno 13] Permission denied:
  'secret'`).
- **F2** (`r2b_built.log`, the built `runner._remove_tree`):
  - A2, C2 and D (a subtree moved out after the open, a subtree renamed up, a parent moved out)
    return **False** with the canary kept;
  - B (a folder swapped for a link) returns False and leaves the link, as Decision 2 now says;
  - A and C (the moves made before the open) remove the tree, and nothing escapes.

## 3. The stand-ins

The builder's table lists 18, each with the checks that failed. Its logs match (`084-standins.log`,
and `084-standins-c10.log` for the two first written wrongly).

I re-ran four myself, from caged scratch copies (EXECUTED):

| stand-in | result |
|---|---|
| the identity check removed (`if False:`) | criterion 7 fails, **and the walk escaped** (B1) |
| the budget on private folders too (10,000) | criterion 9 fails: 9,989 unlinks, then the root and lock left |
| the warning given inside `remove` | criterion 14 fails: `_zip_lock` held (`[True, False, True]`) |
| the re-arm moved before the drop (the later re-arm removed) | criterion 10's drop-order check fails: `sweep()` 0 |

## 4. The code, against the spec (READ)

- **`_remove_at`** is Decision 2.
  - It runs `lstat` on the top, unlinks it if it is not a folder, then opens it `O_NOFOLLOW` and
    checks it by `(st_dev, st_ino)`.
  - A listing of at most 1,024 entries, closed before any action. It unlinks the non-folders in
    order up to the first folder, then descends.
  - The climb opens `..` and compares it with the recorded parent before any `rmdir` or
    listing; a mismatch raises `EBUSY`, which becomes False.
  - The other device is refused twice: by the entry's `stat` and by `fstat` after the open.
  - An unopenable folder gets one `rmdir` (the confirmation's N1).
  - No `chmod`, `mkdir` or `rename` anywhere. The deep case's counts are 3.50 calls per entry
    with a peak of two descriptors (`b_counts.out`; criterion 4's bound is 5 plus 5).
  - `DirEntry.stat()` after the listing closes still works: an fd-based entry keeps the
    original `cur`, which is still open. Termination without a writer: every pass removes,
    descends, records a failure, or ends the folder.
  - Two tiny leaks (INFERRED, not worth a change): an `os.fstat` that raised right after
    opening `child` or `..` would leak that descriptor. Neither call fails in practice.
- **The budget** applies only to the `HOME` (`_remove_fresh_home`, `budget=_REMOVE_BUDGET`).
  Private folders and sweeps get `budget=None`. That is the confirmation's C1, taken, and
  criterion 9's third part checks it.
- **`_Private.remove`:**
  - the walk is guarded by `except Exception`;
  - in a `finally`: unlock and close, unlink the lock file only if the folder is gone, then
    `_drop`;
  - after that, and only if the folder was left: the queued warning, then the re-arm under
    `_lock`. Decisions 5 and 6, in the right order.
- **`_sweep_once` and `_sweep_entry`:**
  - the per-name count is kept under `_held_lock`, and a name at `_SWEEP_TRIES = 3` is skipped;
  - `_sweep_entry` returns whether a retry is due, and the re-arm happens once, in
    `_sweep_once`'s `finally`, after the loop;
  - the warning is keyed by the name, so a folder's own removal and its sweeps warn once per
    process in all.
- **The warning queue:**
  - `_warn_later` appends under its own lock;
  - `_flush_warnings` swaps the list out and warns with no lock held, each warning inside
    `try … except Exception`;
  - I checked every flush point's callers: `_end_session` is reached through `_end_with_ctrl_c`
    (from `Session.close`, `_claim`, and a turn's end) and through the closer thread, each after
    its `with state.lock:` block has closed. No runner lock is held at any flush.
- **The restated check** (criterion 15): the same assertions through `runner._remove_tree`, plus
  `pytest.warns(RuntimeWarning, match=private.name)`, with the flush inside. Faithful and
  stronger. The fixture `temp` also resets `failed`, `_warned` and `_pending_warnings`, so the
  fixed `dead()` name cannot carry a count from one case to the next.
- **README and CHANGELOG:**
  - a new *Safety* item;
  - the *Not protected* additions: a folder a removal had to leave; a concurrent writer can hold a
    `HOME` removal for up to 2**20 calls, "about 50 s on an arm64 Mac", which matches my
    pre-build measurement; private folders have no such limit;
  - two **Fixed** entries, the second for 3.11.

  All match criterion 19. No sentence says Windows guests cannot make links, and the runner's
  two comments are corrected.

## 5. The seven departures, weighed

1. **Criterion 14 holds `_zip_lock` around `remove()` directly**, instead of driving
   `_zip_folder`'s re-make path and a `run`. **Sound.**
   - It is the same lock, taken the same way `_zip_folder` takes it, and the same queue.
   - Its stand-in bites (EXECUTED: a non-blocking `acquire` of `_zip_lock` fails from inside the
     handler).
   - The flush as `run` returns is covered elsewhere: criterion 3's child records the warning
     around `run` and never flushes itself.
   - What it no longer proves is that `_zip_folder`'s own code path queues rather than warns.
     That path calls the same `_Private.remove`, so nothing is lost.
2. **The flush points leave out `Session.run`.** **Sound.**
   - A turn that does not end its session runs no sweep and removes nothing: `_preopens`, and so
     the sweep and `_zip_folder`, run only at the opening, and the folders go at the ending.
   - A turn that ends the session flushes in `_end_session`.
   - What a turn's flush would add is only messages queued by other threads, which the next
     flush gives anyway. That will matter for 078's abandoned teardown, which Decision 7 already
     covers ("given by the next flush").
3. **`errors=` on `_remove_tree`**, private, for the warning's text. **Fine.**
4. **Criteria 6 and 10 split into several functions** (16 unit nodes, 6 embedding nodes).
   **Fine.** Criterion 9's node is named `…_keep_a_home_removal_going` rather than the spec's
   `…_keep_the_removal_going`, which fits its narrower scope after C1.
5. **Criterion 4's stand-in (c) is not written as a mutant.** **Acceptable.** The check asserts
   an `os.rename` count of 0 directly, so any renaming design fails it by construction.
6. **Criterion 9's `HOME` rows call `_remove_home` directly.** **Sound.** `_call_deferred` and
   `_remove_home` both go through the one `_remove_fresh_home`, and the stand-in "no budget on
   the `HOME`" bites.
7. **The Windows path walk unlinks a top that is any reparse point** (`FILE_ATTRIBUTE_REPARSE_POINT`),
   not only a link or a junction. **Sound, and safe** (READ, INFERRED).
   - `os.unlink` on a directory goes to `RemoveDirectoryW` (`Py_DeleteFileW`). That removes a
     name-surrogate link without following it, and refuses a real non-empty folder.
   - So the worst case is a non-link reparse folder (one a cloud-sync or container filter
     tagged) left and warned about, never followed and never emptied. A private root is made
     by the runner in `%TEMP%`, where such tags are unlikely.
   - It is stricter than `_is_folder` for entries (symlink and junction only, as `shutil`). The
     difference can only leave a folder (N2).
8. **Windows is not run here.** That is right for a worktree. Criterion 17, the lane's dry run, is
   where criteria 1 to 4, 6 and 8 to 15 show `PASSED` on `windows-2025`, and where C2 is
   settled. I read the Windows legs for path handling: `deep_tree` builds through `\\?\`;
   `long_path` and `_long_path` agree; `fresh_home` passes no handle on Windows; `writer`'s
   `unlink(path, dir_fd=None)` is valid on Windows; criterion 3 skips with its reason if the
   guest deletes the read-only file. I found nothing that should fail there, but only the dry
   run can say.

## Findings

### B1. Criterion 7's check deletes outside its `tmp_path` when it bites. Medium (EXECUTED)

`tree_with_canary` builds `tree/` and `outside/` directly in `tmp_path`. When the identity check
is missing, the walk climbs once per frame left on its stack, up to four levels: `outside` →
`tmp_path` → the base temp → its parent. It removes what it finds at each level.

- **What I saw.** I ran the stand-in with `--basetemp=<scratch>/build-review/bt-identity`. It
  deleted every entry of `build-review/`: my judge's open log, my diff copy, my earlier logs,
  and the stand-in source copies themselves (which is why my next three stand-ins first ran
  against the real code and passed, until I re-ran them from a deeper folder). The judge's
  record survived only because it was written later. Nothing above `build-review/` was touched.
- **Where it would land by default.** Pytest's base temp is `pytest-of-<user>/pytest-N/`, with
  one `popen-gwK` per xdist worker. So the escape empties the whole session's temp, every
  worker's folders included, and the run fails loudly. It does not reach other sessions.
- **Why it matters.** A future regression of the identity check, or anyone re-running the
  stand-in with a custom `--basetemp` (as I did), deletes real files.
- **Fix (a test-only change, which strengthens the check):** build the tree and the canary under
  at least six throwaway levels inside `tmp_path`, more than the walk's deepest stack in these
  cases. Also assert that the throwaway chain is intact, so an escape both fails the check and
  stays inside `tmp_path`. The same applies to criterion 6's swap case, though its stand-in
  cannot climb.

### N1. The warning points into `wasi_python`. Nit (EXECUTED)

`_flush_warnings` warns with `stacklevel=3`. From `run` that names `runner.py:503`
(`return _run_checked_flushed(…)`), not the caller's line. From the closer thread or `_release`
it names other runner frames. Under the default filters every message is still shown, since
each names its own folder. But a filter by module (`module="myapp"`) never matches. Pointing at
the caller would need a depth per flush point. Optional. The README does not promise a location.

### N2. A Windows top with any reparse point is unlinked. Nit (READ)

See departure 7: safe, and at worst a folder left and named. If it ever shows up as a stray
warning on Windows, compare the top's reparse tag with `IO_REPARSE_TAG_SYMLINK` and
`IO_REPARSE_TAG_MOUNT_POINT`, as `_is_folder` does for entries.

## Verdict

**Lands once B1 is fixed:** criterion 7's tree and canary nested under enough throwaway levels
that a missing identity check fails the check without deleting anything outside its `tmp_path`.
After that change, the criterion 7 stand-in should be run once with a custom `--basetemp`.

This is a judge-file change only. The lane re-judges its exact commit as usual; my record above
holds for everything else. Then come the lane's Windows dry run (criterion 17, with the named
nodes) and the delta look at B1's diff. N1 and N2 are optional.

## One line

084's walk is right and my probes cannot break it. The judge matches the builder's exactly (501
pass, 0 fail, sameness clean), and every departure is sound. It lands once criterion 7's check is
nested so that, when it bites, it cannot delete outside its own temp folder, as it deleted mine.

## Addendum: the B1 fix (`7740b01`, tip `3e28d9b`), 2026-10-19

- **What changed (READ, `2fbeaca..3e28d9b`).** Only `tests/unit/test_runner_sweep.py` and a
  note in the spec.
  - `tree_with_canary` now builds `tree/` and `outside/` under `CHAIN = 8` throwaway levels
    inside `tmp_path`, each level holding a file `chain`.
  - Criteria 6's swap row and 7's three rows also assert `chain_intact(tmp_path)`.
  - The swap's parked folder moved to `tree.parent`.
  - No assertion was dropped. The canary assertions stay, so the checks are stronger, not weaker.
- **The stand-in, re-run by me (EXECUTED).** The identity check removed, from a caged scratch copy
  of `src/` (its import confirmed), under `--basetemp=<cage>/guard/bt`, with sentinel files in
  `guard/` and in the cage above it.
  - Criterion 7 fails in all three rows. Criterion 6's swap row passes (its walk cannot climb).
  - Both sentinels, the base temp and the stand-in's own source are all intact.
  - The builder's `build/084-b1-standin.log` agrees: chain levels 1 to 5 or 6 intact of 8, the
    damage inside the chain, its sentinel untouched.
  - **B1 is closed.**
- **N1 and N2:** answered without a change, as the review allowed.
- **Sameness (EXECUTED).** `sameness.py` on the builder's new record (`7740b01`,
  `build/progress/latest.json`: 501/629 pass, 3 gap, 125 blocked, 0 fail; suite 1595/1603)
  against mine (`2fbeaca`) finds **no difference at all**, not even the suite totals
  (`build-review/sameness_b1_vs_mine.txt`, empty, exit 0). The fix changed existing nodes and
  added none. My record differs only in `meta`: the commit, and the judge hash of
  `test_runner_sweep.py`. Sameness never compares `meta`. So my record still serves the lane's
  sameness step, and the lane's serial judge on its exact commit decides as always.

**Lands.**
