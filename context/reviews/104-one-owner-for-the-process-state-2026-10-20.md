# Review of 104 — One owner for the process's state, and the test seams move off module globals

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (build reviewer for the chain 102–107)
- **Reviewed:** `538e831..3133f18` on `spec/104-one-owner-for-the-process-state` in the worktree
  `/home/user/wt/104` (four commits: `a73b0fe` the checks first, `1f959c2` the code, `e96f1b9` the
  Status line and the landing notes, `3133f18` the rebase record), stacked on 103's reviewed tip
  `538e831`. The specification read at the same tip. Time box: 45 minutes (a judge change in a
  stacked chain; the fast tier re-run in full), used in full.
- **Run:** none; the chain's one dispatch on its final tip stands for criterion 9 (the owner's rule
  for the chain, the specification's "For the lane"). The builder's fast tier is `build/104/fast.log`.
- **Re-ran:** `WASI_PYTHON_ARTIFACTS=/home/user/wasi_python/build/baseline-a7/set/wasi-python-0.1.0a7
  uv run pytest -m "not slow" -n 3 -q -p no:cacheprovider` (under `build/fast-tier.lock`, output
  `build/104/review-fast.log`, record `build/104/review.json`) → **83 failed, 2377 passed, 52
  skipped in 287.35s**, exit 1; the 83 node ids are the chain baseline's `failing-nodes.txt`
  byte-for-byte (`diff`, EXECUTED). `uv run python tests/harness/sameness.py
  /home/user/wt/103/build/103/built.json build/104/review.json --claims build/104/claims.toml` →
  `note: explained by claims: 104 4`, exit 0; the same against
  `/home/user/wasi_python/build/baseline-a7/baseline.json` with `--claims
  build/104/claims-chain.toml` → `note: explained by claims: 102 4 · 103 3 · 104 4`, exit 0; against
  the builder's `build/104/built.json` with no claims → nothing printed, exit 0 (the two records
  agree). `uv run python -I build/104/lock_order_pkg.py src/wasi_python
  _process,_limits,_platform,_artifacts,_engines,_private_dirs,_zip,_places,_home,_call,_sessions,runner`
  → identical to `build/104/lock_order-on-tip.txt` (`diff`): the four pairs and `stop`. Probes by
  node id: `uv run pytest tests/unit/test_runner_package.py tests/unit/test_process.py
  tests/unit/test_scan.py tests/checks/test_rules.py -q -p no:cacheprovider` → 1 failed
  (`test_version_states_the_platform_semantics`, the baseline's), 265 passed, 3 skipped; the four
  real-fork checks (`test_runner_tools.py::test_the_fork_hook_resets_the_tool_thread_count`,
  `test_v1_4_embedding.py::test_a_forked_child_is_refused`,
  `::test_a_forked_child_leaves_the_parents_zip_folder`,
  `test_runner_async.py::test_a_forked_child_of_a_used_runner_is_refused`) → 4 passed; `PYTHONPATH=src:tests
  uv run --python 3.11 --no-project --with pytest python -m pytest tests/unit/test_process.py -q` →
  6 passed on 3.11.17, 6 passed on 3.12.3. A standalone load of `_process.py` (stdlib only, no
  harness) under `uv run --python {3.11,3.12,3.13} --no-project python -I`: `reset_after_fork()`
  renews 15 attributes of the kinds `lock`, `RLock`, `Condition`, `SimpleQueue`, none the same
  object, and every `RENEW` factory's result is its key's type, on all three. `uv run ruff check
  src tests` → All checks passed; `uv run ruff format --check src tests` → 144 files already
  formatted. `grep -nE '^\s*global ' src/wasi_python/*.py` → none. The specification's criterion-5
  grep, widened to 103's module names, over `tests/` → nothing but `_try_lock` (a function seam)
  and `api.py`'s two module-name strings. `git diff 538e831..3133f18 -- tests/public_api.txt` →
  empty. `wc -l src/wasi_python/mounts.py` → 2213.

## Acceptance criteria against evidence
1. `_process.py` holds every name of Decision 1's table, each typed in `__init__`; the grep outside
   `_process.py` matches only constants — met, EXECUTED: every row of the table has an attribute in
   `_Process.__init__` (READ, `src/wasi_python/_process.py:98-181`, groups A to J plus the two
   release callables); the criterion's grep over the tip gives the landing notes' list exactly
   (upper-case constants, `_UNSET`, `_DONE`, `_WAKE`, `_CLOSER`, regexes, the ffi's three, mounts'
   five, `_Listing`, dunders), no lock, no container.
2. Both rules checks seen failing first, with counts, and passing now; their unit rows pass — met:
   the base counts (14 locks, 38 mutables) are READ in `build/104/seen-failing-full.txt` with the
   per-module split; on the tip both checks and both scanner rows pass (EXECUTED, probe 1).
3. The fork check of Decision 3 passes with at least four names and the `RENEW` row; the three
   real-fork checks pass with their reads moved; 103's check 1 retired and named in the
   `--accept-judge` reason; a 3.11 run recorded — met, EXECUTED: `test_process.py` 6 passed on
   3.13, 3.11.17 and 3.12.3; the four real-fork node ids 4 passed; `FORK_HOOK` reads
   `process().tool_threads_lock` and `NO_FORK` prints `process().fork_used, process().forked`
   (READ); 103's check 1 and its tables are gone from `tests/unit/test_runner_package.py` and the
   flag text names the retirement (READ).
4. No `global` statement remains — met, EXECUTED (none).
5. Every test line of Decision 4's table changed; the grep finds nothing — met, EXECUTED: the
   widened grep finds only `_try_lock` (a function, matched by the `[a-z_]*_lock` alternative) and
   `api.py`'s module names; every seam the tests set goes through `process().observers` (six fields
   under `monkeypatch.setattr(process().observers, …)`, three set in subprocess programs as
   `process().observers.<field> = …`; EXECUTED grep) or an attribute of `process()`.
