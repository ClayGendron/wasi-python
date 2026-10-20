# Review of wave 01 — integration of 087, 085, 084 and 091

- **Date:** 2026-10-20 (UTC; 2026-10-19 local)
- **Reviewer:** a fresh agent that wrote and reviewed none of the four entries
- **Reviewed:** `wave/01` at `daceacf` (main `7d0649d`, then 087, 085, 084, 091). The lane is
  judging `47b3695`, which is `daceacf` plus six files under `context/reviews/` (the copied
  084, 085 and 087 reviews). Nothing else (READ: `git diff --name-only daceacf 47b3695`).
- **Time box:** 45 minutes (the wave holds build-class entries).
- **Run:** none of my own. The wave's dry run is dispatched at the fast-forward (progress
  README step 7). I push nothing and touch no branch.
- **Re-ran:** no pytest tier, because `build/lane.lock` exists. I ran 14 unit rows on
  WebAssembly text (WAT) stand-ins, in a `git archive daceacf` export in my scratchpad, with its
  own `build/` (14 passed, 8.4 s, exit 0; `nodes.log`). Those rows were
  `tests/unit/test_runner_sets.py` (the whole file, 10 rows), plus
  `tests/unit/test_runner_sweep.py::test_the_warning_is_given_outside_every_runner_lock`,
  `tests/unit/test_guest.py::test_a_files_times_follow_the_runs_clock_step` and
  `tests/unit/test_upstream.py::test_a_session_runs_the_group_then_its_fact_and_records_each_fuel`.
  See N4: one of these was a file, not a node id. The run's ratchet line names the judge as
  changed in 26 files. That is exactly the union of the four claim lists:
  087 has 9, 085 has 9, 084 has 2 and 091 has 7, and `scoreboard.py` is counted in both 085 and
  091 (EXECUTED).

## Acceptance criteria against evidence

Each item is labelled EXECUTED, READ or INFERRED.

1. **Each entry's `git range-diff` against its reviewed tip** is `=` except for the hunks each
   builder names (EXECUTED; `rd-087.txt`, `rd-085.txt`, `rd-084.txt` beside this file).
   - **087** (`8c07ad4..ace3bdc` against `7d0649d..70bb1a2`): three commits are `!`.
     - The drafting commit: one `context/upstream/README.md` hunk. 078's row 21 is kept, then
       087's row 24. This is hunk 1 of 087's note.
     - The build commit: row 24's carried wording (hunk 2), and the *Deep recursion* paragraph,
       whose two sentences moved to *From any language* step 4 (hunk 3). It also takes the
       hostile-guest file's end (hunk 4).
     - The answer commit: no conflict. Its other differences are context lines that 078 changed:
       the README's `run` stack paragraph, `_run_checked`'s `finally`, and the
       `home = _Home()` line in `_open_session`. No code line of 087's moved.
     - `0f9e694` and `70bb1a2` are new and touch `context/` only.
   - **085** (`9d89535..b9eeadf` against `70bb1a2..650834a`): only the build commit is `!`, by
     the CHANGELOG hunk it names, with both sides kept. Its `release.yml` patch is byte-identical
     to `9128176`'s; the empty hunk in the range-diff is noise. `650834a` touches `context/` only.
   - **084** (`9d89535..b629d40` against `650834a..4d49f61`): two commits are `!`.
     - The build commit: the `_call_deferred` hunk and the `_end_session` hunk, both named.
     - The README and CHANGELOG commit: the CHANGELOG hunk, named.
     - Eight commits are `=`. `4d49f61` touches `context/` only.
   - **091** (`b4d7c8e..8255091` against `4d49f61..daceacf`): six commits are `=`, matching
     "no conflict hunk". `daceacf` touches `context/` only.
   - Nothing changed that a builder did not name.

