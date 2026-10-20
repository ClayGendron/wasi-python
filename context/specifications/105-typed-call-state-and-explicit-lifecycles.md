# 105 — Typed call state, explicit lifecycles, and a type checker in the judge

- **Status:** **drafted 2026-10-20** on `claude/gallant-ride-9nxxmn` from main `5feb7e9` (the memo's
  commit `a9064a2` is on this branch; committed as `46fa9fc`); **reviewed before build** the same
  day (`../reviews/105-typed-call-state-and-explicit-lifecycles-spec-2026-10-20.md`, verdict "does
  not land yet": one High, two Mediums, four Lows); **revised against all seven findings** (see
  *Disposition of the pre-build review*), awaiting the reviewer's confirmation (AGENTS.md rule 8:
  it changes the runner's code). It is **stacked on 104's reviewed tip** (constitution §4.14), the fourth entry
  of the chain 102 → 103 → 104 → 105 → 106 → 107; its base commit is written into this line when
  104 is reviewed, and it rebases onto main, or the wave's tip, when 104 lands. A different agent
  reviews the build.
- **Date:** 2026-10-20
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe** (§5.7): `src/wasi_python/` only, the unit checks and their stand-ins,
  one rules check in `tests/checks/test_rules.py`, one probe line in a hostile-guest check's child
  program, `pyproject.toml` and `uv.lock`, `CHANGELOG.md` and the roadmap. It **changes no line of
  `tests/public_api.txt`** and no artifact byte. It **adds one dev dependency: `mypy==1.19.1`, for
  the type check the judge runs over `src/wasi_python` (Decision 5; constitution §4.13)**. And a
  judge change: a new rules check, new unit rows, stand-ins rewritten; the lane accepts with
  `--accept-judge`.
