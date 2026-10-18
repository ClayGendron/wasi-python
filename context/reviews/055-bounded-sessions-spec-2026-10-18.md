# Review of spec 055 before build: bounded sessions

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). It wrote none of the specification, the memo or
  the question. This is the pre-build review §5.6 requires: the spec adds a guest export and
  changes the build recipe. It is also a security review of the design, since one guest kept
  across several calls is new attack surface.
- **Reviewed:** `spec/055-bounded-sessions` at `797aaf3`, the diff `62d2c56...HEAD`:
  `context/specifications/055-bounded-sessions.md`, `context/research/2026-10-18-bounded-sessions.md`
  and its probe folder, and question 91 in `context/questions-for-the-owner.md`. (Main already
  has a 91, so this becomes 92 at landing. That is not a finding.)
- **Read:** `AGENTS.md`; the constitution (§3, §4.4, §4.6, §4.15, §5.2, §5.6, §6, §7);
  `context/reviews/README.md`; decisions 18–22 and 49; `research/2026-10-17-state-across-agent-turns.md`
  (E2, E5b); the 0.1.0a2 security review (F1, F11) and the 0.1.0a4 security review (F1, F2, F3,
  N5); spec 049's text in `../wasi_python-049`; spec 053 in `../wasi_python-053`; spec 054 in
  `../wasi_python-054`. Code at main `a915aed`, whose `src/` and `recipes/` match `62d2c56`:
  `recipes/reactor_main.c`, `recipes/reactor_bootstrap.py`, `recipes/hostmodule.c`
  (`host_alloc`), `runner.py` (`Defaults`, `_call_deferred`, `_instance`, `_drive`, `_Call`,
  `_shared`, `_epoch_answer`, `_watch`, `_door`, `_poll_oneoff`, `_poll_plan`, `_send_outputs`,
  `_Stream`, the exit hooks, `_release`, `stats`, `_tool_host`), `tools.py` (`_Slot`,
  `_Bounded`), `mounts.py` (`_Files.__init__`, `walk`, `release`, `_ask`), and the README's
  *Safety* and *Not protected*.
- **Executed:** scripts and outputs are beside this file in `probes/`. They ran with
  `uv run --no-sync python -I` from the 055 worktree, whose `src/` is `62d2c56`'s. They ran
  against a scratch copy of the frozen set `build/sets/s-f94dec535086b06c`
  (`shasum -a 256 -c SHA256SUMS`: all OK). Nothing was written in any tree.
  - `pa_reactor_patch` shows that guest code can import `_reactor` and replace `run` and
    `_exit_code`, on both binaries.
  - `pb_fd_exhaust` shows that one guest call takes every host descriptor. Under a soft limit of
    1,024 the guest opened 1,014 files. Under the default it opened 122,870 (macOS's
    per-process ceiling). Either way, the host's own `open()` inside a door call then failed
    with `EMFILE`.
  - `pc_exit_closes_stdin` shows that after a caught `exit(3)`, `sys.stdin.closed` is `True` and
    `read()` raises `ValueError`.
  - `pd_sleep_abstime` shows that the guest's `time.sleep(0.05)` reaches `poll_oneoff` as an
    **absolute** monotonic clock (`ABSTIME=True`).
- **Scoreboard:** not re-run. This diff holds documents and probe scripts only. Running the
  judge would write logs into a tree I may not write to.

Labels: **EXECUTED** (I ran it), **READ** (code or document), **INFERRED** (reasoned, not run).

## Short version

The design is sound. Its main ideas hold: one live instance per session, a `turn` export that
never finalizes, limits re-armed for each turn, a memory cap that lasts the whole session, and
bounds kept by the host on an injectable clock. §4.4 holds: one export is added, no import.
Step 80 needs no change.

Before building, seven things need to be written into the spec:

- the guest can make `session.run` raise (F1);
- a session keeps the host's descriptors for its whole life (F2);
- a session is one trust domain, and the spec never says so (F3);
- the lifetime choice loosens the owner's number (F4);
- 054's import path has no defined way into a session (F5);
- each turn's clock base must be the session's (F6);
- a write-back refused by the file-call limit loses data in a session (F7).

The rest are Low.

## Findings, most severe first

