# 052 — The judge on several cores

- **Status:** built 2026-10-18; awaiting its build review. Confirmed for build the same day (C1, C2
  written in). Revised against its
  pre-build review and confirmed the same day (the review's Confirmation: "ready to build", with
  conditions C1 and C2, written into Decisions 5 and 9 and criterion 5). Drafted 2026-10-18; reviewed the same day
  (`build/reviews-evidence/052-review/052-the-judge-on-several-cores-spec-2026-10-18.md` in the
  main tree, which the lane copies to `context/reviews/`: "ready once F1 to F7 are written in; F8
  to F14 fixed or answered in writing before the build"). Every finding is written in below and
  answered in the Disposition at the end. Rebased onto main `c7b7f26` (specs 035, 049 and 056
  landed); documents only.
- **Date:** 2026-10-18
- **Owner:** Clay Gendron
- **Kind:** a judge change. It edits the harness plugin (`tests/harness/plugin.py`) and
  `tests/harness/zips.py`, adds a harness module and self-tests, fixes five goal checks, and adds
  one pinned development dependency (`pytest-xdist`, with `execnet`) to `pyproject.toml` and
  `uv.lock`. It touches no `scripts/`, `recipes/`, `downloads/SHA256SUMS` or release workflow,
  so it is not build-class (§5.7). It changes neither the guest's imports or exports nor the
  artifact set nor the build recipe; its pre-build review was voluntary. Every judging file it
  edits changes the judge hash: **the lane accepts it with `--accept-judge`.**
- **Depends on:** 002 (the progress harness), 029 (the lane's guards), 050 (the upstream suites
  and their session), 035 (the zips folder this spec makes safe), 032 (the counted-deadline
  pattern of its fourth revision); all landed.
- **Research it stands on:** `../research/2026-10-18-the-judge-on-several-cores.md` (called "the
  memo" below; findings 1 to 10 and its addendum on the rebased commit).

## Intent

Builders and reviewers run `uv run pytest -n 6`: the judge on six cores, with exactly the answer
`uv run pytest` gives. The same status, need, facts and (for gaps and blocked checks)
reason for every check; the same `bytes` and `passes`; fuel within the ratchet's tolerance
(serial runs already differ by up to 1.3 parts in a million); the same unit tally, deselected
list and collected files. The full run drops from about ten minutes to about three on the
project's machine (the memo, finding 5). The judge stays serial unless asked, and **the lane's
accepting run stays serial** until parallel runs have a track record (Decision 11).

## Decisions

1. **pytest-xdist, pinned exactly.** `pytest-xdist==3.8.0` joins the `dev` group in
   `pyproject.toml`; `uv lock` adds it and `execnet` 2.1.2, its one dependency, to `uv.lock` with
   their URLs and SHA-256s. *Reason (§4.13):* xdist is pytest's own project for running tests in
   several processes; it is the only maintained way to do it, and it brings one small dependency.
   3.8.0 is its newest release (2025-07-01). Both are MIT (READ: their metadata's
   `License-Expression`). They are development tools, never in the wheel or the artifact set. The
   pin is exact because the plugin subclasses one of xdist's schedulers (Decision 6) and allows
   its plugins by version (Decision 5); a newer xdist is a change of its own, reviewed.
2. **Serial stays the default.** No `-n` goes into `addopts`. *Reason:* every instruction, CI
   job and self-test that runs `uv run pytest` keeps its meaning; parallelism is asked for on the
   command line, where the run record shows it (Decision 8). `-n` set through `PYTEST_ADDOPTS` is
   already refused for acceptance by spec 002, and stays refused.
3. **Workers make records; the controller keeps them.** On a worker (known by
   `hasattr(config, "workerinput")`, never by `PYTEST_XDIST_WORKER`, which a pytest started by a
   check inherits) `pytest_runtest_makereport` makes each record exactly as today, then appends
   the node's current record to `report.user_properties` as `("wasi_python.record", [node id,
   record])`, and a unit test's tally as `("wasi_python.suite", [passed, skipped])`. The
   controller's `pytest_runtest_logreport` takes them into `State`, keeping the **last** record per
   node. *Reason:* xdist carries `user_properties` to the controller with each report (the memo,
   finding 3); the worker already applies "a failure in any phase stands", so the last record sent
   is the final one. The record's fields are plain JSON values, which execnet carries.
4. **Collection reaches the controller through `workeroutput`; workers write nothing and guard
   nothing.** In its `pytest_sessionfinish`, a worker puts `areas`, `deselected`,
   `collected_files` and `narrowed_files` into `config.workeroutput["wasi_python.collection"]`
   and returns before anything else: no `latest.json`, no ratchet, no `accepted.json`, no
   `history.jsonl`. In its `pytest_configure`, a worker skips spec 029's accept refusal and the
   HEAD stash: **the guards run once, in the controller**, whose `pytest_configure` runs before
   any worker starts and whose `pytest_sessionfinish` (the late re-check, `head_moved`) runs
   after every worker is down. The controller merges every worker's output in
   `pytest_testnodedown`, then its own `pytest_sessionfinish` runs as today. *Reason:* collection
   happens only on workers, and today each worker runs the whole `sessionfinish`, `--accept`
   included; only the foreign-plugin check stops them, by accident (the memo, findings 1 and 2).
   Silencing workers by rule makes "accepted once, by the controller, under spec 029's guards"
   true by construction. A worker that sees the tree change no longer exits on its own; the
   controller refuses once (review F11). A worker that dies is Decision 14.
5. **xdist's plugins are allowed, narrowly.** `foreign_steering` accepts:
   - a plugin module whose file lies inside the **package folder of the installed `pytest-xdist`
     distribution**, `importlib.metadata.distribution("pytest-xdist").locate_file("xdist")` (C1:
     never `locate_file("")`, which is all of `site-packages`), and an object plugin whose type's
     module file lies there (by file, never by a name prefix);
   - **only when** that distribution's version, `xdist.__version__` and the version `uv.lock`
     pins for `pytest-xdist` are all equal, and the installed `execnet`'s version equals the one
     `uv.lock` pins (execnet carries every record, and as a non-plugin the foreign check would
     never see it);
   - an object plugin whose type is defined in a judged file: the harness's own `Controller`
     (Decision 4), whose type's module file is `tests/harness/plugin.py`.

   Every other plugin is foreign, as today; a version mismatch makes each xdist plugin a finding.
   *Reason:* xdist is now part of the judge, and `uv.lock` is a judging file, so its pins are in
   the judge hash. Taking the folder from the distribution, not from `import xdist`, keeps an
   `xdist` package that shadows it on `sys.path` (`pythonpath` includes `tests/`) from passing
   (review F6, F9).
6. **The judge's scheduler keeps each upstream group whole and node ids unchanged.** The plugin
   implements xdist's `pytest_xdist_make_scheduler` (as an optional hook; xdist's own is
   `trylast` and the hook is `firstresult`, so the judge's wins) and returns a subclass of
   `xdist.scheduler.LoadScopeScheduling` whose `_split_scope(node id)` is a harness function,
   `scope_of(node id, scopes)`. `scopes` is an **exact map** built from `upstream.load_all()`:
   `tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[<group>]` and
   `…::test_upstream_class[<class id>]` for each class of that group (the id the test module
   gives it, `f"{k.group}-{k.id}"`) map to `upstream <group>`. Any other node id is its own scope
   (traps included: each runs alone in its session). No prefix is guessed. xdist's default
   reordering by scope size stays on. *Reason:* a class check reads its group's run from a
   session-scoped object, one per process; on another worker it runs the whole group again (150 s
   for one pandas class, the memo, finding 4), and could see a different run of it.
   `--dist loadgroup` appends `@group` to node ids, which the judge keys everything by.
   `--dist loadfile` would put all 266 s of upstream work on one worker. The reordering deals the
   upstream groups first, so the longest starts at once with six workers or more.
7. **One way to run in parallel: every xdist option decided, refused before anything runs.** A
   `tryfirst` `pytest_cmdline_main` in the harness plugin reads the raw options, before xdist's
   own hooks change them, and returns exit code 1 with one line naming the option for each refusal
   below. It skips a worker (which carries the options it was given). The table (review F10):

   | option | fate | why |
   |---|---|---|
   | `-n <int>`, `-n auto` | allowed | the parallel run |
   | `-n logical` | refused | needs `psutil`, which is not pinned |
   | `--maxprocesses`, `--max-worker-restart` | allowed | they only cap workers or restarts |
   | `--dist load` (what `-n` sets) | allowed | the judge's scheduler replaces it |
   | `--dist` anything else | refused | `each` runs every check once per worker; the others would be silently replaced |
   | `-d` / `--distload` | refused | `--dist load` with no workers: nothing to distribute |
   | `--loadscope-reorder` | allowed | the default |
   | `--no-loadscope-reorder` | refused | the size order is what starts the longest group first |
   | `--maxschedchunk` | refused | the LoadScope scheduler ignores it; it would mislead |
   | `--tx`, `--px`, `--rsyncdir`, `--rsyncignore` | refused | other interpreters and remote hosts are not the judged environment |
   | `-f` / `--looponfail` | refused | its child runs a whole session that is neither the judge nor a controller, and would write and accept again on every file change (review F2) |
   | `--testrunuid` | allowed | an identifier only |

   The `Controller` is registered in `pytest_configure` only when xdist distributes:
   `config.option.dist != "no"` **and** `config.option.tx` is not empty. *Reason:* under `-f` the
   controller's `pytest_configure` never runs, and by then xdist has replaced a given `--tx` with
   `["popen"] * n` (review F2, EXECUTED there); a `tryfirst` `pytest_cmdline_main` is the one place
   that sees the raw options in every mode. §5.2: no option is left undecided. A later xdist pin
   re-checks this table against its options.
8. **The run record says how it was judged.** `latest.json`'s `meta` gains `workers`, the number
   of workers xdist starts (`len(config.option.tx)` at the controller's `pytest_configure`, after
   `--maxprocesses`; `0` for a serial run), and `scheduler`, the class name of the scheduler xdist
   used (`null` for a serial run). Both are reported, never compared, and the history line's
   format is unchanged. *Reason:* the verdict does not depend on them (that is this spec's claim),
   but a reader of a record should see how it was made, and criterion 7 reads `scheduler` (review
   F7, F14).
9. **Five checks stop depending on order or speed.** Each is a judge change with this reason,
   named in the landing notes; no assertion changes:
   - `test_v1_2_hostile_guest.py::test_a_call_without_a_root_shares_nothing` and
     `test_a_trapped_call_without_a_root_is_removed` (both parameters): one warm-up call
     (`run(["-c", "pass"])`) **before** `tempfile.tempdir` is redirected, so the runner's
     once-per-process stdlib folder exists outside the scratch folder, as it does when an earlier
     check has run. The second check already has a warm-up; it moves above the redirect.
     *Reason:* both fail when run alone, serially (the memo, finding 7, and its addendum); the
     runner's folder is one per process by design (`runner.py`, "one read-only folder per zip per
     process"), and every accepted serial run judged them warm.
   - `test_v1_4_embedding.py::test_a_deadline_during_a_door_call_under_cancel_is_named`, **by
     count**, spec 032's fourth-revision pattern. The child's `deadline_s` becomes `60.0`, long
     enough that no load ends the run before the door. In `blocks`, the host prints
     `"in the door"`, moves the call's deadline to now by count
     (`runner._stack()[-1].stop_at = runner._epoch_ticker.count()`, the seam of
     `test_writes_land_at_every_ending`), then holds the door for `CANCEL_TICKS + 2` ticks of the
     ticker's count, as it holds it now. The assertions (`"in the door"` first, then
     `deadline None None b''`) are unchanged. *Reason:* a 0.05 s deadline counted from
     instantiation is a bet on how fast the host starts the guest; it lost in two of eleven
     parallel runs and once alone, serially, on a loaded machine (the memo, finding 8 and the
     addendum); §4.9 says a check must not depend on speed (review F3).
   - `test_v1_4_embedding.py::test_a_tool_blocking_past_the_deadline_is_answered`, the same way:
     the child's `deadline_s` becomes `60.0`; the tool `block`, once entered, makes the call's
     deadline overdue by count, as `MOUNT_CANCEL`'s `past_deadline` does in the same file (the
     ticker's count that the runner and the tool bound read set to the call's `stop_at`, and every
     engine's epoch advanced past the deadline), then waits on `release` as now. The assertion
     (`block timeout True`) is unchanged. *Builder's note (C2):* inside the tool,
     `runner._stack()` is empty (the call stack is a `threading.local`, and a tool runs on its own
     thread), so the tool does not read the call's `stop_at` there; it sets the ticker's count
     past any deadline (`runner._epoch_ticker.count = classmethod(lambda cls: 2**62)`), which the
     bound reads at call time. *Reason:* with `deadline_s=3` the guest must reach
     `tools.block()` within three seconds of wall time, or `outcomes[-1]` raises; the same shape as
     the door check (review F3).
10. **The worker count builders and reviewers use is `-n 6` on the project's machine, fewer when
    others are running.** AGENTS.md and `context/progress/README.md` name `uv run pytest -n 6`
    for darwin-arm64 on the 10-core M1 Pro, and `-n auto` on another machine. When another
    agent's full judge is running on the same machine, use `-n 3`. *Reason:* the floor of every
    parallel run is the longest upstream group, pandas-groupby; with xdist's reordering by scope
    size it is the sixth scope dealt, so six workers is the fewest that start it at once. Beyond
    six, CPU and memory grow with N and the group itself runs slower (the memo, finding 5: N = 4
    to 10 took 170 s to 244 s under a shared load, against 580 s to 627 s serially). A `-n 6` run
    peaked at 8.4 to 9.8 GiB; §5.7 allows four specifications in flight, and four such runs at once
    would exceed the machine's 32 GiB (review F13). The numbers are benchmark advice, not rules;
    the verdict does not depend on N, and a later memo may change them without a specification.
11. **The lane's accepting run stays serial, until parallel runs have a record (the lane's
    ruling, review F4).**
    - Lane step 3 stays `uv run pytest --accept "<reason>"` (with `--accept-judge` when the judge
      changed): the verdict of record is serial.
    - Builders' and reviewers' end-of-stage full runs are `uv run pytest -n 6`.
    - **Each landing records the comparison.** When the rebase changed no judged file and no
      code, the landing notes record `uv run python tests/harness/sameness.py <the reviewer's -n 6
      latest.json> <the lane's serial latest.json>` and its output. A difference stops the landing:
      it is a defect of a check (order, speed, a shared path) or of this harness, written in the
      landing notes and fixed by its own judge change before the landing goes on. Nobody re-runs
      to make it go away. When the rebase did change a judged file or code, the notes say so and
      the comparison is not counted either way.
    - **After ten consecutive counted landings with no difference**, a research memo that counts
      them may move lane step 3 to `uv run pytest -n 6 --accept "<reason>"` without a new
      specification. That memo also names a periodic serial confirmation (one serial run at least
      every tenth landing, compared the same way) and what happens when it differs: a stopped
      landing and a fix. The count restarts at any difference.

    *Reason:* the memo's census finds checks that need an earlier check, but cannot find one
    spoiled by an earlier check, and eleven orders are not all orders. A parallel lane could pass
    cold on a fresh worker a check that the serial judge, CI and the release workflow fail. The
    serial lane keeps the verdict of record where every accepted state so far was made, and the
    recorded comparisons build the track record that would justify changing it.
