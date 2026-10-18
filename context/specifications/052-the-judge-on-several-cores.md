# 052 — The judge on several cores

- **Status:** drafted 2026-10-18; awaiting its pre-build review.
- **Date:** 2026-10-18
- **Owner:** Clay Gendron
- **Kind:** a judge change. It edits the harness plugin (`tests/harness/plugin.py`), adds a
  harness module and self-tests, fixes four goal checks, and adds one pinned development
  dependency (`pytest-xdist`, with `execnet`) to `pyproject.toml` and `uv.lock`. It touches no
  `scripts/`, `recipes/`, `downloads/SHA256SUMS` or release workflow, so it is not build-class
  (§5.7), and it changes neither the guest's imports or exports nor the artifact set nor the build
  recipe, so its pre-build review is the owner's choice, asked for here. Every judging file it
  edits changes the judge hash: **the lane accepts it with `--accept-judge`.**
- **Depends on:** 002 (the progress harness), 029 (the lane's guards), 050 (the upstream suites
  and their session); all landed.
- **Research it stands on:** `../research/2026-10-18-the-judge-on-several-cores.md` (called "the
  memo" below; findings 1 to 10).

## Intent

`uv run pytest -n 6` runs the judge on six cores and gives exactly the answer `uv run pytest`
gives: the same status, need and facts for every check, the same `bytes` and `passes`, fuel within
the ratchet's tolerance (serial runs already differ by up to 1.3 parts in a million), the same
unit tally, and one acceptance written by one process
under the lane's guards. The full run drops from about ten minutes to about three on the
project's machine (the memo, finding 5). The judge stays serial unless asked: `uv run pytest`
means what it means today.

## Decisions

1. **pytest-xdist, pinned exactly.** `pytest-xdist==3.8.0` joins the `dev` group in
   `pyproject.toml`; `uv lock` adds it and `execnet` 2.1.2, its one dependency, to `uv.lock` with
   their URLs and SHA-256s. *Reason (§4.13):* xdist is pytest's own project for running tests in
   several processes; it is the only maintained way to do it, and it brings one small dependency.
   3.8.0 is its newest release (2025-07-01). Both are MIT. They are development tools, never in
   the wheel or the artifact set. The pin is exact because the plugin subclasses one of xdist's
   schedulers (Decision 6) and allows its plugins by version (Decision 5); a newer xdist is a
   change of its own, reviewed.
2. **Serial stays the default.** No `-n` goes into `addopts`. *Reason:* every instruction, CI
   job and self-test that runs `uv run pytest` keeps its meaning; parallelism is asked for on the
   command line, where the run record shows it (Decision 8). `-n` set through `PYTEST_ADDOPTS`
   is already refused for acceptance by spec 002, and stays refused.
3. **Workers make records; the controller keeps them.** On a worker (known by
   `hasattr(config, "workerinput")`, never by `PYTEST_XDIST_WORKER`, which a pytest started by a
   check inherits) `pytest_runtest_makereport` makes each record exactly as today, then appends
   the node's current record to `report.user_properties` as `("wasi_python.record", [node id,
   record])`, and a unit test's tally as `("wasi_python.suite", [passed, skipped])`. The
   controller's `pytest_runtest_logreport` takes them into `State`, keeping the last record per
   node. *Reason:* xdist carries `user_properties` to the controller with each report (the memo,
   finding 3); the worker already applies "a failure in any phase stands", so the last record sent
   is the final one. The record's fields are plain JSON values, which execnet carries.
4. **Collection reaches the controller through `workeroutput`; workers write nothing.** In its
   `pytest_sessionfinish`, a worker puts `areas`, `deselected`, `collected_files` and
   `narrowed_files` into `config.workeroutput["wasi_python.collection"]` and returns before
   anything else: no `latest.json`, no ratchet, no `accepted.json`, no `history.jsonl`. The
   controller merges every worker's output in `pytest_testnodedown`, then its own
   `pytest_sessionfinish` runs unchanged. *Reason:* collection happens only on workers, and today
   each worker runs the whole `sessionfinish`, `--accept` included; only the foreign-plugin check
   stops them, by accident (the memo, findings 1 and 2). Silencing workers by rule makes
   "accepted once, by the controller, under spec 029's guards" true by construction. A worker
   that dies sends no output: its checks are `unrun` (another worker collected them too) and the
   run is red, as an interrupted serial run is.
5. **xdist's plugins are allowed, narrowly.** `foreign_steering` accepts a plugin whose module
   file lies in the installed `xdist` package, or whose object's module is `xdist.*`, **only when
   the installed `pytest-xdist` version equals the version `uv.lock` pins**. Every other plugin
   is foreign, as today (execnet's `__channelexec__` module, seen only on a worker, is never
   checked: workers return before the check, Decision 4). *Reason:* xdist is now part of the judge, and `uv.lock` is a
   judging file, so its pin is in the judge hash; an xdist the lock does not name steers pytest
   from outside it.
6. **The judge's scheduler keeps each upstream group whole and node ids unchanged.** The plugin
   implements xdist's `pytest_xdist_make_scheduler` (as an optional hook) and returns a subclass
   of `xdist.scheduler.LoadScopeScheduling` whose `_split_scope(node id)` is a harness function,
   `scope_of(node id, groups)`: `upstream <group>` for `test_upstream_suite[<group>]` and every
   `test_upstream_class[<group>-<class>]`, the node id itself for everything else (traps
   included: each runs alone in its session). The group names come from `upstream.load_all()`; a
   class id is matched to the longest group name it starts with. xdist's default reordering by
   scope size stays on. *Reason:* a class check reads its group's run from a session-scoped
   object, one per process; on another worker it runs the whole group again (150 s for one
   pandas class, the memo, finding 4). `--dist loadgroup` would do the grouping but appends
   `@group` to node ids, and the judge keys everything by node id. `--dist loadfile` would put
   all 266 s of upstream work on one worker. The reordering deals the upstream groups first, so
   the longest starts at once with six workers or more.
7. **Only the plain `-n` is supported.** The plugin exits before collection, with one line, when
   `--dist` is anything but its default (`load`, which `-n` sets), or when `--tx`, `--px`,
   `--rsyncdir` or `--looponfail` is given. *Reason:* the scheduler of Decision 6 replaces xdist's for any
   `--dist`; `--dist each` would run every check once per worker, and remote or other
   interpreters (`--tx`) are not the judged environment. One way to run in parallel keeps one
   thing to review.
8. **The run record says how it was judged.** `latest.json`'s `meta` gains `workers`: the
   number of workers, `0` for a serial run. It is reported, never compared, and the history line's
   format is unchanged. *Reason:* the verdict does not depend on it (that is this spec's claim),
   but a reader of a record should see it.
9. **Four checks stop depending on order or speed.** Each is a judge change with this reason,
   named in the landing notes:
   - `test_v1_2_hostile_guest.py::test_a_call_without_a_root_shares_nothing` and
     `test_a_trapped_call_without_a_root_is_removed` (both parameters): one warm-up call
     (`run(["-c", "pass"])`) **before** `tempfile.tempdir` is redirected, so the runner's
     once-per-process stdlib folder exists outside the scratch folder, as it does when an earlier
     check has run. The second check already has a warm-up; it moves above the redirect. The
     assertions are unchanged. *Reason:* both fail when run alone, serially (the memo, finding 7);
     they asserted something true only after another check had run.
   - `test_v1_4_embedding.py::test_a_deadline_during_a_door_call_under_cancel_is_named`: its
     child's `deadline_s` rises from `0.05` to `2.0`. The host still holds the door until the
     deadline is overdue by count (`ceil(deadline_s / TICK_S) + 2` ticks), so the check takes
     about two seconds longer; the assertions, `"in the door"` first, are unchanged. *Reason:*
     five ticks from instantiation is a bet on how fast the host starts the guest, which failed in
     two of eleven parallel runs (finding 8); §4.9 says a check must not depend on speed. Two
     seconds is forty times the old budget.
10. **The default is `-n 6` on the project's machine.** AGENTS.md and `context/progress/README.md`
    name `uv run pytest -n 6` for darwin-arm64 on the 10-core M1 Pro, and `-n auto` elsewhere.
    *Reason:* the floor of every parallel run is the longest upstream group, pandas-groupby, and
    with xdist's reordering by scope size it is the sixth scope dealt, so six workers is the fewest
    that start it at once. Beyond six, CPU and memory grow with N and the group itself runs slower
    (the memo, finding 5: N = 4 to 10 all took 170 s to 244 s under a shared load, against 580 s to
    627 s serially). The verdict does not depend on N; the number is a benchmark choice, and a later
    memo may change it without a specification.
11. **The lane judges in parallel too.** The lane's acceptance run is `uv run pytest -n 6
    --accept "<reason>"` (with `--accept-judge` when the judge changed). A check that fails under
    `-n` and passes serially on the same commit is a defect of that check: the lane stops, writes it
    in the landing notes, and the landing waits for the check's fix, as for any red run. The lane
    never re-runs to turn a run green. *Reason:* the lane's run is the most frequent full run; the
    acceptance criteria below show its verdict equals the serial one; and rule 5 (no pass is lost
    quietly) forbids retrying until green.
12. **The comparison is a harness function.** `tests/harness/sameness.py` holds
    `differences(a, b) -> list[str]`: every difference between two run records in `status`,
    `need`, `area`, `closer`, `facts`, the set of metric names, `bytes`, `passes`, `deselected`,
    `collected_files` and `suite`, and every fuel value that differs by more than the ratchet's
    `FUEL_TOLERANCE`; and a command, `uv run python tests/harness/sameness.py A.json B.json`, that
    prints them and exits 1 when there are any. *Reason:* the self-tests and the builder's
    evidence use one definition of "the same answer", and fuel's is the one the ratchet already
    uses (the memo, finding 6: serial runs differ by up to 1.25e-6, parallel runs by no more).

## Design

**`tests/harness/plugin.py`.**
- `is_worker(config)`; a `Controller` object registered in `pytest_configure` when
  `config.option.dist != "no"` and not `--collect-only`, holding `pytest_runtest_logreport` and
  `pytest_testnodedown` (Decisions 3 and 4).
- `pytest_runtest_makereport` keeps its body; on a worker it then appends the two properties.
- `pytest_sessionfinish`: on a worker, fill `workeroutput` and return (Decision 4); on the
  controller and in a serial run, unchanged except `meta["workers"]` (Decision 8).
- `pytest_configure`: the refusals of Decision 7, before collection, by `pytest.exit` with
  return code 1.
- `scope_of` and `pytest_xdist_make_scheduler` (Decision 6), marked `optionalhook=True` so a
  pytest without xdist loads the plugin as before.
- `foreign_steering` with the allowance of Decision 5; the pinned version is read from
  `uv.lock` (its `[[package]]` named `pytest-xdist`).

**`tests/harness/sameness.py`** (Decision 12). A judging file under `tests/`.

**The four checks** (Decision 9).

**`pyproject.toml`, `uv.lock`** (Decision 1). The pytest `markers` list is unchanged.

**Documents, in the build:**
- `AGENTS.md`: rule 3a's full run becomes `uv run pytest -n 6` for the builder's and the
  reviewer's end-of-stage runs; rule 6a's lane run likewise; the fast tier may also take `-n 6`
  (memo, finding 3: 304 s to 119 s at `-n 4`).
- `context/progress/README.md`: a section "Several cores (spec 052)": the command, that the
  verdict does not depend on it, what `meta.workers` is, the refusals of Decision 7, and the
  lane's step 3 with `-n 6`.
- `README.md` only if it tells contributors how to run the judge (the builder checks).

## Scope

**In:** Decisions 1 to 12; the self-tests below; the documents above.

**Out:**
- A module cache in the judge's driver and heaviest-first ordering (the memo, finding 10:
  less CPU, no clear gain in wall-clock). A later change may take them with their own measurement.
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
   a pass; a deselected check (`-m`); and passing and skipped unit tests. It runs the suite serially, with `-n 2` and with `-n 3`, each with its
   own `--progress-latest`, and asserts that `sameness.differences` is empty for both parallel
   records against the serial one, **and** that `checks`, `deselected`, `collected_files` and
   `suite` are equal as JSON (fuel included: the suite's metrics are fixed numbers). It also
   asserts that the scoreboard lines printed are the same, `meta` aside.
2. **One acceptance, by the controller.** A self-test runs the suite above with `-n 3 --accept
   "<reason>"` into a scratch `--progress-dir`: `history.jsonl` has exactly 1 line,
   `accepted.json` exists once, and both equal (apart from `at`) what a serial `--accept` writes
   into another scratch folder. A second run with `-n 3 --accept` and a failing check writes
   nothing new (the count stays 1).
3. **Workers write nothing.** A unit test calls the plugin's `pytest_sessionfinish` with a
   stand-in session whose config has `workerinput`, `--accept` set and scratch `--progress-dir`
   and `--progress-latest` paths: it fills `workeroutput["wasi_python.collection"]` with exactly
   the four keys, and the scratch folder holds 0 files afterwards. In criterion 1's `-n 3` record
   every check of the suite is present and none is `unrun`.
4. **The guards hold under `-n`.** The existing spec 029 self-tests (`--accept` refused in a
   linked worktree, on a dirty tree, and when HEAD moves) gain a `-n 2` variant each; each is
   refused as before, and nothing is written.
5. **The allowance is narrow.** Self-tests of `foreign_steering`: xdist's plugins at the locked
   version are allowed (0 findings); with the installed version reported as different from the
   lock (monkeypatched), each xdist plugin is a finding; any other plugin is still a finding.
6. **The refusals.** Self-tests: `--dist each`, `--dist loadfile`, `--tx popen` and
   `--looponfail` each exit 1 before collection with one line naming the option; nothing is
   written.
7. **The scopes.** A unit test of `scope_of` over the collected node ids of
   `tests/checks/test_v1_3_upstream_suites.py` with the real `upstream.load_all()`: 11 upstream
   scopes, each group's check and all its classes in its scope (today 31 node ids in 11 scopes),
   every other node id its own scope; and a node id never changes (the scheduler is given ids and
   returns them).
8. **The four checks.** Each of the four node ids of Decision 9 passes run alone in a fresh
   process (`uv run pytest "<node id>"`), and in the full judge.
9. **The full judge, serial against parallel (the builder's evidence, recorded in the landing
   notes, on the frozen set its class allows).** One `uv run pytest` and three `uv run pytest -n 6`
   on the built commit: `uv run python tests/harness/sameness.py serial.json parallel-k.json`
   prints nothing and exits 0 for k = 1, 2, 3; each scoreboard shows the same counts (on the set
   the memo used: `294/308 pass · 12 gap · 2 blocked · 0 fail (unit suite 1023/1025, 2
   skipped)`, or what the set accepted at build time shows). Wall-clock and CPU are reported as
   benchmark facts beside the numbers, never asserted.
10. **Green.** `ruff check`, `ruff format --check` and the full judge pass; the run is red only by
    `judge changed`, which the lane accepts with `--accept-judge`.

## How builders, reviewers and the lane use it

- **Builders and reviewers:** loop on `uv run pytest -m "not slow" -n 6`; run a slow check
  alone by node id; end each stage with `uv run pytest -n 6` (AGENTS.md rule 3a as amended).
- **The lane:** `uv run pytest -n 6 --accept "<reason>"` (Decision 11). The ratchet line, the
  `unrun` and `upstream unrun` counts and every guard read as before.
- **A machine with fewer cores:** `-n auto`. Serial `uv run pytest` remains correct everywhere.

## Landing notes

(Empty until it lands.)