### F1. A guest can make `session.run` raise and end its session as a runner fault. High (EXECUTED in part, INFERRED)

Decision 7 says a turn result of −1, or any value outside −1 to 255, is a runner fault. The
session then ends `"error"`, and `run` raises `RuntimeError("wasi_python lost track of a
session")`. But the value comes from Python the guest controls. The C side reads it with
`PyLong_AsLong` and returns it, as `run` does today (READ, `reactor_main.c`). `_reactor` is in
`sys.modules`, and its functions can be replaced (EXECUTED, `pa_reactor_patch`: both binaries
printed `replaced: 300 -1`).

- **Failure.** Turn 1 runs `import _reactor; _reactor.turn = lambda s, e: -1`. Or it replaces
  `_reactor._exit_code` and then raises `SystemExit`. Turn 2 then returns −1, or 300.
  `session.run` raises `RuntimeError` instead of returning a `Completed`, and `ended ==
  "error"`.
- **Why it matters.** The guest has made the embedder's call raise. The 0.1.0a2 review made
  exactly that a release blocker (its F1). The README promises that nothing a guest does makes
  `run` raise. It also confuses the API: `"error"` and "lost track" are meant to name the
  runner's own bugs and the embedder's exceptions.
- **Fix.** The C export owns the range. Any Python result that is not an int in 0..255 becomes
  1, or its low byte, the same rule as `SystemExit`. Then −1 comes only from the C refusals,
  which this runner never triggers, and the runner's "lost track" rule stays correct.
  Optionally, C also keeps a strong reference to the original `_reactor.turn`, taken at
  initialization. That makes the entry point immune to replacement and to `del
  sys.modules["_reactor"]`, which would otherwise make every later turn fail.
- **Check.** A turn that sets `_reactor.turn` to return −1, then 300, then a non-int, is
  followed by a turn that returns a `Completed` (`exit_code` as decided), with `ended is None`
  and no raise. Stand-in: today's text, which raises.

### F2. A session keeps the host's file descriptors, and its host memory, for its whole life. Medium (EXECUTED for one call; INFERRED for a session)

- **What I ran.** One call's guest took every descriptor the host process had. Under a 1,024
  soft limit it opened 1,014 files. Under the default it opened 122,870. Either way, a
  `host=` function inside that call then failed `open()` with `EMFILE` (`pb_fd_exhaust`).
- **Why a session makes it worse.** For `run`, this is the known shared-table gap. The 0.1.0a2
  review's F11 recorded it, and the README's *Not protected* says so. But `run` holds the
  descriptors for one call: at most the deadline, 60 s by default. A session keeps its store
  (Decision 11), so it keeps them until it ends. That is up to 15 minutes after the last turn,
  or the full hour.
- **Failure.** In a multi-tenant embedder, one prompt-injected turn opens files in a granted
  folder until `EMFILE`, then stops. For the next 15 minutes, every other session's turn and
  every `run` in the process fails while it prepares (the zip, `_Private`, the lock files). So
  does the embedder's own I/O, sockets included.
- **The same holds for memory.** A session holds up to `memory_bytes` of linear memory, plus up
  to `memory_bytes` of mount staging on the host (Decision 11), for its life. By default that
  is 2 GiB.
- **The spec says neither.** §4.15 wants every limit to have a default, and descriptors have
  none.
- **Fix.** The minimum is to say it in Decision 11 and in the README's *Sessions* and *Not
  protected*: a session holds what its guest opened, and the memory it reached, until it ends.
  Give the advice: a short `idle_s` for untrusted code, and `close()` promptly. Also record a
  later specification for a cap on open descriptors per store. The mount and guard linkers
  already show how to shadow `path_open`. Whether that work blocks 0.1.0 is the owner's call.

### F3. A session is one trust domain, and the spec never says so. Medium (READ; EXECUTED that `_reactor` is reachable)

Every later turn runs inside whatever the earlier turns left behind. An earlier turn can hook
`_reactor`, `builtins`, `compile`, `exec`, `sys.displayhook`, `sys.excepthook`, `sys.settrace`
or `print`. So it can:

- read every later turn's source and data;
- rewrite what later turns print;
- make every later turn report exit 0.

It can also read the secrets that an earlier tool result or an embedder-written turn left in
memory.

