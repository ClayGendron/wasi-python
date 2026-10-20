/* For sklearn.svm._newrand's generated C++ only, through recipes/sklearn_file_includes.txt (spec
 * 044, Decision 6): the module wraps svm/src/newrand/newrand.h's generator for scikit-learn's own
 * tests (set_seed_wrap, bounded_rand_int_wrap), and defines its own copy, as libsvm's template and
 * linear.cpp do. This copy takes the prefix sklearn_newrand_ and keeps its own state. */
#define mt_rand sklearn_newrand_mt_rand
#define set_seed sklearn_newrand_set_seed
#define bounded_rand_int sklearn_newrand_bounded_rand_int
