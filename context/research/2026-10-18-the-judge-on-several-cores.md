# The judge on several cores

- **Status:** executed, 2026-10-18 (time box: one session). Nothing in the repository was changed
  by it: the prototype below lived in the 052 worktree's working copy only, was removed before
  the commit, and every log and run record is under that worktree's `build/research-052/`
  (git-ignored), with the prototype as `prototype-v2.patch` (findings 3 and 4) and
  `prototype-v3.patch` (finding 10), and the scratch scripts named below.
- **Owner:** Clay Gendron
- **Researcher:** the drafting agent (Claude Opus 5.5) of spec 052.
- **Asked by:** the owner, 2026-10-18: run the judge across CPU cores with pytest-xdist, so the
  full run takes less wall-clock time, with identical verdicts, fuel and byte metrics.
- **Feeds:** `../specifications/052-the-judge-on-several-cores.md`.
- **Stands on:** spec 002 (the progress harness), spec 029 (the lane's guards), spec 050 (the
  upstream suites, the slowest checks), `2026-10-16-a-host-supplied-clock-and-random-make-fuel-exact.md`
  (the fuel residual and the ratchet's 0.01% tolerance).

## The question

Can `uv run pytest` run on several cores and give the same answer? "The same answer" means: every
check's status, need, facts, `bytes` and `passes` equal to a serial run's; fuel equal as the
ratchet counts equality; the unit-suite tally, the deselected list and the collected files equal.
And `--accept` must still be written once, by one process, under the lane's guards. If it can,
what does the harness need, and how much faster is it?

## How it was run (EXECUTED)

- **Machine.** Apple M1 Pro, 10 cores (8 performance, 2 efficiency), 32 GiB
  (`sysctl -n hw.ncpu hw.memsize machdep.cpu.brand_string`; `sysctl hw.perflevel0.physicalcpu
  hw.perflevel1.physicalcpu`: 8 and 2). darwin-arm64, Python 3.14.2, pytest 9.1.1, wasmtime-py
  49.0.0.
- **The machine was shared.** Builders of specs 049 and 054 ran their own judges in sibling
  worktrees during these runs. The one-minute load average was 74 to 77 when sampled
  (`uptime`, `sysctl -n vm.loadavg`). Every wall-clock number below is a benchmark fact taken under
  that load, not a quiet-machine figure. Counts and verdicts do not depend on it.
- **Worktree.** `wasi_python-052` at `62d2c56`, with `WASI_PYTHON_ARTIFACTS` set to the frozen
  set `build/sets/s-f94dec535086b06c` of the main tree (read only; its `python.wasm` is the
  artifact in `accepted.json`). As spec 050 Decision 20 does: read-only symbolic links to the
  main tree's untracked `downloads/*` files, its seven source trees and `build/brett-3.14.7`, and
  to each `context/prior_art/` clone; the oracle's cache and interpreter copied into the
  worktree's `build/oracle/` (the venv was then made offline by uv); the kit fetched with
  `uv run python tests/upstream/fetch.py`. Nothing in the main tree was written.
- **pytest-xdist 3.8.0** (the newest release, 2025-07-01, by PyPI's JSON API), with execnet 2.1.2,
  its one dependency; both MIT (READ: their installed metadata). A first try used
  `uv run --with pytest-xdist==3.8.0`; that overlay environment has no `ruff` beside its
  interpreter, so `test_ruff_check_is_clean` failed with `FileNotFoundError` for a reason that
  is not xdist's. The measured runs instead installed it into the worktree's own `.venv` with
  `uv pip install pytest-xdist==3.8.0` and ran `uv run --no-sync pytest …`. `pyproject.toml` and
  `uv.lock` were not edited.
- **Each run** went through a wrapper (scratch `judge.sh`) that records wall-clock, the CPU time
  of the whole process tree (`/usr/bin/time -p`, user plus sys), the peak total RSS of the tree
  sampled once a second (`ps -A -o pid,ppid,rss`), and keeps `build/progress/latest.json`.
- **Comparison** (scratch `compare.py` and `table.py`): every check's `status`, `need`, `area`,
  `closer`, `facts`, `bytes`, `passes`, and the run's `deselected`, `collected_files` and `suite`,
  compared exactly; fuel compared value by value, with its largest relative difference.

## Findings

### 1. Today's harness gives an empty scoreboard under xdist (EXECUTED)

`uv run pytest -m "not slow" -n 4`, the plugin unchanged: exit 1, scoreboard
`0/0 pass · 0 gap · 0 blocked · 0 fail (unit suite 0/0)` and `not selected 294`, then
`RED: steered from outside the judge: plugin xdist …; plugin xdist.looponfail …; plugin
terminaldistreporter (xdist.dsession)` (`build/research-052/fast-x4-try.log`).

Why (READ, `tests/harness/plugin.py`; xdist 3.8.0's `dsession.py`, `remote.py`):

- **Collection runs on the workers only.** The controller never calls
  `pytest_collection_modifyitems` or `pytest_deselected`, so its `State.areas`, `deselected` and
  `collected_files` stay empty.
- **Records are made in `pytest_runtest_makereport`,** which runs where the test runs: on a
  worker. The controller sees only the reports (`pytest_runtest_logreport`). The item's `stash`
  (metrics, notes, facts) never leaves the worker.
- **`pytest_sessionfinish` runs on every worker too,** with the same options, `--accept`
  included. Each worker builds a run record of its own share, the rest marked `unrun`, writes
  `latest.json`, and reaches the acceptance path.
- **`foreign_steering`** names xdist's plugins as foreign, which is right today: nothing in the
  judge names xdist.

What survives as it is (EXECUTED in the prototype below): the gap logic, the need parsing, the
`rep.outcome` rewrites (a worker's report is serialized after `makereport`, so the controller
and its exit status see the rewritten outcome), the node ids, and `report.user_properties`,
which xdist carries from worker to controller.

### 2. Only an accident stops the workers from accepting today (EXECUTED)

`uv run --no-sync pytest tests/checks/test_v1_5_rebuild_from_pins.py -n 3 --accept probe
--progress-dir <scratch>`, three variants:

| plugin | controller | workers | files written |
|---|---|---|---|
| unchanged | `RED: --accept refused: this run collected no goal checks` | refused (INFERRED: as in the next row, xdist's plugins being foreign as well) | `latest.json` only |
| unchanged, plus an allowance for `xdist*` plugins only | the same | each refused, its `red` naming `plugin … (__channelexec__)` (execnet's worker module) | `latest.json` only |
| the prototype (finding 3) | accepted, `history.jsonl line 1` | write nothing | one history line, one `accepted.json` |

The second row was read from a scratch line that wrote each worker's `(exitstatus, records, red,
accept line, reason)` (`build/research-052/worker-gw*.txt`): each worker had 18 records,
exit status 0, and the acceptance refused only because the run was not green, and only because
of execnet's module. So a harness that allowed xdist's and execnet's plugins without silencing
the workers would let every worker try to accept its own partial run (INFERRED), racing on
`accepted.json` and `history.jsonl`. **Workers must be silenced explicitly, not by the foreign
check.**

### 3. A prototype that makes the record whole (EXECUTED)

A scratch change to `tests/harness/plugin.py` (about 120 lines; not committed):

- A worker is `hasattr(config, "workerinput")`. Never the `PYTEST_XDIST_WORKER` variable: a
  pytest that a check starts in a subprocess inherits it.
- On a worker, after each phase, `makereport` appends the node's current record to
  `rep.user_properties` as `("wasi_python.record", [node, record])`, and a unit test's tally as
  `("wasi_python.suite", [passed, skipped])`. The worker's own "a failure in any phase stands" rule
  makes the record; the controller keeps the last one it receives for each node.
- On the controller (registered only when `dist != "no"`), `pytest_runtest_logreport` takes those
  properties into `State`; `pytest_testnodedown` merges each worker's `workeroutput`
  (`areas`, `deselected`, `collected_files`, `narrowed_files`), which every worker fills in its
  `sessionfinish` and then returns, writing nothing.
- `foreign_steering` allows modules of the installed `xdist` package and objects whose module is
  `xdist.*` or the plugin itself.

Fast tier, `-n 4`: exit 0, `267/308 pass · 0 gap · 2 blocked · 0 fail · 39 deselected (unit
suite 1023/1025, 2 skipped)`, the same line as the serial fast tier. Compared with it: 308
checks, 0 status differences, 0 reason differences; two fuel values differ, by 34 and 17
instructions in five billion (`fast-x4-proto`). A second serial fast run differs from the first
in the same two checks, by 34 and 51 (`fast-serial-proto`): that is the known residual
(finding 6), not xdist.

### 4. The upstream suites need their own scheduling (EXECUTED)

Each upstream class check reads its group's run from the session-scoped
`upstream.Session`, one per process (READ: `tests/checks/test_v1_3_upstream_suites.py`,
`tests/harness/upstream.py`). On another worker a class runs its whole group again.

- `uv run --no-sync pytest tests/checks/test_v1_3_upstream_suites.py -n 8 --durations=0`: the
  class checks ran their groups again: `test_upstream_class[pandas-groupby-zip-code-names]`
  150.6 s, `[numpy-core-no-dup-file-left-open]` 87.1 s, `[numpy-core-no-ctypes]` 85.0 s, and so
  on (`upstream-x8.log`). Same verdicts, double the work.
- In the full judge under xdist's default `--dist load` this did not happen, by accident. Its
  first round sends each worker one run of consecutive tests (`items_per_node // 4`, READ:
  `xdist/scheduler/load.py`), and all 32 upstream items (positions 134 to 165 of 1,333 collected)
  fell in one worker's run at `-n 8`. That one worker then ran every upstream group in series:
  wall 445 s against 580 s serial (`full-x8-1`). Other worker counts can split them.
- `--dist loadgroup` is not usable: it appends `@<group>` to every grouped node id
  (READ: `xdist/remote.py`, `item._nodeid = f"{item.nodeid}@{…}"`), and the judge keys every record,
  gap and acceptance by node id.
- **What works:** the plugin answers xdist's `pytest_xdist_make_scheduler` hook with a subclass
  of `LoadScopeScheduling` whose `_split_scope` returns `upstream <group>` for a group's check
  and its classes' checks, and the node id for everything else. Node ids are unchanged. With
  xdist's default reordering by scope size, the upstream groups (two to six items each) are
  dealt first, so the longest group starts at once when there are at least six workers.

### 5. The full judge: identical verdicts, about three times faster (EXECUTED)

The serial baseline is today's judge, plugin unchanged, xdist not installed:
`uv run --no-sync pytest --durations=80`, wall **580 s**, `294/308 pass · 12 gap · 2 blocked ·
0 fail (unit suite 1023/1025, 2 skipped)`, `1317 passed, 4 skipped, 12 xfailed`, the lane's own
line for spec 050 (`full-serial-1`). Its slowest checks are the upstream groups: pandas-groupby
79.7 s, pandas-frame 57.6 s, numpy-core 31.1 s, numpy-others 26.2 s, numpy-lib 22.1 s; the
eleven together about 266 s. The golden oracle check is 21.9 s.

With the prototype and the scheduler (`uv run --no-sync pytest -n N`):

| run | N | wall | CPU | peak RSS (tree) | statuses | other exact fields | fuel values differing / 66 | largest fuel difference |
|---|---|---|---|---|---|---|---|---|
| full-serial-1 (unchanged judge) | serial | 580 s | – | 2.9 GiB | baseline | baseline | – | – |
| full-serial-2-proto | serial | 627 s | 736 s | 2.8 GiB | 0 | 0 | 17 | 7.2e-7 |
| full-x4-sched | 4 | 227 s | 896 s | 9.0 GiB | 0 | 0 | 17 | 1.2e-6 |
| full-x6-sched | 6 | 170 s | 1019 s | 9.2 GiB | **1** | 0 | 16 | 1.1e-6 |
| full-x6-v2-b | 6 | 244 s | 1063 s | 8.9 GiB | 0 | 0 | 18 | 7.5e-7 |
| full-x8-sched | 8 | 200 s | 1138 s | 9.6 GiB | 0 | 0 | 19 | 9.8e-7 |
| full-x10-sched | 10 | 215 s | 1216 s | 10.5 GiB | 0 | 0 | 16 | 1.3e-6 |
| full-x8-1 (`--dist load`, no scheduler) | 8 | 445 s | – | 8.3 GiB | **1** | 0 | 16 | 1.2e-6 |

**The paired runs** (last, back to back, the same prototype; load average sampled before and
after each, `sysctl -n vm.loadavg`):

| run | N | wall | CPU | peak RSS | load before → after | statuses vs pair-serial | other exact | fuel differing | largest |
|---|---|---|---|---|---|---|---|---|---|
| pair-x6-a | 6 | 188 s | 1035 s | 8.4 GiB | 58.9 → 60.1 | 2 (see below) | 0 | 17 | 5.3e-7 |
| pair-serial | serial | 616 s | 720 s | 2.4 GiB | 60.1 → 33.6 | baseline | baseline | – | – |
| pair-x6-b | 6 | 171 s | 1016 s | 9.5 GiB | 33.6 → 49.7 | 0 | 0 | 16 | 1.3e-7 |

pair-serial against full-serial-1: 0 status and 0 other differences, 20 fuel values differing,
largest 1.25e-6. pair-x6-a's two failures are not xdist's: `test_rules.py::test_specifications_have_their_header_and_sections`
and `test_executed_memos_label_their_claims` read this memo and spec 052 while they were still
one-line placeholders in the worktree (`no 'Status' header line`, `no EXECUTED, READ or INFERRED
label`); the rules read untracked documents by design. Both passed in the next two runs, once the
files were written.

"Other exact fields" counts differences in `need`, `area`, `closer`, `facts` (the upstream
groups' `counts`, `passed_digest` and `left_out`), `bytes`, `passes`, the set of metric names, and
the run's `deselected`, `collected_files` and `suite`: zero in every run. The two status
differences are findings 7 and 8; both checks pass in every other run.

- **Speed.** Parallel runs took 170 s to 244 s against 580 s to 627 s serially; back to back,
  616 s serially against 188 s and 171 s at N = 6: **3.3 to 3.6 times faster**. Under the shared load the spread between two runs of the same N was
  larger than the differences between N = 4 and N = 10.
- **The floor is the longest group.** pandas-groupby took 80 s serially but 90 s at N = 4, 149 s
  to 222 s at N = 6, 186 s at N = 8 and 203 s at N = 10, and every parallel run ended within about
  30 s of it. Each guest runs slower when many run at once (INFERRED: the shared caches and
  memory bandwidth of the performance clusters, and the other agents' load; not chased).
- **CPU grows with N.** 736 s serially, 896 s to 1,216 s in parallel. Most of the growth is the
  judge's driver compiling both binaries again in every worker
  (`tests/harness/guest.py` keeps compiled modules per process): 5.4 s and 5.3 s wall and about
  25 CPU-seconds each, maximum RSS 1.3 and 1.9 GiB (scratch `compile_time.py`, EXECUTED).
- **Memory.** 2.8 to 2.9 GiB serially; 9 to 10.5 GiB at N = 4 to 10. Well inside 32 GiB.

### 6. Fuel: no spread beyond the serial residual (EXECUTED)

Of 66 fuel metrics, 40 were equal in every one of the fourteen full runs (three serial, eleven
parallel). The other 26 vary between serial runs too: the residual of the clock-and-random memo,
which it traced to host facts the guest reads (INFERRED there). Over all pairs of the fourteen
run records (a scratch script over `full-*-latest.json` and `pair-*-latest.json`):

- serial against serial: largest relative difference **1.25e-6**;
- parallel against parallel: **7.6e-7**;
- serial against parallel: **1.26e-6**.

The largest values come from `test_upstream_suite[pandas-tslibs]`, which took a different value
in nearly every run, serial or parallel. Every difference is under the ratchet's tolerance of 1e-4
by a factor of about 80. Fuel cannot be "identical" literally even between two serial runs; it is
equal as the judge defines equal, and parallel runs add nothing measurable to the spread.

### 7. Three checks depend on an earlier check in the same process (EXECUTED)

`test_a_call_without_a_root_shares_nothing` failed at N = 6 (`full-x6-sched`):
`assert list(scratch.iterdir()) == []` found `wasi-python-zip-…` and its `.lock`. It points
`tempfile.tempdir` at a scratch folder and expects the call to leave nothing there. But the runner
unpacks its stdlib folder into the temporary folder once per process. Serially an earlier check
has already done it elsewhere; on a fresh worker this check is the first. Run alone, serially,
with xdist disabled (`uv run --no-sync pytest "<node id>" -p no:xdist`), it fails the same way
(`alone-rootless.log`). It is an order dependence that parallel runs expose.

**A census** ran every goal check outside the upstream file alone, each in a fresh process (276
node ids, five at a time, each with its own `--progress-latest`; scratch `alone.sh`; 303 s): 271
pass, 2 blocked (`wheel`, `three systems`, as in the full run), **3 fail**:

- `test_v1_2_hostile_guest.py::test_a_call_without_a_root_shares_nothing`;
- `test_v1_2_hostile_guest.py::test_a_trapped_call_without_a_root_is_removed[busy]` and
  `[sleeping]`: the same defect. This check even has a warm-up call ("the engine and module are
  loaded once per process; count after that"), but it runs after `tempfile.tempdir` is redirected,
  so the warm-up itself unpacks into the scratch folder (READ, lines 333 to 338).

The census finds checks that need an earlier one. It cannot find a check spoiled by an earlier
one; the eleven parallel runs, each in a different order, found none.

### 8. One check depends on how fast the host starts the guest (EXECUTED)

`test_v1_4_embedding.py::test_a_deadline_during_a_door_call_under_cancel_is_named` failed in two
of eleven full parallel runs (`full-x8-1`, and `full-x6-v3`, a variant run of finding 10): it got
`["deadline None None b''"]` without the host's first line `"in the door"`. Its child process
calls the runner with `deadline_s=0.05`, five ticks of `TICK_S = 0.01` counted from
instantiation (READ: `runner.py`, `_instance`), and the guest must import `_host` and reach the
door within them. Under load it does not. The check says itself that the first line "proves the
guest reached the door before its deadline". It measures the host's speed, which §4.9 forbids a
check to depend on; it never failed serially here, but it would on a loaded machine.

**Census of wall-clock deadlines in the tests** (READ: `grep -rn "deadline_s=[0-9]\|deadline_s = [0-9]"
tests`, 12 lines). Most expect the deadline to fire, which load cannot prevent. Two need the
guest to reach a point first: this one (0.05 s) and
`test_a_tool_blocking_past_the_deadline_is_answered` (3 s, never failed here). The concurrency
check (spec 011) already allows for a slow start ("a loaded host can take past 0.2 s").

### 9. Shared state between workers (READ, with the runs as evidence)

- **The runner's `.cwasm` cache** (`build/cwasm-cache`, set by `runner_cache_in_build`): written
  through `mkstemp` and `os.replace` (`runner.py`, `_module_miss`), so a reader sees a whole file
  or none; the directory is made with `exist_ok=True`. The cache checks that count compilations
  use their own `mkdtemp` folders and fresh processes. Safe.
- **Temporary folders:** `guest_workdir`, `work`, the upstream session's staging and each check's
  scratch folders all come from `mkdtemp` under `build/harness/`. Safe. One fixed path,
  `build/harness/oracle-check`, belongs to the one oracle check.
- **The oracle** (`tests/harness/jobs.py`): `oracle_python()` removes and unpacks
  `build/oracle/python/<archive>` when its stamp is missing, and uv makes the venv on first use.
  Two processes doing that at once would race. Only one check needs the oracle today, so only one
  process provisions it (INFERRED; it ran without error in every run here, but the worktree's
  oracle was first made by a serial run).
- **The upstream kit** is unpacked per session into its own `mkdtemp` folder. The staging per
  worker repeats the copy; it stages both packages in every session, as spec 050 requires, so the
  grant and the fuel stay the same.
- **No ports, no sockets.** xdist's workers are local `popen` gateways (READ:
  `xdist/workermanage.py`).

### 10. Two improvements measured but not needed (EXECUTED, one run or two each)

A third prototype added (a) a serialized-module cache to the judge's driver under
`build/driver-cache`, made under an `fcntl` lock by the first process and deserialized by the
others, and (b) heaviest-group-first ordering by accepted fuel. CPU fell to 664 s to 791 s
(close to serial), peak RSS to 4.6 to 7.7 GiB, fuel stayed within the residual, but wall-clock
did not clearly improve: 190 s at N = 4, 191 s and 197 s at N = 6. Left out of spec 052; a later
change may take them with its own measurement on a quiet machine.

## Alternatives considered

- **`--dist loadfile` or `loadscope`** would keep the upstream file on one worker. Exact, but the
  file's 266 s of serial work becomes the floor of every run (finding 4).
- **`--dist loadgroup`** with `xdist_group` marks changes node ids (finding 4).
- **Marking some checks serial.** xdist has no serial phase. The two kinds of defect found
  (findings 7 and 8) are defects of the checks, which fail serially too, alone or under load.
  Fixing the checks is smaller and keeps one rule: a check's verdict does not depend on order or
  speed.
- **Whether the lane judges serially or in parallel.** The verdict must not depend on it, and
  findings 5 and 6 show it does not once findings 7 and 8 are fixed. The spec decides.

## What it decides

1. The judge can run on several cores with exactly the serial verdicts: the same statuses, needs,
   facts, `bytes`, `passes`, unit tally, deselected list and collected files; fuel equal within
   the residual that serial runs already show.
2. It needs: records carried on the reports, collection carried in `workeroutput`, workers that
   write nothing, the controller alone accepting, a narrow allowance for xdist's plugins, and a
   scheduler that keeps each upstream group with its classes without changing node ids.
3. It needs three order-dependent checks and one speed-dependent check fixed first.
4. About three times faster on this machine (580 s to 627 s serially; 170 s to 244 s at N = 4 to
   10; back to back, 616 s against 171 s and 188 s at N = 6). The longest upstream group sets the
   floor, and N = 6 is the fewest workers that start it at once.

## One line

With a small plugin change, a scheduler that keeps upstream groups whole and four flaky checks
fixed, the judge runs on six cores in about a third of the time, with every verdict and counted
metric the same as a serial run.
