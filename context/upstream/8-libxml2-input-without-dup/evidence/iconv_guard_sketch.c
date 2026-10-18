/* Scratch: refuse iconv conversions whose wasi-libc decoder is known wrong (GB18030). */
#include <ctype.h>
#include <errno.h>
#include <iconv.h>
iconv_t __real_iconv_open(const char *to, const char *from);
static int is_gb18030(const char *name) {
    static const char want[] = "gb18030";
    const char *w = want;
    if (!name) return 0;
    for (; *name; name++) {
        if (!isalnum((unsigned char)*name)) continue;
        if (*w == '\0' || tolower((unsigned char)*name) != *w) return 0;
        w++;
    }
    return *w == '\0';
}
iconv_t __wrap_iconv_open(const char *to, const char *from) {
    if (is_gb18030(to) || is_gb18030(from)) {
        errno = EINVAL;
        return (iconv_t)-1;
    }
    return __real_iconv_open(to, from);
}