12. **The comparison is a harness function.** `tests/harness/sameness.py` holds
    `differences(a, b) -> list[str]`: every difference between two run records in `status`,
    `need`, `area`, `closer`, `facts`, the set of metric names, `bytes`, `passes`, `deselected`,
    `collected_files` and `suite`; in `reason` for checks whose status in both records is `pass`,
    `gap` or `blocked` (there the reason is deterministic: a note such as spec 051's coverage line,
    the gap's first line, the need); and in `fuel` wherever
    `abs(a − b) > FUEL_TOLERANCE × max(a, b)`. A `fail`'s reason is not compared: it may name a
    temporary path, and the status comparison already decides. A command,
    `uv run python tests/harness/sameness.py A.json B.json`, prints the differences and exits 1
    when there are any. *Reason:* the self-tests, the builder's evidence and the lane's per-landing
    record use one definition of "the same answer", and fuel's is the ratchet's own tolerance (the
    memo, finding 6: serial runs differ by up to 1.25e-6, parallel runs by no more) (review F12).

    **Changed in the build** (2026-10-18, the builder; for the build review): `reason` is compared
    for `gap` and `blocked` only, not for `pass`. The first serial and `-n 3` full judges differed
    in exactly one field, the note of
    `test_v1_3_the_zips_directory.py::test_a_zone_load_does_not_grow_with_the_zip[plain]`, which
    prints fuel counts (`Paris 8,688,508` serially, `8,688,525` under `-n 3`: 17 instructions, the
    serial residual). The plugin already says a note "is never compared, so it is no metric".
13. **The zips folder is safe across processes.** `zips.judge_zips` builds in its own `mkdtemp`
    folder, as now, then publishes it with **one `os.rename(work, home)`** and never removes a
    `home`:
    - `home` is named `zips-<sha>-v2` (the old name may hold a folder an earlier version left
      half-removed; nothing reads it again);
    - a `home` that exists is complete, because the only way one comes to exist is that one atomic
      rename of a complete build;
    - a process whose rename fails because `home` already exists (`FileExistsError`, or `OSError`
      with `ENOTEMPTY` or `EEXIST`, as Windows and POSIX report it) removes only its own work folder
      and uses the `home` that won; any other error is raised.

    *Reason:* today a second process's `shutil.rmtree(home)` can delete the folder a first process
    is reading, or its `os.replace` can fail on a non-empty folder; four cold processes failed in 2
    of 3 trials (review F1, EXECUTED there). A rename publishes atomically on every system the
    judge runs on, without a lock file; `fcntl` does not exist on Windows, where the release dry
    run judges.
14. **A worker that dies leaves a `fail`, not an `unrun`.** The controller keeps each failed
    report that carries no record property (xdist's report for the check that was running when a
    worker crashed). In its `pytest_sessionfinish`, after the merge, each such node that is a goal
    check and has no record becomes `fail`, its reason `worker crashed: ` and the first line of
    xdist's report. xdist deals the dead worker's other scopes again, so only that one check is
    lost. *Reason:* the run is red either way, but the record should name what happened (review
    F8).

## Design

**`tests/harness/plugin.py`.**
- `is_worker(config)`; the `tryfirst` `pytest_cmdline_main` with the refusals of Decision 7.
- `pytest_configure`: on a worker, skip the accept refusal and the HEAD stash (Decision 4);
  register a `Controller` only when xdist distributes (Decision 7); keep `meta.workers`'s source
  (Decision 8).
- `Controller`: `pytest_runtest_logreport` (records, tallies, failed reports without a record)
  and `pytest_testnodedown` (the merge).
- `pytest_runtest_makereport` keeps its body; on a worker it then appends the two properties.
- `pytest_sessionfinish`: on a worker, fill `workeroutput` and return; on the controller and in a
  serial run, as today plus `meta["workers"]`, `meta["scheduler"]` and Decision 14's crashed
  checks.
- `scope_of`, the exact scope map and `pytest_xdist_make_scheduler` (Decision 6), marked
  `optionalhook=True`, so a pytest without xdist loads the plugin as before.
- `foreign_steering` with Decision 5's allowance; the pins are read from `uv.lock`'s
  `[[package]]` entries named `pytest-xdist` and `execnet`.

**`tests/harness/zips.py`** (Decision 13). **`tests/harness/sameness.py`** (Decision 12). Both are
judging files under `tests/`.

**The five checks** (Decision 9).

**`pyproject.toml`, `uv.lock`** (Decision 1). The pytest `markers` list is unchanged.

**Documents, in the build:**
- `AGENTS.md`: rule 3a: the fast-tier loop may take `-n 6` (memo, finding 3: 304 s to 119 s at
  `-n 4`), and the builder's and the reviewer's end-of-stage full runs are `uv run pytest -n 6`
  (`-n 3` when another agent's judge is running), each keeping its `latest.json` for the lane.
  Rule 6a: the lane judges the exact commit **serially**, accepts, and records `sameness.py`
  between the reviewer's parallel record and its serial one (Decision 11).
- `context/progress/README.md`: a section "Several cores (spec 052)": the command and the advice
  of Decision 10; that the verdict does not depend on it; what `meta.workers` and
  `meta.scheduler` are; the option table of Decision 7; `sameness.py`. In "The landing lane":
  step 3 unchanged (serial); a new step after step 5 recording the comparison; and the rule of ten
  counted landings, with the memo that may end it.
- `README.md` only if it tells contributors how to run the judge (the builder checks).

## Scope

**In:** Decisions 1 to 14; the self-tests below; the documents above.

**Out:**
- A parallel lane. Decision 11 names the record that may move it there, by memo.
- A module cache in the judge's driver and heaviest-first ordering (the memo, finding 10: less
  CPU, no clear gain in wall-clock). A later change may take them with their own measurement.
- Splitting `pandas-groupby` or any upstream group to lower the floor (it would change spec 050's
  groups and their ratcheted metrics).
- Parallel runs in the release workflow or any CI.
- A file lock around the oracle's provisioning: one check needs the oracle today (the memo,
  finding 9). A spec that adds a second one adds the lock or a shared scope.

