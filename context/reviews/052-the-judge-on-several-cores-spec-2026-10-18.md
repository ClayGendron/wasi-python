# Review of spec 052 before build: the judge on several cores

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). It wrote neither the specification nor the memo.
- **Reviewed:** `context/specifications/052-the-judge-on-several-cores.md` at `9047dcf` and
  `context/research/2026-10-18-the-judge-on-several-cores.md` at `484070a`, on branch
  `spec/052-the-judge-on-several-cores` (`git diff 62d2c56...HEAD`: those two files only), with
  the research's evidence (`build/reviews-evidence/research-052/` of the main tree: the run
  records, `prototype-v2.patch`, `prototype-v3.patch`, `runs.txt`, the worker dumps). This is a
  voluntary pre-build review, asked for because the spec changes how every verdict is computed.
  It was reviewed as a judge change. The bar: a parallel run's verdict never differs from a
  serial run's, and no guard of the landing lane (spec 029) gets weaker.
- **Read:** `AGENTS.md` (rules 2, 3a, 4–6a, 9); the constitution (§4.9, §4.13, §5.2, §5.6,
  §5.7); `context/progress/README.md` (the lane, steps 1–6); spec 029 (Decisions 1–7); spec 032
  (its fourth revision after landing: the deadline by count); `context/reviews/README.md`.
  Main's harness at `3dfdab4`, which the build rebases onto: `tests/harness/plugin.py` (the
  whole file; unchanged since `62d2c56`), `scoreboard.py` (`FUEL_TOLERANCE`, `accept`),
  `paths.py` (`JUDGE_PATHS`, `judge_files`), `zips.py` (new since `62d2c56`, spec 035), `jobs.py`,
  `pins.py`, `tests/conftest.py`, `tests/checks/conftest.py`; the four checks of Decision 9 and
  their neighbours in `test_v1_2_hostile_guest.py` and `test_v1_4_embedding.py`;
  `src/wasi_python/runner.py` (`_zip_folder`, `_epoch_ticker`). pytest-xdist 3.8.0's
  `plugin.py`, `looponfail.py`, `dsession.py`, `remote.py`, `workermanage.py`, `newhooks.py`,
  `scheduler/loadscope.py`.
