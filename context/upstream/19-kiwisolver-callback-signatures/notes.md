# How the kiwisolver fix was found and checked (spec 023)

- Spec 023's first build linked kiwisolver 1.5.1's `_cext` into `python.wasm`. A guest
  `Solver().addConstraint(x >= 10)` trapped with `indirect call type mismatch` (EXECUTED), and
  `test_callbacks_have_the_types_cpython_calls` (spec 051) listed 21 kiwisolver findings among
  24 (EXECUTED; spec 023's landing notes).
- The fix adds the ignored parameter to the 21 definitions (`fix.patch`, made by a script that
  rewrote each definition line once and refused any other count). After it the scan reports no
  kiwisolver finding, and the guest calls every one of the 21 (`test_patched_callbacks_run`,
  EXECUTED).
- `git apply --check` of the patch onto the six files of `main` (`ef031dd`) succeeds (EXECUTED,
  2026-10-18).
