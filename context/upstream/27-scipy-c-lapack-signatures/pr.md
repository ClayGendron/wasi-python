# scipy: declare `?gees`, `chla_transtype` and `xerbla_array` as C LAPACK defines them (facts for the owner)

- **Project:** scipy (https://github.com/scipy/scipy)
- **Against:** 1.18.1 (the pinned sdist); the same lines are on `main` as read by spec 037's drafter
- **State:** facts for the owner to write from; nothing is carried for it: wasi_python's build uses shims of its own (`recipes/scipy_lapack_shims.c`) and rename headers (spec 037, Decision 6)
- **Policy, as read** (https://scipy.github.io/devdocs/dev/conduct/ai_policy.html, READ 2026-10-19): an autonomous agent may not submit a pull request; "In explaining your contribution, do not use AI to automatically generate descriptions"; AI must not speak for the contributor; "You must disclose whether AI has been used", naming the tools, how, and which code or text; the submitter must be able to explain the code. So this file is the facts, and the owner writes the pull request in his own words, with the disclosure, if he sends it.

## The facts

scipy built without a Fortran compiler links its LAPACK wrappers against a C LAPACK. OpenBLAS's C translation (`NOFORTRAN=1`), the one current C LAPACK, follows f2c. Three of scipy's declarations differ from it, which on WebAssembly is a trap (wasm-ld warns `function signature mismatch` and links a trapping stub; through f2py's function pointers it traps at run time with no warning). EXECUTED by wasi_python's research and spec 037's build gates:

1. **`?gees` in `scipy/linalg/flapack_gen.pyf.src`** (`callstatement` and `callprotoargument` of both templates): f2py passes two hidden string lengths, `..., &info, 1, 1`, 17 arguments. OpenBLAS's `?gees_` takes 15. Every other f2py wrapper in scipy passes none, and `cython_lapack`'s own `?gees` passes none; with gfortran's LAPACK the two extra arguments are harmless, with a C LAPACK on wasm they are a different signature.
2. **`chla_transtype` in `scipy/linalg/cython_lapack_signatures.txt`**: scipy declares `char chla_transtype(int *trans)`; f2c returns a CHARACTER function's value through its first argument, `void chla_transtype_(char *ret_val, ftnlen ret_val_len, integer *trans)`.
3. **`xerbla_array`** in the same file: scipy declares it with three arguments; f2c adds the hidden length of `srname_array`, four.

The fix: drop the two lengths from the `?gees` callstatement and prototype, and declare the other two as gfortran's ABI does (which, for a CHARACTER*1 function and a hidden length, matches f2c's). Whether scipy wants the C-LAPACK route supported at all is the maintainers' call; Pyodide's scipy build (Emscripten) meets the same signatures.

## Evidence

- `context/research/2026-10-17-openblas-one-return-convention.md` (the six clashes left on scipy's side after OpenBLAS's convention) and spec 037's direct-call gate (`scripts/f2py_direct_calls.py`, step 57's log): 0 mismatches with the shims, which take scipy's signatures and call OpenBLAS's.