2. **The named hunks keep their meaning** (READ; my merged runner is `runner-daceacf.py`).
   - **084 in `_call_deferred`.** 078's `release()` step does
     `store.close()`, then `_remove_fresh_home(...)`, then `_close(tmp_fd)`, through
     `_home_of(c).finish(release)`. This is 084's removal inside 078's ordering: the store closes
     before the folder goes (084, Decision 8).
   - **084 in `_end_session`.** 078's `finish()` (release, outcome, `done`, wake the reaper) runs
     at once, or through `home.finish`. 084's `_flush_warnings()` comes after, at function level.
     This is as it was on 084's reviewed tip, with 078's wrapping added.
   - **Criterion 14 and Decision 7 (warn outside every lock).** `_Home.finish` runs the step
     *after* it lets go of `self.lock`. `_Home.body` gathers an abandoned home's steps under the
     lock, releases it, and then runs them. So a removal never runs under the home's lock, and
     `_warn_later` takes only `_pending_warnings_lock`. Every flush site lies outside the runner
     locks:
     - `_run_checked_flushed` (used by `run` and `run_async`'s worker);
     - `Session.__init__`'s `finally`;
     - the end of `_end_session` (used by `close`, the closer thread and `_end_with_ctrl_c`);
     - `_release` at exit.

     The criterion's own row passes on the merged tree (EXECUTED).
   - **Ordering on an abandoned call.** The steps run in the order they were registered:
     `_call_deferred`'s release (store, then `HOME`), then `_run_checked`'s (walked handles, then
     the private root). Store first, Windows handles before the root: right (READ).
   - **The one semantic change the 084 note claims.** An abandoned guest's removal warns at the
     next flush. Decision 7 allows this in so many words: "A message queued after its call
     returned (078's abandoned teardown) is given by the next flush." The case that remains is N3.
   - **Every 078 `finish` site uses 084's removal.** The four sites are `_call_deferred`,
     `_run_checked`, the scratch `release()` and the failed opening's `_release_session`. Each
     reaches `_Private.remove`, `_remove_fresh_home` or `_remove_home`, never `shutil.rmtree`. The
     three `shutil.rmtree` calls left are the zip and data copies', the same as on 084's tip (READ).
   - **087 at the rebase.** The README's moved sentences say "measured at 512 KiB … as the runner
     ran before spec 078". That is true and necessary. `FileFacts` takes `clock_step_ns` on the
     merged driver (F3).

3. **087's unreviewed answer, `75afd08` (`ace3bdc`'s last commit), against its build review**
   (READ; the rows EXECUTED).
   - **F1, the time-of-check to time-of-use gap (TOCTOU), was offered as optional. It is taken
     and is correct.**
     - `_found_and_checked` returns `_Checked(binary, zip)`, the digests it compared.
     - `_module(..., want)` keys the in-process cache and the `.cwasm` name by the checked
       digest. On a miss it reads the bytes once, re-hashes them, and refuses on any difference
       (`ArtifactsMissing`, "changed after it was checked"). It compiles those same bytes with
       `wt.Module(engine, data)`, and writes a `.cwasm` only after that.
     - `_zip_folder(found, want)` keys the private copy by the checked digest, and `_copy_zip`
       holds the copy to it. So the review's cases a, b and z are closed.
     - Case c (a poisoned `.cwasm` that outlives the swap) cannot arise on the found-set path,
       because the only writer under a checked digest compiled checked bytes.
     - Both artifact loads, `_run_checked` and `_open_session`, pass both digests on.
     - `_zip_known` still hashes the zip on disk. After a swap it returns `None`, and the grant
       judge then protects the whole temp folder. That is stricter, so it opens no hole.
     - The three swap rows pass. So does the rest of `test_runner_sets.py`.
     - What is left is N1.
   - **F2 is met.** README lines 712–719 carry the review's clause almost word for word: it
     names the limit, a checkout's `build/`, and `artifacts=` "even one from `artifacts()`,
     which skips the check".
   - **F3 is met.** `guest.py:643` uses `clock_step_ns`. The new row
     (`ftime.wasm`, the default step and 2 ms) passes.
   - **F8 is fixed.** F4 to F7 are answered in writing.

4. **091's unreviewed answer, `80e6762` (`8255091`'s last commit), against its build review**
   (READ; the row EXECUTED).
   - **F1 is met.** `test_a_session_runs_the_group_then_its_fact_and_records_each_fuel` asserts
     each thing a mutant broke:
     - the two caps and the call order;
     - the staged `judge/f.json` equal to `fact_spec(...)` (M5);
     - `fuel == 111_000` (M3) and `fuel_facts == {"f": 222_000}` (M2);
     - `passes == 3` (M4);
     - the `fuel fact f:` prefix (M6) and the exactly-once finding (M1);
     - the cache (no third session).

     It passes on the merged tree.
   - **F3 is met.** `taken` holds every not-selected path, with any trailing `/` stripped, and a
     fact's file overlaps on equality or under that path as a folder. The row adds
     `numpy/tests`, `numpy/tests/` and the non-match `numpy/test`.
   - **F2 is met.** "For the lane" quotes the fall from 078's accepted 203,331,725,349 (about
     155.81 G expected), and says how sameness differences against the old-base record are read.

