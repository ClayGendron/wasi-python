- **Project:** kiwisolver (https://github.com/nucleic/kiwi)
- **Against:** 1.5.1 (the pinned tarball)
- **Status:** merged https://github.com/nucleic/kiwi/pull/245
- **Title:** Fix signature of `tp_clear` methods
- **Files:** py/src/constraint.cpp, py/src/expression.cpp, py/src/term.cpp, py/src/variable.cpp
- **Why we carry it:** `Constraint`, `Expression`, `Term` and `Variable` define their `tp_clear` as `void (*)(T*)` where CPython calls `int (*)(PyObject *)`; on `wasm32-wasip1` the call's type does not match, so any garbage collection that clears a cycle holding one of these objects ends the guest in `wasm trap: indirect call type mismatch` at `gc_collect_main` (spec 066's survey; spec 096).

There is nothing to send. Upstream already merged this fix: commit `4df2f39c01` (2026-09-10) of pull request #245, "Build wheels for WASM/Pyodide also" (<https://github.com/nucleic/kiwi/pull/245>), whose second part is "Fix signature of `tp_clear` methods". It is on `main` after 1.5.1 (tagged 2026-08-28) and in no release yet (READ, GitHub and PyPI, 2026-10-20: 1.5.1 is the newest).

The carried file is that commit's four C++ hunks (it also changes two CI workflows, which build nothing here), made against the 1.5.1 tarball with carried patch 0001 applied, in `git diff` form, so the build's applier takes it with no offset. Its changed lines equal the commit's in all four files, byte for byte (EXECUTED, `diff` of the `+` and `-` lines, spec 096's drafting). It also applies to the pristine 1.5.1 tarball. The two patches touch different functions.

When spec 096 is built, this file moves unchanged to `context/upstream/patches/kiwisolver-1.5.1/0002-tp-clear-returns-int.md`, and `fix.patch` is copied byte for byte to `recipes/patches/kiwisolver-1.5.1/0002-tp-clear-returns-int.patch`.

## The facts

- **The defect** (READ, `py/src/*.cpp` in 1.5.1). Each of the four types lists `{ Py_tp_clear, void_cast( X_clear ) }` in its `PyType_Slot` array, and `X_clear` returns `void`. CPython's `inquiry` is `int (*)(PyObject *)`, and `delete_garbage` in `Python/gc.c` calls it through that pointer for each object in a garbage cycle. Natively the missing return value is ignored, so nothing shows. WebAssembly's `call_indirect` checks the callee's type and traps.
- **Where it shows** (EXECUTED, spec 066's survey, `context/research/2026-10-20-the-compiled-packages-own-tests-under-the-runtime/kiwisolver-trap.txt`): kiwisolver's own tests trap the guest in `test_expression_creation`, then, with that deselected, in `test_term_creation` and `test_variable_rich_compare_operations`: wherever a collection meets a cycle. A program that makes one cycle through the four types and calls `gc.collect()` traps on both binaries (EXECUTED, spec 096, `context/research/2026-10-20-the-slot-scan/kiwi_cycle_flushed.out`); natively it prints `collected True` (`native-runs.out`).
- **Why the project's scan missed it.** Spec 051's callback scan read method and getset tables only; `PyType_Slot` arrays and the slots of static type objects were out of its scope. Spec 096 widens it, and the widened scan finds exactly these four in the linked `python.wasm` (`context/research/2026-10-20-the-slot-scan/slotscan-main-4eaf1c3d.txt`).
- **When to delete it:** when the pin moves to a kiwisolver release that carries `4df2f39c01` (1.5.2 or later); this draft's status then becomes `released <version>`, which the judge refuses while the patch stays.
