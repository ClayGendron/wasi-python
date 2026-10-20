/* For sklearn.svm._libsvm_sparse only, through recipes/sklearn_file_includes.txt (spec 044,
 * Decision 6). Its generated C includes svm/src/libsvm/libsvm_sparse_helper.c, whose functions are
 * global, and fifteen of them share a name with a function of _libsvm's helper or _liblinear's:
 * harmless in separate shared objects, a duplicate symbol in one static link. _libsvm's keep their
 * names; these take a prefix, in the one translation unit that defines and calls them. */
#define copy_intercept sklearn_libsvm_sparse_copy_intercept
#define copy_n_iter sklearn_libsvm_sparse_copy_n_iter
#define copy_nSV sklearn_libsvm_sparse_copy_nSV
#define copy_probA sklearn_libsvm_sparse_copy_probA
#define copy_probB sklearn_libsvm_sparse_copy_probB
#define copy_support sklearn_libsvm_sparse_copy_support
#define copy_sv_coef sklearn_libsvm_sparse_copy_sv_coef
#define free_model sklearn_libsvm_sparse_free_model
#define free_param sklearn_libsvm_sparse_free_param
#define get_l sklearn_libsvm_sparse_get_l
#define get_nr sklearn_libsvm_sparse_get_nr
#define set_parameter sklearn_libsvm_sparse_set_parameter
#define set_verbosity sklearn_libsvm_sparse_set_verbosity
#define csr_set_problem sklearn_libsvm_sparse_csr_set_problem
#define free_problem sklearn_libsvm_sparse_free_problem
