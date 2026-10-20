/* For sklearn.ensemble._hist_gradient_boosting._gradient_boosting only, through
 * recipes/sklearn_file_includes.txt (spec 044, Decision 6): it and sklearn.ensemble._gradient_boosting
 * share the init name PyInit__gradient_boosting, and only one may keep it in one static link.
 * scripts/gen_inittab.py's RENAMED table names the same. */
#define PyInit__gradient_boosting PyInit_sklearn_ensemble__hist_gradient_boosting__gradient_boosting
