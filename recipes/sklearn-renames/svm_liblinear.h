/* For sklearn.svm._liblinear's generated C and for svm/src/liblinear/linear.cpp, through
 * recipes/sklearn_file_includes.txt (spec 044, Decision 6). The module's C includes
 * liblinear_helper.c, whose five global functions below share names with _libsvm's and
 * _libsvm_sparse's helpers; and liblinear_helper.c's set_parameter calls set_seed, which linear.cpp
 * defines from svm/src/newrand/newrand.h beside its own mt_rand and bounded_rand_int, as libsvm's
 * template and the _newrand module each do. Each copy of the generator keeps its own state, as in
 * separate shared objects: this one takes the prefix sklearn_liblinear_ in both files, so the
 * module's call reaches liblinear's generator and no other. */
#define set_problem sklearn_liblinear_set_problem
#define csr_set_problem sklearn_liblinear_csr_set_problem
#define set_parameter sklearn_liblinear_set_parameter
#define free_problem sklearn_liblinear_free_problem
#define set_verbosity sklearn_liblinear_set_verbosity
#define mt_rand sklearn_liblinear_mt_rand
#define set_seed sklearn_liblinear_set_seed
#define bounded_rand_int sklearn_liblinear_bounded_rand_int