5. **The claim lists hold no overlap or contradiction** (READ).
   - **New goal checks:** 087's 7 and 084's 6, with no name shared. 085 and 091 add none.
   - **Growth:** only 087 claims any: the two `test_binary_is_a_core_wasm_module` byte rows,
     +202 each. 091 claims a *fall* in `test_upstream_suite[numpy-core]` fuel, plus the new fact
     `fuel_facts`, which is not ratcheted and not a metric. No entry claims fuel growth.
   - **Judge files:** 26 in all. The only file shared is `tests/harness/scoreboard.py`, between
     085 and 091, in different hunks. This matches the export's ratchet line.
   - **Rules that meet:**
     - 085's G5 requires every accepted metric to be finite and present on every system. 091's
       `fuel_facts` sits in `facts`, so G5 never sees it.
     - 087's new fuel rows use the standard `guest` fixture, which records fuel on every system,
       so G5's presence rule holds for them (INFERRED).
     - 085's G7 compares the newest line's `set_sums`. The wave's acceptance line is the first
       to carry one.
   - **No retire and no fewer-passes in any entry.**

6. **SHA256SUMS: local macOS build against CI's builds** (READ, EXECUTED).
   - **085 does not touch `scripts/assemble_artifacts.py`.** Its build-class files are
     `release.yml` and the judge. The only `assemble_artifacts.py` change in the wave is 087's,
     three lines: a `MODIFIED` entry for `0002-timeout-ticks.patch`. It is a fixed string,
     written into `LICENSES/regex.txt` on every host. It cannot differ by host.
   - **085's `release.yml` change only hashes what assembly wrote.** It adds
     `shasum -a 256 build/artifacts/SHA256SUMS` in the macOS `build` job. The local record hashes
     the same file (`plugin.py`, `meta.set_sums` from `paths.artifact_dir()/SHA256SUMS`).
   - **What SHA256SUMS depends on.**
     - Its order and format: files sorted by `Path`, operating-system litter dropped, `as_posix`
       names, `\n` endings.
     - The three binaries.
     - LICENSES: pinned tarballs, wheels and the patch list.
     - MANIFEST: fixed `SOURCE_DATE_EPOCH=1767225600` (`scripts/build.sh:20`); the pins, from
       `downloads/SHA256SUMS`, listing every host's pins; the wizer line, with a placeholder
       root; and a `recipe <sha256> <path>` line for every file `git ls-files recipes scripts`
       lists. That last part is hashed **from the working tree**.
   - **So the one way a local build can differ from CI's** is a working-tree file under
     `recipes/` or `scripts/` that differs from the commit CI builds. I checked this.
     - All 68 `recipe` lines in the main tree's `build/artifacts/MANIFEST` equal the SHA-256 of
       `daceacf`'s blobs. There are 68 tracked files, none dirty (EXECUTED).
     - `recipes/`, `scripts/` and `downloads/` are unchanged across
       `650834a..daceacf..47b3695` (EXECUTED).
   - **Linux against macOS** is already compared byte for byte. The "same bytes from every host"
     job `cmp`s each Linux rebuild's SHA256SUMS against the build job's set (`release.yml`
     357–364).
   - **Verdict:** nothing in 085, or in 087's assembly line, can make CI's Linux or macOS
     SHA256SUMS differ from the lane's macOS build. G7's `set_sums` line should be green on a
     dry run of `47b3695`, or of any later commit that changes nothing under `recipes/` or
     `scripts/` (INFERRED from the above).

7. **The accept log's GREW lines: pending.**
   - The claim lists allow exactly two:
     - `tests/checks/test_v1_1_artifact_set.py::test_binary_is_a_core_wasm_module[plain]: bytes 41099661 -> 41099863`
     - `tests/checks/test_v1_1_artifact_set.py::test_binary_is_a_core_wasm_module[snapshot]: bytes 44633983 -> 44634185`

     Both are 087's, and are covered by its `--accept-growth`.
   - `numpy-core` must show a fall to about 155.81 G (091), not a GREW line.
   - Any other GREW line is claimed by no entry. That includes a fuel row moved by 087's set's
     layout beyond the tolerance. Such a line needs its cause before the lane accepts.
   - I check the log when the lane sends it.

