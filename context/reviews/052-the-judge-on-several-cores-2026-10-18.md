# Review of 052 — The judge on several cores (build review)

- **Date:** 2026-10-18
- **Reviewer:** Claude Opus 5.5, a fresh agent. It wrote none of the spec, its pre-build review or the build.
- **Reviewed:** branch `spec/052-the-judge-on-several-cores` in the worktree `wasi_python-052`. The build is `3b80e90..17a9d16`, rebased onto main `94167a8`. The diff is `git diff 94167a8...17a9d16`: 16 files, +2035 / −38.
- **Kind:** a judge change (not build-class). The bar: a parallel run's verdict never differs from a serial run's; no spec 029 guard weakens; the lane's accepting run stays serial; the five fixed checks still test what they claim.
- **Re-ran** (EXECUTED, darwin-arm64, frozen set `build/sets/s-c4190ca065ada03a`, `uv run` only). Records and logs are in the scratchpad folder `052-buildreview/` (`runs/`, `probes/`, `crash/`, `standins/`). No tracked file was edited in any real tree. Stand-ins and probes ran in two scratch clones of the branch.

```
uv run pytest  (serial, 17a9d16)
  wasi_python v1: 340/354 pass · 12 gap · 2 blocked · 0 fail   (unit suite 1097/1099, 2 skipped)
  ratchet vs 5f56591135: lost 0 · absent 0 · unrun 0 · gained 0 · grew 0 · judge changed: pyproject.toml, tests/checks/test_v1_2_hostile_guest.py, tests/checks/test_v1_4_embedding.py and 7 more
  1437 passed, 4 skipped, 12 xfailed in 489.53s; exit 0; wall 527 s, CPU (user+sys) 694 s
uv run pytest -n 3  (17a9d16)
  wasi_python v1: 340/354 pass · 12 gap · 2 blocked · 0 fail   (unit suite 1097/1099, 2 skipped)
  ratchet vs 5f56591135: lost 0 · absent 0 · unrun 0 · gained 0 · grew 0 · judge changed: (the same)
  1437 passed, 4 skipped, 12 xfailed in 225.21s; exit 0; wall 226 s, CPU 849 s
uv run python tests/harness/sameness.py serial.json n3.json   → nothing printed, exit 0 (and exit 0 reversed)
```

Wall-clock and CPU times are benchmark facts only. Other agents' judges were running at the same time. Between the two records (EXECUTED):
- 354 checks each, with equal statuses.
- The judge hash is `4b6455f0ab52` in both, and `dirty` is false in both.
- `meta.workers` is 0 and 3. `meta.scheduler` is `null` and `JudgeScheduling`. `meta.foreign` is `[]` in both.
- Of 86 fuel values, 17 differ. The largest difference is 1.8e-7 relative, against the 1e-4 tolerance.
- Exactly one pass note differs. In `test_a_zone_load_does_not_grow_with_the_zip[plain]`, Tokyo reads 1,378,499 in one run and 1,378,516 in the other.

## Acceptance criteria against evidence

