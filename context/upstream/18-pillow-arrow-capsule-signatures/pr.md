# Pillow: the Arrow export methods take the `args` parameter CPython passes

Facts for the owner, who writes the pull request (owner decision 80). Nothing here is posted.

- **Base:** Pillow 13.0.0 (the pinned tarball); applies unchanged to `main` at `6085656` (2026-10-17), whose two definitions are the same.
- **The defect.** `src/_imaging.c` lists `__arrow_c_schema__` and `__arrow_c_array__` in `methods[]` with `METH_VARARGS`, so CPython calls each as `PyObject *(PyObject *self, PyObject *args)`. Both are defined with one parameter, `(ImagingObject *self)`, and cast to `PyCFunction` in the table.
- **Why it matters.** Calling a function through a pointer of another type is undefined behaviour in C. On most native ABIs the extra argument is ignored. WebAssembly's `call_indirect` checks the callee's type and traps (`indirect call type mismatch`), so on `wasm32-wasip1` (and Emscripten, under Pyodide) the first call ends the program.
- **The fix.** Add `PyObject *args` to both definitions. Two lines; nothing else changes on any platform.
- **Found by** spec 051's static scan of the linked `python.wasm` (`tests/harness/callbacks.py`), which reported `method __arrow_c_schema__: table index … has (i32) -> (i32), called as (i32, i32) -> (i32) (ExportArrowSchemaPyCapsule)` and the same for `__arrow_c_array__`.
- **A test upstream could add:** none is needed for native platforms; the cast stays. A Pyodide or WASI CI job would catch the class.
