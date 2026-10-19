/* For scipy.special's _gufuncs, through recipes/scipy_file_includes.txt (spec 037, Decision 6;
 * Revised at build): xsf's functions inline (recipes/scipy_special_xsf.h), and what xsf defines in
 * headers outside XSF_HOST_DEVICE renamed for this module alone: the namespaces xsf::numpy (its
 * ufunc, gufunc and set_error_check_fpe) and xsf::numbers (i_v), wrap_PyUFunc_getfperr, and
 * xsf::struve_h and struve_l (xsf/struve.h). scipy.special._ufuncs keeps the names; each copy is
 * the same code. */
#include "scipy_special_xsf.h"
#define numpy numpy_gufuncs
#define numbers numbers_gufuncs
#define wrap_PyUFunc_getfperr wrap_PyUFunc_getfperr_gufuncs
#define struve_h struve_h_gufuncs
#define struve_l struve_l_gufuncs
