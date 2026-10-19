/* For scipy.special's cython_special, through recipes/scipy_file_includes.txt (spec 037, Decision 6;
 * Revised at build): its Cython `cdef public` wrap_PyUFunc_getfperr is defined by five other
 * modules too (each one line, PyUFunc_getfperr()); renamed here, scipy.special._ufuncs keeps it. */
#define wrap_PyUFunc_getfperr wrap_PyUFunc_getfperr_cython_special
