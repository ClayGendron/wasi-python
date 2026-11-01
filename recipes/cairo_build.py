"""Write cairocffi's bindings as one C source in cffi's out-of-line API mode, for a static link.

    cairo_build.py <cairocffi's constants.py> <out.c>

Run on the build host with the pinned cffi. The declarations are cairocffi's own
(`constants._CAIRO_HEADERS`), cut before its Windows and Quartz sections, which this cairo does
not have; the C compiler then proves each one exists. Upstream binds cairo at run time with
`ffi.dlopen` and makes its callbacks with `ffi.callback`, and the guest has neither a dynamic
loader nor libffi's closures. So this module is linked in, and it adds a fixed pool of static
callbacks (`extern "Python"`) for the three callback types cairocffi makes, which the stand-in
`cairocffi/ffi.py` hands out, and one helper that makes a cairo font face from a font file's bytes,
since this cairo has no fontconfig to find a font by its family name. A last helper calls one
callback of the pool from C, which the stand-in uses to drop what a freed slot last ran: cffi keeps
that until the slot runs again, and a call from Python would go through libffi, which is not here.
"""

import runpy
import sys

from cffi import FFI

# The pool's size per callback type; the stand-in ffi.py reads the same number from the module.
POOL = 128
# Each callback type cairocffi makes, its trampolines' name stem and C signature.
CALLBACKS = (
    ("read", "cairo_status_t", "void *, unsigned char *, unsigned int"),
    ("write", "cairo_status_t", "void *, const unsigned char *, unsigned int"),
    ("destroy", "void", "void *"),
)
# Where cairocffi's declarations stop being this cairo's: its Windows section comes first.
CUT = "typedef void* HDC;"

SOURCE = r"""
#include <cairo.h>
#include <cairo-pdf.h>
#include <cairo-ps.h>
#include <cairo-svg.h>
#include <cairo-ft.h>
#include <ft2build.h>
#include FT_FREETYPE_H

static const int wasi_cairo_pool = %(pool)d;
static FT_Library wasi_ft_library;
static const cairo_user_data_key_t wasi_ft_key;

static void wasi_ft_done(void *face) { FT_Done_Face((FT_Face)face); }

/* A cairo font face from a font file's bytes, which must outlive the face (FreeType reads them in
   place). The FreeType face is freed with the cairo face. NULL when FreeType cannot read them. */
static cairo_font_face_t *
wasi_cairo_ft_face_from_memory(const unsigned char *data, long size, int index)
{
    FT_Face face;
    cairo_font_face_t *font_face;
    if (!wasi_ft_library && FT_Init_FreeType(&wasi_ft_library))
        return NULL;
    if (FT_New_Memory_Face(wasi_ft_library, data, size, index, &face))
        return NULL;
    font_face = cairo_ft_font_face_create_for_ft_face(face, 0);
    if (cairo_font_face_set_user_data(font_face, &wasi_ft_key, face, wasi_ft_done)) {
        cairo_font_face_destroy(font_face);
        FT_Done_Face(face);
        return NULL;
    }
    return font_face;
}
"""


def run_slot() -> str:
    """C that calls slot n of a pool (0 read, 1 write, 2 destroy) with empty arguments: the
    trampolines declared ahead of cffi's definitions of them, a table of each pool, and the call."""
    out = []
    for stem, ret, args in CALLBACKS:
        out += [f"static {ret} _wasi_cairo_{stem}_{n}({args});" for n in range(POOL)]
        names = ", ".join(f"_wasi_cairo_{stem}_{n}" for n in range(POOL))
        out.append(f"static {ret} (*const wasi_{stem}_slots[{POOL}])({args}) = {{{names}}};")
    out.append(
        "void wasi_cairo_run_slot(int pool, int n)\n{\n"
        f"    if (n < 0 || n >= {POOL}) return;\n"
        "    if (pool == 0) wasi_read_slots[n](NULL, NULL, 0);\n"
        "    else if (pool == 1) wasi_write_slots[n](NULL, NULL, 0);\n"
        "    else if (pool == 2) wasi_destroy_slots[n](NULL);\n"
        "}\n"
    )
    return "\n".join(out)


def main() -> None:
    constants, out = sys.argv[1:]
    headers = runpy.run_path(constants)["_CAIRO_HEADERS"]
    if headers.count(CUT) != 1:
        raise SystemExit(f"{constants}: _CAIRO_HEADERS holds {CUT!r} {headers.count(CUT)} times")
    ffi = FFI()
    ffi.cdef(headers[: headers.index(CUT)])
    trampolines = [
        f'extern "Python" {ret} _wasi_cairo_{stem}_{n}({args});'
        for stem, ret, args in CALLBACKS
        for n in range(POOL)
    ]
    ffi.cdef(
        "\n".join(trampolines)
        + "\nstatic const int wasi_cairo_pool;"
        + "\ncairo_font_face_t *wasi_cairo_ft_face_from_memory(const unsigned char *, long, int);"
        + "\nvoid wasi_cairo_run_slot(int, int);"
    )
    ffi.set_source("_cairocffi_api", SOURCE % {"pool": POOL} + run_slot())
    ffi.emit_c_code(out)


if __name__ == "__main__":
    main()