6. Sameness: only the claimed rows differ; no fuel row moves; no pass lost — met, EXECUTED (the
   three sameness runs above, exit 0; the 83 failures are the baseline's).
7. Thread-safety unchanged; the corrected scanner finds the four pairs and no other on both trees —
   met: EXECUTED on the tip (identical to the builder's output); the base output is READ
   (`build/104/lock_order-on-base.txt`, the same four pairs under 103's names). Independently
   (EXECUTED): every `with` over a lock in the twelve runner modules, normalised to the new names,
   is the same multiset on `538e831` and on the tip (20 over the engines lock, among them the one
   the base spells across three lines in `_Private.remove`; 4 over the ticker's condition; the
   rest one for one), and no local is bound to a lock anywhere.
8. The judge: fast tier green against the baseline's 83, ruff clean, `--accept-judge` named — met,
   EXECUTED (above). The builder ran `-n 3`, not the criterion's `-n 6`, by the machine's budget;
   the verdicts are what the criterion asks for.
9. The release: one dispatch on the chain's final tip — not yet run, by the chain's rule; its run id
   is owed to the landing notes when the chain's tip is dispatched (INFERRED from the owner's rule
   quoted in the specification; nothing here can be executed before the chain's tip exists).

On the brief's particular points:
- (a) `reset_after_fork` against `_after_fork_in_child` at `538e831` (`runner.py:533-567`, READ),
  field by field: the twelve locks and the condition the hook re-made (`_pool_lock`, `_live_lock`,
  `_held_lock`, `_stack_size_lock`, `_tool_threads_lock`, `_zip_lock`, `_lock`,
  `_epoch_callback_lock`, `_outputs_lock` as an `RLock`, `_epoch_ticker._cond`, `_sessions_lock`,
  `_closers_lock`) and the queue it re-made (`_reaper_queue`) are renewed by `RENEW` (15 objects,
  EXECUTED: those thirteen plus `warnings_lock` and `defaults_lock`, the two extra the
  specification states); the stack window (restore then clear), `tool_threads_running = 0`,
  `zips = {}`, `compiling = {}`, pool `None`/size 0, `pools.clear()`, `live.clear()`, the
  ticker's thread `None` and active 0 with its count kept, `sessions` a new `WeakSet`,
  `closers.clear()`, `dropped.clear()`, reaper thread `None` and stop `False` with `hooked` kept,
  `counts["sessions_open"] = 0`, and `forked = True` under `fork_used`: each has its line
  (`_process.py:189-213`), and nothing else is assigned. The method takes no lock. `RENEW` is
  keyed by exact type and works on 3.11, 3.12 and 3.13 (EXECUTED, both the standalone probe and
  the builder's pytest command). The registrations happen at the import of `_process.py`
  (`:238-240`), which `__init__.py` imports first; before, at the import of `runner.py`, also
  during the package's import: import time in both cases, once.
- (b) `release_at_exit` (`_process.py:215-227`) is the old `_release` (`runner.py:750-762` at
  `538e831`, READ) in the same order: zips, warnings, `check_modules`, the five linker tables,
  `modules`, `engines`; the two callables are bound at the zip and private-folder modules' import
  (`_zip.py:285`, `_private_dirs.py:541`, READ) with no-op defaults; `_sessions_at_exit` keeps its
  first-session registration (`_sessions.py:257-259`), so the three exit hooks keep their order.
- (c) The lock order: the scanner re-run on the tip gives Decision 6's four pairs and no other
  (EXECUTED); the docstring (`_process.py:10-28`) says the five items of Decision 6 in that form.
- (d) No module-level hook remains in `src/` (EXECUTED grep: only `_default_drive_folder` and its
  one read); `_Observers` is `@dataclass(slots=True)` and its refusal of a misspelt field is a unit
  row (EXECUTED). The allowance list: my own tally over `tests/unit/*.py` of
  `monkeypatch.setattr(<runner module>, "_name", …)` gives 38 lines and 19 distinct names, the
  notes' list exactly; the checks' three the same. Other spellings exist that the builder's grep
  could not read (finding 1).
- (e) The two placement scanners (`tests/harness/scan.py:1889-2010`, READ) walk the module body and
  every module-level class body, read `Assign` and `AnnAssign`, pair tuple targets with tuple
  values; the lock scanner has no exception; the mutable scanner's exceptions are `__all__`, an
  upper-case name over a dict, set or list display, and `_fields_` in a class body: the
  specification's three and no more. Neither carries a name allowance, so none can go stale;
  `ALLOWED["mounts.py"]` is 2213 and the file is 2213 lines (EXECUTED).
- (f) 103's check 1 retired with its seven tables and helpers; checks 2 to 4 pass with `_process`
  first in `ORDER` and `process` in `SENTINELS` (EXECUTED, probe 1); `RUNNER_MODULES` is `ORDER`
  less `_wasmtime_ffi`; `LATE` gains `mounts.py`'s binding of the owner (READ).
- (g) `tests/public_api.txt` unchanged (EXECUTED); `api.py`'s `RUNNER_FILES` gains `_process.py`
  first (READ).
- (h) The rebase: `_patched` builds its alias map per file and `_is_unchanging` recurses into tuple
  and frozenset elements on the tip (`tests/unit/test_runner_package.py:144-149, 180`, READ); the
  one named conflict's resolution keeps both and the retirement.
- (i) New lines: `_process.py`, `test_process.py`, the two rules checks, the scanners and their
  rows name no specification, memo, review, finding or `context/` path (EXECUTED grep over the
  diff's added lines). Five modified lines carry a citation that stood on the line they replace
  (`spec 076, Decision 1`; `Decision 9`; `spec 055`, `spec 078`; `the build review, N1`;
  `spec 084`), each with its removed counterpart in the diff: carried, not new; 106 and 108 clear
  them.
- (j) Sameness prints nothing outside the claims (above). The claim: `new` the two rules checks and
  `tests/unit/test_process.py`, `units = 7` (six rows in `test_process.py` plus two in
  `test_scan.py` less the retired one), against the diff: exact.
- (k) The eleven stated differences, each checked against the tree: six rows (READ, the file);
  `self._process = process()` in `_Files.__init__` with `LATE` saying so (READ); the name
  `_default_drive_folder` (READ); the tables deleted with the check (READ, the diff);
  `lock_order_pkg.py` with its module set (EXECUTED); the tuple pairing and its row (READ);
  `monkeypatch.undo()` at `test_v1_2_hostile_guest.py:2769, 2800, 2805` (READ); `from . import
  _process` in `__init__.py` (READ); the counts 30/50 and 19/38 (EXECUTED, the tally above);
  no `global` (EXECUTED); `_epoch_ticker.count()` returning `process().ticker_count` (READ,
  `_engines.py:223-225`). Each is sound and written down. The commit subjects and bodies name no
  model; the trailers are the attribution lines every commit on main carries.

## Findings, most severe first
1. **The allowance list for 106 and 107 misses the seams replaced by spellings the builder's grep
   did not read** (`context/specifications/104-one-owner-for-the-process-state.md`, "The allowance
   list for 106 and 107"; `tests/unit/test_runner_sweep.py:340, 740, 759`;
   `tests/checks/test_v1_2_hostile_guest.py:3133, 3138`; `tests/unit/test_runner_threads.py:215,
   220`) — Low. The list counts `monkeypatch.setattr(<module>, "_name", …)` lines; three lines use
   the fixture under the name `m` (`m.setattr(_private_dirs, "_remove_tree", …)`, so `_remove_tree`
   is 6 lines, not 5, and `m.setattr(_private_dirs, "_REMOVE_BUDGET", 10_000, raising=False)` twice,
   a name the list lacks), and three programs or tests assign by name
   (`_sessions._drive_turn, wasmtime.Store.close = drive_turn, close`, `_sessions._abandon_turn =
   abandon`, `_home._Box = LateBox` and its restore), two of which (`_drive_turn`, `_abandon_turn`,
   and the class `_Box`) the list lacks (`_call._drive` and `_home._join_guest`, assigned the same
   way, are listed). All seven lines are on the base unchanged; this specification moves none of
   them, and Decision 4 defines the list by the `monkeypatch.setattr` form, so the code is right
   and the list is short. 107's check reads `<module>._name = …` too (READ, Decision 4), so a list
   handed over short would make 107's first run red for names no one decided.
   Failure: 107 seeds its allowance from this list → `test_runner_sweep.py:740`,
   `test_v1_2_hostile_guest.py:3133, 3138` and `test_runner_threads.py:215` fail its check with no
   closer named.
   Fix text (touches only `context/`): under "The allowance list for 106 and 107", "`_remove_tree`
   (6 lines: five as `monkeypatch.setattr`, one as `m.setattr`)"; a bullet "Constants and classes
   the unit files replace: `_REMOVE_BUDGET` (2 lines, `m.setattr`, `test_runner_sweep.py`), `_Box`
   (`test_runner_threads.py`, assigned by name) — 106's platform seam or 107's list"; a bullet
   "Assigned by name in the hostile-guest programs, for 105's typed call or 106's protocol:
   `_drive_turn`, `_abandon_turn` (`test_v1_2_hostile_guest.py:3133, 3138`), beside `_drive` and
   `_join_guest` already listed"; and the sentence "The tally reads both spellings of the fixture
   (`monkeypatch.` and `m.`) and the `<module>._name = …` form, as 107's check will."
2. **Two self-check items are unchecked** (the specification, "The builder's self-check": the CI
   run on this commit, and the CHANGELOG line) — Low. Each carries its reason in writing: the
   chain's one dispatch on its final tip stands for criterion 9 (the owner's rule), and the brief
   kept `CHANGELOG.md` for the lane, with the line written out under "For the lane". Nothing to
   change in code.
   Failure: none in this tree; the chain's tip is dispatched without this specification's run id
   being written back, or the lane lands without the line.
   Fix text (touches only `context/`): the lane adds the CHANGELOG line as written under the
   unreleased section at the landing, and the chain's run id is written into these landing notes
   under "CI" when the final tip's dispatch is read.

Notes, not findings: the mutable scanner's `_callee` keys on a call's last name, so a module-level
binding of `text.count(…)` or `items.count(…)` would be reported as `(count)`; no such binding
exists on the tip, and a false hit is loud, not silent. An upper-case display that the code later
mutates passes the scanner, as the pre-build review noted; a naming convention, not a check.

## Constitution checks
- §4.3, §4.4 (one target, two imports): untouched; no guest byte changes.
- §4.6 (the artifact set is the product): no artifact byte, pin or recipe changes; the wheel's
  Python only.
- §4.9 (tests count): the new rows count renewed objects, ids, fields and scanner hits; the fork
  checks read values in a child; no time is read.
- §4.10 (claims carry evidence): every number in the landing notes is labelled and reproduced here
  where it could be (the fast tier, sameness, the lock order, the counts, the 3.11 and 3.12 runs);
  finding 1 is a count made by a narrower grep than the sentence it supports.
- §4.13 (uv, ruff, pytest): clean; no dependency added.
- §4.14 (git): a worktree on `spec/104-…` stacked on 103's reviewed tip, the base named in the
  Status line and the rebase recorded with its one conflict; no push, no tag.
- §4.15 (safe by default): no default, limit or channel changes; the fork refusal keeps `fork_used`
  and sets `forked` as before.
- §5.2 (every choice decided): the specification decides each one and says why; the shape check
  passes in the fast tier.
- §5.6 (review): the pre-build review's seven findings have a Disposition each, and the build
  matches it (the `RENEW` table, the corrected lock order, the slotted dataclass, the two release
  callables with defaults, the counts); this build review is by a different agent.
- §7 never-do list: nothing tripped; no patch, no fetch, no copy, no commit beyond the branch's own,
  no number reported that was not run.

## Disposition (filled in by the author, then confirmed by the reviewer)
1. The allowance list misses the seams replaced by other spellings — fixed in the specification's
   landing notes ("The allowance list for 106 and 107"), in the review's own fix text: `_remove_tree`
   is 6 lines (five `monkeypatch.setattr`, one `m.setattr`); a bullet for the constant and the class
   the unit files replace (`_REMOVE_BUDGET`, 2 lines by `m.setattr`; `_Box`, assigned by name and
   restored); a bullet for the two functions the hostile-guest programs assign by name
   (`_drive_turn`, `_abandon_turn`), beside `_drive` and `_join_guest`; and the sentence that the
   tally reads both spellings of the fixture and the `<module>._name = …` form, as 107's check
   will. No line of code changes: each is on the base as it is.
2. Two self-check items unchecked — answered in writing in the landing notes: the CHANGELOG line is
   the integrator's (its text stands under "For the lane"; the lane adds it under the unreleased
   section at the landing), and the chain's run id goes into the notes under "CI" when the final
   tip's dispatch is read; both self-check items and the "CI" bullet say so.

## Verdict
Lands: every criterion but the chain's own dispatch is met on evidence re-run here, the fork
reset and the exit release are the old hooks field for field with the two stated extra renewals,
no lock is taken in a new place, and the two Lows are write-ins to `context/` that need no further
round.
