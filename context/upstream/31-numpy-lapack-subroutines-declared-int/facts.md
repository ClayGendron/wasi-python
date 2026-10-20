- **Project:** numpy (https://github.com/numpy/numpy)
- **Against:** numpy 2.5.2 (`downloads/SHA256SUMS`, `numpy-2.5.2.tar.gz`)
- **Status:** drafted
- **Title:** Declare LAPACK's subroutines and BLAS's `?copy` as returning `void` in `umath_linalg.cpp` and `lapack_litemodule.c`, so numpy links a LAPACK that defines them `void` on wasm
- **Files:** numpy/linalg/umath_linalg.cpp, numpy/linalg/lapack_litemodule.c
- **Why we carry it:** spec 100 carries a recipe, not a patch: `recipes/numpy_lapack_abi.h` sets numpy's own `BLAS_SYMBOL_PREFIX` for numpy's linear-algebra files, and `recipes/numpy_lapack_shims.c` gives each routine numpy calls an `int`-returning shim that calls OpenBLAS's `void` routine and returns 0. The recipe goes when a numpy release declares the subroutines `void`.

**This is a facts sheet, not an issue or a pull request** (question 82(d); decision 80). The owner
writes in their own words. Nothing has been posted, and no agent will post anything. numpy's AI
policy keeps any description in the owner's words.

**The short version.** numpy declares every LAPACK subroutine it calls, and BLAS's four `?copy`
routines, as returning `fortran_int`. They are Fortran subroutines: they return nothing. On x86-64
and arm64 the mismatch is harmless, because the caller just reads a register. On WebAssembly a
function's type includes its result, and a call through a type that differs from the definition's
traps. A LAPACK built for wasm that defines the subroutines `void` (OpenBLAS's C LAPACK does, as
does scipy's f2py interface to it) cannot be linked by numpy without a shim. numpy reads only
`info`, never the returned value, except that `lapack_litemodule.c` returns it in its result dict
(where natively it reads 0). Declaring the subroutines `void` would cost nothing natively and would
let numpy link such a LAPACK on any wasm target.

## The facts

1. **The declarations** (READ, numpy 2.5.2): `numpy/linalg/umath_linalg.cpp:98-401` declares 50
   routines `extern "C" fortran_int FNAME(...)`, among them `?geev`, `?syevd`/`?heevd`, `?gelsd`,
   `?geqrf`, `?orgqr`/`?ungqr`, `?gesv`, `?gesdd`, `?getrf`, `?potrf`, `?potri`, `?potrs`, `?copy`
   and `?gemm`; `?dot` returns its value and `?dotc`/`?dotu` are `void`, which is right.
   `numpy/linalg/lapack_litemodule.c:41-69` declares six more and `xerbla` the same way.
2. **The definitions are `void`** in OpenBLAS 0.3.34's C LAPACK as this project builds it for
   `wasm32-wasip1` (EXECUTED: wasm-ld reads each of the 54 routines' wasm type as `(i32, …) -> void`,
   but `sdot_` `-> f32` and `ddot_` `-> f64`; `context/research/2026-10-20-numpy-on-openblas/sigs.txt`).
3. **The mismatch traps** (EXECUTED: numpy's linear-algebra files compiled with numpy's own
   commands, as a build that found OpenBLAS would, and linked against OpenBLAS: 36 signature
   mismatches, the 35 routines numpy calls and `xerbla_`; the same folder's `proto.txt`,
   variant A). wasm-ld replaces each mismatched call with a stub that traps.
4. **numpy never uses the returned value in `umath_linalg.cpp`** (READ: each `call_*` wrapper
   passes a local `rv` as `info` and returns it, never the call's value, e.g. `call_gesv` at
   `umath_linalg.cpp:1670-1681`); `lapack_litemodule.c` returns it as `'<name>_'` in its dict, which is 0
   natively on OpenBLAS (EXECUTED, `xerbla-native-openblas.out`: `{'dorgqr_': 0, 'info': -5}`).
5. **`python_xerbla.c`** defines `xerbla` with two arguments returning an `int`; LAPACK's callers
   pass three (the hidden string length) and expect nothing. In a static link it would take
   LAPACK's own calls (variant A's 36th mismatch). Natively the shared OpenBLAS keeps its own
   `xerbla`, so numpy's is reached only by `lapack_lite.xerbla()`.

## A shape the fix could take upstream

In `umath_linalg.cpp` and `lapack_litemodule.c`, declare the subroutines `extern "C" void`, and have
`lapack_litemodule.c` put 0 in its `'<name>_'` entries (what native returns today). The ILP64 and
prefix machinery (`BLAS_FUNC`) does not change. `python_xerbla.c`'s signature is a separate
question: it overrides LAPACK's error routine only where the LAPACK resolves `xerbla` to numpy's.
