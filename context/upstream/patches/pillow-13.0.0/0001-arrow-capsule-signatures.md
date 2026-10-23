- **Project:** Pillow (https://github.com/python-pillow/Pillow)
- **Against:** 13.0.0 (the pinned tarball)
- **Status:** drafted
- **Title:** Give the Arrow export methods the signature METH_VARARGS calls them with
- **Files:** src/_imaging.c
- **Why we carry it:** on `wasm32-wasip1` a call through a function pointer of the wrong type traps, so `Image.__arrow_c_schema__()` and `Image.__arrow_c_array__()` would end the guest in a wasm trap (`indirect call type mismatch`); spec 051's callback scan finds both in the linked `python.wasm` (spec 023).

This draft is not the pull request's description: the owner writes and sends it, from the facts in [`../../18-pillow-arrow-capsule-signatures/pr.md`](../../18-pillow-arrow-capsule-signatures/pr.md) (owner decision 80). Pillow's `AGENTS.md` (read on `main`, `6085656`, 2026-10-18) asks that new fixes carry tests and that every pre-commit hook pass; it names no rule on AI-written text, and the owner weighs that before sending. All of this change was written by an agent.

The change adds to `ExportArrowSchemaPyCapsule` and `ExportArrowArrayPyCapsule` the `args` parameter CPython passes a `METH_VARARGS` method; both ignore it, as before. Nothing else changes, on any platform. The patch applies to Pillow's `main` (`6085656`) as it is. `fix.patch` beside the facts is the carried patch, against 13.0.0.
