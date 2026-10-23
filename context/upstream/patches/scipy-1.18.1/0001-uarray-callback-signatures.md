- **Project:** scipy (https://github.com/scipy/scipy)
- **Against:** 1.18.1 (the pinned tarball)
- **Status:** drafted
- **Title:** uarray: give four getters and one METH_NOARGS method the signatures CPython calls them with
- **Files:** scipy/_lib/_uarray/_uarray_dispatch.cxx
- **Why we carry it:** on `wasm32-wasip1` a call through a function pointer of another type traps, so reading `_Function.arg_extractor`, `arg_replacer`, `default` or `domain`, or calling `_BackendState._pickle()`, would end the guest ("indirect call type mismatch").

**This is a facts sheet, not a pull request.** scipy's AI policy (https://scipy.github.io/devdocs/dev/conduct/ai_policy.html, READ 2026-10-19) does not permit an agent to submit a pull request, asks that no AI write the description, and requires a disclosure of what AI wrote. If the owner sends it, he writes the issue or pull request himself from these facts, with that disclosure. Nothing has been posted.

**What is wrong.** In `scipy/_lib/_uarray/_uarray_dispatch.cxx`, CPython calls a `PyGetSetDef` getter as `getter(PyObject *self, void *closure)` and a `METH_NOARGS` method as `PyCFunction(PyObject *self, PyObject *unused)`. Four getters (`Function::get_extractor`, `get_replacer`, `get_default`, `get_domain`, lines 1147-1150 and 1452-1471) take only `self`, and `BackendState::pickle_` (line 330), registered `METH_NOARGS` at line 1474, takes only `self`. The casts in the tables (`(getter)`, `(PyCFunction)`) hide the difference from the compiler. On the platforms scipy ships for, the extra argument is ignored by the calling convention; on WebAssembly an indirect call checks the callee's type and traps. scipy `main` at `6fc15de8` (2026-10-18) has the same lines (READ, the raw file).

**The change.** Each of the five gains the parameter CPython passes, unnamed: `void *` for the getters, `PyObject *` for `pickle_`. Nothing else; nothing calls them directly.

**How it was found and checked.** The judge's callback scan (spec 051, `test_callbacks_have_the_types_cpython_calls`) reads every method table, getset table and member table in the linked `python.wasm` and compares each callback's wasm type with the type CPython calls it as; it named these five (EXECUTED, spec 037's build, first link of scipy). With the patch it names none, and the scipy golden jobs, which use `scipy.fft`'s uarray backend, match native.

It is deleted, and the pin moved, when a scipy release carries the fix.
