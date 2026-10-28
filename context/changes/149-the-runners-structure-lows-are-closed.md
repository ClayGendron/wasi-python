# 149: the runner's structure Lows are closed

## Changelog

### Fixed

- **Two calls that start at the same moment no longer trip over a C library call the runner resolves once** (spec 149): on macOS `run()` no longer raises `KeyError` when the module cache's folder has an access list, and no call is refused for an unreadable stack; and a read of a guest's output pipe that fails and is retried no longer names the stream in `truncated`.

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "149"
new = [
    "tests/unit/test_runner_threads.py::test_a_resolve_once_table_is_never_seen_half_filled[linux stack]",
    "tests/unit/test_runner_threads.py::test_a_resolve_once_table_is_never_seen_half_filled[macos stack]",
    "tests/unit/test_runner_threads.py::test_a_resolve_once_table_is_never_seen_half_filled[macos access list]",
    "tests/unit/test_runner_threads.py::test_a_resolve_once_table_is_never_seen_half_filled[windows stack]",
    "tests/unit/test_runner_waits.py::test_a_misaligned_pointer_records_its_stop_through_the_table",
    "tests/unit/test_runner_waits.py::test_the_poll_and_the_call_require_their_table",
    "tests/unit/test_runner_waits.py::test_a_number_the_table_holds_above_2_is_ready",
    "tests/unit/test_runner_outputs.py::test_a_failed_read_loses_no_byte_and_names_no_stream",
    "tests/unit/test_runner_outputs.py::test_an_end_never_read_again_names_its_stream",
    "tests/checks/test_rules.py::test_only_the_platform_modules_import_its_halves",
]
retired = [
    "tests/unit/test_runner_waits.py::test_with_no_table_every_number_above_2_is_ready",
]
changed = [
    "tests/unit/test_process.py::test_the_observers_refuse_a_misspelt_field",
    "tests/unit/test_runner_outputs.py::test_output_arrives_above_descriptor_1024",
    "tests/unit/test_runner_outputs.py::test_a_reader_whose_wait_fails_still_reads_every_byte",
    "tests/unit/test_async_tools.py::test_a_late_gate_skips_an_async_tool",
    "tests/checks/test_rules.py::test_the_handlers_change_the_table_only_through_its_methods",
]
units = 9
```
