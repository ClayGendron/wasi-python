- **Project:** OpenBLAS (https://github.com/OpenMathLib/OpenBLAS)
- **Against:** 0.3.34 (the pinned tarball)
- **Status:** drafted
- **Title:** C LAPACK: ilaver_ returns void, as the other subroutines now do
- **Files:** lapack-netlib/INSTALL/ilaver.c
- **Why we carry it:** ILAVER is a SUBROUTINE; scipy declares it `void` (f2py and `cython_lapack`), and on `wasm32-wasip1` a call whose signature differs from its definition's traps.

**The case.** `ILAVER` is a Fortran SUBROUTINE (it returns the LAPACK version through its three arguments). OpenBLAS's C translation defines it `int ilaver_(...)` with `return 0;`, as f2c wrote every subroutine. The series #6008 to #6082 on `develop` made every other subroutine of the C LAPACK return `void`; `ilaver_` in `lapack-netlib/INSTALL/ilaver.c` was left `int` (read on `develop` at `5137bb62`, 2026-10-18, line 322). A caller that declares it as the subroutine it is, `void ilaver_(int *, int *, int *)`, as scipy does, links against a function of another type. On WebAssembly that is a different signature: wasm-ld warns `function signature mismatch` and links a stub that traps when called.

**The change.** Two hunks in `ilaver.c`: `int ilaver_(` becomes `void ilaver_(`, and its `return 0;` becomes `return;`, the convention's rules R1 and R3.

**The test, run on `develop`** (EXECUTED 2026-10-19 by spec 037's builder, in a scratch folder: a shallow clone of `develop` at `5137bb62b4ca24fa88873809b845ffc18e601256`, built twice for `wasm32-wasip1` with step 38's make line, wasi-sdk 33): a three-line caller,

```c
void ilaver_(int *, int *, int *);
int main(void) { int a, b, c; ilaver_(&a, &b, &c); return a + b + c; }
```

compiled and linked with `wasm-ld --no-entry --allow-undefined --export=main` against the archive:

- `develop` as it is: `1 signature mismatch(es)`, `wasm-ld: warning: function signature mismatch: ilaver_`;
- `develop` with this patch (`git apply`, it applies cleanly): `0 signature mismatch(es)`.

(`develop` linked whole, `--whole-archive`, already has 0 clashes: the mismatch is only against a caller that declares the subroutine `void`.)

OpenBLAS has no contributor guide or rule on AI-written changes that the agent found (READ, 2026-10-19: `develop`'s top folder and `docs/`). The owner decides how to present it; a disclosure that an agent drafted the change is the honest default. It is deleted, and the pin moved, when an OpenBLAS release carries it.