## Acceptance criteria

Each is counted; none times anything.

1. **A parallel run judges as a serial run (the central criterion).** A self-test in
   `tests/unit/test_plugin.py` (pytester, subprocess runs, the plugin under test) writes a small
   suite that produces every kind of record: passes with `fuel`, `bytes` and `passes` metrics, a
   `note` and `facts`; a gap; a check that fails differently from its gap; an `xfail` with no gap;
   an XPASS under a gap; a blocked check; a skip without a known need; a failure in teardown after
   a pass; a deselected check (`-m`); and passing and skipped unit tests. It runs it serially and
   with `-n 2` and `-n 3`, each with its own `--progress-latest`, in three shapes:
   - the whole suite;
   - a run **narrowed to node ids** (two node ids of one file and one of another), so
     `collected_files - narrowed_files` is judged;
   - a **`-k`** run.

   For each shape it asserts that `sameness.differences` is empty for both parallel records against
   the serial one, **and** that `checks`, `deselected`, `collected_files` and `suite` are equal as
   JSON (fuel included: the suite's metrics are fixed numbers), and that the scoreboard lines
   printed are the same, `meta` aside.

   **Stand-ins it is shown to fail against** (the builder applies each in a scratch copy of the
   plugin, runs this test or criterion 7's, and records the failing assertion in the landing
   notes):
   - (a) today's plugin;
   - (b) a controller that keeps the first record per node, not the last (the teardown failure
     after a pass catches it);
   - (c) records rebuilt on the controller from report outcomes instead of carried (facts, note
     and need are lost);
   - (d) `deselected` or `narrowed_files` not merged;
   - (e) the unit tally counted both from the property and from the report;
   - (f) the judge's scheduler not in effect (criterion 7's end-to-end assertion catches it).
