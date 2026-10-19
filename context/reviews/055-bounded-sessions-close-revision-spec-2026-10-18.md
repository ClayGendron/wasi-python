# Re-review of spec 055's revision before build: sessions close as Jupyter does

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). It wrote none of the specification, the
  revision, the memo's section 8 or its probes. This is the short pre-build re-review §5.6 asks
  for, since the revision adds a guest export (`shutdown`).
- **Reviewed:** `spec/055-bounded-sessions` at `ddc3fff`, the diff `434a811..ddc3fff`:
  `context/specifications/055-bounded-sessions.md` (the section "Revised for the owner's
  decision of 2026-10-18 (92)" and every Decision and criterion it touched: the Terms, Decisions
  2, 4, 5, 6, 7, 8, 9, 10, 11, 13, 17, 19, 20, 22, the Intent, Design, Scope, criteria 4, 6, 7,
  12, 21, 24, 26, 32 and 34–40), and `context/research/2026-10-18-bounded-sessions.md` section 8
  with probes p9, p10, p10b, p11 and p12. The rest of 055 was confirmed earlier
  (`context/reviews/055-bounded-sessions-spec-2026-10-18.md`) and is not re-reviewed.
- **Read:** `AGENTS.md`; the constitution §4.15 and §5.6; `context/decisions.md`, "The owner's
  answers of 2026-10-18, evening", bullet 92; `recipes/reactor_main.c` (`init_interpreter`,
  `wizer_initialize`, `run`); `src/wasi_python/runner.py` (`_register_exit_hook`,
  `_stop_async_calls`, `_release`, `_epoch_ticker`); spec 034's Decision 8; spec 069's draft in
  `../wasi_python-069` (Decisions 4 and 11); ipykernel 7.2.0 and IPython as installed in
  `/Users/claygendron/Git/Repos/vfs/.venv-ci/3.12` (`ipykernel/zmqshell.py`,
  `IPython/core/autocall.py`, `IPython/core/interactiveshell.py`).
- **Executed:** scripts and outputs beside this file. They ran with `uv run` from the main tree
  against the frozen set `build/sets/s-4eb5418a2b1bb553-c353b1d9` (through
  `WASI_PYTHON_ARTIFACTS`). Nothing was written in either git tree.
  - `r1_probe.py` / `r1_probe.txt`: `gc.unfreeze()` placed where the export puts it (before the
    `atexit` handlers, not as the last handler as P12 did), on both binaries; a handler that
    re-freezes; files held by a class instance and by a frozen module's dict; wall time of the
    whole run (a benchmark fact, not a check).
  - `r2_threads_at_exit.py`: whether an exit hook may start threads, on CPython 3.11, 3.12,
    3.13 and 3.14.
  - Native CPython 3.12 and 3.14, inline: a file held only in a self-cycle, and a left-open file
    beside a `def`, at a normal exit.
  - `gc` in `sys.modules` at a program's start, both binaries, through today's `run`.
- **Scoreboard:** not re-run. The diff holds documents and probe scripts only (`git diff --stat`
  shows nothing outside `context/`).

Labels: **EXECUTED** (I ran it), **READ** (code or document), **INFERRED** (reasoned, not run).

## Short version

The revision is sound and follows the owner's answer. The new export is small and well
defended: its three refusals are the right ones, the `shut` flag set before any Python runs
closes the re-entrant path, and no `PyErr_Print` is reachable. The unfreeze is the right fix and
I reproduced it at the export's own placement. The two-attribute design holds. Three things
need writing in before the build: `exit()` and `quit()` do not keep a Jupyter kernel, though
Decision 4 says the session follows Jupyter there; the lifetime's "exact promise" is not exact,
because the ending's deadline is armed from its start, not capped; and the rule for when the
shutdown runs contradicts the table for a turn that returns normally after `close()` or exit
has marked it. Five low findings and a few notes follow.

## Findings, most severe first

### F1. `exit()` and `quit()` shut a Jupyter kernel down; the session keeps them as `SystemExit`. Medium (READ)

