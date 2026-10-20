/* numpy's own floating-point signals, kept in software (spec 099). Force-included into every numpy
 * C and C++ compile by recipes/wasi-numpy.cross, as npy_rename.h is.
 *
 * WebAssembly has no floating-point status flags, and wasi-libc's <fenv.h> defines no FE_INVALID,
 * FE_DIVBYZERO, FE_OVERFLOW or FE_UNDERFLOW (FE_ALL_EXCEPT is 0). numpy then defines the four as 0
 * itself (npymath's ieee754.c.src, common/float_status.hpp), so the signals it raises in software
 * are lost when it compiles: npy_set_floatstatus_invalid() becomes feraiseexcept(0). That call is
 * how umath_linalg reports a failed LAPACK call, so numpy.linalg.inv of a singular matrix returned
 * nans instead of raising LinAlgError, and integer division by zero warned nowhere.
 *
 * Here the flags get bits, and numpy's three calls (feraiseexcept, fetestexcept, feclearexcept)
 * set, test and clear one flag word. The word is a weak definition in every object, and the static
 * link keeps one; step 60's weak-duplicate gate allows it by name
 * (recipes/weak-duplicates-allowed.txt). The guest has no threads; numpy clears the status before
 * each ufunc loop and umath_linalg at each loop's start, as it does natively. Arithmetic still sets nothing: wasm has
 * no flag for 1.0 / 0.0 to set, and that stays silent (the README says so).
 *
 * Remove this file, and its two cross-file lines, when wasi-libc's <fenv.h> defines the flags (the
 * #error below stops the build that day) or when a numpy release keeps its own status without them
 * (context/upstream/30-numpy-fp-status-without-fenv-flags/facts.md). */
#ifndef WASI_PYTHON_NPY_FENV_FLAGS_H
#define WASI_PYTHON_NPY_FENV_FLAGS_H

#include <fenv.h>
#ifdef __cplusplus
#include <cfenv>
#endif

#if defined(FE_INVALID) || defined(FE_DIVBYZERO) || defined(FE_OVERFLOW) || defined(FE_UNDERFLOW)
#error "the C library now defines floating-point exception flags: remove recipes/npy_fenv_flags.h (spec 099)"
#endif

#define FE_INVALID 0x01
#define FE_DIVBYZERO 0x04
#define FE_OVERFLOW 0x08
#define FE_UNDERFLOW 0x10
#define FE_INEXACT 0x20
#undef FE_ALL_EXCEPT
#define FE_ALL_EXCEPT (FE_INVALID | FE_DIVBYZERO | FE_OVERFLOW | FE_UNDERFLOW | FE_INEXACT)

#ifdef __cplusplus
extern "C" {
#endif
__attribute__((weak)) int wasi_python_fe_flags;

static inline int wasi_python_feraiseexcept(int excepts) {
    wasi_python_fe_flags |= excepts & FE_ALL_EXCEPT;
    return 0;
}

static inline int wasi_python_fetestexcept(int excepts) {
    return wasi_python_fe_flags & excepts & FE_ALL_EXCEPT;
}

static inline int wasi_python_feclearexcept(int excepts) {
    wasi_python_fe_flags &= ~(excepts & FE_ALL_EXCEPT);
    return 0;
}
#ifdef __cplusplus
}
/* numpy calls the three unqualified; the std:: spelling compiles too. */
namespace std {
using ::wasi_python_feclearexcept;
using ::wasi_python_feraiseexcept;
using ::wasi_python_fetestexcept;
}
#endif

#define feraiseexcept wasi_python_feraiseexcept
#define fetestexcept wasi_python_fetestexcept
#define feclearexcept wasi_python_feclearexcept

#endif
