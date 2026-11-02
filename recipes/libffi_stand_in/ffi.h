/* A stand-in for libffi's header on wasm32-wasip1, which has no libffi port: cffi's C backend is
   compiled against it. The types and entry points are libffi's public ones. Building a call
   description succeeds, so cffi's API mode and its static `extern "Python"` callbacks work; a
   call through a C function pointer (ABI mode) aborts, and a run-time callback cannot be made. */
#ifndef WASI_LIBFFI_STAND_IN_H
#define WASI_LIBFFI_STAND_IN_H
#include <stddef.h>

typedef enum { FFI_FIRST_ABI = 0, FFI_DEFAULT_ABI = 1, FFI_LAST_ABI } ffi_abi;
typedef enum { FFI_OK = 0, FFI_BAD_TYPEDEF, FFI_BAD_ABI, FFI_BAD_ARGTYPE } ffi_status;

#define FFI_TYPE_VOID 0
#define FFI_TYPE_INT 1
#define FFI_TYPE_FLOAT 2
#define FFI_TYPE_DOUBLE 3
#define FFI_TYPE_LONGDOUBLE 4
#define FFI_TYPE_UINT8 5
#define FFI_TYPE_SINT8 6
#define FFI_TYPE_UINT16 7
#define FFI_TYPE_SINT16 8
#define FFI_TYPE_UINT32 9
#define FFI_TYPE_SINT32 10
#define FFI_TYPE_UINT64 11
#define FFI_TYPE_SINT64 12
#define FFI_TYPE_STRUCT 13
#define FFI_TYPE_POINTER 14
#define FFI_TYPE_COMPLEX 15

typedef struct _ffi_type {
    size_t size;
    unsigned short alignment;
    unsigned short type;
    struct _ffi_type **elements;
} ffi_type;
typedef struct {
    ffi_abi abi;
    unsigned nargs;
    ffi_type **arg_types;
    ffi_type *rtype;
    unsigned bytes;
    unsigned flags;
} ffi_cif;
typedef struct {
    void *trampoline_table;
    ffi_cif *cif;
    void (*fun)(ffi_cif *, void *, void **, void *);
    void *user_data;
} ffi_closure;
typedef unsigned long ffi_arg;
typedef signed long ffi_sarg;

extern ffi_type ffi_type_void, ffi_type_uint8, ffi_type_sint8, ffi_type_uint16, ffi_type_sint16,
    ffi_type_uint32, ffi_type_sint32, ffi_type_uint64, ffi_type_sint64, ffi_type_float,
    ffi_type_double, ffi_type_longdouble, ffi_type_pointer;
/* wasm32: int and long are 32 bits. */
#define ffi_type_uchar ffi_type_uint8
#define ffi_type_schar ffi_type_sint8
#define ffi_type_ushort ffi_type_uint16
#define ffi_type_sshort ffi_type_sint16
#define ffi_type_uint ffi_type_uint32
#define ffi_type_sint ffi_type_sint32
#define ffi_type_ulong ffi_type_uint32
#define ffi_type_slong ffi_type_sint32
#define FFI_CLOSURES 1

ffi_status ffi_prep_cif(ffi_cif *, ffi_abi, unsigned, ffi_type *, ffi_type **);
ffi_status ffi_prep_cif_var(ffi_cif *, ffi_abi, unsigned, unsigned, ffi_type *, ffi_type **);
void ffi_call(ffi_cif *, void (*)(void), void *, void **);
void *ffi_closure_alloc(size_t, void **);
void ffi_closure_free(void *);
ffi_status ffi_prep_closure(ffi_closure *, ffi_cif *, void (*)(ffi_cif *, void *, void **, void *),
                            void *);
ffi_status ffi_prep_closure_loc(ffi_closure *, ffi_cif *,
                                void (*)(ffi_cif *, void *, void **, void *), void *, void *);
#endif
