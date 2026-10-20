/* For statsmodels.tsa.statespace._smoothers._conventional only, through
 * recipes/statsmodels_file_includes.txt (spec 045, Decision 5): it and
 * statsmodels.tsa.statespace._filters._conventional share the init name PyInit__conventional, and
 * only one may keep it in one static link; the filter keeps it. scripts/gen_inittab.py's RENAMED
 * table names the same. */
#define PyInit__conventional PyInit_statsmodels_tsa_statespace__smoothers__conventional