## Findings, most severe first

No High finding, and no Medium.

1. **L1 (Low, lane): the accept flags take one value each**
   (`tests/harness/plugin.py:95–97`, `addoption` with the default `store`).
   - Passing `--accept-judge` four times, once per entry, keeps only the last. It does so
     silently: the history line would carry 091's judge reason alone.
   - **Fix:** give each flag one quoted string that joins the entries' reasons in wave order.
     - `--accept-judge`: "087: …; 085: …; 084: …; 091: …".
     - `--accept-growth`: 087's text alone.
     - `--accept`: "Wave 01: …", with 087's and 091's `--accept` texts inside it.

     Every reason starts with its number, as step 3 asks. The five one-line texts (087's three,
     085's and 084's) contain no `$`, `!`, backquote or backslash (EXECUTED). 091's two span
     several lines, and its builder states they are paste-safe (READ).
2. **N1 (note, 087 F1's residual): a passed set still compiles unheld, under the same cache
   key.**
   - `run(artifacts=...)` takes `_module`'s old path: hash, then `Module.from_file`. That path
     can still write a `.cwasm` under a digest which a later found-set call loads without
     compiling.
   - It needs the same writer of the set's folder during a call that the review's F1 needs.
     The README calls such a set trusted input.
   - It is no regression. It is a candidate for the follow-up that F4 opens. One possible fix is
     to mark `.cwasm` files written from held bytes, or to always hold.
3. **N2 (note, 084 through 078): a warning queued by an abandoned teardown can be lost at exit.**
   - If the process exits while an abandoned guest thread is still running its steps, `_release`
     may flush before the steps queue anything.
   - The folder keeps its lock file, and the next process's sweep retries it (Decision 5). Only
     the warning is lost.
   - This is within Decision 7's "next flush", which may never come. One sentence in 084's notes
     would make it explicit.
4. **N3 (note): the fast-tier counts differ only by environment.**
   - 084's fast tier on `8e69a2b` reads 529 pass and 25 blocked. 091's on `daceacf` reads 532
     pass and 22 blocked. Both have 669 rows and the same three fails, all 087's set-dependent
     rows.
   - The three rows move from blocked to pass. The private sets of the two worktrees differ, and
     091 claims no gain.
   - On the lane's rebuilt set, all three fails should pass. One of them,
     `test_manifest_recipes_match_the_tree`, is a pass the base already had.
5. **N4 (note, my own procedure).**
   - `build/lane.lock` (02:13:25Z) already existed when I ran the 14 unit rows listed above, so
     the rows ran under the lock.
   - One of my arguments was a whole file of 10 rows, not a node id.
   - The rows ran in a `git archive` export, not a git worktree, because `git worktree add` is
     denied in auto mode. The export has its own `build/` and uses no artifact set.
   - Nothing in the main tree was read or written by that run. It ran no guest and measured no
     fuel.

## Constitution checks

- **§4.1 (patches).** 087's `0002-timeout-ticks.patch` carries:
  - its `MODIFIED` line;
  - its `context/upstream/24-regex-timeout-ticks/` facts sheet;
  - its CHANGELOG line.

  Whether it is hashed in MANIFEST is covered by the 68-line check above.
- **§4.14 and §5.7 (one integration branch).** Four entries, one landing. The judge's
  accept-time guards apply, and the lane accepts in the main tree on a detached HEAD.
- **§5.6 (an unreviewed fix).** 087's and 091's answer commits are now reviewed here (criteria 3
  and 4). Neither reopens a finding.
- **§7.** Nothing tripped. No check, golden, gap, allowance or `context/progress/` file is edited
  to turn anything green. 091's single check edit records a fact and changes no assertion.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. L1: for the lane, at the accept command.
2. N1 to N4: no action needed to land.

## Verdict

**Lands as merged at `daceacf`** (judged as `47b3695`, which adds only the copied reviews). The
accept log's GREW lines must be exactly 087's two byte rows (criterion 7).

One line: the four entries merged with only the named hunks; 084's removal sits correctly inside
078's teardown, with warnings still given outside every lock; 087's and 091's fixes close their
findings; the local SHA256SUMS will match CI's.
