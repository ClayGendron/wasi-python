/* freopen refused in the reactor (spec 037, Revised at build), linked with -Wl,--wrap=freopen.
 *
 * Its one caller in python.wasm is qhull's qh_initflags (scipy.spatial), for the `TI <file>`
 * option, which reads qhull's input from a file by reopening stdin (`TO`, the output file, is
 * refused by qhull before it gets there). wasi-libc implements freopen with fd_renumber, a WASI
 * call no other code of this build makes. The runner shadows and counts fd_renumber since spec 068,
 * so this is not a hole; the refusal keeps the import list as it is (the descriptor-import
 * tripwire) and costs nothing, since qhull's file options are no use in the sandbox. Refused,
 * `TI` fails as an unopenable file does: qhull reports it (QH6041) and scipy raises QhullError.
 * Nothing else changes. */
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
