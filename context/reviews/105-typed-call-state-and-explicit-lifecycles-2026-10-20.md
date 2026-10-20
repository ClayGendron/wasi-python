# Review of 105 — Typed call state, explicit lifecycles, and a type checker in the judge

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude), not the builder; the build review (the pre-build review is
  `105-typed-call-state-and-explicit-lifecycles-spec-2026-10-20.md`).
- **Reviewed:** `3133f18..7618b48` on `spec/105-typed-call-state-and-explicit-lifecycles` in the
  worktree `/home/user/wt/105`: `7de0416` (the checks first), `0944ead` (the source change),
  `7618b48` (the Status line and the landing notes); 29 files, +1,431 −447 by `git diff --stat`
  (+1,747 with the spec's notes). Stacked on 104's reviewed tip `3133f18` (`/home/user/wt/104` is on
  `550d79f`, that tip plus 104's review commit, which touches only `context/`; its code is
  `3133f18`'s). Time box: about 60 minutes, as the brief asked (a parallel-safe entry whose diff
  rewrites the runner's two lifecycles earns more than the 25).
- **Run:** none of its own, by the chain's rule: 102 to 107 land as one wave with one dispatch of
  the release workflow on the final tip (criterion 8; the owner, 2026-10-20). The counted tests
  were re-run locally: the fast tier on three cores against the frozen `v0.1.0a7` set, and the
  node ids below.
- **Re-ran** (every command in `/home/user/wt/105` on `7618b48` with
  `WASI_PYTHON_ARTIFACTS=/home/user/wasi_python/build/baseline-a7/set/wasi-python-0.1.0a7`, the
  machine's `build/fast-tier.lock` held for the tier and removed after; outputs in `build/105/`,
  git-ignored):
  - `uv run pytest -m "not slow" -n 3 -q -p no:cacheprovider` → **83 failed, 2427 passed, 52
    skipped in 287.30s**, exit 1 (`build/105/review-fast.log`; the record copied to
    `build/105/review.json`). The 83 are exactly the chain baseline's
    `build/baseline-a7/failing-nodes.txt` (`diff` of the sorted node ids: equal). **The two Ctrl-C
    rows passed.**
  - `uv run python tests/harness/sameness.py /home/user/wt/104/build/104/built.json
    build/105/review.json --claims build/105/claims.toml` → `note: explained by claims: 105 3`,
    exit 0, nothing else.
  - `uv run python tests/harness/sameness.py /home/user/wasi_python/build/baseline-a7/baseline.json
    build/105/review.json --claims build/105/claims-chain.toml` → `note: explained by claims:
    102 4 · 103 3 · 104 4 · 105 3`, exit 0, nothing else.
  - `uv run pytest tests/checks/test_rules.py -k mypy -q -p no:cacheprovider` → 1 passed in 4.45 s.
  - `uv run pytest tests/unit/test_lifecycles.py -q -p no:cacheprovider` → 49 passed in 0.37 s.
  - `uv run mypy --strict src/wasi_python` → **Found 8 errors in 1 file**, all `mounts.py`
    (`type-arg` 1, `union-attr` 2, `no-any-return` 4, `arg-type` 1); the bare `uv run mypy` the
    same 8 lines; `uv run mypy --platform win32` → 22 errors in 5 files; `uv run mypy --version` →
    1.19.1, the version `uv.lock` pins (`+184 −0`, `pyproject.toml` `+11 −0`).
  - `uv run ruff check src tests recipes/guest` → All checks passed; `uv run ruff format --check
    src tests recipes/guest` → 146 + 2 files already formatted.
  - `uv run pytest "tests/checks/test_v1_2_hostile_guest.py::test_ctrl_c_stops_a_computing_guest"
    -q -p no:cacheprovider` → 2 passed in 1.32 s; again → 2 passed in 1.36 s; the same on 104's
    tip in `/home/user/wt/104` → 2 passed in 1.42 s.
  - `uv run pytest tests/checks/test_v1_2_hostile_guest.py -m "not slow" -n 3 -q
    -p no:cacheprovider` → **4 failed, 148 passed, 1 skipped in 130.90s**
    (`build/105/review-stress-105.log`): the four are the baseline's (`test_dup_is_refused…` and
    `test_the_string_hash_is_siphash13`, both modes); the two Ctrl-C rows passed. Load average
    2.4 before, 7.0 after.
  - A probe of the join backstop (finding 1), a script in the reviewer's scratchpad, on both
    trees: 105 "still looping after 3 s | raised: RuntimeError | ended: False"; the base
    "returned | raised: None | ended: True".
  - The greps of criteria 2, 3 and 7 (below).

## Acceptance criteria against evidence

1. **The checks exist and were seen failing first** — met. EXECUTED: `build/105/mypy-base-linux.txt`
   has 83 `error:` lines and `mypy-base-win32.txt` 97 (the base's own counts, restated, as the
   criterion allows); `seen-failing-mypy.txt` shows the rules check red on the base;
   `seen-failing-units.txt` shows the lifecycle file and the rewritten stand-ins red on the base
   (`'_State' object has no attribute 'phase'`, `module 'wasi_python._home' has no attribute
   '_HomePhase'`, `'dict' object has no attribute 'memory_bytes'`); `exhaustiveness-red.txt`
   shows the three exhaustiveness and three liveness rows red with `LIMBO` added. READ: the
   three lines The problem names are in the base run at their moved places. The one-count-on-
   three-systems half waits on the chain's dispatch (criterion 8); the platform pin makes the
   Windows shard's run the linux one.
2. **The call is typed** — met. READ: `_CheckedCall` in `_call.py` is `@dataclass(frozen=True,
   slots=True)` with the Design's 19 fields in its order, none defaulted; `_checked` builds it
   by keyword from `_Limits`, `_Inputs`, `_ToolArgs` and `_Places`; `home: _Home` and `loop`
   are parameters of `_run_checked`, `_call`, `_call_deferred`, `_instance` and `_tool_host`;
   `_home_of` is gone; `run_async` makes its event before `_checked` and passes it as `cancel`.
   EXECUTED: `test_a_checked_call_is_frozen_with_every_field_required` passes; the `replace`
   grep finds `os.replace` and `__init__.py`'s docstring example only.
3. **No read with a default, no flag** — met. EXECUTED on `7618b48`: the `.get`/`checked[` grep
   over `src/wasi_python` finds nothing; the flags grep over `_sessions.py`, `_home.py`,
   `runner.py` and `_call.py` finds nothing (over the package it finds `tools.py`'s own
   `abandoned`, as the builder says: `ToolOutcome.abandoned` is public and `_Slot.abandoned` is
   the bound's); `\.state\b` in `_home.py` finds nothing; the tests grep finds only
   `test_tools.py:158` and `test_plugin.py:231, 409`, a protocol answer and a metrics dict, not
   calls. `tests/harness/calls.py` is the one hand-built call.
4. **Both machines are whole** — met. EXECUTED: 49 rows pass; the tables in the code match the
   Design's rows one for one (`_SESSION_TABLE` 12, `_GUEST_TABLE` 7, `_HOME_TABLE` 13, READ
   against the spec); the exhaustiveness rows drive every pair of the product and assert every
   member has a row; the refused pairs raise a `RuntimeError` naming phase and event. One
   backstop outside the tables is not whole: finding 1.
5. **No verdict moves** — met. EXECUTED: the fast tier's 83 failures are the baseline's; both
   sameness runs print only the claim note, exit 0; the hostile-guest probe's check
   (`test_an_abandoned_turn_keeps_its_session_busy`) passes, its golden lines unchanged.
6. **The judge is green** — met. EXECUTED: ruff clean on `src`, `tests` and `recipes/guest`;
   `uv.lock` is additive (184 lines, none removed; mypy and its four dependencies by hash); the
   bare `uv run mypy` gives the check's 8 `mounts.py` lines.
7. **The numbers, EXECUTED** — met after a write-in (finding 2). EXECUTED on `7618b48`:
   annotations 287 (the notes' 287), `type: ignore` 19 (the notes' 19, each new one with a code
   and a reason on its line), `_State` 31 attributes (`self.` names in `__init__`: 31),
   `tools.py` 2,450 and `mounts.py` 2,213 lines (`ALLOWED` holds both), the mypy check 3.74 s
   cold and 0.28 s warm recorded as a fact and asserted nowhere. The `Any` token counts in the
   notes were stale (400, not 424; `tools.py` 115, not 139): written in.
8. **The release** — pending by design: none of this specification's; the chain's one dispatch
   on its final tip. The builder dispatched no run and says so; this review's **Run** line says
   the same.

## The diff against §4 and §7, and the claim list against the diff

- **Behaviour kept (READ, every setter).** `_claim`, `_release_claim`, `_mark`, `_claim_ending`,
  `_end_session`, `_shutdown_applies`, `_session_turn`, `_abandon_turn`, `_drive_turn`,
  `_open_session`'s `except`, `close`, `_reap`, `_end_dropped`, `_sessions_at_exit` and
  `_release_session` each map onto the Design's rows as its "mapping, function by function"
  says. Two readings checked: a turn cancelled before any guest code (`_drive_turn` returns
  `ran=False`, so `_turn_inside` sets no `cause` and `_session_turn` raises no guest event: the
  guest stays `UNTOUCHED` and the next turn's `ENTER` still runs `_initialize`); and
  `_end_dropped`'s `phase is OPEN` says what `not busy and _mark(...)` said (every other phase
  either has `ended` set or a turn). `_release_session` decrements only in `ENDING`, so a failed
  opening (`OPENING → RELEASED`) never decrements, as `counted=False` made it not; the unit row
  covers both. The home's `done` is a property over `_NO_GUEST`; `_session_turn`'s
  `_GUEST_MAY_RUN` is the complement, so "forced out while the guest thread runs" reads the
  same set as `not home.done` did. Decision 3's sub-slice window (`serve()` no longer clears
  `serving`; `call()` sees `raised` on its next poll) holds as written: `serve()`'s `except`
  calls `self.stop(e)` before anything else.
