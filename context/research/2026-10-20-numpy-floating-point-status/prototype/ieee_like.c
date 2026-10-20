/* numpy's ieee754.c.src pattern, word for word in shape: its FE_* defaults and its three calls. */
#include <fenv.h>
#ifndef FE_DIVBYZERO
#define FE_DIVBYZERO 0
#endif
#ifndef FE_OVERFLOW
#define FE_OVERFLOW 0
#endif
#ifndef FE_UNDERFLOW
#define FE_UNDERFLOW 0
#endif
#ifndef FE_INVALID
#define FE_INVALID 0
#endif

int get_status(void) {
    int s = fetestexcept(FE_DIVBYZERO | FE_OVERFLOW | FE_UNDERFLOW | FE_INVALID);
    return ((FE_DIVBYZERO & s) ? 1 : 0) | ((FE_OVERFLOW & s) ? 2 : 0) |
           ((FE_UNDERFLOW & s) ? 4 : 0) | ((FE_INVALID & s) ? 8 : 0);
}

int clear_status(void) {
    int s = get_status();
    if (s) {
        feclearexcept(FE_DIVBYZERO | FE_OVERFLOW | FE_UNDERFLOW | FE_INVALID);
    }
    return s;
}

void set_invalid(void) { feraiseexcept(FE_INVALID); }
void set_divbyzero(void) { feraiseexcept(FE_DIVBYZERO); }
