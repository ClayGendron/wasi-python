# Build review of 075 — tools.py small fixes, 2026-10-19

- **Reviewer:** a fresh agent. I wrote none of 075's code. I reviewed its specification before
  build and confirmed it (`075-tools-small-fixes-spec-2026-10-19.md`), and I wrote the 0.1.0a6
  security review whose F1 it closes.
- **Under review:** `spec/075-tools-small-fixes` at `2284e7d` over main `23f1c4f`. Four commits:
  `ca7dce4` (the confirmation's c1 and c2), `ff687cb` (the checks alone), `8eeb003` (the code, the
  README and the CHANGELOG) and `2284e7d` (the landing notes). The builder's evidence is in the
  main tree, under `build/reviews-evidence/075-build/`.
- **How I ran it:** a `git clone -b spec/075-tools-small-fixes` of the repository into the
  scratch folder (`built/`), then `uv sync`. All runs used the frozen set `s-c50ca51fae5eb55b`
  (`shasum -c` all OK). I touched no git tree. The clone was restored after every stand-in, and
  `git status` is clean. My probes are in `probes/`, and their logs in `logs/`, beside this file.

Labels: **EXECUTED** (I ran it), **READ**, **INFERRED** (reasoned, not run).

## Short version

The code is the confirmed specification, line for line. Decision 1 adds `returned` and its test;
Decision 2 records the `GeneratorExit` it re-raises; Decision 6 refuses an oversized list from
its exact length before building it. My awaitable matrix gives the same output on the built code
as on the draft's fix: no allow and no `ok` without a return, across 13 kinds of awaitable, each
as a gate's answer and as a tool's, on both loops. The Ctrl-C probes behave as before.

The judge is green on everything 075 touches: 0 fail, lost 0. The three "grew" lines are not
075's; an A/B proves the one the builder did not see.

One low finding: criterion 3's cleanup is not in a `finally`. So when that check fails, every
later check in its file waits 60 s, and a 4-second file took 13 minutes. Fix it in three lines.

## The code against the specification (READ, `git diff 23f1c4f..2284e7d -- src/`)

- **`_Post`** gains `returned`, `False` until set. **`_ToolLoop._wrapper`** sets it on the
  statement after `post.value = await post.awaitable`, inside the same `try`, and its
  `except GeneratorExit as e:` records the exception, then re-raises it. The first step's
  `except GeneratorExit: raise` is unchanged, as Decision 2 says.
- **`_ToolLoop.run`**, after its wait, tests in the stated order: `skipped`, then `error`, then
  `not returned`, which raises `RuntimeError("the awaitable ended without a result")`. Only then
  does it return the value.
- **The list.**
  - `_tools_array()` holds the array, encoded once, as before.
  - The builder's `_list_head(frame_id)` (departure 2) gives the parts before the array.
    `_list_answer` joins them; `_list_length` sums their lengths. So the bytes and the length
    come from one source.
  - The `list` branch refuses on `_list_length(frame_id) > _TOOL_RESPONSE_BYTES` before it
    calls `_list_answer`, and measures nothing again.
  - A bug in `_list_head` would move both the answer and its length, so their equality alone
    could not catch it. Criterion 5 compares both with `len(_encode(...))` of the real message,
    which does.
- **Nothing else changes:** `_Work`, the bound, the protocol, the public API.
  `tests/public_api.txt` is unchanged, and `api.py --check` exits 0 (EXECUTED).
- **README and CHANGELOG.**
  - **Faults stay in the call** names `GeneratorExit`, says an async gate's raise refuses
    (`denied`), and carries the Ctrl-C clause.
  - The builder's wording (departure 5), "ends that call as a fault (a gate's call is
    refused)", is more exact than mine. A tool's call ends `tool_error`, and only a gate's is
    refused; both keep the fault, as q2 and q1 show.
  - The CHANGELOG has one **Fixed** entry under `0.1.0a7 — unreleased`, naming both items and
    their sources.

## Re-run against the built code (EXECUTED)