**Evidence.** In ipykernel 7.2.0, the shell's `exit` and `quit` are the same object, a
`ZMQExitAutocall` (`IPython/core/interactiveshell.py:1411-1412`: `ns['exit'] = self.exiter`,
`ns['quit'] = self.exiter`; `ipykernel/zmqshell.py:550-554`). Calling it with no argument sets
`keepkernel_on_exit = False` and calls `ask_exit()` (`IPython/core/autocall.py:68-70`), which sets
`exit_now = True` (`zmqshell.py:651-653`). The observer stops the kernel's IO loop
(`zmqshell.py:556-566`), and the process leaves through Python's normal shutdown, as the memo's
section 8 describes for a requested shutdown. So in Jupyter, `sys.exit()` keeps the kernel and
`exit()` / `quit()` end it gracefully. Decision 4 groups all of them: "`raise SystemExit(3)`,
`sys.exit(3)`, `exit()` and `quit()` make the turn return their exit status … the session goes
on", and justifies it with Jupyter. Decision 20's README line says "the echo, `SystemExit` (both
as in Jupyter)". The owner's answer names only `sys.exit()`, and its rule is to follow
precedent, "especially that of Jupyter". The plain REPL agrees with Jupyter: `exit()` ends it.
Before this revision a session had no graceful ending, so the question did not arise. Now it has
one, and the precedent points the other way for `exit()` and `quit()`.

**Fix.** Decide it in writing. Either (a) follow Jupyter: the rebound `exit()` / `quit()` make
the turn return its status and then end the session, with its ending running Python's shutdown
on the turn's thread, as for a turn that finished after the lifetime (a promised `ended` value
for it, say `"closed"` or a new `"quit"`; criteria 32 and 36's pattern cover it); or (b) keep
today's text, say plainly in Decision 4 and the README that this is where the session differs
from Jupyter and why (an agent's `exit()` at the end of a script is as habitual as
`sys.exit()`), and record it for the owner. Option (b) is defensible; what is not is the claim
that the current rule is Jupyter's.

### F2. The lifetime's "exact promise" holds only if the ending starts on time. Medium (READ, INFERRED)

**Evidence.** Decision 9: the ending "starts at the earliest when the lifetime passes and runs
no guest instruction later than its start plus `shutdown_s` … So no guest instruction of the
session runs later than the opening plus the lifetime plus `shutdown_s`." The conclusion needs
the start to be *at most* the lifetime, not at least. The ending's deadline is armed when the
ending starts (Decision 8: "both armed by the host before the export is called"). An expiry at
rest starts after the reaper wakes, takes the lock and starts a closer thread; a reaper delayed
by the GIL, a long step or a suspended machine starts it later; a `close()` at rest after the
lifetime has passed but before the reaper ran starts it whenever the embedder calls. Each runs
guest code until start + `shutdown_s`, past the promised bound. The old promise had no such
gap, because past the lifetime no guest code ran at all and a turn's deadline was capped at the
lifetime left (F4's ruling). This promise is the one §4.15 and the lane's ruling care about.

**Fix.** Cap the ending's deadline as the turn's is capped: arm it at
min(start + `shutdown_s`, opening + lifetime + `shutdown_s`), and skip the shutdown
(`"skipped"`) when that is not in the future. Then the promise is exact, to a tick, whatever
the reaper's latency. A fake-clock check is enough (criterion 36: a reaper step at lifetime + X
arms a deadline of `shutdown_s` − X ticks, or skips when X ≥ `shutdown_s`).

### F3. The shutdown's rule and Decision 8's table disagree for a turn that returns normally after `close()` or exit marked it. Medium (READ, INFERRED)