1. **Parallel judges as serial.** Met. The self-tests pass in both full runs. The builder's stand-ins (a) to (f) are recorded in `build-052/standins.txt` (READ). My own real-repo `-k` selection gave the same answer serially and under `-n 3`: 12/79 pass, 67 deselected, unit 1/1. `sameness` exit 0, and `collected_files` are equal (EXECUTED).
2. **One acceptance, by the controller.** Met (EXECUTED). Under `-n 3 --accept` with a scratch `--progress-dir`, `tests/checks/test_rules.py` wrote one `accepted.json` and exactly 1 history line. In a scratch clone's own main tree, a narrow `-n 3 --accept` was refused (32 upstream checks did not run), and `history.jsonl` stayed at 54 lines.
3. **Workers write nothing and guard nothing.** Met for writing (READ: `plugin.py:667` returns before anything is written; EXECUTED in every probe below: 0 files). "Guard nothing" removes one guard by accident: see F2.
4. **The guards hold under `-n`.** Met (EXECUTED). In this linked worktree, `-n 2 --accept x` → exit 1, with "only the landing lane accepts…", before collection; `history.jsonl` unchanged. In a scratch clone's main tree, a worker was killed during a `-n 2 --accept` run: `accepted.json` and `history.jsonl` were byte-equal afterwards. That run hung, though (F1).
5. **The allowance is narrow.** Met (EXECUTED in a scratch clone). With `-p iniconfig` (C1), both serial and `-n 2` runs were RED "steered from outside the judge: plugin iniconfig from …/site-packages/iniconfig/__init__.py". A clean `-n 2` run gave `foreign []` with `JudgeScheduling`.
6. **The refusals.** Met (EXECUTED; 15 probes in a scratch clone, each with its own progress folder and latest path). Each of these exited 1 with one stderr line naming the option and "spec 052", and wrote 0 files: `-f`, `--looponfail`, `-n 2 --tx popen`, `-n 2 --dist loadgroup`, `--dist worksteal`, `--rsyncdir tests` (with and without `-n`), `-n 2 --px popen`, `--dist load` (alone and with `-n 0`), `-n logical`, `--maxschedchunk 1`, `--no-loadscope-reorder`, `-d`, and `PYTEST_ADDOPTS="--tx popen"` with `-n 2`.
   - **The hook wrapper is correct.** READ against xdist 3.8.0. xdist's `pytest_cmdline_main` is `tryfirst` and rewrites `-n` into `--tx`. Looponfail's is a plain impl. A `wrapper=True` impl runs before every non-wrapper impl, whatever the registration order. So the raw options are read before xdist's rewrite, both under `-p harness.plugin` (loaded before the entry points) and under `tests/conftest.py` (loaded after them).
   - **The refusal lands in time.** It is returned by the plugin's own `tryfirst` impl, which always runs before looponfail's plain impl.
   - **It fails closed.** If some later wrapper rewrote `tx` first, every `-n` run would be refused loudly. Nothing would pass silently.
   - **Workers are skipped** by `workerinput`. That is required, since a worker inherits `tx = [popen…]`.
7. **The scopes.** Met. The self-tests pass (READ, and they ran in both full runs). `pytest_xdist_make_scheduler` is the judge's (`meta.scheduler` `JudgeScheduling`), and the node ids are equal between the records (EXECUTED).
8. **Every goal check passes alone.** Met per the builder's census (322 node ids: 320 pass, 2 blocked; READ). I re-ran the five changed checks alone in a fresh process: all pass (EXECUTED).
9. **The surveys.** Met (READ).
10. **The zips folder from many processes.** Met. The self-test passes. I re-ran the pre-build `race.py` against the new `judge_zips` in a scratch clone: 8 cold processes × 5 trials gave 40/40 "ok", exactly one `zips-<sha>-v2` folder each trial, and no work folder left (EXECUTED).
11. **Full judge, serial against parallel.** Met. My pair is above, and the builder's two pairs agree with it (READ).
12. **Green.** Met. Both full runs exit 0. They are red only by `judge changed`, which the lane accepts with `--accept-judge`.

**The five fixed checks against their stand-ins** (EXECUTED; each check alone in a scratch clone, the file restored and compared byte for byte after):

| stand-in | result |
|---|---|
| base: all five checks (both params of the trapped check) | pass |
| `test_a_call_without_a_root_shares_nothing` without the warm-up | **fail**: `assert [PosixPath('/….lock')] == []` |
| `test_a_trapped_call_without_a_root_is_removed[busy]` and `[sleeping]`, warm-up after the redirect (as before) | **fail**, both: the same `.lock` assertion |
| door check without the count seam (`stop_at = count()` removed) | **fail**: `['in the door…the door\n'] == ['in the door…None b'']` |
| tool check without the count seam | **pass**, after the real 60 s deadline (62 s) |
| tool check with the bound broken (`_Bounded._ended` → `None`) | **fail**: `subprocess.TimeoutExpired` at the 120 s fail-safe |

