/* Rename header for the numpy cross build (spec 003), injected with -include into every numpy C file.
 *
 * numpy and pandas both define get_datetime_metadata_from_dtype: numpy's returns a pointer
 * (numpy/_core/src/multiarray/_datetime.h), pandas' vendored copy returns the struct by value
 * (pandas/_libs/src/vendored/numpy/datetime/np_datetime.c). As shared objects they never meet; in one
 * static python.wasm the linker keeps one and turns the other side's calls into a trap
 * (wasm-ld: function signature mismatch). pandas uses the name as a C-API struct member and in
 * function-like macros, so numpy's internal (NPY_NO_EXPORT) copy is the one renamed. */
#define get_datetime_metadata_from_dtype npy_get_datetime_metadata_from_dtype
