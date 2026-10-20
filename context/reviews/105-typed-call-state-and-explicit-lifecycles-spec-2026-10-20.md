# Review of 105 — Typed call state, explicit lifecycles, and a type checker in the judge

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (pre-build reviewer for the chain 102–107)
- **Reviewed:** the specification as drafted
  (`context/specifications/105-typed-call-state-and-explicit-lifecycles.md`, untracked on
  `claude/gallant-ride-9nxxmn` at `c9515ef`), read against `src/wasi_python/` at the same commit
- **Run:** none (pre-build review of the draft)
- **Re-ran:** `uv run pytest tests/checks/test_rules.py -k "specifications or open_question" -q
  -p no:cacheprovider` → 3 passed, exit 0; `uv run --with mypy==1.19.1 mypy --strict
  --no-error-summary src/wasi_python` → 78 errors, exit 1 (the writer's
  `build/105/mypy-strict.txt` says the same: 78 in 4 files, tools.py 36, runner.py 30, mounts.py
  10, cli.py 3); the same with `--python-version 3.11` → 78; with `--platform darwin` → 78; with
  `--platform win32` → **92**; `grep -oE '\bAny\b' -r src/wasi_python --include='*.py' | wc -l`
  → 424; `grep -oE '(: |-> )Any\b' …` → 314; `grep -c 'type: ignore'` → runner.py 9, mounts.py 2,
  cli.py 1; `grep -cE 'c: dict\[str, Any\]' src/wasi_python/runner.py` → 8;
  a case-insensitive grep for the scanner's three banned words on the draft → nothing. Scratch outputs under
  `/tmp/claude-0/-home-user-wasi-python/a7a0f302-7717-538b-8fac-46c5fd7843f5/scratchpad/`
  (`mypy-105.txt`, `mypy-105-win32.txt`, `mypy-105-darwin.txt`).
- **Time box:** 25 minutes (parallel-safe).

## Acceptance criteria against evidence

1. **The checks exist and were seen failing first** — not met yet (pre-build), and the base count
   the criterion restates is Linux's only. EXECUTED: 78 errors in 4 files on Linux and darwin, the
   three lines The problem names present (`runner.py:1020` return-value, `runner.py:5974` misc,
   `tools.py:2002` arg-type: `build/105/mypy-strict.txt` lines 50, 77, 35); **92 on win32**
   (finding H1). The table checks' red-on-base is INFERRED (no enum to import) and sound.
2. **The call is typed** — the field list is right as far as it goes. READ: `_check_limits`
   (`runner.py:147-158`) 4 keys, `_check_inputs` (`177-`) 3, `cancel` (`1522`), `_check_tools`
   (`1588-1595`) 4 with tools and **3 without** (L1), `_check_places` (`1865-1873`) 7. Two late
   writes are named; a third exists (`runner.py:673`, M1).
3. **No read of a call's field has a default** — the today side holds. EXECUTED: 19 `.get` reads
   on 17 lines (2753, 2763×2, 2767, 2845, 2877, 3023, 3029, 4028, 4042, 4049, 5367, 5399, 5524,
   5639, 5658×2, 5667, 5750), as the Design lists them; the flag names grep to exactly the
   setters and readers the Design maps. The tests side is incomplete (M2): three files beyond
   the six named build or index a call by key.
4. **Both machines are whole** — READ, the lifecycle traced (below); every setter in today's
   code maps onto a row; no transition the code needs is missing from either table; the two
   refused session pairs (`_claim_ending` with `ended is None`; a move from `OPENING` by
   another event) are unreachable: every `_claim_ending` caller follows a `_mark` or tests
   `ended` (`5055`, `5097`, `5129`, `5590`, `6051`, `6235`), and an `OPENING` state is in neither
   `_sessions` nor the dropped queue. Two docstring invariants of the home are false by a
   window and by `LOST` (L2).
