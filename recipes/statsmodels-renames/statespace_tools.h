/* For statsmodels.tsa.statespace._tools only, through recipes/statsmodels_file_includes.txt (spec
 * 045, Decision 5): it and scipy.sparse.csgraph._tools share the init name PyInit__tools, and only
 * one may keep it in one static link. scripts/gen_inittab.py's RENAMED table names the same. */
#define PyInit__tools PyInit_statsmodels_tsa_statespace__tools
