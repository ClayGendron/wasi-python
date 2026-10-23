- **Project:** kiwisolver (https://github.com/nucleic/kiwi)
- **Against:** 1.5.1 (the pinned tarball)
- **Status:** drafted
- **Title:** Give the no-argument methods and getters the signatures CPython calls them with
- **Files:** py/src/constraint.cpp, py/src/expression.cpp, py/src/solver.cpp, py/src/strength.cpp, py/src/term.cpp, py/src/variable.cpp
- **Why we carry it:** on `wasm32-wasip1` a call through a function pointer of the wrong type traps, so `Solver.addConstraint`'s path, `Variable.value()` and seventeen more methods and four getters would end the guest in a wasm trap (`indirect call type mismatch`); spec 051's callback scan finds all 21 in the linked `python.wasm` (spec 023).

This draft is not the pull request's description: the owner writes and sends it, from the facts in [`../../19-kiwisolver-callback-signatures/pr.md`](../../19-kiwisolver-callback-signatures/pr.md) (owner decision 80). No contributor guide was found in the repository (`CONTRIBUTING.md` and `AGENTS.md` absent on `main`, `ef031dd`, 2026-10-18), so the owner writes it. All of this change was written by an agent.

The change adds to seventeen `METH_NOARGS` methods the unnamed `PyObject*` parameter CPython passes, and to four getters the unnamed `void*` closure; nothing else changes, on any platform. The patch applies to kiwisolver's `main` (`ef031dd`) as it is. `fix.patch` beside the facts is the carried patch, against 1.5.1.