5. **No verdict moves** — INFERRED; plausible. The probe check (`test_v1_2_hostile_guest.py:3175`)
   carries no `slow` mark (READ; the mark at `3497` is another check's), so the fast tier's
   sameness covers its golden lines; the probe's meaning narrows (L3) without moving them.
6. **The judge is green** — not evidenced for Windows: as drafted the mypy check is red on the
   Windows judge shards (H1). `uv lock` changing nothing else is INFERRED.
7. **The numbers** — the before numbers are reproduced: EXECUTED 424 and 314 `Any`, 12
   `type: ignore` (9/2/1), 8 `c: dict[str, Any]` parameters; `_State` 35 attributes today and
   31 after, by counting the Design's list (READ).
8. **The release** — the chain's one dispatch; with H1 as drafted its Windows legs are red for a
   reason that is neither growth nor G7.

**The lifecycle, traced (READ, `runner.py`).** Session: `__init__` (`5950-5975`: `_State()`,
`_open_session`, `counted = True`, `_sessions.add`) → `OPENING`, `OPENED`; `_open_session`'s
`except` (`5759-5761`: `home.finish(lambda: _release_session(state))`) → `RELEASED` with no
decrement, since `counted` is still `False` there; `_claim` (`6040-6066`) → `MARK` then
`CLAIM_ENDING(me | _CLOSER)` when due, `CLAIM(me)` from rest, `RuntimeError` when busy;
`_release_claim` (`6068-6072`, from `run_async` at `6188` and `6195`) → `RELEASE` from `TURN`, or
from `STOPPING` when another thread's `close()` marked the queued turn (the second kept reading:
confirmed, it then rests in `MARKED` with no claimant, `_reap` at `5052` skips every `ended`
state, so only `_sessions_at_exit` or a later `close()` ends it); `_mark` (`5005-5011`) the one
writer of `ended`; `_session_turn` (`5546-5600`) → `FAILED`/`RETURNED`/`UNWOUND`, the marks,
`TURN_RETURNED`, `CLAIM_ENDING(me)`; `_abandon_turn` (`5603-5612`, on the guest thread) →
`FAILED`, `MARK`, `TURN_RETURNED`, no claim (the first kept reading: confirmed, `_end_dropped`'s
`_mark` at `5097` is `False` on it); `close()` (`6208-6241`) → `MARK`, the holder test, `CLAIM_ENDING(me)`
only at rest; `_reap` (`5039-5061`), `_end_dropped` (`5095-5099`), `_sessions_at_exit`
(`5114-5137`) → `MARK` and `CLAIM_ENDING(_CLOSER)` only at rest; `_end_session` (`5152-5191`) →
`CLAIM_ENDING(me)` with no owner (no caller passes none: `5028` passes `_CLOSER`, `5619` passes
`owner`, and its three callers at `5592`, `6060` and `6238` pass `me`), `TAKE_OVER(me)` for the
owner, else `None`; its `finish` → `_release_session` in `ENDING`, `outcome`, `RELEASED`. The two
thread fields are never both set: `_session_turn` clears `turn_thread` at `5587` before it claims
at `5590`, and every other claim is guarded by `not busy`. Guest: `_drive_turn` (`5431-5435`)
sets `called` after the cancel check and before `_initialize`; `_turn_inside` (`5505-5516`)
gives every entered turn a `returned` or a `cause` (the final `return … True` at `5476` makes
`ran` true, and a `None` value there always comes with an exit code or a trap name), and an
exception out of it takes the error row; so no turn leaves the guest `ENTERED`, and `ENTER`
from `UNSOUND` is unreachable since every `sound = False` (`5571`, `5577`, `5607`) comes with a
mark. Home: `_start_guest` (`4294-4324`) → `START`, its handler `CANCEL` only in `STARTING`;
`body` (`4249-4291`) → `TAKE`, `END` with the steps when abandoned; `finish` (`4237-4247`) →
`LEAVE` while `not done`; `_join_guest`'s backstop (`4327-4347`) → `CANCEL`/`LOST`; `serve()`'s
`serving` (`4212`, `4235`) and `_on_guest_thread`'s (`4371`) become the derived fact, and the
retry at `4374` restarts from `DONE`. The sub-slice window Decision 3 names is real and is as
described: `serve()`'s `finally` runs before `_on_guest_thread`'s handler stores `raised`.