**Evidence.** The rule: the shutdown runs "when all of these hold: the session is at rest; at
least one turn was called; the last turn returned normally …; `shutdown_s` is above 0; and this
is not a process forked … The cause matters only through those." The table: "`close()` during a
turn → no guest code: the stop unwound the interpreter", and Decision 13: a session whose turn
is still running at exit "is closed when that turn returns, and its ending runs no guest code".
But `close()` from another thread stops the turn "within `CANCEL_TICKS` ticks of compute, or at
the end of a wait or a tool call" (Decision 10), and a turn on its way out can return normally
first. A raw `host=` function that calls `close()` near the end of a turn does the same. Then
the interpreter is sound, the rule says shutdown, and the table says none. Decision 7 step 6
names only the lifetime case as a turn whose ending runs guest code. The builder must guess
which thread runs it (the waiting `close()` or the turn's) and which outcome criterion 21 and
39(c) expect in the race.

**Fix.** Write one rule and make the table follow it. Either the interpreter's state decides
(a turn that returned normally leaves a sound interpreter, so its ending runs the shutdown, on
the turn's thread before `run` returns, as in the lifetime row; the table's rows become "`close()`
during a turn, stopped" and "…, finished first"), or the moment decides (an ending whose `ended`
was set while a turn ran skips the shutdown, except the lifetime row). Either is fine. State it
in Decision 7 step 6, Decision 8's rule and table, Decision 10 and Decision 13.

### F4. The ending's write-back runs after a Ctrl-C or an embedder `BaseException`; spec 034's walk does not. Low (READ)

**Evidence.** Decision 8 step 4 hands the mounts' dirty buffers over "on either outcome", and
step 3 counts "a Ctrl-C, a `BaseException` from the embedder's own code" as `"stopped"`. Spec
034's Decision 8 writes back "at every ending that returns a `Completed`", and its walk "checks
… the deferred Ctrl-C". A `run` that raises makes no walk. So after the user's Ctrl-C the
ending keeps calling the embedder's providers, and after a provider raised a `BaseException`
the ending calls providers again, before `close()` re-raises.

**Fix.** Write back after `"finished"` and after a budget stop or a trap (the endings that would
return a `Completed` for a turn), and through the walk's own path with its deferred-Ctrl-C
check; not after a Ctrl-C or an embedder `BaseException`. Add the case to criterion 35 or 38
(a host function that raises `KeyboardInterrupt` in a handler: `close()` raises it after
`sessions_open` falls, `shutdown_outcome == "stopped"`, and the provider received nothing).

### F5. Criterion 37(a) does not prove that the fuel bounds the ending, or that it is the session's fuel. Low (READ)

**Evidence.** 37(a) opens a metered session with `fuel=10**9` and the default `shutdown_s` of
5 s, and a handler that loops forever. An ending armed with no fuel at all is still stopped, by
the deadline, so 37(a) passes on the wrong runner. Its one stand-in covers (b) only. Nothing
checks that the ending's fuel is the session's per-turn fuel rather than some other figure,
which is what Decision 8 promises.

**Fix.** In 37(a) pass a `shutdown_s` the fail-safe would hit first (say 600, under a child's
120 s fail-safe), and add the stand-in "an ending armed without fuel (the child hits the
fail-safe)". Add a case that pins the figure: a handler that burns a known count between a small
fixed share and the session's fuel finishes; the same handler in a session with fuel below its
count is `"stopped"`.

### F6. The `"finished"` checks depend on wall time under the default 5 s. Low (READ, EXECUTED)

**Evidence.** Criteria 21, 24(b), 24(c), 35, 36 and 40 assert `shutdown_outcome == "finished"`
with the default `shutdown_s` of 5 s. Whether a 0.31 G-instruction shutdown fits in 5 s is a
wall-clock fact. It does with room here (EXECUTED, `r1_probe.txt`: the whole snapshot run with
the unfreeze took 0.35–0.58 s on darwin-arm64; the plain reactor's 0.3 G shutdown after pandas
is a similar share), but a loaded Windows release runner is the case rule 6b warns about.
AGENTS.md: tests count operations, never wall-clock.

**Fix.** Those checks pass a generous `shutdown_s` (60, under the 120 s fail-safe), so the
outcome is decided by the guest's work, not the machine's speed. Criterion 4 already checks the
default's value.

### F7. The ending calls embedder code on runner threads; its context, loop and timing are unstated. Low (READ, INFERRED)

**Evidence.** The original text gave, as one reason for closing as a stop, that the reaper and
the collector run "on threads where running guest or provider code would be wrong". Closer
threads answer the thread half. Three things remain unwritten. (1) Which `contextvars` context
the ending's host functions, tools and gate see: `run_async` copies the caller's context so a
door host sees the request's; a closer thread has none. (2) Which tool loop an async tool uses
in the ending: the sync session's private loop must close after the ending, not at `ended`; a
`run_async`-driven session's caller loop may be stopped or closed by then. (3) That a dropped
session's handlers call host functions after the embedder let go of the session, and that at
process exit the runner's hook runs after every `atexit` handler the embedder registered later
(last in, first out), so a provider those handlers already closed sees writes. Each is bounded
by `shutdown_s` and `"stopped"`, so this is clarity, not safety. (EXECUTED, `r2_threads_at_exit`:
starting a closer thread from an exit hook works on 3.11 to 3.14, so the design is buildable.)

