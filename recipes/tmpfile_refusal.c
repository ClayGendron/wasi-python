/* tmpfile() for wasm32-wasip1, which wasi-libc lacks: refused with ENOTSUP. cairo's PostScript
   surface is its one caller, so making a PostScript surface raises cairo's error, while PNG, PDF
   and SVG output never call it. A working tmpfile would need a writable folder the guest is not
   given. Linked inside cairocffi's binding module, since it is cairo that calls it. */
#include <errno.h>
#include <stdio.h>

FILE *tmpfile(void)
{
    errno = ENOTSUP;
    return NULL;
}