2. **One acceptance, by the controller.** A self-test uses a **green variant** of the suite
   (passes with metrics, a note and facts, a gap that matches its entry, a blocked check, a
   deselected check, passing and skipped unit tests). `-n 3 --accept "<reason>"` into a scratch
   `--progress-dir`: `history.jsonl` has exactly 1 line, `accepted.json` exists once, and both equal
   (apart from `at`) what a serial `--accept` of the same variant writes into another scratch
   folder. Then the **failing variant** (criterion 1's suite) with `-n 3 --accept`: refused, and the
   line count stays 1.
3. **Workers write nothing and guard nothing.** A unit test calls the plugin's
   `pytest_sessionfinish` with a stand-in session whose config has `workerinput`, `--accept` set
   and scratch `--progress-dir` and `--progress-latest` paths: it fills
   `workeroutput["wasi_python.collection"]` with exactly the four keys, and the scratch folder holds
   0 files afterwards. Another calls `pytest_configure` with such a config: `HEAD_AT_START` is not
   stashed. In criterion 1's `-n 3` record every check of the suite is present and none is `unrun`.
4. **The guards hold under `-n`.** The existing spec 029 self-tests (`--accept` refused in a
   linked worktree, on a dirty tree, and when HEAD moves) gain a `-n 2` variant each; each is
   refused once, by the controller, and nothing is written.
5. **The allowance is narrow.** Self-tests of `foreign_steering`: xdist's plugins and the
   `Controller` at the locked versions give 0 findings; with the distribution's version,
   `xdist.__version__` or execnet's version reported as different from the lock (monkeypatched),
   each xdist plugin is a finding; a module named `xdist…` outside the distribution's folder is a
   finding; any other plugin is still a finding, including a module from `site-packages` outside
   `xdist/` (C1: `iniconfig` loaded with `-p iniconfig`).
6. **The refusals.** Self-tests, one per refused row of Decision 7's table (`-n logical`,
   `--dist each`, `--dist loadfile`, `-d`, `--no-loadscope-reorder`, `--maxschedchunk 2`,
   `--tx popen` with `-n 2`, `--px …`, `--rsyncdir …`, `--rsyncignore …`, and `-f` run under a
   120 s fail-safe): each exits 1 with one line naming the option, before collection, and the
   scratch progress folder and `--progress-latest` path hold 0 files. One self-test per allowed row
   (`-n 2 --maxprocesses 1`, `-n 2 --max-worker-restart 0`, `-n 2 --dist load`,
   `-n 2 --loadscope-reorder`, `-n 2 --testrunuid x`) runs, and its record equals the serial one by
   `sameness.differences`.
