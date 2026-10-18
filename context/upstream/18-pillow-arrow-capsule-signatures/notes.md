# How the Pillow fix was found and checked (spec 023)

- Spec 023's first build linked Pillow 13.0.0's `_imaging` into `python.wasm`.
  `test_callbacks_have_the_types_cpython_calls` (spec 051) then listed two Pillow findings among
  24: `__arrow_c_schema__` and `__arrow_c_array__` (EXECUTED; spec 023's landing notes).
- The fix adds the ignored `args` parameter to both (`fix.patch`). After it the scan reports no
  Pillow finding, and the guest calls both methods (the build's
  `test_patched_callbacks_run`, EXECUTED).
- `git apply --check` of the patch onto `main`'s `src/_imaging.c` (`6085656`) succeeds with no
  offset (EXECUTED, 2026-10-18).
