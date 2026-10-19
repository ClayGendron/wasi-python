/* For scipy.optimize.cython_optimize._zeros only, through recipes/scipy_file_includes.txt (spec
 * 037, Decision 6): it and scipy.optimize._zeros share the init name PyInit__zeros, and only one
 * may keep it in one static link. scripts/gen_inittab.py's RENAMED table names the same. */
#define PyInit__zeros PyInit_scipy_optimize_cython_optimize__zeros
