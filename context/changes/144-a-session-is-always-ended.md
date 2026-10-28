# 144: a session is always ended

## Changelog

### Fixed

- **`close()` inside a tool no longer hangs, and every session ends.** A `close()` from a tool or a mount's provider during `run_async` used to deadlock; it now returns at once and the session ends with its turn. A turn cancelled while queued, or still queued at exit, no longer leaves its session open. [Know how a session ends](https://claygendron.github.io/wasi-python/how-to/sessions/#know-how-a-session-ends)

### Upgrading

- **`close()` on the event loop's thread now waits for the ending.** During a `run_async` turn, a `close()` called from the loop's own thread used to return at once; it now blocks until the session has ended. Await the turn first, or close from another thread. [Close it, and write files within a turn](https://claygendron.github.io/wasi-python/how-to/sessions/#close-it-and-write-files-within-a-turn)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "144"
new = [
    "tests/unit/test_runner_sessions.py::test_close_from_a_host_function_in_a_run_async_turn_returns_at_once",
    "tests/unit/test_runner_sessions.py::test_close_from_the_loop_thread_waits_for_the_ending",
    "tests/unit/test_runner_sessions.py::test_a_queued_turn_cancelled_after_a_close_is_ended",
    "tests/unit/test_runner_sessions.py::test_a_closer_that_cannot_start_ends_the_session_where_it_was_started",
    "tests/unit/test_runner_sessions.py::test_an_abandoned_turns_session_dropped_is_ended_by_the_reaper",
    "tests/unit/test_runner_async.py::test_a_program_exiting_with_a_turn_queued_ends_the_session",
    "tests/unit/test_runner_async.py::test_a_replaced_pool_is_dropped_once_its_futures_are_done",
    "tests/unit/test_runner_outputs.py::test_a_stream_whose_write_raises_reports_dropped",
    "tests/unit/test_lifecycles.py::test_the_session_table_row[TURN-TAKE_TURN]",
    "tests/unit/test_lifecycles.py::test_the_session_table_row[STOPPING-TAKE_TURN]",
    "tests/unit/test_runner_sessions.py::test_close_from_a_sync_tool_in_a_run_async_turn_ends_the_session",
    "tests/unit/test_runner_sessions.py::test_close_from_an_async_tool_in_a_run_async_turn_ends_the_session",
]
units = 12
```