- **The claim list against the diff.** The judge files the diff touches: `test_rules.py` (one
  new check), `harness/calls.py` (new), `test_lifecycles.py` (new), `test_async_tools.py`,
  `test_runner_calls.py`, `test_runner_inputs.py`, `test_runner_limits.py`,
  `test_runner_sessions.py`, `test_runner_threads.py`, `test_runner_tools.py`,
  `test_v1_4_embedding.py`, `test_v1_4_public_api.py`, `test_v1_2_hostile_guest.py`,
  `pyproject.toml`, `uv.lock`. Every one is in the "as built" claim list (the builder added
  `test_runner_calls.py` there, difference 7). `claims.toml`: `new` the rules check and the
  unit file, `units = 49`; sameness explains exactly three differences by it. No row changed
  and unclaimed. `tests/public_api.txt`, `CHANGELOG.md`, `README.md` and the roadmap are
  untouched (the CHANGELOG line is proposed in the notes for the lane to write, as 104 did by
  its brief; no reserved follow-up needs a roadmap line: the per-platform type check is a
  recourse conditional on the owner, Decision 5).
- **The differences from the spec's text** (16 in the notes, READ against the spec): each has a
  reason the spec would accept. The ones that change a signature: `_State(checked, wt)` (the
  state is whole at construction); `_tool_host`'s `home: _Home | None` with the stand-ins
  passing `None` (a `_Home()` on the test's thread serves no one, so the embedding fuel checks
  failed with it: EXECUTED by the builder, and the session's `_arm`, `_session_tool_host` and
  `_turn_inside` take `home: _Home` as the spec says); `_in_context` for the closer (a partial of
  `Context.run` fails its `ParamSpec`); the `_Done` end mark; `Host` widened to what
  `_door_answer` already accepted. `tools.py` held at exactly 2,450, 103's ceiling, by a
  `_Json` alias and a rewritten `number`: the alias is the cause of finding 2's miscount.
