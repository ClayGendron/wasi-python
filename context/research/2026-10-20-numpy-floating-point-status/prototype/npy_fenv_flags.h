/* Drafting prototype for spec 099 (not the recipe itself; the builder writes that).
 * Force-included into every numpy C and C++ file. wasm has no floating-point status flags, and
 * wasi-libc's <fenv.h> defines no FE_INVALID, FE_DIVBYZERO, FE_OVERFLOW or FE_UNDERFLOW, so numpy
 * defines them 0 and its explicit raises (npy_set_floatstatus_*) and reads become no-ops.
 * Here they get bits, and the three calls numpy makes go to a flag word kept in software. */
#ifndef WASI_PYTHON_NPY_FENV_FLAGS_H
#define WASI_PYTHON_NPY_FENV_FLAGS_H

#include <fenv.h>
#ifdef __cplusplus
#include <cfenv>
#endif

#if defined(FE_INVALID) || defined(FE_DIVBYZERO) || defined(FE_OVERFLOW) || defined(FE_UNDERFLOW)
#error "the C library now defines floating-point exception flags: remove this recipe (spec 099)"
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
int wasi_python_feraiseexcept(int);
int wasi_python_fetestexcept(int);
int wasi_python_feclearexcept(int);
#ifdef __cplusplus
}
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
