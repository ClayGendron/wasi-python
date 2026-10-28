# 144: a session is always ended

## Changelog

### Fixed

- **A session is always ended** (spec 144): a `close()` from a host function or a provider during a `run_async` turn no longer deadlocks, a queued turn cancelled after a `close()` is ended by a closer, a closer that cannot start runs where it was started, and a turn still queued at exit releases its claim. A `close()` from the event loop's thread during a `run_async` turn now waits for the ending, as the docstring says; a dropped session left marked by an abandoned turn is ended at once instead of at exit; a write the output capture could not keep marks its stream truncated; and the default pool a resize replaces is let go once its futures are done.

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
