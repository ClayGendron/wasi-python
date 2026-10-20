/* For sklearn.utils._random only, through recipes/sklearn_file_includes.txt (spec 044, Decision 6;
 * found at build): its init name, PyInit__random, is also CPython's own builtin `_random`
 * (Modules/_randommodule.c). In one static link the inittab's reference resolves to CPython's,
 * scikit-learn's archive member is never pulled in, and nothing warns: `sklearn.utils._random`
 * would be the stdlib's `_random`. scripts/gen_inittab.py's RENAMED table names the same, and its
 * --against check now stops on any init name CPython's own config.c already has. */
#define PyInit__random PyInit_sklearn_utils__random