## Findings, most severe first

1. **A worker that dies hangs the judge, or leaves a `pass` record; Decision 14 does not hold** (`plugin.py:359`, `plugin.py:675`, `plugin.py:520`). Medium. EXECUTED.
   - **Defect.** Under the judge's scheduler, every non-upstream node id is its own LoadScope scope. When a worker dies, xdist re-queues its unfinished scopes, *the crashed check included*, and starts a replacement worker.
   - **Failure, hang.** A check that kills its process gives:
     - with the harness under `-n 2`: 4 hangs in 9 runs of a check that crashes once, and a check that crashes every time hung for 17 min before I killed it;
     - with the same per-node-id scope and no harness: 3 hangs in 4 runs;
     - with plain `--dist loadscope`: 0 hangs in 4 runs;
     - with plain `--dist load`: 0 hangs in 4 runs.

     On real checks, killing one worker of `-n 2 tests/checks/test_v1_2_hostile_guest.py --accept` in a scratch clone hung the run for more than 240 s, until I killed the controller. A serial run in the same state dies at once.
   - **Failure, a masked crash.** When the run does finish, the crashed check runs again on another worker. The re-run's record replaces nothing, because the crash report carried none, so `node not in state.records` is false and the check is never made `fail`. The record reads `test_crash_once: pass`, and the scoreboard says `8/8 pass · 0 fail` with exit 1.
     - Acceptance is still refused: `green` needs exit 0 (EXECUTED: 0 files written).
     - But `sameness.py` compares records only. So a crashed reviewer's `-n` record compares equal to the lane's serial one, and lane step 3a would count that landing as clean.
   - **No check.** Decision 14 has no self-test (AGENTS rule 3).
   - **What works.** With `--max-worker-restart 0`, 4 of 4 runs ended at once with `test_crash_once: fail, worker crashed: worker 'gw0' crashed while running…`. That is exactly Decision 14.
   - **Fix.**
     - When distributing, set `maxworkerrestart` to 0, and refuse any other value. This is a change to Decision 7's table: `--max-worker-restart` is now listed as "allowed".
     - Let a crash win: a node with a crash report stays `fail` even if a later record arrives.
     - Add a self-test: a check that kills its worker once gives `fail` "worker crashed", and the run ends under a fail-safe. Today's plugin is the stand-in it must fail against.