- **Executed** (in a scratch copy of main made with `git archive HEAD`, its own `.venv`, xdist
  only through `uv run --with pytest-xdist==3.8.0`; scripts and logs beside this file; no tree
  of the repository written):
  - **Fuel, recomputed from the fourteen run records** (`fuel.py`): 66 fuel metrics in each; 26
    vary; largest relative differences serial–serial **1.2503e-6** (`full-serial-1` against
    `pair-serial`, `test_upstream_suite[pandas-tslibs]`), parallel–parallel **7.643e-7**,
    serial–parallel **1.2612e-6**. Every other field (`status`, `need`, `area`, `closer`,
    `facts`, `bytes`, `passes`, metric names, `deselected`, `collected_files`, `suite`) equal to
    `full-serial-1` in every run except four status differences: `full-x6-sched` (the rootless
    check), `full-x6-v3` and `full-x8-1` (the door deadline check), `pair-x6-a` (two rules
    checks reading placeholder documents). The memo's numbers hold.
  - **`--looponfail` and the hooks' order** (a probe written into the scratch copy's
    `plugin.py`, then removed): under `-f`, the controller runs only `pytest_cmdline_main`
    (`looponfail=True`); its `pytest_configure` never runs. The child it spawns has
    `looponfail=False` in both hooks and runs a whole harness session: it wrote
    `--progress-latest` (`lf.log`: `unit suite 5/5`, red only by `steered from outside the
    judge: plugin xdist …; plugin xdist.looponfail …; plugin … (xdist.looponfail)`). A tryfirst
    `pytest_cmdline_main` in the harness runs before xdist's and sees the raw options
    (`n=2 dist=no tx=[]`). At `pytest_configure`, `-n 2 --tx popen` and plain `-n 2` both read
    `dist=load tx=['popen', 'popen']`; workers read `dist=no` and keep a given `--tx`.
  - **`zips.judge_zips` from four processes at once, cold** (`race.py`, three trials): trial 1,
    `OSError [Errno 66] Directory not empty: …/zips-g8pzbwtr -> …/zips-daf2cdd86357e617` and
    `FileNotFoundError …/zips-daf2cdd86357e617/padded.zip`; trial 2, one `Directory not empty`;
    trial 3, four `ok`. Then `tests/checks/test_v1_3_the_zips_directory.py` cold under `-n 4`
    once and `-n 8` three times: `20 passed` each time (the race did not show end to end).
  - **The dependency's metadata**: pytest-xdist 3.8.0 `License-Expression: MIT`, `Requires-Dist:
    execnet>=2.1, pytest>=7.0.0`; execnet 2.1.2 `License-Expression: MIT`.
- **Not re-run:** the scoreboard. There is no build to judge yet.

## The design against the questions asked

- **Records and acceptance (READ, with the memo's EXECUTED prototype).** Every field the
  scoreboard, ratchet, `latest.json` and `accepted.json` use is carried. The record (`status`,
  `reason`, `need`, `closer`, `metrics`, `facts` with `passed_digest`, counts, `left_out`) rides
  on each phase's report. The unit tally rides on the report. `areas`, `deselected`,
  `collected_files` and `narrowed_files` ride on `workeroutput`. The gaps file, `gap_errors`,
  `run_meta()` (judge hash, commit, artifact, dirty) and `foreign` are made by the controller
  itself in its own `pytest_configure` and `pytest_sessionfinish`, as today. xdist calls
  `pytest_testnodedown` before the loop ends, so the merge comes before `sessionfinish`
  (`dsession.py`, `worker_workerfinished`). The worker's `sessionfinish` hook runs inside
  xdist's hookwrapper, so `workeroutput` is filled before it is sent (`remote.py:141–149`).
  Workers return before any write. The one hole is a process that is neither a worker nor the
  controller: the looponfail child (F2).
- **Spec 029's guards (READ, EXECUTED for the hook order).** The controller's `pytest_configure`
  runs before any worker starts (workers start in `DSession.pytest_sessionstart`). So the
  worktree refusal and the dirty-tree refusal still come before anything runs. The late
  re-check and `head_moved` run in the controller's `sessionfinish`, after every worker is down.
  Workers also run `accept_refusal` and stash HEAD in their own `pytest_configure`. That writes
  nothing, but the guards then run more than once (F11).
- **The scheduler (READ).** `DSession.pytest_xdist_make_scheduler` is `trylast` and the hook is
  `firstresult`, so the harness's scheduler wins. Node ids pass through it unchanged. With
  `-k`, `-m` or `--lf`, workers deselect the same items (`LFPlugin` skips its cache write on
  workers), and the scheduler sees only what was selected. Ties in the size reordering keep
  collection order, so the deal is deterministic. A wrong scope only costs a second run of a
  group on another worker. But a class check and its group check could then see two different
  runs of one group, so the mapping should be exact, not a prefix guess (F7).
- **The four checks.** *The rootless pair (READ):* the runner's zip folder is one per process by
  design (`runner.py:1555`, "one read-only folder per zip per process"). Every accepted serial
  run judged these checks warm. Moving the warm-up above the redirect keeps exactly what they
  asserted. It hides no defect. *The door deadline:* widening 0.05 s to 2.0 s is still a bet on
  start-up speed, so F3 requires the count-based form.
- **Fuel (EXECUTED).** Confirmed above. The tolerance is documented: `scoreboard.py:31`
  (`FUEL_TOLERANCE = 1e-4`, "the clock-and-random memo") and spec 002 (lines 114, 431, 443).
  The ratchet counts only growth past it. Nothing in the records points to scheduling: the
  parallel band is narrower than the serial one, and no value shifts in step with N.
- **The verdict and N.** No run shows a verdict that depends on N, once findings 7 and 8 are
  fixed. But that evidence covers only the orders that were seen. F4 keeps the verdict of record
  serial until there is a track record.
- **The dependency (READ, EXECUTED).** §4.13's reason is written (Decision 1). Both packages are
  MIT. The pin is exact, and `uv.lock` is in `JUDGE_PATHS`, so the lock is in the judge hash.
  The dev-group check (`test_v1_4_embedding.py:438`) refuses only `wasmtime` there.

## Findings, most severe first

1. **High. Shared caches were never re-surveyed after the rebase, and `zips.judge_zips` races
   (EXECUTED).** Spec 035 landed after the memo's commit. It added a fixed path,
   `build/harness/zips-<sha>`, which `judge_zips` builds in a temp folder, then runs
   `shutil.rmtree(home)` and `os.replace(work, home)` (`tests/harness/zips.py:233–241`). Each
   worker builds it once, from a session fixture. The zips checks are separate scopes, so they
   are dealt to different workers.
   *Failure:* a cold `build/` (any fresh worktree, or any new stdlib zip) and two workers reach
   the fixture together. One worker's `os.replace` fails with `ENOTEMPTY`, or one worker
   deletes the folder another is reading (`FileNotFoundError`). A zips check errors under `-n`
   and passes serially. Four processes at once showed it in 2 of 3 trials. Four cold runs of
   the file under `-n 4` and `-n 8` did not.
   *Required, written into the spec:*
   - make `judge_zips` safe across processes: never remove a home another process may read;
     on `ENOTEMPTY` use the complete home that is already there; or take an `fcntl` lock, as the
     memo's v3 driver cache did;
   - add a unit self-test: N processes build it cold at once, and every one gets both files
     whole;
   - re-run the memo's shared-path census (finding 9) and its run-alone census (finding 7) on
     the rebased commit, and record both in the landing notes;
   - widen criterion 8 to "every goal check outside the upstream file passes alone in a fresh
     process", as a count.
   Main has added the zips, public-API and embedding checks since the memo was run.

2. **High. The `--looponfail` refusal cannot live in `pytest_configure`, and its child would be
   an unrefused acceptor (EXECUTED).** Under `-f`, looponfail's `pytest_cmdline_main` returns
   before the controller's `pytest_configure` runs. The child process then has
   `looponfail=False`. It runs a whole non-worker harness session, which writes `latest.json`.
   Under Decision 5 every plugin it shows is xdist's, so it is no longer foreign.
   *Failure:* `uv run pytest -f --accept r` is not refused. A process that is neither the plain
   judge nor the controller reaches `scoreboard.accept`, and does it again on every re-run after
   a file change. Spec 029's guards still apply, but Decision 7's "exits before collection"
   does not happen.
   The same timing breaks the `--tx` check. By `pytest_configure`, xdist has already replaced
   `tx` with `["popen"] * n`, so `-n 2 --tx popen` looks like `-n 2`.
   *Required:* put all of Decision 7's refusals in a `tryfirst` `pytest_cmdline_main` in the
   harness plugin. It runs before xdist's hooks and sees the raw options. It should return exit
   code 1 with one line, and skip workers, which carry a given `--tx`. Criterion 6 runs `-f`
   under a fail-safe and asserts that nothing was written.

3. **High. The door deadline check must count, not wait 2.0 s (§4.9).** A 2.0 s deadline still
   decides the outcome by how fast the guest starts. Spec 032's fourth revision fixed the same
   failure the counted way: a 0.05 s deadline that start-up outran at load averages 174 to 237.
   It used a 60 s deadline, and the host advanced the ticker past `stop_at` by count. The seams
   are already in this file: `test_v1_4_embedding.py:1795`
   (`runner._epoch_ticker.count = classmethod(lambda cls: call.stop_at)`) and `:3128`
   (`runner._stack()[-1].stop_at = runner._epoch_ticker.count()`).
   *Required:* `deadline_s` large (60 s). In `blocks`, print "in the door", make the call's
   deadline overdue by count, then hold the host for `CANCEL_TICKS + 2` ticks as now. Same
   assertions.
   `test_a_tool_blocking_past_the_deadline_is_answered` (`deadline_s=3`; the guest must reach
   `tools.block()` first, or `outcomes[-1]` raises) has the same shape. The memo names it. The
   spec fixes it the same way, or says in writing why not.
   *Failure without the fix:* several agents each running `-n 6` (F13) slow start-up past the
   budget. Decision 11 then stops the lane on a check that measures time.

4. **High (a decision). The lane's accepting run should stay serial for now (INFERRED, from the
   memo's own limit).** The memo says its census "cannot find a check spoiled by an earlier
   one", and eleven orders are not all orders.
   *Failure:* a check fails only after another check in the same process (pollution, or a fault
   on the warm path). A parallel lane may run it cold on a fresh worker, pass it, and accept a
   pass that the serial judge fails. CI and the release workflow stay serial (Scope, Out), so
   they would later show a lost pass. Decision 11's diagnosis ("fails under `-n` and passes
   serially") also needs a serial run, which a parallel-only lane never makes.
   *Required:* lane step 3 stays `uv run pytest --accept "<reason>"`. Builders and reviewers use
   `-n 6`. Each landing's notes record `sameness.py` between the reviewer's `-n 6` record and
   the lane's serial record, when the rebase changed no judged file or code. After a stated
   number of clean landings (say ten), a memo may move the lane to `-n 6` without a new spec.
   If the owner wants a parallel lane now, the spec must instead name a periodic serial
   confirmation and what happens when it differs.

5. **Medium. Criterion 2 cannot be met as written.** "The suite above" (criterion 1) has failing
   checks on purpose: a check that fails differently from its gap, an `xfail` with no gap, an
   XPASS, a skip without a known need, a failure in teardown. So `--accept` is refused, serially
   and under `-n 3` alike, and `history.jsonl` gets 0 lines, not 1.
   *Required:* a green variant for the first run: passes with metrics, a note and facts, a gap
   that matches, a blocked check, a deselected check, unit tests. Then the failing variant for
   "writes nothing new".

6. **Medium. Decision 5 would flag the harness's own `Controller` as foreign (READ).**
   `Controller` is registered as an object. It has no `__file__`, and its type's module is
   `harness.plugin`. `foreign_steering` names it, so every `-n` run is red. The prototype
   allowed `module == __name__`. The spec does not.
   *Required:* write the allowance for objects whose type is defined in a judged file.

7. **Medium. The central criterion needs named stand-ins and two more shapes.** The spec should
   list the stand-ins the end-to-end test is shown to fail against, recorded by the builder:
   - (a) today's plugin;
   - (b) a controller that keeps the first record per node, not the last (the teardown failure
     after a pass catches it);
   - (c) records rebuilt from report outcomes rather than carried (facts, note and need are
     lost);
   - (d) `deselected` or `narrowed_files` not merged;
   - (e) the unit tally counted both from the property and from the report;
   - (f) the judge's scheduler not in effect.

   The suite has no run narrowed to node ids, which is how `collected_files - narrowed_files`
   is judged, and no `-k`. Add both. Criterion 7 tests `scope_of` but not that xdist used the
   scheduler. Assert that end to end: the controller can note `type(dsession.sched)`, or two ids
   that map to one scope can report the same `os.getpid()`. Build the upstream scope map exactly,
   from the groups and class ids that `upstream.load_all()` yields, not from the longest prefix.

8. **Low. A worker crash shows as `unrun`, not `fail` (READ, `dsession.py:432–452`).** xdist's
   crash report carries no record property. The run is red either way. Say that a goal check
   named in a failed report without a record becomes `fail`, with xdist's message. Decision 4's
   "its checks are unrun" is also too wide: only the check that was running is lost, and the
   dead worker's other scopes are dealt again.

9. **Low. Tighten the allowance.** Take the allowed folder from the `pytest-xdist` distribution
   (`importlib.metadata.distribution("pytest-xdist")`). Require `xdist.__version__` to equal the
   lock's version. As written, the check reads `import xdist`'s folder and the installed
   metadata's version, which disagree if an `xdist` package shadows it on `sys.path` (and
   `pythonpath` includes `tests/`). Check an object plugin by its module's file, not by a
   `xdist.` name prefix. Consider checking execnet's version against the lock too: it carries
   every record, and as a non-plugin the foreign check never sees it.

10. **Low. Decide every xdist option (§5.2).** Name each option and its fate:
    - allowed: `--maxprocesses` and `--max-worker-restart`;
    - `--loadscope-reorder` and `--no-loadscope-reorder` change only the order: allow or refuse
      them;
    - `--maxschedchunk` is ignored by the LoadScope scheduler;
    - `--rsyncignore` belongs with `--rsyncdir`;
    - `--testrunuid` is harmless;
    - `-d` without `-n` gives no workers;
    - `-n logical` needs psutil, which is not installed.

    Register `Controller` only when xdist distributes (`dist != "no"` and `tx`), not on
    `dist != "no"` alone.

11. **Low. Run spec 029's guards once.** Workers skip the accept refusal and the HEAD stash in
    `pytest_configure`. Today they repeat them, and a worker that sees the tree change during the
    run exits at start instead of the controller refusing once.

12. **Low. Decision 12 leaves out `reason`.** For `pass` (the note, spec 051's coverage line),
    `gap` and `blocked`, the reason is deterministic and part of the record. Compare it for those
    statuses, or say why not. Also define the fuel test: `|a − b| > FUEL_TOLERANCE × max(a, b)`.

13. **Low. Memory when agents run side by side.** `-n 6` peaked at 8.4 to 9.8 GiB. §5.7 allows
    four specs in flight. Four full `-n 6` judges at once exceed the 32 GiB machine. Decision 10
    should advise a lower N when others are running. This is a benchmark note, not a rule.

14. **Note.** `meta.workers` should be the number of workers actually started
    (`len(config.option.tx)` after `--maxprocesses`), not `numprocesses`. The run counts in
    criterion 9 (`294/308`) predate main's new checks. The criterion already allows "what the
    set accepted at build time shows".

## Constitution checks

- §4.9: holds once F3 is written in. No criterion times anything. Wall-clock is reported only as
  benchmark facts.
- §4.13: holds. The reason, the licences and the exact pin are written.
- §5.2: needs F10 (every option decided).
- §5.6: this voluntary pre-build review. The build is reviewed again.
- §5.7: needs F4. "The full judge on that exact commit" is still met by a parallel run, but the
  verdict of record should stay serial until it has a track record.
- §7: nothing tripped.

## Verdict

**Ready once F1 to F7 are written in.** F8 to F14 should be fixed or answered in writing in the
spec before it is built.

One line: the record-carrying design is sound and the memo's numbers hold, but the build must
make the zips cache safe across processes, refuse `--looponfail` where it can be refused, make
the door deadline count, and keep the lane's accepting run serial until parallel has a record.

## Disposition (by the author, on `spec/052-the-judge-on-several-cores` rebased onto `c7b7f26`)

Written into the spec at `eb9805a` (Decisions 4 to 14, criteria 1 to 12, and its "Disposition of
the pre-build review" section), with the memo's addendum; the same table is in
`build/reviews-evidence/052-review/disposition.md`. In short:

- **F1:** Decision 13 (one `os.rename` into `zips-<sha>-v2`; a finished folder is never removed;
  no lock, because the Windows dry run has no `fcntl`); criterion 10 (6 processes × 3 trials);
  both surveys re-run (addendum: 311 alone, 305 pass, 2 blocked, 4 fail); criteria 8 and 9.
- **F2:** Decision 7, with every refusal in a `tryfirst` `pytest_cmdline_main` that skips
  workers; criterion 6.
- **F3:** Decision 9: the door check and the tool-deadline check both by count (60 s deadline,
  made overdue by count).
- **F4:** Decision 11, the lane's ruling. The accepting run stays serial. Every landing records
  `sameness.py`. After ten clean landings a memo may move the lane, with a serial confirmation at
  least every tenth landing.
- **F5 to F14:** criterion 2's green variant; the `Controller` allowance; stand-ins (a) to (f)
  with the narrowed and `-k` shapes; the exact scope map and `meta.scheduler`; Decision 14
  (crash → `fail`); the distribution-based allowance with the execnet pin; the full option
  table; guards controller-only; `reason` and the fuel test in `sameness.py`; `-n 3` advice;
  `meta.workers` from `len(tx)` and refreshed counts.

## Confirmation (2026-10-18)

- **Reviewed:** `git diff 5c18ca0 eb9805a` (spec and memo addendum), the disposition, and the
  census logs in the worktree's `build/research-052/alone2/`. Probes ran in the same scratch copy
  of main as before. xdist came only through `uv run --with pytest-xdist==3.8.0`. The prototypes
  were removed afterwards, and no tree was written.

**F1: confirmed.**
- *Census (EXECUTED).* The census logs recount to 311 records: 305 pass, 2 blocked and 4 fail.
  The four failures are the three rootless checks and the door deadline check.
- *Design, macOS (EXECUTED).* `race2.py` implements Decision 13 as written: `mkdtemp`, build,
  `os.rename(work, home)`, and on `FileExistsError`/`ENOTEMPTY`/`EEXIST` remove only its own work
  folder and use `home`. I ran six processes at once, cold, three trials. All 18 returned
  complete zips (1,764 and 7,044 members). Each trial left exactly one `zips-<sha>-v2` folder and
  no work folders. Today's code failed 2 of 3 trials with four processes.
- *Design, Windows (INFERRED, not run).* There is no window in which `home` exists but is
  incomplete. It comes into being only by renaming a finished folder, and it is never renamed
  onto or removed. That holds on Windows as well. There, renaming a directory onto an existing
  one fails with WinError 183, which Python raises as `FileExistsError` (errno `EEXIST`). The
  losing process then takes the winner's folder. Windows can still raise a passing
  `PermissionError` (a scanner holding a freshly written file in `work`). Today's `os.replace`
  has the same exposure, so this is no regression.
- *Optional hardening.* On any `OSError` from the rename, use `home` if it is now a directory,
  and raise only if it is not. Rejecting `fcntl` is sound.

**F2: confirmed (EXECUTED against a scratch prototype of Decision 7).** I added a `tryfirst`
`pytest_cmdline_main` to the scratch copy's `plugin.py`. It reads `config.option`, skips a config
that has `workerinput`, and returns 1 with one line. Results:
- Every refused row of the table exits 1 with its line and writes 0 files under the scratch
  progress paths: `-f`, `-n 2 --tx popen`, `--tx popen --dist load`, `-n logical`,
  `-n 2 --dist each`, `-d`, `--no-loadscope-reorder`, `--maxschedchunk 2`, `--px …`,
  `--rsyncdir tests`, `--rsyncignore x`.
- Every allowed row runs its tests and writes its record: `-n 2`, `--maxprocesses 1`,
  `--max-worker-restart 0`, `--dist load`, `--loadscope-reorder`, `--testrunuid x`, and serial.
  Each still ended red, because Decision 5 is not in the prototype and the xdist plugins counted
  as foreign.
- Workers reach `pytest_cmdline_main` with `workerinput` already set, so skipping them works.
- **The option table is complete** against xdist 3.8.0's command line: `-n`, `--maxprocesses`,
  `--max-worker-restart`, `--dist`, `--loadscope-reorder`, `--no-loadscope-reorder`, `-d`,
  `--tx`, `--px`, `--rsyncdir`, `--rsyncignore`, `--testrunuid`, `--maxschedchunk`, `-f`. The ini
  keys `rsyncdirs`, `rsyncignore` and `looponfailroots` can come only from `pyproject.toml`,
  which is judged, and do nothing without the refused options. They need no row, though one
  line saying so would close §5.2 fully.

**F3: confirmed (READ).** Both checks still test what they claim.
- *The door check.* Under `cancel=`, the epoch callback reads `call.stop_at` at each callback
  (`runner.py:2512–2516`). The door callback runs on the guest's thread, where `_stack()` holds
  the call; the existing seam at `test_v1_4_embedding.py:3128` does the same in a `host=`
  callback. So setting `stop_at` to the current count, then holding the door `CANCEL_TICKS + 2`
  ticks, makes the deadline pass by count while the host is in the door. The first callback after
  the door then names it `"deadline"`. That is the claimed behaviour. Only the conversion from
  `deadline_s` to ticks is no longer exercised, and the check never claimed it.
- *The tool check.* The bound reads `ticks=lambda: _epoch_ticker.count()` at call time
  (`runner.py:3116`, `tools.py:1584`), so raising the count makes it answer `timeout`, which is
  what is asserted.
- *C2 below* covers a pitfall in how the tool check gets the call's `stop_at`.

**F4 to F14: confirmed as written** (READ).
- F4 matches the lane's ruling.
- F6 and F9: see C1.
- F7's end-to-end scheduler assertion and exact map are sound.
- F8, F10 to F14 are answered.

**Conditions for the build** (wording, not design; the build review checks them):
- **C1. The allowance's folder is xdist's package folder, never `site-packages`.** Decision 5
  says "the folder of the installed `pytest-xdist` distribution … where its files are". Read as
  `distribution("pytest-xdist").locate_file("")`, that is all of `site-packages`, and every
  installed plugin would pass. It must be `locate_file("xdist")`, the package folder named in the
  distribution's `RECORD`. Criterion 5's "any other plugin is still a finding" must include a
  module from `site-packages` outside `xdist/`, such as `iniconfig` loaded with `-p`. One line in
  Decision 5 and one in criterion 5.
- **C2. The tool check cannot use `runner._stack()` from inside the tool.** `_calls` is a
  `threading.local` (`runner.py:2399`), and a tool runs on its own thread, so `_stack()` there is
  `[]` and `[-1]` raises. The tool would then report a `tool_error`, not a `timeout`.
  `MOUNT_CANCEL`'s `past_deadline` works only because a provider runs on the guest's thread.
  Inside the tool, set the count past any deadline instead, for example
  `runner._epoch_ticker.count = classmethod(lambda cls: 2**62)`, or take `stop_at` on the guest's
  thread first. A builder's note in Decision 9.

**Verdict: ready to build.** C1 and C2 are carried into the build as conditions. C1 should be
one line in Decision 5 and one in criterion 5 before the builder starts. The build review checks
both.

One line: the revision answers every finding; the rename design, the hook placement and the
option table hold under probes; build it, with the allowance scoped to `xdist/` and the tool
check counting without the guest's thread-local stack.
