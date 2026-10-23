- **Project:** numpy (https://github.com/numpy/numpy)
- **Against:** numpy 2.5.2 (`downloads/SHA256SUMS`, `numpy-2.5.2.tar.gz`)
- **Status:** drafted
- **Title:** On targets whose `<fenv.h>` defines no exception flags (wasm32), keep numpy's own floating-point signals in software, so `numpy.linalg` raises `LinAlgError`
- **Files:** numpy/_core/src/npymath/ieee754.c.src, numpy/_core/src/npymath/ieee754.cpp, numpy/_core/src/common/float_status.hpp
- **Why we carry it:** spec 099 carries a recipe, not a patch: `recipes/npy_fenv_flags.h`, force-included into every numpy compile by `recipes/wasi-numpy.cross`. It gives the four flags bits and sends numpy's three `fe*` calls to one flag word.

**This is a facts sheet, not an issue or a pull request** (question 82(d); decision 80). The owner writes in their own words. Nothing has been posted, and no agent will post anything. numpy's AI policy keeps any description in the owner's words.

**The short version.** WebAssembly has no floating-point status flags. wasi-libc's `<fenv.h>` (EXECUTED, fact 1; Emscripten's musl-based `<fenv.h>` is likely the same shape, INFERRED, not read here) defines `FE_ALL_EXCEPT` as 0 and none of `FE_INVALID`, `FE_DIVBYZERO`, `FE_OVERFLOW`, `FE_UNDERFLOW`. numpy then defines the four as 0 (`ieee754.c.src`, `ieee754.cpp`, `float_status.hpp`). So the signals numpy raises itself, in software, are lost too: `npy_set_floatstatus_invalid()` is `feraiseexcept(0)`. `umath_linalg` reports a singular matrix by that call, and `numpy.linalg.inv` of a singular matrix returns `nan`s instead of raising `LinAlgError`. Integer division by zero warns nowhere. numpy's own tests skip these cases on wasm ("fp errors don't work in wasm"). Keeping a flag word for numpy's own explicit raises when the C library defines no flags would make them work on every wasm target; hardware arithmetic would still set nothing.

## The facts

1. **No flags in the C library** (EXECUTED: wasi-sdk 34's sysroot, `include/wasm32-wasip1/bits/fenv.h`: `#define FE_ALL_EXCEPT 0`, `#define FE_TONEAREST 0`, nothing else; `fenv.h` declares the functions).
2. **numpy's fallback makes its own raises no-ops** (READ, numpy 2.5.2, `numpy/_core/src/npymath/ieee754.c.src:343-405`: `#ifndef FE_INVALID #define FE_INVALID 0`, then `npy_set_floatstatus_invalid(void) { feraiseexcept(FE_INVALID); }`; `float_status.hpp:28-52`, the same as `constexpr` zeros, with `if constexpr (kAllExcept != 0)` around every call).
3. **`umath_linalg` signals every LAPACK failure by that flag** (READ, `numpy/linalg/umath_linalg.cpp:441-449`, `set_fp_invalid_or_clear`; `inv`, `solve`, `solve1`, `cholesky`, `eig`, `eigh`, `svd`, `lstsq`, `qr` call it), and `numpy/linalg/_linalg.py` turns the flag into `LinAlgError` through `errstate(call=..., invalid='call')`.
4. **In a wasm32-wasip1 build**, `numpy.linalg.inv`, `solve`, `tensorinv`, `tensorsolve`, `matrix_power(a, -1)` of `[[1, 2], [2, 4]]` and `cholesky` of `[[1, 2], [2, 1]]` return all-`nan` arrays with no exception; `np.array([1, 2]) // 0` warns nothing, and `np.errstate(divide='raise')` does not raise (EXECUTED, `context/research/2026-10-20-numpy-floating-point-status/fp_probe-guest-*.out`; natively each raises or warns, `fp_probe-native.out`).
5. **A flag word restores them** (EXECUTED, the same folder's `prototype/`: numpy's pattern in a C and a C++ translation unit; without bits, a raise is never seen; with bits and the three calls sent to one word, a C raise, a C++ `FloatStatus::RaiseOverflow` and a clear each round-trip; `1.0 / 0.0` still sets nothing).

## A shape the fix could take upstream

In `ieee754.c.src` and `ieee754.cpp`, when `FE_INVALID` is not defined, keep a `static int` status word: `npy_set_floatstatus_*` set its bits, `npy_get_floatstatus_barrier` reads it, and `npy_clear_floatstatus_barrier` clears it. `float_status.hpp`'s `Raise*` would call `npy_set_floatstatus_*` in that case. The tests numpy skips with "fp errors don't work in wasm" that test numpy's own signals (singular matrices, integer division) could then run on wasm; those that test hardware arithmetic stay skipped.