2. **A plugin registered at collection time escapes the foreign-plugin check under `-n`** (`plugin.py:667` and `plugin.py:708`). Medium. EXECUTED.
   - **Defect.** `foreign_steering` runs only in the controller, and the controller never collects. A conftest that pytest loads only during collection (any conftest below an argument's directory, other than `test*` folders) is loaded on the workers only. So is any plugin such a conftest registers in `pytest_configure`.
   - **Failure.** I put `tests/unit/zz052/inner/conftest.py`, registering an object plugin of a foreign module, into a scratch clone. Then I ran `tests/unit/zz052 tests/checks/test_rules.py::test_known_gaps_are_well_formed`:
     - serially: exit 1, `RED: steered from outside the judge: plugin steer052`;
     - with `-n 2`: exit 0, `meta.foreign []`;
     - `sameness.py` between the two records: exit 0.

     That is a verdict that differs between serial and parallel, which is exactly what this spec says cannot happen. The likelihood is low: the conftest is a judged file, so it moves the judge hash and shows in a diff. The lane's serial run would catch it.
   - **Fix.**
     - Each worker computes `foreign_steering(config)` in its `pytest_sessionfinish` and hands it over in `workeroutput`. The controller takes the union.
     - Have `sameness.differences` compare `meta.foreign` (the one verdict-bearing `meta` field), or say in writing why not.
     - Add a self-test with a collection-time conftest.

3. **The progress README still says a pass's reason is compared** (`context/progress/README.md:115`: "a pass's, gap's or blocked check's reason"). Low. READ.
   - Decision 12 changed in the build, and `sameness.py` compares `reason` for `gap` and `blocked` only.
   - Failure: a lane operator expects a note difference to stop a landing, and it never will. Fix the sentence.
   - Decision 12's original text in the spec also still lists `pass`. The appended note corrects it, but striking the word would be clearer.

4. **The tool-deadline check: the count seam is not what keeps it from depending on speed.** Low; no code change required. EXECUTED.
   - **The check still tests what it claims.** With the bound broken, it fails at the 120 s fail-safe. Without the seam, it passes after the real 60 s deadline (62 s).
   - **Its remaining dependence on time** is the one Decision 9 accepts for the door check too: the guest must reach `tools.block()` within 60 s of wall time. The fix that removes the original 3 s bet is `deadline_s` going from 3 to 60. The seam brings the run time from about 60 s down to about 1 s, which keeps the check far from its 120 s fail-safe.
   - **Verdict on §4.9:** it holds as well as spec 032's accepted pattern does. No fix is needed. The spec's Reason could say so plainly.
   - **The evidence was missing.** The builder's log for this stand-in (`build-052/standin-test_a_tool_blocking_past_the_deadline_is_answered.log`) holds only `command not found: timeout`. The landing notes' claim had no run behind it. This review's run supplies it. Cite it, or re-run it.

5. **`judge_zips` swallows any `OSError` once a home exists** (`zips.py:247`). Note. READ.
   - The spec named `FileExistsError`, `ENOTEMPTY` and `EEXIST`. The code catches every `OSError` and re-raises only if no home exists. This is harmless: a home that exists is complete, since it can only come from one atomic rename. A build error in a losing process simply defers to the winner.
   - Windows, by reasoning (INFERRED):
     - `os.rename` onto an existing folder raises `FileExistsError`, which is caught and uses the winner's folder.
     - Nothing renames or removes a published home.
     - The work folder's files are closed before the rename.
     - An antivirus handle could make the rename raise `PermissionError` with no home yet. That raises, and the run fails visibly, never wrongly. It could also leave a work folder behind after `rmtree(ignore_errors=True)`, which nothing reads.

6. **Decision 12's change (pass notes not compared) is sound.** Note. EXECUTED and READ.
   - The 9 pass notes are 8 fuel figures and one scan count. The difference seen is fuel residual: 17 instructions in 1.38 million.
   - `plugin.py` already says a note "is never compared, so it is no metric". The ratchet never compares notes, so comparing them here would be stricter than the verdict itself.
   - Statuses, facts, `bytes`, `passes` and fuel within tolerance still carry every verdict.

## Other checks

- **The dependency (§4.13).** Correct (READ).
  - `pytest-xdist==3.8.0` is in `dev`, with its reason in both `pyproject.toml` and Decision 1.
  - The `uv.lock` diff adds exactly `execnet` 2.1.2 and `pytest-xdist` 3.8.0 (URLs, SHA-256s), plus the dev-group lines.
  - Installed versions: `xdist.__version__` 3.8.0, `execnet` 2.1.2 (EXECUTED).
- **The lane stays serial.**
  - AGENTS.md rule 6a: "judges the exact commit in the main tree **serially**".
  - Progress README step 3: "**Serially**". Its new step 3a and the "Ten clean landings" rule match Decision 11 (READ).
  - Nothing enforces serial acceptance in code. That is by design (Decision 11): the README and AGENTS carry it.
- **Scheduler and node ids.** The node-id sets are equal in all paired records. `-k` and node-id selections judge the same (EXECUTED above). Self-test shapes cover both (READ).

## Constitution checks

- §4.9: no check times anything. The tool and door checks keep a 60 s margin, as spec 032's pattern does (finding 4). The new unit tests use timeouts only as fail-safes.
- §4.13: holds.
- §5.6: I re-ran the counted tests (both full judges, the probes and the stand-ins).
- §5.7: not build-class. The lane accepts with `--accept-judge`.
- §7: nothing tripped. No upstream patch, no artifact in git.

## Verdict

**Lands once F1 and F2 are fixed.** Both are small. Each needs its self-test and this review's probe as its stand-in. F3 is a one-line documentation fix, which should go in with them. F4 to F6 need no change; F4's evidence should be cited in the landing notes.

One line: the parallel judge gives the serial answer on a healthy run, but a dead worker hangs it or hides the crash, and a plugin loaded only at collection escapes the foreign-plugin check, so fix F1 and F2 first.

## Addendum to the build review of 052: the disposition re-checked

- **Date:** 2026-10-18
- **Reviewer:** Claude Opus 5.5, the same fresh reviewer. I wrote none of the fixes.
- **Reviewed:** `17a9d16..000f656`. `ae30779` holds the code and self-tests; `000f656` holds the spec's revisions and Disposition. I read `disposition.md` beside this file.
- **Re-ran** (EXECUTED, darwin-arm64, frozen set `build/sets/s-c4190ca065ada03a`, `uv run` only). Records are in the session scratchpad, under `052-confirm/`. Probes ran in a scratch clone of `000f656`. No tracked file was edited in any real tree.

```
uv run pytest  (000f656)
  wasi_python v1: 340/354 pass · 12 gap · 2 blocked · 0 fail   (unit suite 1101/1103, 2 skipped)
  ratchet vs 5f56591135: lost 0 · absent 0 · unrun 0 · gained 0 · grew 0 · judge changed: pyproject.toml, tests/checks/test_v1_2_hostile_guest.py, tests/checks/test_v1_4_embedding.py and 7 more
  1441 passed, 4 skipped, 12 xfailed in 498.63s; exit 0; wall 535 s, CPU 704 s
uv run pytest -n 3  (000f656)
  wasi_python v1: 340/354 pass · 12 gap · 2 blocked · 0 fail   (unit suite 1101/1103, 2 skipped)
  ratchet vs 5f56591135: (the same line)
  1441 passed, 4 skipped, 12 xfailed in 208.38s; exit 0; wall 208 s, CPU 808 s
uv run python tests/harness/sameness.py serial.json n3.json   → nothing printed, exit 0
```

About the two records:
- The judge hash is `6d9421bb5a84` in both. `dirty` is false in both.
- `meta.foreign` is `[]` in both.
- The parallel record says `workers 3` and `JudgeScheduling`.
- The 4 new unit tests ran in both: 1101 against 1097.
- Wall times are benchmark facts only. Other agents' judges were running at the same time.

## The original findings

- **F1: fixed for the case it named.** EXECUTED, in a scratch clone of `000f656`, with the crash suite from the review. No `--max-worker-restart` was given, so the judge set it to 0.
  - A check that crashes once, under `-n 2`: 6 of 6 runs ended in about 2 s. Each recorded `test_crash_once: fail` "worker crashed", exited 1, and wrote 0 progress files. Before the fix, 4 of 9 runs hung.
  - The same run with `--accept` was refused, with 0 files written.
  - `--max-worker-restart 1` is refused with one line before anything runs. `--max-worker-restart=0` judges.
  - READ, xdist 3.8.0 `dsession.py:250-262`: with restarts at 0, the first crash calls `triggershutdown()`. Any scopes put back in the queue then become `unrun`, which is honest and red. The run cannot hang waiting for a replacement worker.
  - "A crash outranks a later record" is correct. The crash report always comes before any re-run.
  - But when *every* worker dies, the crashed check vanishes from the record. See F7.
- **F2: fixed for the case it named.** EXECUTED, in a scratch clone: a conftest loaded only during collection registers a foreign plugin. Serial and `-n 2` both exit 1 with `foreign ['plugin steer052 (steer052)']`, and `sameness` exits 0. The new allowance has a hole. See F8.
- **F3: fixed.** READ: the progress README's line, Decision 12, and `sameness.py`'s docstring.
- **F4: answered.** The reason is now cited in Decision 9.
- **F5 and F6: the answers are accepted.**

## New findings

7. **When every worker dies, the crashed check and the unrun checks vanish from the record** (`plugin.py`, `Controller.pytest_testnodedown` and the Decision 14 loop in `pytest_sessionfinish`). Low. EXECUTED.
   - **Why.** A goal check is made `fail` or `unrun` only if it is in `state.areas`. Areas reach the controller only in the `workeroutput` of a worker that finished. When no worker finishes, `areas` stays empty. Then the crash cannot become a `fail`, and nothing can become `unrun`.
   - **Failure.**
     - `-n 1`, a check that crashes once: the record holds 6 checks, the scoreboard says `6/6 pass · 0 fail`, and the exit code is 1. `test_crash_once`, and `test_crash_always` after it, are absent. `collected_files` is `[]`.
     - `-n 2` with a crash on each worker: also `6/6 pass · 0 fail`, exit 1, and both crashed checks absent.
   - **Why it is only Low.** It is not a wrong verdict:
     - the exit code is 1, so `--accept` is refused;
     - against a baseline, the ratchet calls the missing checks `absent`, which is red;
     - `sameness` against a serial record prints "only in the first record" and the `collected_files` difference, exit 1.

     But the scoreboard says "0 fail" for a run in which a worker died, which is what F1 set out to end. And Decision 14 and the progress README say "the check … is `fail`".
   - **Fix (small), either of these:**
     - let `_carry` send the node's area on its setup report as well, so a crashed check is known whatever happens to its worker;
     - or, when the judge distributed and no worker handed its collection over, add a red line, "no worker finished: the record is incomplete".

     Either way, add a third parameter to `test_a_dead_workers_check_fails_and_the_run_ends` with `-n 1`. Or answer in writing why the record may stay as it is.

8. **The `__channelexec__` allowance matches by name, so a worker-only spoof passes in parallel and fails serially** (`plugin.py` `foreign_steering`). Low. EXECUTED.
   - **Failure.** A collection-time conftest registers an object of a class named `WorkerInteractor` whose `__module__` it sets to `"__channelexec__"`:
     - serially: exit 1, `foreign ['plugin spoof052 (__channelexec__)']`;
     - with `-n 2`: exit 0, `foreign []`;
     - `sameness` catches it: exit 1.

     It is deliberate. It is visible in the judged conftest's diff and in the judge hash, and the lane's serial run is red on it. But it is the one plugin check whose answer depends on the number of cores. The existing `_pytest…` prefix rule can be spoofed too, but it gives the same answer in both modes.
   - **Fix (one line).** Also require `Path(type(plugin).__init__.__code__.co_filename).resolve().is_relative_to(xdist_dir)`. On a real worker that path is `…/site-packages/xdist/remote.py` (EXECUTED with a probe conftest under `-n 1`). execnet compiles the source under its real file name, so the genuine interactor passes and a class defined in a conftest does not.
   - Otherwise the allowance is narrow, as claimed. It applies on a worker only, at the locked xdist version only, and only to this one qualified name.

## Verdict

**Reopened: F7 (Low) and F8 (Low).** Neither lets a parallel run accept or come out greener than the lane's serial run: the exit code, the ratchet and `sameness` each catch both. Each fix is a few lines, with one more self-test parameter. A written answer would also close them under the review rules, but F7's "0 fail" scoreboard for a dead worker is worth the fix. F1 to F6 are confirmed closed.

One line: the fixes hold for the cases named, but a run in which every worker dies still shows "0 fail", and the worker allowance matches by name, so fix or answer F7 and F8 before the lane.

## Second addendum to the build review of 052: F7 and F8 re-checked

- **Date:** 2026-10-18
- **Reviewer:** Claude Opus 5.5, the same fresh reviewer. I wrote none of the fixes.
- **Reviewed:** `000f656..b0efb05`. `f770945` holds the code and self-tests; `b0efb05` holds the Disposition rows and a progress README line.
- **Re-ran** (EXECUTED, darwin-arm64, frozen set `build/sets/s-c4190ca065ada03a`, `uv run` only). Records are in the session scratchpad, under `052-confirm2/`. Probes ran in a scratch clone of `b0efb05`. No tracked file was edited in any real tree.

```
uv run pytest -n 3  (b0efb05)
  wasi_python v1: 340/354 pass · 12 gap · 2 blocked · 0 fail   (unit suite 1104/1106, 2 skipped)
  ratchet vs 5f56591135: lost 0 · absent 0 · unrun 0 · gained 0 · grew 0 · judge changed: pyproject.toml, tests/checks/test_v1_2_hostile_guest.py, tests/checks/test_v1_4_embedding.py and 7 more
  1444 passed, 4 skipped, 12 xfailed in 229.62s; exit 0; wall 230 s, CPU 846 s
uv run pytest  (b0efb05, serial)
  wasi_python v1: 340/354 pass · 12 gap · 2 blocked · 0 fail   (unit suite 1104/1106, 2 skipped)
  ratchet vs 5f56591135: (the same line)
  1444 passed, 4 skipped, 12 xfailed in 514.43s; exit 0; wall 550 s, CPU 715 s
uv run python tests/harness/sameness.py serial.json n3.json   → nothing printed, exit 0
```

About the two records:
- The judge hash is `85898d12ae42` in both, which matches the builder's. `dirty` is false in both.
- `meta.foreign` is `[]` in both.
- The parallel record says `workers 3` and `JudgeScheduling`.
- Wall times are benchmark facts only. Other agents' judges were running at the same time.

## F7: fixed

EXECUTED with the crash suite from the first review. No restart option was given.

| case | result |
|---|---|
| `-n 2`, a check crashes once (3 runs) | `test_crash_once` is `fail` "worker crashed"; `7/8 pass · 1 fail`; exit 1; 0 files |
| `-n 1`, crashes once (2 runs) | `fail` "worker crashed"; `6/7 · 1 fail`; RED "no worker handed its collection over: the record is incomplete"; exit 1 |
| `-n 2`, a crash on each worker (2 runs) | both crashed checks `fail` "worker crashed"; `6/8 · 2 fail`; the same RED line |
| `-n 1`, crashing always | `fail`, plus the RED line; the check that never started is absent, and the RED line says so |
| `-n 2 --accept`, a crash on each worker | refused; 0 files written |

READ:
- The area rides on the setup report, so the controller knows a check's area before its call runs.
- A crash during setup, before that report arrives, gets its own RED line, "a worker crashed while running …".
- Normal runs are unchanged: the full judges agree, and `sameness` exits 0.

## F8: fixed against what it named

EXECUTED. Each probe is a conftest loaded only during collection, run serially and with `-n 2`.

| conftest | serial | `-n 2` | `sameness` |
|---|---|---|---|
| registers a foreign plugin | exit 1, foreign | exit 1, foreign | 0 |
| a class *named* `WorkerInteractor`, `__module__ = "__channelexec__"` | exit 1, foreign | exit 1, foreign | 0 |
| the same, but with `__init__` borrowed from `xdist.remote.WorkerInteractor` | exit 1, foreign | exit 0, `[]` | 1 |

**Note (no change required).** The third row passes on a worker, because the borrowed code object's file really is `xdist/remote.py`.
- Adding `type(plugin).__init__.__module__ == "__channelexec__"` would block that borrow: the borrowed function's module is `xdist.remote`. But a code object compiled under a forged file name would still pass.
- Past this point it is an arms race against a hostile judged conftest. Such a conftest can patch `foreign_steering` itself, or behave differently on `PYTEST_XDIST_WORKER`, whatever the number of cores.
- It is deliberate forgery, and it is caught three ways: in the judge-hash diff, by `sameness`, and by the lane's serial run.
- F8's finding was a match "by name alone". That is closed. The builder may add the one-line `__module__` check if they like; it is not a condition.

## Verdict

**Confirmed.** F1 to F8 are closed, and the two full judges on `b0efb05` give the same answer.

One line: a dead worker now always fails its check or turns the run red, the worker allowance checks where its code came from, and serial and `-n 3` agree at judge hash `85898d12ae42`.
