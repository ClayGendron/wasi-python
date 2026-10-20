/* For sklearn._cyutility only, through recipes/sklearn_file_includes.txt (spec 044, Decision 6):
 * pandas and scipy each have a Cython shared utility module of the same name, and only one may
 * keep its init name, and its module-is-main flag, in one static link. scripts/gen_inittab.py's
 * RENAMED table names the same. */
#define PyInit__cyutility PyInit_sklearn__cyutility
#define __pyx_module_is_main__cyutility __pyx_module_is_main_sklearn__cyutility
