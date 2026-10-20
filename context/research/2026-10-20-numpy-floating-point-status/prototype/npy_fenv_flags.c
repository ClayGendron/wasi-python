/* Drafting prototype for spec 099: the flag word. One per process; the guest has no threads. */
#include "npy_fenv_flags.h"

static int flags;

int wasi_python_feraiseexcept(int excepts) {
    flags |= excepts & FE_ALL_EXCEPT;
    return 0;
}

int wasi_python_fetestexcept(int excepts) {
    return flags & excepts & FE_ALL_EXCEPT;
}

int wasi_python_feclearexcept(int excepts) {
    flags &= ~(excepts & FE_ALL_EXCEPT);
    return 0;
}
