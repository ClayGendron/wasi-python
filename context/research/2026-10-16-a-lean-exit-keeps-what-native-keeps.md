# A lean exit keeps what a native exit keeps, at a third of the cost

- **Status:** executed, 2026-10-16
- **Owner:** Clay Gendron
- **Researcher:** the author agent (Claude Opus 5.5), at the owner's request ("research and set up a spike for option 3": the middle path between full finalization and skipping it).
- **Feeds:** a specification that changes `run`'s exit (spec 003 Decision 6 says `run` calls `Py_FinalizeEx()`; changing that is a change to the guest, so it is reviewed before it is built).
- **Evidence:** `2026-10-16-the-lean-exit-spike/` (the variant reactor, its build script, the measuring script). Outputs go to `build/spike-lean-exit/`; nothing in `recipes/` or `build/artifacts/` changes.
- **Machine (benchmark facts only):** Apple arm64, macOS 26.5, wasmtime 49.

## The question

`run` ends with `Py_FinalizeEx()`, which costs about 74 of the snapshot call's 118 million instructions (spec 003's landing notes). Each instance runs one program and is then thrown away, so most of that work tidies memory nobody will read. Which parts of a native exit does a program's user actually rely on, and how cheaply can the guest do just those?

## Method (EXECUTED)

A copy of the reactor whose exit is chosen per run by `WASI_PYTHON_EXIT_MODE`, linked against the landed build and snapshotted with Wizer. Each mode adds one step to the one before it:

| mode | what the exit does after the program |
|---|---|
| 0 | `Py_FinalizeEx()` (today) |
| 1 | flush stdout and stderr, nothing else |
| 2 | 1, after running the `atexit` handlers |
| 3 | 2, after clearing `__main__` and collecting cycles |
| 4 | 3, after clearing every module imported during the run, newest first |
| 5 | 3, after closing every open file object the collector can see |
| 6 | 5, with the plain reactor's start-up heap frozen when `run` begins (the snapshot's is already) |

Ten small programs, each checking one thing a native exit does, ran under every mode on both binaries through the judge's driver, so fuel (instructions executed) is exact. The full table is `2026-10-16-the-lean-exit-spike/measure-output.txt`.

## Findings

1. **Mode 6 keeps everything mode 0 keeps, and one thing more** (EXECUTED, both binaries): an unflushed `print`, a file left open in `__main__`, an `atexit` handler, a file held open by an imported module, and logging to a file all reach their bytes. A `__del__` of an object in `__main__` also runs. Full finalization loses that one, with `NameError: name 'open' is not defined`, because builtins are torn down first.
2. **Both exits lose the same two things, and so does native CPython** (EXECUTED: the pinned host Python 3.14.8, run the same way): a file left in a reference cycle is never flushed, and the `__del__` of an object an imported module holds fails with the same `NameError`. Mode 6 loses the second silently, where native and mode 0 print "Exception ignored". Neither is a guarantee to keep.
3. **The cheaper modes lose real data** (EXECUTED): mode 1 loses unclosed files and `atexit` handlers; mode 2 still loses unclosed files; mode 3 loses files held by imported modules.
4. **Clearing modules (mode 4) is rejected.** It keeps everything, but on the plain reactor it costs more than full finalization (582 against 247 million instructions for `-c pass`) and writes errors to stderr.
5. **The costs, `-c pass`** (EXECUTED, fuel; wall time a benchmark fact, median of seven):

   | binary | mode 0 (today) | mode 6 |
   |---|---|---|
   | snapshot | 117.7M instructions, 20.8 ms | 45.3M, not timed (mode 5: 44.7M, 5.7 ms) |
   | plain reactor | 247.2M, 31.8 ms | 230.3M |

   The snapshot call is about 3.6 times faster. On the plain reactor, mode 5 cost more than mode 0 (257.8M), because finding open files walks the whole heap; freezing the start-up heap first (mode 6) brings it below mode 0.
6. **On a heavier job the gain shrinks to a few percent** (EXECUTED, the pandas golden job): snapshot 788.8M to 722.7M (−8%); plain reactor 5,625M to 5,676M (+0.9%), since the heap the job builds is walked to find its files. The walk grows with the objects a program leaves alive, so the lean exit suits the project's stated load, many light programs (constitution §3), best.

## What it decides

Mode 6 is the candidate for a specification: run the `atexit` handlers, clear `__main__`, collect cycles, close every file object still open, flush stdout and stderr, and return without `Py_FinalizeEx()`; freeze the plain reactor's start-up heap at the start of `run`. The specification states the one documented difference from a native exit (a module-held object's `__del__` is not run, silently) and keeps a check per kept guarantee, on both binaries. A cheaper way to find open files (tracking them as they open, instead of walking the heap) is left for when heavy jobs matter.

## One line

Doing only the exit work a program can observe keeps every guarantee full finalization keeps and cuts the snapshot's call from about 21 ms to about 6 ms.
