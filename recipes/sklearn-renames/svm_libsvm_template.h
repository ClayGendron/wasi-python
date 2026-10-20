/* For svm/src/libsvm/libsvm_template.cpp only (the libsvm-skl static library), through
 * recipes/sklearn_file_includes.txt (spec 044, Decision 6): svm.cpp, which it includes twice,
 * defines the random generator of svm/src/newrand/newrand.h, as linear.cpp and the _newrand module
 * do. Only svm.cpp calls it (svm_train and svm_cross_validation seed it first), so this copy takes
 * the prefix sklearn_libsvm_ and keeps its own state. bounded_rand_int is `inline` inside
 * extern "C", a weak definition: a missed rename would link silently, so step 60's weak-duplicate
 * gate and its link-map check stand behind this header. */
#define mt_rand sklearn_libsvm_mt_rand
#define set_seed sklearn_libsvm_set_seed
#define bounded_rand_int sklearn_libsvm_bounded_rand_int