**Fix.** One paragraph in Decision 8 ("Where it runs") and a sentence in the README: the context
is a copy taken at the opening (or none, stated); a sync session's private loop is closed after
the ending; a `run_async` session's ending uses no caller loop, so an async tool there is
answered as a tool error or at the deadline; endings of dropped sessions and at exit may call
embedder code after the embedder's own cleanup.

### F8. Two gaps in the exit hook's text. Low (READ, INFERRED)

**Evidence.** (1) A session collected shortly before exit has its state on the collector's
`SimpleQueue`, not yet taken by the reaper. The exit hook "stops the reaper and waits for its
current step, then ends every session at rest", but does not say it drains that queue; the
reaper holds sessions weakly, so that state is in no list the hook walks. Before the revision
this only left folders for spec 016's sweep; now it also skips that session's `atexit`
handlers. (2) "The host's exit therefore waits at most the largest `shutdown_s` among them, plus
any embedder call in flight" omits the ending's mount write-backs, which Decision 8 ("a closer
lives for … plus the ending's mount write-backs") and 034 bound by calls and bytes, not time.

**Fix.** The exit hook drains the collector's queue after stopping the reaper and ends those
sessions too; the exit sentence adds "plus the endings' mount write-backs".

## Notes (none blocks the build)

- **N1. Taking the `gc.unfreeze` reference in `init_interpreter` changes the plain reactor's
  `run`** (EXECUTED: today `'gc' in sys.modules` is `False` at a program's start on the plain
  reactor and `True` on the snapshot). `PyImport_ImportModule("gc")` in `init_interpreter` adds
  it for every plain `run`, against Decision 1 ("`run` keeps exactly its behaviour") and
  criterion 20, at a small fuel cost. Take the reference at the start of the first `turn`, before
  any guest code (the same strength: no guest code has run), or on the snapshot only at Wizer
  time.
- **N2. `shutdown` returns 1 for a failed finalization; `run` returns 120** (READ,
  `reactor_main.c:357-358`, CPython's own convention). The runner treats both 0 and 1 as
  `"finished"`, so nothing breaks; returning 120 would keep one convention in the C file and
  for other embedders.
- **N3. A runner fault in the ending is quiet.** A return outside 0 and 1 becomes `"stopped"`,
  where a turn's raises `RuntimeError("wasi_python lost track of a session")`. Defensible
  (`close()` and expiries have no good place to raise), but say why in Decision 8 step 3.
- **N4. "Small" fuel.** The owner asked for "a small fuel and time budget". The ending takes the
  session's per-turn fuel, which may be large, or none. The time budget is the small one; the
  spec's reason for not fixing a small fuel share is sound (P9: 28 M to 303 M). Say in "The
  owner's choices" that this is how "small" was read, so the owner can see it.
- **N5. Memo wording.** The research list says the shutdown "flushes open files on the snapshot
  only once `gc.freeze()` is undone"; P10 shows it flushes them unless a function is defined in
  `__main__`. The cycle caveat's citation ("Memory tied up in circular references … is not
  freed") is about memory, not finalizers; the claim itself is right (EXECUTED: native CPython
  3.12 and 3.14 also leave a self-cycle file at 0 bytes while flushing a left-open file beside a
  `def`). The README's "is not flushed, as in CPython" can stay; "may not be" is more exact.
- **N6. Spec 069** keeps `gc.collect(); gc.freeze()` in `wizer.initialize` (READ, 069 Decision 4),
  so the unfreeze stays needed after it, and its cost falls with the frozen heap. 069's bullet
  for 055 (Decision 11) predates this revision and names only the first-turn figures; it should
  also name the ending's fuel figures, which 055 already says are re-measured.

## The brief's questions, answered

