# kiwisolver: the no-argument methods and getters take the parameters CPython passes

Facts for the owner, who writes the pull request (owner decision 80). Nothing here is posted.

- **Base:** kiwisolver 1.5.1 (the pinned tarball); applies unchanged to `main` at `ef031dd`
  (2026-10-16), whose definitions are the same.
- **The defect.** Seventeen methods listed with `METH_NOARGS` are defined with one parameter
  (`Variable_name( Variable* self )`), where CPython calls `PyObject *(PyObject *self, PyObject
  *unused)`; four getters of `strength` are defined with one parameter where CPython calls
  `getter(PyObject *self, void *closure)`. Each is cast in its table.
  - methods: `Constraint_expression`, `Constraint_op`, `Constraint_strength`,
    `Constraint_violated`, `Expression_terms`, `Expression_constant`, `Expression_value`,
    `Solver_updateVariables`, `Solver_reset`, `Solver_dump`, `Solver_dumps`, `Term_variable`,
    `Term_coefficient`, `Term_value`, `Variable_name`, `Variable_context`, `Variable_value`;
  - getters: `strength_weak`, `strength_medium`, `strength_strong`, `strength_required`.
- **Why it matters.** Calling a function through a pointer of another type is undefined
  behaviour. Native ABIs ignore the extra argument. WebAssembly's `call_indirect` checks the
  callee's type and traps (`indirect call type mismatch`), so on `wasm32-wasip1` (and Pyodide)
  the first call ends the program: matplotlib's constrained layout, which uses kiwisolver, is
  one way to reach them.
- **The fix.** Add the unnamed parameter in C++ (`PyObject*` for the methods, `void*` for the
  getters). Twenty-one lines; nothing else changes on any platform.
- **Found by** spec 051's static scan of the linked `python.wasm` (`tests/harness/callbacks.py`):
  21 findings, every one in kiwisolver's `py/src/`.
