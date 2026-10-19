/* freopen refused in the reactor (spec 037, Revised at build), linked with -Wl,--wrap=freopen.
 *
 * Its one caller in python.wasm is qhull's qh_initflags (scipy.spatial), for the `TO <file>`
 * option, which sends qhull's output to a file by reopening stdout. wasi-libc implements freopen
 * with fd_renumber, a WASI call no other code of this build makes and the runner does not watch
 * (its descriptor shadows: spec 068). Refused, `TO` fails as an unopenable file does: qhull
 * reports it and scipy raises QhullError. Nothing else changes. */
#include <errno.h>
#include <stdio.h>

FILE *__wrap_freopen(const char *path, const char *mode, FILE *stream)
{
    (void)path;
    (void)mode;
    (void)stream;
    errno = ENOTSUP;
    return NULL;
}