- **Depends on:** 104 (one owner for the process's state, on 103's split and 102's engine seam).
  The module names below are 103's (its Design table): `_limits`, `_places`, `_call`, `_home`,
  `_sessions`, `_engines`, `_wasmtime_ffi`, and the thin `runner.py` that keeps `_checked` and
  `_check_tools`; a function or a mutable of another module is reached as `_module.name` (103's
  rule). Landed: 055 (bounded sessions: the lifecycle
  `_State`'s flags encode, Decisions 7, 8, 9 and 13) and 078 (the runner runs each guest on a
  stack of its own: `_Home`, Decisions 2, 4 and 14), whose lifecycles this specification names
  without changing them. It meets 093 (one probe line, Decision 7).
- **Research it stands on:** `../research/2026-10-20-a-design-review-of-the-runner.md`, findings
  H3 (the call's state is an untyped dict; the session's lifecycle is ten flags) and M1 (no
  static type checking), and section 8 (the chain, the owner's four decisions). **The drafting
  run** (EXECUTED 2026-10-20 on this branch at `a9064a2`, Linux): one `mypy --strict` over
  `src/wasi_python` under mypy 1.19.1, its output in `build/105/mypy-strict.txt` (git-ignored); the
  counts below come from it and from `grep` over the same tree.

## The problem

Two things in the runner are true only by convention, and nothing checks them.

1. **A call's checked arguments travel as `dict[str, Any]`.** `_checked` returns a dict of 19
   keys with tools and 18 without (READ: `_check_limits` 4, `_check_inputs` 3, `cancel`,
   `_check_tools` 4 with tools and 3 without, `_check_places` 7). Three writes follow the check:
   `home`, by `_run_checked` (`c = {**c, "home": home}`); `tool_loop`, by `run_async`; and
   `checked["cancel"] = event`, by `run_async` at line 673, after it passed `None` as `cancel`. Readers use `c["fuel"]` in 7 places and `c.get("tools")` in 5, and
   the comments say why the `.get`s exist: "a hand-built `c` without it: no limit"
   (`_tool_host`), "one made here for a call built by hand (the judge's stand-ins)" (`_home_of`).
   Production code carries branches that only a test fixture's omission takes. A field spelled
   wrong is a `KeyError` at run time, under a guest, and no earlier.
2. **A session's lifecycle is eleven fields read together.** `_State` has 35 attributes (READ).
   Its life is encoded across `ended`, `outcome`, `busy`, `closing`, `done`, `turn_thread`,
   `ending_thread`, `called`, `sound`, `needs_initialize` and `counted`. Which combinations are
   legal is implicit in `_claim`, `_mark`, `_claim_ending`, `_end_session`, `_session_turn`,
   `_abandon_turn`, `close`, `_reap`, `_end_dropped` and `_sessions_at_exit`. `_Home` is the same
   in small: a `state` string with four values, plus `done`, `serving` and `abandoned`, written
   in five places under its lock. Each flag is careful and each closed a review finding. But a
   machine written as flags cannot be checked for completeness: nothing says that a turn's thread
   never claims an ending while a closer holds it, except that no path happens to do so.
3. **No type checker.** `src/wasi_python` has 424 `Any` tokens, 314 of them `: Any` or `-> Any`
   annotations (EXECUTED: `grep -oE '\bAny\b' -r src/wasi_python --include='*.py' | wc -l`, and
   `grep -oE '(: |-> )Any\b' …`; by file, runner.py 229 and 168, tools.py 108 and 74, mounts.py
   81 and 70, cli.py 6 and 2; the memo's 286 is READ, with no command beside it). `ruff` selects
   `E, F, I, UP, B` and no type rule. One run of `mypy --strict` finds **78 errors in 4 files**
   (EXECUTED): tools.py 36, runner.py 30, mounts.py 10, cli.py 3; by code, `type-arg` 37,
   `no-any-return` 14, `arg-type` 6, `assignment` 5, `union-attr` 4, `no-untyped-def` 4, and 8
   others. Three of them are not noise:
   - `runner.py:1020: Return value expected [return-value]`: a function declared to return a value
     has a bare `return`.
   - `runner.py:5974: Trying to assign name "atexit" that is not in "__slots__" of type
     "weakref.finalize" [misc]`: `Session.__init__` writes `self._finalizer.atexit = False`;
     CPython exposes `atexit` as a property on a slotted class, so the write works, and the
     checker cannot see that without a word from the code.
   - `tools.py:2002: Argument 1 to "_cancel_post" has incompatible type "_Post | None"; expected
     "_Post" [arg-type]`: a `None` the code excludes by an earlier branch, which the type does not
     record.

The memo's verdict holds: the embedder's side is designed with care; the maintainer's side is
held together by convention. This specification replaces three conventions with three things a
checker can refuse: a frozen dataclass, two transition tables, and `mypy --strict` in the judge.

## Decisions

### 1. `_CheckedCall`: a frozen dataclass of the 19 checked fields, every one required

`_checked` returns a `_CheckedCall` (`@dataclass(frozen=True, slots=True)`), with the field list
of the Design. Every field is typed and required: no default on any field, so a construction
that leaves one out is a `TypeError` at the construction, not a `KeyError` under a guest. Each
helper that fed the dict feeds a typed part instead: `_check_limits` returns a `_Limits`
NamedTuple, `_check_inputs` a `_Inputs`, `_check_tools` a `_ToolArgs`, `_check_places` a
`_Places`; `_checked` builds the one `_CheckedCall` from them, naming every field by keyword. The
dataclass is frozen so that a call's arguments, once checked, are never edited on the way down
(spec 049, Decision 2: a default is read once, when the call is made). `env` is a `dict` by
type and is never mutated after `_checked`; `argv` becomes a tuple.

**`home` and `tool_loop` are not fields.** Neither is an argument the embedder passed and the
runner checked; each is a binding the runner makes while it runs the call. Today both are glued
into the dict so that they ride along with it: `home` by `_run_checked` for `run` and
`run_async`, `tool_loop` by `run_async` only. A session never puts either into its `state.c`: its
turns and its ending each make a `_Home` of their own and pass it, and its loop, as parameters
(`_arm(state, kind, fuel, ticks, stop, output_bytes, loop, home)`). So the session's path already
has the honest shape, and this specification gives `run`'s path the same one:

- `_run_checked` makes the `_Home` and passes it down as a required `home: _Home` parameter of
  `_call`, `_call_deferred` and `_tool_host`; `_home_of` and its "a call built by hand" fallback
  are deleted. `_arm`'s and `_tool_host`'s `home` parameters lose their `None` defaults.
- `loop: asyncio.AbstractEventLoop | None` is a parameter of `_run_checked`, `_call`,
  `_call_deferred` and `_tool_host`: `run` passes `None`, `run_async` the running loop. This is
  the one `Optional` the design keeps, and it is an honest one: a call either has a caller's loop
  or runs tools on a private loop of its own (spec 053).

**The third late write goes away.** `run_async` makes its `threading.Event` before `_checked` and
passes it as `cancel`, which `_checked` validates as it validates `run`'s; the `_live`
registration of the event stays where it is. No production line calls `dataclasses.replace` on a
call (criterion 2): the frozen record has no escape hatch.

That is the whole answer to "without `Optional` soup": the two values that differ between a call
and a session are parameters at the places that differ, not optional fields on the shared
object.

**The stand-ins.** `tests/harness/calls.py` gains `BASE_CALL`, a `_CheckedCall` written out with
every field explicit (no limits, nothing granted: `fuel=None`, `deadline_s=None`,
`memory_bytes=None`, `output_bytes=None`, `argv=("-c", "pass")`, `env=None`, `stdin=None`,
`cancel=None`, `tools=None`, `gate=None`, `tool_calls=None`, `tool_request_bytes=None`,
`root=False`, `grants=()`, `mounts=()`, `import_path=()`, `import_serving=()`, `file_calls=None`,
`open_files=None`), and `checked_call(**fields)`, which is `dataclasses.replace(BASE_CALL,
**fields)`: an unknown name is `replace`'s own `TypeError`. **Every stand-in site today** (READ at `a9064a2`: the review's inventory plus one):
four hand-built dicts given to `_tool_host`, at `tests/unit/test_async_tools.py:350`,
`tests/unit/test_runner_tools.py:754` ("a hand-built call without the key: no byte limit"),
`tests/checks/test_v1_4_embedding.py:3358-3359` and `:4962`, each becomes
`_tool_host(checked_call(tools=(fn,), tool_calls=1000), None, None, None, _Home())`, and the
`_max_bytes is None` row at `test_runner_tools.py:755` asserts the explicit
`tool_request_bytes=None`; three reads of `_checked(...)` by key, the `checked()` helpers of
`test_runner_limits.py:121-125` and `test_runner_tools.py:716-725` and
`tests/checks/test_v1_4_public_api.py:373-374`, read the attribute; `test_runner_tools.py:162-168`
reads `_check_tools(...)` by key and compares it with a dict, and compares with a `_ToolArgs`;
`test_runner_limits.py:36-64` reads `_check_limits(...)` by key on five lines, and
`test_runner_inputs.py:38-148` reads `_check_inputs(...)` by key on eight (38 and 47 compare
`argv` with a list, which becomes a tuple; 148 compares the whole with a dict, which becomes an
`_Inputs`). The two checks files are in Scope and in the claim list. No production line reads a field with a default again: the acceptance grep
(criterion 3) holds it.

### 2. The session's lifecycle is one enum and one table; the interpreter's soundness is a second

**`_Phase`** has seven members: `OPENING`, `OPEN`, `TURN`, `STOPPING`, `MARKED`, `ENDING`, `ENDED`.
Read from the flag combinations today's functions produce (READ, every setter listed in the
Design), these are the states, no more:

- `OPENING`: `_State()` exists; `_open_session` is making the store. Not yet in `_sessions`;
  nothing can mark or claim it.
- `OPEN`: at rest, `ended is None`. A turn may be claimed; a bound may pass.
- `TURN`: a turn is claimed (today `busy`), by the thread `holder` names (today `turn_thread`).
- `STOPPING`: a turn runs and `ended` is set (today `busy` with `ended`): `closing` is set, the
  turn is being stopped, and its thread runs the ending at its return.
- `MARKED`: at rest, `ended` is set, no one has claimed the ending (today `ended` set, not
  `busy`, `ending_thread is None`, `done` not set). It is usually left in the same lock hold it
  was entered in (`_reap`, `_claim`, `close`); it rests only after an abandoned turn.
- `ENDING`: the ending is claimed (today `ending_thread` set), by `holder`: a thread ident, or
  `_CLOSER` while a closer thread is being started.
- `ENDED`: everything is released (today `done` set). Terminal.

**`_Event`** names what happens: `OPENED`, `CLAIM`, `RELEASE`, `MARK`, `TURN_RETURNED`,
`CLAIM_ENDING`, `TAKE_OVER`, `RELEASED`. **One function moves the phase**:

```python
def _move(state: _State, event: _Event, holder: int | None = None) -> _Phase:
    """Under `state.lock`. The table says where (phase, event) goes; a pair not in it is a
    RuntimeError naming both. Sets `holder`, `closing` (on entering STOPPING or MARKED) and
    `done` (on entering ENDED), so a wait handle can never disagree with the phase."""
```

The table is in the Design. The flags it replaces: `busy` (TURN or STOPPING), `turn_thread` and
`ending_thread` (one `holder: int | None`, since the two were never both set: every claim of an
ending requires that no turn runs, and a turn's thread clears its own claim before it claims the
ending), `counted` (a state is counted from `OPENED` until `_release_session` runs in `ENDING`;
a release in `OPENING`, the failed opening, never decrements, as today's `counted=False` made it
not). **`ended: str | None` and `outcome: str | None` stay as the recorded reasons**, and
`closing` and `done` stay as the wait handles the transition sets. `_mark` stays the one writer
of `ended`: it moves `OPEN → MARKED` or `TURN → STOPPING` and returns `True`; with `ended`
already set it returns `False` and raises no event, as today.

**`_Guest`** replaces `called`, `sound` and `needs_initialize`, which are not about the session's
life but about the interpreter inside its store: `UNTOUCHED` (no turn has called an export; the
`_initialize` export, if the instance has one, is still to call), `ENTERED` (a turn has called an
export and has not yet reported), `SOUND` (the last export returned: the interpreter may be
entered for Python's shutdown) and `UNSOUND` (the last export was unwound by a trap, an exit or a
stop, or the turn raised in the embedder's process, or it was abandoned). `needs_initialize` is
exactly `guest is UNTOUCHED and "_initialize" in exports` (READ: it is set from `exports` at the
opening and cleared at the first export call, which also sets `called`), so it is derived, not
stored. `_shutdown_applies` reads `guest is SOUND` where it read `called and sound and not
busy`; `not busy` is the invariant that `ENDING` holds no turn. Why a second enum and not one:
their product would be 28 members, 20 of them unreachable, and the two cross-invariants (an
`ENTERED` guest only in `TURN` or `STOPPING`; an `UNSOUND` guest only with `ended` set) are
shorter to state and to check than a 28-row table. The guest's event table is in the Design too.

**Behaviour does not change.** Every path in `_claim`, `_mark`, `_claim_ending`, `_end_session`,
`_session_turn`, `_abandon_turn`, `Session.close`, `_reap`, `_end_dropped` and `_sessions_at_exit`
maps onto a row; the Design shows the mapping function by function. Two pairs are refused that
today's code would silently accept and that no path reaches: `_claim_ending` on a state whose
`ended` is `None`, and `_move` from `OPENING` by anything but `OPENED` or `RELEASED`. Two
readings the mapping keeps as they are, named so the review does not think them new: a dropped
session that rests in `MARKED` after an abandoned turn is ended at exit, not by the reaper
(`_end_dropped`'s `_mark` returns `False`); and `_release_claim` from `STOPPING` (a queued
`run_async` turn cancelled after another thread's `close()` marked the session) goes to `MARKED`
with no claimant until exit. Both are spec 055's behaviour today, kept exactly; the second is a
reading, written here so a later specification can decide it with its own research.

### 3. `_Home`'s lifecycle is one enum and one table

**`_HomePhase`** has six members: `IDLE`, `STARTING`, `RUNNING`, `ABANDONED`, `CANCELLED`, `DONE`,
replacing `state` (`"idle"`, `"starting"`, `"running"`, `"cancelled"`), `done`, `serving` and
`abandoned`. The memo named five; `ABANDONED` is the sixth, because `abandoned` is not a flag
beside the state but a state: a guest thread lives and its home has left (spec 078, Decision 14),
which the body must know at its end, after it took the start (`steps` go to the guest thread
only then). `DONE` is distinct from `IDLE` so that a start is accepted only from a home that
never started or whose body ended, and a body's `end` only from a home whose body took the
start: today the body writes `"idle"` at its end, which nothing reads, so the two were one
string.

**`_HomeEvent`**: `START`, `TAKE`, `CANCEL`, `LEAVE`, `END`, `LOST`. The table is in the Design.
Derived facts: `done` is `phase in (IDLE, CANCELLED, DONE)`; `serving` is `phase in (STARTING,
RUNNING)`. `call()` raises `_Stopped` when `raised is not None or phase not in (STARTING,
RUNNING)`, where it tested `raised is not None or not serving`. The one difference is a window
shorter than a slice: today `serve()`'s `finally` clears `serving` when the loop leaves by an
exception, a few bytecodes before `_on_guest_thread`'s handler records that exception in
`raised`; the guest's `call()` polls once per `_GUEST_SLICE` and sees `raised` on its next poll.
No check can tell the two apart; the review reads this paragraph against `serve()` and
`_on_guest_thread`. `raised`, `thread`, `ended` (the Event), `steps`, `result`, `inbox`, `lock`,
`ident` and `watched` stay as they are.

`_join_guest`'s backstop (a dead thread whose body never reported) raises `CANCEL` in `STARTING`
and `LOST` in `RUNNING` or `ABANDONED`, where today it writes `"cancelled"` in every state: after
it, no body can run (the thread is dead) and every reader sees "no guest thread" either way, so
the verdicts are the same and the table says the truer thing. A refused pair worth naming:
`START` from `CANCELLED`. Nothing restarts a cancelled home today, and allowing it would let a
late body of the cancelled start take the new start as its own.

### 4. Both machines are checked whole, without a guest

`tests/unit/test_lifecycles.py` drives each table row by row on a bare `_State` or `_Home`:
set the phase, raise the event, assert the phase after and the derived facts (`closing`,
`done`, `holder`; `ended` the Event, `steps` handed or kept). An **exhaustiveness** row then
takes the product of the two enums and asserts that every `(phase, event)` pair is either in the
table or refused with a `RuntimeError` whose message names both, so a member added to either
enum without its rows turns the check red. A **liveness** row asserts that every member but the
initial one (`OPENING`; `IDLE`) is the target of some row, and every member but the terminal
ones (`ENDED`; `CANCELLED`) is the source of some row: no dead member. The guest enum gets the
same three rows. The existing session and home checks keep their behaviour rows and read the
phase where they read a flag (`test_runner_sessions.py`'s `_state()` helper sets `phase` instead
of `busy`; `test_runner_threads.py` asserts `home.phase is _HomePhase.CANCELLED` where it
asserted `home.state == "cancelled"`, and sets up the never-started thread with an explicit
`phase = STARTING` under the lock, as it set three fields).

### 5. mypy, not pyright; pinned exactly; a per-module allowlist that shrinks

**mypy**, for one decisive reason: the `pyright` wheel on PyPI is a wrapper that fetches a Node
runtime and the pyright npm package on first run, a download that is in neither `uv.lock` nor
`downloads/SHA256SUMS`. Constitution §4.2 says every tool is a URL plus a hash, verified before
use, and the judge is a tool. mypy is a wheel `uv.lock` pins by hash. One smaller reason: `--strict`
is one documented flag set, so "what the judge checks" is one word in the spec and in the check.
(A `mypy==1.19.1` line in `tests/jobs/oracle/uv.lock` is scipy's own dev-extra metadata, not a
pin of this repository's: the repository names no mypy today.)

**The dependency** (constitution §4.13): `mypy==1.19.1` in the dev group of `pyproject.toml`,
with the comment: *mypy type-checks `src/wasi_python` in the judge (spec 105, Decision 5);
pinned exactly, as pytest-xdist is, since a mypy release changes which lines are errors and the
check must give the same verdict on every machine and on CI.* `uv lock` records its wheels by
hash. The reason sentence of this Decision is the one §4.13 asks for.

**The configuration**, in `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.11"      # the floor requires-python names; one target on every host
platform = "linux"           # one platform's narrowing on every host (below)
strict = true
files = ["src/wasi_python"]
cache_dir = "build/.mypy_cache"   # build/ is git-ignored (AGENTS.md: artifacts never live in git)
```

so a bare `uv run mypy` and the judge's run say the same thing.

**One platform, as one Python version.** mypy narrows `sys.platform` for the host it runs on, so
the same tree gives a different error set per system: under `--platform win32` the run finds
**92 errors against 78** on linux and darwin (EXECUTED by the pre-build review: 6 `attr-defined`,
`resource.RLIMIT_NOFILE`, `RLIM_INFINITY`, `getrlimit` and `setrlimit` in `cli.py` and
`os.getuid`, `os.uname` in `runner.py`; and 8 `unused-ignore` in `runner.py`, since `--strict`
warns on an ignore the platform does not need). The judge compares one verdict across three
systems (criterion 5; the chain's one dispatch, criterion 8), and a red Windows line that is
neither growth nor G7 would stop the wave. So `platform = "linux"` pins the narrowing: every
host checks Linux's branches, as every host checks Python 3.11's. What is lost: the Windows-only
and darwin-only lines are parsed and their functions annotated, but their bodies are typed
against the linux stubs, so a wrong attribute inside a `sys.platform == "win32"` branch is not
an error here. The runner already keeps every such line behind a `sys.platform` guard (the
memo's M3; 106 gathers them into `_platform.py`), so the loss is bounded to those branches. The
recourse, if the owner wants them checked too: a later specification runs mypy once per
platform with `--platform` and keys the allowance by (module, platform), at three times the
wall time. wasmtime-py ships its types (READ:
the run resolved `Memory`, `Trap` and `WasmtimeError`), so no module needs
`ignore_missing_imports`.

**The check**, `tests/checks/test_rules.py::test_src_type_checks_under_mypy_strict`, runs
`Path(sys.executable).parent / "mypy"` as `_ruff` runs ruff (through `uv run pytest`, the venv's
own binary), with `--no-error-summary`, `cwd=paths.REPO`, and reads every `error:` line into
`(module, code)`. It fails on an error in a module not in the allowlist, on a mypy exit of 2 (a
crash or a configuration error), and on an **allowance with no error left**, so the list can only
shrink (the rule `tests/known_gaps.toml` follows). The allowlist is a dict in the check, module
to closer:

```python
UNTYPED = {"mounts.py": "spec 106"}  # module -> the specification that empties it
```

This specification **empties the allowlist for every module it touches**: the runner's package
as 103 and 104 left it (every module of it), `tools.py` (its 36 errors are 34 `type-arg`, one
`no-any-return`, one `no-untyped-call` and one `arg-type`, each a missing `[str, Any]` or a
narrowing the code does and the type does not say) and `cli.py` (3). **`mounts.py` is the one
entry, its closer 106**, which puts it behind a call-context protocol and moves the platform code
out of it; most of its 10 errors lie in the memory and trap seams 102 and 106 rewrite, so typing
them twice would be waste. A new `# type: ignore[code]` carries its code and a reason on the line;
the landing notes count them (12 lines today, EXECUTED by `grep -c 'type: ignore'`: runner.py 9,
mounts.py 2, cli.py 1; the memo's 9 is READ), as a fact.

**The `Any` count is a fact, not a ratchet.** Before: 424 tokens, 314 annotations (The problem).
After: the builder runs the same two commands and writes both numbers in the landing notes. This
specification removes the `Any` on the call (`c: dict[str, Any]` in 8 parameters, EXECUTED),
`_State`'s `c`, `wt`, `engine`, `store`, `exports`, `table`, `bounded`, `private_loop`, `context`
and `ending_home`, `_Either.home`, `_arm`'s `stop`, `loop` and `home`, `_tool_host`'s `cancel` and
`home`, and `_Home`'s `inbox`; INFERRED, between 30 and 60 fewer tokens. `--strict` allows an
explicit `Any`, so the check does not force the rest; what it forces is that every function is
annotated, every generic has its parameters, and no `Any` leaks out of a declared return. That is
the insurance M1 asked for, and it is why the check passes with 78 fixes rather than 314.

### 6. What this changes for the memo's chain

- **102 and 103** are below this specification: the module names in the Design are 103's
  (`_limits`, `_places`, `_call`, `_home`, `_sessions`, `_engines`, `_wasmtime_ffi`, and the thin
  `runner.py` that keeps `_checked` and `_check_tools`), and a name of another module is reached
  as `_module.name`, 103's rule. 103 owns the module size ceiling (its Decision 6). The type
  check runs over the package as 103 left it; errors 103's moves exposed are fixed here.
- **104** is the base: `_Process` is typed as 104 built it (no change to its shape), and the
  observers 104 moved off module globals are typed callables on it.
- **106** inherits the one allowance and the `.get`-free `mounts.py` seam: `_Files` will take a
  `_CallContext` whose methods are typed here already where the runner implements them.
- **107** owns the function-length ceiling and the test-seam allowance check, **104** the checks
  on where a module-level lock or mutable may live, **103** the module size ceiling; this
  specification adds none of those, only the type check, so its lines in `test_rules.py` are its
  own.

### 7. One probe line in spec 093's child program

`tests/checks/test_v1_2_hostile_guest.py` has a child program (spec 093) that prints `s._state.busy`
twice, and its expected lines are golden. The probe becomes `s._state.phase in (_Phase.TURN, _Phase.STOPPING)`
(imported from `_sessions`), which is what `busy` meant (Decision 2: a turn claimed, marked or
not), printed as the same `True`/`False`, so the expected lines and the verdict do not change,
and the probe keeps its meaning for a later program that marks before it abandons. It is a judge change by the letter (the check's text), named in
the `--accept-judge` reason, and no golden line moves.

## Intent

A call's state is a type the checker reads, a session's and a home's life are tables the judge
drives whole, and `mypy --strict` runs on every judge, so the next flag, field or path that is
missing is a red check before it is a bug under a guest. The embedder sees nothing: no public
name, no message, no verdict moves.

## Design

### The field list of `_CheckedCall` (in `_call.py`; `runner._checked` builds it)

`_Limits` lives in `_limits.py` beside `_check_limits`, `_Inputs` beside `_check_inputs` there,
`_Places` in `_places.py` beside `_check_places`, and `_ToolArgs` beside `_check_tools` in the
thin `runner.py` (103's table); `_CheckedCall` is defined in `_call.py`, which `runner.py`
imports, and every reader names it as `_call._CheckedCall`.

| field | type | from | checked by |
|---|---|---|---|
| `fuel` | `int \| None` | `_Limits` | `_integer_limit` (spec 013) |
| `deadline_s` | `float \| None` | `_Limits` | `_deadline_limit` |
| `memory_bytes` | `int \| None` | `_Limits` | `_integer_limit` |
| `output_bytes` | `int \| None` | `_Limits` | `_integer_limit` |
| `argv` | `tuple[str, ...]` | `_Inputs` | `_text` per item (spec 014) |
| `env` | `dict[str, str] \| None` | `_Inputs` | `_text` per key and value; never mutated after |
| `stdin` | `bytes \| None` | `_Inputs` | `_check_inputs` |
| `cancel` | `threading.Event \| None` | `_checked` | `isinstance` |
| `tools` | `tuple[Tool, ...] \| None` | `_ToolArgs` | `_check_tools` (spec 036) |
| `gate` | `Callable[[ToolCall], Any] \| None` | `_ToolArgs` | `_check_tools`; may be async (spec 053) |
| `tool_calls` | `int \| None` | `_ToolArgs` | `_integer_limit` |
| `tool_request_bytes` | `int \| None` | `_ToolArgs` | `_integer_limit` (spec 060) |
| `root` | `str \| bool \| None` | `_Places` | `_check_root` (spec 025: `False` none, `None` private, a path) |
| `grants` | `tuple[Grant, ...]` | `_Places` | `_check_grants` |
| `mounts` | `tuple[Mount, ...]` | `_Places` | `_check_mounts` (spec 032) |
| `import_path` | `tuple[str, ...]` | `_Places` | `_check_import_path` |
| `import_serving` | `tuple[int, ...]` | `_Places` | `_check_import_path` (the serving grant's index) |
| `file_calls` | `int \| None` | `_Places` | `_integer_limit` (spec 034) |
| `open_files` | `int \| None` | `_Places` | `_integer_limit` (spec 068) |

Nineteen fields, the dict's 19 keys with tools and 18 without; `_ToolArgs`'s no-tools value
carries `tool_request_bytes=None`, so the field is required and explicit where the dict had no
key (READ: `c["pending"]` in the grep is `_ctrl_c["pending"]`,
not a call's). Parameters, not fields: `home: _Home` and `loop: asyncio.AbstractEventLoop |
None` (Decision 1).

**The 19 `.get` reads, on 17 lines, and what each becomes** (EXECUTED, line numbers at `a9064a2`): `c.get("tools")`
at 2753, 4028, 5367, 5639 and 5750 → `checked.tools`; `c.get("mounts", ())` at 2877, 3029 and
5667 and `c.get("mounts")` at 5524 → `checked.mounts`; `c.get("import_path", ())` and `c.get("import_serving", ())` at 2763, 3023
and 5658 → the two fields; `c.get("tool_request_bytes")` at 4049 and 5399 → `checked.tool_request_bytes`;
`c.get("home")` at 2767 and 2845 → the `home` parameter (`_home_of` deleted); `c.get("tool_loop")`
at 4042 → the `loop` parameter. `_State.c` becomes `_State.checked: _CheckedCall` (not `call`: `_drive_turn`, `_turn_inside`
and `_arm` each hold a `_Call` named `call` beside it); `Session._turn_args` reads
`checked.fuel`, `checked.deadline_s`, `checked.output_bytes`.

### The session's table

`_Phase`: `OPENING`, `OPEN`, `TURN`, `STOPPING`, `MARKED`, `ENDING`, `ENDED`.
`_Event`: `OPENED`, `CLAIM`, `RELEASE`, `MARK`, `TURN_RETURNED`, `CLAIM_ENDING`, `TAKE_OVER`,
`RELEASED`.

| phase | event | → phase | holder after | who raises it |
|---|---|---|---|---|
| OPENING | OPENED | OPEN | None | `Session.__init__`, after `_open_session` returns |
| OPENING | RELEASED | ENDED | None | `_open_session`'s `except`, through `home.finish(release)`; no decrement |
| OPEN | CLAIM | TURN | the claimant | `Session._claim` |
| OPEN | MARK | MARKED | None | `_mark` (`_reap`, `_claim` expired, `_end_dropped`, `close`, `_sessions_at_exit`) |
| TURN | RELEASE | OPEN | None | `Session._release_claim` (a queued async turn never started) |
| TURN | MARK | STOPPING | the turn's thread | `_mark` (`close` from another thread or from inside the turn; `_sessions_at_exit`; `_session_turn`'s verdict; `_abandon_turn`) |
| TURN | TURN_RETURNED | OPEN | None | `_session_turn`, no cause and the lifetime not passed |
| STOPPING | RELEASE | MARKED | None | `_release_claim` after a `close()` marked the queued turn (a reading kept, Decision 2) |
| STOPPING | TURN_RETURNED | MARKED | None | `_session_turn` after its mark; `_abandon_turn` on the guest thread |
| MARKED | CLAIM_ENDING | ENDING | the claimant, or `_CLOSER` | `_claim_ending` (`_reap`, `_claim`, `_end_dropped`, `_sessions_at_exit`, `close`, `_session_turn`) |
| ENDING | TAKE_OVER | ENDING | the ending's thread | `_end_session` with `holder == owner` (a closer takes the `_CLOSER` claim) |
| ENDING | RELEASED | ENDED | None | `_end_session`'s `finish`, after `_release_session` and `outcome` |

Every other pair is refused. `_claim_ending` returns `False` without an event in `ENDING` and
`ENDED` (someone has it, or it is over), as today; from any other phase the table refuses, which
no path reaches. `_mark` raises `MARK` only when `ended is None`, so a second mark is never an
event. `_end_session` with no owner on a `MARKED` state claims it (`CLAIM_ENDING` with its own
ident), the branch today's code keeps for a direct call; no caller passes no owner (READ).

**The invariants `state.lock` protects** (the docstring of `_State`):

1. `ended is None` exactly in `OPENING`, `OPEN` and `TURN`; `closing.is_set()` exactly when
   `ended is not None`.
2. `holder` is the turn's thread in `TURN` and `STOPPING`, the ending's thread or `_CLOSER` in
   `ENDING`, and `None` otherwise. A turn and an ending are never held at once.
3. In `ENDING` and `ENDED` no turn's guest thread lives: `STOPPING` leaves only when the turn's
   own thread, or the abandoned turn's guest thread at its end, says so.
4. `done.is_set()` exactly in `ENDED`; `outcome` is written in the same lock hold that enters it.
5. `guest is ENTERED` only in `TURN` or `STOPPING`; `guest is UNSOUND` only with `ended` set.
6. `_counts["sessions_open"]` counts the states in `OPEN`, `TURN`, `STOPPING`, `MARKED` and
   `ENDING`; `_release_session` decrements once, in `ENDING`, never in `OPENING`.
7. `phase`, `holder`, `ended` and `outcome` are written under the lock, through `_move` and
   `_mark`, with one exception kept from today: `close()` in a forked child writes `ended` and
   `outcome` lock-free and moves nothing (the store is the parent's; no thread of the child
   touches it).

**The guest's table.** `_Guest`: `UNTOUCHED`, `ENTERED`, `SOUND`, `UNSOUND`. `_GuestEvent`:
`ENTER`, `RETURNED`, `UNWOUND`, `FAILED`.

| guest | event | → guest | who raises it |
|---|---|---|---|
| UNTOUCHED | ENTER | ENTERED | `_drive_turn`, after the cancel check, before `_initialize` and `turn` |
| SOUND | ENTER | ENTERED | the same, a later turn |
| ENTERED | RETURNED | SOUND | `_session_turn`: `done.returned` |
| ENTERED | UNWOUND | UNSOUND | `_session_turn`: `done.cause is not None` |
| UNTOUCHED, ENTERED, SOUND | FAILED | UNSOUND | `_session_turn`'s error row; `_abandon_turn` |

A turn cancelled before any guest code raises no guest event: the guest stays what it was
(today's "the session is untouched" row). `ENTER` from `UNSOUND` is refused: an unsound guest
always comes with `ended` set, so no turn follows. `_drive_turn`'s write of `ENTER` happens on
the turn's guest thread without the lock, as `called = True` does today; the phase protects it
(one turn at a time, invariant 5).

**The mapping, function by function** (today → with the machine; every line under
`state.lock` unless said):

- `Session.__init__`: `_State()` → phase `OPENING`; after `_open_session`, `counted = True`,
  `_sessions.add` → `OPENED`, `_sessions.add`.
- `_open_session`'s `except`: `home.finish(lambda: _release_session(state))` → the same, and the
  release ends with `RELEASED` (no decrement: phase `OPENING`).
- `_claim(here)`: `ended is None and due passed and not busy` → `phase is OPEN and due passed`:
  `MARK` then `CLAIM_ENDING(me or _CLOSER)`. `ended is None: busy → RuntimeError; else busy =
  True, turn_thread = me` → `OPEN: CLAIM(me)`; `TURN: RuntimeError("a turn is already running")`.
  Else `SessionEnded(ended)` after the expired ending ran here or a closer was started, as today.
- `_release_claim`: `busy = False, turn_thread = None` → `RELEASE` (from `TURN` or `STOPPING`).
- `_mark(reason)`: `ended is not None → False; ended = reason; closing.set(); True` → the same
  test; `ended = reason; MARK; True` (`_move` sets `closing`).
- `_claim_ending(owner)`: `ending_thread is not None or done.is_set() → False; ending_thread =
  owner; True` → `phase in (ENDING, ENDED) → False; CLAIM_ENDING(owner); True`.
- `_end_session(owner)`: `done.is_set() → None; ending_thread is None → = me; == owner → = me;
  else None` → `ENDED → None; MARKED → CLAIM_ENDING(me); ENDING and holder == owner → TAKE_OVER(me);
  else None`. Its `finish`: `_release_session; outcome = …; done.set()` → `_release_session`
  (decrements: phase `ENDING`); `outcome = …; RELEASED`.
- `_shutdown_applies`: `called and sound and not busy and …` → `guest is SOUND and …`.
- `_session_turn`'s verdict: `error → sound = False, _mark("error")` → `FAILED, _mark("error")`;
  `done.returned → sound = True` → `RETURNED`; `done.cause → sound = False` → `UNWOUND`; the
  marks as today; `busy = False, turn_thread = None` → `TURN_RETURNED`; `ended is not None and
  _claim_ending(me)` → `phase is MARKED and _claim_ending(me)`. Its forced-out test `not home.done`
  → `home.phase in (STARTING, RUNNING, ABANDONED)`.
- `_abandon_turn` (the guest thread, at its end): `sound = False; _mark("error"); busy = False;
  turn_thread = None` → `FAILED; _mark("error"); TURN_RETURNED`.
- `_drive_turn`: `called = True; if needs_initialize: needs_initialize = False; _initialize()` →
  `first = guest is UNTOUCHED; ENTER; if first and "_initialize" in exports: _initialize()`.
- `_open_session`: `needs_initialize = "_initialize" in exports` → gone (derived).
- `close()`: forked → facts only, as today. `_mark("closed")`; `turn_thread == me or
  ending_thread == me → return` → `holder == me → return`; `here = not busy and
  _claim_ending(me)` → `here = phase is MARKED and _claim_ending(me)`; then as today.
- `_reap`: `ended is not None or busy or due is None → continue` → `phase is not OPEN or due is
  None → continue`; `_mark(due[1]) and _claim_ending(_CLOSER)` → the same calls.
- `_end_dropped`: `not busy and _mark("closed") and _claim_ending(_CLOSER)` → `phase is OPEN and
  _mark("closed") and _claim_ending(_CLOSER)` (a `MARKED` state: `_mark` is `False` today, so
  the phase test says the same).
- `_sessions_at_exit`: `_mark("closed"); start = not busy and _claim_ending(_CLOSER)` →
  `_mark("closed"); start = phase is MARKED and _claim_ending(_CLOSER)`; then `done.wait()` and
  the closers' joins, as today.
- `_release_session`: `if counted: _counts -= 1; counted = False` → `if state.phase is ENDING:
  _counts -= 1`.
- `_State` after this specification: `lock`, `phase`, `holder`, `ended`, `outcome`, `closing`,
  `done`, `guest`, `opened`, `last_end`, `idle_s`, `lifetime_s`, `shutdown_s`, `checked`, `wt`
  (`types.ModuleType`, the lazily imported wasmtime-py, as `_engines._wasmtime` returns it), `engine`
  (`wasmtime.Engine | None`), `store` (`wasmtime.Store | None`), `exports`, `keys`, `table`
  (`_Files | None`), `host`, `metered`, `origin_ns`, `bounded` (`_Bounded | None`), `private_loop`,
  `scratch`, `private`, `walked`, `home`, `context` (`contextvars.Context | None`), `ending_home`
  (`_Home | None`): 31 attributes, 35 today; each typed with wasmtime-py's own type where it has
  one and `Any` where it does not, counted in the landing notes.

### The home's table

`_HomePhase`: `IDLE`, `STARTING`, `RUNNING`, `ABANDONED`, `CANCELLED`, `DONE`.
`_HomeEvent`: `START`, `TAKE`, `CANCEL`, `LEAVE`, `END`, `LOST`.

| phase | event | → phase | who raises it |
|---|---|---|---|
| IDLE | START | STARTING | `_start_guest`, under the lock, before `thread.start()` |
| DONE | START | STARTING | the same: the one retry after `_ThreadTooSmall` (`_on_guest_thread`) |
| STARTING | TAKE | RUNNING | `body`, its first line under the lock |
| STARTING | CANCEL | CANCELLED | `_start_guest`'s handler when `thread.start()` raised; `_join_guest`'s backstop |
| STARTING | LEAVE | ABANDONED | `finish(step)` while the home is forced out before the body took the start |
| RUNNING | LEAVE | ABANDONED | `finish(step)` while the guest thread runs (spec 078, Decision 14) |
| ABANDONED | TAKE | ABANDONED | a body taking a start whose home has left: it runs, then the steps |
| ABANDONED | LEAVE | ABANDONED | a second step left for the guest thread |
| CANCELLED | TAKE | CANCELLED | a body the OS started after its cancel: it returns at once |
| RUNNING | END | DONE | `body`'s `finally`, under the lock; no steps |
| ABANDONED | END | DONE | the same; the steps are handed to the guest thread, which runs them |
| RUNNING | LOST | DONE | `_join_guest`'s backstop: the thread is dead and never reported |
| ABANDONED | LOST | DONE | the same |

Every other pair is refused, `START` from `CANCELLED` among them (Decision 3). `finish(step)`
raises `LEAVE` only in `STARTING`, `RUNNING` and `ABANDONED`; in `IDLE`, `CANCELLED` and `DONE`
it runs the step at once and returns `True`, as today's `done` test did.

**The invariants `home.lock` protects** (the docstring of `_Home`):

1. `phase` is written under the lock only, through `_Home._move`, which refuses a pair not in the
   table with a `RuntimeError` naming both.
2. `ended.is_set()` only in `IDLE`, `CANCELLED` and `DONE`; `START` clears it in the same lock
   hold; `CANCEL` and `LOST` set it after theirs, and `END` sets it after the steps have run, so
   `DONE` precedes `ended.is_set()` by the steps' run (the join waits on `ended`, as today).
3. `thread` is the guest thread from `START` until the next `START`; `None` before the first.
4. `steps` grows only in `ABANDONED`; `END` from `ABANDONED` empties it into the guest thread's
   hands; `LOST` from `ABANDONED` keeps them in `DONE`: the thread is dead and nothing can run
   them, as today.
5. `raised` is set in `ABANDONED` (`finish` stops the guest with a `_Stopped` at least).
6. `serving` is `phase in (STARTING, RUNNING)`; `done` is `phase in (IDLE, CANCELLED, DONE)`.

**The mapping, function by function:**

- `__init__`: `state = "idle"; done = True; serving = False; abandoned = False` → `phase = IDLE`.
- `_start_guest`: `state, done, thread = "starting", False, thread; serving = True;
  ended.clear()` → `START; thread = thread; ended.clear()`. Its handler: `if state ==
  "starting": state, done, serving = "cancelled", True, False; ended.set()` → `if phase is
  STARTING: CANCEL; ended.set()`.
- `body`: `if state == "cancelled": return; state = "running"` → `if _move(TAKE) is CANCELLED:
  return`. Its `finally`: `done = True; state = "idle"; steps, self.steps = (steps, []) if
  abandoned else ([], steps)` → `was = phase; END; steps = take them if was is ABANDONED`.
- `finish(step)`: `if not done: abandoned = True; steps.append(step); stop(_Stopped()); return
  False` → `if phase in (STARTING, RUNNING, ABANDONED): LEAVE; steps.append(step);
  stop(_Stopped()); return False`.
- `_join_guest`'s backstop: `if not ended.is_set(): state, done, serving = "cancelled", True,
  False; ended.set()` → `if not ended.is_set(): CANCEL if phase is STARTING else LOST;
  ended.set()`.
- `call()`: `raised is not None or not serving` → `raised is not None or phase not in (STARTING,
  RUNNING)`.
- `serve()`: `serving = True` at its start and `False` in its `finally` → gone (Decision 3 names
  the sub-slice window).
- `_on_guest_thread`: `home.serving = False` after the join → gone; the retry's `_start_guest`
  starts from `DONE`.
- `_session_turn`: `if not home.done` → `if home.phase in (STARTING, RUNNING, ABANDONED)`.

### The type check and the allowlist

As Decision 5 says: `[tool.mypy]` in `pyproject.toml`; `mypy==1.19.1` in the dev group;
`test_src_type_checks_under_mypy_strict` in `tests/checks/test_rules.py` with `UNTYPED =
{"mounts.py": "spec 106"}`; a mypy exit of 2 is a failure; an allowance with no error left is a
failure. The check runs in the fast tier (it is not `slow`), once per judge, in whichever worker
takes it under `-n`. Its wall time is a benchmark fact the landing notes record, never asserted
(constitution §4.9); INFERRED from mypy's usual speed on 11,423 lines, ten to twenty seconds cold
and a few warm with the cache under `build/`.

## Scope

In: Decisions 1 to 7. The files: the runner's package (every module 103 made, as 104 left them),
`tools.py`, `cli.py`, `tests/harness/calls.py` (new), `tests/unit/test_lifecycles.py` (new),
`tests/unit/test_async_tools.py`, `test_runner_inputs.py`, `test_runner_limits.py`,
`test_runner_sessions.py`, `test_runner_threads.py`, `test_runner_tools.py`,
`tests/checks/test_rules.py`, `tests/checks/test_v1_4_embedding.py` and
`tests/checks/test_v1_4_public_api.py` (their stand-ins), one probe line in
`tests/checks/test_v1_2_hostile_guest.py`,
`pyproject.toml`, `uv.lock`, `CHANGELOG.md`, `context/roadmap.md`, this file.

Out:

- **`mounts.py`'s 10 errors and its `Any`s** (spec 106, the one allowance).
- **The friend-class coupling in `tools.py`** (the memo's L2) and `tools.py`'s `Any`s beyond what
  its 36 errors need: only the 36 lines change.
- **Any change of behaviour.** The two readings Decision 2 names (a `MARKED` dropped session; a
  cancelled queued turn after a `close()`) are kept exactly and recorded here for a later
  specification with its own research; neither is a gap of this one (no check expects
  otherwise, and the fast tier's verdicts do not move: criterion 5).
- **A ratchet on the `Any` count.** The module size ceiling is 103's, the function-length ceiling
  and the test-seam allowance check are 107's, the lock and mutable placement checks are 104's.
- **A per-platform type check.** The check runs against the linux platform's narrowing on every
  host (Decision 5); checking the Windows-only branches is a later specification's.
- **Typing the tests.** `mypy` runs over `src/wasi_python` only; the harness and the checks are
  the judge's and stay as they are.
- **`ruff`'s rule set.** Adding `ANN` or `TCH` rules is a judge change of its own.
- **The engine seam's types** (spec 102 names them; this specification uses them).

## Acceptance criteria

1. **The checks exist and were seen failing first.** `test_src_type_checks_under_mypy_strict`
   on the base commit: 78 errors in 4 files (or the base's own count, restated), the three of
   The problem among them, recorded in the landing notes, and 92 under `--platform win32` on the
   same base (the pre-build review's EXECUTED count, restated by the builder); then green with
   the one allowance, and, `platform = "linux"` pinned, with the same count on the Linux, macOS
   and Windows judge shards of the chain's dispatch (criterion 8). The
   two table checks and the exhaustiveness and liveness rows red on the base (no enum to import)
   and green on the build. The exhaustiveness row seen red once more with one member added to a
   copy of each enum and no row for it, the output in `build/105/`.
2. **The call is typed.** `_checked` returns a `_CheckedCall` with the 19 fields of the Design,
   frozen, every field required (a construction missing one is a `TypeError`: one unit row).
   `home` and `loop` are parameters on `run`'s path as on the session's; `_home_of` is gone;
   `run_async` passes its event as `cancel`; `grep -rn 'dataclasses.replace\|\breplace(' src/wasi_python`
   finds no replace of a call (EXECUTED by the builder in the landing notes).
3. **No read of a call's field has a default, and no flag remains.** EXECUTED by the builder in
   the landing notes: `grep -rnE '\.get\("(tools|mounts|import_path|import_serving|tool_request_bytes|home|tool_loop)"|checked\[' src/wasi_python`
   finds nothing (no read with a default, no write after the check); `grep -rnE '\.(busy|called|sound|needs_initialize|counted|turn_thread|ending_thread|serving|abandoned)\b' src/wasi_python`
   finds nothing; `grep -rnE '\.state\b' src/wasi_python/<the home module>` finds nothing;
   `tests/harness/calls.py` is the one place in the harness a stand-in call is built, and the
   unit and check files Decision 1 names take theirs from it:
   `grep -rnE '_tool_host\(\{|_tool_host\(c,|\)\["(fuel|deadline_s|memory_bytes|output_bytes|argv|env|stdin|tools|gate|tool_calls|tool_request_bytes|root|grants|mounts|import_path|import_serving|file_calls|open_files)"\]' tests`
   finds nothing.
4. **Both machines are whole.** Every row of the three tables is driven by a unit row; the
   exhaustiveness and liveness rows pass; every illegal pair raises `RuntimeError` naming the
   phase and the event. The existing session and home checks pass unchanged in their rows.
5. **No verdict moves.** The fast tier (`uv run pytest -m "not slow" -n 6`, no `--accept`) on the
   frozen `v0.1.0a7` artifact set, verified against its `SHA256SUMS` (memo section 8), compared
   by `uv run python tests/harness/sameness.py <baseline latest.json> <this latest.json>`: the
   only differences are the claim list's (the new nodes in `test_lifecycles.py` and
   `test_rules.py`, and `collected_files`), each named in *For the lane*; no `status`, `need`,
   `bytes` or `passes` differs; the hostile-guest check's golden lines are unchanged.
6. **The judge is green.** `ruff check` and `ruff format --check` clean on `src`, `tests` and
   `recipes/guest`; `uv lock` adds `mypy==1.19.1` and its wheels by hash and changes nothing else;
   `uv run mypy` (bare) gives the same 10 errors in `mounts.py` as the check sees.
7. **The numbers in the landing notes, EXECUTED:** the `Any` tokens and annotations after, by the
   two commands of The problem; the `type: ignore` count after, with each new one's code and
   reason; `_State`'s attribute count; the fast tier's wall time with and without the mypy check
   (a benchmark fact); the unit rows added.
8. **The release.** The chain lands as one wave with one dispatch of the release workflow on its
   final tip (the owner, 2026-10-20, memo section 8); this specification's builder dispatches a
   run only if it is that tip. The run's red lines, if any, are growth lines or G7, and the run
   id is in the landing notes.

## For the lane

- **Kind:** parallel-safe; **stacked**, fourth in the chain 102 → 103 → 104 → 105 → 106 → 107,
  which lands as one wave of six (the owner's decision, memo section 8). It shares
  `pyproject.toml` and `uv.lock` with no other entry of the chain (102 to 104, 106 and 107 add no
  dependency), `tests/checks/test_rules.py` with 107 (different checks; a textual merge),
  `CHANGELOG.md` and the roadmap with every entry.
- **The order:** it is built on 104's reviewed tip and rebases onto 104's landed form; 106
  builds on its reviewed tip (the allowance and the typed seams).
- **The claim list** (the builder's fast tier on the frozen a7 set; each line starts "105:"):
  - 105: **new checks:** `tests/checks/test_rules.py::test_src_type_checks_under_mypy_strict`
    (no fuel); `tests/unit/test_lifecycles.py` (its rows counted in the landing notes: three
    tables, three exhaustiveness rows, three liveness rows, one `_CheckedCall` row).
  - 105: **rows that change text and not verdict:** the stand-ins in `test_async_tools.py`,
    `test_runner_inputs.py`, `test_runner_limits.py`, `test_runner_sessions.py`,
    `test_runner_threads.py`, `test_runner_tools.py`, and in `tests/checks/test_v1_4_embedding.py`
    (two `_tool_host` stand-ins) and `test_v1_4_public_api.py` (one key read); the probe line of
    spec 093's child program in `test_v1_2_hostile_guest.py`.
  - 105: **retired checks:** none. **Lost passes:** none. **Grown rows:** none (no artifact byte,
    no guest fuel: the machines run on the host).
  - **The judge hash changes** in `tests/checks/test_rules.py`, `tests/harness/calls.py`,
    `tests/unit/test_lifecycles.py`, the six unit files above, `test_v1_4_embedding.py`,
    `test_v1_4_public_api.py` and `test_v1_2_hostile_guest.py`.
- **The flags** (paste-safe):

  ```
  --accept "105: a call's checked arguments are a frozen _CheckedCall with 19 required typed fields, home and loop are parameters, the session's lifecycle is a seven-phase table (_Phase) with a four-state guest (_Guest) and the home's a six-phase table (_HomePhase), each driven whole by the judge, and mypy --strict runs over src/wasi_python as a rules check with one allowance (mounts.py, spec 106); no public name, verdict or artifact byte moves"
  --accept-judge "105: a rules check runs mypy --strict (1.19.1, pinned exactly; platform pinned to linux so three systems give one verdict) over src/wasi_python with a per-module allowlist that must shrink; unit rows drive the session's, the guest's and the home's transition tables whole with exhaustiveness and liveness; every stand-in in the unit files, test_v1_4_embedding.py and test_v1_4_public_api.py builds a _CheckedCall through tests/harness/calls.py instead of a dict or a key read; spec 093's child program reads the phase (TURN or STOPPING) where it read busy, its golden lines unchanged"
  ```

- **Dry-run needs:** none of its own; the chain's one dispatch on its final tip. The Windows judge
  shards run the new unit rows as any other, and the mypy check against the linux platform's
  narrowing, with the same count as the Linux shard (Decision 5).

## Disposition of the pre-build review

The review (`../reviews/105-typed-call-state-and-explicit-lifecycles-spec-2026-10-20.md`) re-ran
the shape checks and the mypy run on three platforms, traced every setter of the lifecycle onto
the tables (its finding: complete), and ranked seven findings. Every one is written in; no
decision changed, one was extended (the platform).

- **F1 (High), written in.** Decision 5 pins `platform = "linux"` with the reason, what is lost and
  the recourse; criterion 1 states the Windows count (92) as the review's EXECUTED fact and asks
  for one count on three systems; Scope out names the per-platform check; the lane's dry-run line
  and the `--accept-judge` reason say it.
- **F2 (Medium), written in.** The problem names the third late write (`runner.py:673`); Decision 1
  makes `run_async` pass its event as `cancel`; criterion 2 forbids `dataclasses.replace` on a call;
  criterion 3's grep gains `checked\[`.
- **F3 (Medium), written in.** Decision 1 lists every stand-in site with its lines (the review's
  plus `test_runner_tools.py:754`); Scope, the claim list and the judge-hash list name
  `test_v1_4_embedding.py` and `test_v1_4_public_api.py`; criterion 3's last sentence is reworded
  and carries the grep.
- **F4 (Low), written in.** 19 keys with tools, 18 without; `_ToolArgs` carries
  `tool_request_bytes=None`; `c.get("mounts")` at 5524 named without its default; the oracle
  sentence dropped and replaced by what the line is.
- **F5 (Low), written in.** The home's invariants 2 and 4 as the review's fix texts.
- **F6 (Low), written in.** The probe reads `phase in (TURN, STOPPING)`.
- **F7 (Low), written in.** `_State.checked`, with the reason.
- **Cross-specification alignment** (the lane, 2026-10-20): the module names are 103's, with its
  `_module.name` rule; the module size ceiling is 103's, the function-length ceiling and the
  test-seam allowance check 107's, the lock and mutable placement checks 104's (Decision 6, Scope).

## One line

A call's state becomes a frozen typed record, a session's and a home's life become tables the
judge drives whole, and `mypy --strict` runs in the judge, so the next missing field, flag or
path is a red check and not a bug under a guest.

## Landing notes

Filled in when it lands.
