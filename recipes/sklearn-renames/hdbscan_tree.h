/* For sklearn.cluster._hdbscan._tree only, through recipes/sklearn_file_includes.txt (spec 044,
 * Decision 6): it and sklearn.tree._tree share the init name PyInit__tree, and only one may keep
 * it in one static link. scripts/gen_inittab.py's RENAMED table names the same. */
#define PyInit__tree PyInit_sklearn_cluster__hdbscan__tree