- **Failure.** The embedder runs the model's code. It then sends its own turn,
  `assert ledger_ok()`, and trusts that turn's exit code. Or it sends a setup turn that holds a
  token. A prompt-injected earlier turn has already replaced the entry or `assert`'s
  machinery. The check passes, or the token is captured.
- **Fix.** Add this to Decision 20's README section and to *Not protected*:
  - a turn's output and exit status are only as trustworthy as the least trusted turn before
    it;
  - never send a more-trusted turn after less-trusted code;
  - what any turn or tool put in the guest stays readable for the rest of the session.

  F1's C fix narrows the worst case. It cannot close this, because the guest is the whole
  interpreter.

### F4. Owner choice 3, "a running turn is never cut by the lifetime", loosens the owner's 1-hour lifetime. Medium (READ)

- **The conflict.** Terms define the lifetime as "the longest a session may exist". Decision 20
  set it at 1 hour. Decision 9 lets a session exist for lifetime plus one turn's deadline.
- **The bound is not tight either.** The mount write-backs after the turn are not under the
  deadline (`walk` makes no deadline check, READ, and the 0.1.0a4 review measured a provider
  holding a run 3 s past its deadline). Neither is a blocking raw `host=` function or provider.
  So "at most its lifetime plus one turn's deadline" is not exact.
- **Who decides.** §4.15's last sentence says a loosened default needs the owner's decision,
  not only a review. The other three choices are sound. `SystemExit` keeps the session, as
  Jupyter does. Closing is a stop, which is tighter. The echo is not a limit. Going ahead with
  them is consistent with §5.2: they are decided, with reasons, and recorded for the owner.
- **Fix, one of two.** (a) The build waits for the owner's answer to question 92, item 3. 055
  is last in the build-class queue, so that probably costs nothing. Or (b) tighten the rule:
  no turn starts at or after the lifetime, and each turn's deadline is capped at the lifetime
  left. Either way, reword the Terms and Decision 9: "no turn starts after the lifetime; a turn
  running then ends by its own limits, and the session ends as it returns, after its
  write-backs."

### F5. Spec 054's `import_path=` has no defined way into a session. Medium (READ)

- **The gap.** Decision 5 says `import_path=` is "applied at the first turn as `run` applies it
  before its program". But 054 applies it through argv: a one-line `-c` prelude that calls
  `_reactor.run` again (054, Decision 7). A session has no argv, since WASI fixes it at
  `[ARGV0]`, and `turn` takes source, not argv. So there is nothing to copy.
- **Failure.** Each obvious improvisation leaks. Code prepended to turn 1 shifts `<turn 1>`'s
  line numbers and appears in its traceback. A hidden setup turn consumes the guest's
  `<turn N>` count and pollutes turn 1's output and fuel. And no criterion covers
  `import_path=` in a session.
- **Fix.** Pick the mechanism now. 055 rebuilds the bootstrap anyway, which 054 itself
  foresaw ("the mechanism may move into the guest"). One option: the runner passes the entries
  to the first `turn` through a field the bootstrap reads. Another: a setup step that is not
  numbered and whose output is discarded. Then add a criterion: a session with
  `import_path=[ro grant]` imports from it in turn 1, and its traceback shows `<turn 1>` lines
  as written.

### F6. Each turn's clock base must be the session's `origin_ns`. Medium (EXECUTED in part, INFERRED)

- **The mechanism.** The guest's `time.sleep` reaches `poll_oneoff` with an absolute monotonic
  clock (EXECUTED, `pd_sleep_abstime`: `ABSTIME=True`, guest 122 ms against the runner's
  72 ms plus the 50 ms sleep). The runner turns that into a wait by subtracting
  `perf_counter_ns() - origin_ns` (READ, `_poll_oneoff`). wasmtime's monotonic clock counts
  from the store's WASI context, which a session makes once, at the opening (Decision 6).
- **The gap.** Decision 7 lists what each turn builds ("its `stop_at`, waits and checks", a
  `_Call`) but never says that `origin_ns` belongs to the session. Today `_instance` takes it
  fresh for each call.
- **Failure.** A builder who copies `_instance` takes `origin_ns` per turn. Then, an hour into
  a session, `time.sleep(1)` computes a wait about an hour long. The deadline cuts it, the turn
  ends `"deadline"`, and the session dies.