- **Code speaks for itself.** READ over every added line of `src/` and `tests/`: the spec,
  review and finding citations on added lines (`(F3)`, `(F7)`, `(C1)`, `(spec 078, Decision
  14)`, `(the build review's F1)`, …) are carry-overs on rewritten lines that carried them on
  the base; the new code (the three enums and their tables, `_move`, `_move_guest`,
  `_Home._move`, `_CheckedCall`, `_ToolArgs`, `_Limits`, `_Inputs`, `_Places`, `calls.py`,
  `test_lifecycles.py`, the rules check) adds none. `UNTYPED`'s value is a reason in words.
  `pyproject.toml` names spec 105 in two comments beside neighbours that name 028 and 052; it
  is not a file the rule lists.
- **The self-check list.** Every item is checked or excluded with a reason (CI: the chain's
  rule; CHANGELOG: the lane's; growth: none). Nothing unchecked to rank.

## Findings, most severe first

1. **`_join_guest`'s backstop loops forever on a home already in `DONE`** (`src/wasi_python/_home.py:371-377`,
   the "backstop" branch) — the branch raises `LOST` (or `CANCEL`) through the table whatever
   the phase, and `(DONE, LOST)` is refused, so the `RuntimeError` is caught by the loop's
   `except BaseException`, kept as `home.raised`, and the wait starts over: the home thread
   polls `ended` every `_GUEST_SLICE` for ever. The base wrote `"cancelled"` and set `ended`
   from any state and returned. Grade **Medium**: Decision 3's guarantee for the backstop
   ("every reader sees 'no guest thread' either way, so the verdicts are the same") is not
   evidenced in `DONE`, and the probe shows the opposite verdict.
   Failure: a guest thread that dies inside its own `finally` after `self._move(_HomeEvent.END)`
   and before `self.ended.set()` (a trace hook raising there, an asynchronous exception an
   embedder injects; nothing the runner itself raises, since the steps are guarded) → phase
   `DONE`, `ended` clear, `is_alive()` false → on 105 the call never returns; on the base it
   returned. EXECUTED with the probe above: 105 "still looping after 3 s | raised: RuntimeError
   | ended: False"; the base "returned". The window is narrow and the death pathological, but
   the backstop exists for pathological deaths (its own comment: "a body ended without saying
   so"), and this is the one phase it no longer covers.
   Fix text (the builder's; two lines and one row): in the backstop, move only from a phase a
   guest may run in, and set `ended` in every case:
   ```python
   if not home.ended.is_set():
       if home.phase in _GUEST_MAY_RUN:  # a body never taken, or one that never reported
           cancel = home.phase is _HomePhase.STARTING
           home._move(_HomeEvent.CANCEL if cancel else _HomeEvent.LOST)
       home.ended.set()  # DONE already: the body moved the phase and died before its last line
   ```
   and a fourth tuple `(HP.DONE, HP.DONE)` in
   `test_the_join_backstop_cancels_a_start_and_loses_a_run`. The `_Home` docstring's invariant
   2 can keep its wording (`DONE` precedes `ended.is_set()` by the steps' run) with the words
   "and the join sets it if the body never does". Evidence that closes it: the row green on
   the fix, or a written answer in Decision 3 that the window cannot be entered.
2. **The landing notes' `Any` token counts were measured before the `_Json` alias** (the spec's
   landing notes, "The numbers") — the notes said 432 → 424 and `tools.py` 108 → 139; the
   committed code (`0944ead`, unchanged by `7618b48`) has **400** and **115** (EXECUTED with
   the notes' own command; every other module's count matches the notes; the annotation counts
   317 → 287 match). The alias names `dict[str, Any]` once for 23 spellings, 24 tokens fewer
   than the builder's `measurements-after.txt`, so the spec's INFERRED 30 to 60 fewer tokens
   did come true (32). Grade **Low**, context only: **written in by the reviewer as `51eba18`**
   (the exact text; the builder's `build/105/measurements-after.txt` stays as it was, a
   git-ignored file).
3. **Note: two dead writes in the hostile-guest child programs.** `tests/checks/test_v1_2_hostile_guest.py:2944`
   and `:3144` still write `self.serving = True` in stand-in `serve`s; a `_Home` has no slots,
   so the write makes an attribute nothing reads. Named by the builder (difference 14) and
   harmless; `test_runner_threads.py`'s two were deleted. For the tests' cleanup, not this
   specification's round.
4. **Note: the two Ctrl-C rows are not this build's.** `test_ctrl_c_stops_a_computing_guest[default]`
   and `[default-turn]` failed in the builder's three records (two runs on this tree, one on
   104's tip, all "the child did not end within its limit", a 120 s `subprocess.run` timeout)
   when the machine's load passed 7. For this review they **passed in every run**: the full fast
   tier at `-n 3`, twice alone on 105's tip, once alone on 104's tip, and the hostile-guest file
   at `-n 3` on 105's tip (load 2.4 to 7.0). READ, the path they take: `default` is `run()` with
   `host=` and `while True: pass`, `default-turn` the same as a session's turn; a simulated
   SIGINT lands in the home thread's `serve()`, `stop(e)` records it, the epoch callback reads
   `call.home.raised` (`_epoch_answer`, unchanged) and stops the guest at the next `CANCEL_TICKS`
   poll; the body's `finally` puts `_DONE`, moves `END`, sets `ended`; `_join_guest` returns.
   What 105 adds on that path is three dictionary lookups under the home's lock (`START`,
   `TAKE`, `END`) and, for the turn, the session's `FAILED`, `MARK`, `TURN_RETURNED` and
   `CLAIM_ENDING` in the one lock hold that held the flag writes; no wait, no poll, no thread
   is added, and `STOPPING` is left by the turn's own thread as `busy=False` was. The child's
   end waits on nothing 105 changed. The verdict moved with the machine, not the branch; the
   lane's run on the wave's tip and the chain's dispatch decide it.
5. **Note: the spec's refused pairs are refused.** EXECUTED through the unit rows and READ:
   `_claim_ending` in `OPEN`, `TURN` or `STOPPING` and `_move` from `OPENING` by anything but
   `OPENED` or `RELEASED` raise; `_start_guest` on a `CANCELLED` home raises before any thread
   is made. No production path reaches them (every caller of `_claim_ending` tests the phase or
   follows a `_mark` that returned True; `_sessions` registers a state only after `OPENED`).

## Constitution checks

- §4 constraints: §4.2 (pins): `mypy==1.19.1` and its four dependencies by hash in `uv.lock`,
  nothing else changed in it; the check runs the venv's own binary, as ruff's does. §4.9
  (operations, not wall-clock): the mypy check's seconds are recorded as a fact and asserted
  nowhere. §4.13 (a dependency with its reason): the reason sentence is in `pyproject.toml`
  and Decision 5. §4.14 (a stacked build): on 104's reviewed tip, the base in the Status line;
  no other branch. "Artifacts never live in git": `build/.mypy_cache` under the ignored
  `build/`; no artifact byte moves. "Code speaks for itself": held for the new code (above).
  Spec 063 (packages): no package added. The module size ceiling (103): `tools.py` held at
  2,450 exactly, `mounts.py` 2,213.
- §7 never-do list: nothing tripped. The judge is not weakened: the allowlist can only shrink
  (an entry with no error left is a finding, which also makes the allowance a canary for an
  unparsed mypy output); no golden moves (the probe prints the same `True`/`False`); no
  `tests/known_gaps.toml`, allowance or `context/progress/` edit; no `--accept` by the builder
  or by this review; nothing built, nothing pushed.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. The join backstop in `DONE` — _the builder's: fixed in <commit> / answered because <reason>._
2. The `Any` counts — written in by the reviewer as `51eba18`; confirmed.
3. to 5. Notes; no action in this round.

## Verdict

Lands once finding 1 is fixed (the two-line guard in `_join_guest`'s backstop and its unit row,
the fast tier re-run on the fixed commit) or answered in writing in Decision 3; everything else
is met, the fast tier is the baseline's 83 failures exactly, both sameness runs are clean, and
the two Ctrl-C rows are the machine's, not this branch's.