- **q1, the awaitable matrix** (`probes/q1_no_default_allow.py`, `logs/q1_built.log`). The
  output is identical to the draft's fix (`diff` empty, after removing task numbers and paths).
  Six kinds that fail open on main now refuse:
  - a bare `__await__` iterator raising `GeneratorExit` or a subclass;
  - a `@types.coroutine` that yields, then raises;
  - an `async def` that raises after one loop turn;
  - a `Future` given `set_exception(GeneratorExit())` or a subclass.

  Each now gives `denied` for a gate and `tool_error` for a tool, with the fault naming the type.
  The other seven kinds are unchanged. **Allow or `ok` without a return: none.**
- **q3** (`logs/q3_built.log`). With `_begin` raising `GeneratorExit`, the call is `denied`, with
  fault `RuntimeError: the awaitable ended without a result`, and the tool does not run. A
  skipped post raises `_NotStarted`, and the coroutine is closed.
- **q2, a real SIGINT** (`probes/q2_ctrl_c_main_thread_loop.py`, `logs/q2_built_*.log`). Every
  case is the same as in the pre-build review:

  | case | result |
  |---|---|
  | `run_until_complete`, the SIGINT lands in a busy gate | `denied`, fault `KeyboardInterrupt`; the guest gets `ToolDenied`; `run_async` returns; the embedder never sees the Ctrl-C (15.4 s, because the first run compiled the new set's `.cwasm`) |
  | `run_until_complete`, the SIGINT lands in `select` | the embedder gets `KeyboardInterrupt`; the work thread waits until `loop.close()` (053 F7 d) |
  | `asyncio.run`, the gate awaits | the gate meets `CancelledError`; the tool does not run |
  | `asyncio.run`, a busy gate | the gate allows before the cancel is processed; the tool ran (056's documented race) |

## Stand-ins

- **The builder's** (`075-build/standins.out`, READ). S1 to S11 each fail. The counts agree with
  the confirmed spec: S2's 38 is criterion 1's 26 plus criterion 2's 12; S4's 16 is criterion 1's
  10 subclass rows plus criterion 2's 6. So the builder's "more failures than predicted"
  (departure 4) is criterion 2's rows, which the spec counts under criterion 2.
- **Mine, over the three tool test files with no `-k` filter** (`probes/r_standins.py`,
  `logs/r_standins.log`, 324 checks; the file restored after each):

  | stand-in | result |
  |---|---|
  | S2, Decision 1 alone | 38 failed |
  | S4, only an exact `GeneratorExit` recorded | 16 failed |
  | S11, `skipped` tested after `returned` | 2 failed (criterion 3, both loops), **in 791 s** |
  | X1 (mine), `returned` set in the wrapper's outer `finally` | 2 failed (criterion 3), **in 788 s** |
  | X2 (mine), the `GeneratorExit` recorded but not re-raised | **survives**: 324 passed (N1) |

The 13-minute runs are F1.

## The judge (EXECUTED)

- **Full, `-n 3`** (`logs/full-n3.log`): 1850 passed, 64 skipped, 3 xfailed, 0 failed. Lost 0,
  gained 0. The judge change is named: the two unit files. Ruff check and format are clean.
  - A first full run, `logs/full-n3-CONTAMINATED.log`, overlapped my stand-in script in the
    same clone, so I set it aside. The clean run above came after the file was restored.
- **Fast, `-n 3`** (`logs/fast-n3.log`): 474/550 pass, 1 gap, 24 blocked, 0 fail. Unit suite
  1359/1367. Lost 0.
- **The "grew" lines are not 075's.**
  - `test_recursion_through_python_raises[heapq-plain]` and `[lru-cache-plain]` (and
    `[pickle-partial-plain]` in the builder's run): spec 071's plain-binary rows. Their fuel
    varies run to run; the builder's `fuel_spread.out` shows 0.27 to 0.37% across five runs. This
    is spec 080's.
  - **`test_stylesheets_and_entities_reach_only_grants[snapshot]`, which the builder did not
    see:** +113,8xx fuel, the same within 50 instructions in all five of my runs. So it is not
    random. **An A/B in my clone settles it:** with the built `tools.py` the row grew to
    216,114,724, and with main's `tools.py` (from `23f1c4f`) to 216,114,747
    (`logs/lxml_ab.log`). 075 does not move it.
  - The likely cause is the checkout's path (INFERRED). The test hands the guest a host path
    under `HARNESS_TMP`, which lives inside the checkout, as an argument. My clone's root is 128
    characters long, against 40 for the main tree, and the builder's worktree path is only 4
    longer than main's.
  - In any case, **075 cannot move any guest fuel row.** The judge's guest driver
    (`tests/harness/guest.py`) does not import `wasi_python` (READ, grep), and neither test passes
    `tools=`.

## The builder's departures

1. **Criterion 5 fails on main only through its last row,** because `_list_length` does not
   exist there. The spec expected the criterion to pass on main and to bite through its
   stand-ins. Putting the equality row last keeps the boundary rows visibly passing on main, and
   S6 to S10 still each fail it. Accepted.
2. **`_list_head`, a third helper.** Better than the spec: one source for the bytes and their
   length. Criterion 5's comparison with the real `_encode` covers it. Accepted.
3. **Exact fault strings in criteria 1 and 2** (`SystemExit: 3`, `GeneratorExit: text`), where
   the spec said "begins with". Stricter, and it pins what the record says. Accepted.
4. **More stand-in failures than predicted:** the counts match once criterion 2's rows are
   counted. Accepted.
5. **The README's Ctrl-C wording:** more exact than the spec's. Accepted.

## Findings

### F1. Criterion 3 leaks its private loop when it fails, and every later check in the file then waits 60 s. Low; fix before landing (EXECUTED)

- **Where:** `test_the_tool_loop_gives_a_value_only_when_the_awaitable_returned` calls
  `loop.close()` (and `host.close()`) inline, after its assertions. When an assertion fails, the
  private `_ToolLoop`'s thread, named `wasi-python-tool--loop`, stays alive. The file's autouse
  `joined` fixture joins every thread whose name starts `wasi-python-tool-`, with a 60 s
  fail-safe. So it waits 60 s after this check, and again after every later check in the file,
  because the thread never ends.
- **Effect:** under S11 and X1, the three tool files took 791 s and 788 s, against about 4 s when
  the check fails cleanly (S2, S4). The builder's own runs took about 2 minutes only because
  they selected the new checks by `-k`. The judge still reports the failure, but a regression
  here would stall a landing for many minutes. Under `-n 3` it would spread across workers.
- **Fix:** put the two cleanups in `try`/`finally` (or a small fixture that closes the
  `_ToolLoop` and the host). Re-run S11 to show it fails in seconds.

## Notes

- **N1. X2 survives: the re-raise in Decision 2 is not pinned.** If `raise` is dropped from
  `except GeneratorExit as e:`, every check still passes (324). The record is still right,
  because the error is kept. But the wrapper's own close path would then break: a pending
  wrapper closed by the loop or the GC would raise `RuntimeError: coroutine ignored
  GeneratorExit`, which Python prints as "Exception ignored". Decision 2 says the re-raise stays
  for exactly this reason. An optional unit row would pin it: drive a wrapper to its `await` on a
  pending `Future`, then `close()` it; no `RuntimeError` is raised. It can follow.
- **N2. A host path in a guest's arguments makes fuel depend on the checkout's location.** The
  lxml snapshot row grows by about 114 k instructions in a checkout 88 characters longer than the
  main tree, whatever `tools.py` holds (A/B above). The lane judges in the main tree, so it should
  not see this. But it is the same class of judge defect as the unseeded recursion rows: worth
  adding to spec 080's scope.
- **N3. One README line runs to 106 columns** (line 1541, the end of the Ctrl-C clause); its
  neighbours wrap at 76. Rewrap it with F1.
- **N4. Constitution.** Host side only: no import, export, artifact or recipe change. No default
  loosened; the change only turns allows into refusals. No public API change. §7: nothing
  tripped.

## Verdict

**Lands once F1 is fixed:** criterion 3's cleanup in a `finally`, shown by S11 failing in
seconds. N3's rewrap can ride along. The code is the confirmed specification. Every fail-open path
I know of is closed on both loops; the Ctrl-C behaviour is unchanged; the judge is green on
everything 075 touches.

## One line

The fix is right and complete: no awaitable allows without returning. Put criterion 3's cleanup
in a `finally` so that a future failure there costs seconds, not 13 minutes, and it lands.
