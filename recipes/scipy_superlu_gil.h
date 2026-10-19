/* For scipy.sparse.linalg._dsolve's _superlu_utils.c only, through recipes/scipy_file_includes.txt
 * (spec 037, Decision 6; found at build: every spsolve aborted). SuperLU's calls release the GIL
 * with CPython's PyEval_SaveThread (_superluobject.h's SLU_BEGIN_THREADS), and its memory hooks
 * take it back with numpy's NPY_ALLOW_C_API. numpy here is built without threads
 * (-Ddisable-threading: NPY_NO_SMP), so that macro is empty, the hook runs with no thread state,
 * finds no SuperLU state and aborts. The three macros get numpy's own threaded definitions in this
 * file alone, so the GIL is taken back as on every other platform. */
#include <Python.h>
#include <numpy/ndarraytypes.h>
#undef NPY_ALLOW_C_API_DEF
#undef NPY_ALLOW_C_API
#undef NPY_DISABLE_C_API
#define NPY_ALLOW_C_API_DEF PyGILState_STATE __save__;
#define NPY_ALLOW_C_API do {__save__ = PyGILState_Ensure();} while (0);
#define NPY_DISABLE_C_API do {PyGILState_Release(__save__);} while (0);