7. **The scopes, exactly and in effect.** A unit test of the scope map over the collected node
   ids of `tests/checks/test_v1_3_upstream_suites.py` with the real `upstream.load_all()`: each
   group's check and every one of its classes' checks in its group's scope, the scope count equal to
   the number of groups, every other node id its own scope, and the map equal to one built by hand
   from the TOML files' groups and class ids (on main today: 11 groups, 31 grouped node ids). End to
   end: a pytester suite placed at the upstream file's path, whose two parametrized checks carry
   one real group's id and one of its class ids, beside six checks that share no scope, run with
   `-n 4`: the two record the same `os.getpid()` (through `facts`), and the record's
   `meta.scheduler` is the judge's scheduler class.
8. **Every goal check outside the upstream file passes alone (a count).** The builder runs each
   such node id alone in a fresh process (`uv run pytest "<node id>"`, each with its own
   `--progress-latest`) on the built commit, against the frozen set: every one is `pass`, or
   `blocked` by a need the full run also lacks. On the rebased commit before the build, 311 node ids
   gave 305 pass, 2 blocked (`wheel`, `three systems`) and 4 fail: the first three checks of
   Decision 9's list and the door deadline check (the memo's addendum). After the build: 0 fail.
   The landing notes record the counts.
9. **The surveys again.** The builder re-runs the memo's shared-path survey (finding 9's `grep`
   and reading) on the built commit and records each fixed path under `build/` with its owner and
   why two processes cannot race on it; any new one without that answer stops the build.
