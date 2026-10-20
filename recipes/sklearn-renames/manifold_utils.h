/* For sklearn.manifold._utils only, through recipes/sklearn_file_includes.txt (spec 044,
 * Decision 6): it and sklearn.tree._utils share the init name PyInit__utils, and only one may keep
 * it in one static link. scripts/gen_inittab.py's RENAMED table names the same. */
#define PyInit__utils PyInit_sklearn_manifold__utils
