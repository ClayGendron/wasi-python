# 164: Output while the guest runs, and stdin for a turn

- **Status:** drafted 2026-10-30; revised the same day against its pre-build review (`../reviews/164-output-while-the-guest-runs-spec-2026-10-30.md`, "Fit to build after amendments"), every finding taken as its Disposition says. Reviewed before build: the public API, the guest's exports and the build recipe change (constitution §5.6). The owner chose it on 2026-10-30 (`../decisions.md`, "The scope of 0.1.3").
- **Date:** 2026-10-30
- **Owner:** Clay Gendron
- **Kind:** public API and **build-class**; **not structural** by spec 108's letter (no new state, private name, platform branch or seam). Listed lengths that rise, claimed (spec 142): `runner.py:run`, `run_async`, `Session.run_async`, `_sessions.py:_open_session` (one line); `_call.py:_instance` falls (Decision 12). `src/`: `_outputs.py`, `_home.py`, `_call.py`, `_sessions.py`, `_limits.py`, `runner.py`, `cli.py`, `__init__.py`. Recipe: `recipes/reactor_main.c` (the export `turn_input`), `recipes/reactor_bootstrap.py` (`turn` takes the turn's stdin). Both binaries, `MANIFEST` and `SHA256SUMS` change; the zip does not. No pin, no patch.
- **Depends on:** landed 015, 055, 078, 129, 142. It lands **before 163**, which reuses its `_Stream` (the sink, the keep, `written`) and its result helper (Decision 12). 162: a checkpoint frees a held stdin buffer (Decision 9). Not 153 (Decision 10).
- **Research it stands on:** `../research/2026-10-30-what-0-1-3-could-carry.md` (§1; §2, item D). wasmtime's source, READ in the clones of 49.0.3 and `main` at `2d9c19b`, which agree (50.0.1 INFERRED): `crates/c-api/src/wasi.rs:117-131`, `crates/wasi/src/p2/pipe.rs:150-190`.

Labels: READ means read from a file, cited; INFERRED means reasoned.

## The problem

A call returns its output when the guest ends (`src/wasi_python/_call.py:551-562`): a long run's progress arrives late, or never if the deadline comes first. A session turn's `input()` reads an empty stream: the session's stdin is an empty file written at the opening (`src/wasi_python/_sessions.py:1057-1059`), and `Session.run` has no `stdin` (`src/wasi_python/runner.py:1146`). A stream past `output_bytes` keeps its head (`src/wasi_python/_outputs.py:61-66`), so the traceback at its end is lost.

## Decisions

### 1. The rows first

Written first, each seen failing, in the `own-runner` shard; none measures time. `tests/unit/test_runner_streaming.py`:

- `test_every_kept_byte_arrives_in_order`: each stream's chunks joined equal its `Completed` field.
- `test_output_arrives_while_the_guest_runs`: the guest prints `ready` flushed, then calls the door until the host answers `seen`, once `on_output` has had `ready`; late delivery ends at the deadline.
- `test_on_output_runs_on_the_calling_thread` (under `run_async`, the loop's).
- `test_the_cap_bounds_what_is_delivered`: `output_bytes=5000`, 9,000 bytes: 5,000 delivered, one `cut=True`, the stream's last; and the cap met exactly, then one more write: an empty chunk with `cut=True`.
- `test_an_exception_in_on_output_stops_delivery_only`: under `pytest.warns(RuntimeWarning)`, with the default `sys.unraisablehook`: one warning, one callback call, `exit_code == 0`, `stdout` whole.
- `test_a_base_exception_in_on_output_stops_the_call`: under `run` and `run_async`, the call raises it.
- `test_a_feed_follows_its_task`, `test_a_feed_ends_when_its_task_is_cancelled_before_it_starts`, and three `TypeError` rows: an async `on_output`, a feed under `run`, a feed used twice.
- `test_tail_keeps_the_end_and_marks_the_cut`: `output_bytes=100`, 1,000 bytes ending `END\n`: `stdout` starts `[900 bytes cut]\n`, ends `END\n`, is 100 bytes, `truncated == ("stdout",)`.

`tests/unit/test_home.py`: `post` runs on the home, a `BaseException` from it stops the home, a `post` after a stop does nothing. `tests/unit/test_runner_sessions.py`: a turn's stdin answers `input()`; a turn without it reads end of file; no turn reads another's leftover; a turn streams. A streamed call leaves no thread behind. `tests/unit/test_cli.py`: `--stream` and `--output-keep tail`.

### 2. `on_output`: who calls it

`run`, `run_async`, `Session.run` and `Session.run_async` take `on_output: Callable[[OutputChunk], object] | None = None`. It must be synchronous: an async callable raises `TypeError` before any work, as `host` does. It runs on the call's home, the thread that made the call, which already serves the embedder's host, providers and tools (`src/wasi_python/_home.py:243-265`).

The path. `_Stream` gains a sink: its `write` hands the admitted bytes to the call's `_Feed`, made by `_outputs._feed_for(on_output, keep, home, loop)`, which appends them under its own lock and, when no delivery is pending, calls `home.post(feed.deliver)`. `_home.py` gains `_Home.post(fn)`, a hand-off nobody waits for: `serve` runs it; a `BaseException` that is not an `Exception` goes to `self.stop(e)`, so the guest stops and the call raises it; a `post` after a stop does nothing. The reader thread and wasmtime's callback thread never run the embedder's code, so a slow callback never blocks a guest's write.

Under `run_async` and `Session.run_async`, `deliver` posts each batch with `loop.call_soon_threadsafe` to a wrapper that catches `Exception` (Decision 5) and hands any other `BaseException` to `home.stop`; a closed loop's `RuntimeError` at the post stops delivery for the call. The last delivery, after `capture.close()` (`_call.py:540`) or the turn's `settle()` (`_sessions.py:840`), runs only when the home has not stopped.

### 3. What a chunk promises

`OutputChunk` is a frozen dataclass: `stream` (`"stdout"` or `"stderr"`), `data: bytes`, `cut: bool = False`. Within a stream, order is exact and adjacent pieces are joined; across streams it is the order the runner read them. A chunk is not a line. Every chunk is delivered before the call returns, at every ending that returns a result; under `run_async`, before the coroutine resumes, since the last batch is posted before the worker returns and `asyncio.wrap_future` resumes through the same queue.

### 4. The cap bounds what is delivered

Per stream, at most `output_bytes` bytes are delivered, in either keep mode. The first byte past the cap marks the stream: the piece that crosses it carries `cut=True`; if the piece that met the cap has gone already, an empty chunk with `cut=True` follows. Once, and nothing more of that stream. So the queue holds at most the cap per stream; with `output_bytes=None` nothing bounds it but the guest's output, as nothing bounds `Completed.stdout`. Under the default keep, the chunks joined are `Completed.stdout` exactly.

### 5. An exception in `on_output`

An `Exception` is reported by `warnings.warn` as a `RuntimeWarning` naming its type and message, outside every lock, as the runner reports other faults no caller can take (`_private_dirs._flush_warnings`). The callback is not called again in that call or turn; the guest runs on and the result is whole. So a guest's bytes cannot make `run` raise through a callback that chokes on them. Any other `BaseException` stops the call (Decision 2).

### 6. The async iterator: `OutputFeed`

`run_async` stays a coroutine function, so `create_task` keeps working. `OutputFeed` is passed as `on_output` and iterated with its task:

```python
feed = wasi_python.OutputFeed()
task = asyncio.create_task(wasi_python.run_async(argv, on_output=feed))
async for chunk in feed.follow(task):
    ...
done = await task
```

`follow` ends once the task is done, whatever its outcome, after the chunks already queued, so a task cancelled before its first line still ends it. `run_async` also ends the feed in a `finally` around its whole body, the argument checks included. A feed serves one call; under `run` or `Session.run` it raises `TypeError`.

### 7. Buffering stays the guest's

CPython buffers a stdout that is not a terminal; the runner keeps that, since more writes would move fuel. A call streams line by line with `-u` (`recipes/reactor_bootstrap.py:106-120`) or `print(..., flush=True)`; a session with `sys.stdout.reconfigure(line_buffering=True)`. stderr is line-buffered already.

### 8. `output_keep="tail"`

The four entry points take `output_keep: Literal["head", "tail"] = "head"`; anything else is `ValueError`. `"head"` is today's, byte for byte, so no default moves (constitution §4.15). Under `"tail"` a stream keeps its last bytes: a buffer that grows to the cap and then wraps. When bytes were cut, the result starts `[N bytes cut]\n` (N is `written` less kept) and the rest of the cap is the tail, so `len(stdout) <= output_bytes` holds; a cap shorter than the marker keeps its tail alone. `truncated` is the signal to trust: a guest could print the marker. The chunks are still the output's start (Decision 4); the traceback is in the result.

### 9. A turn's stdin, through a new export

`Session.run` and `Session.run_async` take `stdin: bytes | bytearray | memoryview | None = None`, checked as `run`'s (`_limits._check_inputs`), at most `MAX_TURN_BYTES`.

Why an export (READ): the C API reads a stdin file through an `AsyncReadStream` (`crates/c-api/src/wasi.rs:117-131`) whose task ends at its first empty read (`crates/wasi/src/p2/pipe.rs:160-180`), so bytes added later never reach descriptor 0; a pipe would block the guest beyond the deadline.

`reactor_main.c` gains `turn_input(ptr, len) -> i32`: a `host_alloc` buffer, as `turn`'s code is, kept until the next `turn` copies it into a `bytes` and frees it on every path. A second `turn_input` before `turn` frees the first. A `NULL` pointer with a length above 0 is the host's out-of-memory: the turn raises `MemoryError` before its code, as for a `NULL` code buffer. `shutdown`, `prepare` and 162's `checkpoint` free a held buffer; `-1` is a refusal, under `turn`'s own. `_drive_turn` (`_sessions.py:746`) calls it before `turn`. `turn(source, environ, stdin)` sets `sys.stdin` to a text reader over the bytes, with the old reader's encoding and errors, and restores it at the turn's end unless the turn replaced it. Without `stdin`, `input()` reads end of file, as today; descriptor 0 stays empty. When `stdin` is given on a set without the export, `ArtifactsMissing` is raised before the claim, from a flag the opening sets from the module's export names (`_sessions.py:1010`).

### 10. Windows works without 153

Windows's callback capture feeds the same `_Stream.write`, so Decisions 2 to 8 hold there; 153 would make it cheaper, not possible.

### 11. The command line

`wasi-python run` gains `--output-keep {head,tail}` (in `VALUED`) and `--stream`: one JSON line per chunk, `{"stream": …, "data": …}` (`data_base64` when not UTF-8, as `cli._stream` does), `"cut": true` on the cut, each flushed. Standard output then holds the chunk lines, then the result or error line; Ctrl-C exits 130 after the chunks written. `cli.py`'s docstring says so. Exit codes do not change.

### 12. One helper for the result, and where 163 meets it

`_instance` (listed at 157), `_turn_inside` (78) and `_checked` (76) are at the ceiling. The last delivery and the `Completed` of a call and of a turn are built by one helper in `_call.py` that both call; the feed is made in `_outputs._feed_for`; the two keyword checks go to `_limits`. `_instance` falls by what it moves; `_turn_inside` and `_checked` stay at or under 80. 164 lands first; 163 extends this helper and reads `_Stream.written`. No `Completed` field is added; chunks never carry displays. The pull request states `runner.py`'s new length (1,318 today; ceiling 1,500).

### 13. Growth, measured and claimed

Both binaries grow. Turns grow by the branch; calls may grow too, since the plain binary unmarshals the bootstrap at every start and the snapshot's heap shifts with it. The news file claims every row the gather lists under GROWTH, by prefix where a family moves together, and both binaries' measured bytes. It predicts nothing.

## Intent

An agent sees progress live, answers a turn's `input()`, and keeps a long output's end, where the error is.

## Design

- `_outputs.py`: `OutputChunk`, `OutputFeed`, `_Feed`, `_feed_for`; `_Stream`'s sink, keep, wrap and `written`. `_home.py`: `_Home.post`.
- `_call.py`: `_CheckedCall.on_output` and `output_keep`; the result helper. `_sessions.py`: `_arm`, `_turn_inside`, `_drive_turn`, the opening's flag. `_limits.py`: the two checks. `runner.py`: the keywords. `__init__.py`: the two names. `cli.py`: Decision 11.
- `recipes/reactor_main.c`, `recipes/reactor_bootstrap.py`: Decision 9. `tests/harness/artifacts.py`: `turn_input` in both export sets, typed `(i32, i32) -> (i32)`.
- The judge: `tests/public_api.txt`, `LONG_FUNCTIONS`, Decision 1's rows, `tests/release_shards.toml`.
- Documents: `docs/how-to/output-while-it-runs.md`, in `mkdocs.yml`'s nav: keep `on_output` short, since your host and providers wait while it runs; hand bytes to a queue, or use `OutputFeed`. `docs/how-to/sessions.md`: a turn's stdin is `sys.stdin` alone (`fileno()` raises). `docs/how-to/limits.md`, `docs/how-to/async.md`, `docs/reference/defaults-and-limits.md`, `python-api.md`, `cli.md`.
- The news file, `context/changes/164-output-while-the-guest-runs.md`.

## Scope

Out: line buffering chosen by the runner (Decision 7); a `Defaults` field or a session-wide `stdin` or `output_keep`; descriptor 0 for a turn; streaming 163's displays; Windows's pipe (153).

## Acceptance criteria

1. Decision 1's rows pass on three systems, each seen failing first (the pull request names the run).
2. Without the new arguments, every existing row passes unchanged (the own-runner shard, EXECUTED).
3. Both binaries export `turn_input` with its type (`tests/checks/test_v1_1_artifact_set.py`, EXECUTED).
4. No module-level mutable or lock, no private name, no platform branch; `_turn_inside` and `_checked` at or under 80 lines; the rises claimed (the rules checks under `quick`, EXECUTED; READ by the reviewer).
5. Every growth line is a news-file claim, and both binaries' bytes are recorded (the pull request's run, READ).
6. The documents say each new argument in words, with no specification number (`uv run pytest tests/lint`, EXECUTED).

## Landing notes

To be written at the landing.