1. **The export.** Its refusals are right and complete for this runner: no turn yet (`turned`
   unset, which covers `run` and a fresh instance), `in_turn` (a running, re-entrant or unwound
   turn), and `shut` (a second call, including from the door during the shutdown, which CPython
   forbids). `shut` set before any Python runs, and `turn` and `run` both checking it, closes the
   re-entrant paths (READ). No `PyErr_Print` is reachable: an error from the unfreeze call is
   displayed and dropped, and an exception in an `atexit` handler is printed by `atexit` itself,
   which ignores `SystemExit` (P9's `sys.exit(7)` case, READ). The cost (about 85 M to 310 M on
   today's snapshot) matches P12 and my probe (EXECUTED: 308.7 M with the unfreeze at the
   export's placement, 83.9 M without). See N1 for where the reference is taken.
2. **Order and outcomes.** `ended` first, then the call, then the outcome, then write-back, then
   close and release: right, and F10's ordering is kept. Exempting the ending's own call from
   the "closing" stop is necessary (otherwise every `close()` would stop its own shutdown at
   once) and safe, since the deadline and fuel still bound it. F3 and F4 are the gaps.
3. **`shutdown_s`.** Refusing `None` is right: the runner starts endings itself, and an
   unbounded one would hold a thread, memory and the host's exit. 5.0 matches jupyter_client's
   `shutdown_wait_time` (READ in the memo; I did not re-fetch it). Fuel from the session is
   reasoned well (N4).
4. **Closer threads and the exit hook.** Buildable (EXECUTED: threads start from exit hooks on
   3.11–3.14) and the epoch ticker is a daemon thread that keeps running through `atexit`, so
   the deadline still fires at exit (READ, `_epoch_ticker`). F7 and F8 are the gaps.
5. **The lifetime and §4.15.** The loosening by `shutdown_s` is the owner's decision ("at close
   and at expiry … inside a small … time budget"), and `shutdown_s=0` restores the old promise,
   so §4.15 is met. The arithmetic needs F2's cap to be exact.
6. **Write-back at the ending.** Bounded as at a turn's end, and the loss of a refused write-back
   is stated honestly. F4 aligns it with 034's Ctrl-C rule.
7. **Two attributes.** Sound: `ended` must be set before the ending (F10) and the outcome is
   known only after, so one set-once string cannot carry both. No defect.
8. **Criteria 34 to 40.** They cover the export raw, close, expiry, hostile handlers, no code
   after a stop, no shutdown after a trap, and the cap, each with a stand-in that fails the wrong
   runner, except as F5 and F6 say. Missing: F2's capped deadline, F3's race, F4's Ctrl-C case,
   F8's queued session.
- **The unfreeze finding.** Right cause, right fix, and proven at the export's placement.
  P10b shows the loss needs a `def` in `__main__` on the snapshot only; P12 shows the unfreeze
  restores the plain reactor's behaviour when run as the last handler; I ran it before the
  handlers, where the export puts it, and the file keeps its 100 bytes, also when held by a class
  instance or a frozen module's dict (EXECUTED, `r1_probe.txt`). The INFERRED cause (`__main__`'s
  dict frozen in the permanent generation, so the dict ↔ function cycle is never collected and
  the file never finalized) fits every variant. A handler that calls `gc.freeze()` again loses
  the bytes on both binaries (EXECUTED); that is the guest's own choice, as in CPython. Criteria
  34 and 35's stand-ins (an export without the unfreeze) will prove it on the built set.
- **The divergence after a trapped or stopped turn** is stated honestly and correctly (Decision
  8, "Why a turn that traps …"; Decision 22): Jupyter's SIGINT becomes `KeyboardInterrupt` and
  unwinds through Python; the guest's epoch stop is a trap. The README's advice to close files
  within a turn follows. F1 is the divergence that is not stated.
- **Fit with 069.** Good (N6).

## Constitution checks

- §4.1: the export is a recipe change in `reactor_main.c`; no upstream patch. Holds.
- §4.4: no new import. Holds.
- §4.15: every limit of the ending has a default and is the embedder's to set; the loosened
  lifetime is the owner's decision. Holds, with F2 for exactness.
- §5.6: this is the re-review it asks for.
- AGENTS rule "tests count operations": F6.

## Verdict

**Ready once F1 to F3 are written in.** F4 to F8 are low: write them in or answer them in the
disposition. The notes need no answer.

## One line

A sound revision with a well-defended `shutdown` export and a proven unfreeze; before the build,
decide `exit()`/`quit()` against Jupyter, cap the ending's deadline so the lifetime promise is
exact, and make one rule for a turn that finishes after `close()`.
