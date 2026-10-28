# 149: the runner's structure Lows are closed

## Changelog

### Fixed

- **Calls that start together no longer fail on macOS.** Two calls starting at the same moment could raise `KeyError` from `run()` when the module cache's folder has an access list. A retried read of a guest's output no longer marks its stream truncated. [Results and errors](https://claygendron.github.io/wasi-python/reference/results-and-errors/)

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
changed = [
    "tests/unit/test_process.py::test_the_observers_refuse_a_misspelt_field",
    "tests/unit/test_runner_outputs.py::test_output_arrives_above_descriptor_1024",
    "tests/unit/test_runner_outputs.py::test_a_reader_whose_wait_fails_still_reads_every_byte",
    "tests/unit/test_async_tools.py::test_a_late_gate_skips_an_async_tool",
    "tests/checks/test_rules.py::test_the_handlers_change_the_table_only_through_its_methods",
]
units = 9
```
