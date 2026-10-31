# 164: Output while the guest runs, and stdin for a turn

- **Status:** drafted 2026-10-30, to be reviewed before it is built (a change to the public API, the guest's exports and the build recipe: constitution §5.6). The owner chose it on 2026-10-30 (`../decisions.md`, "The scope of 0.1.3").
- **Date:** 2026-10-30
- **Owner:** Clay Gendron
- **Kind:** public API and **build-class**; **not structural** by spec 108's letter: no module-level mutable or lock, no private wasmtime-py name, no platform branch, no seam off the process object, no module past its ceiling; the listed lengths of `runner.py:run`, `run_async` and `Session.run_async` rise, claimed (spec 142). The pre-build review still reads Decision 2 against the rubric, since it adds a path from the output reader to the calling thread. `src/`: `_outputs.py`, `_call.py`, `_sessions.py`, `runner.py`, `cli.py`, `__init__.py`. Recipe: `recipes/reactor_main.c` (the export `turn_input`), `recipes/reactor_bootstrap.py` (`turn` takes the turn's stdin). Both binaries, `MANIFEST` and `SHA256SUMS` change; the zip does not. No pin, no patch.
- **Depends on:** landed 015 (run from async code), 055 (sessions), 078 (the guest's own thread and its home), 129 (output from a pipe), 142 (the allowance). In flight: 163 (the same entry points, `reactor_bootstrap.py`'s `turn`, and `_Stream.written`: Decision 12), 162 (a checkpoint never holds a turn's stdin: Decision 9). Not 153 (Decision 10).
- **Research it stands on:** `../research/2026-10-30-what-0-1-3-could-carry.md` (§1, "Stdin landed everywhere this month" and "Rich results and streaming"; §2, item D). wasmtime's source, READ in the prior-art clones of 49.0.3 and of `main` at `2d9c19b`, which agree, so 50.0.1 is INFERRED to: `crates/c-api/src/wasi.rs:117-131` and `crates/wasi/src/p2/pipe.rs:150-190`.

Labels: READ means read from a file, cited; INFERRED means reasoned.

## The problem

A call returns its output once the guest has ended (`src/wasi_python/_call.py:551-562`). A long run's progress reaches the agent only at its end, or never, if the deadline comes first. A session turn's `input()` reads an empty stream: the session's stdin is an empty file, written once at the opening (`src/wasi_python/_sessions.py:1057-1059`), and `Session.run` has no `stdin` (`src/wasi_python/runner.py:1146`). And a stream past `output_bytes` keeps its head (`_outputs._Stream.write`, `src/wasi_python/_outputs.py:61-66`), so the traceback at its end is what is lost.

## Decisions

### 1. The rows first

Written before the code, each seen failing first, in the `own-runner` shard (all three systems). No row measures time. New file `tests/unit/test_runner_streaming.py`:

- `test_every_kept_byte_arrives_in_order`: three flushed writes to stdout, one to stderr; each stream's chunks joined equal its `Completed` field.
- `test_output_arrives_while_the_guest_runs`: the guest prints `ready` with `flush=True`, then calls the door until the host answers `seen`; the host answers `seen` only once `on_output` has had `ready`. Delivery at the end would run to the deadline: `trapped == "deadline"` fails the row.
- `test_on_output_runs_on_the_calling_thread`: every call's `threading.get_ident()` is the caller's; under `run_async`, the loop's.
- `test_the_cap_bounds_what_is_delivered`: `output_bytes=5000`, 9,000 bytes written: 5,000 delivered, one chunk with `cut=True`, the stream's last.
- `test_an_exception_in_on_output_stops_delivery_only`: the callback raises on its first call: one call to `sys.unraisablehook`, one call to the callback, `exit_code == 0`, `stdout` whole.
- `test_a_base_exception_in_on_output_stops_the_call`: a `BaseException` subclass raised there is raised by `run`.
- `test_a_feed_yields_then_ends` (`OutputFeed` under `run_async`), and three `TypeError` rows: an async `on_output`, a feed under `run`, a feed used twice.
- `test_tail_keeps_the_end_and_marks_the_cut`: `output_bytes=100`, 1,000 bytes ending `END\n`: `stdout` starts with `[900 bytes cut]\n`, ends with `END\n`, is 100 bytes, `truncated == ("stdout",)`.
- `test_a_streamed_call_leaves_no_thread_behind`: the thread set equal before and after.

In `tests/unit/test_runner_sessions.py`: `test_a_turns_stdin_answers_input`, `test_a_turn_without_stdin_reads_end_of_file`, `test_stdin_is_the_turns_own` (a second turn never reads the first's leftover), `test_a_turn_streams_its_output`. In `tests/unit/test_cli.py`: `--stream` and `--output-keep tail`.

### 2. `on_output`: who calls it

`run`, `run_async`, `Session.run` and `Session.run_async` take `on_output: Callable[[OutputChunk], object] | None = None`. It is called on the thread that made the call, the call's home (`_home._Home`), which already serves the embedder's host, providers and tools while the guest runs on its own thread (`src/wasi_python/_home.py:243-265`). Under `run_async` and `Session.run_async` it is called on the event loop's thread: the home hands each batch to the loop with `call_soon_threadsafe`, which keeps the order. It must be synchronous: an async callable raises `TypeError` before any work, as `host` does (`runner._is_async_callable`).

The path. `_Stream` gains a sink. Its `write` hands the admitted bytes to the call's `_Feed` (`_outputs.py`), which appends them under its own lock and, when no delivery is pending, puts one hand-off in the home's inbox without waiting for it. The reader thread (`_PipeCapture._take`, `_outputs.py:217-245`) and wasmtime's callback thread (`_write_output`) never run the embedder's code, so a slow callback never blocks the guest in a host write. After `capture.close()` (`_call.py:540`), or a turn's `settle()` (`_sessions.py:840`), the home delivers what is left before the result is built.

### 3. What a chunk promises

`OutputChunk` is a frozen dataclass: `stream` (`"stdout"` or `"stderr"`), `data: bytes`, `cut: bool = False`. Within a stream, order is exact and adjacent pieces are joined. Across streams, chunks come in the order the runner read them, which is not always the guest's order of writes. A chunk is not a line. Every chunk is delivered before the call returns, at every ending that returns a result.

### 4. The cap bounds what is delivered

Per stream, at most `output_bytes` bytes are delivered, in either keep mode. The piece that reaches the cap carries `cut=True`, once; nothing more of that stream follows. So the home's queue holds at most the cap per stream. Under the default keep, the chunks joined are `Completed.stdout` exactly.

### 5. An exception in `on_output`

An `Exception` goes to `sys.unraisablehook`, Python's place for an error no caller can take. The callback is not called again in that call or turn; the guest runs on and the result is whole. So a guest's bytes cannot make `run` raise through a callback that chokes on them. A `BaseException` that is not an `Exception` stops the call, as one raised into the home does (`_Home.stop`), and `run` raises it.

### 6. The async iterator: `OutputFeed`

`run_async` stays a coroutine function, so `asyncio.create_task(run_async(...))` keeps working. `OutputFeed` is the iterator. It is a callable, so it is passed as `on_output`, and an async iterator of `OutputChunk`. The call ends it, whether it returns or raises:

```python
feed = wasi_python.OutputFeed()
task = asyncio.create_task(wasi_python.run_async(argv, on_output=feed))
async for chunk in feed:
    ...
done = await task
```

A feed serves one call. Under `run` or `Session.run` it raises `TypeError`, since nothing could iterate it while the call blocks.

### 7. Buffering stays the guest's

CPython buffers stdout in 8 KiB blocks when it is not a terminal. The runner does not change that, since more writes would move fuel for every call. A call streams line by line with `-u` (the reactor honours it: `recipes/reactor_bootstrap.py:106-120`) or `print(..., flush=True)`; a session with `sys.stdout.reconfigure(line_buffering=True)` in a turn. stderr is line-buffered already.

### 8. `output_keep="tail"`

`run`, `run_async`, `Session.run` and `Session.run_async` take `output_keep: Literal["head", "tail"] = "head"`; anything else is `ValueError`. `"head"` is today's, byte for byte, so no default moves (constitution §4.15). Under `"tail"` a stream keeps its last bytes: a buffer that grows to the cap and then wraps, never holding more. At the end, when bytes were cut, the result starts with `[N bytes cut]\n` and the rest of the cap is the tail, so `len(stdout) <= output_bytes` holds. A cap shorter than the marker keeps its tail alone. `truncated` names the stream as before; the marker is text the guest could also print, and `truncated` is the signal to trust.

### 9. A turn's stdin, through a new export

`Session.run` and `Session.run_async` take `stdin: bytes | bytearray | memoryview | None = None`, checked as `run`'s (`_limits._check_inputs`), at most `MAX_TURN_BYTES`.

Why a new export (READ). The C API opens a stdin file into an `AsyncReadStream` (`crates/c-api/src/wasi.rs:117-131`), whose task reads the file ahead and, at its first read of zero bytes, sends `Closed` and ends (`crates/wasi/src/p2/pipe.rs:160-180`). The session's empty file ends that task before any turn reads. Bytes added later never reach descriptor 0. A pipe would block the guest in a host read, beyond the deadline.

So the guest is given the bytes. `reactor_main.c` gains `turn_input(ptr, len) -> i32`, a `host_alloc` buffer as `turn`'s code is, kept until the next `turn` copies it into a `bytes` and frees it, on every path; `-1` is a refusal, under `turn`'s own refusals. `_drive_turn` (`_sessions.py:746`) calls it before `turn`. `turn(source, environ, stdin)` sets `sys.stdin` to a text reader over the bytes, with the old reader's encoding and errors, and restores it at the turn's end unless the turn replaced it. A turn without `stdin` adds nothing: `input()` reads end of file, as today. Descriptor 0 stays the empty stream. A set without the export raises `ArtifactsMissing` before the claim, read from `state.exports` in `Session._turn_args`. A checkpoint (162) is taken between turns, when no stdin is held.

### 10. Windows works without 153

On Windows the callback capture feeds the same `_Stream.write` on wasmtime's thread, so Decisions 2 to 8 hold there unchanged. 153 would make Windows cheaper, not possible.

### 11. The command line

`wasi-python run` gains `--output-keep {head,tail}`, one of `run`'s arguments, and `--stream`: one JSON line per chunk, `{"stream": …, "data": …}` (`data_base64` when the chunk is not UTF-8, as `cli._stream` does) with `"cut": true` on the cut, each flushed, then the result line, unchanged and last. Exit codes do not change.

### 12. Where it meets the others

163 edits `turn` and the same entry points; the second to land rebases and lists the lengths it measures. `_Stream.written` (163's Decision 8) is added by the first; the tail marker counts `written` less kept. `OutputChunk` carries stream bytes, never displays. No `Completed` field is added.

### 13. Growth, claimed

Both binaries grow by the export and the branch in `turn`, and every metered turn's fuel by that branch's few instructions. The news file claims both. A call's fuel does not move: `run` is unchanged in the guest.

## Intent

An agent sees a long run's progress as it happens, answers a turn's `input()`, and keeps the end of a long output, where the error is. Without the new arguments nothing changes.

## Design

- `src/wasi_python/_outputs.py`: `OutputChunk`, `OutputFeed`, `_Feed` (Decisions 2 to 6), `_Stream`'s sink, keep mode and wrap (Decision 8).
- `src/wasi_python/_call.py`: `_CheckedCall` gains `on_output` and `output_keep`; `_instance` builds the feed and delivers after `release`.
- `src/wasi_python/_sessions.py`: `_arm` and `_turn_inside` the same per turn; `_drive_turn` calls `turn_input`.
- `src/wasi_python/runner.py`: the keywords, checked in `_checked` and `_turn_args`. `__init__.py`: the two names.
- `src/wasi_python/cli.py`: Decision 11.
- `recipes/reactor_main.c`, `recipes/reactor_bootstrap.py`: Decision 9. `tests/harness/artifacts.py`: `turn_input` in both export sets, typed `(i32, i32) -> (i32)`.
- The judge: `tests/public_api.txt`, `LONG_FUNCTIONS`, the rows of Decision 1, `tests/release_shards.toml`.
- Documents: a how-to, `docs/how-to/output-while-it-runs.md`; `docs/how-to/sessions.md` (stdin); `docs/how-to/limits.md` and `docs/reference/defaults-and-limits.md` (`output_keep`); `docs/how-to/async.md` (the feed); `docs/reference/python-api.md`; `docs/reference/cli.md`.
- The news file, `context/changes/164-output-while-the-guest-runs.md`.

## Scope

In: the decisions above. Out: line buffering chosen by the runner (Decision 7); a `Defaults` field for `output_keep`; a session-wide `stdin` or `output_keep`; descriptor 0 for a turn; streaming 163's displays; Windows's pipe (153).

## Acceptance criteria

1. The rows of Decision 1 pass on three systems, each seen failing first on `dev`'s code (the pull request's description names the run).
2. Without the new arguments, every existing row passes unchanged and `stdout` is today's byte for byte (the own-runner shard, EXECUTED).
3. The two binaries export `turn_input` with its type (`tests/checks/test_v1_1_artifact_set.py`, EXECUTED).
4. No module-level mutable or lock, no private name and no platform branch is added; `ruff` and the rules checks are green; the listed lengths are claimed (READ by the reviewer, EXECUTED by `quick`).
5. The growth lines are the news file's claims and no others (the pull request's run, READ).
6. The documents of the Design say each new argument in words, with no specification number (`uv run pytest tests/lint`, EXECUTED).

## Landing notes

To be written at the landing.