## Findings, most severe first

1. **The type check's verdict differs on Windows** (`[tool.mypy]` in Decision 5; "the Windows
   judge shards run … the mypy check as any other" in For the lane; `src/wasi_python/cli.py:189`,
   `runner.py:1004`, `runner.py:4602`, `runner.py:4788`) — mypy narrows on `sys.platform` for the
   host it runs on, so the same tree gives a different error set per system. EXECUTED:
   `mypy --strict --platform win32 src/wasi_python` → 92 errors against 78 on linux and darwin:
   6 `attr-defined` (`resource.RLIMIT_NOFILE`, `RLIM_INFINITY`, `getrlimit`, `setrlimit` in
   `cli.py`; `os.getuid`, `os.uname` in `runner.py`) and 8 `unused-ignore` in `runner.py`
   (`--strict` includes `warn_unused_ignores`, so an ignore a POSIX host needs is an error on
   Windows, and the reverse).
   Failure: the builder empties the allowlist on Linux; the chain's one dispatch runs the Windows
   judge shards; `test_src_type_checks_under_mypy_strict` is red there with 14 errors in modules
   not in `UNTYPED`, a red line that is neither growth nor G7 (criterion 8), found only on the
   chain's final tip with 106 and 107 stacked above. Fix: a sentence in Decision 5 that pins
   `platform = "linux"` in `[tool.mypy]` beside `python_version`, with its reason (one platform's
   branches on every host, as one Python version; the Windows-only lines are still parsed and
   their functions annotated, but their `sys.platform` narrowing is Linux's), and criterion 1
   gains "the same count under `--platform win32` and `--platform darwin` as under the pinned
   platform's run". If the owner wants the Windows-only lines type-checked too, the check runs
   mypy once per platform with `--platform` and the allowance is keyed by (module, platform), the
   wall time tripled; the draft decides one of the two.

2. **A third late write to the checked dict is missing from the inventory** (`runner.py:673`;
   Decision 1, "Two more are bound later: `home` … and `tool_loop`") — `run_async` passes `None`
   as `cancel` to `_checked` (`runner.py:652`) and then writes `checked["cancel"] = event` at
   `673`.
   Failure: with the frozen `_CheckedCall` that line is a `FrozenInstanceError` on every
   `run_async`; a builder who meets it reaches for `dataclasses.replace` in production and
   re-creates the escape hatch the Decision forbids. Fix text for Decision 1: "`run_async` makes
   its `threading.Event` before `_checked` and passes it as `cancel` (`_checked` validates it
   at `1518-1521`); the `_live` registration stays where it is." And criterion 3's first grep
   gains `|checked\[` so a write after the check is red, or criterion 2 states "no
   `dataclasses.replace` in `src/wasi_python`".

3. **The stand-in inventory and the claim list miss three files and five helper lines**
   (Decision 1, "The one hand-built dict today"; Scope; For the lane's judge-hash list;
   criterion 3's last sentence) — READ: `tests/checks/test_v1_4_embedding.py:3358-3359` and
   `:4962` are two more hand-built dicts given to `_tool_host`; `tests/checks/test_v1_4_public_api.py:373-374`
   reads `_checked(...)["memory_bytes"]`; `tests/unit/test_runner_tools.py:162-168` indexes
   `_check_tools(...)` by key and compares it with a dict; `tests/unit/test_runner_limits.py:36-64`
   indexes `_check_limits` by key on five lines and `tests/unit/test_runner_inputs.py:38-138`
   indexes `_check_inputs` by key on five lines beyond the one at `148` the spec names (and
   `38`, `47` compare `argv` with a list, which becomes a tuple). None of the three checks files
   is in Scope, the claim list or the judge-hash list.
   Failure: criterion 3's "`tests/harness/calls.py` is the one place a stand-in call is built"
   is false while `test_v1_4_embedding.py` builds two; the lane's claim-list comparison finds
   rows changed and not claimed (a Medium by `context/reviews/README.md`, item 4). Evidence
   that closes it: Scope and For the lane name the three files and these lines, and the
   builder's landing notes show `grep -rnE '_tool_host\(\{|_checked\([^)]*\)\[|_check_(limits|inputs|tools|places)\([^)]*\)(\[|\s*==)' tests`
   finding nothing.

4. **The key count holds only with tools, and one READ fact is wrong** (The problem 1,
   "a dict of 19 keys … `_check_tools` 4"; Design, "the dict's 19 keys"; Decision 5, "the oracle
   project already pins `mypy==1.19.1`") — `runner.py:1592` returns `{"tools": None, "gate":
   None, "tool_calls": None}` without tools, so a call without tools carries 18 keys; the `.get`
   at `4049` and `5399` is reached only with tools (guards at `4028` and `5367`), so it is a
   stand-in default as the spec says, and `_ToolArgs`'s no-tools value must carry
   `tool_request_bytes=None` for "every field required" to hold. `state.c.get("mounts")` at
   `5524` has no `()` default. The oracle's `uv.lock:663` line is scipy's own dev-extra metadata,
   not the oracle's pin: the repository names no mypy today. Fix text: "`_check_tools` 4 with
   tools, 3 without (its `_ToolArgs` gives `tool_request_bytes=None`)"; drop the oracle sentence
   and keep the two reasons that stand (a wheel `uv.lock` hashes; one documented flag set).

5. **Two home invariants are false by a window and by `LOST`** (Design, the home's invariants 2
   and 4) — `body` sets `ended` after the steps ran (`runner.py:4284-4291`), so `DONE` precedes
   `ended.is_set()` by the steps' run; and `_join_guest`'s backstop from `ABANDONED` (`4343`)
   leaves `steps` non-empty in `DONE`, never run, as today (the thread is dead). Fix text:
   invariant 2 "`END` sets it after the steps have run"; invariant 4 "`LOST` from `ABANDONED`
   keeps them: nothing can run them, as today".

6. **The probe line narrows `busy`** (Decision 7; `tests/checks/test_v1_2_hostile_guest.py:3159`,
   `3167`) — `busy` is `TURN` or `STOPPING` (Decision 2); the probe `phase is _Phase.TURN` is
   `TURN` alone. In spec 093's child program no mark precedes the abandon (READ: `3151-3166`), so
   the golden lines hold either way; `phase in (_Phase.TURN, _Phase.STOPPING)` keeps the probe's
   meaning for a later program. Write-in.

7. **`_State.call` beside the `call: _Call` locals** (Design, `_State` after this specification)
   — `_drive_turn(state, call, data)` (`runner.py:5414`), `_turn_inside` (`5478`) and `_arm`
   (`5329`) each hold a `_Call` named `call` next to `state.call`, two different things one word
   apart. `state.checked` reads as what it is. Write-in.

## Constitution checks

- §4.2 (every tool pinned and hashed): holds; mypy as a wheel `uv.lock` hashes, pyright refused
  for its unpinned Node download. §4.5 (embedder-neutral): holds. §4.9 (tests count): holds; the
  check's wall time is recorded, never asserted. §4.10 (claims carry evidence): holds but for
  the three READ slips in finding 4 and the Linux-only base count of finding 1. §4.13 (no
  dependency without a reason): holds; Decision 5 gives it, `pytest-xdist`'s pin as the pattern.
  §4.14 (stacked build, base commit in the header): holds for a draft; the base commit is to be
  written in when 104 is reviewed. §4.15 (safe by default): nothing loosened; `run`'s `loop` is
  `None` and `home` a fresh `_Home`, as today.
- §5.2 (every choice decided) and §5.6 (a pre-build review where the runner's code changes): held;
  the shape and scanner checks pass (EXECUTED).
- §7 never-do list: nothing tripped; no patch, no import, no fetch, no copy, no commit.

## Disposition (filled in by the author, then confirmed by the reviewer)

Answered by the author on 2026-10-20; the specification is revised in place (its *Disposition of
the pre-build review* says where each finding went) and names 103's module names and the
ceilings' owners (103, 104, 107) as the lane asked.

1. The type check's verdict differs on Windows — fixed: Decision 5 pins `platform = "linux"` in `[tool.mypy]` with the reason (one verdict on three systems; the chain's one dispatch must not be red on Windows for a reason that is neither growth nor G7), what is lost (Windows-only and darwin-only branches are typed against the linux stubs, every one behind a `sys.platform` guard today) and the recourse (a per-platform run with an allowance keyed by (module, platform), a later specification); criterion 1 states the 92 as the review's EXECUTED fact and asks for one count on the three judge shards; Scope out, the dry-run line and the `--accept-judge` reason name it.
2. A third late write to the checked dict is missing from the inventory — fixed: The problem names the third write (`checked["cancel"] = event`, `runner.py:673`); Decision 1 ("The third late write goes away") makes `run_async` make its `threading.Event` before `_checked` and pass it as `cancel`, the `_live` registration unchanged; criterion 2 adds "no `dataclasses.replace` on a call" with its grep; criterion 3's first grep gains `|checked\[`.
3. The stand-in inventory and the claim list miss three files and five helper lines — fixed: Decision 1 ("Every stand-in site today") lists the review's inventory plus one more (`tests/unit/test_runner_tools.py:754`, a fourth hand-built `_tool_host` dict, with its `_max_bytes is None` row at 755): the four `_tool_host` dicts, the three `_checked(...)` key reads, `_check_tools` at 162-168, `_check_limits` on five lines, `_check_inputs` on eight; Scope in, the claim list ("rows that change text and not verdict") and the judge-hash list name `test_v1_4_embedding.py` and `test_v1_4_public_api.py`; criterion 3's last sentence now says calls.py is the one place in the harness a stand-in is built and the named files take theirs from it, with a grep that also catches the two-line `c = {...}; _tool_host(c, …)` form and every `)["key"]` read.
4. The key count holds only with tools, and one READ fact is wrong — fixed: The problem and the Design say 19 keys with tools and 18 without, `_check_tools` 4 with tools and 3 without, and that `_ToolArgs`'s no-tools value carries `tool_request_bytes=None` so the field is required and explicit; the `.get` list names `c.get("mounts")` at 5524 without a default; the oracle sentence is dropped, replaced by what that `uv.lock` line is (scipy's dev-extra metadata; the repository names no mypy today), and the two reasons that stand are kept.
5. Two home invariants are false by a window and by `LOST` — fixed: the home's invariant 2 now says `END` sets `ended` after the steps have run, so `DONE` precedes `ended.is_set()` by the steps' run; invariant 4 says `LOST` from `ABANDONED` keeps the steps in `DONE`, where nothing can run them, as today.
6. The probe line narrows `busy` — fixed: Decision 7's probe is `s._state.phase in (_Phase.TURN, _Phase.STOPPING)`, what `busy` meant, so its meaning holds for a later program that marks before it abandons; the `--accept-judge` reason says "TURN or STOPPING".
7. `_State.call` beside the `call: _Call` locals — fixed: `_State.checked` throughout the Design (the `.get` mapping, `_turn_args`, the attribute list), with the reason (`_drive_turn`, `_turn_inside` and `_arm` each hold a `_Call` named `call`).

## Verdict

Does not land yet: finding 1 (the mypy check is red on Windows as drafted, 92 errors against
78) needs a platform decision in Decision 5 before the build, and findings 2 and 3 written into
Decision 1, Scope and For the lane; the lifecycle tables themselves are complete against today's
code and the draft is otherwise ready to build.