- **Fix.** Put `origin_ns` in Decision 6's per-session list. Add a unit check: drive
  `_poll_oneoff` with its injectable clocks and a turn whose `_Call` was built after the
  session clock advanced, and assert that the wait equals the requested relative time.

### F7. A write-back refused by the file-call limit is marked clean, so a session loses it quietly. Medium-low (READ)

- **The code.** `_Files.walk` refuses a write-back past the limit, records the refusal, and
  then sets `entry.dirty = False` (READ, `mounts.py:526-530`). For `run`, the ending is final,
  so that is correct.
- **Failure in a session.** Turn N's write-backs run past `max_file_calls`. The file stays
  open, and its buffer is now "clean". Unless the guest writes to it again, the provider never
  receives those bytes, while the guest believes the file is written. Decision 11's "its buffer
  is clean afterwards" and "an owed buffer is dropped once written" describe exactly this
  behaviour.
- **Fix.** In a session, a refused write-back stays dirty, and an owed buffer stays owed, for
  the next turn's ending, or for the close if the spec wants that. Add it to criterion 18.

### F8. The export should defend itself, for any embedder. Low (READ, INFERRED)

Decision 2 tells a host never to call `turn` after a trap, and never re-entrantly, but the
guest does not enforce either. The fix is cheap:

- **An `in_turn` flag.** Set it when `turn` starts and clear it when `turn` returns normally. A
  trap or `proc_exit` unwinds without running C, so the flag stays set. The next `turn`, a
  re-entrant `turn` from a door callback, or a `turn` after a trap then returns −1 with no
  Python run.
- **Copy, then free.** Copy the buffer into a `bytes` and free it before any Python runs, so a
  2 GiB turn does not hold twice its size.
- **Say what `turn(0, 0)` does:** an empty turn that returns 0.
- **Fix the bounds check.** Decision 7's host-side check must read `p + len <= memory size`,
  not "a pointer within memory". `_door` already does this.

Add the re-entry and after-trap refusals to criterion 2.

### F9. The collector's finalizer and the reaper need a lock discipline. Low (INFERRED)

- **The risk.** A `weakref.finalize` callback runs wherever the collector fires: on any thread,
  inside another session's host function, or on the reaper while it holds a state lock or the
  registry lock. If the finalizer takes a session's state lock and closes the store there,
  that can deadlock, or close a store inside an unrelated turn's host call.
- **Fix.** Write in Decision 13 that the finalizer only marks the state dropped and wakes the
  reaper, which closes it on its own thread. Also: the exit hook stops the reaper, and waits
  for its current step, before it closes sessions at rest. The `_outputs_lock` comment shows
  this project has already met a finalizer that runs inside a locked block.

### F10. Concurrency details to write in. Low (READ)

- **`ended` is set once.** The first cause sets it under the state lock. The reaper sets
  `ended` under the lock before it closes anything, so a racing `run` sees `SessionEnded` and
  never a closed store.
- **`busy` is always released.** It is cleared in a `finally` on every path, so an unexpected
  host error cannot leave a session that the reaper skips forever.
- **`run_async` claims `busy` before it queues the turn**, inside the coroutine. That way a
  queued turn does not count as idle, and a second concurrent `run_async` fails at once.
  `busy` is released if the task is cancelled while queued.
- **A `cancel` already set before any guest code runs.** `_drive` returns `"cancelled"`
  without running the guest. Under Decision 8 that ends the session, although its interpreter
  is untouched. That is inconsistent with Decision 12's rule for a cancelled queued turn. Say
  which rule applies and why.
- **`close()` blocks.** It waits for a raw `host=` function or a provider call in flight to
  return. Called from a coroutine, it blocks that event loop. The docstring should say so.

### F11. Spec 053: one tool loop per turn breaks async tools that cache loop-bound objects. Low (READ)

- **The rule as written.** Under Decision 5, a sync `session.run` gives each turn 053's private
  loop, closed at the turn's end.
- **The conflict.** A session's tools persist across turns, but each loop would not.
- **Failure.** An async tool that makes an HTTP or MCP client on its first await, and caches
  it, works in turn 1. In turn 2 it fails, because the client is attached to a closed loop. The
  guest sees a `tool_error`.
