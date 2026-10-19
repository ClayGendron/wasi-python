/* For _fblasmodule.c and _flapackmodule.c only, through recipes/scipy_file_includes.txt (spec 037,
 * Decision 6). Both define f2py's numpy API pointer, _npy_f2py_ARRAY_API: two strong definitions,
 * a duplicate symbol in one static link. numpy's own hook makes these two weak, so the linker keeps
 * one; fortranobject.c keeps a strong extern reference, so a missing definition still fails the
 * link. Each module's import_array() writes the same numpy table into the one pointer. */
#define NPY_API_SYMBOL_ATTRIBUTE __attribute__((weak, visibility("hidden")))
