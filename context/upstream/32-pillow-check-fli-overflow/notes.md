# Pillow: `checks/check_fli_overflow.py` fails on native Pillow too

Facts only (spec 066); nothing is drafted to send. The owner decides whether to report.

- **What the check wants.** `checks/check_fli_overflow.py::test_fli_overflow` opens `Tests/images/fli_overflow.fli` and calls `load()`, with the comment "this should not crash with a malloc error or access violation". It passes only if `load()` returns.
- **What happens.** Native Pillow 13.0.0 (the repo's oracle, `build/oracle/venv`, darwin-arm64) raises `OSError: unrecognized data stream contents when reading image file` (EXECUTED, spec 066's rebuild and its confirming review). The guest raises the same message. Neither crashes.
- **Why nobody upstream sees it.** No test command in the sdist names `checks/check_fli_overflow.py`: `testpaths = ["Tests"]`, `tox.ini`, the Makefile and the wheel's `test-command` (which runs only `checks/check_wheel.py`) leave it out.
- **The gap it closes.** `tests/upstream/expected/pillow/fli-overflow-native.txt`, one member, in spec 066's `pillow` group. If Pillow changes the check (to expect the `OSError`, or to drop it), the class empties and its gap says "remove the gap".
