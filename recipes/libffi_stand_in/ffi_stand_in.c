/* libffi's entry points for wasm32-wasip1, the header's stand-in (ffi.h beside this file). The
   types are libffi's; a call description is accepted, a call through it aborts (wasm has no way to
   call a function whose signature is known only at run time), and a closure is refused. */
#include <stdlib.h>
#include "ffi.h"

#define TYPE(name, size, align, kind) ffi_type name = {size, align, kind, NULL}
TYPE(ffi_type_void, 1, 1, FFI_TYPE_VOID);
TYPE(ffi_type_uint8, 1, 1, FFI_TYPE_UINT8);
TYPE(ffi_type_sint8, 1, 1, FFI_TYPE_SINT8);
TYPE(ffi_type_uint16, 2, 2, FFI_TYPE_UINT16);
TYPE(ffi_type_sint16, 2, 2, FFI_TYPE_SINT16);
TYPE(ffi_type_uint32, 4, 4, FFI_TYPE_UINT32);
TYPE(ffi_type_sint32, 4, 4, FFI_TYPE_SINT32);
TYPE(ffi_type_uint64, 8, 8, FFI_TYPE_UINT64);
TYPE(ffi_type_sint64, 8, 8, FFI_TYPE_SINT64);
TYPE(ffi_type_float, 4, 4, FFI_TYPE_FLOAT);
TYPE(ffi_type_double, 8, 8, FFI_TYPE_DOUBLE);
TYPE(ffi_type_longdouble, 16, 16, FFI_TYPE_LONGDOUBLE);
TYPE(ffi_type_pointer, 4, 4, FFI_TYPE_POINTER);

/* Accepted: cffi builds a description for every function type it meets, API mode included. */
ffi_status ffi_prep_cif(ffi_cif *cif, ffi_abi abi, unsigned nargs, ffi_type *rtype, ffi_type **atypes)
{
    (void)cif; (void)abi; (void)nargs; (void)rtype; (void)atypes;
    return FFI_OK;
}

ffi_status ffi_prep_cif_var(ffi_cif *cif, ffi_abi abi, unsigned nfixed, unsigned ntotal,
                            ffi_type *rtype, ffi_type **atypes)
{
    (void)nfixed;
    return ffi_prep_cif(cif, abi, ntotal, rtype, atypes);
}

/* A call through a function pointer only ABI mode makes: no shipped package makes one. */
void ffi_call(ffi_cif *cif, void (*fn)(void), void *rvalue, void **avalue)
{
    (void)cif; (void)fn; (void)rvalue; (void)avalue;
    abort();
}

void *ffi_closure_alloc(size_t size, void **code)
{
    (void)size;
    if (code)
        *code = NULL;
    return NULL;
}

void ffi_closure_free(void *closure) { (void)closure; }

ffi_status ffi_prep_closure(ffi_closure *closure, ffi_cif *cif,
                            void (*fun)(ffi_cif *, void *, void **, void *), void *user_data)
{
    (void)closure; (void)cif; (void)fun; (void)user_data;
    return FFI_BAD_ABI;
}

ffi_status ffi_prep_closure_loc(ffi_closure *closure, ffi_cif *cif,
                                void (*fun)(ffi_cif *, void *, void **, void *), void *user_data,
                                void *codeloc)
{
    (void)codeloc;
    return ffi_prep_closure(closure, cif, fun, user_data);
}