- **Fix.** Decide one of two: either one private loop per session (its tasks cancelled at each
  turn's end, the loop closed at session end), or a README line saying a session's async tools
  must not cache loop-bound objects unless the session runs under `run_async` on one loop.

### F12. Spec 056 should come first, and its README text should cover sessions. Low (READ)

The 0.1.0a4 review's findings get worse in a session:

- **Its F2, a late gate's tool runs anyway.** In a session it can now run during a later turn
  of the same session, or after `close()`. A guest that got `ToolTimeout` and retried can then
  see both effects.
- **Its F1, a `partial`-bound credential.** It sits in the session's tool descriptor for the
  session's life.
- **Its F3, host CPU through frames.** It repeats every turn.

Add 056 to *Depends on*. Add to the README's abandoned-tools text: "…may land during a later
turn of the same session".

### F13. `exit()` and `quit()` close `sys.stdin` for the rest of the session. Low (EXECUTED)

site's `Quitter` closes `sys.stdin` before it raises `SystemExit` (`pc_exit_closes_stdin`).
Decision 4 keeps the session after `exit()`. From then on, every turn's `sys.stdin.read()`
raises `ValueError`, which contradicts Decision 5's "returns `""`".

- **Fix.** Document it in *Sessions*, or have the turn's setup bind `exit` and `quit` to a
  variant that does not close stdin. Either way, criterion 11 should use `exit()` as well as
  `sys.exit`.

### F14. Several criteria where the property is the point name no stand-in. Low (READ)

These criteria "fail first" today only because `Session` or `turn` is missing:

- 3: a turn that traps or ignores a NULL buffer;
- 11: a runner that ends the session on `SystemExit`;
- 12: a runner that keeps the session after an exit trap;
- 13 and 14: bounds enforced only by the reaper, or never at call time;
- 17: a `MemoryError` that ends the session;
- 18: write-backs only at close;
- 21: a `close()` that returns before the turn has returned;
- 24(c): no finalizer.

Name a stand-in for each, as criteria 1, 7, 8, 10 and 15 already do.

Also add criteria for:

- F1 (a guest-returned status out of range);
- F5 (`import_path=` in a session);
- F6 (the clock base);
- F7 (a refused write-back stays dirty);
- `close()` called on the turn's own thread, from a raw `host=` function.

### F15. Criterion 16's band rests on noise measured outside the runner. Low (READ)

- **Where the 9 came from.** The 9-instruction spread is E2's: the door-loop prototype inside
  one `run`. That prototype has no `ast` split, no echo and no `linecache` registration, and
  the memo traces its noise to inodes and the host clock.
- **Why 1,000 is still plausible.** It is 100 times that spread, and the check compares two
  sessions in one process on the snapshot, whose hash seed is fixed. INFERRED.
- **What is missing.** No Linux figure exists, and the judge runs there.
- **Fix.** The builder measures the spread of turns 2 to 6 through the real export, over
  several sessions, on macOS and Linux, and records it in the landing notes before the band
  is fixed.

## Questions the brief asked, answered

- **`turn(ptr, len)`.**
  - **Memory safety.** Ownership is clear: the buffer is always freed, and a negative length is
    refused. A NULL buffer is clean, because `host_alloc` returns 0 at the cap (the memo's P6,
    EXECUTED there). A huge length is bounded by the `i32` and by the memory cap. Re-entry and
    calls after a trap are covered by F8.
  - **After `run`.** `turn` returns −1, and `run` after `turn` returns 70. Both are sound.
  - **§4.4 holds.** One export is added, no import.
  - **The snapshot.** It behaves the same: Wizer keeps the export (memo P7, EXECUTED there).
    Only the heap layout moves, and Decision 19 says so.
- **State that leaks between turns.**
  - Turns persist `sys.modules`, monkey-patches, `os.environ`, open files and the working
    directory. That is by design, and it is the trust-domain point of F3.
  - The guest has no threads or signals.
  - `atexit` never runs. Decision 8 says so, and the README must too.
  - Grants are held by descriptor from the opening (READ: `preopen_dir` at the store, plus
    017's identity check). Swapping a folder on the host later does not redirect the session.
    That is correct.
  - Output, tool records, tool budgets and file counters are per turn. The abandoned-thread
    quota is per session. Both are sound.
  - Secrets a tool returned stay visible to later turns. The README must say so (F3).
- **Limits across turns.** A guest cannot start a turn, so every turn is an embedder call. A
  total for the session would be a cap on the embedder's own loop. Per-turn fuel, output, file
  and tool budgets, with no session total, are therefore acceptable under §4.15, provided the
  README says the limits are per turn. Memory per session is the right bound. The persistent
  host resources (F2) are what need saying.
- **No cap on sessions per process.** Acceptable. No default existed, so nothing is loosened.
  Sessions are opened only by explicit embedder calls, as concurrent `run` calls are, which are
  not capped either. `stats()["sessions_open"]` gives visibility.
- **Can a guest keep a session alive forever?** Not by itself. The lifetime counts from the
  opening, and the idle bound needs a turn the guest cannot start. A session outlives its
  bounds only through:
  - an explicit `deadline_s=None` on a turn;
  - a blocking raw host function or provider;
  - write-back time.

  F4 asks for the wording to match.
- **End states.** The table is right, apart from F1's guest-made `"error"` and F10's
  pre-cancelled turn. `close()` during a turn is race-free if F10's ordering is written in.
- **The four owner choices.** Choices 1, 2 and 4 are right, and going ahead on them is
  consistent with §5.2. Choice 3 loosens the owner's number (F4).
- **Interplay.** 053: F11. 054: F5. 056: F12. 049: Decision 17 lists the snapshot lines and
  the docstring rules. Keep its `Raises:` lists in step with F1. 049 has renamed
  `MAX_ABANDONED` to `_MAX_ABANDONED`, which the spec should use.
- **Process.** The spec has no open questions, is embedder-neutral (Jupyter is cited only as
  prior behaviour), and no check measures time. Criterion 23's 120 s is the existing fail-safe
  pattern.

## Constitution checks

- **§4.1:** a recipe change, no patch. Holds.
- **§4.4:** one export added, no import. Holds.
- **§4.6:** the artifact set's exports change, and the judge's export lists follow. Holds.
- **§4.9:** the checks use an injected clock, events and counts. Holds.
- **§4.15:**
  - the lifetime choice (F4) is a loosening and goes to the owner;
  - descriptors and host memory held per session need stating (F2);
  - all other limits have defaults.
- **§5.2:** no open questions.
- **§5.6:** this review.
- **§7:** nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

The author's answers are at `c25713c` on `spec/055-bounded-sessions`, in the spec's section
"Disposition of the pre-build review" and in `disposition.md` beside this file. Every finding is
taken and none is declined. In short:

- **F1:** fixed in the export (Decision 2). C calls the bootstrap's turn through its own strong
  reference. An int result becomes its low byte; anything else becomes 1. −1 comes only from
  C's own refusals. Check: criterion 32.
- **F2:** documented (Decision 11, Decision 20 *Sessions* and *Not protected*). A
  per-store descriptor cap is recorded as a later specification (Decision 22). Its place
  relative to 0.1.0 is question 92(b).
- **F3:** documented (Decision 11, Decision 20).
- **F4:** tightened by the lane's ruling (Decision 9). No turn starts at or after the
  lifetime. Each turn's effective deadline is the lesser of its own and the lifetime left,
  and `deadline_s=None` included. Criterion 14 checks it by armed ticks. The item is dropped from
  question 92.
- **F5:** decided (Decisions 3 and 5). The WASI argv carries the entries; the first
  turn's unnumbered setup appends them to `sys.path`. Check: criterion 30.
- **F6:** `origin_ns` is per session (Decisions 6 and 7). Check: criterion 31.
- **F7:** in a session, a refused write-back stays dirty, and an owed buffer stays owed
  (Decision 11). Check: criterion 18.
- **F8:** the `in_turn` flag; copy, then free; `turn(0, 0)`; the `p + len` check. Check:
  criterion 2.
- **F9:** the finalizer takes no lock and only wakes the reaper. The exit hook stops the
  reaper first. Check: criterion 24(c).
- **F10:** written into Decisions 7, 8, 10 and 12, with criterion 12(e).
- **F11:** one private tool loop per session for sync turns.
- **F12:** 056 added to *Depends on*, and the README text taken.
- **F13:** `exit` and `quit` are rebound to a `Quitter` subclass that leaves stdin open.
  Check: criterion 11.
- **F14:** stand-ins named for every criterion listed. Criteria 30 to 33 are added.
- **F15:** the spread is measured on both macOS and Linux before the band is fixed; a
  spread above 10 is a finding.

## Verdict

**Ready once F1 to F7 are written in.** That means F1's C-side clamp and its check, F4's owner
answer or tightening, and the documentation and spec text for F2, F3, F5, F6 and F7. F8 to F15
should be taken in the same revision, or answered in writing.

## One line

The session design is sound and keeps the wall, but the guest must not be able to make
`session.run` raise, a session's held descriptors and its single trust domain must be stated,
the lifetime choice goes to the owner, and 054's import path, the clock base and refused
write-backs need exact text before build.

## Confirmation (2026-10-18)

- **Checked:** `git diff 797aaf3 c25713c`, read in full: the spec and question 92. Each
  answer was held against its finding and against the code it names: `reactor_main.c`'s
  `run`, `_poll_oneoff`, `_Files.walk`, and `_epoch_ticker`, which catches up when a sleep runs
  long, so a capped deadline does not drift.
- **Re-ran:** against a fresh scratch copy of `build/sets/s-f94dec535086b06c`
  (`shasum -a 256 -c`: all OK), with `uv run --no-sync python -I` from the 055 worktree.
  - `pa_reactor_patch`: `replaced: 300 -1` on both binaries.
  - `pb_fd_exhaust` at a soft limit of 1,024: the guest opened 1,014 files, and the host's
    `open()` failed with `EMFILE`.
  - `pc_exit_closes_stdin`: `after: True`, then `ValueError`.
  - `pd_sleep_abstime`: `ABSTIME=True`.

  All four reproduce, so the facts the revision cites hold. Outputs are in `*.rerun.txt` in the
  reviewer's scratch folder
  (`/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/5c4a788f-6229-4fb4-8a87-05b4e7e5e695/scratchpad/055-review/probes/`).
  One new probe, `pe_pyerr_print_exits`, is described under N1.

### Each finding

- **F1, confirmed, with N1 below.**
  - Calling through a strong reference taken in `init_interpreter` survives both replacing
    `_reactor.turn` and deleting `sys.modules["_reactor"]`. On the snapshot the reference is a
    C static in the image Wizer captures, so it costs nothing at run time.
  - Taking the range on the C side closes the raise: no Python result can reach −1 or
    anything outside 0..255. Criterion 32 covers −1, 300 and a non-int, and names the right
    stand-in.
  - The spec's own narrowing is honest: `_reactor`'s helpers stay replaceable, which F3
    documents.
  - One gap remains, N1: the failed-call path, which still goes through `PyErr_Print`.
- **F2, F3: confirmed.** The text says what a session holds and for how long. It advises a
  short `idle_s` and a prompt `close()`. It states the trust rule both ways: a turn is only as
  trustworthy as the least trusted turn before it, and a more trusted turn goes in a new
  session. The cap is recorded as a later specification, and its timing is properly the
  owner's (92(b)).
- **F4: confirmed. No default is looser than the owner's hour.**
  - No turn starts at or after the lifetime.
  - Every turn's deadline, `deadline_s=None` included, is capped at the lifetime left.
  - The cap is computed from `_session_clock` and armed as epoch ticks. The ticker catches up
    to wall time (READ, `_tick`), so the cap does not drift.
  - What can still happen after the hour is exactly what `run` allows after its own deadline:
    embedder code already in flight, an abandoned tool's host thread, and write-backs bounded
    by the file calls left and the staging bound. None of that is guest code, and the promise
    says so.
  - Only an explicit embedder choice removes the bound: `lifetime_s=None`, or `set_defaults`
    with `session_lifetime_s=None`. That is §4.15's explicit choice, not a looser default.
  - The idle default (900 s) and the memory, output, fuel, file-call and tool-call defaults
    are unchanged.
  - Item 3 is gone from question 92, as it should be.
- **F5: confirmed.**
  - Putting the entries in argv and having the setup turn read them is clean. No line moves,
    no turn number is used, and the paths are checked at the opening by 054's rules.
  - Criterion 30 has the right stand-in.
  - Its fallback, "moves to 054 if 054 lands second", is sound.
  - See N3 for the contract text another embedder needs.
- **F6, F7: confirmed.** Criteria 31 and 18 each name the stand-in that today's code would be.
- **F8: confirmed.**
  - The `in_turn` flag is set at entry and cleared only on a normal return, so a trap or
    `proc_exit` leaves it set. That refuses re-entry and any call after a trap or exit, with
    no Python run.
  - `run` after a turn still answers 70, through `turned`.
  - Copy, then free; `turn(0, 0)` defined; the `p + len` check as `_door` makes it.
  - Criterion 2's stand-in (no flag, so the call after a trap runs Python) is the right one.
- **F9: confirmed, with N2.**
- **F10 to F15: confirmed.**
  - F10: a cancel set before any guest code now leaves the session untouched, which matches
    the queued-cancel rule. A `close()` still ends it.
  - F11: one tool loop per session for sync turns.
  - F13: rebinding to a `Quitter` subclass, checked through `exit(5)` and a later
    `sys.stdin.read()`.
  - F14: the stand-ins are named.
  - F15: macOS and Linux are both measured.

### New notes from the revision (Low; none reopens a finding)

- **N1. A failed call printed with `PyErr_Print` does not return 1 when the error is
  `SystemExit`. It finalizes and exits. Low (EXECUTED through today's `run`).**
  - **The cause.** CPython's `PyErr_Print` handles a pending `SystemExit` with `Py_Exit`:
    `Py_FinalizeEx`, `atexit` handlers, then `proc_exit`.
  - **How a guest reaches it.** It replaces a helper the strong-referenced turn function
    calls, such as `_reactor._exit_code` or a stream's `flush` (the bootstrap's `finally`
    catches only `Exception`), with one that raises `SystemExit`. That `SystemExit` then
    escapes the turn function.
  - **The probe.** `pe_pyerr_print_exits` does this through today's `run`, which has the same
    C shape. On both binaries the run ended `exit_code 9` and printed `atexit handler ran
    (Py_FinalizeEx)`.
  - **In a session**, that turn would end the session as `"exit"`. It would run the guest's
    `atexit` handlers and finalize, against Decision 2 ("anything else, a failed call
    included, … to 1"; "it never finalizes") and Decision 8 ("no `atexit` handler").
  - **What it is not.** It does not make `session.run` raise (F1's property holds), and a
    guest can end its own session with `os._exit` anyway. So it is a contract inaccuracy,
    not a hole.
  - **Fix.** One sentence in Decision 2: on a failed call, C fetches the exception and prints
    it without `PyErr_Print`'s exit handling, then returns 1. For example,
    `PyErr_GetRaisedException` with `PyErr_DisplayException`, or clear a `SystemExit` after
    printing it. Add one line to criterion 32: a turn that makes `_reactor._exit_code` raise
    `SystemExit` returns `exit_code == 1`, `ended is None`, and no `atexit` output.
- **N2. The finalizer's wake should be lock-free. Low (INFERRED).** "Takes no lock" must cover
  the wake too. `threading.Event.set` and `Condition.notify` take an internal lock, and the
  collector can fire while that same lock is held. Python documents `queue.SimpleQueue.put` as
  safe from weakref callbacks: use it for the wake, with `SimpleQueue.get(timeout=…)` as the
  reaper's wait. Criterion 24(c) already tests the registry lock.
- **N3. The export's contract should say what argv[1:] means. Low (READ).** Another embedder
  that puts ordinary arguments in a turn instance's argv would put them on `sys.path`. A
  relative entry resolves against the guest's working directory, which may be a writable
  root. Decision 20's fourth paragraph should say the entries are absolute, read-only
  folders, as 054 enforces in the runner. The guest's setup could also skip a non-absolute
  entry.

### Verdict

**Ready to build once N1's sentence and its criterion-32 line are written in.** No second review
is needed for that: the lane can check the two lines. N2 and N3 may be taken in the same edit or
by the builder. Every finding F1 to F15 is confirmed fixed. The F4 ruling leaves no default
looser than the owner's one-hour lifetime.
