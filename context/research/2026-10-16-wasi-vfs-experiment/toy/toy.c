/* A toy reactor for the SDK check: reads a packed file, stats it, and writes in the root. */
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <wasi/api.h>

static int pinned = 1;
__wasi_errno_t __real___wasi_path_filestat_get(__wasi_fd_t, __wasi_lookupflags_t, const char *,
                                               __wasi_filestat_t *);
__wasi_errno_t __wrap___wasi_path_filestat_get(__wasi_fd_t fd, __wasi_lookupflags_t fl,
                                               const char *p, __wasi_filestat_t *st) {
    __wasi_errno_t e = __real___wasi_path_filestat_get(fd, fl, p, st);
    if (pinned && e == 0) st->ino = 0;
    return e;
}

__attribute__((export_name("run"))) int run(void) {
    pinned = 0;
    char line[64] = {0};
    FILE *f = fopen("/data/hello.txt", "r");
    if (!f) { perror("open packed"); return 1; }
    fgets(line, sizeof line, f);
    fclose(f);
    struct stat st;
    int s = stat("/data/hello.txt", &st);
    FILE *w = fopen("/rootfile.txt", "w");
    int wok = w && fputs("ok", w) >= 0;
    if (w) fclose(w);
    printf("packed: %s stat=%d size=%lld root-write=%d\n", strtok(line, "\n"), s,
           (long long)st.st_size, wok);
    return 0;
}