10. **The zips folder from many processes.** A unit self-test in `tests/unit/test_zip_directory.py`
    starts 6 processes that call `judge_zips` at once on one small zip with an empty
    `HARNESS_TMP` (monkeypatched to a scratch folder), 3 times: every process returns, both files
    open as zip files with the expected member counts in every process, exactly 1 `zips-*-v2`
    folder exists, and 0 work folders are left. Shown failing against today's `judge_zips` in at
    least one of the 3 trials (the builder records it).
11. **The full judge, serial against parallel (the builder's evidence, in the landing notes, on
    the frozen set its class allows).** One `uv run pytest` and three `uv run pytest -n 6` on the
    built commit: `uv run python tests/harness/sameness.py serial.json parallel-k.json` prints
    nothing and exits 0 for k = 1, 2, 3; each scoreboard shows the same counts (main's accepted
    state at `c7b7f26` holds 329 passes and 12 gaps; the build records what its set shows).
    Wall-clock and CPU are reported as benchmark facts beside the numbers, never asserted.
12. **Green.** `ruff check`, `ruff format --check` and the full judge pass; the run is red only by
    `judge changed`, which the lane accepts with `--accept-judge`.

## How builders, reviewers and the lane use it

- **Builders and reviewers:** loop on `uv run pytest -m "not slow" -n 6`; run a slow check alone
  by node id; end each stage with `uv run pytest -n 6` (`-n 3` when another agent's judge is
  running), and keep that run's `latest.json` for the lane.
- **The lane:** step 3 unchanged, serial: `uv run pytest --accept "<reason>"`. Then it records
  `sameness.py` between the reviewer's parallel record and its own serial one (Decision 11).
- **A machine with fewer cores:** `-n auto`. Serial `uv run pytest` remains correct everywhere.

## Disposition of the pre-build review

Every finding of `052-the-judge-on-several-cores-spec-2026-10-18.md` (main tree,
`build/reviews-evidence/052-review/`):

| finding | disposition |
|---|---|
| F1 (High) the zips folder races; surveys stale | **Fixed in the spec.** Decision 13: one atomic rename, a new folder name, no `home` ever removed (a lock was rejected: `fcntl` is not on Windows, where the release dry run judges). Criterion 10: 6 processes × 3 trials, counted, shown failing against today's code. Both surveys re-run on the rebased commit (the memo's addendum: one new fixed path, the zips folder; 311 checks alone: 305 pass, 2 blocked, 4 fail). Criterion 8 widened to every goal check outside the upstream file, as a count; criterion 9 repeats the shared-path survey in the build. |
| F2 (High) `--looponfail` and `--tx` refusals in the wrong hook | **Fixed.** Decision 7: every refusal in a `tryfirst` `pytest_cmdline_main`, which sees the raw options and skips workers; criterion 6 runs `-f` under a fail-safe and counts 0 files written. |
| F3 (High) the door deadline must count | **Fixed.** Decision 9: `deadline_s=60.0`, the deadline moved to now by count in the door (spec 032's fourth-revision pattern, the seam of `test_writes_land_at_every_ending`), the door held `CANCEL_TICKS + 2` ticks. `test_a_tool_blocking_past_the_deadline_is_answered` fixed the same way (60 s, the deadline made overdue by count from inside the tool, `MOUNT_CANCEL`'s seam). The census on the rebased commit saw the door check fail alone, serially, under load. |
| F4 (High, the lane's ruling) lane stays serial | **Written in.** Decision 11: lane step 3 serial; builders and reviewers `-n 6`; every landing records `sameness.py` between the reviewer's parallel record and the lane's serial one; after ten consecutive counted clean landings a memo may move the lane to `-n 6`, naming a serial confirmation at least every tenth landing and what a difference does. AGENTS.md rule 6a and the progress README's lane steps carry it (Design, documents). |
| F5 (Medium) criterion 2 cannot pass | **Fixed.** Criterion 2 accepts a green variant, then shows the failing suite refused with the line count still 1. |
| F6 (Medium) `Controller` would be foreign | **Fixed.** Decision 5 allows an object plugin whose type is defined in a judged file; criterion 5 counts it. |
| F7 (Medium) stand-ins and shapes | **Fixed.** Criterion 1 names stand-ins (a) to (f) and adds a node-id-narrowed and a `-k` shape; criterion 7 asserts end to end that xdist used the judge's scheduler (one pid for one scope; `meta.scheduler`, Decision 8) and that the scope map is exact (Decision 6: no prefix guess). |
| F8 (Low) a crashed worker shows `unrun` | **Fixed.** Decision 14: such a check becomes `fail` with xdist's message; only the running check is lost, the rest are dealt again. |
| F9 (Low) tighten the allowance | **Fixed.** Decision 5: the folder from the `pytest-xdist` distribution; its version, `xdist.__version__` and the lock all equal; object plugins checked by their module's file; execnet's version checked against the lock. |
| F10 (Low) decide every option; register only when distributing | **Fixed.** Decision 7's table names every xdist 3.8.0 option and its fate; `Controller` registered only when `dist != "no"` and `tx` is not empty. |
| F11 (Low) run spec 029's guards once | **Fixed.** Decision 4: workers skip the accept refusal and the HEAD stash; criterion 3 counts it. |
| F12 (Low) `reason` and the fuel test | **Fixed.** Decision 12 compares `reason` for `pass`, `gap` and `blocked` (not for `fail`, which may name a temporary path) and defines fuel's test as `abs(a − b) > FUEL_TOLERANCE × max(a, b)`. |
| F13 (Low) memory when agents run side by side | **Fixed.** Decision 10 advises `-n 3` when another agent's judge is running, with the memory reason. |
| F14 (Note) `meta.workers`; stale counts | **Fixed.** Decision 8: workers started (`len(config.option.tx)` after `--maxprocesses`). Criterion 11's counts refreshed to main's accepted state (329 passes, 12 gaps). |

## Landing notes

**Built 2026-10-18** by the builder (Claude Opus 5.5) in the worktree `wasi_python-052`, branch
`spec/052-the-judge-on-several-cores`, rebased onto main `94167a8` (spec 054 landed; the one
conflict, `CHANGELOG.md`'s 0.1.0a5 section, kept both entries). Not yet reviewed: the build review
goes under `context/reviews/` and is cited here before the lane lands it. Every number below is
EXECUTED on darwin-arm64 against the frozen set `build/sets/s-c4190ca065ada03a` (main's accepted
set, `python.wasm` `42344e2c…`), with `uv run` only; logs and records are under the worktree's
`build/build-052/`. Nothing in the main tree was written.

**Setup.** As the memo's: read-only links to the main tree's `downloads/*`, source trees,
`build/brett-3.14.7` and prior-art clones; the oracle's cache and interpreter copied; the kit
fetched with `uv run python tests/upstream/fetch.py`.

**Commits** (oldest first): `3fea3d0` the memo; `310ded6` the draft; `c174026` the revision and
the memo's addendum; `3b80e90` C1 and C2; `8ebd7ad` build 1/6 (the pin, the zips folder);
`69e0dd0` build 2/6 (the plugin, `sameness.py`, `tests/unit/test_several_cores.py`); `3544ed7`
build 3/6 (the five checks, criterion 4); `9b197fd` build 4/6 (AGENTS.md, the progress README,
CHANGELOG, README); `0b4156b` build 5/6 (no pass note compared); and this commit (6/6, these
notes).

**The judge, serial and on three cores, on `0b4156b`** (the judged files of the built commit,
judge hash `4b6455f0ab52` in both records; `-n 3` rather than `-n 6`, since other agents' judges
were running, Decision 10):

```
uv run pytest            wasi_python v1: 340/354 pass · 12 gap · 2 blocked · 0 fail   (unit suite 1097/1099, 2 skipped)
                         ratchet vs 5f56591135: lost 0 · absent 0 · unrun 0 · gained 0 · grew 0 · judge changed: pyproject.toml, tests/checks/test_v1_2_hostile_guest.py, tests/checks/test_v1_4_embedding.py and 7 more
                         1437 passed, 4 skipped, 12 xfailed in 620.31s; exit 0; wall 658 s, CPU 755 s, peak RSS 2.4 GiB
uv run pytest -n 3       wasi_python v1: 340/354 pass · 12 gap · 2 blocked · 0 fail   (unit suite 1097/1099, 2 skipped)
                         ratchet vs 5f56591135: lost 0 · absent 0 · unrun 0 · gained 0 · grew 0 · judge changed: (the same)
                         1437 passed, 4 skipped, 12 xfailed in 231.26s; exit 0; wall 232 s, CPU 855 s, peak RSS 6.1 GiB
sameness.py serial.json n3.json        (nothing printed) exit 0
```

Between the two records: 354 checks, 0 status differences; 86 fuel values, 18 differing, the
largest by 5.6e-7 (under the tolerance 1e-4 by a factor of about 180); 2 pass notes differing
(fuel counts printed in notes, see "For the build review"); `meta.workers` 0 and 3,
`meta.scheduler` `null` and `JudgeScheduling`. Both records say `dirty: true`: this specification
was edited while they ran (it is not a judged file; the judge hashes are equal). The load average
was 24 to 86 around the runs (`sysctl -n vm.loadavg`). An earlier pair on `9b197fd` gave the same
lines (serial 645 s, `-n 3` 242 s) and is where the note difference was found.

**Each criterion.**

1. **Passes.** `test_a_parallel_run_judges_as_a_serial_run[whole]`, `[node ids]`, `[-k]`. Against
   today's plugin (stand-in a) 26 of the file's 29 tests failed (`build/build-052/standin-a.log`);
   criterion 1's first failure: the parallel record empty, `test_goals.py::test_blocked: only in
   the first record`. Stand-ins (b) first record kept, (c) records rebuilt from outcomes, (d)
   `deselected` not merged and (d') `narrowed_files` not merged (the node-id shape), (e) the tally
   counted twice: each fails at `assert sameness.differences(serial, record) == []` for `-n 2`;
   (f) the scheduler not in effect: criterion 7's end-to-end test fails, `assert 38323 == 38326`
   (two pids) (`build/build-052/standins.py`, `standins.txt`; the plugin restored and compared
   byte for byte after).
2. **Passes.** `test_one_acceptance_by_the_controller`: one history line serially and under
   `-n 3`, equal but for `at` and `accepted`; `accepted.json`'s checks equal; the failing variant
   refused, the count still 1.
3. **Passes.** `test_a_worker_writes_nothing_and_hands_its_collection_over` (0 files),
   `test_a_worker_skips_the_lanes_guards` (no HEAD stashed; the same config without `workerinput`
   refused in this linked worktree).
4. **Passes.** `test_accept_in_a_worktree_is_refused_before_collection[-n 2]` and
   `test_the_guards_hold_under_several_cores_in_a_main_tree` (a dirty clone refused before
   collection; HEAD moved by a worker's commit refused once, `--accept refused` printed 1 time;
   `history.jsonl` unchanged in both).
5. **Passes.** xdist's three plugins and the `Controller` at the locked versions: 0 findings; each
   of `pytest-xdist`, `xdist.__version__`, `execnet` reported as `0.0.0`: 3 findings; `iniconfig`
   (site-packages outside `xdist/`, C1), a module named `xdist_impostor` outside the package and a
   stranger: 3 findings.
6. **Passes.** The 11 refused rows each exit 1 with one line naming the option and `spec 052`, and
   write 0 files; the 5 allowed rows judge as serial (`sameness` empty; `meta.workers` 2). Against
   today's plugin `-f` ran until its 120 s fail-safe. Builder's detail: under `-p harness.plugin`
   xdist's own `tryfirst` `pytest_cmdline_main` ran before the harness's and had already turned
   `-n 2` into `--tx popen popen`, so a plain `tryfirst` hook refused every `-n` run as `--tx`;
   the options are therefore read in a hook wrapper (`specname="pytest_cmdline_main"`), which runs
   before every implementation, and refused in the `tryfirst` implementation, which runs before
   looponfail's loop and before any session.
7. **Passes.** `test_the_upstream_scopes_are_exact` (the map equals one built by hand: 11 groups,
   31 node ids), `test_the_collected_upstream_ids_fall_in_their_groups`,
   `test_xdist_deals_with_the_judges_scheduler` (one pid for the group's and the class's check;
   `meta.scheduler` `JudgeScheduling`).
8. **Holds.** Every goal check outside the upstream file alone in a fresh process, four at a time
   (`build/build-052/alone.sh`, 357 s, load average 100 after): **322** node ids, **320 pass, 2
   blocked** (`wheel`, `three systems`, as in the full run), **0 fail**. Before the build: 311, 305
   pass, 2 blocked, 4 fail.
9. **Holds** (READ, the memo's `grep` on the built commit). Fixed paths under `build/` and why no
   two processes race: `build/harness/zips-<sha>-v2` (one atomic rename, never removed;
   criterion 10); `build/cwasm-cache` (the runner's `mkstemp` and `os.replace`; directory made with
   `exist_ok`); `build/progress/latest.json` (the controller only); `build/harness/oracle-check`,
   `build/oracle/python/<archive>`, `build/oracle/venv` and `cache` (the one oracle check only, so
   one process; Scope, Out); `build/upstream/wheels` (read only during a run). Everything else is
   `mkdtemp` (`guest-*`, `unit-*`, `upstream/run-*`, the checks' scratch folders) or the runner's
   per-process and per-call folders in the temporary folder. Spec 054's additions use
   `mkdtemp` under `guest_workdir`.
10. **Passes.** `test_the_judges_zips_folder_is_safe_across_processes` (6 processes × 3 trials, 400
    members): passed on 4 runs; against the old `judge_zips` it failed in trial 0 with
    `FileNotFoundError: …/zips-0995790b9b139101/padded.zip` (`build/build-052/c10-before.log`).
11. **Holds, with one change.** One serial and one `-n 3` judge (above) instead of three `-n 6`:
    the coordinator's instruction, other agents' judges running (Decision 10). `sameness` exit 0;
    equal counts. Wall-clock 658 s and 232 s (2.8 times), CPU 755 s and 855 s.
12. **Holds.** `ruff check` and `ruff format --check` on `src tests recipes/guest` clean (the
    rules checks run them); both full judges exit 0, red by nothing; `judge changed` is for the
    lane's `--accept-judge`.

**For the build review.**

- **Decision 12 changed in the build:** `sameness` compares the reason of `gap` and `blocked`
  checks, not of passes. Two pass notes print fuel counts and differed between serial and parallel
  runs by the serial residual (17 instructions in 8.7 million); see Decision 12's added note.
- **Criterion 11** was run as one serial and one `-n 3` judge (twice, on `9b197fd` and on
  `0b4156b`), not three `-n 6` judges.
- **The raw options** are read by a hook wrapper declared with `specname`; criterion 6's detail
  above says why a `tryfirst` hook alone was not enough.
- **The tool-deadline check without its count seam** does not fail: it waits for the real 60 s
  deadline and then passes. The seam removes the dependence on start-up speed; the door check
  without its seam does fail (`assert ['in the door…the door\n'"] == […]`).
- **`meta.scheduler`** is read from xdist's `dsession.sched` at the end of the run, so it names
  the scheduler xdist actually used.
- **The unit suite** gains 29 tests in `tests/unit/test_several_cores.py` (about 15 s serially, most
  of them subprocess runs), 1 in `test_zip_directory.py` and 2 in `test_landing_lane.py`.
- **Lane, for this landing:** step 3 serial with `--accept-judge`; step 3a compares the
  reviewer's `-n 6` (or `-n 3`) record with the lane's serial one.
